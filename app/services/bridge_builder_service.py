"""Bridge Builder service for ChallengeCoin NFT cross-chain trades.

Uses BlockchainService for lockForBridge tx building and BridgeService for
cross-chain bridge API. Persists BridgeTrade records.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BridgeTrade, User
from app.services.blockchain_service import BlockchainService
from app.services.bridge_service import BridgeService

logger = logging.getLogger(__name__)


class BridgeBuilderService:
    """Service for building and executing ChallengeCoin NFT cross-chain trades."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.blockchain = BlockchainService()
        self.bridge = BridgeService()

    def create_bridge_trade(
        self,
        user_id: int,
        token_id: int,
        source_chain_id: int,
        target_chain_id: int,
        target_address: str,
        trade_type: str = "transfer",
    ) -> Dict[str, Any]:
        """Create a bridge trade for a ChallengeCoin NFT.

        Verifies token ownership and builds an unsigned lockForBridge transaction
        for the client to sign. Persists a BridgeTrade with status 'pending'.

        Args:
            user_id: User ID initiating the trade.
            token_id: ChallengeCoin NFT token ID.
            source_chain_id: Source chain ID.
            target_chain_id: Target chain ID.
            target_address: Target address on destination chain.
            trade_type: Type of trade (default 'transfer').

        Returns:
            Dict with trade_id, status 'pending', and lock_transaction (tx dict for signing).

        Raises:
            ValueError: If user not found, no wallet, not owner, or blockchain/contract not ready.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        wallet = getattr(user, "wallet_address", None)
        if not wallet or not str(wallet).strip():
            raise ValueError("User has no wallet address")

        # Verify ownership on-chain
        owner = self.blockchain.get_challenge_coin_owner(token_id)
        if not owner:
            raise ValueError(
                "ChallengeCoin contract not configured or token not found. "
                "Set CHALLENGE_COIN_NFT_CONTRACT and ensure the token exists."
            )
        if str(owner).lower() != str(wallet).lower():
            raise ValueError("User does not own this token")

        # Build lock tx for the user to sign (lock_duration 1 hour)
        lock_duration = 3600
        lock_tx = self.blockchain.build_lock_for_bridge_tx(
            token_id=token_id, lock_duration=lock_duration, from_address=wallet
        )
        if not lock_tx:
            raise ValueError(
                "Could not build lock transaction. Check CHALLENGE_COIN_NFT_CONTRACT and RPC."
            )

        trade = BridgeTrade(
            user_id=user_id,
            token_id=token_id,
            source_chain_id=source_chain_id,
            target_chain_id=target_chain_id,
            target_address=target_address.strip(),
            trade_type=trade_type,
            status="pending",
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        return {
            "trade_id": trade.id,
            "status": "pending",
            "lock_transaction": lock_tx,
        }

    async def execute_bridge_trade(
        self, trade_id: int, signed_lock_tx_hex: str
    ) -> Dict[str, Any]:
        """Execute a bridge trade after the user has signed the lock transaction.

        Sends the signed lock tx on the source chain, then submits a bridge
        request to the bridge API when available. Updates BridgeTrade to
        'locked' and then 'bridging' if the bridge API is used.

        Args:
            trade_id: Bridge trade ID from create_bridge_trade.
            signed_lock_tx_hex: Hex of the signed raw transaction (with or without '0x').

        Returns:
            Dict with trade_id, status, lock_tx_hash, and optionally bridge_transaction_id.

        Raises:
            ValueError: If trade not found or lock tx fails.
        """
        trade = self.db.query(BridgeTrade).filter(BridgeTrade.id == trade_id).first()
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        if trade.status != "pending":
            raise ValueError(f"Trade {trade_id} is not pending (status={trade.status})")

        raw_hex = signed_lock_tx_hex.strip()
        if not raw_hex.startswith("0x"):
            raw_hex = "0x" + raw_hex

        if not self.blockchain.web3 or not self.blockchain.is_connected():
            raise ValueError("Blockchain not connected")

        # Send signed lock tx (raw hex; send_raw_transaction expects 0x-prefixed hex)
        try:
            tx_hash = self.blockchain.web3.eth.send_raw_transaction(raw_hex)
        except Exception as e:
            logger.error("execute_bridge_trade send_raw_transaction failed: %s", e)
            raise ValueError(f"Lock transaction failed: {e}") from e

        receipt = self.blockchain.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            trade.status = "failed"
            self.db.commit()
            raise ValueError(f"Lock transaction reverted (status {receipt.status})")

        lock_tx_hash = tx_hash.hex()
        trade.lock_tx_hash = lock_tx_hash
        trade.status = "locked"
        self.db.commit()

        bridge_external_id: str | None = None
        if self.bridge.is_available:
            cc_contract = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
            try:
                result = await self.bridge.submit_bridge(
                    source_chain_id=trade.source_chain_id,
                    dest_chain_id=trade.target_chain_id,
                    amount="1",
                    token_address=cc_contract or "0x0000000000000000000000000000000000000000",
                    sender_address=((trade.user and getattr(trade.user, "wallet_address", None)) or ""),
                    receiver_address=trade.target_address,
                    extra={
                        "challenge_coin_token_id": trade.token_id,
                        "target_address": trade.target_address,
                        "asset_type": "challenge_coin_nft",
                    },
                )
                bridge_external_id = result.get("bridge_id") or result.get("id") or str(result)
                trade.bridge_external_id = bridge_external_id
                trade.status = "bridging"
                self.db.commit()
            except Exception as e:
                logger.warning("Bridge API submit_bridge failed (trade continues as locked): %s", e)

        return {
            "trade_id": trade.id,
            "status": trade.status,
            "lock_tx_hash": lock_tx_hash,
            "bridge_transaction_id": bridge_external_id,
        }

    async def execute_bridge_trade_with_lock_hash(
        self, trade_id: int, lock_tx_hash: str
    ) -> Dict[str, Any]:
        """Mark a trade as locked when the client has already sent the lock tx (e.g. via MetaMask).

        Updates the trade with lock_tx_hash and status=locked, then submits to the
        bridge API if available (status=bridging).
        """
        trade = self.db.query(BridgeTrade).filter(BridgeTrade.id == trade_id).first()
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        if trade.status != "pending":
            raise ValueError(f"Trade {trade_id} is not pending (status={trade.status})")
        trade.lock_tx_hash = lock_tx_hash.strip()
        trade.status = "locked"
        self.db.commit()

        bridge_external_id: str | None = None
        if self.bridge.is_available:
            cc_contract = getattr(settings, "CHALLENGE_COIN_NFT_CONTRACT", None) or ""
            try:
                result = await self.bridge.submit_bridge(
                    source_chain_id=trade.source_chain_id,
                    dest_chain_id=trade.target_chain_id,
                    amount="1",
                    token_address=cc_contract or "0x0000000000000000000000000000000000000000",
                    sender_address=((trade.user and getattr(trade.user, "wallet_address", None)) or ""),
                    receiver_address=trade.target_address,
                    extra={
                        "challenge_coin_token_id": trade.token_id,
                        "target_address": trade.target_address,
                        "asset_type": "challenge_coin_nft",
                    },
                )
                bridge_external_id = result.get("bridge_id") or result.get("id") or str(result)
                trade.bridge_external_id = bridge_external_id
                trade.status = "bridging"
                self.db.commit()
            except Exception as e:
                logger.warning("Bridge API submit_bridge failed (trade continues as locked): %s", e)

        return {
            "trade_id": trade.id,
            "status": trade.status,
            "lock_tx_hash": trade.lock_tx_hash,
            "bridge_transaction_id": bridge_external_id,
        }
