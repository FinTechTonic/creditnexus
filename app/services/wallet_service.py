"""Wallet service for wallet address management and auto-generation."""

import logging
import hashlib
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)


class WalletService:
    """Service for wallet address management and auto-generation."""
    
    def ensure_user_has_wallet(
        self, 
        user: User, 
        db: Session,
        generate_if_missing: bool = True
    ) -> Optional[str]:
        """
        Ensure user has a wallet address.
        
        If user has wallet_address, return it.
        If missing and generate_if_missing=True, generate a deterministic address
        from user ID (for demo/testing) or prompt MetaMask connection.
        
        Args:
            user: User instance
            db: Database session
            generate_if_missing: If True, auto-generate demo wallet if missing
            
        Returns:
            Wallet address or None
        """
        if user.wallet_address:
            return user.wallet_address
        
        if generate_if_missing and settings.WALLET_AUTO_GENERATE_DEMO:
            # For demo/testing: Generate deterministic address from user ID
            # In production, this would prompt MetaMask connection
            demo_wallet = self._generate_demo_wallet_address(user.id)
            user.wallet_address = demo_wallet
            db.commit()
            logger.info(f"Auto-generated demo wallet for user {user.id}: {demo_wallet}")
            return demo_wallet
        
        return None
    
    def _generate_demo_wallet_address(self, user_id: int) -> str:
        """Generate deterministic demo wallet address from user ID.
        
        Args:
            user_id: User ID to generate wallet from
            
        Returns:
            Ethereum wallet address (checksum format)
        """
        try:
            from eth_account import Account
            
            # Create deterministic private key from user ID
            seed = f"creditnexus_demo_user_{user_id}".encode()
            private_key = hashlib.sha256(seed).digest()
            account = Account.from_key(private_key)
            return account.address
        except ImportError:
            logger.error("eth_account not available, cannot generate demo wallet")
            # Fallback: Generate a deterministic fake address
            seed = f"creditnexus_demo_user_{user_id}".encode()
            hash_bytes = hashlib.sha256(seed).digest()[:20]
            # Format as Ethereum address (0x + 40 hex chars)
            fake_address = "0x" + hash_bytes.hex()
            return fake_address
