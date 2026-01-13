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
                    deal_id=str(notarization.deal_id) if notarization.deal_id else "",
                    signers=signatures,
                    notarization_hash=notarization.notarization_hash,
                )
                # Extract globalKey value from CDM event
                global_key = cdm_event.get("meta", {}).get("globalKey", {})
                if isinstance(global_key, dict):
                    assigned_id = global_key.get("assignedIdentifier", [{}])[0]
                    notarization.cdm_event_id = assigned_id.get("identifier", {}).get("value", "")
                else:
                    # Fallback for string format
                    notarization.cdm_event_id = str(global_key) if global_key else ""
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
        """Get CDM payload for deal.
        
        Extracts CDM data from:
        1. Deal.deal_data JSONB field
        2. Associated documents' source_cdm_data
        3. Document versions' extracted_data
        
        Args:
            deal: Deal instance
            
        Returns:
            CDM payload dictionary
        """
        from app.db.models import Document, DocumentVersion
        from decimal import Decimal
        
        # Initialize payload with deal identifiers
        payload = {
            "deal_id": deal.id,
            "deal_id_str": deal.deal_id,
            "borrower_name": "",
            "total_commitment": None,
            "currency": "USD",  # Default currency
            "sustainability_covenants": [],
        }
        
        # Try to get CDM data from deal.deal_data first
        if deal.deal_data and isinstance(deal.deal_data, dict):
            # Extract borrower name
            if "borrower_name" in deal.deal_data:
                payload["borrower_name"] = deal.deal_data["borrower_name"]
            elif "borrower" in deal.deal_data:
                borrower = deal.deal_data["borrower"]
                if isinstance(borrower, dict):
                    payload["borrower_name"] = borrower.get("name", "")
                elif isinstance(borrower, str):
                    payload["borrower_name"] = borrower
            
            # Extract total commitment
            if "total_commitment" in deal.deal_data:
                commitment = deal.deal_data["total_commitment"]
                if isinstance(commitment, (int, float, Decimal)):
                    payload["total_commitment"] = float(commitment)
                elif isinstance(commitment, dict):
                    payload["total_commitment"] = float(commitment.get("amount", 0))
                    payload["currency"] = commitment.get("currency", "USD")
            
            # Extract currency
            if "currency" in deal.deal_data:
                payload["currency"] = deal.deal_data["currency"]
            
            # Extract sustainability covenants
            if "sustainability_covenants" in deal.deal_data:
                payload["sustainability_covenants"] = deal.deal_data["sustainability_covenants"]
            elif "esg_kpi_targets" in deal.deal_data:
                payload["sustainability_covenants"] = deal.deal_data["esg_kpi_targets"]
            elif "sustainability_provisions" in deal.deal_data:
                provisions = deal.deal_data["sustainability_provisions"]
                if isinstance(provisions, dict):
                    payload["sustainability_covenants"] = provisions.get("covenants", [])
        
        # If borrower_name or total_commitment missing, try documents
        if not payload["borrower_name"] or not payload["total_commitment"]:
            documents = self.db.query(Document).filter(Document.deal_id == deal.id).all()
            
            for doc in documents:
                # Try source_cdm_data first
                if doc.source_cdm_data and isinstance(doc.source_cdm_data, dict):
                    cdm_data = doc.source_cdm_data
                    
                    # Extract borrower from parties
                    if not payload["borrower_name"] and "parties" in cdm_data:
                        parties = cdm_data["parties"]
                        if isinstance(parties, list):
                            for party in parties:
                                if isinstance(party, dict):
                                    role = party.get("role", "").lower()
                                    if "borrower" in role:
                                        payload["borrower_name"] = party.get("name", "")
                                        break
                    
                    # Extract total commitment from facilities
                    if not payload["total_commitment"] and "facilities" in cdm_data:
                        facilities = cdm_data["facilities"]
                        if isinstance(facilities, list):
                            total = Decimal("0")
                            for facility in facilities:
                                if isinstance(facility, dict):
                                    commitment = facility.get("commitment_amount") or facility.get("amount")
                                    if commitment:
                                        if isinstance(commitment, dict):
                                            amount = commitment.get("amount", 0)
                                            if not payload["currency"] and commitment.get("currency"):
                                                payload["currency"] = commitment["currency"]
                                        else:
                                            amount = commitment
                                        total += Decimal(str(amount))
                            if total > 0:
                                payload["total_commitment"] = float(total)
                    
                    # Extract sustainability covenants
                    if not payload["sustainability_covenants"]:
                        if "sustainability_linked" in cdm_data and cdm_data["sustainability_linked"]:
                            if "esg_kpi_targets" in cdm_data:
                                payload["sustainability_covenants"] = cdm_data["esg_kpi_targets"]
                            elif "sustainability_provisions" in cdm_data:
                                provisions = cdm_data["sustainability_provisions"]
                                if isinstance(provisions, dict):
                                    payload["sustainability_covenants"] = provisions.get("covenants", [])
                    
                    # If we found all required data, break
                    if payload["borrower_name"] and payload["total_commitment"]:
                        break
                
                # Try latest document version extracted_data
                if not payload["borrower_name"] or not payload["total_commitment"]:
                    latest_version = (
                        self.db.query(DocumentVersion)
                        .filter(DocumentVersion.document_id == doc.id)
                        .order_by(DocumentVersion.version_number.desc())
                        .first()
                    )
                    
                    if latest_version and latest_version.extracted_data:
                        extracted = latest_version.extracted_data
                        if isinstance(extracted, dict) and "agreement" in extracted:
                            agreement = extracted["agreement"]
                            
                            # Extract borrower from parties
                            if not payload["borrower_name"] and "parties" in agreement:
                                parties = agreement["parties"]
                                if isinstance(parties, list):
                                    for party in parties:
                                        if isinstance(party, dict):
                                            role = party.get("role", "").lower()
                                            if "borrower" in role:
                                                payload["borrower_name"] = party.get("name", "")
                                                break
                            
                            # Extract total commitment
                            if not payload["total_commitment"]:
                                if "total_commitment" in agreement:
                                    payload["total_commitment"] = float(agreement["total_commitment"])
                                elif "facilities" in agreement:
                                    facilities = agreement["facilities"]
                                    if isinstance(facilities, list):
                                        total = Decimal("0")
                                        for facility in facilities:
                                            if isinstance(facility, dict):
                                                amount = facility.get("amount", 0)
                                                if amount:
                                                    total += Decimal(str(amount))
                                                if not payload["currency"] and facility.get("currency"):
                                                    payload["currency"] = facility["currency"]
                                        if total > 0:
                                            payload["total_commitment"] = float(total)
                            
                            # Extract sustainability
                            if not payload["sustainability_covenants"]:
                                if agreement.get("sustainability_linked"):
                                    if "esg_kpi_targets" in agreement:
                                        payload["sustainability_covenants"] = agreement["esg_kpi_targets"]
                            
                            # If we found all required data, break
                            if payload["borrower_name"] and payload["total_commitment"]:
                                break
        
        # Ensure total_commitment is a number (not empty string)
        if payload["total_commitment"] == "":
            payload["total_commitment"] = None
        
        logger.info(
            f"Generated CDM payload for deal {deal.deal_id}: "
            f"borrower={payload['borrower_name']}, "
            f"commitment={payload['total_commitment']} {payload['currency']}"
        )
        
        return payload