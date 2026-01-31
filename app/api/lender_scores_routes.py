"""Lender scores API (Week 16). Users never see their own; only lenders (admin/banker) can view borrower scores."""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.lender_scores_service import (
    get_score_for_lender,
    store_lender_score,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lender-scores", tags=["lender-scores"])


class LenderScoreUpdateRequest(BaseModel):
    """Request to update a user's lender score (admin or internal)."""

    user_id: int = Field(..., description="User (borrower) ID")
    score_value: Optional[Decimal] = Field(None)
    source: Optional[str] = Field(None, max_length=100)


@router.get("/{user_id}", response_model=Dict[str, Any])
def get_borrower_score(
    user_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get lender score for a borrower. Lender only (admin or banker).
    Privacy: returns 404 if requester is the same user (users never see their own score).
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    score = get_score_for_lender(db, borrower_user_id=user_id, lender_user_id=current_user.id)
    if score is None:
        raise HTTPException(status_code=404, detail="Not found")
    return score


@router.post("/update", response_model=Dict[str, Any])
def update_lender_score(
    body: LenderScoreUpdateRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Update a user's lender score (admin or banker only; e.g. from Plaid or internal job).
    """
    if current_user.role not in ("admin", "banker"):
        raise HTTPException(status_code=403, detail="Forbidden")
    row = store_lender_score(
        db,
        user_id=body.user_id,
        score_value=body.score_value,
        source=body.source,
    )
    return row.to_dict()
