"""
Stock Backtest Tool with x402 Payment Protection
Implements HTTP 402 Payment Required pattern
"""

import logging
from typing import Optional

try:
    from server.config import PRICE_BACKTEST_USD, ONRAMP_URL
    from server.services import verify_payment, settle_payment, build_payment_requirements, call_backtest
except ImportError:
    from demo_mcp.server.config import PRICE_BACKTEST_USD, ONRAMP_URL
    from demo_mcp.server.services import verify_payment, settle_payment, build_payment_requirements, call_backtest

logger = logging.getLogger(__name__)


async def run_backtest(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    strategy: Optional[str] = "chronos",
    payment_payload: Optional[dict] = None
) -> dict:
    """
    Run trading strategy backtest with x402 payment protection.

    Flow:
    1. If no payment_payload → Return 402 with payment_requirements
    2. If payment_payload exists → Verify with x402 facilitator
    3. If valid → Settle payment on-chain
    4. If settled → Call CreditNexus backend
    5. Return backtest result + payment receipt

    Args:
        symbol: Stock symbol (e.g., "AAPL", "TSLA")
        start_date: Backtest start date (YYYY-MM-DD, optional)
        end_date: Backtest end date (YYYY-MM-DD, optional)
        strategy: Trading strategy name (default: "chronos")
        payment_payload: x402 v2 PaymentPayload (optional)

    Returns:
        402 response with payment_requirements OR
        Backtest result with payment_receipt
    """

    if not payment_payload:
        logger.info("Backtest request without payment: symbol=%s, strategy=%s", symbol, strategy)
        requirements = build_payment_requirements(
            amount_usd=PRICE_BACKTEST_USD,
            resource=f"/mcp/backtest/{symbol}",
            description=f"Backtest for {symbol} ({strategy} strategy)"
        )

        return {
            "status": 402,
            "message": "Payment Required",
            "paymentRequirements": requirements,
            "resource": {
                "url": f"/mcp/backtest/{symbol}",
                "description": f"Trading strategy backtest for {symbol}",
                "mimeType": "application/json"
            },
            "onrampUrl": ONRAMP_URL
        }

    logger.info("Processing paid backtest: symbol=%s, strategy=%s", symbol, strategy)

    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_BACKTEST_USD,
        resource=f"/mcp/backtest/{symbol}",
        description=f"Backtest for {symbol} ({strategy} strategy)"
    )

    verification = await verify_payment(payment_payload, payment_requirements)

    if not verification.get("isValid"):
        logger.warning("Payment verification failed: %s", verification.get('invalidReason'))
        return {
            "status": 403,
            "error": "Payment verification failed",
            "reason": verification.get("invalidReason"),
            "payer": verification.get("payer")
        }

    logger.info("Payment verified for payer: %s", verification.get('payer'))

    settlement = await settle_payment(payment_payload, payment_requirements, verification)

    if not settlement.get("success"):
        logger.error("Payment settlement failed: %s", settlement.get('errorReason'))
        return {
            "status": 500,
            "error": "Payment settlement failed",
            "reason": settlement.get("errorReason"),
            "payer": verification.get("payer")
        }

    logger.info("Payment settled: tx=%s", settlement.get('transactionHash'))

    try:
        backtest_result = await call_backtest(symbol, start_date, end_date, strategy)
        logger.info("Backtest completed for %s", symbol)
    except Exception as e:
        logger.error("Backend backtest failed: %s", str(e))
        return {
            "status": 500,
            "error": "Backend service failed",
            "reason": str(e),
            "payer": verification.get("payer"),
            "paymentReceipt": {
                "transaction": settlement.get("transaction"),
                "network": settlement.get("network"),
                "payer": verification.get("payer"),
                "amount": PRICE_BACKTEST_USD,
                "settled": True
            },
            "note": "Payment was processed. Please contact support for refund."
        }

    return {
        "status": 200,
        "result": backtest_result,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": verification.get("payer"),
            "amount": PRICE_BACKTEST_USD,
            "resource": f"/mcp/backtest/{symbol}",
            "settled": True
        }
    }


def register_tools(mcp):
    """Register backtest tools with FastMCP server"""
    mcp.tool()(run_backtest)
