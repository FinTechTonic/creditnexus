"""Consent management API routes."""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.consent_service import ConsentService


consent_router = APIRouter(prefix="/consent", tags=["Consent"])

ALLOWED_CONSENT_TYPES = {"processing", "marketing", "sharing", "analytics"}


class ConsentUpdateRequest(BaseModel):
    consents: Dict[str, bool]
    source: Optional[str] = None
    change_reason: Optional[str] = None
    metadata: Optional[dict] = None


def _resolve_target_user(current_user: User, user_id: Optional[int], db: Session) -> User:
    if user_id is None or user_id == current_user.id:
        return current_user
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to view other users' consents",
        )
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target


@consent_router.get("")
async def get_consents(
    user_id: Optional[int] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    target_user = _resolve_target_user(current_user, user_id, db)
    service = ConsentService(db)
    return {
        "user_id": target_user.id,
        "consents": service.get_current_consents(target_user.id),
    }


@consent_router.get("/history")
async def get_consent_history(
    user_id: Optional[int] = None,
    consent_type: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    target_user = _resolve_target_user(current_user, user_id, db)
    service = ConsentService(db)
    history = service.get_history(target_user.id, consent_type=consent_type)
    return {
        "user_id": target_user.id,
        "history": [row.to_dict() for row in history],
    }


@consent_router.post("")
async def update_consents(
    request: ConsentUpdateRequest,
    user_id: Optional[int] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    target_user = _resolve_target_user(current_user, user_id, db)
    unknown = set(request.consents.keys()) - ALLOWED_CONSENT_TYPES
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown consent types: {', '.join(sorted(unknown))}",
        )
    service = ConsentService(db)
    consents = service.set_consents_bulk(
        user_id=target_user.id,
        consents=request.consents,
        source=request.source,
        change_reason=request.change_reason,
        metadata=request.metadata,
    )
    return {"user_id": target_user.id, "consents": consents}
