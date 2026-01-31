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
  Helper to fetch the user's first Plaid access_token (backward compat).
  """
  tokens = _get_user_access_tokens(db, user_id)
  return tokens[0] if tokens else None


def _get_user_access_tokens(db: Session, user_id: int) -> List[str]:
  """
  Return all Plaid access_tokens for the user (multi-item).
  Each UserImplementationConnection (Plaid) row can hold one access_token in connection_data.
  """
  conns = plaid_service.get_plaid_connections(db, user_id)
  tokens: List[str] = []
  for conn in conns or []:
    if not conn.connection_data or not isinstance(conn.connection_data, dict):
      continue
    at = conn.connection_data.get("access_token")
    if at:
      tokens.append(at)
  return tokens


def aggregate_transactions(
  db: Session,
  user_id: int,
  days: int = 30,
) -> AggregatedTransactions:
  """
  Call Plaid Transactions API for all linked items and aggregate (multi-item).
  """
  tokens = _get_user_access_tokens(db, user_id)
  if not tokens:
    return AggregatedTransactions(transactions=[], total_transactions=0)

  end = date.today()
  start = end - timedelta(days=days)
  all_txs: List[Dict[str, Any]] = []
  total_count = 0
  for access_token in tokens:
    resp = plaid_service.get_transactions(access_token, start_date=start, end_date=end)
    if "error" in resp:
      continue
    txs = resp.get("transactions") or []
    all_txs.extend(txs)
    total_count += int(resp.get("total_transactions") or len(txs))
  return AggregatedTransactions(transactions=all_txs, total_transactions=total_count)


def spending_breakdown(
  db: Session,
  user_id: int,
  days: int = 30,
) -> Dict[str, Any]:
  """
  Aggregate Plaid transactions by category (and optionally merchant) for spending analysis.
  Uses personal_finance_category.primary or category from each transaction.
  Outflows (negative amount) are summed as positive "spend" per category.
  """
  aggregated = aggregate_transactions(db, user_id, days=days)
  txs = aggregated.transactions

  by_category: Dict[str, Dict[str, Any]] = {}
  by_merchant: Dict[str, Dict[str, Any]] = {}
  total_spend = 0.0

  for tx in txs:
    amount = float(tx.get("amount") or 0.0)
    # Only count outflows (negative in Plaid) as spend
    if amount < 0:
      spend = abs(amount)
      total_spend += spend

      # Category: Plaid personal_finance_category.primary or category (array or string)
      pfc = tx.get("personal_finance_category") or {}
      category_key = None
      if isinstance(pfc, dict):
        category_key = pfc.get("primary") or pfc.get("detailed")
      if not category_key and "category" in tx:
        cat = tx["category"]
        if isinstance(cat, list) and cat:
          category_key = cat[0] if isinstance(cat[0], str) else str(cat[0])
        elif isinstance(cat, str):
          category_key = cat
      if not category_key:
        category_key = "Uncategorized"

      if category_key not in by_category:
        by_category[category_key] = {"amount": 0.0, "count": 0}
      by_category[category_key]["amount"] += spend
      by_category[category_key]["count"] += 1

      # Merchant: merchant_name or name
      merchant = (tx.get("merchant_name") or tx.get("name") or "").strip() or "Unknown"
      if merchant not in by_merchant:
        by_merchant[merchant] = {"amount": 0.0, "count": 0}
      by_merchant[merchant]["amount"] += spend
      by_merchant[merchant]["count"] += 1

  # Return lists sorted by amount descending
  by_category_list = [
    {"category": k, "amount": round(v["amount"], 2), "count": v["count"]}
    for k, v in sorted(by_category.items(), key=lambda x: -x[1]["amount"])
  ]
  by_merchant_list = [
    {"merchant": k, "amount": round(v["amount"], 2), "count": v["count"]}
    for k, v in sorted(by_merchant.items(), key=lambda x: -x[1]["amount"])
  ]

  return {
    "by_category": by_category_list,
    "by_merchant": by_merchant_list,
    "total_spend": round(total_spend, 2),
    "total_transactions": len(txs),
    "days": days,
  }


def aggregate_investments(
  db: Session,
  user_id: int,
) -> AggregatedInvestments:
  """
  Call Plaid Investments API for all linked items and aggregate (multi-item).
  """
  tokens = _get_user_access_tokens(db, user_id)
  if not tokens:
    return AggregatedInvestments(positions=[], total_market_value=0.0, unrealized_pl=0.0)

  positions: List[Dict[str, Any]] = []
  total_market_value = 0.0

  for access_token in tokens:
    holdings_resp = plaid_service.get_investments_holdings(access_token)
    if "error" in holdings_resp:
      continue
    holdings = holdings_resp.get("holdings") or []
    securities = {s.get("security_id"): s for s in (holdings_resp.get("securities") or [])}

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
          "source": "plaid_investments",
          "type": "equity",
        }
      )
      total_market_value += market_value

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
  Call Plaid Liabilities API for all linked items and merge (multi-item).
  """
  tokens = _get_user_access_tokens(db, user_id)
  if not tokens:
    return AggregatedLiabilities(liabilities={})

  merged: Dict[str, Any] = {}
  for access_token in tokens:
    resp = plaid_service.get_liabilities(access_token)
    if "error" in resp:
      continue
    liab = resp.get("liabilities") or {}
    for key, val in liab.items():
      if key not in merged:
        merged[key] = val if not isinstance(val, list) else []
      elif isinstance(merged[key], list) and isinstance(val, list):
        merged[key] = merged[key] + val
      elif isinstance(merged[key], (int, float)) and isinstance(val, (int, float)):
        merged[key] = (merged[key] or 0) + (val or 0)
  return AggregatedLiabilities(liabilities=merged)


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
  tokens = _get_user_access_tokens(db, user_id)
  bank_balances_value = 0.0
  all_accounts: List[Dict[str, Any]] = []

  for access_token in tokens:
    balances_resp = plaid_service.get_balances(access_token)
    if "error" not in balances_resp:
      accounts = balances_resp.get("accounts") or []
      bank_balances_value += sum(
        float((a.get("balances") or {}).get("current") or 0.0) for a in accounts
      )
      all_accounts.extend(accounts)

  account_info: Dict[str, Any] = {"accounts": all_accounts} if all_accounts else {}
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

