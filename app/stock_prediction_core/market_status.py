"""Market status: is_open, next_trading_day, time_until_open/close for MARKET_CONFIGS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.stock_prediction_core.constants import MARKET_CONFIGS


@dataclass
class MarketStatus:
    """Market status for a given market key."""

    is_open: bool
    status_text: str
    next_trading_day: str
    last_updated: str
    time_until_open: str
    time_until_close: str
    current_time_et: str
    market_name: str
    market_type: str
    market_symbol: str


def _zone(market_key: str):
    tz = MARKET_CONFIGS.get(market_key, {}).get("timezone", "US/Eastern")
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz)
    except Exception:
        from datetime import timezone
        return timezone.utc


def _get_next_trading_day(current: datetime, trading_days: list) -> datetime:
    next_day = current + timedelta(days=1)
    while next_day.weekday() not in trading_days:
        next_day += timedelta(days=1)
    return next_day


def _format_td(td: timedelta) -> str:
    s = int(td.total_seconds())
    if s < 0:
        return "N/A"
    d, r = divmod(s, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    if d > 0:
        return f"{d}d {h}h {m}m"
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def _get_time_until_open(current: datetime, market_open: datetime, config: dict) -> str:
    if config.get("type") in ("futures", "forex", "crypto", "commodities"):
        return "N/A (24/7 Market)"
    days = config.get("days", [0, 1, 2, 3, 4])
    if current.weekday() not in days:
        nd = 1
        while (current + timedelta(days=nd)).weekday() not in days:
            nd += 1
        nxt = current + timedelta(days=nd)
        ho, mo = map(int, config.get("open_time", "09:30").split(":"))
        next_open = nxt.replace(hour=ho, minute=mo, second=0, microsecond=0)
        return _format_td(next_open - current)
    if current < market_open:
        return _format_td(market_open - current)
    tom = current + timedelta(days=1)
    if tom.weekday() in days:
        ho, mo = map(int, config.get("open_time", "09:30").split(":"))
        next_open = tom.replace(hour=ho, minute=mo, second=0, microsecond=0)
        return _format_td(next_open - current)
    nd = 1
    while (current + timedelta(days=nd)).weekday() not in days:
        nd += 1
    nxt = current + timedelta(days=nd)
    ho, mo = map(int, config.get("open_time", "09:30").split(":"))
    next_open = nxt.replace(hour=ho, minute=mo, second=0, microsecond=0)
    return _format_td(next_open - current)


def _get_time_until_close(current: datetime, market_close: datetime, config: dict) -> str:
    if config.get("type") in ("futures", "forex", "crypto", "commodities"):
        return "N/A (24/7 Market)"
    if current.weekday() not in config.get("days", [0, 1, 2, 3, 4]):
        return "N/A (Weekend)"
    if current < market_close:
        return _format_td(market_close - current)
    return "Market closed for today"


def get_market_status(market_key: str = "US_STOCKS") -> MarketStatus:
    """Compute MarketStatus for the given market key."""
    config = MARKET_CONFIGS.get(market_key, MARKET_CONFIGS["US_STOCKS"])
    tz = _zone(market_key)
    now = datetime.now(tz)

    ho, mo = map(int, config.get("open_time", "09:30").split(":"))
    hc, mc = map(int, config.get("close_time", "16:00").split(":"))
    market_open = now.replace(hour=ho, minute=mo, second=0, microsecond=0)
    market_close = now.replace(hour=hc, minute=mc, second=0, microsecond=0)
    days = config.get("days", [0, 1, 2, 3, 4])
    is_trading_day = now.weekday() in days

    if config.get("type") in ("futures", "forex", "crypto", "commodities"):
        is_open = True
        status_text = f"{config['name']} is currently open (24/7)"
    elif not is_trading_day:
        is_open = False
        status_text = f"{config['name']} is closed (Weekend)"
    elif market_open <= now <= market_close:
        is_open = True
        status_text = f"{config['name']} is currently open"
    else:
        is_open = False
        status_text = f"{config['name']} is closed (Before opening)" if now < market_open else f"{config['name']} is closed (After closing)"

    next_trading_day = _get_next_trading_day(now, days)
    time_until_open = _get_time_until_open(now, market_open, config)
    time_until_close = _get_time_until_close(now, market_close, config)

    return MarketStatus(
        is_open=is_open,
        status_text=status_text,
        next_trading_day=next_trading_day.strftime("%Y-%m-%d"),
        last_updated=now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        time_until_open=time_until_open,
        time_until_close=time_until_close,
        current_time_et=now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        market_name=config["name"],
        market_type=config["type"],
        market_symbol=config["symbol"],
    )
