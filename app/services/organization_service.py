"""Organization and OrganizationBlockchainDeployment service."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Organization, OrganizationBlockchainDeployment

logger = logging.getLogger(__name__)


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
