# CreditNexus Refactoring Quick Reference
## Developer Quick Start Guide

**Last Updated**: 2024-12-XX

---

## Plan Documents

1. **`MASTER_IMPLEMENTATION_PLAN.md`** - Start here for overview
2. **`ELECTRON_REFACTORING_PLAN.md`** - Main refactoring plan
3. **`PLAN_INTEGRATION_ADDENDUM.md`** - Feature integration updates
4. **`POLYMARKET_INTEGRATION_PLAN.md`** - Polymarket feature plan
5. **`TRADING_DASHBOARD_IMPLEMENTATION_PLAN.md`** - Trading feature plan
6. **`DIGISIGN_IMPLEMENTATION_PLAN.md`** - DigiSign feature plan

---

## Key Concepts

### Unified Dashboard
- Single dashboard component replacing multiple app views
- Tabs filtered by permissions and subscription tier
- Location: `client/src/components/UnifiedDashboard.tsx`

### Subscription Tiers
- **Free**: Basic features
- **Pro**: Pay-as-you-go, trading, markets
- **Premium**: All Pro + advanced features
- **Lifetime**: One-time payment, all features

### Verified Implementations
- External service connections (Alpaca, Plaid, Polymarket)
- Selected during signup
- Stored in `UserImplementationConnection`

### Commissions
- Configurable per transaction type
- Automatic calculation and application
- Stored in `CommissionCharge` table

---

## File Locations

### Electron
- `electron/main.js` - Main process
- `electron/preload.js` - Preload script
- `electron-builder.config.js` - Build config

### Dashboard Components
- `client/src/components/UnifiedDashboard.tsx` - Main dashboard
- `client/src/components/dashboard-tabs/` - Tab components

### Backend Services
- `app/services/subscription_service.py` - Subscription management
- `app/services/commission_service.py` - Commission calculation
- `app/services/polymarket_service.py` - Polymarket integration
- `app/services/alpaca_service.py` - Trading integration
- `app/services/internal_signature_service.py` - Signature service

### Database Models
- `app/db/models.py` - All models (see new models section)

---

## Common Patterns

### Subscription Tier Check
```python
tier = subscription_service.get_user_tier(current_user.id)
if tier not in ['pro', 'premium', 'lifetime']:
    raise HTTPException(403, "Pro subscription required")
```

### Commission Application
```python
commission_service.apply_commission(
    transaction_id=transaction_id,
    transaction_type="trade_execution",
    transaction_amount=amount,
    payer_id=user_id,
    transaction_metadata={...}
)
```

### Permission Check
```python
if not has_permission(current_user, PERMISSION_FEATURE_VIEW):
    raise HTTPException(403, "Insufficient permissions")
```

### Verified Implementation Connection
```python
connection = get_user_implementation_connection(
    user_id, "alpaca", db
)
```

---

## New Database Models

- `VerifiedImplementation` - Available implementations
- `UserImplementationConnection` - User connections
- `UserSubscription` - Subscription records
- `SubscriptionUsage` - Pay-as-you-go usage
- `CommissionConfig` - Commission configuration
- `CommissionCharge` - Commission charges

---

## New Permissions

- `PERMISSION_TRADING_VIEW`, `PERMISSION_TRADING_TRADE`
- `PERMISSION_MARKET_CREATE`, `PERMISSION_MARKET_VIEW`
- `PERMISSION_SIGNATURE_COORDINATE`, `PERMISSION_SIGNATURE_EXECUTE`
- `PERMISSION_COMPLIANCE_VIEW`, `PERMISSION_COMPLIANCE_AUDIT`
- `PERMISSION_PORTFOLIO_VIEW`, `PERMISSION_PORTFOLIO_MANAGE`

---

## New Roles

- `TRADER` - Trading and portfolio management
- `COMPLIANCE_OFFICER` - Compliance monitoring

---

## Setup Commands

### Development
```bash
# Setup (first time)
./scripts/setup.sh  # or setup.ps1 on Windows

# Start development
npm run electron:dev
```

### Build
```bash
# Build Electron app
npm run electron:build

# Platform-specific builds
npm run electron:build:win
npm run electron:build:mac
npm run electron:build:linux
```

---

## Testing Checklist

- [ ] Subscription tier enforcement works
- [ ] Commissions calculated correctly
- [ ] Permissions filter tabs correctly
- [ ] Verified implementations connect properly
- [ ] All three features integrated
- [ ] Electron app builds successfully
- [ ] Setup scripts work on all platforms

---

## Common Issues & Solutions

### Issue: Tab not showing
**Solution**: Check permission and subscription tier requirements

### Issue: Commission not applied
**Solution**: Verify commission config exists and is active

### Issue: Implementation connection fails
**Solution**: Check user has selected implementation and connection data is valid

### Issue: Subscription tier not updating
**Solution**: Verify subscription service is called and database updated

---

**For detailed implementation, see the plan documents listed above.**
