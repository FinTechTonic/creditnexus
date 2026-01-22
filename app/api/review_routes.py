"""API routes for document review workflows."""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User, WorkflowState
from app.auth.jwt_auth import require_auth
from app.services.review_service import ReviewService
from app.utils.audit import log_audit_action
from app.db.models import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


# Request/Response Models
class SubmitForReviewRequest(BaseModel):
    """Request model for submitting a document for review."""
    reviewers: Optional[List[int]] = Field(None, description="List of reviewer user IDs")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    priority: str = Field("normal", description="Priority level (normal, high, urgent)")


class AssignReviewerRequest(BaseModel):
    """Request model for assigning a reviewer."""
    reviewer_id: int = Field(..., description="User ID of reviewer")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")


class EditExtractedDataRequest(BaseModel):
    """Request model for editing extracted data."""
    edited_data: dict = Field(..., description="Edited extracted data (CDM format)")
    comment: Optional[str] = Field(None, description="Comment explaining the edit")


class AddCommentRequest(BaseModel):
    """Request model for adding a review comment."""
    comment_text: str = Field(..., description="Comment text")
    comment_type: str = Field("general", description="Type of comment (general, annotation, change_request)")
    version_id: Optional[int] = Field(None, description="Version ID to attach comment to")
    target_field: Optional[str] = Field(None, description="Field path for field-specific annotations")
    target_range: Optional[dict] = Field(None, description="Text selection range")
    parent_comment_id: Optional[int] = Field(None, description="Parent comment ID for threading")


class RequestChangesRequest(BaseModel):
    """Request model for requesting changes."""
    reason: str = Field(..., description="Reason for requesting changes")
    required_changes: Optional[List[str]] = Field(None, description="List of specific changes required")


class ApproveWithEditsRequest(BaseModel):
    """Request model for approving with edits."""
    edited_data: dict = Field(..., description="Edited extracted data (CDM format)")
    comment: Optional[str] = Field(None, description="Approval comment")


class UpdateAssignmentStatusRequest(BaseModel):
    """Request model for updating assignment status."""
    status: str = Field(..., description="New status (pending, in_progress, completed, cancelled)")
    review_notes: Optional[str] = Field(None, description="Review notes")


# Review Management Endpoints
@router.post("/documents/{document_id}/submit")
async def submit_for_review(
    document_id: int,
    request_body: SubmitForReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Submit a document for review.
    
    Transitions the workflow from Draft to Under Review and optionally assigns reviewers.
    """
    try:
        service = ReviewService(db)
        
        due_date = None
        if request_body.due_date:
            due_date = datetime.fromisoformat(request_body.due_date.replace('Z', '+00:00'))
        
        result = service.submit_for_review(
            document_id=document_id,
            user_id=current_user.id,
            reviewers=request_body.reviewers,
            due_date=due_date,
            priority=request_body.priority
        )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="workflow",
            target_id=result["workflow"]["id"],
            user_id=current_user.id,
            metadata={
                "document_id": document_id,
                "transition": "submit_for_review",
                "reviewers": request_body.reviewers or []
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": "Document submitted for review",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting document {document_id} for review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit for review: {str(e)}")


@router.post("/documents/{document_id}/assign")
async def assign_reviewer(
    document_id: int,
    request_body: AssignReviewerRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Assign a reviewer to a document."""
    try:
        service = ReviewService(db)
        
        due_date = None
        if request_body.due_date:
            due_date = datetime.fromisoformat(request_body.due_date.replace('Z', '+00:00'))
        
        assignment = service.assign_reviewer(
            document_id=document_id,
            reviewer_id=request_body.reviewer_id,
            assigned_by=current_user.id,
            due_date=due_date
        )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="review_assignment",
            target_id=assignment["id"],
            user_id=current_user.id,
            metadata={
                "document_id": document_id,
                "reviewer_id": request_body.reviewer_id
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": "Reviewer assigned",
            "assignment": assignment
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning reviewer to document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to assign reviewer: {str(e)}")


@router.get("/documents/{document_id}/assignments")
async def get_review_assignments(
    document_id: int,
    reviewer_id: Optional[int] = Query(None, description="Filter by reviewer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get review assignments for a document."""
    try:
        service = ReviewService(db)
        assignments = service.get_review_assignments(
            document_id=document_id,
            reviewer_id=reviewer_id,
            status=status
        )
        
        return {
            "status": "success",
            "assignments": assignments
        }
    except Exception as e:
        logger.error(f"Error getting assignments for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get assignments: {str(e)}")


@router.post("/documents/{document_id}/edit")
async def edit_extracted_data(
    document_id: int,
    request_body: EditExtractedDataRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Edit extracted data and create a new version."""
    try:
        service = ReviewService(db)
        result = service.edit_extracted_data(
            document_id=document_id,
            edited_data=request_body.edited_data,
            user_id=current_user.id,
            comment=request_body.comment
        )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="document",
            target_id=document_id,
            user_id=current_user.id,
            metadata={
                "version_id": result["version"]["id"],
                "version_number": result["version"]["version_number"],
                "action": "edit_extracted_data"
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": "Extracted data edited and new version created",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error editing extracted data for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to edit extracted data: {str(e)}")


@router.get("/documents/{document_id}/versions/{version_id_1}/diff/{version_id_2}")
async def get_diff(
    document_id: int,
    version_id_1: int,
    version_id_2: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get diff between two document versions."""
    try:
        service = ReviewService(db)
        diff_result = service.get_diff(
            document_id=document_id,
            version_id_1=version_id_1,
            version_id_2=version_id_2
        )
        
        return {
            "status": "success",
            **diff_result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting diff for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get diff: {str(e)}")


@router.post("/documents/{document_id}/approve")
async def approve_document(
    document_id: int,
    request_body: Optional[ApproveWithEditsRequest] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Approve a document, optionally with edits."""
    try:
        service = ReviewService(db)
        
        if request_body and request_body.edited_data:
            # Approve with edits
            result = service.approve_with_edits(
                document_id=document_id,
                edited_data=request_body.edited_data,
                user_id=current_user.id,
                comment=request_body.comment
            )
            message = "Document approved with edits"
        else:
            # Simple approval (use existing workflow endpoint logic)
            from app.api.routes import approve_document as approve_document_route
            return await approve_document_route(
                document_id=document_id,
                request=request,
                transition_request=None,
                db=db,
                current_user=current_user
            )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.APPROVE,
            target_type="workflow",
            target_id=result["workflow"]["id"],
            user_id=current_user.id,
            metadata={
                "document_id": document_id,
                "with_edits": True if request_body else False
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": message,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve document: {str(e)}")


@router.post("/documents/{document_id}/request-changes")
async def request_changes(
    document_id: int,
    request_body: RequestChangesRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Request changes to a document under review."""
    try:
        service = ReviewService(db)
        result = service.request_changes(
            document_id=document_id,
            user_id=current_user.id,
            reason=request_body.reason,
            required_changes=request_body.required_changes
        )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.REJECT,
            target_type="workflow",
            target_id=result["workflow"]["id"],
            user_id=current_user.id,
            metadata={
                "document_id": document_id,
                "reason": request_body.reason,
                "required_changes": request_body.required_changes or []
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": "Changes requested",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error requesting changes for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to request changes: {str(e)}")


# Comment Endpoints
@router.post("/documents/{document_id}/comments")
async def add_comment(
    document_id: int,
    request_body: AddCommentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Add a review comment."""
    try:
        service = ReviewService(db)
        comment = service.add_comment(
            document_id=document_id,
            user_id=current_user.id,
            comment_text=request_body.comment_text,
            comment_type=request_body.comment_type,
            version_id=request_body.version_id,
            target_field=request_body.target_field,
            target_range=request_body.target_range,
            parent_comment_id=request_body.parent_comment_id
        )
        
        return {
            "status": "success",
            "message": "Comment added",
            "comment": comment
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding comment to document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/documents/{document_id}/comments")
async def list_comments(
    document_id: int,
    version_id: Optional[int] = Query(None, description="Filter by version ID"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List review comments for a document."""
    try:
        service = ReviewService(db)
        comments = service.get_review_comments(
            document_id=document_id,
            version_id=version_id,
            resolved=resolved
        )
        
        return {
            "status": "success",
            "comments": comments
        }
    except Exception as e:
        logger.error(f"Error listing comments for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list comments: {str(e)}")


@router.put("/comments/{comment_id}/resolve")
async def resolve_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Resolve a review comment."""
    try:
        service = ReviewService(db)
        comment = service.resolve_comment(comment_id, current_user.id)
        
        return {
            "status": "success",
            "message": "Comment resolved",
            "comment": comment
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving comment {comment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resolve comment: {str(e)}")


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Delete a review comment."""
    try:
        from app.db.models import ReviewComment
        
        comment = db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check permissions (only comment author or admin can delete)
        if comment.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You don't have permission to delete this comment")
        
        db.delete(comment)
        db.commit()
        
        return {
            "status": "success",
            "message": "Comment deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")


# Version Endpoints
@router.get("/documents/{document_id}/versions")
async def list_versions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List all versions of a document."""
    try:
        from app.db.models import DocumentVersion
        
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).all()
        
        return {
            "status": "success",
            "versions": [v.to_dict() for v in versions]
        }
    except Exception as e:
        logger.error(f"Error listing versions for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {str(e)}")


@router.get("/documents/{document_id}/versions/{version_id}")
async def get_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get a specific version of a document."""
    try:
        from app.db.models import DocumentVersion
        
        version = db.query(DocumentVersion).filter(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id
        ).first()
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        return {
            "status": "success",
            "version": version.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version {version_id} for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get version: {str(e)}")


@router.put("/assignments/{assignment_id}/status")
async def update_assignment_status(
    assignment_id: int,
    request_body: UpdateAssignmentStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Update review assignment status."""
    try:
        service = ReviewService(db)
        assignment = service.update_assignment_status(
            assignment_id=assignment_id,
            status=request_body.status,
            review_notes=request_body.review_notes
        )
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="review_assignment",
            target_id=assignment_id,
            user_id=current_user.id,
            metadata={
                "status": request_body.status,
                "document_id": assignment["document_id"]
            },
            request=request
        )
        
        return {
            "status": "success",
            "message": "Assignment status updated",
            "assignment": assignment
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating assignment {assignment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update assignment: {str(e)}")
