"""LangChain chain for generating signature request configurations."""

import logging
from typing import Optional, List, Dict, Any
from pydantic import ValidationError

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model
from app.models.signature_requests import SignatureRequestGeneration
from app.models.cdm import CreditAgreement

logger = logging.getLogger(__name__)


def create_signature_request_chain() -> BaseChatModel:
    """Create and configure the LangChain signature request generation chain.
    
    Returns:
        A BaseChatModel instance configured with structured output
        bound to the SignatureRequestGeneration Pydantic model.
    """
    llm = get_chat_model(temperature=0)
    structured_llm = llm.with_structured_output(SignatureRequestGeneration)
    return structured_llm


def create_signature_request_prompt() -> ChatPromptTemplate:
    """Create the prompt template for signature request generation.
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    system_prompt = """You are an expert Document Signing Specialist. Your task is to analyze a credit agreement (CDM format) and determine:
1. Who needs to sign the document (signers)
2. Signing order (parallel vs sequential)
3. Appropriate expiration period
4. Reminder schedule

SIGNER IDENTIFICATION RULES:

1. **Required Signers** (always required):
   - Borrower: The primary borrower party (role: "Borrower")
   - Administrative Agent: The administrative agent (role: "Administrative Agent")
   - Lenders: All parties with role "Lender" (if syndicated)

2. **Optional Signers** (if present in agreement):
   - Guarantors: Parties with role "Guarantor"
   - Security Trustee: Party with role "Security Trustee"
   - Facility Agent: Party with role "Facility Agent"

3. **Signing Order**:
   - **Parallel**: All signers can sign simultaneously (default for most agreements)
   - **Sequential**: Signers must sign in order (e.g., Borrower first, then Lenders)
   - Use sequential only if explicitly required by agreement terms

4. **Expiration Period**:
   - Standard agreements: 30 days
   - Time-sensitive deals: 14 days
   - Complex multi-party agreements: 45 days

5. **Reminder Schedule**:
   - Standard: Reminders at 7, 3, and 1 days before expiration
   - Time-sensitive: Reminders at 3 and 1 days before expiration

EXTRACTION RULES:
- Extract signer names from party.name field
- Extract signer emails from party.contact.email (if available) or generate placeholder format based on party name (e.g., "john.doe@example.com" for "John Doe")
- Extract signer roles from party.roles list
- Determine signing order from agreement structure (typically parallel unless specified)
- Set appropriate expiration based on agreement urgency

CRITICAL RULES:
- Only include parties that actually need to sign (Borrower, Lenders, Agents)
- Do not include parties that are not signatories (e.g., observers, advisors)
- Use parallel signing unless agreement explicitly requires sequential
- Set reasonable expiration periods (14-45 days)
- Include all required signers (Borrower, Administrative Agent, at least one Lender)
- Mark all identified signers as required=True
- Generate appropriate email addresses if not available in CDM data"""

    user_prompt = """Credit Agreement (CDM Format):
{cdm_data}

Additional Context:
- Document Type: {document_type}
- Agreement Date: {agreement_date}
- Urgency: {urgency}
- Custom Message (optional): {custom_message}

Analyze this credit agreement and generate a signature request configuration. Identify all required signers, determine signing workflow, and set appropriate expiration and reminders."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def generate_signature_request(
    credit_agreement: CreditAgreement,
    document_type: str = "facility_agreement",
    urgency: str = "standard",
    custom_message: Optional[str] = None,
    max_retries: int = 3
) -> SignatureRequestGeneration:
    """Generate signature request configuration from credit agreement.
    
    Args:
        credit_agreement: CreditAgreement CDM model instance
        document_type: Type of document
        urgency: Urgency level ("standard", "time_sensitive", "complex")
        custom_message: Optional custom message for signers
        max_retries: Maximum retry attempts
        
    Returns:
        SignatureRequestGeneration instance
        
    Raises:
        ValueError: If generation fails after retries
    """
    prompt = create_signature_request_prompt()
    structured_llm = create_signature_request_chain()
    generation_chain = prompt | structured_llm
    
    cdm_data = credit_agreement.model_dump_json(indent=2)
    
    # Determine expiration and reminders based on urgency
    urgency_config = {
        "standard": {"expiration": 30, "reminders": [7, 3, 1]},
        "time_sensitive": {"expiration": 14, "reminders": [3, 1]},
        "complex": {"expiration": 45, "reminders": [14, 7, 3, 1]}
    }
    config = urgency_config.get(urgency, urgency_config["standard"])
    
    last_error: Exception | None = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Signature request generation attempt {attempt + 1}/{max_retries}...")
            
            result = generation_chain.invoke({
                "cdm_data": cdm_data,
                "document_type": document_type,
                "agreement_date": credit_agreement.agreement_date.isoformat() if credit_agreement.agreement_date else "N/A",
                "urgency": urgency,
                "custom_message": custom_message or "N/A"
            })
            
            # Override expiration and reminders based on urgency
            result.expiration_days = config["expiration"]
            result.reminder_days = config["reminders"]
            result.message = custom_message or result.message
            
            logger.info("Signature request generation completed successfully")
            return result
            
        except ValidationError as e:
            last_error = e
            logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info("Retrying with validation feedback...")
                continue
            raise ValueError(f"Signature request generation failed validation after {max_retries} attempts: {e}") from e
            
        except Exception as e:
            logger.error(f"Unexpected error during signature request generation: {e}")
            raise ValueError(f"Signature request generation failed: {e}") from e
