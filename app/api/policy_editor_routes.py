"""
Policy Editor API Routes for CreditNexus.

Provides endpoints for policy management, validation, testing, and approval workflows.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.dependencies import get_current_user
from app.auth.jwt_auth import require_auth
from app.db.models import User, Policy, PolicyVersion, PolicyApproval, PolicyStatus
from app.services.policy_editor_service import PolicyEditorService
from app.services.policy_approval_service import PolicyApprovalService
from app.services.policy_validator import PolicyValidator
from app.services.policy_tester import PolicyTester
from app.services.policy_engine_factory import create_policy_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/policies", tags=["policies"])


# Request/Response Models

class CreatePolicyRequest(BaseModel):
    """Request model for creating a policy."""
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    rules_yaml: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class UpdatePolicyRequest(BaseModel):
    """Request model for updating a policy."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rules_yaml: Optional[str] = Field(None, min_length=1)
    changes_summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TestPolicyRequest(BaseModel):
    """Request model for testing a policy."""
    test_transactions: List[Dict[str, Any]] = Field(..., min_items=1)
    # Each test transaction should have: transaction, expected_decision, test_name (optional)


class ApprovePolicyRequest(BaseModel):
    """Request model for approving a policy."""
    approval_comment: Optional[str] = None


class RejectPolicyRequest(BaseModel):
    """Request model for rejecting a policy."""
    rejection_comment: str = Field(..., min_length=1)


class ValidatePolicyRequest(BaseModel):
    """Request model for validating policy YAML."""
    rules_yaml: str = Field(..., min_length=1)


# API Endpoints

@router.get("", response_model=Dict[str, Any])
async def list_policies(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    created_by: Optional[int] = Query(None, description="Filter by creator ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    List all policies with optional filters.
    
    Args:
        category: Filter by category
        status: Filter by status
        created_by: Filter by creator ID
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of policies with metadata
    """
    try:
        service = PolicyEditorService(db)
        policies = service.list_policies(
            category=category,
            status=status,
            created_by=created_by,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "policies": [policy.to_dict() for policy in policies],
            "count": len(policies),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error listing policies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing policies: {str(e)}")


@router.get("/{policy_id}", response_model=Dict[str, Any])
async def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get policy details by ID.
    
    Args:
        policy_id: Policy ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Policy details
    """
    try:
        service = PolicyEditorService(db)
        policy = service.get_policy(policy_id)
        
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        
        return {
            "status": "success",
            "policy": policy.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting policy: {str(e)}")


@router.post("", response_model=Dict[str, Any])
async def create_policy(
    request: CreatePolicyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Create a new policy.
    
    Args:
        request: CreatePolicyRequest with policy data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created policy details
    """
    try:
        service = PolicyEditorService(db)
        policy = service.create_policy(
            name=request.name,
            category=request.category,
            rules_yaml=request.rules_yaml,
            description=request.description,
            created_by=current_user.id,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "policy": policy.to_dict()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating policy: {str(e)}")


@router.put("/{policy_id}", response_model=Dict[str, Any])
async def update_policy(
    policy_id: int,
    request: UpdatePolicyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Update an existing policy (creates new version).
    
    Args:
        policy_id: Policy ID
        request: UpdatePolicyRequest with updated data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated policy details
    """
    try:
        service = PolicyEditorService(db)
        policy = service.update_policy(
            policy_id=policy_id,
            rules_yaml=request.rules_yaml,
            name=request.name,
            description=request.description,
            category=request.category,
            updated_by=current_user.id,
            changes_summary=request.changes_summary
        )
        
        return {
            "status": "success",
            "policy": policy.to_dict()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating policy: {str(e)}")


@router.delete("/{policy_id}", response_model=Dict[str, Any])
async def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Soft delete a policy.
    
    Args:
        policy_id: Policy ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Deletion confirmation
    """
    try:
        service = PolicyEditorService(db)
        policy = service.delete_policy(policy_id, deleted_by=current_user.id)
        
        return {
            "status": "success",
            "message": f"Policy {policy_id} deleted",
            "policy": policy.to_dict()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting policy: {str(e)}")


@router.post("/{policy_id}/validate", response_model=Dict[str, Any])
async def validate_policy(
    policy_id: int,
    request: Optional[ValidatePolicyRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Validate policy YAML.
    
    Args:
        policy_id: Policy ID
        request: Optional ValidatePolicyRequest with rules_yaml (uses policy's YAML if not provided)
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Validation results
    """
    try:
        validator = PolicyValidator()
        
        # Get YAML to validate
        if request and request.rules_yaml:
            yaml_to_validate = request.rules_yaml
        else:
            service = PolicyEditorService(db)
            policy = service.get_policy(policy_id)
            if not policy:
                raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
            yaml_to_validate = policy.rules_yaml
        
        # Validate
        result = validator.validate(yaml_to_validate)
        
        return {
            "status": "success",
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validating policy: {str(e)}")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_policy_standalone(
    request: ValidatePolicyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Validate policy YAML without requiring a policy ID.
    
    Args:
        request: ValidatePolicyRequest with rules_yaml
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Validation results
    """
    try:
        validator = PolicyValidator()
        
        # Validate
        result = validator.validate(request.rules_yaml)
        
        return {
            "status": "success",
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error validating policy: {str(e)}")


@router.post("/{policy_id}/test", response_model=Dict[str, Any])
async def test_policy(
    policy_id: int,
    request: TestPolicyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Test policy against sample transactions.
    
    Args:
        policy_id: Policy ID
        request: TestPolicyRequest with test transactions
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Test results
    """
    try:
        service = PolicyEditorService(db)
        policy = service.get_policy(policy_id)
        
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        
        # Prepare test transactions
        test_transactions = []
        for test_case in request.test_transactions:
            transaction = test_case.get("transaction", {})
            expected_decision = test_case.get("expected_decision", "ALLOW")
            test_name = test_case.get("test_name", f"Test {len(test_transactions) + 1}")
            
            test_transactions.append({
                "transaction": transaction,
                "expected_decision": expected_decision,
                "test_name": test_name
            })
        
        # Test policy
        policy_engine = create_policy_engine(vendor="default")
        tester = PolicyTester()
        result = tester.test_policy(
            rules_yaml=policy.rules_yaml,
            test_transactions=test_transactions,
            policy_engine=policy_engine
        )
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "total_tests": result.total_tests,
            "passed": result.passed,
            "failed": result.failed,
            "summary": result.summary,
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "expected_decision": r.expected_decision,
                    "actual_decision": r.actual_decision,
                    "matched_rules": r.matched_rules,
                    "error": r.error
                }
                for r in result.results
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing policy: {str(e)}")


@router.post("/{policy_id}/activate", response_model=Dict[str, Any])
async def activate_policy(
    policy_id: int,
    version: Optional[int] = Query(None, description="Version to activate (defaults to latest)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Activate a policy version.
    
    Args:
        policy_id: Policy ID
        version: Optional version to activate
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Activated policy details
    """
    try:
        service = PolicyEditorService(db)
        policy = service.activate_policy(policy_id, version=version)
        
        return {
            "status": "success",
            "message": f"Policy {policy_id} activated (version {policy.version})",
            "policy": policy.to_dict()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error activating policy: {str(e)}")


@router.get("/{policy_id}/versions", response_model=Dict[str, Any])
async def get_policy_versions(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get policy version history.
    
    Args:
        policy_id: Policy ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of policy versions
    """
    try:
        service = PolicyEditorService(db)
        policy = service.get_policy(policy_id)
        
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        
        versions = service.get_policy_versions(policy_id)
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "current_version": policy.version,
            "versions": [version.to_dict() for version in versions]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting policy versions: {str(e)}")


@router.post("/{policy_id}/submit", response_model=Dict[str, Any])
async def submit_policy_for_approval(
    policy_id: int,
    notify_approvers: bool = Query(True, description="Send email notifications to approvers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Submit policy for approval.
    
    Args:
        policy_id: Policy ID
        notify_approvers: Whether to send email notifications
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated policy details and notification status
    """
    try:
        approval_service = PolicyApprovalService(db)
        result = approval_service.submit_for_approval(
            policy_id=policy_id,
            submitted_by=current_user.id,
            notify_approvers=notify_approvers
        )
        
        service = PolicyEditorService(db)
        policy = service.get_policy(policy_id)
        
        return {
            "status": "success",
            "message": f"Policy {policy_id} submitted for approval",
            "policy": policy.to_dict() if policy else None,
            "approvers_notified": result.get("approvers_notified", 0),
            "notifications": result.get("notifications", [])
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting policy for approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error submitting policy for approval: {str(e)}")


@router.post("/{policy_id}/approve", response_model=Dict[str, Any])
async def approve_policy(
    policy_id: int,
    request: ApprovePolicyRequest,
    notify_submitter: bool = Query(True, description="Send email notification to submitter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Approve a policy for activation.
    
    Args:
        policy_id: Policy ID
        request: ApprovePolicyRequest with approval comment
        notify_submitter: Whether to notify the submitter
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Approved policy details
    """
    try:
        approval_service = PolicyApprovalService(db)
        
        # Check if user can approve
        policy = approval_service.editor_service.get_policy(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        
        if not approval_service.can_user_approve(current_user.id, policy.category):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to approve policies"
            )
        
        result = approval_service.approve_policy(
            policy_id=policy_id,
            approved_by=current_user.id,
            approval_comment=request.approval_comment,
            notify_submitter=notify_submitter
        )
        
        policy = approval_service.editor_service.get_policy(policy_id)
        
        return {
            "status": "success",
            "message": f"Policy {policy_id} approved",
            "policy": policy.to_dict() if policy else None,
            "notification_sent": result.get("notification_sent", False)
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error approving policy: {str(e)}")


@router.post("/{policy_id}/reject", response_model=Dict[str, Any])
async def reject_policy(
    policy_id: int,
    request: RejectPolicyRequest,
    notify_submitter: bool = Query(True, description="Send email notification to submitter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Reject a policy.
    
    Args:
        policy_id: Policy ID
        request: RejectPolicyRequest with rejection comment
        notify_submitter: Whether to notify the submitter
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Rejected policy details
    """
    try:
        approval_service = PolicyApprovalService(db)
        
        # Check if user can approve/reject
        policy = approval_service.editor_service.get_policy(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
        
        if not approval_service.can_user_reject(current_user.id, policy.category):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to reject policies"
            )
        
        result = approval_service.reject_policy(
            policy_id=policy_id,
            rejected_by=current_user.id,
            rejection_comment=request.rejection_comment,
            notify_submitter=notify_submitter
        )
        
        policy = approval_service.editor_service.get_policy(policy_id)
        
        return {
            "status": "success",
            "message": f"Policy {policy_id} rejected",
            "policy": policy.to_dict() if policy else None,
            "notification_sent": result.get("notification_sent", False)
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error rejecting policy: {str(e)}")


@router.get("/pending-approval", response_model=Dict[str, Any])
async def get_pending_approvals(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get list of policies pending approval.
    
    Args:
        category: Optional category filter
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of policies pending approval
    """
    try:
        approval_service = PolicyApprovalService(db)
        
        # Check permission
        if not approval_service.can_user_view_pending(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view pending approvals"
            )
        
        policies = approval_service.get_pending_approvals(
            category=category,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "policies": [policy.to_dict() for policy in policies],
            "count": len(policies),
            "limit": limit,
            "offset": offset
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting pending approvals: {str(e)}")


@router.get("/{policy_id}/approval-history", response_model=Dict[str, Any])
async def get_approval_history(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get approval history for a policy.
    
    Args:
        policy_id: Policy ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Approval history
    """
    try:
        approval_service = PolicyApprovalService(db)
        history = approval_service.get_approval_history(policy_id)
        
        return {
            "status": "success",
            "policy_id": policy_id,
            "approval_history": history
        }
    
    except Exception as e:
        logger.error(f"Error getting approval history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting approval history: {str(e)}")
