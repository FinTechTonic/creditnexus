"""Banking API (Plaid) for account linking, balances, and transactions (Trading Phase 1)."""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.config import settings
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW
from app.db import get_db
from app.db.models import User, UserImplementationConnection
from app.services.plaid_service import (
    create_link_token,
    exchange_public_token,
    get_accounts,
    get_balances,
    get_transactions,
    get_plaid_connection,
    ensure_plaid_implementation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/banking", tags=["banking"])


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


@router.get("/status", response_model=BankingStatusResponse)
async def banking_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get banking status: plaid_enabled (from server config) and connected (user's Plaid link). For client feature flags and Link accounts UI. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    plaid_enabled = bool(getattr(settings, "PLAID_ENABLED", False))
    connected = False
    if plaid_enabled:
        conn = get_plaid_connection(db, current_user.id)
        connected = conn is not None and bool(conn.connection_data)
    return BankingStatusResponse(plaid_enabled=plaid_enabled, connected=connected)


@router.get("/link-token", response_model=Dict[str, Any])
async def banking_link_token(
    current_user: User = Depends(get_current_user),
):
    """Create a Plaid Link token to initialize Link in the frontend. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    _plaid_ok()
    out = create_link_token(current_user.id)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    return out


@router.post("/connect", response_model=Dict[str, Any])
async def banking_connect(
    body: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange Plaid public_token and store access_token in UserImplementationConnection. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    _plaid_ok()

    out = exchange_public_token(body.public_token)
    if "error" in out:
        raise HTTPException(status_code=400, detail=out["error"])

    impl = ensure_plaid_implementation(db)
    conn = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == current_user.id,
        UserImplementationConnection.implementation_id == impl.id,
    ).first()

    connection_data = {"access_token": out["access_token"], "item_id": out["item_id"]}
    if conn:
        conn.connection_data = connection_data
        conn.is_active = True
    else:
        conn = UserImplementationConnection(
            user_id=current_user.id,
            implementation_id=impl.id,
            connection_data=connection_data,
            is_active=True,
        )
        db.add(conn)
    db.commit()
    return {"status": "connected", "connection_id": conn.id}


@router.get("/accounts", response_model=Dict[str, Any])
async def banking_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List accounts from the linked Plaid Item. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    _plaid_ok()

    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_accounts(at)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    return out


@router.get("/balances", response_model=Dict[str, Any])
async def banking_balances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get balances for the linked Plaid Item. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    _plaid_ok()
    
    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_balances(at)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    return out


@router.get("/transactions", response_model=Dict[str, Any])
async def banking_transactions(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    count: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get transactions for the linked Plaid Item. Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    _plaid_ok()

    conn = get_plaid_connection(db, current_user.id)
    if not conn or not conn.connection_data or not isinstance(conn.connection_data, dict):
        raise HTTPException(status_code=404, detail="No Plaid connection. Link a bank first.")

    at = conn.connection_data.get("access_token")
    if not at:
        raise HTTPException(status_code=404, detail="Plaid access_token missing")

    out = get_transactions(at, start_date=start_date, end_date=end_date, account_id=account_id, count=count, offset=offset)
    if "error" in out:
        raise HTTPException(status_code=502, detail=out["error"])
    return out


@router.delete("/disconnect", status_code=204)
async def banking_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Plaid (deactivate connection; does not delete). Requires PERMISSION_TRADE_VIEW."""
    if not has_permission(current_user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    conn = get_plaid_connection(db, current_user.id)
    if not conn:
        raise HTTPException(status_code=404, detail="No Plaid connection")
    conn.is_active = False
    conn.connection_data = None
    db.commit()
    return None
