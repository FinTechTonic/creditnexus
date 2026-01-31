"""
Bridge credit verification service (Phase 12): verify credit usage on-chain and optional sync/bridge.

- verify_credit_usage: Check that a credit usage (CreditTransaction) is reflected on blockchain.
- convert_credits_via_bridge: Convert/move credits via cross-chain bridge (stub or integrate).
- _get_blockchain_credit_balance: Read CreditToken balance for a user/token from chain.
- _sync_balance_from_blockchain: Sync DB CreditBalance from on-chain state.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CreditBalance, CreditTransaction
from app.services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)


class BridgeCreditVerificationServiceError(Exception):
    pass


class BridgeCreditVerificationService:
    """Verify and sync rolling credits with blockchain; optional bridge conversion."""

    def __init__(self, db: Session, blockchain_service: Optional[BlockchainService] = None) -> None:
        self.db = db
        self._blockchain = blockchain_service or BlockchainService()

    def verify_credit_usage(
        self,
        user_id: int,
        credit_type: str,
        amount: float,
        *,
        transaction_id: Optional[int] = None,
        sync_from_chain: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify that a credit usage is reflected on blockchain (optional: sync DB from chain first).

        Returns:
            { "verified": bool, "reason": str, "on_chain_balance": float | None }
        """
        balance = (
            self.db.query(CreditBalance)
            .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
            .first()
        )
        if not balance:
            return {"verified": False, "reason": "no_balance", "on_chain_balance": None}
        if not balance.blockchain_registered or not balance.blockchain_token_id:
            return {"verified": True, "reason": "not_on_chain", "on_chain_balance": None}
        if sync_from_chain:
            self._sync_balance_from_blockchain(user_id)
        on_chain = self._get_blockchain_credit_balance(user_id=user_id)
        if on_chain is None:
            return {"verified": True, "reason": "chain_read_unavailable", "on_chain_balance": None}
        total_on_chain = on_chain.get("total") or 0
        db_total = float(balance.total_balance or 0)
        if abs(total_on_chain - db_total) <= 0.0001:
            if transaction_id:
                tx = self.db.query(CreditTransaction).filter(CreditTransaction.id == transaction_id).first()
                if tx:
                    tx.blockchain_verified = True
                    self.db.commit()
            return {"verified": True, "reason": "match", "on_chain_balance": total_on_chain}
        return {"verified": False, "reason": "mismatch", "on_chain_balance": total_on_chain}

    def convert_credits_via_bridge(
        self,
        user_id: int,
        amount: float,
        *,
        source_chain_id: Optional[int] = None,
        target_chain_id: Optional[int] = None,
        credit_type: str = "universal",
    ) -> Dict[str, Any]:
        """
        Convert/move credits via cross-chain bridge (stub: not implemented).

        Returns:
            { "ok": bool, "reason": str, "bridge_tx_hash": str | None }
        """
        if not source_chain_id or not target_chain_id:
            return {"ok": False, "reason": "source_chain_id and target_chain_id required", "bridge_tx_hash": None}
        logger.info("convert_credits_via_bridge stub: user_id=%s amount=%s", user_id, amount)
        return {"ok": False, "reason": "not_implemented", "bridge_tx_hash": None}

    def _get_blockchain_credit_balance(
        self,
        *,
        user_id: Optional[int] = None,
        token_id: Optional[int] = None,
        wallet_address: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Read CreditToken balance from chain (by token_id or user's token).

        Returns:
            { "total": float, "by_type": { credit_type: float } } or None if read not available.
        """
        if not settings.CREDIT_TOKEN_CONTRACT or "credit_token" not in getattr(
            self._blockchain, "_contract_abis", {}
        ):
            return None
        if token_id is None and user_id is not None:
            balance = (
                self.db.query(CreditBalance)
                .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
                .first()
            )
            if not balance or not balance.blockchain_token_id:
                return None
            try:
                token_id = int(balance.blockchain_token_id)
            except (TypeError, ValueError):
                return None
        if token_id is None:
            return None
        try:
            from web3 import Web3
            addr = settings.CREDIT_TOKEN_CONTRACT
            abis = getattr(self._blockchain, "_contract_abis", None) or {}
            if "credit_token" not in abis or not getattr(self._blockchain, "web3", None):
                return None
            contract = self._blockchain.web3.eth.contract(
                address=Web3.to_checksum_address(addr),
                abi=abis["credit_token"],
            )
            if hasattr(contract.functions, "getCredits"):
                struct = contract.functions.getCredits(token_id).call()
                order = getattr(BlockchainService, "_CREDIT_STRUCT_ORDER", ())
                by_type: Dict[str, float] = {}
                for i, ct in enumerate(order):
                    if i < len(struct):
                        by_type[ct] = struct[i] / 10000.0
                total = sum(by_type.values())
                return {"total": total, "by_type": by_type}
        except Exception as e:
            logger.debug("_get_blockchain_credit_balance failed: %s", e)
        return None

    def _sync_balance_from_blockchain(self, user_id: int) -> Dict[str, Any]:
        """
        Sync DB CreditBalance from on-chain state (overwrite balances from chain).

        Returns:
            { "synced": bool, "reason": str, "total": float | None }
        """
        balance = (
            self.db.query(CreditBalance)
            .filter(CreditBalance.user_id == user_id, CreditBalance.organization_id.is_(None))
            .first()
        )
        if not balance:
            return {"synced": False, "reason": "no_balance", "total": None}
        if not balance.blockchain_registered or not balance.blockchain_token_id:
            return {"synced": False, "reason": "not_on_chain", "total": None}
        on_chain = self._get_blockchain_credit_balance(user_id=user_id)
        if on_chain is None:
            return {"synced": False, "reason": "chain_read_unavailable", "total": None}
        by_type = on_chain.get("by_type") or {}
        total = on_chain.get("total") or 0
        balance.balances = {k: round(v, 4) for k, v in by_type.items()}
        balance.total_balance = Decimal(str(round(total, 4)))
        balance.last_updated = datetime.utcnow()
        self.db.commit()
        self.db.refresh(balance)
        return {"synced": True, "reason": "ok", "total": total}
