"""Organization and OrganizationBlockchainDeployment API."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.db import get_db
from app.db.models import OrganizationSocialFeedWhitelist, User
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


class RegisterOrganizationRequest(BaseModel):
    """Phase 8: full registration body for POST /register."""

    legal_name: str = Field(..., min_length=1)
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    lei: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None


class DeployOrganizationBlockchainRequest(BaseModel):
    """Phase 8: body for POST /{id}/deploy."""

    deployment_type: str = Field(default="private_chain")  # private_chain, sidechain, l2
    chain_id: Optional[int] = None
    network_name: Optional[str] = None
    rpc_url: Optional[str] = None
    notarization_contract: Optional[str] = None
    token_contract: Optional[str] = None
    payment_router_contract: Optional[str] = None
    bridge_contract: Optional[str] = None


class SocialFeedWhitelistAddRequest(BaseModel):
    """Body for POST /{org_id}/social-feed-whitelist."""

    whitelisted_organization_id: int = Field(..., ge=1)


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


@router.post("/register", response_model=Dict[str, Any], status_code=201)
async def register_organization(
    body: RegisterOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new organization with full fields; status='pending' until approved (Phase 8)."""
    svc = OrganizationService(db)
    try:
        return svc.register_organization(
            body.legal_name,
            registration_number=body.registration_number,
            tax_id=body.tax_id,
            lei=body.lei,
            industry=body.industry,
            country=body.country,
            website=body.website,
            email=body.email,
            name=body.name,
            slug=body.slug,
        )
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
    """Approve an organization (admin only). Sets status=approved, approved_by, approved_at (Phase 8)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    svc = OrganizationService(db)
    try:
        org = svc.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return svc.approve_organization(org_id, current_user.id)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/deploy", response_model=Dict[str, Any], status_code=201)
async def deploy_organization_blockchain(
    org_id: int,
    body: DeployOrganizationBlockchainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deploy or record org blockchain deployment (admin or org admin) (Phase 8)."""
    if current_user.role != "admin" and getattr(current_user, "organization_id", None) != org_id:
        raise HTTPException(status_code=403, detail="Admin or org member only")
    svc = OrganizationService(db)
    try:
        org = svc.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return svc.deploy_organization_blockchain(
            org_id,
            deployment_type=body.deployment_type,
            chain_id=body.chain_id,
            deployed_by_user_id=current_user.id,
            network_name=body.network_name,
            rpc_url=body.rpc_url,
            notarization_contract=body.notarization_contract,
            token_contract=body.token_contract,
            payment_router_contract=body.payment_router_contract,
            bridge_contract=body.bridge_contract,
        )
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


def _is_org_admin_or_instance_admin(user: User, org_id: int) -> bool:
    """True if user is instance admin or org admin for the given org."""
    if user.role == "admin" and getattr(user, "is_instance_admin", False):
        return True
    if getattr(user, "organization_id", None) == org_id and (
        user.role == "admin" or getattr(user, "organization_role", None) == "admin"
    ):
        return True
    return False


@router.get("/{org_id}/social-feed-whitelist", response_model=List[Dict[str, Any]])
async def list_social_feed_whitelist(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List organizations whitelisted for social feed (org admin or instance admin)."""
    if not _is_org_admin_or_instance_admin(current_user, org_id):
        raise HTTPException(status_code=403, detail="Org admin or instance admin only")
    rows = (
        db.query(OrganizationSocialFeedWhitelist)
        .filter(OrganizationSocialFeedWhitelist.organization_id == org_id)
        .order_by(OrganizationSocialFeedWhitelist.whitelisted_organization_id)
        .all()
    )
    return [r.to_dict() for r in rows]


@router.post("/{org_id}/social-feed-whitelist", response_model=Dict[str, Any], status_code=201)
async def add_social_feed_whitelist(
    org_id: int,
    body: SocialFeedWhitelistAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an organization to social feed whitelist (org admin or instance admin)."""
    if not _is_org_admin_or_instance_admin(current_user, org_id):
        raise HTTPException(status_code=403, detail="Org admin or instance admin only")
    if body.whitelisted_organization_id == org_id:
        raise HTTPException(status_code=400, detail="Cannot whitelist own organization")
    existing = (
        db.query(OrganizationSocialFeedWhitelist)
        .filter(
            OrganizationSocialFeedWhitelist.organization_id == org_id,
            OrganizationSocialFeedWhitelist.whitelisted_organization_id == body.whitelisted_organization_id,
        )
        .first()
    )
    if existing:
        return existing.to_dict()
    row = OrganizationSocialFeedWhitelist(
        organization_id=org_id,
        whitelisted_organization_id=body.whitelisted_organization_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.to_dict()


@router.delete("/{org_id}/social-feed-whitelist/{whitelisted_org_id}", status_code=204)
async def remove_social_feed_whitelist(
    org_id: int,
    whitelisted_org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an organization from social feed whitelist (org admin or instance admin)."""
    if not _is_org_admin_or_instance_admin(current_user, org_id):
        raise HTTPException(status_code=403, detail="Org admin or instance admin only")
    row = (
        db.query(OrganizationSocialFeedWhitelist)
        .filter(
            OrganizationSocialFeedWhitelist.organization_id == org_id,
            OrganizationSocialFeedWhitelist.whitelisted_organization_id == whitelisted_org_id,
        )
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return None
