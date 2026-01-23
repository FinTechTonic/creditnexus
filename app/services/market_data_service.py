"""Market data service for stock prediction and backtesting: OHLCV from yahooquery or Alpaca."""

from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING

import pandas as pd

from app.core.config import settings
from app.core import data_cache as dc

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Symbol validation constants
MIN_SYMBOL_LENGTH = 2  # Minimum valid symbol length (e.g., "AA" is valid, "A" is not)
MAX_SYMBOL_LENGTH = 10  # Maximum reasonable symbol length
SYMBOL_PATTERN = re.compile(r'^[A-Z0-9.]+$')  # Alphanumeric and dots only

# Date validation constants
MAX_HISTORICAL_DAYS = 3650  # ~10 years
MAX_FUTURE_DAYS = 1  # Allow 1 day in future for timezone differences

# TTL by timeframe for OHLCV (time series; historical is immutable)
_OHLCV_TTL = {"1D": dc.TTL_OHLCV_1D, "1d": dc.TTL_OHLCV_1D, "1H": dc.TTL_OHLCV_1H, "1h": dc.TTL_OHLCV_1H, "15Min": dc.TTL_OHLCV_15M, "15min": dc.TTL_OHLCV_15M}

# timeframe -> yahooquery interval
_YF_INTERVAL = {"1D": "1d", "1d": "1d", "1H": "1h", "1h": "1h", "15Min": "15m", "15min": "15m"}


def is_valid_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        True if symbol is valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    symbol = symbol.strip().upper()
    
    # Check length
    if len(symbol) < MIN_SYMBOL_LENGTH or len(symbol) > MAX_SYMBOL_LENGTH:
        return False
    
    # Check format (alphanumeric and dots only)
    if not SYMBOL_PATTERN.match(symbol):
        return False
    
    return True


def validate_date_range(start: datetime, end: datetime) -> tuple[bool, Optional[str]]:
    """
    Validate date range for market data queries.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    now = datetime.now(timezone.utc)
    
    # Ensure timezone-aware
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
    # Check if start is after end
    if start >= end:
        return False, "Start date must be before end date"
    
    # Check if end is too far in the future
    max_future = now + timedelta(days=MAX_FUTURE_DAYS)
    if end > max_future:
        return False, f"End date cannot be more than {MAX_FUTURE_DAYS} day(s) in the future"
    
    # Check if range is too large
    days_diff = (end - start).days
    if days_diff > MAX_HISTORICAL_DAYS:
        return False, f"Date range cannot exceed {MAX_HISTORICAL_DAYS} days"
    
    # Check if start is too far in the past (optional, but reasonable limit)
    min_past = now - timedelta(days=MAX_HISTORICAL_DAYS)
    if start < min_past:
        return False, f"Start date cannot be more than {MAX_HISTORICAL_DAYS} days in the past"
    
    return True, None


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

    Note: For Alpaca free accounts, automatically adjusts end date to avoid
    15-minute restriction (free accounts cannot query last 15 minutes).

    Returns:
        DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume,
        or None if unconfigured or error.
    """
    # Validate symbol
    if not is_valid_symbol(symbol):
        logger.debug("Invalid symbol format: %s (skipping API call)", symbol)
        return None
    
    # Normalize symbol to uppercase
    symbol = symbol.strip().upper()
    
    # Ensure timezone-aware
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
    # Store original end date for cache key (before any adjustments)
    original_end = end
    
    # For Alpaca free accounts: adjust end date to avoid 15-minute restriction
    # Free accounts cannot query data from the last 15 minutes
    key = getattr(settings, "ALPACA_API_KEY", None)
    secret = getattr(settings, "ALPACA_API_SECRET", None)
    use_alpaca = getattr(settings, "ALPACA_DATA_ENABLED", False) or (key is not None and secret is not None)
    
    if use_alpaca and key and secret:
        # Check if end date is too recent (within last 15 minutes)
        now = datetime.now(timezone.utc)
        time_since_end = (now - end).total_seconds() / 60  # minutes
        if time_since_end < 16:  # Less than 16 minutes ago
            # Adjust end date to 16 minutes ago to avoid Alpaca free account restriction
            adjusted_end = now - timedelta(minutes=16)
            if adjusted_end <= start:
                # If adjusted end is at or before start, we need a valid range
                # Set start to 1 day before adjusted end to ensure we have a valid range
                start = adjusted_end - timedelta(days=1)
            logger.debug("Adjusted end date for Alpaca free account restriction: original=%s, adjusted=%s (now=%s, time_since_end=%.1f min)", 
                        original_end.isoformat(), adjusted_end.isoformat(), now.isoformat(), time_since_end)
            end = adjusted_end
    
    # Validate date range (after potential adjustment)
    is_valid, error_msg = validate_date_range(start, end)
    if not is_valid:
        logger.warning("Invalid date range for symbol %s: %s", symbol, error_msg)
        return None

    # Use original end date for cache key to maintain cache consistency
    # The actual API call will use the adjusted end date if needed
    cache_key = dc.make_key("ohlcv", symbol, start.date().isoformat(), original_end.date().isoformat(), timeframe)
    cached = dc.get(cache_key, db)
    if cached is not None:
        return pd.read_json(io.StringIO(json.dumps(cached)), orient="split")

    # Alpaca path - use Alpaca if DATA_ENABLED is True OR if trading is enabled (API keys set)
    # This ensures trading-related market data always uses Alpaca when trading is configured
    key = getattr(settings, "ALPACA_API_KEY", None)
    secret = getattr(settings, "ALPACA_API_SECRET", None)
    use_alpaca = getattr(settings, "ALPACA_DATA_ENABLED", False) or (key is not None and secret is not None)
    
    if use_alpaca and key and secret:
        df = _get_alpaca_bars(symbol, start, end, timeframe, str(key.get_secret_value()) if hasattr(key, "get_secret_value") else str(key), str(secret.get_secret_value()) if hasattr(secret, "get_secret_value") else str(secret))
        if df is not None and not df.empty:
            _set_ohlcv_cache(cache_key, df, timeframe, db)
            return df
        # For historical data (not real-time), allow fallback to yahooquery if Alpaca returns no data
        # This ensures charts and backtesting work even if Alpaca subscription doesn't cover the data
        logger.warning("Alpaca is configured but returned no data for %s (start=%s, end=%s). Falling back to yahooquery for historical data.", 
                      symbol, start.isoformat(), end.isoformat())
        # Continue to yahooquery fallback below

    # yahooquery path - only use if Alpaca is NOT configured at all
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
        # Fix yahooquery datetime comparison issue: convert datetime to date
        # Also ensure end_date is not in the future (yahooquery doesn't like future dates)
        start_date = start.date() if hasattr(start, 'date') else start
        end_date = end.date() if hasattr(end, 'date') else end
        today = datetime.now(timezone.utc).date()
        if end_date > today:
            logger.debug("Adjusted yahooquery end_date from %s to %s (today)", end_date, today)
            end_date = today
        # Ensure start_date is not after end_date
        if start_date > end_date:
            logger.warning("yahooquery: start_date %s is after end_date %s, adjusting start_date", start_date, end_date)
            start_date = end_date - timedelta(days=1)
        logger.debug("yahooquery: fetching %s from %s to %s (interval=%s)", symbol, start_date, end_date, interval)
        df = t.history(start=start_date, end=end_date, interval=interval)
        if df is None or df.empty:
            logger.warning("yahooquery returned None or empty DataFrame for %s (start=%s, end=%s, interval=%s)", 
                          symbol, start_date, end_date, interval)
            return None
        logger.debug("yahooquery: retrieved %d rows for %s", len(df), symbol)
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
        # StockHistoricalDataClient uses data.alpaca.markets by default (same for paper and live)
        # No need to specify base_url as it's separate from trading API
        client = StockHistoricalDataClient(api_key, api_secret)
        
        # Ensure datetimes are timezone-aware (Alpaca expects UTC)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=start,
            end=end,
            limit=10_000,
            sort=Sort.Asc,
            adjustment=Adjustment.ALL,
        )
        
        logger.debug("Alpaca API call: symbol=%s, start=%s (UTC), end=%s (UTC), timeframe=%s", 
                    symbol, start.isoformat(), end.isoformat(), timeframe)
        try:
            bars = client.get_stock_bars(req)
        except Exception as api_error:
            logger.warning("Alpaca API exception for %s: %s (start=%s, end=%s, timeframe=%s). "
                          "This may indicate API key issues, subscription limitations, or network problems.",
                          symbol, api_error, start.isoformat(), end.isoformat(), timeframe, exc_info=True)
            return None
        
        if bars is None:
            logger.warning("Alpaca get_stock_bars returned None for %s (start=%s, end=%s, timeframe=%s). "
                          "Possible causes: symbol not available, invalid date range, API access issue, or subscription limitations (Basic plan cannot query last 15 minutes).", 
                          symbol, start.isoformat(), end.isoformat(), timeframe)
            return None
        
        # Check if bars object has data
        if not hasattr(bars, 'df'):
            logger.warning("Alpaca bars object missing 'df' attribute for %s", symbol)
            return None
            
        df = bars.df
        if df is None or df.empty:
            logger.warning("Alpaca get_stock_bars returned empty DataFrame for %s (start=%s, end=%s, timeframe=%s). "
                          "Symbol may not have data for this date range or timeframe.", 
                          symbol, start.isoformat(), end.isoformat(), timeframe)
            return None
        if isinstance(df.index, pd.MultiIndex):
            df = df.droplevel(0)
        df = df.sort_index()
        col_map = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
        for k, v in col_map.items():
            if k in df.columns and v not in df.columns:
                df[v] = df[k]
        if not all(c in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]):
            logger.warning("Alpaca get_stock_bars DataFrame missing required columns for %s. Columns: %s", 
                          symbol, list(df.columns))
            return None
        return df[["Open", "High", "Low", "Close", "Volume"]].copy()
    except Exception as e:
        logger.warning("Alpaca get_stock_bars failed for %s: %s (start=%s, end=%s, timeframe=%s)", 
                      symbol, e, start, end, timeframe, exc_info=True)
        return None
