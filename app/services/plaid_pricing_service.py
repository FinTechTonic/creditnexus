"""
Plaid pricing resolution service.

Note: Plaid does not publish a universal per-endpoint price list in docs; we keep
pricing configurable at instance and organization scopes.

Resolution order:
1) Active org-level override (organization_id)
2) Active instance-level default (instance_id match if provided; otherwise instance_id is NULL)
3) Fallback: zeros
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import PlaidPricingConfig

logger = logging.getLogger(__name__)


class PlaidPricingService:
    def __init__(self, db: Session):
        self.db = db

    def get_pricing_for_endpoint(
        self,
        *,
        api_endpoint: str,
        organization_id: Optional[int] = None,
        instance_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Returns pricing dict:
        - cost_per_call_usd: Decimal
        - cost_per_call_credits: Decimal
        - source: "org" | "instance" | "default"
        """
        # 1) Org override
        if organization_id:
            cfg = (
                self.db.query(PlaidPricingConfig)
                .filter(
                    PlaidPricingConfig.organization_id == organization_id,
                    PlaidPricingConfig.api_endpoint == api_endpoint,
                    PlaidPricingConfig.is_active == True,
                )
                .order_by(PlaidPricingConfig.id.desc())
                .first()
            )
            if cfg:
                return {
                    "cost_per_call_usd": Decimal(str(cfg.cost_per_call_usd or 0)),
                    "cost_per_call_credits": Decimal(str(cfg.cost_per_call_credits or 0)),
                    "source": "org",
                    "config_id": cfg.id,
                }

        # 2) Instance default
        q = (
            self.db.query(PlaidPricingConfig)
            .filter(
                PlaidPricingConfig.organization_id.is_(None),
                PlaidPricingConfig.api_endpoint == api_endpoint,
                PlaidPricingConfig.is_active == True,
            )
        )
        if instance_id is not None:
            q = q.filter(PlaidPricingConfig.instance_id == instance_id)
        else:
            q = q.filter(PlaidPricingConfig.instance_id.is_(None))

        cfg = q.order_by(PlaidPricingConfig.id.desc()).first()
        if cfg:
            return {
                "cost_per_call_usd": Decimal(str(cfg.cost_per_call_usd or 0)),
                "cost_per_call_credits": Decimal(str(cfg.cost_per_call_credits or 0)),
                "source": "instance",
                "config_id": cfg.id,
            }

        return {
            "cost_per_call_usd": Decimal("0"),
            "cost_per_call_credits": Decimal("0"),
            "source": "default",
            "config_id": None,
        }

    def calculate_cost(
        self,
        *,
        api_endpoint: str,
        organization_id: Optional[int] = None,
        instance_id: Optional[int] = None,
        multiplier: Decimal = Decimal("1"),
    ) -> Dict[str, Any]:
        """
        Calculate cost for a call (or batch) using a multiplier.
        """
        pricing = self.get_pricing_for_endpoint(
            api_endpoint=api_endpoint,
            organization_id=organization_id,
            instance_id=instance_id,
        )
        usd = (pricing["cost_per_call_usd"] * multiplier).quantize(Decimal("0.0001"))
        credits = (pricing["cost_per_call_credits"] * multiplier).quantize(Decimal("0.0001"))
        return {
            **pricing,
            "multiplier": str(multiplier),
            "cost_usd": usd,
            "cost_credits": credits,
        }

