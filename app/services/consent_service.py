"""Consent management service."""

import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import Consent, ConsentHistory

logger = logging.getLogger(__name__)


class ConsentService:
    """Service for managing consent state and history."""

    def __init__(self, db: Session):
        self.db = db

    def get_current_consents(self, user_id: int) -> Dict[str, bool]:
        rows = self.db.query(Consent).filter(Consent.user_id == user_id).all()
        return {row.consent_type: row.granted for row in rows}

    def get_history(self, user_id: int, consent_type: Optional[str] = None) -> list[ConsentHistory]:
        q = self.db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id)
        if consent_type:
            q = q.filter(ConsentHistory.consent_type == consent_type)
        return q.order_by(ConsentHistory.recorded_at.desc()).all()

    def set_consent(
        self,
        user_id: int,
        consent_type: str,
        granted: bool,
        source: Optional[str] = None,
        change_reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Consent:
        consent = (
            self.db.query(Consent)
            .filter(Consent.user_id == user_id, Consent.consent_type == consent_type)
            .first()
        )
        if consent:
            consent.granted = granted
            consent.source = source
            consent.consent_metadata = metadata
            consent.updated_at = datetime.utcnow()
        else:
            consent = Consent(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                source=source,
                consent_metadata=metadata,
            )
            self.db.add(consent)

        history = ConsentHistory(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            source=source,
            change_reason=change_reason,
            consent_metadata=metadata,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(consent)
        return consent

    def set_consents_bulk(
        self,
        user_id: int,
        consents: Dict[str, bool],
        source: Optional[str] = None,
        change_reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Dict[str, bool]:
        for consent_type, granted in consents.items():
            self.set_consent(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                source=source,
                change_reason=change_reason,
                metadata=metadata,
            )
        return self.get_current_consents(user_id)

    def require_consent(self, user_id: int, consent_type: str) -> None:
        consent = (
            self.db.query(Consent)
            .filter(Consent.user_id == user_id, Consent.consent_type == consent_type)
            .first()
        )
        if not consent or not consent.granted:
            raise PermissionError(f"Consent '{consent_type}' is required")
