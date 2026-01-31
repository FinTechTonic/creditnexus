"""Newsfeed API: posts, like, comment, share; funding (Week 13)."""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.entitlement_service import has_org_unlocked
from app.services.newsfeed_service import NewsfeedService, NewsfeedServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/newsfeed", tags=["newsfeed"])

_ORG_UNLOCK_402_MESSAGE = "Complete initial payment or subscription to use newsfeed funding."


def get_payment_router(request: Request):
    return getattr(request.app.state, "payment_router_service", None)


class CommentRequest(BaseModel):
    """Request to add a comment or reply."""

    content: str = Field(..., min_length=1, max_length=10000)
    parent_comment_id: Optional[int] = None


class ShareRequest(BaseModel):
    """Request to share a post."""

    share_type: str = Field("internal", description="internal, external, fdc3")
    shared_to: Optional[str] = Field(None, max_length=500)


class FundRequest(BaseModel):
    """Request to fund a securitized product from a newsfeed post."""

    post_id: int = Field(..., description="Newsfeed post ID")
    amount: Decimal = Field(..., gt=0, description="Amount in USD")
    payment_type: str = Field(
        ...,
        description="One of: alpaca_funding, polymarket_funding, credit_top_up",
    )
    payment_payload: Optional[Dict[str, Any]] = Field(
        None,
        description="x402 payment payload from wallet; if omitted, returns 402 with payment_request",
    )


@router.get("", response_model=Dict[str, Any])
def get_newsfeed(
    organization_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    post_type: Optional[str] = Query(None),
    deal_type: Optional[str] = Query(None),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get newsfeed posts for the current user."""
    filters = {}
    if post_type:
        filters["post_type"] = post_type
    if deal_type:
        filters["deal_type"] = deal_type
    org_id = organization_id or (current_user.organization_id if current_user else None)
    service = NewsfeedService(db)
    posts = service.get_newsfeed(
        user_id=current_user.id,
        organization_id=org_id,
        limit=limit,
        offset=offset,
        filters=filters or None,
    )
    return {"posts": posts}


@router.post("/posts/{post_id}/like", response_model=Dict[str, Any])
def like_post(
    post_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Toggle like on a post."""
    service = NewsfeedService(db)
    try:
        result = service.like_post(post_id=post_id, user_id=current_user.id)
        return result
    except NewsfeedServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/posts/{post_id}/comment", response_model=Dict[str, Any])
def comment_on_post(
    post_id: int,
    body: CommentRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add a comment or reply to a post."""
    service = NewsfeedService(db)
    try:
        comment = service.comment_on_post(
            post_id=post_id,
            user_id=current_user.id,
            content=body.content,
            parent_comment_id=body.parent_comment_id,
        )
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "parent_comment_id": comment.parent_comment_id,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }
    except NewsfeedServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/posts/{post_id}/share", response_model=Dict[str, Any])
def share_post(
    post_id: int,
    body: ShareRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Record a share of a post."""
    service = NewsfeedService(db)
    try:
        share = service.share_post(
            post_id=post_id,
            user_id=current_user.id,
            share_type=body.share_type,
            shared_to=body.shared_to,
        )
        return {
            "id": share.id,
            "post_id": share.post_id,
            "share_type": share.share_type,
            "created_at": share.created_at.isoformat() if share.created_at else None,
        }
    except NewsfeedServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/funding-options/{asset_type}", response_model=Dict[str, Any])
def get_funding_options(
    asset_type: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get funding options for the given asset type (equity, loan, polymarket, market, or default)."""
    service = NewsfeedService(db)
    options = service.get_funding_options(asset_type or "default")
    return {"asset_type": asset_type or "default", "options": options}


@router.post("/fund", response_model=Dict[str, Any])
async def fund_securitized_product(
    body: FundRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Fund a securitized product from a newsfeed post. Returns 402 with payment_request if payment required.
    """
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    pr = get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    service = NewsfeedService(db)
    try:
        result = await service.fund_securitized_product(
            post_id=body.post_id,
            user_id=current_user.id,
            amount=body.amount,
            payment_type=body.payment_type,
            payment_router=pr,
            payment_payload=body.payment_payload,
        )
    except NewsfeedServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    if result.get("status_code") == 402 or (
        not body.payment_payload and result.get("status") != "settled"
    ):
        response_content = {
            "status": "Payment Required",
            "payment_request": result.get("payment_request"),
            "amount": str(body.amount),
            "currency": "USD",
            "payment_type": body.payment_type,
            "post_id": body.post_id,
            "facilitator_url": getattr(pr.x402, "facilitator_url", None)
            if pr and getattr(pr, "x402", None)
            else None,
        }
        return JSONResponse(status_code=402, content=response_content)

    if result.get("status") != "settled":
        raise HTTPException(
            status_code=400,
            detail=result.get("verification") or result.get("status") or "Payment could not be completed",
        )
    return {"status": "settled", "result": result}
