"""LangChain orchestration for extracting structured user profile data from documents.

This module implements profile extraction using LLMs with structured outputs
to extract user profile information from business cards, resumes, company documents, etc.
"""

import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm_client import get_chat_model
from app.models.user_profile import UserProfileData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_profile_extraction_chain(role: Optional[str] = None) -> BaseChatModel:
    """Create and configure the LangChain profile extraction chain.
    
    Uses the LLM client abstraction to support multiple providers (OpenAI, vLLM, HuggingFace).
    The provider and model are configured via environment variables (LLM_PROVIDER, LLM_MODEL).
    
    Args:
        role: Optional user role to guide extraction (applicant, banker, law_officer, accountant, etc.)
    
    Returns:
        A BaseChatModel instance configured with structured output
        bound to the UserProfileData Pydantic model.
    """
    # Use global LLM configuration (set at startup)
    # Temperature defaults to 0 for deterministic extraction
    llm = get_chat_model(temperature=0)
    
    # Bind the Pydantic model as a structured output tool
    # This ensures the LLM always returns data conforming to UserProfileData schema
    structured_llm = llm.with_structured_output(UserProfileData)
    
    return structured_llm


def create_profile_extraction_prompt(role: Optional[str] = None) -> ChatPromptTemplate:
    """Create the prompt template for user profile extraction.
    
    This prompt is designed to extract structured profile information from various document types:
    - Business cards
    - Resumes/CVs
    - Company documents
    - Professional licenses
    - ID documents
    - Email signatures
    - LinkedIn profiles (if extracted from documents)
    
    Args:
        role: Optional user role to provide role-specific extraction guidance
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    # Role-specific guidance
    role_guidance = ""
    if role:
        role_guidance = f"""
ROLE-SPECIFIC EXTRACTION GUIDANCE:
You are extracting profile data for a user with role: {role}

"""
        if role.lower() in ["applicant", "borrower"]:
            role_guidance += """
For APPLICANT role, prioritize:
- Company information (name, registration, LEI, industry)
- Financial information (revenue, AUM, credit rating)
- Contact information (business email, phone, address)
- Professional information (job title, department, years of experience)
"""
        elif role.lower() in ["banker", "lender"]:
            role_guidance += """
For BANKER role, prioritize:
- Company information (bank name, registration, LEI)
- Professional information (job title, department, certifications, licenses)
- Contact information (business email, phone, office address)
- Specializations (areas of expertise, product knowledge)
"""
        elif role.lower() in ["law_officer", "lawyer", "attorney"]:
            role_guidance += """
For LAW OFFICER role, prioritize:
- Professional information (bar admission, licenses, certifications)
- Company information (law firm name, registration)
- Specializations (practice areas, jurisdictions)
- Contact information (business email, phone, office address)
"""
        elif role.lower() in ["accountant", "auditor"]:
            role_guidance += """
For ACCOUNTANT role, prioritize:
- Professional information (CPA, certifications, licenses)
- Company information (accounting firm name, registration)
- Specializations (audit, tax, advisory)
- Contact information (business email, phone, office address)
"""
    
    system_prompt = f"""You are an expert Data Extraction Specialist. Your task is to extract structured user profile information from the provided document text.

{role_guidance}
CORE EXTRACTION RESPONSIBILITIES:

1. PERSONAL INFORMATION:
   - Extract full name, first name, last name, middle name/initial
   - Extract date of birth if available (format as YYYY-MM-DD)
   - Extract nationality if mentioned

2. CONTACT INFORMATION:
   - Extract phone numbers (office, mobile, fax)
   - Extract email addresses (validate format)
   - Extract physical addresses (street, city, state, postal code, country)
   - Extract LinkedIn profile URLs
   - Extract personal or company websites

3. PROFESSIONAL INFORMATION:
   - Extract job title or position
   - Extract department or division
   - Extract years of experience (if mentioned)
   - Extract professional certifications (CPA, CFA, Bar admission, etc.)
   - Extract professional licenses (license numbers, issuing authorities)
   - Extract specializations or areas of expertise

4. COMPANY/ORGANIZATION INFORMATION:
   - Extract company name and legal entity name
   - Extract company registration number
   - Extract tax identification number (TIN, EIN, etc.)
   - Extract Legal Entity Identifier (LEI) if available
   - Extract industry sector
   - Extract company website
   - Extract company address

5. FINANCIAL INFORMATION (if applicable):
   - Extract annual revenue (with currency)
   - Extract assets under management (AUM) with currency
   - Extract credit rating and rating agency

6. ROLE-SPECIFIC DATA:
   - Extract any additional information relevant to the user's role
   - Store in role_specific_data field as key-value pairs

DOCUMENT TYPES YOU MAY ENCOUNTER:
- Business cards (name, title, company, contact info)
- Resumes/CVs (full professional history, education, certifications)
- Company letterheads (company info, address, contact)
- Professional licenses (license numbers, issuing authorities, expiration dates)
- ID documents (name, date of birth, nationality, address)
- Email signatures (name, title, company, contact info)
- LinkedIn profile exports (comprehensive professional information)
- Company documents (registration, tax ID, LEI, financial info)

TEXT QUALITY CONSIDERATIONS:
- OCR errors: Intelligently correct common OCR mistakes (e.g., "0" vs "O", "1" vs "I")
- Handwritten text: Extract what is legible, mark uncertain fields appropriately
- Poor quality scans: Extract what is readable
- Multiple languages: Extract data regardless of language
- Incomplete information: Extract what is available, leave missing fields as None

CRITICAL RULES:
- If a field is not explicitly stated in the text, return None/Null. Do not guess or infer values.
- Do not make assumptions about missing information.
- Extract dates in ISO 8601 format (YYYY-MM-DD).
- Normalize phone numbers to a consistent format if possible.
- Validate email addresses (must be valid email format).
- For addresses, extract as much detail as available (street, city, state, postal code, country).
- If full address is available as a single string, populate full_address field.
- For financial amounts, include currency code.
- For certifications/licenses, extract as lists if multiple are mentioned.
- Preserve original text structure when possible for audit purposes.
- If text appears corrupted or unreadable, mark appropriate fields as missing rather than guessing.

MERGING WITH EXISTING PROFILE:
- If existing_profile is provided, use it as a base and only override/extend with new information from the document.
- Prefer more complete information over partial information.
- Merge nested objects (contact, address, company, etc.) intelligently.
"""

    user_prompt = """Extract user profile information from the following document text:

Document Text:
{text}

Existing Profile Data (if any):
{existing_profile}

User Role: {role}

Extract all available profile information and return it in the structured format."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def extract_profile_data(
    text: str,
    role: Optional[str] = None,
    existing_profile: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> UserProfileData:
    """Extract structured user profile data from unstructured text.
    
    Implements the "Reflexion" retry pattern: if validation fails, the error
    is fed back to the LLM for correction, allowing it to fix its own mistakes.
    
    Args:
        text: The raw text content extracted from a document.
        role: Optional user role to guide extraction.
        existing_profile: Optional existing profile data to merge with (as dict).
        max_retries: Maximum number of validation retries (default: 3).
        
    Returns:
        A UserProfileData Pydantic model instance containing the extracted data.
        
    Raises:
        ValueError: If extraction fails after retries or other errors occur.
    """
    prompt = create_profile_extraction_prompt(role=role)
    structured_llm = create_profile_extraction_chain(role=role)
    extraction_chain = prompt | structured_llm

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Profile extraction attempt {attempt + 1}/{max_retries}...")

            if attempt == 0:
                # First attempt: normal extraction
                result = extraction_chain.invoke({
                    "text": text,
                    "existing_profile": existing_profile or {},
                    "role": role or "unknown"
                })
            else:
                # Retry attempts: include validation error feedback
                error_feedback = f"""
Previous extraction attempt failed with validation error:
{str(last_error)}

Please correct the following issues:
1. Review the validation error above
2. Ensure all dates are valid and in ISO 8601 format (YYYY-MM-DD)
3. Ensure email addresses are valid email format
4. Ensure all nested objects (contact, address, company, etc.) are properly structured
5. Do not include fields that are not explicitly mentioned in the text

Original Document Text:
{text}

Existing Profile Data:
{existing_profile or {}}
"""
                result = extraction_chain.invoke({
                    "text": error_feedback,
                    "existing_profile": existing_profile or {},
                    "role": role or "unknown"
                })

            logger.info("Profile extraction completed successfully")
            return result

        except ValidationError as e:
            last_error = e
            logger.warning(f"Validation error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                logger.info("Retrying with validation feedback...")
                continue
            raise ValueError(f"Extracted profile data failed validation after {max_retries} attempts: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during profile extraction: {e}")
            raise ValueError(f"Profile extraction failed: {e}") from e
