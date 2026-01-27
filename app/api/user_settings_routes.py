"""User settings API routes for preferences and API key management."""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User
from app.auth.jwt_auth import require_auth

logger = logging.getLogger(__name__)

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
