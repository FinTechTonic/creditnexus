"""Challenge Coin API: my-tokens (ChallengeCoin NFTs held by the current user)."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import User
from app.services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["challenge-coin"])


def get_blockchain_service() -> BlockchainService:
    return BlockchainService()


@router.get("/challenge-coins/my-tokens", response_model=Dict[str, Any])
async def my_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    blockchain: BlockchainService = Depends(get_blockchain_service),
) -> Dict[str, Any]:
    """List ChallengeCoin NFTs held by the current user's wallet."""
    wallet = getattr(current_user, "wallet_address", None)
    if not wallet or not str(wallet).strip():
        return {"tokens": []}
    tokens = blockchain.get_challenge_coin_tokens_by_owner(wallet)
    return {"tokens": tokens}
