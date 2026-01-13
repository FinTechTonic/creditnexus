"""
Filing Service for CreditNexus.

Handles:
- Companies House API integration (UK - automated)
- Manual filing UI preparation (US, FR, DE - pre-filled forms)
- Filing status tracking
"""

import logging
import requests
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentFiling, Deal, DocumentVersion
from app.core.config import settings
from app.services.policy_service import PolicyService, FilingRequirement
from app.services.policy_engine_factory import get_policy_engine
from app.models.cdm import CreditAgreement
from app.chains.filing_requirement_chain import evaluate_filing_requirements
from app.chains.filing_form_generation_chain import generate_filing_form_data

logger = logging.getLogger(__name__)


class FilingService:
    """Service for managing regulatory filings."""

    def __init__(self, db: Session):
        """
        Initialize filing service.

        Args:
            db: Database session
        """
        self.db = db
        self.companies_house_api_key = settings.COMPANIES_HOUSE_API_KEY
        self.companies_house_base_url = "https://api.company-information.service.gov.uk"
        self.policy_service = PolicyService(get_policy_engine())

    def determine_filing_requirements(
        self,
        document_id: int,
        agreement_type: str,
        jurisdiction: Optional[str] = None,
        deal_id: Optional[int] = None,
        use_ai_evaluation: bool = True
    ) -> List[FilingRequirement]:
        """
        Determine what needs to be filed and where using AI-assisted evaluation.

        Args:
            document_id: Document ID
            agreement_type: Type of agreement
            jurisdiction: Optional jurisdiction override
            deal_id: Optional deal ID
            use_ai_evaluation: Use LangChain AI chain for evaluation

        Returns:
            List of FilingRequirement objects
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Load CDM data
        if not document.source_cdm_data:
            raise ValueError(f"Document {document_id} has no CDM data")

        credit_agreement = CreditAgreement(**document.source_cdm_data)

        # Use LangChain AI chain for filing requirement evaluation
        if use_ai_evaluation:
            evaluation = evaluate_filing_requirements(
                credit_agreement=credit_agreement,
                document_id=document_id,
                deal_id=deal_id,
                agreement_type=agreement_type
            )

            # Convert FilingRequirement models to dataclasses
            requirements = []
            for req in evaluation.required_filings:
                requirements.append(FilingRequirement(
                    authority=req.authority,
                    filing_system=req.filing_system,
                    deadline=req.deadline,
                    required_fields=req.required_fields,
                    api_available=req.api_available,
                    api_endpoint=req.api_endpoint,
                    penalty=req.penalty,
                    language_requirement=req.language_requirement,
                    jurisdiction=req.jurisdiction,
                    agreement_type=req.agreement_type,
                    form_type=req.form_type,
                    priority=req.priority
                ))
            return requirements
        else:
            # Fallback to PolicyService (if not using AI)
            decision = self.policy_service.evaluate_filing_requirements(
                credit_agreement=credit_agreement,
                document_id=document_id,
                deal_id=deal_id
            )
            return decision.required_filings

    def file_document_automatically(
        self,
        document_id: int,
        filing_requirement: FilingRequirement
    ) -> DocumentFiling:
        """
        File a document automatically via API (UK only).

        Args:
            document_id: Document ID
            filing_requirement: FilingRequirement object

        Returns:
            DocumentFiling instance
        """
        if filing_requirement.filing_system != "companies_house_api":
            raise ValueError(f"Automatic filing not supported for {filing_requirement.filing_system}")

        # Companies House API integration
        return self._file_companies_house(document_id, filing_requirement)

    def prepare_manual_filing(
        self,
        document_id: int,
        filing_requirement: FilingRequirement
    ) -> DocumentFiling:
        """
        Prepare a manual filing with AI-generated pre-filled form data.

        Args:
            document_id: Document ID
            filing_requirement: FilingRequirement object

        Returns:
            DocumentFiling instance with pre-filled form data
        """
        # 1. Load document and CDM data
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        if not document.source_cdm_data:
            raise ValueError(f"Document {document_id} has no CDM data")

        credit_agreement = CreditAgreement(**document.source_cdm_data)

        # 2. Use LangChain AI chain to generate pre-filled form data
        form_data = generate_filing_form_data(
            credit_agreement=credit_agreement,
            filing_requirement=filing_requirement,
            document_id=document_id,
            deal_id=document.deal_id
        )

        # 3. Create DocumentFiling record with pre-filled form data
        filing = DocumentFiling(
            document_id=document_id,
            deal_id=document.deal_id,
            agreement_type=filing_requirement.agreement_type or "facility_agreement",
            jurisdiction=filing_requirement.jurisdiction or "Unknown",
            filing_authority=filing_requirement.authority,
            filing_system="manual_ui",
            filing_status="pending",
            filing_payload=form_data.model_dump(),  # Store pre-filled form data
            manual_submission_url=form_data.submission_url,
            deadline=filing_requirement.deadline
        )

        self.db.add(filing)
        self.db.commit()
        self.db.refresh(filing)

        logger.info(f"Prepared manual filing for document {document_id}: {filing_requirement.authority}")
        return filing

    def _file_companies_house(
        self,
        document_id: int,
        filing_requirement: FilingRequirement
    ) -> DocumentFiling:
        """
        File charge with Companies House API.

        Args:
            document_id: Document ID
            filing_requirement: FilingRequirement object

        Returns:
            DocumentFiling instance
        """
        # 1. Load document and CDM data
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 2. Extract company number from CDM data
        company_number = self._extract_company_number(document)
        if not company_number:
            raise ValueError("UK company number not found in document data")

        # 3. Prepare charge filing payload
        charge_data = {
            "charge_code": "MR01",  # Charge creation form
            "charge_creation_date": (
                document.agreement_date.isoformat()
                if document.agreement_date
                else datetime.utcnow().date().isoformat()
            ),
            "charge_description": self._generate_charge_description(document),
            "persons_entitled": self._extract_lenders(document),
            "secured_amount": {
                "amount": float(document.total_commitment) if document.total_commitment else 0,
                "currency": document.currency or "GBP"
            }
        }

        # 4. Submit to Companies House API
        api_key_value = (
            self.companies_house_api_key.get_secret_value()
            if hasattr(self.companies_house_api_key, 'get_secret_value')
            else str(self.companies_house_api_key)
        )
        auth_string = base64.b64encode(f"{api_key_value}:".encode()).decode()

        response = requests.post(
            f"{self.companies_house_base_url}/company/{company_number}/charges",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            },
            json=charge_data,
            timeout=30
        )

        if not response.ok:
            error_msg = f"Companies House API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        response_data = response.json()

        # 5. Create DocumentFiling record
        filing = DocumentFiling(
            document_id=document_id,
            deal_id=document.deal_id,
            agreement_type=filing_requirement.agreement_type or "facility_agreement",
            jurisdiction="UK",
            filing_authority="Companies House",
            filing_system="companies_house_api",
            filing_reference=response_data.get("transaction_id") or response_data.get("filing_id"),
            filing_status="submitted",
            filing_payload=charge_data,
            filing_response=response_data,
            filing_url=response_data.get("filing_url"),
            confirmation_url=response_data.get("confirmation_url"),
            filed_at=datetime.utcnow(),
            deadline=filing_requirement.deadline
        )

        self.db.add(filing)
        self.db.commit()
        self.db.refresh(filing)

        logger.info(f"Filed charge with Companies House for document {document_id}: {filing.filing_reference}")
        return filing

    def _extract_company_number(self, document: Document) -> Optional[str]:
        """Extract UK company number from document CDM data."""
        # Try to get from document version CDM data
        if document.current_version_id:
            version = self.db.query(DocumentVersion).filter(
                DocumentVersion.id == document.current_version_id
            ).first()
            if version and version.cdm_data:
                # Extract from parties with UK jurisdiction
                parties = version.cdm_data.get("parties", [])
                for party in parties:
                    if party.get("jurisdiction") == "UK" and party.get("company_number"):
                        return party["company_number"]

        # Try to get from document source_cdm_data
        if document.source_cdm_data:
            parties = document.source_cdm_data.get("parties", [])
            for party in parties:
                if isinstance(party, dict):
                    if party.get("jurisdiction") == "UK" and party.get("company_number"):
                        return party["company_number"]
                else:
                    # Pydantic model
                    if hasattr(party, 'jurisdiction') and hasattr(party, 'company_number'):
                        if party.jurisdiction == "UK" and party.company_number:
                            return party.company_number

        return None

    def _generate_charge_description(self, document: Document) -> str:
        """Generate charge description from document."""
        return f"Charge securing credit facility agreement dated {document.agreement_date or 'N/A'}"

    def _extract_lenders(self, document: Document) -> List[Dict[str, str]]:
        """Extract lender information from document."""
        lenders = []
        
        # Try to get from document source_cdm_data
        if document.source_cdm_data:
            parties = document.source_cdm_data.get("parties", [])
            for party in parties:
                if isinstance(party, dict):
                    roles = party.get("roles", [])
                    if any("Lender" in str(role) for role in roles):
                        lenders.append({
                            "name": party.get("name", ""),
                            "lei": party.get("lei")
                        })
                else:
                    # Pydantic model
                    if hasattr(party, 'roles'):
                        roles = party.roles if isinstance(party.roles, list) else [party.roles]
                        if any("Lender" in str(role) for role in roles):
                            lenders.append({
                                "name": party.name if hasattr(party, 'name') else "",
                                "lei": party.lei if hasattr(party, 'lei') else None
                            })

        return lenders

    def _generate_form_data(self, document: Document, requirement: FilingRequirement) -> Dict[str, Any]:
        """Generate pre-filled form data based on jurisdiction."""
        form_data = {}

        if requirement.jurisdiction == "US":
            form_data = {
                "form_type": requirement.form_type or "8-K",
                "company_name": document.borrower_name,
                "agreement_date": document.agreement_date.isoformat() if document.agreement_date else None,
                "total_commitment": str(document.total_commitment) if document.total_commitment else None,
                "currency": document.currency
            }
        elif requirement.jurisdiction == "FR":
            form_data = {
                "company_name": document.borrower_name,
                "agreement_date": document.agreement_date.isoformat() if document.agreement_date else None,
                "total_commitment": str(document.total_commitment) if document.total_commitment else None,
                "currency": document.currency
            }
        elif requirement.jurisdiction == "DE":
            form_data = {
                "company_name": document.borrower_name,
                "agreement_date": document.agreement_date.isoformat() if document.agreement_date else None,
                "total_commitment": str(document.total_commitment) if document.total_commitment else None,
                "currency": document.currency
            }

        return form_data

    def _get_manual_submission_url(self, requirement: FilingRequirement) -> str:
        """Get manual submission portal URL for filing authority."""
        urls = {
            "SEC": "https://www.sec.gov/edgar/searchedgar/companysearch.html",
            "AMF": "https://www.amf-france.org/en/your-requests/declarations",
            "BaFin": "https://www.bafin.de/EN/Aufsicht/Unternehmen/Unternehmen_node_en.html",
            "Tribunal de Commerce": "https://www.infogreffe.fr/",
            "Handelsregister": "https://www.handelsregister.de/",
            "CFIUS": "https://home.treasury.gov/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius",
            "UK Government (NSIA)": "https://www.gov.uk/government/organisations/investment-security-unit"
        }
        return urls.get(requirement.authority, "")

    def update_manual_filing_status(
        self,
        filing_id: int,
        filing_reference: str,
        submission_notes: Optional[str] = None,
        submitted_by: Optional[int] = None
    ) -> DocumentFiling:
        """
        Update manual filing status after user submits via external portal.

        Args:
            filing_id: DocumentFiling ID
            filing_reference: External filing reference from portal
            submission_notes: Optional notes from user
            submitted_by: User ID who submitted

        Returns:
            Updated DocumentFiling instance
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")

        filing.filing_status = "submitted"
        filing.filing_reference = filing_reference
        filing.submitted_by = submitted_by
        filing.submitted_at = datetime.utcnow()
        filing.submission_notes = submission_notes

        self.db.commit()
        self.db.refresh(filing)

        logger.info(f"Updated manual filing {filing_id} status to submitted: {filing_reference}")
        return filing
