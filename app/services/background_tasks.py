"""
Background Tasks for Filing and Signature Management.

This module contains scheduled background tasks for:
1. Deadline monitoring (daily at 9 AM)
2. Signature status updates (hourly)
3. Filing status verification (daily)
"""

import logging
from datetime import datetime, time
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db import get_db
from app.agents.deadline_verifier import DeadlineVerifier
from app.agents.signature_verifier import SignatureVerifier
from app.agents.filing_verifier import FilingVerifier

logger = logging.getLogger(__name__)


async def monitor_filing_deadlines() -> Dict[str, Any]:
    """
    Background task to monitor filing deadlines.
    
    Runs daily at 9 AM to check for approaching deadlines and generate alerts.
    
    Returns:
        Task execution result
    """
    logger.info("Starting deadline monitoring task")
    
    try:
        db = next(get_db())
        verifier = DeadlineVerifier(db)
        
        # Check deadlines for next 7 days
        result = verifier.check_approaching_deadlines(days_ahead=7)
        
        # Get critical deadlines
        critical = verifier.get_critical_deadlines(hours_ahead=24)
        
        # Escalate critical deadlines
        escalated = verifier.escalate_critical_deadlines()
        
        logger.info(
            f"Deadline monitoring completed: {result['total_alerts']} alerts, "
            f"{critical['critical_count']} critical, {escalated['escalated_count']} escalated"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": result,
            "critical": critical,
            "escalated": escalated
        }
    except Exception as e:
        logger.error(f"Error in deadline monitoring task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def update_signature_statuses() -> Dict[str, Any]:
    """
    Background task to update signature statuses.
    
    Runs hourly to check DigiSigner API for signature status updates.
    
    Returns:
        Task execution result
    """
    logger.info("Starting signature status update task")
    
    try:
        db = next(get_db())
        verifier = SignatureVerifier(db)
        
        # Check for expiring signatures
        expiring = verifier.verify_expired_signatures(hours_ahead=24)
        
        # Update statuses for pending signatures
        from app.db.models import DocumentSignature
        
        pending_signatures = db.query(DocumentSignature).filter(
            DocumentSignature.signature_status == "pending"
        ).limit(100).all()  # Limit to avoid timeout
        
        updated_count = 0
        for signature in pending_signatures:
            try:
                result = verifier.verify_signature_status(signature.id)
                if result.get("status") == "success":
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Error updating signature {signature.id}: {e}")
        
        logger.info(
            f"Signature status update completed: {updated_count} signatures updated, "
            f"{expiring['expiring_count']} expiring soon"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "updated_count": updated_count,
            "expiring": expiring
        }
    except Exception as e:
        logger.error(f"Error in signature status update task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def verify_filing_statuses() -> Dict[str, Any]:
    """
    Background task to verify filing statuses.
    
    Runs daily to verify filing compliance and check status with external authorities.
    
    Returns:
        Task execution result
    """
    logger.info("Starting filing status verification task")
    
    try:
        db = next(get_db())
        verifier = FilingVerifier(db)
        
        # Get pending filings
        from app.db.models import DocumentFiling
        
        pending_filings = db.query(DocumentFiling).filter(
            DocumentFiling.filing_status == "pending"
        ).limit(100).all()  # Limit to avoid timeout
        
        verified_count = 0
        compliance_issues = []
        
        for filing in pending_filings:
            try:
                result = verifier.verify_filing_submission(filing.id)
                if result.get("status") == "success":
                    verified_count += 1
                elif result.get("status") == "warning":
                    compliance_issues.append({
                        "filing_id": filing.id,
                        "issue": result.get("message")
                    })
            except Exception as e:
                logger.warning(f"Error verifying filing {filing.id}: {e}")
        
        # Also verify document-level compliance
        from app.db.models import Document
        
        documents_with_filings = db.query(Document).join(DocumentFiling).distinct().limit(50).all()
        
        compliance_results = []
        for document in documents_with_filings:
            try:
                result = verifier.verify_document_filings(document.id, check_deadlines=True)
                if result.get("compliance_status") != "compliant":
                    compliance_results.append({
                        "document_id": document.id,
                        "compliance_status": result.get("compliance_status"),
                        "issues": result.get("missing_filings", []) + result.get("compliance_issues", [])
                    })
            except Exception as e:
                logger.warning(f"Error verifying document {document.id} filings: {e}")
        
        logger.info(
            f"Filing status verification completed: {verified_count} filings verified, "
            f"{len(compliance_results)} documents with compliance issues"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "verified_count": verified_count,
            "compliance_issues": compliance_issues,
            "compliance_results": compliance_results
        }
    except Exception as e:
        logger.error(f"Error in filing status verification task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# Task schedule configuration
TASK_SCHEDULE = {
    "deadline_monitoring": {
        "task": monitor_filing_deadlines,
        "schedule": "daily",
        "time": time(9, 0),  # 9 AM
        "enabled": True
    },
    "signature_status_updates": {
        "task": update_signature_statuses,
        "schedule": "hourly",
        "enabled": True
    },
    "filing_status_verification": {
        "task": verify_filing_statuses,
        "schedule": "daily",
        "time": time(10, 0),  # 10 AM
        "enabled": True
    }
}
