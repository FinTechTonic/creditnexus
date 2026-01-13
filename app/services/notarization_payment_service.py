"""Notarization payment service for x402 integration."""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.x402_payment_service import X402PaymentService
from app.models.cdm import Party, Money, Currency
from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
from app.db.models import NotarizationRecord, User, PaymentEvent as PaymentEventModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotarizationPaymentService:
    """Service for handling notarization payments via x402."""
    
    def __init__(self, db: Session, payment_service: Optional[X402PaymentService] = None):
        self.db = db
        self.payment_service = payment_service
    
    def get_notarization_fee(self) -> Money:
        """Get configured notarization fee."""
        return Money(
            amount=settings.NOTARIZATION_FEE_AMOUNT,
            currency=settings.NOTARIZATION_FEE_CURRENCY
        )
    
    def can_skip_payment(self, user: User) -> bool:
        """Check if user can skip payment (admin only)."""
        if not settings.NOTARIZATION_FEE_ADMIN_SKIP:
            return False
        return user.role == "admin"
    
    async def request_notarization_payment(
        self,
        notarization: NotarizationRecord,
        payer: Party,
        receiver: Party,
        payment_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request payment for notarization.
        
        Returns 402 Payment Required if payment_payload not provided.
        """
        if not self.payment_service:
            raise ValueError("x402 payment service not available")
        
        fee = self.get_notarization_fee()
        
        return await self.payment_service.process_payment_flow(
            amount=fee.amount,
            currency=fee.currency,
            payer=payer,
            receiver=receiver,
            payment_type="notarization_fee",
            payment_payload=payment_payload,
            cdm_reference={
                "notarization_id": str(notarization.id),
                "deal_id": str(notarization.deal_id),
                "event_type": "Notarization"
            }
        )
