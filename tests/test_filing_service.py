"""
Unit tests for FilingService with mocked Companies House API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.filing_service import FilingService
from app.services.policy_service import FilingRequirement
from app.db.models import Document, DocumentFiling
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_document():
    """Mock document with UK company data."""
    doc = Mock(spec=Document)
    doc.id = 1
    doc.deal_id = 1
    doc.agreement_date = datetime.now().date()
    doc.total_commitment = 5000000.00
    doc.currency = "GBP"
    doc.source_cdm_data = {
        "deal_id": "DEAL_UK_001",
        "parties": [
            {
                "id": "party_1",
                "name": "UK Corp Ltd",
                "role": "Borrower",
                "jurisdiction": "UK",
                "company_number": "12345678"
            }
        ],
        "facilities": [
            {
                "facility_name": "Term Loan",
                "commitment_amount": {
                    "amount": 5000000.00,
                    "currency": "GBP"
                }
            }
        ]
    }
    return doc


@pytest.fixture
def filing_service(mock_db):
    """FilingService instance with mocked database."""
    with patch('app.services.filing_service.get_policy_engine') as mock_engine:
        service = FilingService(mock_db)
        return service


@pytest.fixture
def uk_filing_requirement():
    """UK Companies House filing requirement."""
    return FilingRequirement(
        authority="Companies House",
        filing_system="companies_house_api",
        deadline=datetime.now() + timedelta(days=21),
        required_fields=["company_number", "charge_description"],
        api_available=True,
        api_endpoint="POST /company/{company_number}/charges",
        jurisdiction="UK",
        agreement_type="facility_agreement"
    )


@patch('app.services.filing_service.evaluate_filing_requirements')
def test_determine_filing_requirements(mock_eval, filing_service, mock_db, mock_document):
    """Test determine_filing_requirements with AI evaluation."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    
    # Mock document query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    # Mock AI evaluation
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="Companies House",
                filing_system="companies_house_api",
                deadline=datetime.now() + timedelta(days=21),
                required_fields=["company_number"],
                api_available=True,
                jurisdiction="UK"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace"
    )
    
    requirements = filing_service.determine_filing_requirements(
        document_id=1,
        agreement_type="facility_agreement",
        use_ai_evaluation=True
    )
    
    assert len(requirements) > 0
    assert requirements[0].authority == "Companies House"
    assert requirements[0].filing_system == "companies_house_api"


@patch('app.services.filing_service.requests.post')
def test_file_companies_house(mock_post, filing_service, mock_db, mock_document, uk_filing_requirement):
    """Test Companies House API filing."""
    # Mock document query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    # Mock Companies House API response
    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {
        "transaction_id": "CH_TRANS_123",
        "filing_id": "CH_FILING_456",
        "filing_url": "https://find-and-update.company-information.service.gov.uk/...",
        "confirmation_url": "https://find-and-update.company-information.service.gov.uk/confirmation/..."
    }
    
    with patch('app.services.filing_service.settings') as mock_settings:
        mock_settings.COMPANIES_HOUSE_API_KEY = Mock(get_secret_value=lambda: "test_key")
        
        result = filing_service._file_companies_house(1, uk_filing_requirement)
        
        assert result is not None
        assert isinstance(result, DocumentFiling)
        assert result.filing_status == "submitted"
        assert result.filing_reference == "CH_TRANS_123"
        assert result.jurisdiction == "UK"


@patch('app.services.filing_service.generate_filing_form_data')
def test_prepare_manual_filing(mock_form_gen, filing_service, mock_db, mock_document):
    """Test manual filing preparation."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    # Mock document query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    # Mock form generation
    mock_form_gen.return_value = FilingFormData(
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
        submission_url="https://www.sec.gov/edgar/searchedgar/companysearch.html"
    )
    
    requirement = FilingRequirement(
        authority="SEC",
        filing_system="manual_ui",
        deadline=datetime.now() + timedelta(days=4),
        required_fields=["company_name"],
        api_available=False,
        jurisdiction="US",
        agreement_type="facility_agreement"
    )
    
    result = filing_service.prepare_manual_filing(1, requirement)
    
    assert result is not None
    assert isinstance(result, DocumentFiling)
    assert result.filing_system == "manual_ui"
    assert result.filing_status == "pending"
    assert result.filing_payload is not None


def test_update_manual_filing_status(filing_service, mock_db):
    """Test manual filing status update."""
    # Mock filing in database
    mock_filing = Mock(spec=DocumentFiling)
    mock_filing.id = 1
    mock_filing.filing_status = "pending"
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_filing
    
    result = filing_service.update_manual_filing_status(
        filing_id=1,
        filing_reference="SEC_FILING_789",
        submission_notes="Submitted via SEC portal",
        submitted_by=1
    )
    
    assert result is not None
    assert mock_filing.filing_status == "submitted"
    assert mock_filing.filing_reference == "SEC_FILING_789"
    assert mock_filing.submitted_by == 1
    mock_db.commit.assert_called_once()


def test_extract_company_number(filing_service, mock_db, mock_document):
    """Test company number extraction."""
    # Mock document version with CDM data
    from app.db.models import DocumentVersion
    
    mock_version = Mock(spec=DocumentVersion)
    mock_version.id = 1
    mock_version.cdm_data = {
        "parties": [
            {
                "jurisdiction": "UK",
                "company_number": "12345678"
            }
        ]
    }
    
    mock_document.current_version_id = 1
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_version,  # Version query
        mock_document  # Document query
    ]
    
    company_number = filing_service._extract_company_number(mock_document)
    
    assert company_number == "12345678"


def test_extract_lenders(filing_service, mock_db, mock_document):
    """Test lender extraction."""
    mock_document.source_cdm_data = {
        "parties": [
            {
                "name": "ACME Corp",
                "role": "Borrower",
                "lei": "12345678901234567890"
            },
            {
                "name": "Bank of America",
                "role": "Lender",
                "lei": "98765432109876543210"
            }
        ]
    }
    
    lenders = filing_service._extract_lenders(mock_document)
    
    assert len(lenders) > 0
    assert any("Bank" in lender.get("name", "") for lender in lenders)
