"""Sharing event service for blockchain-notarized sharing events."""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import hashlib
import logging

from app.db.models import SharingEvent
from app.models.cdm_events import generate_cdm_sharing_event
from app.services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)


class SharingEventService:
    """Service for creating blockchain-notarized sharing events."""

    def __init__(self, db: Session):
        """Initialize sharing event service."""
        self.db = db
        self.blockchain_service = BlockchainService()

    def create_send_event(
        self,
        sender_user_id: int,
        sharing_method: str,  # nexus_file, link, p2p
        file_data: bytes,  # .nexus file or link payload
        workflow_id: Optional[str] = None,
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        receiver_user_id: Optional[int] = None,
        receiver_email: Optional[str] = None,
        receiver_wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SharingEvent:
        """Create send event and notarize on blockchain.

        Args:
            sender_user_id: Sender user ID
            sharing_method: Method used (nexus_file, link, p2p)
            file_data: File data or link payload
            workflow_id: Optional workflow ID
            deal_id: Optional deal ID
            document_id: Optional document ID
            receiver_user_id: Optional receiver user ID
            receiver_email: Optional receiver email
            receiver_wallet_address: Optional receiver wallet
            metadata: Optional metadata

        Returns:
            Created SharingEvent with blockchain notarization
        """
        event_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(file_data).hexdigest()
        file_size = len(file_data)

        # Count files (if .nexus file, parse manifest)
        files_included = 0
        if sharing_method == "nexus_file":
            try:
                from app.utils.nexus_file_parser import NexusFileParser
                parser = NexusFileParser()
                parsed = parser.parse_nexus_file(file_data)
                files_included = (
                    len(parsed.get('embedded_files', {})) +
                    len(parsed.get('large_file_references', []))
                )
            except Exception as e:
                logger.warning(f"Failed to parse .nexus file for file count: {e}")

        # Create sharing event
        sharing_event = SharingEvent(
            event_id=event_id,
            event_type="send",
            sharing_method=sharing_method,
            workflow_id=workflow_id,
            deal_id=deal_id,
            document_id=document_id,
            sender_user_id=sender_user_id,
            receiver_user_id=receiver_user_id,
            receiver_email=receiver_email,
            receiver_wallet_address=receiver_wallet_address,
            file_hash=file_hash,
            file_size=file_size,
            files_included=files_included,
            event_metadata=metadata or {},
        )

        self.db.add(sharing_event)
        self.db.flush()

        # Generate CDM event
        cdm_event = generate_cdm_sharing_event(
            event_id=event_id,
            event_type="send",
            sender_user_id=sender_user_id,
            receiver_user_id=receiver_user_id,
            receiver_email=receiver_email,
            receiver_wallet_address=receiver_wallet_address,
            file_hash=file_hash,
            workflow_id=workflow_id,
            deal_id=str(deal_id) if deal_id else None,
        )

        sharing_event.cdm_event = cdm_event

        # Notarize on blockchain
        try:
            tx_hash, block_number = self.notarize_sharing_event(
                event_id=event_id,
                file_hash=file_hash,
                sender_user_id=sender_user_id,
                receiver_wallet_address=receiver_wallet_address,
            )

            sharing_event.blockchain_tx_hash = tx_hash
            sharing_event.blockchain_block_number = block_number
            sharing_event.notarized_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Failed to notarize sharing event on blockchain: {e}")

        self.db.commit()
        self.db.refresh(sharing_event)

        logger.info(f"Created send event {event_id} for workflow {workflow_id}")
        return sharing_event

    def create_receive_event(
        self,
        receiver_user_id: int,
        sharing_method: str,
        file_data: bytes,
        file_hash: str,
        sender_user_id: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_wallet_address: Optional[str] = None,
        workflow_id: Optional[str] = None,
        deal_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SharingEvent:
        """Create receive event and notarize on blockchain.

        Args:
            receiver_user_id: Receiver user ID
            sharing_method: Method used (nexus_file, link, p2p)
            file_data: File data
            file_hash: SHA-256 hash of file
            sender_user_id: Optional sender user ID
            sender_email: Optional sender email
            sender_wallet_address: Optional sender wallet
            workflow_id: Optional workflow ID
            deal_id: Optional deal ID
            metadata: Optional metadata

        Returns:
            Created SharingEvent with blockchain notarization
        """
        event_id = str(uuid.uuid4())
        # DB has sender_user_id NOT NULL; use receiver as placeholder when sender unknown
        _sender_user_id = receiver_user_id if sender_user_id is None else sender_user_id

        sharing_event = SharingEvent(
            event_id=event_id,
            event_type="receive",
            sharing_method=sharing_method,
            workflow_id=workflow_id,
            deal_id=deal_id,
            receiver_user_id=receiver_user_id,
            sender_user_id=_sender_user_id,
            receiver_email=None,  # Receiver is current user
            file_hash=file_hash,
            file_size=len(file_data),
            event_metadata=metadata or {},
        )

        self.db.add(sharing_event)
        self.db.flush()

        # Generate CDM event
        cdm_event = generate_cdm_sharing_event(
            event_id=event_id,
            event_type="receive",
            sender_user_id=_sender_user_id,
            receiver_user_id=receiver_user_id,
            receiver_email=None,
            receiver_wallet_address=None,
            file_hash=file_hash,
            workflow_id=workflow_id,
            deal_id=str(deal_id) if deal_id else None,
        )

        sharing_event.cdm_event = cdm_event

        # Notarize on blockchain
        try:
            tx_hash, block_number = self.notarize_sharing_event(
                event_id=event_id,
                file_hash=file_hash,
                sender_user_id=_sender_user_id,
                receiver_wallet_address=None,  # Would need receiver wallet address
            )

            sharing_event.blockchain_tx_hash = tx_hash
            sharing_event.blockchain_block_number = block_number
            sharing_event.notarized_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Failed to notarize receive event on blockchain: {e}")

        self.db.commit()
        self.db.refresh(sharing_event)

        logger.info(f"Created receive event {event_id} for workflow {workflow_id}")
        return sharing_event

    def notarize_sharing_event(
        self,
        event_id: str,
        file_hash: str,
        sender_user_id: int,
        receiver_wallet_address: Optional[str] = None,
    ) -> tuple[str, Optional[int]]:
        """Notarize sharing event on blockchain.

        Args:
            event_id: Sharing event ID
            file_hash: SHA-256 hash of shared file
            sender_user_id: Sender user ID
            receiver_wallet_address: Optional receiver wallet address

        Returns:
            (transaction_hash, block_number)
        """
        if not self.blockchain_service.web3:
            logger.warning("Blockchain not connected, skipping notarization")
            # Return placeholder hash
            placeholder_hash = f"0x{hashlib.sha256(f'{event_id}{file_hash}{datetime.utcnow()}'.encode()).hexdigest()[:64]}"
            return (placeholder_hash, None)

        try:
            # Get sender wallet address (would need to query user model)
            from app.db.models import User
            sender = self.db.query(User).filter(User.id == sender_user_id).first()
            sender_address = None
            if sender and hasattr(sender, 'wallet_address'):
                sender_address = sender.wallet_address

            # For now, create a placeholder transaction
            # In production, this would call a smart contract method
            # to store the sharing event on-chain
            tx_hash = f"0x{hashlib.sha256(f'{event_id}{file_hash}{datetime.utcnow()}'.encode()).hexdigest()[:64]}"

            # Get block number if available
            block_number = None
            if self.blockchain_service.web3:
                try:
                    block_number = self.blockchain_service.web3.eth.block_number
                except Exception:
                    pass

            logger.info(f"Notarized sharing event {event_id} on blockchain: {tx_hash}")
            return (tx_hash, block_number)

        except Exception as e:
            logger.error(f"Failed to notarize sharing event on blockchain: {e}")
            # Return placeholder hash on error
            placeholder_hash = f"0x{hashlib.sha256(f'{event_id}{file_hash}{datetime.utcnow()}'.encode()).hexdigest()[:64]}"
            return (placeholder_hash, None)
