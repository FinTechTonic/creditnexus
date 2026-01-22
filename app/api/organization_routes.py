"""Organization and OrganizationBlockchainDeployment API."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import User
from app.services.organization_service import OrganizationService, OrganizationServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=1)
    slug: Optional[str] = Field(None)
    is_active: bool = True


class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class AddDeploymentRequest(BaseModel):
    chain_id: int = Field(..., ge=1)
    deployment_type: str = Field(..., min_length=1)  # notarization, token, router, etc.
    contract_address: str = Field(..., min_length=10)
    is_primary: bool = False


@router.get("/signup-choices", response_model=List[Dict[str, Any]])
async def signup_organization_choices(
    db: Session = Depends(get_db),
):
    """List org id and name for signup organization dropdown. No auth required."""
    svc = OrganizationService(db)
    rows = svc.list_organizations(is_active=True, limit=200)
    return [{"id": o["id"], "name": o["name"]} for o in rows]


@router.get("/pending", response_model=List[Dict[str, Any]])
async def list_pending_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List pending organizations awaiting approval (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        return svc.list_organizations(is_active=False, limit=200)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[Dict[str, Any]])
async def list_organizations(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List organizations (for signup selection and admin)."""
    svc = OrganizationService(db)
    try:
        return svc.list_organizations(is_active=is_active, limit=limit, offset=offset)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}", response_model=Dict[str, Any])
async def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    out = svc.get_organization(org_id)
    if not out:
        raise HTTPException(status_code=404, detail="Organization not found")
    return out


@router.post("", response_model=Dict[str, Any], status_code=201)
async def create_organization(
    body: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        return svc.create_organization(
            body.name, slug=body.slug, is_active=body.is_active
        )
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signup", response_model=Dict[str, Any], status_code=201)
async def create_organization_signup(
    body: CreateOrganizationRequest,
    db: Session = Depends(get_db),
):
    """Create a new organization during signup (requires admin approval).
    
    Creates organization with is_active=False, requiring admin approval.
    """
    svc = OrganizationService(db)
    try:
        # Create organization with is_active=False for admin approval
        return svc.create_organization(
            body.name, slug=body.slug, is_active=False
        )
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/approve", response_model=Dict[str, Any])
async def approve_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve an organization (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        org = svc.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Update organization to active
        return svc.update_organization(org_id, is_active=True)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/reject", response_model=Dict[str, Any])
async def reject_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject an organization (admin only). Deletes the organization."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        org = svc.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Delete organization (cascade will handle related records)
        from app.db.models import Organization
        db.delete(db.query(Organization).filter(Organization.id == org_id).first())
        db.commit()
        
        return {"status": "success", "message": "Organization rejected and deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{org_id}", response_model=Dict[str, Any])
async def update_organization(
    org_id: int,
    body: UpdateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        return svc.update_organization(
            org_id, name=body.name, slug=body.slug, is_active=body.is_active
        )
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}/blockchain-deployments", response_model=List[Dict[str, Any]])
async def list_deployments(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizationService(db)
    try:
        return svc.list_deployments(org_id)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{org_id}/blockchain-deployments", response_model=Dict[str, Any], status_code=201)
async def add_deployment(
    org_id: int,
    body: AddDeploymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        return svc.add_deployment(
            org_id,
            body.chain_id,
            body.deployment_type,
            body.contract_address,
            is_primary=body.is_primary,
        )
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
