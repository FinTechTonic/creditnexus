"""
Stock Prediction Tool with x402 Payment Protection
Implements HTTP 402 Payment Required pattern
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Import payment wrapper and backend client
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from payment import verify_payment, settle_payment, build_payment_requirements
from backend import call_prediction

# Pricing
PRICE_USD = float(os.getenv("MCP_PRICE_PREDICTION_USD", "0.06"))


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

    # Step 1: Check if payment exists
    if not payment_payload:
        # Return 402 Payment Required
        requirements = build_payment_requirements(
            amount_usd=PRICE_USD,
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
            "onrampUrl": os.getenv("ONRAMP_URL", "https://faucet.circle.com")
        }

    # Step 2: Build payment requirements (what we expect)
    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_USD,
        resource=f"/mcp/prediction/{symbol}",
        description=f"Stock prediction for {symbol} ({horizon} days)"
    )

    # Step 3: Verify payment with x402 facilitator (via our wrapper)
    verification = await verify_payment(payment_payload, payment_requirements)

    if not verification.get("isValid"):
        return {
            "status": 403,
            "error": "Payment verification failed",
            "reason": verification.get("invalidReason"),
            "payer": verification.get("payer")
        }

    # Step 4: Settle payment on-chain
    settlement = await settle_payment(payment_payload, payment_requirements, verification)

    if not settlement.get("success"):
        return {
            "status": 500,
            "error": "Payment settlement failed",
            "reason": settlement.get("errorReason"),
            "payer": verification.get("payer")
        }

    # Step 5: Call CreditNexus backend for actual prediction
    try:
        prediction = await call_prediction(symbol, horizon)
    except Exception as e:
        # Payment was settled, but backend failed
        # User paid, so we should log this and potentially refund
        return {
            "status": 500,
            "error": "Backend service failed",
            "reason": str(e),
            "payer": verification.get("payer"),
            "paymentReceipt": {
                "transaction": settlement.get("transaction"),
                "network": settlement.get("network"),
                "payer": verification.get("payer"),
                "amount": PRICE_USD,
                "settled": True
            },
            "note": "Payment was processed. Please contact support for refund."
        }

    # Step 6: Return result with payment receipt
    return {
        "status": 200,
        "result": prediction,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": verification.get("payer"),
            "amount": PRICE_USD,
            "resource": f"/mcp/prediction/{symbol}",
            "settled": True
        }
    }


def register_tools(mcp):
    """Register prediction tools with FastMCP server"""
    mcp.tool()(run_prediction)
