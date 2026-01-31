"""Bridge Builder API: create-trade, execute-trade for ChallengeCoin NFT cross-chain."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import BridgeTrade, User
from app.services.blockchain_service import BlockchainService
from app.services.bridge_builder_service import BridgeBuilderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["bridge-builder"])


class CreateTradeRequest(BaseModel):
    token_id: int = Field(..., description="ChallengeCoin NFT token ID")
    target_chain_id: int = Field(..., description="Target chain ID")
    target_address: str = Field(..., min_length=42, max_length=66, description="Target address (0x...)")
    source_chain_id: Optional[int] = Field(None, description="Source chain ID (default: connected chain)")
    trade_type: str = Field("transfer", description="Trade type")


class ExecuteTradeRequest(BaseModel):
    trade_id: int = Field(..., description="Bridge trade ID from create-trade")
    signed_lock_tx: Optional[str] = Field(None, description="Hex of signed lockForBridge transaction (with or without 0x)")
    lock_tx_hash: Optional[str] = Field(None, description="If the client sent the lock tx (e.g. via MetaMask), pass the tx hash here instead of signed_lock_tx")


def get_blockchain_service() -> BlockchainService:
    return BlockchainService()


@router.get("/bridge-builder/trade/{trade_id}", response_model=Dict[str, Any])
async def get_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a bridge trade by id for the current user (Phase 9)."""
    t = db.query(BridgeTrade).filter(BridgeTrade.id == trade_id, BridgeTrade.user_id == current_user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found or access denied")
    return {
        "id": t.id,
        "user_id": t.user_id,
        "token_id": t.token_id,
        "source_chain_id": t.source_chain_id,
        "target_chain_id": t.target_chain_id,
        "target_address": t.target_address,
        "trade_type": t.trade_type,
        "status": t.status,
        "lock_tx_hash": t.lock_tx_hash,
        "bridge_external_id": t.bridge_external_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.post("/bridge-builder/create-trade", response_model=Dict[str, Any])
async def create_trade(
    body: CreateTradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    blockchain: BlockchainService = Depends(get_blockchain_service),
) -> Dict[str, Any]:
    """Create a bridge trade: returns an unsigned lockForBridge tx for the client to sign."""
    source = body.source_chain_id
    if source is None and blockchain.web3 and blockchain.is_connected():
        try:
            source = blockchain.web3.eth.chain_id
        except Exception:
            pass
    if source is None:
        raise HTTPException(
            status_code=400,
            detail="source_chain_id required when not connected to a chain",
        )
    svc = BridgeBuilderService(db)
    try:
        return svc.create_bridge_trade(
            user_id=current_user.id,
            token_id=body.token_id,
            source_chain_id=source,
            target_chain_id=body.target_chain_id,
            target_address=body.target_address,
            trade_type=body.trade_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bridge-builder/execute-trade", response_model=Dict[str, Any])
async def execute_trade(
    body: ExecuteTradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute a bridge trade by submitting the signed lock transaction."""
    t = db.query(BridgeTrade).filter(BridgeTrade.id == body.trade_id).first()
    if not t or t.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Trade not found or access denied")
    svc = BridgeBuilderService(db)
    try:
        if body.lock_tx_hash:
            return await svc.execute_bridge_trade_with_lock_hash(
                trade_id=body.trade_id,
                lock_tx_hash=body.lock_tx_hash.strip(),
            )
        if body.signed_lock_tx:
            return await svc.execute_bridge_trade(
                trade_id=body.trade_id,
                signed_lock_tx_hex=body.signed_lock_tx,
            )
        raise HTTPException(status_code=400, detail="Provide signed_lock_tx or lock_tx_hash")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
