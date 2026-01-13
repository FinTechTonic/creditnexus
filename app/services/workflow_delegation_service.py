"""Workflow delegation service for link-based workflow distribution."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.workflow_types import WorkflowType, get_workflow_metadata
from app.utils.link_payload import LinkPayloadGenerator
from app.services.dynamic_whitelist_service import DynamicWhitelistService
from app.services.verification_service import VerificationService
from app.services.notarization_service import NotarizationService
from app.services.cdm_payload_generator import get_deal_cdm_payload
from app.db.models import Deal, Document, DocumentVersion, User
from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowDelegationService:
    """Service for delegating workflows via encrypted links.
    
    Supports multiple workflow types:
    - Verification
    - Notarization
    - Document Review
    - Deal Approval/Review
    - Custom Workflows
    """

    def __init__(self, db: Session):
        """Initialize workflow delegation service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.link_generator = LinkPayloadGenerator()
        self.whitelist_service = DynamicWhitelistService()
        self.verification_service = VerificationService(db)
        self.notarization_service = NotarizationService(db)

    def delegate_verification_workflow(
        self,
        deal_id: int,
        sender_user_id: int,
        receiver_email: Optional[str] = None,
        receiver_user_id: Optional[int] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_categories: Optional[List[str]] = None,
        file_document_ids: Optional[List[int]] = None,
        expires_in_hours: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate verification workflow to remote user.
        
        Args:
            deal_id: Deal database ID
            sender_user_id: User ID of sender
            receiver_email: Optional receiver email address
            receiver_user_id: Optional receiver user ID
            workflow_metadata: Optional workflow-specific metadata
            file_categories: Optional file categories to include
            file_document_ids: Optional specific document IDs to include
            expires_in_hours: Optional expiration time
            base_url: Optional base URL for link generation
            
        Returns:
            Dictionary with workflow_id, link, and metadata
        """
        # Get deal
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Create verification request
        verification = self.verification_service.create_verification_request(
            deal_id=deal_id,
            verifier_user_id=receiver_user_id,
            created_by=sender_user_id,
            expires_in_hours=expires_in_hours or 72,
            verification_metadata=workflow_metadata,
        )
        
        workflow_id = verification.verification_id
        
        # Get deal data
        deal_data = {
            "deal_id": deal.deal_id,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "deal_data": deal.deal_data or {},
            "applicant_id": deal.applicant_id,
        }
        
        # Get CDM payload
        cdm_payload = get_deal_cdm_payload(self.db, deal)
        
        # Get file references
        file_references = self._get_file_references(
            deal_id=deal_id,
            file_categories=file_categories,
            file_document_ids=file_document_ids,
            workflow_type=WorkflowType.VERIFICATION,
        )
        
        # Get whitelist config
        whitelist_config = self.whitelist_service.get_whitelist_for_workflow(
            workflow_type=WorkflowType.VERIFICATION,
            deal_id=deal_id,
        )
        
        # Filter files by whitelist
        file_references = self.whitelist_service.filter_files_by_whitelist(
            file_references, whitelist_config
        )
        
        # Get sender info
        sender = self.db.query(User).filter(User.id == sender_user_id).first()
        sender_info = {
            "user_id": sender_user_id,
            "email": sender.email if sender else None,
            "name": sender.display_name if sender else None,
            "organization": "CreditNexus",
        }
        
        # Get receiver info
        receiver_info = {}
        if receiver_user_id:
            receiver = self.db.query(User).filter(User.id == receiver_user_id).first()
            receiver_info = {
                "user_id": receiver_user_id,
                "email": receiver.email if receiver else None,
                "name": receiver.display_name if receiver else None,
            }
        elif receiver_email:
            receiver_info = {
                "email": receiver_email,
            }
        
        # Build workflow metadata
        if workflow_metadata is None:
            workflow_metadata = {}
        
        workflow_metadata.setdefault("title", "Deal Verification Request")
        workflow_metadata.setdefault("description", "Please verify this deal and its documents")
        workflow_metadata.setdefault("instructions", [
            "Review deal documents",
            "Verify CDM compliance",
            "Accept or decline verification"
        ])
        
        # Generate link
        encrypted_payload = self.link_generator.generate_workflow_link_payload(
            workflow_type=WorkflowType.VERIFICATION,
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            receiver_info=receiver_info,
            expires_in_hours=expires_in_hours,
        )
        
        # Build full URL
        if not base_url:
            base_url = getattr(settings, "WORKFLOW_DELEGATION_BASE_URL", None) or getattr(settings, "VERIFICATION_BASE_URL", None)
        if not base_url:
            raise ValueError(
                "WORKFLOW_DELEGATION_BASE_URL or VERIFICATION_BASE_URL must be set in configuration. "
                "Please set one of these environment variables."
            )
        link = f"{str(base_url).rstrip('/')}/workflow/{encrypted_payload}"
        
        logger.info(f"Delegated verification workflow {workflow_id} for deal {deal_id}")
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": "verification",
            "link": link,
            "encrypted_payload": encrypted_payload,
            "verification_id": verification.verification_id,
            "files_included": len(file_references),
            "expires_at": verification.expires_at.isoformat() if verification.expires_at else None,
        }

    def delegate_notarization_workflow(
        self,
        deal_id: int,
        sender_user_id: int,
        required_signers: List[str],
        receiver_email: Optional[str] = None,
        receiver_user_id: Optional[int] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        message_prefix: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate notarization workflow to remote user.
        
        Args:
            deal_id: Deal database ID
            sender_user_id: User ID of sender
            required_signers: List of wallet addresses required to sign
            receiver_email: Optional receiver email address
            receiver_user_id: Optional receiver user ID
            workflow_metadata: Optional workflow-specific metadata
            message_prefix: Optional message prefix for signing
            expires_in_hours: Optional expiration time
            base_url: Optional base URL for link generation
            
        Returns:
            Dictionary with workflow_id, link, and metadata
        """
        # Get deal
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Create notarization request
        notarization = self.notarization_service.create_notarization_request(
            deal_id=deal_id,
            required_signers=required_signers,
            message_prefix=message_prefix or "CreditNexus Notarization",
        )
        
        workflow_id = str(notarization.id)
        
        # Get deal data
        deal_data = {
            "deal_id": deal.deal_id,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "deal_data": deal.deal_data or {},
        }
        
        # Get CDM payload
        cdm_payload = get_deal_cdm_payload(self.db, deal)
        
        # Get file references (legal documents only for notarization)
        file_references = self._get_file_references(
            deal_id=deal_id,
            file_categories=["legal"],
            workflow_type=WorkflowType.NOTARIZATION,
        )
        
        # Get whitelist config
        whitelist_config = self.whitelist_service.get_whitelist_for_workflow(
            workflow_type=WorkflowType.NOTARIZATION,
            deal_id=deal_id,
        )
        
        # Filter files by whitelist
        file_references = self.whitelist_service.filter_files_by_whitelist(
            file_references, whitelist_config
        )
        
        # Get sender info
        sender = self.db.query(User).filter(User.id == sender_user_id).first()
        sender_info = {
            "user_id": sender_user_id,
            "email": sender.email if sender else None,
            "name": sender.display_name if sender else None,
        }
        
        # Build workflow metadata
        if workflow_metadata is None:
            workflow_metadata = {}
        
        workflow_metadata.setdefault("title", "Document Notarization Request")
        workflow_metadata.setdefault("description", "Please notarize these documents with blockchain signatures")
        workflow_metadata.setdefault("required_signers", required_signers)
        workflow_metadata.setdefault("notarization_id", notarization.id)
        workflow_metadata.setdefault("notarization_hash", notarization.notarization_hash)
        
        # Generate link
        encrypted_payload = self.link_generator.generate_workflow_link_payload(
            workflow_type=WorkflowType.NOTARIZATION,
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            expires_in_hours=expires_in_hours or 168,  # 7 days default
        )
        
        # Build full URL
        if not base_url:
            base_url = getattr(settings, "WORKFLOW_DELEGATION_BASE_URL", None) or getattr(settings, "VERIFICATION_BASE_URL", None)
        if not base_url:
            raise ValueError(
                "WORKFLOW_DELEGATION_BASE_URL or VERIFICATION_BASE_URL must be set in configuration. "
                "Please set one of these environment variables."
            )
        link = f"{str(base_url).rstrip('/')}/workflow/{encrypted_payload}"
        
        logger.info(f"Delegated notarization workflow {workflow_id} for deal {deal_id}")
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": "notarization",
            "link": link,
            "encrypted_payload": encrypted_payload,
            "notarization_id": notarization.id,
            "notarization_hash": notarization.notarization_hash,
            "files_included": len(file_references),
        }

    def delegate_document_workflow(
        self,
        document_id: int,
        sender_user_id: int,
        review_type: str = "general",
        receiver_email: Optional[str] = None,
        receiver_user_id: Optional[int] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate document review workflow to remote user.
        
        Args:
            document_id: Document database ID
            sender_user_id: User ID of sender
            review_type: Type of review ("legal", "financial", "compliance", "general")
            receiver_email: Optional receiver email address
            receiver_user_id: Optional receiver user ID
            workflow_metadata: Optional workflow-specific metadata
            expires_in_hours: Optional expiration time
            base_url: Optional base URL for link generation
            
        Returns:
            Dictionary with workflow_id, link, and metadata
        """
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get latest version
        latest_version = (
            self.db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )
        
        workflow_id = str(uuid.uuid4())
        
        # Get deal if available
        deal_id = document.deal_id
        deal_data = {}
        cdm_payload = {}
        
        if deal_id:
            deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                deal_data = {
                    "deal_id": deal.deal_id,
                    "status": deal.status,
                    "deal_type": deal.deal_type,
                }
                cdm_payload = get_deal_cdm_payload(self.db, deal)
        
        # Build file reference for document
        file_references = []
        if latest_version and latest_version.source_filename:
            file_references.append({
                "document_id": document_id,
                "filename": latest_version.source_filename,
                "category": review_type,
                "subdirectory": "documents",
                "size": 0,  # Will be populated if file exists
                "download_url": f"/api/deals/{deal_id}/documents/{document_id}/download" if deal_id else f"/api/documents/{document_id}/download",
                "title": document.title or latest_version.source_filename,
            })
        
        # Get whitelist config
        whitelist_config = self.whitelist_service.get_whitelist_for_workflow(
            workflow_type=WorkflowType.DOCUMENT_REVIEW,
            deal_id=deal_id,
        )
        
        # Get sender info
        sender = self.db.query(User).filter(User.id == sender_user_id).first()
        sender_info = {
            "user_id": sender_user_id,
            "email": sender.email if sender else None,
            "name": sender.display_name if sender else None,
        }
        
        # Build workflow metadata
        if workflow_metadata is None:
            workflow_metadata = {}
        
        workflow_metadata.setdefault("title", f"Document Review - {review_type.title()}")
        workflow_metadata.setdefault("description", f"Please review this document ({review_type} review)")
        workflow_metadata.setdefault("document_id", document_id)
        if latest_version:
            workflow_metadata.setdefault("document_version", latest_version.version_number)
        workflow_metadata.setdefault("review_type", review_type)
        
        # Generate link
        encrypted_payload = self.link_generator.generate_document_workflow_link_payload(
            workflow_id=workflow_id,
            document_id=document_id,
            document_version=latest_version.version_number if latest_version else None,
            deal_id=deal_id,
            deal_data=deal_data,
            review_type=review_type,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            expires_in_hours=expires_in_hours,
        )
        
        # Build full URL
        if not base_url:
            base_url = getattr(settings, "WORKFLOW_DELEGATION_BASE_URL", None) or getattr(settings, "VERIFICATION_BASE_URL", None)
        if not base_url:
            raise ValueError(
                "WORKFLOW_DELEGATION_BASE_URL or VERIFICATION_BASE_URL must be set in configuration. "
                "Please set one of these environment variables."
            )
        link = f"{str(base_url).rstrip('/')}/workflow/{encrypted_payload}"
        
        logger.info(f"Delegated document workflow {workflow_id} for document {document_id}")
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": "document_review",
            "link": link,
            "encrypted_payload": encrypted_payload,
            "document_id": document_id,
            "files_included": len(file_references),
        }

    def delegate_deal_flow(
        self,
        deal_id: int,
        sender_user_id: int,
        flow_type: str = "approval",  # "approval", "review", "closure"
        receiver_email: Optional[str] = None,
        receiver_user_id: Optional[int] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_categories: Optional[List[str]] = None,
        expires_in_hours: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate deal flow workflow (approval, review, closure).
        
        Args:
            deal_id: Deal database ID
            sender_user_id: User ID of sender
            flow_type: Type of deal flow ("approval", "review", "closure")
            receiver_email: Optional receiver email address
            receiver_user_id: Optional receiver user ID
            workflow_metadata: Optional workflow-specific metadata
            file_categories: Optional file categories to include
            expires_in_hours: Optional expiration time
            base_url: Optional base URL for link generation
            
        Returns:
            Dictionary with workflow_id, link, and metadata
        """
        # Get deal
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        workflow_id = str(uuid.uuid4())
        
        # Get deal data
        deal_data = {
            "deal_id": deal.deal_id,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "deal_data": deal.deal_data or {},
            "applicant_id": deal.applicant_id,
        }
        
        # Get CDM payload
        cdm_payload = get_deal_cdm_payload(self.db, deal)
        
        # Get file references
        file_references = self._get_file_references(
            deal_id=deal_id,
            file_categories=file_categories,
            workflow_type=WorkflowType.DEAL_APPROVAL if flow_type == "approval" else WorkflowType.DEAL_REVIEW,
        )
        
        # Get whitelist config
        workflow_type = WorkflowType.DEAL_APPROVAL if flow_type == "approval" else WorkflowType.DEAL_REVIEW
        whitelist_config = self.whitelist_service.get_whitelist_for_workflow(
            workflow_type=workflow_type,
            deal_id=deal_id,
        )
        
        # Filter files by whitelist
        file_references = self.whitelist_service.filter_files_by_whitelist(
            file_references, whitelist_config
        )
        
        # Get sender info
        sender = self.db.query(User).filter(User.id == sender_user_id).first()
        sender_info = {
            "user_id": sender_user_id,
            "email": sender.email if sender else None,
            "name": sender.display_name if sender else None,
        }
        
        # Build workflow metadata
        if workflow_metadata is None:
            workflow_metadata = {}
        
        if flow_type == "approval":
            workflow_metadata.setdefault("title", "Deal Approval Request")
            workflow_metadata.setdefault("description", "Please review and approve this deal proposal")
            workflow_metadata.setdefault("required_actions", ["approve", "reject"])
        elif flow_type == "review":
            workflow_metadata.setdefault("title", "Deal Review Request")
            workflow_metadata.setdefault("description", "Please review this deal and provide feedback")
            workflow_metadata.setdefault("required_actions", ["submit_review"])
        else:  # closure
            workflow_metadata.setdefault("title", "Deal Closure Request")
            workflow_metadata.setdefault("description", "Please review and approve deal closure")
            workflow_metadata.setdefault("required_actions", ["approve", "reject"])
        
        # Generate link
        encrypted_payload = self.link_generator.generate_deal_flow_link_payload(
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            flow_type=flow_type,
            cdm_payload=cdm_payload,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            expires_in_hours=expires_in_hours,
        )
        
        # Build full URL
        if not base_url:
            base_url = getattr(settings, "WORKFLOW_DELEGATION_BASE_URL", None) or getattr(settings, "VERIFICATION_BASE_URL", None)
        if not base_url:
            raise ValueError(
                "WORKFLOW_DELEGATION_BASE_URL or VERIFICATION_BASE_URL must be set in configuration. "
                "Please set one of these environment variables."
            )
        link = f"{str(base_url).rstrip('/')}/workflow/{encrypted_payload}"
        
        logger.info(f"Delegated deal flow {flow_type} workflow {workflow_id} for deal {deal_id}")
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": f"deal_{flow_type}",
            "link": link,
            "encrypted_payload": encrypted_payload,
            "deal_id": deal_id,
            "files_included": len(file_references),
        }

    def delegate_custom_workflow(
        self,
        custom_workflow_type: str,
        sender_user_id: int,
        workflow_metadata: Dict[str, Any],
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        receiver_email: Optional[str] = None,
        receiver_user_id: Optional[int] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        expires_in_hours: int = 72,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate custom workflow with extensible metadata.
        
        Args:
            custom_workflow_type: Custom workflow type identifier
            sender_user_id: User ID of sender
            workflow_metadata: Workflow-specific metadata (must include title, description, required_actions)
            deal_id: Optional deal database ID
            document_id: Optional document database ID
            receiver_email: Optional receiver email address
            receiver_user_id: Optional receiver user ID
            file_references: Optional list of file references
            expires_in_hours: Expiration time in hours
            base_url: Optional base URL for link generation
            
        Returns:
            Dictionary with workflow_id, link, and metadata
        """
        workflow_id = str(uuid.uuid4())
        
        # Get deal data if deal_id provided
        deal_data = {}
        cdm_payload = {}
        
        if deal_id:
            deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                deal_data = {
                    "deal_id": deal.deal_id,
                    "status": deal.status,
                    "deal_type": deal.deal_type,
                    "deal_data": deal.deal_data or {},
                }
                cdm_payload = get_deal_cdm_payload(self.db, deal)
        
        # Get file references if not provided
        if file_references is None and deal_id:
            file_references = self._get_file_references(
                deal_id=deal_id,
                workflow_type=WorkflowType.CUSTOM,
            )
        
        # Get whitelist config
        whitelist_config = self.whitelist_service.get_whitelist_for_workflow(
            workflow_type=WorkflowType.CUSTOM,
            deal_id=deal_id,
        )
        
        # Filter files by whitelist if file_references provided
        if file_references:
            file_references = self.whitelist_service.filter_files_by_whitelist(
                file_references, whitelist_config
            )
        
        # Get sender info
        sender = self.db.query(User).filter(User.id == sender_user_id).first()
        sender_info = {
            "user_id": sender_user_id,
            "email": sender.email if sender else None,
            "name": sender.display_name if sender else None,
        }
        
        # Generate link
        encrypted_payload = self.link_generator.generate_custom_workflow_link_payload(
            workflow_id=workflow_id,
            custom_workflow_type=custom_workflow_type,
            workflow_metadata=workflow_metadata,
            deal_id=deal_id,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            expires_in_hours=expires_in_hours,
        )
        
        # Build full URL
        if not base_url:
            base_url = getattr(settings, "WORKFLOW_DELEGATION_BASE_URL", None) or getattr(settings, "VERIFICATION_BASE_URL", None)
        if not base_url:
            raise ValueError(
                "WORKFLOW_DELEGATION_BASE_URL or VERIFICATION_BASE_URL must be set in configuration. "
                "Please set one of these environment variables."
            )
        link = f"{str(base_url).rstrip('/')}/workflow/{encrypted_payload}"
        
        logger.info(f"Delegated custom workflow {custom_workflow_type} ({workflow_id})")
        
        return {
            "workflow_id": workflow_id,
            "workflow_type": custom_workflow_type,
            "link": link,
            "encrypted_payload": encrypted_payload,
            "deal_id": deal_id,
            "document_id": document_id,
            "files_included": len(file_references) if file_references else 0,
        }

    def process_workflow_link(
        self,
        encrypted_payload: str,
        receiver_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process workflow link and create local workflow instance.
        
        Args:
            encrypted_payload: Encrypted workflow link payload
            receiver_user_id: Optional receiver user ID
            
        Returns:
            Dictionary with processed workflow data
        """
        # Parse link payload
        link_data = self.link_generator.parse_workflow_link_payload(encrypted_payload)
        
        if not link_data:
            raise ValueError("Invalid or expired workflow link")
        
        # Update whitelist config if provided and authorized
        if link_data.get("whitelist_config") and receiver_user_id:
            self.whitelist_service.update_whitelist_from_link(
                link_payload=link_data,
                user_id=receiver_user_id,
                require_admin=True,
            )
        
        # Return processed workflow data
        return {
            "workflow_id": link_data.get("workflow_id"),
            "workflow_type": link_data.get("workflow_type"),
            "workflow_metadata": link_data.get("workflow_metadata", {}),
            "deal_id": link_data.get("deal_id"),
            "deal_data": link_data.get("deal_data", {}),
            "cdm_payload": link_data.get("cdm_payload", {}),
            "file_references": link_data.get("file_references", []),
            "sender_info": link_data.get("sender_info", {}),
            "receiver_info": link_data.get("receiver_info", {}),
            "expires_at": link_data.get("expires_at"),
        }

    def sync_workflow_state(
        self,
        workflow_id: str,
        workflow_type: str,
        state: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
    ) -> bool:
        """Sync workflow state to sender via callback URL.
        
        Args:
            workflow_id: Workflow identifier
            workflow_type: Workflow type
            state: New workflow state
            metadata: Optional state metadata
            callback_url: Optional callback URL for state sync
            
        Returns:
            True if sync was successful, False otherwise
        """
        if not callback_url:
            logger.debug(f"No callback URL provided for workflow {workflow_id}")
            return False
        
        try:
            import httpx
            
            payload = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "state": state,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Send state update (with retry logic)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = httpx.post(
                        callback_url,
                        json=payload,
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    logger.info(f"Synced workflow state for {workflow_id} to {callback_url}")
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"State sync attempt {attempt + 1} failed: {e}, retrying...")
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to sync workflow state after {max_retries} attempts: {e}")
                        return False
        except Exception as e:
            logger.error(f"Failed to sync workflow state: {e}")
            return False

    def _get_file_references(
        self,
        deal_id: int,
        file_categories: Optional[List[str]] = None,
        file_document_ids: Optional[List[int]] = None,
        workflow_type: Optional[WorkflowType] = None,
    ) -> List[Dict[str, Any]]:
        """Get file references for deal documents.
        
        Args:
            deal_id: Deal database ID
            file_categories: Optional file categories to filter
            file_document_ids: Optional specific document IDs to include
            workflow_type: Optional workflow type for context
            
        Returns:
            List of file reference dictionaries
        """
        from app.services.file_storage_service import FileStorageService
        
        file_references = []
        
        # Get documents associated with deal
        documents_query = self.db.query(Document).filter(Document.deal_id == deal_id)
        
        # Filter by document IDs if specified
        if file_document_ids:
            documents_query = documents_query.filter(Document.id.in_(file_document_ids))
        
        documents = documents_query.all()
        
        # Get deal for file storage
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return file_references
        
        # Get enabled subdirectories
        enabled_subdirs = self.whitelist_service.file_config.get_enabled_subdirectories()
        
        for subdir in enabled_subdirs:
            if subdir == "documents":
                for doc in documents:
                    # Get latest version
                    latest_version = (
                        self.db.query(DocumentVersion)
                        .filter(DocumentVersion.document_id == doc.id)
                        .order_by(DocumentVersion.version_number.desc())
                        .first()
                    )
                    
                    if latest_version and latest_version.source_filename:
                        # Determine category
                        category = "legal"  # Default category
                        # TODO: Extract category from document metadata or filename
                        
                        # Filter by categories if specified
                        if file_categories and category not in file_categories:
                            continue
                        
                        # Get file size
                        file_size = 0
                        try:
                            file_storage = FileStorageService()
                            deal_docs = file_storage.get_deal_documents(
                                user_id=deal.applicant_id,
                                deal_id=deal.deal_id,
                                subdirectory=subdir
                            )
                            # Find matching file
                            for stored_file in deal_docs:
                                if str(doc.id) in stored_file.get("filename", "") or latest_version.source_filename in stored_file.get("filename", ""):
                                    file_size = stored_file.get("size", 0)
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to get file size for document {doc.id}: {e}")
                        
                        file_references.append({
                            "document_id": doc.id,
                            "filename": latest_version.source_filename,
                            "category": category,
                            "subdirectory": subdir,
                            "size": file_size,
                            "download_url": f"/api/deals/{deal_id}/documents/{doc.id}/download",
                            "title": doc.title or latest_version.source_filename,
                        })
        
        return file_references
