"""
Adaptive pricing API (Phase 12): GET calculate, server-fee, client-fee.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Query

from app.services.adaptive_pricing_service import AdaptivePricingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.get("/calculate", response_model=Dict[str, Any])
def calculate_adaptive_cost(
    feature: str = Query(..., min_length=1),
    quantity: float = Query(1.0, ge=0),
    include_server_fee: bool = Query(True),
):
    """Calculate adaptive cost for a feature (credits or USD-equivalent)."""
    svc = AdaptivePricingService()
    cost = svc.calculate_adaptive_cost(feature, quantity=quantity, include_server_fee=include_server_fee)
    return {"feature": feature, "quantity": quantity, "cost": float(cost), "enabled": svc.is_enabled()}


@router.get("/server-fee", response_model=Dict[str, Any])
def get_server_fee(feature: str = Query(..., min_length=1)):
    """Get server-side fee for a feature."""
    svc = AdaptivePricingService()
    fee = svc.get_server_fee(feature)
    return {"feature": feature, "server_fee": float(fee), "enabled": svc.is_enabled()}


@router.get("/client-fee", response_model=Dict[str, Any])
def get_client_call_fee(feature: str = Query(..., min_length=1)):
    """Get client-call fee (per API call) for a feature."""
    svc = AdaptivePricingService()
    fee = svc.get_client_call_fee(feature)
    return {"feature": feature, "client_fee": float(fee), "enabled": svc.is_enabled()}
