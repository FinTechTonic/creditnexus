"""
Unit tests for Alpaca Broker API client with mocked HTTP.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.alpaca_broker_service import (
    AlpacaBrokerClient,
    AlpacaBrokerAPIError,
    get_broker_client,
)


@pytest.fixture
def broker_client():
    """AlpacaBrokerClient with mocked session."""
    with patch("app.services.alpaca_broker_service.requests.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        client = AlpacaBrokerClient(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://broker-api.sandbox.alpaca.markets",
        )
        client._session = mock_session
        return client


def test_create_account_returns_account_id_and_status(broker_client):
    """create_account returns account id and status from API response."""
    broker_client._session.request.return_value = Mock(
        status_code=200,
        json=lambda: {"id": "acc-123", "status": "SUBMITTED", "account_number": "ABC123", "currency": "USD"},
        content=b"{}",
    )
    result = broker_client.create_account({"contact": {"email_address": "u@example.com"}})
    assert result["id"] == "acc-123"
    assert result["status"] == "SUBMITTED"
    broker_client._session.request.assert_called_once()
    call_args = broker_client._session.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[1].get("json") is not None


def test_create_account_raises_on_4xx(broker_client):
    """create_account raises AlpacaBrokerAPIError on 4xx."""
    broker_client._session.request.return_value = Mock(
        status_code=400,
        json=lambda: {"message": "Invalid payload"},
        text="Bad Request",
    )
    with pytest.raises(AlpacaBrokerAPIError) as exc_info:
        broker_client.create_account({})
    assert exc_info.value.status_code == 400
    assert "Invalid payload" in str(exc_info.value)


def test_get_order_returns_order(broker_client):
    """get_order returns order dict from API."""
    broker_client._session.request.return_value = Mock(
        status_code=200,
        json=lambda: {
            "id": "ord-456",
            "status": "filled",
            "symbol": "AAPL",
            "side": "buy",
            "type": "market",
            "qty": "10",
            "filled_qty": "10",
            "filled_avg_price": "150.0",
        },
        content=b"{}",
    )
    result = broker_client.get_order("acc-123", "ord-456")
    assert result["id"] == "ord-456"
    assert result["status"] == "filled"
    assert result["symbol"] == "AAPL"


def test_get_positions_returns_list(broker_client):
    """get_positions returns list of positions."""
    broker_client._session.request.return_value = Mock(
        status_code=200,
        json=lambda: {"positions": [{"symbol": "AAPL", "qty": "10", "market_value": "1500"}]},
        content=b"{}",
    )
    result = broker_client.get_positions("acc-123")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["symbol"] == "AAPL"


def test_get_broker_client_returns_none_when_not_configured():
    """get_broker_client returns None when ALPACA_BROKER_* not set."""
    with patch("app.core.config.settings") as mock_cfg:
        mock_cfg.ALPACA_BROKER_API_KEY = None
        mock_cfg.ALPACA_BROKER_API_SECRET = None
        assert get_broker_client() is None


def test_get_broker_client_returns_client_when_configured():
    """get_broker_client returns AlpacaBrokerClient when keys set."""
    with patch("app.core.config.settings") as mock_cfg:
        mock_cfg.ALPACA_BROKER_API_KEY = Mock(get_secret_value=lambda: "k")
        mock_cfg.ALPACA_BROKER_API_SECRET = Mock(get_secret_value=lambda: "s")
        mock_cfg.ALPACA_BROKER_BASE_URL = "https://broker-api.sandbox.alpaca.markets"
        mock_cfg.ALPACA_BROKER_PAPER = True
        client = get_broker_client()
        assert client is not None
        assert isinstance(client, AlpacaBrokerClient)
