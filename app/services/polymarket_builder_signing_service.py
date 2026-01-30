"""
Polymarket builder signing: HMAC headers for order attribution and relayer auth.

Per Polymarket Order Attribution: POLY_BUILDER_API_KEY, POLY_BUILDER_TIMESTAMP,
POLY_BUILDER_PASSPHRASE, POLY_BUILDER_SIGNATURE (HMAC-SHA256 over timestamp+method+path+body).
Builder keys stay server-side; never expose secret to client.
"""

import hmac
import hashlib
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_builder_headers(method: str, path: str, body: str) -> Optional[Dict[str, str]]:
    """
    Build Polymarket builder attribution headers for a CLOB/relayer request.

    Returns dict with POLY_BUILDER_API_KEY, POLY_BUILDER_TIMESTAMP, POLY_BUILDER_PASSPHRASE,
    POLY_BUILDER_SIGNATURE. Returns None if builder creds are not configured.
    Do not log secret or passphrase.
    """
    api_key = getattr(settings, "POLY_BUILDER_API_KEY", None)
    secret = getattr(settings, "POLY_BUILDER_SECRET", None)
    passphrase = getattr(settings, "POLY_BUILDER_PASSPHRASE", None)
    if not api_key or not secret or not passphrase:
        logger.debug("Polymarket builder creds not set; skipping builder headers")
        return None
    try:
        api_key_str = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else str(api_key)
        secret_str = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
        passphrase_str = passphrase.get_secret_value() if hasattr(passphrase, "get_secret_value") else str(passphrase)
    except Exception:
        logger.debug("Polymarket builder creds unavailable")
        return None

    timestamp = str(int(time.time()))
    # Polymarket builder signature: HMAC-SHA256(secret, timestamp + method + path + body)
    message = f"{timestamp}{method}{path}{body}"
    signature = hmac.new(
        secret_str.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "POLY_BUILDER_API_KEY": api_key_str,
        "POLY_BUILDER_TIMESTAMP": timestamp,
        "POLY_BUILDER_PASSPHRASE": passphrase_str,
        "POLY_BUILDER_SIGNATURE": signature,
    }
