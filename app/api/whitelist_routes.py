"""WhitelistProfile CRUD API and presets from VerifiedImplementation."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user, require_auth
from app.db import get_db
from app.db.models import User, WhitelistProfile, VerifiedImplementation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])

ALLOWED_LISTS = frozenset({
    "allowed_ips", "allowed_cidrs", "enabled_categories", "implementation_ids",
    "allowed_nodes",
})
# allowed_extensions lives inside file_types; we can support "allowed_extensions" as a special list
ALLOWED_LISTS_ALL = ALLOWED_LISTS | {"allowed_extensions"}


class CreateProfileRequest(BaseModel):
    name: str = Field(..., min_length=1)
    scope: str = Field(..., min_length=1)
    enabled_categories: Optional[List[str]] = None
    file_types: Optional[Dict[str, Any]] = None
    subdirectories: Optional[Dict[str, Any]] = None
    allowed_ips: Optional[List[str]] = None
    allowed_cidrs: Optional[List[str]] = None
    implementation_ids: Optional[List[int]] = None
    allowed_nodes: Optional[List[Dict[str, Any]]] = None
    preset_implementation_id: Optional[int] = None
    organization_id: Optional[int] = None
    is_active: bool = True


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    scope: Optional[str] = None
    enabled_categories: Optional[List[str]] = None
    file_types: Optional[Dict[str, Any]] = None
    subdirectories: Optional[Dict[str, Any]] = None
    allowed_ips: Optional[List[str]] = None
    allowed_cidrs: Optional[List[str]] = None
    implementation_ids: Optional[List[int]] = None
    allowed_nodes: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None


class ProfileItemRequest(BaseModel):
    list: str = Field(..., description="allowed_ips|allowed_cidrs|enabled_categories|implementation_ids|allowed_nodes|allowed_extensions")
    value: Any = Field(..., description="Item to add: string, number, or object for allowed_nodes")


class ProfileItemDeleteRequest(BaseModel):
    list: str = Field(...)
    value: Any = Field(..., description="Item to remove; for allowed_nodes can be object with id or host")


def _merge_preset(impl: VerifiedImplementation, base: Dict[str, Any]) -> Dict[str, Any]:
    pre = impl.whitelist_preset or {}
    out = dict(base)
    if "enabled_categories" in pre and pre["enabled_categories"]:
        out["enabled_categories"] = pre["enabled_categories"]
    if "file_types" in pre and pre["file_types"]:
        ft = dict(out.get("file_types") or {})
        ft.update(pre["file_types"])
        out["file_types"] = ft
    if "allowed_extensions" in pre and pre["allowed_extensions"]:
        ft = dict(out.get("file_types") or {})
        ft["allowed_extensions"] = pre["allowed_extensions"]
        out["file_types"] = ft
    if "allowed_ips" in pre and pre["allowed_ips"]:
        out["allowed_ips"] = pre["allowed_ips"]
    return out


@router.get("/profiles", response_model=Dict[str, Any])
async def list_profiles(
    scope: Optional[str] = Query(None),
    organization_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    q = db.query(WhitelistProfile)
    if scope:
        q = q.filter(WhitelistProfile.scope == scope)
    if organization_id is not None:
        q = q.filter(WhitelistProfile.organization_id == organization_id)
    if is_active is not None:
        q = q.filter(WhitelistProfile.is_active == is_active)
    rows = q.order_by(WhitelistProfile.name).offset(offset).limit(limit).all()
    return {"profiles": [r.to_dict() for r in rows]}


@router.get("/profiles/{profile_id}", response_model=Dict[str, Any])
async def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    p = db.query(WhitelistProfile).filter(WhitelistProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p.to_dict()


@router.post("/profiles", response_model=Dict[str, Any], status_code=201)
async def create_profile(
    body: CreateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    base = {
        "enabled_categories": body.enabled_categories,
        "file_types": body.file_types,
        "subdirectories": body.subdirectories,
        "allowed_ips": body.allowed_ips,
        "allowed_cidrs": body.allowed_cidrs,
        "implementation_ids": body.implementation_ids,
        "allowed_nodes": body.allowed_nodes,
    }
    if body.preset_implementation_id:
        impl = db.query(VerifiedImplementation).filter(
            VerifiedImplementation.id == body.preset_implementation_id,
            VerifiedImplementation.is_active == True,
        ).first()
        if impl:
            base = _merge_preset(impl, base)
    p = WhitelistProfile(
        name=body.name,
        scope=body.scope,
        enabled_categories=base.get("enabled_categories"),
        file_types=base.get("file_types"),
        subdirectories=base.get("subdirectories"),
        allowed_ips=base.get("allowed_ips"),
        allowed_cidrs=base.get("allowed_cidrs"),
        implementation_ids=base.get("implementation_ids"),
        allowed_nodes=base.get("allowed_nodes"),
        preset_implementation_id=body.preset_implementation_id,
        organization_id=body.organization_id,
        is_active=body.is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.patch("/profiles/{profile_id}", response_model=Dict[str, Any])
async def update_profile(
    profile_id: int,
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = db.query(WhitelistProfile).filter(WhitelistProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    for k in ("name", "scope", "enabled_categories", "file_types", "subdirectories",
              "allowed_ips", "allowed_cidrs", "implementation_ids", "allowed_nodes", "is_active"):
        v = getattr(body, k, None)
        if v is not None:
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.delete("/profiles/{profile_id}", response_model=Dict[str, Any])
async def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = db.query(WhitelistProfile).filter(WhitelistProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    p.is_active = False
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.post("/profiles/{profile_id}/items", response_model=Dict[str, Any])
async def add_profile_item(
    profile_id: int,
    body: ProfileItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if body.list not in ALLOWED_LISTS_ALL:
        raise HTTPException(status_code=400, detail=f"list must be one of {sorted(ALLOWED_LISTS_ALL)}")
    p = db.query(WhitelistProfile).filter(WhitelistProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.list == "allowed_extensions":
        ft = dict(p.file_types or {})
        exts = list(ft.get("allowed_extensions") or [])
        v = body.value if isinstance(body.value, str) else str(body.value)
        if not v.startswith("."):
            v = "." + v
        if v not in exts:
            exts.append(v)
        ft["allowed_extensions"] = exts
        p.file_types = ft
    else:
        attr = body.list
        lst = list(getattr(p, attr) or [])
        if body.list == "implementation_ids":
            v = int(body.value) if body.value is not None else None
            if v is not None and v not in lst:
                lst.append(v)
        elif body.list == "allowed_nodes":
            if isinstance(body.value, dict) and body.value not in lst:
                lst.append(body.value)
        else:
            v = body.value if isinstance(body.value, str) else str(body.value)
            if v and v not in lst:
                lst.append(v)
        setattr(p, attr, lst)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.delete("/profiles/{profile_id}/items", response_model=Dict[str, Any])
async def remove_profile_item(
    profile_id: int,
    body: ProfileItemDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if body.list not in ALLOWED_LISTS_ALL:
        raise HTTPException(status_code=400, detail=f"list must be one of {sorted(ALLOWED_LISTS_ALL)}")
    p = db.query(WhitelistProfile).filter(WhitelistProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.list == "allowed_extensions":
        ft = dict(p.file_types or {})
        exts = list(ft.get("allowed_extensions") or [])
        v = body.value if isinstance(body.value, str) else str(body.value)
        if not v.startswith("."):
            v = "." + v
        exts = [x for x in exts if x != v]
        ft["allowed_extensions"] = exts
        p.file_types = ft
    else:
        attr = body.list
        lst = list(getattr(p, attr) or [])
        if body.list == "allowed_nodes":
            if isinstance(body.value, dict):
                vid, vhost = body.value.get("id"), body.value.get("host")
                lst = [n for n in lst if not (isinstance(n, dict) and (n.get("id") == vid or n.get("host") == vhost))]
            else:
                lst = [n for n in lst if n != body.value]
        elif body.list == "implementation_ids":
            v = int(body.value) if body.value is not None else None
            lst = [x for x in lst if x != v]
        else:
            v = body.value if isinstance(body.value, str) else str(body.value)
            lst = [x for x in lst if x != v]
        setattr(p, attr, lst)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/presets/implementations", response_model=List[Dict[str, Any]])
async def list_preset_implementations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """List VerifiedImplementations with whitelist_preset (for 'populate from' dropdown)."""
    rows = (
        db.query(VerifiedImplementation)
        .filter(
            VerifiedImplementation.is_active == True,
            VerifiedImplementation.whitelist_preset.isnot(None),
        )
        .order_by(VerifiedImplementation.name)
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "display_name": r.display_name, "category": r.category, "whitelist_preset": r.whitelist_preset}
        for r in rows
    ]
