"""API routes for workflow delegation via encrypted links."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.db.models import User, WorkflowDelegation, WorkflowDelegationState, WorkflowDelegationStatus
from app.services.workflow_delegation_service import WorkflowDelegationService
from app.core.workflow_types import WorkflowType
from app.auth.jwt_auth import require_auth as require_jwt_auth
from app.utils.audit import log_audit_action, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflow-delegation"])


# Request/Response Models
class DelegateWorkflowRequest(BaseModel):
    """Request model for delegating a workflow."""
    workflow_type: str = Field(..., description="Workflow type (verification, notarization, document_review, etc.)")
    deal_id: Optional[int] = Field(None, description="Deal ID (required for verification, notarization, deal flows)")
    document_id: Optional[int] = Field(None, description="Document ID (required for document_review)")
    receiver_email: Optional[str] = Field(None, description="Receiver email address")
    receiver_user_id: Optional[int] = Field(None, description="Receiver user ID")
    workflow_metadata: Optional[Dict[str, Any]] = Field(None, description="Workflow-specific metadata")
    file_categories: Optional[List[str]] = Field(None, description="File categories to include")
    file_document_ids: Optional[List[int]] = Field(None, description="Specific document IDs to include")
    expires_in_hours: Optional[int] = Field(None, description="Expiration time in hours")
    callback_url: Optional[str] = Field(None, description="Callback URL for state synchronization")
    
    # Workflow-specific fields
    required_signers: Optional[List[str]] = Field(None, description="Required signers (for notarization)")
    review_type: Optional[str] = Field(None, description="Review type (for document_review)")
    flow_type: Optional[str] = Field(None, description="Flow type: approval, review, closure (for deal flows)")
    custom_workflow_type: Optional[str] = Field(None, description="Custom workflow type identifier")


class ProcessWorkflowLinkRequest(BaseModel):
    """Request model for processing a workflow link."""
    encrypted_payload: str = Field(..., description="Encrypted workflow link payload")


class UpdateWorkflowStateRequest(BaseModel):
    """Request model for updating workflow state."""
    state: str = Field(..., description="New workflow state")
    metadata: Optional[Dict[str, Any]] = Field(None, description="State-specific metadata")


class WorkflowDelegationResponse(BaseModel):
    """Response model for workflow delegation."""
    workflow_id: str
    workflow_type: str
    link: str
    encrypted_payload: str
    files_included: int
    expires_at: Optional[str] = None


# Endpoints
@router.post("/delegate", response_model=WorkflowDelegationResponse)
async def delegate_workflow(
    request: DelegateWorkflowRequest,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Delegate a workflow to a remote user via encrypted link.
    
    Supports multiple workflow types:
    - verification: Deal verification workflow
    - notarization: Document notarization workflow
    - document_review: Document review workflow
    - deal_approval: Deal approval workflow
    - deal_review: Deal review workflow
    - custom: Custom workflow types
    
    Args:
        request: Delegation request with workflow type and parameters
        current_user: Authenticated user (sender)
        db: Database session
        http_request: HTTP request object for audit logging
        
    Returns:
        WorkflowDelegationResponse with link and metadata
        
    Raises:
        HTTPException: 400 if request is invalid, 404 if deal/document not found
    """
    try:
        service = WorkflowDelegationService(db)
        
        # Route to appropriate delegation method based on workflow type
        workflow_type = request.workflow_type.lower()
        
        if workflow_type == "verification":
            if not request.deal_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="deal_id is required for verification workflow"
                )
            
            result = service.delegate_verification_workflow(
                deal_id=request.deal_id,
                sender_user_id=current_user.id,
                receiver_email=request.receiver_email,
                receiver_user_id=request.receiver_user_id,
                workflow_metadata=request.workflow_metadata,
                file_categories=request.file_categories,
                file_document_ids=request.file_document_ids,
                expires_in_hours=request.expires_in_hours,
            )
            
        elif workflow_type == "notarization":
            if not request.deal_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="deal_id is required for notarization workflow"
                )
            if not request.required_signers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="required_signers is required for notarization workflow"
                )
            
            result = service.delegate_notarization_workflow(
                deal_id=request.deal_id,
                sender_user_id=current_user.id,
                required_signers=request.required_signers,
                receiver_email=request.receiver_email,
                receiver_user_id=request.receiver_user_id,
                workflow_metadata=request.workflow_metadata,
                expires_in_hours=request.expires_in_hours,
            )
            
        elif workflow_type == "document_review":
            if not request.document_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="document_id is required for document_review workflow"
                )
            
            result = service.delegate_document_workflow(
                document_id=request.document_id,
                sender_user_id=current_user.id,
                review_type=request.review_type or "general",
                receiver_email=request.receiver_email,
                receiver_user_id=request.receiver_user_id,
                workflow_metadata=request.workflow_metadata,
                expires_in_hours=request.expires_in_hours,
            )
            
        elif workflow_type in ["deal_approval", "deal_review"]:
            if not request.deal_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="deal_id is required for deal flow workflows"
                )
            
            flow_type = "approval" if workflow_type == "deal_approval" else "review"
            if request.flow_type:
                flow_type = request.flow_type
            
            result = service.delegate_deal_flow(
                deal_id=request.deal_id,
                sender_user_id=current_user.id,
                flow_type=flow_type,
                receiver_email=request.receiver_email,
                receiver_user_id=request.receiver_user_id,
                workflow_metadata=request.workflow_metadata,
                file_categories=request.file_categories,
                expires_in_hours=request.expires_in_hours,
            )
            
        elif workflow_type == "custom":
            if not request.custom_workflow_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="custom_workflow_type is required for custom workflows"
                )
            if not request.workflow_metadata:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="workflow_metadata is required for custom workflows"
                )
            
            result = service.delegate_custom_workflow(
                custom_workflow_type=request.custom_workflow_type,
                sender_user_id=current_user.id,
                workflow_metadata=request.workflow_metadata,
                deal_id=request.deal_id,
                document_id=request.document_id,
                receiver_email=request.receiver_email,
                receiver_user_id=request.receiver_user_id,
                expires_in_hours=request.expires_in_hours or 72,
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown workflow type: {workflow_type}"
            )
        
        # Create workflow delegation record
        delegation = WorkflowDelegation(
            workflow_id=result["workflow_id"],
            workflow_type=workflow_type,
            deal_id=request.deal_id,
            document_id=request.document_id,
            sender_user_id=current_user.id,
            receiver_user_id=request.receiver_user_id,
            receiver_email=request.receiver_email,
            link_payload=result["encrypted_payload"],
            workflow_metadata=request.workflow_metadata,
            status=WorkflowDelegationStatus.PENDING.value,
            expires_at=datetime.fromisoformat(result.get("expires_at")) if result.get("expires_at") else datetime.utcnow() + timedelta(hours=72),
            callback_url=request.callback_url,
        )
        db.add(delegation)
        db.commit()
        db.refresh(delegation)
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="workflow_delegation",
            target_id=delegation.id,
            user_id=current_user.id,
            metadata={
                "workflow_type": workflow_type,
                "workflow_id": result["workflow_id"],
                "deal_id": request.deal_id,
                "document_id": request.document_id,
            },
            request=http_request,
        )
        db.commit()
        
        return WorkflowDelegationResponse(
            workflow_id=result["workflow_id"],
            workflow_type=workflow_type,
            link=result["link"],
            encrypted_payload=result["encrypted_payload"],
            files_included=result.get("files_included", 0),
            expires_at=result.get("expires_at"),
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delegate workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delegate workflow: {str(e)}"
        )


@router.post("/process", response_model=Dict[str, Any])
async def process_workflow_link(
    request: ProcessWorkflowLinkRequest,
    current_user: Optional[User] = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
):
    """Process a workflow link and create local workflow instance.
    
    Parses the encrypted link payload, validates it, and returns the workflow data.
    Optionally updates whitelist configuration if provided in the link.
    
    Args:
        request: Process request with encrypted payload
        current_user: Authenticated user (optional, for whitelist updates)
        db: Database session
        
    Returns:
        Dictionary with processed workflow data
        
    Raises:
        HTTPException: 400 if link is invalid or expired
    """
    try:
        service = WorkflowDelegationService(db)
        
        result = service.process_workflow_link(
            encrypted_payload=request.encrypted_payload,
            receiver_user_id=current_user.id if current_user else None,
        )
        
        return {
            "status": "success",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to process workflow link: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process workflow link: {str(e)}"
        )


@router.post("/{workflow_id}/state", response_model=Dict[str, Any])
async def update_workflow_state(
    workflow_id: str,
    request: UpdateWorkflowStateRequest,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Update workflow state and sync to sender if callback URL provided.
    
    Args:
        workflow_id: Workflow identifier
        request: State update request
        current_user: Authenticated user
        db: Database session
        http_request: HTTP request object for audit logging
        
    Returns:
        Dictionary with update result
        
    Raises:
        HTTPException: 404 if workflow not found, 400 if state transition invalid
    """
    try:
        # Get workflow delegation
        delegation = (
            db.query(WorkflowDelegation)
            .filter(WorkflowDelegation.workflow_id == workflow_id)
            .first()
        )
        
        if not delegation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Update state
        old_state = delegation.status
        delegation.status = request.state
        delegation.updated_at = datetime.utcnow()
        
        if request.state == WorkflowDelegationStatus.COMPLETED.value:
            delegation.completed_at = datetime.utcnow()
        
        # Create state history entry
        state_entry = WorkflowDelegationState(
            delegation_id=delegation.id,
            state=request.state,
            state_metadata=request.metadata,  # Use state_metadata column name
            timestamp=datetime.utcnow(),
        )
        db.add(state_entry)
        db.commit()
        
        # Sync state to sender if callback URL provided
        if delegation.callback_url:
            service = WorkflowDelegationService(db)
            sync_success = service.sync_workflow_state(
                workflow_id=workflow_id,
                workflow_type=delegation.workflow_type,
                state=request.state,
                metadata=request.metadata,
                callback_url=delegation.callback_url,
            )
            
            if sync_success:
                delegation.state_synced_at = datetime.utcnow()
                db.commit()
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="workflow_delegation",
            target_id=delegation.id,
            user_id=current_user.id,
            metadata={
                "workflow_id": workflow_id,
                "old_state": old_state,
                "new_state": request.state,
                "metadata": request.metadata,
            },
            request=http_request,
        )
        db.commit()
        
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "state": request.state,
            "state_synced": delegation.state_synced_at is not None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow state: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_delegation(
    workflow_id: str,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
):
    """Get workflow delegation details.
    
    Args:
        workflow_id: Workflow identifier
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dictionary with workflow delegation details
        
    Raises:
        HTTPException: 404 if workflow not found
    """
    delegation = (
        db.query(WorkflowDelegation)
        .filter(WorkflowDelegation.workflow_id == workflow_id)
        .first()
    )
    
    if not delegation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Check permissions (sender or receiver can view)
    if delegation.sender_user_id != current_user.id and delegation.receiver_user_id != current_user.id:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this workflow"
            )
    
    # Get state history
    state_history = (
        db.query(WorkflowDelegationState)
        .filter(WorkflowDelegationState.delegation_id == delegation.id)
        .order_by(WorkflowDelegationState.timestamp.desc())
        .all()
    )
    
    return {
        "status": "success",
        "delegation": delegation.to_dict(),
        "state_history": [state.to_dict() for state in state_history],
    }


@router.get("", response_model=Dict[str, Any])
async def list_workflow_delegations(
    workflow_type: Optional[str] = None,
    deal_id: Optional[int] = None,
    document_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
):
    """List workflow delegations with filters.
    
    Args:
        workflow_type: Filter by workflow type
        deal_id: Filter by deal ID
        document_id: Filter by document ID
        status: Filter by status
        limit: Maximum number of results
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dictionary with list of workflow delegations
    """
    query = db.query(WorkflowDelegation)
    
    # Filter by user (non-admins can only see their own delegations)
    if current_user.role != "admin":
        query = query.filter(
            (WorkflowDelegation.sender_user_id == current_user.id) |
            (WorkflowDelegation.receiver_user_id == current_user.id)
        )
    
    if workflow_type:
        query = query.filter(WorkflowDelegation.workflow_type == workflow_type)
    
    if deal_id:
        query = query.filter(WorkflowDelegation.deal_id == deal_id)
    
    if document_id:
        query = query.filter(WorkflowDelegation.document_id == document_id)
    
    if status:
        query = query.filter(WorkflowDelegation.status == status)
    
    total = query.count()
    
    delegations = (
        query.order_by(WorkflowDelegation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return {
        "status": "success",
        "delegations": [d.to_dict() for d in delegations],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{workflow_id}/complete", response_model=Dict[str, Any])
async def complete_workflow(
    workflow_id: str,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Mark workflow as completed and trigger state sync.
    
    Args:
        workflow_id: Workflow identifier
        current_user: Authenticated user
        db: Database session
        http_request: HTTP request object for audit logging
        
    Returns:
        Dictionary with completion result
        
    Raises:
        HTTPException: 404 if workflow not found
    """
    return await update_workflow_state(
        workflow_id=workflow_id,
        request=UpdateWorkflowStateRequest(
            state=WorkflowDelegationStatus.COMPLETED.value,
            metadata={"completed_by": current_user.id, "completed_at": datetime.utcnow().isoformat()}
        ),
        current_user=current_user,
        db=db,
        http_request=http_request,
    )
