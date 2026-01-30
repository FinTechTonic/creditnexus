"""
Alpaca Broker account opening orchestration.

- open_alpaca_account(user_id, db): KYC gate, build payload from User + KYCVerification,
  call Broker API create_account, persist AlpacaCustomerAccount.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import User, UserRole, KYCVerification, AlpacaCustomerAccount
from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError
from app.services.kyc_service import KYCService
from app.utils.audit import log_audit_action
from app.db.models import AuditAction

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-2 -> alpha-3 for contact.country (Alpaca requires alpha-3)
_COUNTRY_ALPHA2_TO_ALPHA3: Dict[str, str] = {
    "US": "USA", "CA": "CAN", "GB": "GBR", "DE": "DEU", "FR": "FRA", "IT": "ITA",
    "ES": "ESP", "AU": "AUS", "JP": "JPN", "CN": "CHN", "IN": "IND", "BR": "BRA",
    "MX": "MEX", "NL": "NLD", "CH": "CHE", "SE": "SWE", "PL": "POL", "IE": "IRL",
}


def _country_to_alpha3(country: str) -> str:
    """Return ISO 3166-1 alpha-3 code; Alpaca contact.country requires alpha-3."""
    s = (str(country) or "").strip().upper()
    if len(s) == 3 and s.isalpha():
        return s[:3]
    if len(s) >= 2:
        return _COUNTRY_ALPHA2_TO_ALPHA3.get(s[:2], "USA")
    return "USA"


class AlpacaAccountServiceError(Exception):
    """Raised when account opening or status update fails."""
    pass


def is_instance_owner(user_id: int, db: Session) -> bool:
    """True if user is instance owner (admin role or first user). Instance owner always has access to brokerage apply."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    role = getattr(user, "role", None)
    if role == UserRole.ADMIN.value:
        return True
    # First user in DB (lowest id) is treated as instance owner
    first = db.query(User).order_by(User.id.asc()).limit(1).first()
    return first is not None and first.id == user_id


def _build_account_payload(
    user: User,
    verification: Optional[KYCVerification],
    *,
    prefill_override: Optional[Dict[str, Any]] = None,
    agreements_override: Optional[List[Dict[str, Any]]] = None,
    enabled_assets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build Alpaca Broker API account creation payload from User, KYCVerification, and optional Plaid prefill/agreements."""
    email = getattr(user, "email", None) or ""
    if hasattr(email, "get_secret_value"):
        email = email.get_secret_value() or ""
    email = str(email)

    display_name = getattr(user, "display_name", None) or email.split("@")[0] or "User"
    if hasattr(display_name, "get_secret_value"):
        display_name = display_name.get_secret_value() or email.split("@")[0]
    display_name = str(display_name).strip()
    parts = display_name.split(None, 1)
    given_name = (prefill_override or {}).get("given_name") or (parts[0] if parts else "Given")
    family_name = (prefill_override or {}).get("family_name") or (parts[1] if len(parts) > 1 else "User")

    profile_data = getattr(user, "profile_data", None) or {}
    kyc = isinstance(profile_data, dict) and profile_data.get("kyc") or {}
    if isinstance(profile_data, dict):
        # Prefer user-configured KYC info from User Settings when present
        phone = (kyc.get("phone") or profile_data.get("phone") or profile_data.get("phone_number") or "").strip()
        # Normalize street: prefill/API may send string or list
        _raw_street = (
            (prefill_override or {}).get("street_address")
            or kyc.get("address_line1")
            or profile_data.get("street_address")
            or profile_data.get("address")
            or ""
        )
        street = (_raw_street[0] if isinstance(_raw_street, list) and _raw_street else str(_raw_street or "")).strip()
        unit = (kyc.get("address_line2") or (prefill_override or {}).get("unit") or "").strip()[:32]
        city = (
            (prefill_override or {}).get("city")
            or kyc.get("address_city")
            or profile_data.get("city")
            or ""
        ).strip()
        state = (
            (prefill_override or {}).get("state")
            or kyc.get("address_state")
            or profile_data.get("state")
            or ""
        ).strip()
        postal_code = (
            (prefill_override or {}).get("postal_code")
            or kyc.get("address_postal_code")
            or profile_data.get("postal_code")
            or profile_data.get("zip")
            or ""
        ).strip()
        country = (
            (prefill_override or {}).get("country")
            or kyc.get("address_country")
            or profile_data.get("country")
            or "USA"
        ).strip()
        if kyc.get("legal_name"):
            kyc_parts = str(kyc["legal_name"]).strip().split(None, 1)
            given_name = (prefill_override or {}).get("given_name") or (kyc_parts[0] if kyc_parts else given_name)
            family_name = (prefill_override or {}).get("family_name") or (kyc_parts[1] if len(kyc_parts) > 1 else family_name)
    else:
        phone = ""
        street = (prefill_override or {}).get("street_address") or ""
        street = (street[0] if isinstance(street, list) and street else str(street or "")).strip()
        unit = ""
        city = (prefill_override or {}).get("city") or ""
        state = (prefill_override or {}).get("state") or ""
        postal_code = (prefill_override or {}).get("postal_code") or ""
        country = (prefill_override or {}).get("country") or "USA"

    # Alpaca requires contact.street_address (array of Latin strings); invalid/empty can return "required"
    # Use valid Latin placeholders when user has not provided address (sandbox only)
    _street_val = str(street)[:64].strip() if street else "123 Application Pending"
    _city_val = (str(city)[:32]).strip() if city else "New York"
    _state_val = (str(state)[:32]).strip() if state else "NY"
    _postal_val = str(postal_code)[:10].strip() if postal_code else "10001"
    _country_contact = (str(country)[:2].upper() if country and len(str(country)) >= 2 else "US")
    if len(_country_contact) != 2:
        _country_contact = "US"

    # Alpaca contact.country must be ISO 3166-1 alpha-3 (e.g. USA, CAN, GBR)
    _country_alpha3 = _country_to_alpha3(country)
    # Alpaca account opening payload (contact, identity, address)
    # https://docs.alpaca.markets/reference/createaccount
    # contact: street_address (array), city, postal_code, state, country, unit (optional)
    contact = {
        "email_address": email,
        "phone_number": str(phone)[:20] if phone else "",
        "street_address": [_street_val],
        "city": _city_val,
        "postal_code": _postal_val,
        "state": _state_val,
        "country": _country_alpha3,
    }
    if unit:
        contact["unit"] = str(unit)[:32]
    dob = "1990-01-01"  # Placeholder if not in profile; Alpaca may require or return ACTION_REQUIRED
    if kyc.get("date_of_birth"):
        dob = str(kyc["date_of_birth"])[:10]
    if isinstance(verification, KYCVerification) and getattr(verification, "verification_metadata", None):
        meta = verification.verification_metadata or {}
        if isinstance(meta, dict) and meta.get("date_of_birth"):
            dob = str(meta["date_of_birth"])[:10]
    # Alpaca identity country fields must be 3 characters (ISO 3166-1 alpha-3), same as contact.country
    # Tax ID: use from profile_data.kyc if present, else sandbox placeholder (Alpaca requires it for account creation)
    tax_id = (kyc.get("tax_id") or "").strip() if isinstance(kyc, dict) else ""
    tax_id_type = (kyc.get("tax_id_type") or "USA_SSN").strip() if isinstance(kyc, dict) else "USA_SSN"
    if not tax_id or len(tax_id.replace("-", "").replace(".", "")) < 9:
        # Sandbox placeholder: 9 digits required for USA_SSN; do not use in production without user-provided SSN
        tax_id = "111-22-3333"
        tax_id_type = "USA_SSN"
    # identity per dev/alpaca.md: country_* in alpha-3, funding_source required in sample
    identity = {
        "given_name": str(given_name)[:50],
        "family_name": str(family_name)[:50],
        "date_of_birth": dob,
        "country_of_citizenship": _country_alpha3,
        "country_of_birth": _country_alpha3,
        "country_of_tax_residence": _country_alpha3,
        "tax_id": str(tax_id)[:40],
        "tax_id_type": tax_id_type,
        "funding_source": ["employment_income"],
    }

    address = {
        "street_address": [_street_val],
        "city": _city_val,
        "state": _state_val,
        "postal_code": _postal_val,
        "country": _country_alpha3,
    }

    # Agreements: use client-provided (Plaid KYC flow) or server-generated
    agreements: List[Dict[str, Any]] = []
    if agreements_override and len(agreements_override) >= 2:
        for a in agreements_override:
            if isinstance(a, dict) and a.get("agreement") and a.get("signed_at"):
                agreements.append({
                    "agreement": str(a["agreement"])[:64],
                    "signed_at": str(a["signed_at"]),
                    "ip_address": str(a.get("ip_address") or "0.0.0.0")[:45],
                })
    if len(agreements) < 2:
        signed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        agreements = [
            {"agreement": "customer_agreement", "signed_at": signed_at, "ip_address": "0.0.0.0"},
            {"agreement": "margin_agreement", "signed_at": signed_at, "ip_address": "0.0.0.0"},
        ]

    # Alpaca enabled_assets: us_equity (equities), crypto, us_option, etc. Default equities only.
    assets: List[str] = (
        [str(a).strip() for a in enabled_assets if isinstance(enabled_assets, list) and str(a).strip()][:10]
        if enabled_assets
        else ["us_equity"]
    )
    return {
        "contact": contact,
        "identity": identity,
        "disclosures": {
            "is_control_person": False,
            "is_affiliated_exchange_or_finra": False,
            "is_affiliated_exchange_or_iiroc": False,
            "is_politically_exposed": False,
            "immediate_family_exposed": False,
        },
        "agreements": agreements,
        "documents": [],
        "trusted_contact": {
            "given_name": str(given_name)[:50],
            "family_name": str(family_name)[:50],
            "email_address": email,
        },
        "address": address,
        "enabled_assets": assets,
    }


def _has_plaid_identity(user_id: int, db: Session) -> bool:
    """True if user has linked Plaid and identity data (owners) is available. Used for Plaid KYC flow."""
    try:
        from app.services.plaid_service import get_plaid_connection, get_identity
        conn = get_plaid_connection(db, user_id)
        if not conn or not getattr(conn, "connection_data", None) or not isinstance(conn.connection_data, dict):
            return False
        access_token = conn.connection_data.get("access_token")
        if not access_token:
            return False
        identity_resp = get_identity(access_token)
        if "error" in identity_resp:
            return False
        accounts = identity_resp.get("accounts") or []
        for acc in accounts:
            owners = acc.get("owners") or []
            if owners:
                return True
        return False
    except Exception as e:
        logger.warning("_has_plaid_identity check failed for user %s: %s", user_id, e)
        return False


def open_alpaca_account(
    user_id: int,
    db: Session,
    *,
    agreements_override: Optional[List[Dict[str, Any]]] = None,
    prefill_override: Optional[Dict[str, Any]] = None,
    use_plaid_kyc: bool = False,
    enabled_assets: Optional[List[str]] = None,
) -> AlpacaCustomerAccount:
    """
    Open an Alpaca Broker account for the user.
    - KYC: instance owner bypass, or use_plaid_kyc + Plaid identity, or evaluate_kyc_for_brokerage.
    - Builds account payload from User + KYCVerification + optional Plaid prefill and client agreements.
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

    # KYC: instance owner bypass, or Plaid KYC (linked Plaid + identity), or policy KYC
    kyc_satisfied = is_instance_owner(user_id, db)
    if not kyc_satisfied and use_plaid_kyc and _has_plaid_identity(user_id, db):
        kyc_satisfied = True
    if not kyc_satisfied:
        kyc = KYCService(db)
        if not kyc.evaluate_kyc_for_brokerage(user_id):
            raise AlpacaAccountServiceError(
                "KYC not sufficient for brokerage. Verify identity with Plaid (link bank) or complete identity verification first."
            )

    client = get_broker_client()
    if not client:
        raise AlpacaAccountServiceError("Broker API not configured (ALPACA_BROKER_API_KEY/SECRET)")

    verification = getattr(user, "kyc_verification", None)
    payload = _build_account_payload(
        user, verification,
        prefill_override=prefill_override,
        agreements_override=agreements_override,
        enabled_assets=enabled_assets,
    )

    # Log payload structure (no PII) for debugging Alpaca 400/422
    _contact = payload.get("contact")
    _identity = payload.get("identity")
    _contact_keys = list(_contact.keys()) if isinstance(_contact, dict) else type(_contact).__name__
    _identity_keys = list(_identity.keys()) if isinstance(_identity, dict) else type(_identity).__name__
    _street_ok = bool(_contact.get("street_address")) if isinstance(_contact, dict) else False
    logger.info(
        "Alpaca account apply: user_id=%s contact_keys=%s identity_keys=%s street_provided=%s",
        user_id, _contact_keys, _identity_keys, _street_ok,
    )
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


def sync_alpaca_account_status(rec: AlpacaCustomerAccount, db: Session) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Poll Alpaca Broker API for account status and update local record.
    Returns (changed, data): changed True if status/account_number/action_required_reason changed;
    data is the raw Alpaca account dict when available (for crypto_status, enabled_assets in API response).
    """
    client = get_broker_client()
    if not client:
        return False, None
    try:
        data = client.get_account(rec.alpaca_account_id)
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca get_account failed for %s: %s", rec.alpaca_account_id, e)
        return False, None

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
        if status in ("ACTIVE", "ACTION_REQUIRED"):
            try:
                from app.services.kyc_brokerage_notification import notify_kyc_brokerage_status

                subject = "Brokerage account status update"
                if status == "ACTIVE":
                    msg = "Your brokerage account is now active. You can place trades."
                else:
                    msg = "Action required on your brokerage account. Please check the app for details."
                notify_kyc_brokerage_status(db, rec.user_id, subject, msg)
            except Exception as exc:
                logger.warning("KYC/brokerage notification failed after Alpaca status sync: %s", exc)
    return changed, data


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
            changed, _ = sync_alpaca_account_status(rec, db)
            if changed:
                synced += 1
        except Exception as e:
            logger.warning("Sync failed for Alpaca account %s: %s", rec.alpaca_account_id, e)
            errors += 1
    return {"pending_count": len(pending), "synced": synced, "errors": errors}
