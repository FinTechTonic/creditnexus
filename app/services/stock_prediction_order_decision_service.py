"""
Stock prediction order decision service: produces buy/sell/hold recommendations from
predictions and trading signals, persists PredictionOrderRecommendation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import PredictionOrderRecommendation, StockPrediction
from app.services.market_data_service import get_historical_data
from app.services.stock_prediction_service import StockPredictionService
from app.stock_prediction_core.trading_strategies import get_trading_signals

logger = logging.getLogger(__name__)

_TF_TO_MARKET = {"daily": "1D", "hourly": "1H", "15min": "15Min"}


class StockPredictionOrderDecisionService:
    def __init__(self, db: Session, prediction_service: Optional[StockPredictionService] = None) -> None:
        self.db = db
        self._pred = prediction_service or StockPredictionService(db)

    def recommend_order(
        self,
        symbol: str,
        user_id: int,
        *,
        prediction_id: Optional[int] = None,
        timeframe: str = "daily",
        strategy: str = "combined",
    ) -> Dict[str, Any]:
        """
        Produce a buy/sell/hold recommendation, persist PredictionOrderRecommendation, return it.

        - If prediction_id: load StockPrediction; fetch recent bars for signals.
        - Else: run StockPredictionService.predict for the timeframe (gets forecast + we need df for signals).
        - Run get_trading_signals(df, strategy) for consensus.
        - Map consensus: bullish->buy, bearish->sell, neutral->hold.
        - confidence from consensus; size=null; reasoning from consensus + forecast summary.
        """
        pred = None
        forecast = None
        df = None
        market_tf = _TF_TO_MARKET.get(timeframe.lower(), "1D")

        if prediction_id:
            pred = self.db.query(StockPrediction).filter(StockPrediction.id == prediction_id).first()
            if not pred:
                return {"error": "prediction_not_found", "prediction_id": prediction_id}
            if pred.symbol != symbol:
                return {"error": "prediction_symbol_mismatch", "symbol": symbol}
            forecast = pred.forecast or {}
            # fetch recent bars for signals (reuse lookback order)
            end = datetime.now(timezone.utc)
            days = min(90, max(30, (pred.lookback_days or 252) // 2))
            start = end - timedelta(days=days)
            df = get_historical_data(symbol, start, end, timeframe=market_tf, db=self.db)
        else:
            # run predict to get forecast; we need the df for signals. predict doesn't return df.
            # So we run predict (which does fetch+infer) and separately fetch again for signals.
            # To avoid double fetch: we could extend StockPredictionService.predict to return (out, df).
            # For simplicity: run predict, then fetch recent data for signals.
            out = self._pred.predict(symbol, timeframe, user_id=user_id, strategy="chronos")
            if "error" in out:
                return out
            forecast = out
            pred_id = out.get("prediction_id")
            if pred_id:
                pred = self.db.query(StockPrediction).filter(StockPrediction.id == pred_id).first()
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=60)
            df = get_historical_data(symbol, start, end, timeframe=market_tf, db=self.db)

        if df is None or df.empty or len(df) < 2:
            return {"error": "insufficient_data", "symbol": symbol}

        if "Close" not in df.columns and "close" in df.columns:
            df = df.copy()
            df["Close"] = df["close"]

        try:
            sigs = get_trading_signals(df, strategy)
        except Exception as e:
            logger.warning("get_trading_signals failed: %s", e)
            return {"error": "signals_failed", "reason": str(e)}

        consensus = sigs.get("consensus") or {}
        signal = (consensus.get("signal") or "neutral").lower()
        confidence = float(consensus.get("confidence") or 0.5)
        if signal == "bullish":
            action = "buy"
        elif signal == "bearish":
            action = "sell"
        else:
            action = "hold"

        horizon = (forecast.get("horizon") or (pred.horizon if pred else 30)) if isinstance(forecast, dict) else (pred.horizon if pred else 30)
        reasoning = f"Consensus: {signal}, confidence {confidence:.2f}. Forecast horizon: {horizon}."

        rec = PredictionOrderRecommendation(
            user_id=user_id,
            prediction_id=pred.id if pred else None,
            symbol=symbol,
            action=action,
            size=None,
            confidence=confidence,
            strategy=strategy,
            reasoning=reasoning,
            extra={"consensus": consensus, "forecast_keys": list(forecast.keys()) if isinstance(forecast, dict) else []},
        )
        self.db.add(rec)
        self.db.flush()
        return rec.to_dict()
