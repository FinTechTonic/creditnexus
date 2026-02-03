"""
CreditNexus Backend API Client
Handles HTTP requests to CreditNexus backend services
When STANDALONE=1, uses vendored stubs and Plaid (no HTTP to CreditNexus).
"""

import asyncio
import httpx
import logging
from typing import Optional

try:
    from server.config import CREDITNEXUS_URL, SERVICE_KEY, STANDALONE
except ImportError:
    from demo_mcp.server.config import CREDITNEXUS_URL, SERVICE_KEY, STANDALONE

logger = logging.getLogger(__name__)


async def call_prediction(
    symbol: str,
    horizon: int = 30
) -> dict:
    """
    Call CreditNexus stock prediction API.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        horizon: Prediction horizon in days

    Returns:
        Prediction results from CreditNexus API

    Raises:
        httpx.HTTPError: If API call fails
    """
    if STANDALONE:
        try:
            from server.vendored.stock_stub import stub_daily
        except ImportError:
            from demo_mcp.server.vendored.stock_stub import stub_daily
        return await asyncio.to_thread(stub_daily, symbol, horizon)
    headers = {}
    if SERVICE_KEY:
        headers["X-API-Key"] = SERVICE_KEY

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CREDITNEXUS_URL}/api/stock-prediction/daily",
            headers=headers,
            params={
                "symbol": symbol,
                "horizon": horizon
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()


async def call_backtest(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    strategy: Optional[str] = "chronos"
) -> dict:
    """
    Call CreditNexus backtest API.

    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        strategy: Trading strategy name

    Returns:
        Backtest results

    Raises:
        httpx.HTTPError: If API call fails
    """
    if STANDALONE:
        try:
            from server.vendored.stock_stub import stub_backtest
        except ImportError:
            from demo_mcp.server.vendored.stock_stub import stub_backtest
        return await asyncio.to_thread(
            stub_backtest, symbol,
            start_date=start_date, end_date=end_date, strategy=strategy,
        )
    headers = {}
    if SERVICE_KEY:
        headers["X-API-Key"] = SERVICE_KEY

    body = {"symbol": symbol}
    if start_date:
        body["start"] = start_date
    if end_date:
        body["end"] = end_date
    if strategy:
        body["strategy"] = strategy

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CREDITNEXUS_URL}/api/stock-prediction/backtest",
            headers=headers,
            json=body,
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()


async def get_borrower_score_for_agent(agent_address: Optional[str]) -> Optional[int]:
    """
    Get Plaid-derived borrower score component for an agent (wallet address).
    Returns None if no linked account or backend does not expose score; otherwise 0–100 component.
    CreditNexus backend may expose GET /api/agent-score?wallet=0x... returning { plaid_score: int }.
    """
    if STANDALONE:
        try:
            from server.vendored.plaid_local import get_plaid_connection_by_agent_wallet
        except ImportError:
            from demo_mcp.server.vendored.plaid_local import get_plaid_connection_by_agent_wallet
        conn = await asyncio.to_thread(get_plaid_connection_by_agent_wallet, agent_address or "")
        return 50 if conn else None
    if not agent_address or not CREDITNEXUS_URL:
        return None
    headers = {}
    if SERVICE_KEY:
        headers["X-API-Key"] = SERVICE_KEY
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CREDITNEXUS_URL}/api/agent-score",
                headers=headers,
                params={"wallet": agent_address},
                timeout=10.0,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("plaid_score") if isinstance(data.get("plaid_score"), (int, float)) else None
    except Exception as e:
        logger.debug("get_borrower_score_for_agent failed: %s", e)
        return None


async def create_plaid_link_token(user_id: Optional[str] = None) -> dict:
    """
    Create Plaid link token for bank account connection.

    Args:
        user_id: Optional user ID for Plaid link

    Returns:
        Plaid link token response

    Raises:
        httpx.HTTPError: If API call fails
    """
    if STANDALONE:
        try:
            from server.vendored.plaid_local import create_link_token
        except ImportError:
            from demo_mcp.server.vendored.plaid_local import create_link_token
        return await asyncio.to_thread(create_link_token, user_id or "mcp-demo")
    headers = {}
    if SERVICE_KEY:
        headers["X-API-Key"] = SERVICE_KEY

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CREDITNEXUS_URL}/api/banking/link-token",
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


async def exchange_plaid_public_token(
    public_token: str,
    agent_wallet: Optional[str] = None,
) -> dict:
    """
    Exchange Plaid public_token for access_token and store in CreditNexus.
    Optionally associate the connection with an agent wallet for borrower score (get_borrower_score).

    Args:
        public_token: Public token from Plaid Link onSuccess
        agent_wallet: Optional agent (payer) wallet address to associate for agent-score lookup

    Returns:
        {"status": "connected", "connection_id": int} or error dict

    Raises:
        httpx.HTTPError: If API call fails
    """
    if STANDALONE:
        try:
            from server.vendored.plaid_local import exchange_public_token
        except ImportError:
            from demo_mcp.server.vendored.plaid_local import exchange_public_token
        return await asyncio.to_thread(exchange_public_token, public_token, agent_wallet)
    headers = {"Content-Type": "application/json"}
    if SERVICE_KEY:
        headers["X-API-Key"] = SERVICE_KEY
    body: dict = {"public_token": public_token}
    if agent_wallet and agent_wallet.strip():
        body["agent_wallet"] = agent_wallet.strip()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CREDITNEXUS_URL}/api/banking/connect",
            headers=headers,
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
