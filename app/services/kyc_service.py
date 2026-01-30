"""KYC and Identity Verification Service.

Handles KYC initialization, document verification, license validation,
and integration with PeopleHub and PolicyService.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import User, KYCVerification, KYCDocument, UserLicense, Document
from app.services.policy_service import PolicyService

logger = logging.getLogger(__name__)


class KYCService:
    """Service for managing user KYC and identity verification."""

    def __init__(self, db: Session) -> None:
        self.db = db
        # Initialize PolicyService with a policy engine (mock or real)
        try:
            from app.services.policy_engine_factory import get_policy_engine

            engine = get_policy_engine()
            self.policy_service: Optional[PolicyService] = PolicyService(engine)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to initialize PolicyService for KYCService: %s", exc)
            self.policy_service = None

    def initiate_kyc_verification(self, user_id: int, level: str = "basic") -> KYCVerification:
        """Initiate KYC verification for a user."""
        verification = self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id).first()
        
        if verification:
            # Reset existing verification if it's not completed or if upgrading level
            verification.kyc_status = "pending"
            verification.kyc_level = level
            verification.submitted_at = datetime.utcnow()
        else:
            verification = KYCVerification(
                user_id=user_id,
                kyc_status="pending",
                kyc_level=level,
                submitted_at=datetime.utcnow()
            )
            self.db.add(verification)
            
        self.db.commit()
        self.db.refresh(verification)
        return verification

    def upload_kyc_document(
        self, user_id: int, document_id: int, doc_type: str, category: str
    ) -> KYCDocument:
        """Link a document to a user's KYC verification."""
        verification = self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id).first()
        if not verification:
            verification = self.initiate_kyc_verification(user_id)
            
        kyc_doc = KYCDocument(
            user_id=user_id,
            kyc_verification_id=verification.id,
            document_type=doc_type,
            document_category=category,
            document_id=document_id,
            verification_status="pending",
            created_at=datetime.utcnow()
        )
        
        self.db.add(kyc_doc)
        self.db.commit()
        self.db.refresh(kyc_doc)
        return kyc_doc

    def upload_license(
        self, 
        user_id: int, 
        license_type: str, 
        license_number: str, 
        category: str, 
        issuing_authority: str,
        document_id: Optional[int] = None
    ) -> UserLicense:
        """Add a professional license for a user."""
        verification = self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id).first()
        
        license = UserLicense(
            user_id=user_id,
            kyc_verification_id=verification.id if verification else None,
            license_type=license_type,
            license_number=license_number,
            license_category=category,
            issuing_authority=issuing_authority,
            document_id=document_id,
            verification_status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(license)
        self.db.commit()
        self.db.refresh(license)
        return license

    def evaluate_kyc_compliance(self, user_id: int, deal_type: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate KYC compliance for a user using PolicyService and KYC records.

        This aggregates KYCVerification, KYCDocument, and UserLicense data into a
        policy transaction so rules can enforce deal-type-specific and role-based
        requirements.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not self.policy_service:
            logger.warning("PolicyService not available in KYCService; returning fallback result")
            return {"status": "error", "compliant": False, "reason": "policy_service_unavailable"}

        verification = user.kyc_verification
        if not verification:
            return {"status": "not_initiated", "compliant": False, "requirements": []}

        # Aggregate KYC document and license state
        kyc_docs: List[KYCDocument] = list(verification.documents or [])
        licenses: List[UserLicense] = list(verification.licenses or [])

        verified_docs = [d for d in kyc_docs if d.verification_status == "verified"]
        verified_licenses = [lic for lic in licenses if lic.verification_status == "verified"]

        has_id_document = any(d.document_type == "id_document" and d.verification_status == "verified" for d in kyc_docs)
        has_proof_of_address = any(
            d.document_type == "proof_of_address" and d.verification_status == "verified" for d in kyc_docs
        )

        has_prof_license = bool(verified_licenses)
        has_banking_license = any(
            lic.license_category == "banking" and lic.verification_status == "verified" for lic in licenses
        )
        has_legal_license = any(
            lic.license_category == "legal" and lic.verification_status == "verified" for lic in licenses
        )
        has_accounting_license = any(
            lic.license_category == "accounting" and lic.verification_status == "verified" for lic in licenses
        )

        # Build profile payload for PolicyService (treated as an "individual" profile)
        profile: Dict[str, Any] = {
            "person_name": getattr(user, "full_name", None) or getattr(user, "name", None) or user.email,
            "profile_type": "individual",
            "user_role": getattr(user, "role", None),
            "deal_type": deal_type,
            "kyc_status": verification.kyc_status,
            "kyc_level": verification.kyc_level,
            "identity_verified": verification.identity_verified,
            "address_verified": verification.address_verified,
            "document_verified": verification.document_verified,
            "license_verified": verification.license_verified,
            "sanctions_check_passed": verification.sanctions_check_passed,
            "pep_check_passed": verification.pep_check_passed,
            "has_id_document": has_id_document,
            "has_proof_of_address": has_proof_of_address,
            "has_professional_license": has_prof_license,
            "has_banking_license": has_banking_license,
            "has_legal_license": has_legal_license,
            "has_accounting_license": has_accounting_license,
            "verified_kyc_doc_count": len(verified_docs),
            "verified_license_count": len(verified_licenses),
        }

        # Evaluate via PolicyService
        decision = self.policy_service.evaluate_kyc_compliance(
            profile=profile,
            profile_type="individual",
            deal_id=None,
            individual_profile_id=user.id,
            business_profile_id=None,
        )

        # Persist compact evaluation result on the verification record
        verification.policy_evaluation_result = {
            "decision": decision.decision,
            "rule_applied": decision.rule_applied,
            "matched_rules": decision.matched_rules,
            "trace_id": decision.trace_id,
        }
        self.db.commit()

        return {
            "status": "evaluated",
            "compliant": decision.decision == "ALLOW",
            "decision": decision.decision,
            "rule_applied": decision.rule_applied,
            "matched_rules": decision.matched_rules,
            "kyc_status": verification.kyc_status,
            "kyc_level": verification.kyc_level,
            "deal_type": deal_type,
        }

    def evaluate_kyc_for_brokerage(self, user_id: int) -> bool:
        """Evaluate whether user meets KYC requirements for brokerage (Alpaca account opening).
        Uses policy with deal_type='brokerage'; requires identity_verified (and optionally docs).
        """
        result = self.evaluate_kyc_compliance(user_id, deal_type="brokerage")
        return result.get("compliant", False) is True

    def get_kyc_requirements(self, deal_type: str) -> List[Dict[str, Any]]:
        """Get KYC requirements for a specific deal type."""
        # This would typically come from a policy or config
        requirements = [
            {"type": "id_document", "required": True, "description": "Valid passport or national ID"},
            {"type": "proof_of_address", "required": True, "description": "Utility bill or bank statement (last 3 months)"},
        ]
        
        if deal_type in ["securitization", "sustainability_linked_loan"]:
            requirements.append({"type": "professional_license", "required": True, "description": "Relevant professional certification"})
            
        return requirements

    def verify_kyc_document(
        self, kyc_document_id: int, verification_status: str, reviewer_id: int
    ) -> KYCDocument:
        """Set verification status of a KYC document (admin/reviewer)."""
        if verification_status not in ("verified", "rejected", "expired"):
            raise ValueError(f"Invalid verification_status: {verification_status}")
        kyc_doc = self.db.query(KYCDocument).filter(KYCDocument.id == kyc_document_id).first()
        if not kyc_doc:
            raise ValueError(f"KYCDocument {kyc_document_id} not found")
        kyc_doc.verification_status = verification_status
        kyc_doc.reviewed_by = reviewer_id
        kyc_doc.reviewed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(kyc_doc)
        return kyc_doc

    def complete_kyc_review(
        self,
        user_id: int,
        kyc_status: str,
        reviewer_id: int,
        rejection_reason: Optional[str] = None,
    ) -> KYCVerification:
        """Complete or reject a user's KYC verification (admin/reviewer)."""
        if kyc_status not in ("completed", "rejected"):
            raise ValueError(f"Invalid kyc_status: {kyc_status}")
        verification = self.db.query(KYCVerification).filter(KYCVerification.user_id == user_id).first()
        if not verification:
            raise ValueError(f"KYCVerification for user {user_id} not found")
        verification.kyc_status = kyc_status
        verification.reviewed_at = datetime.utcnow()
        verification.reviewed_by = reviewer_id
        if kyc_status == "rejected" and rejection_reason:
            meta = verification.verification_metadata or {}
            meta["rejection_reason"] = rejection_reason
            verification.verification_metadata = meta
        if kyc_status == "completed":
            verification.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(verification)
        try:
            from app.services.kyc_brokerage_notification import notify_kyc_brokerage_status

            subject = "KYC verification update"
            if kyc_status == "completed":
                msg = "Your KYC verification has been completed."
            else:
                msg = "Your KYC verification has been reviewed. Please check the app for details."
                if rejection_reason:
                    msg += f" Reason: {rejection_reason}"
            notify_kyc_brokerage_status(self.db, user_id, subject, msg)
        except Exception as exc:
            logger.warning("KYC/brokerage notification failed after complete_kyc_review: %s", exc)
        return verification
