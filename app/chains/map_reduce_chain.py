"""Map-Reduce extraction chain for processing long credit agreement documents.

This module implements the Map-Reduce strategy for handling documents that
exceed token limits. It splits documents by Articles, extracts partial data
from each section, then merges the results into a complete CreditAgreement.
"""

import logging
from typing import List
from pydantic import ValidationError

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.models.cdm import CreditAgreement, ExtractionResult
from app.models.partial_cdm import PartialCreditAgreement
from app.utils.document_splitter import CreditAgreementSplitter, DocumentChunk

logger = logging.getLogger(__name__)


def create_partial_extraction_chain() -> ChatOpenAI:
    """Create a chain for extracting partial data from document sections.
    
    Returns:
        A ChatOpenAI instance configured with structured output
        bound to the PartialCreditAgreement model.
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    
    structured_llm = llm.with_structured_output(PartialCreditAgreement)
    return structured_llm


def create_partial_extraction_prompt() -> ChatPromptTemplate:
    """Create prompt for partial extraction from document sections.
    
    Returns:
        A ChatPromptTemplate optimized for extracting partial data.
    """
    system_prompt = """You are an expert Credit Analyst extracting data from a SECTION of a credit agreement.

This is only ONE SECTION of a larger document. Extract whatever information is present in this section.
Do not worry if some fields are missing - they may be in other sections.

Your task:
1. Extract any parties mentioned (Borrower, Lender, Administrative Agent, etc.)
2. Extract any financial amounts and currencies
3. Extract any interest rate terms (spread in basis points)
4. Extract any dates (agreement date, maturity dates)
5. Extract any loan facilities described
6. Extract governing law if mentioned

CRITICAL RULES:
- Only extract what is EXPLICITLY stated in this section
- Return None/Null for fields not present in this section
- Convert percentages to basis points (2.75% -> 275.0)
- Use ISO 8601 date format (YYYY-MM-DD)
- Do not infer or guess values
"""

    user_prompt = """Document Section:
{text}

Extract all relevant credit agreement data from this section."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def create_reducer_chain() -> ChatOpenAI:
    """Create a reducer chain for merging partial extractions.
    
    Returns:
        A ChatOpenAI instance configured with structured output
        bound to the CreditAgreement model.
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    
    structured_llm = llm.with_structured_output(ExtractionResult)
    return structured_llm


def create_reducer_prompt() -> ChatPromptTemplate:
    """Create prompt for the reducer agent that merges partial extractions.
    
    Returns:
        A ChatPromptTemplate for merging partial data.
    """
    system_prompt = """You are an expert Credit Analyst tasked with MERGING partial extractions from multiple sections of a credit agreement into a single, complete CreditAgreement.

You will receive multiple PartialCreditAgreement objects extracted from different sections (Article I, Article II, etc.).

Your task:
1. Merge all parties, removing duplicates (match by name)
2. Combine all facilities into a single list
3. Select the most authoritative agreement_date (usually from the first article or preamble)
4. Select the governing_law (usually from the last article)
5. Ensure all data is consistent and complete

CRITICAL RULES:
- If the same party appears multiple times, keep only one instance (prefer the most complete)
- If the same facility appears multiple times, merge them (prefer the most complete version)
- If dates conflict, prefer the one from the preamble or Article I
- All required fields must be present in the final CreditAgreement
- Ensure all validations pass (dates not in future, at least one party, at least one facility)
"""

    user_prompt = """Partial Extractions from Document Sections:

{partial_extractions}

Merge these partial extractions into a single, complete CreditAgreement.
Ensure all required fields are present and valid."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    return prompt


def extract_data_map_reduce(text: str) -> ExtractionResult:
    """Extract structured data from a long document using Map-Reduce strategy.
    
    This function:
    1. Splits the document into sections (by Articles)
    2. Extracts partial data from each section (MAP phase)
    3. Merges all partials into a complete CreditAgreement (REDUCE phase)
    
    Args:
        text: The full text content of a credit agreement document.
        
    Returns:
        A complete CreditAgreement Pydantic model instance.
        
    Raises:
        ValueError: If extraction or merging fails.
    """
    try:
        logger.info("Starting Map-Reduce extraction for long document...")
        
        # Step 1: Split document into chunks
        splitter = CreditAgreementSplitter()
        chunks: List[DocumentChunk] = splitter.split_by_articles(text)
        logger.info(f"Document split into {len(chunks)} chunks")
        
        # Step 2: MAP phase - Extract partial data from each chunk
        partial_chain = create_partial_extraction_prompt() | create_partial_extraction_chain()
        partial_extractions: List[PartialCreditAgreement] = []
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {idx + 1}/{len(chunks)}: {chunk.article_title or 'Unknown Section'}")
            
            try:
                # Add source section info
                section_name = f"Article {chunk.article_number}" if chunk.article_number else f"Section {chunk.chunk_index + 1}"
                
                partial = partial_chain.invoke({"text": chunk.text})
                partial.source_section = section_name
                partial_extractions.append(partial)
                
                logger.debug(f"Extracted from {section_name}: parties={len(partial.parties) if partial.parties else 0}, "
                           f"facilities={len(partial.facilities) if partial.facilities else 0}")
            except Exception as e:
                logger.warning(f"Failed to extract from chunk {idx + 1}: {e}")
                # Continue with other chunks even if one fails
                continue
        
        if not partial_extractions:
            raise ValueError("No partial extractions were successful")
        
        logger.info(f"MAP phase complete: {len(partial_extractions)} partial extractions")
        
        # Step 3: REDUCE phase - Merge partial extractions
        logger.info("Starting REDUCE phase: merging partial extractions...")
        
        # Format partial extractions as JSON for the reducer
        partial_extractions_json = "\n\n---\n\n".join([
            f"Section: {p.source_section}\n{p.model_dump_json(indent=2)}"
            for p in partial_extractions
        ])
        
        reducer_chain = create_reducer_prompt() | create_reducer_chain()
        result = reducer_chain.invoke({"partial_extractions": partial_extractions_json})
        
        logger.info("REDUCE phase complete: merged into complete CreditAgreement")
        logger.info(f"Final result: {len(result.parties)} parties, {len(result.facilities)} facilities")
        
        return result
        
    except ValidationError as e:
        logger.error(f"Validation error during map-reduce extraction: {e}")
        raise ValueError(f"Extracted data failed validation: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during map-reduce extraction: {e}")
        raise ValueError(f"Map-reduce extraction failed: {e}") from e

