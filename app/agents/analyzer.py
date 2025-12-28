"""Legal Ingestion Agent for Ground Truth Protocol.

This agent uses OpenAI function calling to extract:
1. Sustainability Performance Targets (SPTs) from loan covenants
2. Collateral addresses for geospatial verification
3. Text embeddings for semantic search
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from app.core.config import settings
from app.models.spt_schema import (
    SustainabilityPerformanceTarget,
    CollateralAddress,
    LegalExtractionResult,
    ResourceTarget,
    FinancialConsequence,
    ComparisonDirection,
    PenaltyType,
    TriggerMechanism,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_spt_extraction_chain() -> ChatOpenAI:
    """
    Create LLM configured for SPT extraction with structured output.
    
    Returns:
        ChatOpenAI instance bound to SustainabilityPerformanceTarget schema
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    return llm.with_structured_output(SustainabilityPerformanceTarget)


def create_address_extraction_chain() -> ChatOpenAI:
    """
    Create LLM configured for collateral address extraction.
    
    Returns:
        ChatOpenAI instance bound to CollateralAddress schema
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )
    return llm.with_structured_output(CollateralAddress)


def get_embeddings_model() -> OpenAIEmbeddings:
    """Get OpenAI embeddings model for vector generation."""
    return OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
        model="text-embedding-3-small"
    )


SPT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Credit Analyst specializing in Sustainability-Linked Loans.
Your task is to extract Sustainability Performance Targets (SPTs) from loan agreement text.

Focus on:
1. The specific environmental/sustainability METRIC being tracked (e.g., forest cover, vegetation index, emissions)
2. The THRESHOLD value (e.g., "80%", ">= 0.7")
3. The comparison DIRECTION (greater than, less than, equal to)
4. The FINANCIAL PENALTY for non-compliance (margin increase in basis points)
5. How the penalty is TRIGGERED (automatic, lender discretion, etc.)

IMPORTANT:
- Extract ONLY information explicitly stated in the text
- Convert percentages to decimal thresholds (e.g., "80%" -> 0.8)
- Convert percentage margin adjustments to basis points (e.g., "0.50%" -> 50)
- If vegetation/forest metrics are mentioned, use "NDVI Index" or "Forest Cover" as appropriate
"""),
    ("user", "Extract the Sustainability Performance Target from this loan covenant text:\n\n{text}")
])


ADDRESS_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at extracting property addresses from legal documents.
Your task is to find and extract the COLLATERAL ADDRESS - the physical location of the asset securing the loan.

Look for phrases like:
- "located at"
- "property situated at" 
- "collateral property address"
- "secured by real property at"
- "physical address of the asset"

Extract the full address and break it into components (street, city, state, postal code, country).
If the country is not specified, assume USA.
Always provide the full_address field with the complete address string."""),
    ("user", "Extract the collateral property address from this legal text:\n\n{text}")
])


async def extract_spt_from_text(text: str, max_retries: int = 2) -> Optional[SustainabilityPerformanceTarget]:
    """
    Extract Sustainability Performance Target from loan covenant text.
    
    Args:
        text: Raw text from loan agreement covenant section
        max_retries: Number of retry attempts on validation failure
        
    Returns:
        SustainabilityPerformanceTarget if found, None otherwise
    """
    structured_llm = create_spt_extraction_chain()
    chain = SPT_EXTRACTION_PROMPT | structured_llm
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"SPT extraction attempt {attempt + 1}/{max_retries + 1}")
            result = await chain.ainvoke({"text": text})
            logger.info(f"Successfully extracted SPT: {result.resource_target.metric}")
            return result
        except ValidationError as e:
            logger.warning(f"SPT validation error on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                logger.error("SPT extraction failed after all retries")
                return None
        except Exception as e:
            logger.error(f"SPT extraction error: {e}")
            return None
    
    return None


async def extract_collateral_address(text: str, max_retries: int = 2) -> Optional[CollateralAddress]:
    """
    Extract collateral property address from legal text using LLM.
    
    Args:
        text: Raw legal document text
        max_retries: Number of retry attempts on validation failure
        
    Returns:
        CollateralAddress if found, None otherwise
    """
    structured_llm = create_address_extraction_chain()
    chain = ADDRESS_EXTRACTION_PROMPT | structured_llm
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Address extraction attempt {attempt + 1}/{max_retries + 1}")
            result = await chain.ainvoke({"text": text})
            logger.info(f"Successfully extracted address: {result.full_address}")
            return result
        except ValidationError as e:
            logger.warning(f"Address validation error on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                logger.error("Address extraction failed after all retries")
                return None
        except Exception as e:
            logger.error(f"Address extraction error: {e}")
            return None
    
    return None


async def generate_legal_vector(text: str) -> Optional[list[float]]:
    """
    Generate OpenAI embedding vector for legal text.
    
    Args:
        text: Legal document text to embed
        
    Returns:
        1536-dimensional embedding vector, or None on error
    """
    try:
        embeddings = get_embeddings_model()
        vector = await embeddings.aembed_query(text)
        logger.info(f"Generated legal vector with {len(vector)} dimensions")
        return vector
    except Exception as e:
        logger.error(f"Legal vector generation failed: {e}")
        return None


async def analyze_legal_document(text: str) -> LegalExtractionResult:
    """
    Complete legal document analysis combining SPT and address extraction.
    
    This is the main entry point for the Legal Ingestion Agent.
    
    Args:
        text: Full text of the loan agreement or covenant section
        
    Returns:
        LegalExtractionResult with extracted SPT, address, and confidence
    """
    logger.info("Starting legal document analysis...")
    
    # Extract SPT and address concurrently
    spt = await extract_spt_from_text(text)
    address = await extract_collateral_address(text)
    
    # Calculate confidence based on extraction success
    confidence = 0.0
    if spt is not None:
        confidence += 0.5
    if address is not None:
        confidence += 0.5
    
    result = LegalExtractionResult(
        spt=spt,
        collateral_address=address,
        confidence_score=confidence,
        raw_covenant_text=text[:1000] if len(text) > 1000 else text  # Store first 1000 chars
    )
    
    logger.info(f"Legal analysis complete. Confidence: {confidence}")
    return result


# Demo/test function with sample covenant text
SAMPLE_COVENANT_TEXT = """
SUSTAINABILITY COVENANT

The Borrower hereby covenants that the Forest Cover Ratio on the Collateral Property 
located at 2847 Timber Ridge Road, Paradise, CA 95969, shall be maintained at or above 
Eighty Percent (80%) as measured by the Normalized Difference Vegetation Index (NDVI) 
calculated from satellite imagery.

In the event that the Forest Cover Ratio falls below the required threshold, the 
applicable Margin shall automatically increase by Fifty (50) basis points for the 
duration of such non-compliance.

Verification shall occur annually using independent satellite data analysis.
"""


async def demo_extraction():
    """Demo function to test extraction pipeline."""
    result = await analyze_legal_document(SAMPLE_COVENANT_TEXT)
    print("=" * 60)
    print("Legal Extraction Result:")
    print("=" * 60)
    if result.spt:
        print(f"Metric: {result.spt.resource_target.metric}")
        print(f"Threshold: {result.spt.resource_target.threshold}")
        print(f"Direction: {result.spt.resource_target.direction}")
        print(f"Penalty: {result.spt.financial_consequence.penalty_bps} bps")
    if result.collateral_address:
        print(f"Address: {result.collateral_address.full_address}")
    print(f"Confidence: {result.confidence_score}")
    return result
