"""Polymarket-style prediction market API for SFP-backed markets."""

import logging
from typing import Any, Dict, List, Optional

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user, require_auth
from app.db import get_db
from app.db.models import User
from app.services.polymarket_service import PolymarketService, PolymarketServiceError
from app.services.polymarket_account_service import (
    get_link_status as get_polymarket_link_status,
    get_user_l2_creds,
    link_polymarket_account,
    unlink_polymarket_account,
)
from app.services.entitlement_service import can_access_byok
from app.services.polymarket_builder_signing_service import build_builder_headers
from app.services.polymarket_clob_service import place_order as clob_place_order
from app.services.polymarket_relayer_service import (
    deploy_safe as relayer_deploy_safe,
    ensure_user_approvals as relayer_ensure_user_approvals,
    execute_transactions as relayer_execute,
    get_transaction as relayer_get_transaction,
)
from pydantic import BaseModel, Field

from app.api.polymarket_surveillance_routes import router as polymarket_surveillance_router
from app.services.unified_funding_service import after_funding_settled, request_funding

logger = logging.getLogger(__name__)


def _get_payment_router(request: Request):
    return getattr(request.app.state, "payment_router_service", None)

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


class PolymarketLinkRequest(BaseModel):
    """Request to link Polymarket L2 credentials (api_key, secret, passphrase per CLOB)."""

    api_key: str = Field(..., min_length=1, description="Polymarket CLOB API key")
    secret: str = Field(..., min_length=1, description="Polymarket CLOB secret")
    passphrase: str = Field(..., min_length=1, description="Polymarket CLOB passphrase")
    funder_address: Optional[str] = Field(None, description="Optional Polygon proxy/Safe address for CLOB funder")


class BuilderSignRequest(BaseModel):
    """Request for remote builder signing (method, path, body for CLOB/relayer request)."""

    method: str = Field(..., description="HTTP method (e.g. POST, GET)")
    path: str = Field(..., description="Request path (e.g. /order)")
    body: str = Field(default="", description="Request body as string (e.g. JSON)")


class PlaceClobOrderRequest(BaseModel):
    """Request to place a signed order on Polymarket CLOB (user L2 + builder headers applied server-side)."""

    order: Dict[str, Any] = Field(..., description="Signed order from client (salt, maker, signer, taker, tokenId, etc.)")
    order_type: str = Field(default="GTC", description="GTC, FOK, or GTD")
    post_only: bool = Field(default=False, description="If true, order only rests on book (no immediate match)")


# ---------------------------------------------------------------------------
# Builder signing (remote mode: client gets headers to attach to CLOB/relayer)
# ---------------------------------------------------------------------------


@router.post("/builder/sign", response_model=Dict[str, str])
async def polymarket_builder_sign(
    body: BuilderSignRequest,
    current_user: User = Depends(require_auth),
):
    """Return Polymarket builder attribution headers for the given method/path/body. Auth required; rate-limit per user in production."""
    headers = build_builder_headers(
        method=body.method.strip() or "GET",
        path=body.path.strip() or "/",
        body=body.body or "",
    )
    if not headers:
        raise HTTPException(
            status_code=503,
            detail="Builder signing not available (POLY_BUILDER_* not configured).",
        )
    return headers


# ---------------------------------------------------------------------------
# Account linking (per-user L2; same semantics as BYOK Polymarket)
# ---------------------------------------------------------------------------


@router.get("/link-status", response_model=Dict[str, Any])
async def polymarket_link_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Return Polymarket account link status (linked, funder_address if set). No raw creds."""
    return get_polymarket_link_status(current_user.id, db)


@router.post("/link", response_model=Dict[str, Any])
async def polymarket_link(
    body: PolymarketLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Link Polymarket L2 credentials (BYOK). Requires BYOK access. Same storage as user-settings BYOK Polymarket."""
    if not can_access_byok(current_user, db):
        raise HTTPException(status_code=402, detail="BYOK access required. Upgrade or pay to configure keys.")
    ok = link_polymarket_account(
        user_id=current_user.id,
        db=db,
        api_key=body.api_key,
        secret=body.secret,
        passphrase=body.passphrase,
        funder_address=body.funder_address,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or missing api_key, secret, or passphrase.")
    return {"linked": True}


@router.delete("/link", response_model=Dict[str, Any])
async def polymarket_unlink(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Unlink Polymarket account (remove stored L2 credentials)."""
    if not can_access_byok(current_user, db):
        raise HTTPException(status_code=402, detail="BYOK access required to manage keys.")
    unlink_polymarket_account(current_user.id, db)
    return {"linked": False}


# ---------------------------------------------------------------------------
# CLOB orders (place client-signed order with user L2 + builder headers)
# ---------------------------------------------------------------------------


@router.post("/orders", response_model=Dict[str, Any])
async def polymarket_place_order(
    body: PlaceClobOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Place a client-signed order on Polymarket CLOB. Requires linked Polymarket account (BYOK) with funder_address. Returns orderId/status or 402 if not linked."""
    result = clob_place_order(
        user_id=current_user.id,
        db=db,
        signed_order=body.order,
        order_type=body.order_type,
        post_only=body.post_only,
    )
    if not result.get("ok") and result.get("error") in ("polymarket_not_linked", "funder_required"):
        raise HTTPException(
            status_code=402,
            detail=result.get("message", "Link Polymarket account with funder_address to place orders."),
        )
    if not result.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Order placement failed."),
        )
    return {
        "success": result.get("success", True),
        "orderId": result.get("orderId"),
        "orderHashes": result.get("orderHashes", []),
        "status": result.get("status"),
        "errorMsg": result.get("errorMsg"),
    }


# ---------------------------------------------------------------------------
# Relayer (gasless Safe/proxy deploy and CTF execute)
# ---------------------------------------------------------------------------


class RelayerDeployRequest(BaseModel):
    """Request to deploy Safe/proxy via Polymarket relayer."""

    funder_address: Optional[str] = Field(None, description="User's EOA or existing proxy address")


class RelayerExecuteRequest(BaseModel):
    """Request to execute transactions via Polymarket relayer."""

    proxy_address: str = Field(..., description="Proxy/Safe address to execute from")
    transactions: List[Dict[str, Any]] = Field(..., description="List of { to, data, value }")
    description: Optional[str] = Field(None, description="Optional description for the batch")


@router.post("/relayer/deploy", response_model=Dict[str, Any])
async def polymarket_relayer_deploy(
    body: RelayerDeployRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Deploy Safe/proxy for current user via Polymarket relayer (gasless). Requires builder creds."""
    result = relayer_deploy_safe(
        user_id=current_user.id,
        db=db,
        funder_address=body.funder_address,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=result.get("status_code", 502),
            detail=result.get("message", "Relayer deploy failed."),
        )
    return {
        "proxy_address": result.get("proxy_address"),
        "transaction_id": result.get("transaction_id"),
        "transaction_hash": result.get("transaction_hash"),
    }


@router.post("/relayer/execute", response_model=Dict[str, Any])
async def polymarket_relayer_execute(
    body: RelayerExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Execute batch of transactions via Polymarket relayer for proxy_address. Require auth; verify proxy belongs to user in production."""
    result = relayer_execute(
        user_id=current_user.id,
        db=db,
        proxy_address=body.proxy_address,
        transactions=body.transactions,
        description=body.description or "",
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=result.get("status_code", 502),
            detail=result.get("message", "Relayer execute failed."),
        )
    return {
        "transaction_id": result.get("transaction_id"),
        "transaction_hash": result.get("transaction_hash"),
        "state": result.get("state"),
    }


class RelayerApproveSetupRequest(BaseModel):
    """Request for approval-setup transactions (USDCe/CTF for proxy)."""

    proxy_address: str = Field(..., description="User's proxy/Safe address to approve for")


@router.post("/relayer/approve-setup", response_model=Dict[str, Any])
async def polymarket_relayer_approve_setup(
    body: RelayerApproveSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Return list of transactions (approve USDCe, approve CTF) for client to submit via POST /relayer/execute."""
    transactions = relayer_ensure_user_approvals(
        user_id=current_user.id,
        db=db,
        proxy_address=body.proxy_address.strip(),
    )
    return {"transactions": transactions, "proxy_address": body.proxy_address.strip()}


@router.get("/relayer/transaction/{transaction_id}", response_model=Dict[str, Any])
async def polymarket_relayer_transaction(
    transaction_id: str,
    current_user: User = Depends(require_auth),
):
    """Get relayer transaction state by id."""
    result = relayer_get_transaction(transaction_id)
    if not result.get("ok"):
        raise HTTPException(
            status_code=result.get("status_code", 404),
            detail=result.get("message", "Transaction not found."),
        )
    return {
        "transaction_id": result.get("transaction_id"),
        "state": result.get("state"),
        "transaction_hash": result.get("transaction_hash"),
        "proxy_address": result.get("proxy_address"),
    }


# ---------------------------------------------------------------------------
# Funding markets and fund via Polymarket (Week 17)
# ---------------------------------------------------------------------------


class PolymarketFundRequest(BaseModel):
    """Request to fund a Polymarket funding market (uses linked account + payment router)."""

    market_id: str = Field(..., min_length=1, description="Funding market ID (pool/tranche/loan listing)")
    amount: float = Field(..., gt=0, description="Amount in USD to fund")


@router.get("/funding-markets", response_model=List[Dict[str, Any]])
async def polymarket_funding_markets(
    visibility: Optional[str] = Query("public", description="Filter by visibility"),
    resolved: bool = Query(False, description="Include resolved markets"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List markets suitable for funding (pool/tranche/loan listings only). Excludes platform equities and structured loan products."""
    svc = PolymarketService(db)
    try:
        return svc.get_funding_markets(visibility=visibility, resolved=resolved, limit=limit, offset=offset)
    except PolymarketServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning("funding-markets failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list funding markets")


@router.post("/fund", response_model=Dict[str, Any])
async def polymarket_fund(
    body: PolymarketFundRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Validate funding market and route payment via unified funding (polymarket_funding). Returns 402 with payment_request or success."""
    svc = PolymarketService(db)
    result = svc.fund_via_polymarket(current_user.id, body.market_id, amount=body.amount, require_linked=True)
    if not result.get("ok") or not result.get("eligible"):
        if result.get("error") == "polymarket_not_linked":
            raise HTTPException(status_code=402, detail=result.get("message", "Link Polymarket account to fund."))
        raise HTTPException(status_code=400, detail=result.get("message", "Not eligible to fund this market."))

    pr = _get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    amount_decimal = Decimal(str(body.amount))
    funding_result = await request_funding(
        db=db,
        user_id=current_user.id,
        amount=amount_decimal,
        payment_type="polymarket_funding",
        destination_identifier=body.market_id,
        payment_router=pr,
        payment_payload=None,
    )
    if "error" in funding_result:
        raise HTTPException(status_code=400, detail=funding_result["error"])

    if funding_result.get("status_code") == 402 or funding_result.get("status") != "settled":
        return JSONResponse(
            status_code=402,
            content={
                "status": "Payment Required",
                "payment_request": funding_result.get("payment_request"),
                "amount": str(body.amount),
                "currency": "USD",
                "payment_type": "polymarket_funding",
                "market_id": body.market_id,
                "facilitator_url": getattr(pr.x402, "facilitator_url", None) if getattr(pr, "x402", None) else None,
            },
        )

    after_funding_settled(
        db=db,
        user_id=current_user.id,
        payment_type="polymarket_funding",
        payment_result=funding_result,
        destination_identifier=body.market_id,
        amount=amount_decimal,
    )
    return {"success": True, "market_id": body.market_id, "amount": str(body.amount), "status": "settled"}


# ---------------------------------------------------------------------------
# Positions and orders (user-scoped)
# ---------------------------------------------------------------------------


@router.get("/positions", response_model=List[Dict[str, Any]])
async def polymarket_positions(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get current user's Polymarket activity/positions (Data API). Requires linked account with funder_address."""
    status = get_polymarket_link_status(current_user.id, db)
    if not status.get("linked") or not status.get("funder_address"):
        return []
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient()
        return client.fetch_activity(user=status["funder_address"], limit=limit)
    except Exception as e:
        logger.warning("Polymarket positions failed: %s", e)
        return []


@router.get("/orders", response_model=List[Dict[str, Any]])
async def polymarket_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get current user's open orders (CLOB). Requires linked Polymarket account. Returns [] if not linked or CLOB unavailable."""
    creds = get_user_l2_creds(current_user.id, db)
    if not creds or not creds.get("api_key"):
        return []
    try:
        from app.services.polymarket_api_client import PolymarketAPIClient
        client = PolymarketAPIClient.from_user_l2_creds(
            api_key=creds["api_key"],
            secret=creds["secret"],
            passphrase=creds["passphrase"],
        )
        # CLOB GET /orders - if client has get_orders use it; else return [] until we add it
        if hasattr(client, "get_orders"):
            return client.get_orders() or []
        return []
    except Exception as e:
        logger.warning("Polymarket orders failed: %s", e)
        return []


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
