"""Polymarket surveillance API: alerts, run-cycle, subscription gating.

All surveillance endpoints require Pro (or higher) when SURVEILLANCE_REQUIRES_PRO is True.
Use require_surveillance_access() at the start of each route.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.core.config import settings
from app.db import get_db
from app.db.models import User
from app.services.polymarket_surveillance_service import PolymarketSurveillanceService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/surveillance", tags=["polymarket-surveillance"])


class ReviewAlertRequest(BaseModel):
    """Request body for POST /alerts/{id}/review."""

    resolution: str = Field(..., description="dismissed, escalated, or false_positive")


def require_surveillance_access(request: Request, user: User, db: Session) -> None:
    """
    Ensure the user has access to market intelligence / surveillance.
    If SURVEILLANCE_REQUIRES_PRO is False, returns without raising.
    Otherwise checks RevenueCat (via PaymentRouterService) or SubscriptionService tier.
    Raises HTTPException 403 with X-Upgrade-Url when access is denied.
    """
    if not getattr(settings, "SURVEILLANCE_REQUIRES_PRO", True):
        return

    # RevenueCat path
    pr = getattr(request.app.state, "payment_router_service", None)
    ent = getattr(settings, "REVENUECAT_ENTITLEMENT_MARKET_INTELLIGENCE", None) or getattr(
        settings, "REVENUECAT_ENTITLEMENT_PRO", "pro"
    )
    if pr and pr.has_subscription_access(app_user_id=str(user.id), entitlement_id=ent):
        return

    # Fallback: SubscriptionService tier
    tier = SubscriptionService(db).get_user_tier(user.id)
    if tier and str(tier).lower() in ("pro", "premium", "lifetime"):
        return

    raise HTTPException(
        status_code=403,
        detail="Market intelligence requires Pro (or higher) subscription",
        headers={"X-Upgrade-Url": "/api/subscriptions/upgrade"},
    )


@router.get("/alerts", response_model=List[dict])
async def list_surveillance_alerts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    """
    List Polymarket surveillance alerts. Requires Pro (or higher) when
    SURVEILLANCE_REQUIRES_PRO is True. Returns 403 with upgrade CTA otherwise.
    """
    require_surveillance_access(request, current_user, db)
    return PolymarketSurveillanceService(db).list_alerts(
        severity=severity, reviewed=reviewed, limit=limit, offset=offset
    )


@router.post("/alerts/{alert_id}/review", response_model=dict)
async def review_surveillance_alert(
    alert_id: int,
    body: ReviewAlertRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Review an alert: set resolution to dismissed, escalated, or false_positive."""
    require_surveillance_access(request, current_user, db)
    if body.resolution not in ("dismissed", "escalated", "false_positive"):
        raise HTTPException(status_code=400, detail="resolution must be dismissed, escalated, or false_positive")
    try:
        a = PolymarketSurveillanceService(db).review_alert(alert_id, body.resolution, current_user.id)
        return {
            "id": a.id,
            "resolution": a.resolution,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run-cycle", response_model=dict)
async def run_surveillance_cycle(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run a surveillance detection cycle (Data API → baselines, alerts). Admin/scheduled."""
    require_surveillance_access(request, current_user, db)
    return PolymarketSurveillanceService(db).run_detection_cycle(markets=None)
