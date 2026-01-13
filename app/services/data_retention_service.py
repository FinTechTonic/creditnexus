"""Data Retention Service for CreditNexus.

This service implements automated data retention policies for GDPR compliance
and regulatory requirements.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import (
    User, Document, Workflow, AuditLog, PolicyDecision,
    Application, Deal, Inquiry, Meeting, RefreshToken
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataRetentionPolicy:
    """Data retention policy configuration."""
    
    # Audit logs: 7 years (regulatory requirement)
    AUDIT_LOGS_RETENTION_DAYS = 365 * 7
    
    # User data: Until deletion requested (GDPR)
    USER_DATA_RETENTION_DAYS = None  # Indefinite until deletion
    
    # Documents: Configurable (default: 5 years)
    DOCUMENTS_RETENTION_DAYS = 365 * 5
    
    # Policy decisions: 7 years (regulatory)
    POLICY_DECISIONS_RETENTION_DAYS = 365 * 7
    
    # Applications: 3 years after closure
    APPLICATIONS_RETENTION_DAYS = 365 * 3
    
    # Deals: 7 years after closure (regulatory)
    DEALS_RETENTION_DAYS = 365 * 7
    
    # Inquiries: 1 year after closure
    INQUIRIES_RETENTION_DAYS = 365
    
    # Meetings: 1 year after scheduled date
    MEETINGS_RETENTION_DAYS = 365
    
    # Refresh tokens: 30 days after expiration
    REFRESH_TOKENS_RETENTION_DAYS = 30


class DataRetentionService:
    """Service for managing data retention policies."""
    
    def __init__(self, db: Session):
        """Initialize data retention service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.policy = DataRetentionPolicy()
    
    def cleanup_audit_logs(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old audit logs based on retention policy.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.AUDIT_LOGS_RETENTION_DAYS)
        
        old_logs = self.db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).all()
        
        count = len(old_logs)
        
        if not dry_run and count > 0:
            # Archive before deletion (optional - implement if needed)
            # For now, we'll keep audit logs for compliance
            # In production, consider archiving to cold storage
            logger.warning(f"Audit logs older than {self.policy.AUDIT_LOGS_RETENTION_DAYS} days found. "
                          f"Consider archiving instead of deletion for compliance.")
            # self.db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete()
            # self.db.commit()
        
        return {
            "type": "audit_logs",
            "cutoff_date": cutoff_date.isoformat(),
            "records_found": count,
            "action": "archive" if not dry_run else "would_archive",
            "retention_days": self.policy.AUDIT_LOGS_RETENTION_DAYS
        }
    
    def cleanup_expired_refresh_tokens(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up expired refresh tokens.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.REFRESH_TOKENS_RETENTION_DAYS)
        
        expired_tokens = self.db.query(RefreshToken).filter(
            and_(
                RefreshToken.expires_at < cutoff_date,
                RefreshToken.is_revoked == True
            )
        ).all()
        
        count = len(expired_tokens)
        
        if not dry_run and count > 0:
            self.db.query(RefreshToken).filter(
                and_(
                    RefreshToken.expires_at < cutoff_date,
                    RefreshToken.is_revoked == True
                )
            ).delete()
            self.db.commit()
            logger.info(f"Deleted {count} expired refresh tokens")
        
        return {
            "type": "refresh_tokens",
            "cutoff_date": cutoff_date.isoformat(),
            "records_found": count,
            "action": "deleted" if not dry_run else "would_delete",
            "retention_days": self.policy.REFRESH_TOKENS_RETENTION_DAYS
        }
    
    def cleanup_old_inquiries(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old closed inquiries.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.INQUIRIES_RETENTION_DAYS)
        
        old_inquiries = self.db.query(Inquiry).filter(
            and_(
                Inquiry.status == "closed",
                Inquiry.created_at < cutoff_date
            )
        ).all()
        
        count = len(old_inquiries)
        
        if not dry_run and count > 0:
            # Anonymize instead of delete (preserve for audit)
            for inquiry in old_inquiries:
                inquiry.message = f"[Deleted - Retention Policy]"
                inquiry.user_id = None  # Anonymize
            self.db.commit()
            logger.info(f"Anonymized {count} old inquiries")
        
        return {
            "type": "inquiries",
            "cutoff_date": cutoff_date.isoformat(),
            "records_found": count,
            "action": "anonymized" if not dry_run else "would_anonymize",
            "retention_days": self.policy.INQUIRIES_RETENTION_DAYS
        }
    
    def cleanup_old_meetings(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old meetings.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.policy.MEETINGS_RETENTION_DAYS)
        
        old_meetings = self.db.query(Meeting).filter(
            Meeting.scheduled_at < cutoff_date
        ).all()
        
        count = len(old_meetings)
        
        if not dry_run and count > 0:
            # Anonymize instead of delete
            for meeting in old_meetings:
                meeting.title = f"[Deleted - Retention Policy]"
                meeting.organizer_id = None  # Anonymize
                meeting.meeting_data = None
            self.db.commit()
            logger.info(f"Anonymized {count} old meetings")
        
        return {
            "type": "meetings",
            "cutoff_date": cutoff_date.isoformat(),
            "records_found": count,
            "action": "anonymized" if not dry_run else "would_anonymize",
            "retention_days": self.policy.MEETINGS_RETENTION_DAYS
        }
    
    def run_cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run all data retention cleanup tasks.
        
        Args:
            dry_run: If True, only report what would be cleaned up
            
        Returns:
            Dictionary with cleanup summary for all tasks
        """
        logger.info(f"Starting data retention cleanup (dry_run={dry_run})")
        
        results = {
            "cleanup_date": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "results": []
        }
        
        # Cleanup tasks (in order of safety)
        tasks = [
            self.cleanup_expired_refresh_tokens,
            self.cleanup_old_inquiries,
            self.cleanup_old_meetings,
            self.cleanup_audit_logs,  # Last - most important for compliance
        ]
        
        for task in tasks:
            try:
                result = task(dry_run=dry_run)
                results["results"].append(result)
            except Exception as e:
                logger.error(f"Error in cleanup task {task.__name__}: {e}", exc_info=True)
                results["results"].append({
                    "type": task.__name__,
                    "error": str(e),
                    "status": "failed"
                })
        
        total_records = sum(r.get("records_found", 0) for r in results["results"])
        results["summary"] = {
            "total_records_affected": total_records,
            "tasks_completed": len([r for r in results["results"] if "error" not in r]),
            "tasks_failed": len([r for r in results["results"] if "error" in r])
        }
        
        logger.info(f"Data retention cleanup completed: {results['summary']}")
        
        return results


def get_retention_policy_summary() -> Dict[str, Any]:
    """Get summary of data retention policies.
    
    Returns:
        Dictionary with retention policy information
    """
    policy = DataRetentionPolicy()
    
    return {
        "policies": {
            "audit_logs": {
                "retention_days": policy.AUDIT_LOGS_RETENTION_DAYS,
                "reason": "Regulatory requirement (7 years)"
            },
            "user_data": {
                "retention_days": "indefinite",
                "reason": "GDPR - until deletion requested"
            },
            "documents": {
                "retention_days": policy.DOCUMENTS_RETENTION_DAYS,
                "reason": "Business requirement (5 years)"
            },
            "policy_decisions": {
                "retention_days": policy.POLICY_DECISIONS_RETENTION_DAYS,
                "reason": "Regulatory requirement (7 years)"
            },
            "applications": {
                "retention_days": policy.APPLICATIONS_RETENTION_DAYS,
                "reason": "Business requirement (3 years after closure)"
            },
            "deals": {
                "retention_days": policy.DEALS_RETENTION_DAYS,
                "reason": "Regulatory requirement (7 years after closure)"
            },
            "inquiries": {
                "retention_days": policy.INQUIRIES_RETENTION_DAYS,
                "reason": "Business requirement (1 year after closure)"
            },
            "meetings": {
                "retention_days": policy.MEETINGS_RETENTION_DAYS,
                "reason": "Business requirement (1 year after scheduled date)"
            },
            "refresh_tokens": {
                "retention_days": policy.REFRESH_TOKENS_RETENTION_DAYS,
                "reason": "Security best practice (30 days after expiration)"
            }
        },
        "automated_cleanup": {
            "enabled": False,  # To be enabled after testing
            "schedule": "weekly",
            "dry_run_by_default": True
        }
    }
