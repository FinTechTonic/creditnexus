"""
CreditNexus MCP Server - Hybrid x402 Approach
Payment-protected tools using official x402 facilitator + CreditNexus allowlist
Serves optional Plaid KYC: GET /plaid/link-token, POST /plaid/exchange (for onboarding).
"""

import sys
import os
from pathlib import Path

# Add demo_mcp to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import logging

# CORS for onboarding (different origin) calling /plaid/*; passed to run(), not add_middleware (MCP middleware is different from ASGI)
CORS_MIDDLEWARE = [Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])]

# Load environment variables (centralized - only here)
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configure logging to match backend format
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration
from demo_mcp.server.config import PORT
from demo_mcp.server.services import create_plaid_link_token, exchange_plaid_public_token

# Initialize FastMCP server
logger.info("Initializing CreditNexus MCP Server")
mcp = FastMCP(
    name="creditnexus-x402",
    instructions="Payment-protected tools for CreditNexus using x402 protocol v2. Supports stock predictions, backtesting, and banking tools."
)

# Register all tools
from demo_mcp.server.tools import register_all_tools

logger.info("Registering MCP tools")
register_all_tools(mcp)


# ----- Plaid KYC HTTP routes (for onboarding; no x402 payment here) -----

@mcp.custom_route("/plaid/link-token", methods=["GET"])
async def plaid_link_token(request: Request):
    """Return Plaid link token from CreditNexus (X-API-Key). For onboarding optional Plaid step."""
    try:
        result = await create_plaid_link_token()
        return JSONResponse(result)
    except Exception as e:
        logger.exception("Plaid link-token failed")
        try:
            status = getattr(e, "response", None)
            if status is not None and hasattr(status, "status_code"):
                return JSONResponse(
                    {"error": getattr(e, "message", str(e)), "status_code": status.status_code},
                    status_code=min(status.status_code, 502),
                )
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=502)


@mcp.custom_route("/plaid/exchange", methods=["POST"])
async def plaid_exchange(request: Request):
    """Exchange Plaid public_token via CreditNexus. Body: { \"public_token\": \"...\", \"wallet\": \"0x...\" } (wallet optional, for borrower score)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    body = body or {}
    if not isinstance(body, dict):
        return JSONResponse({"error": "Body must be a JSON object"}, status_code=400)
    public_token = body.get("public_token")
    if not public_token:
        return JSONResponse({"error": "public_token required"}, status_code=400)
    agent_wallet = body.get("wallet") or body.get("agent_wallet")
    try:
        result = await exchange_plaid_public_token(public_token, agent_wallet=agent_wallet)
        return JSONResponse(result)
    except Exception as e:
        logger.exception("Plaid exchange failed")
        try:
            status = getattr(e, "response", None)
            if status is not None and hasattr(status, "status_code"):
                return JSONResponse(
                    {"error": getattr(e, "message", str(e)), "status_code": status.status_code},
                    status_code=min(status.status_code, 502),
                )
        except Exception:
            pass
        return JSONResponse({"error": str(e)}, status_code=502)


if __name__ == "__main__":
    logger.info("CreditNexus MCP Server (x402 Hybrid) starting on port %s", PORT)
    logger.info("Protocol: x402 v2, Networks: Aptos Testnet + Base Sepolia")
    logger.info("Tools: run_prediction, run_backtest, open_bank_account, get_agent_reputation_score, get_borrower_score")

    mcp.run(transport="http", host="127.0.0.1", port=PORT, middleware=CORS_MIDDLEWARE)
