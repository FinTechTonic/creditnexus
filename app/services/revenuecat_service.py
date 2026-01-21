"""
RevenueCat service for subscription and entitlement checks.

Integrates with x402: after a SUBSCRIPTION_UPGRADE payment via x402, can grant
a promotional entitlement; before gating Polymarket/premium features, can check
has_entitlement. Uses RevenueCat REST API v1.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

REVENUECAT_BASE = "https://api.revenuecat.com/v1"


class RevenueCatService:
    """Service for RevenueCat subscriber and entitlement operations."""

    def __init__(self) -> None:
        self.enabled = getattr(settings, "REVENUECAT_ENABLED", False)
        _key = getattr(settings, "REVENUECAT_API_KEY", None)
        self._api_key = (
            _key.get_secret_value() if hasattr(_key, "get_secret_value") else _key
        )
        self.entitlement_pro = getattr(settings, "REVENUECAT_ENTITLEMENT_PRO", "pro")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def get_subscriber(self, app_user_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /v1/subscribers/{app_user_id}. Returns subscriber info including
        entitlements, subscriptions. 200 = exists, 201 = created by request.
        """
        if not self.enabled or not self._api_key:
            return None
        try:
            with httpx.Client() as client:
                r = client.get(
                    f"{REVENUECAT_BASE}/subscribers/{app_user_id}",
                    headers=self._headers(),
                    timeout=10.0,
                )
            if r.is_success:
                return r.json()
            logger.warning("RevenueCat get_subscriber %s: %s", r.status_code, r.text[:200])
            return None
        except Exception as e:
            logger.warning("RevenueCat get_subscriber failed: %s", e)
            return None

    def has_entitlement(
        self,
        app_user_id: str,
        entitlement_id: Optional[str] = None,
    ) -> bool:
        """
        True if the subscriber has an active entitlement. Uses expires_date
        vs current time; null expires_date is treated as lifetime.
        """
        ent = entitlement_id or self.entitlement_pro
        data = self.get_subscriber(app_user_id)
        if not data:
            return False
        subs = data.get("subscriber", {}) or {}
        ents = subs.get("entitlements") or {}
        info = ents.get(ent)
        if not info:
            return False
        from datetime import datetime, timezone

        exp = info.get("expires_date")
        if exp is None:
            return True
        try:
            # RevenueCat uses ISO dates; parse and compare to now
            if isinstance(exp, str) and exp.endswith("Z"):
                exp = exp.replace("Z", "+00:00")
            end = datetime.fromisoformat(exp) if isinstance(exp, str) else None
            if end and end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            return end is not None and end > datetime.now(timezone.utc)
        except Exception:
            return False

    def grant_promotional_entitlement(
        self,
        app_user_id: str,
        entitlement_id: Optional[str] = None,
        *,
        duration: str = "P1M",
        end_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        POST /v1/subscribers/{app_user_id}/entitlements/{entitlement_identifier}/promotional
        Grant entitlement (e.g. after x402 SUBSCRIPTION_UPGRADE). duration e.g. P1M, P1Y;
        or use end_time_ms. Returns { "success": bool, "reason": str }.
        """
        ent = entitlement_id or self.entitlement_pro
        if not self.enabled or not self._api_key:
            return {"success": False, "reason": "revenuecat_disabled"}

        body: Dict[str, Any] = {}
        if end_time_ms is not None:
            body["end_time_ms"] = end_time_ms
        else:
            body["duration"] = duration

        try:
            with httpx.Client() as client:
                r = client.post(
                    f"{REVENUECAT_BASE}/subscribers/{app_user_id}/entitlements/{ent}/promotional",
                    json=body,
                    headers=self._headers(),
                    timeout=10.0,
                )
            if r.is_success:
                return {"success": True, "reason": "granted", "data": r.json() if r.text else {}}
            return {
                "success": False,
                "reason": "api_error",
                "message": f"{r.status_code}: {r.text[:200] if r.text else ''}",
            }
        except Exception as e:
            logger.warning("RevenueCat grant_promotional_entitlement failed: %s", e)
            return {"success": False, "reason": "request_failed", "message": str(e)}
