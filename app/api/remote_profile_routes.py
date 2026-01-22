"""RemoteAppProfile CRUD API: list, get, create, update, allowed-ips add/remove, rotate-api-key."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user, require_auth
from app.db import get_db
from app.db.models import User
from app.services.remote_profile_service import RemoteProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remote-profiles", tags=["remote-profiles"])


class CreateProfileRequest(BaseModel):
    profile_name: str = Field(..., min_length=1)
    allowed_ips: Optional[List[str]] = None
    permissions: Optional[Dict[str, bool]] = None


class UpdateProfileRequest(BaseModel):
    profile_name: Optional[str] = Field(None, min_length=1)
    allowed_ips: Optional[List[str]] = None
    permissions: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None


class AddAllowedIpRequest(BaseModel):
    value: str = Field(..., min_length=1)  # IP or CIDR


class RemoveAllowedIpRequest(BaseModel):
    value: str = Field(..., min_length=1)


def _normalize_allowed_ips(ips: Any) -> List[str]:
    if ips is None:
        return []
    if isinstance(ips, dict) and "ips" in ips:
        return list(ips.get("ips") or [])
    if isinstance(ips, list):
        return [str(x) for x in ips if x]
    return []


@router.get("", response_model=Dict[str, Any])
async def list_profiles(
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """List RemoteAppProfiles. Admin or delegated role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    rows = svc.list_profiles(is_active=is_active, limit=limit, offset=offset)
    return {"profiles": [r.to_dict() for r in rows]}


@router.get("/{profile_id}", response_model=Dict[str, Any])
async def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    p = svc.get_profile_by_id(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.to_dict()


@router.post("", response_model=Dict[str, Any], status_code=201)
async def create_profile(
    body: CreateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Create profile. Returns profile and api_key once; store api_key securely."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    try:
        profile, api_key = svc.create_profile(
            body.profile_name,
            allowed_ips=body.allowed_ips,
            permissions=body.permissions,
        )
        out = profile.to_dict()
        out["api_key"] = api_key
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{profile_id}", response_model=Dict[str, Any])
async def update_profile(
    profile_id: int,
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    try:
        p = svc.update_profile(
            profile_id,
            profile_name=body.profile_name,
            allowed_ips=body.allowed_ips,
            permissions=body.permissions,
            is_active=body.is_active,
        )
        return p.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{profile_id}/allowed-ips", response_model=Dict[str, Any])
async def add_allowed_ip(
    profile_id: int,
    body: AddAllowedIpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    p = svc.get_profile_by_id(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    lst = _normalize_allowed_ips(p.allowed_ips)
    if body.value in lst:
        return p.to_dict()
    lst.append(body.value)
    p = svc.update_profile(profile_id, allowed_ips=lst)
    return p.to_dict()


@router.delete("/{profile_id}/allowed-ips", response_model=Dict[str, Any])
async def remove_allowed_ip(
    profile_id: int,
    body: RemoveAllowedIpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    p = svc.get_profile_by_id(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    lst = _normalize_allowed_ips(p.allowed_ips)
    lst = [x for x in lst if x != body.value]
    p = svc.update_profile(profile_id, allowed_ips=lst)
    return p.to_dict()


@router.post("/{profile_id}/rotate-api-key", response_model=Dict[str, Any])
async def rotate_api_key(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Rotate API key. Returns new api_key once."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = RemoteProfileService(db)
    try:
        p, new_key = svc.rotate_api_key(profile_id)
        out = p.to_dict()
        out["api_key"] = new_key
        return out
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
