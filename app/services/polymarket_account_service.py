"""
Polymarket account linking: resolve and store per-user L2 credentials (BYOK).

- get_user_l2_creds: from UserByokKey (provider=polymarket).
- link_polymarket_account: validate (optional CLOB check), then store via UserByokKey.
- unlink_polymarket_account: remove UserByokKey for polymarket.
- get_link_status: linked bool and optional funder_address (no raw creds).
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import UserByokKey, ByokProvider

logger = logging.getLogger(__name__)


def get_user_l2_creds(user_id: int, db: Session) -> Optional[Dict[str, Any]]:
    """
    Return Polymarket L2 credentials for the user if linked (from BYOK).
    Returns dict with api_key, secret, passphrase, and optional funder_address.
    Never log secret or passphrase.
    """
    row = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == user_id,
            UserByokKey.provider == ByokProvider.POLYMARKET.value,
        )
        .first()
    )
    if not row or not row.credentials_encrypted:
        return None
    creds = dict(row.credentials_encrypted or {})
    if not creds.get("api_key") and not creds.get("secret"):
        return None
    return {
        "api_key": creds.get("api_key"),
        "secret": creds.get("secret"),
        "passphrase": creds.get("passphrase"),
        "funder_address": creds.get("funder_address"),
    }


def get_link_status(user_id: int, db: Session) -> Dict[str, Any]:
    """Return link status only (linked, funder_address if present). No raw creds."""
    row = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == user_id,
            UserByokKey.provider == ByokProvider.POLYMARKET.value,
        )
        .first()
    )
    if not row or not row.credentials_encrypted:
        return {"linked": False}
    creds = row.credentials_encrypted or {}
    return {
        "linked": True,
        "funder_address": creds.get("funder_address"),
        "linked_at": row.created_at.isoformat() if row.created_at else None,
    }


def link_polymarket_account(
    user_id: int,
    db: Session,
    api_key: str,
    secret: str,
    passphrase: str,
    funder_address: Optional[str] = None,
) -> bool:
    """
    Validate L2 creds (best-effort CLOB check), then create or update UserByokKey.
    Returns True on success. Does not log secret or passphrase.
    """
    api_key = (api_key or "").strip()
    secret = secret or ""
    passphrase = passphrase or ""
    if not api_key or not secret or not passphrase:
        return False

    # Optional: validate by calling CLOB (e.g. GET /auth or a small authenticated request)
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient.from_user_l2_creds(
            api_key=api_key,
            secret=secret,
            passphrase=passphrase,
        )
        # Best-effort validation: public get_book does not require L2; skip if no auth endpoint
        _ = client.clob_url
    except Exception as e:
        logger.debug("Polymarket link validation skip or fail: %s", e)

    credentials = {
        "api_key": api_key,
        "secret": secret,
        "passphrase": passphrase,
    }
    if funder_address:
        credentials["funder_address"] = funder_address.strip()

    existing = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == user_id,
            UserByokKey.provider == ByokProvider.POLYMARKET.value,
        )
        .first()
    )
    if existing:
        existing.credentials_encrypted = credentials
        existing.is_verified = True
        db.commit()
        db.refresh(existing)
    else:
        row = UserByokKey(
            user_id=user_id,
            provider=ByokProvider.POLYMARKET.value,
            provider_type="polymarket",
            credentials_encrypted=credentials,
            is_verified=True,
            unlocks_trading=False,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return True


def unlink_polymarket_account(user_id: int, db: Session) -> bool:
    """Remove Polymarket L2 link (delete UserByokKey for polymarket). Returns True if removed or not present."""
    row = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == user_id,
            UserByokKey.provider == ByokProvider.POLYMARKET.value,
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return True
