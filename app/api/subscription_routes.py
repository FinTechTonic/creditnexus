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
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.config import settings
from app.db import get_db
from app.db.models import User
from app.services.subscription_service import SubscriptionService
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
        from app.services.revenuecat_service import RevenueCatService
        
        # Check if RevenueCat is available
        revenuecat = RevenueCatService()
        revenuecat_available = revenuecat.enabled
        
        response_content = {
            "status": "Payment Required",
            "payment_request": result.get("payment_request"),
            "amount": str(amount),
            "currency": "USD",
            "payment_type": "subscription_upgrade",
            "facilitator_url": getattr(pr.x402, "facilitator_url", None) if pr.x402 else None,
        }
        
        if revenuecat_available:
            response_content["revenuecat_available"] = True
            response_content["revenuecat_endpoint"] = "/api/subscriptions/revenuecat/purchase"
        
        return JSONResponse(status_code=402, content=response_content)

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


@router.post("/org-admin/upgrade")
async def post_org_admin_upgrade(
    body: UpgradeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Organization-admin signup payment ($2): x402 payment flow.
    If payment_payload is omitted, returns 402 with payment_request for the client to complete via x402.
    """
    pr = get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    amount = getattr(settings, "ORG_ADMIN_SIGNUP_AMOUNT", Decimal("2.00"))
    payer = Party(
        id=str(current_user.id),
        name=current_user.display_name or current_user.email or "User",
        role="Payer",
        lei=None,
    )
    receiver = Party(
        id="creditnexus_org_admin_signup",
        name="CreditNexus Org Admin Signup",
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
            cdm_reference={"user_id": current_user.id, "type": "org_admin_signup"},
        )
    except ValueError:
        raise HTTPException(status_code=503, detail="x402 payment service not available")

    if result.get("status_code") == 402 or (not body.payment_payload and result.get("status") != "settled"):
        from fastapi.responses import JSONResponse
        from app.services.revenuecat_service import RevenueCatService
        
        # Check if RevenueCat is available
        revenuecat = RevenueCatService()
        revenuecat_available = revenuecat.enabled
        
        response_content = {
            "status": "Payment Required",
            "payment_request": result.get("payment_request"),
            "amount": str(amount),
            "currency": "USD",
            "payment_type": "org_admin_upgrade",
            "facilitator_url": getattr(pr.x402, "facilitator_url", None) if pr.x402 else None,
        }
        
        if revenuecat_available:
            response_content["revenuecat_available"] = True
            response_content["revenuecat_endpoint"] = "/api/subscriptions/revenuecat/purchase"
        
        return JSONResponse(status_code=402, content=response_content)

    if result.get("status") != "settled":
        raise HTTPException(
            status_code=400,
            detail=result.get("verification") or result.get("status") or "Payment could not be completed",
        )

    return {
        "status": "settled",
        "payment_id": result.get("payment_id"),
        "transaction_hash": result.get("transaction_hash"),
    }


class RevenueCatPurchaseRequest(BaseModel):
    """Request body for RevenueCat purchase."""
    product_id: str = Field(..., description="Product ID (e.g., 'subscription_upgrade', 'org_admin')")
    transaction_id: Optional[str] = Field(None, description="RevenueCat transaction ID (if available)")
    purchase_token: Optional[str] = Field(None, description="Purchase token from RevenueCat SDK")
    amount: Optional[str] = Field(None, description="Purchase amount (for verification)")


@router.post("/revenuecat/purchase")
async def post_revenuecat_purchase(
    body: RevenueCatPurchaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a RevenueCat purchase and grant entitlement.
    
    This endpoint accepts purchase data from RevenueCat SDK and grants the appropriate
    entitlement. For subscription upgrades and org-admin payments.
    """
    from app.services.revenuecat_service import RevenueCatService
    
    revenuecat = RevenueCatService()
    if not revenuecat.enabled:
        raise HTTPException(status_code=503, detail="RevenueCat is not enabled")
    
    app_user_id = str(current_user.id)

    # Buy credits only (no entitlement): product_id = credit_top_up_<pennies> e.g. credit_top_up_500
    if body.product_id.startswith("credit_top_up_"):
        try:
            pennies = int(body.product_id.replace("credit_top_up_", "").strip())
        except ValueError:
            pennies = 0
        if pennies <= 0:
            raise HTTPException(status_code=400, detail="Invalid credit_top_up product_id; use credit_top_up_<pennies> e.g. credit_top_up_500")
        from app.services.rolling_credits_service import RollingCreditsService
        credits_service = RollingCreditsService(db)
        credits_service.add_credits(
            user_id=current_user.id,
            credit_type="universal",
            amount=float(pennies),
            feature="revenuecat_credit_top_up",
            description="Credit top-up (RevenueCat)",
        )
        db.commit()
        return {
            "status": "completed",
            "entitlement_granted": None,
            "credits_added": pennies,
            "revenuecat_result": {"success": True},
        }

    # Determine entitlement based on product_id (subscribe products)
    entitlement_id = None
    duration = "P1M"

    if body.product_id == "org_admin":
        entitlement_id = getattr(settings, "REVENUECAT_ENTITLEMENT_ORG_ADMIN", None) or getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")
        duration = "P1Y"  # Org admin gets 1 year
    elif body.product_id == "subscription_upgrade":
        entitlement_id = getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")
        duration = "P1M"  # Monthly subscription
    elif body.product_id == "mobile_app":
        entitlement_id = getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")
        duration = "P1Y"  # Mobile app purchase: 1-year entitlement + instant credits
    else:
        entitlement_id = getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")
        duration = "P1M"

    # Grant promotional entitlement (subscribe products)
    grant_result = revenuecat.grant_promotional_entitlement(
        app_user_id=app_user_id,
        entitlement_id=entitlement_id,
        duration=duration,
    )

    if not grant_result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Failed to grant entitlement: {grant_result.get('reason', 'unknown')}",
        )

    # Allocate credits after successful subscribe purchase
    from app.services.subscription_service import SubscriptionService

    try:
        subscription_service = SubscriptionService(db)

        
        # For org-admin, mark as paid and ensure user has an organisation
        if body.product_id == "org_admin":
            subscription_service.mark_org_admin_paid(
                user_id=current_user.id,
                payment_id=None,
            )
            subscription_service.ensure_org_for_paying_user(current_user.id)

        from app.services.rolling_credits_service import RollingCreditsService
        credits_service = RollingCreditsService(db)

        if body.product_id == "org_admin":
            credits_service.add_credits(
                user_id=current_user.id,
                credit_type="universal",
                amount=float(getattr(settings, "ORG_ADMIN_SIGNUP_CREDITS", 200)),
                feature="org_admin_signup",
                description="Org admin signup credits",
            )
        elif body.product_id == "subscription_upgrade":
            credits_service.add_credits(
                user_id=current_user.id,
                credit_type="universal",
                amount=float(getattr(settings, "SUBSCRIPTION_UPGRADE_CREDITS", 200)),
                feature="subscription_upgrade",
                description="Subscription upgrade credits",
            )
        elif body.product_id == "mobile_app":
            credits_service.add_credits(
                user_id=current_user.id,
                credit_type="universal",
                amount=float(getattr(settings, "MOBILE_APP_PURCHASE_CREDITS", 360)),
                feature="mobile_app_purchase",
                description="Mobile app purchase credits",
            )

        db.commit()
    except Exception as e:
        logger.error(f"Failed to allocate credits after RevenueCat purchase: {e}", exc_info=True)
        db.rollback()

    return {
        "status": "completed",
        "entitlement_granted": entitlement_id,
        "duration": duration,
        "revenuecat_result": grant_result,
    }
