"""
Script to seed field mappings for LMA templates.

Creates field mappings from CDM paths to template bracket format placeholders.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.templates.registry import TemplateRegistry

# Field mappings for Facility Agreement template (LMA-CL-FA-2024-EN)
FACILITY_AGREEMENT_MAPPINGS = [
    # Parties
    {"template_field": "[BORROWER_NAME]", "cdm_field": "parties[role='Borrower'].name", "mapping_type": "direct", "is_required": True},
    {"template_field": "[BORROWER_LEI]", "cdm_field": "parties[role='Borrower'].lei", "mapping_type": "direct", "is_required": False},
    {"template_field": "[LENDER_NAME]", "cdm_field": "parties[role='Lender'].name", "mapping_type": "direct", "is_required": False},
    {"template_field": "[ADMINISTRATIVE_AGENT_NAME]", "cdm_field": "parties[role='AdministrativeAgent'].name", "mapping_type": "direct", "is_required": False},
    
    # Facility Details
    {"template_field": "[FACILITY_NAME]", "cdm_field": "facilities[0].facility_name", "mapping_type": "direct", "is_required": True},
    {"template_field": "[COMMITMENT_AMOUNT]", "cdm_field": "facilities[0].commitment_amount.amount", "mapping_type": "direct", "is_required": True},
    {"template_field": "[CURRENCY]", "cdm_field": "facilities[0].commitment_amount.currency", "mapping_type": "direct", "is_required": True},
    {"template_field": "[MATURITY_DATE]", "cdm_field": "facilities[0].maturity_date", "mapping_type": "direct", "is_required": True},
    {"template_field": "[AGREEMENT_DATE]", "cdm_field": "agreement_date", "mapping_type": "direct", "is_required": True},
    
    # Interest Terms
    {"template_field": "[BENCHMARK]", "cdm_field": "facilities[0].interest_terms.rate_option.benchmark", "mapping_type": "direct", "is_required": False},
    {"template_field": "[SPREAD]", "cdm_field": "facilities[0].interest_terms.rate_option.spread_bps", "mapping_type": "direct", "is_required": False},
    {"template_field": "[PAYMENT_FREQUENCY]", "cdm_field": "facilities[0].interest_terms.payment_frequency", "mapping_type": "direct", "is_required": False},
    
    # Governing Law
    {"template_field": "[GOVERNING_LAW]", "cdm_field": "governing_law", "mapping_type": "direct", "is_required": False},
    
    # ESG Fields (optional)
    {"template_field": "[SUSTAINABILITY_LINKED]", "cdm_field": "sustainability_linked", "mapping_type": "direct", "is_required": False},
    {"template_field": "[ESG_KPI_TARGETS]", "cdm_field": "esg_kpi_targets", "mapping_type": "direct", "is_required": False},
    {"template_field": "[SPT_DEFINITIONS]", "cdm_field": "spt_definitions", "mapping_type": "direct", "is_required": False},
    {"template_field": "[MARGIN_ADJUSTMENT]", "cdm_field": "margin_adjustment", "mapping_type": "direct", "is_required": False},
]

# Field mappings for Term Sheet template (LMA-CL-TS-2024-EN)
TERM_SHEET_MAPPINGS = [
    # Parties
    {"template_field": "[BORROWER_NAME]", "cdm_field": "parties[role='Borrower'].name", "mapping_type": "direct", "is_required": True},
    {"template_field": "[BORROWER_LEI]", "cdm_field": "parties[role='Borrower'].lei", "mapping_type": "direct", "is_required": False},
    {"template_field": "[LENDER_NAME]", "cdm_field": "parties[role='Lender'].name", "mapping_type": "direct", "is_required": False},
    
    # Facility Details
    {"template_field": "[FACILITY_NAME]", "cdm_field": "facilities[0].facility_name", "mapping_type": "direct", "is_required": True},
    {"template_field": "[COMMITMENT_AMOUNT]", "cdm_field": "facilities[0].commitment_amount.amount", "mapping_type": "direct", "is_required": True},
    {"template_field": "[CURRENCY]", "cdm_field": "facilities[0].commitment_amount.currency", "mapping_type": "direct", "is_required": True},
    {"template_field": "[MATURITY_DATE]", "cdm_field": "facilities[0].maturity_date", "mapping_type": "direct", "is_required": True},
    {"template_field": "[AGREEMENT_DATE]", "cdm_field": "agreement_date", "mapping_type": "direct", "is_required": False},
    
    # Interest Terms
    {"template_field": "[BENCHMARK]", "cdm_field": "facilities[0].interest_terms.rate_option.benchmark", "mapping_type": "direct", "is_required": False},
    {"template_field": "[SPREAD]", "cdm_field": "facilities[0].interest_terms.rate_option.spread_bps", "mapping_type": "direct", "is_required": False},
    {"template_field": "[PAYMENT_FREQUENCY]", "cdm_field": "facilities[0].interest_terms.payment_frequency", "mapping_type": "direct", "is_required": False},
    
    # Governing Law
    {"template_field": "[GOVERNING_LAW]", "cdm_field": "governing_law", "mapping_type": "direct", "is_required": False},
    
    # ESG/Sustainability Fields
    {"template_field": "[SUSTAINABILITY_LINKED]", "cdm_field": "sustainability_linked", "mapping_type": "direct", "is_required": False},
    {"template_field": "[SPT_DEFINITIONS]", "cdm_field": "spt_definitions", "mapping_type": "direct", "is_required": False},
    {"template_field": "[MARGIN_ADJUSTMENT]", "cdm_field": "margin_adjustment", "mapping_type": "direct", "is_required": False},
    {"template_field": "[ESG_KPI_TARGETS]", "cdm_field": "esg_kpi_targets", "mapping_type": "direct", "is_required": False},
    
    # Parties (additional)
    {"template_field": "[ADMINISTRATIVE_AGENT_NAME]", "cdm_field": "parties[role='AdministrativeAgent'].name", "mapping_type": "direct", "is_required": False},
    
    # AI-Generated Sections (these will be handled by AIFieldPopulator)
    {"template_field": "[REPRESENTATIONS_AND_WARRANTIES]", "cdm_field": "representations_and_warranties", "mapping_type": "ai_generated", "is_required": False},
    {"template_field": "[COVENANTS]", "cdm_field": "covenants", "mapping_type": "ai_generated", "is_required": False},
    {"template_field": "[EVENTS_OF_DEFAULT]", "cdm_field": "events_of_default", "mapping_type": "ai_generated", "is_required": False},
]


def seed_field_mappings_for_template(db, template_code: str, mappings: list):
    """
    Seed field mappings for a template.
    
    Args:
        db: Database session
        template_code: Template code (e.g., "LMA-CL-FA-2024-EN")
        mappings: List of field mapping dictionaries
    """
    # Get template
    template = TemplateRegistry.get_template_by_code(db, template_code)
    if not template:
        print(f"Template {template_code} not found. Skipping field mappings.")
        return 0
    
    # Check if mappings already exist - delete them to allow re-seeding
    existing_mappings = TemplateRegistry.get_field_mappings(db, template.id)
    if existing_mappings:
        print(f"Template {template_code} has {len(existing_mappings)} existing field mapping(s). Deleting to re-seed...")
        from app.db.models import TemplateFieldMapping
        db.query(TemplateFieldMapping).filter(TemplateFieldMapping.template_id == template.id).delete()
        db.commit()
    
    # Create mappings
    created_count = 0
    for mapping_data in mappings:
        try:
            TemplateRegistry.create_field_mapping(
                db=db,
                template_id=template.id,
                template_field=mapping_data["template_field"],
                cdm_field=mapping_data["cdm_field"],
                mapping_type=mapping_data.get("mapping_type", "direct"),
                transformation_rule=mapping_data.get("transformation_rule"),
                is_required=mapping_data.get("is_required", False),
            )
            created_count += 1
        except Exception as e:
            print(f"Error creating field mapping {mapping_data['template_field']}: {e}")
            continue
    
    print(f"Created {created_count} field mapping(s) for template {template_code}")
    return created_count


def main():
    """Seed field mappings for all templates."""
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Seed mappings for Facility Agreement
        seed_field_mappings_for_template(db, "LMA-CL-FA-2024-EN", FACILITY_AGREEMENT_MAPPINGS)
        
        # Seed mappings for Term Sheet
        seed_field_mappings_for_template(db, "LMA-CL-TS-2024-EN", TERM_SHEET_MAPPINGS)
        
        db.commit()
        print("\nField mappings seeded successfully!")
        
    except Exception as e:
        print(f"Error: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
