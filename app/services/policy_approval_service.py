"""
Policy Approval Service for CreditNexus.

Handles policy approval workflow including state machine transitions,
approval routing, email notifications, and approval history.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Policy, PolicyApproval, PolicyStatus, User
from app.services.policy_editor_service import PolicyEditorService
from app.core.permissions import (
    PERMISSION_POLICY_APPROVE,
    PERMISSION_POLICY_REJECT,
    PERMISSION_POLICY_VIEW_PENDING,
    has_permission
)

logger = logging.getLogger(__name__)


class PolicyApprovalService:
    """Service for managing policy approval workflows."""
    
    def __init__(self, db: Session):
        """
        Initialize policy approval service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.editor_service = PolicyEditorService(db)
    
    def submit_for_approval(
        self,
        policy_id: int,
        submitted_by: int,
        notify_approvers: bool = True
    ) -> Dict[str, Any]:
        """
        Submit policy for approval and notify approvers.
        
        Args:
            policy_id: Policy ID
            submitted_by: User ID of submitter
            notify_approvers: Whether to send email notifications
            
        Returns:
            Dictionary with submission result and notification status
        """
        policy = self.editor_service.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")
        
        if policy.status != PolicyStatus.DRAFT.value:
            raise ValueError(f"Policy {policy_id} must be in draft status to submit for approval")
        
        # Update policy status
        policy.status = PolicyStatus.PENDING_APPROVAL.value
        self.db.commit()
        self.db.refresh(policy)
        
        # Get approvers for this policy category
        approvers = self.get_approvers_for_category(policy.category)
        
        # Send notifications
        notification_results = []
        if notify_approvers and approvers:
            for approver in approvers:
                try:
                    self.send_approval_notification(
                        policy=policy,
                        approver=approver,
                        submitter_id=submitted_by
                    )
                    notification_results.append({
                        "approver_id": approver.id,
                        "email": approver.email,
                        "status": "sent"
                    })
                except Exception as e:
                    logger.error(f"Failed to send notification to {approver.email}: {e}")
                    notification_results.append({
                        "approver_id": approver.id,
                        "email": approver.email,
                        "status": "failed",
                        "error": str(e)
                    })
        
        logger.info(f"Policy {policy_id} submitted for approval by user {submitted_by}")
        
        return {
            "policy_id": policy_id,
            "status": "submitted",
            "approvers_notified": len([r for r in notification_results if r["status"] == "sent"]),
            "notifications": notification_results
        }
    
    def get_approvers_for_category(self, category: str) -> List[User]:
        """
        Get list of users who can approve policies in a given category.
        
        Args:
            category: Policy category
            
        Returns:
            List of User objects who can approve
        """
        # For now, return all admins
        # In the future, this could be category-specific or role-based
        approvers = self.db.query(User).filter(
            User.role == "admin",
            User.is_active == True
        ).all()
        
        return approvers
    
    def send_approval_notification(
        self,
        policy: Policy,
        approver: User,
        submitter_id: int
    ) -> None:
        """
        Send email notification to approver about pending policy.
        
        Args:
            policy: Policy object
            approver: User who should approve
            submitter_id: User ID of submitter
        """
        # Get submitter info
        submitter = self.db.query(User).filter(User.id == submitter_id).first()
        submitter_name = submitter.display_name if submitter else f"User {submitter_id}"
        
        # For now, just log the notification
        # In production, integrate with email service (SendGrid, AWS SES, etc.)
        logger.info(
            f"Approval notification for policy '{policy.name}' (ID: {policy.id}) "
            f"sent to {approver.email} (User ID: {approver.id})"
        )
        
        # TODO: Implement actual email sending
        # Example:
        # email_service.send_email(
        #     to=approver.email,
        #     subject=f"Policy Approval Required: {policy.name}",
        #     body=f"Policy '{policy.name}' requires your approval...",
        #     html_body=render_approval_email_template(policy, submitter_name)
        # )
    
    def approve_policy(
        self,
        policy_id: int,
        approved_by: int,
        approval_comment: Optional[str] = None,
        notify_submitter: bool = True
    ) -> Dict[str, Any]:
        """
        Approve a policy and notify submitter.
        
        Args:
            policy_id: Policy ID
            approved_by: User ID of approver
            approval_comment: Optional approval comment
            notify_submitter: Whether to notify the submitter
            
        Returns:
            Dictionary with approval result
        """
        policy = self.editor_service.approve_policy(
            policy_id=policy_id,
            approved_by=approved_by,
            approval_comment=approval_comment
        )
        
        # Notify submitter
        notification_sent = False
        if notify_submitter and policy.created_by:
            try:
                submitter = self.db.query(User).filter(User.id == policy.created_by).first()
                if submitter:
                    self.send_approval_result_notification(
                        policy=policy,
                        submitter=submitter,
                        approved=True,
                        approver_id=approved_by
                    )
                    notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
        
        return {
            "policy_id": policy_id,
            "status": "approved",
            "notification_sent": notification_sent
        }
    
    def reject_policy(
        self,
        policy_id: int,
        rejected_by: int,
        rejection_comment: str,
        notify_submitter: bool = True
    ) -> Dict[str, Any]:
        """
        Reject a policy and notify submitter.
        
        Args:
            policy_id: Policy ID
            rejected_by: User ID of rejector
            rejection_comment: Rejection reason
            notify_submitter: Whether to notify the submitter
            
        Returns:
            Dictionary with rejection result
        """
        policy = self.editor_service.reject_policy(
            policy_id=policy_id,
            rejected_by=rejected_by,
            rejection_comment=rejection_comment
        )
        
        # Notify submitter
        notification_sent = False
        if notify_submitter and policy.created_by:
            try:
                submitter = self.db.query(User).filter(User.id == policy.created_by).first()
                if submitter:
                    self.send_approval_result_notification(
                        policy=policy,
                        submitter=submitter,
                        approved=False,
                        approver_id=rejected_by,
                        comment=rejection_comment
                    )
                    notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}")
        
        return {
            "policy_id": policy_id,
            "status": "rejected",
            "notification_sent": notification_sent
        }
    
    def send_approval_result_notification(
        self,
        policy: Policy,
        submitter: User,
        approved: bool,
        approver_id: int,
        comment: Optional[str] = None
    ) -> None:
        """
        Send email notification to submitter about approval result.
        
        Args:
            policy: Policy object
            submitter: User who submitted the policy
            approved: Whether policy was approved
            approver_id: User ID of approver
            comment: Optional comment from approver
        """
        approver = self.db.query(User).filter(User.id == approver_id).first()
        approver_name = approver.display_name if approver else f"User {approver_id}"
        
        # For now, just log the notification
        logger.info(
            f"Approval result notification for policy '{policy.name}' (ID: {policy.id}) "
            f"sent to {submitter.email} (User ID: {submitter.id}). "
            f"Status: {'APPROVED' if approved else 'REJECTED'} by {approver_name}"
        )
        
        # TODO: Implement actual email sending
        # Example:
        # email_service.send_email(
        #     to=submitter.email,
        #     subject=f"Policy {'Approved' if approved else 'Rejected'}: {policy.name}",
        #     body=f"Your policy '{policy.name}' has been {'approved' if approved else 'rejected'}...",
        #     html_body=render_approval_result_template(policy, approved, approver_name, comment)
        # )
    
    def get_approval_history(self, policy_id: int) -> List[Dict[str, Any]]:
        """
        Get approval history for a policy.
        
        Args:
            policy_id: Policy ID
            
        Returns:
            List of approval records
        """
        approvals = self.db.query(PolicyApproval).filter(
            PolicyApproval.policy_id == policy_id
        ).order_by(PolicyApproval.approved_at.desc()).all()
        
        return [approval.to_dict() for approval in approvals]
    
    def get_pending_approvals(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Policy]:
        """
        Get list of policies pending approval.
        
        Args:
            category: Optional category filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Policy objects
        """
        query = self.db.query(Policy).filter(
            Policy.status == PolicyStatus.PENDING_APPROVAL.value,
            Policy.deleted_at.is_(None)
        )
        
        if category:
            query = query.filter(Policy.category == category)
        
        return query.order_by(Policy.created_at.desc()).limit(limit).offset(offset).all()
    
    def can_user_approve(self, user_id: int, policy_category: str) -> bool:
        """
        Check if a user can approve policies in a given category.
        
        Uses permission system to check if user has approval permissions.
        
        Args:
            user_id: User ID
            policy_category: Policy category (for future category-specific permissions)
            
        Returns:
            True if user can approve
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return False
        
        # Check permission using permission system
        return has_permission(user, PERMISSION_POLICY_APPROVE)
    
    def can_user_reject(self, user_id: int, policy_category: str) -> bool:
        """
        Check if a user can reject policies in a given category.
        
        Uses permission system to check if user has rejection permissions.
        
        Args:
            user_id: User ID
            policy_category: Policy category (for future category-specific permissions)
            
        Returns:
            True if user can reject
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return False
        
        # Check permission using permission system
        return has_permission(user, PERMISSION_POLICY_REJECT)
    
    def can_user_view_pending(self, user_id: int) -> bool:
        """
        Check if a user can view pending approvals.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user can view pending approvals
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return False
        
        # Check permission using permission system
        return has_permission(user, PERMISSION_POLICY_VIEW_PENDING)
