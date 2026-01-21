"""
Polymarket API Client for external market integration.

Uses Polymarket Gamma API (events, markets) and CLOB (order book, orders)
per https://docs.polymarket.com. Optionally registers SFP/securitized product
markets when POLYMARKET_PUBLISH_EXTERNAL is enabled.

CLOB L2 auth (when POLYMARKET_API_KEY, POLYMARKET_SECRET, POLYMARKET_PASSPHRASE,
POLYMARKET_SIGNER_ADDRESS are set): HMAC-SHA256 per
https://docs.polymarket.com/developers/CLOB/authentication — POLY_ADDRESS,
POLY_API_KEY, POLY_PASSPHRASE, POLY_TIMESTAMP, POLY_SIGNATURE. Credentials can
come from the Builder account or createOrDeriveApiKey.
"""

import hmac
import hashlib
import logging
import time
from urllib.parse import urlencode

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# CLOB: https://clob.polymarket.com — order book, orders, trades; L2 = POLY_* headers
# Gamma: https://gamma-api.polymarket.com — events, markets (GET); public, no L2


def _get_secret_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    return val.get_secret_value() if hasattr(val, "get_secret_value") else (str(val) if val else None)


class PolymarketAPIClient:
    """Client for Polymarket Gamma (discovery) and CLOB (trading) APIs."""

    def __init__(self) -> None:
        self.clob_url = (
            getattr(settings, "POLYMARKET_API_URL", None)
            or "https://clob.polymarket.com"
        )
        self.gamma_url = (
            getattr(settings, "POLYMARKET_GAMMA_API_URL", None)
            or "https://gamma-api.polymarket.com"
        )
        self._api_key = _get_secret_str(getattr(settings, "POLYMARKET_API_KEY", None))
        self._secret = _get_secret_str(getattr(settings, "POLYMARKET_SECRET", None))
        self._passphrase = _get_secret_str(getattr(settings, "POLYMARKET_PASSPHRASE", None))
        self._signer_address = getattr(settings, "POLYMARKET_SIGNER_ADDRESS", None) or None
        self.network = getattr(settings, "POLYMARKET_NETWORK", "polygon")

    def _gamma_headers(self) -> Dict[str, str]:
        """Gamma is read-only and public; no L2 auth."""
        return {"Content-Type": "application/json"}

    def _clob_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        CLOB L2: POLY_ADDRESS, POLY_API_KEY, POLY_PASSPHRASE, POLY_TIMESTAMP, POLY_SIGNATURE.
        Message for HMAC-SHA256: timestamp + method + path + body. Hex-encoded.
        """
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if not all([self._api_key, self._secret, self._passphrase, self._signer_address]):
            return h
        ts = int(time.time())
        message = str(ts) + method.upper() + path + (body or "")
        sig = hmac.new(
            self._secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        h["POLY_ADDRESS"] = self._signer_address
        h["POLY_API_KEY"] = self._api_key
        h["POLY_PASSPHRASE"] = self._passphrase
        h["POLY_TIMESTAMP"] = str(ts)
        h["POLY_SIGNATURE"] = sig
        return h

    # --- Gamma: events & markets (GET) ---

    def fetch_events(
        self,
        *,
        active: bool = True,
        closed: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """GET /events. List events with filters. Gamma is public; no L2."""
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/events",
                    params={"active": str(active).lower(), "closed": str(closed).lower(), "limit": limit, "offset": offset},
                    headers=self._gamma_headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else []
        except Exception as e:
            logger.warning("Polymarket fetch_events failed: %s", e)
            return []

    def fetch_markets(
        self,
        *,
        tag: Optional[str] = None,
        active: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """GET /markets. List markets with optional tag filter. Gamma is public."""
        try:
            params: Dict[str, Any] = {"active": str(active).lower(), "limit": limit, "offset": offset}
            if tag:
                params["tag"] = tag
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/markets",
                    params=params,
                    headers=self._gamma_headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else []
        except Exception as e:
            logger.warning("Polymarket fetch_markets failed: %s", e)
            return []

    def fetch_market_by_id(self, condition_id_or_slug: str) -> Optional[Dict[str, Any]]:
        """GET /markets/{condition_id} or by slug. Gamma is public."""
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/markets/{condition_id_or_slug}",
                    headers=self._gamma_headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else None
        except Exception as e:
            logger.warning("Polymarket fetch_market_by_id failed: %s", e)
            return None

    # --- CLOB: order book (uses L2 when api_key+secret+passphrase+signer_address) ---

    def get_book(self, token_id: str) -> Dict[str, Any]:
        """GET CLOB /book for outcome token_id. L2 POLY_* headers when configured."""
        try:
            path = "/book" + ("?" + urlencode({"token_id": token_id}) if token_id else "")
            with httpx.Client() as client:
                r = client.get(
                    f"{self.clob_url}/book",
                    params={"token_id": token_id},
                    headers=self._clob_headers("GET", path, ""),
                    timeout=10.0,
                )
            return r.json() if r.is_success else {}
        except Exception as e:
            logger.warning("Polymarket get_book failed: %s", e)
            return {}

    # --- Optional: register SFP / securitized product market ---
    # Gamma does not expose public POST /markets; we try and handle 404/405.
    # For CTF-based creation, use on-chain prepareCondition + partner/relayer.

    def register_sfp_market(
        self,
        question: str,
        description: str,
        outcomes: List[str],
        sfp_id: str,
        merkle_root: str,
        deal_id: int,
        resolution_condition: Dict[str, Any],
        *,
        end_date_iso: Optional[str] = None,
        liquidity_pool_address: Optional[str] = None,
        condition_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attempt to register an SFP/securitized product market with Polymarket.
        When POLYMARKET_PUBLISH_EXTERNAL is False or Gamma does not support
        programmatic create, returns success=False with reason.

        Returns:
            { "success": bool, "external_id": str|None, "reason": str, "message": str }
        """
        if not getattr(settings, "POLYMARKET_PUBLISH_EXTERNAL", False):
            return {
                "success": False,
                "external_id": None,
                "reason": "publish_disabled",
                "message": "POLYMARKET_PUBLISH_EXTERNAL is false",
            }

        body: Dict[str, Any] = {
            "question": question,
            "description": description or question,
            "outcomes": outcomes if outcomes else ["Yes", "No"],
            "resolution_source": "CREDITNEXUS_SFP",
            "sfp_id": sfp_id,
            "merkle_root": merkle_root,
            "deal_id": deal_id,
            "resolution_condition": resolution_condition,
        }
        if end_date_iso:
            body["end_date_iso"] = end_date_iso
        if liquidity_pool_address:
            body["liquidity_pool_address"] = liquidity_pool_address
        if condition_id:
            body["condition_id"] = condition_id

        try:
            # Gamma: POST /markets not in public API; try and handle. Gamma is public; no L2.
            with httpx.Client() as client:
                r = client.post(
                    f"{self.gamma_url}/markets",
                    json=body,
                    headers=self._gamma_headers(),
                    timeout=15.0,
                )
            if r.status_code in (404, 405, 501):
                return {
                    "success": False,
                    "external_id": None,
                    "reason": "create_not_supported",
                    "message": "Polymarket Gamma does not support programmatic market creation; use CTF or partner channel.",
                }
            if r.is_success:
                data = r.json() if r.text else {}
                return {
                    "success": True,
                    "external_id": data.get("id") or data.get("condition_id") or data.get("slug"),
                    "reason": "created",
                    "message": "Market registered with Polymarket Gamma",
                }
            return {
                "success": False,
                "external_id": None,
                "reason": "api_error",
                "message": f"Gamma returned {r.status_code}: {r.text[:200] if r.text else ''}",
            }
        except Exception as e:
            logger.warning("Polymarket register_sfp_market failed: %s", e)
            return {
                "success": False,
                "external_id": None,
                "reason": "request_failed",
                "message": str(e),
            }
