"""
Filing service for regulatory filing of securitization documents and credit agreements.

Handles generation and submission of regulatory documents to SEC, FINRA, etc.
Also handles document filing requirements evaluation and submission.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
import time
import hashlib
import json

from app.utils import get_debug_log_path
# Business days calculation
def add_business_days(start_date: date, days: int) -> date:
    """Add business days to a date (excludes weekends).
    
    Args:
        start_date: Starting date
        days: Number of business days to add
        
    Returns:
        Date after adding business days
    """
    current_date = start_date
    days_added = 0
    
    while days_added < days:
        current_date += timedelta(days=1)
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:  # Monday=0 to Friday=4
            days_added += 1
    
    return current_date

from sqlalchemy.orm import Session

from app.db.models import (
    SecuritizationPool, RegulatoryFiling, GeneratedDocument, User,
    Document, DocumentVersion, DocumentFiling
)
from app.services.securitization_template_service import SecuritizationTemplateService
from app.services.policy_service import PolicyService, FilingRequirement as PolicyFilingRequirement
from app.services.policy_engine_factory import get_policy_engine
from app.models.cdm import CreditAgreement
from app.models.filing_forms import FilingFormData
from app.chains.filing_requirement_chain import evaluate_filing_requirements as evaluate_filing_requirements_chain
from app.chains.filing_form_generation_chain import generate_filing_form_data
from app.services.companies_house_client import CompaniesHouseAPIClient
from app.utils.audit import log_audit_action
from app.db.models import AuditAction
from app.templates.securitization import (
    generate_psa_template,
    generate_trust_agreement_template,
    generate_prospectus_template
)

logger = logging.getLogger(__name__)


from app.services.filing_exceptions import FilingError, FilingAPIError


class FilingService:
    """Service for managing regulatory filings for securitization pools and documents."""
    
    # In-memory cache for filing requirements (document_id -> requirements)
    # Cache expires after 1 hour or when document is updated
    _filing_requirements_cache: Dict[str, tuple] = {}  # key -> (requirements, timestamp)
    _cache_ttl_seconds = 3600  # 1 hour
    
    def __init__(self, db: Session):
        """Initialize filing service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.template_service = SecuritizationTemplateService(db)
        # Initialize policy service for filing requirements
        try:
            policy_engine = get_policy_engine()
            self.policy_service = PolicyService(policy_engine) if policy_engine else None
        except Exception as e:
            logger.warning(f"Could not initialize policy service: {e}")
            self.policy_service = None
    
    def _get_cache_key(
        self,
        document_id: int,
        agreement_type: str,
        deal_id: Optional[int] = None
    ) -> str:
        """Generate cache key for filing requirements.
        
        Args:
            document_id: Document ID
            agreement_type: Agreement type
            deal_id: Optional deal ID
            
        Returns:
            Cache key string
        """
        key_data = {
            "document_id": document_id,
            "agreement_type": agreement_type,
            "deal_id": deal_id
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_cached_requirements(
        self,
        cache_key: str
    ) -> Optional[List[PolicyFilingRequirement]]:
        """Get cached filing requirements if available and not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached requirements or None if not found/expired
        """
        if cache_key not in self._filing_requirements_cache:
            return None
        
        requirements, timestamp = self._filing_requirements_cache[cache_key]
        
        # Check if cache is expired
        age_seconds = (datetime.utcnow() - timestamp).total_seconds()
        if age_seconds > self._cache_ttl_seconds:
            # Cache expired, remove it
            del self._filing_requirements_cache[cache_key]
            logger.debug(f"Cache expired for key {cache_key[:8]}...")
            return None
        
        logger.debug(f"Cache hit for key {cache_key[:8]}... (age: {age_seconds:.0f}s)")
        return requirements
    
    def _cache_requirements(
        self,
        cache_key: str,
        requirements: List[PolicyFilingRequirement]
    ) -> None:
        """Cache filing requirements.
        
        Args:
            cache_key: Cache key
            requirements: Requirements to cache
        """
        self._filing_requirements_cache[cache_key] = (requirements, datetime.utcnow())
        logger.debug(f"Cached requirements for key {cache_key[:8]}...")
    
    def _invalidate_cache(self, document_id: int) -> None:
        """Invalidate cache for a document (called when document is updated).
        
        Args:
            document_id: Document ID
        """
        # Remove all cache entries for this document
        keys_to_remove = [
            key for key in self._filing_requirements_cache.keys()
            if f'"document_id": {document_id}' in json.dumps(self._filing_requirements_cache[key][0])
        ]
        for key in keys_to_remove:
            del self._filing_requirements_cache[key]
        
        logger.debug(f"Invalidated cache for document {document_id}")
    
    def generate_regulatory_documents(
        self,
        pool_id: str,
        filing_types: Optional[List[str]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate all required regulatory documents for a securitization pool.
        
        Args:
            pool_id: Pool identifier
            filing_types: Optional list of document types to generate.
                         Default: ['psa', 'trust_agreement', 'prospectus', 'sec_10d']
            user_id: Optional user ID generating the documents
            
        Returns:
            Dictionary with generated documents and metadata
        """
        if filing_types is None:
            filing_types = ['psa', 'trust_agreement', 'prospectus', 'sec_10d']
        
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        generated_docs = {}
        
        # Generate PSA
        if 'psa' in filing_types:
            try:
                psa_data = self.template_service.generate_psa(pool_id, user_id, 'text')
                generated_docs['psa'] = psa_data
            except Exception as e:
                logger.error(f"Failed to generate PSA for pool {pool_id}: {e}")
                generated_docs['psa'] = {'error': str(e)}
        
        # Generate Trust Agreement
        if 'trust_agreement' in filing_types:
            try:
                trust_data = self.template_service.generate_trust_agreement(pool_id, user_id, 'text')
                generated_docs['trust_agreement'] = trust_data
            except Exception as e:
                logger.error(f"Failed to generate Trust Agreement for pool {pool_id}: {e}")
                generated_docs['trust_agreement'] = {'error': str(e)}
        
        # Generate Prospectus Supplement
        if 'prospectus' in filing_types:
            try:
                prospectus_data = self.template_service.generate_prospectus(pool_id, user_id, 'text')
                generated_docs['prospectus'] = prospectus_data
            except Exception as e:
                logger.error(f"Failed to generate Prospectus for pool {pool_id}: {e}")
                generated_docs['prospectus'] = {'error': str(e)}
        
        # Generate SEC Form 10-D
        if 'sec_10d' in filing_types:
            try:
                sec_10d_data = self._generate_sec_10d(pool_id, user_id)
                generated_docs['sec_10d'] = sec_10d_data
            except Exception as e:
                logger.error(f"Failed to generate SEC Form 10-D for pool {pool_id}: {e}")
                generated_docs['sec_10d'] = {'error': str(e)}
        
        logger.info(f"Generated {len(generated_docs)} regulatory document(s) for pool {pool_id}")
        return {
            'pool_id': pool_id,
            'generated_documents': generated_docs,
            'generated_at': datetime.now().isoformat()
        }
    
    def attach_documents_to_filing(
        self,
        filing_id: int,
        document_ids: List[int],
        user_id: Optional[int] = None
    ) -> DocumentFiling:
        """Attach multiple documents to a filing.
        
        Args:
            filing_id: Filing ID
            document_ids: List of document IDs or generated document IDs to attach
            user_id: Optional user ID for audit logging
            
        Returns:
            Updated DocumentFiling instance
            
        Raises:
            ValueError: If filing not found
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        # Store attachments in filing_payload or create attachments field
        if not filing.filing_payload:
            filing.filing_payload = {}
        
        # Get or create attachments list
        attachments = filing.filing_payload.get("attachments", [])
        
        # Add new document IDs (avoid duplicates)
        existing_ids = {att.get("document_id") for att in attachments if att.get("document_id")}
        for doc_id in document_ids:
            if doc_id not in existing_ids:
                attachments.append({
                    "document_id": doc_id,
                    "attached_at": datetime.utcnow().isoformat(),
                    "attached_by": user_id
                })
        
        filing.filing_payload["attachments"] = attachments
        
        # Also set generated_document_id if only one attachment and it's a generated document
        if len(document_ids) == 1:
            # Check if it's a generated document
            from app.db.models import GeneratedDocument
            gen_doc = self.db.query(GeneratedDocument).filter(GeneratedDocument.id == document_ids[0]).first()
            if gen_doc:
                filing.generated_document_id = document_ids[0]
        
        self.db.commit()
        self.db.refresh(filing)
        
        # Audit logging
        if user_id:
            try:
                log_audit_action(
                    db=self.db,
                    action=AuditAction.UPDATE,
                    target_type="document_filing",
                    target_id=filing_id,
                    user_id=user_id,
                    metadata={
                        "action": "attach_documents",
                        "document_ids": document_ids,
                        "total_attachments": len(attachments)
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit action for document attachment: {audit_error}")
        
        logger.info(f"Attached {len(document_ids)} documents to filing {filing_id}")
        return filing
    
    def get_filing_attachments(
        self,
        filing_id: int
    ) -> List[Dict[str, Any]]:
        """Get all attachments for a filing.
        
        Args:
            filing_id: Filing ID
            
        Returns:
            List of attachment dictionaries with document details
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        attachments = []
        
        # Get attachments from filing_payload
        if filing.filing_payload and "attachments" in filing.filing_payload:
            for att in filing.filing_payload["attachments"]:
                doc_id = att.get("document_id")
                if doc_id:
                    # Get document details
                    from app.db.models import Document, GeneratedDocument
                    doc = self.db.query(Document).filter(Document.id == doc_id).first()
                    gen_doc = self.db.query(GeneratedDocument).filter(GeneratedDocument.id == doc_id).first()
                    
                    if doc:
                        attachments.append({
                            "document_id": doc_id,
                            "document_type": "document",
                            "title": doc.title,
                            "attached_at": att.get("attached_at"),
                            "attached_by": att.get("attached_by")
                        })
                    elif gen_doc:
                        attachments.append({
                            "document_id": doc_id,
                            "document_type": "generated_document",
                            "title": f"Generated Document {doc_id}",
                            "attached_at": att.get("attached_at"),
                            "attached_by": att.get("attached_by")
                        })
        
        # Also include the primary generated_document_id if set
        if filing.generated_document_id:
            # Check if already in attachments
            if not any(att.get("document_id") == filing.generated_document_id for att in attachments):
                from app.db.models import GeneratedDocument
                gen_doc = self.db.query(GeneratedDocument).filter(
                    GeneratedDocument.id == filing.generated_document_id
                ).first()
                if gen_doc:
                    attachments.append({
                        "document_id": filing.generated_document_id,
                        "document_type": "generated_document",
                        "title": f"Generated Document {filing.generated_document_id}",
                        "attached_at": filing.created_at.isoformat() if filing.created_at else None,
                        "attached_by": None
                    })
        
        return attachments
    
    def get_filing_template(
        self,
        jurisdiction: str,
        authority: str,
        form_type: Optional[str] = None,
        agreement_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get filing template for a jurisdiction/authority.
        
        Args:
            jurisdiction: Jurisdiction code
            authority: Regulatory authority
            form_type: Optional form type
            agreement_type: Optional agreement type
            
        Returns:
            Template dictionary or None if not found
        """
        from app.db.models import FilingTemplate
        
        query = self.db.query(FilingTemplate).filter(
            FilingTemplate.jurisdiction == jurisdiction,
            FilingTemplate.authority == authority
        )
        
        if form_type:
            query = query.filter(FilingTemplate.form_type == form_type)
        if agreement_type:
            query = query.filter(FilingTemplate.agreement_type == agreement_type)
        
        template = query.first()
        if template:
            # Increment usage count
            template.usage_count += 1
            self.db.commit()
            return template.to_dict()
        
        return None
    
    def save_filing_template(
        self,
        name: str,
        jurisdiction: str,
        authority: str,
        template_data: Dict[str, Any],
        form_type: Optional[str] = None,
        agreement_type: Optional[str] = None,
        field_mappings: Optional[Dict[str, str]] = None,
        required_fields: Optional[List[str]] = None,
        description: Optional[str] = None,
        language: str = "en",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Save a filing form template for reuse.
        
        Args:
            name: Template name
            jurisdiction: Jurisdiction code
            authority: Regulatory authority
            template_data: FilingFormData structure
            form_type: Optional form type
            agreement_type: Optional agreement type
            field_mappings: Optional CDM to form field mappings
            required_fields: Optional list of required fields
            description: Optional description
            language: Language code (default: "en")
            user_id: Optional user ID creating the template
            
        Returns:
            Saved template dictionary
        """
        from app.db.models import FilingTemplate
        
        template = FilingTemplate(
            name=name,
            jurisdiction=jurisdiction,
            authority=authority,
            form_type=form_type,
            agreement_type=agreement_type,
            template_data=template_data,
            field_mappings=field_mappings,
            required_fields=required_fields,
            description=description,
            language=language,
            is_system_template=False,
            created_by=user_id
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Saved filing template {template.id} for {jurisdiction}/{authority}")
        return template.to_dict()
    
    def list_filing_templates(
        self,
        jurisdiction: Optional[str] = None,
        authority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List filing templates.
        
        Args:
            jurisdiction: Optional jurisdiction filter
            authority: Optional authority filter
            
        Returns:
            List of template dictionaries
        """
        from app.db.models import FilingTemplate
        
        query = self.db.query(FilingTemplate)
        
        if jurisdiction:
            query = query.filter(FilingTemplate.jurisdiction == jurisdiction)
        if authority:
            query = query.filter(FilingTemplate.authority == authority)
        
        templates = query.order_by(FilingTemplate.usage_count.desc()).all()
        return [t.to_dict() for t in templates]
    
    def submit_to_regulatory_body(
        self,
        pool_id: str,
        regulatory_body: str,
        filing_type: str,
        documents: Dict[str, Any],
        user_id: Optional[int] = None,
        mock: bool = True
    ) -> Dict[str, Any]:
        """
        Submit regulatory documents to regulatory body (SEC, FINRA, etc.).
        
        Args:
            pool_id: Pool identifier
            regulatory_body: Regulatory body ('SEC', 'FINRA', etc.)
            filing_type: Type of filing ('sec_10d', 'prospectus', etc.)
            documents: Dictionary of document data to file
            user_id: Optional user ID submitting the filing
            mock: If True, simulate filing (for MVP). If False, attempt actual filing.
            
        Returns:
            Dictionary with filing status and receipt information
        """
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        if mock:
            # Mock filing - simulate submission
            filing_receipt = {
                'filing_id': f"{regulatory_body}-{pool_id}-{datetime.now().strftime('%Y%m%d')}",
                'regulatory_body': regulatory_body,
                'filing_type': filing_type,
                'submission_date': datetime.now().isoformat(),
                'status': 'submitted',
                'receipt_number': f"REC-{regulatory_body}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'mock': True
            }
            
            # Create filing record
            filing = RegulatoryFiling(
                pool_id=pool.id,
                filing_type=filing_type,
                regulatory_body=regulatory_body,
                status='submitted',
                filed_at=datetime.now(),
                filing_number=filing_receipt.get('receipt_number'),
                metadata={
                    'submitted_by': user_id,
                    'submission_date': datetime.now().isoformat(),
                    'mock': True,
                    'filing_receipt': filing_receipt
                }
            )
            
            self.db.add(filing)
            self.db.commit()
            self.db.refresh(filing)
            
            logger.info(f"Mock filing submitted for pool {pool_id} to {regulatory_body}: {filing.id}")
            
            return {
                'status': 'submitted',
                'filing_id': filing.id,
                'receipt': filing_receipt,
                'message': 'Filing submitted (mock mode)'
            }
        else:
            # Real filing - would integrate with SEC EDGAR API, FINRA API, etc.
            # For now, raise NotImplementedError
            raise NotImplementedError(
                f"Real filing to {regulatory_body} not yet implemented. "
                "Use mock=True for testing."
            )
    
    def track_filing_status(
        self,
        filing_id: int
    ) -> Dict[str, Any]:
        # #region agent log
        with open(r'get_debug_log_path()', 'a') as f:
            import json, time
            f.write(json.dumps({'location': 'filing_service.py:585', 'message': 'Entering track_filing_status', 'data': {'filing_id': filing_id}, 'timestamp': int(time.time()*1000), 'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B'}) + '\n')
        # #endregion
        """
        Track the status of a regulatory filing.
        
        Args:
            filing_id: Filing ID
            
        Returns:
            Dictionary with current filing status
        """
        filing = self.db.query(RegulatoryFiling).filter(
            RegulatoryFiling.id == filing_id
        ).first()
        
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        # In mock mode, return stored status
        # In production, would poll regulatory body API
        if filing.metadata and filing.metadata.get('mock'):
            return {
                'filing_id': filing.id,
                'status': filing.status,
                'regulatory_body': filing.regulatory_body,
                'filing_type': filing.filing_type,
                'filed_at': filing.filed_at.isoformat() if filing.filed_at else None,
                'receipt': filing.metadata.get('filing_receipt') if filing.metadata else None,
                'filing_number': filing.filing_number,
                'last_updated': filing.created_at.isoformat() if filing.created_at else None
            }
        else:
            # Would poll actual regulatory body API here
            return {
                'filing_id': filing.id,
                'status': filing.status,
                'regulatory_body': filing.regulatory_body,
                'filing_type': filing.filing_type,
                'filed_at': filing.filed_at.isoformat() if filing.filed_at else None,
                'receipt': filing.filing_receipt,
                'last_updated': filing.updated_at.isoformat() if filing.updated_at else None,
                'note': 'Real filing status tracking not yet implemented'
            }
    
    def file_securitization_pool(
        self,
        pool_id: str,
        regulatory_bodies: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        mock: bool = True
    ) -> Dict[str, Any]:
        """
        Complete filing workflow: generate documents and submit to regulatory bodies.
        
        Args:
            pool_id: Pool identifier
            regulatory_bodies: List of regulatory bodies to file with (default: ['SEC', 'FINRA'])
            user_id: Optional user ID performing the filing
            mock: If True, use mock filing (for MVP)
            
        Returns:
            Dictionary with filing results
        """
        if regulatory_bodies is None:
            regulatory_bodies = ['SEC', 'FINRA']
        
        # Generate all required documents
        documents = self.generate_regulatory_documents(
            pool_id=pool_id,
            filing_types=['psa', 'trust_agreement', 'prospectus', 'sec_10d'],
            user_id=user_id
        )
        
        filing_results = {}
        
        # Submit to each regulatory body
        for body in regulatory_bodies:
            try:
                if body == 'SEC':
                    # File SEC Form 10-D and Prospectus
                    sec_result = self.submit_to_regulatory_body(
                        pool_id=pool_id,
                        regulatory_body='SEC',
                        filing_type='sec_10d',
                        documents=documents['generated_documents'],
                        user_id=user_id,
                        mock=mock
                    )
                    filing_results['SEC'] = sec_result
                    
                    # Also file Prospectus Supplement
                    prospectus_result = self.submit_to_regulatory_body(
                        pool_id=pool_id,
                        regulatory_body='SEC',
                        filing_type='prospectus_supplement',
                        documents={'prospectus': documents['generated_documents'].get('prospectus')},
                        user_id=user_id,
                        mock=mock
                    )
                    filing_results['SEC_Prospectus'] = prospectus_result
                
                elif body == 'FINRA':
                    # File with FINRA
                    finra_result = self.submit_to_regulatory_body(
                        pool_id=pool_id,
                        regulatory_body='FINRA',
                        filing_type='securitization_notice',
                        documents=documents['generated_documents'],
                        user_id=user_id,
                        mock=mock
                    )
                    filing_results['FINRA'] = finra_result
                
            except Exception as e:
                logger.error(f"Failed to file with {body} for pool {pool_id}: {e}")
                filing_results[body] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return {
            'pool_id': pool_id,
            'documents_generated': documents,
            'filing_results': filing_results,
            'filed_at': datetime.now().isoformat()
        }
    
    def _generate_sec_10d(
        self,
        pool_id: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate SEC Form 10-D (Distribution Report) for securitization pool.
        
        Args:
            pool_id: Pool identifier
            user_id: Optional user ID
            
        Returns:
            Dictionary with SEC Form 10-D data
        """
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        # Get pool data
        pool_data = self.template_service._get_pool_data(pool)
        
        # Generate SEC Form 10-D content
        sec_10d_data = {
            'form_type': '10-D',
            'pool_name': pool.pool_name,
            'pool_id': pool.pool_id,
            'pool_type': pool.pool_type,
            'reporting_period': datetime.now().strftime('%Y-%m'),
            'filing_date': datetime.now().isoformat(),
            'total_pool_value': str(pool.total_pool_value),
            'currency': pool.currency,
            'tranche_count': len(pool_data['tranches']),
            'asset_count': len(pool_data['assets']),
            'distribution_summary': {
                'total_distributions': '0',  # Would calculate from actual distributions
                'interest_payments': '0',
                'principal_payments': '0'
            }
        }
        
        # Generate document text
        sec_10d_text = self._generate_sec_10d_document_text(sec_10d_data)
        sec_10d_data['document_text'] = sec_10d_text
        
        # Save as generated document if user_id provided
        if user_id:
            document = self.template_service._save_generated_document(
                pool_id=pool_id,
                document_type='SEC Form 10-D',
                content=sec_10d_text,
                user_id=user_id
            )
            sec_10d_data['document_id'] = document.id
            sec_10d_data['document_path'] = document.file_path
        
        return sec_10d_data


    def _generate_sec_10d_document_text(self, data: Dict[str, Any]) -> str:
        """Generate SEC Form 10-D document text."""
        
        text = f"""
UNITED STATES
SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549

FORM 10-D

DISTRIBUTION REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934

For the reporting period: {data['reporting_period']}

Commission File Number: [TO BE ASSIGNED]

{data['pool_name']}
(Exact name of registrant as specified in its charter)

Pool ID: {data['pool_id']}
Pool Type: {data['pool_type']}

REPORTING PERIOD INFORMATION

Reporting Period: {data['reporting_period']}
Filing Date: {data['filing_date']}

POOL INFORMATION

Pool Name: {data['pool_name']}
Pool ID: {data['pool_id']}
Total Pool Value: {data['currency']} {data['total_pool_value']}
Number of Tranches: {data['tranche_count']}
Number of Underlying Assets: {data['asset_count']}

DISTRIBUTION SUMMARY

Total Distributions: {data['currency']} {data['distribution_summary']['total_distributions']}
Interest Payments: {data['currency']} {data['distribution_summary']['interest_payments']}
Principal Payments: {data['currency']} {data['distribution_summary']['principal_payments']}

ASSET PERFORMANCE

[Asset performance metrics would be included here]

SIGNATURE

Pursuant to the requirements of the Securities Exchange Act of 1934, the registrant
has duly caused this report to be signed on its behalf by the undersigned,
thereunto duly authorized.

{data['pool_name']}

By: _________________________
    [Authorized Signatory]
    Date: {data['filing_date']}
"""
        
        return text.strip()
    
    # ============================================================================
    # Document Filing Methods
    # ============================================================================
    
    def _validate_cdm_data_completeness(
        self,
        credit_agreement: CreditAgreement
    ) -> Dict[str, Any]:
        """Validate CDM data completeness for filing requirement evaluation.
        
        Args:
            credit_agreement: CreditAgreement instance
            
        Returns:
            Dictionary with validation results:
            - complete: bool - Whether data is complete
            - missing_fields: List[str] - List of missing critical fields
            - warnings: List[str] - List of warnings about optional fields
        """
        missing_fields = []
        warnings = []
        
        # Critical fields for filing evaluation
        if not credit_agreement.deal_id:
            missing_fields.append("deal_id")
        
        if not credit_agreement.agreement_date:
            missing_fields.append("agreement_date")
        
        if not credit_agreement.governing_law:
            missing_fields.append("governing_law")
        
        if not credit_agreement.parties or len(credit_agreement.parties) == 0:
            missing_fields.append("parties")
        else:
            # Check for borrower
            has_borrower = any(p.role == "Borrower" for p in credit_agreement.parties)
            if not has_borrower:
                warnings.append("No borrower party found in parties list")
        
        if not credit_agreement.facilities or len(credit_agreement.facilities) == 0:
            missing_fields.append("facilities")
        else:
            # Check for commitment amount
            has_commitment = any(
                f.commitment_amount and f.commitment_amount.amount > 0 
                for f in credit_agreement.facilities
            )
            if not has_commitment:
                warnings.append("No commitment amount found in facilities")
        
        # Optional but recommended fields
        if not credit_agreement.total_commitment:
            warnings.append("total_commitment not set (may be calculated from facilities)")
        
        return {
            "complete": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "warnings": warnings
        }
    
    def calculate_filing_deadline(
        self,
        agreement_date: date,
        jurisdiction: str,
        filing_type: str = "facility_agreement"
    ) -> datetime:
        """Calculate filing deadline based on jurisdiction-specific rules.
        
        Args:
            agreement_date: Date of agreement execution
            jurisdiction: Jurisdiction code ("US", "UK", "FR", "DE")
            filing_type: Type of filing (default: "facility_agreement")
            
        Returns:
            Calculated deadline as datetime
            
        Raises:
            FilingError: If jurisdiction not supported
        """
        if not agreement_date:
            raise FilingError("Agreement date is required for deadline calculation")
        
        # Convert date to datetime for consistency
        if isinstance(agreement_date, datetime):
            agreement_datetime = agreement_date
        else:
            agreement_datetime = datetime.combine(agreement_date, datetime.min.time())
        
        # Jurisdiction-specific deadline rules
        deadline_rules = {
            "US": {
                "facility_agreement": 4,  # 4 business days for SEC 8-K
                "disclosure": 4,
                "default": 4
            },
            "UK": {
                "facility_agreement": 21,  # 21 calendar days for Companies House MR01
                "security_agreement": 21,
                "default": 21
            },
            "FR": {
                "facility_agreement": 15,  # 15 calendar days for AMF
                "default": 15
            },
            "DE": {
                "facility_agreement": 15,  # 15 calendar days for BaFin
                "default": 15
            }
        }
        
        # Get deadline days for jurisdiction and filing type
        jurisdiction_rules = deadline_rules.get(jurisdiction.upper())
        if not jurisdiction_rules:
            raise FilingError(f"Unsupported jurisdiction for deadline calculation: {jurisdiction}")
        
        days = jurisdiction_rules.get(filing_type, jurisdiction_rules.get("default", 30))
        
        # US uses business days, others use calendar days
        if jurisdiction.upper() == "US":
            deadline_date = add_business_days(agreement_date, days)
        else:
            deadline_date = agreement_date + timedelta(days=days)
        
        # Convert to datetime
        if isinstance(deadline_date, date) and not isinstance(deadline_date, datetime):
            deadline_datetime = datetime.combine(deadline_date, datetime.max.time())
        else:
            deadline_datetime = deadline_date
        
        logger.info(
            f"Calculated deadline for {jurisdiction} {filing_type}: "
            f"{deadline_datetime.isoformat()} ({days} days from {agreement_date})"
        )
        
        return deadline_datetime
    
    def calculate_filing_priority(
        self,
        deadline: datetime,
        current_date: Optional[datetime] = None
    ) -> str:
        """Calculate filing priority based on days until deadline.
        
        Args:
            deadline: Filing deadline
            current_date: Current date (defaults to now)
            
        Returns:
            Priority level: "critical", "high", "medium", or "low"
        """
        if current_date is None:
            current_date = datetime.utcnow()
        
        # Calculate days until deadline
        time_diff = deadline - current_date
        days_remaining = time_diff.days
        
        # Priority thresholds
        if days_remaining < 0:
            return "critical"  # Overdue
        elif days_remaining <= 7:
            return "critical"  # Within 7 days
        elif days_remaining <= 30:
            return "high"  # Within 30 days
        elif days_remaining <= 90:
            return "medium"  # Within 90 days
        else:
            return "low"  # More than 90 days
    
    def prepare_batch_filings(
        self,
        document_ids: List[int],
        agreement_type: str = "facility_agreement",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Prepare filings for multiple documents in batch.
        
        Args:
            document_ids: List of document IDs
            agreement_type: Agreement type
            user_id: Optional user ID for audit logging
            
        Returns:
            Dictionary with batch results:
            - total: int - Total documents processed
            - prepared: int - Number of filings prepared
            - failed: int - Number of failures
            - results: List[Dict] - Detailed results per document
        """
        results = []
        prepared = 0
        failed = 0
        
        for document_id in document_ids:
            try:
                # Determine requirements
                requirements = self.determine_filing_requirements(
                    document_id=document_id,
                    agreement_type=agreement_type,
                    use_ai_evaluation=True,
                    user_id=user_id
                )
                
                # Prepare manual filings for each requirement
                filing_results = []
                for requirement in requirements:
                    if requirement.filing_system == "manual_ui":
                        try:
                            filing = self.prepare_manual_filing(
                                document_id=document_id,
                                filing_requirement=requirement,
                                user_id=user_id
                            )
                            filing_results.append({
                                "filing_id": filing.id,
                                "authority": requirement.authority,
                                "jurisdiction": requirement.jurisdiction,
                                "status": "prepared"
                            })
                            prepared += 1
                        except Exception as e:
                            logger.error(f"Failed to prepare filing for document {document_id}: {e}")
                            filing_results.append({
                                "authority": requirement.authority,
                                "jurisdiction": requirement.jurisdiction,
                                "status": "failed",
                                "error": str(e)
                            })
                            failed += 1
                
                results.append({
                    "document_id": document_id,
                    "status": "success",
                    "filings": filing_results
                })
                
            except Exception as e:
                logger.error(f"Failed to process document {document_id}: {e}")
                results.append({
                    "document_id": document_id,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1
        
        return {
            "total": len(document_ids),
            "prepared": prepared,
            "failed": failed,
            "results": results
        }
    
    def submit_batch_filings(
        self,
        filing_ids: List[int],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Submit multiple filings automatically in batch.
        
        Args:
            filing_ids: List of filing IDs to submit
            user_id: Optional user ID for audit logging
            
        Returns:
            Dictionary with batch submission results:
            - total: int - Total filings processed
            - submitted: int - Number successfully submitted
            - failed: int - Number of failures
            - results: List[Dict] - Detailed results per filing
        """
        from app.db.models import DocumentFiling
        from app.services.policy_service import FilingRequirement
        
        results = []
        submitted = 0
        failed = 0
        
        for filing_id in filing_ids:
            try:
                filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
                if not filing:
                    results.append({
                        "filing_id": filing_id,
                        "status": "failed",
                        "error": "Filing not found"
                    })
                    failed += 1
                    continue
                
                # Only submit API-enabled filings
                if filing.filing_system not in ["companies_house_api"]:
                    results.append({
                        "filing_id": filing_id,
                        "status": "skipped",
                        "reason": f"Filing system {filing.filing_system} does not support automatic submission"
                    })
                    continue
                
                # Convert to FilingRequirement
                requirement = FilingRequirement(
                    authority=filing.filing_authority,
                    filing_system=filing.filing_system,
                    deadline=filing.deadline or datetime.utcnow(),
                    required_fields=[],
                    api_available=True,
                    jurisdiction=filing.jurisdiction,
                    agreement_type=filing.agreement_type
                )
                
                # Submit filing
                result_filing = self.file_document_automatically(
                    document_id=filing.document_id,
                    filing_requirement=requirement,
                    user_id=user_id
                )
                
                results.append({
                    "filing_id": filing_id,
                    "status": "submitted",
                    "filing_reference": result_filing.filing_reference,
                    "filing_url": result_filing.filing_url
                })
                submitted += 1
                
            except Exception as e:
                logger.error(f"Failed to submit filing {filing_id}: {e}")
                results.append({
                    "filing_id": filing_id,
                    "status": "failed",
                    "error": str(e)
                })
                failed += 1
        
        return {
            "total": len(filing_ids),
            "submitted": submitted,
            "failed": failed,
            "results": results
        }
    
    def _get_credit_agreement_from_document(
        self,
        document_id: int
    ) -> Optional[CreditAgreement]:
        """Extract CreditAgreement from document.
        
        Args:
            document_id: Document ID
            
        Returns:
            CreditAgreement instance or None if not found
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Try to get from source_cdm_data (for generated documents)
        if document.source_cdm_data:
            try:
                return CreditAgreement(**document.source_cdm_data)
            except Exception as e:
                logger.warning(f"Failed to parse source_cdm_data for document {document_id}: {e}")
        
        # Try to get from DocumentVersion.extracted_data
        if document.current_version_id:
            version = self.db.query(DocumentVersion).filter(
                DocumentVersion.id == document.current_version_id
            ).first()
            if version and version.extracted_data:
                try:
                    return CreditAgreement(**version.extracted_data)
                except Exception as e:
                    logger.warning(f"Failed to parse extracted_data for document {document_id}: {e}")
        
        # Try latest version
        latest_version = self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        if latest_version and latest_version.extracted_data:
            try:
                return CreditAgreement(**latest_version.extracted_data)
            except Exception as e:
                logger.warning(f"Failed to parse latest version extracted_data for document {document_id}: {e}")
        
        return None
    
    def determine_filing_requirements(
        self,
        document_id: int,
        agreement_type: str = "facility_agreement",
        deal_id: Optional[int] = None,
        use_ai_evaluation: bool = True,
        user_id: Optional[int] = None
    ) -> List[PolicyFilingRequirement]:
        """Determine filing requirements for a document.
        
        Args:
            document_id: Document ID
            agreement_type: Type of agreement (default: "facility_agreement")
            deal_id: Optional deal ID for context
            use_ai_evaluation: If True, use AI chain; if False, use policy service
            
        Returns:
            List of FilingRequirement objects
            
        Raises:
            ValueError: If document not found or CDM data unavailable
            FilingError: If evaluation fails
        """
        # Get credit agreement from document
        credit_agreement = self._get_credit_agreement_from_document(document_id)
        if not credit_agreement:
            raise ValueError(f"Could not extract CreditAgreement from document {document_id}")
        
        # Validate CDM data completeness
        validation = self._validate_cdm_data_completeness(credit_agreement)
        if not validation["complete"]:
            logger.warning(
                f"CDM data incomplete for document {document_id}: "
                f"missing fields: {validation['missing_fields']}"
            )
            # Still proceed but log warning
            if validation["warnings"]:
                logger.info(f"CDM data warnings: {validation['warnings']}")
        
        # Check cache first
        cache_key = self._get_cache_key(document_id, agreement_type, deal_id)
        cached_requirements = self._get_cached_requirements(cache_key)
        if cached_requirements is not None:
            logger.info(f"Using cached filing requirements for document {document_id}")
            return cached_requirements
        
        try:
            if use_ai_evaluation:
                # Use AI chain for evaluation
                logger.info(f"Using AI evaluation for filing requirements (document {document_id})")
                evaluation = evaluate_filing_requirements_chain(
                    credit_agreement=credit_agreement,
                    document_id=document_id,
                    deal_id=deal_id,
                    agreement_type=agreement_type
                )
                # Convert FilingRequirementEvaluation to list of PolicyFilingRequirement
                # The chain returns Pydantic models, convert to dataclass for consistency
                requirements = []
                for req in evaluation.required_filings:
                    requirements.append(PolicyFilingRequirement(
                        authority=req.authority,
                        jurisdiction=req.jurisdiction or "US",
                        agreement_type=req.agreement_type,
                        filing_system=req.filing_system,
                        deadline=req.deadline,
                        required_fields=req.required_fields,
                        api_available=req.api_available,
                        api_endpoint=req.api_endpoint,
                        penalty=req.penalty,
                        language_requirement=req.language_requirement,
                        form_type=req.form_type,
                        priority=req.priority
                    ))
                
                # Cache the results
                self._cache_requirements(cache_key, requirements)
                return requirements
            else:
                # Use policy service for evaluation
                if not self.policy_service:
                    raise FilingError("Policy service not available")
                
                logger.info(f"Using policy service for filing requirements (document {document_id})")
                decision = self.policy_service.evaluate_filing_requirements(
                    credit_agreement=credit_agreement,
                    document_id=document_id,
                    deal_id=deal_id
                )
                result = decision.required_filings
                
                # Cache the results
                self._cache_requirements(cache_key, result)
                
                # Audit logging
                if user_id:
                    try:
                        log_audit_action(
                            db=self.db,
                            action=AuditAction.VIEW,
                            target_type="filing_requirements",
                            target_id=document_id,
                            user_id=user_id,
                            metadata={
                                "document_id": document_id,
                                "deal_id": deal_id,
                                "agreement_type": agreement_type,
                                "use_ai_evaluation": use_ai_evaluation,
                                "requirements_count": len(result),
                                "jurisdictions": list(set([r.jurisdiction for r in result if r.jurisdiction])),
                                "cached": False
                            }
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to log audit action for filing requirements: {audit_error}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error determining filing requirements for document {document_id}: {e}")
            raise FilingError(f"Failed to determine filing requirements: {e}") from e
    
    def prepare_manual_filing(
        self,
        document_id: int,
        filing_requirement: PolicyFilingRequirement,
        user_id: Optional[int] = None
    ) -> DocumentFiling:
        """Prepare a manual filing with AI-generated pre-filled form data.
        
        This method creates a DocumentFiling record and uses AI to generate
        pre-filled form data based on the CDM data from the document. The form
        data is stored in the filing_payload JSONB field for display in the UI.
        
        Args:
            document_id: Document ID to prepare filing for
            filing_requirement: FilingRequirement instance with filing details
            user_id: Optional user ID for audit logging
            
        Returns:
            DocumentFiling instance with prepared form data in filing_payload
            
        Raises:
            ValueError: If document not found or CDM data missing
            FilingError: If form generation fails or filing already exists
            
        Example:
            >>> requirement = PolicyFilingRequirement(
            ...     authority="SEC",
            ...     jurisdiction="US",
            ...     filing_system="manual_ui",
            ...     deadline=datetime.now() + timedelta(days=4)
            ... )
            >>> filing = service.prepare_manual_filing(123, requirement)
            >>> print(filing.filing_payload["fields"])  # Pre-filled form fields
        """
        # Check if filing already exists
        existing_filing = self.db.query(DocumentFiling).filter(
            DocumentFiling.document_id == document_id,
            DocumentFiling.filing_authority == filing_requirement.authority,
            DocumentFiling.jurisdiction == filing_requirement.jurisdiction
        ).first()
        
        if existing_filing:
            logger.info(f"Filing already exists for document {document_id}, authority {filing_requirement.authority}")
            # Update existing filing if needed
            if not existing_filing.filing_payload:
                # Generate form data if not already generated
                credit_agreement = self._get_credit_agreement_from_document(document_id)
                if credit_agreement:
                    try:
                        # Determine language from requirement or jurisdiction
                        language = filing_requirement.language_requirement
                        if not language:
                            from app.chains.filing_form_generation_chain import _get_language_for_jurisdiction
                            language = _get_language_for_jurisdiction(filing_requirement.jurisdiction)
                        
                        form_data = generate_filing_form_data(
                            credit_agreement=credit_agreement,
                            filing_requirement=filing_requirement,
                            document_id=document_id,
                            deal_id=existing_filing.deal_id,
                            language=language
                        )
                        existing_filing.filing_payload = form_data.model_dump()
                        self.db.commit()
                        self.db.refresh(existing_filing)
                    except Exception as e:
                        logger.warning(f"Failed to regenerate form data: {e}")
            return existing_filing
        
        # Get credit agreement
        credit_agreement = self._get_credit_agreement_from_document(document_id)
        if not credit_agreement:
            raise ValueError(f"Could not extract CreditAgreement from document {document_id}")
        
        # Get document for deal_id
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Generate form data using AI chain
        try:
            # Determine language from requirement or jurisdiction
            language = filing_requirement.language_requirement
            if not language:
                from app.chains.filing_form_generation_chain import _get_language_for_jurisdiction
                language = _get_language_for_jurisdiction(filing_requirement.jurisdiction)
            
            logger.info(f"Generating filing form data for document {document_id} in language: {language}")
            form_data = generate_filing_form_data(
                credit_agreement=credit_agreement,
                filing_requirement=filing_requirement,
                document_id=document_id,
                deal_id=document.deal_id,
                language=language
            )
        except Exception as e:
            logger.error(f"Failed to generate filing form data: {e}")
            raise FilingError(f"Failed to generate filing form data: {e}") from e
        
        # Create DocumentFiling record
        filing = DocumentFiling(
            document_id=document_id,
            deal_id=document.deal_id,
            agreement_type=filing_requirement.agreement_type or "facility_agreement",
            jurisdiction=filing_requirement.jurisdiction or "US",
            filing_authority=filing_requirement.authority,
            filing_system=filing_requirement.filing_system,
            filing_status="pending",
            deadline=filing_requirement.deadline,
            filing_payload=form_data.model_dump(),
            manual_submission_url=form_data.submission_url
        )
        
        self.db.add(filing)
        self.db.flush()  # Flush to get filing.id
        
        # Audit logging
        if user_id:
            try:
                log_audit_action(
                    db=self.db,
                    action=AuditAction.CREATE,
                    target_type="document_filing",
                    target_id=filing.id,
                    user_id=user_id,
                    metadata={
                        "document_id": document_id,
                        "deal_id": document.deal_id,
                        "filing_authority": filing_requirement.authority,
                        "jurisdiction": filing_requirement.jurisdiction,
                        "filing_system": filing_requirement.filing_system,
                        "form_type": filing_requirement.form_type,
                        "deadline": filing_requirement.deadline.isoformat() if filing_requirement.deadline else None
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit action for filing preparation: {audit_error}")
        
        self.db.commit()
        self.db.refresh(filing)
        
        logger.info(f"Created filing {filing.id} for document {document_id}")
        return filing
    
    def file_document_automatically(
        self,
        document_id: int,
        filing_requirement: PolicyFilingRequirement,
        max_retries: int = 3,
        user_id: Optional[int] = None
    ) -> DocumentFiling:
        """File document automatically via API (e.g., UK Companies House).
        
        Args:
            document_id: Document ID
            filing_requirement: FilingRequirement instance
            max_retries: Maximum retry attempts for API calls
            
        Returns:
            DocumentFiling instance with submission results
            
        Raises:
            ValueError: If document not found or filing system not supported
            FilingAPIError: If API submission fails
        """
        if filing_requirement.filing_system != "companies_house_api":
            raise ValueError(f"Automatic filing not supported for system: {filing_requirement.filing_system}")
        
        if not filing_requirement.api_available:
            raise ValueError(f"API filing not available for {filing_requirement.authority}")
        
        # Check if filing already exists
        existing_filing = self.db.query(DocumentFiling).filter(
            DocumentFiling.document_id == document_id,
            DocumentFiling.filing_authority == filing_requirement.authority,
            DocumentFiling.jurisdiction == filing_requirement.jurisdiction
        ).first()
        
        if existing_filing and existing_filing.filing_status in ["submitted", "accepted"]:
            logger.info(f"Filing already submitted: {existing_filing.id}")
            return existing_filing
        
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get credit agreement
        credit_agreement = self._get_credit_agreement_from_document(document_id)
        if not credit_agreement:
            raise ValueError(f"Could not extract CreditAgreement from document {document_id}")
        
        # Create or update filing record
        if existing_filing:
            filing = existing_filing
        else:
            filing = DocumentFiling(
                document_id=document_id,
                deal_id=document.deal_id,
                agreement_type=filing_requirement.agreement_type or "facility_agreement",
                jurisdiction=filing_requirement.jurisdiction or "UK",
                filing_authority=filing_requirement.authority,
                filing_system=filing_requirement.filing_system,
                filing_status="pending",
                deadline=filing_requirement.deadline
            )
            self.db.add(filing)
            self.db.flush()
        
        # Submit via API with retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Submitting filing {filing.id} to {filing_requirement.authority} (attempt {attempt + 1}/{max_retries})")
                
                # Call Companies House API via client
                client = CompaniesHouseAPIClient()
                result = client.submit_charge(
                    credit_agreement=credit_agreement,
                    filing_requirement=filing_requirement
                )
                
                # Update filing with results
                filing.filing_status = "submitted"
                filing.filing_reference = result.get("filing_reference")
                filing.filing_url = result.get("filing_url")
                filing.confirmation_url = result.get("confirmation_url")
                filing.filing_response = result
                filing.filed_at = datetime.utcnow()
                
                self.db.flush()  # Flush before audit logging
                
                # Audit logging
                if user_id:
                    try:
                        log_audit_action(
                            db=self.db,
                            action=AuditAction.FILE,
                            target_type="document_filing",
                            target_id=filing.id,
                            user_id=user_id,
                            metadata={
                                "document_id": document_id,
                                "deal_id": document.deal_id,
                                "filing_authority": filing_requirement.authority,
                                "jurisdiction": filing_requirement.jurisdiction,
                                "filing_system": filing_requirement.filing_system,
                                "filing_reference": result.get("filing_reference"),
                                "filing_url": result.get("filing_url"),
                                "submission_method": "automatic_api",
                                "retry_count": filing.retry_count
                            }
                        )
                    except Exception as audit_error:
                        logger.warning(f"Failed to log audit action for automatic filing: {audit_error}")
                
                self.db.commit()
                self.db.refresh(filing)
                
                logger.info(f"Successfully submitted filing {filing.id}")
                return filing
                
            except Exception as e:
                last_error = e
                filing.retry_count += 1
                filing.error_message = str(e)
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                    logger.warning(f"API submission failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    filing.filing_status = "rejected"
                    self.db.commit()
                    logger.error(f"API submission failed after {max_retries} attempts: {e}")
                    raise FilingAPIError(f"Failed to submit filing after {max_retries} attempts: {e}") from e
        
        raise FilingAPIError(f"Failed to submit filing: {last_error}") from last_error
    
    def validate_filing_payload(
        self,
        filing_payload: Dict[str, Any],
        required_fields: List[str]
    ) -> Dict[str, Any]:
        """Validate filing payload against required fields.
        
        Args:
            filing_payload: Filing payload dictionary (from filing_payload JSONB field)
            required_fields: List of required field names
            
        Returns:
            Dictionary with validation results:
            - valid: bool - Whether validation passed
            - missing_fields: List[str] - List of missing required fields
            - errors: List[str] - List of validation error messages
            
        Raises:
            FilingError: If payload structure is invalid
        """
        if not filing_payload:
            return {
                "valid": False,
                "missing_fields": required_fields,
                "errors": ["Filing payload is empty"]
            }
        
        # Extract fields from FilingFormData structure
        fields = filing_payload.get("fields", [])
        if not isinstance(fields, list):
            return {
                "valid": False,
                "missing_fields": required_fields,
                "errors": ["Invalid filing payload structure: 'fields' must be a list"]
            }
        
        # Create a map of field_name -> field_value
        field_map = {}
        for field in fields:
            if isinstance(field, dict):
                field_name = field.get("field_name")
                field_value = field.get("field_value")
                if field_name:
                    field_map[field_name] = field_value
        
        # Check for missing required fields
        missing_fields = []
        errors = []
        
        for required_field in required_fields:
            # Check if field exists in field_map
            field_found = False
            for field_name, field_value in field_map.items():
                # Case-insensitive matching and partial matching
                if required_field.lower() in field_name.lower() or field_name.lower() in required_field.lower():
                    if field_value is not None and str(field_value).strip():
                        field_found = True
                        break
            
            if not field_found:
                missing_fields.append(required_field)
                errors.append(f"Required field '{required_field}' is missing or empty")
        
        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "errors": errors
        }
    
    def validate_filing_before_submission(
        self,
        filing_id: int
    ) -> Dict[str, Any]:
        """Validate a filing before submission.
        
        Args:
            filing_id: Filing ID
            
        Returns:
            Dictionary with validation results
            
        Raises:
            ValueError: If filing not found
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        # Get required fields from filing requirement
        # We need to reconstruct the FilingRequirement or get it from the filing
        # For now, extract from filing_payload if available
        required_fields = []
        
        if filing.filing_payload:
            # Try to extract required fields from the form data
            fields = filing.filing_payload.get("fields", [])
            for field in fields:
                if isinstance(field, dict) and field.get("required", False):
                    field_name = field.get("field_name")
                    if field_name:
                        required_fields.append(field_name)
        
        # Validate payload
        validation_result = self.validate_filing_payload(
            filing_payload=filing.filing_payload or {},
            required_fields=required_fields
        )
        
        # Add filing context to result
        validation_result["filing_id"] = filing_id
        validation_result["filing_status"] = filing.filing_status
        validation_result["filing_authority"] = filing.filing_authority
        validation_result["jurisdiction"] = filing.jurisdiction
        
        return validation_result
    
    def update_manual_filing_status(
        self,
        filing_id: int,
        filing_reference: str,
        submission_notes: Optional[str] = None,
        submitted_by: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> DocumentFiling:
        """Update manual filing status after user submits via external portal.
        
        Args:
            filing_id: Filing ID
            filing_reference: External filing reference from portal
            submission_notes: Optional notes from submission
            submitted_by: Optional user ID who submitted
            
        Returns:
            Updated DocumentFiling instance
            
        Raises:
            ValueError: If filing not found
        """
        filing = self.db.query(DocumentFiling).filter(DocumentFiling.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        filing.filing_status = "submitted"
        filing.filing_reference = filing_reference
        filing.submitted_by = submitted_by or user_id
        filing.submitted_at = datetime.utcnow()
        filing.submission_notes = submission_notes
        
        self.db.flush()  # Flush before audit logging
        
        # Audit logging
        audit_user_id = submitted_by or user_id
        if audit_user_id:
            try:
                log_audit_action(
                    db=self.db,
                    action=AuditAction.UPDATE,
                    target_type="document_filing",
                    target_id=filing_id,
                    user_id=audit_user_id,
                    metadata={
                        "document_id": filing.document_id,
                        "deal_id": filing.deal_id,
                        "filing_authority": filing.filing_authority,
                        "jurisdiction": filing.jurisdiction,
                        "filing_reference": filing_reference,
                        "previous_status": "pending",
                        "new_status": "submitted",
                        "submission_method": "manual",
                        "submission_notes": submission_notes
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit action for filing status update: {audit_error}")
        
        self.db.commit()
        self.db.refresh(filing)
        
        logger.info(f"Updated filing {filing_id} status to submitted with reference {filing_reference}")
        return filing

    def generate_compliance_report(
        self,
        deal_id: Optional[int] = None,
        jurisdiction: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        # #region agent log
        with open(r'get_debug_log_path()', 'a') as f:
            import json, time
            f.write(json.dumps({'location': 'filing_service.py:1807', 'message': 'Entering generate_compliance_report', 'data': {'deal_id': deal_id, 'jurisdiction': jurisdiction}, 'timestamp': int(time.time()*1000), 'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'B'}) + '\n')
        # #endregion
        """Generate a compliance report for filings.
        
        Args:
            deal_id: Optional deal ID filter
            jurisdiction: Optional jurisdiction filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with compliance statistics and breakdown
        """
        from app.db.models import DocumentFiling
        from sqlalchemy import func
        
        # Build query
        query = self.db.query(DocumentFiling)
        
        if deal_id:
            query = query.filter(DocumentFiling.deal_id == deal_id)
        if jurisdiction:
            query = query.filter(DocumentFiling.jurisdiction == jurisdiction)
        if start_date:
            query = query.filter(DocumentFiling.created_at >= start_date)
        if end_date:
            query = query.filter(DocumentFiling.created_at <= end_date)
            
        filings = query.all()
        
        # Calculate summary statistics
        total = len(filings)
        if total == 0:
            return {
                "summary": {
                    "total_filings": 0,
                    "compliant_count": 0,
                    "compliance_rate": 100.0,
                    "pending_count": 0,
                    "overdue_count": 0
                },
                "breakdown": {
                    "status": {},
                    "jurisdiction": {},
                    "authority": {}
                }
            }
            
        compliant = sum(1 for f in filings if f.filing_status == "accepted")
        pending = sum(1 for f in filings if f.filing_status == "pending")
        rejected = sum(1 for f in filings if f.filing_status == "rejected")
        
        now = datetime.utcnow()
        overdue = sum(1 for f in filings if f.filing_status == "pending" and f.deadline and f.deadline < now)
        
        # Breakdown by status
        status_breakdown = {}
        for f in filings:
            status_breakdown[f.filing_status] = status_breakdown.get(f.filing_status, 0) + 1
            
        # Breakdown by jurisdiction
        juris_breakdown = {}
        for f in filings:
            juris_breakdown[f.jurisdiction] = juris_breakdown.get(f.jurisdiction, 0) + 1
            
        # Breakdown by authority
        auth_breakdown = {}
        for f in filings:
            auth_breakdown[f.filing_authority] = auth_breakdown.get(f.filing_authority, 0) + 1
            
        return {
            "summary": {
                "total_filings": total,
                "compliant_count": compliant,
                "compliance_rate": (compliant / total) * 100.0,
                "pending_count": pending,
                "overdue_count": overdue,
                "rejected_count": rejected
            },
            "breakdown": {
                "status": status_breakdown,
                "jurisdiction": juris_breakdown,
                "authority": auth_breakdown
            },
            "generated_at": now.isoformat()
        }