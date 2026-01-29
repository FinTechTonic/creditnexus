"""
Alpaca Broker account opening orchestration.

- open_alpaca_account(user_id, db): KYC gate, build payload from User + KYCVerification,
  call Broker API create_account, persist AlpacaCustomerAccount.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import User, KYCVerification, AlpacaCustomerAccount
from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError
from app.services.kyc_service import KYCService
from app.utils.audit import log_audit_action
from app.db.models import AuditAction

logger = logging.getLogger(__name__)


class AlpacaAccountServiceError(Exception):
    """Raised when account opening or status update fails."""
    pass


def _build_account_payload(user: User, verification: Optional[KYCVerification]) -> Dict[str, Any]:
    """Build Alpaca Broker API account creation payload from User and KYCVerification."""
    email = getattr(user, "email", None) or ""
    if hasattr(email, "get_secret_value"):
        email = email.get_secret_value() or ""
    email = str(email)

    display_name = getattr(user, "display_name", None) or email.split("@")[0] or "User"
    if hasattr(display_name, "get_secret_value"):
        display_name = display_name.get_secret_value() or email.split("@")[0]
    display_name = str(display_name).strip()
    parts = display_name.split(None, 1)
    given_name = parts[0] if parts else "Given"
    family_name = parts[1] if len(parts) > 1 else "User"

    profile_data = getattr(user, "profile_data", None) or {}
    if isinstance(profile_data, dict):
        phone = profile_data.get("phone") or profile_data.get("phone_number") or ""
        street = profile_data.get("street_address") or profile_data.get("address") or ""
        city = profile_data.get("city") or ""
        state = profile_data.get("state") or ""
        postal_code = profile_data.get("postal_code") or profile_data.get("zip") or ""
        country = profile_data.get("country") or "USA"
    else:
        phone = street = city = state = postal_code = ""
        country = "USA"

    # Alpaca account opening payload (contact, identity, address)
    # https://docs.alpaca.markets/reference/createaccount
    contact = {
        "email_address": email,
        "phone_number": str(phone)[:20] if phone else "",
    }
    identity = {
        "given_name": given_name[:50],
        "family_name": family_name[:50],
        "date_of_birth": "1990-01-01",  # Placeholder if not in profile; Alpaca may require or return ACTION_REQUIRED
    }
    if isinstance(verification, KYCVerification) and getattr(verification, "verification_metadata", None):
        meta = verification.verification_metadata or {}
        if isinstance(meta, dict) and meta.get("date_of_birth"):
            identity["date_of_birth"] = str(meta["date_of_birth"])[:10]

    address = {
        "street_address": [str(street)[:64]] if street else ["N/A"],
        "city": city[:32] if city else "N/A",
        "state": state[:32] if state else "NY",
        "postal_code": str(postal_code)[:10] if postal_code else "10001",
        "country": country[:2] if len(country) == 2 else "US",
    }

    return {
        "contact": contact,
        "identity": identity,
        "disclosures": {
            "is_control_person": False,
            "is_affiliated_exchange_or_finra": False,
            "is_politically_exposed": False,
            "immediate_family_exposed": False,
        },
        "agreements": [
            {"agreement": "customer_agreement", "signed_at": None, "ip_address": None},
            {"agreement": "margin_agreement", "signed_at": None, "ip_address": None},
        ],
        "documents": [],
        "trusted_contact": {
            "given_name": given_name[:50],
            "family_name": family_name[:50],
            "email_address": email,
        },
        "address": address,
    }


def open_alpaca_account(user_id: int, db: Session) -> AlpacaCustomerAccount:
    """
    Open an Alpaca Broker account for the user.
    - Ensures KYC is sufficient (evaluate_kyc_for_brokerage).
    - Builds account payload from User + KYCVerification.
    - Calls Broker API create_account.
    - Persists AlpacaCustomerAccount (SUBMITTED).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AlpacaAccountServiceError(f"User {user_id} not found")

    existing = db.query(AlpacaCustomerAccount).filter(AlpacaCustomerAccount.user_id == user_id).first()
    if existing:
        if existing.status == "ACTIVE":
            return existing
        if existing.status in ("SUBMITTED", "APPROVAL_PENDING", "APPROVED"):
            raise AlpacaAccountServiceError(
                f"Account application already in progress (status: {existing.status})"
            )
        if existing.status == "ACTION_REQUIRED":
            raise AlpacaAccountServiceError(
                "Account application requires action; upload documents via brokerage/account/documents"
            )
        if existing.status == "REJECTED":
            raise AlpacaAccountServiceError("Account was rejected; contact support to reapply")

    kyc = KYCService(db)
    if not kyc.evaluate_kyc_for_brokerage(user_id):
        raise AlpacaAccountServiceError(
            "KYC not sufficient for brokerage. Complete identity verification and required documents first."
        )

    client = get_broker_client()
    if not client:
        raise AlpacaAccountServiceError("Broker API not configured (ALPACA_BROKER_API_KEY/SECRET)")

    verification = getattr(user, "kyc_verification", None)
    payload = _build_account_payload(user, verification)

    try:
        result = client.create_account(payload)
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca create_account failed for user %s: %s", user_id, e)
        raise AlpacaAccountServiceError(f"Broker API error: {e}") from e

    account_id = result.get("id")
    if not account_id:
        raise AlpacaAccountServiceError("Broker API did not return account id")

    status = (result.get("status") or "SUBMITTED").upper()
    account_number = result.get("account_number")
    currency = result.get("currency") or "USD"

    rec = AlpacaCustomerAccount(
        user_id=user_id,
        alpaca_account_id=str(account_id),
        account_number=account_number,
        status=status,
        currency=currency,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    log_audit_action(
        db=db,
        action=AuditAction.CREATE,
        target_type="alpaca_customer_account",
        target_id=rec.id,
        user_id=user_id,
        metadata={
            "alpaca_account_id": rec.alpaca_account_id,
            "status": rec.status,
        },
    )
    logger.info("Alpaca account application submitted for user %s: %s", user_id, rec.alpaca_account_id)
    return rec


# Statuses that are "final" — no need to poll for updates
_FINAL_STATUSES = frozenset({"ACTIVE", "REJECTED"})


def sync_alpaca_account_status(rec: AlpacaCustomerAccount, db: Session) -> bool:
    """
    Poll Alpaca Broker API for account status and update local record.
    Returns True if status or account_number/action_required_reason changed.
    """
    client = get_broker_client()
    if not client:
        return False
    try:
        data = client.get_account(rec.alpaca_account_id)
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca get_account failed for %s: %s", rec.alpaca_account_id, e)
        return False

    status = (data.get("status") or rec.status).upper()
    account_number = data.get("account_number") or rec.account_number
    # Alpaca may return action_required_reason or similar when status is ACTION_REQUIRED
    action_reason = (
        data.get("action_required_reason")
        or data.get("reason")
        or rec.action_required_reason
    )
    changed = (
        rec.status != status
        or rec.account_number != account_number
        or rec.action_required_reason != action_reason
    )
    if changed:
        previous_status = rec.status
        rec.status = status
        rec.account_number = account_number
        rec.action_required_reason = action_reason
        db.commit()
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="alpaca_customer_account",
            target_id=rec.id,
            user_id=rec.user_id,
            metadata={
                "alpaca_account_id": rec.alpaca_account_id,
                "status": status,
                "previous_status": previous_status,
            },
        )
    return changed


def sync_all_pending_alpaca_accounts(db: Session) -> Dict[str, Any]:
    """
    Sync status from Alpaca for all customer accounts not yet ACTIVE or REJECTED.
    Used by background worker (poll Event API / account GET).
    """
    pending = (
        db.query(AlpacaCustomerAccount)
        .filter(AlpacaCustomerAccount.status.notin_(list(_FINAL_STATUSES)))
        .limit(200)
        .all()
    )
    synced = 0
    errors = 0
    for rec in pending:
        try:
            if sync_alpaca_account_status(rec, db):
                synced += 1
        except Exception as e:
            logger.warning("Sync failed for Alpaca account %s: %s", rec.alpaca_account_id, e)
            errors += 1
    return {"pending_count": len(pending), "synced": synced, "errors": errors}
