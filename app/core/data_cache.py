"""
Unified cache for market data, tool responses, and external API results.
Supports time series (OHLCV, aggregates) and punctual (snapshots, fundamentals, news, quotes).
Auditable via source/kind and optional logging. Uses DB when session provided, else in-memory.
TTL values are configurable via CACHE_TTL_* environment variables (see app.core.config).
"""

from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# TTL (seconds). From CACHE_TTL_* env vars via settings; fallback if attribute missing.
TTL_OHLCV_1D = getattr(settings, "CACHE_TTL_OHLCV_1D", 7 * 24 * 3600)
TTL_OHLCV_1H = getattr(settings, "CACHE_TTL_OHLCV_1H", 24 * 3600)
TTL_OHLCV_15M = getattr(settings, "CACHE_TTL_OHLCV_15M", 4 * 3600)
TTL_SNAPSHOT = getattr(settings, "CACHE_TTL_SNAPSHOT", 90)
TTL_FUNDAMENTAL = getattr(settings, "CACHE_TTL_FUNDAMENTAL", 24 * 3600)
TTL_NEWS = getattr(settings, "CACHE_TTL_NEWS", 30 * 60)
TTL_WEB_SEARCH = getattr(settings, "CACHE_TTL_WEB_SEARCH", 60 * 60)
TTL_TRADING_QUOTE = getattr(settings, "CACHE_TTL_TRADING_QUOTE", 60)
TTL_BACKTEST = getattr(settings, "CACHE_TTL_BACKTEST", 24 * 3600)

# Source and kind for audit
SOURCE_MARKET_DATA = "market_data"
SOURCE_BACKTEST = "backtest"
SOURCE_POLYGON = "polygon"
SOURCE_ALPHA_VANTAGE = "alpha_vantage"
SOURCE_TICKERTICK = "tickertick"
SOURCE_WEB_SEARCH = "web_search"
SOURCE_TRADING = "trading"
KIND_TIMESERIES = "timeseries"
KIND_PUNCTUAL = "punctual"

# In-memory fallback when db is None
_memory: Dict[str, tuple] = {}  # key -> (value, expires_at)
_memory_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_key(prefix: str, *parts: Any) -> str:
    """Build a cache key from prefix and parts. Hashes if too long."""
    raw = ":".join(str(p) for p in (prefix,) + parts)
    if len(raw) <= 512:
        return raw
    h = hashlib.sha256(raw.encode()).hexdigest()[:48]
    return f"{prefix}:{h}"


def get(cache_key: str, db: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """
    Get a cached value. Returns None if miss or expired.
    When db is provided, uses DataCache table; otherwise in-memory.
    """
    now = _now()
    if db is not None:
        try:
            from app.db.models import DataCache
            row = db.query(DataCache).filter(
                DataCache.cache_key == cache_key,
                DataCache.expires_at > now,
            ).first()
            if row and row.result:
                logger.debug("DataCache hit db key=%s source=%s", cache_key[:64], getattr(row, "source", ""))
                return row.result if isinstance(row.result, dict) else {"_raw": row.result}
            return None
        except Exception as e:
            logger.warning("DataCache get error: %s", e)
            return None

    with _memory_lock:
        if cache_key in _memory:
            val, exp = _memory[cache_key]
            if exp > now:
                logger.debug("DataCache hit memory key=%s", cache_key[:64])
                return val
            del _memory[cache_key]
    return None


def set(
    cache_key: str,
    value: Dict[str, Any],
    ttl_seconds: int,
    source: str,
    kind: str,
    db: Optional[Any] = None,
) -> None:
    """
    Store a value. value must be JSON-serializable (dict, list, primitives).
    When db is provided, uses DataCache table; otherwise in-memory.
    """
    expires = _now() + timedelta(seconds=ttl_seconds)
    if db is not None:
        try:
            from app.db.models import DataCache
            existing = db.query(DataCache).filter(DataCache.cache_key == cache_key).first()
            if existing:
                existing.result = value
                existing.expires_at = expires
                existing.source = source
                existing.kind = kind
            else:
                db.add(DataCache(
                    cache_key=cache_key,
                    source=source,
                    kind=kind,
                    result=value,
                    expires_at=expires,
                ))
            db.commit()
            logger.debug("DataCache set db key=%s source=%s kind=%s ttl=%ds", cache_key[:64], source, kind, ttl_seconds)
        except Exception as e:
            logger.warning("DataCache set error: %s", e)
            if db:
                try:
                    db.rollback()
                except Exception:
                    pass
        return

    with _memory_lock:
        _memory[cache_key] = (value, expires)
    logger.debug("DataCache set memory key=%s source=%s kind=%s ttl=%ds", cache_key[:64], source, kind, ttl_seconds)
