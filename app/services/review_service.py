"""Service for managing document review workflows."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import (
    Document, DocumentVersion, Workflow, WorkflowState,
    ReviewComment, CommentType, ReviewAssignment, ReviewAssignmentStatus,
    User, AuditAction
)
from app.utils.audit import log_audit_action
from app.utils.diff_utils import generate_json_diff, format_diff_for_display

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing document review workflows."""
    
    def __init__(self, db: Session):
        """Initialize review service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def submit_for_review(
        self,
        document_id: int,
        user_id: int,
        reviewers: Optional[List[int]] = None,
        due_date: Optional[datetime] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Submit a document for review.
        
        Args:
            document_id: Document ID
            user_id: User ID submitting the document
            reviewers: Optional list of reviewer user IDs to assign
            due_date: Optional due date for review
            priority: Priority level (normal, high, urgent)
            
        Returns:
            Dictionary with workflow and assignment information
            
        Raises:
            ValueError: If document not found or invalid state
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found for document {document_id}")
        
        if workflow.state != WorkflowState.DRAFT.value:
            raise ValueError(f"Cannot submit: document is in '{workflow.state}' state, must be 'draft'")
        
        # Transition to UNDER_REVIEW
        previous_state = workflow.state
        workflow.state = WorkflowState.UNDER_REVIEW.value
        workflow.submitted_at = datetime.utcnow()
        workflow.rejection_reason = None
        workflow.priority = priority
        if due_date:
            workflow.due_date = due_date
        
        # Create review assignments if reviewers provided
        assignments = []
        if reviewers:
            for reviewer_id in reviewers:
                assignment = ReviewAssignment(
                    document_id=document_id,
                    workflow_id=workflow.id,
                    reviewer_id=reviewer_id,
                    assigned_by=user_id,
                    assigned_at=datetime.utcnow(),
                    due_date=due_date,
                    status=ReviewAssignmentStatus.PENDING.value
                )
                self.db.add(assignment)
                assignments.append(assignment)
        
        self.db.commit()
        self.db.refresh(workflow)
        
        logger.info(f"Document {document_id} submitted for review by user {user_id}")
        
        return {
            "workflow": workflow.to_dict(),
            "assignments": [a.to_dict() for a in assignments]
        }
    
    def assign_reviewer(
        self,
        document_id: int,
        reviewer_id: int,
        assigned_by: int,
        due_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Assign a reviewer to a document.
        
        Args:
            document_id: Document ID
            reviewer_id: User ID of reviewer
            assigned_by: User ID assigning the reviewer
            due_date: Optional due date for review
            
        Returns:
            Assignment dictionary
            
        Raises:
            ValueError: If document or workflow not found
        """
        workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found for document {document_id}")
        
        # Check if assignment already exists
        existing = self.db.query(ReviewAssignment).filter(
            and_(
                ReviewAssignment.document_id == document_id,
                ReviewAssignment.reviewer_id == reviewer_id,
                ReviewAssignment.status != ReviewAssignmentStatus.CANCELLED.value
            )
        ).first()
        
        if existing:
            # Update existing assignment
            existing.due_date = due_date or existing.due_date
            existing.status = ReviewAssignmentStatus.PENDING.value
            assignment = existing
        else:
            # Create new assignment
            assignment = ReviewAssignment(
                document_id=document_id,
                workflow_id=workflow.id,
                reviewer_id=reviewer_id,
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                due_date=due_date,
                status=ReviewAssignmentStatus.PENDING.value
            )
            self.db.add(assignment)
        
        self.db.commit()
        self.db.refresh(assignment)
        
        logger.info(f"Reviewer {reviewer_id} assigned to document {document_id} by user {assigned_by}")
        
        return assignment.to_dict()
    
    def edit_extracted_data(
        self,
        document_id: int,
        edited_data: Dict[str, Any],
        user_id: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Edit extracted data and create a new version.
        
        Args:
            document_id: Document ID
            edited_data: Edited extracted data (CDM format)
            user_id: User ID making the edit
            comment: Optional comment explaining the edit
            
        Returns:
            Dictionary with new version information
            
        Raises:
            ValueError: If document not found or no current version
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get current version
        current_version = None
        if document.current_version_id:
            current_version = self.db.query(DocumentVersion).filter(
                DocumentVersion.id == document.current_version_id
            ).first()
        
        if not current_version:
            raise ValueError(f"No current version found for document {document_id}")
        
        # Get next version number
        latest_version = self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create new version
        new_version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            extracted_data=edited_data,
            original_text=current_version.original_text,  # Keep original text
            source_filename=current_version.source_filename,
            extraction_method="manual_edit",
            created_by=user_id
        )
        self.db.add(new_version)
        self.db.flush()
        
        # Update document's current version
        document.current_version_id = new_version.id
        
        # Add comment if provided
        if comment:
            review_comment = ReviewComment(
                document_id=document_id,
                version_id=new_version.id,
                user_id=user_id,
                comment_text=comment,
                comment_type=CommentType.GENERAL.value
            )
            self.db.add(review_comment)
        
        self.db.commit()
        self.db.refresh(new_version)
        
        logger.info(f"Created version {new_version_number} for document {document_id} by user {user_id}")
        
        return {
            "version": new_version.to_dict(),
            "previous_version_id": current_version.id
        }
    
    def add_comment(
        self,
        document_id: int,
        user_id: int,
        comment_text: str,
        comment_type: str = CommentType.GENERAL.value,
        version_id: Optional[int] = None,
        target_field: Optional[str] = None,
        target_range: Optional[Dict[str, Any]] = None,
        parent_comment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a review comment.
        
        Args:
            document_id: Document ID
            user_id: User ID adding the comment
            comment_text: Comment text
            comment_type: Type of comment (general, annotation, change_request)
            version_id: Optional version ID to attach comment to
            target_field: Optional field path for field-specific annotations
            target_range: Optional text selection range
            parent_comment_id: Optional parent comment ID for threading
            
        Returns:
            Comment dictionary
            
        Raises:
            ValueError: If document not found
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        comment = ReviewComment(
            document_id=document_id,
            version_id=version_id,
            user_id=user_id,
            comment_text=comment_text,
            comment_type=comment_type,
            target_field=target_field,
            target_range=target_range,
            parent_comment_id=parent_comment_id,
            resolved=False
        )
        
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        
        logger.info(f"Added comment {comment.id} to document {document_id} by user {user_id}")
        
        return comment.to_dict()
    
    def resolve_comment(self, comment_id: int, user_id: int) -> Dict[str, Any]:
        """Resolve a review comment.
        
        Args:
            comment_id: Comment ID
            user_id: User ID resolving the comment
            
        Returns:
            Updated comment dictionary
            
        Raises:
            ValueError: If comment not found
        """
        comment = self.db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")
        
        comment.resolved = True
        comment.resolved_by = user_id
        comment.resolved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(comment)
        
        logger.info(f"Comment {comment_id} resolved by user {user_id}")
        
        return comment.to_dict()
    
    def get_review_comments(
        self,
        document_id: int,
        version_id: Optional[int] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get review comments for a document.
        
        Args:
            document_id: Document ID
            version_id: Optional version ID to filter by
            resolved: Optional filter by resolved status
            
        Returns:
            List of comment dictionaries
        """
        query = self.db.query(ReviewComment).filter(
            ReviewComment.document_id == document_id
        )
        
        if version_id is not None:
            query = query.filter(ReviewComment.version_id == version_id)
        
        if resolved is not None:
            query = query.filter(ReviewComment.resolved == resolved)
        
        comments = query.order_by(ReviewComment.created_at.asc()).all()
        
        return [c.to_dict() for c in comments]
    
    def get_diff(
        self,
        document_id: int,
        version_id_1: int,
        version_id_2: int
    ) -> Dict[str, Any]:
        """Generate diff between two document versions.
        
        Args:
            document_id: Document ID
            version_id_1: First version ID (older)
            version_id_2: Second version ID (newer)
            
        Returns:
            Dictionary with diff information
            
        Raises:
            ValueError: If versions not found
        """
        version1 = self.db.query(DocumentVersion).filter(
            DocumentVersion.id == version_id_1,
            DocumentVersion.document_id == document_id
        ).first()
        
        version2 = self.db.query(DocumentVersion).filter(
            DocumentVersion.id == version_id_2,
            DocumentVersion.document_id == document_id
        ).first()
        
        if not version1 or not version2:
            raise ValueError("One or both versions not found")
        
        old_data = version1.extracted_data
        new_data = version2.extracted_data
        
        diff = generate_json_diff(old_data, new_data)
        formatted_diff = format_diff_for_display(diff)
        
        return {
            "version_1": version1.to_dict(),
            "version_2": version2.to_dict(),
            "diff": diff,
            "formatted_diff": formatted_diff
        }
    
    def approve_with_edits(
        self,
        document_id: int,
        edited_data: Dict[str, Any],
        user_id: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve document and create new version with edits.
        
        Args:
            document_id: Document ID
            edited_data: Edited extracted data
            user_id: User ID approving
            comment: Optional approval comment
            
        Returns:
            Dictionary with workflow and version information
            
        Raises:
            ValueError: If document or workflow not found or invalid state
        """
        workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found for document {document_id}")
        
        if workflow.state != WorkflowState.UNDER_REVIEW.value:
            raise ValueError(f"Cannot approve: document is in '{workflow.state}' state, must be 'under_review'")
        
        # Create new version with edits
        version_info = self.edit_extracted_data(document_id, edited_data, user_id, comment)
        
        # Approve workflow
        previous_state = workflow.state
        workflow.state = WorkflowState.APPROVED.value
        workflow.approved_at = datetime.utcnow()
        workflow.approved_by = user_id
        
        self.db.commit()
        self.db.refresh(workflow)
        
        logger.info(f"Document {document_id} approved with edits by user {user_id}")
        
        return {
            "workflow": workflow.to_dict(),
            "version": version_info["version"]
        }
    
    def request_changes(
        self,
        document_id: int,
        user_id: int,
        reason: str,
        required_changes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Request changes to a document under review.
        
        Args:
            document_id: Document ID
            user_id: User ID requesting changes
            reason: Reason for requesting changes
            required_changes: Optional list of specific changes required
            
        Returns:
            Dictionary with workflow information
            
        Raises:
            ValueError: If document or workflow not found or invalid state
        """
        workflow = self.db.query(Workflow).filter(Workflow.document_id == document_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found for document {document_id}")
        
        if workflow.state != WorkflowState.UNDER_REVIEW.value:
            raise ValueError(f"Cannot request changes: document is in '{workflow.state}' state, must be 'under_review'")
        
        # Transition back to DRAFT
        previous_state = workflow.state
        workflow.state = WorkflowState.DRAFT.value
        workflow.rejection_reason = reason
        
        # Add comment with change request
        change_request_text = reason
        if required_changes:
            change_request_text += "\n\nRequired changes:\n" + "\n".join(f"- {change}" for change in required_changes)
        
        comment = ReviewComment(
            document_id=document_id,
            user_id=user_id,
            comment_text=change_request_text,
            comment_type=CommentType.CHANGE_REQUEST.value,
            resolved=False
        )
        self.db.add(comment)
        
        self.db.commit()
        self.db.refresh(workflow)
        
        logger.info(f"Changes requested for document {document_id} by user {user_id}")
        
        return {
            "workflow": workflow.to_dict(),
            "comment": comment.to_dict()
        }
    
    def get_review_assignments(
        self,
        document_id: int,
        reviewer_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get review assignments for a document.
        
        Args:
            document_id: Document ID
            reviewer_id: Optional reviewer ID to filter by
            status: Optional status to filter by
            
        Returns:
            List of assignment dictionaries
        """
        query = self.db.query(ReviewAssignment).filter(
            ReviewAssignment.document_id == document_id
        )
        
        if reviewer_id:
            query = query.filter(ReviewAssignment.reviewer_id == reviewer_id)
        
        if status:
            query = query.filter(ReviewAssignment.status == status)
        
        assignments = query.order_by(ReviewAssignment.assigned_at.desc()).all()
        
        return [a.to_dict() for a in assignments]
    
    def update_assignment_status(
        self,
        assignment_id: int,
        status: str,
        review_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update review assignment status.
        
        Args:
            assignment_id: Assignment ID
            status: New status (pending, in_progress, completed, cancelled)
            review_notes: Optional review notes
            
        Returns:
            Updated assignment dictionary
            
        Raises:
            ValueError: If assignment not found or invalid status
        """
        assignment = self.db.query(ReviewAssignment).filter(
            ReviewAssignment.id == assignment_id
        ).first()
        
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        if status not in [s.value for s in ReviewAssignmentStatus]:
            raise ValueError(f"Invalid status: {status}")
        
        assignment.status = status
        if review_notes:
            assignment.review_notes = review_notes
        
        if status == ReviewAssignmentStatus.COMPLETED.value:
            assignment.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(assignment)
        
        logger.info(f"Assignment {assignment_id} updated to status {status}")
        
        return assignment.to_dict()
