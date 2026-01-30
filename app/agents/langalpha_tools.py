"""LangAlpha tools ported from dev/LangAlpha-master.

Tools for quantitative financial analysis:
- Market data (Polygon API)
- Fundamental data (Alpha Vantage)
- Web search (using vendored WebSearchService instead of Tavily)
- News search (using vendored WebSearchService)
- Tickertick news
- Browser automation (Playwright)
- Python REPL for calculations
- Trading strategies

Follows repository patterns:
- Uses existing LLM client abstraction
- Integrates with WebSearchService
- Error handling and retries
- CDM event generation
"""

import logging
import os
import time
import json
from typing import Optional, Dict, Any, List, Literal
from datetime import date, datetime, timedelta
import asyncio
from contextvars import ContextVar

import pandas as pd
import numpy as np

from langchain_core.tools import tool, Tool
from langchain_experimental.utilities import PythonREPL
from polygon.rest import RESTClient
from alpha_vantage.fundamentaldata import FundamentalData
from yahooquery import Ticker
import httpx

from app.core.config import settings
from app.core import data_cache as dc
from app.core.llm_client import get_chat_model
from app.services.web_search_service import WebSearchService, get_web_search_service
from app.utils.audit import log_audit_action
from app.db.models import AuditAction, UserByokKey

logger = logging.getLogger(__name__)


def _to_json_serializable(obj: Any) -> Any:
    """Convert DataFrame, numpy types, and nested structures for json.dumps."""
    if isinstance(obj, pd.DataFrame):
        rows = obj.to_dict(orient="records")
        return [
            {k: (None if (isinstance(v, float) and (v != v)) else v) for k, v in r.items()}
            for r in rows
        ]
    if hasattr(obj, "item") and callable(obj.item):  # numpy scalar
        return obj.item()
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_serializable(x) for x in obj]
    return obj


# Context variables for audit logging (set by graph nodes)
_audit_db: ContextVar[Optional[Any]] = ContextVar('audit_db', default=None)
_audit_user_id: ContextVar[Optional[int]] = ContextVar('audit_user_id', default=None)
_audit_analysis_id: ContextVar[Optional[str]] = ContextVar('audit_analysis_id', default=None)

def set_audit_context(db: Optional[Any] = None, user_id: Optional[int] = None, analysis_id: Optional[str] = None):
    """Set audit context for tool execution."""
    if db is not None:
        _audit_db.set(db)
    if user_id is not None:
        _audit_user_id.set(user_id)
    if analysis_id is not None:
        _audit_analysis_id.set(analysis_id)

def _log_tool_usage(tool_name: str, params: Dict[str, Any], success: bool = True, error: Optional[str] = None):
    """Log tool usage for audit purposes."""
    db = _audit_db.get()
    user_id = _audit_user_id.get()
    analysis_id = _audit_analysis_id.get()
    
    if db and user_id:
        try:
            log_audit_action(
                db=db,
                action=AuditAction.CREATE,
                target_type="agent_tool_usage",
                target_id=None,
                user_id=user_id,
                metadata={
                    "tool_name": tool_name,
                    "analysis_id": analysis_id,
                    "params": params,
                    "success": success,
                    "error": error
                }
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log tool usage for {tool_name}: {e}")
    else:
        # Log to standard logger if audit context not available
        logger.info(f"Tool usage: {tool_name} with params: {params}, success: {success}")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds

# Initialize services
_web_search_service: Optional[WebSearchService] = None

def get_web_search_service_instance() -> WebSearchService:
    """Get or create WebSearchService instance."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = get_web_search_service()
    return _web_search_service


# ============================================================================
# Market Data Tools (Polygon API)
# ============================================================================

def _get_polygon_client() -> Optional[RESTClient]:
    """Get Polygon REST client. Prefer user BYOK key when audit context has user_id and db."""
    api_key = None
    user_id = _audit_user_id.get()
    db = _audit_db.get()
    if user_id and db:
        row = (
            db.query(UserByokKey)
            .filter(
                UserByokKey.user_id == user_id,
                UserByokKey.provider == "polygon",
            )
            .first()
        )
        if row and getattr(row, "credentials_encrypted", None) and isinstance(row.credentials_encrypted, dict):
            api_key = row.credentials_encrypted.get("api_key")
    if not api_key and hasattr(settings, "POLYGON_API_KEY") and settings.POLYGON_API_KEY:
        api_key = settings.POLYGON_API_KEY.get_secret_value()
    if not api_key and os.getenv("POLYGON_API_KEY"):
        api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.warning("POLYGON_API_KEY not configured. Market data tools will fail.")
        return None
    try:
        return RESTClient(api_key=api_key)
    except Exception as e:
        logger.error("Failed to initialize Polygon client: %s", e)
        return None


def _polygon_aggs_ttl(timespan: str) -> int:
    t = (timespan or "day").lower()
    if t in ("minute", "min"):
        return dc.TTL_OHLCV_15M
    if t in ("hour", "h"):
        return dc.TTL_OHLCV_1H
    return dc.TTL_OHLCV_1D


@tool
def get_market_data(
    ticker: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    timespan: str = "day",
    limit: int = 100
) -> str:
    """
    Get market data (OHLCV) for a ticker using Polygon API.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        from_date: Start date (YYYY-MM-DD format, default: 30 days ago)
        to_date: End date (YYYY-MM-DD format, default: today)
        timespan: Time span (minute, hour, day, week, month, quarter, year)
        limit: Maximum number of results (default: 100)
        
    Returns:
        JSON string with market data
    """
    params = {
        "ticker": ticker,
        "from_date": from_date,
        "to_date": to_date,
        "timespan": timespan,
        "limit": limit
    }
    
    client = _get_polygon_client()
    if not client:
        _log_tool_usage("get_market_data", params, success=False, error="Polygon API key not configured")
        return '{"error": "Polygon API key not configured"}'
    
    # Default dates
    if not to_date:
        to_date = date.today().isoformat()
    if not from_date:
        from_date = (date.today() - timedelta(days=30)).isoformat()
    
    cache_key = dc.make_key("polygon_aggs", ticker, from_date, to_date, timespan, limit)
    _db = _audit_db.get()
    cached = dc.get(cache_key, _db)
    if cached is not None:
        _log_tool_usage("get_market_data", params, success=True)
        return json.dumps(cached)
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Get aggregates
            aggs = client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan=timespan,
                from_=from_date,
                to=to_date,
                limit=limit
            )
            
            # Convert to list of dicts (values may be numpy; use _to_json_serializable for JSON)
            data = []
            for agg in aggs:
                data.append({
                    "timestamp": agg.timestamp,
                    "open": agg.open,
                    "high": agg.high,
                    "low": agg.low,
                    "close": agg.close,
                    "volume": agg.volume,
                    "vwap": agg.vwap if hasattr(agg, 'vwap') else None
                })
            
            obj = _to_json_serializable({"ticker": ticker, "data": data, "count": len(data)})
            dc.set(cache_key, obj, _polygon_aggs_ttl(timespan), dc.SOURCE_POLYGON, dc.KIND_TIMESERIES, _db)
            _log_tool_usage("get_market_data", params, success=True)
            return json.dumps(obj)
            
        except Exception as e:
            last_error = e
            logger.warning(f"Error fetching market data for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                continue
            logger.error(f"Failed to fetch market data for {ticker} after {MAX_RETRIES} attempts: {e}")
            _log_tool_usage("get_market_data", params, success=False, error=str(e))
            return f'{{"error": "Failed to fetch market data: {str(e)}"}}'


@tool
def get_ticker_snapshot(ticker: str) -> str:
    """
    Get real-time ticker snapshot using Polygon API.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        JSON string with ticker snapshot
    """
    cache_key = dc.make_key("polygon_snapshot", ticker)
    _db = _audit_db.get()
    cached = dc.get(cache_key, _db)
    if cached is not None:
        return json.dumps(cached)
    
    client = _get_polygon_client()
    if not client:
        return '{"error": "Polygon API key not configured"}'
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            snapshot = client.get_snapshot_ticker(market_type="stocks", ticker=ticker)
            
            # Convert to dict
            result = {
                "ticker": ticker,
                "day": {
                    "open": snapshot.day.open if snapshot.day else None,
                    "high": snapshot.day.high if snapshot.day else None,
                    "low": snapshot.day.low if snapshot.day else None,
                    "close": snapshot.day.close if snapshot.day else None,
                    "volume": snapshot.day.volume if snapshot.day else None,
                } if snapshot.day else None,
                "last_quote": {
                    "bid": snapshot.last_quote.bid if snapshot.last_quote else None,
                    "ask": snapshot.last_quote.ask if snapshot.last_quote else None,
                } if snapshot.last_quote else None,
                "last_trade": {
                    "price": snapshot.last_trade.price if snapshot.last_trade else None,
                    "size": snapshot.last_trade.size if snapshot.last_trade else None,
                } if snapshot.last_trade else None,
            }
            
            dc.set(cache_key, result, dc.TTL_SNAPSHOT, dc.SOURCE_POLYGON, dc.KIND_PUNCTUAL, _db)
            return json.dumps(result)
            
        except Exception as e:
            last_error = e
            logger.warning(f"Error fetching ticker snapshot for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            logger.error(f"Failed to fetch ticker snapshot for {ticker} after {MAX_RETRIES} attempts: {e}")
            return f'{{"error": "Failed to fetch ticker snapshot: {str(e)}"}}'


# ============================================================================
# Fundamental Data Tools (Alpha Vantage)
# ============================================================================

def _get_alpha_vantage_client() -> Optional[FundamentalData]:
    """Get Alpha Vantage client."""
    api_key = None
    if hasattr(settings, "ALPHA_VANTAGE_API_KEY") and settings.ALPHA_VANTAGE_API_KEY:
        api_key = settings.ALPHA_VANTAGE_API_KEY.get_secret_value()
    elif os.getenv("ALPHA_VANTAGE_API_KEY"):
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    if not api_key:
        logger.warning("ALPHA_VANTAGE_API_KEY not configured. Fundamental data tools will fail.")
        return None
    
    try:
        return FundamentalData(key=api_key, output_format='json')
    except Exception as e:
        logger.error(f"Failed to initialize Alpha Vantage client: {e}")
        return None


@tool
def get_fundamental_data(
    ticker: str,
    data_type: str = "overview"
) -> str:
    """
    Get fundamental data for a ticker using Alpha Vantage.
    
    Args:
        ticker: Stock ticker symbol
        data_type: Type of data (overview, income_statement, balance_sheet, cash_flow, earnings)
        
    Returns:
        JSON string with fundamental data
    """
    params = {
        "ticker": ticker,
        "data_type": data_type
    }
    
    if data_type not in ["overview", "income_statement", "balance_sheet", "cash_flow", "earnings"]:
        _log_tool_usage("get_fundamental_data", params, success=False, error=f"Unknown data_type: {data_type}")
        return f'{{"error": "Unknown data_type: {data_type}"}}'
    
    cache_key = dc.make_key("av_fundamental", ticker, data_type)
    _db = _audit_db.get()
    cached = dc.get(cache_key, _db)
    if cached is not None:
        _log_tool_usage("get_fundamental_data", params, success=True)
        return json.dumps(cached)
    
    client = _get_alpha_vantage_client()
    if not client:
        _log_tool_usage("get_fundamental_data", params, success=False, error="Alpha Vantage API key not configured")
        return '{"error": "Alpha Vantage API key not configured"}'
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            if data_type == "overview":
                data = client.get_company_overview(symbol=ticker)
            elif data_type == "income_statement":
                data = client.get_income_statement_annual(symbol=ticker)
            elif data_type == "balance_sheet":
                data = client.get_balance_sheet_annual(symbol=ticker)
            elif data_type == "cash_flow":
                data = client.get_cash_flow_annual(symbol=ticker)
            elif data_type == "earnings":
                data = client.get_earnings_annual(symbol=ticker)
            
            obj = _to_json_serializable(data)
            dc.set(cache_key, obj, dc.TTL_FUNDAMENTAL, dc.SOURCE_ALPHA_VANTAGE, dc.KIND_PUNCTUAL, _db)
            _log_tool_usage("get_fundamental_data", params, success=True)
            return json.dumps(obj)
            
        except Exception as e:
            last_error = e
            logger.warning(f"Error fetching fundamental data for {ticker} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            logger.error(f"Failed to fetch fundamental data for {ticker} after {MAX_RETRIES} attempts: {e}")
            _log_tool_usage("get_fundamental_data", params, success=False, error=str(e))
            return f'{{"error": "Failed to fetch fundamental data: {str(e)}"}}'


# ============================================================================
# Web Search Tools (using vendored WebSearchService)
# ============================================================================

@tool
async def web_search(
    query: str,
    search_type: Literal["search", "news"] = "search",
    num_results: int = 4
) -> str:
    """
    Search the web or news using vendored WebSearchService.
    
    This replaces Tavily search with our vendored web search service.
    
    Args:
        query: Search query
        search_type: "search" for general web search, "news" for news search
        num_results: Number of results to return (1-20, default: 4)
        
    Returns:
        JSON string with search results
    """
    params = {
        "query": query,
        "search_type": search_type,
        "num_results": num_results
    }
    
    try:
        service = get_web_search_service_instance()
        result = await service.search_web(
            query=query,
            search_type=search_type,
            num_results=num_results,
            rerank=True,
            top_k_after_rerank=num_results,
            db=_audit_db.get(),
        )
        
        # Format results for LangAlpha agents (unified shape: news has source/date, search has domain)
        formatted_results = []
        for chunk in result.get("extracted_content", []):
            formatted_results.append({
                "title": chunk.get("title", ""),
                "url": chunk.get("url", ""),
                "content": chunk.get("content", ""),
                "source": chunk.get("source") or chunk.get("domain", ""),
                "date": chunk.get("date", ""),
            })
        
        search_result = json.dumps({
            "query": query,
            "search_type": search_type,
            "results": formatted_results,
            "count": len(formatted_results)
        })
        _log_tool_usage("web_search", params, success=True)
        return search_result
        
    except Exception as e:
        logger.error(f"Error performing web search: {e}")
        _log_tool_usage("web_search", params, success=False, error=str(e))
        return f'{{"error": "Failed to perform web search: {str(e)}"}}'


# ============================================================================
# Tickertick News Tools
# ============================================================================

@tool
def get_tickertick_news(
    ticker: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 30
) -> str:
    """
    Get financial news from Tickertick API.
    
    Args:
        ticker: Stock ticker symbol (optional)
        query: Search query (optional)
        limit: Maximum number of results (default: 30)
        
    Returns:
        JSON string with news articles
    """
    # Build query
    if ticker:
        feed_query = f"z:{ticker}"  # Specific ticker news
    elif query:
        feed_query = query
    else:
        return '{"error": "Either ticker or query must be provided"}'
    
    cache_key = dc.make_key("tickertick_news", feed_query, limit)
    _db = _audit_db.get()
    cached = dc.get(cache_key, _db)
    if cached is not None:
        return json.dumps(cached)
    
    api_key = None
    if hasattr(settings, "TICKERTICK_API_KEY") and settings.TICKERTICK_API_KEY:
        api_key = settings.TICKERTICK_API_KEY.get_secret_value()
    elif os.getenv("TICKERTICK_API_KEY"):
        api_key = os.getenv("TICKERTICK_API_KEY")
    
    if not api_key:
        return '{"error": "Tickertick API key not configured"}'
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Call Tickertick API
            url = f"https://api.tickertick.com/feed?q={feed_query}&n={limit}"
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            
            response = httpx.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert timestamps to ISO format
            if "stories" in data:
                for story in data["stories"]:
                    if "time" in story:
                        timestamp_sec = story["time"] / 1000
                        story["time"] = datetime.fromtimestamp(timestamp_sec).isoformat()
            
            dc.set(cache_key, data, dc.TTL_NEWS, dc.SOURCE_TICKERTICK, dc.KIND_PUNCTUAL, _db)
            return json.dumps(data)
            
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors (client errors)
            if 400 <= e.response.status_code < 500:
                logger.error(f"Tickertick API client error: {e}")
                return f'{{"error": "Tickertick API client error: {e.response.status_code}"}}'
            last_error = e
            logger.warning(f"Error fetching Tickertick news (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except Exception as e:
            last_error = e
            logger.warning(f"Error fetching Tickertick news (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
        
    logger.error(f"Failed to fetch Tickertick news after {MAX_RETRIES} attempts: {last_error}")
    return f'{{"error": "Failed to fetch news: {str(last_error)}"}}'


# ============================================================================
# Browser Tool (Playwright)
# ============================================================================

@tool
async def browser_tool(instruction: str) -> str:
    """
    Use browser automation to interact with web pages.
    
    This is expensive and should be used sparingly.
    
    Args:
        instruction: Natural language instruction for what to do with the browser
        
    Returns:
        String with browser results
    """
    try:
        # Import browser-use only when needed
        from browser_use import Agent as BrowserAgent, Browser, BrowserConfig
        from langchain_openai import ChatOpenAI
        
        # Get OpenAI API key for browser agent
        openai_key = None
        if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
            openai_key = settings.OPENAI_API_KEY.get_secret_value()
        elif os.getenv("OPENAI_API_KEY"):
            openai_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_key:
            return '{"error": "OpenAI API key not configured for browser tool"}'
        
        # Initialize browser
        chrome_path = os.getenv("CHROME_INSTANCE_PATH")
        browser = None
        if chrome_path:
            browser = Browser(config=BrowserConfig(chrome_instance_path=chrome_path))
        
        # Create browser agent
        browser_agent = BrowserAgent(
            task=instruction,
            llm=ChatOpenAI(model="gpt-4o", api_key=openai_key),
            browser=browser
        )
        
        # Run browser task
        result = await browser_agent.run()
        
        return f'{{"result": "{result}", "instruction": "{instruction}"}}'
        
    except ImportError:
        return '{"error": "browser-use package not installed. Install with: pip install browser-use"}'
    except Exception as e:
        logger.error(f"Error using browser tool: {e}")
        return f'{{"error": "Browser tool failed: {str(e)}"}}'


# ============================================================================
# Python REPL Tool
# ============================================================================

_repl = PythonREPL()

@tool
def python_repl_tool(code: str) -> str:
    """
    Execute Python code and return the result.
    
    The code runs in a static sandbox without interactive mode.
    Make sure to print output only.
    
    Args:
        code: Python code to execute
        
    Returns:
        String with execution result
    """
    params = {
        "code_length": len(code),
        "code_preview": code[:100] + "..." if len(code) > 100 else code
    }
    
    try:
        result = _repl.run(code)
        output = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
        _log_tool_usage("python_repl_tool", params, success=True)
        return output
    except Exception as e:
        error_msg = f"Failed to execute. Error: {repr(e)}"
        logger.error(error_msg)
        _log_tool_usage("python_repl_tool", params, success=False, error=str(e))
        return error_msg


# ============================================================================
# Trading Strategies Tool
# ============================================================================

def _calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average for a given period."""
    return data.ewm(span=period, adjust=False).mean()


def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index (ADX)."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    # Directional Movement
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm.abs()), 0)
    minus_dm = minus_dm.abs().where((minus_dm < 0) & (plus_dm < minus_dm.abs()), 0)
    
    # Directional Indicators
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    
    # Directional Index
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx


def _calculate_trend_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate trend following signals using EMAs and ADX."""
    if df.empty:
        return {
            "strategy": "Trend Following",
            "signal": "neutral",
            "confidence": 0,
            "error": "No data available"
        }
    
    # Calculate EMAs
    df['ema8'] = _calculate_ema(df['close'], 8)
    df['ema21'] = _calculate_ema(df['close'], 21)
    df['ema55'] = _calculate_ema(df['close'], 55)
    df['ema200'] = _calculate_ema(df['close'], 200)
    
    # Calculate ADX
    df['adx'] = _calculate_adx(df)
    
    # Determine trends
    df['short_trend'] = np.where(df['ema8'] > df['ema21'], 1, -1)
    df['medium_trend'] = np.where(df['ema21'] > df['ema55'], 1, -1)
    df['long_trend'] = np.where(df['close'] > df['ema200'], 1, -1)
    
    # Get latest data
    latest = df.iloc[-1]
    adx_value = latest['adx']
    adx_threshold = 20
    
    if latest['short_trend'] == 1 and latest['medium_trend'] == 1 and adx_value >= adx_threshold:
        signal = "bullish"
    elif latest['short_trend'] == -1 and latest['medium_trend'] == -1 and adx_value >= adx_threshold:
        signal = "bearish"
    else:
        signal = "neutral"
    
    # Determine confidence
    if pd.isna(adx_value):
        confidence = 0
    else:
        if adx_value < 20:
            confidence = adx_value / 20
        elif adx_value < 40:
            confidence = 1 + (adx_value - 20) / 20
        else:
            confidence = 2 + (adx_value - 40) / 20
            confidence = min(confidence, 3)
    
    return {
        "strategy": "Trend Following",
        "signal": signal,
        "confidence": round(confidence, 2),
        "metrics": {
            "ema8": round(latest['ema8'], 2),
            "ema21": round(latest['ema21'], 2),
            "ema55": round(latest['ema55'], 2),
            "ema200": round(latest['ema200'], 2),
            "adx": round(adx_value if not pd.isna(adx_value) else 0, 2),
            "short_trend": "up" if latest['short_trend'] == 1 else "down",
            "medium_trend": "up" if latest['medium_trend'] == 1 else "down",
            "long_trend": "up" if latest['long_trend'] == 1 else "down"
        }
    }


def _calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    for i in range(period, len(delta)):
        if i < len(avg_gain) and i < len(avg_loss):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + loss.iloc[i]) / period
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def _calculate_mean_reversion_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate mean reversion signals using Z-score, Bollinger Bands, and RSI."""
    if df.empty:
        return {
            "strategy": "Mean Reversion",
            "signal": "neutral",
            "confidence": 0,
            "error": "No data available"
        }
    
    df['sma50'] = df['close'].rolling(window=50).mean()
    df['std50'] = df['close'].rolling(window=50).std()
    df['zscore'] = (df['close'] - df['sma50']) / df['std50']
    
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + 2 * df['std20']
    df['lower_band'] = df['sma20'] - 2 * df['std20']
    
    df['rsi14'] = _calculate_rsi(df['close'], 14)
    df['rsi28'] = _calculate_rsi(df['close'], 28)
    
    latest = df.iloc[-1]
    
    signal = "neutral"
    confidence = 0
    
    if (latest['zscore'] < -1.5 and latest['close'] <= latest['lower_band'] and 
        latest['rsi14'] < 30):
        signal = "bullish"
        confidence = min(abs(latest['zscore']) / 1.5, 3)
    elif (latest['zscore'] > 1.5 and latest['close'] >= latest['upper_band'] and 
          latest['rsi14'] > 70):
        signal = "bearish"
        confidence = min(abs(latest['zscore']) / 1.5, 3)
    
    return {
        "strategy": "Mean Reversion",
        "signal": signal,
        "confidence": round(confidence, 2),
        "metrics": {
            "z_score": round(latest['zscore'], 2) if not pd.isna(latest['zscore']) else 0,
            "price": round(latest['close'], 2),
            "sma50": round(latest['sma50'], 2) if not pd.isna(latest['sma50']) else 0,
            "upper_band": round(latest['upper_band'], 2) if not pd.isna(latest['upper_band']) else 0,
            "lower_band": round(latest['lower_band'], 2) if not pd.isna(latest['lower_band']) else 0,
            "rsi14": round(latest['rsi14'], 2) if not pd.isna(latest['rsi14']) else 0
        }
    }


def _rank_normalize(series: pd.Series) -> pd.Series:
    """Convert a series to percentile ranks (0-1)."""
    return series.rank(pct=True)


def _calculate_momentum_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate momentum signals using price and volume momentum metrics."""
    if df.empty or len(df) < 126:
        return {
            "strategy": "Momentum",
            "signal": "neutral",
            "confidence": 0,
            "error": "Insufficient data for momentum calculation"
        }
    
    df['pct_change'] = df['close'].pct_change()
    df['mom_1m'] = df['close'].pct_change(21)
    df['mom_3m'] = df['close'].pct_change(63)
    df['mom_6m'] = df['close'].pct_change(126)
    
    df['mom_1m_rank'] = _rank_normalize(df['mom_1m'])
    df['mom_3m_rank'] = _rank_normalize(df['mom_3m'])
    df['mom_6m_rank'] = _rank_normalize(df['mom_6m'])
    
    df['vol_ma21'] = df['volume'].rolling(window=21).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma21']
    
    df['momentum_score'] = (0.5 * df['mom_1m_rank'] + 
                           0.3 * df['mom_3m_rank'] + 
                           0.2 * df['mom_6m_rank'])
    df['momentum_score'] = (df['momentum_score'] - 0.5) * 2
    
    latest = df.iloc[-1]
    
    if latest['momentum_score'] > 0.2 and latest['vol_ratio'] > 1.0:
        signal = "bullish"
        confidence = min(abs(latest['momentum_score']) * 3, 3)
    elif latest['momentum_score'] < -0.2 and latest['vol_ratio'] > 1.0:
        signal = "bearish"
        confidence = min(abs(latest['momentum_score']) * 3, 3)
    else:
        signal = "neutral"
        confidence = 0
    
    return {
        "strategy": "Momentum",
        "signal": signal,
        "confidence": round(confidence, 2),
        "metrics": {
            "momentum_1m": round(latest['mom_1m'] * 100, 2) if not pd.isna(latest['mom_1m']) else 0,
            "momentum_3m": round(latest['mom_3m'] * 100, 2) if not pd.isna(latest['mom_3m']) else 0,
            "momentum_6m": round(latest['mom_6m'] * 100, 2) if not pd.isna(latest['mom_6m']) else 0,
            "combined_score": round(latest['momentum_score'], 2) if not pd.isna(latest['momentum_score']) else 0,
            "volume_ratio": round(latest['vol_ratio'], 2) if not pd.isna(latest['vol_ratio']) else 0
        }
    }


def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def _calculate_volatility_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate volatility-based signals."""
    if df.empty or len(df) < 84:
        return {
            "strategy": "Volatility",
            "signal": "neutral",
            "confidence": 0,
            "error": "Insufficient data for volatility calculation"
        }
    
    df['returns'] = df['close'].pct_change()
    df['volatility_21d'] = df['returns'].rolling(window=21).std() * np.sqrt(252)
    df['volatility_63d_avg'] = df['volatility_21d'].rolling(window=63).mean()
    df['volatility_std'] = df['volatility_21d'].rolling(window=63).std()
    df['volatility_zscore'] = (df['volatility_21d'] - df['volatility_63d_avg']) / df['volatility_std']
    df['volatility_rank'] = _rank_normalize(df['volatility_21d'].rolling(window=63))
    df['vol_above_band'] = (df['volatility_zscore'] > 1).rolling(window=5).mean()
    df['vol_below_band'] = (df['volatility_zscore'] < -1).rolling(window=5).mean()
    
    df['atr'] = _calculate_atr(df, 14)
    df['atr_ratio'] = df['atr'] / df['close']
    
    latest = df.iloc[-1]
    
    if (not pd.isna(latest['volatility_zscore']) and 
        latest['volatility_zscore'] < -1.5 and 
        latest['vol_below_band'] > 0.6):
        signal = "bullish"
        confidence = min(abs(latest['volatility_zscore']) / 1.5, 3)
    elif (not pd.isna(latest['volatility_zscore']) and 
          latest['volatility_zscore'] > 1.5 and 
          latest['vol_above_band'] > 0.6):
        signal = "bearish"
        confidence = min(abs(latest['volatility_zscore']) / 1.5, 3)
    else:
        signal = "neutral"
        confidence = 0
    
    return {
        "strategy": "Volatility",
        "signal": signal,
        "confidence": round(confidence, 2),
        "metrics": {
            "current_volatility": round(latest['volatility_21d'] * 100, 2) if not pd.isna(latest['volatility_21d']) else 0,
            "average_volatility": round(latest['volatility_63d_avg'] * 100, 2) if not pd.isna(latest['volatility_63d_avg']) else 0,
            "volatility_zscore": round(latest['volatility_zscore'], 2) if not pd.isna(latest['volatility_zscore']) else 0,
            "atr_14d": round(latest['atr'], 2) if not pd.isna(latest['atr']) else 0
        }
    }


def _calculate_hurst_exponent(time_series: pd.Series, max_lag: int = 20) -> float:
    """Calculate Hurst Exponent."""
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(time_series[lag:].values, time_series[:-lag].values))) for lag in lags]
    reg = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return reg[0]


def _calculate_stat_arb_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate statistical arbitrage signals."""
    if df.empty or len(df) < 126:
        return {
            "strategy": "Statistical Arbitrage",
            "signal": "neutral",
            "confidence": 0,
            "error": "Insufficient data for statistical analysis"
        }
    
    df['returns'] = df['close'].pct_change()
    df['annualized_returns'] = df['returns'] * np.sqrt(252)
    df['skew_63d'] = df['annualized_returns'].rolling(window=63).skew()
    df['kurt_63d'] = df['annualized_returns'].rolling(window=63).kurt()
    
    latest_returns = df['returns'].dropna()
    hurst = _calculate_hurst_exponent(latest_returns) if len(latest_returns) >= 20 else 0.5
    
    latest = df.iloc[-1]
    
    signal = "neutral"
    confidence = 0
    
    if hurst < 0.4:
        if latest['skew_63d'] > 0.5:
            signal = "bullish"
            confidence = (0.5 - hurst) * 10
        elif latest['skew_63d'] < -0.5:
            signal = "bearish"
            confidence = (0.5 - hurst) * 10
    
    confidence = min(confidence, 3)
    
    return {
        "strategy": "Statistical Arbitrage",
        "signal": signal,
        "confidence": round(confidence, 2),
        "metrics": {
            "hurst_exponent": round(hurst, 2),
            "skewness": round(latest['skew_63d'], 2) if not pd.isna(latest['skew_63d']) else 0,
            "kurtosis": round(latest['kurt_63d'], 2) if not pd.isna(latest['kurt_63d']) else 0
        }
    }


def _get_combined_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate signals from all strategies and combine them."""
    trend_signals = _calculate_trend_signals(df)
    mean_reversion_signals = _calculate_mean_reversion_signals(df)
    momentum_signals = _calculate_momentum_signals(df)
    volatility_signals = _calculate_volatility_signals(df)
    stat_arb_signals = _calculate_stat_arb_signals(df)
    
    all_signals = [
        trend_signals,
        mean_reversion_signals,
        momentum_signals,
        volatility_signals,
        stat_arb_signals
    ]
    
    bullish_score = sum(s["confidence"] for s in all_signals if s["signal"] == "bullish")
    bearish_score = sum(s["confidence"] for s in all_signals if s["signal"] == "bearish")
    
    if bullish_score > bearish_score:
        consensus_signal = "bullish"
        consensus_confidence = bullish_score / 15
    elif bearish_score > bullish_score:
        consensus_signal = "bearish"
        consensus_confidence = bearish_score / 15
    else:
        consensus_signal = "neutral"
        consensus_confidence = 0
    
    consensus_confidence = min(consensus_confidence, 1.0)
    
    return {
        "strategies": {
            "trend_following": trend_signals,
            "mean_reversion": mean_reversion_signals,
            "momentum": momentum_signals,
            "volatility": volatility_signals,
            "statistical_arbitrage": stat_arb_signals
        },
        "consensus": {
            "signal": consensus_signal,
            "confidence": round(consensus_confidence, 2),
            "bullish_score": round(bullish_score, 2),
            "bearish_score": round(bearish_score, 2)
        }
    }


@tool
def get_trading_signals(
    ticker: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    strategy: Literal["trend", "mean_reversion", "momentum", "volatility", "stat_arb", "combined"] = "combined"
) -> str:
    """
    Get trading signals for a ticker using various strategies.
    
    Args:
        ticker: Stock ticker symbol
        from_date: Start date (YYYY-MM-DD, default: 252 days ago for sufficient data)
        to_date: End date (YYYY-MM-DD, default: today)
        strategy: Trading strategy type
        
    Returns:
        JSON string with trading signals
    """
    params = {
        "ticker": ticker,
        "from_date": from_date,
        "to_date": to_date,
        "strategy": strategy
    }
    
    try:
        # Get market data first (use .invoke: get_market_data is a @tool/StructuredTool)
        market_data_str = get_market_data.invoke({
            "ticker": ticker,
            "from_date": from_date,
            "to_date": to_date,
            "timespan": "day",
            "limit": 252,  # Need at least 252 days for some strategies
        })
        
        market_data = json.loads(market_data_str)
        
        if "error" in market_data:
            _log_tool_usage("get_trading_signals", params, success=False, error=market_data.get("error"))
            return market_data_str
        
        # Convert to DataFrame
        data_list = market_data.get("data", [])
        if not data_list:
            _log_tool_usage("get_trading_signals", params, success=False, error="No market data available")
            return json.dumps({
                "ticker": ticker,
                "strategy": strategy,
                "error": "No market data available"
            })
        
        # Convert timestamp to datetime and create DataFrame
        df = pd.DataFrame(data_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')
        
        # Calculate signals based on strategy
        if strategy == "trend":
            result = _calculate_trend_signals(df)
        elif strategy == "mean_reversion":
            result = _calculate_mean_reversion_signals(df)
        elif strategy == "momentum":
            result = _calculate_momentum_signals(df)
        elif strategy == "volatility":
            result = _calculate_volatility_signals(df)
        elif strategy == "stat_arb":
            result = _calculate_stat_arb_signals(df)
        else:  # combined
            result = _get_combined_signals(df)
        
        signals_result = json.dumps({
            "ticker": ticker,
            "strategy": strategy,
            "signals": result,
            "data_period": {
                "from": df.index[0].isoformat() if len(df) > 0 else None,
                "to": df.index[-1].isoformat() if len(df) > 0 else None,
                "days": len(df)
            }
        })
        _log_tool_usage("get_trading_signals", params, success=True)
        return signals_result
        
    except Exception as e:
        logger.error(f"Error getting trading signals: {e}", exc_info=True)
        _log_tool_usage("get_trading_signals", params, success=False, error=str(e))
        return json.dumps({
            "ticker": ticker,
            "strategy": strategy,
            "error": f"Failed to get trading signals: {str(e)}"
        })


# ============================================================================
# Tool Exports
# ============================================================================

# List of all available tools for LangAlpha agents
LANGALPHA_TOOLS = [
    get_market_data,
    get_ticker_snapshot,
    get_fundamental_data,
    web_search,
    get_tickertick_news,
    browser_tool,
    python_repl_tool,
    get_trading_signals,
]
