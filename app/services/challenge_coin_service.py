"""Challenge Coin service for issuing ChallengeCoin NFTs.

Uses BlockchainService to build mintChallengeCoin transactions. Caller must
be contract owner or authorizedIssuer; app-side we enforce PERMISSION_ISSUE_CHALLENGE_COIN
and roles banker, trader, admin.
"""

import hashlib
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.permissions import has_permission, PERMISSION_ISSUE_CHALLENGE_COIN
from app.db.models import User, UserRole
from app.services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)


class ChallengeCoinService:
    """Service for issuing and managing ChallengeCoin NFTs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.blockchain = BlockchainService()

    def _can_issue_challenge_coin(self, user: User) -> bool:
        """Check if user can issue challenge coins (role or permission)."""
        allowed = (
            UserRole.BANKER.value,
            UserRole.TRADER.value,
            UserRole.ADMIN.value,
        )
        if user.role in allowed:
            return True
        return bool(has_permission(user, PERMISSION_ISSUE_CHALLENGE_COIN))

    def _generate_metadata_uri(
        self, asset_id: str, deal_id: str, asset_type: str, principal_amount: Decimal
    ) -> str:
        """Generate a deterministic metadata URI for the challenge coin."""
        h = hashlib.sha256(
            f"{asset_id}:{deal_id}:{asset_type}:{principal_amount}".encode()
        ).hexdigest()[:16]
        return f"https://metadata.creditnexus.example/challenge-coin/{asset_id}#{h}"

    def issue_challenge_coin(
        self,
        user_id: int,
        asset_id: str,
        deal_id: str,
        asset_type: str,
        principal_amount: Decimal,
        recipient_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build an unsigned mintChallengeCoin transaction for the user to sign.

        The caller (from_address) must be the contract owner or an authorizedIssuer
        on-chain; we enforce app-side that the user has ISSUE_CHALLENGE_COIN or
        role banker/trader/admin.

        Args:
            user_id: User ID issuing the coin.
            asset_id: Unique asset identifier.
            deal_id: Associated deal ID.
            asset_type: Type of asset (e.g. loan, bond, equity).
            principal_amount: Principal in USDC (e.g. Decimal("1000.00")); converted to 6 decimals.
            recipient_address: Recipient wallet; defaults to the user's wallet.

        Returns:
            Dict with asset_id, transaction (unsigned tx for signing), and metadata_uri.

        Raises:
            ValueError: If user not found, no wallet, or not allowed to issue.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not self._can_issue_challenge_coin(user):
            raise PermissionError(
                "User does not have permission to issue challenge coins. "
                "Requires role banker, trader, or admin, or ISSUE_CHALLENGE_COIN."
            )
        wallet = getattr(user, "wallet_address", None)
        if not wallet or not str(wallet).strip():
            raise ValueError("User has no wallet address")

        recipient = (recipient_address or "").strip() or wallet
        principal_wei = int(principal_amount * Decimal("1000000"))

        metadata_uri = self._generate_metadata_uri(
            asset_id=asset_id,
            deal_id=deal_id,
            asset_type=asset_type,
            principal_amount=principal_amount,
        )

        tx = self.blockchain.build_mint_challenge_coin_tx(
            to=recipient,
            asset_id=asset_id,
            deal_id=deal_id,
            asset_type=asset_type,
            principal_amount=principal_wei,
            metadata_uri=metadata_uri,
            from_address=wallet,
        )
        if not tx:
            raise ValueError(
                "Could not build mint transaction. Set CHALLENGE_COIN_NFT_CONTRACT and ensure RPC."
            )

        return {
            "asset_id": asset_id,
            "transaction": tx,
            "metadata_uri": metadata_uri,
        }
