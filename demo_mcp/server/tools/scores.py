"""
Agent reputation and borrower score tools with x402 payment protection.
Reputation services and third parties pay a small fee to query an agent's score;
the server returns 200 with score (100 for whitelisted, 100+ Plaid-derived when linked) or 403 if not allowlisted.
"""

import logging
from typing import Optional

from demo_mcp.server.config import PRICE_SCORE_USD, ONRAMP_URL  # noqa: I100
from demo_mcp.server.services import (
    verify_payment,
    settle_payment,
    build_payment_requirements,
    check_allowlist,
)
from demo_mcp.server.services import get_borrower_score_for_agent

logger = logging.getLogger(__name__)


async def get_agent_reputation_score(
    agent_address: Optional[str] = None,
    payment_payload: Optional[dict] = None,
) -> dict:
    """
    Get agentic reputation score for an allowlisted agent (x402 protected).
    Reputation services query this endpoint; payment required. Returns 200 with score or 403.

    Base reputation score: 100 (from KYC/whitelist). Compliant way for third parties to gate
    access on agent reputation (e.g. 200 with score vs 403).

    Flow:
    1. No payment_payload → 402 with payment_requirements
    2. Payment invalid or payer not allowlisted → 403
    3. Valid payment + allowlisted → Settle, return 200 with reputation_score: 100
    """
    if not payment_payload:
        requirements = build_payment_requirements(
            amount_usd=PRICE_SCORE_USD,
            resource="/mcp/scores/reputation",
            description="Query agent reputation score (allowlisted agents)",
            network="aptos",
        )
        return {
            "status": 402,
            "message": "Payment Required",
            "paymentRequirements": requirements,
            "resource": {
                "url": "/mcp/scores/reputation",
                "description": "Agent reputation score (100 for whitelisted/KYC)",
                "mimeType": "application/json",
            },
            "onrampUrl": ONRAMP_URL,
        }

    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_SCORE_USD,
        resource="/mcp/scores/reputation",
        description="Query agent reputation score",
        network="aptos",
    )
    verification = await verify_payment(payment_payload, payment_requirements)
    if not verification.get("isValid"):
        return {
            "status": 403,
            "error": "Payment verification failed",
            "reason": verification.get("invalidReason"),
            "payer": verification.get("payer"),
        }

    payer = verification.get("payer") or agent_address
    is_allowed, reason = check_allowlist(payer, is_agent=True)
    if not is_allowed:
        return {
            "status": 403,
            "error": "Not allowlisted",
            "reason": reason or "Agent not on allowlist",
            "payer": payer,
        }

    settlement = await settle_payment(payment_payload, payment_requirements, verification)
    if not settlement.get("success"):
        return {
            "status": 500,
            "error": "Settlement failed",
            "reason": settlement.get("errorReason"),
            "payer": payer,
        }

    return {
        "status": 200,
        "reputation_score": 100,
        "message": "Base reputation 100 (KYC/whitelist). Use get_borrower_score for linked-account score.",
        "payer": payer,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": payer,
            "amount": PRICE_SCORE_USD,
            "resource": "/mcp/scores/reputation",
            "settled": True,
        },
    }


async def get_borrower_score(
    agent_address: Optional[str] = None,
    payment_payload: Optional[dict] = None,
) -> dict:
    """
    Get borrower score for an allowlisted agent (x402 protected).
    Returns 200 with score string: "100" for allowlisted only, "100+{plaid_score}" when agent has linked bank (Plaid).
    Reputation services can query this endpoint; 403 if not allowlisted or payment invalid.

    Flow:
    1. No payment_payload → 402
    2. Invalid or not allowlisted → 403
    3. Valid + allowlisted → Settle, fetch score (100 or 100+plaid from backend if available), return 200 with score.
    """
    if not payment_payload:
        requirements = build_payment_requirements(
            amount_usd=PRICE_SCORE_USD,
            resource="/mcp/scores/borrower",
            description="Query borrower score (allowlisted; 100+ Plaid when linked)",
            network="aptos",
        )
        return {
            "status": 402,
            "message": "Payment Required",
            "paymentRequirements": requirements,
            "resource": {
                "url": "/mcp/scores/borrower",
                "description": "Borrower score: 100 (base) or 100+Plaid when bank linked",
                "mimeType": "application/json",
            },
            "onrampUrl": ONRAMP_URL,
        }

    payment_requirements = build_payment_requirements(
        amount_usd=PRICE_SCORE_USD,
        resource="/mcp/scores/borrower",
        description="Query borrower score",
        network="aptos",
    )
    verification = await verify_payment(payment_payload, payment_requirements)
    if not verification.get("isValid"):
        return {
            "status": 403,
            "error": "Payment verification failed",
            "reason": verification.get("invalidReason"),
            "payer": verification.get("payer"),
        }

    payer = verification.get("payer") or agent_address
    is_allowed, reason = check_allowlist(payer, is_agent=True)
    if not is_allowed:
        return {
            "status": 403,
            "error": "Not allowlisted",
            "reason": reason or "Agent not on allowlist",
            "payer": payer,
        }

    settlement = await settle_payment(payment_payload, payment_requirements, verification)
    if not settlement.get("success"):
        return {
            "status": 500,
            "error": "Settlement failed",
            "reason": settlement.get("errorReason"),
            "payer": payer,
        }

    # Base score 100 for allowlisted; add Plaid-derived score when linked account exists (backend)
    plaid_component = await get_borrower_score_for_agent(payer)
    if plaid_component is not None:
        try:
            val = int(plaid_component) if isinstance(plaid_component, (int, float)) else None
            score_str = f"100+{val}" if val is not None else "100"
        except (TypeError, ValueError):
            score_str = "100"
    else:
        score_str = "100"

    return {
        "status": 200,
        "score": score_str,
        "payer": payer,
        "paymentReceipt": {
            "transaction": settlement.get("transaction"),
            "network": settlement.get("network"),
            "payer": payer,
            "amount": PRICE_SCORE_USD,
            "resource": "/mcp/scores/borrower",
            "settled": True,
        },
    }


def register_tools(mcp):
    """Register score tools with FastMCP server."""
    mcp.tool()(get_agent_reputation_score)
    mcp.tool()(get_borrower_score)
