"""API routes for credit agreement extraction."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chains.extraction_chain import extract_data, extract_data_smart
from app.models.cdm import ExtractionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class ExtractionRequest(BaseModel):
    """Request model for credit agreement extraction."""
    text: str = Field(..., description="The raw text content of a credit agreement document")
    force_map_reduce: bool = Field(False, description="Force map-reduce extraction strategy for large documents")


@router.post("/extract", response_model=ExtractionResult)
async def extract_credit_agreement(request: ExtractionRequest) -> ExtractionResult:
    """Extract structured data from a credit agreement document.
    
    Args:
        request: ExtractionRequest containing the document text and options.
        
    Returns:
        ExtractionResult containing the extracted credit agreement data.
        
    Raises:
        HTTPException: 422 for validation errors, 500 for server errors.
    """
    try:
        logger.info(f"Received extraction request for {len(request.text)} characters")
        
        result = extract_data_smart(
            text=request.text,
            force_map_reduce=request.force_map_reduce
        )
        
        return ExtractionResult(
            status=result.extraction_status,
            agreement=result if result.extraction_status.value in ["success", "partial_data_missing"] else None,
            message=None if result.extraction_status.value in ["success", "partial_data_missing"] else "Document is not a valid credit agreement"
        )
        
    except ValueError as e:
        logger.error(f"Validation error during extraction: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CreditNexus API"}
