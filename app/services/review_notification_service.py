"""Notification service for document review workflows."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models import Document, Workflow, ReviewAssignment, User, ReviewComment
from app.services.messenger.factory import create_messenger
from app.core.config import settings

logger = logging.getLogger(__name__)


class ReviewNotificationService:
    """Service for sending review-related notifications."""
    
    def __init__(self, db: Session):
        """Initialize notification service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.messenger = create_messenger()
    
    def notify_review_assigned(
        self,
        document_id: int,
        reviewer_id: int,
        assigner_id: int
    ) -> Dict[str, Any]:
        """Send notification when a reviewer is assigned.
        
        Args:
            document_id: Document ID
            reviewer_id: Reviewer user ID
            assigner_id: User ID who assigned the reviewer
            
        Returns:
            Notification result dictionary
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
            assigner = self.db.query(User).filter(User.id == assigner_id).first()
            
            if not document or not reviewer or not assigner:
                logger.warning(f"Missing entities for review assignment notification: doc={document_id}, reviewer={reviewer_id}, assigner={assigner_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            subject = f"Review Assigned: {document.title}"
            message = f"""You have been assigned to review the following document:

Document: {document.title}
Assigned by: {assigner.display_name or assigner.email}
Document ID: {document_id}

Please review the document and provide your feedback."""
            
            # Send email notification
            if self.messenger and reviewer.email:
                try:
                    self.messenger.send_message(
                        recipient=reviewer.email,
                        subject=subject,
                        message=message,
                        link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}/review"
                    )
                    logger.info(f"Review assignment notification sent to {reviewer.email}")
                except Exception as e:
                    logger.error(f"Failed to send review assignment email: {e}", exc_info=True)
            
            return {
                "status": "sent",
                "recipient": reviewer.email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending review assignment notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def notify_review_submitted(
        self,
        document_id: int,
        submitter_id: int,
        reviewers: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Send notification when a document is submitted for review.
        
        Args:
            document_id: Document ID
            submitter_id: User ID who submitted the document
            reviewers: Optional list of reviewer user IDs
            
        Returns:
            Notification result dictionary
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            submitter = self.db.query(User).filter(User.id == submitter_id).first()
            
            if not document or not submitter:
                logger.warning(f"Missing entities for review submission notification: doc={document_id}, submitter={submitter_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            # Get reviewers from assignments if not provided
            if not reviewers:
                assignments = self.db.query(ReviewAssignment).filter(
                    ReviewAssignment.document_id == document_id,
                    ReviewAssignment.status != "cancelled"
                ).all()
                reviewers = [a.reviewer_id for a in assignments]
            
            if not reviewers:
                logger.info(f"No reviewers to notify for document {document_id}")
                return {"status": "skipped", "reason": "No reviewers"}
            
            results = []
            for reviewer_id in reviewers:
                reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
                if not reviewer or not reviewer.email:
                    continue
                
                subject = f"Document Submitted for Review: {document.title}"
                message = f"""A document has been submitted for your review:

Document: {document.title}
Submitted by: {submitter.display_name or submitter.email}
Document ID: {document_id}

Please review the document and provide your feedback."""
                
                if self.messenger:
                    try:
                        self.messenger.send_message(
                            recipient=reviewer.email,
                            subject=subject,
                            message=message,
                            link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}/review"
                        )
                        logger.info(f"Review submission notification sent to {reviewer.email}")
                        results.append({"recipient": reviewer.email, "status": "sent"})
                    except Exception as e:
                        logger.error(f"Failed to send review submission email to {reviewer.email}: {e}", exc_info=True)
                        results.append({"recipient": reviewer.email, "status": "error", "error": str(e)})
            
            return {
                "status": "sent",
                "recipients": results,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending review submission notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def notify_comment_added(
        self,
        document_id: int,
        comment_id: int,
        mentioned_users: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Send notification when a comment is added.
        
        Args:
            document_id: Document ID
            comment_id: Comment ID
            mentioned_users: Optional list of user IDs mentioned in the comment
            
        Returns:
            Notification result dictionary
        """
        try:
            comment = self.db.query(ReviewComment).filter(ReviewComment.id == comment_id).first()
            document = self.db.query(Document).filter(Document.id == document_id).first()
            
            if not comment or not document:
                logger.warning(f"Missing entities for comment notification: doc={document_id}, comment={comment_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            commenter = self.db.query(User).filter(User.id == comment.user_id).first()
            
            # Get users to notify (document owner, reviewers, mentioned users)
            users_to_notify = set()
            
            # Add document owner
            if document.uploaded_by:
                users_to_notify.add(document.uploaded_by)
            
            # Add reviewers
            assignments = self.db.query(ReviewAssignment).filter(
                ReviewAssignment.document_id == document_id,
                ReviewAssignment.status != "cancelled"
            ).all()
            for assignment in assignments:
                users_to_notify.add(assignment.reviewer_id)
            
            # Add mentioned users
            if mentioned_users:
                users_to_notify.update(mentioned_users)
            
            # Remove commenter from notification list
            users_to_notify.discard(comment.user_id)
            
            if not users_to_notify:
                logger.info(f"No users to notify for comment {comment_id}")
                return {"status": "skipped", "reason": "No users to notify"}
            
            results = []
            for user_id in users_to_notify:
                user = self.db.query(User).filter(User.id == user_id).first()
                if not user or not user.email:
                    continue
                
                subject = f"New Comment on Document: {document.title}"
                message = f"""A new comment has been added to a document you're reviewing:

Document: {document.title}
Comment by: {commenter.display_name if commenter else 'Unknown'}
Comment: {comment.comment_text[:200]}{'...' if len(comment.comment_text) > 200 else ''}

View the full comment and respond."""
                
                if self.messenger:
                    try:
                        self.messenger.send_message(
                            recipient=user.email,
                            subject=subject,
                            message=message,
                            link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}/review"
                        )
                        logger.info(f"Comment notification sent to {user.email}")
                        results.append({"recipient": user.email, "status": "sent"})
                    except Exception as e:
                        logger.error(f"Failed to send comment email to {user.email}: {e}", exc_info=True)
                        results.append({"recipient": user.email, "status": "error", "error": str(e)})
            
            return {
                "status": "sent",
                "recipients": results,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending comment notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def notify_changes_requested(
        self,
        document_id: int,
        requester_id: int,
        submitter_id: int
    ) -> Dict[str, Any]:
        """Send notification when changes are requested.
        
        Args:
            document_id: Document ID
            requester_id: User ID requesting changes
            submitter_id: User ID who originally submitted the document
            
        Returns:
            Notification result dictionary
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            requester = self.db.query(User).filter(User.id == requester_id).first()
            submitter = self.db.query(User).filter(User.id == submitter_id).first()
            
            if not document or not requester or not submitter:
                logger.warning(f"Missing entities for changes requested notification: doc={document_id}, requester={requester_id}, submitter={submitter_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            subject = f"Changes Requested: {document.title}"
            message = f"""Changes have been requested for your document:

Document: {document.title}
Requested by: {requester.display_name or requester.email}
Document ID: {document_id}

Please review the requested changes and update the document accordingly."""
            
            if self.messenger and submitter.email:
                try:
                    self.messenger.send_message(
                        recipient=submitter.email,
                        subject=subject,
                        message=message,
                        link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}/review"
                    )
                    logger.info(f"Changes requested notification sent to {submitter.email}")
                except Exception as e:
                    logger.error(f"Failed to send changes requested email: {e}", exc_info=True)
            
            return {
                "status": "sent",
                "recipient": submitter.email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending changes requested notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def notify_review_approved(
        self,
        document_id: int,
        approver_id: int,
        submitter_id: int
    ) -> Dict[str, Any]:
        """Send notification when a document is approved.
        
        Args:
            document_id: Document ID
            approver_id: User ID who approved the document
            submitter_id: User ID who originally submitted the document
            
        Returns:
            Notification result dictionary
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            approver = self.db.query(User).filter(User.id == approver_id).first()
            submitter = self.db.query(User).filter(User.id == submitter_id).first()
            
            if not document or not approver or not submitter:
                logger.warning(f"Missing entities for approval notification: doc={document_id}, approver={approver_id}, submitter={submitter_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            subject = f"Document Approved: {document.title}"
            message = f"""Your document has been approved:

Document: {document.title}
Approved by: {approver.display_name or approver.email}
Document ID: {document_id}

The document is now approved and ready for publication."""
            
            if self.messenger and submitter.email:
                try:
                    self.messenger.send_message(
                        recipient=submitter.email,
                        subject=subject,
                        message=message,
                        link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}"
                    )
                    logger.info(f"Approval notification sent to {submitter.email}")
                except Exception as e:
                    logger.error(f"Failed to send approval email: {e}", exc_info=True)
            
            return {
                "status": "sent",
                "recipient": submitter.email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending approval notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def notify_due_date_approaching(
        self,
        document_id: int,
        reviewer_id: int,
        days_until: int
    ) -> Dict[str, Any]:
        """Send notification when review due date is approaching.
        
        Args:
            document_id: Document ID
            reviewer_id: Reviewer user ID
            days_until: Number of days until due date
            
        Returns:
            Notification result dictionary
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
            assignment = self.db.query(ReviewAssignment).filter(
                ReviewAssignment.document_id == document_id,
                ReviewAssignment.reviewer_id == reviewer_id
            ).first()
            
            if not document or not reviewer or not assignment:
                logger.warning(f"Missing entities for due date notification: doc={document_id}, reviewer={reviewer_id}")
                return {"status": "skipped", "reason": "Missing entities"}
            
            if not assignment.due_date:
                return {"status": "skipped", "reason": "No due date"}
            
            subject_prefix = "URGENT: " if days_until <= 1 else ""
            subject = f"{subject_prefix}Review Due Date Approaching: {document.title}"
            message = f"""Your review assignment is due soon:

Document: {document.title}
Due Date: {assignment.due_date.strftime('%Y-%m-%d %H:%M')}
Days Remaining: {days_until}
Document ID: {document_id}

Please complete your review before the due date."""
            
            if self.messenger and reviewer.email:
                try:
                    self.messenger.send_message(
                        recipient=reviewer.email,
                        subject=subject,
                        message=message,
                        link=f"{settings.FRONTEND_URL or 'http://localhost:3000'}/documents/{document_id}/review"
                    )
                    logger.info(f"Due date notification sent to {reviewer.email} ({days_until} days)")
                except Exception as e:
                    logger.error(f"Failed to send due date email: {e}", exc_info=True)
            
            return {
                "status": "sent",
                "recipient": reviewer.email,
                "subject": subject,
                "days_until": days_until,
                "sent_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending due date notification: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
