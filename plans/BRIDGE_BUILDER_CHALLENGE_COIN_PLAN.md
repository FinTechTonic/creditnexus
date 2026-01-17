# Bridge Builder & Challenge Coin NFT Plan
## Cross-Chain Trading & Asset Tokenization

**Status**: Comprehensive Enhancement Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 10-12 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan implements:
1. **Bridge Builder**: User-friendly interface for trading assets across organization blockchains and with the CreditNexus main chain
2. **Challenge Coin NFTs**: ERC-721 NFTs issued for each securitized asset (distinct from tranche NFTs)
3. **Cross-Chain Trading**: Automated bridge operations for asset transfers between chains
4. **Role-Based Issuance**: Permissions for users/roles to issue challenge coin NFTs

---

## Current State Analysis

### Existing Infrastructure

**Securitization Tokens**:
- **Location**: `contracts/SecuritizationToken.sol`
- **Current**: ERC-721 NFTs for tranche positions in securitization pools
- **Gap**: No challenge coin NFTs for individual securitized assets

**Cross-Chain Bridge**:
- **Location**: `dev/ORGANIZATION_MULTI_BLOCKCHAIN_PLAN.md`
- **Current**: Bridge contracts for cross-chain messaging
- **Gap**: No trading/bridge builder interface

**Blockchain Service**:
- **Location**: `app/services/blockchain_service.py`
- **Current**: Single blockchain connection, token minting
- **Gap**: No multi-chain trading support

---

## Project 1: Challenge Coin NFT Contract

### Activity 1.1: Challenge Coin NFT Smart Contract

**File**: `contracts/ChallengeCoinNFT.sol` (NEW)

#### Task 1.1.1: Create Challenge Coin Contract
**Lines**: 1-300

**Subtasks**:
1. **Line 1-100**: Contract structure
   ```solidity
   // SPDX-License-Identifier: MIT
   pragma solidity ^0.8.20;
   
   import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
   import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
   import "@openzeppelin/contracts/access/Ownable.sol";
   import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
   
   /**
    * @title ChallengeCoinNFT
    * @dev ERC-721 NFT representing a securitized asset (challenge coin)
    * Each NFT represents ownership/proof of a securitized asset
    * Can be traded across chains via bridge
    */
   contract ChallengeCoinNFT is ERC721Enumerable, ERC721URIStorage, Ownable {
       struct AssetMetadata {
           string assetId;           // Unique asset identifier
           string dealId;            // Associated deal ID
           string assetType;         // loan, bond, equity, etc.
           uint256 principalAmount;  // Asset principal (in USDC, 6 decimals)
           uint256 issueDate;        // Timestamp of issuance
           address issuer;           // Address that issued the NFT
           string metadataURI;       // IPFS/metadata URI
           bool locked;              // Locked for cross-chain transfer
           uint256 lockedUntil;      // Lock expiration timestamp
       }
       
       mapping(uint256 => AssetMetadata) public assetMetadata;
       mapping(string => uint256) public assetIdToTokenId;  // assetId => tokenId
       mapping(address => bool) public authorizedIssuers;   // Roles that can issue
       
       uint256 private _tokenIdCounter;
       
       event ChallengeCoinMinted(
           uint256 indexed tokenId,
           string indexed assetId,
           string dealId,
           address indexed issuer,
           address to
       );
       
       event ChallengeCoinLocked(
           uint256 indexed tokenId,
           uint256 lockedUntil
       );
       
       event ChallengeCoinUnlocked(
           uint256 indexed tokenId
       );
       
       event ChallengeCoinBridged(
           uint256 indexed tokenId,
           uint256 indexed targetChainId,
           address indexed targetAddress
       );
       
       constructor() ERC721("ChallengeCoin", "CHAL") Ownable(msg.sender) {
           _tokenIdCounter = 1;
       }
       
       /**
        * @dev Mint challenge coin NFT for securitized asset
        * @param to Recipient address
        * @param assetId Unique asset identifier
        * @param dealId Associated deal ID
        * @param assetType Type of asset
        * @param principalAmount Asset principal amount
        * @param metadataURI IPFS/metadata URI
        */
       function mintChallengeCoin(
           address to,
           string memory assetId,
           string memory dealId,
           string memory assetType,
           uint256 principalAmount,
           string memory metadataURI
       ) external returns (uint256) {
           require(
               authorizedIssuers[msg.sender] || msg.sender == owner(),
               "Not authorized to issue challenge coins"
           );
           require(
               assetIdToTokenId[assetId] == 0,
               "Asset ID already minted"
           );
           
           uint256 tokenId = _tokenIdCounter++;
           
           _safeMint(to, tokenId);
           _setTokenURI(tokenId, metadataURI);
           
           assetMetadata[tokenId] = AssetMetadata({
               assetId: assetId,
               dealId: dealId,
               assetType: assetType,
               principalAmount: principalAmount,
               issueDate: block.timestamp,
               issuer: msg.sender,
               metadataURI: metadataURI,
               locked: false,
               lockedUntil: 0
           });
           
           assetIdToTokenId[assetId] = tokenId;
           
           emit ChallengeCoinMinted(tokenId, assetId, dealId, msg.sender, to);
           
           return tokenId;
       }
   ```

2. **Line 101-200**: Bridge locking/unlocking
   ```solidity
       /**
        * @dev Lock NFT for cross-chain transfer
        * @param tokenId Token ID to lock
        * @param lockDuration Duration to lock (seconds)
        */
       function lockForBridge(
           uint256 tokenId,
           uint256 lockDuration
       ) external {
           require(_ownerOf(tokenId) == msg.sender, "Not token owner");
           require(!assetMetadata[tokenId].locked, "Already locked");
           
           assetMetadata[tokenId].locked = true;
           assetMetadata[tokenId].lockedUntil = block.timestamp + lockDuration;
           
           emit ChallengeCoinLocked(tokenId, assetMetadata[tokenId].lockedUntil);
       }
       
       /**
        * @dev Unlock NFT after bridge transfer
        * @param tokenId Token ID to unlock
        */
       function unlockFromBridge(
           uint256 tokenId
       ) external onlyOwner {
           require(assetMetadata[tokenId].locked, "Not locked");
           
           assetMetadata[tokenId].locked = false;
           assetMetadata[tokenId].lockedUntil = 0;
           
           emit ChallengeCoinUnlocked(tokenId);
       }
       
       /**
        * @dev Mark NFT as bridged (burn on source, mint on destination)
        * @param tokenId Token ID to bridge
        * @param targetChainId Target chain ID
        * @param targetAddress Target address on destination chain
        */
       function bridgeToken(
           uint256 tokenId,
           uint256 targetChainId,
           address targetAddress
       ) external onlyOwner {
           require(assetMetadata[tokenId].locked, "Token must be locked");
           
           // Burn token on source chain
           _burn(tokenId);
           
           emit ChallengeCoinBridged(tokenId, targetChainId, targetAddress);
       }
       
       /**
        * @dev Authorize issuer role
        * @param issuer Address to authorize
        */
       function authorizeIssuer(address issuer) external onlyOwner {
           authorizedIssuers[issuer] = true;
       }
       
       /**
        * @dev Revoke issuer authorization
        * @param issuer Address to revoke
        */
       function revokeIssuer(address issuer) external onlyOwner {
           authorizedIssuers[issuer] = false;
       }
   ```

3. **Line 201-300**: Override functions and metadata
   ```solidity
       /**
        * @dev Override required for ERC721Enumerable + ERC721URIStorage
        */
       function _update(
           address to,
           uint256 tokenId,
           address auth
       ) internal override(ERC721, ERC721Enumerable) returns (address) {
           return super._update(to, tokenId, auth);
       }
       
       function _increaseBalance(
           address account,
           uint128 value
       ) internal override(ERC721, ERC721Enumerable) {
           super._increaseBalance(account, value);
       }
       
       function tokenURI(
           uint256 tokenId
       ) public view override(ERC721, ERC721URIStorage) returns (string memory) {
           return super.tokenURI(tokenId);
       }
       
       function supportsInterface(
           bytes4 interfaceId
       ) public view override(ERC721, ERC721Enumerable, ERC721URIStorage) returns (bool) {
           return super.supportsInterface(interfaceId);
       }
       
       /**
        * @dev Get asset metadata
        * @param tokenId Token ID
        */
       function getAssetMetadata(
           uint256 tokenId
       ) external view returns (AssetMetadata memory) {
           require(_ownerOf(tokenId) != address(0), "Token does not exist");
           return assetMetadata[tokenId];
       }
   }
   ```

---

## Project 2: Bridge Builder Service

### Activity 2.1: Bridge Builder Service

**File**: `app/services/bridge_builder_service.py` (NEW)

#### Task 2.1.1: Create Bridge Builder Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-150**: Service class
   ```python
   class BridgeBuilderService:
       """Service for building and executing cross-chain trades."""
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_router = BlockchainRouterService(db)
           self.cross_chain_service = CrossChainService(db)
       
       async def create_bridge_trade(
           self,
           user_id: int,
           token_id: int,
           source_chain_id: int,
           target_chain_id: int,
           target_address: str,
           trade_type: str = "transfer"  # transfer, swap, loan
       ) -> Dict[str, Any]:
           """Create a cross-chain trade for challenge coin NFT.
           
           Args:
               user_id: User ID initiating trade
               token_id: Challenge coin NFT token ID
               source_chain_id: Source blockchain chain ID
               target_chain_id: Target blockchain chain ID
               target_address: Target address on destination chain
               trade_type: Type of trade
               
           Returns:
               Trade execution result
           """
           user = self.db.query(User).filter(User.id == user_id).first()
           if not user:
               raise ValueError(f"User {user_id} not found")
           
           # Get source blockchain
           source_web3 = self.blockchain_router.get_web3_connection(
               organization_id=user.organization_id
           )
           
           # Get challenge coin contract
           challenge_coin_contract = self._get_challenge_coin_contract(
               web3=source_web3,
               chain_id=source_chain_id
           )
           
           # Verify token ownership
           owner = challenge_coin_contract.functions.ownerOf(token_id).call()
           if owner.lower() != user.wallet_address.lower():
               raise ValueError("User does not own this token")
           
           # Lock token for bridge
           lock_duration = 3600  # 1 hour
           lock_tx = challenge_coin_contract.functions.lockForBridge(
               token_id,
               lock_duration
           ).build_transaction({
               'from': user.wallet_address,
               'gas': 200000,
               'gasPrice': source_web3.eth.gas_price,
               'nonce': source_web3.eth.get_transaction_count(user.wallet_address)
           })
           
           # Create bridge trade record
           bridge_trade = BridgeTrade(
               user_id=user_id,
               token_id=token_id,
               source_chain_id=source_chain_id,
               target_chain_id=target_chain_id,
               target_address=target_address,
               trade_type=trade_type,
               status="pending",
               lock_tx_hash=None
           )
           
           self.db.add(bridge_trade)
           self.db.commit()
           
           return {
               "trade_id": bridge_trade.id,
               "status": "pending",
               "lock_transaction": lock_tx
           }
       
       async def execute_bridge_trade(
           self,
           trade_id: int,
           signed_lock_tx: str
       ) -> Dict[str, Any]:
           """Execute bridge trade after lock transaction is signed.
           
           Args:
               trade_id: Bridge trade ID
               signed_lock_tx: Signed lock transaction
               
           Returns:
               Execution result
           """
           trade = self.db.query(BridgeTrade).filter(
               BridgeTrade.id == trade_id
           ).first()
           
           if not trade:
               raise ValueError(f"Trade {trade_id} not found")
           
           # Send lock transaction
           source_web3 = self.blockchain_router.get_web3_connection(
               organization_id=trade.user.organization_id
           )
           
           tx_hash = source_web3.eth.send_raw_transaction(signed_lock_tx)
           receipt = source_web3.eth.wait_for_transaction_receipt(tx_hash)
           
           # Update trade
           trade.lock_tx_hash = tx_hash.hex()
           trade.status = "locked"
           
           # Initiate cross-chain bridge
           bridge_result = await self.cross_chain_service.send_cross_chain_message(
               from_organization_id=trade.user.organization_id,
               to_organization_id=self._get_org_id_from_chain_id(trade.target_chain_id),
               message_type="challenge_coin_bridge",
               payload={
                   "token_id": trade.token_id,
                   "source_chain_id": trade.source_chain_id,
                   "target_chain_id": trade.target_chain_id,
                   "target_address": trade.target_address,
                   "lock_tx_hash": tx_hash.hex()
               }
           )
           
           trade.bridge_tx_id = bridge_result.id
           trade.status = "bridging"
           
           self.db.commit()
           
           return {
               "trade_id": trade.id,
               "status": "bridging",
               "lock_tx_hash": tx_hash.hex(),
               "bridge_transaction_id": bridge_result.id
           }
   ```

---

## Project 3: Challenge Coin Issuance

### Activity 3.1: Challenge Coin Service

**File**: `app/services/challenge_coin_service.py` (NEW)

#### Task 3.1.1: Create Challenge Coin Service
**Lines**: 1-400

**Subtasks**:
1. **Line 1-200**: Service class
   ```python
   class ChallengeCoinService:
       """Service for issuing and managing challenge coin NFTs."""
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_router = BlockchainRouterService(db)
       
       async def issue_challenge_coin(
           self,
           user_id: int,
           asset_id: str,
           deal_id: str,
           asset_type: str,
           principal_amount: Decimal,
           recipient_address: Optional[str] = None
       ) -> Dict[str, Any]:
           """Issue challenge coin NFT for securitized asset.
           
           Args:
               user_id: User ID issuing the coin
               asset_id: Unique asset identifier
               deal_id: Associated deal ID
               asset_type: Type of asset (loan, bond, equity, etc.)
               principal_amount: Asset principal amount
               recipient_address: Optional recipient address (defaults to user's wallet)
               
           Returns:
               Issuance result with token_id and transaction_hash
           """
           user = self.db.query(User).filter(User.id == user_id).first()
           if not user:
               raise ValueError(f"User {user_id} not found")
           
           # Check permissions
           if not self._can_issue_challenge_coin(user):
               raise PermissionError("User does not have permission to issue challenge coins")
           
           # Get blockchain connection
           blockchain_config = self.blockchain_router.get_user_blockchain(user_id)
           web3 = self.blockchain_router.get_web3_connection(
               organization_id=user.organization_id
           )
           
           # Get challenge coin contract address
           contract_address = self._get_challenge_coin_contract_address(
               organization_id=user.organization_id,
               blockchain_config=blockchain_config
           )
           
           # Load contract
           challenge_coin_contract = self._load_challenge_coin_contract(
               web3=web3,
               contract_address=contract_address
           )
           
           # Prepare metadata
           metadata_uri = await self._generate_metadata_uri(
               asset_id=asset_id,
               deal_id=deal_id,
               asset_type=asset_type,
               principal_amount=principal_amount
           )
           
           # Mint NFT
           recipient = recipient_address or user.wallet_address
           principal_wei = int(principal_amount * Decimal("1000000"))  # USDC 6 decimals
           
           mint_tx = challenge_coin_contract.functions.mintChallengeCoin(
               recipient,
               asset_id,
               deal_id,
               asset_type,
               principal_wei,
               metadata_uri
           ).build_transaction({
               'from': user.wallet_address,
               'gas': 300000,
               'gasPrice': web3.eth.gas_price,
               'nonce': web3.eth.get_transaction_count(user.wallet_address)
           })
           
           # Create issuance record
           issuance = ChallengeCoinIssuance(
               user_id=user_id,
               asset_id=asset_id,
               deal_id=deal_id,
               asset_type=asset_type,
               principal_amount=principal_amount,
               recipient_address=recipient,
               status="pending"
           )
           
           self.db.add(issuance)
           self.db.commit()
           
           return {
               "issuance_id": issuance.id,
               "asset_id": asset_id,
               "transaction": mint_tx,
               "metadata_uri": metadata_uri
           }
       
       def _can_issue_challenge_coin(self, user: User) -> bool:
           """Check if user can issue challenge coins."""
           # Roles that can issue: banker, trader, admin
           allowed_roles = ['banker', 'trader', 'admin']
           return user.role in allowed_roles or self._has_permission(
               user, 'PERMISSION_ISSUE_CHALLENGE_COIN'
           )
   ```

---

## Project 4: Bridge Builder UI

### Activity 4.1: Bridge Builder Component

**File**: `client/src/components/dashboard-tabs/BridgeBuilder.tsx` (NEW)

#### Task 4.1.1: Create Bridge Builder Component
**Lines**: 1-500

**Subtasks**:
1. **Line 1-200**: Component setup
   ```typescript
   import { useState, useEffect } from 'react';
   import { ArrowRight, Lock, Unlock, CheckCircle2 } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   import { Select } from '@/components/ui/select';
   
   interface BridgeBuilderProps {
     organizationId?: number;
   }
   
   export function BridgeBuilder({ organizationId }: BridgeBuilderProps) {
     const [userTokens, setUserTokens] = useState<any[]>([]);
     const [selectedToken, setSelectedToken] = useState<number | null>(null);
     const [targetChain, setTargetChain] = useState<string>('');
     const [targetAddress, setTargetAddress] = useState('');
     const [loading, setLoading] = useState(false);
     const [tradeStatus, setTradeStatus] = useState<string | null>(null);
     
     useEffect(() => {
       loadUserTokens();
     }, []);
     
     const loadUserTokens = async () => {
       try {
         const response = await fetchWithAuth('/api/challenge-coins/my-tokens');
         if (response.ok) {
           const data = await response.json();
           setUserTokens(data.tokens || []);
         }
       } catch (error) {
         console.error('Failed to load tokens:', error);
       }
     };
   ```

2. **Line 201-400**: Trade execution
   ```typescript
     const handleCreateTrade = async () => {
       if (!selectedToken || !targetChain || !targetAddress) {
         return;
       }
       
       setLoading(true);
       try {
         const response = await fetchWithAuth('/api/bridge-builder/create-trade', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             token_id: selectedToken,
             target_chain_id: parseInt(targetChain),
             target_address: targetAddress
           })
         });
         
         if (response.ok) {
           const data = await response.json();
           setTradeStatus('pending');
           
           // Sign and execute transaction
           await signAndExecuteTrade(data.transaction);
         }
       } catch (error) {
         console.error('Trade creation failed:', error);
       } finally {
         setLoading(false);
       }
     };
     
     return (
       <div className="space-y-6">
         <div className="text-center mb-6">
           <h2 className="text-2xl font-semibold text-slate-100 mb-2">
             Bridge Builder
           </h2>
           <p className="text-slate-400">
             Trade challenge coins across blockchains
           </p>
         </div>
         
         <div className="grid grid-cols-2 gap-6">
           <Card className="p-6">
             <h3 className="text-lg font-semibold mb-4">Select Token</h3>
             <div className="space-y-2">
               {userTokens.map((token) => (
                 <div
                   key={token.token_id}
                   className={`p-3 border rounded cursor-pointer ${
                     selectedToken === token.token_id
                       ? 'border-emerald-500 bg-emerald-500/10'
                       : 'border-slate-600'
                   }`}
                   onClick={() => setSelectedToken(token.token_id)}
                 >
                   <div className="font-medium">{token.asset_id}</div>
                   <div className="text-sm text-slate-400">
                     {token.asset_type} • {token.principal_amount} USDC
                   </div>
                 </div>
               ))}
             </div>
           </Card>
           
           <Card className="p-6">
             <h3 className="text-lg font-semibold mb-4">Bridge Configuration</h3>
             <div className="space-y-4">
               <Select
                 value={targetChain}
                 onValueChange={setTargetChain}
                 placeholder="Select target chain"
               >
                 <option value="1">CreditNexus Main Chain</option>
                 <option value="8453">Base (L2)</option>
                 {/* Add organization chains */}
               </Select>
               
               <input
                 type="text"
                 placeholder="Target address"
                 value={targetAddress}
                 onChange={(e) => setTargetAddress(e.target.value)}
                 className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded"
               />
               
               <Button
                 onClick={handleCreateTrade}
                 disabled={!selectedToken || !targetChain || !targetAddress || loading}
                 className="w-full"
               >
                 <ArrowRight className="h-4 w-4 mr-2" />
                 Create Bridge Trade
               </Button>
             </div>
           </Card>
         </div>
       </div>
     );
   }
   ```

---

## Implementation Checklist

### Phase 1: Challenge Coin Contract (Week 1-2)
- [ ] Create ChallengeCoinNFT.sol contract
- [ ] Deploy to testnet
- [ ] Test minting, locking, bridging
- [ ] Add to contract registry

### Phase 2: Challenge Coin Service (Week 3-4)
- [ ] Create ChallengeCoinService
- [ ] Implement issuance logic
- [ ] Add permission checks
- [ ] Create API endpoints

### Phase 3: Bridge Builder Service (Week 5-6)
- [ ] Create BridgeBuilderService
- [ ] Implement trade creation
- [ ] Implement trade execution
- [ ] Add cross-chain integration

### Phase 4: Bridge Builder UI (Week 7-8)
- [ ] Create BridgeBuilder component
- [ ] Add to UnifiedDashboard
- [ ] Implement token selection
- [ ] Implement trade execution flow

### Phase 5: Integration & Testing (Week 9-10)
- [ ] Test cross-chain trades
- [ ] Test challenge coin issuance
- [ ] Test permissions
- [ ] Performance optimization

### Phase 6: Documentation & Deployment (Week 11-12)
- [ ] Write documentation
- [ ] Deploy to production
- [ ] User training
- [ ] Monitoring setup

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
