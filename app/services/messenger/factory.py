"""Messenger factory for creating configured messenger instances."""

import logging
from typing import Optional

from app.services.messenger.email import (
    MessengerInterface,
    EmailMessenger,
    SlackMessenger,
    TeamsMessenger,
    WhatsAppMessenger,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_messenger(
    provider: str = None, config: Optional[dict] = None
) -> Optional[MessengerInterface]:
    """Create configured messenger instance.

    Args:
        provider: Messenger provider (email, slack, teams, whatsapp)
                   If None, uses MESSENGER_PROVIDER from config
        config: Optional config dict (uses settings if not provided)

    Returns:
        MessengerInterface or None if provider not configured
    """
    if provider is None:
        provider = getattr(settings, "MESSENGER_PROVIDER", "email")

    provider = provider.lower()

    if provider == "email":
        smtp_host = (
            config.get("smtp_host")
            if config
            else getattr(settings, "MESSENGER_EMAIL_SMTP_HOST", None)
        )
        smtp_port = (
            config.get("smtp_port")
            if config
            else getattr(settings, "MESSENGER_EMAIL_SMTP_PORT", 587)
        )
        smtp_user = (
            config.get("smtp_user")
            if config
            else getattr(settings, "MESSENGER_EMAIL_SMTP_USER", None)
        )
        smtp_password = (
            config.get("smtp_password")
            if config
            else getattr(settings, "MESSENGER_EMAIL_SMTP_PASSWORD", None)
        )
        from_email = (
            config.get("from_email") if config else getattr(settings, "MESSENGER_EMAIL_FROM", None)
        )

        if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email]):
            logger.warning("Email messenger not configured: missing SMTP settings")
            return None

        messenger = EmailMessenger(smtp_host, smtp_port, smtp_user, smtp_password, from_email)

        is_valid, error = messenger.validate_config()
        if not is_valid:
            logger.error(f"Email messenger configuration invalid: {error}")
            return None

        return messenger

    elif provider == "slack":
        webhook_url = (
            config.get("webhook_url")
            if config
            else getattr(settings, "MESSENGER_SLACK_WEBHOOK_URL", None)
        )

        if not webhook_url:
            logger.warning("Slack messenger not configured: missing webhook URL")
            return None

        messenger = SlackMessenger(webhook_url)

        is_valid, error = messenger.validate_config()
        if not is_valid:
            logger.error(f"Slack messenger configuration invalid: {error}")
            return None

        return messenger

    elif provider == "teams":
        webhook_url = (
            config.get("webhook_url")
            if config
            else getattr(settings, "MESSENGER_TEAMS_WEBHOOK_URL", None)
        )

        if not webhook_url:
            logger.warning("Teams messenger not configured: missing webhook URL")
            return None

        messenger = TeamsMessenger(webhook_url)

        is_valid, error = messenger.validate_config()
        if not is_valid:
            logger.error(f"Teams messenger configuration invalid: {error}")
            return None

        return messenger

    elif provider == "whatsapp":
        account_sid = (
            config.get("account_sid") if config else getattr(settings, "TWILIO_ACCOUNT_SID", None)
        )
        auth_token = (
            config.get("auth_token") if config else getattr(settings, "TWILIO_AUTH_TOKEN", None)
        )
        from_number = (
            config.get("from_number") if config else getattr(settings, "TWILIO_PHONE_NUMBER", None)
        )

        if not all([account_sid, auth_token, from_number]):
            logger.warning("WhatsApp messenger not configured: missing Twilio settings")
            return None

        messenger = WhatsAppMessenger(account_sid, auth_token, from_number)

        is_valid, error = messenger.validate_config()
        if not is_valid:
            logger.error(f"WhatsApp messenger configuration invalid: {error}")
            return None

        return messenger

    else:
        logger.warning(f"Unknown messenger provider: {provider}")
        return None


def send_verification_link(
    messenger: MessengerInterface,
    recipient: str,
    verification_id: str,
    verification_link: str,
    deal_id: Optional[str] = None,
) -> bool:
    """Send verification link via configured messenger.

    Args:
        messenger: Messenger instance
        recipient: Recipient (email, phone, webhook, etc.)
        verification_id: Verification ID
        verification_link: Full verification URL
        deal_id: Optional deal ID

    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"Deal Verification Request"

    message = f"""You have been asked to verify a deal in CreditNexus.

Verification ID: {verification_id}"""

    if deal_id:
        message += f"\nDeal ID: {deal_id}"

    message += f"""
Please review the deal details and accept or decline the verification request.

This link will expire in 72 hours."""

    return await messenger.send_message(recipient, subject, message, verification_link)
