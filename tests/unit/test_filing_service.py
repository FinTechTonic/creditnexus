"""
Unit tests for FilingService with mocked Companies House API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.filing_service import FilingService, FilingError, FilingAPIError
from app.services.policy_service import FilingRequirement
from app.db.models import Document, DocumentFiling, DocumentVersion
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_document():
    """Mock document with UK company data."""
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    
    doc = Mock(spec=Document)
    doc.id = 1
    doc.deal_id = 1
    doc.agreement_date = datetime.now().date()
    doc.total_commitment = 5000000.00
    doc.currency = "GBP"
    
    # Create proper CreditAgreement object
    credit_agreement = CreditAgreement(
        deal_id="DEAL_UK_001",
        loan_identification_number="LOAN_UK_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.ENGLISH,
        parties=[
            Party(
                id="party_1",
                name="UK Corp Ltd",
                role="Borrower",
                lei="11111111111111111111"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=5000000.00,
                    currency=Currency.GBP
                )
            )
        ]
    )
    doc.source_cdm_data = credit_agreement.model_dump()
    doc.current_version_id = None
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


@patch('app.services.filing_service.evaluate_filing_requirements_chain')
def test_determine_filing_requirements(mock_eval, filing_service, mock_db, mock_document):
    """Test determine_filing_requirements with AI evaluation."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    
    # Mock document query - need to handle _get_credit_agreement_from_document
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    # Mock AI evaluation chain
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="Companies House",
                filing_system="companies_house_api",
                deadline=datetime.now() + timedelta(days=21),
                required_fields=["company_number"],
                api_available=True,
                jurisdiction="UK",
                agreement_type="facility_agreement",
                priority="high"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace",
        metadata={}
    )
    
    # Mock _get_credit_agreement_from_document
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    credit_agreement = CreditAgreement(
        deal_id="DEAL_UK_001",
        loan_identification_number="LOAN_UK_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.ENGLISH,
        parties=[
            Party(
                id="party_1",
                name="UK Corp Ltd",
                role="Borrower",
                lei="11111111111111111111"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=5000000.00,
                    currency=Currency.GBP
                )
            )
        ]
    )
    
    with patch.object(filing_service, '_get_credit_agreement_from_document', return_value=credit_agreement):
        requirements = filing_service.determine_filing_requirements(
            document_id=1,
            agreement_type="facility_agreement",
            use_ai_evaluation=True
        )
        
        assert len(requirements) > 0
        assert requirements[0].authority == "Companies House"
        assert requirements[0].filing_system == "companies_house_api"


def test_file_document_automatically(filing_service, mock_db, mock_document, uk_filing_requirement):
    """Test automatic filing via Companies House API."""
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    
    # Create a mock filing that will be returned
    mock_filing = Mock(spec=DocumentFiling)
    mock_filing.id = 1
    mock_filing.document_id = 1
    mock_filing.deal_id = 1
    mock_filing.filing_status = "pending"
    mock_filing.retry_count = 0
    mock_filing.filing_reference = None
    mock_filing.filing_url = None
    mock_filing.confirmation_url = None
    mock_filing.filing_response = None
    mock_filing.filed_at = None
    mock_filing.error_message = None
    
    # Mock queries - first for existing filing (None), then for document
    def query_filter_first(*args):
        # First call: DocumentFiling query (no existing filing)
        # Second call: Document query
        if len(mock_db._query_calls) == 0:
            mock_db._query_calls.append(1)
            return None
        else:
            return mock_document
    
    mock_db._query_calls = []
    mock_db.query.return_value.filter.return_value.first.side_effect = query_filter_first
    mock_db.add = Mock()
    mock_db.flush = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock(side_effect=lambda x: setattr(x, 'id', 1) if hasattr(x, 'id') else None)
    
    # Mock _get_credit_agreement_from_document
    credit_agreement = CreditAgreement(
        deal_id="DEAL_UK_001",
        loan_identification_number="LOAN_UK_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.ENGLISH,
        parties=[
            Party(
                id="party_1",
                name="UK Corp Ltd",
                role="Borrower",
                lei="11111111111111111111"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=5000000.00,
                    currency=Currency.GBP
                )
            )
        ]
    )
    
    with patch.object(filing_service, '_get_credit_agreement_from_document', return_value=credit_agreement):
        with patch.object(filing_service, '_submit_to_companies_house', return_value={
            "filing_reference": "CH_TRANS_123",
            "filing_url": "https://find-and-update.company-information.service.gov.uk/...",
            "confirmation_url": "https://find-and-update.company-information.service.gov.uk/confirmation/...",
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat()
        }):
            # Mock the add to create a filing-like object
            created_filing = Mock(spec=DocumentFiling)
            created_filing.id = 1
            created_filing.document_id = 1
            created_filing.deal_id = 1
            created_filing.filing_status = "submitted"
            created_filing.filing_reference = "CH_TRANS_123"
            
            def add_side_effect(obj):
                if isinstance(obj, DocumentFiling) or hasattr(obj, 'filing_status'):
                    # Set attributes on the created filing
                    obj.id = 1
                    obj.filing_status = "pending"
                    obj.retry_count = 0
                    created_filing = obj
            
            mock_db.add.side_effect = add_side_effect
            
            # Make query return document when needed
            def smart_query(model):
                query_mock = Mock()
                filter_mock = Mock()
                if model == DocumentFiling:
                    # First call returns None (no existing), subsequent calls return our filing
                    if not hasattr(mock_db, '_filing_queried'):
                        mock_db._filing_queried = True
                        filter_mock.first.return_value = None
                    else:
                        filter_mock.first.return_value = created_filing
                elif model == Document:
                    filter_mock.first.return_value = mock_document
                else:
                    filter_mock.first.return_value = None
                query_mock.filter.return_value = filter_mock
                return query_mock
            
            mock_db.query.side_effect = smart_query
            
            result = filing_service.file_document_automatically(1, uk_filing_requirement)
            
            assert result is not None
            # The result should be a DocumentFiling-like object
            assert hasattr(result, 'filing_status')


@patch('app.services.filing_service.generate_filing_form_data')
def test_prepare_manual_filing(mock_form_gen, filing_service, mock_db, mock_document):
    """Test manual filing preparation."""
    from app.models.filing_forms import FilingFormData, FilingFormField
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    
    # Mock document query - check for existing filing first, then document
    mock_existing_filing = None
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_existing_filing,  # No existing filing
        mock_document  # Document query
    ]
    
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
        document_references=[],
        submission_url="https://www.sec.gov/edgar/searchedgar/companysearch.html",
        instructions="Submit via SEC EDGAR portal",
        language="en"
    )
    
    # Mock CreditAgreement
    credit_agreement = CreditAgreement(
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
                )
            )
        ]
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
    
    # Mock _get_credit_agreement_from_document
    with patch.object(filing_service, '_get_credit_agreement_from_document', return_value=credit_agreement):
        mock_filing = Mock(spec=DocumentFiling)
        mock_filing.id = 1
        mock_filing.filing_system = "manual_ui"
        mock_filing.filing_status = "pending"
        mock_filing.filing_payload = mock_form_gen.return_value.model_dump()
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda x: setattr(x, 'id', 1))
        
        result = filing_service.prepare_manual_filing(1, requirement)
        
        assert result is not None
        assert isinstance(result, DocumentFiling)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


def test_update_manual_filing_status(filing_service, mock_db):
    """Test manual filing status update."""
    # Mock filing in database
    mock_filing = Mock(spec=DocumentFiling)
    mock_filing.id = 1
    mock_filing.filing_status = "pending"
    mock_filing.filing_reference = None
    mock_filing.submitted_by = None
    mock_filing.submitted_at = None
    mock_filing.submission_notes = None
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_filing
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
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
    assert mock_filing.submission_notes == "Submitted via SEC portal"
    assert mock_filing.submitted_at is not None
    mock_db.commit.assert_called_once()


def test_get_credit_agreement_from_document_source_cdm_data(filing_service, mock_db, mock_document):
    """Test getting CreditAgreement from document source_cdm_data."""
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    
    # Mock document with source_cdm_data
    credit_agreement = CreditAgreement(
        deal_id="DEAL_UK_001",
        loan_identification_number="LOAN_UK_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.ENGLISH,
        parties=[
            Party(
                id="party_1",
                name="UK Corp Ltd",
                role="Borrower",
                lei="11111111111111111111"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=5000000.00,
                    currency=Currency.GBP
                )
            )
        ]
    )
    mock_document.source_cdm_data = credit_agreement.model_dump()
    mock_document.current_version_id = None
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    result = filing_service._get_credit_agreement_from_document(1)
    
    assert result is not None
    assert isinstance(result, CreditAgreement)
    assert result.deal_id == "DEAL_UK_001"


def test_get_credit_agreement_from_document_version(filing_service, mock_db, mock_document):
    """Test getting CreditAgreement from DocumentVersion."""
    from app.db.models import DocumentVersion
    from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
    
    # Mock document with version
    credit_agreement = CreditAgreement(
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
                )
            )
        ]
    )
    
    mock_document.source_cdm_data = None
    mock_document.current_version_id = 1
    
    mock_version = Mock(spec=DocumentVersion)
    mock_version.id = 1
    mock_version.extracted_data = credit_agreement.model_dump()
    
    # Mock queries: document first, then version
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_document,  # Document query
        mock_version    # Version query
    ]
    
    result = filing_service._get_credit_agreement_from_document(1)
    
    assert result is not None
    assert isinstance(result, CreditAgreement)
    assert result.deal_id == "DEAL_US_001"
