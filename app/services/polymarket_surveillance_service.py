"""Polymarket surveillance: baselines, alerts, and detection cycle.

Uses Polymarket Data API (trades, activity, holders, leaderboard, volume, open-interest)
to compute baselines and create alerts for insider-like decision support.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PolymarketSurveillanceAlert, PolymarketSurveillanceBaseline

logger = logging.getLogger(__name__)


class PolymarketSurveillanceService:
    """Service for Polymarket surveillance baselines, alerts, and detection cycles."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from app.services.polymarket_api_client import PolymarketAPIClient

            self._client = PolymarketAPIClient()
        return self._client

    def upsert_baseline(
        self,
        entity_type: str,
        entity_id: str,
        window: str,
        metric: str,
        value: Any,
    ) -> PolymarketSurveillanceBaseline:
        """Insert or update a baseline row. Unique on (entity_type, entity_id, window, metric)."""
        row = (
            self.db.query(PolymarketSurveillanceBaseline)
            .filter(
                PolymarketSurveillanceBaseline.entity_type == entity_type,
                PolymarketSurveillanceBaseline.entity_id == entity_id,
                PolymarketSurveillanceBaseline.window == window,
                PolymarketSurveillanceBaseline.metric == metric,
            )
            .first()
        )
        if row:
            row.value = value
            row.computed_at = datetime.utcnow()
        else:
            row = PolymarketSurveillanceBaseline(
                entity_type=entity_type,
                entity_id=entity_id,
                window=window,
                metric=metric,
                value=value,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        *,
        condition_id: Optional[str] = None,
        proxy_wallet: Optional[str] = None,
        event_id: Optional[str] = None,
        signal_values: Optional[Dict[str, Any]] = None,
    ) -> PolymarketSurveillanceAlert:
        """Create a surveillance alert."""
        a = PolymarketSurveillanceAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            condition_id=condition_id,
            proxy_wallet=proxy_wallet,
            event_id=event_id,
            signal_values=signal_values,
        )
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def get_wallet_first_activity_ts(self, wallet: str) -> Optional[datetime]:
        """Return first_seen_ts from baselines for entity_type=wallet, entity_id=wallet, metric=first_seen_ts."""
        row = (
            self.db.query(PolymarketSurveillanceBaseline)
            .filter(
                PolymarketSurveillanceBaseline.entity_type == "wallet",
                PolymarketSurveillanceBaseline.entity_id == wallet,
                PolymarketSurveillanceBaseline.metric == "first_seen_ts",
            )
            .order_by(PolymarketSurveillanceBaseline.computed_at.desc())
            .first()
        )
        if not row or not row.value:
            return None
        v = row.value
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            return datetime.utcfromtimestamp(float(v))
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    def list_alerts(
        self,
        *,
        severity: Optional[str] = None,
        reviewed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List alerts with optional severity and reviewed filters. Ordered by created_at desc."""
        q = self.db.query(PolymarketSurveillanceAlert)
        if severity:
            q = q.filter(PolymarketSurveillanceAlert.severity == severity)
        if reviewed is not None:
            if reviewed:
                q = q.filter(PolymarketSurveillanceAlert.reviewed_at.isnot(None))
            else:
                q = q.filter(PolymarketSurveillanceAlert.reviewed_at.is_(None))
        rows = q.order_by(PolymarketSurveillanceAlert.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": r.id,
                "alert_type": r.alert_type,
                "severity": r.severity,
                "condition_id": r.condition_id,
                "proxy_wallet": r.proxy_wallet,
                "message": r.message,
                "signal_values": r.signal_values,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "resolution": r.resolution,
            }
            for r in rows
        ]

    def review_alert(self, alert_id: int, resolution: str, reviewed_by: int) -> PolymarketSurveillanceAlert:
        """Set reviewed_at, reviewed_by, resolution for an alert."""
        a = self.db.query(PolymarketSurveillanceAlert).filter(PolymarketSurveillanceAlert.id == alert_id).first()
        if not a:
            raise ValueError(f"Alert {alert_id} not found")
        a.reviewed_at = datetime.utcnow()
        a.reviewed_by = reviewed_by
        a.resolution = resolution
        self.db.commit()
        self.db.refresh(a)
        return a

    def _wallet_from_item(self, d: Dict[str, Any]) -> Optional[str]:
        """Extract wallet/address from a trade or activity item (various API field names)."""
        if not d or not isinstance(d, dict):
            return None
        w = (
            d.get("maker") or d.get("taker") or d.get("user") or d.get("wallet")
            or d.get("owner") or d.get("trader") or d.get("address")
            or d.get("from") or d.get("to")
        )
        if isinstance(w, str) and w.strip():
            return w.strip()
        return None

    def run_detection_cycle(self, markets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run a detection cycle: fetch Data API, update baselines, create alerts when thresholds exceeded.
        If POLYMARKET_SURVEILLANCE_ENABLED is False, returns {"skipped": True}.
        Fetches each endpoint in isolation so 400/404 on one does not break the cycle.
        """
        if not getattr(settings, "POLYMARKET_SURVEILLANCE_ENABLED", False):
            return {"skipped": True, "reason": "POLYMARKET_SURVEILLANCE_ENABLED is False"}

        baselines_updated = 0
        alerts_created = 0
        trades: List[Dict[str, Any]] = []
        activity: List[Dict[str, Any]] = []
        vol: Dict[str, Any] = {}
        oi: Dict[str, Any] = {}

        try:
            trades = self.client.fetch_trades(limit=200)
        except Exception as e:
            logger.debug("Polymarket fetch_trades failed: %s", e)
        if not isinstance(trades, list):
            trades = []

        try:
            activity = self.client.fetch_activity(limit=200)
        except Exception as e:
            logger.debug("Polymarket fetch_activity failed: %s", e)
        if not isinstance(activity, list):
            activity = []

        try:
            vol = self.client.fetch_live_volume(market=markets[0] if markets else None) or {}
        except Exception as e:
            logger.debug("Polymarket fetch_live_volume failed: %s", e)
        if not isinstance(vol, dict):
            vol = {}

        try:
            oi = self.client.fetch_open_interest(market=markets[0] if markets else None) or {}
        except Exception as e:
            logger.debug("Polymarket fetch_open_interest failed: %s", e)
        if not isinstance(oi, dict):
            oi = {}

        try:
            # Aggregations: trade count per wallet (from trades or activity)
            wallet_trade_count: Dict[str, int] = {}
            for t in trades:
                w = self._wallet_from_item(t)
                if w:
                    wallet_trade_count[w] = wallet_trade_count.get(w, 0) + 1
            for a in activity:
                w = self._wallet_from_item(a)
                if w:
                    wallet_trade_count[w] = wallet_trade_count.get(w, 0) + 1

            # Upsert baselines: trade_count per wallet (window=1d)
            for w, cnt in wallet_trade_count.items():
                self.upsert_baseline("wallet", w, "1d", "trade_count", cnt)
                baselines_updated += 1

            # Volume baseline
            v = vol.get("volume") if isinstance(vol, dict) else None
            mk = vol.get("market") or "global"
            if v is not None:
                self.upsert_baseline("market", str(mk), "1d", "volume", v)
                baselines_updated += 1

            # Open interest baseline
            o = oi.get("open_interest") if isinstance(oi, dict) else None
            mk_oi = oi.get("market") or "global"
            if o is not None:
                self.upsert_baseline("market", str(mk_oi), "1d", "open_interest", o)
                baselines_updated += 1

            # Threshold alert: wallet with >= 5 trades in this batch (lowered so alerts appear with sparse data)
            for w, cnt in wallet_trade_count.items():
                if cnt >= 5:
                    self.create_alert(
                        "outsized_bet",
                        "low",
                        f"Wallet {w[:10]}... has {cnt} trades in cycle (threshold 5)",
                        proxy_wallet=w,
                        signal_values={"trade_count": cnt, "threshold": 5},
                    )
                    alerts_created += 1
                    break  # one per cycle to avoid flood

            # If we got trades but no threshold alert, create one informational so the panel shows activity
            if alerts_created == 0 and (len(trades) > 0 or len(wallet_trade_count) > 0):
                n_trades = len(trades)
                n_wallets = len(wallet_trade_count)
                self.create_alert(
                    "cycle_completed",
                    "low",
                    f"Detection cycle completed; {n_trades} trades, {n_wallets} wallets. No threshold exceeded.",
                    signal_values={"trades_count": n_trades, "wallets_count": n_wallets},
                )
                alerts_created += 1

        except Exception as e:
            logger.warning("Polymarket run_detection_cycle failed: %s", e)

        return {
            "skipped": False,
            "baselines_updated": baselines_updated,
            "alerts_created": alerts_created,
        }
