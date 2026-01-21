"""Portfolio aggregation API: combined trading + bank + manual assets (Trading Phase 4)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
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

    trading_equity = 0.0
    positions: List[Dict[str, Any]] = []
    account_info: Dict[str, Any] = {}
    unrealized_pl = 0.0

    try:
        pos_list = list(trading_api_service.get_positions())
        account_info = trading_api_service.get_account_info() or {}
        trading_equity = float(account_info.get("portfolio_value") or 0.0)
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

    manual = db.query(ManualHolding).filter(ManualHolding.user_id == current_user.id).all()
    for m in manual:
        po = _manual_to_position(m)
        positions.append(po)
        if po.get("market_value"):
            trading_equity += po["market_value"]

    bank_balances = 0.0
    conn = get_plaid_connection(db, current_user.id)
    if conn and conn.connection_data and isinstance(conn.connection_data, dict):
        at = conn.connection_data.get("access_token")
        if at:
            bal = get_balances(at)
            if "accounts" in bal and "error" not in bal:
                for acc in bal["accounts"]:
                    b = acc.get("balances") if isinstance(acc, dict) else {}
                    if isinstance(b, dict):
                        bank_balances += float(b.get("current") or b.get("available") or 0)

    manual_assets_value = 0.0
    for a in db.query(ManualAsset).filter(ManualAsset.user_id == current_user.id).all():
        v = a.current_value if a.current_value is not None else a.purchase_price
        if v is not None:
            manual_assets_value += float(v)

    total_equity = trading_equity + bank_balances + manual_assets_value
    buying_power = float(account_info.get("buying_power") or account_info.get("cash") or 0.0)

    return PortfolioOverviewResponse(
        total_equity=total_equity,
        bank_balances=bank_balances,
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
    """
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
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
