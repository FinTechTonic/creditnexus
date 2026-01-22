"""Tests for verification auto-hydration functionality."""

import pytest
import base64
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.verification_hydration_service import VerificationHydrationService
from app.utils.link_payload import LinkPayloadGenerator
from app.db.models import VerificationRequest, Deal, Document, DocumentVersion, VerificationStatus


class TestVerificationHydrationService:
    """Test VerificationHydrationService."""
    
    def test_generate_access_token(self, db_session):
        """Test access token generation."""
        service = VerificationHydrationService(db_session)
        verification_id = "test-verification-123"
        
        token = service.generate_access_token(verification_id)
        
        assert token is not None
        assert len(token) > 0
        
        # Validate token
        is_valid = service.validate_access_token(token, verification_id)
        assert is_valid is True
        
        # Invalid verification ID should fail
        is_valid = service.validate_access_token(token, "wrong-id")
        assert is_valid is False
    
    def test_hydrate_link_payload(self, db_session, sample_deal, sample_documents):
        """Test link payload hydration."""
        # Create verification request
        verification = VerificationRequest(
            verification_id="test-verification-123",
            deal_id=sample_deal.id,
            status=VerificationStatus.PENDING.value,
            expires_at=datetime.utcnow() + timedelta(hours=72),
            created_by=1,
        )
        db_session.add(verification)
        db_session.commit()
        
        service = VerificationHydrationService(db_session)
        
        # Mock file storage to return test file
        with patch.object(service.file_storage, 'get_document_path') as mock_path:
            mock_path.return_value = "/tmp/test_document.pdf"
            
            # Create a test file
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                test_content = b"Test PDF content"
                tmp_file.write(test_content)
                tmp_path = tmp_file.name
            
            mock_path.return_value = tmp_path
            
            try:
                hydrated_payload = service.hydrate_link_payload(
                    verification=verification,
                    include_documents=True,
                    include_extracted_data=True,
                    max_document_size_mb=10,
                )
                
                assert hydrated_payload is not None
                assert hydrated_payload.get("hydrated") is True
                assert hydrated_payload.get("verification_id") == "test-verification-123"
                assert "embedded_documents" in hydrated_payload
                assert "access_token" in hydrated_payload
                assert hydrated_payload.get("version") == "2.1"
                
                # Check embedded documents
                embedded_docs = hydrated_payload.get("embedded_documents", [])
                if embedded_docs:
                    doc = embedded_docs[0]
                    assert doc.get("embedded") is True
                    assert "content" in doc
                    
                    # Verify content can be decoded
                    content_base64 = doc.get("content")
                    content_bytes = base64.b64decode(content_base64)
                    assert content_bytes == test_content
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    def test_dehydrate_link_payload(self, db_session):
        """Test payload dehydration."""
        service = VerificationHydrationService(db_session)
        
        # Create test payload with embedded document
        test_content = b"Test document content"
        content_base64 = base64.b64encode(test_content).decode('utf-8')
        
        payload = {
            "verification_id": "test-123",
            "deal_id": 1,
            "deal_data": {"test": "data"},
            "cdm_payload": {"agreement": {}},
            "embedded_documents": [
                {
                    "document_id": 1,
                    "filename": "test.pdf",
                    "content": content_base64,
                    "content_type": "application/pdf",
                    "size": len(test_content),
                    "embedded": True,
                }
            ],
            "hydrated": True,
            "version": "2.1",
        }
        
        extracted = service.dehydrate_link_payload(payload)
        
        assert extracted is not None
        assert "documents" in extracted
        assert len(extracted["documents"]) == 1
        
        doc = extracted["documents"][0]
        assert doc["content"] == test_content
        assert doc["filename"] == "test.pdf"
        assert doc["document_id"] == 1


class TestLinkPayloadGenerator:
    """Test LinkPayloadGenerator with hydration support."""
    
    def test_generate_hydrated_verification_link(self):
        """Test generating hydrated verification link."""
        generator = LinkPayloadGenerator()
        
        hydrated_payload = {
            "verification_id": "test-123",
            "deal_id": 1,
            "deal_data": {"test": "data"},
            "cdm_payload": {},
            "embedded_documents": [],
            "access_token": "test-token",
            "expires_at": (datetime.utcnow() + timedelta(hours=72)).isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "version": "2.1",
            "hydrated": True,
        }
        
        encrypted_payload = generator.generate_verification_link_payload(
            verification_id="test-123",
            deal_id=1,
            deal_data={},
            cdm_payload={},
            hydrated_payload=hydrated_payload,
        )
        
        assert encrypted_payload is not None
        assert len(encrypted_payload) > 0
        
        # Parse back
        parsed = generator.parse_verification_link_payload(encrypted_payload)
        assert parsed is not None
        assert parsed.get("hydrated") is True
        assert parsed.get("version") == "2.1"
    
    def test_backward_compatibility(self):
        """Test backward compatibility with non-hydrated payloads."""
        generator = LinkPayloadGenerator()
        
        # Generate non-hydrated payload
        encrypted_payload = generator.generate_verification_link_payload(
            verification_id="test-123",
            deal_id=1,
            deal_data={},
            cdm_payload={},
        )
        
        # Parse back
        parsed = generator.parse_verification_link_payload(encrypted_payload)
        assert parsed is not None
        assert parsed.get("hydrated", False) is False
        assert parsed.get("version") == "2.0"


@pytest.fixture
def db_session():
    """Create test database session."""
    from app.db import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_deal(db_session):
    """Create sample deal for testing."""
    deal = Deal(
        deal_id="test-deal-123",
        status="pending",
        deal_type="loan",
        applicant_id=1,
        deal_data={"test": "data"},
    )
    db_session.add(deal)
    db_session.commit()
    db_session.refresh(deal)
    return deal


@pytest.fixture
def sample_documents(db_session, sample_deal):
    """Create sample documents for testing."""
    documents = []
    for i in range(2):
        doc = Document(
            deal_id=sample_deal.id,
            title=f"Test Document {i+1}",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            source_filename=f"test_doc_{i+1}.pdf",
            extracted_data={"test": "data"},
        )
        db_session.add(version)
        db_session.commit()
        
        documents.append(doc)
    
    return documents
