"""
Template Recommendation Service.

Maps deal types to required templates, checks which templates have been generated
for a deal, and recommends missing templates.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import Deal, LMATemplate, GeneratedDocument, Document, TemplateCategory, DealType

logger = logging.getLogger(__name__)


class TemplateRecommendationService:
    """Service for recommending templates based on deal type and status."""
    
    # Mapping of deal types to required template categories
    DEAL_TYPE_TO_TEMPLATES = {
        DealType.LOAN_APPLICATION.value: [
            TemplateCategory.TERM_SHEET.value,
            TemplateCategory.FACILITY_AGREEMENT.value,
            TemplateCategory.CONFIDENTIALITY_AGREEMENT.value,
            TemplateCategory.ORIGINATION.value,
        ],
        DealType.DEBT_SALE.value: [
            TemplateCategory.SECONDARY_TRADING.value,
            TemplateCategory.CONFIDENTIALITY_AGREEMENT.value,
            TemplateCategory.SUPPORTING.value,
        ],
        DealType.LOAN_PURCHASE.value: [
            TemplateCategory.SECONDARY_TRADING.value,
            TemplateCategory.CONFIDENTIALITY_AGREEMENT.value,
            TemplateCategory.SUPPORTING.value,
        ],
        DealType.REFINANCING.value: [
            TemplateCategory.FACILITY_AGREEMENT.value,
            TemplateCategory.TERM_SHEET.value,
            TemplateCategory.CONFIDENTIALITY_AGREEMENT.value,
            TemplateCategory.SUPPORTING.value,
        ],
        DealType.RESTRUCTURING.value: [
            TemplateCategory.RESTRUCTURING.value,
            TemplateCategory.FACILITY_AGREEMENT.value,
            TemplateCategory.SUPPORTING.value,
        ],
    }
    
    # Optional templates that may be recommended based on deal characteristics
    OPTIONAL_TEMPLATE_CATEGORIES = {
        TemplateCategory.SUSTAINABLE_FINANCE.value: {
            "condition": lambda deal: deal.deal_data and deal.deal_data.get("sustainability_linked", False),
            "priority": "high",
        },
        TemplateCategory.REGULATORY.value: {
            "condition": lambda deal: deal.deal_data and deal.deal_data.get("requires_regulatory", False),
            "priority": "medium",
        },
        TemplateCategory.SECURITY_INTERCREDITOR.value: {
            "condition": lambda deal: deal.deal_data and deal.deal_data.get("has_security", False),
            "priority": "high",
        },
    }
    
    def __init__(self, db: Session):
        """
        Initialize template recommendation service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_required_templates_for_deal_type(
        self,
        deal_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Get list of required templates for a deal type.
        
        Args:
            deal_type: Deal type (e.g., "loan_application", "debt_sale")
            
        Returns:
            List of template dictionaries with category, priority, and description
        """
        if not deal_type:
            return []
        
        required_categories = self.DEAL_TYPE_TO_TEMPLATES.get(deal_type, [])
        
        templates = []
        for category in required_categories:
            # Get templates in this category
            category_templates = self.db.query(LMATemplate).filter(
                LMATemplate.category == category
            ).all()
            
            for template in category_templates:
                templates.append({
                    "template_id": template.id,
                    "template_code": template.template_code,
                    "name": template.name,
                    "category": template.category,
                    "subcategory": template.subcategory,
                    "governing_law": template.governing_law,
                    "priority": "required",
                    "reason": f"Required for {deal_type} deals",
                })
        
        return templates
    
    def get_optional_templates_for_deal(
        self,
        deal: Deal
    ) -> List[Dict[str, Any]]:
        """
        Get list of optional templates based on deal characteristics.
        
        Args:
            deal: Deal instance
            
        Returns:
            List of optional template dictionaries
        """
        optional_templates = []
        
        for category, config in self.OPTIONAL_TEMPLATE_CATEGORIES.items():
            # Check if condition is met
            if config["condition"](deal):
                # Get templates in this category
                category_templates = self.db.query(LMATemplate).filter(
                    LMATemplate.category == category
                ).all()
                
                for template in category_templates:
                    optional_templates.append({
                        "template_id": template.id,
                        "template_code": template.template_code,
                        "name": template.name,
                        "category": template.category,
                        "subcategory": template.subcategory,
                        "governing_law": template.governing_law,
                        "priority": config["priority"],
                        "reason": self._get_recommendation_reason(category, deal),
                    })
        
        return optional_templates
    
    def get_generated_templates_for_deal(
        self,
        deal_id: int
    ) -> Set[int]:
        """
        Get set of template IDs that have been generated for a deal.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            Set of template IDs that have been generated
        """
        # Get generated documents linked to this deal
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return set()
        
        # Get documents linked to deal
        documents = self.db.query(Document).filter(
            Document.deal_id == deal_id
        ).all()
        
        generated_template_ids = set()
        
        # Check GeneratedDocument records linked to deal documents
        # First, get all document IDs for this deal
        document_ids = [doc.id for doc in documents]
        
        if document_ids:
            generated_docs = self.db.query(GeneratedDocument).filter(
                GeneratedDocument.source_document_id.in_(document_ids)
            ).all()
            
            for gen_doc in generated_docs:
                if gen_doc.template_id:
                    generated_template_ids.add(gen_doc.template_id)
        
        # Also check documents that have template_id set (generated documents stored as Document records)
        for doc in documents:
            if doc.template_id:
                generated_template_ids.add(doc.template_id)
        
        return generated_template_ids
    
    def recommend_templates(
        self,
        deal_id: int
    ) -> Dict[str, Any]:
        """
        Recommend templates for a deal based on deal type and generated status.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            Dictionary with:
            - required_templates: List of required templates not yet generated
            - optional_templates: List of optional templates that may be useful
            - generated_templates: List of templates already generated
            - missing_required: List of required templates that are missing
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return {
                "error": f"Deal {deal_id} not found",
                "required_templates": [],
                "optional_templates": [],
                "generated_templates": [],
                "missing_required": [],
            }
        
        # Get required templates for deal type
        required_templates = self.get_required_templates_for_deal_type(deal.deal_type)
        
        # Get optional templates
        optional_templates = self.get_optional_templates_for_deal(deal)
        
        # Get generated templates
        generated_template_ids = self.get_generated_templates_for_deal(deal_id)
        
        # Separate required templates into generated and missing
        generated_required = []
        missing_required = []
        
        for template in required_templates:
            if template["template_id"] in generated_template_ids:
                generated_required.append(template)
            else:
                missing_required.append(template)
        
        # Filter optional templates (exclude already generated)
        optional_not_generated = [
            t for t in optional_templates
            if t["template_id"] not in generated_template_ids
        ]
        
        # Get full details of generated templates
        generated_templates = []
        if generated_template_ids:
            generated_template_objs = self.db.query(LMATemplate).filter(
                LMATemplate.id.in_(generated_template_ids)
            ).all()
            
            for template in generated_template_objs:
                generated_templates.append({
                    "template_id": template.id,
                    "template_code": template.template_code,
                    "name": template.name,
                    "category": template.category,
                    "subcategory": template.subcategory,
                    "governing_law": template.governing_law,
                })
        
        return {
            "deal_id": deal_id,
            "deal_type": deal.deal_type,
            "required_templates": required_templates,
            "optional_templates": optional_templates,
            "generated_templates": generated_templates,
            "generated_required": generated_required,
            "missing_required": missing_required,
            "optional_not_generated": optional_not_generated,
            "completion_status": {
                "required_generated": len(generated_required),
                "required_total": len(required_templates),
                "optional_available": len(optional_not_generated),
                "completion_percentage": (
                    (len(generated_required) / len(required_templates) * 100)
                    if required_templates else 100
                ),
            },
        }
    
    def _get_recommendation_reason(
        self,
        category: str,
        deal: Deal
    ) -> str:
        """
        Get human-readable reason for recommending a template category.
        
        Args:
            category: Template category
            deal: Deal instance
            
        Returns:
            Recommendation reason string
        """
        reasons = {
            TemplateCategory.SUSTAINABLE_FINANCE.value: (
                "This deal is sustainability-linked. A sustainability-linked loan "
                "facility agreement is recommended to include ESG provisions."
            ),
            TemplateCategory.REGULATORY.value: (
                "This deal requires regulatory compliance documentation based on "
                "deal characteristics."
            ),
            TemplateCategory.SECURITY_INTERCREDITOR.value: (
                "This deal involves security arrangements. An intercreditor agreement "
                "is recommended to define creditor priorities."
            ),
        }
        
        return reasons.get(category, f"Recommended for {category} deals")
    
    def get_template_by_category(
        self,
        category: str,
        governing_law: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get templates by category, optionally filtered by governing law.
        
        Args:
            category: Template category
            governing_law: Optional governing law filter
            
        Returns:
            List of template dictionaries
        """
        query = self.db.query(LMATemplate).filter(
            LMATemplate.category == category
        )
        
        if governing_law:
            query = query.filter(LMATemplate.governing_law == governing_law)
        
        templates = query.all()
        
        return [
            {
                "template_id": t.id,
                "template_code": t.template_code,
                "name": t.name,
                "category": t.category,
                "subcategory": t.subcategory,
                "governing_law": t.governing_law,
                "version": t.version,
            }
            for t in templates
        ]
