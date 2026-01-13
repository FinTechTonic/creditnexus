"""
Securitization template generation service.

Provides methods for generating securitization agreement templates
(PSA, Trust Agreement, Prospectus Supplement) from pool data.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import SecuritizationPool, GeneratedDocument, User
from app.models.cdm import SecuritizationPool as CDMSecuritizationPool
from app.templates.securitization import (
    generate_psa_template,
    generate_trust_agreement_template,
    generate_prospectus_template
)
from app.generation.renderer import DocumentRenderer
from app.templates.storage import TemplateStorage

logger = logging.getLogger(__name__)


class SecuritizationTemplateService:
    """Service for generating securitization agreement templates."""
    
    def __init__(self, db: Session):
        """Initialize securitization template service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.renderer = DocumentRenderer()
        self.storage = TemplateStorage()
    
    def generate_psa(
        self,
        pool_id: str,
        user_id: Optional[int] = None,
        output_format: str = 'text'
    ) -> Dict[str, Any]:
        """
        Generate Pooling and Servicing Agreement for a securitization pool.
        
        Args:
            pool_id: Pool identifier
            user_id: Optional user ID generating the document
            output_format: Output format ('text', 'dict', 'docx')
            
        Returns:
            Dictionary with PSA content and metadata
            
        Raises:
            ValueError: If pool not found
        """
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        # Convert pool to dict
        pool_data = {
            'pool_name': pool.pool_name,
            'pool_id': pool.pool_id,
            'pool_type': pool.pool_type,
            'total_pool_value': str(pool.total_pool_value),
            'currency': pool.currency,
            'created_at': pool.created_at.isoformat() if pool.created_at else datetime.now().isoformat(),
            'tranches': [],
            'assets': []
        }
        
        # Load tranches
        from app.db.models import SecuritizationTranche
        tranches = self.db.query(SecuritizationTranche).filter(
            SecuritizationTranche.pool_id == pool.id
        ).all()
        
        for tranche in tranches:
            pool_data['tranches'].append({
                'tranche_name': tranche.tranche_name,
                'tranche_class': tranche.tranche_class,
                'size': {'amount': float(tranche.size), 'currency': tranche.currency},
                'interest_rate': float(tranche.interest_rate),
                'risk_rating': tranche.risk_rating,
                'payment_priority': tranche.payment_priority
            })
        
        # Load assets
        from app.db.models import SecuritizationPoolAsset
        assets = self.db.query(SecuritizationPoolAsset).filter(
            SecuritizationPoolAsset.pool_id == pool.id
        ).all()
        
        for asset in assets:
            pool_data['assets'].append({
                'asset_type': asset.asset_type,
                'asset_id': asset.asset_id,
                'asset_value': str(asset.asset_value),
                'currency': asset.currency
            })
        
        # Load CDM data if available
        pool_cdm = None
        if pool.cdm_payload:
            try:
                # Try to reconstruct CDM model from payload
                # This is a simplified approach - in production, you'd properly deserialize
                pool_cdm = None  # Would need proper CDM deserialization
            except Exception as e:
                logger.warning(f"Could not load CDM data for pool {pool_id}: {e}")
        
        # Generate PSA template
        psa_data = generate_psa_template(pool_data, pool_cdm)
        
        # Save as generated document if user_id provided
        if user_id and output_format == 'docx':
            document = self._save_generated_document(
                pool_id=pool_id,
                document_type='PSA',
                content=psa_data['document_text'],
                user_id=user_id
            )
            psa_data['document_id'] = document.id
            psa_data['document_path'] = document.file_path
        
        return psa_data
    
    def generate_trust_agreement(
        self,
        pool_id: str,
        user_id: Optional[int] = None,
        output_format: str = 'text'
    ) -> Dict[str, Any]:
        """
        Generate Trust Agreement for a securitization pool.
        
        Args:
            pool_id: Pool identifier
            user_id: Optional user ID generating the document
            output_format: Output format ('text', 'dict', 'docx')
            
        Returns:
            Dictionary with Trust Agreement content and metadata
        """
        # Similar implementation to generate_psa
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        pool_data = self._get_pool_data(pool)
        pool_cdm = None
        
        trust_data = generate_trust_agreement_template(pool_data, pool_cdm)
        
        if user_id and output_format == 'docx':
            document = self._save_generated_document(
                pool_id=pool_id,
                document_type='Trust Agreement',
                content=trust_data['document_text'],
                user_id=user_id
            )
            trust_data['document_id'] = document.id
            trust_data['document_path'] = document.file_path
        
        return trust_data
    
    def generate_prospectus(
        self,
        pool_id: str,
        user_id: Optional[int] = None,
        output_format: str = 'text'
    ) -> Dict[str, Any]:
        """
        Generate Prospectus Supplement for a securitization pool.
        
        Args:
            pool_id: Pool identifier
            user_id: Optional user ID generating the document
            output_format: Output format ('text', 'dict', 'docx')
            
        Returns:
            Dictionary with Prospectus Supplement content and metadata
        """
        pool = self.db.query(SecuritizationPool).filter(
            SecuritizationPool.pool_id == pool_id
        ).first()
        
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        pool_data = self._get_pool_data(pool)
        pool_cdm = None
        
        prospectus_data = generate_prospectus_template(pool_data, pool_cdm)
        
        if user_id and output_format == 'docx':
            document = self._save_generated_document(
                pool_id=pool_id,
                document_type='Prospectus Supplement',
                content=prospectus_data['document_text'],
                user_id=user_id
            )
            prospectus_data['document_id'] = document.id
            prospectus_data['document_path'] = document.file_path
        
        return prospectus_data
    
    def generate_all_templates(
        self,
        pool_id: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate all securitization templates for a pool.
        
        Args:
            pool_id: Pool identifier
            user_id: Optional user ID generating the documents
            
        Returns:
            Dictionary with all generated templates
        """
        return {
            'psa': self.generate_psa(pool_id, user_id),
            'trust_agreement': self.generate_trust_agreement(pool_id, user_id),
            'prospectus': self.generate_prospectus(pool_id, user_id)
        }
    
    def _get_pool_data(self, pool: SecuritizationPool) -> Dict[str, Any]:
        """Get pool data dictionary from database model."""
        pool_data = {
            'pool_name': pool.pool_name,
            'pool_id': pool.pool_id,
            'pool_type': pool.pool_type,
            'total_pool_value': str(pool.total_pool_value),
            'currency': pool.currency,
            'created_at': pool.created_at.isoformat() if pool.created_at else datetime.now().isoformat(),
            'tranches': [],
            'assets': []
        }
        
        # Load tranches
        from app.db.models import SecuritizationTranche
        tranches = self.db.query(SecuritizationTranche).filter(
            SecuritizationTranche.pool_id == pool.id
        ).all()
        
        for tranche in tranches:
            pool_data['tranches'].append({
                'tranche_name': tranche.tranche_name,
                'tranche_class': tranche.tranche_class,
                'size': {'amount': float(tranche.size), 'currency': tranche.currency},
                'interest_rate': float(tranche.interest_rate),
                'risk_rating': tranche.risk_rating,
                'payment_priority': tranche.payment_priority
            })
        
        # Load assets
        from app.db.models import SecuritizationPoolAsset
        assets = self.db.query(SecuritizationPoolAsset).filter(
            SecuritizationPoolAsset.pool_id == pool.id
        ).all()
        
        for asset in assets:
            pool_data['assets'].append({
                'asset_type': asset.asset_type,
                'asset_id': asset.asset_id,
                'asset_value': str(asset.asset_value),
                'currency': asset.currency
            })
        
        return pool_data
    
    def _save_generated_document(
        self,
        pool_id: str,
        document_type: str,
        content: str,
        user_id: int
    ) -> GeneratedDocument:
        """Save generated document to database and storage."""
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"securitization_{pool_id}_{document_type.replace(' ', '_')}_{timestamp}.txt"
        
        # Save to storage
        file_path = self.storage.save_generated_document(
            content.encode('utf-8'),
            filename
        )
        
        # Create database record
        document = GeneratedDocument(
            title=f"{document_type} - Pool {pool_id}",
            file_path=file_path,
            document_type=document_type,
            source_type='securitization_template',
            metadata={
                'pool_id': pool_id,
                'document_type': document_type,
                'generated_at': datetime.now().isoformat()
            }
        )
        
        if user_id:
            document.user_id = user_id
        
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        
        logger.info(f"Saved generated {document_type} for pool {pool_id} as document {document.id}")
        return document
