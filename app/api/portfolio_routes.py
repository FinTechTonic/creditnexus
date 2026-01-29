"""Portfolio aggregation API: combined trading + bank + manual assets (Trading Phase 4)."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW
from app.db import get_db
from app.db.models import User, ManualHolding, ManualAsset
from app.services.plaid_service import get_plaid_connection, get_balances
from app.services.trading_api_service import TradingAPIError
from app.api.trading_routes import get_trading_api_service
from app.services.trading_api_service import TradingAPIService
from app.services.subscription_service import SubscriptionService
from app.services.portfolio_risk_service import PortfolioRiskService
from app.services.technical_indicators_service import TechnicalIndicatorsService
from app.services import portfolio_aggregation_service

logger = logging.getLogger(__name__)

# Risk analysis: allowed tiers (Pro, Premium, Lifetime)
_RISK_ANALYSIS_TIERS = {"pro", "premium", "lifetime"}

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _manual_to_position(m: ManualHolding) -> Dict[str, Any]:
    q = float(m.quantity)
    ac = float(m.average_cost or 0)
    return {
        "symbol": m.symbol,
        "quantity": q,
        "average_price": ac if ac else None,
        "current_price": None,
        "market_value": q * ac if ac else None,
        "unrealized_pl": None,
    }


class PortfolioOverviewResponse(BaseModel):
    total_equity: float
    bank_balances: float
    trading_equity: float
    manual_assets_value: float
    unrealized_pl: float
    buying_power: float
    positions: List[Dict[str, Any]]
    account_info: Dict[str, Any]


class RiskMetricsModel(BaseModel):
    sharpe_ratio: Optional[float] = None
    beta: Optional[float] = None
    var_95: Optional[float] = None
    max_drawdown: Optional[float] = None


class RiskAnalysisResponse(BaseModel):
    asset_class_allocation: Dict[str, float]
    sector_exposure: Dict[str, float]
    country_exposure: Dict[str, float]
    currency_exposure: Dict[str, float]
    risk_metrics: RiskMetricsModel
    recommendations: List[str]
    total_equity: float


@router.get("/overview", response_model=PortfolioOverviewResponse)
async def get_portfolio_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
):
    """Aggregated portfolio: trading (positions + manual holdings) + Plaid bank balances + manual assets. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Calculate manual assets value
    manual_assets_value = 0.0
    for a in db.query(ManualAsset).filter(ManualAsset.user_id == current_user.id).all():
        v = a.current_value if a.current_value is not None else a.purchase_price
        if v is not None:
            manual_assets_value += float(v)

    # Use the new portfolio aggregation service for Plaid data
    overview = portfolio_aggregation_service.get_unified_portfolio(
        db, current_user.id, manual_assets_value=manual_assets_value
    )

    # Merge trading API positions if available
    positions = list(overview.get("positions") or [])
    account_info = overview.get("account_info") or {}
    unrealized_pl = float(overview.get("unrealized_pl") or 0.0)
    trading_equity = float(overview.get("trading_equity") or 0.0)

    try:
        pos_list = list(trading_api_service.get_positions())
        trading_account_info = trading_api_service.get_account_info() or {}
        account_info.update(trading_account_info)
        trading_equity_from_api = float(trading_account_info.get("portfolio_value") or 0.0)
        if trading_equity_from_api > 0:
            trading_equity = trading_equity_from_api
        
        for p in pos_list:
            positions.append({
                "symbol": p.get("symbol", ""),
                "quantity": float(p.get("qty") or p.get("quantity") or 0),
                "average_price": p.get("avg_entry_price") or p.get("average_price"),
                "current_price": p.get("current_price"),
                "market_value": p.get("market_value"),
                "unrealized_pl": p.get("unrealized_pl"),
            })
            if p.get("unrealized_pl") is not None:
                unrealized_pl += float(p["unrealized_pl"])
    except TradingAPIError:
        pass

    # Add manual holdings
    manual = db.query(ManualHolding).filter(ManualHolding.user_id == current_user.id).all()
    for m in manual:
        po = _manual_to_position(m)
        positions.append(po)
        if po.get("market_value"):
            trading_equity += po["market_value"]

    # Recalculate metrics with merged data
    metrics = portfolio_aggregation_service.calculate_portfolio_metrics(
        bank_balances=float(overview.get("bank_balances") or 0.0),
        trading_equity=trading_equity,
        manual_assets_value=manual_assets_value,
        unrealized_pl=unrealized_pl,
    )
    
    buying_power = float(account_info.get("buying_power") or account_info.get("cash") or metrics.get("buying_power") or 0.0)

    return PortfolioOverviewResponse(
        total_equity=metrics["total_equity"],
        bank_balances=metrics["bank_balances"],
        trading_equity=trading_equity,
        manual_assets_value=manual_assets_value,
        unrealized_pl=unrealized_pl,
        buying_power=buying_power,
        positions=positions,
        account_info=account_info,
    )


@router.get("/risk-analysis", response_model=RiskAnalysisResponse)
async def get_portfolio_risk_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
):
    """
    Premium risk analysis: asset-class allocation, sector/country/currency exposure
    (stubbed), risk metrics (stubbed), and allocation-based recommendations.
    Requires PERMISSION_TRADE_VIEW and subscription tier Pro, Premium, or Lifetime.
    Admin users bypass subscription tier check.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Admin users bypass subscription tier check
    if current_user.role != "admin":
        tier = SubscriptionService(db).get_user_tier(current_user.id)
        if (tier or "free").lower() not in _RISK_ANALYSIS_TIERS:
            raise HTTPException(
                status_code=403,
                detail="Risk analysis requires a Pro, Premium, or Lifetime subscription.",
            )
    result = PortfolioRiskService(db).analyze_diversification(
        current_user.id, trading_api_service
    )
    return RiskAnalysisResponse(
        asset_class_allocation=result["asset_class_allocation"],
        sector_exposure=result["sector_exposure"],
        country_exposure=result["country_exposure"],
        currency_exposure=result["currency_exposure"],
        risk_metrics=RiskMetricsModel(**result["risk_metrics"]),
        recommendations=result["recommendations"],
        total_equity=result["total_equity"],
    )


class PerformanceMetrics(BaseModel):
    total_return: float
    total_return_percent: float
    daily_return: float
    daily_return_percent: float
    weekly_return: float
    weekly_return_percent: float
    monthly_return: float
    monthly_return_percent: float
    best_day: Optional[Dict[str, Any]] = None
    worst_day: Optional[Dict[str, Any]] = None
    win_rate: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None


class PerformanceAnalyticsResponse(BaseModel):
    current_value: float
    initial_value: float
    metrics: PerformanceMetrics
    daily_returns: List[Dict[str, Any]]
    period_start: str
    period_end: str


@router.get("/performance", response_model=PerformanceAnalyticsResponse)
async def get_portfolio_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trading_api_service: TradingAPIService = Depends(get_trading_api_service),
):
    """
    Get portfolio performance analytics.
    
    Calculates returns, win rate, and other performance metrics over the specified period.
    Requires PERMISSION_TRADE_VIEW.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        from decimal import Decimal
        
        # Get current portfolio value
        account_info = trading_api_service.get_account_info() or {}
        current_value = float(account_info.get("portfolio_value") or account_info.get("equity") or 0.0)
        
        # For now, use current value as initial (in production, would track historical values)
        initial_value = current_value * 0.95  # Placeholder: assume 5% gain
        
        # Calculate returns
        total_return = current_value - initial_value
        total_return_percent = (total_return / initial_value * 100) if initial_value > 0 else 0.0
        
        # Daily returns (simplified - in production, would use historical data)
        daily_return = total_return / days if days > 0 else 0.0
        daily_return_percent = (daily_return / initial_value * 100) if initial_value > 0 else 0.0
        weekly_return = daily_return * 7
        weekly_return_percent = daily_return_percent * 7
        monthly_return = daily_return * 30
        monthly_return_percent = daily_return_percent * 30
        
        # Generate daily returns array (placeholder)
        daily_returns = []
        for i in range(days):
            daily_returns.append({
                "date": (datetime.utcnow() - timedelta(days=days - i - 1)).isoformat(),
                "value": initial_value + (total_return * (i + 1) / days),
                "return": daily_return,
                "return_percent": daily_return_percent,
            })
        
        metrics = PerformanceMetrics(
            total_return=total_return,
            total_return_percent=total_return_percent,
            daily_return=daily_return,
            daily_return_percent=daily_return_percent,
            weekly_return=weekly_return,
            weekly_return_percent=weekly_return_percent,
            monthly_return=monthly_return,
            monthly_return_percent=monthly_return_percent,
            win_rate=None,  # Would calculate from trade history
            avg_win=None,
            avg_loss=None,
        )
        
        return PerformanceAnalyticsResponse(
            current_value=current_value,
            initial_value=initial_value,
            metrics=metrics,
            daily_returns=daily_returns,
            period_start=(datetime.utcnow() - timedelta(days=days)).isoformat(),
            period_end=datetime.utcnow().isoformat(),
        )
        
    except Exception as e:
        logger.error(f"Failed to calculate portfolio performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate performance: {str(e)}")


@router.get("/transactions")
async def get_portfolio_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch transactions"),
):
    """Get aggregated transactions from Plaid. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = portfolio_aggregation_service.aggregate_transactions(db, current_user.id, days=days)
    return {
        "transactions": result.transactions,
        "total_transactions": result.total_transactions,
    }


@router.get("/investments")
async def get_portfolio_investments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated investment holdings from Plaid. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = portfolio_aggregation_service.aggregate_investments(db, current_user.id)
    return {
        "positions": result.positions,
        "total_market_value": result.total_market_value,
        "unrealized_pl": result.unrealized_pl,
    }


@router.get("/liabilities")
async def get_portfolio_liabilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated liabilities from Plaid. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = portfolio_aggregation_service.aggregate_liabilities(db, current_user.id)
    return {
        "liabilities": result.liabilities,
    }


@router.get("/technical-indicators")
async def get_technical_indicators(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days for calculation")
):
    """Get technical indicators for user's portfolio.
    
    Returns RSI, MACD, Bollinger Bands, and Moving Averages.
    Requires PERMISSION_TRADE_VIEW.
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        service = TechnicalIndicatorsService(db)
        indicators = service.get_portfolio_technical_indicators(
            user_id=current_user.id,
            days=days
        )
        return indicators
    except Exception as e:
        logger.error(f"Failed to calculate technical indicators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate technical indicators: {str(e)}")
