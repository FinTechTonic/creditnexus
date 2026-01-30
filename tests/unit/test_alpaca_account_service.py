"""
Unit tests for Alpaca account opening service (KYC gate, payload build, create_account).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.db.models import User, KYCVerification, AlpacaCustomerAccount
from app.services.alpaca_account_service import (
    open_alpaca_account,
    AlpacaAccountServiceError,
    _build_account_payload,
)


@pytest.fixture
def mock_user():
    """User with email and display_name."""
    u = Mock(spec=User)
    u.id = 1
    u.email = "user@example.com"
    u.display_name = "Jane Doe"
    u.profile_data = {}
    u.kyc_verification = None
    return u


@pytest.fixture
def mock_verification():
    """KYCVerification with identity_verified."""
    v = Mock(spec=KYCVerification)
    v.verification_metadata = None
    return v


def test_build_account_payload_minimal(mock_user, mock_verification):
    """_build_account_payload produces contact, identity, address from User."""
    mock_user.profile_data = {}
    payload = _build_account_payload(mock_user, mock_verification)
    assert "contact" in payload
    assert payload["contact"]["email_address"] == "user@example.com"
    assert "identity" in payload
    assert payload["identity"]["given_name"] == "Jane"
    assert payload["identity"]["family_name"] == "Doe"
    assert "address" in payload
    assert payload["address"]["country"] in ("US", "USA")


def test_open_alpaca_account_raises_when_user_not_found():
    """open_alpaca_account raises when user_id not found."""
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(AlpacaAccountServiceError) as exc_info:
        open_alpaca_account(999, db)
    assert "not found" in str(exc_info.value).lower()


def test_open_alpaca_account_raises_when_kyc_not_sufficient():
    """open_alpaca_account raises when evaluate_kyc_for_brokerage returns False."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "u@example.com"
    user.display_name = "User"
    user.profile_data = {}
    user.kyc_verification = None

    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.first.side_effect = [
        user,   # User
        None,   # AlpacaCustomerAccount
    ]

    with patch("app.services.alpaca_account_service.KYCService") as mock_kyc_class:
        mock_kyc = Mock()
        mock_kyc.evaluate_kyc_for_brokerage.return_value = False
        mock_kyc_class.return_value = mock_kyc

        with pytest.raises(AlpacaAccountServiceError) as exc_info:
            open_alpaca_account(1, db)
        assert "kyc" in str(exc_info.value).lower() or "verification" in str(exc_info.value).lower()


def test_open_alpaca_account_raises_when_already_submitted():
    """open_alpaca_account raises when user already has SUBMITTED account."""
    existing = Mock(spec=AlpacaCustomerAccount)
    existing.status = "SUBMITTED"
    existing.user_id = 1

    user = Mock(spec=User)
    user.id = 1
    user.email = "u@example.com"
    user.display_name = "User"
    user.profile_data = {}
    user.kyc_verification = None

    db = MagicMock(spec=Session)
    # First query: User; second: AlpacaCustomerAccount (existing SUBMITTED)
    chain = MagicMock()
    chain.filter.return_value.first.side_effect = [user, existing]
    db.query.return_value = chain

    with pytest.raises(AlpacaAccountServiceError) as exc_info:
        open_alpaca_account(1, db)
    assert "in progress" in str(exc_info.value).lower() or "submitted" in str(exc_info.value).lower()
