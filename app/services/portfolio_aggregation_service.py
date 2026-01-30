"""
Portfolio Aggregation Service (Phase 2, Week 6).

This module sits on top of the Plaid service and provides a
single, normalized view of a user's portfolio (bank + trading).

It is intentionally defensive: if Plaid is disabled, not linked,
or partially configured, we return empty aggregates instead of
raising, so the API layer can always respond.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services import plaid_service


@dataclass
class AggregatedTransactions:
  transactions: List[Dict[str, Any]]
  total_transactions: int


@dataclass
class AggregatedInvestments:
  positions: List[Dict[str, Any]]
  total_market_value: float
  unrealized_pl: float


@dataclass
class AggregatedLiabilities:
  liabilities: Dict[str, Any]


def _get_user_access_token(db: Session, user_id: int) -> Optional[str]:
  """
  Helper to fetch the user's Plaid access_token, if any.
  Token is stored in connection_data (dict) on UserImplementationConnection.
  """
  conn = plaid_service.get_plaid_connection(db, user_id)
  if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
    return None
  return conn.connection_data.get("access_token")


def aggregate_transactions(
  db: Session,
  user_id: int,
  days: int = 30,
) -> AggregatedTransactions:
  """
  Call Plaid Transactions API and aggregate recent transactions.
  """
  access_token = _get_user_access_token(db, user_id)
  if not access_token:
    return AggregatedTransactions(transactions=[], total_transactions=0)

  end = date.today()
  start = end - timedelta(days=days)
  resp = plaid_service.get_transactions(access_token, start_date=start, end_date=end)
  if "error" in resp:
    return AggregatedTransactions(transactions=[], total_transactions=0)

  txs = resp.get("transactions") or []
  total = int(resp.get("total_transactions") or len(txs))
  return AggregatedTransactions(transactions=txs, total_transactions=total)


def aggregate_investments(
  db: Session,
  user_id: int,
) -> AggregatedInvestments:
  """
  Call Plaid Investments API and aggregate positions / market value.
  """
  access_token = _get_user_access_token(db, user_id)
  if not access_token:
    return AggregatedInvestments(positions=[], total_market_value=0.0, unrealized_pl=0.0)

  holdings_resp = plaid_service.get_investments_holdings(access_token)
  if "error" in holdings_resp:
    return AggregatedInvestments(positions=[], total_market_value=0.0, unrealized_pl=0.0)

  holdings = holdings_resp.get("holdings") or []
  securities = {s.get("security_id"): s for s in (holdings_resp.get("securities") or [])}

  positions: List[Dict[str, Any]] = []
  total_market_value = 0.0

  for h in holdings:
    security = securities.get(h.get("security_id") or "")
    symbol = (security or {}).get("ticker_symbol") or (security or {}).get("name")
    quantity = float(h.get("quantity") or 0.0)
    current_price = float((security or {}).get("close_price") or 0.0)
    market_value = quantity * current_price
    cost_basis = float(h.get("cost_basis") or 0.0)
    unrealized_pl = market_value - cost_basis if cost_basis else 0.0

    positions.append(
      {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": float(h.get("cost_basis") or 0.0) / quantity if quantity and h.get("cost_basis") else 0.0,
        "current_price": current_price,
        "market_value": market_value,
        "unrealized_pl": unrealized_pl,
      }
    )
    total_market_value += market_value

  # For now, unrealized P&L is the sum across positions
  total_unrealized = sum(float(p.get("unrealized_pl") or 0.0) for p in positions)
  return AggregatedInvestments(
    positions=positions,
    total_market_value=total_market_value,
    unrealized_pl=total_unrealized,
  )


def aggregate_liabilities(
  db: Session,
  user_id: int,
) -> AggregatedLiabilities:
  """
  Call Plaid Liabilities API and aggregate results.
  """
  access_token = _get_user_access_token(db, user_id)
  if not access_token:
    return AggregatedLiabilities(liabilities={})

  resp = plaid_service.get_liabilities(access_token)
  if "error" in resp:
    return AggregatedLiabilities(liabilities={})

  return AggregatedLiabilities(liabilities=resp.get("liabilities") or {})


def calculate_portfolio_metrics(
  *,
  bank_balances: float,
  trading_equity: float,
  manual_assets_value: float,
  unrealized_pl: float,
) -> Dict[str, float]:
  """
  Calculate high-level portfolio metrics for the overview card.
  """
  total_equity = float(bank_balances) + float(trading_equity) + float(manual_assets_value)
  # Conservative: use cash + a fraction of trading equity as buying power placeholder.
  buying_power = float(bank_balances) + 0.5 * float(trading_equity)

  return {
    "total_equity": total_equity,
    "bank_balances": float(bank_balances),
    "trading_equity": float(trading_equity),
    "manual_assets_value": float(manual_assets_value),
    "unrealized_pl": float(unrealized_pl),
    "buying_power": float(buying_power),
  }


def get_unified_portfolio(
  db: Session,
  user_id: int,
  *,
  manual_assets_value: float = 0.0,
) -> Dict[str, Any]:
  """
  Combine Plaid data into a single portfolio overview structure
  consumed by `PortfolioDashboard`.
  """
  access_token = _get_user_access_token(db, user_id)
  bank_balances_value = 0.0
  account_info: Dict[str, Any] = {}

  if access_token:
    balances_resp = plaid_service.get_balances(access_token)
    if "error" not in balances_resp:
      accounts = balances_resp.get("accounts") or []
      bank_balances_value = sum(
        float((a.get("balances") or {}).get("current") or 0.0) for a in accounts
      )
      account_info["accounts"] = accounts

  txs = aggregate_transactions(db, user_id)
  investments = aggregate_investments(db, user_id)

  metrics = calculate_portfolio_metrics(
    bank_balances=bank_balances_value,
    trading_equity=investments.total_market_value,
    manual_assets_value=manual_assets_value,
    unrealized_pl=investments.unrealized_pl,
  )

  overview: Dict[str, Any] = {
    **metrics,
    "positions": investments.positions,
    "account_info": account_info,
    "recent_transactions": txs.transactions,
  }

  return overview

