"""Enhanced verification service with file reference support."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import VerificationRequest, Deal, User, VerificationStatus, VerificationAuditLog
from app.utils.link_payload import LinkPayloadGenerator
from app.core.verification_file_config import VerificationFileConfig

logger = logging.getLogger(__name__)


class VerificationService:
    """Enhanced service for managing verification requests with file references."""

    def __init__(self, db: Session):
        """Initialize verification service.

        Args:
            db: Database session
        """
        self.db = db

    def create_verification_request(
        self,
        deal_id: Optional[int] = None,
        verifier_user_id: Optional[int] = None,
        created_by: int = None,
        expires_in_hours: int = 72,
        verification_metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationRequest:
        """Create a new verification request.

        Args:
            deal_id: Optional deal ID to verify
            verifier_user_id: Optional user ID of verifier
            created_by: User ID creating request
            expires_in_hours: Custom expiration time (uses default if None)
            verification_metadata: Additional metadata

        Returns:
            Created VerificationRequest
        """
        # Generate token and verification ID
        verification_id = str(secrets.token_urlsafe(16))

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        verification = VerificationRequest(
            verification_id=verification_id,
            deal_id=deal_id,
            verifier_user_id=verifier_user_id,
            verification_link_token=verification_id,  # Using ID as token (will be encrypted)
            status=VerificationStatus.PENDING.value,
            expires_at=expires_at,
            verification_metadata=verification_metadata or {},
            created_by=created_by,
        )

        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)

        # Update deal if specified
        if deal_id:
            deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                deal.verification_required = True
                self.db.commit()

        logger.info(f"Created verification request: {verification_id} for deal {deal_id}")

        return verification

    def generate_verification_link(
        self,
        verification: VerificationRequest,
        base_url: Optional[str] = None,
        include_files: bool = True,
        file_categories: Optional[List[str]] = None,
        file_document_ids: Optional[List[int]] = None,
    ) -> str:
        """Generate self-contained verification link with file references.

        Args:
            verification: VerificationRequest object
            base_url: Optional base URL for links
            include_files: Whether to include file references
            file_categories: File categories to include
            file_document_ids: Specific document IDs to include

        Returns:
            Full verification URL
        """
        from app.core.config import settings

        if not base_url:
            base_url = getattr(settings, "VERIFICATION_BASE_URL", None)
            if not base_url:
                raise ValueError(
                    "VERIFICATION_BASE_URL must be set in configuration. "
                    "Please set VERIFICATION_BASE_URL environment variable."
                )

        # Build file references
        file_references = []
        if include_files:
            file_config = VerificationFileConfig()
            enabled_subdirs = file_config.get_enabled_subdirectories()

            for subdir in enabled_subdirs:
                if subdir == "documents":
                    # Get deal documents from database
                    if verification.deal_id:
                        from app.db.models import Document, DocumentVersion
                        from app.services.file_storage_service import FileStorageService
                        
                        # Get deal
                        deal = self.db.query(Deal).filter(Deal.id == verification.deal_id).first()
                        if not deal:
                            logger.warning(f"Deal {verification.deal_id} not found for verification {verification.verification_id}")
                        else:
                            # Get documents associated with deal
                            documents_query = self.db.query(Document).filter(Document.deal_id == verification.deal_id)
                            
                            # Filter by document IDs if specified
                            if file_document_ids:
                                documents_query = documents_query.filter(Document.id.in_(file_document_ids))
                            
                            documents = documents_query.all()
                            
                            for doc in documents:
                                # Get latest version
                                latest_version = (
                                    self.db.query(DocumentVersion)
                                    .filter(DocumentVersion.document_id == doc.id)
                                    .order_by(DocumentVersion.version_number.desc())
                                    .first()
                                )
                                
                                if latest_version:
                                    # Determine category and subdirectory
                                    category = "legal"  # Default category
                                    
                                    # Filter by categories if specified
                                    if file_categories and category not in file_categories:
                                        continue
                                    
                                    # Get file size from version or filesystem
                                    file_size = 0
                                    if latest_version.source_filename:
                                        try:
                                            file_storage = FileStorageService()
                                            deal_docs = file_storage.get_deal_documents(
                                                user_id=deal.applicant_id,
                                                deal_id=deal.deal_id,
                                                subdirectory=subdir
                                            )
                                            # Find matching file
                                            for stored_file in deal_docs:
                                                if str(doc.id) in stored_file.get("filename", ""):
                                                    file_size = stored_file.get("size", 0)
                                                    break
                                        except Exception as e:
                                            logger.warning(f"Failed to get file size for document {doc.id}: {e}")
                                    
                                    file_references.append({
                                        "document_id": doc.id,
                                        "filename": latest_version.source_filename or doc.title,
                                        "category": category,
                                        "subdirectory": subdir,
                                        "size": file_size,
                                        "download_url": f"/api/deals/{verification.deal_id}/documents/{doc.id}/download",
                                    })

        # Get deal data and CDM payload
        deal_data = {}
        cdm_payload = {}
        
        if verification.deal_id:
            deal = self.db.query(Deal).filter(Deal.id == verification.deal_id).first()
            if deal:
                # Get deal data
                deal_data = {
                    "deal_id": deal.deal_id,
                    "status": deal.status,
                    "deal_type": deal.deal_type,
                    "deal_data": deal.deal_data or {},
                    "applicant_id": deal.applicant_id,
                }
                
                # Get CDM payload from deal documents
                # Look for CDM data in document source_cdm_data or extracted_data
                from app.db.models import Document, DocumentVersion
                documents = self.db.query(Document).filter(Document.deal_id == verification.deal_id).all()
                
                for doc in documents:
                    if doc.source_cdm_data:
                        cdm_payload = doc.source_cdm_data
                        break
                    else:
                        # Check latest version for extracted CDM data
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
        
        # Calculate expiration hours from verification.expires_at
        expires_in_hours = 72  # Default
        if verification.expires_at:
            time_remaining = verification.expires_at - datetime.utcnow()
            if time_remaining.total_seconds() > 0:
                expires_in_hours = int(time_remaining.total_seconds() / 3600)
        
        # Generate encrypted link payload
        payload_generator = LinkPayloadGenerator()
        encrypted_payload = payload_generator.generate_verification_link_payload(
            verification_id=verification.verification_id,
            deal_id=verification.deal_id or 0,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            file_references=file_references if file_references else None,
            expires_in_hours=expires_in_hours,
        )

        # Construct full URL
        link = f"{base_url.rstrip('/')}/verify/{encrypted_payload}"

        logger.info(f"Generated verification link for {verification.verification_id}")
        return link

    def accept_verification(
        self, verification_id: str, verifier_user_id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> VerificationRequest:
        """Accept a verification request.

        Args:
            verification_id: Verification ID
            verifier_user_id: User ID of verifier
            metadata: Optional acceptance metadata

        Returns:
            Updated VerificationRequest

        Raises:
            ValueError: If verification not found or not in pending status
        """
        verification = self.get_verification_by_id(verification_id)

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        if verification.status != VerificationStatus.PENDING.value:
            raise ValueError(
                f"Verification must be pending to accept (current: {verification.status})"
            )

        # Check expiration
        if datetime.utcnow() > verification.expires_at:
            verification.status = VerificationStatus.EXPIRED.value
            self.db.commit()
            raise ValueError("Verification has expired")

        # Update verification
        verification.status = VerificationStatus.ACCEPTED.value
        verification.accepted_at = datetime.utcnow()
        verification.verifier_user_id = verifier_user_id

        if metadata:
            if not verification.verification_metadata:
                verification.verification_metadata = {}
            verification.verification_metadata.update(metadata)

        self.db.commit()
        self.db.refresh(verification)

        # Update deal
        if verification.deal_id:
            deal = self.db.query(Deal).filter(Deal.id == verification.deal_id).first()
            if deal:
                deal.verification_completed_at = datetime.utcnow()
                self.db.commit()

        # Log audit entry
        self._log_audit(verification.id, "accepted", verifier_user_id)

        logger.info(f"Verification {verification_id} accepted by user {verifier_user_id}")

        return verification

    def decline_verification(
        self, verification_id: str, verifier_user_id: int, reason: str
    ) -> VerificationRequest:
        """Decline a verification request.

        Args:
            verification_id: Verification ID
            verifier_user_id: User ID of verifier
            reason: Decline reason

        Returns:
            Updated VerificationRequest

        Raises:
            ValueError: If verification not found or not in pending status
        """
        verification = self.get_verification_by_id(verification_id)

        if not verification:
            raise ValueError(f"Verification {verification_id} not found")

        if verification.status != VerificationStatus.PENDING.value:
            raise ValueError(
                f"Verification must be pending to decline (current: {verification.status})"
            )

        # Update verification
        verification.status = VerificationStatus.DECLINED.value
        verification.declined_at = datetime.utcnow()
        verification.declined_reason = reason

        self.db.commit()
        self.db.refresh(verification)

        # Log audit entry
        self._log_audit(verification.id, "declined", verifier_user_id, {"reason": reason})

        logger.info(f"Verification {verification_id} declined by user {verifier_user_id}: {reason}")

        return verification

    def expire_pending_verifications(self) -> int:
        """Mark expired pending verifications.

        Returns:
            Number of verifications expired
        """
        expired_count = 0

        pending_verifications = (
            self.db.query(VerificationRequest)
            .filter(
                VerificationRequest.status == VerificationStatus.PENDING.value,
                VerificationRequest.expires_at < datetime.utcnow(),
            )
            .all()
        )

        for verification in pending_verifications:
            verification.status = VerificationStatus.EXPIRED.value
            expired_count += 1

        self.db.commit()

        if expired_count > 0:
            logger.info(f"Expired {expired_count} pending verifications")

        return expired_count

    def list_verifications(
        self,
        deal_id: Optional[int] = None,
        verifier_user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[VerificationRequest]:
        """List verification requests with filters.

        Args:
            deal_id: Filter by deal ID
            verifier_user_id: Filter by verifier user ID
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of VerificationRequest instances
        """
        query = self.db.query(VerificationRequest)

        if deal_id:
            query = query.filter(VerificationRequest.deal_id == deal_id)

        if verifier_user_id:
            query = query.filter(VerificationRequest.verifier_user_id == verifier_user_id)

        if status:
            query = query.filter(VerificationRequest.status == status)

        return (
            query.order_by(VerificationRequest.created_at.desc()).limit(limit).offset(offset).all()
        )

    def get_verification_by_id(self, verification_id: str) -> Optional[VerificationRequest]:
        """Get verification request by ID.

        Args:
            verification_id: Verification ID

        Returns:
            VerificationRequest or None
        """
        return (
            self.db.query(VerificationRequest)
            .filter(VerificationRequest.verification_id == verification_id)
            .first()
        )

    def get_verification_stats(self, deal_id: Optional[int] = None) -> Dict[str, int]:
        """Get verification statistics.

        Args:
            deal_id: Optional deal ID filter

        Returns:
            Dictionary with counts by status
        """
        query = self.db.query(VerificationRequest)

        if deal_id:
            query = query.filter(VerificationRequest.deal_id == deal_id)

        total = query.count()
        pending = query.filter(
            VerificationRequest.status == VerificationStatus.PENDING.value
        ).count()
        accepted = query.filter(
            VerificationRequest.status == VerificationStatus.ACCEPTED.value
        ).count()
        declined = query.filter(
            VerificationRequest.status == VerificationStatus.DECLINED.value
        ).count()
        expired = query.filter(
            VerificationRequest.status == VerificationStatus.EXPIRED.value
        ).count()

        return {
            "total": total,
            "pending": pending,
            "accepted": accepted,
            "declined": declined,
            "expired": expired,
        }

    def _log_audit(
        self,
        verification_db_id: int,
        action: str,
        actor_user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log verification audit entry.

        Args:
            verification_db_id: Database ID of verification
            action: Action performed
            actor_user_id: User ID performing action
            metadata: Additional metadata
        """
        audit_log = VerificationAuditLog(
            verification_id=verification_db_id,
            action=action,
            actor_user_id=actor_user_id,
            metadata=metadata or {},
        )

        self.db.add(audit_log)
        self.db.commit()
