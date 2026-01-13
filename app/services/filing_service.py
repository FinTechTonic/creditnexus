"""
Filing service for regulatory filing of securitization documents.

Handles generation and submission of regulatory documents to SEC, FINRA, etc.
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import (
    SecuritizationPool, RegulatoryFiling, GeneratedDocument, User
)
from app.services.securitization_template_service import SecuritizationTemplateService
from app.templates.securitization import (
    generate_psa_template,
    generate_trust_agreement_template,
    generate_prospectus_template
)

logger = logging.getLogger(__name__)


class FilingService:
    """Service for managing regulatory filings for securitization pools."""
    
    def __init__(self, db: Session):
        """Initialize filing service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.template_service = SecuritizationTemplateService(db)
    
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
        sec_10d_text = _generate_sec_10d_document_text(sec_10d_data)
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


def _generate_sec_10d_document_text(data: Dict[str, Any]) -> str:
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
