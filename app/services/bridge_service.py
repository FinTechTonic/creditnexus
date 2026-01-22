"""
BridgeService for Polymarket cross-chain transfers.

Calls POLYMARKET_BRIDGE_API_URL for:
- get_bridge_status(bridge_id): GET /bridge/status/{bridge_id} (or equivalent)
- submit_bridge(...): POST /bridge/submit

Exact request/response shapes depend on the bridge/relay; this implements
a reasonable default. CrossChainTransaction persistence is done by the API layer.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BridgeService:
    """Client for the Polymarket bridge / cross-chain relay API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url or getattr(settings, "POLYMARKET_BRIDGE_API_URL", None) or ""
        ).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    @property
    def is_available(self) -> bool:
        return bool(
            getattr(settings, "CROSS_CHAIN_ENABLED", False) and self.base_url
        )

    async def get_bridge_status(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /bridge/status/{bridge_id} (or equivalent).
        Returns bridge status from the external API or None if unavailable/error.
        """
        if not self.is_available:
            logger.debug(
                "BridgeService: CROSS_CHAIN_ENABLED or POLYMARKET_BRIDGE_API_URL not set"
            )
            return None
        try:
            client = self._ensure_client()
            url = f"{self.base_url}/bridge/status/{bridge_id}"
            r = await client.get(url, timeout=15.0)
            if r.status_code == 404:
                return {"status": "not_found", "bridge_id": bridge_id}
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            logger.warning("BridgeService get_bridge_status failed: %s", e)
            return None

    async def submit_bridge(
        self,
        *,
        source_chain_id: int,
        dest_chain_id: int,
        amount: str,
        token_address: str,
        sender_address: str,
        market_event_id: Optional[int] = None,
        outcome_token_id: Optional[str] = None,
        receiver_address: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        POST /bridge/submit to start a cross-chain transfer.
        Returns { "bridge_id": str, "status": str, ... } or raises.
        """
        if not self.is_available:
            raise RuntimeError(
                "BridgeService: CROSS_CHAIN_ENABLED or POLYMARKET_BRIDGE_API_URL not set"
            )
        payload: Dict[str, Any] = {
            "source_chain_id": source_chain_id,
            "dest_chain_id": dest_chain_id,
            "amount": amount,
            "token_address": token_address,
            "sender_address": sender_address,
        }
        if market_event_id is not None:
            payload["market_event_id"] = market_event_id
        if outcome_token_id is not None:
            payload["outcome_token_id"] = outcome_token_id
        if receiver_address is not None:
            payload["receiver_address"] = receiver_address
        if extra:
            payload["extra"] = extra

        try:
            client = self._ensure_client()
            r = await client.post(
                f"{self.base_url}/bridge/submit",
                json=payload,
                timeout=30.0,
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            logger.warning("BridgeService submit_bridge failed: %s", e)
            raise

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:  # pragma: no cover
                pass
            self._client = None
