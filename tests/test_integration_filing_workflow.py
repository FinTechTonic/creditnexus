"""
Integration tests for end-to-end filing workflow.
Tests UK automated filing and US/FR/DE manual filing workflows.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.filing_service import FilingService
from app.services.policy_service import FilingRequirement
from app.db.models import Document, DocumentFiling, Deal
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw


@pytest.fixture
def test_db():
    """Test database session."""
    # In a real test, you'd use a test database
    # For now, we'll use mocks
    db = Mock(spec=Session)
    return db


@pytest.fixture
def uk_credit_agreement():
    """UK credit agreement for automated filing."""
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
            ),
            Party(
                id="party_2",
                name="HSBC Bank",
                role="Lender",
                lei="22222222222222222222"
            )
        ],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(
                    amount=2000000.00,
                    currency=Currency.GBP
                )
            )
        ]
    )


@pytest.fixture
def us_credit_agreement():
    """US credit agreement for manual filing."""
    return CreditAgreement(
        deal_id="DEAL_US_001",
        loan_identification_number="LOAN_US_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.NEW_YORK,
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


@patch('app.services.filing_service.requests.post')
@patch('app.services.filing_service.evaluate_filing_requirements')
def test_uk_automated_filing_workflow(mock_eval, mock_post, test_db, uk_credit_agreement):
    """Test end-to-end UK automated filing workflow."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    
    # Setup
    filing_service = FilingService(test_db)
    
    # Mock document
    mock_doc = Mock(spec=Document)
    mock_doc.id = 1
    mock_doc.deal_id = 1
    mock_doc.agreement_date = datetime.now().date()
    mock_doc.total_commitment = 2000000.00
    mock_doc.currency = "GBP"
    mock_doc.source_cdm_data = uk_credit_agreement.model_dump()
    
    test_db.query.return_value.filter.return_value.first.return_value = mock_doc
    
    # Mock filing requirement evaluation
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="Companies House",
                filing_system="companies_house_api",
                deadline=datetime.now() + timedelta(days=21),
                required_fields=["company_number", "charge_description"],
                api_available=True,
                jurisdiction="UK",
                agreement_type="facility_agreement"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace"
    )
    
    # Mock Companies House API
    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {
        "transaction_id": "CH_TRANS_123",
        "filing_id": "CH_FILING_456",
        "filing_url": "https://find-and-update.company-information.service.gov.uk/...",
        "confirmation_url": "https://find-and-update.company-information.service.gov.uk/confirmation/..."
    }
    
    with patch('app.services.filing_service.settings') as mock_settings:
        mock_settings.COMPANIES_HOUSE_API_KEY = Mock(get_secret_value=lambda: "test_key")
        
        # 1. Determine requirements
        requirements = filing_service.determine_filing_requirements(
            document_id=1,
            agreement_type="facility_agreement",
            use_ai_evaluation=True
        )
        
        assert len(requirements) > 0
        uk_requirement = next((r for r in requirements if r.jurisdiction == "UK"), None)
        assert uk_requirement is not None
        assert uk_requirement.filing_system == "companies_house_api"
        
        # 2. File automatically
        filing = filing_service.file_document_automatically(1, uk_requirement)
        
        assert filing is not None
        assert filing.filing_status == "submitted"
        assert filing.filing_reference == "CH_TRANS_123"
        assert filing.jurisdiction == "UK"


@patch('app.services.filing_service.generate_filing_form_data')
@patch('app.services.filing_service.evaluate_filing_requirements')
def test_us_manual_filing_workflow(mock_eval, mock_form_gen, test_db, us_credit_agreement):
    """Test end-to-end US manual filing workflow."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    # Setup
    filing_service = FilingService(test_db)
    
    # Mock document
    mock_doc = Mock(spec=Document)
    mock_doc.id = 1
    mock_doc.deal_id = 1
    mock_doc.agreement_date = datetime.now().date()
    mock_doc.total_commitment = 5000000.00
    mock_doc.currency = "USD"
    mock_doc.source_cdm_data = us_credit_agreement.model_dump()
    
    test_db.query.return_value.filter.return_value.first.return_value = mock_doc
    
    # Mock filing requirement evaluation
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="SEC",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=4),
                required_fields=["company_name", "agreement_date", "total_commitment"],
                api_available=False,
                jurisdiction="US",
                agreement_type="facility_agreement",
                form_type="8-K"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace"
    )
    
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
            ),
            FilingFormField(
                field_name="Agreement Date",
                field_value=datetime.now().date().isoformat(),
                field_type="date",
                required=True
            )
        ],
        submission_url="https://www.sec.gov/edgar/searchedgar/companysearch.html"
    )
    
    # 1. Determine requirements
    requirements = filing_service.determine_filing_requirements(
        document_id=1,
        agreement_type="facility_agreement",
        use_ai_evaluation=True
    )
    
    assert len(requirements) > 0
    us_requirement = next((r for r in requirements if r.jurisdiction == "US"), None)
    assert us_requirement is not None
    assert us_requirement.filing_system == "manual_ui"
    
    # 2. Prepare manual filing
    filing = filing_service.prepare_manual_filing(1, us_requirement)
    
    assert filing is not None
    assert filing.filing_system == "manual_ui"
    assert filing.filing_status == "pending"
    assert filing.filing_payload is not None
    assert filing.manual_submission_url is not None
    
    # 3. Update manual filing status (simulating user submission)
    filing.filing_status = "submitted"
    filing.filing_reference = "SEC_FILING_789"
    filing.submitted_at = datetime.utcnow()
    
    updated = filing_service.update_manual_filing_status(
        filing_id=filing.id,
        filing_reference="SEC_FILING_789",
        submission_notes="Submitted via SEC EDGAR portal"
    )
    
    assert updated.filing_status == "submitted"
    assert updated.filing_reference == "SEC_FILING_789"


@patch('app.services.filing_service.generate_filing_form_data')
@patch('app.services.filing_service.evaluate_filing_requirements')
def test_fr_manual_filing_workflow(mock_eval, mock_form_gen, test_db):
    """Test end-to-end French manual filing workflow."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    fr_agreement = CreditAgreement(
        deal_id="DEAL_FR_001",
        loan_identification_number="LOAN_FR_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.FRENCH,
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
                )
            )
        ]
    )
    
    filing_service = FilingService(test_db)
    
    mock_doc = Mock(spec=Document)
    mock_doc.id = 1
    mock_doc.deal_id = 1
    mock_doc.source_cdm_data = fr_agreement.model_dump()
    
    test_db.query.return_value.filter.return_value.first.return_value = mock_doc
    
    # Mock filing requirement
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="AMF",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=15),
                required_fields=["borrower_name", "borrower_siren"],
                api_available=False,
                jurisdiction="FR",
                agreement_type="facility_agreement",
                language_requirement="French"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace"
    )
    
    # Mock form generation
    mock_form_gen.return_value = FilingFormData(
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
        language="fr",
        submission_url="https://www.amf-france.org/en/your-requests/declarations"
    )
    
    requirements = filing_service.determine_filing_requirements(
        document_id=1,
        agreement_type="facility_agreement",
        use_ai_evaluation=True
    )
    
    fr_requirement = next((r for r in requirements if r.jurisdiction == "FR"), None)
    if fr_requirement:
        filing = filing_service.prepare_manual_filing(1, fr_requirement)
        assert filing.jurisdiction == "FR"
        assert filing.filing_system == "manual_ui"


@patch('app.services.filing_service.generate_filing_form_data')
@patch('app.services.filing_service.evaluate_filing_requirements')
def test_de_manual_filing_workflow(mock_eval, mock_form_gen, test_db):
    """Test end-to-end German manual filing workflow."""
    from app.models.filing_requirements import FilingRequirementEvaluation, FilingRequirement as FilingReqModel
    from app.models.filing_forms import FilingFormData, FilingFormField
    
    de_agreement = CreditAgreement(
        deal_id="DEAL_DE_001",
        loan_identification_number="LOAN_DE_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.GERMAN,
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
                )
            )
        ]
    )
    
    filing_service = FilingService(test_db)
    
    mock_doc = Mock(spec=Document)
    mock_doc.id = 1
    mock_doc.deal_id = 1
    mock_doc.source_cdm_data = de_agreement.model_dump()
    
    test_db.query.return_value.filter.return_value.first.return_value = mock_doc
    
    # Mock filing requirement
    mock_eval.return_value = FilingRequirementEvaluation(
        required_filings=[
            FilingReqModel(
                authority="BaFin",
                filing_system="manual_ui",
                deadline=datetime.now() + timedelta(days=15),
                required_fields=["borrower_name", "borrower_hrb"],
                api_available=False,
                jurisdiction="DE",
                agreement_type="facility_agreement",
                language_requirement="German"
            )
        ],
        compliance_status="compliant",
        missing_fields=[],
        deadline_alerts=[],
        trace_id="test_trace"
    )
    
    # Mock form generation
    mock_form_gen.return_value = FilingFormData(
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
        language="de",
        submission_url="https://www.bafin.de/EN/Aufsicht/Unternehmen/Unternehmen_node_en.html"
    )
    
    requirements = filing_service.determine_filing_requirements(
        document_id=1,
        agreement_type="facility_agreement",
        use_ai_evaluation=True
    )
    
    de_requirement = next((r for r in requirements if r.jurisdiction == "DE"), None)
    if de_requirement:
        filing = filing_service.prepare_manual_filing(1, de_requirement)
        assert filing.jurisdiction == "DE"
        assert filing.filing_system == "manual_ui"
