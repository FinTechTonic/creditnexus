"""
Unit tests for filing form generation chain.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.chains.filing_form_generation_chain import generate_filing_form_data
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw, InterestRatePayout, FloatingRateOption, Frequency, PeriodEnum
from app.services.policy_service import FilingRequirement


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
        ]
    )


@pytest.fixture
def sample_credit_agreement_fr():
    """Sample French credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_FR_001",
        loan_identification_number="LOAN_FR_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.OTHER,  # French not in enum
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
        ]
    )


@pytest.fixture
def sample_credit_agreement_de():
    """Sample German credit agreement."""
    return CreditAgreement(
        deal_id="DEAL_DE_001",
        loan_identification_number="LOAN_DE_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.OTHER,  # German not in enum
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
        ]
    )


@pytest.fixture
def us_filing_requirement():
    """US SEC filing requirement."""
    return FilingRequirement(
        authority="SEC",
        filing_system="manual_ui",
        deadline=datetime.now() + timedelta(days=4),
        required_fields=["borrower_name", "agreement_date", "total_commitment"],
        api_available=False,
        jurisdiction="US",
        agreement_type="facility_agreement",
        form_type="8-K",
        priority="high"
    )


@pytest.fixture
def fr_filing_requirement():
    """French AMF filing requirement."""
    return FilingRequirement(
        authority="AMF",
        filing_system="manual_ui",
        deadline=datetime.now() + timedelta(days=15),
        required_fields=["borrower_name", "borrower_siren", "agreement_date"],
        api_available=False,
        jurisdiction="FR",
        agreement_type="facility_agreement",
        language_requirement="French",
        priority="medium"
    )


@pytest.fixture
def de_filing_requirement():
    """German BaFin filing requirement."""
    return FilingRequirement(
        authority="BaFin",
        filing_system="manual_ui",
        deadline=datetime.now() + timedelta(days=15),
        required_fields=["borrower_name", "borrower_hrb", "agreement_date"],
        api_available=False,
        jurisdiction="DE",
        agreement_type="facility_agreement",
        language_requirement="German",
        priority="medium"
    )


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_us_form_generation(mock_prompt_func, mock_chain_func, sample_credit_agreement_us, us_filing_requirement):
    """Test form generation for US SEC filing."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="US",
        authority="SEC",
        form_type="8-K",
        fields=[
            FilingFormField(
                field_name="Company Name",
                field_value="ACME Corp",
                field_type="text",
                required=True
            )
        ],
        language="en"
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_us,
        filing_requirement=us_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    assert result is not None
    assert result.jurisdiction == "US"
    assert result.authority == "SEC"
    assert result.form_type == "8-K"
    assert len(result.fields) > 0
    
    # Check that required fields are present
    field_names = [f.field_name for f in result.fields]
    assert len(field_names) > 0  # Should have at least one field
    assert result.language == "en"


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_fr_form_generation(mock_prompt_func, mock_chain_func, sample_credit_agreement_fr, fr_filing_requirement):
    """Test form generation for French AMF filing."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="FR",
        authority="AMF",
        form_type="Foreign Investment Declaration",
        fields=[
            FilingFormField(
                field_name="Nom de l'entreprise",
                field_value="Société Française SA",
                field_type="text",
                required=True
            )
        ],
        language="fr"
    )
    
    mock_prompt = MagicMock()
    mock_structured_llm = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = mock_structured_llm
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_fr,
        filing_requirement=fr_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    assert result is not None
    assert result.jurisdiction == "FR"
    assert result.authority == "AMF"
    assert result.language == "fr"  # French language requirement
    
    # Check that fields are present
    field_names = [f.field_name for f in result.fields]
    assert len(field_names) > 0  # Should have at least one field


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_de_form_generation(mock_prompt_func, mock_chain_func, sample_credit_agreement_de, de_filing_requirement):
    """Test form generation for German BaFin filing."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="DE",
        authority="BaFin",
        form_type="Foreign Investment Notification",
        fields=[
            FilingFormField(
                field_name="Firmenname",
                field_value="Deutsche GmbH",
                field_type="text",
                required=True
            )
        ],
        language="de"
    )
    
    mock_prompt = MagicMock()
    mock_structured_llm = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = mock_structured_llm
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_de,
        filing_requirement=de_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    assert result is not None
    assert result.jurisdiction == "DE"
    assert result.authority == "BaFin"
    assert result.language == "de"  # German language requirement
    
    # Check that fields are present
    field_names = [f.field_name for f in result.fields]
    assert len(field_names) > 0  # Should have at least one field


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_form_field_types(mock_prompt_func, mock_chain_func, sample_credit_agreement_us, us_filing_requirement):
    """Test that form fields have correct types."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="US",
        authority="SEC",
        form_type="8-K",
        fields=[
            FilingFormField(field_name="Company Name", field_value="ACME", field_type="text", required=True),
            FilingFormField(field_name="Date", field_value="2026-01-15", field_type="date", required=True)
        ],
        language="en"
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_us,
        filing_requirement=us_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    for field in result.fields:
        assert field.field_type in ["text", "date", "number", "select", "file"]
        assert field.field_name is not None
        # Field value may be None for optional fields
        assert field.required in [True, False]


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_form_submission_url(mock_prompt_func, mock_chain_func, sample_credit_agreement_us, us_filing_requirement):
    """Test that form includes submission URL when available."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="US",
        authority="SEC",
        form_type="8-K",
        fields=[FilingFormField(field_name="Company Name", field_value="ACME", field_type="text", required=True)],
        submission_url="https://www.sec.gov/edgar/searchedgar/companysearch.html",
        language="en"
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_us,
        filing_requirement=us_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    # Submission URL may or may not be present
    if result.submission_url:
        assert result.submission_url.startswith("http")


@patch('app.chains.filing_form_generation_chain.create_filing_form_chain')
@patch('app.chains.filing_form_generation_chain.create_filing_form_prompt')
def test_form_instructions(mock_prompt_func, mock_chain_func, sample_credit_agreement_us, us_filing_requirement):
    """Test that form includes instructions when available."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    mock_evaluation = FilingFormData(
        jurisdiction="US",
        authority="SEC",
        form_type="8-K",
        fields=[FilingFormField(field_name="Company Name", field_value="ACME", field_type="text", required=True)],
        instructions="Submit via EDGAR portal",
        language="en"
    )
    
    mock_prompt = MagicMock()
    mock_evaluation_chain = MagicMock()
    mock_evaluation_chain.invoke.return_value = mock_evaluation
    mock_prompt.__or__ = MagicMock(return_value=mock_evaluation_chain)
    mock_prompt_func.return_value = mock_prompt
    mock_chain_func.return_value = MagicMock()
    
    result = generate_filing_form_data(
        credit_agreement=sample_credit_agreement_us,
        filing_requirement=us_filing_requirement,
        document_id=1,
        deal_id=1
    )
    
    # Instructions may or may not be present
    if result.instructions:
        assert len(result.instructions) > 0
