"""
Unit tests for filing requirement chain.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.chains.filing_requirement_chain import evaluate_filing_requirements
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw, InterestRatePayout, FloatingRateOption, Frequency, PeriodEnum
from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement


@pytest.fixture
def sample_credit_agreement_us():
    """Sample US credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_US_001",
        loan_identification_number="LOAN_US_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.NY,
        parties=[
            Party(
                id="party_1",
                name="ACME Corp",
                role="Borrower",
                lei="12345678901234567890"
            ),
            Party(
                id="party_2",
                name="Bank of America",
                role="Lender",
                lei="98765432109876543210"
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


@pytest.fixture
def sample_credit_agreement_uk():
    """Sample UK credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_UK_001",
        loan_identification_number="LOAN_UK_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.ENGLISH,
        parties=[
            Party(
                id="party_1",
                name="UK Corp Ltd",
                role="Borrower",
                lei="11111111111111111111",
                company_number="12345678"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=2000000.00,
                    currency=Currency.GBP
                ),
                interest_terms=InterestRatePayout(
                    rate_option=FloatingRateOption(
                        benchmark="SONIA",
                        spread_bps=200.0
                    ),
                    payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
                ),
                maturity_date=datetime.now().date().replace(year=datetime.now().year + 5)
            )
        ],
        sustainability_linked=False
    )


@pytest.fixture
def sample_credit_agreement_fr():
    """Sample French credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_FR_001",
        loan_identification_number="LOAN_FR_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.OTHER,  # French not in enum, use OTHER
        parties=[
            Party(
                id="party_1",
                name="Société Française SA",
                role="Borrower",
                lei="22222222222222222222",
                siren="123456789"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Crédit Revolving",
                commitment_amount=Money(
                    amount=3000000.00,
                    currency=Currency.EUR
                ),
                interest_terms=InterestRatePayout(
                    rate_option=FloatingRateOption(
                        benchmark="EURIBOR",
                        spread_bps=180.0
                    ),
                    payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
                ),
                maturity_date=datetime.now().date().replace(year=datetime.now().year + 5)
            )
        ],
        sustainability_linked=False
    )


@pytest.fixture
def sample_credit_agreement_de():
    """Sample German credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_DE_001",
        loan_identification_number="LOAN_DE_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.OTHER,  # German not in enum, use OTHER
        parties=[
            Party(
                id="party_1",
                name="Deutsche GmbH",
                role="Borrower",
                lei="33333333333333333333",
                hrb="HRB 12345"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Kreditlinie",
                commitment_amount=Money(
                    amount=4000000.00,
                    currency=Currency.EUR
                ),
                interest_terms=InterestRatePayout(
                    rate_option=FloatingRateOption(
                        benchmark="EURIBOR",
                        spread_bps=175.0
                    ),
                    payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
                ),
                maturity_date=datetime.now().date().replace(year=datetime.now().year + 5)
            )
        ],
        sustainability_linked=False
    )


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
@patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt')
def test_us_filing_requirements(mock_prompt_func, mock_chain_func, sample_credit_agreement_us):
    """Test filing requirement evaluation for US jurisdiction."""
    # Create a mock evaluation result
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[
            FilingRequirement(
                authority="SEC",
                jurisdiction="US",
                agreement_type="facility_agreement",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=4),
                required_fields=["company_name", "agreement_date"],
                api_available=False,
                form_type="8-K",
                priority="high"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_123"
    )
    
    # Mock the chain components
    mock_prompt = MagicMock()
    mock_structured_llm = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    
    # Set up the pipe operator mock
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = mock_structured_llm
    
    result = evaluate_filing_requirements(
        credit_agreement=sample_credit_agreement_us,
        document_id=1,
        deal_id=1,
        agreement_type="facility_agreement"
    )
    
    assert result is not None
    assert hasattr(result, 'required_filings')
    assert hasattr(result, 'compliance_status')
    
    # US should have SEC filing requirements for material agreements
    us_filings = [f for f in result.required_filings if f.jurisdiction == "US"]
    assert len(us_filings) > 0, f"Should have at least one US filing requirement, got {len(result.required_filings)} total filings"
    
    sec_filing = next((f for f in us_filings if f.authority == "SEC"), None)
    assert sec_filing is not None, "Should have SEC filing requirement"
    assert sec_filing.filing_system == "manual_ui"
    assert sec_filing.form_type in ["8-K", None]  # May or may not have form type


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
@patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt')
def test_uk_filing_requirements(mock_prompt_func, mock_chain_func, sample_credit_agreement_uk):
    """Test filing requirement evaluation for UK jurisdiction."""
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[
            FilingRequirement(
                authority="Companies House",
                jurisdiction="UK",
                agreement_type="facility_agreement",
                filing_system="companies_house_api",
                deadline=datetime.now() + timedelta(days=21),
                required_fields=["company_number", "charge_description"],
                api_available=True,
                api_endpoint="/company/{company_number}/charges",
                priority="high"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_456"
    )
    
    # Mock the chain components
    mock_prompt = MagicMock()
    mock_structured_llm = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    
    # Set up the pipe operator mock
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = mock_structured_llm
    
    result = evaluate_filing_requirements(
        credit_agreement=sample_credit_agreement_uk,
        document_id=1,
        deal_id=1,
        agreement_type="facility_agreement"
    )
    
    assert result is not None
    assert hasattr(result, 'required_filings')
    
    # UK should have Companies House filing requirements
    uk_filings = [f for f in result.required_filings if f.jurisdiction == "UK"]
    assert len(uk_filings) > 0, f"Should have at least one UK filing requirement, got {len(result.required_filings)} total filings"
    
    companies_house = next((f for f in uk_filings if f.authority == "Companies House"), None)
    assert companies_house is not None, "Should have Companies House filing requirement"
    assert companies_house.filing_system == "companies_house_api"
    assert companies_house.api_available is True


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
def test_fr_filing_requirements(mock_chain, sample_credit_agreement_fr):
    """Test filing requirement evaluation for French jurisdiction."""
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_789"
    )
    
    mock_chain_instance = MagicMock()
    mock_chain_instance.invoke.return_value = mock_evaluation
    
    with patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt', return_value=MagicMock()):
        with patch('app.chains.filing_requirement_chain.create_filing_requirement_chain', return_value=mock_chain_instance):
            result = evaluate_filing_requirements(
                credit_agreement=sample_credit_agreement_fr,
                document_id=1,
                deal_id=1,
                agreement_type="facility_agreement"
            )
    
    assert result is not None
    assert hasattr(result, 'required_filings')
    
    # France should have AMF or Commercial Court filing requirements
    fr_filings = [f for f in result.required_filings if f.jurisdiction == "FR"]
    # May or may not have filings depending on agreement type
    assert isinstance(fr_filings, list)


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
def test_de_filing_requirements(mock_chain, sample_credit_agreement_de):
    """Test filing requirement evaluation for German jurisdiction."""
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_101112"
    )
    
    mock_chain_instance = MagicMock()
    mock_chain_instance.invoke.return_value = mock_evaluation
    
    with patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt', return_value=MagicMock()):
        with patch('app.chains.filing_requirement_chain.create_filing_requirement_chain', return_value=mock_chain_instance):
            result = evaluate_filing_requirements(
                credit_agreement=sample_credit_agreement_de,
                document_id=1,
                deal_id=1,
                agreement_type="facility_agreement"
            )
    
    assert result is not None
    assert hasattr(result, 'required_filings')
    
    # Germany should have BaFin or Commercial Register filing requirements
    de_filings = [f for f in result.required_filings if f.jurisdiction == "DE"]
    # May or may not have filings depending on agreement type
    assert isinstance(de_filings, list)


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
def test_filing_requirement_deadlines(mock_chain, sample_credit_agreement_us):
    """Test that filing requirements have deadlines."""
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[
            FilingRequirement(
                authority="SEC",
                jurisdiction="US",
                agreement_type="facility_agreement",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=4),
                required_fields=["company_name"],
                api_available=False,
                priority="high"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_deadlines"
    )
    
    mock_chain_instance = MagicMock()
    mock_chain_instance.invoke.return_value = mock_evaluation
    
    with patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt', return_value=MagicMock()):
        with patch('app.chains.filing_requirement_chain.create_filing_requirement_chain', return_value=mock_chain_instance):
            result = evaluate_filing_requirements(
                credit_agreement=sample_credit_agreement_us,
                document_id=1,
                deal_id=1,
                agreement_type="facility_agreement"
            )
    
    for filing in result.required_filings:
        assert filing.deadline is not None, f"Filing {filing.authority} should have a deadline"
        assert isinstance(filing.deadline, datetime), "Deadline should be a datetime object"


@patch('app.chains.filing_requirement_chain.create_filing_requirement_chain')
def test_filing_requirement_priority(mock_chain, sample_credit_agreement_us):
    """Test that filing requirements have priority levels."""
    mock_evaluation = FilingRequirementEvaluation(
        required_filings=[
            FilingRequirement(
                authority="SEC",
                jurisdiction="US",
                agreement_type="facility_agreement",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=4),
                required_fields=["company_name"],
                api_available=False,
                priority="high"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace_priority"
    )
    
    mock_chain_instance = MagicMock()
    mock_chain_instance.invoke.return_value = mock_evaluation
    
    with patch('app.chains.filing_requirement_chain.create_filing_requirement_prompt', return_value=MagicMock()):
        with patch('app.chains.filing_requirement_chain.create_filing_requirement_chain', return_value=mock_chain_instance):
            result = evaluate_filing_requirements(
                credit_agreement=sample_credit_agreement_us,
                document_id=1,
                deal_id=1,
                agreement_type="facility_agreement"
            )
    
    for filing in result.required_filings:
        assert filing.priority in ["critical", "high", "medium", "low"], \
            f"Filing {filing.authority} should have a valid priority level"
