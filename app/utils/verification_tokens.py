"""Verification token generation and validation utilities."""

import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_verification_token() -> Tuple[str, str]:
    """Generate a secure verification token.

    Returns:
        Tuple of (token, verification_id)
    """
    verification_id = str(secrets.token_urlsafe(16))

    # Create HMAC signature
    hmac_key = (
        settings.OPENAI_API_KEY.get_secret_value()
        if hasattr(settings, "OPENAI_API_KEY")
        else secrets.token_hex(32)
    )
    timestamp = datetime.utcnow().isoformat()

    signature = hmac.new(
        hmac_key.encode(), f"{verification_id}:{timestamp}".encode(), hashlib.sha256
    ).hexdigest()

    # Token format: verification_id:timestamp:signature
    token = f"{verification_id}:{timestamp}:{signature}"

    return token, verification_id


def validate_verification_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a verification token.

    Args:
        token: Verification token to validate

    Returns:
        Tuple of (is_valid, verification_id, error_message)
    """
    try:
        parts = token.split(":")

        if len(parts) != 3:
            return False, None, "Invalid token format"

        verification_id, timestamp_str, signature = parts

        # Verify timestamp format
        try:
            token_time = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return False, None, "Invalid timestamp"

        # Check expiration
        expires_at = token_time + timedelta(hours=settings.VERIFICATION_LINK_EXPIRY_HOURS)
        if datetime.utcnow() > expires_at:
            return False, None, "Verification link has expired"

        # Verify HMAC signature
        hmac_key = (
            settings.OPENAI_API_KEY.get_secret_value()
            if hasattr(settings, "OPENAI_API_KEY")
            else secrets.token_hex(32)
        )
        expected_signature = hmac.new(
            hmac_key.encode(), f"{verification_id}:{timestamp_str}".encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return False, None, "Invalid token signature"

        return True, verification_id, None

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return False, None, "Token validation failed"


def is_token_expired(token: str) -> bool:
    """Check if a verification token has expired.

    Args:
        token: Verification token

    Returns:
        True if expired, False otherwise
    """
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return True

        _, timestamp_str, _ = parts
        token_time = datetime.fromisoformat(timestamp_str)
        expires_at = token_time + timedelta(hours=settings.VERIFICATION_LINK_EXPIRY_HOURS)

        return datetime.utcnow() > expires_at

    except Exception:
        return True


def generate_verification_link(token: str) -> str:
    """Generate a full verification link from token.

    Args:
        token: Verification token

    Returns:
        Full verification URL
    """
    base_url = settings.VERIFICATION_BASE_URL or "http://localhost:5173"
    return f"{base_url.rstrip('/')}/verify/{token}"


def extract_verification_id(token: str) -> Optional[str]:
    """Extract verification_id from token without validation.

    Args:
        token: Verification token

    Returns:
        Verification ID or None
    """
    try:
        return token.split(":")[0]
    except (IndexError, AttributeError):
        return None


def generate_one_time_token(expires_in_minutes: int = 30) -> str:
    """Generate a one-time use token for single-step verification.

    Args:
        expires_in_minutes: Token expiration time in minutes

    Returns:
        One-time token
    """
    timestamp = datetime.utcnow().isoformat()
    random_part = secrets.token_urlsafe(16)

    token = f"OT:{timestamp}:{random_part}"
    return token


def validate_one_time_token(token: str, max_age_minutes: int = 30) -> Tuple[bool, Optional[str]]:
    """Validate a one-time token.

    Args:
        token: One-time token
        max_age_minutes: Maximum age in minutes

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not token.startswith("OT:"):
            return False, "Invalid one-time token format"

        parts = token[3:].split(":")

        if len(parts) != 2:
            return False, "Invalid one-time token format"

        timestamp_str, random_part = parts

        # Verify timestamp
        try:
            token_time = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return False, "Invalid timestamp"

        # Check age
        max_age = timedelta(minutes=max_age_minutes)
        if datetime.utcnow() - token_time > max_age:
            return False, "Token has expired"

        return True, None

    except Exception as e:
        logger.error(f"One-time token validation error: {e}")
        return False, "Token validation failed"
