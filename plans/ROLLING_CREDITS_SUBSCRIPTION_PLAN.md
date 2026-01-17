# Rolling Credits Subscription Service Plan
## Blockchain-Registered Credits with Adaptive Pricing

**Status**: Comprehensive Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 8-10 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan provides a **complete rolling credits subscription service** that:
- Generates credits from PRO and Premium subscriptions
- Registers credits on organization blockchain
- Uses bridge to convert credits and verify usage by server
- Calculates costs adaptively per service
- Sets fees by server for server transactions/calls
- Sets fees adaptively for client-side calls (server-controlled)
- Supports different credit types per workflow
- Provides tier-based credit allocation per workflow type (securitization, signing, verification, trading, loaning, borrowing, etc.)

---

## Current State Analysis

### ✅ Existing Infrastructure

**Credits System** (Planned):
- `CreditBalance` model (from ENHANCED_NAVIGATION_CHATBOT_PLAN.md)
- `CreditTransaction` model
- `CreditPackage` model
- `CreditsService` (basic implementation planned)

**Blockchain Infrastructure**:
- `Organization` model with blockchain deployment
- `CrossChainBridge.sol` contract for cross-chain messaging
- `CrossChainService` for bridge operations
- `BlockchainRouterService` for routing to org chains

**Workflow Types**:
- Verification, Notarization, Document Review, Deal Approval, Signature, Compliance Check
- Securitization, Trading, Loaning, Borrowing (from other features)

**Subscription Tiers**:
- Free, Pro (pay-as-you-go), Premium, Lifetime

### ❌ Missing

**Credit Types**:
- No credit type differentiation (all credits are generic)
- No workflow-specific credit types

**Blockchain Credit Registration**:
- No credit token contract on organization chains
- No bridge integration for credit verification

**Adaptive Pricing**:
- No adaptive cost calculation
- No server-controlled fee setting for client calls

**Rolling Credits**:
- No automatic credit generation from subscriptions
- No tier-based credit allocation per workflow

---

## Credit Type Assessment

### Analysis: Do We Need Different Credit Types?

**YES - Different credit types are needed because:**

1. **Different Workflow Costs**: 
   - Securitization: High cost (complex, requires multiple services)
   - Trading: Medium cost (real-time, requires market data)
   - Verification: Medium cost (satellite imagery, AI analysis)
   - Signing: Low cost (simple signature coordination)
   - Loaning/Borrowing: Medium cost (document processing, KYC)
   - Document Review: Low-Medium cost (AI analysis)

2. **Different Resource Requirements**:
   - Some workflows require LLM calls (expensive)
   - Some require blockchain transactions (gas costs)
   - Some require external API calls (market data, satellite imagery)
   - Some are compute-intensive (risk analysis)

3. **Tier-Based Allocation**:
   - PRO tier might get more "basic" credits (signing, document review)
   - Premium tier might get more "advanced" credits (securitization, trading)
   - Different workflows need different credit types

### Credit Type Structure

```python
class CreditType(str, Enum):
    """Credit types for different workflows."""
    # Basic workflows (low cost)
    SIGNING = "signing"  # Document signing coordination
    DOCUMENT_REVIEW = "document_review"  # Basic document review
    
    # Medium workflows (medium cost)
    VERIFICATION = "verification"  # Deal verification with satellite imagery
    TRADING = "trading"  # Trade execution
    LOANING = "loaning"  # Loan origination
    BORROWING = "borrowing"  # Loan application processing
    COMPLIANCE_CHECK = "compliance_check"  # Compliance verification
    
    # Advanced workflows (high cost)
    SECURITIZATION = "securitization"  # Securitization pool creation
    RISK_ANALYSIS = "risk_analysis"  # Advanced risk analysis
    QUANTITATIVE_ANALYSIS = "quantitative_analysis"  # LangAlpha queries
    
    # Stock prediction workflows (variable cost by timeframe)
    STOCK_PREDICTION_DAILY = "stock_prediction_daily"  # Daily stock predictions (Chronos model)
    STOCK_PREDICTION_HOURLY = "stock_prediction_hourly"  # Hourly stock predictions
    STOCK_PREDICTION_15MIN = "stock_prediction_15min"  # 15-minute stock predictions
    
    # Generic (can be used for any workflow)
    UNIVERSAL = "universal"  # Can be converted to any type
```

---

## Project 1: Credit Type Models & Blockchain Registration

### Activity 1.1: Enhanced Credit Models

**File**: `app/db/models.py` (UPDATE)

#### Task 1.1.1: Add Credit Type Support
**Lines**: ~3400-3700

**Subtasks**:
1. **Line 3400-3600**: Enhanced credit models
   ```python
   class CreditType(str, enum.Enum):
       """Credit types for different workflows."""
       SIGNING = "signing"
       DOCUMENT_REVIEW = "document_review"
       VERIFICATION = "verification"
       TRADING = "trading"
       LOANING = "loaning"
       BORROWING = "borrowing"
       COMPLIANCE_CHECK = "compliance_check"
       SECURITIZATION = "securitization"
       RISK_ANALYSIS = "risk_analysis"
       QUANTITATIVE_ANALYSIS = "quantitative_analysis"
       STOCK_PREDICTION_DAILY = "stock_prediction_daily"  # Daily stock predictions
       STOCK_PREDICTION_HOURLY = "stock_prediction_hourly"  # Hourly stock predictions
       STOCK_PREDICTION_15MIN = "stock_prediction_15min"  # 15-minute stock predictions
       UNIVERSAL = "universal"  # Can be converted to any type
   
   class CreditBalance(Base):
       """User credit balance with type support."""
       __tablename__ = "credit_balances"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
       
       # Credit balances by type (JSONB for flexibility)
       balances = Column(JSONB, nullable=False, default={})  # {"signing": 100, "trading": 50, ...}
       total_balance = Column(Numeric(19, 4), default=0, nullable=False)  # Sum of all types
       
       # Lifetime tracking
       lifetime_earned = Column(JSONB, nullable=False, default={})  # By type
       lifetime_spent = Column(JSONB, nullable=False, default={})  # By type
       
       # Blockchain registration
       blockchain_registered = Column(Boolean, default=False, nullable=False)
       blockchain_token_id = Column(String(255), nullable=True, unique=True, index=True)  # NFT token ID on org chain
       blockchain_tx_hash = Column(String(255), nullable=True, index=True)  # Registration transaction
       blockchain_chain_id = Column(Integer, nullable=True)  # Organization chain ID
       
       # Last update
       last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
       created_at = Column(DateTime, default=datetime.utcnow)
       
       # Relationships
       user = relationship("User", back_populates="credit_balance")
       organization = relationship("Organization", back_populates="credit_balances")
       transactions = relationship("CreditTransaction", back_populates="balance")
       
       def get_balance(self, credit_type: str = "universal") -> Decimal:
           """Get balance for a specific credit type."""
           if credit_type == "universal":
               return self.total_balance
           return Decimal(str(self.balances.get(credit_type, 0)))
       
       def to_dict(self):
           """Convert to dictionary."""
           return {
               "id": self.id,
               "user_id": self.user_id,
               "organization_id": self.organization_id,
               "balances": self.balances,
               "total_balance": float(self.total_balance) if self.total_balance else 0,
               "lifetime_earned": self.lifetime_earned,
               "lifetime_spent": self.lifetime_spent,
               "blockchain_registered": self.blockchain_registered,
               "blockchain_token_id": self.blockchain_token_id,
               "blockchain_tx_hash": self.blockchain_tx_hash,
               "blockchain_chain_id": self.blockchain_chain_id,
               "last_updated": self.last_updated.isoformat() if self.last_updated else None,
               "created_at": self.created_at.isoformat() if self.created_at else None
           }
   
   class CreditTransaction(Base):
       """Credit transaction with type support."""
       __tablename__ = "credit_transactions"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       balance_id = Column(Integer, ForeignKey("credit_balances.id", ondelete="CASCADE"), nullable=False, index=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
       
       # Transaction details
       transaction_type = Column(String(50), nullable=False)  # "subscription", "purchase", "usage", "conversion", "refund"
       credit_type = Column(String(50), nullable=False, index=True)  # CreditType enum
       amount = Column(Numeric(19, 4), nullable=False)  # Positive for earned, negative for spent
       
       # Balance tracking
       balance_before = Column(JSONB, nullable=True)  # Balances before transaction
       balance_after = Column(JSONB, nullable=True)  # Balances after transaction
       
       # Workflow context
       feature = Column(String(100), nullable=True, index=True)  # Workflow type (securitization, trading, etc.)
       related_transaction_id = Column(String(255), nullable=True, index=True)  # Trade ID, Deal ID, etc.
       
       # Subscription context
       subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
       
       # Blockchain verification
       blockchain_verified = Column(Boolean, default=False, nullable=False)
       blockchain_tx_hash = Column(String(255), nullable=True, index=True)
       bridge_tx_hash = Column(String(255), nullable=True, index=True)  # Bridge transaction hash
       
       # Adaptive pricing
       base_cost = Column(Numeric(19, 4), nullable=True)  # Base cost before adaptation
       adaptive_cost = Column(Numeric(19, 4), nullable=True)  # Actual cost after adaptation
       pricing_factors = Column(JSONB, nullable=True)  # Factors that influenced pricing
       
       # Metadata
       description = Column(Text, nullable=True)
       payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
       metadata = Column(JSONB, nullable=True)
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
       
       # Relationships
       balance = relationship("CreditBalance", back_populates="transactions")
       user = relationship("User", foreign_keys=[user_id])
       organization = relationship("Organization", foreign_keys=[organization_id])
       subscription = relationship("UserSubscription", foreign_keys=[subscription_id])
       payment_event = relationship("PaymentEvent", foreign_keys=[payment_event_id])
   ```

### Activity 1.2: Credit Token Smart Contract

**File**: `contracts/CreditToken.sol` (NEW)

#### Task 1.2.1: Create Credit Token Contract
**Lines**: 1-400

**Subtasks**:
1. **Line 1-400**: ERC-721 credit token contract
   ```solidity
   // SPDX-License-Identifier: MIT
   pragma solidity ^0.8.20;
   
   import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
   import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
   import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
   import "@openzeppelin/contracts/access/Ownable.sol";
   
   /**
    * @title CreditToken
    * @dev ERC-721 NFT representing credit balances on organization blockchain
    * Each token represents a user's credit balance with type-specific amounts
    */
   contract CreditToken is ERC721Enumerable, ERC721URIStorage, Ownable {
       struct CreditBalance {
           uint256 signing;
           uint256 documentReview;
           uint256 verification;
           uint256 trading;
           uint256 loaning;
           uint256 borrowing;
           uint256 complianceCheck;
           uint256 securitization;
           uint256 riskAnalysis;
           uint256 quantitativeAnalysis;
           uint256 universal;
       }
       
       mapping(uint256 => CreditBalance) public creditBalances;
       mapping(address => uint256) public userTokenIds;  // user address => token ID
       mapping(uint256 => address) public tokenOwners;  // token ID => user address
       
       uint256 private _tokenIdCounter;
       
       event CreditsMinted(
           uint256 indexed tokenId,
           address indexed user,
           CreditBalance credits
       );
       
       event CreditsUpdated(
           uint256 indexed tokenId,
           address indexed user,
           string creditType,
           uint256 amount,
           bool isSpend  // true if spending, false if earning
       );
       
       event CreditsBridged(
           uint256 indexed tokenId,
           uint256 targetChainId,
           address targetAddress
       );
       
       constructor() ERC721("CreditNexus Credits", "CNCRED") Ownable(msg.sender) {}
       
       /**
        * @dev Mint credit token for user (called when subscription generates credits)
        */
       function mintCredits(
           address user,
           CreditBalance memory credits
       ) external onlyOwner returns (uint256) {
           require(user != address(0), "Invalid user address");
           
           uint256 tokenId = _tokenIdCounter++;
           _safeMint(user, tokenId);
           
           creditBalances[tokenId] = credits;
           userTokenIds[user] = tokenId;
           tokenOwners[tokenId] = user;
           
           emit CreditsMinted(tokenId, user, credits);
           
           return tokenId;
       }
       
       /**
        * @dev Update credits for a token (spend or earn)
        */
       function updateCredits(
           uint256 tokenId,
           string memory creditType,
           uint256 amount,
           bool isSpend
       ) external onlyOwner {
           require(_ownerOf(tokenId) != address(0), "Token does not exist");
           
           CreditBalance storage balance = creditBalances[tokenId];
           
           if (isSpend) {
               // Verify sufficient balance
               require(_getCreditBalance(balance, creditType) >= amount, "Insufficient credits");
               _decreaseCreditBalance(balance, creditType, amount);
           } else {
               _increaseCreditBalance(balance, creditType, amount);
           }
           
           emit CreditsUpdated(tokenId, tokenOwners[tokenId], creditType, amount, isSpend);
       }
       
       /**
        * @dev Get credit balance for a type
        */
       function getCreditBalance(
           uint256 tokenId,
           string memory creditType
       ) external view returns (uint256) {
           require(_ownerOf(tokenId) != address(0), "Token does not exist");
           return _getCreditBalance(creditBalances[tokenId], creditType);
       }
       
       /**
        * @dev Get all credit balances for a token
        */
       function getAllCredits(uint256 tokenId) external view returns (CreditBalance memory) {
           require(_ownerOf(tokenId) != address(0), "Token does not exist");
           return creditBalances[tokenId];
       }
       
       /**
        * @dev Lock credits for bridge transfer
        */
       function lockForBridge(
           uint256 tokenId,
           uint256 duration
       ) external onlyOwner {
           // Implementation for locking credits during bridge
       }
       
       /**
        * @dev Bridge credits to another chain
        */
       function bridgeCredits(
           uint256 tokenId,
           uint256 targetChainId,
           address targetAddress
       ) external onlyOwner {
           require(_ownerOf(tokenId) != address(0), "Token does not exist");
           
           emit CreditsBridged(tokenId, targetChainId, targetAddress);
       }
       
       // Internal helper functions
       function _getCreditBalance(CreditBalance memory balance, string memory creditType) internal pure returns (uint256) {
           bytes32 typeHash = keccak256(bytes(creditType));
           if (typeHash == keccak256("signing")) return balance.signing;
           if (typeHash == keccak256("document_review")) return balance.documentReview;
           if (typeHash == keccak256("verification")) return balance.verification;
           if (typeHash == keccak256("trading")) return balance.trading;
           if (typeHash == keccak256("loaning")) return balance.loaning;
           if (typeHash == keccak256("borrowing")) return balance.borrowing;
           if (typeHash == keccak256("compliance_check")) return balance.complianceCheck;
           if (typeHash == keccak256("securitization")) return balance.securitization;
           if (typeHash == keccak256("risk_analysis")) return balance.riskAnalysis;
           if (typeHash == keccak256("quantitative_analysis")) return balance.quantitativeAnalysis;
           if (typeHash == keccak256("universal")) return balance.universal;
           return 0;
       }
       
       function _increaseCreditBalance(CreditBalance storage balance, string memory creditType, uint256 amount) internal {
           bytes32 typeHash = keccak256(bytes(creditType));
           if (typeHash == keccak256("signing")) balance.signing += amount;
           else if (typeHash == keccak256("document_review")) balance.documentReview += amount;
           else if (typeHash == keccak256("verification")) balance.verification += amount;
           else if (typeHash == keccak256("trading")) balance.trading += amount;
           else if (typeHash == keccak256("loaning")) balance.loaning += amount;
           else if (typeHash == keccak256("borrowing")) balance.borrowing += amount;
           else if (typeHash == keccak256("compliance_check")) balance.complianceCheck += amount;
           else if (typeHash == keccak256("securitization")) balance.securitization += amount;
           else if (typeHash == keccak256("risk_analysis")) balance.riskAnalysis += amount;
           else if (typeHash == keccak256("quantitative_analysis")) balance.quantitativeAnalysis += amount;
           else if (typeHash == keccak256("universal")) balance.universal += amount;
       }
       
       function _decreaseCreditBalance(CreditBalance storage balance, string memory creditType, uint256 amount) internal {
           bytes32 typeHash = keccak256(bytes(creditType));
           if (typeHash == keccak256("signing")) balance.signing -= amount;
           else if (typeHash == keccak256("document_review")) balance.documentReview -= amount;
           else if (typeHash == keccak256("verification")) balance.verification -= amount;
           else if (typeHash == keccak256("trading")) balance.trading -= amount;
           else if (typeHash == keccak256("loaning")) balance.loaning -= amount;
           else if (typeHash == keccak256("borrowing")) balance.borrowing -= amount;
           else if (typeHash == keccak256("compliance_check")) balance.complianceCheck -= amount;
           else if (typeHash == keccak256("securitization")) balance.securitization -= amount;
           else if (typeHash == keccak256("risk_analysis")) balance.riskAnalysis -= amount;
           else if (typeHash == keccak256("quantitative_analysis")) balance.quantitativeAnalysis -= amount;
           else if (typeHash == keccak256("universal")) balance.universal -= amount;
       }
       
       // Override required functions
       function _update(address to, uint256 tokenId, address auth) internal override(ERC721, ERC721Enumerable) returns (address) {
           return super._update(to, tokenId, auth);
       }
       
       function _increaseBalance(address account, uint128 value) internal override(ERC721, ERC721Enumerable) {
           super._increaseBalance(account, value);
       }
       
       function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
           return super.tokenURI(tokenId);
       }
       
       function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721Enumerable, ERC721URIStorage) returns (bool) {
           return super.supportsInterface(interfaceId);
       }
   }
   ```

---

## Project 2: Rolling Credits Subscription Service

### Activity 2.1: Subscription Credit Generation

**File**: `app/services/rolling_credits_service.py` (NEW)

#### Task 2.1.1: Create Rolling Credits Service
**Lines**: 1-800

**Subtasks**:
1. **Line 1-400**: Core service
   ```python
   from typing import Dict, Any, List, Optional, Tuple
   from datetime import datetime, timedelta
   from decimal import Decimal
   from sqlalchemy.orm import Session
   import logging
   
   from app.db.models import (
       CreditBalance, CreditTransaction, UserSubscription,
       Organization, User, UserRole
   )
   from app.services.blockchain_service import BlockchainService
   from app.services.cross_chain_service import CrossChainService
   from app.services.blockchain_router_service import BlockchainRouterService
   
   logger = logging.getLogger(__name__)
   
   
   class RollingCreditsService:
       """Service for managing rolling credits from subscriptions."""
       
      # Tier-based credit allocation per workflow type
      TIER_CREDIT_ALLOCATION = {
          "pro": {
              "signing": 100,  # 100 credits per month
              "document_review": 50,
              "verification": 25,
              "trading": 50,
              "loaning": 25,
              "borrowing": 25,
              "compliance_check": 25,
              "securitization": 10,
              "risk_analysis": 20,
              "quantitative_analysis": 10,
              "stock_prediction_daily": 30,  # 30 daily predictions per month
              "stock_prediction_hourly": 20,  # 20 hourly predictions per month
              "stock_prediction_15min": 10,  # 10 15-minute predictions per month
              "universal": 50
          },
          "premium": {
              "signing": 500,  # 500 credits per month
              "document_review": 250,
              "verification": 150,
              "trading": 200,
              "loaning": 150,
              "borrowing": 150,
              "compliance_check": 100,
              "securitization": 100,
              "risk_analysis": 150,
              "quantitative_analysis": 100,
              "stock_prediction_daily": 200,  # 200 daily predictions per month
              "stock_prediction_hourly": 150,  # 150 hourly predictions per month
              "stock_prediction_15min": 100,  # 100 15-minute predictions per month
              "universal": 200
          }
      }
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_service = BlockchainService()
           self.cross_chain_service = CrossChainService(db)
           self.blockchain_router = BlockchainRouterService(db)
       
       def generate_subscription_credits(
           self,
           user_id: int,
           subscription_id: int,
           tier: str,
           billing_period_start: datetime,
           billing_period_end: datetime
       ) -> Dict[str, Any]:
           """Generate credits from subscription for billing period.
           
           Args:
               user_id: User ID
               subscription_id: Subscription ID
               tier: Subscription tier (pro, premium)
               billing_period_start: Start of billing period
               billing_period_end: End of billing period
               
           Returns:
               Dictionary with credit generation result
           """
           if tier not in ["pro", "premium"]:
               return {
                   "success": False,
                   "error": f"Tier {tier} does not generate credits"
               }
           
           # Get credit allocation for tier
           credit_allocation = self.TIER_CREDIT_ALLOCATION.get(tier, {})
           
           # Get or create credit balance
           balance = self.db.query(CreditBalance).filter(
               CreditBalance.user_id == user_id
           ).first()
           
           if not balance:
               user = self.db.query(User).filter(User.id == user_id).first()
               balance = CreditBalance(
                   user_id=user_id,
                   organization_id=user.organization_id if user else None,
                   balances={},
                   total_balance=Decimal("0")
               )
               self.db.add(balance)
               self.db.commit()
               self.db.refresh(balance)
           
           # Calculate proration if needed
           days_in_period = (billing_period_end - billing_period_start).days + 1
           proration_factor = Decimal(days_in_period) / Decimal(30)  # Assume 30-day month
           
           # Generate credits for each type
           generated_credits = {}
           transactions = []
           
           for credit_type, base_amount in credit_allocation.items():
               prorated_amount = Decimal(str(base_amount)) * proration_factor
               
               # Update balance
               current_balance = Decimal(str(balance.balances.get(credit_type, 0)))
               new_balance = current_balance + prorated_amount
               
               balance.balances[credit_type] = float(new_balance)
               balance.total_balance += prorated_amount
               
               # Update lifetime earned
               lifetime_earned = balance.lifetime_earned or {}
               lifetime_earned[credit_type] = lifetime_earned.get(credit_type, 0) + float(prorated_amount)
               balance.lifetime_earned = lifetime_earned
               
               generated_credits[credit_type] = float(prorated_amount)
               
               # Create transaction
               transaction = CreditTransaction(
                   balance_id=balance.id,
                   user_id=user_id,
                   organization_id=balance.organization_id,
                   transaction_type="subscription",
                   credit_type=credit_type,
                   amount=prorated_amount,
                   balance_before={credit_type: float(current_balance)},
                   balance_after={credit_type: float(new_balance)},
                   subscription_id=subscription_id,
                   description=f"Subscription credits for {tier} tier - {credit_type}",
                   blockchain_verified=False
               )
               self.db.add(transaction)
               transactions.append(transaction)
           
           balance.last_updated = datetime.utcnow()
           self.db.commit()
           
           # Register credits on blockchain
           registration_result = self._register_credits_on_blockchain(balance, generated_credits)
           
           return {
               "success": True,
               "user_id": user_id,
               "subscription_id": subscription_id,
               "tier": tier,
               "generated_credits": generated_credits,
               "total_credits": float(balance.total_balance),
               "blockchain_registered": registration_result.get("registered", False),
               "blockchain_tx_hash": registration_result.get("tx_hash"),
               "transactions": [t.id for t in transactions]
           }
       
       def _register_credits_on_blockchain(
           self,
           balance: CreditBalance,
           new_credits: Dict[str, float]
       ) -> Dict[str, Any]:
           """Register credits on organization blockchain.
           
           Args:
               balance: CreditBalance object
               new_credits: Dictionary of new credits by type
               
           Returns:
               Registration result
           """
           if not balance.organization_id:
               # No organization, skip blockchain registration
               return {"registered": False, "reason": "no_organization"}
           
           try:
               # Get organization blockchain
               org = self.db.query(Organization).filter(
                   Organization.id == balance.organization_id
               ).first()
               
               if not org or not org.blockchain_rpc_url:
                   return {"registered": False, "reason": "no_blockchain"}
               
               # Get blockchain connection
               web3 = self.blockchain_router.get_web3_connection(
                   organization_id=balance.organization_id
               )
               
               # Get credit token contract
               credit_token_address = org.blockchain_contract_addresses.get("CreditToken")
               if not credit_token_address:
                   # Deploy credit token contract if not exists
                   credit_token_address = self._deploy_credit_token_contract(
                       web3=web3,
                       organization_id=balance.organization_id
                   )
                   if not org.blockchain_contract_addresses:
                       org.blockchain_contract_addresses = {}
                   org.blockchain_contract_addresses["CreditToken"] = credit_token_address
                   self.db.commit()
               
               # Get user wallet address
               user = self.db.query(User).filter(User.id == balance.user_id).first()
               if not user or not user.wallet_address:
                   return {"registered": False, "reason": "no_wallet"}
               
               # Check if token already exists
               if balance.blockchain_token_id:
                   # Update existing token
                   tx_hash = self._update_credit_token(
                       web3=web3,
                       contract_address=credit_token_address,
                       token_id=int(balance.blockchain_token_id),
                       credits=new_credits,
                       is_spend=False
                   )
               else:
                   # Mint new token
                   token_id, tx_hash = self._mint_credit_token(
                       web3=web3,
                       contract_address=credit_token_address,
                       user_address=user.wallet_address,
                       credits=balance.balances
                   )
                   balance.blockchain_token_id = str(token_id)
                   balance.blockchain_registered = True
               
               balance.blockchain_tx_hash = tx_hash
               balance.blockchain_chain_id = web3.eth.chain_id
               self.db.commit()
               
               return {
                   "registered": True,
                   "tx_hash": tx_hash,
                   "token_id": balance.blockchain_token_id
               }
               
           except Exception as e:
               logger.error(f"Failed to register credits on blockchain: {e}", exc_info=True)
               return {"registered": False, "error": str(e)}
       
       def _deploy_credit_token_contract(
           self,
           web3,
           organization_id: int
       ) -> str:
           """Deploy CreditToken contract to organization blockchain."""
           # Load contract ABI and bytecode
           from app.services.blockchain_service import BlockchainService
           blockchain_service = BlockchainService()
           
           # Deploy contract
           contract_address = blockchain_service.deploy_contract(
               web3=web3,
               contract_name="CreditToken",
               constructor_args=[]
           )
           
           return contract_address
       
       def _mint_credit_token(
           self,
           web3,
           contract_address: str,
           user_address: str,
           credits: Dict[str, float]
       ) -> Tuple[int, str]:
           """Mint credit token for user."""
           # Convert credits dict to CreditBalance struct
           credit_balance = self._convert_credits_to_struct(credits)
           
           # Call mintCredits function
           contract = web3.eth.contract(address=contract_address, abi=self._get_credit_token_abi())
           
           tx = contract.functions.mintCredits(
               user_address,
               credit_balance
           ).build_transaction({
               'from': web3.eth.default_account,
               'gas': 500000,
               'gasPrice': web3.eth.gas_price,
               'nonce': web3.eth.get_transaction_count(web3.eth.default_account)
           })
           
           signed_tx = web3.eth.account.sign_transaction(tx, private_key=web3.eth.default_account.key)
           tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
           receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
           
           # Extract token ID from event
           token_id = self._extract_token_id_from_receipt(receipt)
           
           return token_id, tx_hash.hex()
       
       def _update_credit_token(
           self,
           web3,
           contract_address: str,
           token_id: int,
           credits: Dict[str, float],
           is_spend: bool
       ) -> str:
           """Update credit token on blockchain."""
           contract = web3.eth.contract(address=contract_address, abi=self._get_credit_token_abi())
           
           # Update each credit type
           tx_hashes = []
           for credit_type, amount in credits.items():
               tx = contract.functions.updateCredits(
                   token_id,
                   credit_type,
                   int(amount * 10000),  # Convert to integer (4 decimals)
                   is_spend
               ).build_transaction({
                   'from': web3.eth.default_account,
                   'gas': 200000,
                   'gasPrice': web3.eth.gas_price,
                   'nonce': web3.eth.get_transaction_count(web3.eth.default_account)
               })
               
               signed_tx = web3.eth.account.sign_transaction(tx, private_key=web3.eth.default_account.key)
               tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
               receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
               tx_hashes.append(tx_hash.hex())
           
           return tx_hashes[0] if tx_hashes else None
   ```

---

## Project 3: Adaptive Pricing Service

### Activity 3.1: Adaptive Cost Calculation

**File**: `app/services/adaptive_pricing_service.py` (NEW)

#### Task 3.1.1: Create Adaptive Pricing Service
**Lines**: 1-600

**Subtasks**:
1. **Line 1-400**: Adaptive pricing service
   ```python
   from typing import Dict, Any, Optional
   from decimal import Decimal
   from datetime import datetime
   from sqlalchemy.orm import Session
   import logging
   
   from app.db.models import CreditTransaction, Organization, User
   
   logger = logging.getLogger(__name__)
   
   
   class AdaptivePricingService:
       """Service for adaptive cost calculation per service."""
       
       # Base costs per workflow (in credits)
       BASE_COSTS = {
           "signing": Decimal("1.0"),
           "document_review": Decimal("2.0"),
           "verification": Decimal("5.0"),
           "trading": Decimal("3.0"),
           "loaning": Decimal("4.0"),
           "borrowing": Decimal("3.0"),
           "compliance_check": Decimal("2.5"),
           "securitization": Decimal("10.0"),
           "risk_analysis": Decimal("5.0"),
           "quantitative_analysis": Decimal("3.0")
       }
       
       # Server-set fees for server transactions
       SERVER_FEES = {
           "trade_execution": Decimal("0.5"),  # 0.5 credits
           "market_creation": Decimal("1.0"),
           "deal_processing": Decimal("2.0"),
           "notarization": Decimal("1.5"),
           "policy_evaluation": Decimal("0.5"),
           "llm_query": Decimal("0.1"),
           "satellite_imagery": Decimal("2.0"),
           "blockchain_transaction": Decimal("0.3")
       }
       
       def __init__(self, db: Session):
           self.db = db
       
       def calculate_adaptive_cost(
           self,
           workflow_type: str,
           user_id: Optional[int] = None,
           organization_id: Optional[int] = None,
           transaction_metadata: Optional[Dict[str, Any]] = None
       ) -> Dict[str, Any]:
           """Calculate adaptive cost for a workflow.
           
           Args:
               workflow_type: Type of workflow
               user_id: User ID (for user-specific pricing)
               organization_id: Organization ID (for org-specific pricing)
               transaction_metadata: Additional metadata (transaction size, complexity, etc.)
               
           Returns:
               Dictionary with cost calculation
           """
           base_cost = self.BASE_COSTS.get(workflow_type, Decimal("1.0"))
           
           # Get pricing factors
           factors = self._get_pricing_factors(
               workflow_type=workflow_type,
               user_id=user_id,
               organization_id=organization_id,
               transaction_metadata=transaction_metadata
           )
           
           # Calculate adaptive cost
           adaptive_cost = base_cost
           
           # Apply factors
           for factor_name, factor_value in factors.items():
               if factor_name == "complexity_multiplier":
                   adaptive_cost *= Decimal(str(factor_value))
               elif factor_name == "volume_discount":
                   adaptive_cost *= (Decimal("1.0") - Decimal(str(factor_value)))
               elif factor_name == "tier_discount":
                   adaptive_cost *= (Decimal("1.0") - Decimal(str(factor_value)))
               elif factor_name == "time_of_day_multiplier":
                   adaptive_cost *= Decimal(str(factor_value))
           
           # Apply min/max bounds
           min_cost = base_cost * Decimal("0.5")  # 50% of base
           max_cost = base_cost * Decimal("2.0")  # 200% of base
           adaptive_cost = max(min_cost, min(adaptive_cost, max_cost))
           
           return {
               "workflow_type": workflow_type,
               "base_cost": float(base_cost),
               "adaptive_cost": float(adaptive_cost),
               "pricing_factors": factors,
               "cost_adjustment": float(adaptive_cost - base_cost),
               "adjustment_percentage": float((adaptive_cost - base_cost) / base_cost * 100)
           }
       
       def _get_pricing_factors(
           self,
           workflow_type: str,
           user_id: Optional[int],
           organization_id: Optional[int],
           transaction_metadata: Optional[Dict[str, Any]]
       ) -> Dict[str, float]:
           """Get pricing factors for adaptive calculation."""
           factors = {}
           
           # Complexity factor (based on transaction metadata)
           if transaction_metadata:
               complexity = transaction_metadata.get("complexity", "medium")
               complexity_multipliers = {
                   "low": 0.8,
                   "medium": 1.0,
                   "high": 1.5,
                   "very_high": 2.0
               }
               factors["complexity_multiplier"] = complexity_multipliers.get(complexity, 1.0)
               
               # Volume factor (discount for high volume)
               volume = transaction_metadata.get("volume", 0)
               if volume > 100:
                   factors["volume_discount"] = 0.1  # 10% discount
               elif volume > 50:
                   factors["volume_discount"] = 0.05  # 5% discount
           
           # Tier factor (discount for premium tier)
           if user_id:
               user = self.db.query(User).filter(User.id == user_id).first()
               if user:
                   # Check subscription tier
                   from app.services.subscription_service import SubscriptionService
                   subscription_service = SubscriptionService(self.db)
                   tier = subscription_service.get_user_tier(user_id)
                   if tier == "premium":
                       factors["tier_discount"] = 0.15  # 15% discount
                   elif tier == "pro":
                       factors["tier_discount"] = 0.05  # 5% discount
           
           # Time of day factor (peak hours cost more)
           current_hour = datetime.utcnow().hour
           if 9 <= current_hour <= 17:  # Business hours
               factors["time_of_day_multiplier"] = 1.1  # 10% premium
           else:
               factors["time_of_day_multiplier"] = 0.9  # 10% discount
           
           # Organization factor (enterprise discounts)
           if organization_id:
               org = self.db.query(Organization).filter(Organization.id == organization_id).first()
               if org and org.subscription_tier == "enterprise":
                   factors["organization_discount"] = 0.2  # 20% discount
           
           return factors
       
       def get_server_fee(
           self,
           service_type: str,
           transaction_metadata: Optional[Dict[str, Any]] = None
       ) -> Decimal:
           """Get server-set fee for server transaction/call.
           
           Args:
               service_type: Type of server service
               transaction_metadata: Additional metadata
               
           Returns:
               Fee in credits
           """
           base_fee = self.SERVER_FEES.get(service_type, Decimal("0.5"))
           
           # Server fees are fixed but can be adjusted based on metadata
           if transaction_metadata:
               # Adjust for transaction size
               size = transaction_metadata.get("size", 0)
               if size > 1000000:  # > 1MB
                   base_fee *= Decimal("1.5")
               elif size > 100000:  # > 100KB
                   base_fee *= Decimal("1.2")
           
           return base_fee
       
       def get_client_call_fee(
           self,
           call_type: str,
           user_id: Optional[int] = None,
           organization_id: Optional[int] = None,
           call_metadata: Optional[Dict[str, Any]] = None
       ) -> Decimal:
           """Get adaptive fee for client-side call (set by server).
           
           Args:
               call_type: Type of client call
               user_id: User ID
               organization_id: Organization ID
               call_metadata: Call metadata
               
           Returns:
               Fee in credits
           """
           # Base fee for client calls (lower than server fees)
           base_fees = {
               "api_call": Decimal("0.1"),
               "data_fetch": Decimal("0.05"),
               "query": Decimal("0.2"),
               "export": Decimal("0.5"),
               "report_generation": Decimal("1.0")
           }
           
           base_fee = base_fees.get(call_type, Decimal("0.1"))
           
           # Apply adaptive factors
           factors = self._get_pricing_factors(
               workflow_type=call_type,
               user_id=user_id,
               organization_id=organization_id,
               transaction_metadata=call_metadata
           )
           
           adaptive_fee = base_fee
           for factor_name, factor_value in factors.items():
               if factor_name.endswith("_multiplier"):
                   adaptive_fee *= Decimal(str(factor_value))
               elif factor_name.endswith("_discount"):
                   adaptive_fee *= (Decimal("1.0") - Decimal(str(factor_value)))
           
           return adaptive_fee
   ```

---

## Project 4: Bridge Credit Verification

### Activity 4.1: Bridge Credit Verification Service

**File**: `app/services/bridge_credit_verification_service.py` (NEW)

#### Task 4.1.1: Create Bridge Verification Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-500**: Bridge verification service
   ```python
   from typing import Dict, Any, Optional
   from decimal import Decimal
   from sqlalchemy.orm import Session
   import logging
   
   from app.db.models import CreditBalance, CreditTransaction, Organization, User
   from app.services.cross_chain_service import CrossChainService
   from app.services.blockchain_router_service import BlockchainRouterService
   
   logger = logging.getLogger(__name__)
   
   
   class BridgeCreditVerificationService:
       """Service for verifying credit usage via blockchain bridge."""
       
       def __init__(self, db: Session):
           self.db = db
           self.cross_chain_service = CrossChainService(db)
           self.blockchain_router = BlockchainRouterService(db)
       
       async def verify_credit_usage(
           self,
           transaction_id: int,
           user_id: int,
           credit_type: str,
           amount: Decimal
       ) -> Dict[str, Any]:
           """Verify credit usage on organization blockchain via bridge.
           
           Args:
               transaction_id: CreditTransaction ID
               user_id: User ID
               credit_type: Type of credit used
               amount: Amount of credits used
               
           Returns:
               Verification result
           """
           transaction = self.db.query(CreditTransaction).filter(
               CreditTransaction.id == transaction_id
           ).first()
           
           if not transaction:
               return {"verified": False, "error": "Transaction not found"}
           
           balance = self.db.query(CreditBalance).filter(
               CreditBalance.id == transaction.balance_id
           ).first()
           
           if not balance or not balance.organization_id:
               return {"verified": False, "error": "No organization blockchain"}
           
           # Get organization blockchain
           org = self.db.query(Organization).filter(
               Organization.id == balance.organization_id
           ).first()
           
           if not org or not org.blockchain_rpc_url:
               return {"verified": False, "error": "Organization blockchain not configured"}
           
           try:
               # Get blockchain connection
               web3 = self.blockchain_router.get_web3_connection(
                   organization_id=balance.organization_id
               )
               
               # Get credit token contract
               credit_token_address = org.blockchain_contract_addresses.get("CreditToken")
               if not credit_token_address:
                   return {"verified": False, "error": "Credit token contract not deployed"}
               
               # Verify credit balance on blockchain
               blockchain_balance = self._get_blockchain_credit_balance(
                   web3=web3,
                   contract_address=credit_token_address,
                   token_id=int(balance.blockchain_token_id),
                   credit_type=credit_type
               )
               
               # Compare with database balance
               db_balance = Decimal(str(balance.balances.get(credit_type, 0)))
               
               if abs(blockchain_balance - db_balance) > Decimal("0.01"):  # Allow small rounding differences
                   logger.warning(
                       f"Credit balance mismatch for user {user_id}: "
                       f"DB={db_balance}, Blockchain={blockchain_balance}"
                   )
                   # Sync from blockchain
                   self._sync_balance_from_blockchain(balance, web3, credit_token_address)
                   return {
                       "verified": True,
                       "synced": True,
                       "blockchain_balance": float(blockchain_balance),
                       "db_balance": float(db_balance)
                   }
               
               # Update transaction with verification
               transaction.blockchain_verified = True
               transaction.blockchain_tx_hash = self._get_latest_tx_hash(web3, credit_token_address)
               self.db.commit()
               
               return {
                   "verified": True,
                   "blockchain_balance": float(blockchain_balance),
                   "db_balance": float(db_balance)
               }
               
           except Exception as e:
               logger.error(f"Failed to verify credit usage: {e}", exc_info=True)
               return {"verified": False, "error": str(e)}
       
       async def convert_credits_via_bridge(
           self,
           user_id: int,
           from_type: str,
           to_type: str,
           amount: Decimal,
           conversion_rate: Optional[Decimal] = None
       ) -> Dict[str, Any]:
           """Convert credits from one type to another via bridge.
           
           Args:
               user_id: User ID
               from_type: Source credit type
               to_type: Target credit type
               amount: Amount to convert
               conversion_rate: Optional conversion rate (default: 1:1)
               
           Returns:
               Conversion result
           """
           balance = self.db.query(CreditBalance).filter(
               CreditBalance.user_id == user_id
           ).first()
           
           if not balance:
               return {"success": False, "error": "Credit balance not found"}
           
           # Check sufficient balance
           from_balance = Decimal(str(balance.balances.get(from_type, 0)))
           if from_balance < amount:
               return {
                   "success": False,
                   "error": f"Insufficient {from_type} credits. Available: {from_balance}, Required: {amount}"
               }
           
           # Calculate conversion
           if conversion_rate is None:
               conversion_rate = Decimal("1.0")  # 1:1 default
           
           converted_amount = amount * conversion_rate
           
           # Update database balances
           balance.balances[from_type] = float(from_balance - amount)
           to_balance = Decimal(str(balance.balances.get(to_type, 0)))
           balance.balances[to_type] = float(to_balance + converted_amount)
           
           # Create conversion transaction
           transaction = CreditTransaction(
               balance_id=balance.id,
               user_id=user_id,
               organization_id=balance.organization_id,
               transaction_type="conversion",
               credit_type=from_type,
               amount=-amount,
               balance_before={from_type: float(from_balance), to_type: float(to_balance)},
               balance_after={from_type: float(from_balance - amount), to_type: float(to_balance + converted_amount)},
               description=f"Converted {amount} {from_type} to {converted_amount} {to_type}",
               metadata={"conversion_rate": float(conversion_rate), "to_type": to_type}
           )
           self.db.add(transaction)
           
           # Update on blockchain via bridge
           bridge_result = await self._update_credits_via_bridge(
               balance=balance,
               credit_type=from_type,
               amount=-amount,
               is_spend=True
           )
           
           if bridge_result.get("success"):
               # Add converted credits
               await self._update_credits_via_bridge(
                   balance=balance,
                   credit_type=to_type,
                   amount=converted_amount,
                   is_spend=False
               )
               
               transaction.blockchain_verified = True
               transaction.bridge_tx_hash = bridge_result.get("bridge_tx_hash")
           
           self.db.commit()
           
           return {
               "success": True,
               "from_type": from_type,
               "to_type": to_type,
               "amount_converted": float(amount),
               "amount_received": float(converted_amount),
               "conversion_rate": float(conversion_rate),
               "blockchain_verified": bridge_result.get("success", False)
           }
       
       async def _update_credits_via_bridge(
           self,
           balance: CreditBalance,
           credit_type: str,
           amount: Decimal,
           is_spend: bool
       ) -> Dict[str, Any]:
           """Update credits on organization blockchain via bridge."""
           try:
               # Get organization blockchain
               org = self.db.query(Organization).filter(
                   Organization.id == balance.organization_id
               ).first()
               
               if not org:
                   return {"success": False, "error": "Organization not found"}
               
               # Send cross-chain message to update credits
               bridge_message = {
                   "type": "credit_update",
                   "token_id": balance.blockchain_token_id,
                   "credit_type": credit_type,
                   "amount": float(amount),
                   "is_spend": is_spend
               }
               
               bridge_result = await self.cross_chain_service.send_cross_chain_message(
                   from_organization_id=balance.organization_id,
                   to_organization_id=None,  # To CreditNexus main chain
                   message_type="credit_update",
                   payload=bridge_message
               )
               
               return {
                   "success": True,
                   "bridge_tx_hash": bridge_result.get("source_tx_hash")
               }
               
           except Exception as e:
               logger.error(f"Failed to update credits via bridge: {e}", exc_info=True)
               return {"success": False, "error": str(e)}
       
       def _get_blockchain_credit_balance(
           self,
           web3,
           contract_address: str,
           token_id: int,
           credit_type: str
       ) -> Decimal:
           """Get credit balance from blockchain."""
           contract = web3.eth.contract(address=contract_address, abi=self._get_credit_token_abi())
           balance = contract.functions.getCreditBalance(token_id, credit_type).call()
           return Decimal(balance) / Decimal(10000)  # Convert from integer (4 decimals)
       
       def _sync_balance_from_blockchain(
           self,
           balance: CreditBalance,
           web3,
           contract_address: str
       ) -> None:
           """Sync credit balance from blockchain to database."""
           token_id = int(balance.blockchain_token_id)
           all_credits = contract.functions.getAllCredits(token_id).call()
           
           # Update database balances
           balance.balances = {
               "signing": float(all_credits[0]) / 10000,
               "document_review": float(all_credits[1]) / 10000,
               "verification": float(all_credits[2]) / 10000,
               "trading": float(all_credits[3]) / 10000,
               "loaning": float(all_credits[4]) / 10000,
               "borrowing": float(all_credits[5]) / 10000,
               "compliance_check": float(all_credits[6]) / 10000,
               "securitization": float(all_credits[7]) / 10000,
               "risk_analysis": float(all_credits[8]) / 10000,
               "quantitative_analysis": float(all_credits[9]) / 10000,
               "universal": float(all_credits[10]) / 10000
           }
           
           balance.total_balance = sum(Decimal(str(v)) for v in balance.balances.values())
           self.db.commit()
   ```

---

## Project 5: Subscription Credit Generation Integration

### Activity 5.1: Subscription Service Integration

**File**: `app/services/subscription_service.py` (UPDATE)

#### Task 5.1.1: Add Credit Generation to Subscriptions
**Lines**: ~200-400

**Subtasks**:
1. **Line 200-400**: Credit generation integration
   ```python
   def activate_subscription(
       self,
       user_id: int,
       tier: str,
       subscription_type: str,
       payment_event_id: Optional[int] = None
   ) -> UserSubscription:
       """Activate subscription and generate initial credits."""
       from app.services.rolling_credits_service import RollingCreditsService
       from datetime import datetime, timedelta
       
       # Create subscription
       subscription = UserSubscription(
           user_id=user_id,
           tier=tier,
           subscription_type=subscription_type,
           is_active=True,
           started_at=datetime.utcnow()
       )
       
       if subscription_type == "lifetime":
           subscription.expires_at = None
       elif subscription_type == "monthly":
           subscription.expires_at = datetime.utcnow() + timedelta(days=30)
       elif subscription_type == "yearly":
           subscription.expires_at = datetime.utcnow() + timedelta(days=365)
       
       subscription.payment_event_id = payment_event_id
       self.db.add(subscription)
       self.db.commit()
       self.db.refresh(subscription)
       
       # Generate credits for PRO and Premium tiers
       if tier in ["pro", "premium"]:
           rolling_credits_service = RollingCreditsService(self.db)
           
           # Calculate billing period
           period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
           if period_start.month == 12:
               period_end = datetime(period_start.year + 1, 1, 1) - timedelta(days=1)
           else:
               period_end = datetime(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
           
           # Generate credits
           credit_result = rolling_credits_service.generate_subscription_credits(
               user_id=user_id,
               subscription_id=subscription.id,
               tier=tier,
               billing_period_start=period_start,
               billing_period_end=period_end
           )
           
           if credit_result.get("success"):
               logger.info(
                   f"Generated {credit_result.get('total_credits')} credits for user {user_id} "
                   f"subscription {subscription.id}"
               )
       
       return subscription
   
   def renew_subscription(
       self,
       subscription_id: int,
       payment_event_id: Optional[int] = None
   ) -> UserSubscription:
       """Renew subscription and generate credits for new period."""
       from app.services.rolling_credits_service import RollingCreditsService
       from datetime import datetime, timedelta
       
       subscription = self.db.query(UserSubscription).filter(
           UserSubscription.id == subscription_id
       ).first()
       
       if not subscription:
           raise ValueError(f"Subscription {subscription_id} not found")
       
       # Update expiration
       if subscription.subscription_type == "monthly":
           subscription.expires_at = datetime.utcnow() + timedelta(days=30)
       elif subscription.subscription_type == "yearly":
           subscription.expires_at = datetime.utcnow() + timedelta(days=365)
       
       subscription.payment_event_id = payment_event_id
       self.db.commit()
       
       # Generate credits for new period
       if subscription.tier in ["pro", "premium"]:
           rolling_credits_service = RollingCreditsService(self.db)
           
           period_start = subscription.expires_at - timedelta(days=30 if subscription.subscription_type == "monthly" else 365)
           period_end = subscription.expires_at
           
           credit_result = rolling_credits_service.generate_subscription_credits(
               user_id=subscription.user_id,
               subscription_id=subscription.id,
               tier=subscription.tier,
               billing_period_start=period_start,
               billing_period_end=period_end
           )
           
           if credit_result.get("success"):
               logger.info(
                   f"Generated {credit_result.get('total_credits')} credits for renewed subscription {subscription_id}"
               )
       
       return subscription
   ```

---

## Implementation Checklist

### Phase 1: Credit Types & Models (Week 1-2)
- [ ] Add CreditType enum
- [ ] Update CreditBalance model with type support
- [ ] Update CreditTransaction model with type support
- [ ] Add blockchain registration fields
- [ ] Create Alembic migration

### Phase 2: Credit Token Contract (Week 2-3)
- [ ] Create CreditToken.sol contract
- [ ] Deploy contract to testnet
- [ ] Test credit minting and updates
- [ ] Integrate with organization blockchain deployment

### Phase 3: Rolling Credits Service (Week 3-4)
- [ ] Create RollingCreditsService
- [ ] Implement subscription credit generation
- [ ] Implement blockchain registration
- [ ] Add tier-based credit allocation
- [ ] Test credit generation flow

### Phase 4: Adaptive Pricing (Week 4-5)
- [ ] Create AdaptivePricingService
- [ ] Implement adaptive cost calculation
- [ ] Implement server fee setting
- [ ] Implement client call fee setting
- [ ] Add pricing factors (complexity, volume, tier, time)

### Phase 5: Bridge Verification (Week 5-6)
- [ ] Create BridgeCreditVerificationService
- [ ] Implement credit usage verification
- [ ] Implement credit conversion via bridge
- [ ] Add balance synchronization
- [ ] Test bridge operations

### Phase 6: Subscription Integration (Week 6-7)
- [ ] Integrate credit generation with subscription activation
- [ ] Integrate credit generation with subscription renewal
- [ ] Add automatic credit generation on billing period
- [ ] Test subscription credit flow

### Phase 7: API Endpoints & UI (Week 7-8)
- [ ] Create credits API endpoints
- [ ] Add credit balance display
- [ ] Add credit transaction history
- [ ] Add credit conversion UI
- [ ] Add adaptive pricing display

### Phase 8: Testing & Optimization (Week 8-10)
- [ ] Test all credit workflows
- [ ] Test blockchain registration
- [ ] Test bridge verification
- [ ] Test adaptive pricing
- [ ] Performance optimization
- [ ] Documentation

---

## Key Design Decisions

### 1. Credit Types
- **11 credit types** for different workflows
- **Universal credits** can be converted to any type
- **Type-specific credits** prevent misuse (e.g., can't use signing credits for securitization)

### 2. Blockchain Registration
- Credits registered as **ERC-721 NFTs** on organization blockchain
- Each user gets **one token** with all credit types
- **Bridge** used to sync with CreditNexus main chain for verification

### 3. Adaptive Pricing
- **Base costs** per workflow type
- **Adaptive factors**: complexity, volume, tier, time of day, organization
- **Server fees** fixed but adjustable
- **Client call fees** adaptive based on factors

### 4. Rolling Credits
- **PRO tier**: 100-50 credits per workflow type per month
- **Premium tier**: 500-100 credits per workflow type per month
- **Automatic generation** on subscription activation/renewal
- **Prorated** for partial periods

### 5. Bridge Verification
- **Server verifies** credit usage on organization blockchain
- **Bridge messages** for cross-chain credit updates
- **Balance synchronization** if mismatch detected

---

## Success Criteria

1. ✅ PRO and Premium subscriptions generate credits automatically
2. ✅ Credits registered on organization blockchain
3. ✅ Bridge verification for credit usage
4. ✅ Adaptive cost calculation per service
5. ✅ Server-set fees for server transactions
6. ✅ Adaptive fees for client-side calls
7. ✅ Different credit types per workflow
8. ✅ Tier-based credit allocation
9. ✅ Credit conversion via bridge
10. ✅ Complete integration with billing system

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
