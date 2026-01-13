"""
Signature Status Verification Agent.

This agent verifies signature status by:
1. Checking signature request status with DigiSigner API
2. Validating signer completion
3. Monitoring signature expiration
4. Downloading signed documents when complete
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import DocumentSignature
from app.services.signature_service import SignatureService

logger = logging.getLogger(__name__)


class SignatureVerifier:
    """Agent for verifying signature status."""

    def __init__(self, db: Session):
        """
        Initialize signature verifier.

        Args:
            db: Database session
        """
        self.db = db
        self.signature_service = SignatureService(db)

    def verify_signature_status(
        self,
        signature_id: int
    ) -> Dict[str, Any]:
        """
        Verify signature status by checking with DigiSigner API.

        Args:
            signature_id: DocumentSignature ID to verify

        Returns:
            Verification result with updated status
        """
        signature = self.db.query(DocumentSignature).filter(
            DocumentSignature.id == signature_id
        ).first()

        if not signature:
            return {
                "status": "error",
                "message": f"Signature {signature_id} not found"
            }

        try:
            # Check status with DigiSigner API
            provider_status = self.signature_service.check_signature_status(
                signature.signature_request_id
            )

            # Update local status if changed
            new_status = provider_status.get("status", signature.signature_status)
            if new_status != signature.signature_status:
                self.signature_service.update_signature_status(
                    signature_id=signature_id,
                    status=new_status,
                    signed_document_url=provider_status.get("signed_document_url")
                )
                signature = self.db.query(DocumentSignature).filter(
                    DocumentSignature.id == signature_id
                ).first()

            # Check if all signers have signed
            all_signed = all(
                signer.get("signed_at") for signer in (signature.signers or [])
            )

            # Check expiration
            is_expired = False
            if signature.expires_at:
                is_expired = datetime.utcnow() > signature.expires_at

            return {
                "status": "success",
                "signature_id": signature_id,
                "signature_status": signature.signature_status,
                "provider_status": provider_status,
                "all_signed": all_signed,
                "is_expired": is_expired,
                "signers_count": len(signature.signers or []),
                "signed_count": sum(
                    1 for signer in (signature.signers or [])
                    if signer.get("signed_at")
                ),
                "verified_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error verifying signature {signature_id}: {e}")
            return {
                "status": "error",
                "signature_id": signature_id,
                "message": str(e)
            }

    def verify_document_signatures(
        self,
        document_id: int
    ) -> Dict[str, Any]:
        """
        Verify all signatures for a document.

        Args:
            document_id: Document ID to verify

        Returns:
            Verification result for all signatures
        """
        signatures = self.db.query(DocumentSignature).filter(
            DocumentSignature.document_id == document_id
        ).all()

        if not signatures:
            return {
                "status": "success",
                "document_id": document_id,
                "signatures_count": 0,
                "message": "No signatures found for this document"
            }

        results = []
        for signature in signatures:
            result = self.verify_signature_status(signature.id)
            results.append(result)

        # Aggregate results
        completed = sum(1 for r in results if r.get("signature_status") == "completed")
        pending = sum(1 for r in results if r.get("signature_status") == "pending")
        expired = sum(1 for r in results if r.get("is_expired", False))

        overall_status = "completed" if completed == len(signatures) else "pending"

        return {
            "status": "success",
            "document_id": document_id,
            "overall_status": overall_status,
            "signatures_count": len(signatures),
            "completed_count": completed,
            "pending_count": pending,
            "expired_count": expired,
            "signature_results": results
        }

    def verify_expired_signatures(
        self,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        Find and verify signatures expiring soon.

        Args:
            hours_ahead: Number of hours ahead to check

        Returns:
            List of signatures expiring soon
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() + timedelta(hours=hours_ahead)

        expiring_signatures = self.db.query(DocumentSignature).filter(
            DocumentSignature.signature_status == "pending",
            DocumentSignature.expires_at <= cutoff_time,
            DocumentSignature.expires_at > datetime.utcnow()
        ).all()

        results = []
        for signature in expiring_signatures:
            result = self.verify_signature_status(signature.id)
            results.append({
                "signature_id": signature.id,
                "document_id": signature.document_id,
                "expires_at": signature.expires_at.isoformat() if signature.expires_at else None,
                "status": result.get("signature_status"),
                "all_signed": result.get("all_signed", False)
            })

        return {
            "status": "success",
            "expiring_count": len(expiring_signatures),
            "expiring_signatures": results
        }
