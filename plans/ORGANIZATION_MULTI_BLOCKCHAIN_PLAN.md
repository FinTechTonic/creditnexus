# Organization-Based Multi-Blockchain Architecture Plan
## Registered Organizations with Per-Organization Blockchains and Cross-Chain Communication

**Status**: Comprehensive Architecture Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 12-16 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan transforms CreditNexus into a **multi-tenant, multi-blockchain platform** where:
1. **Organization Registration**: All users must be attached to a registered organization during signup
2. **Per-Organization Blockchains**: Each organization has its own blockchain instance (private chain, sidechain, or L2)
3. **Cross-Chain Communication**: Organizations can communicate with the CreditNexus main blockchain via bridge contracts
4. **User Routing**: Users are automatically routed to their organization's blockchain for all operations
5. **Unified Interface**: Single CreditNexus interface that abstracts blockchain complexity

---

## Current State Analysis

### Existing Infrastructure

**Blockchain**:
- **Location**: `app/services/blockchain_service.py`
- **Current**: Single blockchain connection (Base network via `X402_NETWORK_RPC_URL`)
- **Smart Contracts**: `SecuritizationNotarization.sol` deployed on Base
- **Services**: `NotarizationService`, `BlockchainService`
- **Gap**: No organization-level blockchain routing

**User Model**:
- **Location**: `app/db/models.py` (User model)
- **Current**: Users have `profile_data` JSONB with optional company info
- **Gap**: No formal `Organization` model or `organization_id` foreign key

**Signup Flow**:
- **Location**: `client/src/components/SignupFlow.tsx`
- **Current**: Users select role but no organization selection
- **Gap**: No organization attachment during signup

---

## Architecture Overview

### Multi-Blockchain Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CreditNexus Platform                     │
│                  (Unified User Interface)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Routes users to org blockchain
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Org A       │    │  Org B       │    │  Org C       │
│  Blockchain  │    │  Blockchain  │    │  Blockchain  │
│  (Private)   │    │  (Sidechain) │    │  (L2)        │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  CreditNexus Main     │
                │  Blockchain (Base)    │
                │  (Bridge Contracts)   │
                └───────────────────────┘
```

### Cross-Chain Communication Flow

```
Organization Blockchain → Bridge Contract → CreditNexus Main Chain
                                 ↓
                    Cross-Chain Message Relay
                                 ↓
CreditNexus Main Chain → Bridge Contract → Organization Blockchain
```

---

## Project 1: Organization Model & Registration

### Activity 1.1: Database Models

**File**: `app/db/models.py` (UPDATE)

#### Task 1.1.1: Create Organization Model
**Lines**: ~2800-3000

**Subtasks**:
1. **Line 2800-3000**: Organization model
   ```python
   class Organization(Base):
       """Registered organization model."""
       __tablename__ = "organizations"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Organization identification
       name = Column(String(255), nullable=False, index=True)
       legal_name = Column(EncryptedString(500), nullable=False)  # Encrypted PII
       registration_number = Column(EncryptedString(100), nullable=True, unique=True, index=True)  # Encrypted PII
       tax_id = Column(EncryptedString(100), nullable=True)  # Encrypted PII
       lei = Column(EncryptedString(20), nullable=True, unique=True, index=True)  # Legal Entity Identifier - Encrypted PII
       
       # Organization details
       industry = Column(String(100), nullable=True)
       country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
       website = Column(String(500), nullable=True)
       email = Column(EncryptedString(255), nullable=True)  # Encrypted PII
       
       # Blockchain configuration
       blockchain_type = Column(String(50), nullable=False, default="private")  # private, sidechain, l2, mainnet
       blockchain_network = Column(String(100), nullable=True)  # Network name/identifier
       blockchain_rpc_url = Column(EncryptedString(500), nullable=True)  # Encrypted - RPC endpoint
       blockchain_chain_id = Column(Integer, nullable=True)  # Chain ID
       blockchain_contract_addresses = Column(JSONB, nullable=True)  # Organization's contract addresses
       
       # Bridge configuration (for cross-chain communication)
       bridge_contract_address = Column(String(255), nullable=True)  # Bridge contract on CreditNexus main chain
       bridge_status = Column(String(20), default="pending", nullable=False)  # pending, active, suspended
       
       # Organization status
       status = Column(String(20), default="pending", nullable=False, index=True)  # pending, active, suspended, terminated
       registration_date = Column(DateTime, nullable=True)
       approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
       approved_at = Column(DateTime, nullable=True)
       
       # Subscription & billing
       subscription_tier = Column(String(20), default="free", nullable=False)  # free, pro, premium, lifetime, enterprise
       subscription_expires_at = Column(DateTime, nullable=True)
       
       # Metadata
       metadata = Column(JSONB, nullable=True)  # Additional organization data
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       users = relationship("User", back_populates="organization")
       admin_users = relationship("User", foreign_keys=[approved_by])
       blockchain_deployments = relationship("OrganizationBlockchainDeployment", back_populates="organization")
       cross_chain_transactions = relationship("CrossChainTransaction", back_populates="organization")
       
       def to_dict(self):
           """Convert model to dictionary."""
           return {
               "id": self.id,
               "name": self.name,
               "legal_name": self.legal_name,
               "registration_number": self.registration_number,
               "lei": self.lei,
               "industry": self.industry,
               "country": self.country,
               "blockchain_type": self.blockchain_type,
               "blockchain_network": self.blockchain_network,
               "bridge_contract_address": self.bridge_contract_address,
               "bridge_status": self.bridge_status,
               "status": self.status,
               "subscription_tier": self.subscription_tier,
               "created_at": self.created_at.isoformat() if self.created_at else None,
           }
   
   class OrganizationBlockchainDeployment(Base):
       """Tracks blockchain deployments for organizations."""
       __tablename__ = "organization_blockchain_deployments"
       
       id = Column(Integer, primary_key=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
       
       # Deployment details
       deployment_type = Column(String(50), nullable=False)  # private_chain, sidechain, l2, testnet
       network_name = Column(String(100), nullable=False)
       rpc_url = Column(EncryptedString(500), nullable=False)  # Encrypted
       chain_id = Column(Integer, nullable=False)
       
       # Contract addresses
       notarization_contract = Column(String(255), nullable=True)
       token_contract = Column(String(255), nullable=True)
       payment_router_contract = Column(String(255), nullable=True)
       bridge_contract = Column(String(255), nullable=True)  # Bridge contract on org chain
       
       # Deployment status
       status = Column(String(20), default="pending", nullable=False)  # pending, deploying, active, failed
       deployed_at = Column(DateTime, nullable=True)
       deployed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
       
       # Deployment metadata
       deployment_metadata = Column(JSONB, nullable=True)  # Deployment logs, gas costs, etc.
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       organization = relationship("Organization", back_populates="blockchain_deployments")
       deployer = relationship("User", foreign_keys=[deployed_by])
   
   class CrossChainTransaction(Base):
       """Tracks cross-chain transactions between organization and CreditNexus main chain."""
       __tablename__ = "cross_chain_transactions"
       
       id = Column(Integer, primary_key=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
       
       # Transaction details
       transaction_type = Column(String(50), nullable=False)  # notarization, payment, data_sync, etc.
       direction = Column(String(20), nullable=False)  # org_to_main, main_to_org
       
       # Source chain
       source_chain = Column(String(100), nullable=False)
       source_tx_hash = Column(String(255), nullable=False, index=True)
       source_block_number = Column(Integer, nullable=True)
       
       # Destination chain
       dest_chain = Column(String(100), nullable=False)
       dest_tx_hash = Column(String(255), nullable=True, index=True)
       dest_block_number = Column(Integer, nullable=True)
       
       # Bridge details
       bridge_contract_address = Column(String(255), nullable=True)
       bridge_tx_hash = Column(String(255), nullable=True)
       
       # Transaction data
       transaction_data = Column(JSONB, nullable=True)  # CDM payload, metadata, etc.
       
       # Status
       status = Column(String(20), default="pending", nullable=False, index=True)  # pending, confirmed, failed
       confirmed_at = Column(DateTime, nullable=True)
       
       # Error handling
       error_message = Column(Text, nullable=True)
       retry_count = Column(Integer, default=0, nullable=False)
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       organization = relationship("Organization", back_populates="cross_chain_transactions")
   ```

2. **Line 3001-3100**: Update User model
   ```python
   # In User model, add:
   organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
   
   # Add relationship:
   organization = relationship("Organization", back_populates="users")
   
   # Add helper method:
   def get_blockchain_rpc_url(self) -> Optional[str]:
       """Get organization's blockchain RPC URL."""
       if self.organization and self.organization.blockchain_rpc_url:
           return self.organization.blockchain_rpc_url
       return None  # Fallback to CreditNexus main chain
   ```

---

## Project 2: Organization Registration & Onboarding

### Activity 2.1: Organization Registration Service

**File**: `app/services/organization_service.py` (NEW)

#### Task 2.1.1: Create Organization Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-200**: Service class
   ```python
   class OrganizationService:
       """Service for managing organizations and their blockchain deployments."""
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_service = BlockchainService()
       
       async def register_organization(
           self,
           name: str,
           legal_name: str,
           registration_number: Optional[str] = None,
           tax_id: Optional[str] = None,
           lei: Optional[str] = None,
           industry: Optional[str] = None,
           country: Optional[str] = None,
           website: Optional[str] = None,
           email: Optional[str] = None,
           blockchain_type: str = "private",
           registered_by_user_id: Optional[int] = None
       ) -> Organization:
           """Register a new organization.
           
           Args:
               name: Organization name
               legal_name: Legal entity name
               registration_number: Business registration number
               tax_id: Tax identification number
               lei: Legal Entity Identifier
               industry: Industry sector
               country: ISO country code
               website: Organization website
               email: Organization contact email
               blockchain_type: Type of blockchain (private, sidechain, l2, mainnet)
               registered_by_user_id: User ID of registrant
               
           Returns:
               Created Organization
           """
           # Check for duplicate LEI or registration number
           if lei:
               existing = self.db.query(Organization).filter(
                   Organization.lei == lei
               ).first()
               if existing:
                   raise ValueError(f"Organization with LEI {lei} already exists")
           
           if registration_number:
               existing = self.db.query(Organization).filter(
                   Organization.registration_number == registration_number
               ).first()
               if existing:
                   raise ValueError(f"Organization with registration number {registration_number} already exists")
           
           # Create organization
           org = Organization(
               name=name,
               legal_name=legal_name,
               registration_number=registration_number,
               tax_id=tax_id,
               lei=lei,
               industry=industry,
               country=country,
               website=website,
               email=email,
               blockchain_type=blockchain_type,
               status="pending",
               registration_date=datetime.utcnow()
           )
           
           self.db.add(org)
           self.db.commit()
           self.db.refresh(org)
           
           # Log registration
           if registered_by_user_id:
               log_audit_action(
                   self.db,
                   AuditAction.CREATE,
                   "organization",
                   org.id,
                   registered_by_user_id,
                   metadata={"blockchain_type": blockchain_type}
               )
           
           return org
       
       async def approve_organization(
           self,
           organization_id: int,
           approved_by_user_id: int,
           blockchain_config: Optional[Dict[str, Any]] = None
       ) -> Organization:
           """Approve organization registration and optionally deploy blockchain.
           
           Args:
               organization_id: Organization ID
               approved_by_user_id: User ID of approver
               blockchain_config: Optional blockchain deployment configuration
               
           Returns:
               Updated Organization
           """
           org = self.db.query(Organization).filter(
               Organization.id == organization_id
           ).first()
           
           if not org:
               raise ValueError(f"Organization {organization_id} not found")
           
           org.status = "active"
           org.approved_by = approved_by_user_id
           org.approved_at = datetime.utcnow()
           
           # Deploy blockchain if configured
           if blockchain_config:
               deployment = await self.deploy_organization_blockchain(
                   organization_id=organization_id,
                   deployment_type=blockchain_config.get("type", "private"),
                   deployed_by_user_id=approved_by_user_id
               )
               org.blockchain_network = deployment.network_name
               org.blockchain_rpc_url = deployment.rpc_url
               org.blockchain_chain_id = deployment.chain_id
               org.blockchain_contract_addresses = {
                   "notarization": deployment.notarization_contract,
                   "token": deployment.token_contract,
                   "payment_router": deployment.payment_router_contract,
                   "bridge": deployment.bridge_contract
               }
           
           self.db.commit()
           self.db.refresh(org)
           
           return org
   ```

2. **Line 201-400**: Blockchain deployment
   ```python
       async def deploy_organization_blockchain(
           self,
           organization_id: int,
           deployment_type: str = "private",
           deployed_by_user_id: Optional[int] = None
       ) -> OrganizationBlockchainDeployment:
           """Deploy blockchain infrastructure for organization.
           
           Args:
               organization_id: Organization ID
               deployment_type: Type of deployment (private_chain, sidechain, l2, testnet)
               deployed_by_user_id: User ID of deployer
               
           Returns:
               Deployment record
           """
           org = self.db.query(Organization).filter(
               Organization.id == organization_id
           ).first()
           
           if not org:
               raise ValueError(f"Organization {organization_id} not found")
           
           # Create deployment record
           deployment = OrganizationBlockchainDeployment(
               organization_id=organization_id,
               deployment_type=deployment_type,
               network_name=f"{org.name.lower().replace(' ', '_')}_chain",
               status="deploying",
               deployed_by=deployed_by_user_id
           )
           
           self.db.add(deployment)
           self.db.commit()
           
           try:
               # Deploy based on type
               if deployment_type == "private":
                   # Deploy private blockchain (e.g., using Hyperledger Besu, Quorum)
                   result = await self._deploy_private_chain(org, deployment)
               elif deployment_type == "sidechain":
                   # Deploy sidechain (e.g., Polygon, Arbitrum)
                   result = await self._deploy_sidechain(org, deployment)
               elif deployment_type == "l2":
                   # Deploy L2 solution (e.g., Optimism, zkSync)
                   result = await self._deploy_l2(org, deployment)
               else:
                   raise ValueError(f"Unsupported deployment type: {deployment_type}")
               
               # Update deployment with results
               deployment.rpc_url = result["rpc_url"]
               deployment.chain_id = result["chain_id"]
               deployment.notarization_contract = result.get("notarization_contract")
               deployment.token_contract = result.get("token_contract")
               deployment.payment_router_contract = result.get("payment_router_contract")
               deployment.bridge_contract = result.get("bridge_contract")
               deployment.status = "active"
               deployment.deployed_at = datetime.utcnow()
               deployment.deployment_metadata = result.get("metadata", {})
               
               # Deploy bridge contract on CreditNexus main chain
               bridge_address = await self._deploy_bridge_contract(
                   organization_id=organization_id,
                   org_chain_id=deployment.chain_id,
                   org_bridge_contract=deployment.bridge_contract
               )
               
               # Update organization with bridge address
               org.bridge_contract_address = bridge_address
               org.bridge_status = "active"
               
           except Exception as e:
               deployment.status = "failed"
               deployment.deployment_metadata = {"error": str(e)}
               logger.error(f"Failed to deploy blockchain for org {organization_id}: {e}")
               raise
           
           self.db.commit()
           self.db.refresh(deployment)
           
           return deployment
   ```

### Activity 2.2: Organization Selection in Signup

**File**: `client/src/components/SignupFlow.tsx` (UPDATE)

#### Task 2.2.1: Add Organization Selection Step
**Lines**: ~44-50 (STEPS array), ~160-200 (renderStepContent)

**Subtasks**:
1. **Line 44-50**: Update STEPS array
   ```typescript
   const STEPS = [
     { id: 0, title: 'Organization Selection', description: 'Select or register your organization' },  // NEW
     { id: 1, title: 'AI Profile Extraction', description: 'Extract profile data using AI' },
     { id: 2, title: 'Basic Information', description: 'Email, password, and role selection' },
     { id: 3, title: 'Profile Enrichment', description: 'Complete your profile information' },
     { id: 4, title: 'KYC Verification', description: 'Complete KYC compliance and upload documents' },
     { id: 5, title: 'License Upload', description: 'Upload required licenses (role-specific)' },
     { id: 6, title: 'Review & Submit', description: 'Review your information and complete signup' },
   ];
   ```

2. **Line 160-200**: Add organization selection step
   ```typescript
   case 0:
     return (
       <div className="space-y-6">
         <OrganizationSelectionStep
           onSelect={(orgId) => {
             updateFormData({ organizationId: orgId });
             handleNext();
           }}
           onRegister={(orgData) => {
             // Handle organization registration
             registerOrganization(orgData).then((org) => {
               updateFormData({ organizationId: org.id });
               handleNext();
             });
           }}
         />
       </div>
     );
   ```

### Activity 2.3: Organization Selection Component

**File**: `client/src/components/onboarding/OrganizationSelectionStep.tsx` (NEW)

#### Task 2.3.1: Create Organization Selection Component
**Lines**: 1-400

**Subtasks**:
1. **Line 1-200**: Component with search and registration
   ```typescript
   import { useState, useEffect } from 'react';
   import { Search, Building2, Plus, CheckCircle2 } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   import { Input } from '@/components/ui/input';
   
   interface OrganizationSelectionStepProps {
     onSelect: (organizationId: number) => void;
     onRegister: (orgData: OrganizationData) => void;
   }
   
   interface OrganizationData {
     name: string;
     legal_name: string;
     registration_number?: string;
     lei?: string;
     industry?: string;
     country?: string;
   }
   
   export function OrganizationSelectionStep({
     onSelect,
     onRegister
   }: OrganizationSelectionStepProps) {
     const [searchQuery, setSearchQuery] = useState('');
     const [organizations, setOrganizations] = useState<any[]>([]);
     const [loading, setLoading] = useState(false);
     const [showRegisterForm, setShowRegisterForm] = useState(false);
     const [selectedOrg, setSelectedOrg] = useState<number | null>(null);
     
     useEffect(() => {
       if (searchQuery.length >= 2) {
         searchOrganizations(searchQuery);
       }
     }, [searchQuery]);
     
     const searchOrganizations = async (query: string) => {
       setLoading(true);
       try {
         const response = await fetchWithAuth(`/api/organizations/search?q=${encodeURIComponent(query)}`);
         if (response.ok) {
           const data = await response.json();
           setOrganizations(data.organizations || []);
         }
       } catch (error) {
         console.error('Organization search error:', error);
       } finally {
         setLoading(false);
       }
     };
     
     return (
       <div className="space-y-6">
         <div className="text-center mb-6">
           <h3 className="text-xl font-semibold text-slate-100 mb-2">
             Select Your Organization
           </h3>
           <p className="text-slate-400">
             Search for your organization or register a new one
           </p>
         </div>
         
         <div className="space-y-4">
           <div className="relative">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
             <Input
               type="text"
               placeholder="Search organizations by name, LEI, or registration number..."
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               className="pl-10"
             />
           </div>
           
           {organizations.length > 0 && (
             <div className="space-y-2 max-h-64 overflow-y-auto">
               {organizations.map((org) => (
                 <Card
                   key={org.id}
                   className={`p-4 cursor-pointer transition-all ${
                     selectedOrg === org.id
                       ? 'border-emerald-500 bg-emerald-500/10'
                       : 'border-slate-600 hover:border-slate-500'
                   }`}
                   onClick={() => setSelectedOrg(org.id)}
                 >
                   <div className="flex items-center justify-between">
                     <div>
                       <div className="font-semibold text-slate-100">{org.name}</div>
                       {org.lei && (
                         <div className="text-sm text-slate-400">LEI: {org.lei}</div>
                       )}
                       {org.industry && (
                         <div className="text-sm text-slate-400">{org.industry}</div>
                       )}
                     </div>
                     {selectedOrg === org.id && (
                       <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                     )}
                   </div>
                 </Card>
               ))}
             </div>
           )}
           
           <Button
             variant="outline"
             className="w-full"
             onClick={() => setShowRegisterForm(!showRegisterForm)}
           >
             <Plus className="h-4 w-4 mr-2" />
             Register New Organization
           </Button>
           
           {showRegisterForm && (
             <OrganizationRegistrationForm
               onSubmit={(orgData) => {
                 onRegister(orgData);
                 setShowRegisterForm(false);
               }}
               onCancel={() => setShowRegisterForm(false)}
             />
           )}
           
           {selectedOrg && (
             <Button
               onClick={() => onSelect(selectedOrg)}
               className="w-full"
             >
               Continue with Selected Organization
             </Button>
           )}
         </div>
       </div>
     );
   }
   ```

---

## Project 3: Multi-Blockchain Routing Service

### Activity 3.1: Blockchain Router Service

**File**: `app/services/blockchain_router_service.py` (NEW)

#### Task 3.1.1: Create Router Service
**Lines**: 1-400

**Subtasks**:
1. **Line 1-200**: Router service class
   ```python
   class BlockchainRouterService:
       """Service for routing blockchain operations to organization-specific blockchains."""
       
       def __init__(self, db: Session):
           self.db = db
           self._web3_connections = {}  # Cache Web3 connections per organization
       
       def get_user_blockchain(
           self,
           user_id: int
       ) -> Optional[Dict[str, Any]]:
           """Get blockchain configuration for user's organization.
           
           Args:
               user_id: User ID
               
           Returns:
               Blockchain configuration dict or None (fallback to main chain)
           """
           user = self.db.query(User).filter(User.id == user_id).first()
           if not user or not user.organization_id:
               return None  # Fallback to CreditNexus main chain
           
           org = self.db.query(Organization).filter(
               Organization.id == user.organization_id
           ).first()
           
           if not org or org.status != "active":
               return None
           
           return {
               "organization_id": org.id,
               "blockchain_type": org.blockchain_type,
               "rpc_url": org.blockchain_rpc_url,
               "chain_id": org.blockchain_chain_id,
               "contract_addresses": org.blockchain_contract_addresses,
               "bridge_contract_address": org.bridge_contract_address
           }
       
       def get_web3_connection(
           self,
           organization_id: Optional[int] = None,
           rpc_url: Optional[str] = None
       ):
           """Get or create Web3 connection for organization.
           
           Args:
               organization_id: Organization ID (for caching)
               rpc_url: RPC URL (if not provided, uses organization's RPC)
               
           Returns:
               Web3 instance
           """
           from web3 import Web3
           
           # Use organization's RPC if provided
           if organization_id and not rpc_url:
               org = self.db.query(Organization).filter(
                   Organization.id == organization_id
               ).first()
               if org and org.blockchain_rpc_url:
                   rpc_url = org.blockchain_rpc_url
           
           # Fallback to CreditNexus main chain
           if not rpc_url:
               from app.core.config import settings
               rpc_url = settings.X402_NETWORK_RPC_URL
           
           # Cache connection
           cache_key = rpc_url
           if cache_key not in self._web3_connections:
               self._web3_connections[cache_key] = Web3(Web3.HTTPProvider(rpc_url))
           
           return self._web3_connections[cache_key]
       
       async def route_notarization(
           self,
           user_id: int,
           deal_id: int,
           required_signers: List[str]
       ) -> Dict[str, Any]:
           """Route notarization to user's organization blockchain.
           
           Args:
               user_id: User ID
               deal_id: Deal ID
               required_signers: List of signer addresses
               
           Returns:
               Notarization result
           """
           blockchain_config = self.get_user_blockchain(user_id)
           
           if blockchain_config:
               # Use organization's blockchain
               return await self._notarize_on_org_blockchain(
                   blockchain_config=blockchain_config,
                   deal_id=deal_id,
                   required_signers=required_signers
               )
           else:
               # Use CreditNexus main chain
               return await self._notarize_on_main_chain(
                   deal_id=deal_id,
                   required_signers=required_signers
               )
   ```

---

## Project 4: Cross-Chain Bridge Contracts

### Activity 4.1: Bridge Smart Contract

**File**: `contracts/CrossChainBridge.sol` (NEW)

#### Task 4.1.1: Create Bridge Contract
**Lines**: 1-300

**Subtasks**:
1. **Line 1-300**: Bridge contract
   ```solidity
   // SPDX-License-Identifier: MIT
   pragma solidity ^0.8.20;
   
   /**
    * @title CrossChainBridge
    * @dev Bridge contract for cross-chain communication between organization blockchains and CreditNexus main chain
    */
   contract CrossChainBridge {
       struct Message {
           uint256 messageId;
           address fromOrganization;
           uint256 fromChainId;
           address toOrganization;
           uint256 toChainId;
           bytes payload;
           uint256 timestamp;
           bool executed;
       }
       
       mapping(uint256 => Message) public messages;
       mapping(address => bool) public authorizedRelayers;
       uint256 public messageCounter;
       
       event MessageSent(
           uint256 indexed messageId,
           address indexed fromOrganization,
           uint256 fromChainId,
           address indexed toOrganization,
           uint256 toChainId
       );
       
       event MessageExecuted(
           uint256 indexed messageId,
           bool success
       );
       
       modifier onlyAuthorized() {
           require(authorizedRelayers[msg.sender], "Not authorized");
           _;
       }
       
       function sendMessage(
           address toOrganization,
           uint256 toChainId,
           bytes calldata payload
       ) external returns (uint256) {
           messageCounter++;
           
           messages[messageCounter] = Message({
               messageId: messageCounter,
               fromOrganization: msg.sender,
               fromChainId: block.chainid,
               toOrganization: toOrganization,
               toChainId: toChainId,
               payload: payload,
               timestamp: block.timestamp,
               executed: false
           });
           
           emit MessageSent(
               messageCounter,
               msg.sender,
               block.chainid,
               toOrganization,
               toChainId
           );
           
           return messageCounter;
       }
       
       function executeMessage(
           uint256 messageId,
           bytes calldata proof
       ) external onlyAuthorized {
           Message storage message = messages[messageId];
           require(!message.executed, "Message already executed");
           
           // Verify proof (simplified - in production, use proper cross-chain verification)
           // This would typically use Merkle proofs, oracle verification, etc.
           
           message.executed = true;
           
           // Execute payload (call target contract)
           (bool success, ) = message.toOrganization.call(message.payload);
           
           emit MessageExecuted(messageId, success);
       }
   }
   ```

---

## Project 5: Cross-Chain Communication Service

### Activity 5.1: Cross-Chain Service

**File**: `app/services/cross_chain_service.py` (NEW)

#### Task 5.1.1: Create Cross-Chain Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-300**: Service class
   ```python
   class CrossChainService:
       """Service for managing cross-chain communication between organization and CreditNexus main chain."""
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_router = BlockchainRouterService(db)
       
       async def send_cross_chain_message(
           self,
           from_organization_id: int,
           to_organization_id: Optional[int],  # None = CreditNexus main chain
           message_type: str,
           payload: Dict[str, Any]
       ) -> CrossChainTransaction:
           """Send message from organization blockchain to CreditNexus main chain or vice versa.
           
           Args:
               from_organization_id: Source organization ID
               to_organization_id: Destination organization ID (None for main chain)
               message_type: Type of message (notarization, payment, data_sync)
               payload: Message payload
               
           Returns:
               CrossChainTransaction record
           """
           from_org = self.db.query(Organization).filter(
               Organization.id == from_organization_id
           ).first()
           
           if not from_org:
               raise ValueError(f"Organization {from_organization_id} not found")
           
           # Determine destination chain
           if to_organization_id:
               to_org = self.db.query(Organization).filter(
                   Organization.id == to_organization_id
               ).first()
               dest_chain = f"org_{to_org.id}"
           else:
               dest_chain = "creditnexus_main"
           
           # Create transaction record
           transaction = CrossChainTransaction(
               organization_id=from_organization_id,
               transaction_type=message_type,
               direction="org_to_main" if not to_organization_id else "org_to_org",
               source_chain=f"org_{from_org.id}",
               dest_chain=dest_chain,
               transaction_data=payload,
               status="pending"
           )
           
           self.db.add(transaction)
           self.db.commit()
           
           try:
               # Get source blockchain connection
               source_web3 = self.blockchain_router.get_web3_connection(
                   organization_id=from_organization_id
               )
               
               # Get bridge contract
               bridge_address = from_org.bridge_contract_address
               if not bridge_address:
                   raise ValueError("Bridge contract not deployed for organization")
               
               # Send message via bridge
               result = await self._send_via_bridge(
                   web3=source_web3,
                   bridge_address=bridge_address,
                   to_chain_id=self._get_chain_id(dest_chain),
                   payload=payload
               )
               
               # Update transaction
               transaction.source_tx_hash = result["tx_hash"]
               transaction.source_block_number = result["block_number"]
               transaction.status = "confirmed"
               transaction.confirmed_at = datetime.utcnow()
               
           except Exception as e:
               transaction.status = "failed"
               transaction.error_message = str(e)
               logger.error(f"Cross-chain transaction failed: {e}")
           
           self.db.commit()
           self.db.refresh(transaction)
           
           return transaction
   ```

---

## Implementation Checklist

### Phase 1: Organization Model (Week 1-2)
- [ ] Create Organization model
- [ ] Create OrganizationBlockchainDeployment model
- [ ] Create CrossChainTransaction model
- [ ] Update User model with organization_id
- [ ] Create Alembic migration

### Phase 2: Organization Service (Week 3-4)
- [ ] Create OrganizationService
- [ ] Implement organization registration
- [ ] Implement organization approval
- [ ] Implement blockchain deployment logic
- [ ] Add organization API endpoints

### Phase 3: Signup Integration (Week 5-6)
- [ ] Add organization selection step to SignupFlow
- [ ] Create OrganizationSelectionStep component
- [ ] Create OrganizationRegistrationForm component
- [ ] Update signup endpoints to require organization
- [ ] Update KYC onboarding to include organization

### Phase 4: Blockchain Router (Week 7-8)
- [ ] Create BlockchainRouterService
- [ ] Implement user-to-blockchain routing
- [ ] Implement Web3 connection caching
- [ ] Update BlockchainService to use router
- [ ] Update NotarizationService to use router

### Phase 5: Bridge Contracts (Week 9-10)
- [ ] Create CrossChainBridge.sol
- [ ] Deploy bridge contracts on testnet
- [ ] Test cross-chain messaging
- [ ] Integrate bridge with organization deployment

### Phase 6: Cross-Chain Service (Week 11-12)
- [ ] Create CrossChainService
- [ ] Implement message sending
- [ ] Implement message execution
- [ ] Add cross-chain transaction tracking
- [ ] Add retry logic for failed transactions

### Phase 7: Testing & Refinement (Week 13-16)
- [ ] Test organization registration flow
- [ ] Test blockchain deployment
- [ ] Test cross-chain communication
- [ ] Test user routing
- [ ] Performance optimization
- [ ] Security audit

---

## Success Criteria

1. ✅ All users must be attached to an organization during signup
2. ✅ Each organization has its own blockchain instance
3. ✅ Organizations can communicate with CreditNexus main chain via bridge
4. ✅ Users are automatically routed to their organization's blockchain
5. ✅ Cross-chain transactions are tracked and auditable
6. ✅ Bridge contracts deployed and functional
7. ✅ Organization registration and approval workflow complete
8. ✅ Blockchain deployment automated per organization

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
