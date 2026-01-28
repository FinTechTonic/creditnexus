"""Service for managing user subscriptions."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    User, UserSubscription, SubscriptionUsage,
    SubscriptionTier, SubscriptionType
)
from app.services.rolling_credits_service import RollingCreditsService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing user subscriptions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_tier(self, user_id: int) -> str:
        """Get user's current subscription tier."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return SubscriptionTier.FREE.value
        
        # Check for active subscription
        active_sub = self.db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active == True
        ).first()
        
        if active_sub:
            # Check if expired (unless lifetime)
            if active_sub.expires_at and active_sub.expires_at < datetime.utcnow():
                return SubscriptionTier.FREE.value
            return active_sub.tier
        
        return user.subscription_tier or SubscriptionTier.FREE.value
    
    def create_subscription(
        self,
        user_id: int,
        tier: str,
        subscription_type: str,
        payment_id: Optional[int] = None,
        lifetime: bool = False
    ) -> UserSubscription:
        """Create a new subscription (activate) and generate rolling credits for pro/premium tiers."""
        now = datetime.utcnow()
        if lifetime:
            expires_at = None
        elif subscription_type == SubscriptionType.MONTHLY.value:
            expires_at = now + timedelta(days=30)
        elif subscription_type == SubscriptionType.YEARLY.value:
            expires_at = now + timedelta(days=365)
        else:
            expires_at = None  # Pay-as-you-go

        subscription = UserSubscription(
            user_id=user_id,
            tier=tier,
            subscription_type=subscription_type,
            payment_id=payment_id,
            expires_at=expires_at,
            is_active=True,
            started_at=now,
        )
        self.db.add(subscription)
        self.db.flush()  # ensure subscription.id for credit generation

        # Generate rolling credits for pro/premium (activate)
        if tier in ("pro", "premium"):
            period_start = subscription.started_at or now
            period_end = subscription.expires_at if subscription.expires_at else (period_start + timedelta(days=30))
            try:
                result = RollingCreditsService(self.db).generate_subscription_credits(
                    user_id=subscription.user_id,
                    subscription_id=subscription.id,
                    tier=tier,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                )
                if result.get("transactions_created", 0) or result.get("generated_credits"):
                    logger.info(
                        "Rolling credits generated on activate: user_id=%s sub_id=%s credits=%s",
                        user_id, subscription.id, result.get("generated_credits"),
                    )
            except Exception as e:
                logger.warning("Rolling credits on activate failed (subscription created): %s", e)

        # Update user tier
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_tier = tier

        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def mark_org_admin_paid(self, user_id: int, *, payment_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Mark a user as having completed org-admin signup payment.
        This is used to gate organization admin access during signup.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"ok": False, "reason": "user_not_found"}

        user.org_admin_payment_status = "paid"
        user.org_admin_payment_id = payment_id
        user.org_admin_paid_at = datetime.utcnow()
        self.db.commit()
        return {"ok": True}

    def renew_subscription(self, subscription_id: int) -> Optional[UserSubscription]:
        """Renew a subscription for the next billing period and generate rolling credits (pro/premium).

        - period_start = current expires_at; period_end = period_start + 30 (monthly) or 365 (yearly).
        - Lifetime (expires_at is None) is left unchanged.
        """
        sub = (
            self.db.query(UserSubscription)
            .filter(UserSubscription.id == subscription_id, UserSubscription.is_active == True)
            .first()
        )
        if not sub or not sub.expires_at:
            return sub

        period_start = sub.expires_at
        if sub.subscription_type == SubscriptionType.YEARLY.value:
            period_end = period_start + timedelta(days=365)
        else:
            period_end = period_start + timedelta(days=30)

        if sub.tier in ("pro", "premium"):
            try:
                result = RollingCreditsService(self.db).generate_subscription_credits(
                    user_id=sub.user_id,
                    subscription_id=sub.id,
                    tier=sub.tier,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                )
                if result.get("transactions_created", 0) or result.get("generated_credits"):
                    logger.info(
                        "Rolling credits generated on renew: user_id=%s sub_id=%s credits=%s",
                        sub.user_id, sub.id, result.get("generated_credits"),
                    )
            except Exception as e:
                logger.warning("Rolling credits on renew failed (renewal will still extend expires_at): %s", e)

        sub.expires_at = period_end
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def track_usage(
        self,
        user_id: int,
        feature: str,
        increment: int = 1
    ) -> Dict[str, Any]:
        """Track usage for pay-as-you-go subscriptions."""
        tier = self.get_user_tier(user_id)
        if tier != SubscriptionTier.PRO.value:
            return {"tracked": False, "reason": "not_pro_tier"}
        
        # Get current billing period
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        period_end = period_start + timedelta(days=32)
        period_end = period_end.replace(day=1) - timedelta(days=1)
        
        usage = self.db.query(SubscriptionUsage).filter(
            SubscriptionUsage.user_id == user_id,
            SubscriptionUsage.feature == feature,
            SubscriptionUsage.billing_period_start == period_start
        ).first()
        
        if usage:
            usage.usage_count += increment
        else:
            subscription = self.db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id,
                UserSubscription.is_active == True
            ).first()
            
            usage = SubscriptionUsage(
                user_id=user_id,
                subscription_id=subscription.id if subscription else None,
                feature=feature,
                usage_count=increment,
                billing_period_start=period_start,
                billing_period_end=period_end
            )
            self.db.add(usage)
        
        self.db.commit()
        return {"tracked": True, "usage_count": usage.usage_count}
