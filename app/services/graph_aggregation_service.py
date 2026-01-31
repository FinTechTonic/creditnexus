"""
Graph Aggregation Service (Week 18 Data Flow Integration).

Aggregates Plaid-backed portfolio data and other sources into structures suitable
for unified graphs and dashboards. Used to populate interfaces with consistent
portfolio and time-series data.

- aggregate_graph_data: pull from portfolio_aggregation (Plaid), optional risk/positions.
- calculate_metrics: totals, by-asset breakdown, time-bucketed metrics.
- format_graph_data: chart-ready series and labels for frontend.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.portfolio_aggregation_service import (
    aggregate_investments,
    aggregate_transactions,
    get_unified_portfolio,
)

logger = logging.getLogger(__name__)


def aggregate_graph_data(
    db: Session,
    user_id: int,
    *,
    days: int = 30,
    include_risk: bool = False,
) -> Dict[str, Any]:
    """
    Aggregate data from Plaid (via portfolio_aggregation) and optional risk/other
    sources into a single structure for graphs and metrics.

    Returns dict with: positions, transactions, balances, account_info,
    optional risk_snapshot, and raw aggregates for calculate_metrics/format_graph_data.
    """
    unified = get_unified_portfolio(db, user_id)
    txs_agg = aggregate_transactions(db, user_id, days=days)
    inv_agg = aggregate_investments(db, user_id)

    out: Dict[str, Any] = {
        "positions": unified.get("positions") or inv_agg.positions,
        "transactions": txs_agg.transactions,
        "total_transactions": txs_agg.total_transactions,
        "total_market_value": inv_agg.total_market_value,
        "unrealized_pl": inv_agg.unrealized_pl,
        "bank_balances": unified.get("bank_balances", 0.0),
        "trading_equity": unified.get("trading_equity", inv_agg.total_market_value),
        "total_equity": unified.get("total_equity", 0.0),
        "buying_power": unified.get("buying_power", 0.0),
        "account_info": unified.get("account_info") or {},
        "as_of": datetime.utcnow().isoformat() + "Z",
    }

    if include_risk:
        try:
            from app.services.credit_risk_service import CreditRiskService
            risk_svc = CreditRiskService(db)
            if hasattr(risk_svc, "get_risk_summary"):
                out["risk_snapshot"] = risk_svc.get_risk_summary(user_id=user_id) or {}
            else:
                out["risk_snapshot"] = {}
        except Exception as e:
            logger.debug("Risk snapshot skipped for graph aggregation: %s", e)
            out["risk_snapshot"] = {}

    return out


def calculate_metrics(aggregated: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute metrics from aggregated graph data: totals, by-asset breakdown,
    time-bucketed transaction totals for time-series charts.
    """
    positions = aggregated.get("positions") or []
    transactions = aggregated.get("transactions") or []

    by_symbol: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"market_value": 0.0, "quantity": 0.0, "unrealized_pl": 0.0})
    for p in positions:
        sym = (p.get("symbol") or "Unknown").strip() or "Unknown"
        by_symbol[sym]["market_value"] += float(p.get("market_value") or 0.0)
        by_symbol[sym]["quantity"] += float(p.get("quantity") or 0.0)
        by_symbol[sym]["unrealized_pl"] += float(p.get("unrealized_pl") or 0.0)

    # Time buckets (last 30 days by default): daily totals for chart
    buckets: Dict[str, float] = defaultdict(float)
    for t in transactions:
        dt_str = (t.get("date") or t.get("authorized_date") or "")
        if not dt_str:
            continue
        try:
            if "T" in dt_str:
                d = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()
            else:
                d = datetime.strptime(dt_str[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        amt = float(t.get("amount") or 0.0)
        buckets[d.isoformat()] += amt

    sorted_dates = sorted(buckets.keys())
    time_series = [{"date": d, "total_amount": buckets[d]} for d in sorted_dates]

    total_market_value = aggregated.get("total_market_value") or 0.0
    total_equity = aggregated.get("total_equity") or 0.0

    return {
        "by_symbol": dict(by_symbol),
        "position_count": len(positions),
        "transaction_count": len(transactions),
        "total_market_value": total_market_value,
        "total_equity": total_equity,
        "time_series_transactions": time_series,
        "date_range": {"min": sorted_dates[0] if sorted_dates else None, "max": sorted_dates[-1] if sorted_dates else None},
    }


def format_graph_data(
    aggregated: Dict[str, Any],
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format aggregated data and metrics into chart-ready structures: series for
    pie/bar (allocation by symbol), time series for line/area (transactions over time),
    and a summary for cards.
    """
    if metrics is None:
        metrics = calculate_metrics(aggregated)

    by_symbol = metrics.get("by_symbol") or {}
    time_series = metrics.get("time_series_transactions") or []

    # Pie/bar: allocation by symbol
    allocation_series = [
        {"name": name, "value": round(data.get("market_value", 0.0), 2)}
        for name, data in sorted(by_symbol.items(), key=lambda x: -x[1].get("market_value", 0))
    ]

    # Line/area: transaction totals by date
    line_series = [
        {"date": pt["date"], "value": round(pt.get("total_amount", 0.0), 2)}
        for pt in time_series
    ]

    return {
        "allocation": allocation_series,
        "transaction_series": line_series,
        "summary": {
            "total_equity": aggregated.get("total_equity"),
            "total_market_value": aggregated.get("total_market_value"),
            "bank_balances": aggregated.get("bank_balances"),
            "position_count": metrics.get("position_count", 0),
            "transaction_count": metrics.get("transaction_count", 0),
        },
        "as_of": aggregated.get("as_of"),
    }
