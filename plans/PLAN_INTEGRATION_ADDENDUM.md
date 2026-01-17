# Plan Integration Addendum

## NEW: Stock Prediction Integration

**Reference**: `STOCK_PREDICTION_VENDORING_PLAN.md`

This addendum now includes integration with:
1. **Stock Prediction Service**: Amazon Chronos T5 model integration for multi-timeframe stock predictions
2. **Trading Dashboard Integration**: Stock prediction interface integrated into Trading Dashboard
3. **Credit Integration**: Stock predictions consume credits (daily, hourly, 15-minute types)
4. **Billing Integration**: Prediction costs tracked in billing dashboard (base + ensemble + stress test + GPU costs)
5. **Audit Integration**: Chronos T5 model calls logged with GPU usage, prediction parameters, and performance metrics

---

## NEW: Billing Dashboard Integration

**Reference**: `BILLING_DASHBOARD_PLAN.md`

This addendum now includes integration with:
1. **Billing Dashboard**: Permissioned billing dashboard with cost tracking per organization and role
2. **Cost Allocation**: Automatic cost allocation for subscriptions, usage, commissions, credits, and payments
3. **Billing Integration**: All features automatically track costs and integrate with billing system
4. **Stock Prediction Costs**: Stock prediction costs tracked by timeframe with ensemble, stress test, and GPU costs

---

## NEW: Enhanced Navigation & Chatbot Architecture

**Reference**: `ENHANCED_NAVIGATION_CHATBOT_PLAN.md`

This addendum now includes integration with:
1. **Sidebar Navigation System**: All features integrate with SidebarNavigation component
2. **Credits-Based Subscriptions**: Pro tier uses credits for pay-as-you-go features
3. **Multi-User Chatbots**: Screen-specific chatbots with isolated memory
4. **Cloud Production Infrastructure**: Database optimizations for scale

---

# Plan Integration Addendum (Original)
## Updates to Polymarket, Trading Dashboard, and DigiSign Plans for Unified Dashboard

**Status**: Integration Addendum  
**Last Updated**: 2024-12-XX

---

## Overview

This document provides integration updates for the three feature implementation plans to align with the unified dashboard architecture and Electron refactoring plan.

---

## Polymarket Integration Updates

### Changes Required

#### 1. Market Dashboard Component Location
**Original**: `client/src/apps/polymarket-nexus/MarketDashboard.tsx`  
**Updated**: `client/src/components/dashboard-tabs/MarketDashboard.tsx`

**Reason**: All dashboard tabs should be in a unified location for the UnifiedDashboard component.

#### 2. Integration with Unified Dashboard
**File**: `client/src/components/UnifiedDashboard.tsx` (UPDATE)

Add to dashboardTabs array:
```typescript
{
  id: 'polymarket',
  label: 'Polymarket',
  icon: <BarChart3 />,
  component: MarketDashboard,
  requiredPermission: PERMISSION_MARKET_VIEW,
  subscriptionTier: 'pro'  // Pro tier required
}
```

#### 3. Subscription Tier Enforcement
**File**: `app/api/polymarket_routes.py` (UPDATE)

Add subscription tier check to market creation endpoint:
```python
@router.post("/markets/create")
async def create_market(
    request: CreateMarketRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    # Check subscription tier
    tier = subscription_service.get_user_tier(current_user.id)
    if tier not in ['pro', 'premium', 'lifetime']:
        raise HTTPException(
            status_code=403,
            detail="Pro subscription required to create markets"
        )
    
    # ... rest of implementation
```

#### 4. Commission Integration
**File**: `app/services/polymarket_service.py` (UPDATE)

Add commission calculation when creating markets:
```python
from app.services.commission_service import CommissionService

# In create_market method:
commission_service = CommissionService(db)
commission = commission_service.apply_commission(
    transaction_id=f"market_{market_id}",
    transaction_type="market_creation",
    transaction_amount=Decimal(str(request.initial_liquidity or 0)),
    payer_id=creator_user_id,
    transaction_metadata={"market_id": market_id, "deal_id": deal_id}
)
```

---

## Trading Dashboard Integration Updates

### Changes Required

#### 1. Trading Dashboard Component Location
**Original**: `client/src/apps/trading-dashboard/TradingDashboard.tsx`  
**Updated**: `client/src/components/dashboard-tabs/TradingDashboard.tsx`

#### 2. Integration with Unified Dashboard
**File**: `client/src/components/UnifiedDashboard.tsx` (UPDATE)

Add to dashboardTabs array:
```typescript
{
  id: 'trading',
  label: 'Trading',
  icon: <TrendingUp />,
  component: TradingDashboard,
  requiredPermission: PERMISSION_TRADING_VIEW,
  subscriptionTier: 'pro'  // Pro tier required
}
```

#### 3. Portfolio Aggregation Tab
Add separate portfolio tab:
```typescript
{
  id: 'portfolio',
  label: 'Portfolio',
  icon: <PieChart />,
  component: PortfolioAggregationDashboard,
  requiredPermission: PERMISSION_PORTFOLIO_VIEW,
  subscriptionTier: 'free'  // Free tier can view basic portfolio
}
```

#### 4. Subscription Tier for Risk Analysis
**File**: `app/api/portfolio_routes.py` (UPDATE)

Add tier checks:
```python
@router.get("/risk-analysis")
async def get_risk_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    tier = subscription_service.get_user_tier(current_user.id)
    if tier not in ['pro', 'premium', 'lifetime']:
        raise HTTPException(
            status_code=403,
            detail="Pro subscription required for risk analysis"
        )
    
    # ... risk analysis implementation
```

#### 5. Commission Integration for Trades
**File**: `app/services/alpaca_service.py` (UPDATE)

Add commission calculation when executing trades:
```python
from app.services.commission_service import CommissionService

# In create_order method, after order execution:
commission_service = CommissionService(db)
commission = commission_service.apply_commission(
    transaction_id=order_id,
    transaction_type="trade_execution",
    transaction_amount=Decimal(str(order_data.get("notional") or order_data.get("qty", 0) * current_price)),
    payer_id=user_id,
    transaction_metadata={"symbol": symbol, "order_type": order_type}
)
```

#### 6. Verified Implementations Integration
**File**: `app/services/alpaca_service.py` (UPDATE)

Use verified implementations for Alpaca connection:
```python
from app.db.models import UserImplementationConnection, VerifiedImplementation

# In __init__ or connection method:
def get_user_alpaca_connection(self, user_id: int, db: Session):
    """Get user's Alpaca connection from verified implementations."""
    impl = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.name == "alpaca"
    ).first()
    
    if not impl:
        raise ValueError("Alpaca implementation not configured")
    
    connection = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == user_id,
        UserImplementationConnection.implementation_id == impl.id,
        UserImplementationConnection.is_active == True
    ).first()
    
    if not connection:
        raise ValueError("User has not connected Alpaca account")
    
    return connection.connection_data
```

---

## DigiSign Integration Updates

### Changes Required

#### 1. Signature Dashboard Component Location
**Original**: `client/src/components/MySignaturesWidget.tsx`  
**Updated**: `client/src/components/dashboard-tabs/SignatureDashboard.tsx`

#### 2. Integration with Unified Dashboard
**File**: `client/src/components/UnifiedDashboard.tsx` (UPDATE)

Add to dashboardTabs array:
```typescript
{
  id: 'signatures',
  label: 'Signatures',
  icon: <PenTool />,
  component: SignatureDashboard,
  requiredPermission: PERMISSION_SIGNATURE_VIEW,
  subscriptionTier: 'free'  // Free tier can sign documents
}
```

#### 3. Role-Based Views in Signature Dashboard
**File**: `client/src/components/dashboard-tabs/SignatureDashboard.tsx` (NEW)

Create component with role-based sections:
```typescript
export function SignatureDashboard() {
  const { user } = useAuth();
  const { hasPermission } = usePermissions();
  
  return (
    <div className="space-y-6">
      {/* For all users */}
      <MyPendingSignatures />
      
      {/* For Bankers and Law Officers */}
      {hasPermission(PERMISSION_SIGNATURE_COORDINATE) && (
        <SignatureCoordinationPanel />
      )}
      
      {/* For Auditors */}
      {hasPermission(PERMISSION_SIGNATURE_AUDIT) && (
        <SignatureAuditTrail />
      )}
    </div>
  );
}
```

#### 4. Commission Integration for Signature Services
**File**: `app/services/internal_signature_service.py` (UPDATE)

Add commission for signature coordination (if applicable):
```python
# Optional: Charge for signature coordination services
# This would be configurable in commission configs
if charge_for_coordination:
    commission_service = CommissionService(db)
    commission_service.apply_commission(
        transaction_id=f"signature_{signature_request_id}",
        transaction_type="signature_coordination",
        transaction_amount=Decimal("0"),  # Or fixed fee
        payer_id=coordinator_user_id,
        transaction_metadata={"document_id": document_id}
    )
```

---

## Common Integration Points

### 1. Subscription Tier Checks
All three features should check subscription tiers at API level:

**Pattern**:
```python
from app.services.subscription_service import SubscriptionService, get_subscription_service

@router.post("/feature-endpoint")
async def feature_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    tier = subscription_service.get_user_tier(current_user.id)
    required_tier = 'pro'  # or 'premium', 'lifetime'
    
    if tier not in [required_tier, 'premium', 'lifetime']:
        raise HTTPException(
            status_code=403,
            detail=f"{required_tier.capitalize()} subscription required"
        )
```

### 2. Commission Application
All transaction-generating features should apply commissions:

**Pattern**:
```python
from app.services.commission_service import CommissionService

commission_service = CommissionService(db)
commission_service.apply_commission(
    transaction_id=transaction_id,
    transaction_type="feature_specific_type",
    transaction_amount=amount,
    payer_id=user_id,
    transaction_metadata={...}
)
```

### 3. Verified Implementations
All external service integrations should use verified implementations:

**Pattern**:
```python
from app.db.models import UserImplementationConnection, VerifiedImplementation

def get_user_connection(user_id: int, implementation_name: str, db: Session):
    impl = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.name == implementation_name
    ).first()
    
    connection = db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == user_id,
        UserImplementationConnection.implementation_id == impl.id,
        UserImplementationConnection.is_active == True
    ).first()
    
    return connection.connection_data if connection else None
```

### 4. Permission Checks
All features should use permission system:

**Backend**:
```python
from app.core.permissions import has_permission

if not has_permission(current_user, PERMISSION_FEATURE_VIEW):
    raise HTTPException(403, "Insufficient permissions")
```

**Frontend**:
```typescript
import { usePermissions } from '@/hooks/usePermissions';

const { hasPermission } = usePermissions();

if (!hasPermission(PERMISSION_FEATURE_VIEW)) {
  return <UpgradePrompt />;
}
```

### 5. Billing Integration
All features that generate costs should integrate with the billing system:

**Pattern**:
```python
from app.services.billing_service import BillingService

# Costs are automatically tracked via:
# - SubscriptionUsage (for pay-as-you-go)
# - CommissionCharge (for commissions)
# - CreditTransaction (for credit usage)
# - PaymentEvent (for payment processing fees)

# Billing periods are automatically created and costs allocated
# Users can view their billing in the BillingDashboard component
```

**Frontend Integration**:
```typescript
// BillingDashboard is available as a tab in UnifiedDashboard
{
  id: 'billing',
  label: 'Billing',
  icon: <DollarSign />,
  component: BillingDashboard,
  requiredPermission: PERMISSION_BILLING_VIEW,  // Users can view their own, admins can view all
  subscriptionTier: 'free'  // All tiers can view billing
}
```

---

## Updated File Structure

```
client/src/
├── components/
│   ├── UnifiedDashboard.tsx          # Main unified dashboard
│   └── dashboard-tabs/
│       ├── OverviewTab.tsx            # Overview tab
│       ├── TradingDashboard.tsx       # Trading tab (from Trading plan)
│       ├── MarketDashboard.tsx        # Polymarket tab (from Polymarket plan)
│       ├── SignatureDashboard.tsx     # Signatures tab (from DigiSign plan)
│       ├── PortfolioDashboard.tsx      # Portfolio tab (from Trading plan)
│       ├── ComplianceDashboard.tsx    # Compliance tab (new)
│       ├── BillingDashboard.tsx       # Billing tab (from Billing plan)
│       └── ApplicationDashboard.tsx  # Applications tab (existing)
```

---

## Migration Checklist

### Polymarket Plan
- [ ] Move MarketDashboard to `dashboard-tabs/`
- [ ] Add to UnifiedDashboard tabs array
- [ ] Add subscription tier checks to API endpoints
- [ ] Add commission calculation for market creation
- [ ] Update permissions to use new permission constants

### Trading Dashboard Plan
- [ ] Move TradingDashboard to `dashboard-tabs/`
- [ ] Create PortfolioDashboard component
- [ ] Add both to UnifiedDashboard tabs array
- [ ] Add subscription tier checks for risk analysis
- [ ] Add commission calculation for trades
- [ ] Integrate verified implementations for Alpaca/Plaid

### DigiSign Plan
- [ ] Create SignatureDashboard component
- [ ] Add to UnifiedDashboard tabs array
- [ ] Implement role-based views within dashboard
- [ ] Add permission checks for coordination/audit features
- [ ] Optional: Add commission for coordination services

### Billing Dashboard Plan
- [ ] Create BillingDashboard component
- [ ] Add to UnifiedDashboard tabs array
- [ ] Integrate cost tracking with all features
- [ ] Add permission checks for billing access
- [ ] Ensure all cost-generating features create billing records

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0
