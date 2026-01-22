"""Organization context service for routing services to organization blockchains."""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    User, Organization, OrganizationBlockchainDeployment,
    UserImplementationConnection, VerifiedImplementation
)

logger = logging.getLogger(__name__)


class OrganizationContextService:
    """Service for loading organization context for service routing."""
    
    def __init__(self, db: Session):
        """Initialize organization context service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_organization_blockchain(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get organization's blockchain deployment for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with organization blockchain info or None
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.organization_id:
            return None
        
        org = self.db.query(Organization).filter(
            Organization.id == user.organization_id
        ).first()
        
        if not org:
            return None
        
        # Get primary blockchain deployment
        deployment = self.db.query(OrganizationBlockchainDeployment).filter(
            OrganizationBlockchainDeployment.organization_id == org.id,
            OrganizationBlockchainDeployment.is_primary == True
        ).first()
        
        if not deployment:
            return None
        
        return {
            "organization_id": org.id,
            "organization_name": org.name,
            "chain_id": deployment.chain_id,
            "deployment_type": deployment.deployment_type,
            "contract_address": deployment.contract_address,
            "rpc_url": None  # Will be loaded from organization config or deployment
        }
    
    def get_user_implementation_credentials(
        self,
        user_id: int,
        implementation_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get user's credentials for a specific implementation.
        
        Args:
            user_id: User ID
            implementation_name: Implementation name (e.g., "alpaca", "plaid")
            
        Returns:
            Connection data dictionary or None
        """
        connection = self.db.query(UserImplementationConnection).join(
            VerifiedImplementation
        ).filter(
            UserImplementationConnection.user_id == user_id,
            VerifiedImplementation.name == implementation_name,
            UserImplementationConnection.is_active == True
        ).first()
        
        if not connection or not connection.connection_data:
            return None
        
        return connection.connection_data
