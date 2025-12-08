"""API routes for credit agreement extraction."""

import logging
import io
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.chains.extraction_chain import extract_data, extract_data_smart
from app.models.cdm import ExtractionResult

logger = logging.getLogger(__name__)


MAX_FILE_SIZE_MB = 20

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from a PDF file using PyMuPDF.
    
    Args:
        file_content: The raw bytes of the PDF file.
        
    Returns:
        Extracted text from all pages.
    """
    import fitz
    
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large ({file_size_mb:.1f} MB). Maximum size is {MAX_FILE_SIZE_MB} MB.")
    
    doc = None
    text_parts = []
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page in doc:
            text_parts.append(page.get_text())
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to parse PDF file: {str(e)}")
    finally:
        if doc:
            doc.close()
    
    return "\n".join(text_parts)

router = APIRouter(prefix="/api")


class ExtractionRequest(BaseModel):
    """Request model for credit agreement extraction."""
    text: str = Field(..., description="The raw text content of a credit agreement document")
    force_map_reduce: bool = Field(False, description="Force map-reduce extraction strategy for large documents")


@router.post("/extract")
async def extract_credit_agreement(request: ExtractionRequest):
    """Extract structured data from a credit agreement document.
    
    Args:
        request: ExtractionRequest containing the document text and options.
        
    Returns:
        Extraction result with status, agreement data, and optional message.
    """
    from app.models.cdm import ExtractionStatus
    
    try:
        logger.info(f"Received extraction request for {len(request.text)} characters")
        
        result = extract_data_smart(
            text=request.text,
            force_map_reduce=request.force_map_reduce
        )
        
        if result is None:
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "Extraction returned no data"}
            )
        
        if result.status == ExtractionStatus.FAILURE:
            raise HTTPException(
                status_code=422,
                detail={"status": "irrelevant_document", "message": result.message or "This document does not appear to be a credit agreement."}
            )
        
        message = result.message
        if result.status == ExtractionStatus.PARTIAL and not message:
            missing_fields = []
            if result.agreement:
                if not result.agreement.agreement_date:
                    missing_fields.append("agreement date")
                if not result.agreement.parties:
                    missing_fields.append("parties")
                if not result.agreement.facilities:
                    missing_fields.append("loan facilities")
                if not result.agreement.governing_law:
                    missing_fields.append("governing law")
            if missing_fields:
                message = f"Partial extraction: missing {', '.join(missing_fields)}. Please review carefully."
            else:
                message = "Some data may be incomplete. Please review the extracted information carefully."
        
        return {
            "status": result.status.value,
            "agreement": result.agreement.model_dump() if result.agreement else None,
            "message": message
        }
        
    except ValueError as e:
        logger.warning(f"Validation issue during extraction: {e}")
        raise HTTPException(
            status_code=422,
            detail={"status": "partial_data_missing", "message": str(e)}
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Extraction failed: {str(e)}"}
        )


@router.post("/upload")
async def upload_and_extract(file: UploadFile = File(...)):
    """Upload a file (PDF or TXT) and extract structured data.
    
    Args:
        file: The uploaded file.
        
    Returns:
        Extraction result with status, agreement data, extracted text, and optional message.
    """
    from app.models.cdm import ExtractionStatus
    
    filename = file.filename or ""
    extension = filename.lower().split(".")[-1] if "." in filename else ""
    
    if extension == "pdf" or (file.content_type and "pdf" in file.content_type.lower()):
        file_type = "pdf"
    elif extension == "txt" or file.content_type == "text/plain":
        file_type = "txt"
    else:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": f"Unsupported file type: {extension or file.content_type}. Supported types: PDF, TXT"}
        )
    
    try:
        content = await file.read()
        
        if file_type == "pdf":
            text = extract_text_from_pdf(content)
        else:
            text = content.decode("utf-8", errors="replace")
        
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "The uploaded file contains no extractable text."}
            )
        
        logger.info(f"Extracted {len(text)} characters from uploaded {file_type.upper()} file")
        
        result = extract_data_smart(text=text, force_map_reduce=False)
        
        if result is None:
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "Extraction returned no data"}
            )
        
        if result.status == ExtractionStatus.FAILURE:
            raise HTTPException(
                status_code=422,
                detail={"status": "irrelevant_document", "message": result.message or "This document does not appear to be a credit agreement."}
            )
        
        message = result.message
        if result.status == ExtractionStatus.PARTIAL and not message:
            missing_fields = []
            if result.agreement:
                if not result.agreement.agreement_date:
                    missing_fields.append("agreement date")
                if not result.agreement.parties:
                    missing_fields.append("parties")
                if not result.agreement.facilities:
                    missing_fields.append("loan facilities")
                if not result.agreement.governing_law:
                    missing_fields.append("governing law")
            if missing_fields:
                message = f"Partial extraction: missing {', '.join(missing_fields)}. Please review carefully."
            else:
                message = "Some data may be incomplete. Please review the extracted information carefully."
        
        return {
            "status": result.status.value,
            "agreement": result.agreement.model_dump() if result.agreement else None,
            "message": message,
            "extracted_text": text
        }
        
    except ValueError as e:
        logger.warning(f"File parsing error: {e}")
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": str(e)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload and extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to process file: {str(e)}"}
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CreditNexus API"}
