"""Market data service for stock prediction and backtesting: OHLCV from yahooquery or Alpaca."""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import pandas as pd

from app.core.config import settings
from app.core import data_cache as dc

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# TTL by timeframe for OHLCV (time series; historical is immutable)
_OHLCV_TTL = {"1D": dc.TTL_OHLCV_1D, "1d": dc.TTL_OHLCV_1D, "1H": dc.TTL_OHLCV_1H, "1h": dc.TTL_OHLCV_1H, "15Min": dc.TTL_OHLCV_15M, "15min": dc.TTL_OHLCV_15M}

# timeframe -> yahooquery interval
_YF_INTERVAL = {"1D": "1d", "1d": "1d", "1H": "1h", "1h": "1h", "15Min": "15m", "15min": "15m"}


def get_historical_data(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str = "1D",
    db: Optional["Session"] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV bars for a symbol and range.

    - When db is provided: uses DataCache (DB or in-memory) for get/set; OHLCV
      is stored as time series with TTL from _OHLCV_TTL.
    - When ALPACA_DATA_ENABLED and ALPACA_API_KEY/SECRET are set: uses Alpaca
      (alpaca.data.StockHistoricalDataClient) if alpaca-py is available.
    - Otherwise: uses yahooquery (Ticker.history). Requires yahooquery.

    Returns:
        DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume,
        or None if unconfigured or error.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    cache_key = dc.make_key("ohlcv", symbol, start.date().isoformat(), end.date().isoformat(), timeframe)
    cached = dc.get(cache_key, db)
    if cached is not None:
        return pd.read_json(io.StringIO(json.dumps(cached)), orient="split")

    # Alpaca path
    if getattr(settings, "ALPACA_DATA_ENABLED", False):
        key = getattr(settings, "ALPACA_API_KEY", None)
        secret = getattr(settings, "ALPACA_API_SECRET", None)
        if key and secret:
            df = _get_alpaca_bars(symbol, start, end, timeframe, str(key.get_secret_value()) if hasattr(key, "get_secret_value") else str(key), str(secret.get_secret_value()) if hasattr(secret, "get_secret_value") else str(secret))
            if df is not None and not df.empty:
                _set_ohlcv_cache(cache_key, df, timeframe, db)
                return df
            logger.debug("Alpaca returned no data for %s, falling back to yahooquery", symbol)

    # yahooquery path
    df = _get_yahooquery_bars(symbol, start, end, timeframe)
    if df is not None and not df.empty:
        _set_ohlcv_cache(cache_key, df, timeframe, db)
    return df


def _set_ohlcv_cache(cache_key: str, df: pd.DataFrame, timeframe: str, db: Optional["Session"]) -> None:
    val = json.loads(df.to_json(orient="split", date_format="iso"))
    ttl = _OHLCV_TTL.get(timeframe, dc.TTL_OHLCV_1D)
    dc.set(cache_key, val, ttl, dc.SOURCE_MARKET_DATA, dc.KIND_TIMESERIES, db)


def _get_yahooquery_bars(symbol: str, start: datetime, end: datetime, timeframe: str) -> Optional[pd.DataFrame]:
    try:
        from yahooquery import Ticker
    except ImportError:
        logger.warning("yahooquery not installed; cannot fetch market data")
        return None

    interval = _YF_INTERVAL.get(timeframe, "1d")
    try:
        t = Ticker(symbol)
        df = t.history(start=start, end=end, interval=interval)
        if df is None or df.empty:
            return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel(0)
        df = df.sort_index()
        # normalize to Open, High, Low, Close, Volume
        col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        for k, v in col_map.items():
            if k in df.columns and v not in df.columns:
                df[v] = df[k]
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            if c not in df.columns:
                return None
        return df[["Open", "High", "Low", "Close", "Volume"]].copy()
    except Exception as e:
        logger.warning("yahooquery history failed for %s: %s", symbol, e)
        return None


def _get_alpaca_bars(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str,
    api_key: str,
    api_secret: str,
) -> Optional[pd.DataFrame]:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from alpaca.data.enums import Adjustment, Sort
    except ImportError:
        logger.debug("alpaca-py not installed; cannot use Alpaca for market data")
        return None

    tf_map = {
        "1D": TimeFrame(1, TimeFrameUnit.Day),
        "1d": TimeFrame(1, TimeFrameUnit.Day),
        "1H": TimeFrame(1, TimeFrameUnit.Hour),
        "1h": TimeFrame(1, TimeFrameUnit.Hour),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "15min": TimeFrame(15, TimeFrameUnit.Minute),
    }
    tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))

    try:
        client = StockHistoricalDataClient(api_key, api_secret)
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=start,
            end=end,
            limit=10_000,
            sort=Sort.Asc,
            adjustment=Adjustment.ALL,
        )
        bars = client.get_stock_bars(req)
        if bars is None:
            return None
        df = bars.df
        if df is None or df.empty:
            return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel(0)
        df = df.sort_index()
        col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        for k, v in col_map.items():
            if k in df.columns and v not in df.columns:
                df[v] = df[k]
        if not all(c in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]):
            return None
        return df[["Open", "High", "Low", "Close", "Volume"]].copy()
    except Exception as e:
        logger.warning("Alpaca get_stock_bars failed for %s: %s", symbol, e)
        return None
