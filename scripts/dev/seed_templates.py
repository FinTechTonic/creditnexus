"""
Script to seed initial LMA templates into database.

Loads template metadata from JSON file and creates LMATemplate and TemplateFieldMapping records.
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.templates.registry import TemplateRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_templates(db, templates_data: List[Dict[str, Any]]) -> int:
    """
    Seed templates into database.
    
    Args:
        db: Database session
        templates_data: List of template metadata dictionaries
        
    Returns:
        Number of templates created
    """
    created_count = 0
    
    for template_data in templates_data:
        template_code = template_data.get("template_code") or template_data.get("code")
        if not template_code:
            logger.warning(f"Skipping template without template_code: {template_data.get('name', 'Unknown')}")
            continue
        
        # Check if template already exists
        existing = TemplateRegistry.get_template_by_code(db, template_code)
        if existing:
            logger.info(f"Template {template_code} already exists, skipping")
            continue
        
        try:
            # Register template
            template = TemplateRegistry.register_template(db, {
                "template_code": template_code,
                "name": template_data.get("name", template_data.get("template_name", "Unknown Template")),
                "category": template_data.get("category", "Facility Agreement"),
                "subcategory": template_data.get("subcategory"),
                "governing_law": template_data.get("governing_law"),
                "version": template_data.get("version", "2024.1"),
                "file_path": template_data.get("file_path", f"storage/templates/{template_code}-{template_data.get('version', '2024.1')}.docx"),
                "metadata": template_data.get("metadata", {}),
                "required_fields": template_data.get("required_cdm_fields", template_data.get("required_fields", [])),
                "optional_fields": template_data.get("optional_cdm_fields", template_data.get("optional_fields", [])),
                "ai_generated_sections": template_data.get("ai_generated_sections", []),
            })
            
            created_count += 1
            logger.info(f"Created template: {template.name} ({template.template_code})")
            
            # Validate AI-generated sections have corresponding prompts
            ai_sections = template_data.get("ai_generated_sections", [])
            if ai_sections:
                _validate_ai_sections(template.category, ai_sections)
            
            # Seed field mappings if provided
            mappings = template_data.get("field_mappings", [])
            if mappings:
                seed_field_mappings(db, template.id, mappings)
                
        except Exception as e:
            logger.error(f"Failed to seed template {template_code}: {e}")
            db.rollback()
            continue
    
    return created_count


def seed_field_mappings(db, template_id: int, mappings: List[Dict[str, Any]]) -> int:
    """
    Seed field mappings for a template.
    
    Args:
        db: Database session
        template_id: Template ID
        mappings: List of field mapping dictionaries
        
    Returns:
        Number of mappings created
    """
    created_count = 0
    
    for mapping_data in mappings:
        try:
            mapping = TemplateRegistry.create_field_mapping(
                db=db,
                template_id=template_id,
                template_field=mapping_data.get("template_field"),
                cdm_field=mapping_data.get("cdm_field"),
                mapping_type=mapping_data.get("mapping_type", "direct"),
                transformation_rule=mapping_data.get("transformation_rule"),
                is_required=mapping_data.get("is_required", False),
            )
            created_count += 1
        except Exception as e:
            logger.warning(f"Failed to create field mapping: {e}")
            continue
    
    logger.info(f"Created {created_count} field mapping(s) for template {template_id}")
    return created_count


def _validate_ai_sections(template_category: str, ai_sections: List[str]) -> None:
    """
    Validate that all AI-generated sections have corresponding prompt templates.
    
    Args:
        template_category: Template category (e.g., "Facility Agreement")
        ai_sections: List of AI-generated section names
    """
    from app.prompts.templates.loader import PromptLoader
    from pathlib import Path
    import importlib.util
    
    # First check if prompt module file exists
    module_map = PromptLoader.PROMPT_MODULE_MAP
    if template_category not in module_map:
        logger.warning(
            f"Template category '{template_category}' not mapped in PROMPT_MODULE_MAP. "
            f"AI-generated sections will not be validated."
        )
        return
    
    module_path = module_map[template_category]
    # Convert module path to file path
    module_file = Path(module_path.replace(".", "/") + ".py")
    if not module_file.exists():
        logger.warning(
            f"Prompt module file not found for category '{template_category}': {module_path}. "
            f"AI-generated sections will not be available."
        )
        return
    
    # Validate each section has a prompt
    missing_prompts = []
    for section in ai_sections:
        try:
            prompt = PromptLoader.get_prompt_for_section(template_category, section)
            if not prompt:
                missing_prompts.append(section)
        except (ImportError, KeyError) as e:
            logger.warning(
                f"Error loading prompt for section '{section}' in category '{template_category}': {e}"
            )
            missing_prompts.append(section)
    
    if missing_prompts:
        logger.warning(
            f"Template category '{template_category}' has AI-generated sections without prompts: "
            f"{', '.join(missing_prompts)}. These sections will not be generated."
        )


def load_template_metadata(json_path: Path) -> List[Dict[str, Any]]:
    """
    Load template metadata from JSON file.
    
    Args:
        json_path: Path to JSON file containing template metadata
        
    Returns:
        List of template metadata dictionaries
    """
    if not json_path.exists():
        logger.warning(f"Template metadata file not found: {json_path}")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, dict) and "templates" in data:
        return data["templates"]
    elif isinstance(data, list):
        return data
    else:
        logger.error(f"Invalid JSON structure in {json_path}")
        return []


def main():
    """Main execution block."""
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Load template metadata
        # Try multiple possible locations
        json_paths = [
            Path("data/templates_metadata.json"),
            Path("scripts/templates_metadata.json"),
            Path("storage/templates_metadata.json"),
        ]
        
        templates_data = []
        for json_path in json_paths:
            if json_path.exists():
                templates_data = load_template_metadata(json_path)
                logger.info(f"Loaded template metadata from {json_path}")
                break
        
        if not templates_data:
            logger.warning("No template metadata file found. Creating sample templates...")
            # Create sample template data inline
            templates_data = [
                {
                    "template_code": "LMA-CL-FA-2024-EN",
                    "code": "CL-FA-EN",
                    "name": "Corporate Lending Facility Agreement (English Law)",
                    "category": "Facility Agreement",
                    "subcategory": "Corporate Lending - Syndicated",
                    "governing_law": "English",
                    "version": "2024.1",
                    "file_path": "storage/templates/facility_agreements/corporate_lending/english/CL-FA-EN-2024.1.docx",
                    "required_cdm_fields": [
                        "parties[role='Borrower'].name",
                        "parties[role='Borrower'].lei",
                        "facilities[0].facility_name",
                        "facilities[0].commitment_amount.amount",
                        "facilities[0].commitment_amount.currency",
                        "facilities[0].maturity_date",
                        "facilities[0].interest_terms.rate_option.benchmark",
                        "facilities[0].interest_terms.rate_option.spread_bps",
                        "agreement_date",
                        "governing_law"
                    ],
                    "optional_cdm_fields": [
                        "parties[role='Administrative Agent']",
                        "parties[role='Lender']",
                        "sustainability_linked",
                        "esg_kpi_targets",
                        "deal_id",
                        "loan_identification_number"
                    ],
                    "ai_generated_sections": [
                        "representations_and_warranties",
                        "conditions_precedent",
                        "covenants",
                        "events_of_default",
                        "governing_law_clause"
                    ],
                    "field_mappings": [
                        {
                            "template_field": "[BORROWER_NAME]",
                            "cdm_field": "parties[role='Borrower'].name",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[BORROWER_LEI]",
                            "cdm_field": "parties[role='Borrower'].lei",
                            "mapping_type": "direct",
                            "is_required": False
                        },
                        {
                            "template_field": "[FACILITY_NAME]",
                            "cdm_field": "facilities[0].facility_name",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[COMMITMENT_AMOUNT]",
                            "cdm_field": "facilities[0].commitment_amount.amount",
                            "mapping_type": "computed",
                            "transformation_rule": "format_currency",
                            "is_required": True
                        },
                        {
                            "template_field": "[CURRENCY]",
                            "cdm_field": "facilities[0].commitment_amount.currency",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[MATURITY_DATE]",
                            "cdm_field": "facilities[0].maturity_date",
                            "mapping_type": "computed",
                            "transformation_rule": "format_date",
                            "is_required": True
                        },
                        {
                            "template_field": "[BENCHMARK]",
                            "cdm_field": "facilities[0].interest_terms.rate_option.benchmark",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[SPREAD]",
                            "cdm_field": "facilities[0].interest_terms.rate_option.spread_bps",
                            "mapping_type": "computed",
                            "transformation_rule": "format_spread",
                            "is_required": True
                        },
                        {
                            "template_field": "[AGREEMENT_DATE]",
                            "cdm_field": "agreement_date",
                            "mapping_type": "computed",
                            "transformation_rule": "format_date",
                            "is_required": True
                        },
                        {
                            "template_field": "[GOVERNING_LAW]",
                            "cdm_field": "governing_law",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[REPRESENTATIONS_AND_WARRANTIES]",
                            "cdm_field": "",
                            "mapping_type": "ai_generated",
                            "is_required": False
                        },
                        {
                            "template_field": "[CONDITIONS_PRECEDENT]",
                            "cdm_field": "",
                            "mapping_type": "ai_generated",
                            "is_required": False
                        },
                        {
                            "template_field": "[COVENANTS]",
                            "cdm_field": "",
                            "mapping_type": "ai_generated",
                            "is_required": False
                        },
                        {
                            "template_field": "[EVENTS_OF_DEFAULT]",
                            "cdm_field": "",
                            "mapping_type": "ai_generated",
                            "is_required": False
                        }
                    ]
                },
                {
                    "template_code": "LMA-CL-TS-2024-EN",
                    "code": "CL-TS-EN",
                    "name": "Corporate Lending Term Sheet (English Law)",
                    "category": "Term Sheet",
                    "subcategory": "Corporate Lending",
                    "governing_law": "English",
                    "version": "2024.1",
                    "file_path": "storage/templates/term_sheets/corporate_lending/english/CL-TS-EN-2024.1.docx",
                    "required_cdm_fields": [
                        "parties[role='Borrower'].name",
                        "facilities[0].facility_name",
                        "facilities[0].commitment_amount.amount",
                        "facilities[0].commitment_amount.currency",
                        "facilities[0].maturity_date",
                        "facilities[0].interest_terms.rate_option.benchmark",
                        "facilities[0].interest_terms.rate_option.spread_bps"
                    ],
                    "optional_cdm_fields": [
                        "agreement_date",
                        "governing_law",
                        "sustainability_linked"
                    ],
                    "ai_generated_sections": [
                        "purpose",
                        "conditions_precedent",
                        "representations",
                        "fees"
                    ],
                    "field_mappings": [
                        {
                            "template_field": "[BORROWER]",
                            "cdm_field": "parties[role='Borrower'].name",
                            "mapping_type": "direct",
                            "is_required": True
                        },
                        {
                            "template_field": "[FACILITY_TYPE]",
                            "cdm_field": "facilities[0].facility_name",
                            "mapping_type": "computed",
                            "transformation_rule": "extract_facility_type",
                            "is_required": True
                        },
                        {
                            "template_field": "[TOTAL_COMMITMENT]",
                            "cdm_field": "facilities",
                            "mapping_type": "computed",
                            "transformation_rule": "sum_commitment_amounts",
                            "is_required": True
                        },
                        {
                            "template_field": "[PRICING]",
                            "cdm_field": "facilities[0].interest_terms.rate_option",
                            "mapping_type": "computed",
                            "transformation_rule": "format_pricing",
                            "is_required": True
                        },
                        {
                            "template_field": "[PURPOSE]",
                            "cdm_field": "",
                            "mapping_type": "ai_generated",
                            "is_required": False
                        }
                    ]
                }
            ]
        
        # Seed templates
        created = seed_templates(db, templates_data)
        
        # Commit transaction
        db.commit()
        
        logger.info(f"Successfully seeded {created} template(s)")
        
    except Exception as e:
        logger.error(f"Error seeding templates: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
















