"""
Policy Editor Service for CreditNexus.

Manages policy CRUD operations, versioning, and approval workflows.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Policy, PolicyVersion, PolicyApproval, PolicyStatus
from app.services.policy_validator import PolicyValidator
from app.services.policy_tester import PolicyTester

logger = logging.getLogger(__name__)


class PolicyEditorService:
    """Service for managing policies in the editor."""
    
    def __init__(self, db: Session):
        """
        Initialize policy editor service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.validator = PolicyValidator()
        self.tester = PolicyTester()
    
    def create_policy(
        self,
        name: str,
        category: str,
        rules_yaml: str,
        description: Optional[str] = None,
        created_by: int = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Policy:
        """
        Create a new policy.
        
        Args:
            name: Policy name
            category: Policy category
            rules_yaml: Policy rules YAML
            description: Optional description
            created_by: User ID of creator
            metadata: Optional metadata
            
        Returns:
            Created Policy instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate YAML
        validation_result = self.validator.validate(rules_yaml)
        if not validation_result.valid:
            raise ValueError(f"Invalid policy YAML: {', '.join(validation_result.errors)}")
        
        # Create policy
        policy = Policy(
            name=name,
            category=category,
            description=description,
            rules_yaml=rules_yaml,
            status=PolicyStatus.DRAFT.value,
            version=1,
            created_by=created_by,
            additional_metadata=metadata or {}
        )
        
        self.db.add(policy)
        self.db.flush()
        
        # Create initial version
        version = PolicyVersion(
            policy_id=policy.id,
            version=1,
            rules_yaml=rules_yaml,
            changes_summary="Initial version",
            created_by=created_by
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Created policy {policy.id}: {name}")
        return policy
    
    def update_policy(
        self,
        policy_id: int,
        rules_yaml: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        updated_by: int = None,
        changes_summary: Optional[str] = None
    ) -> Policy:
        """
        Update an existing policy (creates new version).
        
        Args:
            policy_id: Policy ID
            rules_yaml: Updated rules YAML (optional)
            name: Updated name (optional)
            description: Updated description (optional)
            category: Updated category (optional)
            updated_by: User ID of updater
            changes_summary: Summary of changes
            
        Returns:
            Updated Policy instance
            
        Raises:
            ValueError: If policy not found or validation fails
        """
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if policy.deleted_at:
            raise ValueError(f"Policy {policy_id} is deleted")
        
        # Validate YAML if provided
        if rules_yaml:
            validation_result = self.validator.validate(rules_yaml)
            if not validation_result.valid:
                raise ValueError(f"Invalid policy YAML: {', '.join(validation_result.errors)}")
            policy.rules_yaml = rules_yaml
        
        # Update fields
        if name:
            policy.name = name
        if description is not None:
            policy.description = description
        if category:
            policy.category = category
        
        # Increment version
        new_version = policy.version + 1
        policy.version = new_version
        policy.updated_at = datetime.utcnow()
        
        # Create new version record
        version = PolicyVersion(
            policy_id=policy.id,
            version=new_version,
            rules_yaml=policy.rules_yaml,
            changes_summary=changes_summary or f"Updated to version {new_version}",
            created_by=updated_by
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Updated policy {policy.id} to version {new_version}")
        return policy
    
    def delete_policy(self, policy_id: int, deleted_by: int = None) -> Policy:
        """
        Soft delete a policy.
        
        Args:
            policy_id: Policy ID
            deleted_by: User ID of deleter
            
        Returns:
            Deleted Policy instance
            
        Raises:
            ValueError: If policy not found
        """
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy.deleted_at = datetime.utcnow()
        policy.status = PolicyStatus.ARCHIVED.value
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Deleted policy {policy.id}: {policy.name}")
        return policy
    
    def get_policy(self, policy_id: int) -> Optional[Policy]:
        """Get policy by ID."""
        return self.db.query(Policy).filter(
            Policy.id == policy_id,
            Policy.deleted_at.is_(None)
        ).first()
    
    def list_policies(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Policy]:
        """
        List policies with filters.
        
        Args:
            category: Filter by category
            status: Filter by status
            created_by: Filter by creator
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Policy instances
        """
        query = self.db.query(Policy).filter(Policy.deleted_at.is_(None))
        
        if category:
            query = query.filter(Policy.category == category)
        if status:
            query = query.filter(Policy.status == status)
        if created_by:
            query = query.filter(Policy.created_by == created_by)
        
        return query.order_by(Policy.created_at.desc()).limit(limit).offset(offset).all()
    
    def get_policy_versions(self, policy_id: int) -> List[PolicyVersion]:
        """Get all versions of a policy."""
        return self.db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy_id
        ).order_by(PolicyVersion.version.desc()).all()
    
    def submit_for_approval(self, policy_id: int, submitted_by: int = None) -> Policy:
        """
        Submit policy for approval.
        
        Args:
            policy_id: Policy ID
            submitted_by: User ID of submitter
            
        Returns:
            Updated Policy instance
            
        Raises:
            ValueError: If policy not found or not in draft status
        """
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if policy.status != PolicyStatus.DRAFT.value:
            raise ValueError(f"Policy {policy_id} must be in draft status to submit for approval")
        
        policy.status = PolicyStatus.PENDING_APPROVAL.value
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Policy {policy_id} submitted for approval")
        return policy
    
    def approve_policy(
        self,
        policy_id: int,
        approved_by: int,
        approval_comment: Optional[str] = None
    ) -> Policy:
        """
        Approve a policy for activation.
        
        Args:
            policy_id: Policy ID
            approved_by: User ID of approver
            approval_comment: Optional approval comment
            
        Returns:
            Updated Policy instance
            
        Raises:
            ValueError: If policy not found or not pending approval
        """
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if policy.status != PolicyStatus.PENDING_APPROVAL.value:
            raise ValueError(f"Policy {policy_id} must be pending approval")
        
        # Create approval record
        approval = PolicyApproval(
            policy_id=policy.id,
            version=policy.version,
            approved_by=approved_by,
            approval_status="approved",
            approval_comment=approval_comment
        )
        self.db.add(approval)
        
        # Update policy
        policy.status = PolicyStatus.ACTIVE.value
        policy.approved_by = approved_by
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Policy {policy_id} approved by user {approved_by}")
        return policy
    
    def reject_policy(
        self,
        policy_id: int,
        rejected_by: int,
        rejection_comment: str
    ) -> Policy:
        """
        Reject a policy.
        
        Args:
            policy_id: Policy ID
            rejected_by: User ID of rejector
            rejection_comment: Rejection reason
            
        Returns:
            Updated Policy instance
            
        Raises:
            ValueError: If policy not found or not pending approval
        """
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if policy.status != PolicyStatus.PENDING_APPROVAL.value:
            raise ValueError(f"Policy {policy_id} must be pending approval")
        
        # Create rejection record
        approval = PolicyApproval(
            policy_id=policy.id,
            version=policy.version,
            approved_by=rejected_by,
            approval_status="rejected",
            approval_comment=rejection_comment
        )
        self.db.add(approval)
        
        # Revert to draft
        policy.status = PolicyStatus.DRAFT.value
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Policy {policy_id} rejected by user {rejected_by}")
        return policy
    
    def activate_policy(self, policy_id: int, version: Optional[int] = None) -> Policy:
        """
        Activate a policy version.
        
        Args:
            policy_id: Policy ID
            version: Optional version to activate (defaults to latest)
            
        Returns:
            Updated Policy instance
            
        Raises:
            ValueError: If policy not found or version not found
        """
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if version:
            # Activate specific version
            version_record = self.db.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.version == version
            ).first()
            
            if not version_record:
                raise ValueError(f"Version {version} not found for policy {policy_id}")
            
            # Update policy to use this version
            policy.rules_yaml = version_record.rules_yaml
            policy.version = version
        
        policy.status = PolicyStatus.ACTIVE.value
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Policy {policy_id} activated (version {policy.version})")
        return policy
