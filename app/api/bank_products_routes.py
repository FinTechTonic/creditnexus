"""Bank products marketplace API (Week 14)."""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.db import get_db
from app.db.models import User
from app.services.bank_products_service import (
    BankProductsServiceError,
    get_bank_products,
    get_product_details,
    list_products_for_sale,
    sell_product,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bank-products", tags=["bank-products"])


class SellProductRequest(BaseModel):
    """Request to list a bank product for sale."""

    name: str = Field(..., min_length=1, max_length=255)
    asking_price: Decimal = Field(..., gt=0)
    plaid_account_id: Optional[str] = None
    plaid_security_id: Optional[str] = None
    product_type: Optional[str] = None


@router.get("", response_model=Dict[str, Any])
def get_my_bank_products(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get current user's bank-held investment products (from Plaid)."""
    products = get_bank_products(db, current_user.id)
    return {"products": products}


@router.get("/marketplace", response_model=Dict[str, Any])
def get_marketplace(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str = Query("active"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List products available for sale on the marketplace."""
    listings = list_products_for_sale(db, limit=limit, offset=offset, status=status)
    return {"listings": listings}


@router.post("/sell", response_model=Dict[str, Any])
def sell_product_listing(
    body: SellProductRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a marketplace listing to sell a bank product (configurable flat fee applies)."""
    try:
        listing = sell_product(
            db=db,
            user_id=current_user.id,
            name=body.name,
            asking_price=body.asking_price,
            plaid_account_id=body.plaid_account_id or None,
            plaid_security_id=body.plaid_security_id or None,
            product_type=body.product_type or None,
        )
        return listing.to_dict()
    except BankProductsServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{listing_id}", response_model=Dict[str, Any])
def get_listing(
    listing_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get one marketplace listing by id."""
    details = get_product_details(db, listing_id)
    if not details:
        raise HTTPException(status_code=404, detail="Listing not found")
    return details
