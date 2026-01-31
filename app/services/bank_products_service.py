"""
Bank products marketplace (Week 14).
- get_bank_products: user's investment holdings from Plaid.
- list_products_for_sale: marketplace listings.
- sell_product: create listing with configurable flat fee.
- get_product_details: one listing by id.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BankProductListing
from app.services.portfolio_aggregation_service import aggregate_investments

logger = logging.getLogger(__name__)


class BankProductsServiceError(Exception):
    """Raised when bank products operations fail."""

    pass


def get_flat_fee() -> Decimal:
    """Configurable flat fee for selling a bank product (default 0)."""
    val = getattr(settings, "BANK_PRODUCTS_FLAT_FEE", None)
    if val is not None:
        try:
            return Decimal(str(val))
        except Exception:
            pass
    return Decimal("0")


def get_bank_products(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Get bank-held investment products for the user (from Plaid Investments).
    Returns list of products with symbol, name, quantity, market_value, etc.
    """
    inv = aggregate_investments(db, user_id)
    products: List[Dict[str, Any]] = []
    for i, pos in enumerate(inv.positions or []):
        products.append({
            "id": f"holding_{i}",
            "symbol": pos.get("symbol"),
            "name": pos.get("symbol") or "Unknown",
            "quantity": pos.get("quantity"),
            "market_value": pos.get("market_value"),
            "current_price": pos.get("current_price"),
            "product_type": "equity",
        })
    return products


def list_products_for_sale(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    status: str = "active",
) -> List[Dict[str, Any]]:
    """List marketplace listings (products for sale)."""
    q = db.query(BankProductListing).filter(BankProductListing.status == status)
    q = q.order_by(BankProductListing.created_at.desc())
    rows = q.offset(offset).limit(limit).all()
    return [r.to_dict() for r in rows]


def sell_product(
    db: Session,
    user_id: int,
    name: str,
    asking_price: Decimal,
    plaid_account_id: Optional[str] = None,
    plaid_security_id: Optional[str] = None,
    product_type: Optional[str] = None,
) -> BankProductListing:
    """
    Create a marketplace listing to sell a bank product. Applies configurable flat_fee.
    """
    if asking_price <= 0:
        raise BankProductsServiceError("Asking price must be positive")
    flat_fee = get_flat_fee()
    listing = BankProductListing(
        user_id=user_id,
        plaid_account_id=plaid_account_id,
        plaid_security_id=plaid_security_id,
        name=name or "Bank product",
        product_type=product_type or "equity",
        asking_price=asking_price,
        flat_fee=flat_fee,
        status="active",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def get_product_details(db: Session, listing_id: int) -> Optional[Dict[str, Any]]:
    """Get one marketplace listing by id."""
    row = db.query(BankProductListing).filter(BankProductListing.id == listing_id).first()
    return row.to_dict() if row else None
