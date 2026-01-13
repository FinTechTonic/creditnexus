"""LangChain orchestration for extracting structured data from credit agreements.

This module implements the cognitive layer that uses OpenAI's GPT-4o
with structured outputs to extract FINOS CDM-compliant data from
unstructured legal text.
"""

import logging
from typing import Optional
from pydantic import ValidationError

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model
from app.models.cdm import CreditAgreement, ExtractionResult
from app.chains.map_reduce_chain import extract_data_map_reduce

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Threshold for using map-reduce (approximately 50k characters = ~12k tokens)
MAP_REDUCE_THRESHOLD = 50000
# Threshold for using agentic pipeline (for very large documents >100k chars)
AGENTIC_PIPELINE_THRESHOLD = 100000


def create_extraction_chain() -> BaseChatModel:
    """Create and configure the LangChain extraction chain.
    
    Uses the LLM client abstraction to support multiple providers (OpenAI, vLLM, HuggingFace).
    The provider and model are configured via environment variables (LLM_PROVIDER, LLM_MODEL).
    
    Returns:
        A BaseChatModel instance configured with structured output
        bound to the CreditAgreement Pydantic model.
    """
    # Use global LLM configuration (set at startup)
    # Temperature defaults to 0 for deterministic extraction
    llm = get_chat_model(temperature=0)
    
    # Bind the Pydantic model as a structured output tool
    # This ensures the LLM always returns data conforming to ExtractionResult schema
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    return structured_llm


def create_extraction_prompt() -> ChatPromptTemplate:
    """Create the prompt template for credit agreement extraction.
    
    This prompt is designed to extract ALL fields needed for diverse document templates including:
    - Standard facility agreements
    - Sustainable finance documents
    - Regulatory compliance documents
    - Security and intercreditor agreements
    - Origination documents
    - Secondary trading documents
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    system_prompt = """You are an expert Credit Analyst and Financial Document Specialist. Your task is to extract comprehensive structured data from the provided Credit Agreement or financial document text.

CORE EXTRACTION RESPONSIBILITIES:
1. PARTIES AND ENTITIES:
   - Extract exact legal names of all parties and their roles (Borrower, Lender, Administrative Agent, Guarantor, Security Trustee, etc.)
   - Extract LEI (Legal Entity Identifier) for parties when available
   - Extract party addresses, jurisdictions, and registration numbers
   - Identify beneficial owners if mentioned

2. FINANCIAL TERMS:
   - Normalize all financial amounts to the Money structure (amount as Decimal, currency as code)
   - Convert percentage spreads to basis points (e.g., 3.5% -> 350.0, 2.75% -> 275.0)
   - Extract all loan facilities and their terms:
     * Facility name and type
     * Commitment amount and currency
     * Maturity date
     * Interest rate terms (benchmark, spread in basis points, payment frequency)
     * Drawdown conditions and availability periods
   - Extract payment frequency with both period (Day/Week/Month/Year) and period_multiplier (e.g., 3 for quarterly)

3. DATES AND TIMELINES:
   - Extract dates in ISO 8601 format (YYYY-MM-DD)
   - Agreement date, effective date, maturity dates
   - Payment dates, review dates, reporting dates

4. LEGAL AND REGULATORY:
   - Extract governing law/jurisdiction
   - Extract dispute resolution mechanisms (arbitration, courts, etc.)
   - Extract regulatory compliance statements

5. SUSTAINABLE FINANCE (if applicable):
   - ESG KPI targets and performance metrics
   - Sustainability-linked loan provisions
   - Green loan framework certifications
   - Margin adjustment mechanisms based on sustainability performance
   - Reporting obligations for sustainability metrics

6. REGULATORY COMPLIANCE (if applicable):
   - FATF compliance statements
   - Customer Due Diligence (CDD) obligations
   - Suspicious Transaction Reporting (STR) requirements
   - Sanctions compliance provisions
   - Capital adequacy certifications
   - Risk weighting disclosures
   - Regulatory capital requirements
   - AML (Anti-Money Laundering) certifications

7. SECURITY AND INTERCREDITOR (if applicable):
   - Priority provisions and subordination arrangements
   - Voting mechanisms and decision-making processes
   - Standstill provisions
   - Enforcement restrictions
   - Collateral obligations and security arrangements

8. ORIGINATION DOCUMENTS (if applicable):
   - Source of funds declarations
   - Ongoing compliance obligations
   - KYC (Know Your Customer) requirements
   - Application status and approval conditions

9. SECONDARY TRADING (if applicable):
   - Transfer provisions and assignment restrictions
   - Margin calculation methodologies
   - Dispute resolution mechanisms
   - Trading restrictions and conditions

10. CRYPTO AND DIGITAL ASSETS (if applicable):
    - Digital asset types and amounts
    - Blockchain network information
    - Wallet addresses and custody arrangements
    - Regulatory classifications

11. EXTRACTION STATUS:
    - success: valid credit/financial agreement extracted with sufficient data
    - partial_data_missing: some fields missing/uncertain but document is relevant
    - irrelevant_document: not a credit/financial agreement or insufficient information

CRITICAL RULES:
- If a field is not explicitly stated in the text, return None/Null. Do not guess or infer values.
- Do not use market standards or assumptions unless explicitly mentioned in the document.
- Convert written numbers (e.g., "five million", "3.5 million") to numeric values.
- Ensure all dates are valid and in the correct format (YYYY-MM-DD).
- For interest rates, always extract the spread in basis points (multiply percentages by 100).
- For payment frequency, extract both period (e.g., "Month") and period_multiplier (e.g., 3 for "every 3 months").
- Always extract spread_bps (spread in basis points) and period_multiplier for payment frequency.
- Extract ALL fields mentioned in the document, even if they seem unusual or template-specific.
- Pay attention to regulatory, compliance, and specialized provisions that may be required for specific document types.
"""

    user_prompt = "Contract Text: {text}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def create_comprehensive_extraction_prompt() -> ChatPromptTemplate:
    """Create a comprehensive prompt template that works for any financial/legal document.
    
    This prompt is designed to extract CDM data from various sources including:
    - Scanned documents (PDFs, images)
    - Webcam photos of documents
    - Regular photos of contracts
    - Schemas and diagrams
    - Accounting documents
    - Credit agreements in any format
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    system_prompt = """You are an expert Financial Data Analyst specializing in extracting structured information from financial and legal documents. Your task is to extract structured CDM (Common Domain Model) compliant data from any provided text, regardless of its source.

DOCUMENT SOURCES YOU MAY ENCOUNTER:
- Scanned credit agreements, loan documents, or term sheets
- Photos taken with webcam or mobile device of contracts
- Handwritten or printed financial documents
- Accounting records, invoices, or financial statements
- Legal schemas, diagrams, or structured layouts
- OCR-extracted text from images of any quality

YOUR RESPONSIBILITIES:
1. Extract the exact legal names of parties and their roles (Borrower, Lender, Administrative Agent, Guarantor, etc.)
2. Normalize all financial amounts to the Money structure (amount as Decimal, currency as code)
3. Convert percentage spreads to basis points (e.g., 3.5% -> 350.0, 2.75% -> 275.0)
4. Extract dates in ISO 8601 format (YYYY-MM-DD) - handle various date formats intelligently
5. Identify all loan facilities, credit lines, or financial instruments and their terms
6. Extract the governing law/jurisdiction
7. Identify sustainability-linked provisions, ESG KPIs, or environmental targets if present
8. Extract interest rates, spreads, benchmarks (SOFR, LIBOR, etc.), and payment frequencies
9. Set extraction_status appropriately:
   - success: valid credit/financial agreement extracted with sufficient data
   - partial_data_missing: some fields missing/uncertain but document is relevant
   - irrelevant_document: not a credit/financial agreement or insufficient information

HANDLING VARIOUS DOCUMENT TYPES:
- For credit agreements: Extract parties, facilities, terms, dates, governing law
- For term sheets: Extract key terms, amounts, parties, dates
- For accounting documents: Extract financial amounts, dates, parties, transaction details
- For schemas/diagrams: Extract structured relationships, parties, financial flows
- For partial documents: Extract what is available, mark as partial_data_missing

TEXT QUALITY CONSIDERATIONS:
- OCR errors: Intelligently correct common OCR mistakes (e.g., "0" vs "O", "1" vs "I")
- Handwritten text: Extract what is legible, mark uncertain fields appropriately
- Poor quality scans: Extract what is readable, use partial_data_missing status
- Multiple languages: Extract data regardless of language, preserve original text structure

CRITICAL RULES:
- If a field is not explicitly stated in the text, return None/Null. Do not guess or infer values.
- Do not use market standards or assumptions unless explicitly mentioned in the document.
- Convert written numbers (e.g., "five million", "3.5 million") to numeric values.
- Ensure all dates are valid and in ISO 8601 format (YYYY-MM-DD).
- For interest rates, always extract the spread in basis points (multiply percentages by 100).
- Handle currency symbols and codes intelligently (USD, $, EUR, €, GBP, £, etc.).
- Preserve original text structure when possible for audit purposes.
- If text appears corrupted or unreadable, mark appropriate fields as missing rather than guessing.
"""

    user_prompt = "Extracted Text (from image, scan, photo, or document): {text}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def extract_data(text: str, max_retries: int = 3) -> ExtractionResult:
    """Extract structured credit agreement data from unstructured text.
    
    Implements the "Reflexion" retry pattern: if validation fails, the error
    is fed back to the LLM for correction, allowing it to fix its own mistakes.
    
    Args:
        text: The raw text content of a credit agreement document.
        max_retries: Maximum number of validation retries (default: 3).
        
    Returns:
        An ExtractionResult Pydantic model instance containing the extracted data.
        
    Raises:
        ValueError: If extraction fails after retries or other errors occur.
    """
    prompt = create_extraction_prompt()
    structured_llm = create_extraction_chain()
    extraction_chain = prompt | structured_llm

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Extraction attempt {attempt + 1}/{max_retries}...")

            if attempt == 0:
                # First attempt: normal extraction
                result = extraction_chain.invoke({"text": text})
            else:
                # Retry attempts: include validation error feedback
                error_feedback = f"""
Previous extraction attempt failed with validation error:
{str(last_error)}

Please correct the following issues:
1. Review the validation error above
2. Ensure all dates are valid and in ISO 8601 format (YYYY-MM-DD)
3. Ensure each facility maturity_date is after agreement_date
4. Ensure all facilities use the same currency
5. Ensure at least one party has role 'Borrower'
6. Convert percentage spreads to basis points (multiply by 100)

Original Contract Text:
{text}
"""
                result = extraction_chain.invoke({"text": error_feedback})

            logger.info("Extraction completed successfully")
            return result

        except ValidationError as e:
            last_error = e
            logger.warning(f"Validation error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                logger.info("Retrying with validation feedback...")
                continue
            raise ValueError(f"Extracted data failed validation after {max_retries} attempts: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}")
            raise ValueError(f"Extraction failed: {e}") from e


def extract_data_smart(text: str, force_map_reduce: bool = False, max_retries: int = 3) -> ExtractionResult:
    """Extract structured data with automatic strategy selection.
    
    Automatically chooses between:
    - Simple extraction (for short documents <50k chars)
    - Map-reduce extraction (for medium documents 50k-100k chars)
    - Agentic pipeline (for very large documents >100k chars)
    
    Args:
        text: The raw text content of a credit agreement document.
        force_map_reduce: If True, always use map-reduce strategy (overrides agentic pipeline).
        max_retries: Maximum number of validation retries for simple extraction.
        
    Returns:
        An ExtractionResult Pydantic model instance containing the extracted data.
    """
    text_length = len(text)
    
    # For very large documents (>100k chars), use agentic pipeline
    if not force_map_reduce and text_length > AGENTIC_PIPELINE_THRESHOLD:
        logger.info(f"Document length ({text_length} chars) exceeds agentic threshold, using Agentic Pipeline strategy")
        from app.chains.agentic_pipeline import extract_with_agentic_pipeline
        
        try:
            result = extract_with_agentic_pipeline(text)
            
            # Convert agentic pipeline result to ExtractionResult
            if result.get("status") == "error" or not result.get("agreement"):
                # Fallback to map-reduce if agentic pipeline fails
                logger.warning("Agentic pipeline failed, falling back to map-reduce")
                return extract_data_map_reduce(text)
            
            # Extract agreement data from agentic pipeline result
            agreement_dict = result.get("agreement", {})
            
            # Convert to CreditAgreement and wrap in ExtractionResult
            # Note: This is a simplified conversion - the agentic pipeline's
            # ExtractedAgreement format may need mapping to CreditAgreement
            try:
                agreement = CreditAgreement.model_validate(agreement_dict)
                return ExtractionResult(agreement=agreement)
            except ValidationError as e:
                logger.warning(f"Failed to validate agentic pipeline result as CreditAgreement: {e}")
                # Fallback to map-reduce
                return extract_data_map_reduce(text)
                
        except Exception as e:
            logger.error(f"Agentic pipeline error: {e}, falling back to map-reduce")
            return extract_data_map_reduce(text)
    
    elif force_map_reduce or text_length > MAP_REDUCE_THRESHOLD:
        logger.info(f"Document length ({text_length} chars) exceeds threshold, using Map-Reduce strategy")
        return extract_data_map_reduce(text)
    else:
        logger.info(f"Document length ({text_length} chars) within threshold, using simple extraction")
        return extract_data(text, max_retries=max_retries)

