"""
Document generation service for LMA templates.

Orchestrates the complete document generation workflow:
1. CDM data validation
2. Field mapping (CDM to template)
3. AI field population
4. Document rendering
5. Storage and database persistence
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cdm import CreditAgreement
from app.db.models import LMATemplate, GeneratedDocument, User
from app.templates.registry import TemplateRegistry
from app.templates.storage import TemplateStorage
from app.generation.mapper import FieldMapper
from app.generation.populator import AIFieldPopulator
from app.generation.renderer import DocumentRenderer
from app.utils.json_serializer import serialize_cdm_data

logger = logging.getLogger(__name__)


class DocumentGenerationService:
    """
    Service for generating LMA documents from templates.
    
    Coordinates:
    - Template retrieval
    - CDM data validation
    - Field mapping
    - AI field population
    - Document rendering
    - Storage and persistence
    """
    
    def __init__(self):
        """Initialize document generation service."""
        self.template_storage = TemplateStorage()
        self.renderer = DocumentRenderer()
        logger.info("DocumentGenerationService initialized")
    
    def generate_document(
        self,
        db: Session,
        template_id: int,
        cdm_data: CreditAgreement,
        user_id: Optional[int] = None,
        source_document_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        field_overrides: Optional[Dict[str, Any]] = None
    ) -> GeneratedDocument:
        """
        Generate a document from a template using CDM data.
        
        Args:
            db: Database session
            template_id: Template ID
            cdm_data: CreditAgreement instance with CDM data
            user_id: Optional user ID who is generating the document
            source_document_id: Optional source document ID if generated from existing document
            deal_id: Optional deal ID to load deal context and link generated document to deal
            field_overrides: Optional dictionary of field path -> value to override in CDM data
                Example: {"parties[role='Borrower'].lei": "12345678901234567890"}
            
        Returns:
            GeneratedDocument instance
            
        Raises:
            ValueError: If template not found or required fields missing
            IOError: If template file cannot be loaded or document cannot be saved
        """
        # Apply field overrides if provided
        if field_overrides:
            cdm_data = self._apply_field_overrides(cdm_data, field_overrides)
            logger.info(f"Applied {len(field_overrides)} field override(s)")
        
        # Get template from database with mappings loaded
        try:
            template = TemplateRegistry.get_template(db, template_id)
            # Ensure mappings are loaded
            if not template.field_mappings:
                # Load mappings explicitly
                from app.db.models import TemplateFieldMapping
                template.field_mappings = db.query(TemplateFieldMapping).filter(
                    TemplateFieldMapping.template_id == template_id
                ).all()
        except Exception as e:
            raise ValueError(f"Template with ID {template_id} not found: {e}") from e
        
        logger.info(f"Generating document from template {template.template_code} (ID: {template_id})")
        
        # Create field mapper with template and its mappings
        field_mapper = FieldMapper(template, field_mappings=template.field_mappings)
        
        # Validate required fields
        missing_fields = field_mapper.validate_required_fields(cdm_data)
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            # Don't fail, but log warning - some fields may be optional in practice
        
        # Map CDM data to template fields
        mapped_fields = field_mapper.map_cdm_to_template(cdm_data)
        logger.debug(f"Mapped {len(mapped_fields)} field(s) from CDM data")
        
        # Load deal context if deal_id provided
        deal_context = None
        related_documents = []
        if deal_id:
            try:
                from app.services.deal_service import DealService
                deal_service = DealService(db)
                deal = deal_service.get_deal(deal_id)
                if deal:
                    deal_context = {
                        "deal_id": deal.deal_id,
                        "status": deal.status,
                        "deal_type": deal.deal_type,
                        "deal_data": deal.deal_data,
                    }
                    
                    # Load related documents from database
                    from app.db.models import Document
                    db_docs = db.query(Document).filter(
                        Document.deal_id == deal_id
                    ).order_by(Document.created_at.desc()).limit(5).all()
                    
                    for doc in db_docs:
                        related_documents.append({
                            "document_id": doc.id,
                            "title": doc.title,
                            "subdirectory": "documents",
                            "source": "database",
                        })
                    
                    # Try to load from ChromaDB for semantically similar documents
                    try:
                        from app.chains.document_retrieval_chain import DocumentRetrievalService
                        doc_retrieval = DocumentRetrievalService(collection_name="creditnexus_documents")
                        search_query = f"deal {deal.deal_id} {deal.deal_type or ''} {deal.status or ''}"
                        
                        similar_docs = doc_retrieval.retrieve_similar_documents(
                            query=search_query,
                            top_k=5,
                            filter_metadata={"deal_id": str(deal_id)} if deal_id else None
                        )
                        
                        # Merge with database documents, avoiding duplicates
                        existing_ids = {doc["document_id"] for doc in related_documents if "document_id" in doc}
                        for doc in similar_docs:
                            if doc.get("document_id") not in existing_ids:
                                related_documents.append(doc)
                    except Exception as e:
                        logger.warning(f"Failed to load related documents from ChromaDB: {e}")
                    
                    logger.info(f"Loaded deal context for deal {deal_id}: {deal.deal_id}")
            except Exception as e:
                logger.warning(f"Failed to load deal context: {e}")
        
        # Load user profile if user_id provided
        user_profile = None
        if user_id:
            try:
                from app.db.models import User
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user_profile = {
                        "role": user.role,
                        "display_name": user.display_name,
                        "profile_data": user.profile_data,
                    }
                    logger.debug(f"Loaded user profile for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to load user profile: {e}")
        
        # Generate AI-populated fields with context
        ai_populator = AIFieldPopulator(db=db)
        ai_fields = ai_populator.populate_ai_fields(
            cdm_data=cdm_data,
            template=template,
            mapped_fields=mapped_fields,
            user_id=user_id,
            deal_context=deal_context,
            user_profile=user_profile,
            related_documents=related_documents
        )
        logger.debug(f"Generated {len(ai_fields)} AI field(s)")
        
        # Merge mapped and AI-generated fields
        all_field_values = {**mapped_fields, **ai_fields}
        
        # Load template file
        try:
            template_path = self.template_storage.get_template_path(
                template_code=template.template_code,
                version=template.version
            )
        except FileNotFoundError:
            # Try using file_path from template metadata
            template_path = template.file_path
            template_file = Path(template_path)
            if not template_file.exists():
                raise IOError(f"Template file not found: {template_path}")
        
        # Render document
        try:
            rendered_doc = self.renderer.render_template(
                template_path=template_path,
                field_values=all_field_values,
                cdm_data=cdm_data
            )
        except Exception as e:
            raise IOError(f"Failed to render template: {e}") from e
        
        # Validate rendered document for remaining placeholders
        validation_result = self.renderer.validate_rendered_document(rendered_doc)
        
        if not validation_result["valid"]:
            logger.warning(
                f"Document rendered with {validation_result['total_placeholders_found']} remaining placeholder(s): "
                f"{', '.join(validation_result['remaining_placeholders'][:5])}"
            )
        
        # Save generated document
        filename = f"generated_{template.template_code}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        try:
            file_path = self.template_storage.save_generated_document(
                content=self.renderer.render_template_to_bytes(template_path, all_field_values, cdm_data),
                filename=filename
            )
        except Exception as e:
            raise IOError(f"Failed to save generated document: {e}") from e
        
        # Create generation summary
        generation_summary = self.get_generation_summary(
            mapped_fields, 
            ai_fields, 
            missing_fields,
            validation_result=validation_result
        )
        
        # Create GeneratedDocument record
        # Serialize CDM data to JSON-safe format (handles Decimal, datetime, etc.)
        cdm_data_dict = serialize_cdm_data(cdm_data)
        
        generated_doc = GeneratedDocument(
            template_id=template_id,
            source_document_id=source_document_id,
            cdm_data=cdm_data_dict,
            generated_content=None,  # Optional: store text content if needed
            file_path=file_path,
            status="draft",
            generation_summary=generation_summary,
            created_by=user_id,
        )
        
        db.add(generated_doc)
        db.commit()
        db.refresh(generated_doc)
        
        # Link generated document to deal if deal_id provided
        if deal_id:
            try:
                from app.db.models import Document
                from app.services.deal_service import DealService
                
                # Create Document record for generated document
                generated_doc_record = Document(
                    title=generated_doc.file_path.split('/')[-1] or f"Generated from {template.template_code}",
                    uploaded_by=user_id,
                    deal_id=deal_id,
                    is_generated=True,
                    template_id=template_id,
                    source_cdm_data=cdm_data_dict,
                )
                db.add(generated_doc_record)
                db.flush()
                
                # Attach to deal via DealService
                deal_service = DealService(db)
                deal_service.attach_document_to_deal(
                    deal_id=deal_id,
                    document_id=generated_doc_record.id,
                    user_id=user_id
                )
                
                db.commit()
                logger.info(f"Linked generated document {generated_doc_record.id} to deal {deal_id}")
            except Exception as e:
                logger.warning(f"Failed to link generated document to deal: {e}")
                # Don't fail the generation if linking fails
        
        logger.info(f"Generated document ID {generated_doc.id} from template {template.template_code}")
        return generated_doc
    
    def get_generation_summary(
        self,
        mapped_fields: Dict[str, Any],
        ai_fields: Dict[str, str],
        missing_fields: Optional[list] = None,
        validation_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary of the document generation process.
        
        Args:
            mapped_fields: Dictionary of directly/computed mapped fields
            ai_fields: Dictionary of AI-generated fields
            missing_fields: Optional list of missing required fields
            validation_result: Optional validation result from post-render validation
            
        Returns:
            Summary dictionary with statistics and metadata
        """
        summary = {
            "total_fields": len(mapped_fields) + len(ai_fields),
            "mapped_fields_count": len(mapped_fields),
            "ai_fields_count": len(ai_fields),
            "missing_required_fields": missing_fields or [],
            "mapped_field_names": list(mapped_fields.keys()),
            "ai_field_names": list(ai_fields.keys()),
            "generation_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add validation results if provided
        if validation_result:
            summary["validation"] = {
                "valid": validation_result["valid"],
                "remaining_placeholders_count": len(validation_result["remaining_placeholders"]),
                "remaining_placeholders": validation_result["remaining_placeholders"],
                "total_placeholders_found": validation_result["total_placeholders_found"]
            }
        
        return summary
    
    def _apply_field_overrides(
        self,
        cdm_data: CreditAgreement,
        field_overrides: Dict[str, Any]
    ) -> CreditAgreement:
        """
        Apply field overrides to CDM data.
        
        Args:
            cdm_data: Original CreditAgreement instance
            field_overrides: Dictionary mapping field paths to values
                Example: {"parties[role='Borrower'].lei": "12345678901234567890"}
            
        Returns:
            New CreditAgreement instance with overrides applied
        """
        from app.generation.field_parser import FieldPathParser
        
        # Convert CDM model to dict for easier manipulation
        # Use mode='json' to get a deep copy that we can safely modify
        # Include all fields (even unset ones) to preserve structure
        cdm_dict = cdm_data.model_dump(mode='json', exclude_unset=False, exclude_none=False)
        parser = FieldPathParser()
        
        # Apply each override
        for field_path, value in field_overrides.items():
            try:
                # Special handling: if the override is for a top-level field that's a list/object,
                # and the value is also a dict/list, we need to merge rather than replace
                if '.' not in field_path and '[' not in field_path:
                    # Simple top-level field - check if it's a dict/list that needs merging
                    if isinstance(value, dict) and isinstance(cdm_dict.get(field_path), dict):
                        # Merge dictionaries recursively to preserve nested structures
                        def deep_merge(base: dict, override: dict) -> dict:
                            """Recursively merge override dict into base dict."""
                            result = base.copy()
                            for key, val in override.items():
                                if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                                    result[key] = deep_merge(result[key], val)
                                else:
                                    result[key] = val
                            return result
                        cdm_dict[field_path] = deep_merge(cdm_dict[field_path], value)
                        logger.debug(f"Merged override for top-level field: {field_path}")
                        continue
                    elif isinstance(value, list) and isinstance(cdm_dict.get(field_path), list):
                        # For lists, we need to be careful - if items have IDs, merge by ID
                        # Otherwise, replace the list
                        cdm_dict[field_path] = value
                        logger.debug(f"Replaced list override for top-level field: {field_path}")
                        continue
                
                # Use the parser's set_nested_value method for nested paths
                parser.set_nested_value(cdm_dict, field_path, value)
                logger.debug(f"Applied override: {field_path} = {value}")
            except Exception as e:
                logger.warning(f"Failed to apply override for {field_path}: {e}")
                continue
        
        # Reconstruct CreditAgreement from modified dict
        # Use model_validate to handle missing required fields more gracefully
        try:
            # First, ensure all required fields are present by using model_validate with mode='json'
            # This will use default values for missing optional fields
            return CreditAgreement.model_validate(cdm_dict, strict=False)
        except Exception as e:
            logger.error(f"Failed to reconstruct CreditAgreement after overrides: {e}")
            # Try to preserve as much as possible by using the original data
            # and only applying the overrides that worked
            logger.warning("Returning original CDM data due to validation failure")
            return cdm_data

