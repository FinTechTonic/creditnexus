"""API routes for generic structured investment products (SIPs)."""

import logging
from typing import List, Dict, Any, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User
from app.auth.jwt_auth import require_auth
from app.services.structured_products_service import StructuredProductsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/structured-products", tags=["structured-products"])

# Request Models
class CreateTemplateRequest(BaseModel):
    name: str
    product_type: str
    underlying_symbol: str
    payoff_formula: Dict[str, Any]
    maturity_days: int
    principal: Decimal
    fees: Decimal = Decimal("0")

class IssueProductRequest(BaseModel):
    template_id: int
    total_notional: Decimal
    issue_date: Optional[date] = None

class SubscribeRequest(BaseModel):
    instance_id: int
    amount: Decimal

# Routes
@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_templates(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List available structured product templates."""
    service = StructuredProductsService(db)
    templates = service.get_templates(active_only=active_only)
    return [t.to_dict() for t in templates]

@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new structured product template."""
    # Only admins or specific roles should create templates
    if current_user.role not in ["admin", "banker"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    service = StructuredProductsService(db)
    template = service.create_template(
        name=payload.name,
        product_type=payload.product_type,
        underlying_symbol=payload.underlying_symbol,
        payoff_formula=payload.payoff_formula,
        maturity_days=payload.maturity_days,
        principal=payload.principal,
        fees=payload.fees,
        created_by=current_user.id
    )
    return template.to_dict()

@router.get("/instances", response_model=List[Dict[str, Any]])
async def list_instances(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List issued structured product instances."""
    service = StructuredProductsService(db)
    instances = service.get_instances(status=status)
    return [i.to_dict() for i in instances]

@router.post("/instances", status_code=status.HTTP_201_CREATED)
async def issue_product(
    payload: IssueProductRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Issue a new structured product instance."""
    if current_user.role not in ["admin", "banker"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    service = StructuredProductsService(db)
    try:
        instance = service.issue_product(
            template_id=payload.template_id,
            issuer_user_id=current_user.id,
            total_notional=payload.total_notional,
            issue_date=payload.issue_date
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscriptions", response_model=List[Dict[str, Any]])
async def list_user_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get current user's subscriptions."""
    service = StructuredProductsService(db)
    subscriptions = service.get_user_subscriptions(current_user.id)
    return [s.to_dict() for s in subscriptions]

@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_to_product(
    payload: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Subscribe to a structured product instance."""
    service = StructuredProductsService(db)
    try:
        subscription = service.subscribe_to_product(
            instance_id=payload.instance_id,
            investor_user_id=current_user.id,
            amount=payload.amount
        )
        return subscription.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/instances/{instance_id}/fair-value")
async def get_instance_fair_value(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Calculate and return the current fair value of an instance."""
    service = StructuredProductsService(db)
    try:
        fair_value = service.calculate_fair_value(instance_id)
        # Optionally update the instance with this value
        service.update_instance_value(instance_id, fair_value)
        return {"instance_id": instance_id, "fair_value": float(fair_value)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating fair value: {e}")
        raise HTTPException(status_code=500, detail="Calculation failed")
