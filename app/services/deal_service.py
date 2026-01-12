"""
Deal service for managing deal lifecycle and state transitions.

This service handles deal creation, status updates, document attachment,
and CDM event generation for deal state changes.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import Deal, Document, Application, DealStatus, DealType, ApplicationStatus, ApplicationType, PolicyDecision, DealNote
from app.models.cdm_events import generate_cdm_policy_evaluation
from app.services.file_storage_service import FileStorageService
import uuid
from app.utils.audit import log_audit_action, AuditAction

logger = logging.getLogger(__name__)


class DealService:
    """Service for managing deals and their lifecycle."""
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        DealStatus.DRAFT.value: [DealStatus.SUBMITTED.value],
        DealStatus.SUBMITTED.value: [DealStatus.UNDER_REVIEW.value, DealStatus.REJECTED.value],
        DealStatus.UNDER_REVIEW.value: [DealStatus.APPROVED.value, DealStatus.REJECTED.value],
        DealStatus.APPROVED.value: [DealStatus.ACTIVE.value],
        DealStatus.ACTIVE.value: [DealStatus.CLOSED.value],
        DealStatus.REJECTED.value: [],  # Terminal state
        DealStatus.CLOSED.value: [],  # Terminal state
    }
    
    def __init__(self, db: Session):
        """
        Initialize deal service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.file_storage = FileStorageService()
    
    def create_deal_from_application(
        self,
        application_id: int,
        deal_type: Optional[str] = None,
        deal_data: Optional[Dict[str, Any]] = None
    ) -> Deal:
        """
        Create a deal from an approved application.
        
        Args:
            application_id: ID of the application
            deal_type: Type of deal (defaults to application type)
            deal_data: Additional deal metadata
            
        Returns:
            Created Deal instance
            
        Raises:
            ValueError: If application not found or not approved
        """
        application = self.db.query(Application).filter(Application.id == application_id).first()
        
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        if application.status != ApplicationStatus.APPROVED.value:
            raise ValueError(f"Application {application_id} is not approved (status: {application.status})")
        
        # Generate unique deal_id
        deal_id = f"DEAL-{application_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Determine deal type from application if not provided
        if not deal_type:
            if application.application_type == ApplicationType.BUSINESS.value:
                deal_type = DealType.LOAN_APPLICATION.value
            else:
                deal_type = DealType.LOAN_APPLICATION.value
        
        # Create deal folder structure
        folder_path = self.file_storage.create_deal_folder(
            user_id=application.user_id,
            deal_id=deal_id
        )
        
        # Create deal
        deal = Deal(
            deal_id=deal_id,
            applicant_id=application.user_id,
            application_id=application_id,
            status=DealStatus.DRAFT.value,
            deal_type=deal_type,
            deal_data=deal_data or {},
            folder_path=folder_path
        )
        
        self.db.add(deal)
        self.db.flush()
        
        # Create CDM event for deal creation
        cdm_event = generate_cdm_policy_evaluation(
            transaction_id=deal_id,
            transaction_type="deal_creation",
            decision="ALLOW",
            rule_applied="deal_created_from_application",
            related_event_identifiers=[],
            evaluation_trace=[{
                "action": "deal_created",
                "application_id": application_id,
                "deal_id": deal_id,
                "deal_type": deal_type
            }],
            matched_rules=["deal_created_from_application"]
        )
        
        # Store CDM event in deal folder
        self.file_storage.store_cdm_event(
            user_id=application.user_id,
            deal_id=deal_id,
            event_id=f"DEAL_CREATION_{deal.id}",
            event_data=cdm_event
        )
        
        # Create PolicyDecision record in database for audit trail
        policy_decision = PolicyDecision(
            transaction_id=deal_id,
            transaction_type="deal_creation",
            decision="ALLOW",
            rule_applied="deal_created_from_application",
            trace_id=str(uuid.uuid4()),
            trace=[{
                "action": "deal_created",
                "application_id": application_id,
                "deal_id": deal_id,
                "deal_type": deal_type
            }],
            matched_rules=["deal_created_from_application"],
            cdm_events=[cdm_event],
            deal_id=deal.id,
            user_id=application.user_id
        )
        self.db.add(policy_decision)
        self.db.commit()
        self.db.refresh(deal)
        
        # Auto-evaluate green finance on deal creation (if enabled and location data available)
        if settings.ENHANCED_SATELLITE_ENABLED:
            try:
                from app.services.policy_service import PolicyService
                from app.services.policy_engine_factory import get_policy_engine
                from app.models.cdm import CreditAgreement
                from app.models.loan_asset import LoanAsset
                
                # Check if deal has loan assets with location data
                # Note: Loan assets may be created later, so this is optional
                loan_assets = self.db.query(LoanAsset).filter(
                    LoanAsset.loan_id.like(f"%{deal.deal_id}%")
                ).all()
                
                if loan_assets:
                    # Get first loan asset with location
                    loan_asset_with_location = next(
                        (la for la in loan_assets if la.geo_lat and la.geo_lon),
                        None
                    )
                    
                    if loan_asset_with_location:
                        policy_service = PolicyService(get_policy_engine())
                        
                        # Create basic CreditAgreement for evaluation
                        # In production, this would come from extracted documents
                        credit_agreement = CreditAgreement(
                            deal_id=deal.deal_id,
                            loan_identification_number=deal.deal_id,
                            sustainability_linked=deal.deal_data.get("sustainability_linked", False) if deal.deal_data else False
                        )
                        
                        # Evaluate green finance compliance
                        green_finance_result = policy_service.evaluate_green_finance_compliance(
                            credit_agreement=credit_agreement,
                            loan_asset=loan_asset_with_location,
                            document_id=None
                        )
                        
                        # Store green finance assessment in deal metadata
                        if deal.deal_data is None:
                            deal.deal_data = {}
                        deal.deal_data["green_finance_assessment"] = {
                            "decision": green_finance_result.decision,
                            "rule_applied": green_finance_result.rule_applied,
                            "trace_id": green_finance_result.trace_id,
                            "matched_rules": green_finance_result.matched_rules,
                            "assessed_at": datetime.utcnow().isoformat()
                        }
                        
                        # Create PolicyDecision for green finance
                        green_policy_decision = PolicyDecision(
                            transaction_id=deal.deal_id,
                            transaction_type="green_finance_assessment",
                            decision=green_finance_result.decision,
                            rule_applied=green_finance_result.rule_applied,
                            trace_id=green_finance_result.trace_id,
                            trace=green_finance_result.trace,
                            matched_rules=green_finance_result.matched_rules,
                            cdm_events=[generate_cdm_policy_evaluation(
                                transaction_id=deal.deal_id,
                                transaction_type="green_finance_assessment",
                                decision=green_finance_result.decision,
                                rule_applied=green_finance_result.rule_applied,
                                related_event_identifiers=[],
                                evaluation_trace=green_finance_result.trace,
                                matched_rules=green_finance_result.matched_rules
                            )],
                            deal_id=deal.id,
                            user_id=application.user_id
                        )
                        self.db.add(green_policy_decision)
                        self.db.commit()
                        
                        logger.info(
                            f"Green finance assessment for deal {deal.id}: "
                            f"{green_finance_result.decision} (rule: {green_finance_result.rule_applied})"
                        )
            except Exception as e:
                logger.warning(f"Green finance evaluation failed for deal {deal.id}: {e}", exc_info=True)
                # Don't fail deal creation if green finance evaluation fails
        
        # Index deal in ChromaDB
        try:
            from app.chains.document_retrieval_chain import add_deal
            # Get documents and notes for indexing (initially empty)
            documents = []
            notes = []
            add_deal(
                deal_id=deal.id,
                deal_data=deal.to_dict(),
                documents=documents,
                notes=notes
            )
            logger.info(f"Indexed deal {deal.id} in ChromaDB")
        except Exception as e:
            logger.warning(f"Failed to index deal in ChromaDB: {e}")
            # Don't fail deal creation if indexing fails
        
        # Auto-evaluate credit risk on deal creation
        try:
            from app.services.policy_service import PolicyService
            from app.services.policy_engine_factory import get_policy_engine
            from app.models.cdm import CreditAgreement
            
            # Create a basic CreditAgreement from deal data if available
            if deal.deal_data:
                # Try to construct CreditAgreement from deal_data
                # This is a simplified approach - in production, you'd load from document
                policy_service = PolicyService(get_policy_engine())
                
                # Evaluate credit risk if we have sufficient data
                additional_context = deal.deal_data.copy()
                additional_context.update({
                    "deal_id": deal.deal_id,
                    "deal_type": deal.deal_type,
                    "status": deal.status
                })
                
                # For now, we'll store credit risk metrics in deal_data
                # In a full implementation, you'd create a CreditAgreement from documents
                logger.info(f"Credit risk evaluation will be performed when documents are attached to deal {deal.id}")
        except Exception as e:
            logger.warning(f"Failed to evaluate credit risk on deal creation: {e}")
            # Don't fail deal creation if credit risk evaluation fails
        
        logger.info(f"Created deal {deal_id} from application {application_id}")
        
        return deal
    
    def update_deal_status(
        self,
        deal_id: int,
        new_status: str,
        user_id: int,
        reason: Optional[str] = None
    ) -> Deal:
        """
        Update deal status with validation and CDM event generation.
        
        Args:
            deal_id: ID of the deal
            new_status: New status value
            user_id: ID of user making the change
            reason: Optional reason for status change
            
        Returns:
            Updated Deal instance
            
        Raises:
            ValueError: If deal not found or invalid transition
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        old_status = deal.status
        
        # Validate transition
        if new_status not in self.VALID_TRANSITIONS.get(old_status, []):
            raise ValueError(
                f"Invalid status transition from {old_status} to {new_status}. "
                f"Valid transitions: {self.VALID_TRANSITIONS.get(old_status, [])}"
            )
        
        # Update status
        deal.status = new_status
        deal.updated_at = datetime.utcnow()
        
        # Create CDM event for status change
        decision = "ALLOW"
        if new_status == DealStatus.REJECTED.value:
            decision = "BLOCK"
        elif new_status == DealStatus.UNDER_REVIEW.value:
            decision = "FLAG"
        
        cdm_event = generate_cdm_policy_evaluation(
            transaction_id=deal.deal_id,
            transaction_type="deal_status_change",
            decision=decision,
            rule_applied=f"deal_status_{old_status}_to_{new_status}",
            related_event_identifiers=[],
            evaluation_trace=[{
                "action": "status_change",
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "user_id": user_id
            }],
            matched_rules=[f"deal_status_{old_status}_to_{new_status}"]
        )
        
        # Store CDM event
        self.file_storage.store_cdm_event(
            user_id=deal.applicant_id,
            deal_id=deal.deal_id,
            event_id=f"STATUS_CHANGE_{deal.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            event_data=cdm_event
        )
        
        # Create PolicyDecision record in database for audit trail
        policy_decision = PolicyDecision(
            transaction_id=deal.deal_id,
            transaction_type="deal_status_change",
            decision=decision,
            rule_applied=f"deal_status_{old_status}_to_{new_status}",
            trace_id=str(uuid.uuid4()),
            trace=[{
                "action": "status_change",
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "user_id": user_id
            }],
            matched_rules=[f"deal_status_{old_status}_to_{new_status}"],
            cdm_events=[cdm_event],
            deal_id=deal.id,
            user_id=user_id
        )
        self.db.add(policy_decision)
        self.db.commit()
        self.db.refresh(deal)
        
        # Re-index deal in ChromaDB after status update
        try:
            from app.chains.document_retrieval_chain import add_deal
            # Get documents and notes for indexing
            documents = [doc.to_dict() for doc in self.db.query(Document).filter(Document.deal_id == deal_id).limit(10).all()]
            notes = [note.to_dict() for note in self.db.query(DealNote).filter(DealNote.deal_id == deal_id).order_by(DealNote.created_at.desc()).limit(10).all()]
            add_deal(
                deal_id=deal.id,
                deal_data=deal.to_dict(),
                documents=documents,
                notes=notes
            )
            logger.info(f"Re-indexed deal {deal.id} in ChromaDB after status update")
        except Exception as e:
            logger.warning(f"Failed to re-index deal in ChromaDB: {e}")
            # Don't fail status update if indexing fails
        
        # Audit log
        log_audit_action(
            self.db,
            AuditAction.UPDATE,
            "deal",
            deal.id,
            user_id,
            metadata={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason
            }
        )
        
        logger.info(f"Updated deal {deal.deal_id} status from {old_status} to {new_status}")
        
        return deal
    
    def attach_document_to_deal(
        self,
        deal_id: int,
        document_id: int,
        user_id: int
    ) -> Document:
        """
        Attach a document to a deal.
        
        Args:
            deal_id: ID of the deal
            document_id: ID of the document
            user_id: ID of user making the attachment
            
        Returns:
            Updated Document instance
            
        Raises:
            ValueError: If deal or document not found
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Attach document to deal
        document.deal_id = deal_id
        document.updated_at = datetime.utcnow()
        
        # Create CDM event for document attachment
        cdm_event = generate_cdm_policy_evaluation(
            transaction_id=deal.deal_id,
            transaction_type="document_attachment",
            decision="ALLOW",
            rule_applied="document_attached_to_deal",
            related_event_identifiers=[],
            evaluation_trace=[{
                "action": "document_attached",
                "document_id": document_id,
                "deal_id": deal_id,
                "user_id": user_id
            }],
            matched_rules=["document_attached_to_deal"]
        )
        
        # Store CDM event
        self.file_storage.store_cdm_event(
            user_id=deal.applicant_id,
            deal_id=deal.deal_id,
            event_id=f"DOC_ATTACH_{document_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            event_data=cdm_event
        )
        
        # Create PolicyDecision record in database for audit trail
        policy_decision = PolicyDecision(
            transaction_id=deal.deal_id,
            transaction_type="document_attachment",
            decision="ALLOW",
            rule_applied="document_attached_to_deal",
            trace_id=str(uuid.uuid4()),
            trace=[{
                "action": "document_attached",
                "document_id": document_id,
                "deal_id": deal_id,
                "user_id": user_id
            }],
            matched_rules=["document_attached_to_deal"],
            cdm_events=[cdm_event],
            deal_id=deal_id,
            document_id=document_id,
            user_id=user_id
        )
        self.db.add(policy_decision)
        
        # Audit log
        log_audit_action(
            self.db,
            AuditAction.UPDATE,
            "document",
            document_id,
            user_id,
            metadata={"deal_id": deal_id, "action": "attach_to_deal"}
        )
        
        self.db.commit()
        self.db.refresh(document)
        
        # Re-index deal in ChromaDB after document attachment
        try:
            from app.chains.document_retrieval_chain import add_deal
            # Get documents and notes for indexing
            documents = [doc.to_dict() for doc in self.db.query(Document).filter(Document.deal_id == deal_id).limit(10).all()]
            notes = [note.to_dict() for note in self.db.query(DealNote).filter(DealNote.deal_id == deal_id).order_by(DealNote.created_at.desc()).limit(10).all()]
            add_deal(
                deal_id=deal.id,
                deal_data=deal.to_dict(),
                documents=documents,
                notes=notes
            )
            logger.info(f"Re-indexed deal {deal.id} in ChromaDB after document attachment")
        except Exception as e:
            logger.warning(f"Failed to re-index deal in ChromaDB: {e}")
            # Don't fail document attachment if indexing fails
        
        logger.info(f"Attached document {document_id} to deal {deal.deal_id}")
        
        return document
    
    def get_deal_timeline(
        self,
        deal_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of all events for a deal.
        
        Includes:
        - Deal creation
        - Status changes
        - Document attachments
        - CDM events from file storage
        
        Args:
            deal_id: ID of the deal
            
        Returns:
            List of timeline events in chronological order
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        timeline = []
        
        # Add deal creation event
        timeline.append({
            "event_type": "deal_created",
            "timestamp": deal.created_at.isoformat() if deal.created_at else None,
            "data": {
                "deal_id": deal.deal_id,
                "deal_type": deal.deal_type,
                "applicant_id": deal.applicant_id,
                "application_id": deal.application_id
            }
        })
        
        # Add status changes from CDM events in file storage
        events_dir = self.file_storage.base_storage_path / str(deal.applicant_id) / deal.deal_id / "events"
        if events_dir.exists():
            import json
            for event_file in sorted(events_dir.glob("*.json")):
                try:
                    with open(event_file, 'r', encoding='utf-8') as f:
                        event_data = json.load(f)
                        timeline.append({
                            "event_type": event_data.get("eventType", "unknown"),
                            "timestamp": event_data.get("eventDate"),
                            "data": event_data
                        })
                except Exception as e:
                    logger.warning(f"Failed to load event file {event_file}: {e}")
        
        # Add document attachments
        documents = self.db.query(Document).filter(Document.deal_id == deal_id).all()
        for doc in documents:
            timeline.append({
                "event_type": "document_attached",
                "timestamp": doc.created_at.isoformat() if doc.created_at else None,
                "data": {
                    "document_id": doc.id,
                    "title": doc.title,
                    "borrower_name": doc.borrower_name
                }
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        
        return timeline
    
    def get_deal(self, deal_id: int) -> Optional[Deal]:
        """Get deal by ID."""
        return self.db.query(Deal).filter(Deal.id == deal_id).first()
    
    def get_deal_by_deal_id(self, deal_id_str: str) -> Optional[Deal]:
        """Get deal by deal_id string."""
        return self.db.query(Deal).filter(Deal.deal_id == deal_id_str).first()
    
    def update_deal_on_verification(
        self,
        deal_id: int,
        verification_result: Dict[str, Any],
        loan_asset_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Deal:
        """
        Update deal with satellite verification results.
        
        This method:
        1. Updates deal metadata with verification results
        2. Stores verification result JSON in deal folder
        3. Creates a deal note with verification summary
        4. Optionally updates deal status if breach detected
        
        Args:
            deal_id: ID of the deal
            verification_result: Dictionary with verification results (ndvi_score, risk_status, etc.)
            loan_asset_id: Optional loan asset ID associated with verification
            user_id: Optional user ID performing verification
            
        Returns:
            Updated Deal instance
            
        Raises:
            ValueError: If deal not found
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Extract verification data
        ndvi_score = verification_result.get("ndvi_score")
        risk_status = verification_result.get("risk_status", verification_result.get("status"))
        threshold = verification_result.get("threshold", 0.8)
        verified_at = verification_result.get("verified_at", datetime.utcnow().isoformat())
        data_source = verification_result.get("data_source", "unknown")
        
        # Update deal metadata with verification results
        if deal.deal_data is None:
            deal.deal_data = {}
        
        if "verification_history" not in deal.deal_data:
            deal.deal_data["verification_history"] = []
        
        # Extract enhanced metrics if available
        location_type = verification_result.get("location_type")
        air_quality_index = verification_result.get("air_quality_index")
        composite_sustainability_score = verification_result.get("composite_sustainability_score")
        sustainability_components = verification_result.get("sustainability_components")
        osm_metrics = verification_result.get("osm_metrics", {})
        air_quality = verification_result.get("air_quality", {})
        
        verification_entry = {
            "ndvi_score": ndvi_score,
            "risk_status": risk_status,
            "threshold": threshold,
            "verified_at": verified_at,
            "data_source": data_source,
            "loan_asset_id": loan_asset_id
        }
        deal.deal_data["verification_history"].append(verification_entry)
        
        # Update latest verification in deal_data
        deal.deal_data["latest_verification"] = verification_entry
        
        # Store verification result JSON in deal folder
        verification_file_path = self.file_storage.store_cdm_event(
            user_id=deal.applicant_id,
            deal_id=deal.deal_id,
            event_id=f"VERIFICATION_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            event_data={
                "eventType": "VerificationResult",
                "eventDate": verified_at,
                "verification": verification_result,
                "deal_id": deal.deal_id,
                "loan_asset_id": loan_asset_id
            }
        )
        
        # Create deal note with verification summary
        note_content = (
            f"Satellite Verification Completed\n\n"
            f"NDVI Score: {ndvi_score:.4f if ndvi_score else 'N/A'}\n"
            f"Risk Status: {risk_status}\n"
            f"Threshold: {threshold}\n"
            f"Data Source: {data_source}\n"
            f"Verified At: {verified_at}\n"
        )
        
        if risk_status == "BREACH":
            note_content += "\n⚠️ BREACH DETECTED: Sustainability performance target not met. Interest rate penalty may apply."
        elif risk_status == "WARNING":
            note_content += "\n⚠️ WARNING: Approaching threshold. Monitor closely."
        elif risk_status == "COMPLIANT":
            note_content += "\n✅ COMPLIANT: Sustainability performance target met."
        
        # Create deal note in database
        from app.db.models import DealNote
        deal_note = DealNote(
            deal_id=deal_id,
            user_id=user_id or deal.applicant_id,
            content=note_content,
            note_type="verification",
            metadata={
                "verification_result": verification_result,
                "verification_file_path": verification_file_path,
                "loan_asset_id": loan_asset_id
            }
        )
        self.db.add(deal_note)
        self.db.flush()  # Flush to get the note ID
        
        # Store note in file system
        self.file_storage.store_deal_note(
            user_id=deal.applicant_id,
            deal_id=deal.deal_id,
            note_id=deal_note.id,
            content=note_content,
            metadata=deal_note.note_metadata
        )
        
        # Optionally update deal status based on verification
        # If breach detected and deal is active, flag for review
        if risk_status == "BREACH" and deal.status == DealStatus.ACTIVE.value:
            # Don't automatically change status, but add to metadata
            if "flags" not in deal.deal_data:
                deal.deal_data["flags"] = []
            if "verification_breach" not in deal.deal_data["flags"]:
                deal.deal_data["flags"].append({
                    "type": "verification_breach",
                    "detected_at": verified_at,
                    "ndvi_score": ndvi_score,
                    "threshold": threshold
                })
        
        deal.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(deal)
        self.db.refresh(deal_note)
        
        # Re-index deal in ChromaDB after verification update
        try:
            from app.chains.document_retrieval_chain import add_deal
            # Get documents and notes for indexing
            documents = [doc.to_dict() for doc in self.db.query(Document).filter(Document.deal_id == deal_id).limit(10).all()]
            notes = [note.to_dict() for note in self.db.query(DealNote).filter(DealNote.deal_id == deal_id).order_by(DealNote.created_at.desc()).limit(10).all()]
            add_deal(
                deal_id=deal.id,
                deal_data=deal.to_dict(),
                documents=documents,
                notes=notes
            )
            logger.info(f"Re-indexed deal {deal.id} in ChromaDB after verification update")
        except Exception as e:
            logger.warning(f"Failed to re-index deal in ChromaDB: {e}")
            # Don't fail verification update if indexing fails
        
        logger.info(
            f"Updated deal {deal.deal_id} with verification results: "
            f"NDVI={ndvi_score}, status={risk_status}"
        )
        
        return deal
    
    def list_deals(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        deal_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Deal]:
        """
        List deals with optional filtering.
        
        Args:
            user_id: Filter by applicant ID (None for all users)
            status: Filter by status
            deal_type: Filter by deal type
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Deal instances
        """
        query = self.db.query(Deal)
        
        if user_id:
            query = query.filter(Deal.applicant_id == user_id)
        
        if status:
            query = query.filter(Deal.status == status)
        
        if deal_type:
            query = query.filter(Deal.deal_type == deal_type)
        
        return query.order_by(Deal.created_at.desc()).limit(limit).offset(offset).all()
