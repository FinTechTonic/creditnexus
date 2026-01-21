"""
Polymarket-style prediction market service for Structured Financial Products.

Creates markets linked to SFP bundles (Merkle-anchored deal data), lists them,
and resolves them. Optionally anchors SFP to blockchain via SFPBundlerService.
Optionally registers markets with external Polymarket Gamma/CLOB when
POLYMARKET_PUBLISH_EXTERNAL is enabled.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Deal, MarketEvent, SFPPackage, User
from app.services.sfp_bundler_service import SFPBundlerService

logger = logging.getLogger(__name__)


class PolymarketServiceError(Exception):
    """Raised when Polymarket service operations fail."""

    pass


class PolymarketService:
    """Service for Polymarket-style prediction markets tied to SFPs."""

    def __init__(self, db: Session):
        self.db = db
        self._bundler = SFPBundlerService(db)
        self._api_client: Optional[Any] = None

    def _get_api_client(self) -> Optional[Any]:
        if self._api_client is None:
            try:
                from app.services.polymarket_api_client import PolymarketAPIClient
                self._api_client = PolymarketAPIClient()
            except Exception as e:
                logger.debug("PolymarketAPIClient not available: %s", e)
        return self._api_client

    def _check_enabled(self) -> None:
        if not getattr(settings, "POLYMARKET_ENABLED", False):
            raise PolymarketServiceError("Polymarket is disabled (POLYMARKET_ENABLED=false)")

    def create_market(
        self,
        deal_id: int,
        question: str,
        outcome_type: str,
        resolution_condition: Dict[str, Any],
        created_by: int,
        *,
        market_event_type: str = "NDVI_COMPLIANCE",
        anchor_to_blockchain: bool = True,
        signers: Optional[List[str]] = None,
        liquidity_pool_address: Optional[str] = None,
        visibility: str = "public",
        publish_to_polymarket: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Create a prediction market for a deal: bundle SFP, optionally anchor, create SFPPackage and MarketEvent.

        Args:
            deal_id: Deal ID
            question: Market question (e.g. "Will NDVI remain above 0.5?")
            outcome_type: e.g. "binary", "categorical"
            resolution_condition: JSON-serializable condition (e.g. {"type":"NDVI_COMPLIANCE","threshold":0.5})
            created_by: User ID of creator
            market_event_type: Type for SFP bundle (default NDVI_COMPLIANCE)
            anchor_to_blockchain: Whether to call SFPBundler.anchor_sfp_to_blockchain
            signers: Addresses for notarization; if None and anchor=True, bundler uses deployer
            liquidity_pool_address: Optional CLOB/liquidity pool address
            visibility: "public" or "internal"

        Returns:
            Dict with market_id, sfp_id, merkle_root, transaction_hash (if anchored), resolution_condition, created_at.
        """
        self._check_enabled()

        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise PolymarketServiceError(f"Deal {deal_id} not found")

        creator = self.db.query(User).filter(User.id == created_by).first()
        if not creator:
            raise PolymarketServiceError(f"User {created_by} not found")

        # 1) Bundle SFP
        bundle = self._bundler.bundle_sfp(deal_id=deal_id, market_event_type=market_event_type)
        sfp_id = bundle["sfp_id"]
        merkle_root = bundle["merkle_root"]

        # 2) Optionally anchor to blockchain
        tx_hash: Optional[str] = None
        block_number: Optional[int] = None
        if anchor_to_blockchain:
            anchor_result = self._bundler.anchor_sfp_to_blockchain(
                sfp_bundle=bundle,
                signers=signers or [],
            )
            tx_hash = anchor_result.get("transaction_hash")
            block_number = anchor_result.get("block_number")

        # 3) Persist SFPPackage
        ts = datetime.utcnow()
        bundle_ts = bundle.get("bundle_timestamp") or ts.isoformat()
        if isinstance(bundle_ts, str):
            try:
                bundle_ts = datetime.fromisoformat(bundle_ts.replace("Z", "+00:00"))
            except Exception:
                bundle_ts = ts

        pkg = SFPPackage(
            sfp_id=sfp_id,
            deal_id=deal_id,
            merkle_root=merkle_root,
            cdm_hash=bundle["cdm_hash"],
            signature_hashes=bundle["signature_hashes"],
            filing_hashes=bundle["filing_hashes"],
            transaction_hash=tx_hash,
            block_number=block_number,
            bundle_timestamp=bundle_ts,
            market_event_type=market_event_type,
        )
        self.db.add(pkg)
        self.db.flush()

        # 4) Persist MarketEvent
        market_id = f"MKT_{deal_id}_{ts.strftime('%Y%m%d%H%M%S')}"
        evt = MarketEvent(
            market_id=market_id,
            sfp_package_id=pkg.id,
            deal_id=deal_id,
            question=question,
            outcome_type=outcome_type,
            resolution_condition=resolution_condition,
            created_by=created_by,
            liquidity_pool_address=liquidity_pool_address,
            visibility=visibility,
        )
        self.db.add(evt)
        self.db.commit()
        self.db.refresh(evt)

        out: Dict[str, Any] = {
            "market_id": market_id,
            "sfp_id": sfp_id,
            "merkle_root": merkle_root,
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "resolution_condition": resolution_condition,
            "created_at": evt.created_at.isoformat() if evt.created_at else None,
        }

        # Optionally register with Polymarket Gamma/CLOB for SFP/securitized products
        do_publish = publish_to_polymarket if publish_to_polymarket is not None else getattr(settings, "POLYMARKET_PUBLISH_EXTERNAL", False)
        if do_publish:
            client = self._get_api_client()
            if client:
                outcomes_list: List[str] = ["Yes", "No"]
                if outcome_type == "categorical" and isinstance(resolution_condition.get("outcomes"), list):
                    outcomes_list = [str(o) for o in resolution_condition["outcomes"]]
                pub = client.register_sfp_market(
                    question=question,
                    description=question,
                    outcomes=outcomes_list,
                    sfp_id=sfp_id,
                    merkle_root=merkle_root,
                    deal_id=deal_id,
                    resolution_condition=resolution_condition,
                    liquidity_pool_address=liquidity_pool_address,
                )
                out["polymarket_publish"] = pub
            else:
                out["polymarket_publish"] = {"success": False, "reason": "client_unavailable", "message": "PolymarketAPIClient not loaded"}

        return out

    def list_markets(
        self,
        *,
        deal_id: Optional[int] = None,
        resolved: Optional[bool] = None,
        visibility: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List market events with optional filters.

        Args:
            deal_id: Filter by deal
            resolved: If True, only resolved; if False, only open; if None, all
            visibility: Filter by visibility (e.g. "public")
            limit: Max results
            offset: Pagination offset

        Returns:
            List of dicts with market_id, deal_id, question, outcome_type, resolution_condition,
            resolved_at, resolution_outcome, oracle_triggered, created_at, sfp_id, merkle_root.
        """
        self._check_enabled()

        q = self.db.query(MarketEvent).join(MarketEvent.sfp_package)
        if deal_id is not None:
            q = q.filter(MarketEvent.deal_id == deal_id)
        if resolved is True:
            q = q.filter(MarketEvent.resolved_at.isnot(None))
        elif resolved is False:
            q = q.filter(MarketEvent.resolved_at.is_(None))
        if visibility is not None:
            q = q.filter(MarketEvent.visibility == visibility)

        rows = q.order_by(MarketEvent.created_at.desc()).offset(offset).limit(limit).all()
        out: List[Dict[str, Any]] = []
        for evt in rows:
            pkg = evt.sfp_package
            out.append({
                "market_id": evt.market_id,
                "deal_id": evt.deal_id,
                "question": evt.question,
                "outcome_type": evt.outcome_type,
                "resolution_condition": evt.resolution_condition or {},
                "resolved_at": evt.resolved_at.isoformat() if evt.resolved_at else None,
                "resolution_outcome": evt.resolution_outcome,
                "oracle_triggered": evt.oracle_triggered or False,
                "created_at": evt.created_at.isoformat() if evt.created_at else None,
                "sfp_id": pkg.sfp_id if pkg else None,
                "merkle_root": pkg.merkle_root if pkg else None,
            })
        return out

    def resolve_market(
        self,
        market_id: str,
        resolution_outcome: str,
        *,
        oracle_triggered: bool = False,
    ) -> Dict[str, Any]:
        """
        Mark a market as resolved.

        Args:
            market_id: Market ID (e.g. MKT_1_20260121120000)
            resolution_outcome: "yes", "no", or category value
            oracle_triggered: Whether resolution was triggered by oracle/automation

        Returns:
            Dict with market_id, resolved_at, resolution_outcome, oracle_triggered.
        """
        self._check_enabled()

        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")
        if evt.resolved_at is not None:
            raise PolymarketServiceError(f"Market {market_id} already resolved")

        evt.resolved_at = datetime.utcnow()
        evt.resolution_outcome = resolution_outcome
        evt.oracle_triggered = oracle_triggered
        self.db.commit()
        self.db.refresh(evt)

        return {
            "market_id": market_id,
            "resolved_at": evt.resolved_at.isoformat() if evt.resolved_at else None,
            "resolution_outcome": evt.resolution_outcome,
            "oracle_triggered": evt.oracle_triggered or False,
        }
