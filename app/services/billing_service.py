"""Billing service (Phase 10): periods, invoices, cost allocations."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import BillingPeriod, CostAllocation, Invoice

logger = logging.getLogger(__name__)


class BillingServiceError(Exception):
    pass


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_billing_period(
        self,
        period_type: str,
        period_start: datetime,
        period_end: datetime,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a billing period (admin/org_admin)."""
        p = BillingPeriod(
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            organization_id=organization_id,
            user_id=user_id,
            status="pending",
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p.to_dict()

    def get_billing_period(self, period_id: int) -> Optional[Dict[str, Any]]:
        """Get a billing period by id."""
        p = self.db.query(BillingPeriod).filter(BillingPeriod.id == period_id).first()
        return p.to_dict() if p else None

    def list_billing_periods(
        self,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List billing periods with optional filters."""
        q = self.db.query(BillingPeriod)
        if organization_id is not None:
            q = q.filter(BillingPeriod.organization_id == organization_id)
        if user_id is not None:
            q = q.filter(BillingPeriod.user_id == user_id)
        if status:
            q = q.filter(BillingPeriod.status == status)
        rows = q.order_by(BillingPeriod.period_end.desc()).offset(offset).limit(limit).all()
        return [r.to_dict() for r in rows]

    def create_invoice(
        self,
        billing_period_id: int,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        subtotal: Optional[Decimal] = None,
        tax: Optional[Decimal] = None,
        due_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create an invoice for a billing period."""
        period = self.db.query(BillingPeriod).filter(BillingPeriod.id == billing_period_id).first()
        if not period:
            raise BillingServiceError(f"Billing period {billing_period_id} not found")
        subtotal = subtotal or Decimal("0")
        tax = tax or Decimal("0")
        total = subtotal + tax
        # Generate invoice number: INV-YYYYMM-N
        year_month = datetime.utcnow().strftime("%Y%m")
        n = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.invoice_number.like(f"INV-{year_month}-%"))
            .scalar()
            or 0
        )
        invoice_number = f"INV-{year_month}-{n + 1:04d}"
        inv = Invoice(
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow(),
            due_date=due_date or period.period_end,
            organization_id=organization_id or period.organization_id,
            user_id=user_id or period.user_id,
            subtotal=subtotal,
            tax=tax,
            total=total,
            currency=period.currency,
            status="draft",
        )
        self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        period.invoice_id = inv.id
        period.status = "invoiced"
        self.db.commit()
        return inv.to_dict()

    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get an invoice by id."""
        inv = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        return inv.to_dict() if inv else None

    def list_invoices(
        self,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List invoices with optional filters."""
        q = self.db.query(Invoice)
        if organization_id is not None:
            q = q.filter(Invoice.organization_id == organization_id)
        if user_id is not None:
            q = q.filter(Invoice.user_id == user_id)
        if status:
            q = q.filter(Invoice.status == status)
        rows = q.order_by(Invoice.invoice_date.desc()).offset(offset).limit(limit).all()
        return [r.to_dict() for r in rows]

    def mark_invoice_paid(self, invoice_id: int, payment_event_id: Optional[int] = None) -> Dict[str, Any]:
        """Mark an invoice as paid."""
        inv = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise BillingServiceError(f"Invoice {invoice_id} not found")
        inv.status = "paid"
        inv.paid_at = datetime.utcnow()
        if payment_event_id is not None:
            inv.payment_event_id = payment_event_id
        self.db.commit()
        self.db.refresh(inv)
        return inv.to_dict()

    def add_cost_allocation(
        self,
        billing_period_id: int,
        cost_type: str,
        amount: Decimal,
        *,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_role: Optional[str] = None,
        feature: Optional[str] = None,
        allocation_method: str = "direct",
        allocation_percentage: Optional[Decimal] = None,
        source_transaction_id: Optional[str] = None,
        source_transaction_type: Optional[str] = None,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """Add a cost allocation row for a billing period."""
        c = CostAllocation(
            billing_period_id=billing_period_id,
            organization_id=organization_id,
            user_id=user_id,
            user_role=user_role,
            cost_type=cost_type,
            feature=feature,
            amount=amount,
            currency=currency,
            allocation_method=allocation_method,
            allocation_percentage=allocation_percentage,
            source_transaction_id=source_transaction_id,
            source_transaction_type=source_transaction_type,
        )
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c.to_dict()

    def get_cost_allocations(self, billing_period_id: int) -> List[Dict[str, Any]]:
        """Get all cost allocations for a billing period."""
        rows = (
            self.db.query(CostAllocation)
            .filter(CostAllocation.billing_period_id == billing_period_id)
            .order_by(CostAllocation.cost_type, CostAllocation.feature)
            .all()
        )
        return [r.to_dict() for r in rows]

    def aggregate_by_organization(self, period_id: int) -> List[Dict[str, Any]]:
        """Aggregate cost allocations by organization for a period."""
        rows = (
            self.db.query(
                CostAllocation.organization_id,
                func.sum(CostAllocation.amount).label("total"),
            )
            .filter(CostAllocation.billing_period_id == period_id)
            .group_by(CostAllocation.organization_id)
            .all()
        )
        return [
            {"organization_id": r.organization_id, "total": float(r.total) if r.total else 0}
            for r in rows
        ]

    def aggregate_by_role(self, period_id: int) -> List[Dict[str, Any]]:
        """Aggregate cost allocations by user role for a period."""
        rows = (
            self.db.query(
                CostAllocation.user_role,
                func.sum(CostAllocation.amount).label("total"),
            )
            .filter(CostAllocation.billing_period_id == period_id)
            .group_by(CostAllocation.user_role)
            .all()
        )
        return [
            {"user_role": r.user_role, "total": float(r.total) if r.total else 0}
            for r in rows
        ]

    def aggregate_costs_for_period(self, period_id: int) -> Dict[str, Any]:
        """Sum CostAllocation rows for the period and update BillingPeriod totals."""
        period = self.db.query(BillingPeriod).filter(BillingPeriod.id == period_id).first()
        if not period:
            raise BillingServiceError(f"Billing period {period_id} not found")
        rows = self.db.query(CostAllocation).filter(CostAllocation.billing_period_id == period_id).all()
        total_cost = sum(Decimal(str(r.amount or 0)) for r in rows)
        # Optionally break down by cost_type
        by_type: Dict[str, Decimal] = {}
        for r in rows:
            k = r.cost_type or "other"
            by_type[k] = by_type.get(k, Decimal("0")) + Decimal(str(r.amount or 0))
        period.total_cost = total_cost
        if "subscription" in by_type:
            period.subscription_cost = by_type["subscription"]
        if "usage" in by_type:
            period.usage_cost = by_type["usage"]
        if "credit" in by_type:
            period.credit_usage = by_type["credit"]
        if "payment" in by_type:
            period.payment_cost = by_type["payment"]
        if "commission" in by_type:
            period.commission_revenue = by_type["commission"]
        self.db.commit()
        self.db.refresh(period)
        return period.to_dict()
