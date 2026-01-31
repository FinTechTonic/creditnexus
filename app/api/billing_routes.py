"""
Billing API (Phase 10): periods, invoices, cost allocations.

- GET/POST /api/billing/periods
- GET /api/billing/periods/{id}
- GET/POST /api/billing/periods/{id}/cost-allocations
- GET /api/billing/periods/{id}/aggregate-by-organization
- GET /api/billing/periods/{id}/aggregate-by-role
- POST /api/billing/periods/{id}/aggregate
- POST /api/billing/invoices (create from period)
- GET /api/billing/invoices
- GET /api/billing/invoices/{id}
- POST /api/billing/invoices/{id}/mark-paid
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import User, UserRole
from app.services.billing_service import BillingService, BillingServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _is_admin(user: User) -> bool:
    return getattr(user, "role", None) == UserRole.ADMIN.value


def _scope_filters(user: User) -> Dict[str, Any]:
    """Return filters for list endpoints: non-admin sees only own user_id and org."""
    if _is_admin(user):
        return {}
    filters: Dict[str, Any] = {}
    # Non-admin: allow listing by user_id or organization_id (OR logic in service)
    filters["user_id"] = user.id
    filters["organization_id"] = getattr(user, "organization_id", None)
    return filters


# --- Request/response schemas ---


class CreateBillingPeriodBody(BaseModel):
    period_type: str = Field(..., min_length=1)
    period_start: datetime
    period_end: datetime
    organization_id: Optional[int] = None
    user_id: Optional[int] = None


class CreateInvoiceBody(BaseModel):
    billing_period_id: int
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    due_date: Optional[datetime] = None


class AddCostAllocationBody(BaseModel):
    cost_type: str = Field(..., min_length=1)
    amount: Decimal = Field(..., ge=0)
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    feature: Optional[str] = None
    allocation_method: str = "direct"
    allocation_percentage: Optional[Decimal] = None
    source_transaction_id: Optional[str] = None
    source_transaction_type: Optional[str] = None
    currency: str = "USD"


class MarkInvoicePaidBody(BaseModel):
    payment_event_id: Optional[int] = None


# --- Periods ---


@router.get("/periods", response_model=List[Dict[str, Any]])
def list_billing_periods(
    organization_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List billing periods. Non-admin see only their user_id or organization_id."""
    svc = BillingService(db)
    if not _is_admin(current_user):
        organization_id = organization_id or getattr(current_user, "organization_id", None)
        user_id = user_id or current_user.id
    return svc.list_billing_periods(
        organization_id=organization_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/periods", response_model=Dict[str, Any], status_code=201)
def create_billing_period(
    body: CreateBillingPeriodBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a billing period (admin/org_admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin required to create billing periods")
    svc = BillingService(db)
    try:
        return svc.create_billing_period(
            period_type=body.period_type,
            period_start=body.period_start,
            period_end=body.period_end,
            organization_id=body.organization_id,
            user_id=body.user_id,
        )
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/periods/{period_id}", response_model=Dict[str, Any])
def get_billing_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a billing period by id. Non-admin only if period belongs to user or org."""
    svc = BillingService(db)
    period = svc.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    if not _is_admin(current_user):
        if period.get("user_id") != current_user.id and period.get("organization_id") != getattr(
            current_user, "organization_id", None
        ):
            raise HTTPException(status_code=403, detail="Not allowed to view this period")
    return period


@router.get("/periods/{period_id}/cost-allocations", response_model=List[Dict[str, Any]])
def get_cost_allocations(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get cost allocations for a billing period."""
    svc = BillingService(db)
    period = svc.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    if not _is_admin(current_user):
        if period.get("user_id") != current_user.id and period.get("organization_id") != getattr(
            current_user, "organization_id", None
        ):
            raise HTTPException(status_code=403, detail="Not allowed to view this period")
    return svc.get_cost_allocations(period_id)


@router.post("/periods/{period_id}/cost-allocations", response_model=Dict[str, Any], status_code=201)
def add_cost_allocation(
    period_id: int,
    body: AddCostAllocationBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a cost allocation to a billing period (admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin required to add cost allocations")
    svc = BillingService(db)
    period = svc.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    try:
        return svc.add_cost_allocation(
            billing_period_id=period_id,
            cost_type=body.cost_type,
            amount=body.amount,
            organization_id=body.organization_id,
            user_id=body.user_id,
            user_role=body.user_role,
            feature=body.feature,
            allocation_method=body.allocation_method,
            allocation_percentage=body.allocation_percentage,
            source_transaction_id=body.source_transaction_id,
            source_transaction_type=body.source_transaction_type,
            currency=body.currency,
        )
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/periods/{period_id}/aggregate-by-organization", response_model=List[Dict[str, Any]])
def aggregate_by_organization(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate cost allocations by organization for a period."""
    svc = BillingService(db)
    period = svc.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    if not _is_admin(current_user):
        if period.get("user_id") != current_user.id and period.get("organization_id") != getattr(
            current_user, "organization_id", None
        ):
            raise HTTPException(status_code=403, detail="Not allowed to view this period")
    return svc.aggregate_by_organization(period_id)


@router.get("/periods/{period_id}/aggregate-by-role", response_model=List[Dict[str, Any]])
def aggregate_by_role(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate cost allocations by user role for a period."""
    svc = BillingService(db)
    period = svc.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    if not _is_admin(current_user):
        if period.get("user_id") != current_user.id and period.get("organization_id") != getattr(
            current_user, "organization_id", None
        ):
            raise HTTPException(status_code=403, detail="Not allowed to view this period")
    return svc.aggregate_by_role(period_id)


@router.post("/periods/{period_id}/aggregate", response_model=Dict[str, Any])
def aggregate_costs_for_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sum cost allocations for the period and update period totals (admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin required to aggregate period costs")
    svc = BillingService(db)
    try:
        return svc.aggregate_costs_for_period(period_id)
    except BillingServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Invoices ---


@router.post("/invoices", response_model=Dict[str, Any], status_code=201)
def create_invoice(
    body: CreateInvoiceBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an invoice for a billing period (admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin required to create invoices")
    svc = BillingService(db)
    try:
        return svc.create_invoice(
            billing_period_id=body.billing_period_id,
            organization_id=body.organization_id,
            user_id=body.user_id,
            subtotal=body.subtotal,
            tax=body.tax,
            due_date=body.due_date,
        )
    except BillingServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices", response_model=List[Dict[str, Any]])
def list_invoices(
    organization_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List invoices. Non-admin see only their user_id or organization_id."""
    svc = BillingService(db)
    if not _is_admin(current_user):
        organization_id = organization_id or getattr(current_user, "organization_id", None)
        user_id = user_id or current_user.id
    return svc.list_invoices(
        organization_id=organization_id,
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/invoices/{invoice_id}", response_model=Dict[str, Any])
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an invoice by id. Non-admin only if invoice belongs to user or org."""
    svc = BillingService(db)
    inv = svc.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not _is_admin(current_user):
        if inv.get("user_id") != current_user.id and inv.get("organization_id") != getattr(
            current_user, "organization_id", None
        ):
            raise HTTPException(status_code=403, detail="Not allowed to view this invoice")
    return inv


@router.post("/invoices/{invoice_id}/mark-paid", response_model=Dict[str, Any])
def mark_invoice_paid(
    invoice_id: int,
    body: Optional[MarkInvoicePaidBody] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an invoice as paid (admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin required to mark invoices paid")
    svc = BillingService(db)
    try:
        return svc.mark_invoice_paid(
            invoice_id=invoice_id,
            payment_event_id=body.payment_event_id if body else None,
        )
    except BillingServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
