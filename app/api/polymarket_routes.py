"""Polymarket-style prediction market API for SFP-backed markets."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import User
from app.services.polymarket_service import PolymarketService, PolymarketServiceError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket", tags=["polymarket"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateMarketRequest(BaseModel):
    """Request to create a prediction market for a deal."""

    deal_id: int = Field(..., description="Deal ID")
    question: str = Field(..., min_length=1, description="Market question")
    outcome_type: str = Field("binary", description="Outcome type: binary, categorical")
    resolution_condition: Dict[str, Any] = Field(
        ...,
        description="Condition for resolution (e.g. {\"type\":\"NDVI_COMPLIANCE\",\"threshold\":0.5})",
    )
    market_event_type: str = Field("NDVI_COMPLIANCE", description="SFP market event type")
    anchor_to_blockchain: bool = Field(True, description="Anchor SFP Merkle root on-chain")
    signers: Optional[List[str]] = Field(None, description="Signer addresses for notarization")
    liquidity_pool_address: Optional[str] = Field(None, description="CLOB/liquidity pool address")
    visibility: str = Field("public", description="public or internal")
    publish_to_polymarket: Optional[bool] = Field(
        None,
        description="Register with Polymarket Gamma/CLOB when True; when None, use POLYMARKET_PUBLISH_EXTERNAL",
    )


class ResolveMarketRequest(BaseModel):
    """Request to resolve a market."""

    resolution_outcome: str = Field(..., description="Outcome: yes, no, or category value")
    oracle_triggered: bool = Field(False, description="Whether resolution was oracle/automation-triggered")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/markets", response_model=Dict[str, Any])
async def create_market(
    request: CreateMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a prediction market for a deal (SFP bundle + optional blockchain anchor)."""
    svc = PolymarketService(db)
    try:
        return svc.create_market(
            deal_id=request.deal_id,
            question=request.question,
            outcome_type=request.outcome_type,
            resolution_condition=request.resolution_condition,
            created_by=current_user.id,
            market_event_type=request.market_event_type,
            anchor_to_blockchain=request.anchor_to_blockchain,
            signers=request.signers,
            liquidity_pool_address=request.liquidity_pool_address,
            visibility=request.visibility,
            publish_to_polymarket=request.publish_to_polymarket,
        )
    except PolymarketServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("create_market failed")
        raise HTTPException(status_code=500, detail="Failed to create market")


@router.get("/external/events", response_model=List[Dict[str, Any]])
async def external_events(
    active: bool = Query(True),
    closed: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """Proxy to Polymarket Gamma API: list events (for discovery)."""
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient()
        return client.fetch_events(active=active, closed=closed, limit=limit, offset=offset)
    except Exception as e:
        logger.warning("external_events failed: %s", e)
        return []


@router.get("/external/markets", response_model=List[Dict[str, Any]])
async def external_markets(
    tag: Optional[str] = Query(None),
    active: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """Proxy to Polymarket Gamma API: list markets (for discovery)."""
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient()
        return client.fetch_markets(tag=tag, active=active, limit=limit, offset=offset)
    except Exception as e:
        logger.warning("external_markets failed: %s", e)
        return []


@router.get("/external/book", response_model=Dict[str, Any])
async def external_book(
    token_id: str = Query(..., description="Outcome token ID"),
    current_user: User = Depends(get_current_user),
):
    """Proxy to Polymarket CLOB: order book for an outcome token."""
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient()
        return client.get_book(token_id)
    except Exception as e:
        logger.warning("external_book failed: %s", e)
        return {}


@router.get("/markets", response_model=List[Dict[str, Any]])
async def list_markets(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    resolved: Optional[bool] = Query(None, description="True=resolved only, False=open only"),
    visibility: Optional[str] = Query(None, description="Filter by visibility"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List prediction markets with optional filters."""
    svc = PolymarketService(db)
    try:
        return svc.list_markets(
            deal_id=deal_id,
            resolved=resolved,
            visibility=visibility,
            limit=limit,
            offset=offset,
        )
    except PolymarketServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("list_markets failed")
        raise HTTPException(status_code=500, detail="Failed to list markets")


@router.post("/markets/{market_id}/resolve", response_model=Dict[str, Any])
async def resolve_market(
    market_id: str,
    body: ResolveMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve a prediction market."""
    svc = PolymarketService(db)
    try:
        return svc.resolve_market(
            market_id=market_id,
            resolution_outcome=body.resolution_outcome,
            oracle_triggered=body.oracle_triggered,
        )
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "already resolved" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("resolve_market failed")
        raise HTTPException(status_code=500, detail="Failed to resolve market")
