"""
Bridge credit verification API (Phase 12): POST verify, convert, sync.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import User
from app.services.bridge_credit_verification_service import BridgeCreditVerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge-verification", tags=["bridge-verification"])


class VerifyBody(BaseModel):
    credit_type: str = Field(..., min_length=1)
    amount: float = Field(..., ge=0)
    transaction_id: Optional[int] = None
    sync_from_chain: bool = False


class ConvertBody(BaseModel):
    amount: float = Field(..., ge=0)
    source_chain_id: Optional[int] = None
    target_chain_id: Optional[int] = None
    credit_type: str = "universal"


@router.post("/verify", response_model=Dict[str, Any])
def verify_credit_usage(
    body: VerifyBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify that a credit usage is reflected on blockchain (optional sync from chain)."""
    svc = BridgeCreditVerificationService(db)
    return svc.verify_credit_usage(
        user_id=current_user.id,
        credit_type=body.credit_type,
        amount=body.amount,
        transaction_id=body.transaction_id,
        sync_from_chain=body.sync_from_chain,
    )


@router.post("/convert", response_model=Dict[str, Any])
def convert_credits_via_bridge(
    body: ConvertBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert/move credits via cross-chain bridge (stub)."""
    svc = BridgeCreditVerificationService(db)
    return svc.convert_credits_via_bridge(
        user_id=current_user.id,
        amount=body.amount,
        source_chain_id=body.source_chain_id,
        target_chain_id=body.target_chain_id,
        credit_type=body.credit_type,
    )


@router.post("/sync", response_model=Dict[str, Any])
def sync_balance_from_blockchain(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync DB CreditBalance from on-chain state for current user."""
    svc = BridgeCreditVerificationService(db)
    return svc._sync_balance_from_blockchain(current_user.id)
