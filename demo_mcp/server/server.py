"""
CreditNexus MCP Server - Hybrid x402 Approach
Payment-protected tools using official x402 facilitator + CreditNexus allowlist
"""

import sys
import os
from pathlib import Path

# Add demo_mcp to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP
from dotenv import load_dotenv
import logging

# Load environment variables (centralized - only here)
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configure logging to match backend format
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration
from demo_mcp.server.config import PORT

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


if __name__ == "__main__":
    logger.info("CreditNexus MCP Server (x402 Hybrid) starting on port %s", PORT)
    logger.info("Protocol: x402 v2, Networks: Aptos Testnet + Base Sepolia")
    logger.info("Tools: run_prediction, run_backtest, open_bank_account")

    mcp.run(transport="http", host="127.0.0.1", port=PORT)
