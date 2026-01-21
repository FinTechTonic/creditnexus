"""
Asset amortization and alerts (Trading Phase 3).

- generate_amortization_schedule: fixed income payment schedule
- check_upcoming_payments: maturity and amortization due in next N days
- create_maturity_alert: create AssetAlert for maturity/amortization
- send_maturity_alert: log notification (in production: email/in-app)
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ManualAsset, AssetAlert, User

logger = logging.getLogger(__name__)

FREQ_MONTHS = {"monthly": 1, "quarterly": 3, "annually": 12, "at_maturity": 0}


class AssetAmortizationService:
    """Amortization schedules and maturity/amortization alerts for ManualAsset."""

    def __init__(self, db: Session):
        self.db = db

    def generate_amortization_schedule(
        self,
        principal: Decimal,
        interest_rate: Decimal,
        maturity_date: date,
        payment_frequency: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate amortization schedule for fixed income.
        payment_frequency: monthly, quarterly, annually, at_maturity.
        at_maturity: single row at maturity_date with full interest.
        """
        months = FREQ_MONTHS.get((payment_frequency or "").lower(), 0)
        out: List[Dict[str, Any]] = []
        rate_annual = float(interest_rate or 0) / 100.0

        if months == 0:
            # at_maturity: one payment at maturity
            years = (maturity_date - date.today()).days / 365.25 if maturity_date else 0
            years = max(0, years)
            interest = float(principal) * rate_annual * years
            out.append({
                "date": maturity_date.isoformat() if maturity_date else None,
                "principal_payment": float(principal),
                "interest_payment": round(interest, 4),
                "remaining_balance": 0,
            })
            return out

        # Simplified: equal principal + interest per period
        today = date.today()
        if not maturity_date or maturity_date <= today:
            return out
        periods = max(1, int((maturity_date - today).days / (365.25 / 12 * months)))
        principal_per = float(principal) / periods
        remaining = float(principal)
        d = today
        for i in range(periods):
            d = self._add_months(d, months)
            if d > maturity_date:
                d = maturity_date
            int_p = remaining * (rate_annual / 12 * months)
            princ_p = min(principal_per, remaining)
            remaining = max(0, remaining - princ_p)
            out.append({
                "date": d.isoformat(),
                "principal_payment": round(princ_p, 4),
                "interest_payment": round(int_p, 4),
                "remaining_balance": round(remaining, 4),
            })
            if remaining <= 0:
                break
        return out

    def _add_months(self, d: date, months: int) -> date:
        year, month, day = d.year, d.month, d.day
        month += months
        while month > 12:
            month -= 12
            year += 1
        while month < 1:
            month += 12
            year -= 1
        day = min(day, [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return date(year, month, day)

    def check_upcoming_payments(self, days_ahead: int = 30, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        ManualAssets with maturity_date or amortization_schedule due in [today, today+days_ahead].
        If user_id, only that user's assets. Returns list of {asset, asset_id, due_date, days_until, type, amount, message}.
        """
        today = date.today()
        end = today + timedelta(days=days_ahead)
        out: List[Dict[str, Any]] = []
        user_filter = [ManualAsset.user_id == user_id] if user_id is not None else []

        # Maturity dates
        rows = self.db.query(ManualAsset).filter(
            *user_filter,
            ManualAsset.maturity_date.isnot(None),
            ManualAsset.maturity_date >= today,
            ManualAsset.maturity_date <= end,
        ).all()
        for a in rows:
            if a.maturity_date:
                out.append({
                    "asset": a,
                    "asset_id": a.id,
                    "due_date": a.maturity_date.isoformat(),
                    "days_until": (a.maturity_date - today).days,
                    "type": "maturity",
                    "amount": float(a.purchase_price or 0),
                    "message": f"Maturity: {a.name}",
                })

        # Amortization schedule payments
        rows = self.db.query(ManualAsset).filter(
            *user_filter,
            ManualAsset.amortization_schedule.isnot(None),
        ).all()
        for a in rows:
            sched = a.amortization_schedule or []
            if not isinstance(sched, list):
                continue
            for row in sched:
                dstr = row.get("date") if isinstance(row, dict) else None
                if not dstr:
                    continue
                try:
                    d = date.fromisoformat(dstr) if isinstance(dstr, str) else None
                except Exception:
                    continue
                if not d or d < today or d > end:
                    continue
                principal = float((row.get("principal_payment") or 0) if isinstance(row, dict) else 0)
                interest = float((row.get("interest_payment") or 0) if isinstance(row, dict) else 0)
                out.append({
                    "asset": a,
                    "asset_id": a.id,
                    "due_date": d.isoformat(),
                    "days_until": (d - today).days,
                    "type": "amortization_payment",
                    "amount": principal + interest,
                    "message": f"Amortization payment: {a.name}",
                })
        out.sort(key=lambda x: (x["due_date"], x["asset_id"]))
        return out

    def create_maturity_alert(
        self,
        asset: ManualAsset,
        trigger_date: date,
        alert_type: str,
        message: str,
    ) -> Optional[AssetAlert]:
        """Create AssetAlert if one does not already exist for this asset+trigger_date+alert_type."""
        existing = self.db.query(AssetAlert).filter(
            AssetAlert.asset_id == asset.id,
            AssetAlert.alert_type == alert_type,
            AssetAlert.trigger_date == trigger_date,
            AssetAlert.is_active == True,
        ).first()
        if existing:
            return existing
        al = AssetAlert(
            asset_id=asset.id,
            alert_type=alert_type,
            trigger_date=trigger_date,
            message=message,
            is_active=True,
            notified=False,
        )
        self.db.add(al)
        self.db.commit()
        self.db.refresh(al)
        return al

    def send_maturity_alert(self, asset: ManualAsset, days_until: int, due_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Create in-app AssetAlert and log. In production would also email/push.
        due_date: used for trigger_date when days_until is for a specific date.
        """
        d = due_date or (asset.maturity_date if days_until and asset.maturity_date else None)
        if not d and asset.maturity_date:
            d = asset.maturity_date
        if not d:
            d = date.today() + timedelta(days=days_until)
        msg = f"{asset.name}: maturity in {days_until} days" if days_until > 0 else f"{asset.name}: maturity due"
        al = self.create_maturity_alert(asset, d, "maturity", msg)
        logger.info("Asset maturity alert: asset_id=%s days_until=%s alert_id=%s", asset.id, days_until, al.id if al else None)
        return {"status": "created", "alert_id": al.id if al else None, "days_until": days_until}
