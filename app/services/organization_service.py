"""Organization and OrganizationBlockchainDeployment service."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Organization, OrganizationBlockchainDeployment

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Simple slug from name (lowercase, spaces to hyphens, alphanumeric + hyphen)."""
    if not name:
        return ""
    return "".join(c if c.isalnum() or c == "-" else "-" for c in name.lower().replace(" ", "-")).strip("-") or "org"


class OrganizationServiceError(Exception):
    pass


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_organizations(
        self,
        *,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        q = self.db.query(Organization)
        if is_active is not None:
            q = q.filter(Organization.is_active == is_active)
        rows = q.order_by(Organization.name).offset(offset).limit(limit).all()
        return [o.to_dict() for o in rows]

    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        return o.to_dict() if o else None

    def create_organization(
        self,
        name: str,
        *,
        slug: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        if slug and self.db.query(Organization).filter(Organization.slug == slug).first():
            raise OrganizationServiceError(f"Organization slug already exists: {slug}")
        o = Organization(name=name, slug=slug or None, is_active=is_active)
        self.db.add(o)
        self.db.commit()
        self.db.refresh(o)
        return o.to_dict()

    def update_organization(
        self,
        org_id: int,
        *,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not o:
            raise OrganizationServiceError(f"Organization {org_id} not found")
        if name is not None:
            o.name = name
        if slug is not None:
            o.slug = slug
        if is_active is not None:
            o.is_active = is_active
        self.db.commit()
        self.db.refresh(o)
        return o.to_dict()

    def list_deployments(self, org_id: int) -> List[Dict[str, Any]]:
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not o:
            raise OrganizationServiceError(f"Organization {org_id} not found")
        rows = (
            self.db.query(OrganizationBlockchainDeployment)
            .filter(OrganizationBlockchainDeployment.organization_id == org_id)
            .order_by(OrganizationBlockchainDeployment.chain_id, OrganizationBlockchainDeployment.deployment_type)
            .all()
        )
        return [d.to_dict() for d in rows]

    def add_deployment(
        self,
        org_id: int,
        chain_id: int,
        deployment_type: str,
        contract_address: str,
        *,
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not o:
            raise OrganizationServiceError(f"Organization {org_id} not found")
        d = OrganizationBlockchainDeployment(
            organization_id=org_id,
            chain_id=chain_id,
            deployment_type=deployment_type,
            contract_address=contract_address,
            is_primary=is_primary,
        )
        self.db.add(d)
        self.db.commit()
        self.db.refresh(d)
        return d.to_dict()

    def register_organization(
        self,
        legal_name: str,
        *,
        registration_number: Optional[str] = None,
        tax_id: Optional[str] = None,
        lei: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        website: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new organization with full fields; status='pending' until approved."""
        if registration_number and self.db.query(Organization).filter(Organization.registration_number == registration_number).first():
            raise OrganizationServiceError("Organization with this registration number already exists")
        if lei and self.db.query(Organization).filter(Organization.lei == lei).first():
            raise OrganizationServiceError("Organization with this LEI already exists")
        display_name = name or legal_name
        base_slug = slug or _slugify(display_name)
        s = base_slug
        n = 0
        while self.db.query(Organization).filter(Organization.slug == s).first():
            n += 1
            s = f"{base_slug}-{n}"
        o = Organization(
            name=display_name,
            slug=s,
            is_active=True,
            legal_name=legal_name,
            registration_number=registration_number,
            tax_id=tax_id,
            lei=lei,
            industry=industry,
            country=country,
            website=website,
            email=email,
            status="pending",
            registration_date=datetime.utcnow(),
            subscription_tier="free",
        )
        self.db.add(o)
        self.db.commit()
        self.db.refresh(o)
        return o.to_dict()

    def approve_organization(self, org_id: int, approved_by_user_id: int) -> Dict[str, Any]:
        """Set organization status to 'approved' and record approver."""
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not o:
            raise OrganizationServiceError(f"Organization {org_id} not found")
        o.status = "approved"
        o.approved_by = approved_by_user_id
        o.approved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(o)
        return o.to_dict()

    def deploy_organization_blockchain(
        self,
        org_id: int,
        *,
        deployment_type: str = "private_chain",
        chain_id: Optional[int] = None,
        deployed_by_user_id: Optional[int] = None,
        network_name: Optional[str] = None,
        rpc_url: Optional[str] = None,
        notarization_contract: Optional[str] = None,
        token_contract: Optional[str] = None,
        payment_router_contract: Optional[str] = None,
        bridge_contract: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy or record org blockchain deployment; calls _deploy_* stubs."""
        o = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not o:
            raise OrganizationServiceError(f"Organization {org_id} not found")
        if deployment_type == "private_chain":
            self._deploy_private_chain(org_id)
        elif deployment_type == "sidechain":
            self._deploy_sidechain(org_id)
        elif deployment_type == "l2":
            self._deploy_l2(org_id)
        cid = chain_id or 0
        d = OrganizationBlockchainDeployment(
            organization_id=org_id,
            chain_id=cid,
            deployment_type=deployment_type,
            contract_address=notarization_contract or token_contract or "0x0",
            is_primary=True,
            network_name=network_name,
            rpc_url=rpc_url,
            notarization_contract=notarization_contract,
            token_contract=token_contract,
            payment_router_contract=payment_router_contract,
            bridge_contract=bridge_contract,
            status="deployed",
            deployed_at=datetime.utcnow(),
            deployed_by=deployed_by_user_id,
        )
        self.db.add(d)
        self.db.commit()
        self.db.refresh(d)
        return d.to_dict()

    def _deploy_private_chain(self, org_id: int) -> None:
        """Stub: integrate with existing blockchain_service for private chain deployment."""
        logger.info("_deploy_private_chain stub called for org_id=%s", org_id)

    def _deploy_sidechain(self, org_id: int) -> None:
        """Stub: integrate for sidechain deployment."""
        logger.info("_deploy_sidechain stub called for org_id=%s", org_id)

    def _deploy_l2(self, org_id: int) -> None:
        """Stub: integrate for L2 deployment."""
        logger.info("_deploy_l2 stub called for org_id=%s", org_id)
