"""Service for managing user subscriptions."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    User, UserSubscription, SubscriptionUsage,
    SubscriptionTier, SubscriptionType
)

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
        """Create a new subscription."""
        if lifetime:
            expires_at = None
        elif subscription_type == SubscriptionType.MONTHLY.value:
            expires_at = datetime.utcnow() + timedelta(days=30)
        elif subscription_type == SubscriptionType.YEARLY.value:
            expires_at = datetime.utcnow() + timedelta(days=365)
        else:
            expires_at = None  # Pay-as-you-go
        
        subscription = UserSubscription(
            user_id=user_id,
            tier=tier,
            subscription_type=subscription_type,
            payment_id=payment_id,
            expires_at=expires_at,
            is_active=True
        )
        self.db.add(subscription)
        
        # Update user tier
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_tier = tier
        
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
    
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
