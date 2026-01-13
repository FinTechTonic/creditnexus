"""
Digital Signature Service for CreditNexus.

Integrates with DigiSigner API for document signing workflows.
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.models import Document, DocumentSignature, GeneratedDocument, DocumentVersion
from app.core.config import settings
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)


class SignatureService:
    """Service for managing digital signatures via DigiSigner API."""

    def __init__(self, db: Session):
        """
        Initialize signature service.

        Args:
            db: Database session
        """
        self.db = db
        self.api_key = settings.DIGISIGNER_API_KEY
        self.base_url = settings.DIGISIGNER_BASE_URL
        self.file_storage = FileStorageService()

        if not self.api_key:
            logger.warning("DigiSigner API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        api_key_value = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else str(self.api_key)
        return {
            "X-DigiSigner-API-Key": api_key_value,
            "Content-Type": "application/json"
        }

    def _handle_api_error(self, response: requests.Response) -> None:
        """Handle API error responses."""
        if not response.ok:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                logger.error(f"DigiSigner API error: {error_msg}")
                raise ValueError(f"DigiSigner API error: {error_msg}")
            except ValueError:
                raise
            except Exception:
                raise ValueError(f"DigiSigner API error: {response.status_code} - {response.text}")

    def _get_document_path(self, document: Document) -> Optional[str]:
        """Get document file path."""
        # Try to get from document version
        if document.current_version_id:
            version = self.db.query(DocumentVersion).filter(
                DocumentVersion.id == document.current_version_id
            ).first()
            if version and version.file_path:
                return version.file_path

        # Try to get from file storage
        if document.deal_id:
            from app.db.models import Deal
            deal = self.db.query(Deal).filter(Deal.id == document.deal_id).first()
            if deal:
                return self.file_storage.get_document_path(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id,
                    document_id=document.id
                )

        return None

    def _upload_document_to_digisigner(self, document_path: str) -> str:
        """Upload document to DigiSigner and return document ID."""
        api_key_value = self.api_key.get_secret_value() if hasattr(self.api_key, 'get_secret_value') else str(self.api_key)
        
        with open(document_path, 'rb') as f:
            files = {'file': (Path(document_path).name, f, 'application/pdf')}
            headers = {"X-DigiSigner-API-Key": api_key_value}
            response = requests.post(
                f"{self.base_url}/documents",
                headers=headers,
                files=files,
                timeout=60
            )

        self._handle_api_error(response)
        response_data = response.json()
        return response_data.get("document_id") or response_data.get("id")

    def request_signature(
        self,
        document_id: int,
        signers: Optional[List[Dict[str, str]]] = None,
        auto_detect_signers: bool = True,
        signature_provider: str = "digisigner",
        expires_in_days: int = 30,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        urgency: str = "standard"
    ) -> DocumentSignature:
        """
        Request signatures for a document via DigiSigner API.

        Args:
            document_id: Document ID to sign
            signers: List of signers [{"name": "...", "email": "...", "role": "..."}]
                     If None and auto_detect_signers=True, uses AI to detect signers
            auto_detect_signers: Use AI to automatically detect signers from CDM data
            signature_provider: Signature provider (default: "digisigner")
            expires_in_days: Days until signature request expires
            subject: Email subject (optional)
            message: Email message (optional)
            urgency: Urgency level for AI signer detection ("standard", "time_sensitive", "complex")

        Returns:
            DocumentSignature instance
        """
        # 1. Load document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 2. Use AI chain to detect signers if not provided
        if auto_detect_signers and not signers:
            from app.models.cdm import CreditAgreement
            from app.chains.signature_request_chain import generate_signature_request

            if document.source_cdm_data:
                credit_agreement = CreditAgreement(**document.source_cdm_data)
                signature_config = generate_signature_request(
                    credit_agreement=credit_agreement,
                    document_type="facility_agreement",
                    urgency=urgency
                )

                signers = [
                    {
                        "name": signer.name,
                        "email": signer.email,
                        "role": signer.role
                    }
                    for signer in signature_config.signers
                ]

                expires_in_days = signature_config.expiration_days
                message = signature_config.message or message

        if not signers:
            raise ValueError("No signers provided and auto-detection failed")

        # 3. Get document file path
        document_path = self._get_document_path(document)
        if not document_path or not Path(document_path).exists():
            raise ValueError(f"Document file not found: {document_path}")

        # 4. Upload document to DigiSigner
        digisigner_document_id = self._upload_document_to_digisigner(document_path)

        # 5. Create signature request via DigiSigner API
        request_payload = {
            "document_id": digisigner_document_id,
            "signers": [
                {
                    "email": signer["email"],
                    "name": signer["name"],
                    "role": signer.get("role", "Signer"),
                    "signing_order": idx + 1 if len(signers) > 1 else None
                }
                for idx, signer in enumerate(signers)
            ],
            "subject": subject or "Please sign the document",
            "message": message or "Please review and sign the attached document",
            "expires_in_days": expires_in_days
        }

        response = requests.post(
            f"{self.base_url}/documents/{digisigner_document_id}/send",
            headers=self._get_headers(),
            json=request_payload,
            timeout=30
        )

        self._handle_api_error(response)
        response_data = response.json()

        # 6. Create DocumentSignature record
        signature = DocumentSignature(
            document_id=document_id,
            signature_provider=signature_provider,
            signature_request_id=response_data.get("signature_request_id") or response_data.get("id"),
            signature_status="pending",
            signers=signers,
            signature_provider_data=response_data,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )

        self.db.add(signature)
        self.db.commit()
        self.db.refresh(signature)

        logger.info(f"Created DigiSigner signature request {signature.signature_request_id} for document {document_id}")
        return signature

    def check_signature_status(self, signature_request_id: str) -> Dict[str, Any]:
        """
        Check status of signature request via DigiSigner API.

        Args:
            signature_request_id: DigiSigner signature request ID

        Returns:
            Status information from DigiSigner
        """
        response = requests.get(
            f"{self.base_url}/documents/{signature_request_id}",
            headers=self._get_headers(),
            timeout=30
        )

        self._handle_api_error(response)
        return response.json()

    def download_signed_document(
        self,
        signature_request_id: str,
        save_path: Optional[Path] = None
    ) -> bytes:
        """
        Download signed document from DigiSigner.

        Args:
            signature_request_id: DigiSigner signature request ID
            save_path: Optional path to save the document

        Returns:
            Document content as bytes
        """
        response = requests.get(
            f"{self.base_url}/documents/{signature_request_id}/download",
            headers=self._get_headers(),
            timeout=60  # Longer timeout for file downloads
        )

        self._handle_api_error(response)
        content = response.content

        if save_path:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(content)

        return content

    def update_signature_status(
        self,
        signature_id: int,
        status: str,
        signed_document_url: Optional[str] = None,
        signed_document_path: Optional[str] = None
    ) -> DocumentSignature:
        """
        Update signature status in database.

        Args:
            signature_id: DocumentSignature ID
            status: New status ("pending", "completed", "declined", "expired")
            signed_document_url: URL to signed document (if completed)
            signed_document_path: Local path to signed document (if downloaded)

        Returns:
            Updated DocumentSignature instance
        """
        signature = self.db.query(DocumentSignature).filter(
            DocumentSignature.id == signature_id
        ).first()

        if not signature:
            raise ValueError(f"Signature {signature_id} not found")

        signature.signature_status = status
        if signed_document_url:
            signature.signed_document_url = signed_document_url
        if signed_document_path:
            signature.signed_document_path = signed_document_path
        if status == "completed":
            signature.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(signature)

        logger.info(f"Updated signature {signature_id} status to {status}")
        return signature
