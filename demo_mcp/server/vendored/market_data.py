"""
Vendored market data: OHLCV from yahooquery only (no Alpaca, no DB cache).
Matches CreditNexus app.services.market_data_service behavior for get_historical_data.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

MIN_SYMBOL_LENGTH = 2
MAX_SYMBOL_LENGTH = 10
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.]+$")
MAX_HISTORICAL_DAYS = 3650
_YF_INTERVAL = {"1D": "1d", "1d": "1d", "1H": "1h", "1h": "1h", "15Min": "15m", "15min": "15m"}


def is_valid_symbol(symbol: str) -> bool:
    if not symbol or not isinstance(symbol, str):
        return False
    symbol = symbol.strip().upper()
    if len(symbol) < MIN_SYMBOL_LENGTH or len(symbol) > MAX_SYMBOL_LENGTH:
        return False
    return bool(SYMBOL_PATTERN.match(symbol))


def validate_date_range(start: datetime, end: datetime) -> tuple[bool, Optional[str]]:
    now = datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        return False, "Start date must be before end date"
    if (end - start).days > MAX_HISTORICAL_DAYS:
        return False, f"Date range cannot exceed {MAX_HISTORICAL_DAYS} days"
    return True, None


def get_historical_data(
    symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str = "1D",
    db: Optional[object] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV via yahooquery Ticker.history. No cache, no Alpaca.
    Returns DataFrame with Open, High, Low, Close, Volume or None.
    """
    if not is_valid_symbol(symbol):
        logger.debug("Invalid symbol format: %s", symbol)
        return None
    symbol = symbol.strip().upper()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    ok, err = validate_date_range(start, end)
    if not ok:
        logger.warning("Invalid date range for %s: %s", symbol, err)
        return None
    try:
        from yahooquery import Ticker
    except ImportError:
        logger.warning("yahooquery not installed; cannot fetch market data")
        return None
    interval = _YF_INTERVAL.get(timeframe, "1d")
    try:
        t = Ticker(symbol)
        start_date = start.date() if hasattr(start, "date") else start
        end_date = end.date() if hasattr(end, "date") else end
        today = datetime.now(timezone.utc).date()
        if end_date > today:
            end_date = today
        if start_date > end_date:
            start_date = end_date - timedelta(days=1)
        df = t.history(start=start_date, end=end_date, interval=interval)
        if df is None or df.empty:
            return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel(0)
        df = df.sort_index()
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
