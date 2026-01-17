# Permissioned Billing Dashboard Plan
## Complete Cost Tracking per Organization and Role

**Status**: Comprehensive Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 6-8 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan provides a **complete permissioned billing dashboard** that:
- Tracks costs per organization with detailed breakdowns
- Tracks costs per role within organizations
- Provides permissioned access (admins see all, org admins see their org, users see their own)
- Integrates with subscriptions, commissions, credits, and payment systems
- Shows billing history, usage analytics, invoices, and cost forecasts
- Supports multiple billing models (subscription, pay-as-you-go, credits, commissions)

---

## Current State Analysis

### ✅ Existing Models

**Payment Tracking**:
- `PaymentEvent` model (`app/db/models.py` lines 2389-2448)
  - Tracks payment_id, payment_type, amount, currency, payer_id, receiver_id
  - Links to deals, trades, notarizations
  - Payment status tracking

**Planned Models** (from other plans):
- `UserSubscription` - User subscription records
- `SubscriptionUsage` - Usage tracking for pay-as-you-go
- `CommissionConfig` - Commission configuration
- `CommissionCharge` - Commission charges applied
- `CreditBalance` - User credit balances
- `CreditTransaction` - Credit transactions
- `CreditPackage` - Credit packages
- `Organization` - Organization model with subscription_tier

**User Roles**:
- ADMIN, AUDITOR, BANKER, LAW_OFFICER, ACCOUNTANT, APPLICANT, TRADER, COMPLIANCE_OFFICER

### ❌ Missing

**Billing Models**:
- No `BillingPeriod` model
- No `Invoice` model
- No `CostAllocation` model (per org/role)
- No `BillingDashboard` UI component

**Cost Tracking**:
- No organization-level cost aggregation
- No role-level cost tracking
- No cost breakdown by feature/service
- No billing history views

---

## Project 1: Billing Database Models

### Activity 1.1: Billing Period & Invoice Models

**File**: `app/db/models.py` (UPDATE)

#### Task 1.1.1: Add Billing Models
**Lines**: ~3500-3800

**Subtasks**:
1. **Line 3500-3650**: Billing period and invoice models
   ```python
   class BillingPeriod(Base):
       """Billing period for organizations and users."""
       __tablename__ = "billing_periods"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Period identification
       period_type = Column(String(20), nullable=False)  # "monthly", "quarterly", "yearly", "custom"
       period_start = Column(DateTime, nullable=False, index=True)
       period_end = Column(DateTime, nullable=False, index=True)
       
       # Entity (organization or user)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
       
       # Billing summary
       total_cost = Column(Numeric(19, 4), default=0, nullable=False)
       subscription_cost = Column(Numeric(19, 4), default=0, nullable=False)  # Subscription fees
       usage_cost = Column(Numeric(19, 4), default=0, nullable=False)  # Pay-as-you-go usage
       commission_revenue = Column(Numeric(19, 4), default=0, nullable=False)  # Commissions earned
       credit_purchases = Column(Numeric(19, 4), default=0, nullable=False)  # Credits purchased
       credit_usage = Column(Numeric(19, 4), default=0, nullable=False)  # Credits used
       payment_cost = Column(Numeric(19, 4), default=0, nullable=False)  # Payment processing fees
       currency = Column(String(3), default="USD", nullable=False)
       
       # Status
       status = Column(String(20), default="pending", nullable=False, index=True)  # pending, invoiced, paid, overdue, cancelled
       invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
       
       # Metadata
       metadata = Column(JSONB, nullable=True)  # Additional billing data
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       organization = relationship("Organization", backref="billing_periods")
       user = relationship("User", backref="billing_periods")
       invoice = relationship("Invoice", backref="billing_periods")
       
       def to_dict(self):
           """Convert to dictionary."""
           return {
               "id": self.id,
               "period_type": self.period_type,
               "period_start": self.period_start.isoformat() if self.period_start else None,
               "period_end": self.period_end.isoformat() if self.period_end else None,
               "organization_id": self.organization_id,
               "user_id": self.user_id,
               "total_cost": float(self.total_cost) if self.total_cost else 0,
               "subscription_cost": float(self.subscription_cost) if self.subscription_cost else 0,
               "usage_cost": float(self.usage_cost) if self.usage_cost else 0,
               "commission_revenue": float(self.commission_revenue) if self.commission_revenue else 0,
               "credit_purchases": float(self.credit_purchases) if self.credit_purchases else 0,
               "credit_usage": float(self.credit_usage) if self.credit_usage else 0,
               "payment_cost": float(self.payment_cost) if self.payment_cost else 0,
               "currency": self.currency,
               "status": self.status,
               "invoice_id": self.invoice_id,
               "created_at": self.created_at.isoformat() if self.created_at else None,
               "updated_at": self.updated_at.isoformat() if self.updated_at else None
           }
   
   class Invoice(Base):
       """Invoice for billing periods."""
       __tablename__ = "invoices"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Invoice identification
       invoice_number = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "INV-2024-001"
       invoice_date = Column(DateTime, nullable=False, index=True)
       due_date = Column(DateTime, nullable=False, index=True)
       
       # Entity (organization or user)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
       
       # Amounts
       subtotal = Column(Numeric(19, 4), nullable=False)
       tax = Column(Numeric(19, 4), default=0, nullable=False)
       total = Column(Numeric(19, 4), nullable=False)
       currency = Column(String(3), default="USD", nullable=False)
       
       # Status
       status = Column(String(20), default="draft", nullable=False, index=True)  # draft, sent, paid, overdue, cancelled
       paid_at = Column(DateTime, nullable=True)
       payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
       
       # Line items (JSONB for flexibility)
       line_items = Column(JSONB, nullable=True)  # Array of invoice line items
       
       # Metadata
       notes = Column(Text, nullable=True)
       metadata = Column(JSONB, nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       organization = relationship("Organization", backref="invoices")
       user = relationship("User", backref="invoices")
       payment_event = relationship("PaymentEvent", foreign_keys=[payment_event_id])
       
       def to_dict(self):
           """Convert to dictionary."""
           return {
               "id": self.id,
               "invoice_number": self.invoice_number,
               "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
               "due_date": self.due_date.isoformat() if self.due_date else None,
               "organization_id": self.organization_id,
               "user_id": self.user_id,
               "subtotal": float(self.subtotal) if self.subtotal else 0,
               "tax": float(self.tax) if self.tax else 0,
               "total": float(self.total) if self.total else 0,
               "currency": self.currency,
               "status": self.status,
               "paid_at": self.paid_at.isoformat() if self.paid_at else None,
               "payment_event_id": self.payment_event_id,
               "line_items": self.line_items,
               "notes": self.notes,
               "created_at": self.created_at.isoformat() if self.created_at else None,
               "updated_at": self.updated_at.isoformat() if self.updated_at else None
           }
   
   class CostAllocation(Base):
       """Cost allocation per organization and role."""
       __tablename__ = "cost_allocations"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Billing period
       billing_period_id = Column(Integer, ForeignKey("billing_periods.id", ondelete="CASCADE"), nullable=False, index=True)
       
       # Entity allocation
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
       user_role = Column(String(50), nullable=True, index=True)  # Role for role-based allocation
       
       # Cost breakdown
       cost_type = Column(String(50), nullable=False, index=True)  # "subscription", "usage", "commission", "credit", "payment"
       feature = Column(String(100), nullable=True, index=True)  # "trade_execution", "market_creation", "risk_analysis", "stock_prediction_daily", etc.
       amount = Column(Numeric(19, 4), nullable=False)
       currency = Column(String(3), default="USD", nullable=False)
       
       # Allocation details
       allocation_method = Column(String(50), nullable=False)  # "direct", "proportional", "equal", "role_based"
       allocation_percentage = Column(Numeric(5, 2), nullable=True)  # Percentage if proportional
       
       # Source transaction
       source_transaction_id = Column(String(255), nullable=True, index=True)  # Trade ID, Deal ID, etc.
       source_transaction_type = Column(String(50), nullable=True)  # "trade", "deal", "market", etc.
       
       # Metadata
       metadata = Column(JSONB, nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       billing_period = relationship("BillingPeriod", backref="cost_allocations")
       organization = relationship("Organization", backref="cost_allocations")
       user = relationship("User", backref="cost_allocations")
       
       def to_dict(self):
           """Convert to dictionary."""
           return {
               "id": self.id,
               "billing_period_id": self.billing_period_id,
               "organization_id": self.organization_id,
               "user_id": self.user_id,
               "user_role": self.user_role,
               "cost_type": self.cost_type,
               "feature": self.feature,
               "amount": float(self.amount) if self.amount else 0,
               "currency": self.currency,
               "allocation_method": self.allocation_method,
               "allocation_percentage": float(self.allocation_percentage) if self.allocation_percentage else None,
               "source_transaction_id": self.source_transaction_id,
               "source_transaction_type": self.source_transaction_type,
               "created_at": self.created_at.isoformat() if self.created_at else None
           }
   ```

---

## Project 2: Billing Service

### Activity 2.1: Billing Service Implementation

**File**: `app/services/billing_service.py` (NEW)

#### Task 2.1.1: Create Billing Service
**Lines**: 1-600

**Subtasks**:
1. **Line 1-300**: Core billing service
   ```python
   from typing import Dict, Any, List, Optional
   from datetime import datetime, timedelta
   from decimal import Decimal
   from sqlalchemy.orm import Session
   from sqlalchemy import func, and_, or_
   import logging
   
   from app.db.models import (
       BillingPeriod, Invoice, CostAllocation, PaymentEvent,
       CommissionCharge, SubscriptionUsage, CreditTransaction,
       Organization, User, UserSubscription
   )
   
   logger = logging.getLogger(__name__)
   
   
   class BillingService:
       """Service for managing billing and cost tracking."""
       
       def __init__(self, db: Session):
           self.db = db
       
       def create_billing_period(
           self,
           organization_id: Optional[int] = None,
           user_id: Optional[int] = None,
           period_type: str = "monthly",
           period_start: Optional[datetime] = None,
           period_end: Optional[datetime] = None
       ) -> BillingPeriod:
           """Create a new billing period."""
           if not period_start:
               # Default to current month
               now = datetime.utcnow()
               period_start = datetime(now.year, now.month, 1)
           
           if not period_end:
               if period_type == "monthly":
                   # End of current month
                   if period_start.month == 12:
                       period_end = datetime(period_start.year + 1, 1, 1) - timedelta(days=1)
                   else:
                       period_end = datetime(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
               elif period_type == "quarterly":
                   # End of quarter
                   quarter_end_month = ((period_start.month - 1) // 3 + 1) * 3
                   if quarter_end_month == 12:
                       period_end = datetime(period_start.year + 1, 1, 1) - timedelta(days=1)
                   else:
                       period_end = datetime(period_start.year, quarter_end_month + 1, 1) - timedelta(days=1)
               elif period_type == "yearly":
                   period_end = datetime(period_start.year + 1, 1, 1) - timedelta(days=1)
           
           billing_period = BillingPeriod(
               period_type=period_type,
               period_start=period_start,
               period_end=period_end,
               organization_id=organization_id,
               user_id=user_id,
               status="pending"
           )
           
           self.db.add(billing_period)
           self.db.commit()
           self.db.refresh(billing_period)
           
           # Calculate costs for this period
           self._calculate_period_costs(billing_period)
           
           return billing_period
       
       def _calculate_period_costs(self, billing_period: BillingPeriod) -> None:
           """Calculate all costs for a billing period."""
           period_start = billing_period.period_start
           period_end = billing_period.period_end
           
           # Subscription costs
           subscription_cost = self._calculate_subscription_cost(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Usage costs (pay-as-you-go)
           usage_cost = self._calculate_usage_cost(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Commission revenue (for CreditNexus)
           commission_revenue = self._calculate_commission_revenue(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Credit purchases
           credit_purchases = self._calculate_credit_purchases(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Credit usage
           credit_usage = self._calculate_credit_usage(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Payment processing costs
           payment_cost = self._calculate_payment_cost(
               billing_period.organization_id,
               billing_period.user_id,
               period_start,
               period_end
           )
           
           # Update billing period
           billing_period.subscription_cost = subscription_cost
           billing_period.usage_cost = usage_cost
           billing_period.commission_revenue = commission_revenue
           billing_period.credit_purchases = credit_purchases
           billing_period.credit_usage = credit_usage
           billing_period.payment_cost = payment_cost
           billing_period.total_cost = (
               subscription_cost + usage_cost + payment_cost - commission_revenue
           )
           
           self.db.commit()
           
           # Create cost allocations
           self._create_cost_allocations(billing_period)
       
       def _calculate_subscription_cost(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate subscription costs for the period."""
           # Get active subscriptions
           if organization_id:
               # Organization-level subscription
               org = self.db.query(Organization).filter(Organization.id == organization_id).first()
               if org and org.subscription_tier:
                   # Calculate based on tier and period
                   tier_costs = {
                       "free": Decimal("0"),
                       "pro": Decimal("9.99"),
                       "premium": Decimal("29.99"),
                       "lifetime": Decimal("0"),  # One-time payment
                       "enterprise": Decimal("99.99")  # Organization-level, custom pricing available
                   }
                   base_cost = tier_costs.get(org.subscription_tier, Decimal("0"))
                   # Prorate if needed
                   days_in_period = (period_end - period_start).days + 1
                   return base_cost * Decimal(days_in_period) / Decimal(30)
           
           if user_id:
               # User-level subscription
               subscription = self.db.query(UserSubscription).filter(
                   UserSubscription.user_id == user_id,
                   UserSubscription.is_active == True,
                   or_(
                       UserSubscription.expires_at == None,
                       UserSubscription.expires_at >= period_start
                   )
               ).first()
               
               if subscription:
                   tier_costs = {
                       "free": Decimal("0"),
                       "pro": Decimal("9.99"),
                       "premium": Decimal("29.99"),
                       "lifetime": Decimal("0")  # One-time payment
                   }
                   base_cost = tier_costs.get(subscription.tier, Decimal("0"))
                   days_in_period = (period_end - period_start).days + 1
                   return base_cost * Decimal(days_in_period) / Decimal(30)
           
           return Decimal("0")
       
       def _calculate_usage_cost(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate pay-as-you-go usage costs."""
           # Get usage records for the period
           query = self.db.query(SubscriptionUsage).filter(
               SubscriptionUsage.billing_period_start >= period_start,
               SubscriptionUsage.billing_period_end <= period_end
           )
           
           if organization_id:
               # Get users in organization
               org_users = self.db.query(User.id).filter(User.organization_id == organization_id).all()
               user_ids = [u.id for u in org_users]
               query = query.filter(SubscriptionUsage.user_id.in_(user_ids))
           elif user_id:
               query = query.filter(SubscriptionUsage.user_id == user_id)
           
           # Calculate total usage cost
           # This would need feature pricing configuration
           total_cost = Decimal("0")
           usage_records = query.all()
           
           for usage in usage_records:
               # Feature pricing (example)
               feature_prices = {
                   "trade_execution": Decimal("0.10"),
                   "market_creation": Decimal("0.50"),
                   "risk_analysis": Decimal("0.20"),
                   "llm_query": Decimal("0.01"),
                   "stock_prediction_daily": Decimal("0.30"),  # Daily stock prediction (Chronos T5)
                   "stock_prediction_hourly": Decimal("0.45"),  # Hourly stock prediction
                   "stock_prediction_15min": Decimal("0.60"),  # 15-minute stock prediction
                   "stock_prediction_ensemble": Decimal("0.10"),  # Ensemble method additional cost
                   "stock_prediction_stress_test": Decimal("0.15"),  # Stress testing additional cost
                   "stock_prediction_gpu": Decimal("0.05")  # GPU compute cost per prediction
               }
               price_per_unit = feature_prices.get(usage.feature, Decimal("0.10"))
               total_cost += price_per_unit * Decimal(usage.usage_count)
           
           return total_cost
       
       def _calculate_commission_revenue(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate commission revenue (for CreditNexus)."""
           query = self.db.query(CommissionCharge).filter(
               CommissionCharge.created_at >= period_start,
               CommissionCharge.created_at <= period_end
           )
           
           if organization_id:
               # Get users in organization
               org_users = self.db.query(User.id).filter(User.organization_id == organization_id).all()
               user_ids = [u.id for u in org_users]
               query = query.filter(CommissionCharge.payer_id.in_(user_ids))
           elif user_id:
               query = query.filter(CommissionCharge.payer_id == user_id)
           
           total_revenue = self.db.query(func.sum(CommissionCharge.amount)).filter(
               CommissionCharge.id.in_([c.id for c in query.all()])
           ).scalar() or Decimal("0")
           
           return total_revenue
       
       def _calculate_credit_purchases(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate credit purchases."""
           query = self.db.query(CreditTransaction).filter(
               CreditTransaction.transaction_type == "purchase",
               CreditTransaction.created_at >= period_start,
               CreditTransaction.created_at <= period_end
           )
           
           if organization_id:
               org_users = self.db.query(User.id).filter(User.organization_id == organization_id).all()
               user_ids = [u.id for u in org_users]
               query = query.filter(CreditTransaction.user_id.in_(user_ids))
           elif user_id:
               query = query.filter(CreditTransaction.user_id == user_id)
           
           total_purchases = self.db.query(func.sum(CreditTransaction.amount)).filter(
               CreditTransaction.id.in_([t.id for t in query.all()])
           ).scalar() or Decimal("0")
           
           return total_purchases
       
       def _calculate_credit_usage(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate credit usage."""
           query = self.db.query(CreditTransaction).filter(
               CreditTransaction.transaction_type == "spend",
               CreditTransaction.created_at >= period_start,
               CreditTransaction.created_at <= period_end
           )
           
           if organization_id:
               org_users = self.db.query(User.id).filter(User.organization_id == organization_id).all()
               user_ids = [u.id for u in org_users]
               query = query.filter(CreditTransaction.user_id.in_(user_ids))
           elif user_id:
               query = query.filter(CreditTransaction.user_id == user_id)
           
           total_usage = self.db.query(func.sum(CreditTransaction.amount)).filter(
               CreditTransaction.id.in_([t.id for t in query.all()])
           ).scalar() or Decimal("0")
           
           return abs(total_usage)  # Usage is negative, so take absolute value
       
       def _calculate_payment_cost(
           self,
           organization_id: Optional[int],
           user_id: Optional[int],
           period_start: datetime,
           period_end: datetime
       ) -> Decimal:
           """Calculate payment processing costs."""
           # Payment processing fees (e.g., 2.9% + $0.30 per transaction)
           query = self.db.query(PaymentEvent).filter(
               PaymentEvent.created_at >= period_start,
               PaymentEvent.created_at <= period_end,
               PaymentEvent.payment_status == "paid"
           )
           
           if organization_id:
               org_users = self.db.query(User.id).filter(User.organization_id == organization_id).all()
               user_ids = [u.id for u in org_users]
               query = query.filter(
                   or_(
                       PaymentEvent.payer_id.in_(user_ids),
                       PaymentEvent.receiver_id.in_(user_ids)
                   )
               )
           elif user_id:
               query = query.filter(
                   or_(
                       PaymentEvent.payer_id == user_id,
                       PaymentEvent.receiver_id == user_id
                   )
               )
           
           total_cost = Decimal("0")
           payment_events = query.all()
           
           for payment in payment_events:
               # Payment processing fee: 2.9% + $0.30
               fee = payment.amount * Decimal("0.029") + Decimal("0.30")
               total_cost += fee
           
           return total_cost
       
       def _create_cost_allocations(self, billing_period: BillingPeriod) -> None:
           """Create cost allocations for the billing period."""
           # Allocate costs by organization and role
           if billing_period.organization_id:
               # Get all users in organization
               org_users = self.db.query(User).filter(
                   User.organization_id == billing_period.organization_id
               ).all()
               
               # Allocate costs by role
               role_costs = {}
               for user in org_users:
                   role = user.role
                   if role not in role_costs:
                       role_costs[role] = {
                           "users": [],
                           "total_cost": Decimal("0")
                       }
                   role_costs[role]["users"].append(user.id)
               
               # Allocate subscription cost equally per role
               if billing_period.subscription_cost > 0:
                   roles_count = len(role_costs)
                   if roles_count > 0:
                       cost_per_role = billing_period.subscription_cost / Decimal(roles_count)
                       for role, data in role_costs.items():
                           allocation = CostAllocation(
                               billing_period_id=billing_period.id,
                               organization_id=billing_period.organization_id,
                               user_role=role,
                               cost_type="subscription",
                               amount=cost_per_role,
                               currency=billing_period.currency,
                               allocation_method="equal",
                               allocation_percentage=100.0 / roles_count
                           )
                           self.db.add(allocation)
               
               # Allocate usage costs proportionally by user
               # (This would need more detailed tracking)
               
           self.db.commit()
       
       def get_organization_costs(
           self,
           organization_id: int,
           start_date: Optional[datetime] = None,
           end_date: Optional[datetime] = None
       ) -> Dict[str, Any]:
           """Get cost summary for an organization."""
           query = self.db.query(BillingPeriod).filter(
               BillingPeriod.organization_id == organization_id
           )
           
           if start_date:
               query = query.filter(BillingPeriod.period_start >= start_date)
           if end_date:
               query = query.filter(BillingPeriod.period_end <= end_date)
           
           periods = query.all()
           
           total_cost = sum(p.total_cost for p in periods)
           total_subscription = sum(p.subscription_cost for p in periods)
           total_usage = sum(p.usage_cost for p in periods)
           total_commission = sum(p.commission_revenue for p in periods)
           total_credits = sum(p.credit_purchases for p in periods)
           
           # Get cost breakdown by role
           role_costs = self._get_role_costs(organization_id, start_date, end_date)
           
           return {
               "organization_id": organization_id,
               "periods": [p.to_dict() for p in periods],
               "totals": {
                   "total_cost": float(total_cost),
                   "subscription_cost": float(total_subscription),
                   "usage_cost": float(total_usage),
                   "commission_revenue": float(total_commission),
                   "credit_purchases": float(total_credits)
               },
               "role_breakdown": role_costs
           }
       
       def _get_role_costs(
           self,
           organization_id: int,
           start_date: Optional[datetime],
           end_date: Optional[datetime]
       ) -> Dict[str, Any]:
           """Get cost breakdown by role."""
           query = self.db.query(CostAllocation).join(BillingPeriod).filter(
               CostAllocation.organization_id == organization_id
           )
           
           if start_date:
               query = query.filter(BillingPeriod.period_start >= start_date)
           if end_date:
               query = query.filter(BillingPeriod.period_end <= end_date)
           
           allocations = query.all()
           
           role_costs = {}
           for allocation in allocations:
               role = allocation.user_role or "unknown"
               if role not in role_costs:
                   role_costs[role] = {
                       "total_cost": Decimal("0"),
                       "subscription_cost": Decimal("0"),
                       "usage_cost": Decimal("0"),
                       "credit_cost": Decimal("0")
                   }
               
               role_costs[role]["total_cost"] += allocation.amount
               if allocation.cost_type == "subscription":
                   role_costs[role]["subscription_cost"] += allocation.amount
               elif allocation.cost_type == "usage":
                   role_costs[role]["usage_cost"] += allocation.amount
               elif allocation.cost_type == "credit":
                   role_costs[role]["credit_cost"] += allocation.amount
           
           # Convert to float for JSON serialization
           return {
               role: {
                   k: float(v) if isinstance(v, Decimal) else v
                   for k, v in costs.items()
               }
               for role, costs in role_costs.items()
           }
   ```

---

## Project 3: Billing Dashboard UI

### Activity 3.1: Billing Dashboard Component

**File**: `client/src/components/dashboard-tabs/BillingDashboard.tsx` (NEW)

#### Task 3.1.1: Create Billing Dashboard
**Lines**: 1-1000

**Subtasks**:
1. **Line 1-500**: Main dashboard component
   ```typescript
   import { useState, useEffect } from 'react';
   import { DollarSign, TrendingUp, Users, Building2, Shield, Download } from 'lucide-react';
   import { useAuth } from '@/context/AuthContext';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Card } from '@/components/ui/card';
   import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
   import { Button } from '@/components/ui/button';
   import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
   import { BillingOverview } from '@/components/billing/BillingOverview';
   import { OrganizationCosts } from '@/components/billing/OrganizationCosts';
   import { RoleCosts } from '@/components/billing/RoleCosts';
   import { BillingHistory } from '@/components/billing/BillingHistory';
   import { InvoicesList } from '@/components/billing/InvoicesList';
   
   interface BillingSummary {
     total_cost: number;
     subscription_cost: number;
     usage_cost: number;
     commission_revenue: number;
     credit_purchases: number;
     currency: string;
   }
   
   export function BillingDashboard() {
     const { user } = useAuth();
     const [loading, setLoading] = useState(false);
     const [summary, setSummary] = useState<BillingSummary | null>(null);
     const [selectedPeriod, setSelectedPeriod] = useState<string>('current_month');
     const [selectedOrganization, setSelectedOrganization] = useState<number | null>(null);
     const [permissions, setPermissions] = useState({
       can_view_all: false,
       can_view_organization: false,
       can_view_own: true
     });
     
     useEffect(() => {
       checkPermissions();
       loadBillingData();
     }, [user, selectedPeriod, selectedOrganization]);
     
     const checkPermissions = () => {
       if (!user) return;
       
       // Admin can view all
       if (user.role === 'admin') {
         setPermissions({
           can_view_all: true,
           can_view_organization: true,
           can_view_own: true
         });
       } else if (user.organization_id) {
         // Organization members can view their org
         setPermissions({
           can_view_all: false,
           can_view_organization: true,
           can_view_own: true
         });
         setSelectedOrganization(user.organization_id);
       } else {
         // Users can only view their own
         setPermissions({
           can_view_all: false,
           can_view_organization: false,
           can_view_own: true
         });
       }
     };
     
     const loadBillingData = async () => {
       setLoading(true);
       try {
         let url = '/api/billing/summary';
         const params = new URLSearchParams();
         
         if (selectedPeriod) {
           params.append('period', selectedPeriod);
         }
         
         if (selectedOrganization && permissions.can_view_organization) {
           params.append('organization_id', selectedOrganization.toString());
         } else if (!permissions.can_view_all) {
           params.append('user_id', user?.id?.toString() || '');
         }
         
         if (params.toString()) {
           url += '?' + params.toString();
         }
         
         const response = await fetchWithAuth(url);
         if (response.ok) {
           const data = await response.json();
           setSummary(data.summary);
         }
       } catch (error) {
         console.error('Failed to load billing data:', error);
       } finally {
         setLoading(false);
       }
     };
     
     return (
       <div className="space-y-6">
         <div className="flex items-center justify-between">
           <div>
             <h2 className="text-2xl font-semibold text-slate-100 mb-2">
               Billing Dashboard
             </h2>
             <p className="text-slate-400">
               Track costs per organization and role
             </p>
           </div>
           <div className="flex items-center gap-2">
             <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
               <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
                 <SelectValue />
               </SelectTrigger>
               <SelectContent>
                 <SelectItem value="current_month">Current Month</SelectItem>
                 <SelectItem value="last_month">Last Month</SelectItem>
                 <SelectItem value="current_quarter">Current Quarter</SelectItem>
                 <SelectItem value="last_quarter">Last Quarter</SelectItem>
                 <SelectItem value="current_year">Current Year</SelectItem>
                 <SelectItem value="custom">Custom Range</SelectItem>
               </SelectContent>
             </Select>
             {permissions.can_view_all && (
               <Select
                 value={selectedOrganization?.toString() || 'all'}
                 onValueChange={(v) => setSelectedOrganization(v === 'all' ? null : parseInt(v))}
               >
                 <SelectTrigger className="w-48 bg-slate-900 border-slate-700">
                   <SelectValue placeholder="All Organizations" />
                 </SelectTrigger>
                 <SelectContent>
                   <SelectItem value="all">All Organizations</SelectItem>
                   {/* Organization options loaded from API */}
                 </SelectContent>
               </Select>
             )}
             <Button variant="outline" onClick={() => loadBillingData()}>
               <Download className="h-4 w-4 mr-2" />
               Export
             </Button>
           </div>
         </div>
         
         {loading ? (
           <div className="text-center py-8 text-slate-400">Loading billing data...</div>
         ) : (
           <Tabs defaultValue="overview">
             <TabsList className="grid w-full grid-cols-5">
               <TabsTrigger value="overview">Overview</TabsTrigger>
               <TabsTrigger value="organization">Organization</TabsTrigger>
               <TabsTrigger value="roles">Roles</TabsTrigger>
               <TabsTrigger value="history">History</TabsTrigger>
               <TabsTrigger value="invoices">Invoices</TabsTrigger>
             </TabsList>
             
             <TabsContent value="overview" className="space-y-4">
               <BillingOverview summary={summary} />
             </TabsContent>
             
             <TabsContent value="organization" className="space-y-4">
               {permissions.can_view_organization || permissions.can_view_all ? (
                 <OrganizationCosts
                   organizationId={selectedOrganization || user?.organization_id}
                   period={selectedPeriod}
                 />
               ) : (
                 <div className="text-center py-8 text-slate-400">
                   You don't have permission to view organization costs.
                 </div>
               )}
             </TabsContent>
             
             <TabsContent value="roles" className="space-y-4">
               {permissions.can_view_organization || permissions.can_view_all ? (
                 <RoleCosts
                   organizationId={selectedOrganization || user?.organization_id}
                   period={selectedPeriod}
                 />
               ) : (
                 <div className="text-center py-8 text-slate-400">
                   You don't have permission to view role costs.
                 </div>
               )}
             </TabsContent>
             
             <TabsContent value="history" className="space-y-4">
               <BillingHistory
                 organizationId={selectedOrganization || user?.organization_id}
                 userId={permissions.can_view_own ? user?.id : null}
                 period={selectedPeriod}
               />
             </TabsContent>
             
             <TabsContent value="invoices" className="space-y-4">
               <InvoicesList
                 organizationId={selectedOrganization || user?.organization_id}
                 userId={permissions.can_view_own ? user?.id : null}
               />
             </TabsContent>
           </Tabs>
         )}
       </div>
     );
   }
   ```

---

## Project 4: Billing API Endpoints

### Activity 4.1: Billing API Routes

**File**: `app/api/billing_routes.py` (NEW)

#### Task 4.1.1: Create Billing Endpoints
**Lines**: 1-500

**Subtasks**:
1. **Line 1-500**: Billing API endpoints
   ```python
   from fastapi import APIRouter, Depends, HTTPException, status, Query
   from sqlalchemy.orm import Session
   from typing import Optional
   from datetime import datetime
   from pydantic import BaseModel
   
   from app.db import get_db
   from app.auth.jwt_auth import require_auth
   from app.db.models import User, UserRole, Organization
   from app.services.billing_service import BillingService
   
   router = APIRouter(prefix="/api/billing", tags=["billing"])
   
   
   @router.get("/summary")
   async def get_billing_summary(
       period: Optional[str] = Query(None, description="Period: current_month, last_month, etc."),
       organization_id: Optional[int] = Query(None),
       user_id: Optional[int] = Query(None),
       db: Session = Depends(get_db),
       current_user: User = Depends(require_auth)
   ):
       """Get billing summary with permission checks."""
       # Permission checks
       if current_user.role != UserRole.ADMIN.value:
           if organization_id and organization_id != current_user.organization_id:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail="You can only view billing for your own organization"
               )
           if user_id and user_id != current_user.id:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail="You can only view your own billing"
               )
       
       service = BillingService(db)
       
       # Calculate period dates
       start_date, end_date = _get_period_dates(period)
       
       if organization_id:
           summary = service.get_organization_costs(organization_id, start_date, end_date)
       elif user_id:
           summary = service.get_user_costs(user_id, start_date, end_date)
       else:
           # Admin view: all organizations
           if current_user.role != UserRole.ADMIN.value:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail="Only administrators can view all billing"
               )
           summary = service.get_all_organization_costs(start_date, end_date)
       
       return {
           "status": "success",
           "summary": summary,
           "period": period,
           "start_date": start_date.isoformat() if start_date else None,
           "end_date": end_date.isoformat() if end_date else None
       }
   
   
   @router.get("/organization/{organization_id}/costs")
   async def get_organization_costs(
       organization_id: int,
       period: Optional[str] = Query(None),
       db: Session = Depends(get_db),
       current_user: User = Depends(require_auth)
   ):
       """Get costs for a specific organization."""
       # Permission check
       if current_user.role != UserRole.ADMIN.value:
           if current_user.organization_id != organization_id:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail="You can only view costs for your own organization"
               )
       
       service = BillingService(db)
       start_date, end_date = _get_period_dates(period)
       costs = service.get_organization_costs(organization_id, start_date, end_date)
       
       return {
           "status": "success",
           "organization_id": organization_id,
           "costs": costs
       }
   
   
   @router.get("/organization/{organization_id}/role-costs")
   async def get_role_costs(
       organization_id: int,
       period: Optional[str] = Query(None),
       db: Session = Depends(get_db),
       current_user: User = Depends(require_auth)
   ):
       """Get cost breakdown by role for an organization."""
       # Permission check
       if current_user.role != UserRole.ADMIN.value:
           if current_user.organization_id != organization_id:
               raise HTTPException(
                   status_code=status.HTTP_403_FORBIDDEN,
                   detail="You can only view role costs for your own organization"
               )
       
       service = BillingService(db)
       start_date, end_date = _get_period_dates(period)
       role_costs = service._get_role_costs(organization_id, start_date, end_date)
       
       return {
           "status": "success",
           "organization_id": organization_id,
           "role_costs": role_costs
       }
   
   
   def _get_period_dates(period: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
       """Get start and end dates for a period."""
       if not period:
           return None, None
       
       now = datetime.utcnow()
       
       if period == "current_month":
           start = datetime(now.year, now.month, 1)
           if now.month == 12:
               end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
           else:
               end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
       elif period == "last_month":
           if now.month == 1:
               start = datetime(now.year - 1, 12, 1)
               end = datetime(now.year, 1, 1) - timedelta(days=1)
           else:
               start = datetime(now.year, now.month - 1, 1)
               end = datetime(now.year, now.month, 1) - timedelta(days=1)
       # ... other period calculations
       else:
           return None, None
       
       return start, end
   ```

---

## Implementation Checklist

### Phase 1: Database Models (Week 1)
- [ ] Create BillingPeriod model
- [ ] Create Invoice model
- [ ] Create CostAllocation model
- [ ] Create Alembic migration
- [ ] Add indexes for performance

### Phase 2: Billing Service (Week 2-3)
- [ ] Create BillingService class
- [ ] Implement cost calculation methods
- [ ] Implement cost allocation logic
- [ ] Add role-based cost tracking
- [ ] Test cost calculations

### Phase 3: Billing API (Week 4)
- [ ] Create billing API endpoints
- [ ] Add permission checks
- [ ] Add period filtering
- [ ] Test API endpoints

### Phase 4: Billing Dashboard UI (Week 5-6)
- [ ] Create BillingDashboard component
- [ ] Create BillingOverview component
- [ ] Create OrganizationCosts component
- [ ] Create RoleCosts component
- [ ] Create BillingHistory component
- [ ] Create InvoicesList component
- [ ] Add charts and visualizations

### Phase 5: Integration & Testing (Week 7-8)
- [ ] Integrate with subscription system
- [ ] Integrate with commission system
- [ ] Integrate with credits system
- [ ] Add export functionality
- [ ] Test permissioned access
- [ ] Performance optimization

---

## Key Design Decisions

### 1. Permission Model
- **Admin**: Can view all organizations and all costs
- **Organization Admin**: Can view their organization's costs and role breakdowns
- **Organization Members**: Can view their organization's summary (not detailed breakdowns)
- **Individual Users**: Can only view their own costs

### 2. Cost Allocation Methods
- **Direct**: Direct assignment to user/organization
- **Proportional**: Allocated based on usage percentage
- **Equal**: Split equally among roles/users
- **Role-Based**: Allocated based on role (e.g., traders use more resources)

### 3. Cost Types Tracked
- **Subscription**: Monthly/yearly subscription fees
- **Usage**: Pay-as-you-go usage costs
- **Commission**: Commissions earned (revenue for CreditNexus)
- **Credit**: Credit purchases and usage
- **Payment**: Payment processing fees
- **Stock Predictions**: Stock prediction costs by timeframe (daily, hourly, 15-minute)
  - Base prediction cost per timeframe
  - Ensemble method additional cost
  - Stress testing additional cost
  - GPU compute costs
  - See `STOCK_PREDICTION_VENDORING_PLAN.md` for detailed cost structure

### 4. Billing Periods
- **Monthly**: Default billing period
- **Quarterly**: For enterprise customers
- **Yearly**: For annual subscriptions
- **Custom**: For special arrangements

---

## Success Criteria

1. ✅ Complete cost tracking per organization
2. ✅ Complete cost tracking per role
3. ✅ Permissioned access enforced
4. ✅ Integration with all billing systems
5. ✅ Billing dashboard with visualizations
6. ✅ Invoice generation and management
7. ✅ Export functionality
8. ✅ Performance optimized for large datasets

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
