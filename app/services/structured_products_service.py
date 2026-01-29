"""Service for managing generic structured investment products (SIPs)."""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.db.models import (
    StructuredProductTemplate,
    StructuredProductInstance,
    ProductSubscription,
    User,
)

logger = logging.getLogger(__name__)

class StructuredProductsService:
    """Service for managing structured product templates, instances, and subscriptions."""

    def __init__(self, db: Session):
        self.db = db
        # Optional blockchain integration for anchoring SIP issuance on-chain
        try:
            from app.services.blockchain_service import BlockchainService

            self.blockchain_service: Optional[BlockchainService] = BlockchainService()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("BlockchainService not available for StructuredProductsService: %s", exc)
            self.blockchain_service = None

    def create_template(
        self,
        name: str,
        product_type: str,
        underlying_symbol: str,
        payoff_formula: Dict[str, Any],
        maturity_days: int,
        principal: Decimal,
        created_by: int,
        fees: Decimal = Decimal("0"),
    ) -> StructuredProductTemplate:
        """Create a new structured product template."""
        template = StructuredProductTemplate(
            name=name,
            product_type=product_type,
            underlying_symbol=underlying_symbol,
            payoff_formula=payoff_formula,
            maturity_days=maturity_days,
            principal=principal,
            fees=fees,
            created_by=created_by
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Created structured product template: {name} (ID: {template.id})")
        return template

    def issue_product(
        self,
        template_id: int,
        issuer_user_id: int,
        total_notional: Decimal,
        issue_date: Optional[date] = None
    ) -> StructuredProductInstance:
        """Issue a new instance of a structured product template."""
        template = self.db.query(StructuredProductTemplate).filter(
            StructuredProductTemplate.id == template_id
        ).first()
        if not template:
            raise ValueError(f"Template {template_id} not found")

        if not issue_date:
            issue_date = date.today()

        maturity_date = issue_date + timedelta(days=template.maturity_days)

        instance = StructuredProductInstance(
            template_id=template_id,
            issuer_user_id=issuer_user_id,
            total_notional=total_notional,
            issue_date=issue_date,
            maturity_date=maturity_date,
            status="active",
            current_value=template.principal
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Issued structured product instance: ID {instance.id} from template {template_id}")

        # Anchor structured product issuance on-chain via securitization notarization contract (best-effort).
        self._anchor_instance_on_chain(instance, template)

        return instance

    def subscribe_to_product(
        self,
        instance_id: int,
        investor_user_id: int,
        amount: Decimal
    ) -> ProductSubscription:
        """Subscribe an investor to a structured product instance."""
        instance = self.db.query(StructuredProductInstance).filter(
            StructuredProductInstance.id == instance_id
        ).first()
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status != "active":
            raise ValueError(f"Instance {instance_id} is not active (status: {instance.status})")

        subscription = ProductSubscription(
            instance_id=instance_id,
            investor_user_id=investor_user_id,
            subscription_amount=amount,
            subscription_date=date.today(),
            status="active"
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        logger.info(f"User {investor_user_id} subscribed {amount} to product {instance_id}")
        return subscription

    def get_templates(self, active_only: bool = True) -> List[StructuredProductTemplate]:
        """Get all structured product templates."""
        query = self.db.query(StructuredProductTemplate)
        if active_only:
            query = query.filter(StructuredProductTemplate.is_active == True)
        return query.order_by(StructuredProductTemplate.created_at.desc()).all()

    def get_instances(self, status: Optional[str] = None) -> List[StructuredProductInstance]:
        """Get all structured product instances."""
        query = self.db.query(StructuredProductInstance)
        if status:
            query = query.filter(StructuredProductInstance.status == status)
        return query.order_by(StructuredProductInstance.issue_date.desc()).all()

    def get_user_subscriptions(self, user_id: int) -> List[ProductSubscription]:
        """Get all subscriptions for a user."""
        return self.db.query(ProductSubscription).filter(
            ProductSubscription.investor_user_id == user_id
        ).order_by(ProductSubscription.subscription_date.desc()).all()

    def update_instance_value(self, instance_id: int, new_value: Decimal) -> StructuredProductInstance:
        """Update the current fair value of a product instance."""
        instance = self.db.query(StructuredProductInstance).filter(
            StructuredProductInstance.id == instance_id
        ).first()
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        instance.current_value = new_value
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def _anchor_instance_on_chain(
        self,
        instance: StructuredProductInstance,
        template: Optional[StructuredProductTemplate] = None,
    ) -> None:
        """
        Best-effort anchoring of a structured product instance on-chain using the
        existing SecuritizationNotarization contract.

        This reuses the same hashing approach as deal notarization, but uses a
        synthetic pool_id of the form \"sip_{instance.id}\" so SIPs remain
        logically distinct from securitization pools.
        """
        if not self.blockchain_service:
            logger.debug("Skipping SIP blockchain anchoring: BlockchainService unavailable")
            return

        # Import lazily to avoid circulars at module import time
        try:
            from app.utils.crypto_verification import compute_payload_hash
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Skipping SIP blockchain anchoring: compute_payload_hash unavailable: %s", exc)
            return

        try:
            if template is None:
                template = instance.template

            issuer: Optional[User] = instance.issuer if hasattr(instance, "issuer") else None

            payload: Dict[str, Any] = {
                "sip_instance_id": instance.id,
                "sip_template_id": instance.template_id,
                "name": getattr(template, "name", None),
                "product_type": getattr(template, "product_type", None),
                "underlying_symbol": getattr(template, "underlying_symbol", None),
                "principal": float(template.principal) if template and template.principal is not None else None,
                "total_notional": float(instance.total_notional) if instance.total_notional is not None else None,
                "issuer_user_id": instance.issuer_user_id,
                "issue_date": instance.issue_date.isoformat() if instance.issue_date else None,
                "maturity_date": instance.maturity_date.isoformat() if instance.maturity_date else None,
                "created_at": instance.created_at.isoformat() if instance.created_at else None,
            }

            notarization_hash = compute_payload_hash(payload)

            # Prefer issuer's wallet as signer if available; otherwise let BlockchainService
            # fall back to its demo/deployer account.
            signers: List[str] = []
            if issuer and issuer.wallet_address:
                try:
                    # EncryptedString transparently decrypts on attribute access.
                    signers = [str(issuer.wallet_address)]
                except Exception:
                    # If decryption fails, just fall back to empty signers list.
                    signers = []

            pool_id = f"sip_{instance.id}"
            result = self.blockchain_service.create_pool_notarization_on_chain(
                pool_id=pool_id,
                notarization_hash_hex=notarization_hash,
                signers=signers,
            )

            if result.get("success"):
                logger.info(
                    "Anchored SIP instance %s on-chain via pool_id=%s tx=%s",
                    instance.id,
                    pool_id,
                    result.get("transaction_hash"),
                )
            else:
                logger.warning(
                    "Failed to anchor SIP instance %s on-chain: %s",
                    instance.id,
                    result.get("error"),
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Unexpected error anchoring SIP instance %s on-chain: %s", instance.id, exc, exc_info=True)

    def calculate_fair_value(self, instance_id: int) -> Decimal:
        """
        Calculate fair value based on underlying price and payoff formula.
        """
        from app.services.market_data_service import get_historical_data
        from datetime import datetime, timezone

        instance = self.db.query(StructuredProductInstance).filter(
            StructuredProductInstance.id == instance_id
        ).first()
        if not instance or not instance.template:
            raise ValueError(f"Instance {instance_id} not found")

        template = instance.template
        symbol = template.underlying_symbol
        
        # Get current price
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=5) # Buffer for weekends
        df = get_historical_data(symbol, start, now, db=self.db)
        
        if df is None or df.empty:
            logger.warning(f"Could not fetch market data for {symbol}, using last known value")
            return instance.current_value or template.principal

        current_price = Decimal(str(df.iloc[-1]["Close"]))
        formula = template.payoff_formula or {}
        
        # Simplified payoff calculation based on formula type
        # In a real app, this would be a robust expression evaluator
        payoff_type = formula.get("type", "vanilla")
        strike_price = Decimal(str(formula.get("strike_price", template.principal)))
        
        if payoff_type == "equity_linked_note":
            # Payoff = Principal * (1 + Participation * Max(0, (Final - Initial)/Initial))
            initial_price = Decimal(str(formula.get("initial_price", current_price)))
            participation = Decimal(str(formula.get("participation", "1.0")))
            perf = (current_price - initial_price) / initial_price
            payoff = template.principal * (Decimal("1") + participation * max(Decimal("0"), perf))
            return payoff
        elif payoff_type == "barrier_option":
            # Simplified barrier logic
            barrier = Decimal(str(formula.get("barrier_price", "0")))
            if current_price <= barrier:
                return Decimal("0") # Knock-out
            return max(Decimal("0"), current_price - strike_price)
        
        # Default: return current principal value
        return template.principal
