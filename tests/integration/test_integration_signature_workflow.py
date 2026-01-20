"""
Integration tests for end-to-end signature workflow with AI-assisted signer detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.signature_service import SignatureService
from app.db.models import Document, DocumentSignature, DocumentVersion
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, GoverningLaw
from app.models.signature_requests import SignatureRequestGeneration, Signer


@pytest.fixture
def test_db():
    """Test database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def sample_credit_agreement():
    """Sample credit agreement with multiple parties."""
    return CreditAgreement(
        deal_id="DEAL_001",
        loan_identification_number="LOAN_001",
        agreement_date=datetime.now().date(),
        governing_law=GoverningLaw.NEW_YORK,
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
                )
            )
        ]
    )


@patch('app.services.signature_service.generate_signature_request')
@patch('app.services.signature_service.requests.post')
def test_ai_assisted_signature_workflow(mock_post, mock_ai, test_db, sample_credit_agreement):
    """Test end-to-end signature workflow with AI-assisted signer detection."""
    # Setup
    with patch('app.services.signature_service.settings') as mock_settings:
        mock_settings.DIGISIGNER_API_KEY = Mock(get_secret_value=lambda: "test_key")
        mock_settings.DIGISIGNER_BASE_URL = "https://api.digisigner.com/v1"
        
        signature_service = SignatureService(test_db)
        
        # Mock document
        mock_doc = Mock(spec=Document)
        mock_doc.id = 1
        mock_doc.deal_id = 1
        mock_doc.source_cdm_data = sample_credit_agreement.model_dump()
        mock_doc.current_version_id = 1
        
        # Mock document version
        mock_version = Mock(spec=DocumentVersion)
        mock_version.id = 1
        mock_version.file_path = "/path/to/document.pdf"
        
        test_db.query.return_value.filter.return_value.first.side_effect = [
            mock_version,  # Version query
            mock_doc  # Document query
        ]
        
        # Mock AI signer detection
        mock_ai.return_value = SignatureRequestGeneration(
            signers=[
                Signer(
                    name="ACME Corp",
                    email="borrower@acme.com",
                    role="Borrower",
                    signing_order=0,
                    required=True
                ),
                Signer(
                    name="Bank of America",
                    email="lender@bofa.com",
                    role="Lender",
                    signing_order=0,
                    required=True
                )
            ],
            signing_workflow="parallel",
            expiration_days=30,
            reminder_enabled=True,
            reminder_days=[7, 3, 1],
            message="Please review and sign the credit agreement"
        )
        
        # Mock file exists
        with patch('app.services.signature_service.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            
            # Mock DigiSigner API responses
            mock_post.return_value.ok = True
            mock_post.return_value.json.side_effect = [
                {"document_id": "digisigner_doc_123"},  # Upload response
                {
                    "signature_request_id": "sig_req_456",
                    "id": "sig_req_456",
                    "status": "pending"
                }  # Signature request response
            ]
            
            # Mock file open
            with patch('builtins.open', create=True):
                # 1. Request signature with AI detection
                signature = signature_service.request_signature(
                    document_id=1,
                    auto_detect_signers=True,
                    expires_in_days=30
                )
                
                assert signature is not None
                assert isinstance(signature, DocumentSignature)
                assert signature.signature_request_id == "sig_req_456"
                assert signature.signature_status == "pending"
                assert len(signature.signers) == 2
                
                # Verify AI was called
                mock_ai.assert_called_once()
                
                # 2. Check signature status
                mock_get = MagicMock()
                mock_get.return_value.ok = True
                mock_get.return_value.json.return_value = {
                    "status": "pending",
                    "signers": [
                        {"email": "borrower@acme.com", "signed_at": None},
                        {"email": "lender@bofa.com", "signed_at": None}
                    ]
                }
                
                with patch('app.services.signature_service.requests.get', mock_get):
                    status = signature_service.check_signature_status("sig_req_456")
                    assert status is not None
                    assert status.get("status") == "pending"
                
                # 3. Simulate completion
                mock_get.return_value.json.return_value = {
                    "status": "completed",
                    "signed_document_url": "https://digisigner.com/signed/doc.pdf",
                    "signers": [
                        {"email": "borrower@acme.com", "signed_at": datetime.now().isoformat()},
                        {"email": "lender@bofa.com", "signed_at": datetime.now().isoformat()}
                    ]
                }
                
                with patch('app.services.signature_service.requests.get', mock_get):
                    status = signature_service.check_signature_status("sig_req_456")
                    assert status.get("status") == "completed"
                    
                    # Update signature status
                    updated = signature_service.update_signature_status(
                        signature_id=signature.id,
                        status="completed",
                        signed_document_url="https://digisigner.com/signed/doc.pdf"
                    )
                    
                    assert updated.signature_status == "completed"
                    assert updated.completed_at is not None


@patch('app.services.signature_service.generate_signature_request')
@patch('app.services.signature_service.requests.post')
def test_sequential_signature_workflow(mock_post, mock_ai, test_db, sample_credit_agreement):
    """Test sequential signature workflow."""
    with patch('app.services.signature_service.settings') as mock_settings:
        mock_settings.DIGISIGNER_API_KEY = Mock(get_secret_value=lambda: "test_key")
        mock_settings.DIGISIGNER_BASE_URL = "https://api.digisigner.com/v1"
        
        signature_service = SignatureService(test_db)
        
        mock_doc = Mock(spec=Document)
        mock_doc.id = 1
        mock_doc.source_cdm_data = sample_credit_agreement.model_dump()
        mock_doc.current_version_id = 1
        
        mock_version = Mock(spec=DocumentVersion)
        mock_version.id = 1
        mock_version.file_path = "/path/to/document.pdf"
        
        test_db.query.return_value.filter.return_value.first.side_effect = [
            mock_version,
            mock_doc
        ]
        
        # Mock sequential workflow
        mock_ai.return_value = SignatureRequestGeneration(
            signers=[
                Signer(
                    name="ACME Corp",
                    email="borrower@acme.com",
                    role="Borrower",
                    signing_order=1,
                    required=True
                ),
                Signer(
                    name="Bank of America",
                    email="lender@bofa.com",
                    role="Lender",
                    signing_order=2,
                    required=True
                )
            ],
            signing_workflow="sequential",
            expiration_days=30
        )
        
        with patch('app.services.signature_service.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            
            mock_post.return_value.ok = True
            mock_post.return_value.json.side_effect = [
                {"document_id": "digisigner_doc_123"},
                {"signature_request_id": "sig_req_789", "id": "sig_req_789"}
            ]
            
            with patch('builtins.open', create=True):
                signature = signature_service.request_signature(
                    document_id=1,
                    auto_detect_signers=True,
                    urgency="time_sensitive"
                )
                
                assert signature is not None
                # Verify sequential workflow was used
                mock_ai.assert_called_once()
                call_kwargs = mock_ai.call_args[1]
                assert call_kwargs.get("urgency") == "time_sensitive"


@patch('app.services.signature_service.requests.get')
def test_signature_download_workflow(mock_get, test_db):
    """Test signed document download workflow."""
    with patch('app.services.signature_service.settings') as mock_settings:
        mock_settings.DIGISIGNER_API_KEY = Mock(get_secret_value=lambda: "test_key")
        mock_settings.DIGISIGNER_BASE_URL = "https://api.digisigner.com/v1"
        
        signature_service = SignatureService(test_db)
        
        # Mock signature
        mock_signature = Mock(spec=DocumentSignature)
        mock_signature.id = 1
        mock_signature.signature_request_id = "sig_req_123"
        mock_signature.signature_status = "completed"
        
        test_db.query.return_value.filter.return_value.first.return_value = mock_signature
        
        # Mock download
        mock_get.return_value.ok = True
        mock_get.return_value.content = b"PDF content here"
        
        content = signature_service.download_signed_document("sig_req_123")
        
        assert content == b"PDF content here"
        mock_get.assert_called_once()
