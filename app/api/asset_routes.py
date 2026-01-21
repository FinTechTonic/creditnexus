"""Assets API: manual assets, amortization, alerts (Trading Phase 3)."""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.permissions import has_permission, PERMISSION_TRADE_VIEW
from app.db import get_db
from app.db.models import User, ManualAsset, AssetAlert
from app.services.asset_amortization_service import AssetAmortizationService
from decimal import Decimal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _check_trade_view(user: User) -> None:
    if not has_permission(user, PERMISSION_TRADE_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# --- ManualAsset schemas ---

class ManualAssetCreate(BaseModel):
    asset_type: str = Field(..., description="fixed_income, real_estate, physical, interest_account")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    purchase_price: Decimal = Field(..., ge=0)
    current_value: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    maturity_date: Optional[date] = None
    interest_rate: Optional[Decimal] = None
    payment_frequency: Optional[str] = None  # monthly, quarterly, annually, at_maturity
    purchase_date: date = Field(...)
    notes: Optional[str] = None


class ManualAssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    current_value: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    maturity_date: Optional[date] = None
    interest_rate: Optional[Decimal] = None
    payment_frequency: Optional[str] = None
    notes: Optional[str] = None


class ManualAssetResponse(BaseModel):
    id: int
    asset_type: str
    name: str
    description: Optional[str]
    purchase_price: Decimal
    current_value: Optional[Decimal]
    quantity: Optional[Decimal]
    unit: Optional[str]
    maturity_date: Optional[date]
    interest_rate: Optional[Decimal]
    payment_frequency: Optional[str]
    amortization_schedule: Optional[List[Dict[str, Any]]] = None
    purchase_date: date
    notes: Optional[str]

    class Config:
        from_attributes = True


class AssetAlertCreate(BaseModel):
    alert_type: str = Field(..., description="maturity, price_threshold, amortization_payment")
    trigger_date: Optional[date] = None
    trigger_price: Optional[Decimal] = None
    message: str = Field(..., min_length=1)


def _asset_to_response(a: ManualAsset) -> ManualAssetResponse:
    return ManualAssetResponse(
        id=a.id,
        asset_type=a.asset_type,
        name=a.name,
        description=a.description,
        purchase_price=a.purchase_price,
        current_value=a.current_value,
        quantity=a.quantity,
        unit=a.unit,
        maturity_date=a.maturity_date,
        interest_rate=a.interest_rate,
        payment_frequency=a.payment_frequency,
        amortization_schedule=a.amortization_schedule if isinstance(a.amortization_schedule, list) else None,
        purchase_date=a.purchase_date,
        notes=a.notes,
    )


@router.get("/manual", response_model=List[ManualAssetResponse])
async def list_manual_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List manual assets for the current user."""
    _check_trade_view(current_user)
    rows = db.query(ManualAsset).filter(ManualAsset.user_id == current_user.id).order_by(ManualAsset.name).all()
    return [_asset_to_response(a) for a in rows]


@router.post("/manual", response_model=ManualAssetResponse)
async def create_manual_asset(
    body: ManualAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a manual asset."""
    _check_trade_view(current_user)
    a = ManualAsset(
        user_id=current_user.id,
        asset_type=body.asset_type,
        name=body.name,
        description=body.description,
        purchase_price=body.purchase_price,
        current_value=body.current_value,
        quantity=body.quantity,
        unit=body.unit,
        maturity_date=body.maturity_date,
        interest_rate=body.interest_rate,
        payment_frequency=body.payment_frequency,
        purchase_date=body.purchase_date,
        notes=body.notes,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _asset_to_response(a)


@router.get("/manual/{asset_id}", response_model=ManualAssetResponse)
async def get_manual_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a manual asset by id."""
    _check_trade_view(current_user)
    a = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.user_id == current_user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Manual asset not found")
    return _asset_to_response(a)


@router.put("/manual/{asset_id}", response_model=ManualAssetResponse)
async def update_manual_asset(
    asset_id: int,
    body: ManualAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a manual asset."""
    _check_trade_view(current_user)
    a = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.user_id == current_user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Manual asset not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _asset_to_response(a)


@router.delete("/manual/{asset_id}", status_code=204)
async def delete_manual_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a manual asset and its alerts."""
    _check_trade_view(current_user)
    a = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.user_id == current_user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Manual asset not found")
    db.delete(a)
    db.commit()
    return None


@router.post("/manual/{asset_id}/generate-schedule", response_model=Dict[str, Any])
async def generate_amortization_schedule(
    asset_id: int,
    save: bool = Query(False, description="If true, update asset.amortization_schedule"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate amortization schedule for a fixed-income manual asset. Optionally save to asset."""
    _check_trade_view(current_user)
    a = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.user_id == current_user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Manual asset not found")
    svc = AssetAmortizationService(db)
    sched = svc.generate_amortization_schedule(
        principal=a.purchase_price or Decimal(0),
        interest_rate=a.interest_rate or Decimal(0),
        maturity_date=a.maturity_date or date.today(),
        payment_frequency=a.payment_frequency or "at_maturity",
    )
    if save:
        a.amortization_schedule = sched
        db.commit()
    return {"schedule": sched, "saved": save}


@router.get("/upcoming-payments", response_model=List[Dict[str, Any]])
async def get_upcoming_payments(
    days_ahead: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List upcoming maturity and amortization payments for the user's manual assets."""
    _check_trade_view(current_user)
    svc = AssetAmortizationService(db)
    items = svc.check_upcoming_payments(days_ahead=days_ahead, user_id=current_user.id)
    return [
        {"asset_id": x["asset_id"], "due_date": x["due_date"], "days_until": x["days_until"], "type": x["type"], "amount": x["amount"], "message": x["message"]}
        for x in items
    ]


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def list_alerts(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List asset alerts for the user's manual assets."""
    _check_trade_view(current_user)
    q = db.query(AssetAlert).join(ManualAsset).filter(ManualAsset.user_id == current_user.id)
    if active_only:
        q = q.filter(AssetAlert.is_active == True)
    rows = q.order_by(AssetAlert.trigger_date.asc().nullslast()).all()
    return [
        {
            "id": al.id,
            "asset_id": al.asset_id,
            "alert_type": al.alert_type,
            "trigger_date": al.trigger_date.isoformat() if al.trigger_date else None,
            "trigger_price": float(al.trigger_price) if al.trigger_price is not None else None,
            "message": al.message,
            "is_active": al.is_active,
            "notified": al.notified,
            "notified_at": al.notified_at.isoformat() if al.notified_at else None,
            "created_at": al.created_at.isoformat() if al.created_at else None,
        }
        for al in rows
    ]


@router.post("/manual/{asset_id}/alerts", response_model=Dict[str, Any])
async def create_asset_alert(
    asset_id: int,
    body: AssetAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an alert for a manual asset."""
    _check_trade_view(current_user)
    a = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.user_id == current_user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Manual asset not found")
    al = AssetAlert(
        asset_id=asset_id,
        alert_type=body.alert_type,
        trigger_date=body.trigger_date,
        trigger_price=body.trigger_price,
        message=body.message,
        is_active=True,
        notified=False,
    )
    db.add(al)
    db.commit()
    db.refresh(al)
    return {
        "id": al.id,
        "asset_id": al.asset_id,
        "alert_type": al.alert_type,
        "trigger_date": al.trigger_date.isoformat() if al.trigger_date else None,
        "message": al.message,
    }
