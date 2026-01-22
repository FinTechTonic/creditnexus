"""
Backtesting for trading strategies and prediction-assisted signals.

Supports signal strategies: trend, mean_reversion, momentum, volatility, stat_arb, combined.
Data: app.services.market_data_service.get_historical_data (yahooquery or Alpaca via settings).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.core import data_cache as dc
from app.stock_prediction_core.trading_strategies import STRATEGIES, get_trading_signals

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    n_trades: int
    equity_curve: Optional[List[float]] = None
    trades: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    m = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    d = df.copy()
    for l, u in m.items():
        if l in d.columns and u not in d.columns:
            d[u] = d[l]
    return d


def run_backtest(
    df: pd.DataFrame,
    strategy: str = "combined",
    initial_capital: float = 100_000.0,
    position_pct: float = 1.0,
    min_bars_for_signal: int = 126,
) -> BacktestResult:
    """
    Run a long-only backtest on OHLCV data using a signal strategy.
    """
    df = _ensure_ohlcv(df).sort_index()
    if strategy not in STRATEGIES:
        strategy = "combined"

    cash = initial_capital
    position = 0.0
    entry_price = 0.0
    equity_curve = [initial_capital]
    trades: List[Dict[str, Any]] = []
    Close = "Close" if "Close" in df.columns else "close"
    Open = "Open" if "Open" in df.columns else "open"

    for i in range(min_bars_for_signal, len(df) - 1):
        window = df.iloc[: i + 1]
        res = get_trading_signals(window, strategy)
        signal = res.get("consensus", res).get("signal", res.get("signal", "neutral"))
        if isinstance(signal, dict):
            signal = signal.get("signal", "neutral")

        next_open = float(df.iloc[i + 1][Open])
        next_close = float(df.iloc[i + 1][Close])

        if position > 0 and signal in ("bearish", "neutral"):
            proceeds = next_open * position
            cash += proceeds
            pnl = proceeds - (entry_price * position)
            equity = cash
            trades.append({"side": "sell", "price": next_open, "shares": position, "pnl": pnl, "equity": equity})
            position = 0.0

        if position == 0 and signal == "bullish":
            cost = min(cash * position_pct, cash)
            position = cost / next_open if next_open > 0 else 0.0
            entry_price = next_open
            cash -= cost
            if position > 0:
                trades.append({"side": "buy", "price": next_open, "shares": position, "cost": cost})

        equity = cash + position * next_close
        equity_curve.append(equity)

    if position > 0 and len(df) > 0:
        last_price = float(df.iloc[-1][Close])
        proceeds = last_price * position
        cash += proceeds
        trades.append({"side": "sell", "price": last_price, "shares": position, "pnl": proceeds - entry_price * position, "equity": cash})
        position = 0.0
    equity = cash

    if len(equity_curve) > 0:
        equity = equity_curve[-1]
    total_return = (equity - initial_capital) / initial_capital if initial_capital else 0.0
    ec = np.array(equity_curve)
    returns = np.diff(ec) / ec[:-1]
    returns = returns[~np.isnan(returns)]
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 0 and np.std(returns) > 0 else 0.0
    peak = np.maximum.accumulate(ec)
    dd = (ec - peak) / peak
    max_drawdown = float(np.min(dd)) if len(dd) > 0 else 0.0

    sell_trades = [t for t in trades if t.get("side") == "sell" and "pnl" in t]
    n = len(sell_trades)
    wins = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
    win_rate = wins / n if n > 0 else 0.0

    return BacktestResult(
        total_return=total_return,
        sharpe_ratio=sharpe,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        n_trades=len(trades),
        equity_curve=equity_curve,
        trades=trades,
        metadata={"strategy": strategy, "initial_capital": initial_capital, "final_equity": equity},
    )


def run_backtest_from_data_source(
    symbol: str,
    start: datetime,
    end: datetime,
    strategy: str = "combined",
    timeframe: str = "1d",
    initial_capital: float = 100_000.0,
    db: Optional[Any] = None,
) -> BacktestResult:
    """
    Load OHLCV via app.services.market_data_service.get_historical_data, then run_backtest.
    When db is provided, results are cached with TTL_BACKTEST.
    """
    from app.services.market_data_service import get_historical_data

    start_d = start.date().isoformat() if hasattr(start, "date") else str(start)[:10]
    end_d = end.date().isoformat() if hasattr(end, "date") else str(end)[:10]
    cache_key = dc.make_key("backtest", symbol, start_d, end_d, strategy, timeframe, initial_capital)
    cached = dc.get(cache_key, db)
    if cached is not None:
        return BacktestResult(**cached)

    tf_map = {"1d": "1D", "1h": "1H", "15m": "15Min"}
    tf = tf_map.get(timeframe.lower(), "1D")
    df = get_historical_data(symbol, start, end, timeframe=tf, db=db)

    if df is None or df.empty or len(df) < 130:
        return BacktestResult(
            total_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            n_trades=0,
            metadata={"error": "Insufficient data", "symbol": symbol, "strategy": strategy},
        )

    res = run_backtest(df, strategy=strategy, initial_capital=initial_capital)
    dc.set(cache_key, asdict(res), dc.TTL_BACKTEST, dc.SOURCE_BACKTEST, dc.KIND_PUNCTUAL, db)
    return res
