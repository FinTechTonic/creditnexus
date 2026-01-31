"""Banking API (Plaid) for account linking, balances, and transactions (Trading Phase 1)."""

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.auth.jwt_auth import require_auth
from app.core.config import settings
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW
from app.db import get_db
from app.db.models import PlaidUsageTracking, User, UserImplementationConnection
from app.services.entitlement_service import has_org_unlocked
from app.services.payment_gateway_service import PaymentGatewayService
from app.services.plaid_service import (
    create_link_token,
    exchange_public_token,
    get_accounts,
    get_balances,
    get_transactions,
    get_plaid_connection,
    get_plaid_connections,
    ensure_plaid_implementation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/banking", tags=["banking"])

def _track_plaid_usage(
    *,
    db: Session,
    user_id: int,
    organization_id: Optional[int],
    api_endpoint: str,
    item_id: Optional[str] = None,
    account_id: Optional[str] = None,
    request_id: Optional[str] = None,
    cost_usd: float = 0.0,
    usage_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort Plaid usage tracking for billing/credits. Never store secrets.
    If tracking fails, do not block the primary request.
    """
    try:
        rec = PlaidUsageTracking(
            user_id=user_id,
            organization_id=organization_id,
            api_endpoint=api_endpoint,
            request_id=request_id,
            cost_usd=cost_usd,
            item_id=item_id,
            account_id=account_id,
            usage_metadata=usage_metadata or {},
        )
        db.add(rec)
        db.commit()
    except Exception as e:
        logger.warning("Plaid usage tracking failed: %s", e)


class ConnectRequest(BaseModel):
    """Request to connect a bank via Plaid (exchange public_token)."""
    public_token: str = Field(..., description="Public token from Plaid Link onSuccess")


def _plaid_ok() -> None:
    if not getattr(settings, "PLAID_ENABLED", False):
        raise HTTPException(status_code=503, detail="Plaid is disabled (PLAID_ENABLED=false)")


class BankingStatusResponse(BaseModel):
    """Banking feature and connection status (client-safe; no secrets)."""
    plaid_enabled: bool = Field(..., description="Whether Plaid bank linking is enabled server-side")
    connected: bool = Field(..., description="Whether the user has an active Plaid connection")


class BankingConnectionItem(BaseModel):
    """One Plaid connection (multi-item); no secrets."""
    id: int = Field(..., description="Connection row id")
    item_id_masked: Optional[str] = Field(None, description="Last 4 of item_id for display")
    created_at: Optional[str] = Field(None, description="Created at ISO string")


@router.get("/status", response_model=BankingStatusResponse)
async def banking_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get banking status: plaid_enabled (from server config) and connected (any Plaid link)."""
    plaid_enabled = bool(getattr(settings, "PLAID_ENABLED", False))
    connected = False
    if plaid_enabled:
        conns = get_plaid_connections(db, current_user.id)
        connected = any(
            c.connection_data and isinstance(c.connection_data, dict) and c.connection_data.get("access_token")
            for c in (conns or [])
        )
    return BankingStatusResponse(plaid_enabled=plaid_enabled, connected=connected)


_ORG_UNLOCK_402_MESSAGE = (
    "Complete initial $2 payment or subscription to link accounts and open accounts."
)


@router.get("/link-token", response_model=Dict[str, Any])
async def banking_link_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Create a Plaid Link token to initialize Link in the frontend."""
    _plaid_ok()
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )
    out = create_link_token(current_user.id)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    return out


@router.post("/connect", response_model=Dict[str, Any])
async def banking_connect(
    body: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Exchange Plaid public_token and store access_token in UserImplementationConnection."""
    _plaid_ok()
    if not has_org_unlocked(current_user, getattr(current_user, "organization_id", None), db):
        raise HTTPException(
            status_code=402,
            detail={"status": "error", "message": _ORG_UNLOCK_402_MESSAGE},
        )

    out = exchange_public_token(body.public_token)
    if "error" in out:
        raise HTTPException(status_code=400, detail=out["error"])

    impl = ensure_plaid_implementation(db)
    # Multi-item: always create a new connection so each Plaid item is a separate row.
    connection_data = {"access_token": out["access_token"], "item_id": out["item_id"]}
    conn = UserImplementationConnection(
        user_id=current_user.id,
        implementation_id=impl.id,
        connection_data=connection_data,
        is_active=True,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    _track_plaid_usage(
        db=db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        api_endpoint="item/public_token/exchange",
        item_id=out.get("item_id"),
        usage_metadata={"source": "banking_connect"},
    )
    return {"status": "connected", "connection_id": conn.id}


@router.get("/accounts", response_model=Dict[str, Any])
async def banking_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """List accounts from the linked Plaid Item."""
    _plaid_ok()

    # Credits gate: 1 credit per call; cost_usd for 402 (Plaid ~2–10 cents per call)
    plaid_cost = Decimal(str(getattr(settings, "PLAID_COST_USD", 0.05)))
    gate = await PaymentGatewayService(db).require_credits_or_402(
        user_id=current_user.id,
        credit_type="trading",
        amount=1.0,
        feature="plaid_accounts_get",
        cost_usd=plaid_cost,
    )
    if not gate.get("ok") and gate.get("status_code") == 402:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=402, content=gate)

    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_accounts(at)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    _track_plaid_usage(
        db=db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        api_endpoint="accounts/get",
        item_id=(conn.connection_data or {}).get("item_id") if isinstance(conn.connection_data, dict) else None,
        cost_usd=float(plaid_cost),
        usage_metadata={"source": "banking_accounts"},
    )
    return out


@router.get("/balances", response_model=Dict[str, Any])
async def banking_balances(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get balances for the linked Plaid Item."""
    _plaid_ok()

    plaid_cost = Decimal(str(getattr(settings, "PLAID_COST_USD", 0.05)))
    gate = await PaymentGatewayService(db).require_credits_or_402(
        user_id=current_user.id,
        credit_type="trading",
        amount=1.0,
        feature="plaid_balances_get",
        cost_usd=plaid_cost,
    )
    if not gate.get("ok") and gate.get("status_code") == 402:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=402, content=gate)
    
    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_balances(at)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    _track_plaid_usage(
        db=db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        api_endpoint="accounts/balance/get",
        item_id=(conn.connection_data or {}).get("item_id") if isinstance(conn.connection_data, dict) else None,
        cost_usd=float(plaid_cost),
        usage_metadata={"source": "banking_balances"},
    )
    return out


@router.get("/transactions", response_model=Dict[str, Any])
async def banking_transactions(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    count: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get transactions for the linked Plaid Item."""
    _plaid_ok()

    plaid_cost = Decimal(str(getattr(settings, "PLAID_COST_USD", 0.05)))
    gate = await PaymentGatewayService(db).require_credits_or_402(
        user_id=current_user.id,
        credit_type="trading",
        amount=1.0,
        feature="plaid_transactions_get",
        cost_usd=plaid_cost,
    )
    if not gate.get("ok") and gate.get("status_code") == 402:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=402, content=gate)

    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_transactions(at, start_date=start_date, end_date=end_date, account_id=account_id, count=count, offset=offset)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    _track_plaid_usage(
        db=db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        api_endpoint="transactions/get",
        item_id=(conn.connection_data or {}).get("item_id") if isinstance(conn.connection_data, dict) else None,
        account_id=account_id,
        cost_usd=float(plaid_cost),
        usage_metadata={"source": "banking_transactions", "count": count, "offset": offset},
    )
    return out


@router.get("/connections", response_model=List[BankingConnectionItem])
async def banking_list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """List user's Plaid connections (multi-item). Returns id, masked item_id, created_at; no secrets."""
    _plaid_ok()
    conns = get_plaid_connections(db, current_user.id)
    out: List[BankingConnectionItem] = []
    for c in conns or []:
        item_id = None
        if c.connection_data and isinstance(c.connection_data, dict):
            raw = c.connection_data.get("item_id") or ""
            item_id = f"…{str(raw)[-4:]}" if len(str(raw)) >= 4 else "…"
        out.append(
            BankingConnectionItem(
                id=c.id,
                item_id_masked=item_id,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
        )
    return out


@router.delete("/disconnect", status_code=204)
async def banking_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Disconnect all Plaid connections for the current user."""
    _plaid_ok()
    conns = get_plaid_connections(db, current_user.id)
    for conn in conns or []:
        conn.is_active = False
    if conns:
        db.commit()


@router.delete("/connections/{connection_id}", status_code=204)
async def banking_disconnect_one(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Disconnect one Plaid connection by id (multi-item)."""
    _plaid_ok()
    conn = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.id == connection_id,
        UserImplementationConnection.user_id == current_user.id,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn.is_active = False
    db.commit()


# Payment initiation endpoint (for Plaid bank payments)
class PlaidPaymentInitiationRequest(BaseModel):
    """Request for Plaid payment initiation."""
    amount: str = Field(..., description="Payment amount")
    currency: str = Field(default="USD", description="Payment currency")
    payment_type: str = Field(..., description="Payment type (e.g., org_admin_upgrade, subscription_upgrade)")
    recipient_name: Optional[str] = Field(None, description="(UK/EU) Recipient name for Payment Initiation")
    iban: Optional[str] = Field(None, description="(UK/EU) Recipient IBAN for Payment Initiation")


@router.post("/payment/initiate", response_model=Dict[str, Any])
async def plaid_payment_initiate(
    body: PlaidPaymentInitiationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Initiate a Plaid payment (bank transfer).
    
    This endpoint routes to PlaidService for bank-based payments.
    Note: Plaid Payment Initiation is currently a placeholder.
    """
    _plaid_ok()
    
    # Check if user has Plaid connection
    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(
            status_code=404,
            detail="No Plaid connection. Please link a bank account first."
        )
    
    # Route to PlaidService for payment initiation
    from app.services.plaid_service import create_payment_initiation
    
    result = create_payment_initiation(
        access_token=conn.connection_data.get("access_token"),
        amount=body.amount,
        currency=body.currency,
        payment_type=body.payment_type,
        recipient_name=body.recipient_name,
        iban=body.iban,
    )
    
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    
    # Track usage
    _track_plaid_usage(
        db=db,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
        api_endpoint="payment_initiation/create",
        item_id=conn.connection_data.get("item_id"),
        usage_metadata={"source": "plaid_payment_initiate", "payment_type": body.payment_type},
    )
    
    return {
        "status": "initiated",
        "mode": result.get("mode"),
        "payment_id": (
            (result.get("payment") or {}).get("payment_id")
            or (result.get("payment") or {}).get("id")
            or ((result.get("transfer") or {}).get("transfer") or {}).get("id")
            or (result.get("transfer") or {}).get("id")
        ),
        "message": "Plaid payment initiated. Waiting for confirmation via webhook.",
    }
