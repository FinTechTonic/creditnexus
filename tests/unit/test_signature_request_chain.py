"""
Unit tests for signature request chain.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.chains.signature_request_chain import generate_signature_request
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw, InterestRatePayout, FloatingRateOption, Frequency, PeriodEnum


@pytest.fixture
def sample_credit_agreement():
    """Sample credit agreement with multiple parties."""
    return CreditAgreement(
        deal_id="DEAL_001",
        loan_identification_number="LOAN_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.NY,
        parties=[
            Party(
                id="party_1",
                name="ACME Corp",
                role="Borrower",
                email="borrower@acme.com",
                lei="12345678901234567890"
            ),
            Party(
                id="party_2",
                name="Bank of America",
                role="Lender",
                email="lender@bofa.com",
                lei="98765432109876543210"
            ),
            Party(
                id="party_3",
                name="Guarantor Inc",
                role="Guarantor",
                email="guarantor@guarantor.com"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Revolving Credit Facility",
                commitment_amount=Money(
                    amount=5000000.00,
                    currency=Currency.USD
                ),
                interest_terms=InterestRatePayout(
                    rate_option=FloatingRateOption(
                        benchmark="Term SOFR",
                        spread_bps=250.0
                    ),
                    payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
                ),
                maturity_date=datetime.now().date().replace(year=datetime.now().year + 5)
            )
        ],
        sustainability_linked=False
    )


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_parallel_signature_workflow(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test parallel signature workflow (all signers sign simultaneously)."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_evaluation = SignatureRequestGeneration(
        signers=[
            Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", signing_order=0, required=True),
            Signer(name="Bank of America", email="lender@bofa.com", role="Lender", signing_order=0, required=True)
        ],
        signing_workflow="parallel",
        expiration_days=30
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="standard"
    )
    
    assert result is not None
    assert len(result.signers) > 0
    assert result.signing_workflow == "parallel"
    
    # In parallel workflow, all signers should have signing_order = 0
    for signer in result.signers:
        assert signer.signing_order == 0


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_sequential_signature_workflow(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test sequential signature workflow (signers sign in order)."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_evaluation = SignatureRequestGeneration(
        signers=[
            Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", signing_order=1, required=True),
            Signer(name="Bank of America", email="lender@bofa.com", role="Lender", signing_order=2, required=True)
        ],
        signing_workflow="sequential",
        expiration_days=14
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="time_sensitive"
    )
    
    assert result is not None
    assert len(result.signers) > 0
    assert result.signing_workflow in ["parallel", "sequential"]
    
    # If sequential, signing orders should be unique and sequential
    if result.signing_workflow == "sequential":
        orders = [s.signing_order for s in result.signers if s.signing_order > 0]
        if orders:
            assert sorted(orders) == list(range(1, len(orders) + 1))


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_signer_detection(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test that signers are correctly detected from CDM data."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_evaluation = SignatureRequestGeneration(
        signers=[
            Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", required=True),
            Signer(name="Bank of America", email="lender@bofa.com", role="Lender", required=True)
        ],
        signing_workflow="parallel",
        expiration_days=30
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="standard"
    )
    
    assert len(result.signers) > 0
    
    # Should detect borrower and lender at minimum
    roles = [s.role for s in result.signers]
    assert "Borrower" in roles or any("borrower" in r.lower() for r in roles)
    assert "Lender" in roles or any("lender" in r.lower() for r in roles)
    
    # All signers should have name and email
    for signer in result.signers:
        assert signer.name is not None
        assert signer.email is not None
        assert "@" in signer.email  # Basic email validation


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_signature_expiration(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test that signature requests have expiration settings."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_evaluation = SignatureRequestGeneration(
        signers=[Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", required=True)],
        signing_workflow="parallel",
        expiration_days=30,
        reminder_enabled=True,
        reminder_days=[7, 3, 1]
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="standard"
    )
    
    assert result.expiration_days > 0
    assert result.expiration_days <= 90  # Reasonable maximum
    
    # Should have reminder settings
    assert result.reminder_enabled in [True, False]
    if result.reminder_enabled:
        assert len(result.reminder_days) > 0
        assert all(day > 0 for day in result.reminder_days)


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_urgency_levels(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test different urgency levels affect signature configuration."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_eval_standard = SignatureRequestGeneration(
        signers=[Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", required=True)],
        signing_workflow="parallel",
        expiration_days=30
    )
    
    mock_eval_time_sensitive = SignatureRequestGeneration(
        signers=[Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", required=True)],
        signing_workflow="parallel",
        expiration_days=14
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.side_effect = [mock_eval_standard, mock_eval_time_sensitive]
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    standard = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="standard"
    )
    
    time_sensitive = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="time_sensitive"
    )
    
    # Time sensitive may have shorter expiration or different workflow
    # Both should be valid configurations
    assert standard.expiration_days > 0
    assert time_sensitive.expiration_days > 0


@patch('app.chains.signature_request_chain.create_signature_request_chain')
@patch('app.chains.signature_request_chain.create_signature_request_prompt')
def test_required_signers(mock_prompt_func, mock_chain_func, sample_credit_agreement):
    """Test that required signers are marked as required."""
    from app.models.signature_requests import SignatureRequestGeneration, Signer
    
    mock_evaluation = SignatureRequestGeneration(
        signers=[
            Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower", required=True),
            Signer(name="Bank of America", email="lender@bofa.com", role="Lender", required=True)
        ],
        signing_workflow="parallel",
        expiration_days=30
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_signature_request(
        credit_agreement=sample_credit_agreement,
        document_type="facility_agreement",
        urgency="standard"
    )
    
    # Borrower and lender should be required
    required_signers = [s for s in result.signers if s.required]
    assert len(required_signers) > 0
    
    # At minimum, borrower should be required
    borrower = next((s for s in result.signers if "borrower" in s.role.lower()), None)
    if borrower:
        assert borrower.required is True
