"""Securitization service for structured finance products."""

import logging
from decimal import Decimal
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import (
    SecuritizationPool, SecuritizationTranche, SecuritizationPoolAsset,
    RegulatoryFiling, Deal, LoanAsset, User, NotarizationRecord
)
from app.models.cdm import (
    SecuritizationPool as CDMSecuritizationPool,
    UnderlyingAsset, Tranche, PaymentWaterfall, PaymentRule,
    Party, Money, Currency
)
from app.models.cdm_events import (
    generate_cdm_securitization_creation,
    generate_cdm_securitization_notarization
)
from app.services.wallet_service import WalletService
from app.services.blockchain_service import BlockchainService
from app.services.x402_payment_service import X402PaymentService
from app.services.notarization_service import NotarizationService
from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
from app.db.models import PaymentEvent as PaymentEventModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class SecuritizationService:
    """Service for managing securitization pools and structured finance products."""
    
    def __init__(self, db: Session):
        """Initialize securitization service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.wallet_service = WalletService()
        self.blockchain_service = BlockchainService()
    
    def create_securitization_pool(
        self,
        pool_name: str,
        pool_type: str,
        originator_id: int,
        trustee_id: int,
        underlying_assets: List[Dict[str, Any]],
        tranches: List[Dict[str, Any]],
        payment_waterfall: Optional[Dict[str, Any]] = None
    ) -> SecuritizationPool:
        """
        Create a new securitization pool.
        
        Args:
            pool_name: Name of the pool
            pool_type: Type of pool (ABS, CLO, MBS, etc.)
            originator_id: User ID of originator
            trustee_id: User ID of trustee
            underlying_assets: List of asset dictionaries with asset_id, asset_type, deal_id/loan_asset_id
            tranches: List of tranche dictionaries with tranche_name, tranche_class, size, interest_rate, etc.
            payment_waterfall: Optional payment waterfall rules
            
        Returns:
            Created SecuritizationPool instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate users exist
        originator = self.db.query(User).filter(User.id == originator_id).first()
        if not originator:
            raise ValueError(f"Originator user {originator_id} not found")
        
        trustee = self.db.query(User).filter(User.id == trustee_id).first()
        if not trustee:
            raise ValueError(f"Trustee user {trustee_id} not found")
        
        # Ensure users have wallet addresses
        originator_wallet = self.wallet_service.ensure_user_has_wallet(originator, self.db)
        trustee_wallet = self.wallet_service.ensure_user_has_wallet(trustee, self.db)
        
        # Validate and calculate total pool value from underlying assets
        total_pool_value = Decimal("0")
        currency = Currency.USD  # Default currency
        
        validated_assets = []
        for asset_data in underlying_assets:
            asset_type = asset_data.get("asset_type")
            deal_id = asset_data.get("deal_id")
            loan_asset_id = asset_data.get("loan_asset_id")
            allocation_percentage = Decimal(str(asset_data.get("allocation_percentage", 0)))
            
            if asset_type == "deal" and deal_id:
                deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
                if not deal:
                    raise ValueError(f"Deal {deal_id} not found")
                
                # Extract value from deal
                if deal.deal_data and isinstance(deal.deal_data, dict):
                    commitment = deal.deal_data.get("total_commitment")
                    if commitment:
                        asset_value = Decimal(str(commitment))
                        total_pool_value += asset_value
                        if not currency and deal.deal_data.get("currency"):
                            currency = Currency(deal.deal_data["currency"])
                
                validated_assets.append({
                    "asset_id": f"deal_{deal_id}",
                    "asset_type": "deal",
                    "deal_id": str(deal_id),
                    "asset_value": asset_value,
                    "allocation_percentage": allocation_percentage
                })
            
            elif asset_type == "loan_asset" and loan_asset_id:
                loan = self.db.query(LoanAsset).filter(LoanAsset.id == loan_asset_id).first()
                if not loan:
                    raise ValueError(f"Loan asset {loan_asset_id} not found")
                
                # Extract value from loan
                if loan.principal_amount:
                    asset_value = Decimal(str(loan.principal_amount))
                    total_pool_value += asset_value
                
                validated_assets.append({
                    "asset_id": f"loan_{loan_asset_id}",
                    "asset_type": "loan_asset",
                    "loan_asset_id": str(loan_asset_id),
                    "asset_value": asset_value,
                    "allocation_percentage": allocation_percentage
                })
        
        if total_pool_value <= 0:
            raise ValueError("Total pool value must be greater than zero")
        
        # Validate tranche structure
        tranche_sum = Decimal("0")
        for tranche_data in tranches:
            tranche_size = Decimal(str(tranche_data.get("size", {}).get("amount", 0)))
            tranche_sum += tranche_size
        
        if abs(tranche_sum - total_pool_value) > Decimal("0.01"):
            raise ValueError(f"Tranche sizes ({tranche_sum}) must sum to total pool value ({total_pool_value})")
        
        # Generate pool ID
        pool_id = f"POOL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create CDM SecuritizationPool object
        originator_party = Party(
            id=f"originator_{originator_id}",
            name=originator.display_name,
            lei=None
        )
        
        trustee_party = Party(
            id=f"trustee_{trustee_id}",
            name=trustee.display_name,
            lei=None
        )
        
        # Build CDM underlying assets
        cdm_underlying_assets = [
            UnderlyingAsset(
                asset_id=asset["asset_id"],
                asset_type=asset["asset_type"],
                deal_id=asset.get("deal_id"),
                loan_asset_id=asset.get("loan_asset_id"),
                asset_value=Money(amount=asset["asset_value"], currency=currency),
                allocation_percentage=asset["allocation_percentage"]
            )
            for asset in validated_assets
        ]
        
        # Build CDM tranches
        cdm_tranches = []
        for tranche_data in tranches:
            tranche_size = Decimal(str(tranche_data.get("size", {}).get("amount", 0)))
            tranche_currency = Currency(tranche_data.get("size", {}).get("currency", "USD"))
            
            cdm_tranche = Tranche(
                tranche_id=f"{pool_id}_{tranche_data.get('tranche_name', '').lower().replace(' ', '_')}",
                tranche_name=tranche_data.get("tranche_name", ""),
                tranche_class=tranche_data.get("tranche_class", ""),
                size=Money(amount=tranche_size, currency=tranche_currency),
                interest_rate=Decimal(str(tranche_data.get("interest_rate", 0))),
                risk_rating=tranche_data.get("risk_rating"),
                payment_priority=tranche_data.get("payment_priority", 999),
                cdm_tranche_data=tranche_data.get("cdm_tranche_data", {})
            )
            cdm_tranches.append(cdm_tranche)
        
        # Build payment waterfall
        if payment_waterfall:
            waterfall_rules = [
                PaymentRule(
                    priority=rule.get("priority", 999),
                    tranche_id=rule.get("tranche_id", ""),
                    payment_type=rule.get("payment_type", "interest"),
                    percentage=Decimal(str(rule.get("percentage", 0)))
                )
                for rule in payment_waterfall.get("rules", [])
            ]
        else:
            # Default waterfall: pay tranches in priority order
            waterfall_rules = [
                PaymentRule(
                    priority=t.payment_priority,
                    tranche_id=t.tranche_id,
                    payment_type="interest",
                    percentage=Decimal("100")  # 100% to this tranche at this priority
                )
                for t in sorted(cdm_tranches, key=lambda x: x.payment_priority)
            ]
        
        cdm_payment_waterfall = PaymentWaterfall(rules=waterfall_rules)
        
        # Create CDM SecuritizationPool
        cdm_pool = CDMSecuritizationPool(
            pool_id=pool_id,
            pool_name=pool_name,
            pool_type=pool_type,
            originator=originator_party,
            trustee=trustee_party,
            servicer=None,
            total_pool_value=Money(amount=total_pool_value, currency=currency),
            underlying_assets=cdm_underlying_assets,
            tranches=cdm_tranches,
            payment_waterfall=cdm_payment_waterfall,
            creation_date=date.today(),
            effective_date=date.today(),
            maturity_date=None
        )
        
        # Create database record
        pool = SecuritizationPool(
            pool_id=pool_id,
            pool_name=pool_name,
            pool_type=pool_type,
            originator_id=originator_id,
            trustee_id=trustee_id,
            total_pool_value=total_pool_value,
            currency=currency.value,
            cdm_payload=cdm_pool.model_dump(),
            status="draft"
        )
        
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)
        
        # Add underlying assets to pool
        for asset_data in validated_assets:
            pool_asset = SecuritizationPoolAsset(
                pool_id=pool.id,
                deal_id=int(asset_data["deal_id"]) if asset_data.get("deal_id") else None,
                loan_asset_id=int(asset_data["loan_asset_id"]) if asset_data.get("loan_asset_id") else None,
                asset_type=asset_data["asset_type"],
                allocation_percentage=asset_data["allocation_percentage"],
                allocation_amount=asset_data["asset_value"]
            )
            self.db.add(pool_asset)
        
        # Create tranche records
        for cdm_tranche in cdm_tranches:
            tranche = SecuritizationTranche(
                pool_id=pool.id,
                tranche_name=cdm_tranche.tranche_name,
                tranche_class=cdm_tranche.tranche_class,
                tranche_size=cdm_tranche.size.amount,
                interest_rate=cdm_tranche.interest_rate,
                risk_rating=cdm_tranche.risk_rating,
                payment_priority=cdm_tranche.payment_priority,
                cdm_tranche_data=cdm_tranche.model_dump(mode='json')
            )
            self.db.add(tranche)
        
        self.db.commit()
        
        # Initialize payment schedule metadata in pool CDM data
        payment_schedule = self._calculate_payment_schedule(cdm_tranches, currency, pool.effective_date if hasattr(pool, 'effective_date') and pool.effective_date else date.today())
        
        # Update pool CDM data with payment schedule
        pool_cdm_data = pool.cdm_data or {}
        if isinstance(pool_cdm_data, dict):
            pool_cdm_data['payment_schedule'] = payment_schedule
            pool.cdm_data = pool_cdm_data
            self.db.commit()
        
        # Generate CDM SecuritizationCreation event
        underlying_assets_data = [asset.model_dump() for asset in cdm_underlying_assets]
        tranches_data = [t.model_dump() for t in cdm_tranches]
        
        cdm_event = generate_cdm_securitization_creation(
            pool_id=pool_id,
            pool_name=pool_name,
            pool_type=pool_type,
            originator=originator_wallet or originator_party.id,
            trustee=trustee_wallet or trustee_party.id,
            total_pool_value=float(total_pool_value),
            currency=currency.value,
            underlying_assets=underlying_assets_data,
            tranches=tranches_data,
            related_event_identifiers=[]
        )
        
        logger.info(f"Created securitization pool {pool_id} with {len(cdm_tranches)} tranches")
        
        return pool
    
    def _calculate_payment_schedule(
        self,
        tranches: List[Tranche],
        currency: Currency,
        effective_date: date
    ) -> Dict[str, Any]:
        """Calculate payment schedule for securitization pool.
        
        Creates payment schedule metadata based on tranche interest rates and payment priorities.
        This is a simplified schedule - in production, you'd calculate based on actual payment dates.
        
        Args:
            tranches: List of CDM Tranche objects
            currency: Payment currency
            effective_date: Pool effective date
            
        Returns:
            Payment schedule dictionary with payment dates and amounts per tranche
        """
        from datetime import timedelta
        
        # Calculate payment schedule for each tranche
        # For now, create monthly payment schedule for 12 months (simplified)
        payment_dates = []
        for month in range(1, 13):  # 12 months
            payment_date = effective_date + timedelta(days=30 * month)
            payment_dates.append(payment_date.isoformat())
        
        # Create payment schedule entries for each tranche
        schedule_entries = []
        for tranche in tranches:
            # Calculate interest payment per period
            interest_per_period = (tranche.size.amount * tranche.interest_rate) / Decimal("12")  # Monthly
            
            for payment_date in payment_dates:
                schedule_entries.append({
                    "tranche_id": tranche.tranche_id,
                    "tranche_name": tranche.tranche_name,
                    "payment_type": "interest",
                    "amount": str(interest_per_period),
                    "currency": currency.value,
                    "due_date": payment_date,
                    "payment_priority": tranche.payment_priority,
                    "status": "pending"
                })
        
        return {
            "payment_frequency": "monthly",
            "total_periods": 12,
            "effective_date": effective_date.isoformat(),
            "schedule_entries": schedule_entries
        }
    
    def create_tranches(
        self,
        pool_id: int,
        tranches: List[Dict[str, Any]]
    ) -> List[SecuritizationTranche]:
        """Add tranches to an existing securitization pool.
        
        Args:
            pool_id: Pool database ID
            tranches: List of tranche dictionaries with tranche_name, tranche_class, size, interest_rate, priority, risk_rating
            
        Returns:
            List of created SecuritizationTranche instances
            
        Raises:
            ValueError: If validation fails
        """
        # Get pool
        pool = self.db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        # Get existing tranches to calculate current total
        existing_tranches = self.db.query(SecuritizationTranche).filter(
            SecuritizationTranche.pool_id == pool_id
        ).all()
        
        existing_tranche_sum = sum(Decimal(str(t.tranche_size)) for t in existing_tranches)
        
        # Validate new tranches
        new_tranche_sum = Decimal("0")
        cdm_tranches = []
        
        for tranche_data in tranches:
            tranche_size = Decimal(str(tranche_data.get("size", {}).get("amount", 0)))
            new_tranche_sum += tranche_size
            
            tranche_currency = Currency(tranche_data.get("size", {}).get("currency", "USD"))
            
            cdm_tranche = Tranche(
                tranche_id=f"{pool.pool_id}_{tranche_data.get('tranche_name', '').lower().replace(' ', '_')}",
                tranche_name=tranche_data.get("tranche_name", ""),
                tranche_class=tranche_data.get("tranche_class", ""),
                size=Money(amount=tranche_size, currency=tranche_currency),
                interest_rate=Decimal(str(tranche_data.get("interest_rate", 0))),
                risk_rating=tranche_data.get("risk_rating"),
                payment_priority=tranche_data.get("payment_priority", 999),
                cdm_tranche_data=tranche_data.get("cdm_tranche_data", {})
            )
            cdm_tranches.append(cdm_tranche)
        
        # Validate that new tranches don't exceed pool value
        total_tranche_sum = existing_tranche_sum + new_tranche_sum
        if total_tranche_sum > pool.total_pool_value:
            raise ValueError(
                f"Total tranche size ({total_tranche_sum}) exceeds pool value ({pool.total_pool_value})"
            )
        
        # Create tranche records
        created_tranches = []
        for cdm_tranche in cdm_tranches:
            tranche = SecuritizationTranche(
                pool_id=pool.id,
                tranche_name=cdm_tranche.tranche_name,
                tranche_class=cdm_tranche.tranche_class,
                tranche_size=cdm_tranche.size.amount,
                interest_rate=cdm_tranche.interest_rate,
                risk_rating=cdm_tranche.risk_rating,
                payment_priority=cdm_tranche.payment_priority,
                cdm_tranche_data=cdm_tranche.model_dump(mode='json')
            )
            self.db.add(tranche)
            created_tranches.append(tranche)
        
        # Update payment schedule in pool CDM data
        all_tranches = existing_tranches + created_tranches
        # Convert existing tranches to CDM format for schedule calculation
        existing_cdm_tranches = []
        for t in existing_tranches:
            # Extract tranche_id from cdm_tranche_data if available, or generate it
            tranche_id = None
            if t.cdm_tranche_data and isinstance(t.cdm_tranche_data, dict):
                tranche_id = t.cdm_tranche_data.get("tranche_id")
            if not tranche_id:
                tranche_id = f"{pool.pool_id}_{t.tranche_name.lower().replace(' ', '_')}"
            
            existing_cdm_tranches.append(
                Tranche(
                    tranche_id=tranche_id,
                    tranche_name=t.tranche_name,
                    tranche_class=t.tranche_class,
                    size=Money(amount=Decimal(str(t.tranche_size)), currency=Currency(pool.currency)),
                    interest_rate=t.interest_rate,
                    risk_rating=t.risk_rating,
                    payment_priority=t.payment_priority,
                    cdm_tranche_data=t.cdm_tranche_data or {}
                )
            )
        all_cdm_tranches = existing_cdm_tranches + cdm_tranches
        
        effective_date = pool.effective_date if hasattr(pool, 'effective_date') and pool.effective_date else date.today()
        payment_schedule = self._calculate_payment_schedule(
            all_cdm_tranches,
            Currency(pool.currency),
            effective_date
        )
        
        # Update pool CDM data
        pool_cdm_data = pool.cdm_data or {}
        if isinstance(pool_cdm_data, dict):
            pool_cdm_data['payment_schedule'] = payment_schedule
            pool.cdm_data = pool_cdm_data
        
        self.db.commit()
        self.db.refresh(pool)
        
        logger.info(f"Created {len(created_tranches)} tranches for pool {pool.pool_id}")
        
        return created_tranches
    
    def get_pool_details(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pool details with all relationships.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Pool details dictionary or None if not found
        """
        pool = (
            self.db.query(SecuritizationPool)
            .filter(SecuritizationPool.pool_id == pool_id)
            .first()
        )
        
        if not pool:
            return None
        
        # Load relationships
        tranches = self.db.query(SecuritizationTranche).filter(
            SecuritizationTranche.pool_id == pool.id
        ).all()
        
        assets = self.db.query(SecuritizationPoolAsset).filter(
            SecuritizationPoolAsset.pool_id == pool.id
        ).all()
        
        filings = self.db.query(RegulatoryFiling).filter(
            RegulatoryFiling.pool_id == pool.id
        ).all()
        
        return {
            "pool": pool.to_dict(),
            "tranches": [t.to_dict() for t in tranches],
            "assets": [a.to_dict() for a in assets],
            "filings": [f.to_dict() for f in filings],
            "cdm_payload": pool.cdm_payload
        }
    
    def purchase_tranche_with_payment(
        self,
        pool_id: str,
        tranche_id: str,
        buyer_id: int,
        payment_payload: Optional[Dict[str, Any]] = None,
        payment_service: Optional[X402PaymentService] = None
    ) -> Dict[str, Any]:
        """
        Purchase tranche with x402 payment.
        
        Args:
            pool_id: Pool identifier
            tranche_id: Tranche identifier
            buyer_id: User ID of buyer
            payment_payload: Optional x402 payment payload
            payment_service: Optional x402 payment service
            
        Returns:
            Purchase result with token_id and transaction_hash
        """
        # Get pool and tranche
        pool = (
            self.db.query(SecuritizationPool)
            .filter(SecuritizationPool.pool_id == pool_id)
            .first()
        )
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        tranche = (
            self.db.query(SecuritizationTranche)
            .filter(
                and_(
                    SecuritizationTranche.pool_id == pool.id,
                    SecuritizationTranche.tranche_name == tranche_id
                )
            )
            .first()
        )
        if not tranche:
            raise ValueError(f"Tranche {tranche_id} not found in pool {pool_id}")
        
        buyer = self.db.query(User).filter(User.id == buyer_id).first()
        if not buyer:
            raise ValueError(f"Buyer user {buyer_id} not found")
        
        # Process payment via x402
        if payment_service and payment_payload:
            payer = Party(
                id=f"buyer_{buyer_id}",
                name=buyer.display_name,
                lei=None
            )
            
            receiver = Party(
                id=f"pool_{pool_id}",
                name=pool.pool_name,
                lei=None
            )
            
            # Note: process_payment_flow is async, but this method is sync
            # In production, this should be called from an async endpoint
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            payment_result = loop.run_until_complete(
                payment_service.process_payment_flow(
                amount=tranche.tranche_size,
                currency=Currency(pool.currency),
                payer=payer,
                receiver=receiver,
                    payment_type="tranche_purchase",
                    payment_payload=payment_payload,
                    cdm_reference={"pool_id": pool_id, "tranche_id": tranche_id}
                )
            )
            
            if payment_result.get("status") != "settled":
                return payment_result  # Returns 402 Payment Required structure
        
        # Get buyer wallet address
        buyer_wallet = self.wallet_service.ensure_user_has_wallet(buyer, self.db)
        if not buyer_wallet:
            raise ValueError(f"Buyer {buyer_id} does not have a wallet address")
        
        # Mint ERC-721 token via SecuritizationToken contract
        # Prepare metadata for token minting
        # Convert interest rate to basis points (e.g., 5.5% = 550)
        interest_rate_bps = int(tranche.interest_rate * 100) if tranche.interest_rate else 0
        
        token_metadata = {
            "pool_id": pool_id,
            "tranche_id": tranche_id,
            "tranche_name": tranche.tranche_name,
            "tranche_class": tranche.tranche_class,
            "size": str(tranche.tranche_size),
            "interest_rate_percent": str(tranche.interest_rate),
            "risk_rating": tranche.risk_rating,
            "buyer_id": buyer_id,
            "purchase_date": datetime.utcnow().isoformat(),
            # Contract-specific fields (required for mintTranche function)
            "principal_amount": int(tranche.tranche_size),  # In smallest currency unit (e.g., cents for USD)
            "interest_rate": interest_rate_bps,  # In basis points for contract
            "payment_priority": tranche.payment_priority if hasattr(tranche, 'payment_priority') else 999
        }
        
        try:
            mint_result = self.blockchain_service.mint_tranche_token(
                pool_id=pool_id,
                tranche_id=tranche_id,
                buyer_address=buyer_wallet,
                metadata=token_metadata
            )
            
            # Update tranche record with token_id and owner
            # Store in cdm_tranche_data if fields don't exist in schema yet
            if mint_result.get("token_id"):
                # Try to set fields if they exist
                if hasattr(tranche, 'token_id'):
                    tranche.token_id = mint_result["token_id"]
                if hasattr(tranche, 'owner_wallet_address'):
                    tranche.owner_wallet_address = buyer_wallet
                
                # Also store in cdm_tranche_data for compatibility
                tranche_data = tranche.cdm_tranche_data or {}
                if not isinstance(tranche_data, dict):
                    tranche_data = {}
                tranche_data["token_id"] = mint_result["token_id"]
                tranche_data["owner_wallet_address"] = buyer_wallet
                tranche.cdm_tranche_data = tranche_data
                
                self.db.commit()
                self.db.refresh(tranche)
            
            logger.info(f"Tranche {tranche_id} purchased by user {buyer_id} for pool {pool_id}, token_id: {mint_result.get('token_id')}")
            
            return {
                "status": "success",
                "pool_id": pool_id,
                "tranche_id": tranche_id,
                "buyer_id": buyer_id,
                "token_id": mint_result.get("token_id"),
                "transaction_hash": payment_result.get("transaction_hash") if payment_service else mint_result.get("transaction_hash"),
                "mint_status": mint_result.get("status", "pending")
            }
        except Exception as e:
            logger.error(f"Failed to mint token for tranche purchase: {e}")
            # Still return success if payment was processed, but log the error
            return {
                "status": "success",
                "pool_id": pool_id,
                "tranche_id": tranche_id,
                "buyer_id": buyer_id,
                "transaction_hash": payment_result.get("transaction_hash") if payment_service else None,
                "token_id": None,
                "warning": f"Token minting failed: {str(e)}"
            }
    
    def distribute_payments(
        self,
        pool_id: str,
        total_payment_amount: Decimal,
        payment_type: str = "interest",
        payment_service: Optional[X402PaymentService] = None
    ) -> List[Dict[str, Any]]:
        """
        Distribute payments to tranche holders according to waterfall.
        
        Args:
            pool_id: Pool identifier
            total_payment_amount: Total amount to distribute
            payment_type: Type of payment (interest, principal)
            payment_service: Optional x402 payment service
            
        Returns:
            List of distribution results
        """
        pool = (
            self.db.query(SecuritizationPool)
            .filter(SecuritizationPool.pool_id == pool_id)
            .first()
        )
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        # Get tranches ordered by payment priority
        tranches = (
            self.db.query(SecuritizationTranche)
            .filter(SecuritizationTranche.pool_id == pool.id)
            .order_by(SecuritizationTranche.payment_priority.asc())
            .all()
        )
        
        distributions = []
        remaining = total_payment_amount
        
        # Distribute according to waterfall (simplified: pay in priority order)
        for tranche in tranches:
            if remaining <= 0:
                break
            
            # Calculate payment for this tranche
            if payment_type == "interest":
                tranche_payment = min(
                    remaining,
                    (tranche.tranche_size * tranche.interest_rate) / Decimal("100")
                )
            else:
                # Principal payment
                tranche_payment = min(remaining, tranche.tranche_size)
            
            if tranche_payment > 0:
                # Get tranche holders (owners of tokens for this tranche)
                tranche_holders = []
                # Check if tranche has owner_wallet_address (may not exist in schema yet)
                owner_wallet = getattr(tranche, 'owner_wallet_address', None)
                token_id = getattr(tranche, 'token_id', None)
                
                if owner_wallet:
                    # Single owner (simplified - in production, would query all token owners)
                    tranche_holders.append({
                        "wallet_address": owner_wallet,
                        "token_id": token_id,
                        "ownership_percentage": Decimal("100")  # Simplified - would calculate from token supply
                    })
                
                # Process payment distribution via smart contract if available
                distribution_result = None
                if tranche_holders and self.blockchain_service.is_connected():
                    try:
                        distribution_result = self.blockchain_service.distribute_payment_to_tranche(
                            pool_id=pool_id,
                            tranche_id=tranche.tranche_name,
                            amount=tranche_payment,
                            currency=pool.currency,
                            payment_type=payment_type
                        )
                    except Exception as e:
                        logger.warning(f"Smart contract distribution failed: {e}, falling back to manual distribution")
                
                # Process payments via x402 for each holder
                payment_transactions = []
                if payment_service and tranche_holders:
                    for holder in tranche_holders:
                        holder_payment = (tranche_payment * holder["ownership_percentage"]) / Decimal("100")
                        
                        payer = Party(
                            id=f"pool_{pool_id}",
                            name=pool.pool_name,
                            lei=None
                        )
                        
                        receiver = Party(
                            id=holder["wallet_address"],
                            name=f"Tranche Holder {holder['wallet_address'][:8]}",
                            lei=None
                        )
                        
                        try:
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            payment_result = loop.run_until_complete(
                                payment_service.process_payment_flow(
                                    amount=holder_payment,
                                    currency=Currency(pool.currency),
                                    payer=payer,
                                    receiver=receiver,
                                    payment_type=f"tranche_{payment_type}",
                                    payment_payload=None,  # Would be provided by holder
                                    cdm_reference={
                                        "pool_id": pool_id,
                                        "tranche_id": tranche.tranche_name,
                                        "token_id": holder.get("token_id")
                                    }
                                )
                            )
                            
                            if payment_result.get("status") == "settled":
                                payment_transactions.append({
                                    "holder": holder["wallet_address"],
                                    "amount": float(holder_payment),
                                    "transaction_hash": payment_result.get("transaction_hash")
                                })
                        except Exception as e:
                            logger.error(f"Failed to process payment for holder {holder['wallet_address']}: {e}")
                
                # Update tranche position metadata (accumulate payments)
                # Store in cdm_tranche_data since we may not have a dedicated field yet
                tranche_data = tranche.cdm_tranche_data or {}
                if not isinstance(tranche_data, dict):
                    tranche_data = {}
                
                total_payments = tranche_data.get("total_payments_received", {})
                if payment_type not in total_payments:
                    total_payments[payment_type] = Decimal("0")
                else:
                    total_payments[payment_type] = Decimal(str(total_payments[payment_type]))
                
                total_payments[payment_type] += tranche_payment
                tranche_data["total_payments_received"] = {
                    k: str(v) if isinstance(v, Decimal) else v 
                    for k, v in total_payments.items()
                }
                tranche.cdm_tranche_data = tranche_data
                
                distributions.append({
                    "tranche_id": tranche.tranche_name,
                    "amount": float(tranche_payment),
                    "currency": pool.currency,
                    "payment_type": payment_type,
                    "holders_count": len(tranche_holders),
                    "payment_transactions": payment_transactions,
                    "smart_contract_distribution": distribution_result,
                    "status": "completed" if payment_transactions or distribution_result else "pending"
                })
                remaining -= tranche_payment
        
        # Commit tranche updates
        self.db.commit()
        
        logger.info(f"Distributed {total_payment_amount} {pool.currency} to {len(distributions)} tranches in pool {pool_id}")
        
        return distributions
