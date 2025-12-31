"""LangChain orchestration for extracting structured data from credit agreements.

This module implements the cognitive layer that uses OpenAI's GPT-4o
with structured outputs to extract FINOS CDM-compliant data from
unstructured legal text.
"""

import logging
from typing import Optional
from pydantic import ValidationError

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.models.cdm import ExtractionResult
from app.chains.map_reduce_chain import extract_data_map_reduce

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Threshold for using map-reduce (approximately 50k characters = ~12k tokens)
MAP_REDUCE_THRESHOLD = 50000


def create_extraction_chain() -> ChatOpenAI:
    """Create and configure the LangChain extraction chain.
    
    Returns:
        A ChatOpenAI instance configured with structured output
        bound to the ExtractionResult Pydantic model.
    """
    # Initialize the LLM with temperature=0 for deterministic extraction
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    
    # Bind the Pydantic model as a structured output tool
    # This ensures the LLM always returns data conforming to ExtractionResult schema
    structured_llm = llm.with_structured_output(ExtractionResult)
    
    return structured_llm


def create_extraction_prompt() -> ChatPromptTemplate:
    """Create the prompt template for credit agreement extraction.
    
    Returns:
        A ChatPromptTemplate with system and user message templates.
    """
    system_prompt = """You are an expert Credit Analyst. Your task is to extract structured data from the provided Credit Agreement text.

Your responsibilities:
1. Extract the exact legal names of parties and their roles (Borrower, Lender, Administrative Agent, etc.)
2. Normalize all financial amounts to the Money structure (amount as string to preserve precision, currency as ISO 4217 code)
3. Convert percentage spreads to basis points (e.g., 3.5% -> 350.0, 2.75% -> 275.0)
4. Extract dates in ISO 8601 format (YYYY-MM-DD)
5. Identify all loan facilities and their terms
6. Extract the governing law/jurisdiction
7. Set extraction_status:
   - success: valid credit agreement extracted
   - partial_data_missing: some fields missing/uncertain
   - irrelevant_document: not a credit agreement or insufficient info

CRITICAL RULES:
- If a field is not explicitly stated in the text, return None/Null. Do not guess or infer values.
- Do not use market standards or assumptions unless explicitly mentioned in the document.
- Convert written numbers (e.g., "five million") to numeric values.
- Ensure all dates are valid and in the correct format.
- For interest rates, always extract the spread in basis points (multiply percentages by 100).
"""

    user_prompt = "Contract Text: {text}"

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
    
    Automatically chooses between simple extraction (for short documents)
    and map-reduce extraction (for long documents) based on document length.
    
    Args:
        text: The raw text content of a credit agreement document.
        force_map_reduce: If True, always use map-reduce strategy.
        max_retries: Maximum number of validation retries for simple extraction.
        
    Returns:
        An ExtractionResult Pydantic model instance containing the extracted data.
    """
    text_length = len(text)
    
    if force_map_reduce or text_length > MAP_REDUCE_THRESHOLD:
        logger.info(f"Document length ({text_length} chars) exceeds threshold, using Map-Reduce strategy")
        return extract_data_map_reduce(text)
    else:
        logger.info(f"Document length ({text_length} chars) within threshold, using simple extraction")
        return extract_data(text, max_retries=max_retries)
