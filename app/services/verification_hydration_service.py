"""Verification hydration service for auto-hydrating verification links with documents and data."""

import logging
import secrets
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import VerificationRequest, Deal, Document, DocumentVersion
from app.services.file_storage_service import FileStorageService
from app.utils.link_payload import LinkPayloadGenerator

logger = logging.getLogger(__name__)


class VerificationHydrationService:
    """Service for hydrating verification links with embedded documents and data."""
    
    def __init__(self, db: Session):
        """Initialize hydration service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.file_storage = FileStorageService()
        self.payload_generator = LinkPayloadGenerator()
    
    def generate_access_token(self, verification_id: str) -> str:
        """Generate access token for verification link validation.
        
        Args:
            verification_id: Verification ID
            
        Returns:
            Access token string
        """
        # Generate a secure token tied to verification ID
        token_data = {
            "verification_id": verification_id,
            "created_at": datetime.utcnow().isoformat(),
            "nonce": secrets.token_urlsafe(16),
        }
        
        # Encode token data
        token_json = json.dumps(token_data, sort_keys=True)
        token_bytes = token_json.encode('utf-8')
        token = base64.urlsafe_b64encode(token_bytes).decode('utf-8').rstrip('=')
        
        return token
    
    def validate_access_token(self, token: str, verification_id: str) -> bool:
        """Validate access token for verification link.
        
        Args:
            token: Access token
            verification_id: Verification ID to validate against
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Add padding if needed
            padding = 4 - len(token) % 4
            if padding != 4:
                token += "=" * padding
            
            # Decode token
            token_bytes = base64.urlsafe_b64decode(token)
            token_data = json.loads(token_bytes.decode('utf-8'))
            
            # Validate verification ID matches
            if token_data.get("verification_id") != verification_id:
                return False
            
            # Token is valid (could add expiration check here if needed)
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate access token: {e}")
            return False
    
    def hydrate_link_payload(
        self,
        verification: VerificationRequest,
        include_documents: bool = True,
        include_extracted_data: bool = True,
        max_document_size_mb: int = 10,
    ) -> Dict[str, Any]:
        """Hydrate verification link payload with embedded documents and data.
        
        Args:
            verification: VerificationRequest object
            include_documents: Whether to embed document content
            include_extracted_data: Whether to include full extracted data
            max_document_size_mb: Maximum document size to embed (in MB)
            
        Returns:
            Hydrated payload dictionary ready for encryption
        """
        deal_id = verification.deal_id
        deal_data = {}
        cdm_payload = {}
        embedded_documents = []
        
        # Get deal data
        if deal_id:
            deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                deal_data = {
                    "deal_id": deal.deal_id,
                    "status": deal.status,
                    "deal_type": deal.deal_type,
                    "deal_data": deal.deal_data or {},
                    "applicant_id": deal.applicant_id,
                }
                
                # Get CDM payload from documents
                if include_extracted_data:
                    documents = self.db.query(Document).filter(Document.deal_id == deal_id).all()
                    
                    for doc in documents:
                        # Try source_cdm_data first
                        if doc.source_cdm_data:
                            cdm_payload = doc.source_cdm_data
                            break
                        else:
                            # Check latest version for extracted data
                            latest_version = (
                                self.db.query(DocumentVersion)
                                .filter(DocumentVersion.document_id == doc.id)
                                .order_by(DocumentVersion.version_number.desc())
                                .first()
                            )
                            if latest_version and latest_version.extracted_data:
                                extracted = latest_version.extracted_data
                                if isinstance(extracted, dict) and "agreement" in extracted:
                                    cdm_payload = extracted
                                    break
                
                # Embed documents if requested
                if include_documents:
                    documents = self.db.query(Document).filter(Document.deal_id == deal_id).all()
                    
                    for doc in documents:
                        latest_version = (
                            self.db.query(DocumentVersion)
                            .filter(DocumentVersion.document_id == doc.id)
                            .order_by(DocumentVersion.version_number.desc())
                            .first()
                        )
                        
                        if not latest_version or not latest_version.source_filename:
                            continue
                        
                        try:
                            # Get document file path
                            file_path = self.file_storage.get_document_path(
                                user_id=deal.applicant_id,
                                deal_id=deal.deal_id,
                                document_id=doc.id
                            )
                            
                            if not file_path:
                                logger.warning(f"Document file not found for document {doc.id}")
                                continue
                            
                            # Read file content
                            from pathlib import Path
                            file_path_obj = Path(file_path)
                            
                            if not file_path_obj.exists():
                                logger.warning(f"File path does not exist: {file_path}")
                                continue
                            
                            # Check file size
                            file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
                            if file_size_mb > max_document_size_mb:
                                logger.warning(
                                    f"Document {doc.id} too large ({file_size_mb:.2f}MB), "
                                    f"skipping (max: {max_document_size_mb}MB)"
                                )
                                # Include reference instead
                                embedded_documents.append({
                                    "document_id": doc.id,
                                    "filename": latest_version.source_filename,
                                    "size": int(file_path_obj.stat().st_size),
                                    "embedded": False,
                                    "reason": "file_too_large",
                                })
                                continue
                            
                            # Read and encode file
                            file_content = file_path_obj.read_bytes()
                            
                            # Decrypt if encrypted
                            if file_path.endswith('.encrypted'):
                                from app.services.encryption_service import get_encryption_service
                                encryption_service = get_encryption_service()
                                file_content = encryption_service.decrypt(file_content)
                            
                            # Base64 encode
                            file_base64 = base64.b64encode(file_content).decode('utf-8')
                            
                            embedded_documents.append({
                                "document_id": doc.id,
                                "filename": latest_version.source_filename,
                                "content": file_base64,
                                "content_type": latest_version.source_filename.split('.')[-1] if '.' in latest_version.source_filename else "application/octet-stream",
                                "size": len(file_content),
                                "embedded": True,
                            })
                            
                        except Exception as e:
                            logger.error(f"Failed to embed document {doc.id}: {e}")
                            # Include reference instead
                            embedded_documents.append({
                                "document_id": doc.id,
                                "filename": latest_version.source_filename if latest_version else doc.title,
                                "embedded": False,
                                "reason": str(e),
                            })
        
        # Generate access token
        access_token = self.generate_access_token(verification.verification_id)
        
        # Calculate expiration
        expires_in_hours = 72  # Default
        if verification.expires_at:
            time_remaining = verification.expires_at - datetime.utcnow()
            if time_remaining.total_seconds() > 0:
                expires_in_hours = int(time_remaining.total_seconds() / 3600)
        
        # Build hydrated payload
        hydrated_payload = {
            "verification_id": verification.verification_id,
            "deal_id": deal_id or 0,
            "deal_data": deal_data,
            "cdm_payload": cdm_payload,
            "embedded_documents": embedded_documents,
            "access_token": access_token,
            "expires_at": verification.expires_at.isoformat() if verification.expires_at else None,
            "created_at": datetime.utcnow().isoformat(),
            "version": "2.1",  # Version 2.1 for hydrated payloads
            "hydrated": True,
        }
        
        logger.info(
            f"Hydrated verification link for {verification.verification_id}: "
            f"{len(embedded_documents)} documents embedded"
        )
        
        return hydrated_payload
    
    def dehydrate_link_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract embedded documents and data from hydrated payload.
        
        Args:
            payload: Parsed payload dictionary
            
        Returns:
            Dictionary with extracted documents and data
        """
        embedded_documents = payload.get("embedded_documents", [])
        extracted_documents = []
        
        for doc in embedded_documents:
            if doc.get("embedded"):
                # Decode base64 content
                try:
                    content_base64 = doc.get("content", "")
                    content_bytes = base64.b64decode(content_base64)
                    
                    extracted_documents.append({
                        "document_id": doc.get("document_id"),
                        "filename": doc.get("filename"),
                        "content": content_bytes,
                        "content_type": doc.get("content_type", "application/octet-stream"),
                        "size": doc.get("size", len(content_bytes)),
                    })
                except Exception as e:
                    logger.error(f"Failed to extract embedded document: {e}")
        
        return {
            "documents": extracted_documents,
            "deal_data": payload.get("deal_data", {}),
            "cdm_payload": payload.get("cdm_payload", {}),
            "access_token": payload.get("access_token"),
        }
