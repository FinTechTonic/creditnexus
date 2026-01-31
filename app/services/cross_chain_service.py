"""Cross-chain message service (Phase 8). Submit, status, and list cross-chain messages.
Reuses CrossChainTransaction for persistence; integrates with BridgeService or org bridge contracts.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import CrossChainTransaction

logger = logging.getLogger(__name__)


class CrossChainService:
    """Submit and query cross-chain messages (bridge/org contracts)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def submit_message(
        self,
        org_id: int,
        source_chain_id: int,
        dest_chain_id: int,
        transaction_type: str,
        payload: Dict[str, Any],
        *,
        user_id: int,
    ) -> int:
        """Create a cross-chain message record (pending); return message id."""
        rec = CrossChainTransaction(
            user_id=user_id,
            organization_id=org_id,
            source_chain_id=source_chain_id,
            dest_chain_id=dest_chain_id,
            status="pending",
            extra_data={"transaction_type": transaction_type, "payload": payload},
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        logger.info("CrossChainService.submit_message created id=%s org_id=%s", rec.id, org_id)
        return rec.id

    def get_message_status(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Return status and details for a cross-chain message."""
        rec = self.db.query(CrossChainTransaction).filter(CrossChainTransaction.id == message_id).first()
        if not rec:
            return None
        return {
            "id": rec.id,
            "status": rec.status,
            "source_chain_id": rec.source_chain_id,
            "dest_chain_id": rec.dest_chain_id,
            "bridge_external_id": rec.bridge_external_id,
            "dest_tx_hash": rec.dest_tx_hash,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
            "extra_data": rec.extra_data,
        }

    def list_messages(
        self,
        org_id: int,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List cross-chain messages for org with optional status filter."""
        q = self.db.query(CrossChainTransaction).filter(CrossChainTransaction.organization_id == org_id)
        if status:
            q = q.filter(CrossChainTransaction.status == status)
        rows = q.order_by(CrossChainTransaction.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "source_chain_id": r.source_chain_id,
                "dest_chain_id": r.dest_chain_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
