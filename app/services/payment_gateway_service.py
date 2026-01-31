"""
Payment gateway service.

Goal: provide a single place to:
- check / spend rolling credits
- if insufficient: return an x402-style 402 payload (payment instructions)

This is intentionally minimal in Week 2; settlement + credit top-ups are handled later.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.models.cdm import Currency, Party
from app.models.cdm_payment import PaymentType
from app.services.rolling_credits_service import RollingCreditsService
from app.services.x402_payment_service import X402PaymentService
from app.services.revenuecat_service import RevenueCatService

logger = logging.getLogger(__name__)


def billable_402_response(gate: Dict[str, Any]):
    """
    Return the same 402 JSONResponse for every billable-feature route.
    Use when require_credits_or_402 returns ok=False and status_code=402.
    Ensures identical response shape (payment_type, payment_request, etc.) across all services.
    """
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=402, content={**gate, "payment_type": "billable_feature"})


class PaymentGatewayService:
    def __init__(self, db: Session):
        self.db = db

    def _get_user(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    async def require_credits_or_402(
        self,
        *,
        user_id: int,
        credit_type: str,
        amount: float,
        feature: str,
        payment_type: PaymentType = PaymentType.NOTARIZATION_FEE,
        cost_usd: Decimal = Decimal("0.00"),
        currency: Currency = Currency.USD,
        cdm_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Try to spend rolling credits. If insufficient, return x402 402 payload.

        Returns:
          - { "ok": True } when credits were spent
          - { "ok": False, "status_code": 402, ... } when payment required
        """
        user = self._get_user(user_id)
        if not user:
            return {"ok": False, "status_code": 404, "detail": "user_not_found"}

        # Spend credits (tries credit_type then universal inside RollingCreditsService)
        spend = RollingCreditsService(self.db).spend_credits(
            user_id=user_id,
            credit_type=credit_type,
            amount=amount,
            feature=feature,
            description=f"{feature}:{credit_type}",
        )
        if spend.get("ok"):
            # Important: spend_credits mutates balance + inserts tx; commit/flush is handled elsewhere in flow.
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
            return {"ok": True, "spent": {"credit_type": credit_type, "amount": amount, "feature": feature}}

        if spend.get("reason") != "insufficient_credits":
            return {"ok": False, "status_code": 400, "detail": spend.get("reason", "credit_spend_failed")}

        # Payment required (x402)
        if not getattr(settings, "X402_ENABLED", True):
            return {"ok": False, "status_code": 402, "detail": "payment_required", "message": "Insufficient credits"}

        x402 = X402PaymentService(
            facilitator_url=settings.X402_FACILITATOR_URL,
            network=settings.X402_NETWORK,
            token=settings.X402_TOKEN,
        )

        payer = Party(id=str(user.id), name="user", lei=None)  # do not include PII
        receiver = Party(id="creditnexus", name="CreditNexus", lei=None)

        payment_request = await x402.request_payment(
            amount=cost_usd,
            currency=currency,
            payer=payer,
            receiver=receiver,
            payment_type=payment_type.value if hasattr(payment_type, "value") else str(payment_type),
            cdm_reference=cdm_reference,
        )
        # Check if RevenueCat is available for this payment type (subscription or billable pay-as-you-go)
        revenuecat_available = False
        revenuecat_service = RevenueCatService()
        if payment_type in (PaymentType.SUBSCRIPTION_UPGRADE, PaymentType.BILLABLE_FEATURE) and revenuecat_service.enabled:
            revenuecat_available = True
        
        # Normalize for API layer
        response = {
            "ok": False,
            "status_code": 402,
            "detail": "payment_required",
            "message": "Insufficient credits; payment required",
            "payment_request": payment_request.get("payment_request"),
            "facilitator_url": payment_request.get("facilitator_url"),
            "cost": {"usd": str(cost_usd), "credits": str(amount), "credit_type": credit_type},
            "payment_type": payment_type.value if hasattr(payment_type, "value") else str(payment_type),
        }
        
        # Add RevenueCat availability if applicable
        if revenuecat_available:
            response["revenuecat_available"] = True
            response["revenuecat_endpoint"] = "/api/subscriptions/revenuecat/purchase"
        
        return response

