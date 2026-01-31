"""
Adaptive pricing service (Phase 12): feature-based costs and fees.

- calculate_adaptive_cost(feature, quantity): cost in credits or USD equivalent.
- get_server_fee(feature): server-side fee for the feature.
- get_client_call_fee(feature): client-call fee (e.g. per API call).
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_base_costs() -> Dict[str, Decimal]:
    """Base cost per feature (credits or USD-equivalent). From config or default."""
    raw = getattr(settings, "ADAPTIVE_PRICING_BASE_COSTS", None)
    if raw is None:
        pass
    elif isinstance(raw, dict):
        return {k: Decimal(str(v)) for k, v in raw.items()}
    elif isinstance(raw, str) and raw.strip():
        import json
        try:
            d = json.loads(raw)
            return {k: Decimal(str(v)) for k, v in d.items()}
        except Exception:
            pass
    # Defaults per feature
    return {
        "stock_prediction_daily": Decimal("0.10"),
        "stock_prediction_hourly": Decimal("0.05"),
        "stock_prediction_15min": Decimal("0.02"),
        "quantitative_analysis": Decimal("0.25"),
        "risk_analysis": Decimal("0.15"),
        "document_review": Decimal("0.05"),
        "verification": Decimal("0.05"),
        "trading": Decimal("0.01"),
        "plaid_refresh": Decimal("0.05"),
        "default": Decimal("0.01"),
    }


def _get_server_fees() -> Dict[str, Decimal]:
    """Server fee per feature (added to base cost when billing server)."""
    raw = getattr(settings, "SERVER_FEES", None)
    if raw is None:
        pass
    elif isinstance(raw, dict):
        return {k: Decimal(str(v)) for k, v in raw.items()}
    elif isinstance(raw, (int, float)):
        return {"default": Decimal(str(raw))}
    elif isinstance(raw, str) and raw.strip():
        import json
        try:
            if raw.strip().startswith("{"):
                d = json.loads(raw)
                return {k: Decimal(str(v)) for k, v in d.items()}
            return {"default": Decimal(raw.strip())}
        except Exception:
            pass
    return {"default": Decimal("0")}


class AdaptivePricingService:
    """Compute adaptive costs and fees per feature."""

    def __init__(self) -> None:
        self._enabled = getattr(settings, "ADAPTIVE_PRICING_ENABLED", False)
        self._base_costs = _get_base_costs()
        self._server_fees = _get_server_fees()

    def is_enabled(self) -> bool:
        return bool(self._enabled)

    def calculate_adaptive_cost(
        self,
        feature: str,
        quantity: float = 1.0,
        *,
        include_server_fee: bool = True,
    ) -> Decimal:
        """
        Calculate cost for a feature usage (e.g. 1 stock prediction call).

        Args:
            feature: Feature key (e.g. stock_prediction_daily, plaid_refresh).
            quantity: Multiplier (e.g. number of calls).
            include_server_fee: If True, add server fee to base cost.

        Returns:
            Total cost (base * quantity + optional server fee).
        """
        if quantity <= 0:
            return Decimal("0")
        base = self._base_costs.get(feature) or self._base_costs.get("default", Decimal("0"))
        total = base * Decimal(str(quantity))
        if include_server_fee:
            fee = self._server_fees.get(feature) or self._server_fees.get("default", Decimal("0"))
            total += fee
        return total.quantize(Decimal("0.0001"))

    def get_server_fee(self, feature: str) -> Decimal:
        """Return server-side fee for the feature."""
        return self._server_fees.get(feature) or self._server_fees.get("default", Decimal("0"))

    def get_client_call_fee(self, feature: str) -> Decimal:
        """Return client-call fee (per API call) for the feature. May equal base cost or a separate fee."""
        base = self._base_costs.get(feature) or self._base_costs.get("default", Decimal("0"))
        return base.quantize(Decimal("0.0001"))
