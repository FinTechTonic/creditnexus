"""Entitlement checks for BYOK access, trading unlock, and org/blockchain unlock.

BYOK (Bring Your Own Keys) is paywalled: instance admin always has access;
other users need entitlement (paid/subscription/credits).
Trading is unlocked when admin or user has a valid Alpaca key in BYOK.
Org and org blockchain are unlocked when user has paid $2 or has active subscription.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import ByokProvider, User, UserByokKey

logger = logging.getLogger(__name__)


def _is_instance_admin(user: User) -> bool:
    """True if user is instance admin (admin always allowed for BYOK)."""
    return getattr(user, "is_instance_admin", False) or (getattr(user, "role", None) == "admin")


def can_access_byok(user: User, db: Session) -> bool:
    """True if user can access BYOK: admin always; else paywalled (entitlement/credits/subscription)."""
    if _is_instance_admin(user):
        return True
    # Paywalled BYOK: user must have entitlement (e.g. paid $2, active subscription, or credits)
    if getattr(user, "org_admin_payment_status", None) == "paid":
        return True
    if getattr(user, "subscription_tier", None) and str(user.subscription_tier).lower() not in ("free", ""):
        return True
    # Optional: check CreditBalance for user (rolling credits / pay-as-you-go)
    try:
        from app.db.models import CreditBalance
        balance = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
        if balance and getattr(balance, "total_balance", 0) and int(balance.total_balance or 0) > 0:
            return True
    except Exception as e:  # noqa: BLE001
        logger.debug("CreditBalance check for BYOK access: %s", e)
    return False


def has_trading_unlocked(user: User, db: Session) -> bool:
    """True if user can trade: admin or user has valid Alpaca key in BYOK (unlocks_trading)."""
    if _is_instance_admin(user):
        return True
    byok_alpaca = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == user.id,
            UserByokKey.provider == ByokProvider.ALPACA.value,
        )
        .first()
    )
    return byok_alpaca is not None and (
        getattr(byok_alpaca, "unlocks_trading", False) or bool(getattr(byok_alpaca, "credentials_encrypted", None))
    )


def _user_has_org_entitlement(user: User, db: Session) -> bool:
    """True if user has paid $2 or has active subscription/credits (for org unlock)."""
    if getattr(user, "org_admin_payment_status", None) == "paid":
        return True
    if getattr(user, "subscription_tier", None) and str(user.subscription_tier).lower() not in ("free", ""):
        return True
    try:
        from app.db.models import CreditBalance
        balance = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
        if balance and getattr(balance, "total_balance", 0) and int(balance.total_balance or 0) > 0:
            return True
    except Exception as e:  # noqa: BLE001
        logger.debug("CreditBalance check for org unlock: %s", e)
    return False


def has_org_unlocked(user: User, org_id: Optional[int], db: Session) -> bool:
    """
    True if user can access org features: instance admin, or org belongs to user
    and user has paid $2 or has active $2 subscription for that org.
    If org_id is None, uses user.organization_id.
    """
    if _is_instance_admin(user):
        return True
    resolved_org_id = org_id if org_id is not None else getattr(user, "organization_id", None)
    if resolved_org_id is None:
        return False
    if getattr(user, "organization_id", None) != resolved_org_id:
        return False
    return _user_has_org_entitlement(user, db)


def can_access_org_blockchain(user: User, org_id: Optional[int], db: Session) -> bool:
    """
    True if user can access org blockchain features. Same criteria as has_org_unlocked:
    instance admin, or org belongs to user and user has paid $2 or has active subscription.
    """
    return has_org_unlocked(user, org_id, db)
