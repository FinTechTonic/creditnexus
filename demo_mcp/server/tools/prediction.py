"""
Stock Prediction Tool with x402 Payment Protection
Implements HTTP 402 Payment Required pattern
"""

import logging
from typing import Optional

try:
    from server.config import PRICE_PREDICTION_USD, ONRAMP_URL
    from server.services import verify_payment, settle_payment, build_payment_requirements, call_prediction
except ImportError:
    from demo_mcp.server.config import PRICE_PREDICTION_USD, ONRAMP_URL
    from demo_mcp.server.services import verify_payment, settle_payment, build_payment_requirements, call_prediction

logger = logging.getLogger(__name__)


async def run_prediction(
    symbol: str,
    horizon: int = 30,
    payment_payload: Optional[dict] = None
) -> dict:
    """
    Run stock prediction with x402 payment protection.

    Flow:
    1. If no payment_payload → Return 402 with payment_requirements
    2. If payment_payload exists → Verify with x402 facilitator
    3. If valid → Settle payment on-chain
    4. If settled → Call CreditNexus backend
    5. Return prediction result + payment receipt

    Args:
        symbol: Stock symbol (e.g., "AAPL", "TSLA")
        horizon: Prediction horizon in days (default: 30)
        payment_payload: x402 v2 PaymentPayload (optional)

    Returns:
        402 response with payment_requirements OR
        Prediction result with payment_receipt
    """

    if not payment_payload:
        logger.info("Prediction request without payment: symbol=%s, horizon=%s", symbol, horizon)
        requirements = build_payment_requirements(
            amount_usd=PRICE_PREDICTION_USD,
            resource=f"/mcp/prediction/{symbol}",
            description=f"Stock prediction for {symbol} ({horizon} days)"
        )

        return {
            "status": 402,
            "message": "Payment Required",
            "paymentRequirements": requirements,
            "resource": {
                "url": f"/mcp/prediction/{symbol}",
                "description": f"Stock prediction for {symbol}",
                "mimeType": "application/json"
            },
            "onrampUrl": ONRAMP_URL
        }

    logger.info("Processing paid prediction: symbol=%s, horizon=%s", symbol, horizon)

    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_PREDICTION_USD,
        resource=f"/mcp/prediction/{symbol}",
        description=f"Stock prediction for {symbol} ({horizon} days)"
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
        prediction = await call_prediction(symbol, horizon)
        logger.info("Prediction completed for %s", symbol)
    except Exception as e:
        logger.error("Backend prediction failed: %s", str(e))
        return {
            "status": 500,
            "error": "Backend service failed",
            "reason": str(e),
            "payer": verification.get("payer"),
            "paymentReceipt": {
                "transaction": settlement.get("transaction"),
                "network": settlement.get("network"),
                "payer": verification.get("payer"),
                "amount": PRICE_PREDICTION_USD,
                "settled": True
            },
            "note": "Payment was processed. Please contact support for refund."
        }

    return {
        "status": 200,
        "result": prediction,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": verification.get("payer"),
            "amount": PRICE_PREDICTION_USD,
            "resource": f"/mcp/prediction/{symbol}",
            "settled": True
        }
    }


def register_tools(mcp):
    """Register prediction tools with FastMCP server"""
    mcp.tool()(run_prediction)
