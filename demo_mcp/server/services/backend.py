"""
CreditNexus Backend API Client
Handles HTTP requests to CreditNexus backend services
"""

import httpx
import logging
from typing import Optional

from demo_mcp.server.config import CREDITNEXUS_URL, SERVICE_KEY

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
    headers = {}
    if SERVICE_KEY:
        headers["Authorization"] = f"Bearer {SERVICE_KEY}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CREDITNEXUS_URL}/api/stock-prediction/daily",
            headers=headers,
            params={
                "symbol": symbol,
                "horizon": horizon
            },
            timeout=30.0
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
    headers = {}
    if SERVICE_KEY:
        headers["Authorization"] = f"Bearer {SERVICE_KEY}"

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
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()


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
    headers = {}
    if SERVICE_KEY:
        headers["Authorization"] = f"Bearer {SERVICE_KEY}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CREDITNEXUS_URL}/api/banking/link-token",
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
