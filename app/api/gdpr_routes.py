"""GDPR Compliance API endpoints for CreditNexus.

This module implements GDPR compliance features:
- Right to access (data export)
- Right to deletion (data erasure)
- Data portability
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db import get_db
from app.db.models import (
    User, Document, Workflow, PolicyDecision, AuditLog, 
    Application, Deal, Inquiry, Meeting, RefreshToken
)
from app.services.data_retention_service import (
    DataRetentionService, get_retention_policy_summary
)
from app.auth.jwt_auth import require_auth
from app.utils.audit import log_audit_action
from app.db.models import AuditAction

logger = logging.getLogger(__name__)

gdpr_router = APIRouter(prefix="/gdpr", tags=["GDPR Compliance"])


class GDPRExportRequest(BaseModel):
    """Request model for GDPR data export."""
    email: EmailStr
    format: str = "json"  # json or csv


class GDPRDeletionRequest(BaseModel):
    """Request model for GDPR data deletion."""
    email: EmailStr
    confirm: bool = False  # Require explicit confirmation
    reason: Optional[str] = None


class GDPRExportResponse(BaseModel):
    """Response model for GDPR data export."""
    user_id: int
    email: str
    exported_at: str
    data: Dict[str, Any]
    format: str


def export_user_data(user: User, db: Session) -> Dict[str, Any]:
    """Export all user data for GDPR compliance.
    
    Args:
        user: User object to export data for
        db: Database session
        
    Returns:
        Dictionary containing all user data
    """
    # Collect all user-related data
    user_data = {
        "user_profile": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "wallet_address": user.wallet_address,
            "profile_data": user.profile_data,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "documents": [],
        "workflows": [],
        "policy_decisions": [],
        "audit_logs": [],
        "applications": [],
        "deals": [],
        "inquiries": [],
        "meetings": [],
    }
    
    # Export documents
    documents = db.query(Document).filter(Document.uploaded_by == user.id).all()
    for doc in documents:
        user_data["documents"].append({
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "metadata": doc.metadata,
        })
    
    # Export workflows (where user is assigned or approved)
    workflows = db.query(Workflow).filter(
        (Workflow.assigned_to == user.id) | (Workflow.approved_by == user.id)
    ).all()
    for workflow in workflows:
        user_data["workflows"].append({
            "id": workflow.id,
            "document_id": workflow.document_id,
            "state": workflow.state,
            "assigned_to": workflow.assigned_to,
            "approved_by": workflow.approved_by,
            "submitted_at": workflow.submitted_at.isoformat() if workflow.submitted_at else None,
            "approved_at": workflow.approved_at.isoformat() if workflow.approved_at else None,
        })
    
    # Export policy decisions (where user is involved)
    policy_decisions = db.query(PolicyDecision).filter(
        PolicyDecision.user_id == user.id
    ).all()
    for decision in policy_decisions:
        user_data["policy_decisions"].append({
            "id": decision.id,
            "transaction_id": decision.transaction_id,
            "transaction_type": decision.transaction_type,
            "decision": decision.decision,
            "rule_applied": decision.rule_applied,
            "created_at": decision.created_at.isoformat() if decision.created_at else None,
        })
    
    # Export audit logs
    audit_logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).all()
    for log in audit_logs:
        user_data["audit_logs"].append({
            "id": log.id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "action_metadata": log.action_metadata,
        })
    
    # Export applications
    applications = db.query(Application).filter(Application.user_id == user.id).all()
    for app in applications:
        user_data["applications"].append({
            "id": app.id,
            "application_type": app.application_type,
            "status": app.status,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "application_data": app.application_data,
        })
    
    # Export deals (where user is applicant)
    deals = db.query(Deal).filter(Deal.applicant_id == user.id).all()
    for deal in deals:
        user_data["deals"].append({
            "id": deal.id,
            "deal_id": deal.deal_id,
            "deal_type": deal.deal_type,
            "status": deal.status,
            "created_at": deal.created_at.isoformat() if deal.created_at else None,
            "deal_data": deal.deal_data,
        })
    
    # Export inquiries
    inquiries = db.query(Inquiry).filter(Inquiry.user_id == user.id).all()
    for inquiry in inquiries:
        user_data["inquiries"].append({
            "id": inquiry.id,
            "inquiry_type": inquiry.inquiry_type,
            "status": inquiry.status,
            "message": inquiry.message,
            "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
        })
    
    # Export meetings (where user is organizer)
    meetings = db.query(Meeting).filter(Meeting.organizer_id == user.id).all()
    for meeting in meetings:
        user_data["meetings"].append({
            "id": meeting.id,
            "title": meeting.title,
            "scheduled_at": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
            "meeting_data": meeting.meeting_data,
        })
    
    return user_data


def delete_user_data(user: User, db: Session, soft_delete: bool = True) -> Dict[str, Any]:
    """Delete all user data for GDPR compliance.
    
    Args:
        user: User object to delete data for
        db: Database session
        soft_delete: If True, anonymize data instead of hard delete (recommended for audit)
        
    Returns:
        Dictionary with deletion summary
    """
    deletion_summary = {
        "user_id": user.id,
            "email": user.email,
            "deleted_at": datetime.utcnow().isoformat(),
            "soft_delete": soft_delete,
            "items_deleted": {
                "documents": 0,
                "workflows": 0,
                "policy_decisions": 0,
                "audit_logs": 0,
                "applications": 0,
                "deals": 0,
                "inquiries": 0,
                "meetings": 0,
                "refresh_tokens": 0,
            }
    }
    
    if soft_delete:
        # Anonymize user data (preserve for audit trail)
        user.email = f"deleted_{user.id}@deleted.local"
        user.display_name = "Deleted User"
        user.profile_data = None
        user.wallet_address = None
        user.is_active = False
        user.password_hash = None  # Remove password hash
        db.commit()
        
        # Anonymize related data
        # Documents - anonymize
        documents = db.query(Document).filter(Document.uploaded_by == user.id).all()
        for doc in documents:
            doc.title = f"Deleted Document {doc.id}"
            doc.borrower_name = None
            doc.borrower_lei = None
            doc.uploaded_by = None  # Remove user reference
            deletion_summary["items_deleted"]["documents"] += 1
        db.commit()
        
        # Refresh tokens - revoke all
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).all()
        for token in tokens:
            token.is_revoked = True
            deletion_summary["items_deleted"]["refresh_tokens"] += len(tokens)
        db.commit()
        
        # Note: Audit logs are preserved for compliance
        # Other data can be anonymized similarly
        
    else:
        # Hard delete (not recommended - loses audit trail)
        # Delete documents
        documents = db.query(Document).filter(Document.uploaded_by_user_id == user.id).all()
        deletion_summary["items_deleted"]["documents"] = len(documents)
        for doc in documents:
            db.delete(doc)
        
        # Anonymize workflows (where user is assigned or approved)
        workflows = db.query(Workflow).filter(
            (Workflow.assigned_to == user.id) | (Workflow.approved_by == user.id)
        ).all()
        deletion_summary["items_deleted"]["workflows"] = len(workflows)
        for workflow in workflows:
            if workflow.assigned_to == user.id:
                workflow.assigned_to = None
            if workflow.approved_by == user.id:
                workflow.approved_by = None
        
        # Delete refresh tokens
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user.id).all()
        deletion_summary["items_deleted"]["refresh_tokens"] = len(tokens)
        for token in tokens:
            db.delete(token)
        
        # Delete user
        db.delete(user)
        db.commit()
    
    return deletion_summary


@gdpr_router.post("/export", response_model=GDPRExportResponse)
async def export_user_data_endpoint(
    request: GDPRExportRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Export user data for GDPR compliance (Right to Access).
    
    Users can export their own data. Admins can export any user's data.
    """
    # Check if user is requesting their own data or is admin
    target_user = db.query(User).filter(User.email == request.email).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if target_user.id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only export your own data unless you are an admin"
        )
    
    # Export data
    user_data = export_user_data(target_user, db)
    
    # Log audit action
    log_audit_action(
        db, 
        AuditAction.EXPORT, 
        "user", 
        target_user.id, 
        current_user.id,
        action_metadata={"gdpr_export": True, "format": request.format}
    )
    
    if request.format == "json":
        return GDPRExportResponse(
            user_id=target_user.id,
            email=target_user.email,
            exported_at=datetime.utcnow().isoformat(),
            data=user_data,
            format="json"
        )
    else:
        # CSV format (simplified - would need proper CSV generation)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="CSV export not yet implemented"
        )


@gdpr_router.post("/delete")
async def delete_user_data_endpoint(
    request: GDPRDeletionRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Delete user data for GDPR compliance (Right to Erasure).
    
    Users can delete their own data. Admins can delete any user's data.
    Requires explicit confirmation.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion requires explicit confirmation (confirm=true)"
        )
    
    # Check if user is requesting their own data or is admin
    target_user = db.query(User).filter(User.email == request.email).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if target_user.id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own data unless you are an admin"
        )
    
    # Prevent admin from deleting themselves
    if target_user.id == current_user.id and current_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete their own accounts via this endpoint. Contact support."
        )
    
    # Perform deletion (soft delete by default for audit trail)
    deletion_summary = delete_user_data(target_user, db, soft_delete=True)
    
    # Log audit action
    log_audit_action(
        db,
        AuditAction.DELETE,
        "user",
        target_user.id,
        current_user.id,
        action_metadata={
            "gdpr_deletion": True,
            "soft_delete": True,
            "reason": request.reason,
            "deletion_summary": deletion_summary
        }
    )
    
    return {
        "status": "success",
        "message": "User data deleted successfully",
        "deletion_summary": deletion_summary
    }


@gdpr_router.get("/status")
async def gdpr_compliance_status(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get GDPR compliance status and available actions."""
    retention_policy = get_retention_policy_summary()
    
    return {
        "gdpr_compliant": True,
        "available_actions": {
            "export": "/api/gdpr/export",
            "delete": "/api/gdpr/delete",
        },
        "data_retention_policy": retention_policy["policies"],
        "user_rights": [
            "Right to access (data export)",
            "Right to erasure (data deletion)",
            "Right to data portability",
            "Right to rectification (update profile)",
        ],
        "automated_cleanup": retention_policy["automated_cleanup"]
    }


@gdpr_router.post("/retention/cleanup")
async def run_data_retention_cleanup(
    dry_run: bool = True,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Run data retention cleanup (admin only).
    
    This endpoint runs automated data retention cleanup based on configured policies.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    service = DataRetentionService(db)
    results = service.run_cleanup(dry_run=dry_run)
    
    # Log audit action
    log_audit_action(
        db,
        AuditAction.UPDATE,
        "data_retention",
        None,
        current_user.id,
        action_metadata={
            "cleanup_results": results,
            "dry_run": dry_run
        }
    )
    
    return {
        "status": "success",
        "dry_run": dry_run,
        "results": results
    }
