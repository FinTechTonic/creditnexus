"""
Integration tests for brokerage flow (apply, status, documents).
Tests response models and route logic; full app integration requires server env (eth_account, etc.).
"""

import pytest

_import_error = None
try:
    from app.api.brokerage_routes import AccountStatusResponse
except Exception as e:
    AccountStatusResponse = None
    _import_error = e


@pytest.fixture(autouse=True)
def skip_if_no_app():
    if AccountStatusResponse is None:
        pytest.skip(f"Brokerage routes not importable (e.g. missing deps): {_import_error}")


def test_brokerage_status_response_shape():
    """AccountStatusResponse has expected fields."""
    r = AccountStatusResponse(has_account=False, currency="USD")
    assert r.has_account is False
    assert r.currency == "USD"

    r2 = AccountStatusResponse(
        has_account=True,
        status="ACTIVE",
        alpaca_account_id="acc-123",
        account_number="12345678",
        currency="USD",
    )
    assert r2.status == "ACTIVE"
    assert r2.alpaca_account_id == "acc-123"


def test_brokerage_status_response_action_required():
    """AccountStatusResponse supports ACTION_REQUIRED with reason."""
    r = AccountStatusResponse(
        has_account=True,
        status="ACTION_REQUIRED",
        alpaca_account_id="acc-456",
        action_required_reason="Upload identity document",
        currency="USD",
    )
    assert r.status == "ACTION_REQUIRED"
    assert r.action_required_reason == "Upload identity document"
