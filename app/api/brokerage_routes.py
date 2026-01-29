"""Brokerage API: Alpaca account opening (apply, status, documents)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.core.config import settings
from app.db import get_db
from app.db.models import User, AlpacaCustomerAccount
from app.db.models import AuditAction
from app.services.alpaca_account_service import open_alpaca_account, AlpacaAccountServiceError
from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError
from app.services.plaid_service import (
    create_link_token_for_brokerage,
    get_identity,
    get_plaid_connection,
)
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brokerage", tags=["brokerage"])


class AccountStatusResponse(BaseModel):
    """Brokerage account status for the current user."""
    has_account: bool
    status: Optional[str] = None
    alpaca_account_id: Optional[str] = None
    account_number: Optional[str] = None
    action_required_reason: Optional[str] = None
    currency: str = "USD"


@router.get("/link-token", response_model=Dict[str, Any])
async def brokerage_link_token(
    current_user: User = Depends(require_auth),
):
    """Get Plaid Link token for brokerage onboarding (link-for-brokerage). Optional fee info when fee enabled."""
    result = create_link_token_for_brokerage(current_user.id)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    out = {"link_token": result["link_token"]}
    if getattr(settings, "BROKERAGE_ONBOARDING_FEE_ENABLED", False):
        out["fee_enabled"] = True
        out["fee_amount"] = str(getattr(settings, "BROKERAGE_ONBOARDING_FEE_AMOUNT", 0))
        out["fee_currency"] = getattr(
            getattr(settings, "BROKERAGE_ONBOARDING_FEE_CURRENCY", None), "value", "USD"
        )
        out["product_id"] = getattr(settings, "BROKERAGE_ONBOARDING_PRODUCT_ID", "brokerage_onboarding")
    else:
        out["fee_enabled"] = False
    return out


@router.get("/prefill", response_model=Dict[str, Any])
async def brokerage_prefill(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get identity/account prefill from linked Plaid connection for brokerage application form."""
    conn = get_plaid_connection(db, current_user.id)
    if not conn or not getattr(conn, "connection_data", None) or not isinstance(conn.connection_data, dict):
        return {"prefill": {}, "message": "No linked bank account. Link an account to prefill the form."}
    access_token = conn.connection_data.get("access_token")
    if not access_token:
        return {"prefill": {}, "message": "Plaid connection missing access token."}
    identity_resp = get_identity(access_token)
    if "error" in identity_resp:
        return {"prefill": {}, "message": identity_resp.get("error", "Could not fetch identity.")}
    accounts = identity_resp.get("accounts") or []
    prefill_data: Dict[str, Any] = {}
    for acc in accounts:
        owners = acc.get("owners") or []
        for owner in owners:
            if not isinstance(owner, dict):
                continue
            names = owner.get("names") or []
            if names and isinstance(names, list):
                full = (names[0] or "").strip()
                parts = full.split(None, 1)
                prefill_data["given_name"] = parts[0] if parts else ""
                prefill_data["family_name"] = parts[1] if len(parts) > 1 else (names[1] if len(names) > 1 else "")
            addrs = owner.get("addresses") or []
            for a in addrs:
                if isinstance(a, dict) and a.get("data"):
                    d = a["data"]
                    prefill_data["street_address"] = d.get("street") or ""
                    prefill_data["city"] = d.get("city") or ""
                    prefill_data["state"] = d.get("region") or ""
                    prefill_data["postal_code"] = d.get("postal_code") or ""
                    prefill_data["country"] = d.get("country") or "US"
                    break
            if prefill_data:
                break
        if prefill_data:
            break
    return {"prefill": prefill_data}


@router.post("/account/apply", response_model=Dict[str, Any])
async def brokerage_account_apply(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Submit Alpaca Broker account application. Requires KYC to be sufficient."""
    try:
        rec = open_alpaca_account(current_user.id, db)
        return {
            "status": "submitted",
            "alpaca_account_id": rec.alpaca_account_id,
            "account_status": rec.status,
            "message": "Application submitted. You will receive status updates; check GET /api/brokerage/account/status.",
        }
    except AlpacaAccountServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/status", response_model=AccountStatusResponse)
async def brokerage_account_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get current user's Alpaca Broker account status."""
    acc = (
        db.query(AlpacaCustomerAccount)
        .filter(AlpacaCustomerAccount.user_id == current_user.id)
        .first()
    )
    if not acc:
        return AccountStatusResponse(has_account=False, currency="USD")
    return AccountStatusResponse(
        has_account=True,
        status=acc.status,
        alpaca_account_id=acc.alpaca_account_id,
        account_number=acc.account_number,
        action_required_reason=acc.action_required_reason,
        currency=acc.currency or "USD",
    )


@router.post("/account/documents", response_model=Dict[str, Any])
async def brokerage_account_documents(
    document_type: str = Form(..., description="e.g. identity_document, address_verification"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Upload a document for Alpaca account (when status is ACTION_REQUIRED)."""
    acc = (
        db.query(AlpacaCustomerAccount)
        .filter(
            AlpacaCustomerAccount.user_id == current_user.id,
            AlpacaCustomerAccount.status == "ACTION_REQUIRED",
        )
        .first()
    )
    if not acc:
        raise HTTPException(
            status_code=400,
            detail="No brokerage account in ACTION_REQUIRED status. Apply first or check status.",
        )
    client = get_broker_client()
    if not client:
        raise HTTPException(status_code=503, detail="Broker API not configured")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        import io
        client.upload_document(
            acc.alpaca_account_id,
            document_type=document_type,
            file_content=io.BytesIO(content),
            filename=file.filename or "document.pdf",
            content_type=file.content_type or "application/pdf",
        )
    except AlpacaBrokerAPIError as e:
        logger.warning("Broker document upload failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Broker API error: {e}")
    log_audit_action(
        db=db,
        action=AuditAction.UPDATE,
        target_type="alpaca_customer_account",
        target_id=acc.id,
        user_id=current_user.id,
        metadata={
            "alpaca_account_id": acc.alpaca_account_id,
            "brokerage_event": "document_upload",
            "document_type": document_type,
        },
    )
    return {"status": "uploaded", "message": "Document submitted for review."}


@router.post("/fund", response_model=Dict[str, Any])
async def brokerage_fund_placeholder(
    current_user: User = Depends(require_auth),
):
    """Placeholder: fund account from bank (Plaid/ACH). Not implemented."""
    raise HTTPException(
        status_code=501,
        detail="Fund account not yet implemented. See docs for future Plaid/ACH integration.",
    )


@router.post("/withdraw", response_model=Dict[str, Any])
async def brokerage_withdraw_placeholder(
    current_user: User = Depends(require_auth),
):
    """Placeholder: withdraw from brokerage account. Not implemented."""
    raise HTTPException(
        status_code=501,
        detail="Withdraw not yet implemented. See docs for future integration.",
    )
