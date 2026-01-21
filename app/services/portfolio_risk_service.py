"""
Portfolio Risk Analysis Service (Trading Phase 5).

Premium feature: diversification analysis, asset-class allocation,
stubbed risk metrics (Sharpe, beta, VaR, max drawdown), and simple
allocation recommendations. Gated by subscription tier (Pro/Premium/Lifetime).
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import ManualHolding, ManualAsset
from app.services.plaid_service import get_plaid_connection, get_balances
from app.services.trading_api_service import TradingAPIService, TradingAPIError

logger = logging.getLogger(__name__)

# ManualAsset.asset_type -> asset class for allocation
_ASSET_TYPE_TO_CLASS = {
    "fixed_income": "bonds",
    "real_estate": "real_estate",
    "physical": "commodities",
    "interest_account": "cash",
}
_DEFAULT_MANUAL_CLASS = "other"

# Allocation thresholds for recommendations (percent of total)
_CASH_HIGH = 80.0
_EQUITY_HIGH = 90.0
_BONDS_HIGH = 60.0


class PortfolioRiskService:
    """Analyzes portfolio diversification and produces risk metrics (premium)."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_diversification(
        self, user_id: int, trading_api_service: TradingAPIService
    ) -> Dict[str, Any]:
        """
        Aggregate holdings from trading, manual holdings, manual assets, and Plaid;
        compute asset-class allocation, stubbed sector/country/currency exposure,
        stubbed risk metrics, and allocation-based recommendations.
        """
        # --- 1. Collect values by asset class ---
        by_class: Dict[str, float] = {
            "equity": 0.0,
            "bonds": 0.0,
            "real_estate": 0.0,
            "commodities": 0.0,
            "cash": 0.0,
            "other": 0.0,
        }

        # Trading API positions
        try:
            for p in trading_api_service.get_positions():
                q = float(p.get("qty") or p.get("quantity") or 0)
                mv = p.get("market_value")
                if mv is not None:
                    by_class["equity"] += float(mv)
                else:
                    avg = p.get("avg_entry_price") or p.get("average_price")
                    if avg is not None and q:
                        by_class["equity"] += float(avg) * q
        except TradingAPIError:
            pass

        # Manual holdings (treated as equity)
        for m in self.db.query(ManualHolding).filter(ManualHolding.user_id == user_id).all():
            q = float(m.quantity or 0)
            ac = float(m.average_cost or 0)
            if ac and q:
                by_class["equity"] += q * ac

        # Manual assets by asset_type
        for a in self.db.query(ManualAsset).filter(ManualAsset.user_id == user_id).all():
            v = a.current_value if a.current_value is not None else a.purchase_price
            if v is not None:
                vf = float(v)
                ac = _ASSET_TYPE_TO_CLASS.get(
                    (a.asset_type or "").strip().lower(), _DEFAULT_MANUAL_CLASS
                )
                if ac not in by_class:
                    by_class[ac] = 0.0
                by_class[ac] += vf

        # Bank (Plaid) -> cash
        conn = get_plaid_connection(self.db, user_id)
        if conn and conn.connection_data and isinstance(conn.connection_data, dict):
            at = conn.connection_data.get("access_token")
            if at:
                bal = get_balances(at)
                if isinstance(bal, dict) and "accounts" in bal and "error" not in bal:
                    for acc in bal["accounts"]:
                        b = acc.get("balances") if isinstance(acc, dict) else {}
                        if isinstance(b, dict):
                            by_class["cash"] += float(
                                b.get("current") or b.get("available") or 0
                            )

        total = sum(by_class.values())
        if total <= 0:
            return {
                "asset_class_allocation": {k: 0.0 for k in by_class},
                "sector_exposure": {},
                "country_exposure": {},
                "currency_exposure": {"USD": 1.0},
                "risk_metrics": {
                    "sharpe_ratio": None,
                    "beta": None,
                    "var_95": None,
                    "max_drawdown": None,
                },
                "recommendations": [
                    "Add positions or manual assets to unlock risk analysis."
                ],
                "total_equity": 0.0,
            }

        # --- 2. Asset class allocation (fractions) ---
        asset_class_allocation = {k: round(v / total, 4) for k, v in by_class.items()}

        # --- 3. Stubbed exposures (no symbol-level data) ---
        sector_exposure: Dict[str, float] = {}
        country_exposure: Dict[str, float] = {}
        if by_class.get("equity", 0) > 0:
            sector_exposure["equity"] = round(by_class["equity"] / total, 4)
        country_exposure = {"Unknown": 1.0}
        currency_exposure = {"USD": 1.0}

        # --- 4. Stubbed risk metrics (no return history) ---
        risk_metrics = {
            "sharpe_ratio": None,
            "beta": None,
            "var_95": None,
            "max_drawdown": None,
        }

        # --- 5. Recommendations from allocation ---
        recs: List[str] = []
        cash_pct = asset_class_allocation.get("cash", 0.0) * 100
        equity_pct = asset_class_allocation.get("equity", 0.0) * 100
        bonds_pct = asset_class_allocation.get("bonds", 0.0) * 100

        if cash_pct >= _CASH_HIGH:
            recs.append(
                "High cash allocation; consider diversifying into equities or bonds."
            )
        if equity_pct >= _EQUITY_HIGH:
            recs.append(
                "High equity concentration; consider adding bonds or alternatives for diversification."
            )
        if bonds_pct >= _BONDS_HIGH:
            recs.append("Bond-heavy; ensure alignment with risk tolerance.")
        if not recs:
            recs.append("Diversification is within typical ranges.")

        return {
            "asset_class_allocation": asset_class_allocation,
            "sector_exposure": sector_exposure,
            "country_exposure": country_exposure,
            "currency_exposure": currency_exposure,
            "risk_metrics": risk_metrics,
            "recommendations": recs,
            "total_equity": round(total, 2),
        }
