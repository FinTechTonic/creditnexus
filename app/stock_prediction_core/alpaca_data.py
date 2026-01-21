"""
Alpaca historical bar data for stock prediction and backtesting.

When ALPACA_DATA_ENABLED and ALPACA_API_KEY/SECRET are set, get_historical_bars
and get_stock_bars can replace yfinance in get_historical_data and backtesting.

Requires: alpaca-py (StockHistoricalDataClient, StockBarsRequest, TimeFrame, etc.)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    from alpaca.data.enums import Adjustment, Sort

    ALPACA_DATA_AVAILABLE = True
except ImportError:
    ALPACA_DATA_AVAILABLE = False


def get_stock_bars(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str = "1D",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    limit: int = 10_000,
) -> Optional[object]:
    """
    Fetch OHLCV bars from Alpaca for a symbol and range.

    Args:
        symbol: Ticker (e.g. "AAPL").
        start: Start datetime (prefer timezone-aware UTC).
        end: End datetime (prefer timezone-aware UTC).
        timeframe: "1Min", "5Min", "15Min", "1H", "1D".
        api_key: Alpaca API key (or from env/config).
        api_secret: Alpaca secret.
        limit: Max bars to return.

    Returns:
        BarSet (alpaca.data.models.BarSet) or None if unconfigured/error.
    """
    if not ALPACA_DATA_AVAILABLE or not api_key or not api_secret:
        return None

    tf_map = {
        "1Min": TimeFrame(1, TimeFrameUnit.Minute),
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1H": TimeFrame(1, TimeFrameUnit.Hour),
        "1D": TimeFrame(1, TimeFrameUnit.Day),
    }
    tf = tf_map.get(timeframe) or TimeFrame(1, TimeFrameUnit.Day)

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    try:
        client = StockHistoricalDataClient(api_key, api_secret)
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
            sort=Sort.Asc,
            adjustment=Adjustment.ALL,
        )
        bars = client.get_stock_bars(req)
        return bars
    except Exception as e:
        logger.warning("Alpaca get_stock_bars failed for %s: %s", symbol, e)
        return None


def get_historical_bars_as_dataframe(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str = "1D",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> Optional[object]:
    """
    Fetch Alpaca bars and return a DataFrame with columns aligned to yfinance:
    Open, High, Low, Close, Volume (and index = timestamp).
    """
    bars = get_stock_bars(symbol, start, end, timeframe, api_key, api_secret)
    if bars is None:
        return None

    try:
        import pandas as pd

        df = bars.df
        if df is None or df.empty:
            return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel(0)
        df = df.sort_index()
        col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        required = ["Open", "High", "Low", "Close", "Volume"]
        if all(c in df.columns for c in required):
            return df[required].copy()
        return df
    except Exception as e:
        logger.warning("Alpaca bars to DataFrame failed for %s: %s", symbol, e)
        return None
