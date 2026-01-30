"""Unified funding API: request (402 or settled), complete (after_funding_settled)."""

import logging
from decimal import Decimal
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.entitlement_service import has_org_unlocked
from app.services.unified_funding_service import request_funding, after_funding_settled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/funding", tags=["funding"])

_ORG_UNLOCK_402_MESSAGE = (
    "Complete initial payment or subscription to use funding."
)


def get_payment_router(request: Request):
    return getattr(request.app.state, "payment_router_service", None)


class FundingRequest(BaseModel):
    """Request to fund a destination (credit_top_up, polymarket_funding, alpaca_funding)."""
    amount: Decimal = Field(..., gt=0, description="Amount in USD")
    payment_type: Literal["credit_top_up", "polymarket_funding", "alpaca_funding"] = Field(
        ...,
        description="Funding destination type",
    )
    destination_id: Optional[str] = Field(None, description="Optional destination (e.g. proxy address for Polymarket)")
    payment_payload: Optional[Dict[str, Any]] = Field(
        None,
        description="x402 payment payload from wallet; if omitted, response is 402 with payment_request",
    )


class FundingCompleteRequest(BaseModel):
    """Request to complete funding after payment (callback or client pays)."""
    payment_type: Literal["credit_top_up", "polymarket_funding", "alpaca_funding"] = Field(...)
    payment_result: Dict[str, Any] = Field(..., description="Payment result (status, amount, etc.)")
    destination_id: Optional[str] = Field(None)
    amount: Optional[Decimal] = Field(None, description="Amount settled (if not in payment_result)")


@router.post("/request", response_model=Dict[str, Any])
async def funding_request(
    body: FundingRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Request funding: route payment by type. If payment_payload omitted, returns 402 with payment_request (same shape as org-admin upgrade).
    """
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    pr = get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    result = await request_funding(
        db=db,
        user_id=current_user.id,
        amount=body.amount,
        payment_type=body.payment_type,
        destination_identifier=body.destination_id,
        payment_router=pr,
        payment_payload=body.payment_payload,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    if result.get("status_code") == 402 or (not body.payment_payload and result.get("status") != "settled"):
        response_content = {
            "status": "Payment Required",
            "payment_request": result.get("payment_request"),
            "amount": str(body.amount),
            "currency": "USD",
            "payment_type": body.payment_type,
            "facilitator_url": getattr(pr.x402, "facilitator_url", None) if pr and getattr(pr, "x402", None) else None,
        }
        return JSONResponse(status_code=402, content=response_content)

    if result.get("status") != "settled":
        raise HTTPException(
            status_code=400,
            detail=result.get("verification") or result.get("status") or "Payment could not be completed",
        )

    # Payment settled in same request; run after_funding_settled
    after = after_funding_settled(
        db=db,
        user_id=current_user.id,
        payment_type=body.payment_type,
        payment_result=result,
        destination_identifier=body.destination_id,
        amount=body.amount,
    )
    return {
        "status": "settled",
        "payment_id": result.get("payment_id"),
        "transaction_hash": result.get("transaction_hash"),
        "after_funding": after,
    }


@router.post("/complete", response_model=Dict[str, Any])
async def funding_complete(
    body: FundingCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Complete funding after payment: verify payment_result and call after_funding_settled (add credits, etc.).
    """
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    amount = body.amount
    if amount is None and isinstance(body.payment_result.get("amount"), (int, float)):
        amount = Decimal(str(body.payment_result["amount"]))
    after = after_funding_settled(
        db=db,
        user_id=current_user.id,
        payment_type=body.payment_type,
        payment_result=body.payment_result,
        destination_identifier=body.destination_id,
        amount=amount,
    )
    if not after.get("ok", True):
        raise HTTPException(status_code=400, detail=after.get("reason", "after_funding_settled failed"))
    return {"status": "completed", "after_funding": after}


# Credits top-up: convenience route that uses funding/request with payment_type=credit_top_up
credits_router = APIRouter(prefix="/api/credits", tags=["credits"])


class CreditsTopUpRequest(BaseModel):
    """Request to top up rolling credits (x402 or RevenueCat)."""
    amount: Decimal = Field(..., gt=0, description="Amount in USD")
    payment_payload: Optional[Dict[str, Any]] = Field(
        None,
        description="x402 payment payload; if omitted, returns 402 with payment_request",
    )


@credits_router.post("/top-up", response_model=Dict[str, Any])
async def credits_top_up(
    body: CreditsTopUpRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Top up rolling credits. If payment_payload omitted, returns 402 with payment_request (same shape as funding/request).
    On success, adds credits via after_funding_settled(CREDIT_TOP_UP).
    """
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    pr = get_payment_router(request)
    if not pr:
        raise HTTPException(status_code=503, detail="Payment router not available")

    result = await request_funding(
        db=db,
        user_id=current_user.id,
        amount=body.amount,
        payment_type="credit_top_up",
        destination_identifier=None,
        payment_router=pr,
        payment_payload=body.payment_payload,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    if result.get("status_code") == 402 or (not body.payment_payload and result.get("status") != "settled"):
        response_content = {
            "status": "Payment Required",
            "payment_request": result.get("payment_request"),
            "amount": str(body.amount),
            "currency": "USD",
            "payment_type": "credit_top_up",
            "facilitator_url": getattr(pr.x402, "facilitator_url", None) if pr and getattr(pr, "x402", None) else None,
        }
        return JSONResponse(status_code=402, content=response_content)

    if result.get("status") != "settled":
        raise HTTPException(
            status_code=400,
            detail=result.get("verification") or result.get("status") or "Payment could not be completed",
        )

    after = after_funding_settled(
        db=db,
        user_id=current_user.id,
        payment_type="credit_top_up",
        payment_result=result,
        destination_identifier=None,
        amount=body.amount,
    )
    return {
        "status": "settled",
        "payment_id": result.get("payment_id"),
        "transaction_hash": result.get("transaction_hash"),
        "after_funding": after,
    }
