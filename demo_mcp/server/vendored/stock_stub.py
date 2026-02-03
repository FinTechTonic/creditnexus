"""
Vendored stock prediction (daily, technical strategy) and backtest.
Uses CreditNexus logic: market_data (yahooquery), trading_strategies, backtesting.
When data is unavailable or yahooquery fails, falls back to deterministic stub response shapes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _stub_forecast(symbol: str, horizon: int) -> dict:
    """Fallback when market data unavailable: deterministic stub shape."""
    seed = hash((symbol.upper(), horizon)) % (2**31)
    forecast = [(seed % 1000) / 1000.0 + (i * 0.001) for i in range(horizon)]
    return {"forecast": forecast, "model_id": "standalone-stub", "symbol": symbol}


def _stub_backtest_result(symbol: str, strategy: Optional[str]) -> dict:
    """Fallback when backtest has insufficient data: stub shape."""
    return {
        "total_return": 0.02,
        "sharpe_ratio": 0.5,
        "max_drawdown": -0.05,
        "win_rate": 0.55,
        "n_trades": 10,
        "equity_curve": [100_000.0, 102_000.0],
        "trades": [],
        "metadata": {"strategy": strategy or "combined", "symbol": symbol},
    }


def stub_daily(symbol: str, horizon: int = 30) -> dict:
    """
    Daily prediction using CreditNexus technical strategy: get_historical_data + get_trading_signals + extend last close.
    Falls back to stub if yahooquery/data unavailable. Returns {"forecast": list[float], "model_id": str, "symbol": str, ...}.
    """
    try:
        try:
            from server.vendored.market_data import get_historical_data
            from server.vendored.trading_strategies import get_trading_signals
        except ImportError:
            from demo_mcp.server.vendored.market_data import get_historical_data
            from demo_mcp.server.vendored.trading_strategies import get_trading_signals
        end = datetime.now(timezone.utc)
        lookback_days = 252
        start = end - timedelta(days=lookback_days)
        df = get_historical_data(symbol, start, end, timeframe="1D", db=None)
        if df is None or df.empty or len(df) < 2:
            return _stub_forecast(symbol, horizon)
        if "Close" not in df.columns and "close" in df.columns:
            df["Close"] = df["close"]
        if "Open" not in df.columns and "open" in df.columns:
            df["Open"] = df["open"]
        res = get_trading_signals(df, "combined")
        col = "Close" if "Close" in df.columns else "close"
        last = float(df[col].iloc[-1])
        forecast = [last] * horizon
        return {
            "forecast": forecast,
            "model_id": "technical",
            "symbol": symbol,
            "strategy": "technical",
            "signal": res.get("consensus", res).get("signal", res.get("signal")),
        }
    except Exception as e:
        logger.warning("stub_daily vendored path failed for %s: %s; using stub", symbol, e)
        return _stub_forecast(symbol, horizon)


def stub_backtest(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    strategy: Optional[str] = "chronos",
) -> dict:
    """
    Backtest using CreditNexus run_backtest_from_data_source (yahooquery + trading_strategies).
    strategy "chronos" maps to "combined" for vendored logic. Falls back to stub if insufficient data.
    Returns main-app shape: total_return, sharpe_ratio, max_drawdown, win_rate, n_trades, equity_curve, trades, metadata.
    """
    try:
        try:
            from server.vendored.backtesting import run_backtest_from_data_source
        except ImportError:
            from demo_mcp.server.vendored.backtesting import run_backtest_from_data_source
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=365)
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        bt_strategy = "combined" if (strategy == "chronos" or not strategy) else (strategy or "combined")
        res = run_backtest_from_data_source(
            symbol, start, end,
            strategy=bt_strategy,
            timeframe="1d",
            initial_capital=100_000.0,
            db=None,
        )
        if res.metadata.get("error") == "Insufficient data":
            return _stub_backtest_result(symbol, strategy)
        return {
            "total_return": res.total_return,
            "sharpe_ratio": res.sharpe_ratio,
            "max_drawdown": res.max_drawdown,
            "win_rate": res.win_rate,
            "n_trades": res.n_trades,
            "equity_curve": res.equity_curve or [],
            "trades": res.trades or [],
            "metadata": {**res.metadata, "strategy": strategy or "chronos"},
        }
    except Exception as e:
        logger.warning("stub_backtest vendored path failed for %s: %s; using stub", symbol, e)
        return _stub_backtest_result(symbol, strategy)
