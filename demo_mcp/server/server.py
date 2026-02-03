"""
CreditNexus MCP Server - Hybrid x402 Approach
Payment-protected tools using official x402 facilitator + CreditNexus allowlist
Serves optional Plaid KYC: GET /plaid/link-token, POST /plaid/exchange (for onboarding).
"""

import sys
import os
from pathlib import Path

# Path bootstrap: support both monorepo (CreditNexus root) and standalone (demo_mcp root)
_root = Path(__file__).resolve().parent.parent  # demo_mcp directory
if _root.parent and (_root.parent / "demo_mcp").is_dir() and (_root.parent / "demo_mcp").resolve() == _root.resolve():
    sys.path.insert(0, str(_root.parent))  # monorepo: demo_mcp.server resolves
else:
    sys.path.insert(0, str(_root))  # standalone: server resolves

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

# Import configuration (dual-mode: standalone first, then monorepo)
try:
    from server.config import PORT, SERVICE_KEY
    from server.services import (
        create_plaid_link_token,
        exchange_plaid_public_token,
        get_borrower_score_for_agent,
    )
except ImportError:
    from demo_mcp.server.config import PORT, SERVICE_KEY
    from demo_mcp.server.services import (
        create_plaid_link_token,
        exchange_plaid_public_token,
        get_borrower_score_for_agent,
    )

# Initialize FastMCP server
logger.info("Initializing CreditNexus MCP Server")
mcp = FastMCP(
    name="creditnexus-x402",
    instructions="Payment-protected tools for CreditNexus using x402 protocol v2. Supports stock predictions, backtesting, and banking tools."
)

# Register all tools (dual-mode)
try:
    from server.tools import register_all_tools
except ImportError:
    from demo_mcp.server.tools import register_all_tools

logger.info("Registering MCP tools")
register_all_tools(mcp)

# ----- Vendored API routes (standalone: stock stub + Plaid/agent-score in P3) -----
# #region agent log
try:
    from server.vendored.stock_stub import stub_daily, stub_backtest
except ImportError:
    from demo_mcp.server.vendored.stock_stub import stub_daily, stub_backtest
# #endregion


@mcp.custom_route("/api/stock-prediction/daily", methods=["GET"])
async def api_stock_prediction_daily(request: Request):
    """Stub or proxied daily prediction. Query: symbol (required), horizon (default 30). Optional X-API-Key."""
    if SERVICE_KEY:
        api_key = request.headers.get("X-API-Key")
        if api_key != SERVICE_KEY:
            return JSONResponse({"detail": "Missing or invalid X-API-Key"}, status_code=401)
    params = request.query_params
    symbol = (params.get("symbol") or "").strip()
    if not symbol:
        return JSONResponse({"detail": "symbol is required"}, status_code=400)
    try:
        horizon = int(params.get("horizon", "30"))
    except ValueError:
        horizon = 30
    result = stub_daily(symbol, horizon=horizon)
    return JSONResponse(result)


@mcp.custom_route("/api/stock-prediction/backtest", methods=["POST"])
async def api_stock_prediction_backtest(request: Request):
    """Stub or proxied backtest. Body: symbol (required), start, end, strategy (optional). Optional X-API-Key."""
    if SERVICE_KEY:
        api_key = request.headers.get("X-API-Key")
        if api_key != SERVICE_KEY:
            return JSONResponse({"detail": "Missing or invalid X-API-Key"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)
    body = body or {}
    symbol = (body.get("symbol") or "").strip()
    if not symbol:
        return JSONResponse({"detail": "symbol is required"}, status_code=400)
    result = stub_backtest(
        symbol,
        start_date=body.get("start"),
        end_date=body.get("end"),
        strategy=body.get("strategy"),
    )
    return JSONResponse(result)


@mcp.custom_route("/api/banking/link-token", methods=["GET"])
async def api_banking_link_token(request: Request):
    """Return Plaid link token (vendored when STANDALONE). Optional X-API-Key."""
    if SERVICE_KEY:
        api_key = request.headers.get("X-API-Key")
        if api_key != SERVICE_KEY:
            return JSONResponse({"detail": "Missing or invalid X-API-Key"}, status_code=401)
    try:
        result = await create_plaid_link_token()
        return JSONResponse(result)
    except Exception as e:
        logger.exception("api/banking/link-token failed")
        return JSONResponse({"error": str(e)}, status_code=502)


@mcp.custom_route("/api/banking/connect", methods=["POST"])
async def api_banking_connect(request: Request):
    """Exchange Plaid public_token and store (vendored when STANDALONE). Body: public_token, optional agent_wallet. Optional X-API-Key."""
    if SERVICE_KEY:
        api_key = request.headers.get("X-API-Key")
        if api_key != SERVICE_KEY:
            return JSONResponse({"detail": "Missing or invalid X-API-Key"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    body = body or {}
    public_token = (body.get("public_token") or "").strip()
    if not public_token:
        return JSONResponse({"error": "public_token required"}, status_code=400)
    agent_wallet = body.get("agent_wallet") or body.get("wallet")
    try:
        result = await exchange_plaid_public_token(public_token, agent_wallet=agent_wallet)
        return JSONResponse(result)
    except Exception as e:
        logger.exception("api/banking/connect failed")
        return JSONResponse({"error": str(e)}, status_code=502)


@mcp.custom_route("/api/agent-score", methods=["GET"])
async def api_agent_score(request: Request):
    """Return Plaid-derived score for agent wallet. Query: wallet=0x... Optional X-API-Key."""
    if SERVICE_KEY:
        api_key = request.headers.get("X-API-Key")
        if api_key != SERVICE_KEY:
            return JSONResponse({"detail": "Missing or invalid X-API-Key"}, status_code=401)
    wallet = (request.query_params.get("wallet") or "").strip()
    if not wallet:
        return JSONResponse({"detail": "wallet query parameter required"}, status_code=400)
    score = await get_borrower_score_for_agent(wallet)
    if score is None:
        return JSONResponse({"detail": "No Plaid connection for this agent wallet"}, status_code=404)
    return JSONResponse({"plaid_score": score})


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
