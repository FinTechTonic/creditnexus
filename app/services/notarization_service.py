"""Remote verification & notarization service with enhanced features."""

import logging
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import NotarizationRecord, Deal, VerificationRequest
from app.utils.crypto_verification import (
    verify_ethereum_signature,
    generate_nonce,
    generate_signing_message,
    compute_payload_hash,
)
from app.models.cdm_events import generate_cdm_notarization_event

logger = logging.getLogger(__name__)


class NotarizationService:
    """Service for managing notarization records with CDM events."""

    def __init__(self, db: Session):
        """Initialize notarization service.

        Args:
            db: Database session
        """
        self.db = db

    def create_notarization_request(
        self, deal_id: int, required_signers: List[str], message_prefix: Optional[str] = None
    ) -> NotarizationRecord:
        """Create a new notarization request.

        Args:
            deal_id: Deal ID
            required_signers: List of wallet addresses
            message_prefix: Optional prefix for signing message

        Returns:
            Created NotarizationRecord
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()

        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        # Get or create CDM payload
        cdm_payload = self._get_deal_cdm_payload(deal)

        # Generate hash
        notarization_hash = compute_payload_hash(cdm_payload)

        record = NotarizationRecord(
            deal_id=deal_id,
            notarization_hash=notarization_hash,
            required_signers=required_signers,
            signatures=[],
            status="pending",
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        # Update deal
        deal.notarization_required = True
        self.db.commit()

        logger.info(
            f"Created notarization request: deal_id={deal_id}, signers={len(required_signers)}"
        )

        return record

    def generate_signing_message(
        self, notarization: NotarizationRecord, wallet_address: str
    ) -> str:
        """Generate message for wallet to sign.

        Args:
            notarization: Notarization record
            wallet_address: Signer's wallet address

        Returns:
            Message to sign
        """
        nonce = generate_nonce()
        timestamp = datetime.utcnow().isoformat()

        prefix = "CreditNexus Notarization"

        return generate_signing_message(
            nonce=nonce, timestamp=timestamp, deal_id=notarization.deal_id, verification_id=None
        )

    def verify_and_store_signature(
        self, notarization_id: int, wallet_address: str, signature: str, message: str
    ) -> NotarizationRecord:
        """Verify signature and store in notarization record.

        Args:
            notarization_id: Notarization record ID
            wallet_address: Signer's wallet address
            signature: Ethereum signature
            message: Message that was signed

        Returns:
            Updated NotarizationRecord

        Raises:
            ValueError: If notarization not found or signature invalid
        """
        notarization = (
            self.db.query(NotarizationRecord)
            .filter(NotarizationRecord.id == notarization_id)
            .first()
        )

        if not notarization:
            raise ValueError(f"Notarization {notarization_id} not found")

        # Verify signature
        is_valid = verify_ethereum_signature(
            message=message, signature=signature, wallet_address=wallet_address
        )

        if not is_valid:
            raise ValueError("Invalid signature")

        # Check if signer is in required signers list
        if wallet_address.lower() not in [s.lower() for s in notarization.required_signers]:
            raise ValueError("Signer not in required signers list")

        # Check if already signed
        signatures = notarization.signatures or []
        if any(s.get("wallet_address", "").lower() == wallet_address.lower() for s in signatures):
            raise ValueError("Already signed")

        # Add signature
        signature_data = {
            "wallet_address": wallet_address.lower(),
            "signature": signature,
            "signed_at": datetime.utcnow().isoformat(),
            "message": message,
        }

        signatures.append(signature_data)

        # Check if all signers have signed
        if len(signatures) >= len(notarization.required_signers):
            notarization.status = "signed"
            notarization.completed_at = datetime.utcnow()

            # Generate CDM event
            try:
                cdm_event = generate_cdm_notarization_event(
                    notarization_id=str(notarization.id),
                    deal_id=str(notarization.deal_id),
                    signers=signatures,
                    notarization_hash=notarization.notarization_hash,
                )
                notarization.cdm_event_id = (
                    cdm_event.get("meta", {})
                    .get("globalKey", {})
                    .get("assignedIdentifier", [{}])[0]
                    .get("identifier", {})
                    .get("value", "")
                )
                logger.info(f"Generated CDM notarization event: {notarization.cdm_event_id}")
            except Exception as e:
                logger.error(f"Failed to generate CDM notarization event: {e}")

        self.db.commit()
        self.db.refresh(notarization)

        logger.info(
            f"Signature added to notarization {notarization_id}: "
            f"wallet={wallet_address}, "
            f"signatures={len(signatures)}/{len(notarization.required_signers)}"
        )

        return notarization

    def complete_notarization(self, notarization_id: int) -> NotarizationRecord:
        """Mark notarization as completed (after all signatures collected).

        Args:
            notarization_id: Notarization record ID

        Returns:
            Updated NotarizationRecord

        Raises:
            ValueError: If notarization not found or not all signatures collected
        """
        notarization = (
            self.db.query(NotarizationRecord)
            .filter(NotarizationRecord.id == notarization_id)
            .first()
        )

        if not notarization:
            raise ValueError(f"Notarization {notarization_id} not found")

        # Verify all required signers have signed
        signed_addresses = [
            s["wallet_address"] for s in notarization.signatures if isinstance(s, dict)
        ]
        required_addresses = [s.lower() for s in notarization.required_signers]

        if set(signed_addresses) != set(required_addresses):
            raise ValueError(
                f"Not all required signers have signed. "
                f"Missing: {set(required_addresses) - set(signed_addresses)}"
            )

        notarization.status = "signed"
        notarization.completed_at = datetime.utcnow()

        # Update deal
        deal = self.db.query(Deal).filter(Deal.id == notarization.deal_id).first()
        if deal:
            deal.notarization_completed_at = datetime.utcnow()
            self.db.commit()

        self.db.commit()
        self.db.refresh(notarization)

        logger.info(f"Completed notarization {notarization_id}")

        return notarization

    def _get_deal_cdm_payload(self, deal: Deal) -> Dict[str, Any]:
        """Get CDM payload for deal."""
        # TODO: Implement full CDM payload generation from deal.deal_data
        return {
            "deal_id": deal.id,
            "deal_id_str": deal.deal_id,
            "borrower_name": "",  # TODO: Extract from deal data
            "total_commitment": "",  # TODO: Extract from deal data
            "currency": "",  # TODO: Extract from deal data
            "sustainability_covenants": [],  # TODO: Extract from deal data
        }
