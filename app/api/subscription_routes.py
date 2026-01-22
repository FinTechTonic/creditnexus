"""
Subscription and entitlement routes: RevenueCat + x402.

- GET /entitlement: check if current user has Pro (or specified) entitlement.
- POST /upgrade: run SUBSCRIPTION_UPGRADE via PaymentRouter (x402); on success
  optionally grant RevenueCat promotional entitlement.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.jwt_auth import get_current_user
from app.core.config import settings
from app.db.models import User
from app.models.cdm import Currency, Party

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


def get_payment_router(request: Request):
    return getattr(request.app.state, "payment_router_service", None)


class UpgradeRequest(BaseModel):
    """Request body for subscription upgrade (x402 + optional RevenueCat grant)."""
    payment_payload: Optional[Dict[str, Any]] = Field(
        None,
        description="x402 payment payload from wallet; if omitted, response is 402 with payment_request",
    )


@router.get("/entitlement")
async def get_entitlement(
    request: Request,
    entitlement_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Check if the current user has the given (or default Pro) RevenueCat entitlement.
    Returns { "has_pro": bool } (or has_<entitlement_id> when entitlement_id is set).
    """
    pr = get_payment_router(request)
    if not pr:
        return {"has_pro": False, "reason": "payment_router_unavailable"}

    app_user_id = str(current_user.id)
    ent = entitlement_id or getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")
    has = pr.has_subscription_access(app_user_id=app_user_id, entitlement_id=ent)
    key = f"has_{ent}" if entitlement_id else "has_pro"
    return {key: has}


@router.post("/upgrade")
async def post_upgrade(
    body: UpgradeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Process a subscription upgrade: x402 payment (SUBSCRIPTION_UPGRADE) then
    optionally grant RevenueCat Pro entitlement. If payment_payload is omitted,
    returns 402 with payment_request for the client to complete via x402.
    """
    pr = get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    amount = getattr(settings, "SUBSCRIPTION_UPGRADE_AMOUNT", Decimal("9.99"))
    payer = Party(
        id=str(current_user.id),
        name=current_user.display_name or current_user.email or "User",
        role="Payer",
        lei=None,
    )
    receiver = Party(
        id="creditnexus_subscriptions",
        name="CreditNexus Subscriptions",
        role="Receiver",
        lei=None,
    )

    from app.models.cdm_payment import PaymentType

    try:
        result = await pr.route_payment(
            amount=amount,
            currency=Currency.USD,
            payer=payer,
            receiver=receiver,
            payment_type=PaymentType.SUBSCRIPTION_UPGRADE,
            payment_payload=body.payment_payload,
            cdm_reference={"user_id": current_user.id, "type": "subscription_upgrade"},
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail="x402 payment service not available")

    # If no payload was provided, x402 returns 402-like structure
    if result.get("status_code") == 402 or (not body.payment_payload and result.get("status") != "settled"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=402,
            content={
                "status": "Payment Required",
                "payment_request": result.get("payment_request"),
                "amount": str(amount),
                "currency": "USD",
                "facilitator_url": getattr(pr.x402, "facilitator_url", None) if pr.x402 else None,
            },
        )

    if result.get("status") != "settled":
        raise HTTPException(
            status_code=400,
            detail=result.get("verification") or result.get("status") or "Payment could not be completed",
        )

    # Optionally grant RevenueCat entitlement
    grant = pr.after_subscription_payment(
        app_user_id=str(current_user.id),
        payment_result=result,
        entitlement_id=getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro"),
        duration="P1M",
    )

    return {
        "status": "settled",
        "payment_id": result.get("payment_id"),
        "transaction_hash": result.get("transaction_hash"),
        "revenuecat_grant": grant,
    }
