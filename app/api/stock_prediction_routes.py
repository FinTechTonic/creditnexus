"""Stock prediction API: daily, hourly, 15min, backtest, market-status, recommend-order. Pay-as-you-go: 402 when insufficient credits."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user, require_auth
from app.core.config import settings
from app.db import get_db
from app.db.models import User
from app.models.cdm_payment import PaymentType
from app.services.payment_gateway_service import PaymentGatewayService
from app.services.rolling_credits_service import RollingCreditsService
from app.services.stock_prediction_service import StockPredictionService
from app.services.stock_prediction_order_decision_service import StockPredictionOrderDecisionService
from app.stock_prediction_core import get_market_status, run_backtest_from_data_source, CHRONOS_SELECTABLE_MODELS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock-prediction", tags=["stock-prediction"])


def _stock_prediction_enabled() -> None:
    if not getattr(settings, "STOCK_PREDICTION_ENABLED", False):
        raise HTTPException( status_code=403, detail="Stock prediction is disabled (STOCK_PREDICTION_ENABLED=false)" )


def _get_prediction_service(db: Session, user: Optional[User] = None) -> StockPredictionService:
    credits = RollingCreditsService(db) if user else None
    return StockPredictionService(db, rolling_credits=credits)


# ---------------------------------------------------------------------------
# GET /daily
# ---------------------------------------------------------------------------

@router.get("/daily")
async def predict_daily(
    symbol: str = Query(..., min_length=1, max_length=20),
    lookback: Optional[int] = Query(None, ge=1, le=2520),
    horizon: int = Query(30, ge=1, le=365),
    strategy: str = Query("chronos", pattern="^(chronos|technical)$"),
    model_id: Optional[str] = Query(None, description="Chronos model (e.g. amazon/chronos-t5-small, amazon/chronos-t5-base)"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> dict:
    _stock_prediction_enabled()
    svc = _get_prediction_service(db, user)
    result = svc.predict_daily(symbol, user_id=user.id if user else None, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)
    if result.get("error") == "insufficient_credits" and user:
        gate = await PaymentGatewayService(db).require_credits_or_402(
            user_id=user.id,
            credit_type="stock_prediction_daily",
            amount=1.0,
            feature="stock_prediction",
            payment_type=PaymentType.BILLABLE_FEATURE,
            cost_usd=Decimal("0.10"),
        )
        if gate.get("status_code") == 402:
            return billable_402_response(gate)
    return result


# ---------------------------------------------------------------------------
# GET /hourly
# ---------------------------------------------------------------------------

@router.get("/hourly")
async def predict_hourly(
    symbol: str = Query(..., min_length=1, max_length=20),
    lookback: Optional[int] = Query(None, ge=1, le=2016),
    horizon: int = Query(120, ge=1, le=168),
    strategy: str = Query("chronos", pattern="^(chronos|technical)$"),
    model_id: Optional[str] = Query(None, description="Chronos model (e.g. amazon/chronos-t5-small, amazon/chronos-t5-base)"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> dict:
    _stock_prediction_enabled()
    svc = _get_prediction_service(db, user)
    result = svc.predict_hourly(symbol, user_id=user.id if user else None, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)
    if result.get("error") == "insufficient_credits" and user:
        gate = await PaymentGatewayService(db).require_credits_or_402(
            user_id=user.id,
            credit_type="stock_prediction_hourly",
            amount=1.0,
            feature="stock_prediction",
            payment_type=PaymentType.BILLABLE_FEATURE,
            cost_usd=Decimal("0.10"),
        )
        if gate.get("status_code") == 402:
            return billable_402_response(gate)
    return result


# ---------------------------------------------------------------------------
# GET /15min
# ---------------------------------------------------------------------------

@router.get("/15min")
async def predict_15min(
    symbol: str = Query(..., min_length=1, max_length=20),
    lookback: Optional[int] = Query(None, ge=1, le=672),
    horizon: int = Query(96, ge=1, le=192),
    strategy: str = Query("chronos", pattern="^(chronos|technical)$"),
    model_id: Optional[str] = Query(None, description="Chronos model (e.g. amazon/chronos-t5-small, amazon/chronos-t5-base)"),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
) -> dict:
    _stock_prediction_enabled()
    svc = _get_prediction_service(db, user)
    result = svc.predict_15min(symbol, user_id=user.id if user else None, lookback=lookback, horizon=horizon, strategy=strategy, model_id=model_id)
    if result.get("error") == "insufficient_credits" and user:
        gate = await PaymentGatewayService(db).require_credits_or_402(
            user_id=user.id,
            credit_type="stock_prediction_15min",
            amount=1.0,
            feature="stock_prediction",
            payment_type=PaymentType.BILLABLE_FEATURE,
            cost_usd=Decimal("0.10"),
        )
        if gate.get("status_code") == 402:
            return billable_402_response(gate)
    return result


# ---------------------------------------------------------------------------
# POST /backtest
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    start: Optional[str] = Field(None, description="YYYY-MM-DD")
    end: Optional[str] = Field(None, description="YYYY-MM-DD")
    strategy: str = Field("combined", description="combined, trend, mean_reversion, momentum, volatility, stat_arb")
    timeframe: str = Field("1d", description="1d, 1h, 15m")
    initial_capital: float = Field(default=100_000.0, ge=100.0, description="Initial capital for the backtest")


@router.post("/backtest")
def backtest(body: BacktestRequest, db: Session = Depends(get_db)) -> dict:
    _stock_prediction_enabled()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    if body.end:
        try:
            end = datetime.fromisoformat(body.end.replace("Z", "+00:00"))
        except Exception:
            end = datetime.now(timezone.utc)
    if body.start:
        try:
            start = datetime.fromisoformat(body.start.replace("Z", "+00:00"))
        except Exception:
            start = end - timedelta(days=365)
    cap = float(body.initial_capital)
    res = run_backtest_from_data_source(
        body.symbol, start, end, strategy=body.strategy, timeframe=body.timeframe, initial_capital=cap, db=db
    )
    return {
        "total_return": res.total_return,
        "sharpe_ratio": res.sharpe_ratio,
        "max_drawdown": res.max_drawdown,
        "win_rate": res.win_rate,
        "n_trades": res.n_trades,
        "equity_curve": res.equity_curve or [],
        "trades": res.trades or [],
        "metadata": res.metadata,
    }


# ---------------------------------------------------------------------------
# GET /models (selectable Chronos model IDs)
# ---------------------------------------------------------------------------

@router.get("/models")
def list_chronos_models() -> dict:
    """Return selectable Chronos model IDs for the Predictions tab. No auth required."""
    _stock_prediction_enabled()
    return {"models": CHRONOS_SELECTABLE_MODELS}


# ---------------------------------------------------------------------------
# GET /market-status
# ---------------------------------------------------------------------------

@router.get("/market-status")
def market_status(
    market: str = Query("US_STOCKS", description="US_STOCKS, US_FUTURES, FOREX, CRYPTO, etc."),
) -> dict:
    _stock_prediction_enabled()
    st = get_market_status(market)
    return {
        "is_open": st.is_open,
        "status_text": st.status_text,
        "next_trading_day": st.next_trading_day,
        "last_updated": st.last_updated,
        "time_until_open": st.time_until_open,
        "time_until_close": st.time_until_close,
        "current_time_et": st.current_time_et,
        "market_name": st.market_name,
        "market_type": st.market_type,
        "market_symbol": st.market_symbol,
    }


# ---------------------------------------------------------------------------
# POST /recommend-order
# ---------------------------------------------------------------------------

class RecommendOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    prediction_id: Optional[int] = None
    timeframe: str = Field("daily", description="daily, hourly, 15min")
    strategy: str = Field("combined", description="combined, trend, mean_reversion, momentum, volatility, stat_arb")


@router.post("/recommend-order")
def recommend_order(
    body: RecommendOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth),
) -> dict:
    _stock_prediction_enabled()
    pred_svc = _get_prediction_service(db, user)
    dec_svc = StockPredictionOrderDecisionService(db, prediction_service=pred_svc)
    return dec_svc.recommend_order(
        body.symbol,
        user.id,
        prediction_id=body.prediction_id,
        timeframe=body.timeframe,
        strategy=body.strategy,
    )
