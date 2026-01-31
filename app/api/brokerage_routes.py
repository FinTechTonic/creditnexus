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
from app.services.entitlement_service import has_org_unlocked
from app.services.alpaca_account_service import (
    open_alpaca_account,
    AlpacaAccountServiceError,
    sync_alpaca_account_status,
)
from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError
from app.services.plaid_service import (
    create_link_token_for_brokerage,
    create_link_token_for_funding,
    get_identity,
    get_plaid_connection,
)
from app.services.brokerage_funding_service import (
    link_bank_for_funding,
    list_linked_banks,
    fund_account,
    withdraw_from_account,
)
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brokerage", tags=["brokerage"])


class AccountStatusResponse(BaseModel):
    """Brokerage account status for the current user (equities + crypto per Alpaca)."""
    has_account: bool
    status: Optional[str] = None  # Equities: SUBMITTED, ACTIVE, ACTION_REQUIRED, REJECTED
    crypto_status: Optional[str] = None  # Crypto: INACTIVE, ACTIVE, SUBMISSION_FAILED
    enabled_assets: Optional[List[str]] = None  # e.g. ["us_equity"] when equities active
    alpaca_account_id: Optional[str] = None
    account_number: Optional[str] = None
    action_required_reason: Optional[str] = None
    currency: str = "USD"


class AgreementItem(BaseModel):
    """Single agreement acceptance (Alpaca customer_agreement / margin_agreement)."""
    agreement: str = Field(..., description="e.g. customer_agreement, margin_agreement")
    signed_at: str = Field(..., description="ISO 8601 timestamp when user accepted")
    ip_address: Optional[str] = Field("0.0.0.0", description="Client IP at acceptance (optional)")


class FundRequest(BaseModel):
    """Request to fund brokerage account (ACH INCOMING)."""
    amount: str = Field(..., description="Amount in USD (e.g. 100.00)")
    relationship_id: Optional[str] = Field(None, description="Linked bank relationship_id; omit to use first.")


class WithdrawRequest(BaseModel):
    """Request to withdraw from brokerage to linked bank (ACH OUTGOING)."""
    amount: str = Field(..., description="Amount in USD")
    relationship_id: str = Field(..., description="Linked bank relationship_id (required).")


class LinkBankForFundingRequest(BaseModel):
    """Request to link a bank for brokerage funding (Plaid Link → processor token → Alpaca ACH)."""
    public_token: str = Field(..., description="Plaid Link onSuccess public_token")
    plaid_account_id: str = Field(..., description="Plaid account_id from Link metadata")
    nickname: Optional[str] = Field(None, description="Optional nickname for the linked bank")


class ApplyRequest(BaseModel):
    """Brokerage apply request: optional agreements (from UI), Plaid KYC flag, and asset classes."""
    agreements: Optional[List[AgreementItem]] = Field(
        None,
        description="Client-provided agreement acceptances (signed_at from UI). Required for Plaid KYC flow.",
    )
    use_plaid_kyc: bool = Field(
        False,
        description="When True, KYC is satisfied by linked Plaid identity (user must have linked via brokerage Link).",
    )
    prefill: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional prefill from Plaid identity (given_name, family_name, address, etc.).",
    )
    enabled_assets: Optional[List[str]] = Field(
        None,
        description="Asset classes to enable: e.g. ['us_equity', 'crypto']. Defaults to ['us_equity'] if omitted.",
    )


_ORG_UNLOCK_402_MESSAGE = (
    "Complete initial $2 payment or subscription to link accounts and open accounts."
)


@router.get("/link-token", response_model=Dict[str, Any])
async def brokerage_link_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get Plaid Link token for brokerage onboarding (link-for-brokerage). Optional fee info when fee enabled."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
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


def _kyc_to_prefill(profile_data: Any) -> Dict[str, Any]:
    """Build brokerage prefill dict from user-settings KYC info (profile_data.kyc)."""
    if not profile_data or not isinstance(profile_data, dict):
        return {}
    kyc = profile_data.get("kyc") or {}
    if not kyc:
        return {}
    prefill: Dict[str, Any] = {}
    legal = (kyc.get("legal_name") or "").strip()
    if legal:
        parts = legal.split(None, 1)
        prefill["given_name"] = parts[0] if parts else ""
        prefill["family_name"] = parts[1] if len(parts) > 1 else ""
    if kyc.get("date_of_birth"):
        prefill["date_of_birth"] = str(kyc["date_of_birth"])[:10]
    if kyc.get("address_line1"):
        prefill["street_address"] = str(kyc["address_line1"]).strip()
    if kyc.get("address_city"):
        prefill["city"] = str(kyc["address_city"]).strip()
    if kyc.get("address_state"):
        prefill["state"] = str(kyc["address_state"]).strip()
    if kyc.get("address_postal_code"):
        prefill["postal_code"] = str(kyc["address_postal_code"]).strip()
    if kyc.get("address_country"):
        prefill["country"] = str(kyc["address_country"]).strip()
    return prefill


@router.get("/prefill", response_model=Dict[str, Any])
async def brokerage_prefill(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get identity/account prefill from Plaid and/or User Settings KYC for brokerage application form."""
    prefill_data: Dict[str, Any] = {}
    source = "none"
    message = ""

    # 1) Plaid identity (if linked)
    conn = get_plaid_connection(db, current_user.id)
    if conn and getattr(conn, "connection_data", None) and isinstance(conn.connection_data, dict):
        access_token = conn.connection_data.get("access_token")
        if access_token:
            identity_resp = get_identity(access_token)
            if "error" not in identity_resp:
                accounts = identity_resp.get("accounts") or []
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
                if prefill_data:
                    source = "plaid"
            else:
                message = identity_resp.get("error", "Could not fetch identity.")
        else:
            message = "Plaid connection missing access token."
    else:
        message = "No linked bank account. Link an account or fill User Settings → KYC & Identity to prefill."

    # 2) Merge or fallback to User Settings KYC info
    kyc_prefill = _kyc_to_prefill(getattr(current_user, "profile_data", None))
    if kyc_prefill:
        if source == "plaid":
            for key, value in kyc_prefill.items():
                if value and not prefill_data.get(key):
                    prefill_data[key] = value
            source = "both"
        else:
            prefill_data = kyc_prefill
            source = "user_settings"
        if not message and source == "user_settings":
            message = "Prefill from User Settings → KYC & Identity. Edit there to change."

    return {"prefill": prefill_data, "source": source, "message": message or None}


@router.post("/account/apply", response_model=Dict[str, Any])
async def brokerage_account_apply(
    body: Optional[ApplyRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Submit Alpaca Broker account application.
    Use Plaid KYC flow: link via Plaid (brokerage link-token), pass agreements (signed_at from UI), use_plaid_kyc=True.
    """
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    agreements_override = None
    prefill_override = None
    use_plaid_kyc = False
    enabled_assets = None
    if body:
        use_plaid_kyc = body.use_plaid_kyc
        prefill_override = body.prefill
        enabled_assets = body.enabled_assets
        if body.agreements and len(body.agreements) >= 2:
            agreements_override = [
                {"agreement": a.agreement, "signed_at": a.signed_at, "ip_address": a.ip_address or "0.0.0.0"}
                for a in body.agreements
            ]
    try:
        rec = open_alpaca_account(
            current_user.id,
            db,
            agreements_override=agreements_override,
            prefill_override=prefill_override,
            use_plaid_kyc=use_plaid_kyc,
            enabled_assets=enabled_assets,
        )
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
    """Get current user's Alpaca Broker account status. Syncs from Alpaca so refresh returns status, crypto_status, and enabled_assets."""
    acc = (
        db.query(AlpacaCustomerAccount)
        .filter(AlpacaCustomerAccount.user_id == current_user.id)
        .first()
    )
    if not acc:
        return AccountStatusResponse(has_account=False, currency="USD")
    # Always sync from Alpaca so response includes equities status, crypto_status, enabled_assets
    _, alpaca_data = sync_alpaca_account_status(acc, db)
    db.refresh(acc)
    # If sync returned no data (e.g. client unavailable), try direct fetch so we still show ACTIVE when Alpaca says so
    if not alpaca_data:
        client = get_broker_client()
        if client:
            try:
                alpaca_data = client.get_account(acc.alpaca_account_id)
                # Persist so DB matches Alpaca and next request does not need to re-fetch
                if alpaca_data:
                    _s = (alpaca_data.get("status") or "").upper()
                    if _s and (_s != (acc.status or "").upper() or acc.account_number != (alpaca_data.get("account_number") or acc.account_number)):
                        acc.status = _s
                        acc.account_number = alpaca_data.get("account_number") or acc.account_number
                        acc.action_required_reason = alpaca_data.get("action_required_reason") or alpaca_data.get("reason") or acc.action_required_reason
                        db.commit()
                        db.refresh(acc)
            except AlpacaBrokerAPIError as e:
                logger.warning("Brokerage status fallback get_account failed for %s: %s", acc.alpaca_account_id, e)
    if alpaca_data:
        _status = (alpaca_data.get("status") or acc.status) or ""
        _status = (_status.upper() if isinstance(_status, str) else str(_status)) or acc.status
        _crypto = alpaca_data.get("crypto_status")
        if _crypto and isinstance(_crypto, str):
            _crypto = _crypto.upper()
        return AccountStatusResponse(
            has_account=True,
            status=_status,
            crypto_status=_crypto,
            enabled_assets=alpaca_data.get("enabled_assets") if isinstance(alpaca_data.get("enabled_assets"), list) else None,
            alpaca_account_id=acc.alpaca_account_id,
            account_number=alpaca_data.get("account_number") or acc.account_number,
            action_required_reason=alpaca_data.get("action_required_reason") or alpaca_data.get("reason") or acc.action_required_reason,
            currency=alpaca_data.get("currency") or acc.currency or "USD",
        )
    return AccountStatusResponse(
        has_account=True,
        status=(acc.status or "").upper() or None,
        crypto_status=None,
        enabled_assets=None,
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


@router.get("/funding-link-token", response_model=Dict[str, Any])
async def brokerage_funding_link_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get Plaid Link token for linking a bank for brokerage funding (Auth product only)."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = create_link_token_for_funding(current_user.id)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return {"link_token": result["link_token"]}


@router.get("/ach-relationships", response_model=List[Dict[str, Any]])
async def brokerage_ach_relationships(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """List linked banks (ACH relationships) for brokerage funding/withdraw."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    return list_linked_banks(db, current_user.id)


@router.post("/link-bank-for-funding", response_model=Dict[str, Any])
async def brokerage_link_bank_for_funding(
    body: LinkBankForFundingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Link a bank for brokerage funding (Plaid Link → processor token → Alpaca ACH)."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = link_bank_for_funding(
        db,
        current_user.id,
        body.public_token,
        body.plaid_account_id,
        body.nickname,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/fund", response_model=Dict[str, Any])
async def brokerage_fund(
    body: FundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Fund brokerage account from linked bank (ACH INCOMING)."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = fund_account(db, current_user.id, body.amount, body.relationship_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/withdraw", response_model=Dict[str, Any])
async def brokerage_withdraw(
    body: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Withdraw from brokerage account to linked bank (ACH OUTGOING)."""
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    result = withdraw_from_account(db, current_user.id, body.amount, body.relationship_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
