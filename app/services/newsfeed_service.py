"""Newsfeed service: posts for deals/markets, like, comment, share, and funding (Week 13)."""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.db.models import (
    Deal,
    MarketEvent,
    NewsfeedComment,
    NewsfeedLike,
    NewsfeedPost,
    NewsfeedShare,
    OrganizationSocialFeedWhitelist,
    User,
)

logger = logging.getLogger(__name__)


class NewsfeedServiceError(Exception):
    """Raised when newsfeed operations fail."""

    pass


def _post_to_dict(post: NewsfeedPost) -> Dict[str, Any]:
    """Serialize NewsfeedPost to dict (no relationships)."""
    return {
        "id": post.id,
        "post_type": post.post_type,
        "title": post.title,
        "content": post.content,
        "deal_id": post.deal_id,
        "market_id": post.market_id,
        "organization_id": post.organization_id,
        "author_id": post.author_id,
        "polymarket_market_id": post.polymarket_market_id,
        "polymarket_market_url": post.polymarket_market_url,
        "likes_count": post.likes_count,
        "comments_count": post.comments_count,
        "shares_count": post.shares_count,
        "views_count": post.views_count,
        "visibility": post.visibility,
        "is_pinned": post.is_pinned,
        "metadata": post.post_metadata,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


class NewsfeedService:
    """Service for newsfeed posts and social interactions."""

    def __init__(self, db: Session):
        self.db = db

    def create_market_post(
        self,
        market_id: int,
        author_id: int,
        organization_id: Optional[int] = None,
    ) -> NewsfeedPost:
        """Create a newsfeed post when a market is created.

        Args:
            market_id: MarketEvent.id (internal)
            author_id: User ID of market creator
            organization_id: Optional organization scope

        Returns:
            Created NewsfeedPost
        """
        market = self.db.query(MarketEvent).filter(MarketEvent.id == market_id).first()
        if not market:
            raise NewsfeedServiceError(f"Market {market_id} not found")
        polymarket_url = f"https://polymarket.com/event/{market.market_id}"
        post = NewsfeedPost(
            post_type="market_created",
            title=f"New Market: {market.question}",
            content=f"Market created for deal {market.deal_id}" if market.deal_id else market.question,
            deal_id=market.deal_id,
            market_id=market.id,
            organization_id=organization_id,
            author_id=author_id,
            polymarket_market_id=market.market_id,
            polymarket_market_url=polymarket_url,
            visibility=getattr(market, "visibility", "public") or "public",
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_newsfeed(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get newsfeed posts for a user with engagement flags.

        Args:
            user_id: Viewer user ID
            organization_id: Optional org filter
            limit: Page size
            offset: Pagination offset
            filters: Optional post_type, deal_type

        Returns:
            List of post dicts with user_liked, author, deal, market
        """
        query = self.db.query(NewsfeedPost)
        if organization_id is not None:
            rows = (
                self.db.query(OrganizationSocialFeedWhitelist.whitelisted_organization_id)
                .filter(OrganizationSocialFeedWhitelist.organization_id == organization_id)
                .distinct()
                .all()
            )
            whitelisted_ids = [r[0] for r in rows]
            allowed_org_ids = [organization_id] + whitelisted_ids
            query = query.filter(
                or_(
                    NewsfeedPost.visibility == "public",
                    and_(
                        NewsfeedPost.visibility == "organization",
                        NewsfeedPost.organization_id.in_(allowed_org_ids),
                    ),
                )
            )
        else:
            query = query.filter(NewsfeedPost.visibility == "public")
        if filters:
            if filters.get("post_type"):
                query = query.filter(NewsfeedPost.post_type == filters["post_type"])
            if filters.get("deal_type"):
                query = query.join(Deal).filter(Deal.deal_type == filters["deal_type"])
        query = query.order_by(NewsfeedPost.is_pinned.desc(), NewsfeedPost.created_at.desc())
        posts = query.offset(offset).limit(limit).all()
        result = []
        for post in posts:
            user_liked = (
                self.db.query(NewsfeedLike)
                .filter(NewsfeedLike.post_id == post.id, NewsfeedLike.user_id == user_id)
                .first()
                is not None
            )
            author = post.author
            deal = post.deal
            market = post.market
            result.append({
                **_post_to_dict(post),
                "user_liked": user_liked,
                "author": author.to_dict() if author and hasattr(author, "to_dict") else ({"id": post.author_id} if post.author_id else None),
                "deal": deal.to_dict() if deal and hasattr(deal, "to_dict") else ({"id": post.deal_id} if post.deal_id else None),
                "market": {
                    "id": market.id,
                    "market_id": market.market_id,
                    "question": market.question,
                } if market else None,
            })
        return result

    def like_post(self, post_id: int, user_id: int) -> Dict[str, Any]:
        """Toggle like on a post. Returns updated like state and counts."""
        post = self.db.query(NewsfeedPost).filter(NewsfeedPost.id == post_id).first()
        if not post:
            raise NewsfeedServiceError(f"Post {post_id} not found")
        existing = (
            self.db.query(NewsfeedLike)
            .filter(NewsfeedLike.post_id == post_id, NewsfeedLike.user_id == user_id)
            .first()
        )
        if existing:
            self.db.delete(existing)
            post.likes_count = max(0, (post.likes_count or 0) - 1)
            liked = False
        else:
            self.db.add(NewsfeedLike(post_id=post_id, user_id=user_id))
            post.likes_count = (post.likes_count or 0) + 1
            liked = True
        self.db.commit()
        self.db.refresh(post)
        return {"liked": liked, "likes_count": post.likes_count}

    def comment_on_post(
        self,
        post_id: int,
        user_id: int,
        content: str,
        parent_comment_id: Optional[int] = None,
    ) -> NewsfeedComment:
        """Add a comment (or reply) to a post."""
        post = self.db.query(NewsfeedPost).filter(NewsfeedPost.id == post_id).first()
        if not post:
            raise NewsfeedServiceError(f"Post {post_id} not found")
        comment = NewsfeedComment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            parent_comment_id=parent_comment_id,
        )
        self.db.add(comment)
        post.comments_count = (post.comments_count or 0) + 1
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def share_post(
        self,
        post_id: int,
        user_id: int,
        share_type: str = "internal",
        shared_to: Optional[str] = None,
    ) -> NewsfeedShare:
        """Record a share of a post."""
        post = self.db.query(NewsfeedPost).filter(NewsfeedPost.id == post_id).first()
        if not post:
            raise NewsfeedServiceError(f"Post {post_id} not found")
        share = NewsfeedShare(
            post_id=post_id,
            user_id=user_id,
            share_type=share_type,
            shared_to=shared_to,
        )
        self.db.add(share)
        post.shares_count = (post.shares_count or 0) + 1
        self.db.commit()
        self.db.refresh(share)
        return share

    # -------------------------------------------------------------------------
    # Week 13: Funding for securitized products
    # -------------------------------------------------------------------------

    def get_funding_options(self, asset_type: str) -> List[Dict[str, Any]]:
        """
        Return funding options available for the given asset type.
        Asset types: equity, equities, loan, loans, polymarket, market, securitized, or default.
        """
        asset_type_lower = (asset_type or "").strip().lower()
        options: List[Dict[str, Any]] = []
        if asset_type_lower in ("equity", "equities", "securitized", ""):
            options.append({
                "id": "alpaca_funding",
                "payment_type": "alpaca_funding",
                "label": "Fund via brokerage",
                "description": "Add funds to your Alpaca brokerage account from a linked bank.",
            })
        if asset_type_lower in ("loan", "loans", "securitized", ""):
            options.append({
                "id": "credit_top_up",
                "payment_type": "credit_top_up",
                "label": "Add credits",
                "description": "Top up your CreditNexus credits for platform use.",
            })
        if asset_type_lower in ("polymarket", "market", ""):
            options.append({
                "id": "polymarket_funding",
                "payment_type": "polymarket_funding",
                "label": "Fund via Polymarket",
                "description": "Fund your Polymarket trading balance.",
            })
        if not options:
            options = [
                {"id": "alpaca_funding", "payment_type": "alpaca_funding", "label": "Fund via brokerage", "description": "Add funds to brokerage."},
                {"id": "credit_top_up", "payment_type": "credit_top_up", "label": "Add credits", "description": "Top up credits."},
                {"id": "polymarket_funding", "payment_type": "polymarket_funding", "label": "Fund via Polymarket", "description": "Fund Polymarket balance."},
            ]
        return options

    async def fund_securitized_product(
        self,
        post_id: int,
        user_id: int,
        amount: Decimal,
        payment_type: str,
        payment_router: Any,
        destination_identifier: Optional[str] = None,
        payment_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initiate funding for a securitized product linked to a newsfeed post.
        Delegates to unified_funding_service.request_funding.
        Returns result dict (may contain 402 payment_request) or error.
        """
        from app.services.unified_funding_service import request_funding

        post = self.db.query(NewsfeedPost).filter(NewsfeedPost.id == post_id).first()
        if not post:
            raise NewsfeedServiceError(f"Post {post_id} not found")
        if amount <= 0:
            raise NewsfeedServiceError("Amount must be positive")
        payment_type = (payment_type or "").strip().lower().replace("-", "_")
        if payment_type not in ("alpaca_funding", "polymarket_funding", "credit_top_up"):
            raise NewsfeedServiceError(f"Unsupported payment_type: {payment_type}")
        dest = destination_identifier or f"post_{post_id}"
        if post.market_id:
            dest = f"{dest}_market_{post.market_id}"
        result = await request_funding(
            db=self.db,
            user_id=user_id,
            amount=amount,
            payment_type=payment_type,
            destination_identifier=dest,
            payment_router=payment_router,
            payment_payload=payment_payload,
        )
        return result

    async def process_funding(
        self,
        post_id: int,
        user_id: int,
        amount: Decimal,
        payment_type: str,
        payment_router: Any,
        destination_identifier: Optional[str] = None,
        payment_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Alias for fund_securitized_product."""
        return await self.fund_securitized_product(
            post_id=post_id,
            user_id=user_id,
            amount=amount,
            payment_type=payment_type,
            payment_router=payment_router,
            destination_identifier=destination_identifier,
            payment_payload=payment_payload,
        )
