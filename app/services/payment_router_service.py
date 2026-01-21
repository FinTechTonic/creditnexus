"""
Payment router: routes by PaymentType to x402 and optionally RevenueCat.

Supports: LOAN_DISBURSEMENT, TRADE_SETTLEMENT, INTEREST_PAYMENT, PENALTY_PAYMENT,
PRINCIPAL_REPAYMENT, NOTARIZATION_FEE, POLYMARKET_TRADE, MARKET_CREATION_FEE,
SUBSCRIPTION_UPGRADE. All are sent to x402. For SUBSCRIPTION_UPGRADE, can
optionally grant a RevenueCat promotional entitlement after successful x402 settle.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from app.models.cdm import Currency, Party
from app.models.cdm_payment import PaymentType

logger = logging.getLogger(__name__)


class PaymentRouterService:
    """Routes payments to x402; optionally integrates RevenueCat for subscriptions."""

    def __init__(
        self,
        x402_service: Optional[Any] = None,
        revenuecat_service: Optional[Any] = None,
    ) -> None:
        self.x402 = x402_service
        self.revenuecat = revenuecat_service

    def _ensure_x402(self) -> Any:
        if not self.x402:
            raise ValueError("x402 payment service not available")
        return self.x402

    async def route_payment(
        self,
        amount: Decimal,
        currency: Currency,
        payer: Party,
        receiver: Party,
        payment_type: PaymentType,
        *,
        payment_payload: Optional[Dict[str, Any]] = None,
        cdm_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Route a payment by type to x402 (request → verify → settle).
        PaymentType.POLYMARKET_TRADE, MARKET_CREATION_FEE, SUBSCRIPTION_UPGRADE
        use the same x402 flow as NOTARIZATION_FEE.
        """
        self._ensure_x402()
        pt = payment_type.value if isinstance(payment_type, PaymentType) else str(payment_type)
        return await self.x402.process_payment_flow(
            amount=amount,
            currency=currency,
            payer=payer,
            receiver=receiver,
            payment_type=pt,
            payment_payload=payment_payload,
            cdm_reference=cdm_reference,
        )

    def after_subscription_payment(
        self,
        app_user_id: str,
        payment_result: Dict[str, Any],
        entitlement_id: Optional[str] = None,
        duration: str = "P1M",
    ) -> Dict[str, Any]:
        """
        After a successful x402 SUBSCRIPTION_UPGRADE, optionally grant
        a RevenueCat promotional entitlement. No-op if RevenueCat disabled.
        """
        if not self.revenuecat or not getattr(self.revenuecat, "enabled", False):
            return {"success": False, "reason": "revenuecat_disabled"}

        st = payment_result.get("status") or ""
        if st != "settled":
            return {"success": False, "reason": "payment_not_settled", "status": st}

        return self.revenuecat.grant_promotional_entitlement(
            app_user_id=app_user_id,
            entitlement_id=entitlement_id,
            duration=duration,
        )

    def has_subscription_access(
        self,
        app_user_id: str,
        entitlement_id: Optional[str] = None,
    ) -> bool:
        """
        Check if user has an active RevenueCat entitlement (e.g. pro for Polymarket).
        Returns False if RevenueCat disabled or not configured.
        """
        if not self.revenuecat or not getattr(self.revenuecat, "enabled", False):
            return False
        return self.revenuecat.has_entitlement(
            app_user_id=app_user_id,
            entitlement_id=entitlement_id,
        )
