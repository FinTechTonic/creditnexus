"""
Deal Signature & Documentation Tracking Service.
Tracks signatures and documentation per deal with CDM compliance and blockchain notarization.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Deal, Document, DocumentSignature, NotarizationRecord
from app.services.notarization_service import NotarizationService
from app.services.cdm_event_service import CDMEventService
from app.models.cdm_events import generate_cdm_signature_event, generate_cdm_documentation_event

logger = logging.getLogger(__name__)


class DealSignatureService:
    """Service for tracking signatures and documentation per deal."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notarization_service = NotarizationService(db)
        self.cdm_event_service = CDMEventService(db)
    
    def initialize_deal_signatures(
        self,
        deal_id: int,
        required_signatures: List[Dict[str, str]],
        signature_deadline: Optional[datetime] = None
    ) -> Deal:
        """Initialize signature requirements for a deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        deal.required_signatures = required_signatures
        deal.completed_signatures = []
        deal.signature_status = "pending"
        deal.signature_progress = 0
        deal.signature_deadline = signature_deadline
        
        self.db.commit()
        self.db.refresh(deal)
        
        logger.info(f"Initialized signatures for deal {deal_id}: {len(required_signatures)} required")
        
        return deal
    
    def initialize_deal_documentation(
        self,
        deal_id: int,
        required_documents: List[Dict[str, str]],
        documentation_deadline: Optional[datetime] = None
    ) -> Deal:
        """Initialize documentation requirements for a deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        deal.required_documents = required_documents
        deal.completed_documents = []
        deal.documentation_status = "pending"
        deal.documentation_progress = 0
        deal.documentation_deadline = documentation_deadline
        
        self.db.commit()
        self.db.refresh(deal)
        
        logger.info(f"Initialized documentation for deal {deal_id}: {len(required_documents)} required")
        
        return deal
    
    def update_signature_status(
        self,
        deal_id: int,
        signature_id: int,
        signer_email: str
    ) -> Deal:
        """Update deal signature status when a signature is completed."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Get signature record
        signature = self.db.query(DocumentSignature).filter(
            DocumentSignature.id == signature_id
        ).first()
        
        if not signature or signature.signature_status != "completed":
            raise ValueError(f"Signature {signature_id} not found or not completed")
        
        # Add to completed signatures if not already there
        completed = deal.completed_signatures or []
        if not any(s.get("signer_email") == signer_email for s in completed):
            completed.append({
                "signer_email": signer_email,
                "signed_at": signature.completed_at.isoformat() if signature.completed_at else datetime.utcnow().isoformat(),
                "signature_id": signature_id
            })
            deal.completed_signatures = completed
        
        # Update progress
        required_count = len(deal.required_signatures or [])
        completed_count = len(completed)
        deal.signature_progress = int((completed_count / required_count * 100) if required_count > 0 else 0)
        
        # Update status
        if deal.signature_progress >= 100:
            deal.signature_status = "completed"
        elif deal.signature_progress > 0:
            deal.signature_status = "in_progress"
        
        # Check compliance
        self._update_compliance_status(deal)
        
        self.db.commit()
        self.db.refresh(deal)
        
        # Generate and persist CDM event
        try:
            cdm_event = generate_cdm_signature_event(
                signature_id=str(signature_id),
                document_id=signature.document_id,
                deal_id=deal_id,
                signer_name=signer_email,
                signature_status="completed",
                signature_method="digital"
            )
            self.cdm_event_service.persist_event(
                deal_id=deal_id,
                event_type="SignatureEvent",
                event_data=cdm_event,
                user_id=deal.applicant_id
            )
        except Exception as e:
            logger.error(f"Failed to persist CDM signature event: {e}", exc_info=True)
        
        # Notarize on organization blockchain if required
        if deal.applicant and deal.applicant.organization_id:
            self._notarize_signature_on_blockchain(deal_id, signature_id, deal.applicant.organization_id)
        
        logger.info(f"Updated signature status for deal {deal_id}: {deal.signature_progress}% complete")
        
        return deal
    
    def _notarize_signature_on_blockchain(
        self,
        deal_id: int,
        signature_id: int,
        organization_id: int
    ) -> Optional[NotarizationRecord]:
        """Notarize signature on organization blockchain."""
        from app.services.organization_context_service import OrganizationContextService
        
        # Get deal to access applicant_id
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal or not deal.applicant_id:
            logger.warning(f"Deal {deal_id} or applicant not found")
            return None
        
        org_service = OrganizationContextService(self.db)
        # get_organization_blockchain expects user_id, not organization_id
        blockchain_config = org_service.get_organization_blockchain(deal.applicant_id)
        
        if not blockchain_config:
            logger.warning(f"No blockchain config for organization {organization_id}")
            return None
        
        # Get signature
        signature = self.db.query(DocumentSignature).filter(
            DocumentSignature.id == signature_id
        ).first()
        
        if not signature:
            return None
        
        # Create notarization record using NotarizationService
        # Note: NotarizationService.create_notarization_request expects deal_id and required_signers
        # For signature notarization, we'll create a simplified notarization
        try:
            # Get signer email from signature
            signer_email = None
            if signature.signers and isinstance(signature.signers, list) and len(signature.signers) > 0:
                signer_email = signature.signers[0].get("email")
            
            notarization_data = {
                "deal_id": deal_id,
                "signature_id": signature_id,
                "document_id": signature.document_id,
                "signer_email": signer_email,
                "signed_at": signature.completed_at.isoformat() if signature.completed_at else None
            }
            
            # Create notarization request with organization blockchain support
            notarization = self.notarization_service.create_notarization_request(
                deal_id=deal_id,
                required_signers=[],  # Will be populated from signature data
                message_prefix="CreditNexus Signature Notarization",
                organization_id=organization_id
            )
            
            # If blockchain config is available, notarize on organization blockchain
            if blockchain_config:
                try:
                    self.notarization_service._notarize_on_org_blockchain(
                        deal_id=deal_id,
                        notarization_id=notarization.id,
                        organization_id=organization_id,
                        blockchain_config=blockchain_config
                    )
                except Exception as e:
                    logger.warning(f"Failed to notarize on organization blockchain: {e}")
            
            logger.info(f"Notarized signature {signature_id} for deal {deal_id} on organization blockchain")
            
            return notarization
        except Exception as e:
            logger.error(f"Failed to notarize signature on blockchain: {e}")
            return None
    
    def update_documentation_status(
        self,
        deal_id: int,
        document_id: int
    ) -> Deal:
        """Update deal documentation status when a document is added."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Add to completed documents if not already there
        completed = deal.completed_documents or []
        if not any(d.get("document_id") == document_id for d in completed):
            completed.append({
                "document_id": document_id,
                "document_type": getattr(document, 'document_type', None) or "unknown",
                "document_category": getattr(document, 'document_category', None) or "unknown",
                "completed_at": document.created_at.isoformat() if document.created_at else datetime.utcnow().isoformat()
            })
            deal.completed_documents = completed
        
        # Update progress
        required_count = len(deal.required_documents or [])
        completed_count = len(completed)
        deal.documentation_progress = int((completed_count / required_count * 100) if required_count > 0 else 0)
        
        # Update status
        if deal.documentation_progress >= 100:
            deal.documentation_status = "complete"
        elif deal.documentation_progress > 0:
            deal.documentation_status = "in_progress"
        
        # Check compliance
        self._update_compliance_status(deal)
        
        self.db.commit()
        self.db.refresh(deal)
        
        # Generate and persist CDM event
        try:
            cdm_event = generate_cdm_documentation_event(
                document_id=document_id,
                deal_id=deal_id,
                document_type=getattr(document, 'document_type', None) or "unknown",
                document_category=getattr(document, 'document_category', None) or "unknown",
                documentation_status=deal.documentation_status,
                action="added"
            )
            self.cdm_event_service.persist_event(
                deal_id=deal_id,
                event_type="DocumentationEvent",
                event_data=cdm_event,
                user_id=deal.applicant_id
            )
        except Exception as e:
            logger.error(f"Failed to persist CDM documentation event: {e}", exc_info=True)
        
        logger.info(f"Updated documentation status for deal {deal_id}: {deal.documentation_progress}% complete")
        
        return deal
    
    def _update_compliance_status(self, deal: Deal) -> None:
        """Update compliance status based on signatures and documentation."""
        signature_complete = deal.signature_status == "completed"
        documentation_complete = deal.documentation_status == "complete"
        
        if signature_complete and documentation_complete:
            deal.compliance_status = "compliant"
        elif deal.signature_status == "expired" or deal.documentation_status == "non_compliant":
            deal.compliance_status = "non_compliant"
        else:
            deal.compliance_status = "pending_review"
    
    def get_deal_signature_status(self, deal_id: int) -> Dict[str, Any]:
        """Get signature status for a deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        return {
            "deal_id": deal_id,
            "required_signatures": deal.required_signatures or [],
            "completed_signatures": deal.completed_signatures or [],
            "signature_status": deal.signature_status,
            "signature_progress": deal.signature_progress,
            "signature_deadline": deal.signature_deadline.isoformat() if deal.signature_deadline else None
        }
    
    def get_deal_documentation_status(self, deal_id: int) -> Dict[str, Any]:
        """Get documentation status for a deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        return {
            "deal_id": deal_id,
            "required_documents": deal.required_documents or [],
            "completed_documents": deal.completed_documents or [],
            "documentation_status": deal.documentation_status,
            "documentation_progress": deal.documentation_progress,
            "documentation_deadline": deal.documentation_deadline.isoformat() if deal.documentation_deadline else None
        }
    
    def get_deal_compliance_summary(self, deal_id: int) -> Dict[str, Any]:
        """Get comprehensive compliance summary for a deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        return {
            "deal_id": deal_id,
            "compliance_status": deal.compliance_status,
            "signature_status": self.get_deal_signature_status(deal_id),
            "documentation_status": self.get_deal_documentation_status(deal_id),
            "compliance_notes": deal.compliance_notes
        }
