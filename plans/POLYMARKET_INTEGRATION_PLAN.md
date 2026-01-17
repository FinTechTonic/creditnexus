# Polymarket & SFP Integration Plan: CreditNexus
## Complete Implementation with Code References

**Status**: Comprehensive Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 12-15 days  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete implementation plan** for integrating **Polymarket** prediction markets into CreditNexus, enabling trading and hedging of credit-linked events. The integration bundles document hashes, smart contracts, and CDM-compliant financial data into **Structured Financial Products (SFPs)** with immutable proof of existence via blockchain notarization.

**Key Integration Points:**
- **SFP Bundling**: Merkle tree generation from `CreditAgreement`, `DocumentSignature`, and `DocumentFiling` records
- **Polymarket API**: Market creation via Conditional Token Framework (CTF) for credit event prediction
- **Oracle Automation**: `VerifierAgent` (NDVI) and `PolicyService` as automated market resolution oracles
- **Hybrid Payments**: MetaMask (x402) for crypto trades + RevenueCat for subscription-based access tiers
- **Permissioned Access**: Deal-level visibility with RBAC integration

---

## Current State Analysis (Verified)

### ✅ Existing Infrastructure

#### 1. Smart Contract Notarization
**Location**: `contracts/SecuritizationNotarization.sol` (lines 1-172)

**Current Capabilities:**
- `createNotarization(poolId, poolHash, signers)` - Creates notarization record with hash
- `addSignature(poolId, signature)` - Multi-signer signature collection
- `getNotarizationStatus(poolId)` - Status query function
- Events: `NotarizationCreated`, `SignatureAdded`, `NotarizationCompleted`

**Gap**: No SFP-specific anchor method. Need to extend with `anchorSFPBundle()`.

**Code Reference**:
```46:61:contracts/SecuritizationNotarization.sol
function createNotarization(
    string memory poolId,
    bytes32 poolHash,
    address[] memory signers
) external {
    require(!poolNotarized[poolId], "Pool already notarized");
    require(signers.length > 0, "At least one signer required");
    
    NotarizationRecord storage record = notarizations[poolId];
    record.poolId = poolId;
    record.poolHash = poolHash;
    record.signers = signers;
    record.completed = false;
    
    emit NotarizationCreated(poolId, poolHash, signers);
}
```

#### 2. x402 Payment Service
**Location**: `app/services/x402_payment_service.py` (lines 19-276)

**Current Capabilities:**
- `request_payment()` - Returns HTTP 402 with payment instructions
- `verify_payment()` - Verifies payment via facilitator
- `settle_payment()` - Completes payment settlement
- `process_payment_flow()` - Complete request → verify → settle flow
- USDC on Base network: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

**Gap**: No Polymarket trade settlement payment type. Need to add `POLYMARKET_TRADE` to `PaymentType` enum.

**Code Reference**:
```171:226:app/services/x402_payment_service.py
async def process_payment_flow(
    self,
    amount: Decimal,
    currency: Currency,
    payer: Party,
    receiver: Party,
    payment_type: str,
    payment_payload: Optional[Dict[str, Any]] = None,
    cdm_reference: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete payment flow: request → verify → settle.
    """
    # Step 1: Request payment (if payload not provided)
    if payment_payload is None:
        payment_request = await self.request_payment(...)
        return payment_request
    
    # Step 2: Verify payment
    verification = await self.verify_payment(payment_payload)
    
    # Step 3: Settle payment
    settlement = await self.settle_payment(payment_payload, verification)
    
    return {
        "status": "settled",
        "verification": verification,
        "settlement": settlement,
        "payment_id": settlement.get("payment_id"),
        "transaction_hash": settlement.get("transaction_hash")
    }
```

#### 3. VerifierAgent (NDVI Oracle)
**Location**: `app/agents/verifier.py` (lines 1-359)

**Current Capabilities:**
- `verify_asset_location(lat, lon, threshold)` - Complete verification workflow
- `calculate_ndvi(nir_band, red_band)` - NDVI calculation from Sentinel-2 data
- `determine_risk_status(ndvi_score, threshold)` - Returns "COMPLIANT", "WARNING", or "BREACH"
- Integration with Sentinel Hub API

**Gap**: No direct market resolution trigger. Need to add `resolve_market_event()` method.

**Code Reference**:
```285:307:app/agents/verifier.py
def determine_risk_status(ndvi_score: float, threshold: float = 0.8) -> str:
    """
    Determine risk status based on NDVI score and SPT threshold.
    
    Returns:
        Risk status string: "COMPLIANT", "WARNING", or "BREACH"
    """
    normalized = (ndvi_score + 1) / 2  # Map -1..1 to 0..1
    
    if normalized >= threshold:
        return "COMPLIANT"
    elif normalized >= threshold * 0.9:
        return "WARNING"
    else:
        return "BREACH"
```

#### 4. Policy Service
**Location**: `app/services/policy_service.py` (lines 82-1712)

**Current Capabilities:**
- `evaluate_facility_creation()` - Policy evaluation for new facilities
- `evaluate_trade_execution()` - Trade execution policy checks
- `evaluate_loan_asset()` - Loan asset verification
- `evaluate_terms_change()` - Interest rate change evaluation
- Returns `PolicyDecision` with `decision` ("ALLOW", "BLOCK", "FLAG")

**Gap**: No market resolution evaluation. Need to add `evaluate_market_resolution()`.

#### 5. Database Models
**Location**: `app/db/models.py`

**Existing Models:**
- `Deal` (line 1254) - Deal lifecycle management
- `Document` (line 244) - Document metadata
- `DocumentSignature` (line 912) - Digital signatures
- `DocumentFiling` (line 982) - Regulatory filings

**Gap**: No `SFPPackage` or `MarketEvent` models. Need to create new models.

#### 6. Frontend Payment Integration
**Location**: `client/src/hooks/useX402Payment.ts` (lines 61-184)

**Current Capabilities:**
- `processPayment()` - Handles 402 Payment Required responses
- MetaMask wallet integration via `useWallet()` hook
- Payment facilitator URL handling

**Gap**: No Polymarket-specific payment flow. Need to add `usePolymarketTrade()` hook.

---

## Project 1: SFP Bundling Engine (Backend)

### Activity 1.1: Create SFP Bundler Service

**File**: `app/services/sfp_bundler_service.py` (NEW)

#### Task 1.1.1: Implement SFPBundlerService Class
**Lines**: 1-50 (Class definition and initialization)

**Subtasks**:
1. **Line 1-15**: Import statements
   - `from typing import Dict, Any, List, Optional`
   - `from decimal import Decimal`
   - `from sqlalchemy.orm import Session`
   - `from app.db.models import Deal, Document, DocumentSignature, DocumentFiling`
   - `from app.models.cdm import CreditAgreement`
   - `import hashlib`
   - `import json`
   - `from datetime import datetime`

2. **Line 16-30**: Class definition
   ```python
   class SFPBundlerService:
       """
       Service for bundling Structured Financial Products (SFPs).
       
       Creates Merkle trees from CDM data, signatures, and filings,
       then anchors the root hash to blockchain via SecuritizationNotarization.
       """
       
       def __init__(self, db: Session):
           self.db = db
   ```

3. **Line 31-50**: Helper methods
   - `_hash_data(data: bytes) -> str` - SHA-256 hash function
   - `_create_merkle_tree(items: List[str]) -> str` - Merkle root calculation

#### Task 1.1.2: Implement Bundle Generation Method
**Lines**: 51-150

**Subtasks**:
1. **Line 51-80**: `bundle_sfp(deal_id: int, market_event_type: str) -> Dict[str, Any]`
   - Fetch `Deal` record from database (reference: `app/db/models.py:1254`)
   - Fetch all `Document` records linked to deal (via `deal_data` JSONB field)
   - Fetch all `DocumentSignature` records (reference: `app/db/models.py:912`)
   - Fetch all `DocumentFiling` records (reference: `app/db/models.py:982`)

2. **Line 81-110**: CDM Data Extraction
   - Extract `CreditAgreement` from `DocumentVersion.extracted_data` (JSONB)
   - Serialize to JSON using `json.dumps()` with `sort_keys=True`
   - Hash CDM data: `cdm_hash = self._hash_data(cdm_json.encode())`

3. **Line 111-130**: Signature Collection
   - Iterate through `DocumentSignature` records
   - Extract `signature_data` (JSONB field)
   - Create signature hash list: `signature_hashes = [self._hash_data(sig.encode()) for sig in signatures]`

4. **Line 131-150**: Filing Collection
   - Iterate through `DocumentFiling` records
   - Extract `filing_data` (JSONB field)
   - Create filing hash list: `filing_hashes = [self._hash_data(filing.encode()) for filing in filings]`

5. **Line 151-180**: Merkle Tree Construction
   - Combine all hashes: `all_hashes = [cdm_hash] + signature_hashes + filing_hashes`
   - Build Merkle tree: `merkle_root = self._create_merkle_tree(all_hashes)`
   - Return SFP bundle structure:
     ```python
     return {
         "sfp_id": f"SFP_{deal_id}_{datetime.utcnow().isoformat()}",
         "deal_id": deal_id,
         "merkle_root": merkle_root,
         "cdm_hash": cdm_hash,
         "signature_hashes": signature_hashes,
         "filing_hashes": filing_hashes,
         "bundle_timestamp": datetime.utcnow().isoformat(),
         "market_event_type": market_event_type
     }
     ```

#### Task 1.1.3: Implement Blockchain Anchoring
**Lines**: 181-250

**Subtasks**:
1. **Line 181-200**: `anchor_sfp_to_blockchain(sfp_bundle: Dict[str, Any], signers: List[str]) -> str`
   - Convert `merkle_root` to `bytes32` for Solidity
   - Call `SecuritizationNotarization.createNotarization()` via web3.py
   - Reference contract: `contracts/SecuritizationNotarization.sol:46-61`

2. **Line 201-220**: Transaction Handling
   - Use `web3.eth.send_raw_transaction()` for contract interaction
   - Wait for transaction receipt
   - Extract `transaction_hash` from receipt

3. **Line 221-250**: Database Storage
   - Create `SFPPackage` database record (see Task 1.2.1)
   - Store `merkle_root`, `transaction_hash`, `block_number`
   - Link to `Deal` via foreign key

### Activity 1.2: Database Models for SFP

**File**: `app/db/models.py` (UPDATE)

#### Task 1.2.1: Add SFPPackage Model
**Lines**: ~2900-3000 (after `DealNote` model, line ~1350)

**Subtasks**:
1. **Line 2900-2920**: Model definition
   ```python
   class SFPPackage(Base):
       """Structured Financial Product bundle with Merkle root anchor."""
       
       __tablename__ = "sfp_packages"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       sfp_id = Column(String(255), unique=True, nullable=False, index=True)
       deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)
       merkle_root = Column(String(66), nullable=False)  # 0x + 64 hex chars
       cdm_hash = Column(String(66), nullable=False)
       signature_hashes = Column(JSONB, nullable=False)  # Array of hashes
       filing_hashes = Column(JSONB, nullable=False)  # Array of hashes
       transaction_hash = Column(String(66), nullable=True)  # Blockchain TX
       block_number = Column(Integer, nullable=True)
       bundle_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
       market_event_type = Column(String(50), nullable=False)  # e.g., "NDVI_COMPLIANCE"
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       deal = relationship("Deal", back_populates="sfp_packages")
   ```

2. **Line 2921-2930**: Add relationship to `Deal` model
   - In `Deal` class (line ~1254), add: `sfp_packages = relationship("SFPPackage", back_populates="deal")`

#### Task 1.2.2: Add MarketEvent Model
**Lines**: ~2931-3050

**Subtasks**:
1. **Line 2931-2980**: Model definition
   ```python
   class MarketEvent(Base):
       """Polymarket prediction market event linked to SFP."""
       
       __tablename__ = "market_events"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       market_id = Column(String(255), unique=True, nullable=False, index=True)  # Polymarket market ID
       sfp_package_id = Column(Integer, ForeignKey("sfp_packages.id"), nullable=False, index=True)
       deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)
       question = Column(Text, nullable=False)  # e.g., "Will NDVI drop below 0.6?"
       outcome_type = Column(String(50), nullable=False)  # "YES", "NO", "MULTI"
       resolution_condition = Column(JSONB, nullable=False)  # Oracle resolution logic
       created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       resolved_at = Column(DateTime, nullable=True)
       resolution_outcome = Column(String(20), nullable=True)  # "YES", "NO", "CANCELLED"
       oracle_triggered = Column(Boolean, default=False, nullable=False)
       liquidity_pool_address = Column(String(66), nullable=True)  # CTF pool address
       visibility = Column(String(20), default="public", nullable=False)  # "public", "deal_participants", "private"
       
       # Relationships
       sfp_package = relationship("SFPPackage", back_populates="market_events")
       deal = relationship("Deal", back_populates="market_events")
       creator = relationship("User", foreign_keys=[created_by])
   ```

2. **Line 2981-2990**: Add relationships
   - In `SFPPackage`: `market_events = relationship("MarketEvent", back_populates="sfp_package")`
   - In `Deal`: `market_events = relationship("MarketEvent", back_populates="deal")`

#### Task 1.2.3: Create Alembic Migration
**File**: `alembic/versions/XXXX_add_sfp_and_market_models.py` (NEW)

**Subtasks**:
1. Create migration file with `alembic revision -m "add_sfp_and_market_models"`
2. Add `upgrade()` function to create `sfp_packages` and `market_events` tables
3. Add `downgrade()` function to drop tables
4. Reference existing migrations in `alembic/versions/` for pattern

---

## Project 2: Polymarket Integration Service

### Activity 2.1: Create Polymarket Service

**File**: `app/services/polymarket_service.py` (NEW)

#### Task 2.1.1: Implement PolymarketService Class
**Lines**: 1-100

**Subtasks**:
1. **Line 1-30**: Imports and configuration
   ```python
   import logging
   from typing import Dict, Any, Optional, List
   from datetime import datetime
   from sqlalchemy.orm import Session
   import httpx
   from app.core.config import settings
   from app.db.models import MarketEvent, SFPPackage, Deal
   from app.services.sfp_bundler_service import SFPBundlerService
   
   logger = logging.getLogger(__name__)
   ```

2. **Line 31-60**: Class initialization
   ```python
   class PolymarketService:
       """
       Service for Polymarket CTF integration.
       
       Creates prediction markets for credit events, manages liquidity,
       and handles automated oracle resolution.
       """
       
       def __init__(self, db: Session, polymarket_api_url: str):
           self.db = db
           self.api_url = polymarket_api_url.rstrip('/')
           self.client = httpx.AsyncClient(timeout=30.0)
           self.sfp_bundler = SFPBundlerService(db)
   ```

#### Task 2.1.2: Implement Market Creation
**Lines**: 61-200

**Subtasks**:
1. **Line 61-100**: `create_market(deal_id: int, question: str, resolution_condition: Dict[str, Any], creator_user_id: int) -> Dict[str, Any]`
   - Bundle SFP using `SFPBundlerService.bundle_sfp()`
   - Anchor to blockchain using `SFPBundlerService.anchor_sfp_to_blockchain()`
   - Create `MarketEvent` database record
   - Call Polymarket API: `POST /api/v1/markets/create`
   - **Note**: Commission calculation is handled in the API endpoint (see Task 4.1.1)

2. **Line 101-140**: Polymarket API Integration
   ```python
   async def _create_polymarket_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
       """Create market via Polymarket API."""
       response = await self.client.post(
           f"{self.api_url}/api/v1/markets/create",
           json={
               "question": market_data["question"],
               "outcome_type": market_data["outcome_type"],
               "resolution_date": market_data["resolution_date"],
               "category": "credit_risk",
               "metadata": {
                   "sfp_id": market_data["sfp_id"],
                   "merkle_root": market_data["merkle_root"],
                   "deal_id": market_data["deal_id"]
               }
           },
           headers={"Authorization": f"Bearer {settings.POLYMARKET_API_KEY}"}
       )
       response.raise_for_status()
       return response.json()
   ```

3. **Line 141-180**: CTF Pool Creation
   - Extract `liquidity_pool_address` from Polymarket API response
   - Update `MarketEvent.liquidity_pool_address` in database
   - Store `market_id` from Polymarket response

4. **Line 181-200**: Return market creation result
   ```python
   return {
       "market_id": market_data["market_id"],
       "sfp_id": sfp_bundle["sfp_id"],
       "merkle_root": sfp_bundle["merkle_root"],
       "transaction_hash": anchor_result["transaction_hash"],
       "liquidity_pool_address": market_data["liquidity_pool_address"],
       "polymarket_url": f"https://polymarket.com/event/{market_data['market_id']}"
   }
   ```

#### Task 2.1.3: Implement Oracle Resolution
**Lines**: 201-350

**Subtasks**:
1. **Line 201-250**: `resolve_market_from_ndvi(loan_asset_id: int, market_event_id: int) -> Dict[str, Any]`
   - Fetch `LoanAsset` record (reference: `app/db/models.py` - search for `LoanAsset`)
   - Call `VerifierAgent.verify_asset_location()` (reference: `app/agents/verifier.py:309-359`)
   - Extract `risk_status` from verification result
   - Map to market outcome: `"YES"` if `risk_status == "BREACH"`, else `"NO"`

2. **Line 251-300**: `resolve_market_from_policy(policy_decision: PolicyDecision, market_event_id: int) -> Dict[str, Any]`
   - Map `PolicyDecision.decision` to market outcome
   - `"BLOCK"` → `"YES"` (policy violation occurred)
   - `"ALLOW"` → `"NO"` (no violation)
   - `"FLAG"` → Requires manual resolution

3. **Line 301-350**: Market Resolution API Call
   ```python
   async def _resolve_polymarket_market(self, market_id: str, outcome: str, oracle_data: Dict[str, Any]) -> Dict[str, Any]:
       """Resolve market via Polymarket API."""
       response = await self.client.post(
           f"{self.api_url}/api/v1/markets/{market_id}/resolve",
           json={
               "outcome": outcome,
               "oracle_data": oracle_data,
               "resolved_at": datetime.utcnow().isoformat()
           },
           headers={"Authorization": f"Bearer {settings.POLYMARKET_API_KEY}"}
       )
       response.raise_for_status()
       return response.json()
   ```

#### Task 2.1.4: Add Configuration Settings
**File**: `app/core/config.py` (UPDATE)

**Lines**: ~500-550 (after existing payment settings)

**Subtasks**:
1. Add Polymarket API configuration:
   ```python
   # Polymarket Integration
   POLYMARKET_ENABLED: bool = Field(default=False, description="Enable Polymarket integration")
   POLYMARKET_API_URL: Optional[str] = Field(default=None, description="Polymarket API base URL")
   POLYMARKET_API_KEY: Optional[SecretStr] = Field(default=None, description="Polymarket API key")
   POLYMARKET_NETWORK: str = Field(default="polygon", description="Polymarket network (polygon, ethereum)")
   ```

---

## Project 3: Payment Routing (MetaMask + RevenueCat)

### Activity 3.1: Create Payment Router Service

**File**: `app/services/payment_router_service.py` (NEW)

#### Task 3.1.1: Implement PaymentRouterService Class
**Lines**: 1-150

**Subtasks**:
1. **Line 1-40**: Imports and class definition
   ```python
   from typing import Dict, Any, Optional, Literal
   from decimal import Decimal
   from sqlalchemy.orm import Session
   from app.services.x402_payment_service import X402PaymentService
   from app.services.revenuecat_service import RevenueCatService  # NEW
   from app.db.models import User
   from app.models.cdm import Currency, Party
   
   class PaymentRouterService:
       """
       Routes payments between MetaMask (x402) and RevenueCat based on payment type.
       
       - Crypto payments (USDC) → MetaMask + x402
       - Subscription payments → RevenueCat
       """
   ```

2. **Line 41-80**: Initialize services
   ```python
   def __init__(
       self,
       db: Session,
       x402_service: Optional[X402PaymentService],
       revenuecat_service: Optional[RevenueCatService]
   ):
       self.db = db
       self.x402_service = x402_service
       self.revenuecat_service = revenuecat_service
   ```

3. **Line 81-120**: Route payment method
   ```python
   async def route_payment(
       self,
       payment_type: str,
       amount: Decimal,
       currency: Currency,
       payer: Party,
       receiver: Party,
       user: Optional[User] = None,
       payment_payload: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
       """
       Route payment to appropriate service.
       
       Payment types:
       - trade_settlement, loan_disbursement, penalty_payment → x402 (MetaMask)
       - subscription_upgrade, market_creation_fee → RevenueCat
       - polymarket_trade → x402 (MetaMask) for USDC trades
       """
       # Determine routing
       if payment_type in ["trade_settlement", "loan_disbursement", "penalty_payment", "polymarket_trade"]:
           return await self._route_to_x402(...)
       elif payment_type in ["subscription_upgrade", "market_creation_fee"]:
           return await self._route_to_revenuecat(...)
       else:
           raise ValueError(f"Unknown payment type: {payment_type}")
   ```

4. **Line 121-150**: Route to x402
   ```python
   async def _route_to_x402(
       self,
       amount: Decimal,
       currency: Currency,
       payer: Party,
       receiver: Party,
       payment_type: str,
       payment_payload: Optional[Dict[str, Any]]
   ) -> Dict[str, Any]:
       """Route payment to x402 service (MetaMask)."""
       if not self.x402_service:
           raise ValueError("x402 payment service not available")
       
       return await self.x402_service.process_payment_flow(
           amount=amount,
           currency=currency,
           payer=payer,
           receiver=receiver,
           payment_type=payment_type,
           payment_payload=payment_payload
       )
   ```

#### Task 3.1.2: Create RevenueCat Service
**File**: `app/services/revenuecat_service.py` (NEW)

**Lines**: 1-200

**Subtasks**:
1. **Line 1-50**: Class definition and initialization
   ```python
   import logging
   from typing import Dict, Any, Optional
   from sqlalchemy.orm import Session
   import httpx
   from app.core.config import settings
   from app.db.models import User
   
   logger = logging.getLogger(__name__)
   
   class RevenueCatService:
       """
       RevenueCat integration for subscription management.
       
       Tiers:
       - Free: View public markets
       - Pro: Create markets, access private hedge pools
       - Enterprise: White-label markets, institutional reporting
       """
       
       def __init__(self, api_key: str, base_url: str = "https://api.revenuecat.com/v1"):
           self.api_key = api_key
           self.base_url = base_url.rstrip('/')
           self.client = httpx.AsyncClient(
               timeout=30.0,
               headers={"Authorization": f"Bearer {api_key}"}
           )
   ```

2. **Line 51-100**: Get user subscription tier
   ```python
   async def get_user_tier(self, user_id: int, revenuecat_user_id: Optional[str] = None) -> Dict[str, Any]:
       """Get user's subscription tier from RevenueCat."""
       # RevenueCat user ID is typically email or custom ID
       user_identifier = revenuecat_user_id or f"user_{user_id}"
       
       response = await self.client.get(
           f"{self.base_url}/subscribers/{user_identifier}"
       )
       response.raise_for_status()
       data = response.json()
       
       # Extract active entitlement (tier)
       entitlements = data.get("subscriber", {}).get("entitlements", {})
       active_tier = "free"  # Default
       
       if "pro" in entitlements and entitlements["pro"]["is_active"]:
           active_tier = "pro"
       elif "enterprise" in entitlements and entitlements["enterprise"]["is_active"]:
           active_tier = "enterprise"
       
       return {
           "tier": active_tier,
           "is_active": True,
           "expires_at": entitlements.get(active_tier, {}).get("expires_date")
       }
   ```

3. **Line 101-150**: Process subscription payment
   ```python
   async def process_subscription_payment(
       self,
       user_id: int,
       tier: str,  # "pro" or "enterprise"
       payment_method: str = "stripe"  # or "apple", "google"
   ) -> Dict[str, Any]:
       """Process subscription upgrade payment via RevenueCat."""
       # RevenueCat handles payment processing
       # This method creates a purchase or updates subscription
       response = await self.client.post(
           f"{self.base_url}/receipts",
           json={
               "app_user_id": f"user_{user_id}",
               "product_id": f"creditnexus_{tier}",
               "price": self._get_tier_price(tier),
               "currency": "USD"
           }
       )
       response.raise_for_status()
       return response.json()
   ```

4. **Line 151-200**: Check tier permissions
   ```python
   def check_tier_permission(self, tier: str, required_permission: str) -> bool:
       """Check if tier has required permission."""
       tier_permissions = {
           "free": ["view_public_markets"],
           "pro": ["view_public_markets", "create_markets", "access_private_pools"],
           "enterprise": ["view_public_markets", "create_markets", "access_private_pools", "white_label", "institutional_reporting"]
       }
       return required_permission in tier_permissions.get(tier, [])
   ```

#### Task 3.1.3: Add RevenueCat Configuration
**File**: `app/core/config.py` (UPDATE)

**Lines**: ~550-570

**Subtasks**:
1. Add RevenueCat settings:
   ```python
   # RevenueCat Integration
   REVENUECAT_ENABLED: bool = Field(default=False, description="Enable RevenueCat integration")
   REVENUECAT_API_KEY: Optional[SecretStr] = Field(default=None, description="RevenueCat API key")
   REVENUECAT_BASE_URL: str = Field(default="https://api.revenuecat.com/v1", description="RevenueCat API base URL")
   ```

#### Task 3.1.4: Update PaymentType Enum
**File**: `app/models/cdm_payment.py` (UPDATE)

**Lines**: ~30-60 (find `PaymentType` enum)

**Subtasks**:
1. Add new payment types:
   ```python
   class PaymentType(str, Enum):
       # Existing types...
       TRADE_SETTLEMENT = "trade_settlement"
       LOAN_DISBURSEMENT = "loan_disbursement"
       PENALTY_PAYMENT = "penalty_payment"
       # New types
       POLYMARKET_TRADE = "polymarket_trade"
       SUBSCRIPTION_UPGRADE = "subscription_upgrade"
       MARKET_CREATION_FEE = "market_creation_fee"
   ```

---

## Project 4: API Endpoints

### Activity 4.1: Create Polymarket API Routes

**File**: `app/api/polymarket_routes.py` (NEW)

#### Task 4.1.1: Market Creation Endpoint
**Lines**: 1-100

**Subtasks**:
1. **Line 1-30**: Imports and router setup
   ```python
   from fastapi import APIRouter, Depends, HTTPException, status
   from sqlalchemy.orm import Session
   from pydantic import BaseModel, Field
   from typing import Dict, Any, Optional
   from app.db import get_db
   from app.auth.jwt_auth import get_current_user
   from app.db.models import User, Deal
   from app.services.polymarket_service import PolymarketService
   from app.services.payment_router_service import PaymentRouterService
   from app.services.subscription_service import SubscriptionService, get_subscription_service
   from app.services.commission_service import CommissionService
   from app.core.permissions import has_permission, PERMISSION_MARKET_CREATE
   from decimal import Decimal
   
   router = APIRouter(prefix="/api/polymarket", tags=["polymarket"])
   ```

2. **Line 31-60**: Request model
   ```python
   class CreateMarketRequest(BaseModel):
       deal_id: int = Field(..., description="Deal ID to create market for")
       question: str = Field(..., min_length=10, max_length=500, description="Market question")
       resolution_condition: Dict[str, Any] = Field(..., description="Oracle resolution condition")
       visibility: str = Field(default="public", pattern="^(public|deal_participants|private)$")
       initial_liquidity: Optional[float] = Field(None, description="Initial liquidity amount (USDC)")
   ```

3. **Line 61-100**: Create market endpoint
   ```python
   @router.post("/markets/create")
   async def create_market(
       request: CreateMarketRequest,
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user),
       polymarket_service: PolymarketService = Depends(get_polymarket_service),
       payment_router: PaymentRouterService = Depends(get_payment_router),
       subscription_service: SubscriptionService = Depends(get_subscription_service)
   ):
       """Create a new prediction market for a credit event."""
       # Permission check
       if not has_permission(current_user, PERMISSION_MARKET_CREATE):
           raise HTTPException(status_code=403, detail="Insufficient permissions")
       
       # Check subscription tier (Pro tier required for market creation)
       tier = subscription_service.get_user_tier(current_user.id)
       if tier not in ['pro', 'premium', 'lifetime']:
           raise HTTPException(
               status_code=403,
               detail="Pro subscription required to create markets"
           )
       
       # Check deal access
       deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
       if not deal:
           raise HTTPException(status_code=404, detail="Deal not found")
       
       # Create market
       result = await polymarket_service.create_market(
           deal_id=request.deal_id,
           question=request.question,
           resolution_condition=request.resolution_condition,
           creator_user_id=current_user.id,
           visibility=request.visibility
       )
       
       # Apply commission for market creation
       commission_service = CommissionService(db)
       commission = commission_service.apply_commission(
           transaction_id=f"market_{result['market_id']}",
           transaction_type="market_creation",
           transaction_amount=Decimal(str(request.initial_liquidity or 0)),
           payer_id=current_user.id,
           transaction_metadata={
               "market_id": result["market_id"],
               "deal_id": request.deal_id
           }
       )
       
       return {
           "market_id": result["market_id"],
           "sfp_id": result["sfp_id"],
           "merkle_root": result["merkle_root"],
           "polymarket_url": result["polymarket_url"],
           "transaction_hash": result["transaction_hash"],
           "commission": {
               "amount": str(commission.amount),
               "currency": commission.currency
           }
       }
   ```

#### Task 4.1.2: Market Listing Endpoint
**Lines**: 101-200

**Subtasks**:
1. **Line 101-150**: List markets with filtering
   ```python
   @router.get("/markets")
   async def list_markets(
       deal_id: Optional[int] = None,
       status: Optional[str] = None,  # "active", "resolved", "cancelled"
       visibility: Optional[str] = None,
       page: int = 1,
       limit: int = 50,
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user),
       polymarket_service: PolymarketService = Depends(get_polymarket_service)
   ):
       """List available markets with permission-based filtering."""
       # Filter by deal access (deal_participants visibility)
       markets = await polymarket_service.list_markets(
           deal_id=deal_id,
           status=status,
           visibility=visibility,
           user_id=current_user.id,
           page=page,
           limit=limit
       )
       return markets
   ```

#### Task 4.1.3: Market Resolution Endpoint
**Lines**: 201-300

**Subtasks**:
1. **Line 201-250**: Manual resolution (admin only)
   ```python
   @router.post("/markets/{market_id}/resolve")
   async def resolve_market(
       market_id: str,
       outcome: str,  # "YES", "NO", "CANCELLED"
       oracle_data: Dict[str, Any],
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user),
       polymarket_service: PolymarketService = Depends(get_polymarket_service)
   ):
       """Manually resolve a market (admin/oracle only)."""
       # Check admin permission
       if current_user.role != "admin":
           raise HTTPException(status_code=403, detail="Admin access required")
       
       result = await polymarket_service.resolve_market(
           market_id=market_id,
           outcome=outcome,
           oracle_data=oracle_data
       )
       return result
   ```

#### Task 4.1.4: Register Routes in Main App
**File**: `server.py` (UPDATE)

**Lines**: ~200-250 (find router registration section)

**Subtasks**:
1. Import polymarket routes:
   ```python
   from app.api.polymarket_routes import router as polymarket_router
   ```

2. Register router:
   ```python
   app.include_router(polymarket_router)
   ```

---

## Project 5: Frontend Integration

### Activity 5.1: Create Polymarket Dashboard Tab

**File**: `client/src/components/dashboard-tabs/MarketDashboard.tsx` (NEW)

**Note**: This component is integrated into the UnifiedDashboard as a tab. See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture.

#### Task 5.1.1: Market Dashboard Component
**Lines**: 1-200

**Subtasks**:
1. **Line 1-50**: Imports and setup
   ```typescript
   import { useState, useEffect } from 'react';
   import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
   import { Button } from '@/components/ui/button';
   import { useAuth, fetchWithAuth } from '@/context/AuthContext';
   import { useFDC3 } from '@/hooks/useFDC3';
   import { TrendingUp, TrendingDown, Eye, Plus } from 'lucide-react';
   ```

2. **Line 51-100**: State management
   ```typescript
   interface Market {
     market_id: string;
     question: string;
     sfp_id: string;
     merkle_root: string;
     status: 'active' | 'resolved' | 'cancelled';
     outcome: 'YES' | 'NO' | null;
     visibility: 'public' | 'deal_participants' | 'private';
     deal_id: number;
     polymarket_url: string;
   }
   
   export function MarketDashboard() {
     const { user } = useAuth();
     const { broadcast } = useFDC3();
     const [markets, setMarkets] = useState<Market[]>([]);
     const [loading, setLoading] = useState(true);
     const [filter, setFilter] = useState<'all' | 'active' | 'resolved'>('all');
   ```

3. **Line 101-150**: Fetch markets
   ```typescript
   useEffect(() => {
     const fetchMarkets = async () => {
       try {
         const response = await fetchWithAuth('/api/polymarket/markets');
         if (response.ok) {
           const data = await response.json();
           setMarkets(data.markets || []);
         }
       } catch (error) {
         console.error('Error fetching markets:', error);
       } finally {
         setLoading(false);
       }
     };
     fetchMarkets();
   }, [filter]);
   ```

4. **Line 151-200**: Render market list
   ```typescript
   return (
     <div className="space-y-6">
       <div className="flex justify-between items-center">
         <h1 className="text-3xl font-bold">Prediction Markets</h1>
         <Button onClick={() => setShowCreateModal(true)}>
           <Plus className="h-4 w-4 mr-2" />
           Create Market
         </Button>
       </div>
       
       {markets.map(market => (
         <Card key={market.market_id}>
           <CardHeader>
             <CardTitle>{market.question}</CardTitle>
           </CardHeader>
           <CardContent>
             <div className="flex justify-between">
               <span>Status: {market.status}</span>
               <Button onClick={() => window.open(market.polymarket_url, '_blank')}>
                 Trade on Polymarket
               </Button>
             </div>
           </CardContent>
         </Card>
       ))}
     </div>
   );
   ```

#### Task 5.1.2: Market Creation Modal
**File**: `client/src/apps/polymarket-nexus/MarketCreationModal.tsx` (NEW)

**Lines**: 1-250

**Subtasks**:
1. Create modal component with form for:
   - Deal selection (dropdown)
   - Question input
   - Resolution condition (JSON editor)
   - Visibility selection
   - Initial liquidity (optional)

2. Submit to `/api/polymarket/markets/create`
3. Handle payment routing (RevenueCat for market creation fee if required)

#### Task 5.1.3: SFP Inspector Component
**File**: `client/src/apps/polymarket-nexus/SFPInspector.tsx` (NEW)

**Lines**: 1-200

**Subtasks**:
1. Display SFP bundle details:
   - Merkle root
   - CDM hash
   - Signature hashes
   - Filing hashes
   - Blockchain transaction hash
   - Link to Base explorer

2. Verify button to check Merkle root on-chain

#### Task 5.1.4: Integration with Unified Dashboard
**File**: `client/src/components/UnifiedDashboard.tsx` (UPDATE)

**Lines**: ~100-200 (in dashboardTabs array)

**Subtasks**:
1. Import MarketDashboard component:
   ```typescript
   import { MarketDashboard } from '@/components/dashboard-tabs/MarketDashboard';
   import { BarChart3 } from 'lucide-react';
   import { PERMISSION_MARKET_VIEW } from '@/utils/permissions';
   ```

2. Add Polymarket tab to dashboardTabs array:
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

**Note**: The UnifiedDashboard component automatically filters tabs based on permissions and subscription tier. See `ELECTRON_REFACTORING_PLAN.md` for details.

---

## Project 6: Permissions & Security

### Activity 6.1: Add Market Permissions

**File**: `app/core/permissions.py` (UPDATE)

**Lines**: ~100-110 (after existing permissions)

**Subtasks**:
1. Add permission constants:
   ```python
   # Market Permissions
   PERMISSION_MARKET_CREATE = "MARKET_CREATE"
   PERMISSION_MARKET_VIEW = "MARKET_VIEW"
   PERMISSION_MARKET_TRADE = "MARKET_TRADE"
   PERMISSION_MARKET_RESOLVE = "MARKET_RESOLVE"
   ```

2. Add to `PERMISSION_CATEGORIES` (line ~113):
   ```python
   "market": [
       PERMISSION_MARKET_CREATE,
       PERMISSION_MARKET_VIEW,
       PERMISSION_MARKET_TRADE,
       PERMISSION_MARKET_RESOLVE,
   ],
   ```

3. Add to role permissions (line ~218):
   ```python
   UserRole.BANKER.value: [
       # ... existing permissions ...
       PERMISSION_MARKET_CREATE,
       PERMISSION_MARKET_VIEW,
       PERMISSION_MARKET_TRADE,
   ],
   ```

### Activity 6.2: Deal-Level Visibility

**File**: `app/services/polymarket_service.py` (UPDATE)

**Lines**: ~400-500 (add new method)

**Subtasks**:
1. Implement `check_market_visibility()` method:
   ```python
   def check_market_visibility(
       self,
       market: MarketEvent,
       user_id: int
   ) -> bool:
       """Check if user can view market based on visibility setting."""
       if market.visibility == "public":
           return True
       elif market.visibility == "deal_participants":
           # Check if user is participant in deal
           deal = self.db.query(Deal).filter(Deal.id == market.deal_id).first()
           # Check deal participants (from deal_data JSONB or separate table)
           participants = deal.deal_data.get("participants", [])
           return user_id in participants or deal.applicant_id == user_id
       elif market.visibility == "private":
           return market.created_by == user_id
       return False
   ```

---

## Project 7: Oracle Automation

### Activity 7.1: Integrate VerifierAgent with Market Resolution

**File**: `app/services/polymarket_service.py` (UPDATE)

**Lines**: ~350-400 (enhance existing resolution method)

**Subtasks**:
1. Add automatic resolution trigger:
   ```python
   async def auto_resolve_from_verification(
       self,
       loan_asset_id: int,
       market_event_id: int
   ) -> Dict[str, Any]:
       """Automatically resolve market when NDVI verification completes."""
       from app.agents.verifier import verify_asset_location
       from app.db.models import LoanAsset
       
       # Fetch loan asset
       loan_asset = self.db.query(LoanAsset).filter(LoanAsset.id == loan_asset_id).first()
       if not loan_asset:
           raise ValueError("Loan asset not found")
       
       # Run verification
       verification_result = await verify_asset_location(
           lat=loan_asset.latitude,
           lon=loan_asset.longitude,
           threshold=loan_asset.ndvi_threshold or 0.8
       )
       
       # Map to market outcome
       risk_status = verification_result.get("risk_status")
       outcome = "YES" if risk_status == "BREACH" else "NO"
       
       # Resolve market
       return await self.resolve_market(
           market_event_id=market_event_id,
           outcome=outcome,
           oracle_data={
               "source": "verifier_agent",
               "ndvi_score": verification_result.get("ndvi_score"),
               "risk_status": risk_status,
               "verified_at": verification_result.get("verified_at")
           }
       )
   ```

### Activity 7.2: Add Background Task for Oracle Monitoring

**File**: `app/services/oracle_monitor_service.py` (NEW)

**Lines**: 1-200

**Subtasks**:
1. Create background service that:
   - Monitors `LoanAsset` records for verification updates
   - Checks for active markets linked to assets
   - Triggers automatic resolution via `PolymarketService.auto_resolve_from_verification()`

2. Integrate with FastAPI background tasks (reference: `app/api/routes.py` background task patterns)

---

## Integration with Unified Dashboard

### Overview
The Polymarket integration is designed to work within the UnifiedDashboard architecture. The MarketDashboard component is accessible as a tab in the unified dashboard, with automatic filtering based on permissions and subscription tiers.

### Key Integration Points

1. **Component Location**: `client/src/components/dashboard-tabs/MarketDashboard.tsx`
2. **Tab Configuration**: Added to UnifiedDashboard tabs array with:
   - Tab ID: `polymarket`
   - Required Permission: `PERMISSION_MARKET_VIEW`
   - Subscription Tier: `pro` (Pro tier required)
3. **Subscription Tier Enforcement**: Market creation endpoint checks for Pro/Premium/Lifetime tier
4. **Commission Integration**: Market creation automatically applies commission charges
5. **Billing Integration**: All market creation costs, commissions, and usage are automatically tracked in the billing system (see `BILLING_DASHBOARD_PLAN.md`)
6. **Verified Implementations**: Polymarket connection uses verified implementations system
7. **Social Newsfeed Integration**: Markets are automatically posted to newsfeed (see `SOCIAL_NEWSFEED_PLAN.md`)

### Billing Integration Details

Market creation and trading activities automatically generate billing records:

1. **Market Creation Costs**: Tracked as `usage_cost` in billing periods
2. **Commission Charges**: Tracked as `commission_revenue` (for CreditNexus) in billing periods
3. **Cost Allocation**: Costs are allocated to organizations and roles via `CostAllocation` records
4. **Billing Dashboard**: Users can view their Polymarket-related costs in the `BillingDashboard` component

**Code Reference**: See `BILLING_DASHBOARD_PLAN.md` for complete billing system details.

### References
- See `PLAN_INTEGRATION_ADDENDUM.md` for detailed integration patterns
- See `ELECTRON_REFACTORING_PLAN.md` for unified dashboard architecture
- See `MASTER_IMPLEMENTATION_PLAN.md` for overall implementation overview
- See `SOCIAL_NEWSFEED_PLAN.md` for newsfeed integration details
- See `BILLING_DASHBOARD_PLAN.md` for billing system integration

---

## Implementation Checklist

### Phase 1: Backend Foundation (Days 1-4)
- [ ] **Task 1.1**: Create `SFPBundlerService` with Merkle tree generation
- [ ] **Task 1.2**: Add `SFPPackage` and `MarketEvent` database models
- [ ] **Task 1.3**: Create Alembic migration for new models
- [ ] **Task 2.1**: Create `PolymarketService` with market creation
- [ ] **Task 2.2**: Add Polymarket API configuration to `app/core/config.py`

### Phase 2: Payment Routing (Days 5-7)
- [ ] **Task 3.1**: Create `PaymentRouterService` for MetaMask/RevenueCat routing
- [ ] **Task 3.2**: Create `RevenueCatService` for subscription management
- [ ] **Task 3.3**: Add RevenueCat configuration
- [ ] **Task 3.4**: Update `PaymentType` enum with new types

### Phase 3: API Endpoints (Days 8-9)
- [ ] **Task 4.1**: Create `/api/polymarket/markets/create` endpoint
- [ ] **Task 4.2**: Create `/api/polymarket/markets` listing endpoint
- [ ] **Task 4.3**: Create `/api/polymarket/markets/{id}/resolve` endpoint
- [ ] **Task 4.4**: Register routes in `server.py`

### Phase 4: Frontend (Days 10-12)
- [ ] **Task 5.1**: Create `MarketDashboard.tsx` component
- [ ] **Task 5.2**: Create `MarketCreationModal.tsx` component
- [ ] **Task 5.3**: Create `SFPInspector.tsx` component
- [ ] **Task 5.4**: Add Polymarket-Nexus to `DesktopAppLayout.tsx`

### Phase 5: Permissions & Oracle (Days 13-15)
- [ ] **Task 6.1**: Add market permissions to `app/core/permissions.py`
- [ ] **Task 6.2**: Implement deal-level visibility checks
- [ ] **Task 7.1**: Integrate VerifierAgent with market resolution
- [ ] **Task 7.2**: Create oracle monitoring background service

---

## Testing Requirements

### Unit Tests
- `tests/test_sfp_bundler.py` - Test Merkle tree generation
- `tests/test_polymarket_service.py` - Test market creation and resolution
- `tests/test_payment_router.py` - Test payment routing logic

### Integration Tests
- `tests/test_polymarket_api.py` - Test API endpoints
- `tests/test_oracle_resolution.py` - Test automatic market resolution

---

## Environment Variables

Add to `.env`:
```bash
# Polymarket
POLYMARKET_ENABLED=true
POLYMARKET_API_URL=https://api.polymarket.com
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_NETWORK=polygon

# RevenueCat
REVENUECAT_ENABLED=true
REVENUECAT_API_KEY=your_revenuecat_key_here
REVENUECAT_BASE_URL=https://api.revenuecat.com/v1
```

---

## Success Criteria

1. ✅ Bankers can create prediction markets for deals with SFP bundling
2. ✅ Markets are anchored to blockchain via `SecuritizationNotarization`
3. ✅ Investors can view and trade markets via Polymarket integration
4. ✅ NDVI verification automatically resolves markets
5. ✅ Payment routing works for both MetaMask (crypto) and RevenueCat (subscriptions)
6. ✅ Deal-level visibility restricts market access appropriately
7. ✅ All actions are logged in audit trail

---

**Last Updated**: 2024-12-XX  
**Version**: 2.0  
**Status**: Ready for Implementation
