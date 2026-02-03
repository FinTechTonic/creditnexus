"""
MCP Tools Package
Payment-protected tools for CreditNexus
"""

import logging

try:
    from server.tools.prediction import register_tools as register_prediction_tools
    from server.tools.backtest import register_tools as register_backtest_tools
    from server.tools.banking import register_tools as register_banking_tools
    from server.tools.scores import register_tools as register_score_tools
except ImportError:
    from demo_mcp.server.tools.prediction import register_tools as register_prediction_tools
    from demo_mcp.server.tools.backtest import register_tools as register_backtest_tools
    from demo_mcp.server.tools.banking import register_tools as register_banking_tools
    from demo_mcp.server.tools.scores import register_tools as register_score_tools

logger = logging.getLogger(__name__)


def register_all_tools(mcp):
    """Register all MCP tools with the FastMCP server"""
    register_prediction_tools(mcp)
    logger.info("Registered run_prediction tool")

    register_backtest_tools(mcp)
    logger.info("Registered run_backtest tool")

    register_banking_tools(mcp)
    logger.info("Registered open_bank_account tool")

    register_score_tools(mcp)
    logger.info("Registered get_agent_reputation_score and get_borrower_score tools")


__all__ = [
    'register_prediction_tools',
    'register_backtest_tools',
    'register_banking_tools',
    'register_score_tools',
    'register_all_tools',
]
