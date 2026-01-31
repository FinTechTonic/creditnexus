"""
Unified funding: request_funding (payment router / 402) and after_funding_settled (credits, Alpaca, Polymarket).

- request_funding: Build payer/receiver; call PaymentRouterService.route_payment with PaymentType (ALPACA_FUNDING, POLYMARKET_FUNDING, CREDIT_TOP_UP); return 402 payload or success.
- after_funding_settled: For CREDIT_TOP_UP call RollingCreditsService.add_credits; optionally blockchain sync. For ALPACA_FUNDING document ACH-from-linked-bank only. For POLYMARKET_FUNDING optional relayer USDC to proxy.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import User, AuditAction
from app.models.cdm import Currency, Party
from app.models.cdm_payment import PaymentType
from app.services.rolling_credits_service import RollingCreditsService
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)


async def request_funding(
    db: Session,
    user_id: int,
    amount: Decimal,
    payment_type: str,
    destination_identifier: Optional[str] = None,
    payment_router: Optional[Any] = None,
    payment_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Request funding: route payment by type (alpaca_funding, polymarket_funding, credit_top_up).
    Build payer from user; receiver from config. Call payment_router.route_payment; return result (402 payload or settled).
    Caller must inject payment_router (from request.app.state or get_payment_router).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "user_not_found"}
    if not payment_router:
        return {"error": "payment_router_not_available"}
    try:
        pt = PaymentType(payment_type)
    except ValueError:
        return {"error": f"invalid_payment_type: {payment_type}"}
    if pt not in (PaymentType.ALPACA_FUNDING, PaymentType.POLYMARKET_FUNDING, PaymentType.CREDIT_TOP_UP):
        return {"error": f"funding_type_not_supported: {payment_type}"}

    payer = Party(
        id=str(user_id),
        name=getattr(user, "display_name", None) or getattr(user, "email", "User") or "User",
        role="Payer",
        lei=None,
    )
    receiver_id = f"creditnexus_funding_{payment_type}"
    receiver_name = {
        PaymentType.ALPACA_FUNDING.value: "CreditNexus Alpaca Funding",
        PaymentType.POLYMARKET_FUNDING.value: "CreditNexus Polymarket Funding",
        PaymentType.CREDIT_TOP_UP.value: "CreditNexus Credit Top-Up",
    }.get(payment_type, "CreditNexus Funding")
    receiver = Party(id=receiver_id, name=receiver_name, role="Receiver", lei=None)

    try:
        result = await payment_router.route_payment(
            amount=amount,
            currency=Currency.USD,
            payer=payer,
            receiver=receiver,
            payment_type=pt,
            payment_payload=payment_payload,
            cdm_reference={
                "user_id": user_id,
                "type": payment_type,
                "destination_id": destination_identifier,
            },
        )
    except Exception as e:
        logger.warning("Unified funding route_payment failed: %s", e)
        return {"error": str(e)}

    return result


def after_funding_settled(
    db: Session,
    user_id: int,
    payment_type: str,
    payment_result: Dict[str, Any],
    destination_identifier: Optional[str] = None,
    amount: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    After payment settled: for CREDIT_TOP_UP add credits (+ optional on-chain); for ALPACA_FUNDING no-op (ACH from linked bank only); for POLYMARKET_FUNDING optional relayer USDC.
    """
    status = payment_result.get("status") or ""
    if status != "settled":
        return {"ok": False, "reason": "payment_not_settled", "status": status}

    try:
        pt = PaymentType(payment_type)
    except ValueError:
        return {"ok": False, "reason": f"invalid_payment_type: {payment_type}"}

    if pt == PaymentType.CREDIT_TOP_UP:
        amt_usd = float(amount) if amount is not None else float(payment_result.get("amount", 0))
        if amt_usd <= 0:
            return {"ok": False, "reason": "invalid_amount"}
        # Credits = pennies: 1 USD adds CREDITS_PENNIES_PER_USD credits (default 100)
        from app.core.config import settings
        pennies_per_usd = int(getattr(settings, "CREDITS_PENNIES_PER_USD", 100))
        credits_to_add = amt_usd * pennies_per_usd
        credits_service = RollingCreditsService(db)
        out = credits_service.add_credits(
            user_id=user_id,
            credit_type="universal",
            amount=credits_to_add,
            feature="credit_top_up",
            description="Credit top-up (pennies)",
        )
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="credit_top_up",
            target_id=None,
            user_id=user_id,
            metadata={"amount_usd": amt_usd, "credits_pennies": credits_to_add, "payment_type": payment_type},
        )
        return {"ok": out.get("ok", True), "balance_after": out.get("balance_after")}

    if pt == PaymentType.ALPACA_FUNDING:
        # Alpaca funding is ACH-from-linked-bank only in this plan; no x402→transfer.
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="alpaca_funding_request",
            target_id=None,
            user_id=user_id,
            metadata={"payment_type": payment_type, "destination_id": destination_identifier},
        )
        return {"ok": True, "note": "Alpaca funding via ACH from linked bank"}

    if pt == PaymentType.POLYMARKET_FUNDING:
        # Optional: trigger relayer USDC to user's Polymarket proxy (destination_identifier = proxy address).
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="polymarket_funding_request",
            target_id=None,
            user_id=user_id,
            metadata={"payment_type": payment_type, "destination_id": destination_identifier},
        )
        return {"ok": True, "note": "Polymarket funding; relayer USDC optional"}

    return {"ok": False, "reason": "unsupported_type"}
