"""Service for calculating and applying commissions."""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import CommissionConfig, CommissionCharge

logger = logging.getLogger(__name__)


class CommissionService:
    """Service for calculating and applying commissions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_commission(
        self,
        transaction_type: str,
        transaction_amount: Decimal,
        transaction_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate commission for a transaction."""
        # Find applicable commission config
        config = self.db.query(CommissionConfig).filter(
            CommissionConfig.category == transaction_type,
            CommissionConfig.is_active == True
        ).first()
        
        if not config:
            return {"commission": Decimal("0"), "config_id": None}
        
        # Calculate based on fee type
        if config.fee_type == "percentage":
            commission = transaction_amount * (config.fee_value / 100)
        elif config.fee_type == "fixed":
            commission = config.fee_value
        else:  # tiered
            commission = self._calculate_tiered_fee(config, transaction_amount)
        
        # Apply min/max limits
        if config.min_fee:
            commission = max(commission, config.min_fee)
        if config.max_fee:
            commission = min(commission, config.max_fee)
        
        return {
            "commission": commission,
            "config_id": config.id,
            "fee_type": config.fee_type,
            "currency": config.currency
        }
    
    def _calculate_tiered_fee(
        self,
        config: CommissionConfig,
        transaction_amount: Decimal
    ) -> Decimal:
        """Calculate tiered fee based on transaction amount."""
        # For now, use percentage as fallback
        # TODO: Implement proper tiered fee calculation based on config.applies_to
        if config.fee_type == "tiered":
            # Default to percentage calculation
            return transaction_amount * (config.fee_value / 100)
        return Decimal("0")
    
    def apply_commission(
        self,
        transaction_id: str,
        transaction_type: str,
        transaction_amount: Decimal,
        payer_id: int,
        transaction_metadata: Dict[str, Any]
    ) -> CommissionCharge:
        """Apply commission to a transaction."""
        calculation = self.calculate_commission(
            transaction_type,
            transaction_amount,
            transaction_metadata
        )
        
        charge = CommissionCharge(
            config_id=calculation["config_id"],
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=calculation["commission"],
            currency=calculation["currency"],
            payer_id=payer_id,
            calculation_details=calculation
        )
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        
        return charge
