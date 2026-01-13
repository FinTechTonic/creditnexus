"""CDM payload generation utility for deals."""

import logging
from typing import Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session

from app.db.models import Deal, Document, DocumentVersion

logger = logging.getLogger(__name__)


def get_deal_cdm_payload(db: Session, deal: Deal) -> Dict[str, Any]:
    """Get CDM payload for deal.
    
    Extracts CDM data from:
    1. Deal.deal_data JSONB field
    2. Associated documents' source_cdm_data
    3. Document versions' extracted_data
    
    Args:
        db: Database session
        deal: Deal instance
        
    Returns:
        CDM payload dictionary
    """
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
        documents = db.query(Document).filter(Document.deal_id == deal.id).all()
        
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
                    db.query(DocumentVersion)
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
