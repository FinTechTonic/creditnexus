"""User settings API routes for preferences and API key management."""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import ByokProvider, User, UserByokKey
from app.auth.jwt_auth import require_auth
from app.services.entitlement_service import can_access_byok, has_trading_unlocked
from app.services.alpaca_broker_service import validate_alpaca_user_key

logger = logging.getLogger(__name__)


def _validate_polygon_api_key(api_key: str) -> bool:
    """Validate Polygon API key with a minimal aggs call. Do not log key."""
    try:
        from polygon.rest import RESTClient
        client = RESTClient(api_key=api_key)
        client.get_aggs(
            ticker="AAPL",
            multiplier=1,
            timespan="day",
            from_="2024-01-02",
            to="2024-01-03",
            limit=1,
        )
        return True
    except Exception as e:
        logger.debug("Polygon API key validation failed: %s", e)
        return False


router = APIRouter(prefix="/api/user-settings", tags=["user-settings"])


class UserPreferencesUpdate(BaseModel):
    """User preferences update model."""
    audio_input_mode: bool = False
    investment_mode: bool = False
    loan_mode: bool = False
    bank_mode: bool = False
    trading_mode: bool = False
    email_notifications: bool = True
    push_notifications: bool = False
    kyc_brokerage_notifications: bool = True
    brokerage_plaid_kyc_preferred: bool = False


class ByokAlpacaCreate(BaseModel):
    """BYOK Alpaca key (Trading API) – required to unlock trading."""

    api_key: str
    api_secret: str
    paper: bool = True


class ByokPolygonCreate(BaseModel):
    """BYOK Polygon key (market data)."""

    api_key: str


class ByokPolymarketCreate(BaseModel):
    """BYOK Polymarket L2 credentials (per-wallet; for CLOB orders). Include funder_address for orders and positions."""

    api_key: str
    secret: str
    passphrase: str
    funder_address: Optional[str] = None


class SignupFlagsUpdate(BaseModel):
    """Signup skip flags for analytics and post-signup CTAs."""

    signup_skipped_payment: Optional[bool] = None
    signup_skipped_plaid: Optional[bool] = None


class CertificationItem(BaseModel):
    """Optional FINRA or equivalent certification (type, number, expiry)."""

    certification_type: str = Field(..., description="e.g. FINRA Series 7, CFA")
    number: Optional[str] = Field(None, description="License/certification number")
    expiry: Optional[str] = Field(None, description="Expiry date (YYYY-MM-DD or free text)")


class CertificationsUpdate(BaseModel):
    """List of professional certifications (stored in profile_data.certifications)."""

    certifications: List[CertificationItem] = Field(default_factory=list)


class APIKeyCreate(BaseModel):
    """API key creation model."""
    name: str
    key: str  # Will be encrypted on storage


class APIKeyResponse(BaseModel):
    """API key response model."""
    id: int
    name: str
    created_at: str
    # Note: key value is not returned for security


@router.post("/signup-flags")
async def update_signup_flags(
    body: SignupFlagsUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Store signup skip flags (payment, Plaid) for analytics and post-signup CTAs."""
    if not current_user.profile_data:
        current_user.profile_data = {}
    if isinstance(current_user.profile_data, dict):
        if body.signup_skipped_payment is not None:
            current_user.profile_data["signup_skipped_payment"] = body.signup_skipped_payment
        if body.signup_skipped_plaid is not None:
            current_user.profile_data["signup_skipped_plaid"] = body.signup_skipped_plaid
    db.commit()
    db.refresh(current_user)
    return {"ok": True}


@router.get("/certifications")
async def get_certifications(
    current_user: User = Depends(require_auth),
):
    """Get optional FINRA/equivalent certifications from profile_data."""
    certs = []
    if getattr(current_user, "profile_data", None) and isinstance(current_user.profile_data, dict):
        raw = current_user.profile_data.get("certifications")
        if isinstance(raw, list):
            for c in raw:
                if isinstance(c, dict):
                    certs.append({
                        "certification_type": c.get("certification_type") or "",
                        "number": c.get("number"),
                        "expiry": c.get("expiry"),
                    })
    return {"certifications": certs}


@router.put("/certifications")
async def update_certifications(
    body: CertificationsUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Store optional FINRA/equivalent certifications in profile_data.certifications."""
    if not current_user.profile_data:
        current_user.profile_data = {}
    if not isinstance(current_user.profile_data, dict):
        current_user.profile_data = {}
    current_user.profile_data["certifications"] = [c.model_dump() for c in body.certifications]
    db.commit()
    db.refresh(current_user)
    return {"status": "success", "certifications": current_user.profile_data.get("certifications", [])}


@router.get("/byok/access")
async def get_byok_access(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get BYOK (Bring Your Own Keys) access: allowed or paywalled. Admin always allowed."""
    allowed = can_access_byok(current_user, db)
    return {
        "allowed": allowed,
        "reason": "admin_or_entitled" if allowed else "paywall",
    }


@router.get("/byok/trading-unlocked")
async def get_byok_trading_unlocked(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get whether trading is unlocked: admin or user has Alpaca key in BYOK."""
    unlocked = has_trading_unlocked(current_user, db)
    return {"unlocked": unlocked}


@router.post("/byok/alpaca")
async def post_byok_alpaca(
    body: ByokAlpacaCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add Alpaca Trading API key to BYOK; validates key and unlocks trading if valid."""
    if not can_access_byok(current_user, db):
        raise HTTPException(status_code=402, detail="BYOK access required. Upgrade or pay to configure keys.")
    if not validate_alpaca_user_key(body.api_key, body.api_secret, body.paper):
        raise HTTPException(status_code=400, detail="Invalid Alpaca API key or secret.")
    provider_type = "alpaca_paper" if body.paper else "alpaca_live"
    credentials = {
        "api_key": body.api_key,
        "api_secret": body.api_secret,
        "paper": body.paper,
    }
    existing = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == current_user.id,
            UserByokKey.provider == ByokProvider.ALPACA.value,
        )
        .first()
    )
    if existing:
        existing.provider_type = provider_type
        existing.credentials_encrypted = credentials
        existing.is_verified = True
        existing.unlocks_trading = True
        db.commit()
        db.refresh(existing)
    else:
        row = UserByokKey(
            user_id=current_user.id,
            provider=ByokProvider.ALPACA.value,
            provider_type=provider_type,
            credentials_encrypted=credentials,
            is_verified=True,
            unlocks_trading=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"trading_unlocked": True}


@router.post("/byok/polygon")
async def post_byok_polygon(
    body: ByokPolygonCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add Polygon API key to BYOK for market data (LangAlpha, stock analysis)."""
    if not can_access_byok(current_user, db):
        raise HTTPException(status_code=402, detail="BYOK access required. Upgrade or pay to configure keys.")
    if not body.api_key or not body.api_key.strip():
        raise HTTPException(status_code=400, detail="API key is required.")
    if not _validate_polygon_api_key(body.api_key.strip()):
        raise HTTPException(status_code=400, detail="Invalid Polygon API key.")
    credentials = {"api_key": body.api_key.strip()}
    existing = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == current_user.id,
            UserByokKey.provider == ByokProvider.POLYGON.value,
        )
        .first()
    )
    if existing:
        existing.credentials_encrypted = credentials
        existing.is_verified = True
        db.commit()
        db.refresh(existing)
    else:
        row = UserByokKey(
            user_id=current_user.id,
            provider=ByokProvider.POLYGON.value,
            provider_type="polygon",
            credentials_encrypted=credentials,
            is_verified=True,
            unlocks_trading=False,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"configured": True}


@router.post("/byok/polymarket")
async def post_byok_polymarket(
    body: ByokPolymarketCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add Polymarket L2 credentials to BYOK (api_key, secret, passphrase per wallet; for CLOB orders)."""
    if not can_access_byok(current_user, db):
        raise HTTPException(status_code=402, detail="BYOK access required. Upgrade or pay to configure keys.")
    if not body.api_key or not body.secret or not body.passphrase:
        raise HTTPException(status_code=400, detail="api_key, secret, and passphrase are required.")
    credentials = {
        "api_key": body.api_key.strip(),
        "secret": body.secret,
        "passphrase": body.passphrase,
    }
    if getattr(body, "funder_address", None) and str(body.funder_address).strip():
        credentials["funder_address"] = str(body.funder_address).strip()
    existing = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == current_user.id,
            UserByokKey.provider == ByokProvider.POLYMARKET.value,
        )
        .first()
    )
    if existing:
        existing.credentials_encrypted = credentials
        existing.is_verified = True
        db.commit()
        db.refresh(existing)
    else:
        row = UserByokKey(
            user_id=current_user.id,
            provider=ByokProvider.POLYMARKET.value,
            provider_type="polymarket",
            credentials_encrypted=credentials,
            is_verified=True,
            unlocks_trading=False,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"configured": True}


@router.get("/byok/keys")
async def get_byok_keys(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List configured BYOK providers (metadata only; no raw secrets). Never expose Plaid as BYOK."""
    if not can_access_byok(current_user, db):
        return {"keys": []}
    rows = db.query(UserByokKey).filter(UserByokKey.user_id == current_user.id).all()
    return {
        "keys": [
            {
                "provider": r.provider,
                "provider_type": r.provider_type,
                "is_verified": r.is_verified,
                "unlocks_trading": r.unlocks_trading,
            }
            for r in rows
        ]
    }


@router.delete("/byok/{provider}")
async def delete_byok_provider(
    provider: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove BYOK key for a provider. Provider must be alpaca, polygon, polymarket, other (not plaid)."""
    if provider.lower() == "plaid":
        raise HTTPException(status_code=400, detail="Plaid is not BYOK; link accounts in Link Accounts.")
    if provider.lower() not in [p.value for p in ByokProvider]:
        raise HTTPException(status_code=400, detail=f"Unknown BYOK provider: {provider}")
    row = (
        db.query(UserByokKey)
        .filter(
            UserByokKey.user_id == current_user.id,
            UserByokKey.provider == provider.lower(),
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return {"removed": True}


@router.get("/preferences")
async def get_user_preferences(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user preferences."""
    
    # Get preferences from user model
    # For now, use profile_data if preferences field doesn't exist yet
    preferences = {}
    if hasattr(current_user, 'preferences') and current_user.preferences:
        preferences = current_user.preferences
    elif hasattr(current_user, 'profile_data') and current_user.profile_data:
        # Fallback to profile_data.preferences if exists
        profile_data = current_user.profile_data
        if isinstance(profile_data, dict) and 'preferences' in profile_data:
            preferences = profile_data['preferences']
    
    return {
        "audio_input_mode": preferences.get("audio_input_mode", False),
        "investment_mode": preferences.get("investment_mode", False),
        "loan_mode": preferences.get("loan_mode", False),
        "bank_mode": preferences.get("bank_mode", False),
        "trading_mode": preferences.get("trading_mode", False),
        "email_notifications": preferences.get("email_notifications", True),
        "push_notifications": preferences.get("push_notifications", False),
        "kyc_brokerage_notifications": preferences.get("kyc_brokerage_notifications", True),
        "brokerage_plaid_kyc_preferred": preferences.get("brokerage_plaid_kyc_preferred", False),
    }


@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    
    # Update preferences
    if hasattr(current_user, 'preferences'):
        if not current_user.preferences:
            current_user.preferences = {}
        current_user.preferences.update(preferences.model_dump())
    else:
        # Fallback: store in profile_data if preferences field doesn't exist
        if not current_user.profile_data:
            current_user.profile_data = {}
        if 'preferences' not in current_user.profile_data:
            current_user.profile_data['preferences'] = {}
        current_user.profile_data['preferences'].update(preferences.model_dump())
    
    db.commit()
    db.refresh(current_user)
    
    return {"status": "success"}


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_user_api_keys(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user API keys (metadata only, not the actual keys)."""
    
    # Get API keys from user model
    api_keys = []
    if hasattr(current_user, 'api_keys') and current_user.api_keys:
        api_keys = current_user.api_keys
    elif hasattr(current_user, 'profile_data') and current_user.profile_data:
        # Fallback to profile_data.api_keys if exists
        profile_data = current_user.profile_data
        if isinstance(profile_data, dict) and 'api_keys' in profile_data:
            api_keys = profile_data['api_keys']
    
    return [
        {
            "id": key.get("id", idx + 1),
            "name": key.get("name", ""),
            "created_at": key.get("created_at", datetime.utcnow().isoformat()),
        }
        for idx, key in enumerate(api_keys)
    ]


@router.post("/api-keys")
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create new API key (encrypted storage)."""
    
    # For now, store in plain text (will be encrypted when encryption utility is available)
    # TODO: Use encryption utility when available
    # from app.utils.encryption import encrypt_field
    # encrypted_key = encrypt_field(key_data.key)
    
    new_key = {
        "id": 0,  # Will be set based on existing keys
        "name": key_data.name,
        "key": key_data.key,  # TODO: Encrypt this
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Get existing keys
    api_keys = []
    if hasattr(current_user, 'api_keys') and current_user.api_keys:
        api_keys = current_user.api_keys
    elif hasattr(current_user, 'profile_data') and current_user.profile_data:
        profile_data = current_user.profile_data
        if isinstance(profile_data, dict) and 'api_keys' in profile_data:
            api_keys = profile_data['api_keys']
    
    # Set ID
    if api_keys:
        new_key["id"] = max(k.get("id", 0) for k in api_keys) + 1
    else:
        new_key["id"] = 1
    
    # Add new key
    api_keys.append(new_key)
    
    # Save back to user model
    if hasattr(current_user, 'api_keys'):
        current_user.api_keys = api_keys
    else:
        # Fallback: store in profile_data
        if not current_user.profile_data:
            current_user.profile_data = {}
        current_user.profile_data['api_keys'] = api_keys
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": new_key["id"],
        "name": new_key["name"],
        "created_at": new_key["created_at"],
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete API key by ID."""
    
    # Get existing keys
    api_keys = []
    if hasattr(current_user, 'api_keys') and current_user.api_keys:
        api_keys = current_user.api_keys
    elif hasattr(current_user, 'profile_data') and current_user.profile_data:
        profile_data = current_user.profile_data
        if isinstance(profile_data, dict) and 'api_keys' in profile_data:
            api_keys = profile_data['api_keys']
    
    # Find and remove key
    original_count = len(api_keys)
    api_keys = [k for k in api_keys if k.get("id") != key_id]
    
    if len(api_keys) == original_count:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Save back to user model
    if hasattr(current_user, 'api_keys'):
        current_user.api_keys = api_keys
    else:
        # Fallback: store in profile_data
        if not current_user.profile_data:
            current_user.profile_data = {}
        current_user.profile_data['api_keys'] = api_keys
    
    db.commit()
    
    return {"status": "success"}


class UserProfileUpdate(BaseModel):
    """User profile update model."""
    display_name: Optional[str] = None
    profile_image: Optional[str] = None


class UserKYCInfoUpdate(BaseModel):
    """KYC information used for identity verification (stored in profile_data.kyc)."""
    legal_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO date string YYYY-MM-DD
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None  # SSN / TIN for brokerage (e.g. USA: XXX-XX-XXXX)
    tax_id_type: Optional[str] = None  # e.g. USA_SSN, USA_TIN


@router.get("/kyc-info")
async def get_user_kyc_info(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get KYC-related information (legal name, DOB, address, phone) used for identity verification."""
    kyc = {}
    if getattr(current_user, "profile_data", None) and isinstance(current_user.profile_data, dict):
        kyc = current_user.profile_data.get("kyc") or {}
    return {
        "legal_name": kyc.get("legal_name") or "",
        "date_of_birth": kyc.get("date_of_birth") or "",
        "address_line1": kyc.get("address_line1") or "",
        "address_line2": kyc.get("address_line2") or "",
        "address_city": kyc.get("address_city") or "",
        "address_state": kyc.get("address_state") or "",
        "address_postal_code": kyc.get("address_postal_code") or "",
        "address_country": kyc.get("address_country") or "",
        "phone": kyc.get("phone") or "",
        "tax_id": kyc.get("tax_id") or "",
        "tax_id_type": kyc.get("tax_id_type") or "USA_SSN",
    }


@router.put("/kyc-info")
async def update_user_kyc_info(
    payload: UserKYCInfoUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update KYC-related information (stored in profile_data.kyc)."""
    if not current_user.profile_data:
        current_user.profile_data = {}
    if "kyc" not in current_user.profile_data:
        current_user.profile_data["kyc"] = {}
    kyc = current_user.profile_data["kyc"]
    data = payload.model_dump(exclude_none=False)
    for key, value in data.items():
        kyc[key] = value or ""
    # Sync to top-level profile_data so Alpaca/brokerage prefill can use them
    current_user.profile_data["phone"] = kyc.get("phone") or ""
    current_user.profile_data["street_address"] = kyc.get("address_line1") or ""
    current_user.profile_data["city"] = kyc.get("address_city") or ""
    current_user.profile_data["state"] = kyc.get("address_state") or ""
    current_user.profile_data["postal_code"] = kyc.get("address_postal_code") or ""
    current_user.profile_data["country"] = kyc.get("address_country") or ""
    db.commit()
    db.refresh(current_user)
    return {"status": "success"}


@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user profile information."""
    
    return {
        "display_name": current_user.display_name,
        "email": current_user.email,
        "profile_image": current_user.profile_image,
    }


@router.put("/profile")
async def update_user_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    
    if profile.display_name is not None:
        current_user.display_name = profile.display_name
    if profile.profile_image is not None:
        current_user.profile_image = profile.profile_image
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "status": "success",
        "display_name": current_user.display_name,
        "profile_image": current_user.profile_image,
    }
