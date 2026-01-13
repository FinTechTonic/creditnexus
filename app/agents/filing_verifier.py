"""
Filing Compliance Verification Agent.

This agent verifies filing compliance by:
1. Checking if required filings have been submitted
2. Validating filing data completeness
3. Monitoring filing deadlines
4. Verifying filing status with external authorities
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentFiling, Deal
from app.services.policy_service import PolicyService
from app.services.policy_engine_factory import get_policy_engine
from app.models.cdm import CreditAgreement

logger = logging.getLogger(__name__)


class FilingVerifier:
    """Agent for verifying filing compliance."""

    def __init__(self, db: Session):
        """
        Initialize filing verifier.

        Args:
            db: Database session
        """
        self.db = db
        self.policy_service = PolicyService(get_policy_engine())

    def verify_document_filings(
        self,
        document_id: int,
        check_deadlines: bool = True
    ) -> Dict[str, Any]:
        """
        Verify filing compliance for a document.

        Args:
            document_id: Document ID to verify
            check_deadlines: Whether to check for approaching deadlines

        Returns:
            Verification result with compliance status and issues
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {
                "status": "error",
                "message": f"Document {document_id} not found"
            }

        # 1. Get filing requirements
        if not document.source_cdm_data:
            return {
                "status": "error",
                "message": "Document has no CDM data"
            }

        credit_agreement = CreditAgreement(**document.source_cdm_data)
        filing_decision = self.policy_service.evaluate_filing_requirements(
            credit_agreement=credit_agreement,
            document_id=document_id,
            deal_id=document.deal_id
        )

        # 2. Check existing filings
        existing_filings = self.db.query(DocumentFiling).filter(
            DocumentFiling.document_id == document_id
        ).all()

        # 3. Match requirements with existing filings
        compliance_issues = []
        missing_filings = []
        deadline_issues = []

        for requirement in filing_decision.required_filings:
            # Find matching filing
            matching_filing = next(
                (
                    f for f in existing_filings
                    if f.filing_authority == requirement.authority
                    and f.jurisdiction == requirement.jurisdiction
                ),
                None
            )

            if not matching_filing:
                missing_filings.append({
                    "authority": requirement.authority,
                    "jurisdiction": requirement.jurisdiction,
                    "deadline": requirement.deadline.isoformat() if hasattr(requirement.deadline, 'isoformat') else str(requirement.deadline),
                    "priority": requirement.priority
                })
            else:
                # Check filing status
                if matching_filing.filing_status not in ["submitted", "accepted"]:
                    compliance_issues.append({
                        "type": "pending_filing",
                        "authority": requirement.authority,
                        "status": matching_filing.filing_status,
                        "filing_id": matching_filing.id
                    })

                # Check deadline
                if check_deadlines and matching_filing.deadline:
                    days_remaining = (matching_filing.deadline - datetime.utcnow()).days
                    if days_remaining <= 7:
                        deadline_issues.append({
                            "filing_id": matching_filing.id,
                            "authority": requirement.authority,
                            "days_remaining": days_remaining,
                            "urgency": "critical" if days_remaining <= 1 else "high"
                        })

        # 4. Determine overall compliance status
        compliance_status = "compliant"
        if missing_filings or compliance_issues:
            compliance_status = "non_compliant"
        elif deadline_issues:
            compliance_status = "at_risk"

        return {
            "status": "success",
            "document_id": document_id,
            "compliance_status": compliance_status,
            "required_filings_count": len(filing_decision.required_filings),
            "existing_filings_count": len(existing_filings),
            "missing_filings": missing_filings,
            "compliance_issues": compliance_issues,
            "deadline_issues": deadline_issues,
            "deadline_alerts": filing_decision.deadline_alerts
        }

    def verify_filing_submission(
        self,
        filing_id: int
    ) -> Dict[str, Any]:
        """
        Verify a specific filing submission.

        Args:
            filing_id: DocumentFiling ID to verify

        Returns:
            Verification result
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            return {
                "status": "error",
                "message": f"Filing {filing_id} not found"
            }

        # For automated filings (Companies House), verify status via API
        if filing.filing_system == "companies_house_api" and filing.filing_reference:
            # In production, would call Companies House API to verify
            # For now, return current status
            return {
                "status": "success",
                "filing_id": filing_id,
                "filing_status": filing.filing_status,
                "filing_reference": filing.filing_reference,
                "verified_at": datetime.utcnow().isoformat(),
                "note": "API verification not implemented - using database status"
            }

        # For manual filings, check if reference is provided
        if filing.filing_system == "manual_ui":
            if filing.filing_reference:
                return {
                    "status": "success",
                    "filing_id": filing_id,
                    "filing_status": filing.filing_status,
                    "filing_reference": filing.filing_reference,
                    "verified_at": datetime.utcnow().isoformat(),
                    "note": "Manual filing - reference provided"
                }
            else:
                return {
                    "status": "warning",
                    "filing_id": filing_id,
                    "message": "Manual filing has no reference number"
                }

        return {
            "status": "success",
            "filing_id": filing_id,
            "filing_status": filing.filing_status
        }

    def verify_deal_filings(
        self,
        deal_id: int
    ) -> Dict[str, Any]:
        """
        Verify filing compliance for all documents in a deal.

        Args:
            deal_id: Deal ID to verify

        Returns:
            Verification result for all documents
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return {
                "status": "error",
                "message": f"Deal {deal_id} not found"
            }

        documents = self.db.query(Document).filter(Document.deal_id == deal_id).all()

        results = []
        for document in documents:
            result = self.verify_document_filings(document.id)
            results.append(result)

        # Aggregate results
        total_required = sum(r.get("required_filings_count", 0) for r in results)
        total_existing = sum(r.get("existing_filings_count", 0) for r in results)
        total_missing = sum(len(r.get("missing_filings", [])) for r in results)

        overall_status = "compliant"
        if total_missing > 0:
            overall_status = "non_compliant"
        elif any(r.get("compliance_status") == "at_risk" for r in results):
            overall_status = "at_risk"

        return {
            "status": "success",
            "deal_id": deal_id,
            "overall_status": overall_status,
            "documents_checked": len(documents),
            "total_required_filings": total_required,
            "total_existing_filings": total_existing,
            "total_missing_filings": total_missing,
            "document_results": results
        }
