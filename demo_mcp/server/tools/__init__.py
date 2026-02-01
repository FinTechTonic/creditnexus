"""
MCP Tools Package
Payment-protected tools for CreditNexus
"""

import logging

from demo_mcp.server.tools.prediction import register_tools as register_prediction_tools
from demo_mcp.server.tools.backtest import register_tools as register_backtest_tools
from demo_mcp.server.tools.banking import register_tools as register_banking_tools

logger = logging.getLogger(__name__)


def register_all_tools(mcp):
    """Register all MCP tools with the FastMCP server"""
    register_prediction_tools(mcp)
    logger.info("Registered run_prediction tool")

    register_backtest_tools(mcp)
    logger.info("Registered run_backtest tool")

    register_banking_tools(mcp)
    logger.info("Registered open_bank_account tool")


__all__ = [
    'register_prediction_tools',
    'register_backtest_tools',
    'register_banking_tools',
    'register_all_tools',
]
