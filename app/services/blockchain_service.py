"""Blockchain service for smart contract deployment and interaction."""

import logging
import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service for smart contract deployment and interaction."""
    
    def __init__(self, organization_context: Optional[Dict[str, Any]] = None):
        """Initialize blockchain service with optional organization context.
        
        Args:
            organization_context: Optional organization blockchain context dictionary
        """
        self.organization_context = organization_context
        self.web3 = None
        self.deployer_account = None
        self._contract_abis = {}
        self._contract_bytecodes = {}
        self._initialize_web3()
        self._load_contract_artifacts()
    
    def _initialize_web3(self):
        """Initialize Web3 connection to organization's blockchain or default."""
        try:
            from web3 import Web3
            
            # Use organization's RPC if available
            rpc_url = None
            if self.organization_context and self.organization_context.get("rpc_url"):
                rpc_url = self.organization_context["rpc_url"]
            else:
                rpc_url = settings.X402_NETWORK_RPC_URL
            
            if rpc_url:
                self.web3 = Web3(Web3.HTTPProvider(rpc_url))
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

            # Load CreditToken (rolling credits / subscription balances)
            credit_token_path = artifacts_dir / "CreditToken.sol" / "CreditToken.json"
            if credit_token_path.exists():
                with open(credit_token_path, 'r') as f:
                    credit_artifact = json.load(f)
                    self._contract_abis['credit_token'] = credit_artifact.get('abi', [])
                    self._contract_bytecodes['credit_token'] = credit_artifact.get('bytecode', '')
                    logger.info("Loaded CreditToken ABI")

            # Load SFPOutcomeToken (ERC-1155 for Polymarket cross-chain outcome tokens)
            sfp_path = artifacts_dir / "SFPOutcomeToken.sol" / "SFPOutcomeToken.json"
            if sfp_path.exists():
                with open(sfp_path, 'r') as f:
                    sfp_artifact = json.load(f)
                    self._contract_abis['sfp_outcome_token'] = sfp_artifact.get('abi', [])
                    self._contract_bytecodes['sfp_outcome_token'] = sfp_artifact.get('bytecode', '')
                    logger.info("Loaded SFPOutcomeToken ABI")

            # Load ChallengeCoinNFT (ERC-721 for securitized asset challenge coins, bridge builder)
            cc_path = artifacts_dir / "ChallengeCoinNFT.sol" / "ChallengeCoinNFT.json"
            if cc_path.exists():
                with open(cc_path, 'r') as f:
                    cc_artifact = json.load(f)
                    self._contract_abis['challenge_coin'] = cc_artifact.get('abi', [])
                    self._contract_bytecodes['challenge_coin'] = cc_artifact.get('bytecode', '')
                    logger.info("Loaded ChallengeCoinNFT ABI")

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
            'usdc': settings.USDC_TOKEN_ADDRESS,
            'challenge_coin': getattr(settings, 'CHALLENGE_COIN_NFT_CONTRACT', None) or "",
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

    def create_pool_notarization_on_chain(
        self,
        pool_id: str,
        notarization_hash_hex: str,
        signers: List[str],
    ) -> Dict[str, Any]:
        """Create a notarization request on-chain via SecuritizationNotarization.createNotarization.
        Used when notarizing a securitization pool (pool/tranche verification linkage).

        Args:
            pool_id: Pool identifier string (e.g. pool.pool_id)
            notarization_hash_hex: SHA-256 hash of CDM payload as hex (64 chars, no 0x)
            signers: List of ethereum addresses (required by contract)

        Returns:
            {"success": True, "transaction_hash": str, "block_number": int} or
            {"success": False, "error": str}
        """
        if not self.web3 or not self.is_connected():
            return {"success": False, "error": "Blockchain not connected"}
        addr = (
            settings.SECURITIZATION_NOTARIZATION_CONTRACT
            or (self.get_contract_addresses() or {}).get("notarization")
        )
        if not addr or "notarization" not in (self._contract_abis or {}):
            return {"success": False, "error": "SecuritizationNotarization contract not configured"}
        try:
            h = (notarization_hash_hex or "").replace("0x", "")
            if len(h) != 64:
                return {"success": False, "error": "notarization_hash must be 64-char hex"}
            pool_hash_bytes = bytes.fromhex(h)
            if len(pool_hash_bytes) != 32:
                return {"success": False, "error": "invalid hash length"}
            signer_addrs = [self.web3.to_checksum_address(s) for s in (signers or []) if s]
            if not signer_addrs:
                acc = self._get_deployer_account()
                signer_addrs = (
                    [acc.address] if acc
                    else [self.web3.to_checksum_address("0x0000000000000000000000000000000000000001")]
                )
            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address(addr),
                abi=self._contract_abis["notarization"],
            )
            tx = contract.functions.createNotarization(pool_id, pool_hash_bytes, signer_addrs)
            built = tx.build_transaction(
                {"from": self.deployer_account.address} if self.deployer_account else {}
            )
            if not self.deployer_account:
                return {"success": False, "error": "Deployer account not available"}
            signed = self.web3.eth.account.sign_transaction(built, self.deployer_account.key)
            sent = self.web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(sent)
            return {
                "success": True,
                "transaction_hash": self.web3.to_hex(receipt.get("transactionHash"))
                if receipt.get("transactionHash")
                else None,
                "block_number": receipt.get("blockNumber"),
            }
        except Exception as e:
            logger.warning("create_pool_notarization_on_chain failed: %s", e)
            return {"success": False, "error": str(e)}

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
    
    # CreditToken struct field order for mintCredits (CreditBalanceStruct)
    _CREDIT_STRUCT_ORDER: Tuple[str, ...] = (
        "signing", "document_review", "verification", "trading", "loaning", "borrowing",
        "compliance_check", "securitization", "risk_analysis", "quantitative_analysis",
        "stock_prediction_daily", "stock_prediction_hourly", "stock_prediction_15min", "universal",
    )

    def mint_credit_token(self, user_address: str, credits_by_type: Dict[str, float]) -> Dict[str, Any]:
        """Mint CreditToken NFT with initial credit balances. Amounts in credits (4 decimals on-chain: 1.0 -> 10000).

        Args:
            user_address: Wallet address to mint to
            credits_by_type: Dict of credit_type -> amount (float)

        Returns:
            Dict with token_id, tx_hash, chain_id on success; or status/message on skip/error.
        """
        if not self.web3 or not self.is_connected():
            return {"status": "skipped", "message": "Blockchain not connected"}
        addr = settings.CREDIT_TOKEN_CONTRACT
        if not addr:
            return {"status": "skipped", "message": "CREDIT_TOKEN_CONTRACT not configured"}
        if "credit_token" not in self._contract_abis:
            return {"status": "skipped", "message": "CreditToken ABI not loaded"}
        if not self.deployer_account:
            return {"status": "skipped", "message": "Deployer account not available"}

        try:
            from web3 import Web3

            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["credit_token"],
            )
            # Build struct as tuple of 14 uint256 in _CREDIT_STRUCT_ORDER (4 decimals: 1.0 -> 10000)
            struct: List[int] = []
            for k in self._CREDIT_STRUCT_ORDER:
                v = credits_by_type.get(k, 0) or 0
                struct.append(int(round(float(v) * 10000)))

            fn = contract.functions.mintCredits(Web3.to_checksum_address(user_address), tuple(struct))
            gas = 300_000
            try:
                gas = fn.estimate_gas({"from": self.deployer_account.address})
            except Exception:
                pass
            tx = fn.build_transaction({
                "from": self.deployer_account.address,
                "gas": gas,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.deployer_account.address),
            })
            signed = self.deployer_account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                return {"status": "error", "message": f"Transaction reverted (status {receipt.status})"}

            # mintCredits returns (uint256 tokenId)
            token_id = contract.functions.userTokenIds(Web3.to_checksum_address(user_address)).call()
            chain_id = self.web3.eth.chain_id
            logger.info(f"CreditToken minted: tokenId={token_id} for {user_address[:10]}...")
            return {
                "status": "completed",
                "token_id": str(token_id),
                "tx_hash": tx_hash.hex(),
                "chain_id": chain_id,
            }
        except Exception as e:
            logger.error(f"mint_credit_token failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def update_credit_token(self, token_id: int, credit_type: str, amount: float, is_spend: bool = False) -> Dict[str, Any]:
        """Update credits for an existing CreditToken. amount in credit units (converted to 4 decimals on-chain).

        Args:
            token_id: CreditToken NFT id
            credit_type: e.g. signing, document_review, universal
            amount: Amount (float); stored as int(round(amount * 10000)) on-chain
            is_spend: True to deduct, False to add

        Returns:
            Dict with tx_hash, chain_id on success; status/message on skip/error.
        """
        if not self.web3 or not self.is_connected():
            return {"status": "skipped", "message": "Blockchain not connected"}
        addr = settings.CREDIT_TOKEN_CONTRACT
        if not addr or "credit_token" not in self._contract_abis or not self.deployer_account:
            return {"status": "skipped", "message": "CreditToken or deployer not configured"}

        amount_4 = int(round(amount * 10000))
        if amount_4 <= 0:
            return {"status": "skipped", "message": "amount is zero"}

        try:
            from web3 import Web3

            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["credit_token"],
            )
            fn = contract.functions.updateCredits(int(token_id), credit_type, amount_4, is_spend)
            gas = 150_000
            try:
                gas = fn.estimate_gas({"from": self.deployer_account.address})
            except Exception:
                pass
            tx = fn.build_transaction({
                "from": self.deployer_account.address,
                "gas": gas,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.deployer_account.address),
            })
            signed = self.deployer_account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                return {"status": "error", "message": f"Transaction reverted (status {receipt.status})"}
            return {
                "status": "completed",
                "tx_hash": tx_hash.hex(),
                "chain_id": self.web3.eth.chain_id,
            }
        except Exception as e:
            logger.error(f"update_credit_token failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def mint_outcome_token(
        self,
        recipient_address: str,
        outcome_token_id: int,
        amount: int,
        data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Mint SFP outcome tokens (ERC-1155) to a recipient. Used for Polymarket-style
        outcome tokens on OUTCOME_TOKEN_CHAIN_ID. Requires CROSS_CHAIN_ENABLED,
        SFP_OUTCOME_TOKEN_CONTRACT, and deployer account. Uses the same Web3/RPC as
        other contracts; ensure X402_NETWORK_RPC_URL targets OUTCOME_TOKEN_CHAIN_ID
        when minting outcome tokens.

        Args:
            recipient_address: Wallet to receive tokens
            outcome_token_id: ERC-1155 token id (outcome index)
            amount: Token amount (integer units; decimals are market-specific)
            data: Optional extra data for mint (default 0x)

        Returns:
            Dict with status, transaction_hash, outcome_token_id; or status/message on skip/error.
        """
        if not getattr(settings, "CROSS_CHAIN_ENABLED", False):
            return {"status": "skipped", "message": "CROSS_CHAIN_ENABLED is false"}
        addr = getattr(settings, "SFP_OUTCOME_TOKEN_CONTRACT", None)
        if not addr:
            return {"status": "skipped", "message": "SFP_OUTCOME_TOKEN_CONTRACT not configured"}
        if not self.web3 or not self.is_connected():
            return {"status": "skipped", "message": "Blockchain not connected"}
        if "sfp_outcome_token" not in self._contract_abis:
            return {"status": "skipped", "message": "SFPOutcomeToken ABI not loaded"}
        if not self.deployer_account:
            return {"status": "skipped", "message": "Deployer account not available"}

        try:
            from web3 import Web3

            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["sfp_outcome_token"],
            )
            hex_data = "0x" if not data else "0x" + data.hex()
            fn = contract.functions.mint(
                Web3.to_checksum_address(recipient_address),
                outcome_token_id,
                amount,
                hex_data,
            )
            gas = 150_000
            try:
                gas = fn.estimate_gas({"from": self.deployer_account.address})
            except Exception:
                pass
            tx = fn.build_transaction({
                "from": self.deployer_account.address,
                "gas": gas,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(self.deployer_account.address),
            })
            signed = self.deployer_account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                return {
                    "status": "error",
                    "message": f"Transaction reverted (status {receipt.status})",
                    "outcome_token_id": outcome_token_id,
                }
            logger.info(
                "SFPOutcomeToken minted: id=%s amount=%s to %s",
                outcome_token_id,
                amount,
                recipient_address[:10] + "...",
            )
            return {
                "status": "completed",
                "transaction_hash": tx_hash.hex(),
                "outcome_token_id": outcome_token_id,
                "amount": amount,
                "recipient": recipient_address,
            }
        except Exception as e:
            logger.error(f"mint_outcome_token failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "outcome_token_id": outcome_token_id,
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

    def get_challenge_coin_owner(self, token_id: int) -> Optional[str]:
        """Get owner of a ChallengeCoin NFT token.

        Args:
            token_id: ChallengeCoin NFT token ID.

        Returns:
            Owner wallet address or None if not configured or call fails.
        """
        if not self.web3 or not self.is_connected():
            return None
        addr = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
        if not addr or "challenge_coin" not in self._contract_abis:
            return None
        try:
            from web3 import Web3
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["challenge_coin"],
            )
            return contract.functions.ownerOf(token_id).call()
        except Exception as e:
            logger.error(f"get_challenge_coin_owner failed: {e}")
            return None

    def build_lock_for_bridge_tx(
        self, token_id: int, lock_duration: int, from_address: str
    ) -> Optional[Dict[str, Any]]:
        """Build an unsigned lockForBridge transaction for the token owner to sign.

        Args:
            token_id: ChallengeCoin NFT token ID.
            lock_duration: Lock duration in seconds.
            from_address: Owner address (signer).

        Returns:
            Transaction dict for eth_account.sign_transaction, or None if not configured.
        """
        if not self.web3 or not self.is_connected():
            return None
        addr = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
        if not addr or "challenge_coin" not in self._contract_abis:
            return None
        try:
            from web3 import Web3
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["challenge_coin"],
            )
            fn = contract.functions.lockForBridge(token_id, lock_duration)
            gas = 200_000
            try:
                gas = fn.estimate_gas({"from": from_address})
            except Exception:
                pass
            return fn.build_transaction({
                "from": from_address,
                "gas": gas,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(from_address),
            })
        except Exception as e:
            logger.error(f"build_lock_for_bridge_tx failed: {e}")
            return None

    def build_mint_challenge_coin_tx(
        self,
        to: str,
        asset_id: str,
        deal_id: str,
        asset_type: str,
        principal_amount: int,
        metadata_uri: str,
        from_address: str,
    ) -> Optional[Dict[str, Any]]:
        """Build an unsigned mintChallengeCoin transaction for owner/authorizedIssuer to sign.

        Args:
            to: Recipient address.
            asset_id: Unique asset identifier.
            deal_id: Associated deal ID.
            asset_type: Type of asset (e.g. loan, bond, equity).
            principal_amount: Principal in USDC 6-decimal units (e.g. 1_000000 for 1 USDC).
            metadata_uri: Metadata URI (e.g. IPFS or URL).
            from_address: Caller address (must be contract owner or authorizedIssuer).

        Returns:
            Transaction dict for signing, or None if not configured.
        """
        if not self.web3 or not self.is_connected():
            return None
        addr = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
        if not addr or "challenge_coin" not in self._contract_abis:
            return None
        try:
            from web3 import Web3
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["challenge_coin"],
            )
            fn = contract.functions.mintChallengeCoin(
                Web3.to_checksum_address(to),
                asset_id,
                deal_id,
                asset_type,
                principal_amount,
                metadata_uri,
            )
            gas = 300_000
            try:
                gas = fn.estimate_gas({"from": from_address})
            except Exception:
                pass
            return fn.build_transaction({
                "from": from_address,
                "gas": gas,
                "gasPrice": self.web3.eth.gas_price,
                "nonce": self.web3.eth.get_transaction_count(from_address),
            })
        except Exception as e:
            logger.error(f"build_mint_challenge_coin_tx failed: {e}")
            return None

    def get_challenge_coin_tokens_by_owner(self, owner_address: str) -> List[Dict[str, Any]]:
        """Return ChallengeCoin NFTs held by an address (ERC721Enumerable).

        Args:
            owner_address: Wallet address.

        Returns:
            List of {token_id, asset_id, deal_id, asset_type, principal_amount, ...}.
        """
        if not self.web3 or not self.is_connected():
            return []
        addr = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
        if not addr or "challenge_coin" not in self._contract_abis:
            return []
        out: List[Dict[str, Any]] = []
        try:
            from web3 import Web3
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=self._contract_abis["challenge_coin"],
            )
            owner = Web3.to_checksum_address(owner_address)
            n = contract.functions.balanceOf(owner).call()
            keys = (
                "assetId", "dealId", "assetType", "principalAmount", "issueDate",
                "issuer", "metadataURI", "locked", "lockedUntil",
            )
            for i in range(n):
                token_id = contract.functions.tokenOfOwnerByIndex(owner, i).call()
                t = contract.functions.getAssetMetadata(token_id).call()
                # t is a tuple in ABI order
                rec = {"token_id": token_id}
                for j, k in enumerate(keys):
                    if k == "assetId":
                        rec["asset_id"] = t[j]
                    elif k == "dealId":
                        rec["deal_id"] = t[j]
                    elif k == "assetType":
                        rec["asset_type"] = t[j]
                    elif k == "principalAmount":
                        rec["principal_amount"] = str(t[j])
                    elif k == "issueDate":
                        rec["issue_date"] = t[j]
                    elif k == "issuer":
                        rec["issuer"] = t[j]
                    elif k == "metadataURI":
                        rec["metadata_uri"] = t[j]
                    elif k == "locked":
                        rec["locked"] = bool(t[j])
                    elif k == "lockedUntil":
                        rec["locked_until"] = t[j]
                out.append(rec)
        except Exception as e:
            logger.warning("get_challenge_coin_tokens_by_owner: %s", e)
        return out
