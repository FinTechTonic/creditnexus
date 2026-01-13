"""Blockchain service for smart contract deployment and interaction."""

import logging
import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service for smart contract deployment and interaction."""
    
    def __init__(self):
        """Initialize blockchain service."""
        self.web3 = None
        self.deployer_account = None
        self._contract_abis = {}
        self._contract_bytecodes = {}
        self._initialize_web3()
        self._load_contract_artifacts()
    
    def _initialize_web3(self):
        """Initialize Web3 connection."""
        try:
            from web3 import Web3
            
            if settings.X402_NETWORK_RPC_URL:
                self.web3 = Web3(Web3.HTTPProvider(settings.X402_NETWORK_RPC_URL))
                if not self.web3.is_connected():
                    logger.warning(f"Failed to connect to blockchain at {settings.X402_NETWORK_RPC_URL}")
                    self.web3 = None
                else:
                    logger.info(f"Connected to blockchain: {settings.X402_NETWORK_RPC_URL}")
        except ImportError:
            logger.warning("web3.py not installed, blockchain features disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            self.web3 = None
        
        # Initialize deployer account
        self.deployer_account = self._get_deployer_account()
    
    def _load_contract_artifacts(self):
        """Load contract ABIs and bytecode from Hardhat artifacts."""
        try:
            # Path to Hardhat artifacts
            artifacts_dir = Path(__file__).parent.parent.parent / "contracts" / "artifacts" / "contracts"
            
            if not artifacts_dir.exists():
                logger.warning(f"Contract artifacts directory not found: {artifacts_dir}")
                return
            
            # Load SecuritizationToken
            token_artifact_path = artifacts_dir / "SecuritizationToken.sol" / "SecuritizationToken.json"
            if token_artifact_path.exists():
                with open(token_artifact_path, 'r') as f:
                    token_artifact = json.load(f)
                    self._contract_abis['token'] = token_artifact.get('abi', [])
                    self._contract_bytecodes['token'] = token_artifact.get('bytecode', '')
                    logger.info("Loaded SecuritizationToken ABI")
            
            # Load SecuritizationPaymentRouter
            router_artifact_path = artifacts_dir / "SecuritizationPaymentRouter.sol" / "SecuritizationPaymentRouter.json"
            if router_artifact_path.exists():
                with open(router_artifact_path, 'r') as f:
                    router_artifact = json.load(f)
                    self._contract_abis['router'] = router_artifact.get('abi', [])
                    self._contract_bytecodes['router'] = router_artifact.get('bytecode', '')
                    logger.info("Loaded SecuritizationPaymentRouter ABI")
            
            # Load SecuritizationNotarization
            notarization_artifact_path = artifacts_dir / "SecuritizationNotarization.sol" / "SecuritizationNotarization.json"
            if notarization_artifact_path.exists():
                with open(notarization_artifact_path, 'r') as f:
                    notarization_artifact = json.load(f)
                    self._contract_abis['notarization'] = notarization_artifact.get('abi', [])
                    self._contract_bytecodes['notarization'] = notarization_artifact.get('bytecode', '')
                    logger.info("Loaded SecuritizationNotarization ABI")
                    
        except Exception as e:
            logger.warning(f"Failed to load contract artifacts: {e}")
            logger.warning("Contract interaction will use placeholder methods")
    
    def ensure_contracts_deployed(
        self,
        db: Session
    ) -> Dict[str, str]:
        """
        Ensure all securitization contracts are deployed.
        
        Checks config for contract addresses. If missing and auto-deploy enabled,
        attempts to auto-deploy contracts. Otherwise returns empty addresses.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary of contract_name -> address
        """
        contracts = {}
        
        # Check SecuritizationNotarization
        if settings.SECURITIZATION_NOTARIZATION_CONTRACT:
            contracts['notarization'] = settings.SECURITIZATION_NOTARIZATION_CONTRACT
        elif settings.BLOCKCHAIN_AUTO_DEPLOY and self.web3:
            try:
                contracts['notarization'] = self._deploy_notarization_contract()
                logger.info(f"Auto-deployed SecuritizationNotarization: {contracts['notarization']}")
            except Exception as e:
                logger.error(f"Failed to deploy notarization contract: {e}")
                contracts['notarization'] = ""
        else:
            contracts['notarization'] = ""
        
        # Check SecuritizationToken
        if settings.SECURITIZATION_TOKEN_CONTRACT:
            contracts['token'] = settings.SECURITIZATION_TOKEN_CONTRACT
        elif settings.BLOCKCHAIN_AUTO_DEPLOY and self.web3:
            try:
                contracts['token'] = self._deploy_token_contract()
                logger.info(f"Auto-deployed SecuritizationToken: {contracts['token']}")
            except Exception as e:
                logger.error(f"Failed to deploy token contract: {e}")
                contracts['token'] = ""
        else:
            contracts['token'] = ""
        
        # Check SecuritizationPaymentRouter
        if settings.SECURITIZATION_PAYMENT_ROUTER_CONTRACT:
            contracts['router'] = settings.SECURITIZATION_PAYMENT_ROUTER_CONTRACT
        elif settings.BLOCKCHAIN_AUTO_DEPLOY and self.web3 and contracts.get('token'):
            try:
                contracts['router'] = self._deploy_payment_router_contract(
                    token_address=contracts['token']
                )
                logger.info(f"Auto-deployed SecuritizationPaymentRouter: {contracts['router']}")
            except Exception as e:
                logger.error(f"Failed to deploy payment router contract: {e}")
                contracts['router'] = ""
        else:
            contracts['router'] = ""
        
        return contracts
    
    def _deploy_notarization_contract(self) -> str:
        """Deploy SecuritizationNotarization contract.
        
        Returns:
            Contract address
            
        Raises:
            ValueError: If contract deployment fails
        """
        if not self.web3:
            raise ValueError("Web3 not initialized")
        
        # For now, return a placeholder - actual deployment requires compiled contracts
        # In production, this would load from contracts/build/SecuritizationNotarization.json
        logger.warning("Contract deployment requires compiled Solidity contracts")
        raise NotImplementedError("Contract deployment requires compiled contracts. Set contract addresses in config.")
    
    def _deploy_token_contract(self) -> str:
        """Deploy SecuritizationToken contract.
        
        Returns:
            Contract address
            
        Raises:
            ValueError: If contract deployment fails
        """
        if not self.web3:
            raise ValueError("Web3 not initialized")
        
        logger.warning("Contract deployment requires compiled Solidity contracts")
        raise NotImplementedError("Contract deployment requires compiled contracts. Set contract addresses in config.")
    
    def _deploy_payment_router_contract(self, token_address: str) -> str:
        """Deploy SecuritizationPaymentRouter contract.
        
        Args:
            token_address: Address of SecuritizationToken contract
            
        Returns:
            Contract address
            
        Raises:
            ValueError: If contract deployment fails
        """
        if not self.web3:
            raise ValueError("Web3 not initialized")
        
        if not token_address:
            raise ValueError("Token contract address required")
        
        logger.warning("Contract deployment requires compiled Solidity contracts")
        raise NotImplementedError("Contract deployment requires compiled contracts. Set contract addresses in config.")
    
    def _get_deployer_account(self):
        """Get deployer account from private key or generate for demo.
        
        Returns:
            Account object or None
        """
        deployer_key = settings.BLOCKCHAIN_DEPLOYER_PRIVATE_KEY
        
        if deployer_key:
            try:
                from eth_account import Account
                return Account.from_key(deployer_key.get_secret_value() if hasattr(deployer_key, 'get_secret_value') else deployer_key)
            except Exception as e:
                logger.error(f"Failed to load deployer account: {e}")
                return None
        
        # Generate deterministic demo deployer if in development
        if settings.BLOCKCHAIN_AUTO_DEPLOY:
            try:
                from eth_account import Account
                seed = "creditnexus_demo_deployer".encode()
                private_key = hashlib.sha256(seed).digest()
                account = Account.from_key(private_key)
                logger.info(f"Generated demo deployer account: {account.address}")
                return account
            except ImportError:
                logger.warning("eth_account not available, cannot generate deployer account")
                return None
            except Exception as e:
                logger.error(f"Failed to generate demo deployer: {e}")
                return None
        
        return None
    
    def get_contract_addresses(self) -> Dict[str, str]:
        """Get current contract addresses from config.
        
        Returns:
            Dictionary of contract_name -> address
        """
        return {
            'notarization': settings.SECURITIZATION_NOTARIZATION_CONTRACT or "",
            'token': settings.SECURITIZATION_TOKEN_CONTRACT or "",
            'router': settings.SECURITIZATION_PAYMENT_ROUTER_CONTRACT or "",
            'usdc': settings.USDC_TOKEN_ADDRESS
        }
    
    def is_connected(self) -> bool:
        """Check if Web3 is connected to blockchain.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.web3:
            return False
        try:
            return self.web3.is_connected()
        except:
            return False
    
    def mint_tranche_token(
        self,
        pool_id: str,
        tranche_id: str,
        buyer_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mint ERC-721 token for tranche purchase.
        
        Args:
            pool_id: Pool identifier
            tranche_id: Tranche identifier
            buyer_address: Buyer's wallet address
            metadata: Optional token metadata
            
        Returns:
            Dictionary with token_id and transaction_hash
            
        Raises:
            ValueError: If contract not available or minting fails
        """
        if not self.web3 or not self.is_connected():
            logger.warning("Blockchain not connected, skipping token minting")
            return {
                "token_id": None,
                "transaction_hash": None,
                "status": "skipped",
                "message": "Blockchain not connected"
            }
        
        token_contract_address = settings.SECURITIZATION_TOKEN_CONTRACT
        if not token_contract_address:
            logger.warning("SecuritizationToken contract not configured, skipping token minting")
            return {
                "token_id": None,
                "transaction_hash": None,
                "status": "skipped",
                "message": "Token contract not configured"
            }
        
        try:
            from web3 import Web3
            from eth_account import Account
            
            # Load contract ABI
            if 'token' not in self._contract_abis:
                logger.warning("Token contract ABI not loaded, using placeholder")
                token_id = int(hashlib.sha256(f"{pool_id}_{tranche_id}".encode()).hexdigest()[:8], 16) % (10**18)
                return {
                    "token_id": str(token_id),
                    "transaction_hash": None,
                    "status": "skipped",
                    "message": "Contract ABI not available"
                }
            
            # Create contract instance
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_contract_address),
                abi=self._contract_abis['token']
            )
            
            # Extract metadata values
            principal_amount = int(metadata.get('principal_amount', 0)) if metadata else 0
            interest_rate = int(metadata.get('interest_rate', 0)) if metadata else 0  # In basis points
            payment_priority = int(metadata.get('payment_priority', 0)) if metadata else 0
            
            # Get deployer account for transaction
            if not self.deployer_account:
                logger.warning("No deployer account available, using placeholder")
                token_id = int(hashlib.sha256(f"{pool_id}_{tranche_id}".encode()).hexdigest()[:8], 16) % (10**18)
                return {
                    "token_id": str(token_id),
                    "transaction_hash": None,
                    "status": "skipped",
                    "message": "Deployer account not available"
                }
            
            # Build transaction
            function_call = contract.functions.mintTranche(
                Web3.to_checksum_address(buyer_address),
                pool_id,
                tranche_id,
                principal_amount,
                interest_rate,
                payment_priority
            )
            
            # Estimate gas
            try:
                gas_estimate = function_call.estimate_gas({'from': self.deployer_account.address})
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default")
                gas_estimate = 200000  # Default gas limit
            
            # Build and sign transaction
            transaction = function_call.build_transaction({
                'from': self.deployer_account.address,
                'gas': gas_estimate,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.deployer_account.address)
            })
            
            signed_txn = self.deployer_account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.info(f"Token minting transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status != 1:
                raise ValueError(f"Transaction failed with status {receipt.status}")
            
            # Extract token_id from event logs
            token_id = None
            tranche_minted_event = contract.events.TrancheMinted()
            for log in receipt.logs:
                try:
                    decoded = tranche_minted_event.process_log(log)
                    if decoded and decoded.args:
                        token_id = decoded.args.tokenId
                        break
                except:
                    continue
            
            # Fallback: if event not found, use transaction hash to generate deterministic ID
            if token_id is None:
                logger.warning("Token ID not found in event logs, using deterministic fallback")
                token_id = int(hashlib.sha256(f"{pool_id}_{tranche_id}_{tx_hash.hex()}".encode()).hexdigest()[:8], 16) % (10**18)
            
            logger.info(f"Successfully minted token {token_id} to {buyer_address} for pool {pool_id}, tranche {tranche_id}")
            
            return {
                "token_id": str(token_id),
                "transaction_hash": tx_hash.hex(),
                "status": "completed",
                "message": "Token minted successfully"
            }
        except Exception as e:
            logger.error(f"Failed to mint token: {e}", exc_info=True)
            # Fallback to placeholder on error
            token_id = int(hashlib.sha256(f"{pool_id}_{tranche_id}".encode()).hexdigest()[:8], 16) % (10**18)
            return {
                "token_id": str(token_id),
                "transaction_hash": None,
                "status": "error",
                "message": f"Token minting failed: {str(e)}"
            }
    
    def distribute_payment_to_tranche(
        self,
        pool_id: str,
        tranche_id: str,
        amount: Decimal,
        currency: str,
        payment_type: str = "interest"
    ) -> Dict[str, Any]:
        """Distribute payment to tranche holders via smart contract.
        
        Args:
            pool_id: Pool identifier
            tranche_id: Tranche identifier
            amount: Payment amount
            currency: Payment currency
            payment_type: Type of payment (interest, principal)
            
        Returns:
            Dictionary with transaction_hash and distribution details
            
        Raises:
            ValueError: If contract not available or distribution fails
        """
        if not self.web3 or not self.is_connected():
            logger.warning("Blockchain not connected, skipping smart contract distribution")
            return {
                "transaction_hash": None,
                "status": "skipped",
                "message": "Blockchain not connected"
            }
        
        router_contract_address = settings.SECURITIZATION_PAYMENT_ROUTER_CONTRACT
        if not router_contract_address:
            logger.warning("PaymentRouter contract not configured, skipping smart contract distribution")
            return {
                "transaction_hash": None,
                "status": "skipped",
                "message": "Payment router contract not configured"
            }
        
        try:
            from web3 import Web3
            from eth_account import Account
            
            # Load contract ABI
            if 'router' not in self._contract_abis:
                logger.warning("Payment router contract ABI not loaded, using placeholder")
                return {
                    "transaction_hash": None,
                    "status": "skipped",
                    "message": "Contract ABI not available"
                }
            
            # Create contract instance
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(router_contract_address),
                abi=self._contract_abis['router']
            )
            
            # Convert amount to wei (assuming USDC with 6 decimals)
            # For USDC: 1 USDC = 1,000,000 (10^6) units
            if currency.upper() == "USDC":
                amount_wei = int(amount * Decimal("1000000"))
            else:
                # For ETH: 1 ETH = 10^18 wei
                amount_wei = int(amount * Decimal("1000000000000000000"))
            
            # Get deployer account for transaction
            if not self.deployer_account:
                logger.warning("No deployer account available, using placeholder")
                return {
                    "transaction_hash": None,
                    "status": "skipped",
                    "message": "Deployer account not available"
                }
            
            # Build transaction - distributePayment takes poolId and totalAmount
            function_call = contract.functions.distributePayment(
                pool_id,
                amount_wei
            )
            
            # Estimate gas
            try:
                gas_estimate = function_call.estimate_gas({'from': self.deployer_account.address})
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default")
                gas_estimate = 500000  # Default gas limit for payment distribution
            
            # Build and sign transaction
            transaction = function_call.build_transaction({
                'from': self.deployer_account.address,
                'gas': gas_estimate,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.deployer_account.address)
            })
            
            signed_txn = self.deployer_account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.info(f"Payment distribution transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status != 1:
                raise ValueError(f"Transaction failed with status {receipt.status}")
            
            logger.info(f"Successfully distributed {amount} {currency} to pool {pool_id}")
            
            return {
                "transaction_hash": tx_hash.hex(),
                "status": "completed",
                "message": "Payment distributed successfully",
                "amount": str(amount),
                "currency": currency
            }
        except Exception as e:
            logger.error(f"Failed to distribute payment: {e}", exc_info=True)
            return {
                "transaction_hash": None,
                "status": "error",
                "message": f"Payment distribution failed: {str(e)}"
            }
    
    def get_token_owner(self, token_id: str) -> Optional[str]:
        """Get owner of a tranche token.
        
        Args:
            token_id: Token ID
            
        Returns:
            Owner wallet address or None if not found
        """
        if not self.web3 or not self.is_connected():
            return None
        
        token_contract_address = settings.SECURITIZATION_TOKEN_CONTRACT
        if not token_contract_address:
            return None
        
        try:
            from web3 import Web3
            
            # Load contract ABI
            if 'token' not in self._contract_abis:
                logger.warning("Token contract ABI not loaded")
                return None
            
            # Create contract instance
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_contract_address),
                abi=self._contract_abis['token']
            )
            
            # Call ownerOf function
            owner_address = contract.functions.ownerOf(int(token_id)).call()
            
            logger.debug(f"Token {token_id} owner: {owner_address}")
            return owner_address
        except Exception as e:
            logger.error(f"Failed to get token owner: {e}")
            return None
