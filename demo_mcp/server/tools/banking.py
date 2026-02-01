"""
Banking Tool (Plaid Link) with x402 Payment Protection
Implements HTTP 402 Payment Required pattern with EVM payments
"""

import logging
from typing import Optional

from demo_mcp.server.config import PRICE_BANKING_USD, ONRAMP_URL
from demo_mcp.server.services import verify_payment, settle_payment, build_payment_requirements, create_plaid_link_token

logger = logging.getLogger(__name__)


async def open_bank_account(
    user_id: Optional[str] = None,
    payment_payload: Optional[dict] = None
) -> dict:
    """
    Open bank account (Plaid Link) with x402 payment protection.
    Uses EVM (Base Sepolia) for payment instead of Aptos.

    Flow:
    1. If no payment_payload → Return 402 with payment_requirements (EVM)
    2. If payment_payload exists → Verify with x402 facilitator
    3. If valid → Settle payment on-chain (Base Sepolia)
    4. If settled → Call CreditNexus Plaid link creation
    5. Return link_token + payment receipt

    Args:
        user_id: Optional user ID for Plaid link
        payment_payload: x402 v2 PaymentPayload (optional)

    Returns:
        402 response with payment_requirements OR
        Plaid link token with payment_receipt
    """

    if not payment_payload:
        logger.info("Banking request without payment: user_id=%s", user_id)
        requirements = build_payment_requirements(
            amount_usd=PRICE_BANKING_USD,
            resource="/mcp/banking/open-account",
            description="Open bank account via Plaid Link",
            network="evm"
        )

        return {
            "status": 402,
            "message": "Payment Required",
            "paymentRequirements": requirements,
            "resource": {
                "url": "/mcp/banking/open-account",
                "description": "Plaid Link token for bank account connection",
                "mimeType": "application/json"
            },
            "onrampUrl": ONRAMP_URL
        }

    logger.info("Processing paid banking request: user_id=%s", user_id)

    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_BANKING_USD,
        resource="/mcp/banking/open-account",
        description="Open bank account via Plaid Link",
        network="evm"
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
        plaid_response = await create_plaid_link_token(user_id)
        logger.info("Plaid link token created for user: %s", user_id)
    except Exception as e:
        logger.error("Backend Plaid link creation failed: %s", str(e))
        return {
            "status": 500,
            "error": "Backend service failed",
            "reason": str(e),
            "payer": verification.get("payer"),
            "paymentReceipt": {
                "transaction": settlement.get("transaction"),
                "network": settlement.get("network"),
                "payer": verification.get("payer"),
                "amount": PRICE_BANKING_USD,
                "settled": True
            },
            "note": "Payment was processed. Please contact support for refund."
        }

    return {
        "status": 200,
        "result": plaid_response,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": verification.get("payer"),
            "amount": PRICE_BANKING_USD,
            "resource": "/mcp/banking/open-account",
            "settled": True
        }
    }


def register_tools(mcp):
    """Register banking tools with FastMCP server"""
    mcp.tool()(open_bank_account)
