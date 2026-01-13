"""
Unit tests for SignatureService with mocked DigiSigner API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.signature_service import SignatureService
from app.db.models import Document, DocumentSignature, DocumentVersion
from app.core.config import settings


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_document():
    """Mock document."""
    doc = Mock(spec=Document)
    doc.id = 1
    doc.deal_id = 1
    doc.source_cdm_data = {
        "deal_id": "DEAL_001",
        "parties": [
            {
                "id": "party_1",
                "name": "ACME Corp",
                "role": "Borrower",
                "email": "borrower@acme.com"
            },
            {
                "id": "party_2",
                "name": "Bank of America",
                "role": "Lender",
                "email": "lender@bofa.com"
            }
        ]
    }
    doc.current_version_id = 1
    return doc


@pytest.fixture
def mock_document_version():
    """Mock document version."""
    version = Mock(spec=DocumentVersion)
    version.id = 1
    version.file_path = "/path/to/document.pdf"
    return version


@pytest.fixture
def signature_service(mock_db):
    """SignatureService instance with mocked database."""
    with patch('app.services.signature_service.settings') as mock_settings:
        mock_settings.DIGISIGNER_API_KEY = Mock(get_secret_value=lambda: "test_key")
        mock_settings.DIGISIGNER_BASE_URL = "https://api.digisigner.com/v1"
        service = SignatureService(mock_db)
        return service


@patch('app.services.signature_service.requests.post')
@patch('app.services.signature_service.requests.get')
def test_request_signature(mock_get, mock_post, signature_service, mock_db, mock_document, mock_document_version):
    """Test signature request creation."""
    # Mock document query
    mock_db.query.return_value.filter.return_value.first.return_value = mock_document
    
    # Mock document version query
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_document_version,  # For version query
        None  # For other queries
    ]
    
    # Mock file exists
    with patch('app.services.signature_service.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        
        # Mock DigiSigner API responses
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            "document_id": "digisigner_doc_123",
            "id": "digisigner_doc_123"
        }
        
        mock_post.return_value.json.side_effect = [
            {"document_id": "digisigner_doc_123"},  # Upload response
            {"signature_request_id": "sig_req_456", "id": "sig_req_456"}  # Signature request response
        ]
        
        # Mock AI chain
        with patch('app.services.signature_service.generate_signature_request') as mock_ai:
            from app.models.signature_requests import SignatureRequestGeneration, Signer
            mock_ai.return_value = SignatureRequestGeneration(
                signers=[
                    Signer(name="ACME Corp", email="borrower@acme.com", role="Borrower"),
                    Signer(name="Bank of America", email="lender@bofa.com", role="Lender")
                ],
                expiration_days=30
            )
            
            # Mock file open
            with patch('builtins.open', create=True):
                result = signature_service.request_signature(
                    document_id=1,
                    auto_detect_signers=True
                )
                
                assert result is not None
                assert isinstance(result, DocumentSignature)
                assert result.signature_request_id == "sig_req_456"
                assert result.signature_status == "pending"


@patch('app.services.signature_service.requests.get')
def test_check_signature_status(mock_get, signature_service, mock_db):
    """Test signature status check."""
    # Mock signature in database
    mock_signature = Mock(spec=DocumentSignature)
    mock_signature.id = 1
    mock_signature.signature_request_id = "sig_req_123"
    mock_signature.signature_status = "pending"
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_signature
    
    # Mock DigiSigner API response
    mock_get.return_value.ok = True
    mock_get.return_value.json.return_value = {
        "status": "completed",
        "signed_document_url": "https://digisigner.com/signed/doc.pdf"
    }
    
    result = signature_service.check_signature_status("sig_req_123")
    
    assert result is not None
    assert result.get("status") == "completed"
    assert "signed_document_url" in result


@patch('app.services.signature_service.requests.get')
def test_download_signed_document(mock_get, signature_service):
    """Test signed document download."""
    # Mock DigiSigner API response
    mock_get.return_value.ok = True
    mock_get.return_value.content = b"PDF content here"
    
    content = signature_service.download_signed_document("sig_req_123")
    
    assert content == b"PDF content here"
    mock_get.assert_called_once()


def test_update_signature_status(signature_service, mock_db):
    """Test signature status update."""
    # Mock signature in database
    mock_signature = Mock(spec=DocumentSignature)
    mock_signature.id = 1
    mock_signature.signature_status = "pending"
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_signature
    
    result = signature_service.update_signature_status(
        signature_id=1,
        status="completed",
        signed_document_url="https://digisigner.com/signed/doc.pdf"
    )
    
    assert result is not None
    assert mock_signature.signature_status == "completed"
    assert mock_signature.signed_document_url == "https://digisigner.com/signed/doc.pdf"
    mock_db.commit.assert_called_once()
