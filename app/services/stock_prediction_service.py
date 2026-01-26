"""
Stock prediction service: daily, hourly, 15min predictions via Chronos (Modal) or technical strategy.

Uses MarketDataService, ChronosModelManager, StockPredictionCache, RollingCreditsService (optional).
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import StockPrediction, StockPredictionCache
from app.services.market_data_service import get_historical_data
from app.services.chronos_model_manager import ChronosModelManager
from app.stock_prediction_core.trading_strategies import get_trading_signals

logger = logging.getLogger(__name__)

try:
    from app.core.metrics import (
        stock_predictions_total,
        stock_prediction_duration_seconds,
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# timeframe (api) -> market_data_service timeframe
_TF_TO_MARKET = {"daily": "1D", "hourly": "1H", "15min": "15Min"}

# cache TTL in minutes by timeframe
_CACHE_TTL = {"daily": 60, "hourly": 15, "15min": 5}

# credit_type by timeframe for spend_credits
_CREDIT_TYPE = {"daily": "stock_prediction_daily", "hourly": "stock_prediction_hourly", "15min": "stock_prediction_15min"}


def _make_cache_key(symbol: str, timeframe: str, lookback: int, horizon: int, strategy: str, model_id: Optional[str] = None) -> str:
    raw = f"stock_pred:{symbol}:{timeframe}:{lookback}:{horizon}:{strategy}:{model_id or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


class StockPredictionService:
    def __init__(
        self,
        db: Session,
        *,
        chronos: Optional[ChronosModelManager] = None,
        rolling_credits: Optional[Any] = None,
    ) -> None:
        self.db = db
        self._chronos = chronos or ChronosModelManager()
        self._credits = rolling_credits

    def _tf_to_market(self, tf: str) -> str:
        return _TF_TO_MARKET.get(tf.lower(), "1D")

    def _fetch_range_days(self, timeframe: str, lookback_bars: int) -> int:
        if timeframe == "daily":
            return max(1, lookback_bars)
        if timeframe == "hourly":
            return max(1, (lookback_bars + 6) // 7)
        return max(1, (lookback_bars + 25) // 26)

    def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        row = (
            self.db.query(StockPredictionCache)
            .filter(StockPredictionCache.cache_key == cache_key, StockPredictionCache.expires_at > now)
            .first()
        )
        if not row or not row.result:
            return None
        return row.result if isinstance(row.result, dict) else {"forecast": row.result}

    def _set_cached(self, cache_key: str, result: Dict[str, Any], ttl_minutes: int) -> None:
        expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        existing = self.db.query(StockPredictionCache).filter(StockPredictionCache.cache_key == cache_key).first()
        if existing:
            existing.result = result
            existing.expires_at = expires
        else:
            self.db.add(StockPredictionCache(cache_key=cache_key, result=result, expires_at=expires))

    def _run_chronos(self, symbol: str, df, horizon: int, model_id: str) -> Dict[str, Any]:
        close = "Close" if "Close" in df.columns else "close"
        context = df[close].astype(float).dropna().tolist()
        if not context:
            return {"forecast": [], "model_id": model_id, "error": "no close prices"}
        return self._chronos.run_inference(symbol=symbol, context=context, horizon=horizon, model_id=model_id)

    def _run_technical(self, df, horizon: int) -> Dict[str, Any]:
        try:
            res = get_trading_signals(df, "combined")
            col = "Close" if "Close" in df.columns else "close"
            last = float(df[col].iloc[-1])
            extended = [last] * horizon
            return {
                "forecast": extended,
                "model_id": "technical",
                "signals": res,
            }
        except Exception as e:
            logger.warning("Technical signals failed: %s", e)
            return {"forecast": [], "model_id": "technical", "error": str(e)}

    def predict(
        self,
        symbol: str,
        timeframe: str,
        *,
        user_id: Optional[int] = None,
        lookback: Optional[int] = None,
        horizon: Optional[int] = None,
        strategy: str = "chronos",
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run prediction for symbol and timeframe (daily, hourly, 15min).
        strategy: chronos | technical. model_id: override for Chronos (e.g. amazon/chronos-t5-base).
        """
        start_time = time.time()
        tf = timeframe.lower()
        if tf not in _TF_TO_MARKET:
            return {"error": "invalid_timeframe", "timeframe": timeframe}

        if not getattr(settings, "STOCK_PREDICTION_ENABLED", False):
            if METRICS_AVAILABLE:
                stock_predictions_total.labels(timeframe=tf, status="error").inc()
            return {"error": "stock_prediction_disabled"}

        # defaults
        if tf == "daily":
            lb = lookback or getattr(settings, "STOCK_PREDICTION_DEFAULT_LOOKBACK_DAILY", 252)
            h = horizon or 30
        elif tf == "hourly":
            lb = lookback or getattr(settings, "STOCK_PREDICTION_DEFAULT_LOOKBACK_HOURLY", 504)
            h = horizon or 120
        else:
            lb = lookback or getattr(settings, "STOCK_PREDICTION_DEFAULT_LOOKBACK_15MIN", 96)
            h = horizon or 96

        mid = model_id or getattr(settings, "CHRONOS_MODEL_ID", None) or "amazon/chronos-t5-small"
        cache_key = _make_cache_key(symbol, tf, lb, h, strategy, mid if strategy == "chronos" else None)
        cached = self._get_cached(cache_key)
        if cached is not None:
            # Extract forecast array from cached result
            forecast_array = cached.get("forecast", [])
            if not isinstance(forecast_array, list):
                forecast_array = []
            return {
                "forecast": forecast_array,
                "cached": True,
                "model_id": cached.get("model_id", mid),
                "strategy": strategy,
                "symbol": symbol,
                "timeframe": tf,
                "error": cached.get("error"),
                "signal": cached.get("signal"),
            }

        # credits (skip if no user or no service)
        # For demo/development, allow predictions without credits if user has no balance
        credit_type = _CREDIT_TYPE.get(tf, "universal")
        if user_id and self._credits:
            spent = self._credits.spend_credits(
                user_id,
                credit_type,
                amount=1.0,
                feature="stock_prediction",
                description=f"Stock prediction {tf} {symbol}",
            )
            if not spent.get("ok"):
                # In development/demo mode, allow predictions even without credits
                # Check if this is a demo user or if credits are optional
                # Note: settings is already imported at module level, don't import again
                if not getattr(settings, "REQUIRE_CREDITS_FOR_PREDICTIONS", False):
                    logger.info(f"User {user_id} has insufficient credits for {credit_type}, but allowing prediction in demo mode")
                else:
                    if METRICS_AVAILABLE:
                        stock_predictions_total.labels(timeframe=tf, status="error").inc()
                    return {"error": "insufficient_credits", "reason": spent.get("reason", "insufficient_credits")}

        # fetch data
        market_tf = self._tf_to_market(tf)
        end = datetime.now(timezone.utc)
        days = self._fetch_range_days(tf, lb)
        start = end - timedelta(days=days)
        df = get_historical_data(symbol, start, end, timeframe=market_tf, db=self.db)
        if df is None or df.empty or len(df) < 2:
            if METRICS_AVAILABLE:
                stock_predictions_total.labels(timeframe=tf, status="error").inc()
            return {"error": "insufficient_data", "symbol": symbol}

        # ensure Open/Close
        if "Close" not in df.columns and "close" in df.columns:
            df["Close"] = df["close"]
        if "Open" not in df.columns and "open" in df.columns:
            df["Open"] = df["open"]

        if strategy == "technical":
            out = self._run_technical(df, h)
        else:
            out = self._run_chronos(symbol, df, h, mid)

        if "error" in out and not out.get("forecast"):
            if METRICS_AVAILABLE:
                stock_predictions_total.labels(timeframe=tf, status="error").inc()
                stock_prediction_duration_seconds.labels(timeframe=tf).observe(time.time() - start_time)
            return {**out, "error": out.get("error", "inference_failed")}

        # Extract forecast array from out dict for API response
        forecast_array = out.get("forecast", [])
        if not isinstance(forecast_array, list):
            forecast_array = []
        
        # persist
        rec = StockPrediction(
            user_id=user_id,
            symbol=symbol,
            timeframe=tf,
            model_id=out.get("model_id", mid),
            strategy=strategy,
            forecast=out,  # Store full dict in DB
            lookback_days=lb,
            horizon=h,
            prediction_metadata={"cdm_events": [{"type": "StockPredictionRequest", "timeframe": tf, "symbol": symbol}]},
        )
        self.db.add(rec)
        self.db.flush()

        # cache
        self._set_cached(cache_key, out, _CACHE_TTL.get(tf, 10))

        if METRICS_AVAILABLE:
            stock_predictions_total.labels(timeframe=tf, status="success").inc()
            stock_prediction_duration_seconds.labels(timeframe=tf).observe(time.time() - start_time)

        # Return forecast as array for API compatibility
        return {
            "forecast": forecast_array,
            "prediction_id": rec.id,
            "cached": False,
            "model_id": out.get("model_id", mid),
            "strategy": strategy,
            "symbol": symbol,
            "timeframe": tf,
            "error": out.get("error"),
            "signal": out.get("signal"),
        }

    def predict_daily(
        self,
        symbol: str,
        *,
        user_id: Optional[int] = None,
        lookback: Optional[int] = None,
        horizon: int = 30,
        strategy: str = "chronos",
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.predict(symbol, "daily", user_id=user_id, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)

    def predict_hourly(
        self,
        symbol: str,
        *,
        user_id: Optional[int] = None,
        lookback: Optional[int] = None,
        horizon: int = 120,
        strategy: str = "chronos",
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.predict(symbol, "hourly", user_id=user_id, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)

    def predict_15min(
        self,
        symbol: str,
        *,
        user_id: Optional[int] = None,
        lookback: Optional[int] = None,
        horizon: int = 96,
        strategy: str = "chronos",
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.predict(symbol, "15min", user_id=user_id, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)
