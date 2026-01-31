"""
Polymarket API Client for external market integration.

Uses Polymarket Gamma API (events, markets) and CLOB (order book, orders)
per https://docs.polymarket.com. Optionally registers SFP/securitized product
markets when POLYMARKET_PUBLISH_EXTERNAL is enabled.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# CLOB: https://clob.polymarket.com — order book, orders, trades
# Gamma: https://gamma-api.polymarket.com — events, markets (GET); create not in public API


class PolymarketAPIClient:
    """Client for Polymarket Gamma (discovery) and CLOB (trading) APIs.

    Default constructor uses server POLYMARKET_API_KEY (Gamma, Data API, surveillance).
    Use from_user_l2_creds() to build a client with user BYOK L2 credentials for
    placing CLOB orders on behalf of that user.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> None:
        self.clob_url = (
            getattr(settings, "POLYMARKET_API_URL", None)
            or "https://clob.polymarket.com"
        )
        self.gamma_url = (
            getattr(settings, "POLYMARKET_GAMMA_API_URL", None)
            or "https://gamma-api.polymarket.com"
        )
        self.data_url = (
            getattr(settings, "POLYMARKET_DATA_API_URL", None)
            or "https://data-api.polymarket.com"
        )
        self.network = getattr(settings, "POLYMARKET_NETWORK", "polygon")
        if api_key is not None:
            self._api_key = api_key
            self._secret = secret
            self._passphrase = passphrase
        else:
            _key = getattr(settings, "POLYMARKET_API_KEY", None)
            self._api_key = _key.get_secret_value() if hasattr(_key, "get_secret_value") else _key
            self._secret = None
            self._passphrase = None

    @classmethod
    def from_user_l2_creds(
        cls,
        api_key: str,
        secret: str,
        passphrase: str,
    ) -> "PolymarketAPIClient":
        """Build a client with user BYOK L2 credentials for CLOB order placement."""
        return cls(api_key=api_key, secret=secret, passphrase=passphrase)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
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
        """GET /events. List events with filters."""
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/events",
                    params={"active": str(active).lower(), "closed": str(closed).lower(), "limit": limit, "offset": offset},
                    headers=self._headers(),
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
        """GET /markets. List markets with optional tag filter."""
        try:
            params: Dict[str, Any] = {"active": str(active).lower(), "limit": limit, "offset": offset}
            if tag:
                params["tag"] = tag
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/markets",
                    params=params,
                    headers=self._headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else []
        except Exception as e:
            logger.warning("Polymarket fetch_markets failed: %s", e)
            return []

    def fetch_market_by_id(self, condition_id_or_slug: str) -> Optional[Dict[str, Any]]:
        """GET /markets/{condition_id} or by slug."""
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{self.gamma_url}/markets/{condition_id_or_slug}",
                    headers=self._headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else None
        except Exception as e:
            logger.warning("Polymarket fetch_market_by_id failed: %s", e)
            return None

    # --- CLOB: order book ---

    def get_book(self, token_id: str) -> Dict[str, Any]:
        """GET CLOB /book for outcome token_id."""
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{self.clob_url}/book",
                    params={"token_id": token_id},
                    headers=self._headers(),
                    timeout=10.0,
                )
            return r.json() if r.is_success else {}
        except Exception as e:
            logger.warning("Polymarket get_book failed: %s", e)
            return {}

    def _data_path(self, subpath: str) -> str:
        """Build Data API URL for a subpath. Override if production paths differ."""
        base = (self.data_url or "").rstrip("/")
        return f"{base}/{subpath.lstrip('/')}" if base else ""

    # --- Data API: trades, activity, holders, leaderboard, volume, open-interest ---
    # When data_url is unset or the request fails, returns empty/default and logs debug.

    def fetch_trades(
        self,
        *,
        market: Optional[str] = None,
        asset_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """GET /trades with optional market or asset_id. Returns list of trade dicts."""
        url = self._data_path("trades")
        if not url:
            logger.debug("Polymarket Data API: data_url unset, fetch_trades returns []")
            return []
        try:
            params: Dict[str, Any] = {"limit": limit}
            if market:
                params["market"] = market
            if asset_id:
                params["asset_id"] = asset_id
            with httpx.Client() as client:
                r = client.get(url, params=params, headers=self._headers(), timeout=15.0)
            return r.json() if r.is_success else []
        except Exception as e:
            logger.debug("Polymarket fetch_trades failed: %s", e)
            return []

    def fetch_activity(
        self,
        *,
        user: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """GET /activity with optional user or market filter."""
        url = self._data_path("activity")
        if not url:
            logger.debug("Polymarket Data API: data_url unset, fetch_activity returns []")
            return []
        try:
            params: Dict[str, Any] = {"limit": limit}
            if user:
                params["user"] = user
            if market:
                params["market"] = market
            with httpx.Client() as client:
                r = client.get(url, params=params, headers=self._headers(), timeout=15.0)
            return r.json() if r.is_success else []
        except Exception as e:
            logger.debug("Polymarket fetch_activity failed: %s", e)
            return []

    def fetch_holders(
        self,
        token_id: str,
        *,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """GET /holders for token_id (or CLOB/Subgraph-derived)."""
        url = self._data_path("holders")
        if not url:
            logger.debug("Polymarket Data API: data_url unset, fetch_holders returns []")
            return []
        try:
            with httpx.Client() as client:
                r = client.get(
                    url,
                    params={"token_id": token_id, "limit": limit},
                    headers=self._headers(),
                    timeout=15.0,
                )
            return r.json() if r.is_success else []
        except Exception as e:
            logger.debug("Polymarket fetch_holders failed: %s", e)
            return []

    def fetch_leaderboard(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        """GET /leaderboard or /analytics/leaderboard."""
        for subpath in ("leaderboard", "analytics/leaderboard"):
            url = self._data_path(subpath)
            if not url:
                continue
            try:
                with httpx.Client() as client:
                    r = client.get(
                        url,
                        params={"limit": limit},
                        headers=self._headers(),
                        timeout=15.0,
                    )
                if r.is_success:
                    data = r.json()
                    return data if isinstance(data, list) else []
            except Exception as e:
                logger.debug("Polymarket fetch_leaderboard %s failed: %s", subpath, e)
        logger.debug("Polymarket Data API: fetch_leaderboard returns []")
        return []

    def fetch_live_volume(self, market: Optional[str] = None) -> Dict[str, Any]:
        """GET /markets/{id}/volume or aggregated. Returns { volume, market }."""
        if market:
            url = self._data_path(f"markets/{market}/volume")
        else:
            url = self._data_path("volume")
        if not url:
            logger.debug("Polymarket Data API: data_url unset, fetch_live_volume returns {}")
            return {}
        try:
            with httpx.Client() as client:
                r = client.get(url, headers=self._headers(), timeout=15.0)
            if r.is_success:
                data = r.json()
                data = data if isinstance(data, dict) else {}
                return {"volume": data.get("volume", 0), "market": market or data.get("market")}
            return {}
        except Exception as e:
            logger.debug("Polymarket fetch_live_volume failed: %s", e)
            return {}

    def fetch_open_interest(self, market: Optional[str] = None) -> Dict[str, Any]:
        """GET /markets/{id}/open-interest or derived. Returns dict with open_interest, market."""
        if market:
            url = self._data_path(f"markets/{market}/open-interest")
        else:
            url = self._data_path("open-interest")
        if not url:
            logger.debug("Polymarket Data API: data_url unset, fetch_open_interest returns {}")
            return {}
        try:
            with httpx.Client() as client:
                r = client.get(url, headers=self._headers(), timeout=15.0)
            if r.is_success:
                data = r.json()
                data = data if isinstance(data, dict) else {}
                return {"open_interest": data.get("open_interest", 0), "market": market or data.get("market")}
            return {}
        except Exception as e:
            logger.debug("Polymarket fetch_open_interest failed: %s", e)
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
            # Gamma: POST /markets not in public API; try and handle
            with httpx.Client() as client:
                r = client.post(
                    f"{self.gamma_url}/markets",
                    json=body,
                    headers=self._headers(),
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
