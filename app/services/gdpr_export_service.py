"""Enhanced GDPR data export service with complete data coverage."""

import json
import logging
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models import (
    User,
    Document,
    Workflow,
    PolicyDecision,
    AuditLog,
    Application,
    Deal,
    Inquiry,
    Meeting,
    RefreshToken,
    KYCVerification,
    UserLicense,
    KYCDocument,
    ConsentRecord,
    DataProcessingRequest,
)

logger = logging.getLogger(__name__)

class GDPRExportService:
    """Enhanced GDPR data export service with complete data coverage and portability."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def export_user_data_complete(
        self,
        user: User,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export all user data including new Phase 2/3 data types."""
        # Base export (mirrors legacy export_user_data implementation)
        db = self.db

        user_data: Dict[str, Any] = {
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

        # Documents
        documents = db.query(Document).filter(Document.uploaded_by == user.id).all()
        for doc in documents:
            user_data["documents"].append(
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "metadata": doc.metadata,
                }
            )

        # Workflows
        workflows = (
            db.query(Workflow)
            .filter((Workflow.assigned_to == user.id) | (Workflow.approved_by == user.id))
            .all()
        )
        for workflow in workflows:
            user_data["workflows"].append(
                {
                    "id": workflow.id,
                    "document_id": workflow.document_id,
                    "state": workflow.state,
                    "assigned_to": workflow.assigned_to,
                    "approved_by": workflow.approved_by,
                    "submitted_at": workflow.submitted_at.isoformat()
                    if workflow.submitted_at
                    else None,
                    "approved_at": workflow.approved_at.isoformat()
                    if workflow.approved_at
                    else None,
                }
            )

        # Policy decisions
        policy_decisions = db.query(PolicyDecision).filter(
            PolicyDecision.user_id == user.id
        ).all()
        for decision in policy_decisions:
            user_data["policy_decisions"].append(
                {
                    "id": decision.id,
                    "transaction_id": decision.transaction_id,
                    "transaction_type": decision.transaction_type,
                    "decision": decision.decision,
                    "rule_applied": decision.rule_applied,
                    "created_at": decision.created_at.isoformat()
                    if decision.created_at
                    else None,
                }
            )

        # Audit logs
        audit_logs = db.query(AuditLog).filter(AuditLog.user_id == user.id).all()
        for log in audit_logs:
            user_data["audit_logs"].append(
                {
                    "id": log.id,
                    "action": log.action,
                    "target_type": log.target_type,
                    "target_id": log.target_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "created_at": log.created_at.isoformat()
                    if log.created_at
                    else None,
                    "action_metadata": log.action_metadata,
                }
            )

        # Applications
        applications = (
            db.query(Application).filter(Application.user_id == user.id).all()
        )
        for app in applications:
            user_data["applications"].append(
                {
                    "id": app.id,
                    "application_type": app.application_type,
                    "status": app.status,
                    "submitted_at": app.submitted_at.isoformat()
                    if app.submitted_at
                    else None,
                    "application_data": app.application_data,
                }
            )

        # Deals
        deals = db.query(Deal).filter(Deal.applicant_id == user.id).all()
        for deal in deals:
            user_data["deals"].append(
                {
                    "id": deal.id,
                    "deal_id": deal.deal_id,
                    "deal_type": deal.deal_type,
                    "status": deal.status,
                    "created_at": deal.created_at.isoformat()
                    if deal.created_at
                    else None,
                    "deal_data": deal.deal_data,
                }
            )

        # Inquiries
        inquiries = db.query(Inquiry).filter(Inquiry.user_id == user.id).all()
        for inquiry in inquiries:
            user_data["inquiries"].append(
                {
                    "id": inquiry.id,
                    "inquiry_type": inquiry.inquiry_type,
                    "status": inquiry.status,
                    "message": inquiry.message,
                    "created_at": inquiry.created_at.isoformat()
                    if inquiry.created_at
                    else None,
                }
            )

        # Meetings
        meetings = (
            db.query(Meeting).filter(Meeting.organizer_id == user.id).all()
        )
        for meeting in meetings:
            user_data["meetings"].append(
                {
                    "id": meeting.id,
                    "title": meeting.title,
                    "scheduled_at": meeting.scheduled_at.isoformat()
                    if meeting.scheduled_at
                    else None,
                    "meeting_data": meeting.meeting_data,
                }
            )
        
        # Add KYC data
        kyc = self.db.query(KYCVerification).filter(KYCVerification.user_id == user.id).first()
        if kyc:
            user_data["kyc_verification"] = kyc.to_dict()
            
        # Add Licenses
        licenses = self.db.query(UserLicense).filter(UserLicense.user_id == user.id).all()
        user_data["licenses"] = [l.to_dict() for l in licenses]
        
        # Add KYC Documents
        kyc_docs = self.db.query(KYCDocument).filter(KYCDocument.user_id == user.id).all()
        user_data["kyc_documents"] = [d.to_dict() for d in kyc_docs]
        
        # Add Consent records
        consents = self.db.query(ConsentRecord).filter(ConsentRecord.user_id == user.id).all()
        user_data["consent_history"] = [c.to_dict() for c in consents]
        
        # Add Processing requests
        requests = self.db.query(DataProcessingRequest).filter(DataProcessingRequest.user_id == user.id).all()
        user_data["privacy_requests"] = [r.id for r in requests] # Simplified
        
        return user_data

    def convert_to_json_ld(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert data to JSON-LD (Schema.org) for portability."""
        profile = data.get("user_profile", {})
        return {
            "@context": "https://schema.org",
            "@type": "Person",
            "identifier": profile.get("id"),
            "email": profile.get("email"),
            "name": profile.get("display_name"),
            "jobTitle": profile.get("role"),
            "description": "CreditNexus User Data Export",
            "additionalProperty": [
                {"name": k, "value": v} for k, v in data.items() if k != "user_profile"
            ]
        }

    def convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert simplified flat data to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write user profile
        writer.writerow(["Category", "Key", "Value"])
        profile = data.get("user_profile", {})
        for k, v in profile.items():
            writer.writerow(["Profile", k, str(v)])
            
        # Write summaries of other lists
        for key, value in data.items():
            if key != "user_profile" and isinstance(value, list):
                writer.writerow([key, "Count", len(value)])
                
        return output.getvalue()
