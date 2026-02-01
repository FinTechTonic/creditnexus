"""Agent score API: Plaid-derived borrower score by agent wallet (MCP x402 flow)."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.service_auth import get_user_for_api
from app.db import get_db
from app.db.models import User
from app.services.plaid_service import get_plaid_connection_by_agent_wallet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent-score"])

# Default Plaid-linked score component when no Signal/risk data (0–100 additive to base 100).
DEFAULT_PLAID_LINKED_SCORE = 50


@router.get("/agent-score", response_model=Dict[str, Any])
def get_agent_score(
    wallet: str = Query(..., description="Agent (payer) wallet address"),
    current_user: User = Depends(get_user_for_api),
    db: Session = Depends(get_db),
):
    """
    Get Plaid-derived borrower score component for an agent wallet.
    Used by MCP get_borrower_score: returns { plaid_score: int } when the wallet
    has an associated Plaid connection (from onboarding or open_bank_account).
    """
    conn = get_plaid_connection_by_agent_wallet(db, wallet)
    if not conn:
        raise HTTPException(status_code=404, detail="No Plaid connection for this agent wallet")
    # When Plaid Signal or lender score is available we could use it; for now return default.
    plaid_score = DEFAULT_PLAID_LINKED_SCORE
    return {"plaid_score": plaid_score}
