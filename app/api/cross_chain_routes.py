"""
Cross-chain and bridge API routes for Polymarket/SFP.

- GET /api/cross-chain/transactions — list CrossChainTransaction for current user
- GET /api/bridge/status — BridgeService.get_bridge_status(bridge_id)
- POST /api/outcome-tokens/mint — x402 gated; mints SFP outcome tokens via blockchain_service
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.config import settings
from app.db import get_db
from app.db.models import CrossChainTransaction, User
from app.models.cdm import Currency, Party
from app.services.blockchain_service import BlockchainService
from app.services.bridge_service import BridgeService
from app.services.x402_payment_service import X402PaymentService, get_x402_payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cross-chain"])


# ----- request/response models -----


class MintOutcomeTokenRequest(BaseModel):
    """Request for POST /outcome-tokens/mint. payment_payload omitted -> 402."""

    recipient_address: str = Field(..., description="Wallet to receive outcome tokens")
    outcome_token_id: int = Field(..., description="ERC-1155 outcome token id")
    amount: int = Field(..., gt=0, description="Token amount (integer units)")
    data: Optional[str] = Field(None, description="Optional hex or base64 data for mint (e.g. 0x or omit)")
    payment_payload: Optional[Dict[str, Any]] = Field(
        None,
        description="x402 payment payload; if omitted, response is 402 with payment_request",
    )


# ----- dependencies -----


def get_bridge_service() -> BridgeService:
    return BridgeService()


def get_blockchain_service() -> BlockchainService:
    return BlockchainService()


# ----- GET /api/cross-chain/transactions -----


@router.get("/cross-chain/transactions", response_model=List[Dict[str, Any]])
async def list_cross_chain_transactions(
    status: Optional[str] = Query(None, description="Filter by status: pending, submitted, completed, failed"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List cross-chain transactions for the current user."""
    q = db.query(CrossChainTransaction).filter(CrossChainTransaction.user_id == current_user.id)
    if status:
        q = q.filter(CrossChainTransaction.status == status)
    rows = q.order_by(CrossChainTransaction.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "source_chain_id": r.source_chain_id,
            "dest_chain_id": r.dest_chain_id,
            "bridge_external_id": r.bridge_external_id,
            "status": r.status,
            "amount": str(r.amount) if r.amount is not None else None,
            "token_address": r.token_address,
            "market_event_id": r.market_event_id,
            "outcome_token_id": r.outcome_token_id,
            "dest_tx_hash": r.dest_tx_hash,
            "extra_data": r.extra_data,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


# ----- GET /api/bridge/status -----


@router.get("/bridge/status", response_model=Dict[str, Any])
async def bridge_status(
    bridge_id: str = Query(..., description="Bridge transfer id from submit"),
    bridge_svc: BridgeService = Depends(get_bridge_service),
) -> Dict[str, Any]:
    """Return status of a bridge transfer from the external bridge API."""
    if not bridge_svc.is_available:
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "message": "CROSS_CHAIN_ENABLED or POLYMARKET_BRIDGE_API_URL not set"},
        )
    result = await bridge_svc.get_bridge_status(bridge_id)
    if result is None:
        raise HTTPException(status_code=502, detail={"status": "error", "message": "Bridge API request failed"})
    return result


# ----- POST /api/outcome-tokens/mint (x402) -----


# Default minting fee when x402 is used (config could add OUTCOME_MINT_FEE_AMOUNT / CURRENCY later)
_DEFAULT_MINT_FEE = Decimal("0.01")
_DEFAULT_MINT_FEE_CURRENCY = Currency.USD


@router.post("/outcome-tokens/mint", response_model=Dict[str, Any])
async def mint_outcome_token(
    body: MintOutcomeTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service),
    blockchain: BlockchainService = Depends(get_blockchain_service),
) -> Dict[str, Any]:
    """
    Mint SFP outcome tokens (ERC-1155) to recipient. Requires CROSS_CHAIN_ENABLED and
    SFP_OUTCOME_TOKEN_CONTRACT. When payment_payload is omitted, returns 402 with
    payment_request; when provided, processes x402 then mints.
    """
    if not getattr(settings, "CROSS_CHAIN_ENABLED", False):
        raise HTTPException(status_code=503, detail={"message": "CROSS_CHAIN_ENABLED is false"})
    if not getattr(settings, "SFP_OUTCOME_TOKEN_CONTRACT", None):
        raise HTTPException(status_code=503, detail={"message": "SFP_OUTCOME_TOKEN_CONTRACT not configured"})

    data_bytes: Optional[bytes] = None
    if body.data:
        if body.data.startswith("0x"):
            try:
                data_bytes = bytes.fromhex(body.data[2:])
            except ValueError:
                pass
        if data_bytes is None:
            import base64
            try:
                data_bytes = base64.b64decode(body.data)
            except Exception:
                data_bytes = body.data.encode("utf-8")

    # --- x402 payment flow ---
    if not payment_service:
        raise HTTPException(status_code=503, detail={"message": "x402 payment service not available"})

    payer = Party(
        id=str(current_user.id),
        name=getattr(current_user, "display_name", None) or getattr(current_user, "email", None) or "User",
        role="Payer",
        lei=None,
    )
    receiver = Party(
        id="creditnexus-outcome-mint",
        name="CreditNexus Outcome Mint",
        role="Receiver",
        lei=None,
    )

    payment_payload = body.payment_payload
    payment_result = await payment_service.process_payment_flow(
        amount=_DEFAULT_MINT_FEE,
        currency=_DEFAULT_MINT_FEE_CURRENCY,
        payer=payer,
        receiver=receiver,
        payment_type="outcome_token_mint",
        payment_payload=payment_payload,
        cdm_reference={"outcome_token_id": body.outcome_token_id, "recipient": body.recipient_address},
    )

    if payment_payload is None or payment_result.get("status") != "settled":
        return JSONResponse(
            status_code=402,
            content={
                "status": "Payment Required",
                "payment_request": payment_result.get("payment_request"),
                "amount": str(_DEFAULT_MINT_FEE),
                "currency": _DEFAULT_MINT_FEE_CURRENCY.value,
                "payer": {"id": payer.id, "name": payer.name, "lei": payer.lei},
                "receiver": {"id": receiver.id, "name": receiver.name, "lei": receiver.lei},
                "facilitator_url": payment_service.facilitator_url,
            },
        )

    # --- mint ---
    out = blockchain.mint_outcome_token(
        recipient_address=body.recipient_address,
        outcome_token_id=body.outcome_token_id,
        amount=body.amount,
        data=data_bytes,
    )
    if out.get("status") == "error":
        raise HTTPException(status_code=500, detail=out)
    if out.get("status") == "skipped":
        raise HTTPException(status_code=503, detail=out)
    return {
        "status": "completed",
        "transaction_hash": out.get("transaction_hash"),
        "outcome_token_id": body.outcome_token_id,
        "amount": body.amount,
        "recipient": body.recipient_address,
    }
