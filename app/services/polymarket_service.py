"""
Internal SFP marketplace: notarize and list structured financial products in CreditNexus.

- SFPs are bundled (CDM + signatures + filings → Merkle root), anchored on-chain via
  SecuritizationNotarization.createNotarization, and listed only in CreditNexus.
- All create/list/resolve/order-book flows are internal. External Polymarket is used
  only for optional "Browse Polymarket" (read-only) and optional explicit export
  (publish_to_polymarket=True); SFPs are never listed on external Polymarket by default.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Deal, GreenFinanceAssessment, MarketEvent, MarketOrder, SFPPackage, User
from app.services.newsfeed_service import NewsfeedService, NewsfeedServiceError
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
        question: str,
        outcome_type: str,
        resolution_condition: Dict[str, Any],
        created_by: int,
        *,
        deal_id: Optional[int] = None,
        pool_id: Optional[int] = None,
        tranche_id: Optional[int] = None,
        loan_asset_id: Optional[int] = None,
        market_event_type: str = "NDVI_COMPLIANCE",
        anchor_to_blockchain: bool = True,
        signers: Optional[List[str]] = None,
        liquidity_pool_address: Optional[str] = None,
        visibility: str = "public",
        publish_to_polymarket: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Create a prediction market: for a deal (SFP+bundle+anchor), or list pool/tranche for funding, or loan binary.
        When pool_id, tranche_id, or loan_asset_id is set: skip SFP bundle and anchor; create MarketEvent with those FKs.
        """
        self._check_enabled()

        creator = self.db.query(User).filter(User.id == created_by).first()
        if not creator:
            raise PolymarketServiceError(f"User {created_by} not found")

        ts = datetime.utcnow()
        ts_s = ts.strftime("%Y%m%d%H%M%S")
        is_listing = pool_id is not None or tranche_id is not None or loan_asset_id is not None

        if is_listing:
            # Pool/tranche/loan listing: no SFP, no anchor
            if pool_id is not None:
                from app.db.models import SecuritizationPool
                if not self.db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first():
                    raise PolymarketServiceError(f"Pool {pool_id} not found")
                market_id = f"MKT_P{pool_id}_{ts_s}"
            elif tranche_id is not None:
                from app.db.models import SecuritizationTranche
                if not self.db.query(SecuritizationTranche).filter(SecuritizationTranche.id == tranche_id).first():
                    raise PolymarketServiceError(f"Tranche {tranche_id} not found")
                market_id = f"MKT_T{tranche_id}_{ts_s}"
            else:
                from app.db.models import LoanAsset
                if not self.db.query(LoanAsset).filter(LoanAsset.id == loan_asset_id).first():
                    raise PolymarketServiceError(f"Loan asset {loan_asset_id} not found")
                market_id = f"MKT_L{loan_asset_id}_{ts_s}"

            evt = MarketEvent(
                market_id=market_id,
                sfp_package_id=None,
                deal_id=None,
                pool_id=pool_id,
                tranche_id=tranche_id,
                loan_asset_id=loan_asset_id,
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
            try:
                newsfeed = NewsfeedService(self.db)
                newsfeed.create_market_post(
                    market_id=evt.id,
                    author_id=created_by,
                    organization_id=getattr(creator, "organization_id", None),
                )
            except NewsfeedServiceError as e:
                logger.warning("create_market_post after listing create failed: %s", e)
            return {
                "market_id": market_id,
                "sfp_id": None,
                "merkle_root": None,
                "transaction_hash": None,
                "block_number": None,
                "resolution_condition": resolution_condition,
                "created_at": evt.created_at.isoformat() if evt.created_at else None,
                "pool_id": pool_id,
                "tranche_id": tranche_id,
                "loan_asset_id": loan_asset_id,
            }
        # Deal path: bundle SFP, optionally anchor
        if not deal_id:
            raise PolymarketServiceError("deal_id required when not using pool_id/tranche_id/loan_asset_id")
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise PolymarketServiceError(f"Deal {deal_id} not found")

        bundle = self._bundler.bundle_sfp(deal_id=deal_id, market_event_type=market_event_type)
        sfp_id = bundle["sfp_id"]
        merkle_root = bundle["merkle_root"]

        tx_hash: Optional[str] = None
        block_number: Optional[int] = None
        if anchor_to_blockchain:
            anchor_result = self._bundler.anchor_sfp_to_blockchain(
                sfp_bundle=bundle,
                signers=signers or [],
            )
            tx_hash = anchor_result.get("transaction_hash")
            block_number = anchor_result.get("block_number")

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

        market_id = f"MKT_{deal_id}_{ts_s}"
        evt = MarketEvent(
            market_id=market_id,
            sfp_package_id=pkg.id,
            deal_id=deal_id,
            pool_id=None,
            tranche_id=None,
            loan_asset_id=None,
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

        try:
            newsfeed = NewsfeedService(self.db)
            newsfeed.create_market_post(
                market_id=evt.id,
                author_id=created_by,
                organization_id=getattr(creator, "organization_id", None),
            )
        except NewsfeedServiceError as e:
            logger.warning("create_market_post after deal create failed: %s", e)

        out: Dict[str, Any] = {
            "market_id": market_id,
            "sfp_id": sfp_id,
            "merkle_root": merkle_root,
            "transaction_hash": tx_hash,
            "block_number": block_number,
            "resolution_condition": resolution_condition,
            "created_at": evt.created_at.isoformat() if evt.created_at else None,
        }

        if publish_to_polymarket is True:
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

        q = self.db.query(MarketEvent)
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
            pkg = evt.sfp_package  # None for pool/tranche/loan listings
            out.append({
                "market_id": evt.market_id,
                "deal_id": evt.deal_id,
                "pool_id": evt.pool_id,
                "tranche_id": evt.tranche_id,
                "loan_asset_id": evt.loan_asset_id,
                "question": evt.question,
                "outcome_type": evt.outcome_type,
                "resolution_condition": evt.resolution_condition or {},
                "resolved_at": evt.resolved_at.isoformat() if evt.resolved_at else None,
                "resolution_outcome": evt.resolution_outcome,
                "oracle_triggered": evt.oracle_triggered or False,
                "created_at": evt.created_at.isoformat() if evt.created_at else None,
                "sfp_id": pkg.sfp_id if pkg else None,
                "merkle_root": pkg.merkle_root if pkg else None,
                "transaction_hash": pkg.transaction_hash if pkg else None,
                "block_number": pkg.block_number if pkg else None,
            })
        return out

    def get_funding_markets(
        self,
        *,
        visibility: Optional[str] = "public",
        resolved: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List markets suitable for funding: pool, tranche, or loan listings only.
        Excludes platform-created equities (deal_id-only SFP) and structured loan
        products per Week 17 roadmap; aligns with linked account + relayer for funding.
        """
        self._check_enabled()

        q = self.db.query(MarketEvent).filter(
            or_(
                MarketEvent.pool_id.isnot(None),
                MarketEvent.tranche_id.isnot(None),
                MarketEvent.loan_asset_id.isnot(None),
            )
        )
        if resolved is False:
            q = q.filter(MarketEvent.resolved_at.is_(None))
        elif resolved is True:
            q = q.filter(MarketEvent.resolved_at.isnot(None))
        if visibility is not None:
            q = q.filter(MarketEvent.visibility == visibility)

        rows = q.order_by(MarketEvent.created_at.desc()).offset(offset).limit(limit).all()
        out: List[Dict[str, Any]] = []
        for evt in rows:
            pkg = evt.sfp_package
            out.append({
                "market_id": evt.market_id,
                "deal_id": evt.deal_id,
                "pool_id": evt.pool_id,
                "tranche_id": evt.tranche_id,
                "loan_asset_id": evt.loan_asset_id,
                "question": evt.question,
                "outcome_type": evt.outcome_type,
                "resolution_condition": evt.resolution_condition or {},
                "resolved_at": evt.resolved_at.isoformat() if evt.resolved_at else None,
                "resolution_outcome": evt.resolution_outcome,
                "oracle_triggered": evt.oracle_triggered or False,
                "created_at": evt.created_at.isoformat() if evt.created_at else None,
                "sfp_id": pkg.sfp_id if pkg else None,
                "merkle_root": pkg.merkle_root if pkg else None,
                "transaction_hash": pkg.transaction_hash if pkg else None,
                "block_number": pkg.block_number if pkg else None,
            })
        return out

    def fund_via_polymarket(
        self,
        user_id: int,
        market_id: str,
        amount: Optional[float] = None,
        *,
        require_linked: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate funding eligibility for a market using linked Polymarket account.
        Does not perform payment; caller (route) should call unified_funding_service
        with payment_type=polymarket_funding. Returns ok, eligible, message, and
        destination_id for payment routing.
        """
        self._check_enabled()

        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            return {"ok": False, "eligible": False, "error": "market_not_found", "message": f"Market {market_id} not found"}

        if evt.resolved_at is not None:
            return {"ok": False, "eligible": False, "error": "market_resolved", "message": "Market is already resolved"}

        is_funding_market = evt.pool_id is not None or evt.tranche_id is not None or evt.loan_asset_id is not None
        if not is_funding_market:
            return {"ok": False, "eligible": False, "error": "not_funding_market", "message": "Market is not a funding market (pool/tranche/loan listing)"}

        if require_linked:
            from app.services.polymarket_account_service import get_user_l2_creds
            creds = get_user_l2_creds(user_id, self.db)
            if not creds or not creds.get("api_key"):
                return {"ok": False, "eligible": False, "error": "polymarket_not_linked", "message": "Link Polymarket account (BYOK) to fund."}

        amt = float(amount) if amount is not None else 0.0
        return {
            "ok": True,
            "eligible": True,
            "market_id": market_id,
            "destination_id": market_id,
            "amount": amt if amt > 0 else None,
            "message": "Eligible; use POST /api/funding/request with payment_type=polymarket_funding.",
        }

    def resolve_market(
        self,
        market_id: str,
        resolution_outcome: str,
        *,
        oracle_triggered: bool = False,
        policy_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Mark a market as resolved.

        Args:
            market_id: Market ID (e.g. MKT_1_20260121120000)
            resolution_outcome: "yes", "no", or category value
            oracle_triggered: Whether resolution was triggered by oracle/automation
            policy_service: Optional PolicyService; if provided, BLOCK blocks resolution.

        Returns:
            Dict with market_id, resolved_at, resolution_outcome, oracle_triggered.
        """
        self._check_enabled()

        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")
        if evt.resolved_at is not None:
            raise PolymarketServiceError(f"Market {market_id} already resolved")

        if policy_service is not None:
            decision = policy_service.evaluate_market_resolution(
                market_id,
                resolution_outcome,
                context={"oracle_triggered": oracle_triggered, "deal_id": evt.deal_id},
            )
            if decision.decision == "BLOCK":
                raise PolymarketServiceError(
                    f"Policy blocks resolution: {decision.rule_applied or 'rule'}"
                )

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

    async def suggest_resolution(self, market_id: str) -> Dict[str, Any]:
        """
        Suggest resolution outcome from Verifier/oracle (e.g. NDVI) when applicable.

        Uses resolution_condition type (e.g. NDVI_COMPLIANCE) and deal location
        (GreenFinanceAssessment->LoanAsset or deal_data address geocoding).
        Returns suggested_outcome "yes"|"no" or None if not applicable.
        """
        self._check_enabled()

        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")
        if evt.resolved_at is not None:
            raise PolymarketServiceError(f"Market {market_id} already resolved")

        cond = evt.resolution_condition or {}
        ctype = (cond.get("type") or "").upper()
        if ctype in ("LOAN_REPAID", "LOAN_ON_TIME", "LOAN_REPAID_CRYPTO"):
            return {
                "suggested_outcome": None,
                "reason": "oracle_not_implemented",
                "verification": {},
            }
        if ctype != "NDVI_COMPLIANCE":
            return {
                "suggested_outcome": None,
                "reason": "unsupported_condition_type",
                "verification": {},
            }

        threshold = float(cond.get("threshold", 0.5))

        deal = self.db.query(Deal).filter(Deal.id == evt.deal_id).first()
        if not deal:
            return {"suggested_outcome": None, "reason": "deal_not_found", "verification": {}}

        lat, lon = None, None

        # 1) GreenFinanceAssessment (location_lat, location_lon) for the deal
        gfa = (
            self.db.query(GreenFinanceAssessment)
            .filter(GreenFinanceAssessment.deal_id == evt.deal_id)
            .first()
        )
        if gfa and gfa.location_lat is not None and gfa.location_lon is not None:
            lat, lon = float(gfa.location_lat), float(gfa.location_lon)

        # 2) deal_data address -> geocode
        if lat is None and deal.deal_data:
            addr = (
                (deal.deal_data or {}).get("collateral_address")
                or (deal.deal_data or {}).get("address")
                or (deal.deal_data or {}).get("asset_address")
            )
            if isinstance(addr, str) and addr.strip():
                try:
                    from app.agents.verifier import geocode_address
                    coords = await geocode_address(addr)
                    if coords:
                        lat, lon = coords
                except Exception as e:
                    logger.debug("geocode for suggest_resolution failed: %s", e)

        if lat is None or lon is None:
            return {"suggested_outcome": None, "reason": "no_location", "verification": {}}

        try:
            from app.agents.verifier import suggest_outcome_from_ndvi
            outcome, verification = await suggest_outcome_from_ndvi(lat, lon, threshold=threshold)
            return {
                "suggested_outcome": outcome,
                "reason": "oracle",
                "verification": verification,
            }
        except Exception as e:
            logger.warning("suggest_outcome_from_ndvi failed: %s", e)
            return {"suggested_outcome": None, "reason": "verification_failed", "verification": {"error": str(e)}}

    def place_order(
        self,
        market_id: str,
        user_id: int,
        side: str,
        price: float,
        size: float,
    ) -> Dict[str, Any]:
        """
        Place an order in the internal order book.

        Args:
            market_id: Market ID (e.g. MKT_1_20260121120000)
            user_id: User placing the order
            side: "yes" or "no"
            price: Price in [0, 1]
            size: Order size

        Returns:
            Dict with order_id, market_id, side, price, size, status, created_at.
        """
        self._check_enabled()
        if side not in ("yes", "no"):
            raise PolymarketServiceError("side must be 'yes' or 'no'")
        if not (0 <= price <= 1):
            raise PolymarketServiceError("price must be between 0 and 1")
        if size <= 0:
            raise PolymarketServiceError("size must be positive")

        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")
        if evt.resolved_at is not None:
            raise PolymarketServiceError(f"Market {market_id} is resolved; no new orders")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise PolymarketServiceError(f"User {user_id} not found")

        order = MarketOrder(
            market_event_id=evt.id,
            user_id=user_id,
            side=side,
            price=price,
            size=size,
            status="open",
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return {
            "order_id": order.id,
            "market_id": market_id,
            "side": order.side,
            "price": float(order.price),
            "size": float(order.size),
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }

    def cancel_order(self, order_id: int, user_id: int) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            order_id: Order ID
            user_id: Must match order owner

        Returns:
            Dict with order_id, status.
        """
        self._check_enabled()
        order = self.db.query(MarketOrder).filter(MarketOrder.id == order_id).first()
        if not order:
            raise PolymarketServiceError(f"Order {order_id} not found")
        if order.user_id != user_id:
            raise PolymarketServiceError("Order does not belong to user")
        if order.status != "open":
            raise PolymarketServiceError(f"Order {order_id} is not open (status={order.status})")

        order.status = "cancelled"
        self.db.commit()
        self.db.refresh(order)

        return {"order_id": order_id, "status": "cancelled"}

    def get_order_book(self, market_id: str) -> Dict[str, Any]:
        """
        Get aggregated order book for a market.

        Bids: open orders with side=yes, aggregated by price, sorted desc.
        Asks: open orders with side=no, aggregated by price, sorted asc.

        Returns:
            {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        self._check_enabled()
        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")

        # bids: side=yes, (price, sum(size)), order by price desc
        bid_rows = (
            self.db.query(MarketOrder.price, func.sum(MarketOrder.size).label("size"))
            .filter(
                MarketOrder.market_event_id == evt.id,
                MarketOrder.status == "open",
                MarketOrder.side == "yes",
            )
            .group_by(MarketOrder.price)
            .order_by(MarketOrder.price.desc())
            .all()
        )
        bids = [[float(r.price), float(r.size)] for r in bid_rows]

        # asks: side=no, (price, sum(size)), order by price asc
        ask_rows = (
            self.db.query(MarketOrder.price, func.sum(MarketOrder.size).label("size"))
            .filter(
                MarketOrder.market_event_id == evt.id,
                MarketOrder.status == "open",
                MarketOrder.side == "no",
            )
            .group_by(MarketOrder.price)
            .order_by(MarketOrder.price.asc())
            .all()
        )
        asks = [[float(r.price), float(r.size)] for r in ask_rows]

        return {"bids": bids, "asks": asks}

    def get_user_orders(
        self,
        market_id: str,
        user_id: int,
        *,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List a user's orders for a market.

        Args:
            market_id: Market ID
            user_id: User ID
            status: If set, filter by status (open, filled, cancelled)

        Returns:
            List of order dicts.
        """
        self._check_enabled()
        evt = self.db.query(MarketEvent).filter(MarketEvent.market_id == market_id).first()
        if not evt:
            raise PolymarketServiceError(f"Market {market_id} not found")

        q = (
            self.db.query(MarketOrder)
            .filter(MarketOrder.market_event_id == evt.id, MarketOrder.user_id == user_id)
            .order_by(MarketOrder.created_at.desc())
        )
        if status:
            q = q.filter(MarketOrder.status == status)
        orders = q.all()

        return [
            {
                "order_id": o.id,
                "market_id": market_id,
                "side": o.side,
                "price": float(o.price),
                "size": float(o.size),
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "filled_at": o.filled_at.isoformat() if o.filled_at else None,
            }
            for o in orders
        ]
