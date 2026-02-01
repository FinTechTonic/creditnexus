"""
CreditNexus Backend API Client
Handles HTTP requests to CreditNexus backend services
"""

import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

CREDITNEXUS_URL = os.getenv("CREDITNEXUS_API_URL", "http://localhost:8000")
SERVICE_KEY = os.getenv("CREDITNEXUS_SERVICE_KEY", "")


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
    end_date: Optional[str] = None
) -> dict:
    """
    Call CreditNexus backtest API.

    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Backtest results

    Raises:
        httpx.HTTPError: If API call fails
    """
    headers = {}
    if SERVICE_KEY:
        headers["Authorization"] = f"Bearer {SERVICE_KEY}"

    params = {"symbol": symbol}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CREDITNEXUS_URL}/api/stock-prediction/backtest",
            headers=headers,
            params=params,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
