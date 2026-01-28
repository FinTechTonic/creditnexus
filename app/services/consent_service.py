"""Service for managing GDPR consent records."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import ConsentRecord, DataProcessingRequest, User, AuditAction
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)

class ConsentService:
    """Service for managing GDPR consent records and data processing requests."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def record_consent(
        self,
        user_id: int,
        consent_type: str,
        consent_purpose: str,
        legal_basis: str,
        consent_given: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        consent_source: str = "settings"
    ) -> ConsentRecord:
        """Record user consent for data processing."""
        # Deactivate old consents of the same type
        old_consents = self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.consent_withdrawn == False
        ).all()
        
        for old in old_consents:
            old.consent_withdrawn = True
            old.consent_withdrawn_at = datetime.utcnow()
        
        consent = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            consent_purpose=consent_purpose,
            legal_basis=legal_basis,
            consent_given=consent_given,
            consent_method="explicit",
            consent_source=consent_source,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_given_at=datetime.utcnow() if consent_given else None
        )
        
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        
        log_audit_action(
            self.db,
            AuditAction.UPDATE,
            "consent",
            consent.id,
            user_id,
            metadata={"consent_type": consent_type, "given": consent_given}
        )
        
        return consent

    def get_user_consents(self, user_id: int) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        return self.db.query(ConsentRecord).filter(
            ConsentRecord.user_id == user_id
        ).order_by(ConsentRecord.created_at.desc()).all()

    async def create_processing_request(
        self,
        user_id: int,
        request_type: str,
        description: str,
        requested_changes: Optional[Dict[str, Any]] = None
    ) -> DataProcessingRequest:
        """Create a GDPR data processing request."""
        request = DataProcessingRequest(
            user_id=user_id,
            request_type=request_type,
            request_status="pending",
            request_description=description,
            requested_changes=requested_changes
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        log_audit_action(
            self.db,
            AuditAction.CREATE,
            "data_processing_request",
            request.id,
            user_id,
            metadata={"request_type": request_type}
        )
        
        return request
