"""Rolling credits service: subscription-based credit generation and optional blockchain registration."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CreditBalance, CreditTransaction, User, UserSubscription
from app.services.adaptive_pricing_service import AdaptivePricingService
from app.services.blockchain_service import BlockchainService
from app.services.bridge_credit_verification_service import BridgeCreditVerificationService

logger = logging.getLogger(__name__)

# Per-tier base allocation per billing period (prorated by billing days/30). Units: credits.
# TIER_10 ($10/mo), TIER_15 ($15/mo) include Plaid cover via universal credits and PLAID_REFRESHES_INCLUDED.
TIER_CREDIT_ALLOCATION: Dict[str, Dict[str, int]] = {
    "pro": {
        "signing": 20,
        "document_review": 20,
        "verification": 20,
        "trading": 30,
        "loaning": 20,
        "borrowing": 20,
        "compliance_check": 20,
        "securitization": 15,
        "risk_analysis": 20,
        "quantitative_analysis": 15,
        "stock_prediction_daily": 5,
        "stock_prediction_hourly": 5,
        "stock_prediction_15min": 5,
        "universal": 100,
    },
    "premium": {
        "signing": 60,
        "document_review": 60,
        "verification": 60,
        "trading": 90,
        "loaning": 60,
        "borrowing": 60,
        "compliance_check": 60,
        "securitization": 45,
        "risk_analysis": 60,
        "quantitative_analysis": 45,
        "stock_prediction_daily": 15,
        "stock_prediction_hourly": 15,
        "stock_prediction_15min": 15,
        "universal": 300,
    },
    "tier_10": {
        "signing": 10,
        "document_review": 10,
        "verification": 10,
        "trading": 15,
        "loaning": 10,
        "borrowing": 10,
        "compliance_check": 10,
        "securitization": 8,
        "risk_analysis": 10,
        "quantitative_analysis": 8,
        "stock_prediction_daily": 3,
        "stock_prediction_hourly": 3,
        "stock_prediction_15min": 3,
        "universal": 50,
    },
    "tier_15": {
        "signing": 25,
        "document_review": 25,
        "verification": 25,
        "trading": 40,
        "loaning": 25,
        "borrowing": 25,
        "compliance_check": 25,
        "securitization": 20,
        "risk_analysis": 25,
        "quantitative_analysis": 20,
        "stock_prediction_daily": 8,
        "stock_prediction_hourly": 8,
        "stock_prediction_15min": 8,
        "universal": 150,
    },
}

# Plaid cover: first N dashboard refreshes (or Plaid calls) per month included; beyond that use credits/pay-as-you-go.
PLAID_REFRESHES_INCLUDED: Dict[str, int] = {
    "tier_10": 10,
    "tier_15": 25,
    "pro": 20,
    "premium": 50,
}


class RollingCreditsService:
    """Generate subscription credits and optionally register them on CreditToken (ERC-721)."""

    def __init__(self, db: Session, blockchain_service: Optional[BlockchainService] = None):
        self.db = db
        self._blockchain = blockchain_service or BlockchainService()

    def generate_subscription_credits(
        self,
        user_id: int,
        subscription_id: int,
        tier: str,
        billing_period_start: datetime,
        billing_period_end: datetime,
    ) -> Dict[str, Any]:
        """
        Generate credits for a subscription billing period, update DB, and optionally register on-chain.

        - Prorates allocation by (billing days / 30), capped to 1.0.
        - Gets or creates CreditBalance for the user (organization_id=None).
        - Updates balances, lifetime_earned, total_balance; creates CreditTransaction per type.
        - Calls _register_credits_on_blockchain when contract and wallet are configured.

        Args:
            user_id: User id
            subscription_id: UserSubscription id
            tier: "pro" or "premium"
            billing_period_start: Start of billing window
            billing_period_end: End of billing window

        Returns:
            Dict with generated_credits, balance_id, transactions_created, blockchain (registered, reason, etc.)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "user_not_found", "generated_credits": {}}

        sub = self.db.query(UserSubscription).filter(
            UserSubscription.id == subscription_id,
            UserSubscription.user_id == user_id,
        ).first()
        if not sub:
            return {"error": "subscription_not_found", "generated_credits": {}}

        base = TIER_CREDIT_ALLOCATION.get(tier) or TIER_CREDIT_ALLOCATION.get("pro", {})
        if not base:
            return {"error": "tier_not_supported", "tier": tier, "generated_credits": {}}

        days = max(0, (billing_period_end - billing_period_start).days)
        factor = min(1.0, days / 30.0) if days else 0.0
        generated_credits: Dict[str, float] = {
            k: round(v * factor, 4) for k, v in base.items() if v and round(v * factor, 4) > 0
        }
        if not generated_credits:
            return {"generated_credits": {}, "balance_id": None, "transactions_created": 0, "blockchain": {"registered": False, "reason": "no_credits_generated"}}

        # Get or create CreditBalance (organization_id=None; User has no organization_id)
        balance = (
            self.db.query(CreditBalance)
            .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
            .first()
        )
        if not balance:
            balance = CreditBalance(
                user_id=user_id,
                organization_id=None,
                balances={},
                total_balance=0,
                lifetime_earned={},
                lifetime_spent={},
                blockchain_registered=False,
            )
            self.db.add(balance)
            self.db.flush()

        balances = dict(balance.balances or {})
        lifetime_earned = dict(balance.lifetime_earned or {})
        balance_before = dict(balances)
        tx_created = 0

        for credit_type, amount in generated_credits.items():
            if amount <= 0:
                continue
            prev = float(balances.get(credit_type, 0) or 0)
            new_val = round(prev + amount, 4)
            balances[credit_type] = new_val
            lifetime_earned[credit_type] = round(float(lifetime_earned.get(credit_type, 0) or 0) + amount, 4)

            self.db.add(
                CreditTransaction(
                    balance_id=balance.id,
                    user_id=user_id,
                    organization_id=balance.organization_id,
                    transaction_type="subscription",
                    credit_type=credit_type,
                    amount=Decimal(str(amount)),
                    balance_before=balance_before,
                    balance_after=dict(balances),
                    feature="subscription_credits",
                    subscription_id=subscription_id,
                    description=f"Subscription credits ({tier}, prorated {factor:.2f})",
                )
            )
            tx_created += 1
            balance_before = dict(balances)

        total_balance = sum(float(v) for v in balances.values())
        balance.balances = balances
        balance.lifetime_earned = lifetime_earned
        balance.total_balance = Decimal(str(round(total_balance, 4)))
        balance.last_updated = datetime.utcnow()

        # Optional blockchain registration (no-op if no contract or no wallet)
        bc_result = self._register_credits_on_blockchain(balance, generated_credits)
        if bc_result.get("registered"):
            balance.blockchain_registered = True
            balance.blockchain_token_id = str(bc_result.get("token_id") or balance.blockchain_token_id or "")
            balance.blockchain_tx_hash = bc_result.get("tx_hash") or balance.blockchain_tx_hash
            balance.blockchain_chain_id = bc_result.get("chain_id")

        return {
            "generated_credits": generated_credits,
            "balance_id": balance.id,
            "transactions_created": tx_created,
            "blockchain": bc_result,
        }

    def _register_credits_on_blockchain(
        self, balance: CreditBalance, generated_credits: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Register new credits on CreditToken (mint if no token, else updateCredits per type).

        - Skips if CREDIT_TOKEN_CONTRACT not set, or user has no wallet_address.
        - On first run: mintCredits(user, struct from generated_credits).
        - On later runs: updateCredits(token_id, credit_type, amount, false) for each type.

        Returns:
            { registered: bool, reason?: str, token_id?: str, tx_hash?: str, chain_id?: int }
        """
        if not generated_credits:
            return {"registered": False, "reason": "no_credits"}

        if not settings.CREDIT_TOKEN_CONTRACT:
            return {"registered": False, "reason": "blockchain_not_configured"}

        if not self._blockchain.is_connected() or not self._blockchain.deployer_account:
            return {"registered": False, "reason": "blockchain_not_connected"}

        # Need user for wallet_address
        user = getattr(balance, "user", None) or self.db.query(User).filter(User.id == balance.user_id).first()
        if not user:
            return {"registered": False, "reason": "user_not_found"}

        wallet = getattr(user, "wallet_address", None)
        if not wallet or not str(wallet).strip():
            return {"registered": False, "reason": "no_wallet"}

        wallet = str(wallet).strip()

        existing_token = balance.blockchain_token_id

        if existing_token:
            # Update: call updateCredits for each type with amount > 0
            last_tx = None
            last_chain = None
            ok = 0
            for ct, amt in generated_credits.items():
                if not amt or amt <= 0:
                    continue
                res = self._blockchain.update_credit_token(int(existing_token), ct, amt, is_spend=False)
                if res.get("status") == "completed":
                    last_tx = res.get("tx_hash")
                    last_chain = res.get("chain_id")
                    ok += 1
                else:
                    logger.warning("update_credit_token %s: %s", ct, res.get("message", res))
            if ok:
                return {"registered": True, "token_id": existing_token, "tx_hash": last_tx, "chain_id": last_chain}
            return {"registered": False, "reason": "update_credits_failed"}

        # Mint: build struct from generated_credits (0 for missing types)
        struct_map = {k: generated_credits.get(k, 0) for k in BlockchainService._CREDIT_STRUCT_ORDER}
        res = self._blockchain.mint_credit_token(wallet, struct_map)
        if res.get("status") == "completed":
            return {
                "registered": True,
                "token_id": res.get("token_id"),
                "tx_hash": res.get("tx_hash"),
                "chain_id": res.get("chain_id"),
            }
        return {"registered": False, "reason": res.get("message", "mint_failed")}

    def spend_credits(
        self,
        user_id: int,
        credit_type: str,
        amount: float = 1.0,
        *,
        feature: str = "stock_prediction",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deduct credits for feature usage (e.g. stock_prediction_daily). Creates a usage CreditTransaction.

        - Finds CreditBalance for user (organization_id=None).
        - Tries credit_type first; if insufficient, tries "universal".
        - Deducts, creates CreditTransaction(transaction_type="usage"), updates balance.

        Returns:
            { "ok": True, "balance_after": float } or { "ok": False, "reason": "insufficient_credits"|"user_not_found"|"no_balance" }
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"ok": False, "reason": "user_not_found"}

        balance = (
            self.db.query(CreditBalance)
            .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
            .first()
        )
        if not balance:
            return {"ok": False, "reason": "no_balance"}

        # Phase 12: use AdaptivePricingService when enabled for cost
        effective_amount = amount
        if getattr(settings, "ADAPTIVE_PRICING_ENABLED", False):
            try:
                pricing = AdaptivePricingService()
                if pricing.is_enabled():
                    cost = pricing.calculate_adaptive_cost(feature, quantity=1.0, include_server_fee=True)
                    effective_amount = float(cost)
            except Exception as e:
                logger.debug("AdaptivePricingService cost lookup failed: %s", e)
        amt = Decimal(str(round(effective_amount, 4)))
        if amt <= 0:
            return {"ok": True, "balance_after": float(balance.get_balance(credit_type))}

        balances = dict(balance.balances or {})
        balance_before = dict(balances)

        # Try credit_type then universal
        for ctype in (credit_type, "universal"):
            if ctype not in balances:
                continue
            available = Decimal(str(balances[ctype] or 0))
            if available <= 0:
                continue
            deduct = min(amt, available)
            new_val = round(float(available - deduct), 4)
            balances[ctype] = new_val if new_val > 0 else 0
            if new_val <= 0:
                del balances[ctype]
            amt -= deduct
            lifetime_spent = dict(balance.lifetime_spent or {})
            lifetime_spent[ctype] = round(float(lifetime_spent.get(ctype, 0) or 0) + float(deduct), 4)
            balance.lifetime_spent = lifetime_spent

            self.db.add(
                CreditTransaction(
                    balance_id=balance.id,
                    user_id=user_id,
                    organization_id=balance.organization_id,
                    transaction_type="usage",
                    credit_type=ctype,
                    amount=Decimal(str(-float(deduct))),
                    balance_before=balance_before,
                    balance_after=dict(balances),
                    feature=feature,
                    description=description or f"Spend {deduct} {ctype} for {feature}",
                )
            )
            balance_before = dict(balances)
            if amt <= 0:
                break

        if amt > 0:
            return {"ok": False, "reason": "insufficient_credits"}

        total_balance = sum(float(v) for v in balances.values())
        balance.balances = balances
        balance.total_balance = Decimal(str(round(total_balance, 4)))
        balance.last_updated = datetime.utcnow()

        # Phase 12: optional bridge verification after spend
        if getattr(settings, "BRIDGE_VERIFY_AFTER_SPEND", False):
            try:
                bridge = BridgeCreditVerificationService(self.db)
                bridge.verify_credit_usage(
                    user_id=user_id,
                    credit_type=credit_type,
                    amount=effective_amount,
                    sync_from_chain=False,
                )
            except Exception as e:
                logger.debug("BridgeCreditVerificationService after spend failed: %s", e)

        return {"ok": True, "balance_after": total_balance}

    def add_credits(
        self,
        user_id: int,
        credit_type: str,
        amount: float,
        *,
        feature: str = "purchase",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add credits to user balance (e.g. org_admin signup, subscription upgrade, mobile app purchase).
        Gets or creates CreditBalance; creates CreditTransaction(transaction_type='subscription').
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"ok": False, "reason": "user_not_found"}
        balance = (
            self.db.query(CreditBalance)
            .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
            .first()
        )
        if not balance:
            balance = CreditBalance(
                user_id=user_id,
                organization_id=None,
                balances={},
                total_balance=0,
                lifetime_earned={},
                lifetime_spent={},
                blockchain_registered=False,
            )
            self.db.add(balance)
            self.db.flush()
        balances = dict(balance.balances or {})
        lifetime_earned = dict(balance.lifetime_earned or {})
        amt = Decimal(str(round(amount, 4)))
        if amt <= 0:
            return {"ok": True}
        prev = float(balances.get(credit_type, 0) or 0)
        new_val = round(prev + float(amt), 4)
        balances[credit_type] = new_val
        lifetime_earned[credit_type] = round(float(lifetime_earned.get(credit_type, 0) or 0) + float(amt), 4)
        total_balance = sum(float(v) for v in balances.values())
        balance.balances = balances
        balance.lifetime_earned = lifetime_earned
        balance.total_balance = Decimal(str(round(total_balance, 4)))
        balance.last_updated = datetime.utcnow()
        self.db.add(
            CreditTransaction(
                balance_id=balance.id,
                user_id=user_id,
                organization_id=balance.organization_id,
                transaction_type="subscription",
                credit_type=credit_type,
                amount=amt,
                balance_before={credit_type: prev},
                balance_after=dict(balances),
                feature=feature,
                description=description or f"{feature} credits",
            )
        )
        return {"ok": True, "balance_after": new_val}
