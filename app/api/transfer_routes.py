"""Plaid Transfer API: authorize, create, get (instant interbank)."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.entitlement_service import has_org_unlocked
from app.services.plaid_transfer_service import (
    create_transfer_authorization,
    create_transfer,
    get_transfer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transfers", tags=["transfers"])

_ORG_UNLOCK_402_MESSAGE = (
    "Complete initial payment or subscription to use instant transfers."
)


class TransferAuthorizeRequest(BaseModel):
    """Request to authorize a Plaid transfer."""
    access_token: str = Field(..., description="Plaid access token (from linked item)")
    account_id: str = Field(..., description="Plaid account_id")
    amount: str = Field(..., description="Amount in USD")
    direction: str = Field(default="debit", description="debit (pull from user) or credit (push to user)")
    counterparty: Dict[str, Any] = Field(default_factory=dict, description="Optional counterparty (e.g. legal_name)")


class TransferCreateRequest(BaseModel):
    """Request to create a transfer after authorization."""
    authorization_id: str = Field(..., description="Authorization ID from /transfers/authorize")
    idempotency_key: str = Field(..., description="Idempotency key for safe retries")
    access_token: str = Field(..., description="Plaid access token")
    account_id: str = Field(..., description="Plaid account_id")
    description: str = Field(default="CreditNexus transfer", description="Transfer description")


@router.post("/authorize", response_model=Dict[str, Any])
async def transfers_authorize(
    body: TransferAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Authorize a Plaid transfer (POST /transfer/authorization/create). Gate: org unlock → 402."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = create_transfer_authorization(
        access_token=body.access_token,
        account_id=body.account_id,
        amount=body.amount,
        direction=body.direction,
        counterparty=body.counterparty,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/create", response_model=Dict[str, Any])
async def transfers_create(
    body: TransferCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Create a transfer after authorization (POST /transfer/create). Gate: org unlock → 402."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = create_transfer(
        authorization_id=body.authorization_id,
        idempotency_key=body.idempotency_key,
        access_token=body.access_token,
        account_id=body.account_id,
        description=body.description,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{transfer_id}", response_model=Dict[str, Any])
async def transfers_get(
    transfer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get transfer status (GET /transfer/get). Gate: org unlock → 402. Caller must ensure transfer belongs to user (via linked account)."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = get_transfer(transfer_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
