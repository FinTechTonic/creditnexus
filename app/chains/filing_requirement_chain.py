"""LangChain chain for evaluating filing requirements from CDM data."""

import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model
from app.models.filing_requirements import FilingRequirementEvaluation
from app.models.cdm import CreditAgreement

logger = logging.getLogger(__name__)


def create_filing_requirement_chain() -> BaseChatModel:
    """Create and configure the LangChain filing requirement evaluation chain.
    
    Uses the LLM client abstraction to support multiple providers.
    Temperature set to 0 for deterministic evaluation.
    
    Returns:
        A BaseChatModel instance configured with structured output
        bound to the FilingRequirementEvaluation Pydantic model.
    """
    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(FilingRequirementEvaluation)
    return structured_llm


def create_filing_requirement_prompt() -> ChatPromptTemplate:
    """Create the prompt template for filing requirement evaluation.
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    system_prompt = """You are an expert Regulatory Compliance Analyst specializing in credit agreement filing requirements across multiple jurisdictions.

Your task is to analyze a Credit Agreement (CDM format) and determine:
1. Which regulatory filings are required based on jurisdiction, agreement type, and deal characteristics
2. Filing deadlines and priority levels
3. Required fields for each filing
4. Whether API filing is available or manual filing is required
5. Compliance status and missing information

JURISDICTIONS YOU MUST EVALUATE:
- **US (United States)**: SEC EDGAR filings (8-K, 10-Q, 10-K), state-level filings
- **UK (United Kingdom)**: Companies House filings (MR01 charges, annual returns)
- **FR (France)**: AMF filings, Commercial Court registrations
- **DE (Germany)**: BaFin filings, Commercial Register entries

AGREEMENT TYPES:
- facility_agreement: Credit facility agreements
- disclosure: Regulatory disclosures
- security_agreement: Security/charge registrations
- intercreditor: Intercreditor agreements
- term_sheet: Term sheet filings (if required)

FILING REQUIREMENT DETERMINATION RULES:

1. **US SEC Filings**:
   - 8-K required for material credit agreements (typically >$100M or >10% of assets)
   - Deadline: 4 business days after agreement execution
   - Required fields: Company name, CIK, agreement date, total commitment, parties
   - Filing system: manual_ui (no direct API)
   - Form type: "8-K"

2. **UK Companies House**:
   - MR01 required for charges/security interests
   - Deadline: 21 days after charge creation
   - Required fields: Company number, charge creation date, persons entitled, property charged, amount secured
   - Filing system: companies_house_api (API available)
   - Form type: "MR01"

3. **France AMF/Court**:
   - Required for material credit agreements (typically >€150M)
   - Deadline: Varies by agreement type (typically 15-30 days)
   - Required fields: Company name, SIREN, agreement date, total commitment
   - Filing system: manual_ui
   - Language requirement: French
   - Form type: "Declaration de prêt"

4. **Germany BaFin/Register**:
   - Required for material credit agreements (typically >€150M)
   - Deadline: Varies by agreement type (typically 15-30 days)
   - Required fields: Company name, HRB number, agreement date, total commitment
   - Filing system: manual_ui
   - Language requirement: German
   - Form type: "Kreditvertrag Anmeldung"

PRIORITY LEVELS:
- **critical**: Deadline within 7 days
- **high**: Deadline within 30 days
- **medium**: Deadline within 90 days
- **low**: Deadline beyond 90 days

COMPLIANCE STATUS:
- **compliant**: All required filings identified and all required fields present
- **non_compliant**: Required filings identified but required fields missing
- **pending**: Filings identified but not yet submitted

CRITICAL RULES:
- Only identify filings that are ACTUALLY REQUIRED by law/regulation
- Consider agreement amount thresholds (materiality)
- Consider jurisdiction of borrower and lenders
- Extract exact deadlines from regulatory rules
- Identify missing required fields accurately
- Set appropriate priority based on deadline proximity
- Return empty list if no filings required (don't guess)"""

    user_prompt = """Credit Agreement (CDM Format):
{cdm_data}

Additional Context:
- Document ID: {document_id}
- Deal ID: {deal_id}
- Agreement Type: {agreement_type}
- Current Date: {current_date}

Evaluate filing requirements for this credit agreement. Identify all required filings, deadlines, and missing information."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def evaluate_filing_requirements(
    credit_agreement: CreditAgreement,
    document_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    agreement_type: str = "facility_agreement",
    max_retries: int = 3
) -> FilingRequirementEvaluation:
    """Evaluate filing requirements for a credit agreement.
    
    Args:
        credit_agreement: CreditAgreement CDM model instance
        document_id: Optional document ID
        deal_id: Optional deal ID
        agreement_type: Type of agreement
        max_retries: Maximum retry attempts
        
    Returns:
        FilingRequirementEvaluation instance
        
    Raises:
        ValueError: If evaluation fails after retries
    """
    prompt = create_filing_requirement_prompt()
    structured_llm = create_filing_requirement_chain()
    evaluation_chain = prompt | structured_llm
    
    from datetime import datetime
    
    # Convert CreditAgreement to dict for prompt
    cdm_data = credit_agreement.model_dump_json(indent=2)
    
    last_error: Exception | None = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Filing requirement evaluation attempt {attempt + 1}/{max_retries}...")
            
            result = evaluation_chain.invoke({
                "cdm_data": cdm_data,
                "document_id": str(document_id) if document_id else "N/A",
                "deal_id": str(deal_id) if deal_id else "N/A",
                "agreement_type": agreement_type,
                "current_date": datetime.utcnow().isoformat()
            })
            
            logger.info("Filing requirement evaluation completed successfully")
            return result
            
        except ValidationError as e:
            last_error = e
            logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info("Retrying with validation feedback...")
                continue
            raise ValueError(f"Filing requirement evaluation failed validation after {max_retries} attempts: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error during filing requirement evaluation: {e}")
            raise ValueError(f"Filing requirement evaluation failed: {e}") from e
