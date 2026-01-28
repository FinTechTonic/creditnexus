"""Internal/native signature service for Phase 2.

This implementation is intentionally conservative:
- Creates internal signature records tied to documents
- Provides completion hooks that can later anchor to blockchain
- Leaves PDF injection and detailed audit trails for follow-up steps
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentSignature, Deal, User
from app.services.notarization_service import NotarizationService
from app.services.messenger.factory import create_messenger, send_signature_request
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SignatureCoordinates:
    """Simple value object for signature placement on a PDF page."""

    page: int
    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


class InternalSignatureService:
    """
    Native internal signature service.

    NOTE: This is a Phase 2 skeleton focusing on:
    - Service wiring and method contracts
    - Safe, non-breaking defaults for unimplemented functionality

    PDF manipulation (PyMuPDF/fitz) and full MetaMask anchoring will be
    implemented in follow‑up steps of the Phase 2 todos.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.notarization_service = NotarizationService(db)

    # ------------------------------------------------------------------
    # High‑level public API
    # ------------------------------------------------------------------
    async def create_signature_request(
        self,
        document_id: int,
        signer_email: str,
        coordinates: SignatureCoordinates,
        expires_in_days: int = 30,
        require_metamask: bool = False,
    ) -> DocumentSignature:
        """
        Create a native signature request for a document.
        """
        document: Optional[Document] = (
            self.db.query(Document).filter(Document.id == document_id).first()
        )
        if not document:
            raise ValueError(f"Document {document_id} not found")

        access_token = f"sig_{document_id}_{int(datetime.utcnow().timestamp())}"

        signature = DocumentSignature(
            document_id=document_id,
            signature_provider="internal",
            signature_status="pending",
            signers=[{"email": signer_email}],
            access_token=access_token,
            coordinates=coordinates.to_dict(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        )

        self.db.add(signature)
        self.db.commit()
        self.db.refresh(signature)

        # Send notification
        try:
            messenger = create_messenger()
            if messenger:
                # Get document title for notification
                doc_title = document.title or f"Document {document_id}"
                
                # Construct signing link (assuming standard frontend URL)
                # In a real app, this base URL would be in settings
                frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5000")
                signing_link = f"{frontend_url}/signers/{access_token}"
                
                await send_signature_request(
                    messenger=messenger,
                    recipient=signer_email,
                    signer_name=signer_email.split('@')[0], # Fallback name
                    document_title=doc_title,
                    signing_link=signing_link,
                    expires_at=signature.expires_at
                )
                logger.info("Sent signature request notification to %s", signer_email)
        except Exception as exc:
            logger.warning("Failed to send signature request notification: %s", exc)

        return signature

    def inject_signature_into_pdf(
        self,
        signature_id: int,
        signature_data_url: str,
    ) -> str:
        """
        Inject a signature image into the document PDF.
        """
        import base64
        import io
        import os
        import tempfile
        import fitz
        from PIL import Image

        signature = self.db.query(DocumentSignature).filter(DocumentSignature.id == signature_id).first()
        if not signature or not signature.document:
            raise ValueError(f"Signature {signature_id} or document not found")

        document = signature.document
        if not document.file_path or not os.path.exists(document.file_path):
            raise ValueError(f"Document file not found at {document.file_path}")

        coords = signature.coordinates or {}
        page_num = coords.get("page", 0)
        x = coords.get("x", 50)
        y = coords.get("y", 50)
        width = coords.get("width", 200)
        height = coords.get("height", 80)

        # 1. Prepare signature image
        try:
            # Data URL format: "data:image/png;base64,..."
            if "," in signature_data_url:
                header, base64_data = signature_data_url.split(",", 1)
            else:
                base64_data = signature_data_url

            img_data = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_data))
            
            # Save to temporary file for PyMuPDF
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                img.save(tmp_img.name)
                tmp_img_path = tmp_img.name
        except Exception as exc:
            logger.error("Failed to process signature image: %s", exc)
            raise ValueError(f"Invalid signature image data: {exc}")

        # 2. Open PDF and inject image
        try:
            pdf_doc = fitz.open(document.file_path)
            if page_num >= len(pdf_doc):
                logger.warning("Page number %s out of range for PDF with %s pages. Using last page.", page_num, len(pdf_doc))
                page_num = len(pdf_doc) - 1
            
            page = pdf_doc[page_num]
            
            # Define rectangle for signature
            rect = fitz.Rect(x, y, x + width, y + height)
            
            # Insert image
            page.insert_image(rect, filename=tmp_img_path)
            
            # 3. Save updated PDF
            # Create a new version of the document or overwrite? 
            # Usually better to create a new file or version.
            # For simplicity in this Phase 2, we'll create a "signed" version in the same folder.
            dir_name = os.path.dirname(document.file_path)
            base_name = os.path.basename(document.file_path)
            signed_filename = f"signed_{base_name}"
            signed_path = os.path.join(dir_name, signed_filename)
            
            pdf_doc.save(signed_path)
            pdf_doc.close()
            
            # Update document metadata to point to signed version
            document.audit_metadata = {
                **(document.audit_metadata or {}),
                "signed_file_path": signed_path,
                "last_signed_at": datetime.utcnow().isoformat(),
            }
            
            # Clean up temp image
            if os.path.exists(tmp_img_path):
                os.remove(tmp_img_path)
                
            return signed_path
            
        except Exception as exc:
            logger.error("Failed to inject signature into PDF: %s", exc)
            if 'tmp_img_path' in locals() and os.path.exists(tmp_img_path):
                os.remove(tmp_img_path)
            raise ValueError(f"PDF injection failed: {exc}")

    def complete_signature(
        self,
        signature_id: int,
        signature_data_url: Optional[str] = None,
        signer_wallet_address: Optional[str] = None,
        use_metamask: bool = False,
    ) -> DocumentSignature:
        """
        Mark an internal signature request as completed and optionally anchor on blockchain.
        """
        signature: Optional[DocumentSignature] = (
            self.db.query(DocumentSignature).filter(DocumentSignature.id == signature_id).first()
        )
        if not signature:
            raise ValueError(f"DocumentSignature {signature_id} not found")

        signature.signature_status = "completed"
        signature.completed_at = datetime.utcnow()

        if signature_data_url:
            # Save signature data URL to audit_data for now
            # In a real app, we might store the image file separately
            signature.audit_data = {
                **(signature.audit_data or {}),
                "signature_data_url": signature_data_url,
            }

            # Attempt to inject signature into PDF
            try:
                self.inject_signature_into_pdf(signature.id, signature_data_url)
            except Exception as exc:
                logger.error("Failed to inject signature into PDF: %s", exc, exc_info=True)

        self.db.commit()
        self.db.refresh(signature)

        # MetaMask anchoring & deal-level notarization
        if use_metamask and signer_wallet_address and signature.document and signature.document.deal_id:
            try:
                deal: Optional[Deal] = (
                    self.db.query(Deal).filter(Deal.id == signature.document.deal_id).first()
                )
                if deal:
                    # Create or update a notarization request for this deal, using the MetaMask wallet
                    notarization = self.notarization_service.create_notarization_request(
                        deal_id=deal.id,
                        required_signers=[signer_wallet_address],
                    )
                    # Persist a link from the signature record to the notarization for auditability
                    signature.audit_data = {
                        **(signature.audit_data or {}),
                        "notarization_id": notarization.id,
                        "notarization_status": notarization.status,
                    }
                    self.db.commit()
                    self.db.refresh(signature)
                    logger.info(
                        "Anchored internal signature %s to notarization %s for deal %s using MetaMask wallet %s",
                        signature.id,
                        notarization.id,
                        deal.id,
                        signer_wallet_address,
                    )
            except Exception as exc:
                logger.warning("Failed to anchor internal signature on blockchain: %s", exc, exc_info=True)

        return signature

