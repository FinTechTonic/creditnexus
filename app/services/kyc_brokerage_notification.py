"""KYC and brokerage status change notifications.

When user preference kyc_brokerage_notifications is True, trigger notification
(log and optionally email) on brokerage account status change or KYC verification
completed/rejected by admin.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import User

logger = logging.getLogger(__name__)

_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kyc_brokerage_notify")
    return _executor


def _get_user_kyc_brokerage_notifications_preference(db: Session, user_id: int) -> bool:
    """Return True if user has kyc_brokerage_notifications enabled."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    preferences = {}
    if hasattr(user, "preferences") and user.preferences:
        preferences = user.preferences
    elif getattr(user, "profile_data", None) and isinstance(user.profile_data, dict):
        preferences = user.profile_data.get("preferences") or {}
    return preferences.get("kyc_brokerage_notifications", True)


def _get_user_email(user: User) -> Optional[str]:
    """Return user email for notification (handles EncryptedString)."""
    email = getattr(user, "email", None)
    if email is None:
        return None
    if hasattr(email, "decrypt"):
        try:
            return email.decrypt()
        except Exception:
            return str(email)
    return str(email)


async def _send_notification_email(user_id: int, recipient: str, subject: str, message: str) -> bool:
    """Send notification email via messenger if configured."""
    try:
        from app.services.messenger.factory import create_messenger

        messenger = create_messenger()
        if not messenger:
            return False
        return await messenger.send_message(recipient, subject, message, None)
    except Exception as exc:
        logger.warning("Failed to send KYC/brokerage notification email to user %s: %s", user_id, exc)
        return False


def _run_send(user_id: int, recipient: str, subject: str, message: str) -> None:
    """Run async send in a dedicated thread (avoids nested event loop)."""
    try:
        asyncio.run(_send_notification_email(user_id, recipient, subject, message))
    except Exception as exc:
        logger.warning("KYC/brokerage notification send failed for user %s: %s", user_id, exc)


def notify_kyc_brokerage_status(
    db: Session,
    user_id: int,
    subject: str,
    message: str,
) -> None:
    """
    If user has kyc_brokerage_notifications enabled, log and optionally send email.
    Called when brokerage account status changes or KYC verification is completed/rejected.
    """
    if not _get_user_kyc_brokerage_notifications_preference(db, user_id):
        return
    logger.info(
        "KYC/brokerage notification: user_id=%s subject=%s",
        user_id,
        subject,
        extra={"user_id": user_id, "subject": subject},
    )
    user = db.query(User).filter(User.id == user_id).first()
    recipient = _get_user_email(user) if user else None
    if not recipient:
        return
    _get_executor().submit(_run_send, user_id, recipient, subject, message)
