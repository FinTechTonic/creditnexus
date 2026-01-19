"""
Script to load LMA template metadata and CDM schema docs into vector store.

This script:
1. Loads all LMA templates from the database
2. Generates CDM schema documentation from Pydantic models
3. Adds all content to ChromaDB knowledge base for chatbot RAG
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import inspect

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.templates.registry import TemplateRegistry
from app.chains.decision_support_chain import DecisionSupportChatbot
from app.models.cdm import (
    CreditAgreement,
    Party,
    LoanFacility,
    Money,
    Frequency,
    FloatingRateOption,
    InterestRatePayout,
    ESGKPITarget,
    Currency,
    GoverningLaw,
    ESGKPIType,
    PeriodEnum,
    ExtractionStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_template_documentation(template: Dict[str, Any]) -> str:
    """Generate documentation text for a template.
    
    Args:
        template: Template dictionary from database
        
    Returns:
        Documentation text for the template
    """
    doc_parts = []
    
    doc_parts.append(f"LMA Template: {template.get('name', 'Unknown')}")
    doc_parts.append(f"Template Code: {template.get('template_code', 'N/A')}")
    doc_parts.append(f"Category: {template.get('category', 'N/A')}")
    
    if template.get('subcategory'):
        doc_parts.append(f"Subcategory: {template['subcategory']}")
    
    if template.get('governing_law'):
        doc_parts.append(f"Governing Law: {template['governing_law']}")
    
    doc_parts.append(f"Version: {template.get('version', 'N/A')}")
    
    # Required fields
    required_fields = template.get('required_fields', [])
    if required_fields:
        doc_parts.append(f"\nRequired CDM Fields ({len(required_fields)}):")
        for field in required_fields:
            doc_parts.append(f"  - {field}")
    
    # Optional fields
    optional_fields = template.get('optional_fields', [])
    if optional_fields:
        doc_parts.append(f"\nOptional CDM Fields ({len(optional_fields)}):")
        for field in optional_fields[:10]:  # Limit to first 10
            doc_parts.append(f"  - {field}")
        if len(optional_fields) > 10:
            doc_parts.append(f"  ... and {len(optional_fields) - 10} more")
    
    # AI-generated sections
    ai_sections = template.get('ai_generated_sections', [])
    if ai_sections:
        doc_parts.append(f"\nAI-Generated Sections ({len(ai_sections)}):")
        for section in ai_sections:
            doc_parts.append(f"  - {section}")
    
    # Metadata
    metadata = template.get('metadata', {})
    if metadata:
        doc_parts.append(f"\nAdditional Metadata:")
        for key, value in list(metadata.items())[:5]:  # Limit to first 5
            doc_parts.append(f"  - {key}: {value}")
    
    return "\n".join(doc_parts)


def generate_cdm_schema_documentation() -> List[Dict[str, str]]:
    """Generate CDM schema documentation from Pydantic models.
    
    Returns:
        List of documentation dictionaries with content and metadata
    """
    docs = []
    
    # CreditAgreement documentation
    credit_agreement_doc = """CDM CreditAgreement Model

The CreditAgreement is the root object representing a syndicated credit agreement.

Required Fields:
- parties: List[Party] - At least one party required, must include at least one Borrower
- facilities: List[LoanFacility] - At least one facility required
- agreement_date: date (ISO 8601: YYYY-MM-DD) - Must not be in the future
- governing_law: str - Jurisdiction governing the agreement

Optional Fields:
- deal_id: str - Unique deal identifier
- loan_identification_number: str - Loan Identification Number (LIN)
- sustainability_linked: bool - Whether this is a sustainability-linked loan
- esg_kpi_targets: List[ESGKPITarget] - ESG KPI targets for sustainability-linked loans
- extraction_status: ExtractionStatus - Status of extraction (success, partial_data_missing, irrelevant_document)

Validation Rules:
- At least one party must have role 'Borrower'
- All facilities must use the same currency
- Each facility's maturity_date must be after agreement_date
- If sustainability_linked is true, esg_kpi_targets should be provided
- Parties with LEI must have exactly 20 alphanumeric characters

Example:
{
  "agreement_date": "2024-01-15",
  "parties": [
    {"id": "p1", "name": "ACME Corp", "role": "Borrower", "lei": "12345678901234567890"}
  ],
  "facilities": [
    {
      "facility_name": "Term Loan A",
      "commitment_amount": {"amount": 1000000, "currency": "USD"},
      "interest_terms": {
        "rate_option": {"benchmark": "SOFR", "spread_bps": 250.0},
        "payment_frequency": {"period": "Month", "period_multiplier": 3}
      },
      "maturity_date": "2029-01-15"
    }
  ],
  "governing_law": "NY"
}"""
    
    docs.append({
        "content": credit_agreement_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_model",
            "model_name": "CreditAgreement",
        }
    })
    
    # Party documentation
    party_doc = """CDM Party Model

Represents a legal entity involved in the credit agreement.

Required Fields:
- id: str - Unique identifier for the party in the document
- name: str - Legal name of the party
- role: str - Role of the party (e.g., 'Borrower', 'Lender', 'Administrative Agent', 'Guarantor')

Optional Fields:
- lei: str - Legal Entity Identifier (LEI), must be exactly 20 alphanumeric characters if provided

Common Roles:
- Borrower: The entity borrowing funds
- Lender: The entity providing funds
- Administrative Agent: Manages the loan on behalf of lenders
- Guarantor: Provides guarantee for the borrower's obligations
- Collateral Agent: Manages collateral

Example:
{
  "id": "p1",
  "name": "ACME Corporation",
  "role": "Borrower",
  "lei": "12345678901234567890"
}"""
    
    docs.append({
        "content": party_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_model",
            "model_name": "Party",
        }
    })
    
    # LoanFacility documentation
    facility_doc = """CDM LoanFacility Model

Represents a single loan facility within a credit agreement.

Required Fields:
- facility_name: str - Name of the facility (e.g., 'Term Loan A', 'Revolving Credit Facility')
- commitment_amount: Money - Total commitment amount with currency
- interest_terms: InterestRatePayout - Interest rate structure and payment frequency
- maturity_date: date (ISO 8601: YYYY-MM-DD) - Must be after agreement_date

Money Structure:
- amount: Decimal - Numerical monetary amount (use Decimal for precision)
- currency: Currency - Currency code (USD, EUR, GBP, JPY)

InterestRatePayout Structure:
- rate_option: FloatingRateOption
  - benchmark: str - Floating rate index (e.g., 'SOFR', 'EURIBOR', 'Term SOFR')
  - spread_bps: float - Margin in basis points (e.g., 2.5% = 250.0)
- payment_frequency: Frequency
  - period: PeriodEnum - Time period unit (Day, Week, Month, Year)
  - period_multiplier: int - Number of periods (e.g., 3 for 'every 3 months')

Example:
{
  "facility_name": "Term Loan B",
  "commitment_amount": {
    "amount": 5000000,
    "currency": "USD"
  },
  "interest_terms": {
    "rate_option": {
      "benchmark": "SOFR",
      "spread_bps": 275.0
    },
    "payment_frequency": {
      "period": "Month",
      "period_multiplier": 3
    }
  },
  "maturity_date": "2029-12-31"
}"""
    
    docs.append({
        "content": facility_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_model",
            "model_name": "LoanFacility",
        }
    })
    
    # ESG KPI documentation
    esg_doc = """CDM ESG KPI Target Model

For sustainability-linked loans, tracks ESG key performance indicators.

Required Fields:
- kpi_type: ESGKPIType - Type of ESG metric (CO2 Emissions, Renewable Energy Percentage, etc.)
- target_value: float - Target value for the KPI
- unit: str - Unit of measurement (e.g., 'tons CO2', '%', 'incidents')
- margin_adjustment_bps: float - Margin adjustment in basis points if target is met (negative = discount)

Optional Fields:
- current_value: float - Current reported value for the KPI

Common KPI Types:
- CO2 Emissions: Carbon dioxide emissions reduction
- Renewable Energy Percentage: Percentage of energy from renewable sources
- Water Usage: Water consumption reduction
- Waste Reduction: Waste reduction targets
- Diversity Score: Diversity and inclusion metrics
- Safety Incidents: Workplace safety metrics

Example:
{
  "kpi_type": "CO2 Emissions",
  "target_value": 20.0,
  "current_value": 25.0,
  "unit": "tons CO2",
  "margin_adjustment_bps": -10.0
}"""
    
    docs.append({
        "content": esg_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_model",
            "model_name": "ESGKPITarget",
        }
    })
    
    # Field path documentation
    field_paths_doc = """CDM Field Paths Reference

Common field paths for accessing CDM data:

Top-level fields:
- agreement_date: date
- governing_law: str
- deal_id: str
- loan_identification_number: str
- sustainability_linked: bool

Party fields:
- parties: List[Party]
- parties[0].name: First party's name
- parties[0].role: First party's role
- parties[0].lei: First party's LEI
- parties[role='Borrower'].name: Borrower's name (query syntax)

Facility fields:
- facilities: List[LoanFacility]
- facilities[0].facility_name: First facility's name
- facilities[0].commitment_amount.amount: First facility's amount
- facilities[0].commitment_amount.currency: First facility's currency
- facilities[0].maturity_date: First facility's maturity date
- facilities[0].interest_terms.rate_option.benchmark: Interest benchmark
- facilities[0].interest_terms.rate_option.spread_bps: Interest spread in basis points
- facilities[0].interest_terms.payment_frequency.period: Payment period
- facilities[0].interest_terms.payment_frequency.period_multiplier: Payment frequency

ESG fields:
- esg_kpi_targets: List[ESGKPITarget]
- esg_kpi_targets[0].kpi_type: First KPI type
- esg_kpi_targets[0].target_value: First KPI target value

Note: Array indices start at 0. Use dot notation for nested fields."""
    
    docs.append({
        "content": field_paths_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_reference",
            "model_name": "FieldPaths",
        }
    })
    
    # Data types and formats
    data_types_doc = """CDM Data Types and Formats

Date Format:
- All dates must be in ISO 8601 format: YYYY-MM-DD
- Example: "2024-01-15"
- Dates cannot be in the future for agreement_date

Currency:
- Supported currencies: USD, EUR, GBP, JPY
- Use currency codes, not symbols

Monetary Amounts:
- Use Decimal type for precision (not float)
- Example: 1000000.00 (not 1e6)

Interest Rates:
- Spreads must be in basis points (multiply percentage by 100)
- Example: 2.5% = 250.0 basis points
- Valid range: -10000 to 10000 basis points

LEI (Legal Entity Identifier):
- Must be exactly 20 alphanumeric characters
- Example: "12345678901234567890"
- Automatically converted to uppercase

Frequency:
- Period options: Day, Week, Month, Year
- period_multiplier must be positive integer
- Example: {"period": "Month", "period_multiplier": 3} = every 3 months

Extraction Status:
- success: Valid credit agreement extracted
- partial_data_missing: Some fields missing but document is relevant
- irrelevant_document: Not a credit agreement or insufficient information"""
    
    docs.append({
        "content": data_types_doc,
        "metadata": {
            "source": "cdm_schema",
            "content_type": "cdm_reference",
            "model_name": "DataTypes",
        }
    })
    
    return docs


def load_templates_to_kb(chatbot: DecisionSupportChatbot, db) -> int:
    """Load LMA templates from database into knowledge base.
    
    Args:
        chatbot: DecisionSupportChatbot instance
        db: Database session
        
    Returns:
        Number of templates loaded
    """
    try:
        templates = TemplateRegistry.list_templates(db)
        logger.info(f"Found {len(templates)} templates in database")
        
        loaded_count = 0
        for template in templates:
            try:
                template_dict = template.to_dict()
                doc_text = generate_template_documentation(template_dict)
                
                chatbot.add_to_knowledge_base(
                    content=doc_text,
                    metadata={
                        "source": "lma_template",
                        "content_type": "template_metadata",
                        "template_id": template.id,
                        "template_code": template.template_code,
                        "category": template.category,
                    },
                    doc_id=f"template_{template.id}",
                )
                
                loaded_count += 1
                logger.info(f"Loaded template: {template.name} ({template.template_code})")
            except Exception as e:
                logger.error(f"Failed to load template {template.template_code}: {e}")
                continue
        
        return loaded_count
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")
        return 0


def load_cdm_schema_to_kb(chatbot: DecisionSupportChatbot) -> int:
    """Load CDM schema documentation into knowledge base.
    
    Args:
        chatbot: DecisionSupportChatbot instance
        
    Returns:
        Number of schema docs loaded
    """
    try:
        schema_docs = generate_cdm_schema_documentation()
        logger.info(f"Generated {len(schema_docs)} CDM schema documents")
        
        loaded_count = 0
        for doc in schema_docs:
            try:
                chatbot.add_to_knowledge_base(
                    content=doc["content"],
                    metadata=doc["metadata"],
                    doc_id=f"cdm_{doc['metadata']['model_name'].lower()}",
                )
                
                loaded_count += 1
                logger.info(f"Loaded CDM schema: {doc['metadata']['model_name']}")
            except Exception as e:
                logger.error(f"Failed to load CDM schema {doc['metadata']['model_name']}: {e}")
                continue
        
        return loaded_count
    except Exception as e:
        logger.error(f"Failed to load CDM schema: {e}")
        return 0


def main():
    """Main function to set up chatbot knowledge base."""
    logger.info("Starting chatbot knowledge base setup...")
    
    # Initialize database
    try:
        init_db()
        db = SessionLocal()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1
    
    try:
        # Initialize chatbot
        try:
            chatbot = DecisionSupportChatbot()
            logger.info("Chatbot initialized")
        except ImportError as e:
            logger.error(f"ChromaDB not available: {e}")
            logger.error("Install ChromaDB with: pip install chromadb")
            return 1
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {e}")
            return 1
        
        # Load templates
        logger.info("Loading LMA templates into knowledge base...")
        templates_count = load_templates_to_kb(chatbot, db)
        logger.info(f"Loaded {templates_count} templates")
        
        # Load CDM schema
        logger.info("Loading CDM schema documentation into knowledge base...")
        schema_count = load_cdm_schema_to_kb(chatbot)
        logger.info(f"Loaded {schema_count} CDM schema documents")
        
        # Get KB stats
        stats = chatbot.get_kb_stats()
        logger.info(f"Knowledge base statistics: {stats}")
        
        logger.info("Knowledge base setup complete!")
        logger.info(f"Total documents: {stats.get('document_count', 0)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())














