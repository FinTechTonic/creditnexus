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

from app.api.polymarket_surveillance_routes import router as polymarket_surveillance_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/polymarket", tags=["polymarket"])
router.include_router(polymarket_surveillance_router)


def _get_policy_service() -> Optional[Any]:
    """PolicyService for market resolution checks; None if policy disabled."""
    try:
        from app.services.policy_engine_factory import get_policy_engine
        from app.services.policy_service import PolicyService
        e = get_policy_engine()
        return PolicyService(e) if e else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateMarketRequest(BaseModel):
    """Request to create a prediction market for a deal, or to list pool/tranche for funding, or a loan binary market."""

    deal_id: Optional[int] = Field(None, description="Deal ID (required for SFP/NDVI markets)")
    pool_id: Optional[int] = Field(None, description="Pool ID for pool funding listing")
    tranche_id: Optional[int] = Field(None, description="Tranche ID for tranche investment listing")
    loan_asset_id: Optional[int] = Field(None, description="Loan asset ID for loan binary markets (LOAN_REPAID, LOAN_ON_TIME, LOAN_REPAID_CRYPTO)")
    question: str = Field(..., min_length=1, description="Market question")
    outcome_type: str = Field("binary", description="Outcome type: binary, categorical")
    resolution_condition: Dict[str, Any] = Field(
        ...,
        description="Condition for resolution (e.g. {\"type\":\"NDVI_COMPLIANCE\",\"threshold\":0.5} or {\"type\":\"LOAN_REPAID\",\"loan_asset_id\":1})",
    )
    market_event_type: str = Field("NDVI_COMPLIANCE", description="SFP market event type or LOAN_REPAID, LOAN_ON_TIME, LOAN_REPAID_CRYPTO for loan binaries")
    anchor_to_blockchain: bool = Field(True, description="Anchor SFP Merkle root on-chain (skipped for pool/tranche/loan listings)")
    signers: Optional[List[str]] = Field(None, description="Signer addresses for notarization")
    liquidity_pool_address: Optional[str] = Field(None, description="CLOB/liquidity pool address")
    visibility: str = Field("public", description="public or internal")
    publish_to_polymarket: bool = Field(
        False,
        description="Optional: also export to external Polymarket for discovery; SFPs are always listed internally.",
    )


class ResolveMarketRequest(BaseModel):
    """Request to resolve a market."""

    resolution_outcome: str = Field(..., description="Outcome: yes, no, or category value")
    oracle_triggered: bool = Field(False, description="Whether resolution was oracle/automation-triggered")


class PlaceOrderRequest(BaseModel):
    """Request to place an order in the internal order book."""

    side: str = Field(..., description="yes or no")
    price: float = Field(..., ge=0, le=1, description="Price in [0, 1]")
    size: float = Field(..., gt=0, description="Order size")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/markets", response_model=Dict[str, Any])
async def create_market(
    request: CreateMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a prediction market: for a deal (SFP), or list pool/tranche for funding, or loan binary (LOAN_REPAID/ON_TIME/CRYPTO)."""
    if not any([request.deal_id, request.pool_id, request.tranche_id, request.loan_asset_id]):
        raise HTTPException(
            status_code=400,
            detail="One of deal_id, pool_id, tranche_id, loan_asset_id is required",
        )
    svc = PolymarketService(db)
    try:
        return svc.create_market(
            deal_id=request.deal_id,
            pool_id=request.pool_id,
            tranche_id=request.tranche_id,
            loan_asset_id=request.loan_asset_id,
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


@router.get("/markets/{market_id}/book", response_model=Dict[str, Any])
async def get_order_book(
    market_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get order book (bids/asks) for an internal SFP market."""
    svc = PolymarketService(db)
    try:
        return svc.get_order_book(market_id=market_id)
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("get_order_book failed")
        raise HTTPException(status_code=500, detail="Failed to get order book")


@router.get("/markets/{market_id}/orders", response_model=List[Dict[str, Any]])
async def list_market_orders(
    market_id: str,
    user: Optional[str] = Query("me", description="'me' for current user's orders"),
    status: Optional[str] = Query(None, description="Filter: open, filled, cancelled"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List orders for a market. Use user=me for current user's orders."""
    if user != "me":
        raise HTTPException(status_code=400, detail="Only user=me is supported")
    svc = PolymarketService(db)
    try:
        return svc.get_user_orders(market_id=market_id, user_id=current_user.id, status=status)
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("list_market_orders failed")
        raise HTTPException(status_code=500, detail="Failed to list orders")


@router.post("/markets/{market_id}/orders", response_model=Dict[str, Any])
async def place_order(
    market_id: str,
    body: PlaceOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Place an order in the internal SFP market order book."""
    svc = PolymarketService(db)
    try:
        return svc.place_order(
            market_id=market_id,
            user_id=current_user.id,
            side=body.side,
            price=body.price,
            size=body.size,
        )
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "resolved" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("place_order failed")
        raise HTTPException(status_code=500, detail="Failed to place order")


@router.delete("/markets/orders/{order_id}", response_model=Dict[str, Any])
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an open order."""
    svc = PolymarketService(db)
    try:
        return svc.cancel_order(order_id=order_id, user_id=current_user.id)
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("cancel_order failed")
        raise HTTPException(status_code=500, detail="Failed to cancel order")


@router.get("/markets/{market_id}/suggest-resolution", response_model=Dict[str, Any])
async def suggest_resolution(
    market_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest resolution outcome from Verifier/oracle (e.g. NDVI) when condition type is NDVI_COMPLIANCE."""
    svc = PolymarketService(db)
    try:
        return await svc.suggest_resolution(market_id=market_id)
    except PolymarketServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "already resolved" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("suggest_resolution failed")
        raise HTTPException(status_code=500, detail="Failed to suggest resolution")


@router.post("/markets/{market_id}/resolve", response_model=Dict[str, Any])
async def resolve_market(
    market_id: str,
    body: ResolveMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    policy_service: Optional[Any] = Depends(_get_policy_service),
):
    """Resolve a prediction market. Policy service blocks resolution when decision is BLOCK."""
    svc = PolymarketService(db)
    try:
        return svc.resolve_market(
            market_id=market_id,
            resolution_outcome=body.resolution_outcome,
            oracle_triggered=body.oracle_triggered,
            policy_service=policy_service,
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
