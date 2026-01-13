"""
Deadline Monitoring Verification Agent.

This agent monitors filing deadlines by:
1. Checking approaching deadlines
2. Generating deadline alerts
3. Verifying deadline compliance
4. Escalating critical deadlines
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import DocumentFiling
from app.services.policy_service import PolicyService
from app.services.policy_engine_factory import get_policy_engine

logger = logging.getLogger(__name__)


class DeadlineVerifier:
    """Agent for monitoring and verifying filing deadlines."""

    def __init__(self, db: Session):
        """
        Initialize deadline verifier.

        Args:
            db: Database session
        """
        self.db = db
        self.policy_service = PolicyService(get_policy_engine())

    def check_approaching_deadlines(
        self,
        days_ahead: int = 7,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check for approaching filing deadlines.

        Args:
            days_ahead: Number of days ahead to check
            deal_id: Optional deal ID to filter
            document_id: Optional document ID to filter

        Returns:
            List of approaching deadlines with alerts
        """
        alerts = self.policy_service.check_filing_deadlines(
            deal_id=deal_id,
            document_id=document_id,
            days_ahead=days_ahead
        )

        # Group by urgency
        critical = [a for a in alerts if a.urgency == "critical"]
        high = [a for a in alerts if a.urgency == "high"]
        medium = [a for a in alerts if a.urgency == "medium"]

        return {
            "status": "success",
            "total_alerts": len(alerts),
            "critical_count": len(critical),
            "high_count": len(high),
            "medium_count": len(medium),
            "alerts": [
                {
                    "filing_id": alert.filing_id,
                    "document_id": alert.document_id,
                    "deal_id": alert.deal_id,
                    "authority": alert.authority,
                    "deadline": alert.deadline.isoformat() if hasattr(alert.deadline, 'isoformat') else str(alert.deadline),
                    "days_remaining": alert.days_remaining,
                    "urgency": alert.urgency,
                    "penalty": alert.penalty
                }
                for alert in alerts
            ],
            "critical_alerts": [
                {
                    "filing_id": alert.filing_id,
                    "authority": alert.authority,
                    "days_remaining": alert.days_remaining
                }
                for alert in critical
            ]
        }

    def verify_deadline_compliance(
        self,
        filing_id: int
    ) -> Dict[str, Any]:
        """
        Verify if a filing meets its deadline.

        Args:
            filing_id: DocumentFiling ID to verify

        Returns:
            Compliance verification result
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()

        if not filing:
            return {
                "status": "error",
                "message": f"Filing {filing_id} not found"
            }

        if not filing.deadline:
            return {
                "status": "warning",
                "filing_id": filing_id,
                "message": "Filing has no deadline set"
            }

        now = datetime.utcnow()
        days_remaining = (filing.deadline - now).days

        # Check if deadline has passed
        deadline_passed = filing.deadline < now

        # Check if filing was submitted on time
        submitted_on_time = False
        if filing.filed_at:
            submitted_on_time = filing.filed_at <= filing.deadline
        elif filing.submitted_at:
            submitted_on_time = filing.submitted_at <= filing.deadline

        compliance_status = "compliant"
        if deadline_passed and filing.filing_status != "submitted":
            compliance_status = "non_compliant"
        elif days_remaining <= 1 and filing.filing_status == "pending":
            compliance_status = "critical"
        elif days_remaining <= 7 and filing.filing_status == "pending":
            compliance_status = "at_risk"

        return {
            "status": "success",
            "filing_id": filing_id,
            "compliance_status": compliance_status,
            "deadline": filing.deadline.isoformat(),
            "days_remaining": days_remaining,
            "deadline_passed": deadline_passed,
            "submitted_on_time": submitted_on_time,
            "filing_status": filing.filing_status,
            "filed_at": filing.filed_at.isoformat() if filing.filed_at else None,
            "submitted_at": filing.submitted_at.isoformat() if filing.submitted_at else None
        }

    def get_critical_deadlines(
        self,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """
        Get critical deadlines within the next N hours.

        Args:
            hours_ahead: Number of hours ahead to check

        Returns:
            List of critical deadlines
        """
        cutoff_time = datetime.utcnow() + timedelta(hours=hours_ahead)

        critical_filings = self.db.query(DocumentFiling).filter(
            DocumentFiling.filing_status == "pending",
            DocumentFiling.deadline <= cutoff_time,
            DocumentFiling.deadline > datetime.utcnow()
        ).all()

        results = []
        for filing in critical_filings:
            days_remaining = (filing.deadline - datetime.utcnow()).days
            hours_remaining = (filing.deadline - datetime.utcnow()).total_seconds() / 3600

            results.append({
                "filing_id": filing.id,
                "document_id": filing.document_id,
                "deal_id": filing.deal_id,
                "authority": filing.filing_authority,
                "jurisdiction": filing.jurisdiction,
                "deadline": filing.deadline.isoformat(),
                "days_remaining": days_remaining,
                "hours_remaining": round(hours_remaining, 1),
                "urgency": "critical" if hours_remaining <= 24 else "high"
            })

        return {
            "status": "success",
            "critical_count": len(critical_filings),
            "critical_deadlines": results
        }

    def escalate_critical_deadlines(
        self
    ) -> Dict[str, Any]:
        """
        Escalate critical deadlines that are past due or expiring very soon.

        Returns:
            Escalation results
        """
        now = datetime.utcnow()
        
        # Find overdue filings
        overdue = self.db.query(DocumentFiling).filter(
            DocumentFiling.filing_status == "pending",
            DocumentFiling.deadline < now
        ).all()

        # Find filings expiring in next 24 hours
        expiring_soon = self.db.query(DocumentFiling).filter(
            DocumentFiling.filing_status == "pending",
            DocumentFiling.deadline <= now + timedelta(hours=24),
            DocumentFiling.deadline > now
        ).all()

        escalated = []

        for filing in overdue + expiring_soon:
            escalated.append({
                "filing_id": filing.id,
                "document_id": filing.document_id,
                "deal_id": filing.deal_id,
                "authority": filing.filing_authority,
                "deadline": filing.deadline.isoformat(),
                "status": "overdue" if filing.deadline < now else "expiring_soon",
                "days_overdue": (now - filing.deadline).days if filing.deadline < now else 0
            })

        return {
            "status": "success",
            "escalated_count": len(escalated),
            "overdue_count": len(overdue),
            "expiring_soon_count": len(expiring_soon),
            "escalated_filings": escalated
        }
