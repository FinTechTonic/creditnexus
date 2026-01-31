"""
Lender scores (Week 16). Users never see their own scores; only lenders can view borrower scores.
- get_lender_score: internal use (fetch score for a user).
- store_lender_score: store/update score (from Plaid or internal).
- get_score_for_lender: return borrower score only if caller is an allowed lender.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import LenderScore, User

logger = logging.getLogger(__name__)


class LenderScoresServiceError(Exception):
    """Raised when lender score operations fail."""

    pass


def _is_lender(user: User) -> bool:
    """True if user is allowed to view borrower lender scores (admin or banker)."""
    if not user or not user.role:
        return False
    return user.role in (UserRole.ADMIN.value, UserRole.BANKER.value)


def get_lender_score(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get lender score for a user (internal use only; do not expose to the subject user).
    """
    row = db.query(LenderScore).filter(LenderScore.user_id == user_id).first()
    return row.to_dict() if row else None


def store_lender_score(
    db: Session,
    user_id: int,
    score_value: Optional[Decimal] = None,
    source: Optional[str] = None,
) -> LenderScore:
    """Store or update lender score for a user (from Plaid or internal)."""
    row = db.query(LenderScore).filter(LenderScore.user_id == user_id).first()
    if row:
        if score_value is not None:
            row.score_value = score_value
        if source is not None:
            row.source = source
        db.commit()
        db.refresh(row)
        return row
    row = LenderScore(
        user_id=user_id,
        score_value=score_value,
        source=source or "internal",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_score_for_lender(
    db: Session,
    borrower_user_id: int,
    lender_user_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Get borrower's lender score only if the caller (lender_user_id) is allowed.
    Privacy: borrower_user_id must not equal lender_user_id (users never see own).
    """
    if borrower_user_id == lender_user_id:
        return None
    lender = db.query(User).filter(User.id == lender_user_id).first()
    if not lender or not _is_lender(lender):
        return None
    return get_lender_score(db, borrower_user_id)
