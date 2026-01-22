"""
Structured Product Pricing Engine (Trading Phase 6).

Provides fair-value, yield, spread, duration, and convexity for
securitization tranches and pool-level aggregate pricing.
"""

import logging
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import SecuritizationPool, SecuritizationTranche

logger = logging.getLogger(__name__)

# Default assumed maturity (years) when not in CDM
_DEFAULT_MATURITY_YEARS = 5
# Payments per year for duration/convexity
_FREQ = 2  # semi-annual


class StructuredProductPricingService:
    """Pricing engine for securitization tranches and pools."""

    def __init__(self, db: Session):
        self.db = db

    def _get_maturity_years(self, tranche: SecuritizationTranche) -> int:
        """Infer maturity in years from cdm_data or use default."""
        data = tranche.cdm_data if isinstance(tranche.cdm_data, dict) else {}
        d = data.get("maturity_date")
        if d:
            try:
                if isinstance(d, str):
                    mat = datetime.fromisoformat(d.replace("Z", "+00:00")).date()
                else:
                    mat = d
                today = date.today()
                if hasattr(mat, "year"):
                    delta = (mat - today).days / 365.25
                    return max(1, int(round(delta)))
            except Exception:
                pass
        years = data.get("maturity_years") or getattr(tranche, "maturity_years", None)
        if years is not None:
            return max(1, int(years))
        return _DEFAULT_MATURITY_YEARS

    def price_tranche(
        self,
        tranche: SecuritizationTranche,
        pool: SecuritizationPool,
        benchmark_rate: Optional[Decimal] = None,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Price a single tranche: fair value, YTM, spread, duration, convexity.

        Treats the tranche as a fixed-coupon bond. When maturity is unknown,
        uses a default term. benchmark_rate as decimal (e.g. 0.05 for 5%).
        """
        if benchmark_rate is None:
            benchmark_rate = Decimal("0.05")
        as_of_date = as_of_date or date.today()

        principal = Decimal(str(tranche.size or tranche.principal_remaining or 0))
        if principal <= 0:
            return {
                "tranche_id": tranche.tranche_id,
                "tranche_name": tranche.tranche_name,
                "fair_value": 0,
                "yield_to_maturity": None,
                "spread_bps": None,
                "duration": None,
                "convexity": None,
                "currency": getattr(tranche, "currency", None) or (pool.currency if pool else "USD"),
                "as_of_date": as_of_date.isoformat(),
            }

        # Coupon in percent (e.g. 5.5); annual cash flow
        rate = Decimal(str(tranche.interest_rate or 0)) / Decimal("100")
        coup_annual = principal * rate

        maturity_y = self._get_maturity_years(tranche)
        n = maturity_y * _FREQ  # number of periods (semi-annual)
        r = benchmark_rate / _FREQ  # per-period discount
        coup_per = coup_annual / _FREQ

        # PV of coupons + principal
        pv = Decimal("0")
        for t in range(1, n + 1):
            pv += coup_per / ((1 + r) ** t)
        pv += principal / ((1 + r) ** n)
        fair_value = float(round(pv, 2))

        # YTM: use coupon rate as proxy when we assume par; else approximate
        ytm_decimal = rate  # proxy: yield ≈ coupon when at par
        ytm_percent = float(rate * 100)
        spread_bps = float((ytm_decimal - benchmark_rate) * 10000)

        # Macaulay duration (semi-annual): simplified
        y = benchmark_rate / _FREQ
        try:
            mac = sum(
                (t / _FREQ) * (coup_per / ((1 + y) ** t)) for t in range(1, n + 1)
            ) + (n / _FREQ) * (principal / ((1 + y) ** n))
            mac = mac / pv if pv else Decimal("0")
            duration = float(round(mac, 2))
        except Exception:
            duration = float(maturity_y)  # fallback

        # Convexity: stub
        convexity = 0.0

        return {
            "tranche_id": tranche.tranche_id,
            "tranche_name": tranche.tranche_name,
            "fair_value": fair_value,
            "yield_to_maturity": round(ytm_percent, 2),
            "spread_bps": round(spread_bps, 0),
            "duration": duration,
            "convexity": convexity,
            "currency": getattr(tranche, "currency", None) or (pool.currency if pool else "USD"),
            "as_of_date": as_of_date.isoformat(),
            "principal": float(principal),
            "coupon_rate_percent": float(tranche.interest_rate or 0),
        }

    def price_pool(
        self,
        pool_id: int,
        benchmark_rate: Optional[Decimal] = None,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Price all tranches in a pool and return pool-level aggregates.
        pool_id: database id of SecuritizationPool.
        """
        pool = self.db.query(SecuritizationPool).filter(SecuritizationPool.id == pool_id).first()
        if not pool:
            raise ValueError(f"Pool id {pool_id} not found")

        tranches = (
            self.db.query(SecuritizationTranche)
            .filter(SecuritizationTranche.pool_id == pool_id)
            .order_by(SecuritizationTranche.payment_priority.asc())
            .all()
        )

        as_of_date = as_of_date or date.today()
        benchmark_rate = benchmark_rate or Decimal("0.05")

        results: List[Dict[str, Any]] = []
        total_fv = Decimal("0")
        wavg_yield_num = Decimal("0")
        wavg_yield_den = Decimal("0")

        for t in tranches:
            p = self.price_tranche(t, pool, benchmark_rate=benchmark_rate, as_of_date=as_of_date)
            results.append(p)
            fv = Decimal(str(p.get("fair_value") or 0))
            total_fv += fv
            y = p.get("yield_to_maturity")
            if y is not None and fv > 0:
                wavg_yield_num += Decimal(str(y)) * fv
                wavg_yield_den += fv

        wavg_yield = float(wavg_yield_num / wavg_yield_den) if wavg_yield_den else None

        return {
            "pool_id": pool.pool_id,
            "pool_name": pool.pool_name,
            "currency": pool.currency,
            "as_of_date": as_of_date.isoformat(),
            "benchmark_rate_percent": float(benchmark_rate * 100),
            "tranches": results,
            "total_fair_value": float(round(total_fv, 2)),
            "weighted_average_yield_percent": wavg_yield,
        }
