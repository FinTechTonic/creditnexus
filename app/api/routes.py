"""API routes for credit agreement extraction."""

import logging
import io
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, Request, Form, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session, joinedload
import pandas as pd

from app.chains.extraction_chain import extract_data, extract_data_smart
from app.models.cdm import ExtractionResult, CreditAgreement
from app.db import get_db
from app.db.models import StagedExtraction, ExtractionStatus, Document, DocumentVersion, Workflow, WorkflowState, User, AuditLog, AuditAction, PolicyDecision as PolicyDecisionModel, PolicyDecision, ClauseCache, LMATemplate, Deal, DealNote, GreenFinanceAssessment
from app.auth.jwt_auth import get_current_user, require_auth
from app.services.policy_service import PolicyService
from app.services.x402_payment_service import X402PaymentService
from app.services.clause_cache_service import ClauseCacheService
from app.services.file_storage_service import FileStorageService
from app.services.deal_service import DealService
from app.services.profile_extraction_service import ProfileExtractionService
from app.chains.document_retrieval_chain import DocumentRetrievalService, add_user_profile, search_user_profiles
from app.utils.audit import log_audit_action
from fastapi import Request

logger = logging.getLogger(__name__)

# Deep Tech Components (Loaded on startup)
from app.agents.classifier import LandUseClassifier
from app.models.cdm_events import generate_cdm_trade_execution, generate_cdm_observation, generate_cdm_terms_change
from app.agents.vector_store import GLOBAL_VECTOR_STORE
import hashlib

# Initialize TorchGeo Classifier (Loads ResNet50 Weights)
# This might take a few seconds on first run
GLOBAL_CLASSIFIER = LandUseClassifier()


def get_policy_service(request: Request) -> Optional[PolicyService]:
    """
    Get policy service instance from application state.
    
    This dependency function provides access to the PolicyService instance
    that was initialized at application startup. Returns None if policy
    engine is disabled.
    
    Args:
        request: FastAPI request object (to access app.state)
        
    Returns:
        PolicyService instance or None if disabled
    """
    if hasattr(request.app.state, 'policy_service'):
        return request.app.state.policy_service
    return None


def get_x402_payment_service(request: Request) -> Optional[X402PaymentService]:
    """
    Get x402 payment service instance from application state.
    
    This dependency function provides access to the X402PaymentService instance
    that was initialized at application startup. Returns None if x402
    payment service is disabled.
    
    Args:
        request: FastAPI request object (to access app.state)
        
    Returns:
        X402PaymentService instance or None if disabled
    """
    if hasattr(request.app.state, 'x402_payment_service'):
        return request.app.state.x402_payment_service
    return None


MAX_FILE_SIZE_MB = 20

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from a PDF file using PyMuPDF.
    
    Args:
        file_content: The raw bytes of the PDF file.
        
    Returns:
        Extracted text from all pages.
        
    Raises:
        ValueError: If file is not a valid PDF, too large, or corrupted.
    """
    import fitz
    
    # Validate file size first
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large ({file_size_mb:.1f} MB). Maximum size is {MAX_FILE_SIZE_MB} MB.")
    
    # Validate PDF magic bytes (PDF files start with %PDF-)
    if not file_content.startswith(b'%PDF-'):
        raise ValueError("Invalid PDF file: File does not start with PDF magic bytes.")
    
    # Validate PDF structure by attempting to open it
    doc = None
    text_parts = []
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        # Additional validation: check if document has pages
        if doc.page_count == 0:
            raise ValueError("Invalid PDF file: Document has no pages.")
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
# Rate limiting: Uses slowapi default_limits (60/minute) from server.py
# This endpoint processes large documents and may need custom limits in production
async def extract_credit_agreement(
    request: ExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    policy_service: Optional[PolicyService] = Depends(get_policy_service)
):
    """Extract structured data from a credit agreement document.
    
    Args:
        request: ExtractionRequest containing the document text and options.
        db: Database session for audit logging.
        current_user: Current authenticated user.
        policy_service: Policy service for compliance evaluation (optional).
        
    Returns:
        Extraction result with status, agreement data, policy decision, and optional message.
    """
    from app.models.cdm import ExtractionStatus
    from app.db.models import PolicyDecision as PolicyDecisionModel
    from app.models.cdm_events import generate_cdm_policy_evaluation
    
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
        
        # Policy evaluation (if enabled and agreement extracted)
        policy_decision = None
        policy_evaluation_event = None
        
        if policy_service and result.agreement:
            try:
                # Evaluate facility creation for compliance
                policy_result = policy_service.evaluate_facility_creation(
                    credit_agreement=result.agreement,
                    document_id=None  # No document ID yet at extraction stage
                )
                
                # Create CDM PolicyEvaluation event
                policy_evaluation_event = generate_cdm_policy_evaluation(
                    transaction_id=result.agreement.deal_id or result.agreement.loan_identification_number or "unknown",
                    transaction_type="facility_creation",
                    decision=policy_result.decision,
                    rule_applied=policy_result.rule_applied,
                    related_event_identifiers=[],
                    evaluation_trace=policy_result.trace,
                    matched_rules=policy_result.matched_rules
                )
                
                # Handle BLOCK decision - prevent workflow progression
                if policy_result.decision == "BLOCK":
                    logger.warning(
                        f"Policy evaluation BLOCKED facility creation: "
                        f"rule={policy_result.rule_applied}, trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    # Note: loan_asset_id is None for document extraction (no loan asset yet)
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=result.agreement.deal_id or result.agreement.loan_identification_number or "unknown",
                            transaction_type="facility_creation",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"document_extraction": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset at extraction stage
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        # The foreign key constraint exists in DB, but SQLAlchemy may not find it in metadata
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with block decision.")
                        db.rollback()
                    
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "status": "blocked",
                            "reason": policy_result.rule_applied,
                            "trace_id": policy_result.trace_id,
                            "message": f"Facility creation blocked by compliance policy: {policy_result.rule_applied}",
                            "cdm_event": policy_evaluation_event
                        }
                    )
                
                # Handle FLAG decision - allow but mark for review
                elif policy_result.decision == "FLAG":
                    logger.info(
                        f"Policy evaluation FLAGGED facility creation: "
                        f"rule={policy_result.rule_applied}, trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=result.agreement.deal_id or result.agreement.loan_identification_number or "unknown",
                            transaction_type="facility_creation",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"document_extraction": True, "requires_review": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset at extraction stage
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with extraction.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id,
                        "requires_review": True
                    }
                
                # Handle ALLOW decision - log for audit
                else:
                    logger.debug(
                        f"Policy evaluation ALLOWED facility creation: trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=result.agreement.deal_id or result.agreement.loan_identification_number or "unknown",
                            transaction_type="facility_creation",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"document_extraction": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset at extraction stage
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with extraction.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id
                    }
                    
            except HTTPException:
                # Re-raise HTTP exceptions (e.g., BLOCK decision)
                raise
            except Exception as e:
                # Log policy evaluation errors but don't block extraction
                logger.error(f"Policy evaluation failed: {e}", exc_info=True)
                # Continue with extraction even if policy evaluation fails
        
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
            "policy_decision": policy_decision,
            "cdm_events": [policy_evaluation_event] if policy_evaluation_event else []
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
# Rate limiting: Uses slowapi default_limits (60/minute) from server.py
# File upload endpoints may benefit from stricter limits (e.g., 10/minute) in production
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


@router.post("/audio/transcribe")
# Rate limiting: Uses slowapi default_limits (60/minute) from server.py
# Audio processing is resource-intensive; consider stricter limits (e.g., 5/minute) in production
async def transcribe_audio(
    file: UploadFile = File(...),
    source_lang: Optional[str] = Query(None, description="Source language code (e.g., 'en', 'es')"),
    target_lang: Optional[str] = Query(None, description="Target language code (e.g., 'en', 'es')"),
    extract_cdm: bool = Query(True, description="Whether to extract CDM data from transcription"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Transcribe audio file and optionally extract CDM data.
    
    This endpoint:
    1. Transcribes the uploaded audio file using nvidia/canary-1b-v2
    2. Optionally extracts CDM data from the transcription using existing extraction chain
    3. Stores transcription separately for audit purposes
    
    Args:
        file: The uploaded audio file (WAV, MP3, M4A, OGG, FLAC, etc.)
        source_lang: Source language code (default: from config or 'en')
        target_lang: Target language code (default: from config or 'en')
        extract_cdm: Whether to extract CDM data from transcription (default: True)
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Transcription result with transcribed text, optional CDM data, and audit info
    """
    from app.chains.audio_transcription_chain import process_audio_file
    from app.models.cdm import ExtractionStatus
    
    # Validate file type
    filename = file.filename or "audio.wav"
    extension = filename.lower().split(".")[-1] if "." in filename else ""
    supported_extensions = ["wav", "mp3", "m4a", "ogg", "flac", "webm"]
    
    if extension not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": f"Unsupported audio format: {extension}. Supported: {', '.join(supported_extensions)}"
            }
        )
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Uploaded file is empty"}
            )
        
        logger.info(f"Transcribing audio file: {filename} ({len(audio_bytes)} bytes)")
        
        # Transcribe audio
        try:
            transcribed_text = process_audio_file(
                audio_bytes=audio_bytes,
                filename=filename,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except ValueError as e:
            logger.error(f"Audio transcription failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": f"Audio transcription failed: {str(e)}"}
            )
        
        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "Transcription returned empty text"}
            )
        
        logger.info(f"Transcription complete: {len(transcribed_text)} characters")
        
        # Prepare response
        response_data = {
            "status": "success",
            "transcription": transcribed_text,
            "transcription_length": len(transcribed_text),
            "source_filename": filename,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        
        # Optionally extract CDM data from transcription
        if extract_cdm:
            try:
                logger.info("Extracting CDM data from transcription...")
                result = extract_data_smart(text=transcribed_text, force_map_reduce=False)
                
                if result and result.agreement:
                    response_data["agreement"] = result.agreement.model_dump()
                    response_data["extraction_status"] = result.status.value
                    response_data["extraction_message"] = result.message
                else:
                    response_data["agreement"] = None
                    response_data["extraction_status"] = "failure"
                    response_data["extraction_message"] = "CDM extraction returned no data"
                    
            except Exception as e:
                logger.warning(f"CDM extraction from transcription failed: {e}")
                response_data["agreement"] = None
                response_data["extraction_status"] = "error"
                response_data["extraction_message"] = f"CDM extraction failed: {str(e)}"
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="audio_transcription",
                    user_id=current_user.id,
                    metadata={
                        "filename": filename,
                        "transcription_length": len(transcribed_text),
                        "extract_cdm": extract_cdm,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log audio transcription audit: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during audio transcription: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to process audio file: {str(e)}"}
        )


@router.post("/image/extract")
# Rate limiting: Uses slowapi default_limits (60/minute) from server.py
# Image processing is resource-intensive; consider stricter limits (e.g., 10/minute) in production
async def extract_from_images(
    files: List[UploadFile] = File(...),
    extract_cdm: bool = Query(True, description="Whether to extract CDM data from OCR text"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Extract text from images and optionally extract CDM data.
    
    This endpoint:
    1. Extracts text from uploaded image files using OCR (Multimodal-OCR3)
    2. Combines OCR text from all images
    3. Optionally extracts CDM data from the combined text using comprehensive extraction chain
    4. Stores OCR text separately for audit purposes
    
    Supports multiple image uploads for processing documents across multiple pages/images.
    
    Args:
        files: List of uploaded image files (PNG, JPEG, WEBP, etc.)
        extract_cdm: Whether to extract CDM data from OCR text (default: True)
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Extraction result with OCR text, optional CDM data, and audit info
    """
    from app.chains.image_extraction_chain import process_multiple_image_files
    from app.chains.extraction_chain import extract_data_smart
    from app.models.cdm import ExtractionStatus
    
    # Validate file types
    supported_extensions = ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif"]
    image_files = []
    filenames = []
    
    for file in files:
        filename = file.filename or "image.png"
        extension = filename.lower().split(".")[-1] if "." in filename else ""
        
        if extension not in supported_extensions:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Unsupported image format: {extension}. Supported: {', '.join(supported_extensions)}"
                }
            )
        
        filenames.append(filename)
    
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "No image files provided"}
        )
    
    try:
        # Read all image files
        for file in files:
            image_bytes = await file.read()
            if len(image_bytes) == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Uploaded file {file.filename} is empty"}
                )
            image_files.append((image_bytes, file.filename or "image.png"))
        
        logger.info(f"Processing {len(image_files)} image(s) for OCR extraction")
        
        # Extract text from all images using OCR
        try:
            ocr_texts = process_multiple_image_files(image_files)
        except ValueError as e:
            logger.error(f"Image OCR failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": f"Image OCR failed: {str(e)}"}
            )
        
        # Combine OCR text from all images
        combined_text = "\n\n--- Image Separator ---\n\n".join(
            [text if text else f"[No text extracted from {filename}]" 
             for text, filename in zip(ocr_texts, filenames)]
        )
        
        if not combined_text.strip() or combined_text.strip() == "":
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "OCR returned no text from any image"}
            )
        
        logger.info(f"OCR complete: {len(combined_text)} characters extracted from {len(image_files)} image(s)")
        
        # Prepare response
        response_data = {
            "status": "success",
            "ocr_text": combined_text,
            "ocr_text_length": len(combined_text),
            "source_filenames": filenames,
            "images_processed": len(image_files),
            "ocr_texts_per_image": [
                {"filename": filename, "text": text, "length": len(text)}
                for filename, text in zip(filenames, ocr_texts)
            ],
        }
        
        # Optionally extract CDM data from OCR text
        if extract_cdm:
            try:
                logger.info("Extracting CDM data from OCR text...")
                # Use comprehensive extraction prompt for better handling of various document types
                result = extract_data_smart(text=combined_text, force_map_reduce=False)
                
                if result and result.agreement:
                    response_data["agreement"] = result.agreement.model_dump()
                    response_data["extraction_status"] = result.status.value
                    response_data["extraction_message"] = result.message
                else:
                    response_data["agreement"] = None
                    response_data["extraction_status"] = "failure"
                    response_data["extraction_message"] = "CDM extraction returned no data"
                    
            except Exception as e:
                logger.warning(f"CDM extraction from OCR text failed: {e}")
                response_data["agreement"] = None
                response_data["extraction_status"] = "error"
                response_data["extraction_message"] = f"CDM extraction failed: {str(e)}"
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="image_extraction",
                    user_id=current_user.id,
                    metadata={
                        "filenames": filenames,
                        "images_count": len(image_files),
                        "ocr_text_length": len(combined_text),
                        "extract_cdm": extract_cdm,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log image extraction audit: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to process image files: {str(e)}"}
        )


@router.get("/health")
async def health_check():
    """Health check endpoint that reports system status."""
    from app.db import SessionLocal, engine
    from app.core.config import settings
    from fastapi.responses import JSONResponse
    
    # Check database availability
    db_status = "unavailable"
    db_type = None
    if SessionLocal is not None and engine is not None:
        db_status = "operational"
        # Determine database type from URL
        db_url = str(engine.url) if hasattr(engine, 'url') else None
        if db_url:
            if "sqlite" in db_url.lower():
                db_type = "SQLite"
            elif "postgresql" in db_url.lower() or "postgres" in db_url.lower():
                db_type = "PostgreSQL"
            else:
                db_type = "Unknown"
    
    status = {
        "status": "healthy",
        "service": "CreditNexus API",
        "services": {
            "api": "operational",
            "database": {
                "status": db_status,
                "type": db_type,
                "enabled": settings.DATABASE_ENABLED
            },
            "llm": "operational",  # TODO: Add actual LLM health check
            "policy_engine": "operational" if settings.POLICY_ENABLED else "disabled",
        }
    }
    
    # Mark as degraded if database is unavailable but enabled
    if settings.DATABASE_ENABLED and db_status == "unavailable":
        status["status"] = "degraded"
        status["warnings"] = ["Database is enabled but not available"]
    
    status_code = 200 if status["status"] == "healthy" else 503
    return JSONResponse(content=status, status_code=status_code)


@router.get("/health/database/ssl")
async def health_check_database_ssl():
    """Check SSL status of database connection.
    
    Returns SSL connection information including:
    - SSL enabled status
    - SSL version
    - SSL cipher
    - Certificate validation status
    """
    from app.db import SessionLocal, engine
    from app.core.config import settings
    from app.db.ssl_config import validate_ssl_config
    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    
    # Check if database is available
    if SessionLocal is None or engine is None:
        return JSONResponse(
            content={
                "ssl_enabled": False,
                "error": "Database not configured",
                "status": "error"
            },
            status_code=503
        )
    
    # Validate SSL configuration
    is_valid, error_msg = validate_ssl_config()
    
    ssl_info = {
        "ssl_enabled": False,
        "ssl_mode": settings.DB_SSL_MODE,
        "ssl_required": settings.DB_SSL_REQUIRED,
        "ssl_version": None,
        "ssl_cipher": None,
        "certificate_validation": None,
        "config_valid": is_valid,
        "config_error": error_msg if not is_valid else None,
        "status": "unknown"
    }
    
    # Try to check SSL status from database
    try:
        with engine.connect() as conn:
            # Check if SSL is active (PostgreSQL only)
            if not str(engine.url).startswith("sqlite"):
                try:
                    # Check SSL status
                    ssl_result = conn.execute(text("SHOW ssl"))
                    ssl_active = ssl_result.scalar() == "on"
                    ssl_info["ssl_enabled"] = ssl_active
                    
                    if ssl_active:
                        # Get SSL version
                        try:
                            version_result = conn.execute(text("SHOW ssl_version"))
                            ssl_info["ssl_version"] = version_result.scalar()
                        except Exception:
                            pass
                        
                        # Get SSL cipher
                        try:
                            cipher_result = conn.execute(text("SHOW ssl_cipher"))
                            ssl_info["ssl_cipher"] = cipher_result.scalar()
                        except Exception:
                            pass
                        
                        # Determine certificate validation status
                        if settings.DB_SSL_MODE in ["verify-ca", "verify-full"]:
                            ssl_info["certificate_validation"] = "enabled"
                        elif settings.DB_SSL_MODE == "require":
                            ssl_info["certificate_validation"] = "disabled"
                        else:
                            ssl_info["certificate_validation"] = "optional"
                        
                        ssl_info["status"] = "healthy"
                    else:
                        if settings.DB_SSL_REQUIRED:
                            ssl_info["status"] = "error"
                            ssl_info["error"] = "SSL is required but connection is not using SSL"
                        else:
                            ssl_info["status"] = "warning"
                            ssl_info["warning"] = "SSL is not active but not required"
                            
                except Exception as e:
                    # PostgreSQL might not support these commands or SSL might not be configured
                    ssl_info["status"] = "warning"
                    ssl_info["warning"] = f"Could not determine SSL status: {str(e)}"
            else:
                # SQLite doesn't support SSL
                ssl_info["status"] = "not_applicable"
                ssl_info["message"] = "SQLite does not support SSL/TLS"
                
    except Exception as e:
        ssl_info["status"] = "error"
        ssl_info["error"] = str(e)
    
    # Determine HTTP status code
    if ssl_info["status"] == "error":
        status_code = 503
    elif ssl_info["status"] == "warning":
        status_code = 200  # Still return 200 but with warning
    else:
        status_code = 200
    
    return JSONResponse(content=ssl_info, status_code=status_code)


class ApproveRequest(BaseModel):
    """Request model for approving an extraction."""
    agreement_data: dict = Field(..., description="The extracted agreement data to approve")
    original_text: Optional[str] = Field(None, description="The original document text")
    source_filename: Optional[str] = Field(None, description="The source file name")
    reviewed_by: Optional[str] = Field(None, description="Who reviewed the extraction")


class RejectRequest(BaseModel):
    """Request model for rejecting an extraction."""
    agreement_data: dict = Field(..., description="The extracted agreement data being rejected")
    rejection_reason: str = Field(..., description="Reason for rejecting the extraction")
    original_text: Optional[str] = Field(None, description="The original document text")
    source_filename: Optional[str] = Field(None, description="The source file name")
    reviewed_by: Optional[str] = Field(None, description="Who reviewed the extraction")


@router.post("/approve")
async def approve_extraction(request: ApproveRequest, db: Session = Depends(get_db)):
    """Approve and store an extraction in the staging database.
    
    Args:
        request: ApproveRequest containing the agreement data and metadata.
        db: Database session.
        
    Returns:
        The created staged extraction record.
    """
    try:
        staged = StagedExtraction(
            status=ExtractionStatus.APPROVED.value,
            agreement_data=request.agreement_data,
            original_text=request.original_text,
            source_filename=request.source_filename,
            reviewed_by=request.reviewed_by,
        )
        db.add(staged)
        db.commit()
        db.refresh(staged)
        
        logger.info(f"Approved extraction saved with ID: {staged.id}")
        
        return {
            "status": "success",
            "message": "Extraction approved and saved",
            "extraction": staged.to_dict()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving approved extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to save extraction: {str(e)}"}
        )


@router.post("/reject")
async def reject_extraction(request: RejectRequest, db: Session = Depends(get_db)):
    """Reject and store an extraction in the staging database with a reason.
    
    Args:
        request: RejectRequest containing the agreement data, reason, and metadata.
        db: Database session.
        
    Returns:
        The created staged extraction record.
    """
    try:
        staged = StagedExtraction(
            status=ExtractionStatus.REJECTED.value,
            agreement_data=request.agreement_data,
            original_text=request.original_text,
            source_filename=request.source_filename,
            rejection_reason=request.rejection_reason,
            reviewed_by=request.reviewed_by,
        )
        db.add(staged)
        db.commit()
        db.refresh(staged)
        
        logger.info(f"Rejected extraction saved with ID: {staged.id}")
        
        return {
            "status": "success",
            "message": "Extraction rejected and saved",
            "extraction": staged.to_dict()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving rejected extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to save rejection: {str(e)}"}
        )


@router.get("/extractions")
async def list_extractions(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """List staged extractions with optional filtering.
    
    Args:
        status: Optional status filter.
        limit: Maximum number of results (default 50, max 100).
        offset: Pagination offset.
        db: Database session.
        
    Returns:
        List of staged extractions.
    """
    try:
        query = db.query(StagedExtraction)
        
        if status:
            if status not in [s.value for s in ExtractionStatus]:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid status: {status}. Must be one of: pending, approved, rejected"}
                )
            query = query.filter(StagedExtraction.status == status)
        
        total = query.count()
        
        extractions = query.order_by(StagedExtraction.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "extractions": [e.to_dict() for e in extractions]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing extractions: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list extractions: {str(e)}"}
        )


class CreateDocumentRequest(BaseModel):
    """Request model for creating a new document."""
    title: str = Field(..., description="Document title")
    agreement_data: dict = Field(..., description="The extracted agreement data")
    original_text: Optional[str] = Field(None, description="The original document text")
    source_filename: Optional[str] = Field(None, description="The source file name")
    extraction_method: str = Field("simple", description="The extraction method used")
    # LMA Template Generation fields
    is_generated: Optional[bool] = Field(False, description="Whether this document was generated from a template")
    template_id: Optional[int] = Field(None, description="LMA template ID if generated from template")
    source_cdm_data: Optional[dict] = Field(None, description="Source CDM data used for generation")
    # Deal relationship
    deal_id: Optional[int] = Field(None, description="Optional deal ID to attach document to a deal")


class CreateVersionRequest(BaseModel):
    """Request model for creating a new document version."""
    agreement_data: dict = Field(..., description="The updated extracted agreement data")
    original_text: Optional[str] = Field(None, description="The original document text")
    source_filename: Optional[str] = Field(None, description="The source file name")
    extraction_method: str = Field("simple", description="The extraction method used")


class TradeExecutionRequest(BaseModel):
    """Request model for trade execution with policy evaluation."""
    trade_id: str = Field(..., description="Unique trade identifier")
    borrower: str = Field(..., description="Borrower name or identifier")
    amount: float = Field(..., gt=0, description="Trade amount (must be positive)")
    rate: float = Field(..., ge=0, description="Interest rate (percentage or basis points)")
    credit_agreement_id: Optional[int] = Field(None, description="Optional credit agreement ID for context")


def extract_document_metadata(agreement_data: dict) -> dict:
    """Extract document-level metadata from agreement data."""
    metadata = {}
    
    if "agreement_date" in agreement_data and agreement_data["agreement_date"]:
        try:
            if isinstance(agreement_data["agreement_date"], str):
                metadata["agreement_date"] = datetime.fromisoformat(agreement_data["agreement_date"].replace("Z", "+00:00")).date()
            else:
                metadata["agreement_date"] = agreement_data["agreement_date"]
        except (ValueError, TypeError):
            pass
    
    if "governing_law" in agreement_data:
        metadata["governing_law"] = agreement_data["governing_law"]
    
    parties = agreement_data.get("parties", [])
    for party in parties:
        role = party.get("role", "")
        if isinstance(role, str) and "borrower" in role.lower():
            metadata["borrower_name"] = party.get("name") or party.get("legal_name")
            metadata["borrower_lei"] = party.get("lei")
            break
    
    facilities = agreement_data.get("facilities", [])
    if facilities:
        total = Decimal("0")
        currency = None
        for facility in facilities:
            if not isinstance(facility, dict):
                continue
            commitment = facility.get("commitment_amount") or facility.get("commitment")
            if commitment and isinstance(commitment, dict):
                amount = commitment.get("amount")
                if amount:
                    total += Decimal(str(amount))
                if not currency and commitment.get("currency"):
                    currency = commitment["currency"]
        if total > 0:
            metadata["total_commitment"] = total
            metadata["currency"] = currency
    
    sustainability = agreement_data.get("sustainability_provisions")
    if sustainability and isinstance(sustainability, dict):
        metadata["sustainability_linked"] = sustainability.get("is_sustainability_linked", False)
        metadata["esg_metadata"] = sustainability
    elif agreement_data.get("sustainability_linked"):
        metadata["sustainability_linked"] = agreement_data.get("sustainability_linked", False)
    
    # Extract transaction identifiers for policy decision lookup
    if agreement_data.get("deal_id"):
        metadata["deal_id"] = agreement_data.get("deal_id")
    if agreement_data.get("loan_identification_number"):
        metadata["loan_identification_number"] = agreement_data.get("loan_identification_number")
    
    return metadata


@router.post("/documents")
async def create_document(
    doc_request: CreateDocumentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new document with its first version.
    
    Args:
        doc_request: CreateDocumentRequest containing the document data.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The created document with its first version.
    """
    try:
        metadata = extract_document_metadata(doc_request.agreement_data)
        
        # Handle deal linking if deal_id is provided
        deal = None
        file_storage = FileStorageService()
        if doc_request.deal_id:
            deal = db.query(Deal).filter(Deal.id == doc_request.deal_id).first()
            if not deal:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "message": f"Deal {doc_request.deal_id} not found"}
                )
            # Ensure deal folder exists
            if not deal.folder_path:
                deal.folder_path = file_storage.create_deal_folder(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id
                )
                db.flush()
        
        doc = Document(
            title=doc_request.title,
            borrower_name=metadata.get("borrower_name"),
            borrower_lei=metadata.get("borrower_lei"),
            governing_law=metadata.get("governing_law"),
            total_commitment=metadata.get("total_commitment"),
            currency=metadata.get("currency"),
            agreement_date=metadata.get("agreement_date"),
            sustainability_linked=metadata.get("sustainability_linked", False),
            esg_metadata=metadata.get("esg_metadata"),
            uploaded_by=current_user.id,
            # LMA Template Generation fields
            is_generated=doc_request.is_generated or False,
            template_id=doc_request.template_id,
            source_cdm_data=doc_request.source_cdm_data,
            # Deal relationship
            deal_id=doc_request.deal_id,
        )
        db.add(doc)
        db.flush()
        
        # Store document in deal folder if deal is linked
        if deal and doc_request.original_text:
            try:
                file_storage.store_deal_document(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id,
                    document_id=doc.id,
                    filename=doc_request.source_filename or f"document_{doc.id}.txt",
                    content=doc_request.original_text.encode('utf-8'),
                    subdirectory="documents"
                )
            except Exception as e:
                logger.warning(f"Failed to store document in deal folder: {e}")
        
        # If document is attached to deal, use DealService to create CDM event
        if deal:
            try:
                deal_service = DealService(db)
                deal_service.attach_document_to_deal(
                    deal_id=deal.id,
                    document_id=doc.id,
                    user_id=current_user.id
                )
            except Exception as e:
                logger.warning(f"Failed to attach document to deal via DealService: {e}")
        
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            extracted_data=doc_request.agreement_data,
            original_text=doc_request.original_text,
            source_filename=doc_request.source_filename,
            extraction_method=doc_request.extraction_method,
            created_by=current_user.id,
        )
        db.add(version)
        db.flush()
        
        doc.current_version_id = version.id
        
        # Check for policy decisions that might affect workflow priority
        # Look for recent policy decisions for this transaction (deal_id or loan_identification_number)
        priority = "normal"
        # Set initial state based on whether document is generated
        if doc_request.is_generated:
            initial_state = WorkflowState.GENERATED.value
        else:
            initial_state = WorkflowState.DRAFT.value
        
        if metadata.get("deal_id") or metadata.get("loan_identification_number"):
            transaction_id = metadata.get("deal_id") or metadata.get("loan_identification_number")
            
            # Query for recent policy decision for this transaction
            recent_policy_decision = db.query(PolicyDecisionModel).filter(
                PolicyDecisionModel.transaction_id == transaction_id,
                PolicyDecisionModel.transaction_type == "facility_creation"
            ).order_by(PolicyDecisionModel.created_at.desc()).first()
            
            if recent_policy_decision:
                if recent_policy_decision.decision == "FLAG":
                    # FLAG decision: set high priority and mark for review
                    priority = "high"
                    logger.info(
                        f"Workflow for document {doc.id} set to high priority due to FLAG policy decision: "
                        f"{recent_policy_decision.rule_applied}"
                    )
                elif recent_policy_decision.decision == "BLOCK":
                    # BLOCK decision: This should have been caught earlier, but log it
                    logger.warning(
                        f"Document {doc.id} created despite BLOCK policy decision: "
                        f"{recent_policy_decision.rule_applied}"
                    )
                    priority = "high"  # Still set high priority for visibility
        
        workflow = Workflow(
            document_id=doc.id,
            state=initial_state,
            priority=priority,
        )
        db.add(workflow)
        
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="document",
            target_id=doc.id,
            user_id=current_user.id,
            metadata={"title": doc_request.title, "borrower_name": metadata.get("borrower_name")},
            request=request
        )
        
        db.commit()
        db.refresh(doc)
        db.refresh(version)
        
        logger.info(f"Created document {doc.id} with version {version.id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document created successfully",
            "document": {
                **doc.to_dict(),
                "versions": [version.to_dict()],
                "workflow": workflow.to_dict() if workflow else None,
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating document: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create document: {str(e)}"}
        )


@router.get("/documents")
async def list_documents(
    search: Optional[str] = Query(None, description="Search term for title or borrower name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo documents (check deal.deal_data['is_demo'])"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents with optional filtering.
    
    Args:
        search: Optional search term.
        limit: Maximum number of results (default 50, max 100).
        offset: Pagination offset.
        is_demo: Optional filter for demo documents (checks deal.deal_data['is_demo']).
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        List of documents with summary information.
    """
    try:
        query = db.query(Document).options(
            joinedload(Document.workflow),
            joinedload(Document.uploaded_by_user),
            joinedload(Document.deal)
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Document.title.ilike(search_term)) |
                (Document.borrower_name.ilike(search_term))
            )
        
        # Filter by is_demo if requested (check deal.deal_data['is_demo'])
        if is_demo is not None:
            if is_demo:
                # Only include documents where deal.deal_data['is_demo'] == True
                query = query.join(Deal).filter(
                    Deal.deal_data['is_demo'].astext == 'true'
                )
            else:
                # Exclude demo documents
                query = query.outerjoin(Deal).filter(
                    (Deal.id.is_(None)) | (Deal.deal_data['is_demo'].astext != 'true')
                )
        
        total = query.count()
        
        documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for doc in documents:
            doc_dict = doc.to_dict()
            doc_dict["workflow_state"] = doc.workflow.state if doc.workflow else None
            doc_dict["uploaded_by_name"] = doc.uploaded_by_user.display_name if doc.uploaded_by_user else None
            # Add is_demo flag from deal if available
            if doc.deal and doc.deal.deal_data:
                doc_dict["is_demo"] = doc.deal.deal_data.get("is_demo", False)
            else:
                doc_dict["is_demo"] = False
            # Add has_cdm_data flag - check if document has CDM data in any version
            has_cdm = False
            if doc.source_cdm_data:
                has_cdm = True
            elif doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    has_cdm = True
            elif doc.versions:
                # Check latest version
                latest_version = sorted(doc.versions, key=lambda v: v.version_number or 0, reverse=True)[0]
                if latest_version and latest_version.extracted_data:
                    has_cdm = True
            doc_dict["has_cdm_data"] = has_cdm
            result.append(doc_dict)
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": result
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list documents: {str(e)}"}
        )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    include_cdm_data: bool = Query(False, description="Include CDM data in response"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a document with all its versions.
    
    Args:
        document_id: The document ID.
        include_cdm_data: If True, include CDM data in the response.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        The document with all versions, optionally including CDM data.
    """
    try:
        doc = db.query(Document).options(
            joinedload(Document.versions),
            joinedload(Document.workflow),
            joinedload(Document.uploaded_by_user)
        ).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        doc_dict = doc.to_dict()
        doc_dict["versions"] = [v.to_dict() for v in doc.versions]
        doc_dict["workflow"] = doc.workflow.to_dict() if doc.workflow else None
        doc_dict["uploaded_by_name"] = doc.uploaded_by_user.display_name if doc.uploaded_by_user else None
        
        response = {
            "status": "success",
            "document": doc_dict
        }
        
        # Include CDM data if requested
        if include_cdm_data:
            cdm_data = None
            # Try source_cdm_data first, then latest version's extracted_data
            if doc.source_cdm_data:
                cdm_data = doc.source_cdm_data
            elif doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    cdm_data = version.extracted_data
            # Also try latest version if current_version_id is not set
            if not cdm_data and doc.versions:
                latest_version = sorted(doc.versions, key=lambda v: v.version_number or 0, reverse=True)[0]
                if latest_version and latest_version.extracted_data:
                    cdm_data = latest_version.extracted_data
            
            response["cdm_data"] = cdm_data
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get document: {str(e)}"}
        )


@router.post("/documents/re-extract")
async def re_extract_document(
    document_id: int = Form(...),
    additional_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Re-extract CDM data from a document by appending new information.
    
    This endpoint allows users to:
    1. Append additional text to the original document
    2. Upload an image file (OCR will extract text)
    3. Upload an audio file (transcription will extract text)
    4. Re-run extraction on the combined text
    5. Create a new document version with updated CDM data
    
    Args:
        document_id: Document ID to re-extract
        additional_text: Optional additional text to append
        file: Optional image or audio file to process
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated CDM data and extraction result
    """
    try:
        from app.chains.extraction_chain import extract_data_smart
        from app.chains.image_extraction_chain import process_multiple_image_files
        from app.models.cdm import ExtractionStatus
        
        # Get original document
        doc = db.query(Document).options(
            joinedload(Document.versions)
        ).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        # Check user access
        if doc.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You do not have access to this document"}
            )
        
        # Get original text from latest version
        latest_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        if not latest_version or not latest_version.original_text:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Original document text not found"}
            )
        
        original_text = latest_version.original_text
        
        # Process additional inputs
        additional_text_parts = []
        
        # Process additional text if provided
        if additional_text and additional_text.strip():
            additional_text_parts.append(f"\n\n--- Additional Information ---\n\n{additional_text.strip()}")
        
        # Process file if provided
        if file:
            filename = file.filename or "file"
            extension = filename.lower().split(".")[-1] if "." in filename else ""
            file_bytes = await file.read()
            
            if extension in ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif"]:
                # Image file - use OCR
                try:
                    from app.chains.image_extraction_chain import process_multiple_image_files
                    ocr_texts = process_multiple_image_files([(file_bytes, filename)])
                    if ocr_texts and ocr_texts[0]:
                        additional_text_parts.append(
                            f"\n\n--- Information from Image: {filename} ---\n\n{ocr_texts[0]}"
                        )
                except Exception as e:
                    logger.error(f"Image OCR failed: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail={"status": "error", "message": f"Image OCR failed: {str(e)}"}
                    )
            elif extension in ["mp3", "wav", "m4a", "ogg", "flac", "webm"]:
                # Audio file - use transcription
                try:
                    from app.chains.audio_transcription_chain import process_audio_file
                    transcription = process_audio_file(
                        audio_bytes=file_bytes,
                        filename=filename
                    )
                    if transcription:
                        additional_text_parts.append(
                            f"\n\n--- Information from Audio: {filename} ---\n\n{transcription}"
                        )
                except Exception as e:
                    logger.error(f"Audio transcription failed: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail={"status": "error", "message": f"Audio transcription failed: {str(e)}"}
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Unsupported file type: {extension}. Supported: images (png, jpg, etc.) or audio (mp3, wav, etc.)"}
                )
        
        if not additional_text_parts:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Please provide either additional_text or a file (image/audio)"}
            )
        
        # Combine original text with additional information
        combined_text = original_text + "\n".join(additional_text_parts)
        
        logger.info(f"Re-extracting document {document_id} with {len(combined_text)} characters (original: {len(original_text)}, additional: {len(combined_text) - len(original_text)})")
        
        # Re-run extraction
        extraction_result = extract_data_smart(text=combined_text)
        
        if extraction_result.status == ExtractionStatus.FAILURE:
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": extraction_result.message or "Extraction failed"}
            )
        
        if not extraction_result.agreement:
            raise HTTPException(
                status_code=422,
                detail={"status": "error", "message": "No CDM data extracted from combined text"}
            )
        
        # Create new document version
        new_version_number = (latest_version.version_number or 0) + 1
        new_version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            extracted_data=extraction_result.agreement.model_dump(mode='json'),
            original_text=combined_text,
            source_filename=latest_version.source_filename,
            extraction_method="re-extraction",
            created_by=current_user.id
        )
        db.add(new_version)
        
        # Update document's current version
        doc.current_version_id = new_version.id
        if extraction_result.agreement.deal_id:
            # Update document metadata if available
            if extraction_result.agreement.parties:
                borrower = next((p for p in extraction_result.agreement.parties if p.role == "Borrower"), None)
                if borrower:
                    doc.borrower_name = borrower.name
                    doc.borrower_lei = borrower.lei
        
        db.commit()
        db.refresh(new_version)
        
        # Audit log
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="document",
            target_id=document_id,
            user_id=current_user.id,
            metadata={"action": "re-extraction", "version": new_version_number}
        )
        
        return {
            "status": "success",
            "message": "Document re-extracted successfully",
            "document_id": document_id,
            "version_id": new_version.id,
            "version_number": new_version_number,
            "cdm_data": extraction_result.agreement.model_dump(mode='json'),
            "extraction_summary": {
                "original_length": len(original_text),
                "additional_length": len(combined_text) - len(original_text),
                "combined_length": len(combined_text),
                "extraction_status": extraction_result.status.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Re-extraction failed for document {document_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Re-extraction failed: {str(e)}"}
        )


@router.get("/documents/{document_id}/cdm-data")
async def get_document_cdm_data(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get CDM data for a specific document.
    
    Args:
        document_id: The document ID.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        CDM data extracted from the document.
    """
    try:
        doc = db.query(Document).options(
            joinedload(Document.versions)
        ).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        # Try source_cdm_data first, then latest version's extracted_data
        cdm_data = None
        if doc.source_cdm_data:
            cdm_data = doc.source_cdm_data
        elif doc.current_version_id:
            version = db.query(DocumentVersion).filter(
                DocumentVersion.id == doc.current_version_id
            ).first()
            if version and version.extracted_data:
                cdm_data = version.extracted_data
        
        if not cdm_data:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "No CDM data found for this document"}
            )
        
        return {
            "status": "success",
            "document_id": document_id,
            "cdm_data": cdm_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CDM data for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get CDM data: {str(e)}"}
        )


class DocumentRetrieveRequest(BaseModel):
    """Request model for document retrieval."""
    query: str = Field(..., description="Query text or CDM data (JSON string) to search for similar documents")
    top_k: int = Field(5, ge=1, le=20, description="Number of similar documents to retrieve (default: 5, max: 20)")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters (e.g., {'borrower_name': 'ACME Corp'})")
    extract_cdm: bool = Field(True, description="Whether to extract CDM data from retrieved documents")


# ============================================================================
# CDM Field Editing API
# ============================================================================

class CdmFieldUpdateRequest(BaseModel):
    """Request model for updating CDM fields."""
    field_path: str = Field(..., description="CDM field path (e.g., 'parties[0].name', 'facilities[0].commitment_amount.amount')")
    value: Any = Field(..., description="New value for the field")
    update_version: bool = Field(False, description="Whether to update the current version's extracted_data (default: updates source_cdm_data)")


@router.patch("/documents/{document_id}/cdm-fields")
async def update_document_cdm_field(
    document_id: int,
    request: CdmFieldUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Update a specific CDM field in a document's CDM data.
    
    Supports nested field paths like:
    - "parties[0].name"
    - "facilities[0].commitment_amount.amount"
    - "parties[role='Borrower'].lei"
    
    Args:
        document_id: Document ID
        request: CdmFieldUpdateRequest with field_path and value
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated CDM data
    """
    from app.generation.field_parser import FieldPathParser
    from app.models.cdm import CreditAgreement
    
    try:
        # Get document
        doc = db.query(Document).options(
            joinedload(Document.versions)
        ).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        # Check authorization
        if doc.uploaded_by != current_user.id and current_user.role not in ["admin", "reviewer"]:
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to edit this document"}
            )
        
        # Get current CDM data
        cdm_data_dict = None
        if request.update_version and doc.current_version_id:
            # Update version's extracted_data
            version = db.query(DocumentVersion).filter(
                DocumentVersion.id == doc.current_version_id
            ).first()
            if version and version.extracted_data:
                cdm_data_dict = version.extracted_data.copy()
            else:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "message": "Document version has no CDM data"}
                )
        else:
            # Update source_cdm_data
            if doc.source_cdm_data:
                cdm_data_dict = doc.source_cdm_data.copy()
            elif doc.current_version_id:
                # Fallback to version's extracted_data
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    cdm_data_dict = version.extracted_data.copy()
                else:
                    raise HTTPException(
                        status_code=404,
                        detail={"status": "error", "message": "Document has no CDM data"}
                    )
            else:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "message": "Document has no CDM data"}
                )
        
        # Parse CDM data to CreditAgreement for validation
        try:
            cdm_agreement = CreditAgreement(**cdm_data_dict)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Invalid CDM data structure: {str(e)}"}
            )
        
        # Update field in dict representation (simpler and more reliable)
        # Convert to dict for easier manipulation
        cdm_dict = cdm_data_dict.copy()
        
        try:
            # Parse the field path
            parser = FieldPathParser()
            segments = parser.parse_field_path(request.field_path)
            
            # Navigate to the parent in the dict
            current = cdm_dict
            for i, segment in enumerate(segments[:-1]):
                if isinstance(segment, str):
                    if segment not in current:
                        raise ValueError(f"Field '{segment}' not found in path")
                    current = current[segment]
                elif isinstance(segment, dict):
                    if "filter" in segment:
                        # Filter list by attribute
                        filter_key = list(segment["filter"].keys())[0]
                        filter_value = segment["filter"][filter_key]
                        if isinstance(current, list):
                            found = next(
                                (item for item in current if isinstance(item, dict) and item.get(filter_key) == filter_value),
                                None
                            )
                            if found is None:
                                raise ValueError(f"No item found matching filter {filter_key}={filter_value}")
                            current = found
                        else:
                            raise ValueError(f"Cannot filter non-list type")
                    elif "index" in segment:
                        # Array index
                        if isinstance(current, list):
                            if segment["index"] >= len(current):
                                raise ValueError(f"Index {segment['index']} out of range")
                            current = current[segment["index"]]
                        else:
                            raise ValueError(f"Cannot index into non-list type")
            
            # Set the value on the last segment
            last_segment = segments[-1]
            if isinstance(last_segment, str):
                current[last_segment] = request.value
            else:
                raise ValueError("Last segment must be a field name, not a filter or index")
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Failed to update field: {str(e)}"}
            )
        
        # Validate updated CDM data
        try:
            # Re-validate the entire structure
            validated_agreement = CreditAgreement(**cdm_dict)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Updated CDM data is invalid: {str(e)}"}
            )
        
        # Convert back to dict and update document
        updated_cdm_dict = validated_agreement.model_dump(mode='json')
        
        if request.update_version and doc.current_version_id:
            # Update version's extracted_data
            version.extracted_data = updated_cdm_dict
            db.commit()
            db.refresh(version)
        else:
            # Update source_cdm_data
            doc.source_cdm_data = updated_cdm_dict
            db.commit()
            db.refresh(doc)
        
        # Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="document",
            target_id=document_id,
            user_id=current_user.id,
            metadata={
                "field_path": request.field_path,
                "action": "cdm_field_update"
            }
        )
        
        logger.info(f"Updated CDM field {request.field_path} in document {document_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"Field {request.field_path} updated successfully",
            "cdm_data": updated_cdm_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating CDM field in document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to update CDM field: {str(e)}"}
        )


@router.post("/documents/retrieve")
async def retrieve_similar_documents(
    request: DocumentRetrieveRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Retrieve similar documents based on query text or CDM data.
    
    This endpoint:
    1. Searches for similar documents using ChromaDB vector similarity
    2. Fetches full document data from the database
    3. Returns similar documents with their CDM data
    
    Args:
        request: DocumentRetrieveRequest with query, top_k, and optional filters
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        List of similar documents with CDM data, similarity scores, and metadata
    """
    from app.chains.document_retrieval_chain import retrieve_similar_documents as retrieve_docs
    from app.models.cdm import CreditAgreement
    
    try:
        # Parse query - check if it's JSON (CDM data) or plain text
        query = request.query.strip()
        query_data = None
        
        # Try to parse as JSON (CDM data)
        try:
            query_data = json.loads(query)
            if isinstance(query_data, dict):
                query = query_data  # Use dict for CDM-based search
        except (json.JSONDecodeError, ValueError):
            # Not JSON, use as plain text query
            pass
        
        logger.info(f"Retrieving similar documents for query: {query[:100] if isinstance(query, str) else 'CDM data'}...")
        
        # Retrieve similar documents from ChromaDB
        try:
            similar_docs = retrieve_docs(
                query=query,
                top_k=request.top_k,
                filter_metadata=request.filter_metadata,
            )
        except ImportError as e:
            logger.error(f"ChromaDB not available: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "message": "Document retrieval service is not available. ChromaDB is not installed."
                }
            )
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Document retrieval failed: {str(e)}"
                }
            )
        
        if not similar_docs:
            return {
                "status": "success",
                "query": query if isinstance(query, str) else "CDM data",
                "results_count": 0,
                "documents": []
            }
        
        # Fetch full document data from database
        results = []
        for doc_result in similar_docs:
            document_id = doc_result["document_id"]
            
            try:
                # Fetch document from database
                doc = db.query(Document).options(
                    joinedload(Document.versions),
                    joinedload(Document.workflow),
                    joinedload(Document.uploaded_by_user)
                ).filter(Document.id == document_id).first()
                
                if not doc:
                    logger.warning(f"Document {document_id} not found in database (may have been deleted)")
                    continue
                
                # Get CDM data from document
                cdm_data = None
                if request.extract_cdm:
                    # Try to get CDM data from source_cdm_data or latest version
                    if doc.source_cdm_data:
                        cdm_data = doc.source_cdm_data
                    elif doc.current_version_id:
                        version = db.query(DocumentVersion).filter(
                            DocumentVersion.id == doc.current_version_id
                        ).first()
                        if version and version.extracted_data:
                            cdm_data = version.extracted_data
                
                # Build result
                result_item = {
                    "document_id": document_id,
                    "similarity_score": doc_result["similarity_score"],
                    "distance": doc_result["distance"],
                    "document": doc.to_dict(),
                    "cdm_data": cdm_data,
                }
                
                # Add workflow info if available
                if doc.workflow:
                    result_item["workflow"] = doc.workflow.to_dict()
                
                # Add version info
                if doc.versions:
                    result_item["latest_version"] = doc.versions[0].to_dict() if doc.versions else None
                
                results.append(result_item)
                
            except Exception as e:
                logger.error(f"Error fetching document {document_id}: {e}")
                # Continue with other documents even if one fails
                continue
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="document_retrieval",
                    user_id=current_user.id,
                    metadata={
                        "query": query[:200] if isinstance(query, str) else "CDM data",
                        "results_count": len(results),
                        "top_k": request.top_k,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log document retrieval audit: {e}")
        
        return {
            "status": "success",
            "query": query if isinstance(query, str) else "CDM data",
            "results_count": len(results),
            "documents": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during document retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to retrieve documents: {str(e)}"}
        )


class MultimodalFusionRequest(BaseModel):
    """Request model for multimodal CDM fusion."""
    audio_cdm: Optional[Dict[str, Any]] = Field(None, description="Optional CDM data from audio transcription")
    image_cdm: Optional[Dict[str, Any]] = Field(None, description="Optional CDM data from image OCR")
    document_cdm: Optional[Dict[str, Any]] = Field(None, description="Optional CDM data from document retrieval")
    text_cdm: Optional[Dict[str, Any]] = Field(None, description="Optional CDM data from text extraction")
    audio_text: Optional[str] = Field(None, description="Optional raw transcription text from audio")
    image_text: Optional[str] = Field(None, description="Optional raw OCR text from images")
    document_text: Optional[str] = Field(None, description="Optional raw text from retrieved document")
    text_input: Optional[str] = Field(None, description="Required text input (if no text_cdm provided)")
    use_llm_fusion: bool = Field(True, description="Whether to use LLM for complex merging (default: True)")


@router.post("/multimodal/fuse")
async def fuse_multimodal_cdm(
    request: MultimodalFusionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Fuse CDM data from multiple sources into a unified CDM structure.
    
    This endpoint:
    1. Accepts CDM data from multiple sources (audio, image, document, text)
    2. Prepends optional inputs (audio, image) to required inputs (document, text)
    3. Tracks source for each field
    4. Detects conflicts between sources
    5. Uses deterministic fallbacks for simple cases
    6. Uses LLM for complex merging when conflicts exist
    
    Args:
        request: MultimodalFusionRequest with CDM data and/or text from various sources
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Fused CDM data with source tracking, conflicts, and fusion method
    """
    from app.chains.multimodal_fusion_chain import fuse_multimodal_inputs
    
    try:
        # Validate that at least one source is provided
        has_cdm = any([
            request.audio_cdm,
            request.image_cdm,
            request.document_cdm,
            request.text_cdm,
        ])
        has_text = any([
            request.audio_text,
            request.image_text,
            request.document_text,
            request.text_input,
        ])
        
        if not has_cdm and not has_text:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": "At least one CDM data source or text input must be provided"
                }
            )
        
        logger.info(
            f"Fusing multimodal inputs: "
            f"audio_cdm={request.audio_cdm is not None}, "
            f"image_cdm={request.image_cdm is not None}, "
            f"document_cdm={request.document_cdm is not None}, "
            f"text_cdm={request.text_cdm is not None}, "
            f"text_input={request.text_input is not None}"
        )
        
        # Perform fusion
        try:
            fusion_result = fuse_multimodal_inputs(
                audio_cdm=request.audio_cdm,
                image_cdm=request.image_cdm,
                document_cdm=request.document_cdm,
                text_cdm=request.text_cdm,
                audio_text=request.audio_text,
                image_text=request.image_text,
                document_text=request.document_text,
                text_input=request.text_input,
                use_llm_fusion=request.use_llm_fusion,
            )
        except ValueError as e:
            logger.error(f"Fusion failed: {e}")
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": f"Fusion failed: {str(e)}"
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error during fusion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Fusion failed with unexpected error: {str(e)}"
                }
            )
        
        # Prepare response
        response_data = {
            "status": "success",
            "agreement": fusion_result.agreement.model_dump(),
            "source_tracking": {
                field: src.to_dict()
                for field, src in fusion_result.source_tracking.items()
            },
            "conflicts": [c.to_dict() for c in fusion_result.conflicts],
            "fusion_method": fusion_result.fusion_method,
            "conflicts_count": len(fusion_result.conflicts),
        }
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="multimodal_fusion",
                    user_id=current_user.id,
                    metadata={
                        "sources_count": sum([
                            1 if request.audio_cdm else 0,
                            1 if request.image_cdm else 0,
                            1 if request.document_cdm else 0,
                            1 if request.text_cdm else 0,
                        ]),
                        "fusion_method": fusion_result.fusion_method,
                        "conflicts_count": len(fusion_result.conflicts),
                        "use_llm_fusion": request.use_llm_fusion,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log multimodal fusion audit: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during multimodal fusion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to fuse multimodal inputs: {str(e)}"}
        )


class ChatbotChatRequest(BaseModel):
    """Request model for chatbot chat."""
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Previous conversation messages [{\"role\": \"user\"|\"assistant\", \"content\": \"...\"}]"
    )
    cdm_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Current CDM data context"
    )
    use_kb: bool = Field(True, description="Whether to use knowledge base retrieval (default: True)")
    deal_id: Optional[int] = Field(None, description="Optional deal ID to load deal context")


@router.post("/chatbot/chat")
async def chatbot_chat(
    request: ChatbotChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Chat with the decision support chatbot.
    
    This endpoint provides an AI chatbot interface for:
    - Answering questions about LMA templates and CDM schema
    - Providing guidance on template selection
    - Helping with field filling
    - General document generation assistance
    
    Uses RAG (Retrieval Augmented Generation) with ChromaDB knowledge base.
    
    Args:
        request: ChatbotChatRequest with message, conversation history, and CDM context
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Chatbot response with answer, sources, and metadata
    """
    from app.chains.decision_support_chain import DecisionSupportChatbot
    
    try:
        # Initialize chatbot with database session for deal context loading
        chatbot = DecisionSupportChatbot(db_session=db)
        
        logger.info(
            f"Chatbot chat request: message length={len(request.message)}, "
            f"has_cdm_context={request.cdm_context is not None}, "
            f"deal_id={request.deal_id}, user_id={current_user.id if current_user else None}"
        )
        
        # Call chatbot
        try:
            result = chatbot.chat(
                message=request.message,
                conversation_history=request.conversation_history,
                cdm_context=request.cdm_context,
                use_kb=request.use_kb,
                deal_id=request.deal_id,
                user_id=current_user.id if current_user else None,
            )
        except ImportError as e:
            logger.error(f"ChromaDB not available: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "message": "Chatbot service is not available. ChromaDB is not installed."
                }
            )
        except Exception as e:
            logger.error(f"Chatbot chat failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Chatbot failed: {str(e)}"
                }
            )
        
        # Prepare response
        response_data = {
            "status": "success",
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "context_used": result.get("context_used", False),
        }
        
        if "error" in result:
            response_data["error"] = result["error"]
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="chatbot_chat",
                    user_id=current_user.id,
                    metadata={
                        "message_length": len(request.message),
                        "has_cdm_context": request.cdm_context is not None,
                        "has_conversation_history": request.conversation_history is not None,
                        "use_kb": request.use_kb,
                        "context_used": result.get("context_used", False),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log chatbot chat audit: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during chatbot chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to process chat message: {str(e)}"}
        )


class ChatbotSuggestTemplatesRequest(BaseModel):
    """Request model for template suggestions."""
    cdm_data: Dict[str, Any] = Field(..., description="CDM data to analyze for template suggestions")
    category_filter: Optional[str] = Field(None, description="Optional category filter for templates")
    deal_id: Optional[int] = Field(None, description="Optional deal ID to get template recommendations based on deal type")


@router.post("/chatbot/suggest-templates")
async def chatbot_suggest_templates(
    request: ChatbotSuggestTemplatesRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Get template suggestions based on CDM data.
    
    This endpoint uses AI to analyze CDM data and suggest appropriate LMA templates.
    It considers:
    - Agreement type and structure
    - Governing law requirements
    - Sustainability-linked loan indicators
    - Complexity and specific clauses needed
    
    Args:
        request: ChatbotSuggestTemplatesRequest with CDM data and optional category filter
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Template suggestions with reasoning and CDM analysis
    """
    from app.chains.decision_support_chain import DecisionSupportChatbot
    from app.templates.registry import TemplateRegistry
    
    try:
        # Get available templates from database
        available_templates = []
        try:
            templates = TemplateRegistry.list_templates(
                db=db,
                category=request.category_filter
            )
            available_templates = [t.to_dict() for t in templates]
        except Exception as e:
            logger.warning(f"Failed to load templates from database: {e}")
            # Continue without template list - chatbot can still provide suggestions
        
        # Initialize chatbot with database session for deal context
        chatbot = DecisionSupportChatbot(db_session=db)
        
        logger.info(
            f"Template suggestion request: has_cdm_data={bool(request.cdm_data)}, "
            f"templates_count={len(available_templates)}, deal_id={request.deal_id}"
        )
        
        # Get suggestions
        try:
            result = chatbot.suggest_template(
                cdm_data=request.cdm_data,
                available_templates=available_templates if available_templates else None,
                deal_id=request.deal_id,
            )
        except ImportError as e:
            logger.error(f"ChromaDB not available: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "message": "Template suggestion service is not available. ChromaDB is not installed."
                }
            )
        except Exception as e:
            logger.error(f"Template suggestion failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Template suggestion failed: {str(e)}"
                }
            )
        
        # Prepare response
        response_data = {
            "status": "success",
            "suggestions": result.get("suggestions", []),
            "reasoning": result.get("reasoning", ""),
            "cdm_analysis": result.get("cdm_analysis", {}),
        }
        
        if "error" in result:
            response_data["error"] = result["error"]
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.CREATE,
                    target_type="chatbot_template_suggestion",
                    user_id=current_user.id,
                    metadata={
                        "suggestions_count": len(result.get("suggestions", [])),
                        "has_parties": result.get("cdm_analysis", {}).get("has_parties", False),
                        "has_facilities": result.get("cdm_analysis", {}).get("has_facilities", False),
                        "is_sustainability_linked": result.get("cdm_analysis", {}).get("is_sustainability_linked", False),
                        "category_filter": request.category_filter,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log template suggestion audit: {e}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during template suggestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to suggest templates: {str(e)}"}
        )


class ChatbotFillFieldsRequest(BaseModel):
    """Request model for filling missing CDM fields."""
    cdm_data: Dict[str, Any] = Field(..., description="Current CDM data (may be incomplete)")
    required_fields: List[str] = Field(..., description="List of required field paths (e.g., [\"parties\", \"facilities[0].facility_name\"])")
    conversation_context: Optional[str] = Field(None, description="Optional conversation context about what user is trying to do")
    deal_id: Optional[int] = Field(None, description="Optional deal ID to provide deal context for field filling")


@router.post("/chatbot/fill-fields")
async def chatbot_fill_fields(
    request: ChatbotFillFieldsRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Help fill missing CDM fields interactively.
    
    This endpoint uses AI to:
    - Identify missing required fields in CDM data
    - Provide guidance on what each field represents
    - Ask clarifying questions
    - Suggest values based on existing data
    - Provide example values for reference
    
    Args:
        request: ChatbotFillFieldsRequest with CDM data, required fields, and optional context
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        Field filling assistance with suggestions, questions, and guidance
    """
    from app.chains.decision_support_chain import DecisionSupportChatbot
    
    # Validate required fields
    if not request.required_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "required_fields cannot be empty"
            }
        )
    
    # Initialize chatbot with database session for deal context
    chatbot = DecisionSupportChatbot(db_session=db)
    
    logger.info(
        f"Field filling request: required_fields_count={len(request.required_fields)}, "
        f"has_cdm_data={bool(request.cdm_data)}, has_context={bool(request.conversation_context)}, "
        f"deal_id={request.deal_id}"
    )
    
    # Get field filling assistance
    try:
        result = chatbot.fill_missing_fields(
            cdm_data=request.cdm_data,
            required_fields=request.required_fields,
            conversation_context=request.conversation_context,
            deal_id=request.deal_id,
        )
    except ImportError as e:
        logger.error(f"ChromaDB not available: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Field filling service is not available. ChromaDB is not installed."
            }
        )
    except Exception as e:
        logger.error(f"Field filling failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Field filling failed: {str(e)}"
            }
        )
    
    # Prepare response
    # Frontend expects field_guidance.suggested_values format
    suggestions = result.get("suggestions", {})
    response_data = {
        "status": "success",
        "all_fields_present": result.get("all_fields_present", False),
        "missing_fields": result.get("missing_fields", []),
        "suggestions": suggestions,
        "guidance": result.get("guidance", ""),
        "questions": result.get("questions", []),
        # Add field_guidance format for frontend compatibility
        "field_guidance": {
            "suggested_values": suggestions,
            "guidance": result.get("guidance", ""),
            "questions": result.get("questions", [])
        }
    }
    
    if "error" in result:
        response_data["error"] = result["error"]
    
    # If all fields are present, include the filled data
    if result.get("all_fields_present"):
        response_data["filled_data"] = result.get("filled_data", request.cdm_data)
    
    # Audit log (if user is authenticated)
    if current_user:
        try:
            log_audit_action(
                db=db,
                action=AuditAction.CREATE,
                target_type="chatbot_fill_fields",
                user_id=current_user.id,
                metadata={
                    "required_fields_count": len(request.required_fields),
                    "missing_fields_count": len(result.get("missing_fields", [])),
                    "all_fields_present": result.get("all_fields_present", False),
                    "has_conversation_context": bool(request.conversation_context),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log field filling audit: {e}")
    
    return response_data


@router.get("/documents/{document_id}/versions")
async def list_document_versions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all versions of a document.
    
    Args:
        document_id: The document ID.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        List of document versions.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).all()
        
        return {
            "status": "success",
            "document_id": document_id,
            "current_version_id": doc.current_version_id,
            "versions": [v.to_dict() for v in versions]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing versions for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list versions: {str(e)}"}
        )


@router.get("/documents/{document_id}/versions/{version_id}")
async def get_document_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific version of a document.
    
    Args:
        document_id: The document ID.
        version_id: The version ID.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        The document version with full extracted data.
    """
    try:
        version = db.query(DocumentVersion).filter(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id
        ).first()
        
        if not version:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Version not found"}
            )
        
        return {
            "status": "success",
            "version": version.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version {version_id} for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get version: {str(e)}"}
        )


@router.post("/documents/{document_id}/versions")
async def create_document_version(
    document_id: int,
    version_request: CreateVersionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new version of a document.
    
    Args:
        document_id: The document ID.
        version_request: CreateVersionRequest containing the new version data.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The created version.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        latest_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            extracted_data=version_request.agreement_data,
            original_text=version_request.original_text,
            source_filename=version_request.source_filename,
            extraction_method=version_request.extraction_method,
            created_by=current_user.id,
        )
        db.add(version)
        db.flush()
        
        metadata = extract_document_metadata(version_request.agreement_data)
        doc.borrower_name = metadata.get("borrower_name", doc.borrower_name)
        doc.borrower_lei = metadata.get("borrower_lei", doc.borrower_lei)
        doc.governing_law = metadata.get("governing_law", doc.governing_law)
        doc.total_commitment = metadata.get("total_commitment", doc.total_commitment)
        doc.currency = metadata.get("currency", doc.currency)
        doc.agreement_date = metadata.get("agreement_date", doc.agreement_date)
        doc.sustainability_linked = metadata.get("sustainability_linked", doc.sustainability_linked)
        if metadata.get("esg_metadata"):
            doc.esg_metadata = metadata["esg_metadata"]
        doc.current_version_id = version.id
        
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="document",
            target_id=document_id,
            user_id=current_user.id,
            metadata={"version_number": new_version_number, "version_id": version.id},
            request=request
        )
        
        db.commit()
        db.refresh(version)
        
        logger.info(f"Created version {version.id} (v{new_version_number}) for document {document_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"Version {new_version_number} created successfully",
            "version": version.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating version for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create version: {str(e)}"}
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Delete a document and all its versions.
    
    Args:
        document_id: The document ID.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        Success message.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        if doc.uploaded_by != current_user.id and current_user.role not in ["admin", "reviewer"]:
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to delete this document"}
            )
        
        doc_title = doc.title
        
        log_audit_action(
            db=db,
            action=AuditAction.DELETE,
            target_type="document",
            target_id=document_id,
            user_id=current_user.id,
            metadata={"title": doc_title},
            request=request
        )
        
        db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).delete()
        db.query(Workflow).filter(Workflow.document_id == document_id).delete()
        db.delete(doc)
        db.commit()
        
        logger.info(f"Deleted document {document_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to delete document: {str(e)}"}
        )


@router.get("/analytics/portfolio")
async def get_portfolio_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get portfolio-level analytics aggregating all documents.
    
    Returns:
        Portfolio analytics including total commitments, ESG breakdown,
        workflow distribution, and maturity timeline.
    """
    from sqlalchemy import func
    from collections import defaultdict
    
    try:
        total_documents = db.query(Document).count()
        
        commitment_result = db.query(
            func.sum(Document.total_commitment).label("total"),
            Document.currency
        ).filter(
            Document.total_commitment.isnot(None)
        ).group_by(Document.currency).all()
        
        commitments_by_currency = {}
        total_commitment_usd = Decimal("0")
        for row in commitment_result:
            if row.currency:
                amount = float(row.total) if row.total else 0
                commitments_by_currency[row.currency] = amount
                if row.currency == "USD":
                    total_commitment_usd += Decimal(str(amount))
        
        sustainability_count = db.query(Document).filter(
            Document.sustainability_linked == True
        ).count()
        sustainability_percentage = (sustainability_count / total_documents * 100) if total_documents > 0 else 0
        
        workflow_states = db.query(
            Workflow.state,
            func.count(Workflow.id).label("count")
        ).group_by(Workflow.state).all()
        
        workflow_distribution = {row.state: row.count for row in workflow_states}
        
        maturity_data = []
        documents_with_dates = db.query(
            Document.id,
            Document.title,
            Document.borrower_name,
            Document.agreement_date,
            Document.total_commitment,
            Document.currency,
            Document.sustainability_linked
        ).filter(
            Document.agreement_date.isnot(None)
        ).order_by(Document.agreement_date.desc()).limit(50).all()
        
        for doc in documents_with_dates:
            maturity_data.append({
                "id": doc.id,
                "title": doc.title,
                "borrower_name": doc.borrower_name,
                "agreement_date": doc.agreement_date.isoformat() if doc.agreement_date else None,
                "total_commitment": float(doc.total_commitment) if doc.total_commitment else None,
                "currency": doc.currency,
                "sustainability_linked": doc.sustainability_linked
            })
        
        esg_breakdown = {
            "sustainability_linked": sustainability_count,
            "non_sustainability": total_documents - sustainability_count,
            "esg_score_distribution": {}
        }
        
        docs_with_esg = db.query(Document).filter(
            Document.esg_metadata.isnot(None)
        ).all()
        
        for doc in docs_with_esg:
            if doc.esg_metadata:
                kpis = doc.esg_metadata.get("kpis", [])
                for kpi in kpis:
                    category = kpi.get("category", "Other")
                    if category not in esg_breakdown["esg_score_distribution"]:
                        esg_breakdown["esg_score_distribution"][category] = 0
                    esg_breakdown["esg_score_distribution"][category] += 1
        
        recent_activity = db.query(Document).options(
            joinedload(Document.workflow)
        ).order_by(Document.updated_at.desc()).limit(5).all()
        
        recent_docs = []
        for doc in recent_activity:
            recent_docs.append({
                "id": doc.id,
                "title": doc.title,
                "borrower_name": doc.borrower_name,
                "workflow_state": doc.workflow.state if doc.workflow else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            })
        
        return {
            "status": "success",
            "analytics": {
                "summary": {
                    "total_documents": total_documents,
                    "total_commitment_usd": float(total_commitment_usd),
                    "commitments_by_currency": commitments_by_currency,
                    "sustainability_linked_count": sustainability_count,
                    "sustainability_percentage": round(sustainability_percentage, 1)
                },
                "workflow_distribution": workflow_distribution,
                "esg_breakdown": esg_breakdown,
                "maturity_timeline": maturity_data,
                "recent_activity": recent_docs
            }
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to fetch analytics: {str(e)}"}
        )


@router.get("/analytics/dashboard")
async def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get enhanced dashboard analytics with activity feed and key metrics.
    
    Returns:
        Dashboard analytics including key metrics, activity feed from audit logs,
        pending approvals, and trend indicators.
    """
    from sqlalchemy import func
    from datetime import timedelta
    
    try:
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        total_documents = db.query(Document).count()
        
        docs_this_week = db.query(Document).filter(
            Document.created_at >= week_ago
        ).count()
        
        docs_last_week = db.query(Document).filter(
            Document.created_at >= two_weeks_ago,
            Document.created_at < week_ago
        ).count()
        
        pending_review = db.query(Workflow).filter(
            Workflow.state == WorkflowState.UNDER_REVIEW.value
        ).count()
        
        approved_this_week = db.query(Workflow).filter(
            Workflow.state == WorkflowState.APPROVED.value,
            Workflow.updated_at >= week_ago
        ).count()
        
        published_count = db.query(Workflow).filter(
            Workflow.state == WorkflowState.PUBLISHED.value
        ).count()
        
        draft_count = db.query(Workflow).filter(
            Workflow.state == WorkflowState.DRAFT.value
        ).count()
        
        commitment_result = db.query(
            func.sum(Document.total_commitment)
        ).filter(
            Document.currency == "USD",
            Document.total_commitment.isnot(None)
        ).scalar()
        total_commitment_usd = float(commitment_result) if commitment_result else 0
        
        sustainability_count = db.query(Document).filter(
            Document.sustainability_linked == True
        ).count()
        sustainability_percentage = (sustainability_count / total_documents * 100) if total_documents > 0 else 0
        
        activity_logs = db.query(AuditLog).options(
            joinedload(AuditLog.user)
        ).order_by(AuditLog.occurred_at.desc()).limit(15).all()
        
        activity_feed = []
        for log in activity_logs:
            action_descriptions = {
                "create": "created",
                "update": "updated",
                "delete": "deleted",
                "approve": "approved",
                "reject": "rejected",
                "publish": "published",
                "export": "exported",
                "submit_review": "submitted for review",
                "login": "logged in",
                "logout": "logged out",
                "broadcast": "broadcast message"
            }
            
            action_text = action_descriptions.get(log.action, log.action)
            target_name = None
            if log.action_metadata:
                target_name = log.action_metadata.get("title") or log.action_metadata.get("name")
            
            activity_feed.append({
                "id": log.id,
                "action": log.action,
                "action_text": action_text,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "target_name": target_name,
                "user_name": log.user.display_name if log.user else "System",
                "user_id": log.user_id,
                "occurred_at": log.occurred_at.isoformat() if log.occurred_at else None,
                "metadata": log.action_metadata
            })
        
        docs_trend = 0
        if docs_last_week > 0:
            docs_trend = round(((docs_this_week - docs_last_week) / docs_last_week) * 100, 1)
        elif docs_this_week > 0:
            docs_trend = 100.0
        
        return {
            "status": "success",
            "dashboard": {
                "key_metrics": {
                    "total_documents": total_documents,
                    "docs_this_week": docs_this_week,
                    "docs_trend_percent": docs_trend,
                    "pending_review": pending_review,
                    "approved_this_week": approved_this_week,
                    "published_count": published_count,
                    "draft_count": draft_count,
                    "total_commitment_usd": total_commitment_usd,
                    "sustainability_count": sustainability_count,
                    "sustainability_percentage": round(sustainability_percentage, 1)
                },
                "activity_feed": activity_feed,
                "last_updated": now.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to fetch dashboard analytics: {str(e)}"}
        )


@router.get("/analytics/template-metrics")
async def get_template_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get template usage metrics for dashboard.
    
    Returns:
        Template metrics including:
        - Total generations
        - Success rate
        - Average generation time
        - Most used templates
    """
    from sqlalchemy import func
    from app.db.models import GeneratedDocument, GeneratedDocumentStatus
    
    try:
        # Total generations
        total_generations = db.query(GeneratedDocument).count()
        
        # Success rate (approved or executed / total)
        successful_generations = db.query(GeneratedDocument).filter(
            GeneratedDocument.status.in_([
                GeneratedDocumentStatus.APPROVED.value,
                GeneratedDocumentStatus.EXECUTED.value
            ])
        ).count()
        success_rate = (successful_generations / total_generations * 100) if total_generations > 0 else 0
        
        # Average generation time (if available in metadata)
        # For now, we'll use a placeholder - this would need to be tracked during generation
        avg_generation_time = 0.0
        if total_generations > 0:
            # Calculate from created_at timestamps if we track start/end times
            # For now, return a default estimate
            avg_generation_time = 45.0  # seconds
        
        # Most used templates
        template_usage = db.query(
            GeneratedDocument.template_id,
            func.count(GeneratedDocument.id).label('usage_count')
        ).filter(
            GeneratedDocument.template_id.isnot(None)
        ).group_by(GeneratedDocument.template_id).order_by(
            func.count(GeneratedDocument.id).desc()
        ).limit(5).all()
        
        most_used = []
        for template_id, usage_count in template_usage:
            template = db.query(LMATemplate).filter(LMATemplate.id == template_id).first()
            if template:
                most_used.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "template_category": template.category,
                    "usage_count": usage_count
                })
        
        return {
            "status": "success",
            "template_metrics": {
                "total_generations": total_generations,
                "success_rate": round(success_rate, 1),
                "average_generation_time_seconds": round(avg_generation_time, 1),
                "most_used_templates": most_used
            }
        }
    except Exception as e:
        logger.error(f"Error fetching template metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to fetch template metrics: {str(e)}"}
        )


@router.get("/analytics/charts")
async def get_chart_analytics(
    range: str = Query("7d", description="Date range: 7d, 30d, 90d, or all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get time-series chart data for dashboard visualizations.
    
    Args:
        range: Date range filter - 7d (week), 30d (month), 90d (quarter), or all
        
    Returns:
        Chart data including document trends over time and workflow pipeline data.
    """
    from sqlalchemy import func, cast, Date
    from datetime import timedelta
    from collections import defaultdict
    
    try:
        now = datetime.utcnow()
        
        range_days = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "all": 365
        }
        days = range_days.get(range, 7)
        start_date = now - timedelta(days=days)
        
        if days <= 7:
            group_format = "%Y-%m-%d"
            date_labels = [(now - timedelta(days=i)).strftime("%b %d") for i in range(days, -1, -1)]
        elif days <= 30:
            group_format = "%Y-%m-%d"
            date_labels = [(now - timedelta(days=i)).strftime("%b %d") for i in range(days, -1, -1)]
        else:
            group_format = "%Y-%U"
            weeks = days // 7
            date_labels = [(now - timedelta(weeks=i)).strftime("Week %U") for i in range(weeks, -1, -1)]
        
        docs_by_date = defaultdict(int)
        
        documents = db.query(
            Document.created_at
        ).filter(
            Document.created_at >= start_date
        ).all()
        
        for doc in documents:
            if doc.created_at:
                if days <= 30:
                    date_key = doc.created_at.strftime("%b %d")
                else:
                    date_key = doc.created_at.strftime("Week %U")
                docs_by_date[date_key] += 1
        
        document_trend = []
        cumulative = 0
        for label in date_labels:
            count = docs_by_date.get(label, 0)
            cumulative += count
            document_trend.append({
                "date": label,
                "documents": count,
                "cumulative": cumulative
            })
        
        workflow_states = db.query(
            Workflow.state,
            func.count(Workflow.id).label('count')
        ).group_by(Workflow.state).all()
        
        workflow_colors = {
            "draft": "#64748b",
            "under_review": "#f59e0b",
            "approved": "#10b981",
            "published": "#3b82f6",
            "archived": "#6b7280"
        }
        
        workflow_pipeline = []
        for state, count in workflow_states:
            workflow_pipeline.append({
                "state": state,
                "label": state.replace("_", " ").title(),
                "count": count,
                "color": workflow_colors.get(state, "#64748b")
            })
        
        commitments_by_date = defaultdict(float)
        
        commitment_docs = db.query(
            Document.created_at,
            Document.total_commitment,
            Document.currency
        ).filter(
            Document.created_at >= start_date,
            Document.total_commitment.isnot(None)
        ).all()
        
        for doc in commitment_docs:
            if doc.created_at and doc.total_commitment:
                if days <= 30:
                    date_key = doc.created_at.strftime("%b %d")
                else:
                    date_key = doc.created_at.strftime("Week %U")
                amount = float(doc.total_commitment)
                commitments_by_date[date_key] += amount
        
        commitment_trend = []
        cumulative_commitment = 0
        for label in date_labels:
            amount = commitments_by_date.get(label, 0)
            cumulative_commitment += amount
            commitment_trend.append({
                "date": label,
                "amount": round(amount, 2),
                "cumulative": round(cumulative_commitment, 2)
            })
        
        action_counts = db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.occurred_at >= start_date
        ).group_by(AuditLog.action).all()
        
        activity_by_type = []
        for action, count in action_counts:
            activity_by_type.append({
                "action": action,
                "label": action.replace("_", " ").title(),
                "count": count
            })
        
        return {
            "status": "success",
            "charts": {
                "date_range": range,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
                "document_trend": document_trend,
                "workflow_pipeline": workflow_pipeline,
                "commitment_trend": commitment_trend,
                "activity_by_type": activity_by_type
            }
        }
    except Exception as e:
        logger.error(f"Error fetching chart analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to fetch chart analytics: {str(e)}"}
        )


class WorkflowTransitionRequest(BaseModel):
    """Request model for workflow transitions."""
    comment: Optional[str] = Field(None, description="Optional comment for the transition")
    assigned_to: Optional[int] = Field(None, description="User ID to assign the review to")
    priority: Optional[str] = Field(None, description="Priority level: low, normal, high, urgent")
    due_date: Optional[str] = Field(None, description="Due date for review in ISO format")


class WorkflowRejectRequest(BaseModel):
    """Request model for rejecting a document."""
    reason: str = Field(..., description="Reason for rejection")
    comment: Optional[str] = Field(None, description="Additional comment")


def check_workflow_permission(user: User, required_roles: List[str]) -> bool:
    """Check if user has one of the required roles."""
    return user.role in required_roles


def get_workflow_or_404(db: Session, document_id: int) -> Workflow:
    """Get workflow for a document or raise 404."""
    workflow = db.query(Workflow).filter(Workflow.document_id == document_id).first()
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "Workflow not found for this document"}
        )
    return workflow


def _get_transaction_id_from_document(db: Session, document_id: int) -> Optional[str]:
    """
    Extract transaction ID (deal_id or loan_identification_number) from document.
    
    Checks source_cdm_data first, then falls back to DocumentVersion.extracted_data.
    
    Args:
        db: Database session
        document_id: Document ID
        
    Returns:
        Transaction ID string or None if not found
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None
    
    # Try source_cdm_data first
    if doc.source_cdm_data:
        if doc.source_cdm_data.get("deal_id"):
            return doc.source_cdm_data.get("deal_id")
        if doc.source_cdm_data.get("loan_identification_number"):
            return doc.source_cdm_data.get("loan_identification_number")
    
    # Fallback to latest version's extracted_data
    if doc.current_version_id:
        version = db.query(DocumentVersion).filter(
            DocumentVersion.id == doc.current_version_id
        ).first()
        if version and version.extracted_data:
            if version.extracted_data.get("deal_id"):
                return version.extracted_data.get("deal_id")
            if version.extracted_data.get("loan_identification_number"):
                return version.extracted_data.get("loan_identification_number")
    
    return None


@router.post("/documents/{document_id}/workflow/submit")
async def submit_for_review(
    document_id: int,
    request: Request,
    transition_request: WorkflowTransitionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Submit a document for review.
    
    Transitions the workflow from Draft to Under Review.
    Required roles: analyst, reviewer, admin
    """
    try:
        if not check_workflow_permission(current_user, ["analyst", "reviewer", "admin"]):
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to submit documents for review"}
            )
        
        workflow = get_workflow_or_404(db, document_id)
        
        if workflow.state != WorkflowState.DRAFT.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Cannot submit for review: document is in '{workflow.state}' state, must be 'draft'"}
            )
        
        previous_state = workflow.state
        workflow.state = WorkflowState.UNDER_REVIEW.value
        workflow.submitted_at = datetime.utcnow()
        workflow.rejection_reason = None
        
        # Check for policy decisions that might affect workflow priority
        # Query for recent policy decision for this document's transaction
        transaction_id = _get_transaction_id_from_document(db, document_id)
        
        if transaction_id:
                recent_policy_decision = db.query(PolicyDecisionModel).filter(
                    PolicyDecisionModel.transaction_id == transaction_id,
                    PolicyDecisionModel.transaction_type == "facility_creation"
                ).order_by(PolicyDecisionModel.created_at.desc()).first()
                
                if recent_policy_decision and recent_policy_decision.decision == "FLAG":
                    # FLAG decision: ensure high priority
                    if not transition_request or not transition_request.priority:
                        workflow.priority = "high"
                        logger.info(
                            f"Workflow for document {document_id} set to high priority due to FLAG policy decision: "
                            f"{recent_policy_decision.rule_applied}"
                        )
        
        if transition_request:
            if transition_request.assigned_to:
                assignee = db.query(User).filter(User.id == transition_request.assigned_to).first()
                if assignee and assignee.role in ["reviewer", "admin"]:
                    workflow.assigned_to = transition_request.assigned_to
            if transition_request.priority:
                workflow.priority = transition_request.priority
            if transition_request.due_date:
                try:
                    workflow.due_date = datetime.fromisoformat(transition_request.due_date.replace("Z", "+00:00"))
                except ValueError:
                    pass
        
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="workflow",
            target_id=workflow.id,
            user_id=current_user.id,
            metadata={"document_id": document_id, "transition": "submit", "from_state": previous_state, "to_state": WorkflowState.UNDER_REVIEW.value},
            request=request
        )
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Document {document_id} submitted for review by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document submitted for review",
            "workflow": workflow.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting document {document_id} for review: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to submit for review: {str(e)}"}
        )


@router.post("/documents/{document_id}/workflow/approve")
async def approve_document(
    document_id: int,
    request: Request,
    transition_request: WorkflowTransitionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Approve a document under review.
    
    Transitions the workflow from Under Review to Approved.
    Required roles: reviewer, admin
    """
    try:
        if not check_workflow_permission(current_user, ["reviewer", "admin"]):
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to approve documents"}
            )
        
        workflow = get_workflow_or_404(db, document_id)
        
        if workflow.state != WorkflowState.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Cannot approve: document is in '{workflow.state}' state, must be 'under_review'"}
            )
        
        previous_state = workflow.state
        workflow.state = WorkflowState.APPROVED.value
        workflow.approved_at = datetime.utcnow()
        workflow.approved_by = current_user.id
        
        log_audit_action(
            db=db,
            action=AuditAction.APPROVE,
            target_type="workflow",
            target_id=workflow.id,
            user_id=current_user.id,
            metadata={"document_id": document_id, "transition": "approve", "from_state": previous_state, "to_state": WorkflowState.APPROVED.value},
            request=request
        )
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Document {document_id} approved by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document approved",
            "workflow": workflow.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to approve document: {str(e)}"}
        )


@router.post("/documents/{document_id}/workflow/reject")
async def reject_document(
    document_id: int,
    reject_request: WorkflowRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Reject a document under review.
    
    Transitions the workflow from Under Review back to Draft.
    Required roles: reviewer, admin
    """
    try:
        if not check_workflow_permission(current_user, ["reviewer", "admin"]):
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to reject documents"}
            )
        
        workflow = get_workflow_or_404(db, document_id)
        
        if workflow.state != WorkflowState.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Cannot reject: document is in '{workflow.state}' state, must be 'under_review'"}
            )
        
        previous_state = workflow.state
        workflow.state = WorkflowState.DRAFT.value
        workflow.rejection_reason = reject_request.reason
        workflow.approved_at = None
        workflow.approved_by = None
        workflow.assigned_to = None
        workflow.due_date = None
        
        log_audit_action(
            db=db,
            action=AuditAction.REJECT,
            target_type="workflow",
            target_id=workflow.id,
            user_id=current_user.id,
            metadata={"document_id": document_id, "transition": "reject", "from_state": previous_state, "to_state": WorkflowState.DRAFT.value, "reason": reject_request.reason},
            request=request
        )
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Document {document_id} rejected by user {current_user.id}: {reject_request.reason}")
        
        return {
            "status": "success",
            "message": "Document rejected and returned to draft",
            "workflow": workflow.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to reject document: {str(e)}"}
        )


@router.post("/documents/{document_id}/workflow/publish")
async def publish_document(
    document_id: int,
    request: Request,
    transition_request: WorkflowTransitionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Publish an approved document.
    
    Transitions the workflow from Approved to Published.
    Required roles: reviewer, admin
    """
    try:
        if not check_workflow_permission(current_user, ["reviewer", "admin"]):
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to publish documents"}
            )
        
        workflow = get_workflow_or_404(db, document_id)
        
        if workflow.state != WorkflowState.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Cannot publish: document is in '{workflow.state}' state, must be 'approved'"}
            )
        
        previous_state = workflow.state
        workflow.state = WorkflowState.PUBLISHED.value
        workflow.published_at = datetime.utcnow()
        
        log_audit_action(
            db=db,
            action=AuditAction.PUBLISH,
            target_type="workflow",
            target_id=workflow.id,
            user_id=current_user.id,
            metadata={"document_id": document_id, "transition": "publish", "from_state": previous_state, "to_state": WorkflowState.PUBLISHED.value},
            request=request
        )
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Document {document_id} published by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document published",
            "workflow": workflow.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to publish document: {str(e)}"}
        )


@router.post("/documents/{document_id}/workflow/archive")
async def archive_document(
    document_id: int,
    request: Request,
    transition_request: WorkflowTransitionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Archive a document.
    
    Transitions the workflow from any state to Archived.
    Required roles: reviewer, admin
    """
    try:
        if not check_workflow_permission(current_user, ["reviewer", "admin"]):
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "You don't have permission to archive documents"}
            )
        
        workflow = get_workflow_or_404(db, document_id)
        
        if workflow.state == WorkflowState.ARCHIVED.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Document is already archived"}
            )
        
        previous_state = workflow.state
        workflow.state = WorkflowState.ARCHIVED.value
        
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="workflow",
            target_id=workflow.id,
            user_id=current_user.id,
            metadata={"document_id": document_id, "transition": "archive", "from_state": previous_state, "to_state": WorkflowState.ARCHIVED.value},
            request=request
        )
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Document {document_id} archived by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Document archived",
            "workflow": workflow.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error archiving document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to archive document: {str(e)}"}
        )


@router.get("/documents/{document_id}/workflow")
async def get_document_workflow(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current workflow state for a document.
    
    Returns workflow details including available actions based on current state.
    """
    try:
        workflow = get_workflow_or_404(db, document_id)
        
        available_actions = []
        state = workflow.state
        
        if state == WorkflowState.DRAFT.value:
            available_actions = ["submit"]
        elif state == WorkflowState.UNDER_REVIEW.value:
            available_actions = ["approve", "reject"]
        elif state == WorkflowState.APPROVED.value:
            available_actions = ["publish", "archive"]
        elif state == WorkflowState.PUBLISHED.value:
            available_actions = ["archive"]
        
        result = workflow.to_dict()
        result["available_actions"] = available_actions
        
        if workflow.approved_by:
            approver = db.query(User).filter(User.id == workflow.approved_by).first()
            result["approved_by_name"] = approver.display_name if approver else None
        
        if workflow.assigned_to:
            assignee = db.query(User).filter(User.id == workflow.assigned_to).first()
            result["assigned_to_name"] = assignee.display_name if assignee else None
        
        return {
            "status": "success",
            "workflow": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get workflow: {str(e)}"}
        )


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type (create, update, delete, approve, reject, publish, export, login, logout, broadcast)"),
    target_type: Optional[str] = Query(None, description="Filter by target type (document, workflow, user)"),
    target_id: Optional[int] = Query(None, description="Filter by target ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Filter logs from this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter logs until this date (ISO format)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List audit logs with optional filtering.
    
    Returns a paginated list of audit log entries. Only accessible by authenticated users.
    Admins and reviewers can see all logs; other users can only see logs related to their actions.
    """
    try:
        query = db.query(AuditLog).options(joinedload(AuditLog.user))
        
        if current_user.role not in ["admin", "reviewer"]:
            query = query.filter(AuditLog.user_id == current_user.id)
        
        if action:
            valid_actions = [a.value for a in AuditAction]
            if action not in valid_actions:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"}
                )
            query = query.filter(AuditLog.action == action)
        
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        
        if target_id:
            query = query.filter(AuditLog.target_id == target_id)
        
        if user_id:
            if current_user.role in ["admin", "reviewer"]:
                query = query.filter(AuditLog.user_id == user_id)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.filter(AuditLog.occurred_at >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid start_date format: {start_date}. Use ISO format."}
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.filter(AuditLog.occurred_at <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid end_date format: {end_date}. Use ISO format."}
                )
        
        total = query.count()
        
        logs = query.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for log in logs:
            log_dict = log.to_dict()
            log_dict["user_name"] = log.user.display_name if log.user else None
            log_dict["user_email"] = log.user.email if log.user else None
            result.append(log_dict)
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing audit logs: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list audit logs: {str(e)}"}
        )


@router.get("/documents/{document_id}/audit-logs")
async def list_document_audit_logs(
    document_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List audit logs for a specific document.
    
    Returns audit log entries related to a specific document, including workflow changes.
    """
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        workflow = db.query(Workflow).filter(Workflow.document_id == document_id).first()
        workflow_id = workflow.id if workflow else None
        
        query = db.query(AuditLog).options(joinedload(AuditLog.user))
        
        if workflow_id:
            query = query.filter(
                ((AuditLog.target_type == "document") & (AuditLog.target_id == document_id)) |
                ((AuditLog.target_type == "workflow") & (AuditLog.target_id == workflow_id))
            )
        else:
            query = query.filter(
                (AuditLog.target_type == "document") & (AuditLog.target_id == document_id)
            )
        
        total = query.count()
        
        logs = query.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for log in logs:
            log_dict = log.to_dict()
            log_dict["user_name"] = log.user.display_name if log.user else None
            result.append(log_dict)
        
        return {
            "status": "success",
            "document_id": document_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing audit logs for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list document audit logs: {str(e)}"}
        )


def flatten_agreement_data(agreement_data: dict) -> dict:
    """Flatten nested agreement data structure for tabular export.
    
    Args:
        agreement_data: The nested agreement data from extraction.
        
    Returns:
        Flattened dictionary suitable for DataFrame/CSV export.
    """
    flat = {}
    
    flat["agreement_date"] = agreement_data.get("agreement_date")
    flat["governing_law"] = agreement_data.get("governing_law")
    flat["amendment_number"] = agreement_data.get("amendment_number")
    
    parties = agreement_data.get("parties", [])
    borrowers = [p for p in parties if isinstance(p.get("role", ""), str) and "borrower" in p.get("role", "").lower()]
    lenders = [p for p in parties if p.get("role") in ["Lender", "Administrative Agent"]]
    
    if borrowers:
        flat["borrower_name"] = borrowers[0].get("name") or borrowers[0].get("legal_name")
        flat["borrower_lei"] = borrowers[0].get("lei")
        flat["borrower_jurisdiction"] = borrowers[0].get("jurisdiction")
    
    if lenders:
        flat["lender_count"] = len(lenders)
        flat["administrative_agent"] = next(
            (p.get("name") or p.get("legal_name") for p in lenders if p.get("role") == "Administrative Agent"),
            None
        )
    
    facilities = agreement_data.get("facilities", [])
    flat["facility_count"] = len(facilities)
    
    total_commitment = Decimal("0")
    currency = None
    for i, facility in enumerate(facilities):
        if not isinstance(facility, dict):
            continue
        prefix = f"facility_{i+1}_"
        flat[f"{prefix}type"] = facility.get("facility_type")
        flat[f"{prefix}name"] = facility.get("facility_name")
        
        commitment = facility.get("commitment_amount") or facility.get("commitment")
        if commitment and isinstance(commitment, dict):
            amount = commitment.get("amount")
            if amount:
                flat[f"{prefix}commitment_amount"] = float(amount)
                total_commitment += Decimal(str(amount))
            curr = commitment.get("currency")
            if curr:
                flat[f"{prefix}currency"] = curr
                if not currency:
                    currency = curr
        
        flat[f"{prefix}maturity_date"] = facility.get("maturity_date")
        
        interest = facility.get("interest_terms") or facility.get("interest_rate_payout")
        if interest and isinstance(interest, dict):
            floating = interest.get("rate_option") or interest.get("floating_rate_option")
            if floating and isinstance(floating, dict):
                flat[f"{prefix}benchmark_rate"] = floating.get("benchmark") or floating.get("benchmark_rate")
                flat[f"{prefix}spread_bps"] = floating.get("spread_bps") or floating.get("spread")
            pf = interest.get("payment_frequency")
            if pf and isinstance(pf, dict):
                flat[f"{prefix}payment_frequency"] = f"{pf.get('period_multiplier')} {pf.get('period')}"
            else:
                flat[f"{prefix}payment_frequency"] = pf
    
    flat["total_commitment"] = float(total_commitment) if total_commitment > 0 else None
    flat["currency"] = currency
    
    sustainability = agreement_data.get("sustainability_provisions")
    if sustainability and isinstance(sustainability, dict):
        flat["sustainability_linked"] = sustainability.get("is_sustainability_linked", False)
        kpis = sustainability.get("esg_kpis", [])
        if kpis:
            flat["esg_kpi_count"] = len(kpis)
            flat["esg_kpis"] = "; ".join([k.get("name", "") for k in kpis if k.get("name")])
        margin = sustainability.get("margin_adjustment")
        if margin:
            flat["margin_adjustment_bps"] = margin.get("basis_points")
    else:
        flat["sustainability_linked"] = False
    
    covenants = agreement_data.get("financial_covenants", [])
    if covenants:
        flat["covenant_count"] = len(covenants)
        flat["covenants"] = "; ".join([c.get("name", "") for c in covenants if c.get("name")])
    
    return flat


def agreement_to_dataframe(agreement_data: dict, include_raw: bool = False) -> pd.DataFrame:
    """Convert agreement data to a pandas DataFrame.
    
    Args:
        agreement_data: The agreement data from extraction.
        include_raw: Whether to include a column with the raw JSON.
        
    Returns:
        DataFrame with one row containing the flattened data.
    """
    flat = flatten_agreement_data(agreement_data)
    
    if include_raw:
        flat["raw_json"] = json.dumps(agreement_data, default=str)
    
    df = pd.DataFrame([flat])
    return df


def facilities_to_dataframe(agreement_data: dict) -> pd.DataFrame:
    """Convert facilities from agreement data to a DataFrame.
    
    Args:
        agreement_data: The agreement data from extraction.
        
    Returns:
        DataFrame with one row per facility.
    """
    facilities = agreement_data.get("facilities", [])
    if not facilities:
        return pd.DataFrame()
    
    rows = []
    for facility in facilities:
        if not isinstance(facility, dict):
            continue
        row = {
            "facility_type": facility.get("facility_type"),
            "facility_name": facility.get("facility_name"),
            "maturity_date": facility.get("maturity_date"),
        }
        
        commitment = facility.get("commitment_amount") or facility.get("commitment")
        if commitment and isinstance(commitment, dict):
            row["commitment_amount"] = commitment.get("amount")
            row["currency"] = commitment.get("currency")
        
        interest = facility.get("interest_terms") or facility.get("interest_rate_payout")
        if interest and isinstance(interest, dict):
            floating = interest.get("rate_option") or interest.get("floating_rate_option")
            if floating and isinstance(floating, dict):
                row["benchmark_rate"] = floating.get("benchmark") or floating.get("benchmark_rate")
                row["spread_bps"] = floating.get("spread_bps") or floating.get("spread")
            pf = interest.get("payment_frequency")
            if pf and isinstance(pf, dict):
                row["payment_frequency"] = f"{pf.get('period_multiplier')} {pf.get('period')}"
            else:
                row["payment_frequency"] = pf
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def parties_to_dataframe(agreement_data: dict) -> pd.DataFrame:
    """Convert parties from agreement data to a DataFrame.
    
    Args:
        agreement_data: The agreement data from extraction.
        
    Returns:
        DataFrame with one row per party.
    """
    parties = agreement_data.get("parties", [])
    if not parties:
        return pd.DataFrame()
    
    rows = []
    for party in parties:
        rows.append({
            "name": party.get("name") or party.get("legal_name"),
            "role": party.get("role"),
            "lei": party.get("lei"),
            "jurisdiction": party.get("jurisdiction"),
        })
    
    return pd.DataFrame(rows)


@router.get("/documents/{document_id}/export")
async def export_document(
    document_id: int,
    format: str = Query("json", description="Export format: json, csv, or excel"),
    version_id: Optional[int] = Query(None, description="Specific version ID to export (defaults to current version)"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export document data in various formats.
    
    Args:
        document_id: The document ID.
        format: Export format (json, csv, excel).
        version_id: Optional specific version to export.
        request: The HTTP request.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        The exported data as a file download.
    """
    format = format.lower()
    if format not in ["json", "csv", "excel", "xlsx"]:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": f"Invalid format: {format}. Supported: json, csv, excel"}
        )
    
    if format == "xlsx":
        format = "excel"
    
    try:
        doc = db.query(Document).options(
            joinedload(Document.versions)
        ).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Document not found"}
            )
        
        if version_id:
            version = next((v for v in doc.versions if v.id == version_id), None)
            if not version:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "message": f"Version {version_id} not found"}
                )
        else:
            version = next((v for v in doc.versions if v.id == doc.current_version_id), None)
            if not version and doc.versions:
                version = max(doc.versions, key=lambda v: v.version_number)
        
        if not version:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "No versions found for this document"}
            )
        
        agreement_data = version.extracted_data
        safe_title = "".join(c for c in doc.title if c.isalnum() or c in " -_").strip()[:50]
        filename_base = f"{safe_title}_v{version.version_number}"
        
        if format == "json":
            output = io.BytesIO()
            json_data = json.dumps(agreement_data, indent=2, default=str)
            output.write(json_data.encode("utf-8"))
            output.seek(0)
            
            if current_user:
                log_audit_action(
                    db=db,
                    action=AuditAction.EXPORT,
                    target_type="document",
                    target_id=document_id,
                    user_id=current_user.id,
                    metadata={"format": "json", "version_id": version.id},
                    request=request
                )
                db.commit()
            
            return StreamingResponse(
                output,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename_base}.json"'
                }
            )
        
        elif format == "csv":
            df = agreement_to_dataframe(agreement_data)
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            if current_user:
                log_audit_action(
                    db=db,
                    action=AuditAction.EXPORT,
                    target_type="document",
                    target_id=document_id,
                    user_id=current_user.id,
                    metadata={"format": "csv", "version_id": version.id},
                    request=request
                )
                db.commit()
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename_base}.csv"'
                }
            )
        
        elif format == "excel":
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                summary_df = agreement_to_dataframe(agreement_data)
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
                
                facilities_df = facilities_to_dataframe(agreement_data)
                if not facilities_df.empty:
                    facilities_df.to_excel(writer, sheet_name="Facilities", index=False)
                
                parties_df = parties_to_dataframe(agreement_data)
                if not parties_df.empty:
                    parties_df.to_excel(writer, sheet_name="Parties", index=False)
            
            output.seek(0)
            
            if current_user:
                log_audit_action(
                    db=db,
                    action=AuditAction.EXPORT,
                    target_type="document",
                    target_id=document_id,
                    user_id=current_user.id,
                    metadata={"format": "excel", "version_id": version.id},
                    request=request
                )
                db.commit()
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error exporting document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to export document: {str(e)}"}
        )


# ============================================================================
# GROUND TRUTH PROTOCOL - Loan Asset & Geospatial Verification Endpoints
# ============================================================================

from app.models.loan_asset import LoanAsset, RiskStatus
from app.agents.audit_workflow import run_full_audit, AuditResult


class CreateLoanAssetRequest(BaseModel):
    """Request model for creating a loan asset."""
    loan_id: str = Field(..., description="External loan identifier")
    document_text: str = Field(..., description="Full text of loan agreement")
    title: Optional[str] = Field(None, description="Optional title for the asset")


class RunAuditRequest(BaseModel):
    """Request model for running a full audit."""
    document_text: Optional[str] = Field(None, description="Optional new document text to re-analyze")


@router.post("/loan-assets")
async def create_loan_asset(
    request_data: CreateLoanAssetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    policy_service: Optional[PolicyService] = Depends(get_policy_service)
):
    """
    Create a new loan asset and run the full Ground Truth audit.
    
    This is the "Securitize & Verify" endpoint that:
    1. Extracts SPT and collateral address from document
    2. Geocodes the address
    3. Fetches satellite imagery
    4. Calculates NDVI and determines compliance status
    5. Evaluates policy compliance for securitization
    
    Args:
        request_data: Loan ID and document text
        request: HTTP request for audit logging
        db: Database session
        current_user: Authenticated user
        policy_service: Policy service for compliance evaluation (optional)
        
    Returns:
        Created loan asset with verification results
    """
    from app.models.cdm import CreditAgreement
    
    try:
        logger.info(f"Creating loan asset {request_data.loan_id}")
        
        # Try to get credit agreement from document if document_id provided
        credit_agreement = None
        if hasattr(request_data, 'document_id') and request_data.document_id:
            doc = db.query(Document).filter(Document.id == request_data.document_id).first()
            if doc and doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    try:
                        credit_agreement = CreditAgreement(**version.extracted_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse credit agreement from document: {e}")
        
        # Run the full audit workflow with policy service
        audit_result = await run_full_audit(
            loan_id=request_data.loan_id,
            document_text=request_data.document_text,
            db_session=db,
            policy_service=policy_service,
            credit_agreement=credit_agreement
        )
        
        if not audit_result.loan_asset:
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": "Failed to create loan asset"}
            )
        
        # Log the audit action
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="loan_asset",
            target_id=audit_result.loan_asset.id,
            user_id=current_user.id if current_user else None,
            metadata={
                "loan_id": request_data.loan_id,
                "stages_completed": audit_result.stages_completed,
                "stages_failed": audit_result.stages_failed,
                "risk_status": audit_result.loan_asset.risk_status
            },
            request=request
        )
        db.commit()
        
        return {
            "status": "success",
            "message": "Loan asset created and verified",
            "loan_asset": audit_result.loan_asset.to_dict(),
            "audit": {
                "success": audit_result.success,
                "stages_completed": audit_result.stages_completed,
                "stages_failed": audit_result.stages_failed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating loan asset: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create loan asset: {str(e)}"}
        )


@router.get("/loan-assets")
async def list_loan_assets(
    status: Optional[str] = Query(None, description="Filter by risk status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all loan assets with optional filtering.
    
    Args:
        status: Optional risk status filter (COMPLIANT, WARNING, BREACH, PENDING)
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        current_user: Current user
        
    Returns:
        List of loan assets
    """
    try:
        query = db.query(LoanAsset)
        
        if status:
            query = query.filter(LoanAsset.risk_status == status.upper())
        
        total = query.count()
        assets = query.order_by(LoanAsset.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "loan_assets": [asset.to_dict() for asset in assets]
        }
        
    except Exception as e:
        logger.error(f"Error listing loan assets: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list loan assets: {str(e)}"}
        )


@router.get("/loan-assets/{asset_id}")
async def get_loan_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single loan asset by ID.
    
    Args:
        asset_id: Loan asset ID
        db: Database session
        current_user: Current user
        
    Returns:
        Loan asset details
    """
    try:
        asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Loan asset not found"}
            )
        
        return {
            "status": "success",
            "loan_asset": asset.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting loan asset {asset_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get loan asset: {str(e)}"}
        )


@router.post("/audit/run/{asset_id}")
async def run_asset_audit(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Run or re-run the Ground Truth verification for an existing asset.
    
    This fetches fresh satellite data and recalculates NDVI.
    
    Args:
        asset_id: Loan asset ID
        request: HTTP request
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated verification results
    """
    from app.agents.verifier import verify_asset_location
    
    try:
        asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Loan asset not found"}
            )
        
        if not asset.geo_lat or not asset.geo_lon:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Asset has no coordinates - cannot verify"}
            )
        
        logger.info(f"Running verification for asset {asset_id}")
        
        # Run verification
        verification = await verify_asset_location(
            lat=asset.geo_lat,
            lon=asset.geo_lon,
            threshold=asset.spt_threshold or 0.8
        )
        
        if verification.get("success"):
            ndvi_score = verification["ndvi_score"]
            asset.update_verification(ndvi_score)
        else:
            asset.risk_status = RiskStatus.ERROR
            asset.verification_error = verification.get("error", "Unknown error")
        
        # Log the audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="loan_asset",
            target_id=asset_id,
            user_id=current_user.id if current_user else None,
            metadata={
                "action": "verification",
                "ndvi_score": verification.get("ndvi_score"),
                "risk_status": asset.risk_status,
                "data_source": verification.get("data_source")
            },
            request=request
        )
        
        db.commit()
        db.refresh(asset)
        
        return {
            "status": "success",
            "message": "Verification complete",
            "loan_asset": asset.to_dict(),
            "verification": verification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error running audit for asset {asset_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to run audit: {str(e)}"}
        )


@router.get("/audit/status/{asset_id}")
async def get_audit_status(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current verification status of a loan asset.
    
    This is a lightweight polling endpoint for frontend status updates.
    
    Args:
        asset_id: Loan asset ID
        db: Database session
        current_user: Current user
        
    Returns:
        Current status and key metrics
    """
    try:
        asset = db.query(LoanAsset).filter(LoanAsset.id == asset_id).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Loan asset not found"}
            )
        
        return {
            "status": "success",
            "asset_id": asset_id,
            "loan_id": asset.loan_id,
            "risk_status": asset.risk_status,
            "ndvi_score": asset.last_verified_score,
            "spt_threshold": asset.spt_threshold,
            "base_interest_rate": asset.base_interest_rate,
            "current_interest_rate": asset.current_interest_rate,
            "last_verified_at": asset.last_verified_at.isoformat() if asset.last_verified_at else None,
            "verification_error": asset.verification_error,
            "is_cdm_compliant": asset.spt_data is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit status for asset {asset_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get audit status: {str(e)}"}
        )


@router.get("/loan-assets/demo")
async def demo_loan_asset(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get or create a demo loan asset for testing.
    
    Uses the Paradise, CA forest area as a demo location.
    """
    try:
        # Check if demo asset exists
        demo_asset = db.query(LoanAsset).filter(LoanAsset.loan_id == "DEMO-2024-001").first()
        
        if demo_asset:
            return {
                "status": "success",
                "message": "Demo asset already exists",
                "loan_asset": demo_asset.to_dict()
            }
        
        # Create demo asset
        from app.agents.audit_workflow import DEMO_COVENANT, run_full_audit
        
        result = await run_full_audit(
            loan_id="DEMO-2024-001",
            document_text=DEMO_COVENANT,
            db_session=db
        )
        
        return {
            "status": "success",
            "message": "Demo asset created",
            "loan_asset": result.loan_asset.to_dict() if result.loan_asset else None,
            "audit": {
                "success": result.success,
                "stages_completed": result.stages_completed,
                "stages_failed": result.stages_failed
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating demo asset: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create demo asset: {str(e)}"}
        )

# ------------------------------------------------------------------------------
# Ground Truth Protocol - "Kill Shot" Demo Endpoints
# ------------------------------------------------------------------------------

@router.get("/cdm/events/{trade_id}")
async def get_cdm_events(trade_id: str):
    """
    Returns the Life-Cycle Events for the trade in FINOS CDM format.
    Includes the 'TermsChange' event triggered by the satellite observation.
    """
    # 1. Trade Execution (State v1)
    execution = generate_cdm_trade_execution(
        trade_id=trade_id,
        borrower="Napa Valley Vineyards LLC",
        amount=50000000.00,
        rate=5.00
    )
    
    # 2. Observation (The Satellite Signal) - Hardcoded 'BREACH' for demo storytelling
    # In a real sync workflow, this would come from the database
    mock_hash = hashlib.sha256(b"sentinel_2_image_patch_2024_08_15").hexdigest()
    observation = generate_cdm_observation(
        trade_id=trade_id,
        satellite_hash=mock_hash,
        ndvi_score=0.65,
        status="BREACH"
    )
    
    # 3. Terms Change (State v2) - The Financial Consequence
    terms_change = generate_cdm_terms_change(
        trade_id=trade_id,
        current_rate=5.00,
        status="BREACH"
    )
    
    # ---------------------------------------------------------
    # INFRASTRUCTURE LAYER: Vector Indexing (Side Effect)
    # ---------------------------------------------------------
    GLOBAL_VECTOR_STORE.add_trade_event(execution)
    GLOBAL_VECTOR_STORE.add_trade_event(observation)
    GLOBAL_VECTOR_STORE.add_trade_event(terms_change)
    
    return [execution, observation, terms_change]

@router.get("/search")
async def semantic_search_trades(q: str):
    """
    Semantic Search over Trade Lifecycle Events.
    Demonstrates "Hybrid Search" capabilities.
    """
    results = GLOBAL_VECTOR_STORE.semantic_search(q)
    return results

@router.post("/classify")
async def classify_land_use(lat: float, lon: float):
    """
    Real-time Deep Learning Inference using TorchGeo.
    """
    if not GLOBAL_CLASSIFIER:
        raise HTTPException(status_code=503, detail="Classifier not initialized")
        
    result = GLOBAL_CLASSIFIER.classify_lat_lon(lat, lon)
    return result


class TermsChangeRequest(BaseModel):
    """Request model for terms change with policy evaluation."""
    trade_id: str = Field(..., description="Trade identifier")
    current_rate: float = Field(..., ge=0, description="Current interest rate")
    proposed_rate: float = Field(..., ge=0, description="Proposed new interest rate")
    reason: str = Field(..., description="Reason for terms change")


@router.post("/trades/{trade_id}/terms-change")
async def change_trade_terms(
    trade_id: str,
    terms_request: TermsChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    policy_service: Optional[PolicyService] = Depends(get_policy_service)
):
    """
    Change trade terms (interest rate) with policy evaluation.
    
    This endpoint:
    1. Evaluates the proposed rate change against compliance policies
    2. Blocks, flags, or allows the rate change based on policy decision
    3. Generates CDM TermsChange event if allowed
    4. Returns the terms change result with policy decision
    
    Args:
        trade_id: Trade identifier (from path)
        terms_request: Terms change request with current/proposed rates
        db: Database session
        current_user: Current authenticated user
        policy_service: Policy service for compliance evaluation (optional)
        
    Returns:
        Terms change result with policy decision and CDM events
    """
    from app.models.cdm_events import generate_cdm_terms_change
    from app.db.models import PolicyDecision as PolicyDecisionModel
    
    try:
        # Validate trade_id matches request
        if terms_request.trade_id != trade_id:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Trade ID in path must match trade_id in request body"}
            )
        
        logger.info(
            f"Terms change request: trade_id={trade_id}, "
            f"current_rate={terms_request.current_rate}, "
            f"proposed_rate={terms_request.proposed_rate}, "
            f"reason={terms_request.reason}"
        )
        
        # Calculate rate delta
        rate_delta = terms_request.proposed_rate - terms_request.current_rate
        
        # Policy evaluation (if enabled)
        policy_decision = None
        policy_evaluation_event = None
        
        if policy_service:
            try:
                # Evaluate terms change for compliance
                policy_result = policy_service.evaluate_terms_change(
                    trade_id=trade_id,
                    current_rate=terms_request.current_rate,
                    proposed_rate=terms_request.proposed_rate,
                    reason=terms_request.reason
                )
                
                # Create CDM PolicyEvaluation event
                from app.models.cdm_events import generate_cdm_policy_evaluation
                policy_evaluation_event = generate_cdm_policy_evaluation(
                    transaction_id=trade_id,
                    transaction_type="terms_change",
                    decision=policy_result.decision,
                    rule_applied=policy_result.rule_applied,
                    related_event_identifiers=[],
                    evaluation_trace=policy_result.trace,
                    matched_rules=policy_result.matched_rules
                )
                
                # Handle BLOCK decision - prevent rate change
                if policy_result.decision == "BLOCK":
                    logger.warning(
                        f"Policy evaluation BLOCKED terms change: "
                        f"trade_id={trade_id}, current_rate={terms_request.current_rate}, "
                        f"proposed_rate={terms_request.proposed_rate}, rule={policy_result.rule_applied}, "
                        f"trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=f"terms_change_{trade_id}",
                            transaction_type="terms_change",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={
                                "trade_id": trade_id,
                                "current_rate": terms_request.current_rate,
                                "proposed_rate": terms_request.proposed_rate,
                                "rate_delta": rate_delta,
                                "reason": terms_request.reason
                            },
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for terms change
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with block decision.")
                        db.rollback()
                    
                    return {
                        "status": "blocked",
                        "decision": "BLOCK",
                        "rule": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id,
                        "message": f"Terms change blocked by compliance policy: {policy_result.rule_applied}",
                        "current_rate": terms_request.current_rate,
                        "proposed_rate": terms_request.proposed_rate,
                        "cdm_event": policy_evaluation_event
                    }
                
                # Handle FLAG decision - allow but mark for review
                elif policy_result.decision == "FLAG":
                    logger.info(
                        f"Policy evaluation FLAGGED terms change: "
                        f"trade_id={trade_id}, rule={policy_result.rule_applied}, "
                        f"trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=f"terms_change_{trade_id}",
                            transaction_type="terms_change",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={
                                "trade_id": trade_id,
                                "current_rate": terms_request.current_rate,
                                "proposed_rate": terms_request.proposed_rate,
                                "rate_delta": rate_delta,
                                "reason": terms_request.reason,
                                "requires_review": True
                            },
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for terms change
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with terms change.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id,
                        "requires_review": True
                    }
                
                # Handle ALLOW decision - log for audit
                else:
                    logger.debug(
                        f"Policy evaluation ALLOWED terms change: "
                        f"trade_id={trade_id}, trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=f"terms_change_{trade_id}",
                            transaction_type="terms_change",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={
                                "trade_id": trade_id,
                                "current_rate": terms_request.current_rate,
                                "proposed_rate": terms_request.proposed_rate,
                                "rate_delta": rate_delta,
                                "reason": terms_request.reason
                            },
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for terms change
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with terms change.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id
                    }
                    
            except Exception as e:
                # Log policy evaluation errors but don't block terms change
                logger.error(f"Policy evaluation failed for terms change: {e}", exc_info=True)
                # Continue with terms change even if policy evaluation fails
        
        # Generate CDM TermsChange event (if not blocked)
        # Determine status from reason or rate delta
        status = "BREACH" if "breach" in terms_request.reason.lower() else "COMPLIANT"
        
        terms_change_event = generate_cdm_terms_change(
            trade_id=trade_id,
            current_rate=terms_request.current_rate,
            status=status,
            policy_service=policy_service
        )
        
        # If policy blocked the change, terms_change_event will be None
        if terms_change_event is None:
            return {
                "status": "blocked",
                "message": "Terms change blocked by policy evaluation",
                "current_rate": terms_request.current_rate,
                "proposed_rate": terms_request.proposed_rate
            }
        
        # Return terms change result
        return {
            "status": "changed",
            "trade_id": trade_id,
            "current_rate": terms_request.current_rate,
            "new_rate": terms_request.proposed_rate,
            "rate_delta": rate_delta,
            "terms_change_event": terms_change_event,
            "policy_decision": policy_decision,
            "cdm_events": (
                [terms_change_event, policy_evaluation_event]
                if policy_evaluation_event
                else [terms_change_event]
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during terms change: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Terms change failed: {str(e)}"}
        )


# ------------------------------------------------------------------------------
# x402 Payment Integration - Helper Functions
# ------------------------------------------------------------------------------

def get_trade_execution(trade_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Get trade execution event by trade ID.
    
    This helper function retrieves trade execution events. In a production system,
    trades would be stored in a database. For now, we'll check if the trade
    was recently executed and stored in the vector store or generate it on-demand.
    
    Args:
        trade_id: Trade identifier
        db: Database session
        
    Returns:
        Trade execution CDM event dictionary or None if not found
    """
    # Check vector store for trade events
    try:
        # Search vector store for trade events
        results = GLOBAL_VECTOR_STORE.semantic_search(trade_id)
        for result in results:
            event = result.get("json", {})
            if event.get("eventType") == "TradeExecution":
                trade = event.get("trade", {})
                trade_identifier = trade.get("tradeIdentifier", {})
                assigned_ids = trade_identifier.get("assignedIdentifier", [])
                if assigned_ids:
                    event_trade_id = assigned_ids[0].get("identifier", {}).get("value", "")
                    if event_trade_id == trade_id:
                        return event
    except Exception as e:
        logger.warning(f"Error searching vector store for trade {trade_id}: {e}")
    
    # If not found, return None (caller should handle)
    return None


def get_party_by_id(party_id: str, db: Session, credit_agreement = None):
    """
    Get party by ID from credit agreement or database.
    
    Args:
        party_id: Party identifier (LEI or internal ID)
        db: Database session
        credit_agreement: Optional credit agreement to search
        
    Returns:
        CDM Party object or None if not found
    """
    from app.models.cdm import Party, CreditAgreement
    
    # First, try to find in provided credit agreement
    if credit_agreement and credit_agreement.parties:
        for party in credit_agreement.parties:
            if party.id == party_id or party.lei == party_id:
                return party
    
    # If not found, try to find in documents
    try:
        # Query documents for party information
        from app.db.models import Document, DocumentVersion
        
        documents = db.query(Document).join(DocumentVersion).filter(
            DocumentVersion.extracted_data.isnot(None)
        ).limit(10).all()
        
        for doc in documents:
            if doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    try:
                        agreement = CreditAgreement(**version.extracted_data)
                        if agreement.parties:
                            for party in agreement.parties:
                                if party.id == party_id or party.lei == party_id:
                                    return party
                    except Exception:
                        continue
    except Exception as e:
        logger.warning(f"Error querying database for party {party_id}: {e}")
    
    # If not found, create a minimal party object
    # This is a fallback for demo purposes
    return Party(
        id=party_id,
        name=party_id,  # Use ID as name if not found
        role="Unknown",
        lei=None
    )


def update_trade_status(trade_id: str, status: str, db: Session) -> None:
    """
    Update trade status in database or tracking system.
    
    In a production system, this would update a trades table.
    For now, we'll log the status change to the audit trail.
    
    Args:
        trade_id: Trade identifier
        status: New status (pending, confirmed, settled, etc.)
        db: Database session
    """
    try:
        # Log status change to audit trail
        from app.db.models import AuditLog, AuditAction
        from datetime import datetime
        
        audit_log = AuditLog(
            user_id=None,  # System action
            action=AuditAction.UPDATE,
            target_type="trade",
            target_id=None,  # No numeric ID for trades yet
            metadata={
                "trade_id": trade_id,
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Trade {trade_id} status updated to {status}")
    except Exception as e:
        logger.error(f"Error updating trade status: {e}")
        db.rollback()


def get_credit_agreement_for_loan(loan_id: str, db: Session):
    """
    Get credit agreement for a loan by loan_id.
    
    This helper function retrieves the credit agreement associated with a loan.
    It searches through documents to find the agreement that matches the loan_id.
    
    Args:
        loan_id: Loan identifier
        db: Database session
        
    Returns:
        CreditAgreement object or None if not found
    """
    from app.models.cdm import CreditAgreement
    from app.db.models import Document, DocumentVersion
    
    try:
        # First, try to find loan asset and get associated document
        loan_asset = db.query(LoanAsset).filter(LoanAsset.loan_id == loan_id).first()
        
        # If loan asset exists and has document reference, use it
        # (Note: LoanAsset model may not have document_id field yet)
        
        # Search documents for credit agreement matching loan_id
        # Check if loan_id matches deal_id or loan_identification_number in extracted_data
        documents = db.query(Document).join(DocumentVersion).filter(
            DocumentVersion.extracted_data.isnot(None)
        ).all()
        
        for doc in documents:
            if doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    try:
                        agreement = CreditAgreement(**version.extracted_data)
                        # Check if loan_id matches deal_id or loan_identification_number
                        if (agreement.deal_id == loan_id or 
                            agreement.loan_identification_number == loan_id or
                            (loan_asset and hasattr(loan_asset, 'original_text') and 
                             loan_id in (loan_asset.original_text or ""))):
                            return agreement
                    except Exception as e:
                        logger.debug(f"Error parsing credit agreement from document {doc.id}: {e}")
                        continue
        
        # If not found in documents, try to extract from loan asset's original_text
        if loan_asset and hasattr(loan_asset, 'original_text') and loan_asset.original_text:
            try:
                # Try to extract credit agreement from loan asset's document text
                from app.chains.extraction_chain import extract_data_smart
                result = extract_data_smart(text=loan_asset.original_text)
                if result and result.agreement:
                    return result.agreement
            except Exception as e:
                logger.warning(f"Error extracting credit agreement from loan asset text: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting credit agreement for loan {loan_id}: {e}")
        return None


class PaymentPayloadRequest(BaseModel):
    """Request model for x402 payment payload."""
    payment_payload: Dict[str, Any] = Field(..., description="x402 payment payload from client wallet")


@router.post("/trades/{trade_id}/settle")
async def settle_trade_with_payment(
    trade_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service)
):
    # Parse request body manually to handle optional payment payload
    payment_request = None
    try:
        body = await request.json()
        if body and "payment_payload" in body:
            payment_request = PaymentPayloadRequest(**body)
    except Exception:
        # No body or invalid JSON - payment_request remains None
        pass
    
    """
    Settle trade with x402 payment.
    
    This endpoint:
    1. Retrieves the trade execution event
    2. Extracts parties and amount from CDM trade event
    3. Processes payment via x402 (request → verify → settle)
    4. Creates CDM PaymentEvent
    5. Updates trade status to settled
    
    Args:
        trade_id: Trade identifier
        payment_request: Optional x402 payment payload (if None, returns 402 Payment Required)
        db: Database session
        current_user: Current authenticated user
        payment_service: x402 payment service (optional)
        
    Returns:
        Settlement result with payment confirmation or 402 Payment Required
    """
    from app.models.cdm import Party, Money, Currency
    from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod, PaymentStatus
    from app.db.models import PaymentEvent as PaymentEventModel
    from fastapi.responses import JSONResponse
    
    try:
        # Step 1: Get trade execution event
        trade_event = get_trade_execution(trade_id, db)
        
        if not trade_event:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Trade {trade_id} not found"}
            )
        
        # Step 2: Extract parties and amount from CDM trade event
        try:
            trade = trade_event.get("trade", {})
            tradable_product = trade.get("tradableProduct", {})
            counterparties = tradable_product.get("counterparty", [])
            
            if len(counterparties) < 2:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": "Trade event missing counterparty information"}
                )
            
            # Extract payer and receiver from counterparties
            payer_ref = counterparties[0].get("partyReference", {}).get("globalReference", "")
            receiver_ref = counterparties[1].get("partyReference", {}).get("globalReference", "")
            
            # Extract amount and currency
            economic_terms = tradable_product.get("economicTerms", {})
            notional = economic_terms.get("notional", {})
            amount_value = notional.get("amount", {}).get("value", 0)
            currency_value = notional.get("currency", {}).get("value", "USD")
            
            amount = Decimal(str(amount_value))
            currency = Currency(currency_value)
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing trade event: {e}")
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Invalid trade event structure: {str(e)}"}
            )
        
        # Step 3: Get parties from CDM
        payer = get_party_by_id(payer_ref, db)
        receiver = get_party_by_id(receiver_ref, db)
        
        if not payer or not receiver:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Party information not found"}
            )
        
        # Step 4: Process payment via x402
        if not payment_service:
            raise HTTPException(
                status_code=503,
                detail={"status": "error", "message": "x402 payment service is not available"}
            )
        
        payment_payload = payment_request.payment_payload if payment_request else None
        
        try:
            payment_result = await payment_service.process_payment_flow(
                amount=amount,
                currency=currency,
                payer=payer,
                receiver=receiver,
                payment_type="trade_settlement",
                payment_payload=payment_payload,
                cdm_reference={
                    "trade_id": trade_id,
                    "event_type": "TradeExecution"
                }
            )
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Payment flow failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": f"Payment processing failed: {str(e)}"}
            )
        
        # Step 5: Handle payment required (402 response)
        if payment_payload is None or payment_result.get("status") != "settled":
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "payment_request": payment_result.get("payment_request"),
                    "amount": str(amount),
                    "currency": currency.value,
                    "payer": {
                        "id": payer.id,
                        "name": payer.name,
                        "lei": payer.lei
                    },
                    "receiver": {
                        "id": receiver.id,
                        "name": receiver.name,
                        "lei": receiver.lei
                    },
                    "facilitator_url": payment_service.facilitator_url
                }
            )
        
        # Step 6: Create CDM PaymentEvent using CDM-compliant factory method
        payment_event = PaymentEvent.from_cdm_party(
            payer=payer,
            receiver=receiver,
            amount=Money(amount=amount, currency=currency),
            payment_type=PaymentType.TRADE_SETTLEMENT,
            payment_method=PaymentMethod.X402,
            trade_id=trade_id
        )
        
        # Step 7: Update with x402 payment details
        payment_event = payment_event.model_copy(update={
            "x402PaymentDetails": {
                "payment_payload": payment_payload,
                "verification": payment_result.get("verification"),
                "settlement": payment_result.get("settlement")
            },
            "transactionHash": payment_result.get("transaction_hash")
        })
        
        # Step 8: Transition through state machine: PENDING -> VERIFIED -> SETTLED
        payment_event = payment_event.transition_to_verified()
        payment_event = payment_event.transition_to_settled(payment_result.get("transaction_hash", ""))
        
        # Step 9: Save payment event to database
        payment_event_db = PaymentEventModel(
            payment_id=payment_event.paymentIdentifier.assignedIdentifier[0]["identifier"]["value"],
            payment_method=payment_event.paymentMethod.value,
            payment_type=payment_event.paymentType.value,
            payer_id=payment_event.payerPartyReference.globalReference,
            payer_name=payer.name,
            receiver_id=payment_event.receiverPartyReference.globalReference,
            receiver_name=receiver.name,
            amount=payment_event.paymentAmount.amount,
            currency=payment_event.paymentAmount.currency.value,
            status=payment_event.paymentStatus.value,
            x402_payment_payload=payment_payload,
            x402_verification=payment_result.get("verification"),
            x402_settlement=payment_result.get("settlement"),
            transaction_hash=payment_result.get("transaction_hash"),
            related_trade_id=trade_id,
            cdm_event=payment_event.to_cdm_json(),
            settled_at=datetime.utcnow()
        )
        db.add(payment_event_db)
        db.commit()
        
        # Step 10: Update trade status
        update_trade_status(trade_id, "settled", db)
        
        # Step 11: Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="trade",
            target_id=None,
            user_id=current_user.id if current_user else None,
            metadata={
                "trade_id": trade_id,
                "status": "settled",
                "payment_id": payment_event_db.payment_id,
                "transaction_hash": payment_result.get("transaction_hash")
            },
            request=None
        )
        
        logger.info(f"Trade {trade_id} settled with payment {payment_event_db.payment_id}")
        
        return {
            "status": "success",
            "trade_id": trade_id,
            "payment": payment_event.to_cdm_json(),
            "settlement": payment_result,
            "payment_id": payment_event_db.payment_id,
            "transaction_hash": payment_result.get("transaction_hash")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during trade settlement: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Trade settlement failed: {str(e)}"}
        )


@router.post("/loans/{loan_id}/disburse")
async def disburse_loan_with_payment(
    loan_id: str,
    payment_request: Optional[PaymentPayloadRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service)
):
    """
    Disburse loan with x402 payment verification.
    
    Requires payment before disbursing loan funds. Returns 402 Payment Required
    if payment payload is not provided.
    
    This endpoint:
    1. Gets loan asset and credit agreement
    2. Extracts borrower and lender parties
    3. Calculates disbursement amount from facilities
    4. Processes payment via x402 (lender pays borrower)
    5. Creates CDM PaymentEvent
    6. Updates loan asset disbursement status
    
    Args:
        loan_id: Loan identifier
        payment_request: Optional x402 payment payload
        db: Database session
        current_user: Current authenticated user
        payment_service: x402 payment service (optional)
        
    Returns:
        Disbursement result or 402 Payment Required response
    """
    from app.models.cdm import Party, Money, Currency
    from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
    from app.db.models import PaymentEvent as PaymentEventModel
    from fastapi.responses import JSONResponse
    
    try:
        # Step 1: Get loan asset
        loan_asset = db.query(LoanAsset).filter(LoanAsset.loan_id == loan_id).first()
        
        if not loan_asset:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Loan {loan_id} not found"}
            )
        
        # Step 2: Get credit agreement
        credit_agreement = get_credit_agreement_for_loan(loan_id, db)
        
        if not credit_agreement:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Credit agreement not found for loan {loan_id}"}
            )
        
        # Step 3: Extract borrower and lender from CDM
        borrower = None
        lender = None
        
        if credit_agreement.parties:
            for party in credit_agreement.parties:
                role_lower = party.role.lower()
                if "borrower" in role_lower:
                    borrower = party
                elif "lender" in role_lower or "creditor" in role_lower:
                    lender = party
        
        if not borrower or not lender:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Missing borrower or lender in credit agreement"}
            )
        
        # Step 4: Calculate disbursement amount
        total_commitment = Decimal("0")
        currency = Currency.USD
        
        if credit_agreement.facilities:
            for facility in credit_agreement.facilities:
                if facility.commitment_amount:
                    total_commitment += facility.commitment_amount.amount
                    if not currency:
                        currency = facility.commitment_amount.currency
        
        if total_commitment <= 0:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "No commitment amount found in facilities"}
            )
        
        # Step 5: Process payment via x402 (lender disburses to borrower)
        if not payment_service:
            raise HTTPException(
                status_code=503,
                detail={"status": "error", "message": "x402 payment service is not available"}
            )
        
        payment_payload = payment_request.payment_payload if payment_request else None
        
        payment_result = await payment_service.process_payment_flow(
            amount=total_commitment,
            currency=currency,
            payer=lender,  # Lender disburses to borrower
            receiver=borrower,
            payment_type="loan_disbursement",
            payment_payload=payment_payload,
            cdm_reference={
                "loan_id": loan_id,
                "credit_agreement_id": credit_agreement.deal_id or credit_agreement.loan_identification_number
            }
        )
        
        # Step 6: Handle payment required (402 response)
        if payment_payload is None or payment_result.get("status") != "settled":
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "payment_request": payment_result.get("payment_request"),
                    "amount": str(total_commitment),
                    "currency": currency.value,
                    "payer": {
                        "id": lender.id,
                        "name": lender.name,
                        "lei": lender.lei
                    },
                    "receiver": {
                        "id": borrower.id,
                        "name": borrower.name,
                        "lei": borrower.lei
                    },
                    "facilitator_url": payment_service.facilitator_url,
                    "loan_id": loan_id
                }
            )
        
        # Step 7: Create CDM PaymentEvent using CDM-compliant factory method
        payment_event = PaymentEvent.from_cdm_party(
            payer=lender,
            receiver=borrower,
            amount=Money(amount=total_commitment, currency=currency),
            payment_type=PaymentType.LOAN_DISBURSEMENT,
            payment_method=PaymentMethod.X402
        )
        
        # Step 8: Update with loan and facility references
        facility_id = None
        if credit_agreement.facilities and len(credit_agreement.facilities) > 0:
            facility_id = credit_agreement.facilities[0].facility_name or credit_agreement.facilities[0].facility_type
        
        payment_event = payment_event.model_copy(update={
            "relatedLoanId": loan_id,
            "relatedFacilityId": facility_id,
            "x402PaymentDetails": {
                "payment_payload": payment_payload,
                "settlement": payment_result.get("settlement")
            },
            "transactionHash": payment_result.get("transaction_hash")
        })
        
        # Step 9: Transition through state machine: PENDING -> VERIFIED -> SETTLED
        payment_event = payment_event.transition_to_verified()
        payment_event = payment_event.transition_to_settled(payment_result.get("transaction_hash", ""))
        
        # Step 10: Save payment event to database
        payment_event_db = PaymentEventModel(
            payment_id=payment_event.paymentIdentifier.assignedIdentifier[0]["identifier"]["value"],
            payment_method=payment_event.paymentMethod.value,
            payment_type=payment_event.paymentType.value,
            payer_id=payment_event.payerPartyReference.globalReference,
            payer_name=lender.name,
            receiver_id=payment_event.receiverPartyReference.globalReference,
            receiver_name=borrower.name,
            amount=payment_event.paymentAmount.amount,
            currency=payment_event.paymentAmount.currency.value,
            status=payment_event.paymentStatus.value,
            x402_payment_payload=payment_payload,
            x402_verification=payment_result.get("verification"),
            x402_settlement=payment_result.get("settlement"),
            transaction_hash=payment_result.get("transaction_hash"),
            related_loan_id=loan_id,
            related_facility_id=facility_id,
            cdm_event=payment_event.to_cdm_json(),
            settled_at=datetime.utcnow()
        )
        db.add(payment_event_db)
        
        # Step 11: Update loan asset disbursement status
        # Note: LoanAsset model may need disbursement_status and disbursement_date fields
        # For now, we'll log it in asset_metadata
        if hasattr(loan_asset, 'asset_metadata'):
            if loan_asset.asset_metadata is None:
                loan_asset.asset_metadata = {}
            loan_asset.asset_metadata["disbursement_status"] = "disbursed"
            loan_asset.asset_metadata["disbursement_date"] = datetime.utcnow().isoformat()
            loan_asset.asset_metadata["disbursement_amount"] = str(total_commitment)
            loan_asset.asset_metadata["disbursement_currency"] = currency.value
            loan_asset.asset_metadata["payment_id"] = payment_event_db.payment_id
        
        db.commit()
        
        # Step 12: Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="loan_asset",
            target_id=loan_asset.id,
            user_id=current_user.id if current_user else None,
            metadata={
                "loan_id": loan_id,
                "action": "disbursement",
                "amount": str(total_commitment),
                "currency": currency.value,
                "payment_id": payment_event_db.payment_id,
                "transaction_hash": payment_result.get("transaction_hash")
            },
            request=None
        )
        
        logger.info(f"Loan {loan_id} disbursed with payment {payment_event_db.payment_id}")
        
        return {
            "status": "success",
            "loan_id": loan_id,
            "disbursement_amount": str(total_commitment),
            "currency": currency.value,
            "payment": payment_event.to_cdm_json(),
            "payment_id": payment_event_db.payment_id,
            "transaction_hash": payment_result.get("transaction_hash")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during loan disbursement: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Loan disbursement failed: {str(e)}"}
        )


@router.post("/loans/{loan_id}/penalty-payment")
async def penalty_payment(
    loan_id: str,
    payment_request: Optional[PaymentPayloadRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_service: Optional[X402PaymentService] = Depends(get_x402_payment_service)
):
    """
    Process penalty payment for loan breach.
    
    When a loan asset breaches its sustainability targets (NDVI below threshold),
    a penalty payment is required. This endpoint processes the penalty payment via x402.
    
    Args:
        loan_id: Loan identifier
        payment_request: Optional x402 payment payload
        db: Database session
        current_user: Current authenticated user
        payment_service: x402 payment service (optional)
        
    Returns:
        Penalty payment result or 402 Payment Required response
    """
    from app.models.cdm import Party, Money, Currency
    from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
    from app.db.models import PaymentEvent as PaymentEventModel
    from fastapi.responses import JSONResponse
    
    try:
        # Step 1: Get loan asset
        loan_asset = db.query(LoanAsset).filter(LoanAsset.loan_id == loan_id).first()
        
        if not loan_asset:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Loan {loan_id} not found"}
            )
        
        # Step 2: Verify breach status
        if loan_asset.risk_status != RiskStatus.BREACH:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": f"Loan {loan_id} is not in breach status. Current status: {loan_asset.risk_status}"
                }
            )
        
        # Step 3: Get credit agreement
        credit_agreement = get_credit_agreement_for_loan(loan_id, db)
        
        if not credit_agreement:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Credit agreement not found for loan {loan_id}"}
            )
        
        # Step 4: Extract borrower and lender
        borrower = None
        lender = None
        
        if credit_agreement.parties:
            for party in credit_agreement.parties:
                role_lower = party.role.lower()
                if "borrower" in role_lower:
                    borrower = party
                elif "lender" in role_lower or "creditor" in role_lower:
                    lender = party
        
        if not borrower or not lender:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "Missing borrower or lender in credit agreement"}
            )
        
        # Step 5: Calculate penalty amount
        # Penalty is calculated based on penalty_bps and principal amount
        if not credit_agreement.facilities or not credit_agreement.facilities[0].commitment_amount:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "No commitment amount found in facilities"}
            )
        
        facility = credit_agreement.facilities[0]
        principal = facility.commitment_amount.amount
        currency = facility.commitment_amount.currency
        
        # Calculate penalty: principal * (penalty_bps / 10000)
        penalty_bps = loan_asset.penalty_bps or 50.0  # Default 50 bps
        penalty_amount = principal * (Decimal(str(penalty_bps)) / Decimal("10000"))
        
        # Step 6: Process payment via x402 (borrower pays lender penalty)
        if not payment_service:
            raise HTTPException(
                status_code=503,
                detail={"status": "error", "message": "x402 payment service is not available"}
            )
        
        payment_payload = payment_request.payment_payload if payment_request else None
        
        payment_result = await payment_service.process_payment_flow(
            amount=penalty_amount,
            currency=currency,
            payer=borrower,  # Borrower pays penalty to lender
            receiver=lender,
            payment_type="penalty_payment",
            payment_payload=payment_payload,
            cdm_reference={
                "loan_id": loan_id,
                "breach_ndvi_score": loan_asset.last_verified_score,
                "penalty_bps": penalty_bps
            }
        )
        
        # Step 7: Handle payment required (402 response)
        if payment_payload is None or payment_result.get("status") != "settled":
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "payment_request": payment_result.get("payment_request"),
                    "amount": str(penalty_amount),
                    "currency": currency.value,
                    "penalty_bps": penalty_bps,
                    "payer": {
                        "id": borrower.id,
                        "name": borrower.name,
                        "lei": borrower.lei
                    },
                    "receiver": {
                        "id": lender.id,
                        "name": lender.name,
                        "lei": lender.lei
                    },
                    "facilitator_url": payment_service.facilitator_url,
                    "loan_id": loan_id,
                    "breach_reason": f"NDVI score {loan_asset.last_verified_score} below threshold {loan_asset.spt_threshold}"
                }
            )
        
        # Step 8: Create CDM PaymentEvent
        payment_event = PaymentEvent.from_cdm_party(
            payer=borrower,
            receiver=lender,
            amount=Money(amount=penalty_amount, currency=currency),
            payment_type=PaymentType.PENALTY_PAYMENT,
            payment_method=PaymentMethod.X402
        )
        
        # Update with loan and breach information
        facility_id = None
        if credit_agreement.facilities and len(credit_agreement.facilities) > 0:
            facility_id = credit_agreement.facilities[0].facility_name or credit_agreement.facilities[0].facility_type
        
        payment_event = payment_event.model_copy(update={
            "relatedLoanId": loan_id,
            "relatedFacilityId": facility_id,
            "x402PaymentDetails": {
                "payment_payload": payment_payload,
                "settlement": payment_result.get("settlement"),
                "breach_ndvi_score": loan_asset.last_verified_score,
                "penalty_bps": penalty_bps
            },
            "transactionHash": payment_result.get("transaction_hash")
        })
        
        # Step 9: Transition through state machine
        payment_event = payment_event.transition_to_verified()
        payment_event = payment_event.transition_to_settled(payment_result.get("transaction_hash", ""))
        
        # Step 10: Save payment event to database
        payment_event_db = PaymentEventModel(
            payment_id=payment_event.paymentIdentifier.assignedIdentifier[0]["identifier"]["value"],
            payment_method=payment_event.paymentMethod.value,
            payment_type=payment_event.paymentType.value,
            payer_id=payment_event.payerPartyReference.globalReference,
            payer_name=borrower.name,
            receiver_id=payment_event.receiverPartyReference.globalReference,
            receiver_name=lender.name,
            amount=payment_event.paymentAmount.amount,
            currency=payment_event.paymentAmount.currency.value,
            status=payment_event.paymentStatus.value,
            x402_payment_payload=payment_payload,
            x402_verification=payment_result.get("verification"),
            x402_settlement=payment_result.get("settlement"),
            transaction_hash=payment_result.get("transaction_hash"),
            related_loan_id=loan_id,
            related_facility_id=facility_id,
            cdm_event=payment_event.to_cdm_json(),
            settled_at=datetime.utcnow()
        )
        db.add(payment_event_db)
        
        # Step 11: Update loan asset metadata to mark penalty as paid
        if loan_asset.asset_metadata is None:
            loan_asset.asset_metadata = {}
        loan_asset.asset_metadata["penalty_payment_required"] = False
        loan_asset.asset_metadata["penalty_payment_paid"] = True
        loan_asset.asset_metadata["penalty_payment_id"] = payment_event_db.payment_id
        loan_asset.asset_metadata["penalty_payment_date"] = datetime.utcnow().isoformat()
        loan_asset.asset_metadata["penalty_amount"] = str(penalty_amount)
        
        db.commit()
        
        # Step 12: Log audit action
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="loan_asset",
            target_id=loan_asset.id,
            user_id=current_user.id if current_user else None,
            metadata={
                "loan_id": loan_id,
                "action": "penalty_payment",
                "amount": str(penalty_amount),
                "currency": currency.value,
                "penalty_bps": penalty_bps,
                "payment_id": payment_event_db.payment_id,
                "transaction_hash": payment_result.get("transaction_hash"),
                "breach_ndvi_score": loan_asset.last_verified_score
            },
            request=None
        )
        
        logger.info(
            f"Penalty payment processed for loan {loan_id}: "
            f"payment_id={payment_event_db.payment_id}, "
            f"amount={penalty_amount}"
        )
        
        return {
            "status": "success",
            "loan_id": loan_id,
            "penalty_amount": str(penalty_amount),
            "currency": currency.value,
            "penalty_bps": penalty_bps,
            "payment": payment_event.to_cdm_json(),
            "payment_id": payment_event_db.payment_id,
            "transaction_hash": payment_result.get("transaction_hash"),
            "breach_ndvi_score": loan_asset.last_verified_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during penalty payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Penalty payment failed: {str(e)}"}
        )


@router.get("/policy/statistics")
async def get_policy_statistics(
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW, BLOCK, FLAG)"),
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated policy decision statistics.
    
    Provides comprehensive statistics about policy evaluations including:
    - Total decisions processed
    - Counts by decision type (ALLOW, BLOCK, FLAG)
    - Top rules applied
    - Counts by transaction type
    - Time series data for charting
    
    Args:
        transaction_type: Optional filter by transaction type
        decision: Optional filter by decision
        start_date: Optional start date filter (ISO 8601)
        end_date: Optional end date filter (ISO 8601)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with policy statistics
    """
    from app.services.policy_audit import get_policy_statistics as get_stats
    
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid start_date format: {start_date}. Use ISO 8601 format."}
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid end_date format: {end_date}. Use ISO 8601 format."}
                )
        
        # Get statistics
        stats = get_stats(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            transaction_type=transaction_type
        )
        
        # Apply decision filter if provided
        if decision:
            decision_upper = decision.upper()
            if decision_upper not in ["ALLOW", "BLOCK", "FLAG"]:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid decision: {decision}. Must be ALLOW, BLOCK, or FLAG."}
                )
            # Filter time series and other data by decision
            # Note: The statistics function already aggregates by decision,
            # so we just return the filtered decision count
            stats["decisions"] = {decision_upper: stats["decisions"].get(decision_upper, 0)}
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get policy statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get policy statistics: {str(e)}"}
        )


@router.get("/policy/decisions")
async def list_policy_decisions(
    transaction_id: Optional[str] = Query(None, description="Filter by transaction ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW, BLOCK, FLAG)"),
    rule_applied: Optional[str] = Query(None, description="Filter by rule name"),
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List policy decisions with filtering and pagination.
    
    Args:
        transaction_id: Filter by transaction ID
        transaction_type: Filter by transaction type
        decision: Filter by decision (ALLOW, BLOCK, FLAG)
        rule_applied: Filter by rule name
        start_date: Filter by start date (ISO 8601)
        end_date: Filter by end date (ISO 8601)
        limit: Maximum results (default 50, max 100)
        offset: Pagination offset
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of policy decisions
    """
    from app.services.policy_audit import get_policy_decisions
    
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid start_date format: {start_date}"}
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"status": "error", "message": f"Invalid end_date format: {end_date}"}
                )
        
        # Get decisions
        decisions = get_policy_decisions(
            db=db,
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            decision=decision,
            rule_applied=rule_applied,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "total": len(decisions),
            "limit": limit,
            "offset": offset,
            "decisions": [decision.to_dict() for decision in decisions]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list policy decisions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list policy decisions: {str(e)}"}
        )


@router.post("/trades/execute")
async def execute_trade(
    trade_request: TradeExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    policy_service: Optional[PolicyService] = Depends(get_policy_service)
):
    """
    Execute a trade with policy evaluation.
    
    This endpoint:
    1. Generates a CDM TradeExecution event
    2. Evaluates the trade against compliance policies
    3. Blocks, flags, or allows the trade based on policy decision
    4. Returns the trade execution result with policy decision
    
    Args:
        trade_request: Trade execution request with trade details
        db: Database session
        current_user: Current authenticated user
        policy_service: Policy service for compliance evaluation (optional)
        
    Returns:
        Trade execution result with policy decision and CDM events
    """
    from app.models.cdm_events import generate_cdm_trade_execution
    from app.db.models import PolicyDecision as PolicyDecisionModel
    from app.models.cdm import CreditAgreement
    
    try:
        logger.info(
            f"Trade execution request: trade_id={trade_request.trade_id}, "
            f"borrower={trade_request.borrower}, amount={trade_request.amount}"
        )
        
        # Step 1: Generate CDM TradeExecution event
        trade_event = generate_cdm_trade_execution(
            trade_id=trade_request.trade_id,
            borrower=trade_request.borrower,
            amount=trade_request.amount,
            rate=trade_request.rate
        )
        
        # Step 2: Get credit agreement if provided
        credit_agreement = None
        if trade_request.credit_agreement_id:
            doc = db.query(Document).filter(Document.id == trade_request.credit_agreement_id).first()
            if doc and doc.current_version_id:
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == doc.current_version_id
                ).first()
                if version and version.extracted_data:
                    try:
                        credit_agreement = CreditAgreement(**version.extracted_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse credit agreement from document: {e}")
        
        # Step 3: Policy evaluation (if enabled)
        policy_decision = None
        policy_evaluation_event = None
        
        if policy_service:
            try:
                # Evaluate trade execution for compliance
                policy_result = policy_service.evaluate_trade_execution(
                    cdm_event=trade_event,
                    credit_agreement=credit_agreement
                )
                
                # Create CDM PolicyEvaluation event
                from app.models.cdm_events import generate_cdm_policy_evaluation
                policy_evaluation_event = generate_cdm_policy_evaluation(
                    transaction_id=trade_request.trade_id,
                    transaction_type="trade_execution",
                    decision=policy_result.decision,
                    rule_applied=policy_result.rule_applied,
                    related_event_identifiers=[{
                        "eventIdentifier": {
                            "issuer": "CreditNexus",
                            "assignedIdentifier": [{
                                "identifier": {"value": trade_event["meta"]["globalKey"]}
                            }]
                        }
                    }],
                    evaluation_trace=policy_result.trace,
                    matched_rules=policy_result.matched_rules
                )
                
                # Handle BLOCK decision - prevent trade execution
                if policy_result.decision == "BLOCK":
                    logger.warning(
                        f"Policy evaluation BLOCKED trade execution: "
                        f"trade_id={trade_request.trade_id}, rule={policy_result.rule_applied}, "
                        f"trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=trade_request.trade_id,
                            transaction_type="trade_execution",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"trade_execution": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for trade execution
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with block decision.")
                        db.rollback()
                    
                    return {
                        "status": "blocked",
                        "decision": "BLOCK",
                        "rule": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id,
                        "message": f"Trade execution blocked by compliance policy: {policy_result.rule_applied}",
                        "cdm_event": policy_evaluation_event,
                        "trade_event": trade_event
                    }
                
                # Handle FLAG decision - allow but mark for review
                elif policy_result.decision == "FLAG":
                    logger.info(
                        f"Policy evaluation FLAGGED trade execution: "
                        f"trade_id={trade_request.trade_id}, rule={policy_result.rule_applied}, "
                        f"trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=trade_request.trade_id,
                            transaction_type="trade_execution",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"trade_execution": True, "requires_review": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for trade execution
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with trade execution.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id,
                        "requires_review": True
                    }
                
                # Handle ALLOW decision - log for audit
                else:
                    logger.debug(
                        f"Policy evaluation ALLOWED trade execution: "
                        f"trade_id={trade_request.trade_id}, trace_id={policy_result.trace_id}"
                    )
                    
                    # Log policy decision to audit trail
                    try:
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=trade_request.trade_id,
                            transaction_type="trade_execution",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            trace_id=policy_result.trace_id,
                            trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules,
                            additional_metadata={"trade_execution": True},
                            cdm_events=[policy_evaluation_event],
                            loan_asset_id=None,  # No loan asset for trade execution
                            user_id=current_user.id if current_user else None
                        )
                        db.add(policy_decision_db)
                        db.commit()
                    except Exception as e:
                        # Handle foreign key validation errors gracefully
                        logger.warning(f"Could not persist policy decision to database: {e}. Continuing with trade execution.")
                        db.rollback()
                    
                    policy_decision = {
                        "decision": policy_result.decision,
                        "rule_applied": policy_result.rule_applied,
                        "trace_id": policy_result.trace_id
                    }
                    
            except Exception as e:
                # Log policy evaluation errors but don't block trade
                logger.error(f"Policy evaluation failed for trade {trade_request.trade_id}: {e}", exc_info=True)
                # Continue with trade execution even if policy evaluation fails
        
        # Step 4: Return trade execution result
        return {
            "status": "executed",
            "trade_id": trade_request.trade_id,
            "trade_event": trade_event,
            "policy_decision": policy_decision,
            "cdm_events": (
                [trade_event, policy_evaluation_event]
                if policy_evaluation_event
                else [trade_event]
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during trade execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Trade execution failed: {str(e)}"}
        )


# ============================================================================
# LMA Template Generation API Endpoints
# ============================================================================

from app.templates.registry import TemplateRegistry
from app.generation.service import DocumentGenerationService
from app.db.models import LMATemplate, GeneratedDocument, TemplateFieldMapping


class GenerateDocumentRequest(BaseModel):
    """Request model for document generation.
    
    Either cdm_data or document_id must be provided:
    - If document_id is provided, CDM data will be loaded from that document
    - If cdm_data is provided, it will be used directly
    - If both are provided, document_id takes precedence
    """
    template_id: int = Field(..., description="Template ID")
    cdm_data: Optional[dict] = Field(None, description="CDM CreditAgreement data (optional if document_id provided)")
    document_id: Optional[int] = Field(None, description="Document ID to load CDM data from library (optional if cdm_data provided)")
    deal_id: Optional[int] = Field(None, description="Optional deal ID to load deal context and link generated document to deal")
    source_document_id: Optional[int] = Field(None, description="Optional source document ID for tracking")
    field_overrides: Optional[Dict[str, Any]] = Field(None, description="Optional field overrides to apply to CDM data before generation. Format: {\"parties[role='Borrower'].lei\": \"value\"}")
    
    @model_validator(mode='after')
    def validate_cdm_source(self) -> 'GenerateDocumentRequest':
        """Ensure either cdm_data or document_id is provided."""
        if not self.cdm_data and not self.document_id:
            raise ValueError("Either 'cdm_data' or 'document_id' must be provided")
        return self


class ExportRequest(BaseModel):
    """Request model for document export."""
    format: str = Field(..., description="Export format: 'word' or 'pdf'")


@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by template category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    List available LMA templates.
    
    Args:
        category: Optional category filter
        subcategory: Optional subcategory filter
        db: Database session
        current_user: Optional authenticated user (allows unauthenticated access)
        
    Returns:
        List of template metadata
    """
    try:
        templates = TemplateRegistry.list_templates(
            db,
            category,
            subcategory
        )
        
        return {
            "templates": [template.to_dict() for template in templates],
            "count": len(templates)
        }
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get template metadata by ID.
    
    Args:
        template_id: Template ID
        db: Database session
        current_user: Optional authenticated user (allows unauthenticated access)
        
    Returns:
        Template metadata
    """
    try:
        template = TemplateRegistry.get_template(db, template_id)
        return template.to_dict()
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Template not found: {str(e)}")


@router.get("/templates/{template_id}/requirements")
async def get_template_requirements(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get required CDM fields for a template.
    
    Args:
        template_id: Template ID
        db: Database session
        current_user: Optional authenticated user (allows unauthenticated access)
        
    Returns:
        Dictionary with required and optional fields
    """
    try:
        template = TemplateRegistry.get_template(db, template_id)
        required_fields = TemplateRegistry.get_required_fields(template)
        
        return {
            "template_id": template_id,
            "template_code": template.template_code,
            "required_fields": required_fields,
            "optional_fields": template.optional_fields or [],
            "ai_generated_sections": template.ai_generated_sections or [],
        }
    except Exception as e:
        logger.error(f"Error getting template requirements {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Template not found: {str(e)}")


class PreGenerationAnalysisRequest(BaseModel):
    """Request model for pre-generation analysis."""
    cdm_data: Optional[dict] = Field(None, description="CDM CreditAgreement data (optional if document_id provided)")
    document_id: Optional[int] = Field(None, description="Document ID to load CDM data from library (optional if cdm_data provided)")
    field_overrides: Optional[Dict[str, Any]] = Field(None, description="Optional field overrides to apply")
    
    @model_validator(mode='after')
    def validate_cdm_source(self) -> 'PreGenerationAnalysisRequest':
        """Ensure either cdm_data or document_id is provided."""
        if not self.cdm_data and not self.document_id:
            raise ValueError("Either 'cdm_data' or 'document_id' must be provided")
        return self


@router.post("/templates/{template_id}/pre-generation-analysis")
async def get_pre_generation_analysis(
    template_id: int,
    request: PreGenerationAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get pre-generation analysis for a template and CDM data.
    
    Provides:
    - Field completeness analysis
    - Clause cache predictions
    - Template compatibility assessment
    - Recommendations
    
    Args:
        template_id: Template ID
        request: Optional request body with cdm_data dict
        document_id: Optional document ID to load CDM data from library (query param)
    """
    try:
        from app.generation.analyzer import analyze_pre_generation
        from app.models.cdm import CreditAgreement
        from app.templates.registry import TemplateRegistry
        
        # Get template
        template = TemplateRegistry.get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        
        # Get CDM data
        cdm_data = None
        field_overrides = request.field_overrides
        
        if request.cdm_data:
            # Get from request body
            try:
                cdm_data = CreditAgreement.model_validate(request.cdm_data)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid CDM data in request: {e}"
                )
        
        if not cdm_data and request.document_id:
            # Load from document library
            document = db.query(Document).filter(Document.id == request.document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail=f"Document with ID {request.document_id} not found")
            
            # Get latest version with CDM data
            version = db.query(DocumentVersion).filter(
                DocumentVersion.document_id == request.document_id
            ).order_by(DocumentVersion.version_number.desc()).first()
            
            if not version or not version.extracted_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document {request.document_id} does not have CDM data"
                )
            
            # Convert extracted_data to CreditAgreement
            try:
                cdm_data = CreditAgreement.model_validate(version.extracted_data)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse CDM data from document: {e}"
                )
        
        if not cdm_data:
            raise HTTPException(
                status_code=400,
                detail="CDM data is required. Provide either 'cdm_data' in request body or 'document_id' query parameter"
            )
        
        # Perform analysis
        analysis = analyze_pre_generation(
            db=db,
            template_id=template_id,
            cdm_data=cdm_data,
            field_overrides=field_overrides
        )
        
        return {
            "status": "success",
            "template_id": template_id,
            "template_code": template.template_code,
            "template_name": template.name,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform pre-generation analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pre-generation analysis failed: {str(e)}"
        )


@router.get("/templates/{template_id}/mappings")
async def get_template_mappings(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get CDM field mappings for a template.
    
    Args:
        template_id: Template ID
        db: Database session
        current_user: Optional authenticated user (allows unauthenticated access)
        
    Returns:
        List of field mappings
    """
    try:
        template = TemplateRegistry.get_template(db, template_id)
        mappings = TemplateRegistry.get_field_mappings(db, template_id)
        
        return {
            "template_id": template_id,
            "template_code": template.template_code,
            "mappings": [mapping.to_dict() for mapping in mappings],
            "count": len(mappings)
        }
    except Exception as e:
        logger.error(f"Error getting template mappings {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Template not found: {str(e)}")


@router.post("/templates/generate")
async def generate_document(
    request: GenerateDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Generate a document from a template using CDM data.
    
    Args:
        request: GenerateDocumentRequest with template_id and either cdm_data or document_id
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Generated document metadata
    """
    try:
        # Load CDM data from document if document_id is provided
        cdm_data_dict = request.cdm_data
        
        if request.document_id:
            # Load document from database
            document = db.query(Document).filter(Document.id == request.document_id).first()
            if not document:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document with ID {request.document_id} not found"
                )
            
            # Check if user has access to this document (skip check for demo documents)
            # Demo documents may not have uploaded_by set
            if document.uploaded_by is not None and document.uploaded_by != current_user.id:
                # Check if this is a demo document by checking deal.is_demo column
                is_demo = False
                if document.deal:
                    is_demo = getattr(document.deal, 'is_demo', False)
                
                if not is_demo:
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have access to this document"
                    )
            
            # Try to get CDM data from document
            if document.source_cdm_data:
                cdm_data_dict = document.source_cdm_data
            elif document.current_version_id:
                # Try to get from current version
                version = db.query(DocumentVersion).filter(
                    DocumentVersion.id == document.current_version_id
                ).first()
                if version and version.extracted_data:
                    cdm_data_dict = version.extracted_data
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Document {request.document_id} has no CDM data available"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document {request.document_id} has no CDM data available"
                )
        
        if not cdm_data_dict:
            raise HTTPException(
                status_code=400,
                detail="CDM data is required. Provide either 'cdm_data' or 'document_id'"
            )
        
        # Parse CDM data
        try:
            cdm_agreement = CreditAgreement(**cdm_data_dict)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CDM data: {str(e)}"
            )
        
        # Use document_id as source_document_id if not explicitly provided
        source_document_id = request.source_document_id or request.document_id
        
        # Generate document
        generation_service = DocumentGenerationService()
        try:
            generated_doc = generation_service.generate_document(
                db=db,
                template_id=request.template_id,
                cdm_data=cdm_agreement,
                user_id=current_user.id,
                source_document_id=source_document_id,
                deal_id=request.deal_id,
                field_overrides=request.field_overrides
            )
        except Exception as e:
            raise
        
        return {
            "id": generated_doc.id,
            "template_id": generated_doc.template_id,
            "source_document_id": generated_doc.source_document_id,
            "file_path": generated_doc.file_path,
            "status": generated_doc.status,
            "generation_summary": generated_doc.generation_summary,
            "created_at": generated_doc.created_at.isoformat() if generated_doc.created_at else None,
        }
        
    except ValueError as e:
        logger.error(f"Validation error during document generation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        logger.error(f"I/O error during document generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during document generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")


# ============================================================================
# Clause Cache Management API
# ============================================================================

class ClauseUpdateRequest(BaseModel):
    """Request model for updating a cached clause."""
    clause_content: str = Field(..., description="Updated clause content")


@router.get("/clauses")
async def list_clauses(
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    field_name: Optional[str] = Query(None, description="Filter by field name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List cached clauses with optional filters.
    
    Args:
        template_id: Optional template ID filter
        field_name: Optional field name filter (e.g., "REPRESENTATIONS_AND_WARRANTIES")
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of cached clauses with metadata
    """
    try:
        cache_service = ClauseCacheService()
        clauses = cache_service.list_clauses(
            db=db,
            template_id=template_id,
            field_name=field_name,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "clauses": [clause.to_dict() for clause in clauses],
            "count": len(clauses)
        }
    except Exception as e:
        logger.error(f"Error listing clauses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list clauses: {str(e)}"}
        )


@router.get("/clauses/{clause_id}")
async def get_clause(
    clause_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific cached clause by ID.
    
    Args:
        clause_id: Clause cache ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Clause cache details
    """
    try:
        clause = db.query(ClauseCache).filter(ClauseCache.id == clause_id).first()
        
        if not clause:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Clause not found"}
            )
        
        # Load template info
        template = db.query(LMATemplate).filter(LMATemplate.id == clause.template_id).first()
        
        clause_dict = clause.to_dict()
        if template:
            clause_dict["template"] = {
                "id": template.id,
                "code": template.template_code,
                "name": template.name
            }
        
        return {
            "status": "success",
            "clause": clause_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clause {clause_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get clause: {str(e)}"}
        )


@router.put("/clauses/{clause_id}")
async def update_clause(
    clause_id: int,
    request: ClauseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Update a cached clause's content.
    
    Args:
        clause_id: Clause cache ID
        request: Clause update request with new content
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated clause details
    """
    try:
        clause = db.query(ClauseCache).filter(ClauseCache.id == clause_id).first()
        
        if not clause:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Clause not found"}
            )
        
        # Update clause content
        clause.clause_content = request.clause_content
        clause.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(clause)
        
        logger.info(f"Updated clause {clause_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "clause": clause.to_dict(),
            "message": "Clause updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating clause {clause_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to update clause: {str(e)}"}
        )


@router.delete("/clauses/{clause_id}")
async def delete_clause(
    clause_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Delete a cached clause.
    
    Args:
        clause_id: Clause cache ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Success message
    """
    try:
        cache_service = ClauseCacheService()
        deleted = cache_service.delete_clause(db=db, clause_id=clause_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Clause not found"}
            )
        
        logger.info(f"Deleted clause {clause_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Clause deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting clause {clause_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to delete clause: {str(e)}"}
        )


@router.get("/generated-documents")
async def list_generated_documents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    List generated documents with pagination.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
        template_id: Optional template ID filter
        status: Optional status filter
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Paginated list of generated documents
    """
    try:
        query = db.query(GeneratedDocument)
        
        # Apply filters
        if template_id:
            query = query.filter(GeneratedDocument.template_id == template_id)
        if status:
            query = query.filter(GeneratedDocument.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        documents = query.order_by(GeneratedDocument.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "documents": [doc.to_dict() for doc in documents],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Error listing generated documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/generated-documents/{document_id}")
async def get_generated_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get generated document details by ID.
    
    Args:
        document_id: Generated document ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Generated document details
    """
    try:
        doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Generated document {document_id} not found")
        
        return doc.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generated document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.post("/generated-documents/{document_id}/export")
async def export_generated_document(
    document_id: int,
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Export generated document as Word or PDF.
    
    Args:
        document_id: Generated document ID
        request: ExportRequest with format
        db: Database session
        current_user: Authenticated user
        
    Returns:
        File download response
    """
    try:
        from pathlib import Path
        from fastapi.responses import FileResponse
        
        doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Generated document {document_id} not found")
        
        if not doc.file_path:
            raise HTTPException(status_code=400, detail="Document file not found")
        
        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found on disk")
        
        # For Word format, return as-is
        if request.format.lower() == "word":
            return FileResponse(
                path=str(file_path),
                filename=file_path.name,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        # For PDF, convert (if implemented)
        elif request.format.lower() == "pdf":
            # For now, raise NotImplementedError
            # In production, implement PDF conversion
            raise HTTPException(
                status_code=501,
                detail="PDF export not yet implemented. Use Word format for now."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ============================================================================
# Application Management API Endpoints
# ============================================================================

from app.db.models import Application, Inquiry, Meeting, ApplicationType, ApplicationStatus, InquiryType, InquiryStatus
from app.services.ics_generator import generate_ics_file, save_ics_file, get_ics_file_path
from fastapi.responses import FileResponse
from pathlib import Path


class ApplicationCreate(BaseModel):
    """Request model for creating an application."""
    application_type: str = Field(..., description="Type: 'individual' or 'business'")
    application_data: Optional[dict] = Field(None, description="General application form data")
    business_data: Optional[dict] = Field(None, description="Business-specific data (debt selling, loan buying)")
    individual_data: Optional[dict] = Field(None, description="Individual-specific data")


class ApplicationUpdate(BaseModel):
    """Request model for updating an application."""
    application_data: Optional[dict] = None
    business_data: Optional[dict] = None
    individual_data: Optional[dict] = None


class ApplicationResponse(BaseModel):
    """Response model for application."""
    id: int
    application_type: str
    status: str
    user_id: Optional[int]
    submitted_at: Optional[str]
    reviewed_at: Optional[str]
    approved_at: Optional[str]
    rejected_at: Optional[str]
    rejection_reason: Optional[str]
    application_data: Optional[dict]
    business_data: Optional[dict]
    individual_data: Optional[dict]
    created_at: str
    updated_at: str


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    request: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new application."""
    # Validate application type
    if request.application_type not in [ApplicationType.INDIVIDUAL.value, ApplicationType.BUSINESS.value]:
        raise HTTPException(status_code=400, detail="Invalid application_type. Must be 'individual' or 'business'")
    
    application = Application(
        application_type=request.application_type,
        status=ApplicationStatus.DRAFT.value,
        user_id=current_user.id if current_user else None,
        application_data=request.application_data,
        business_data=request.business_data,
        individual_data=request.individual_data
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    
    if current_user:
        log_audit_action(db, AuditAction.CREATE, "application", application.id, current_user.id)
    
    return ApplicationResponse(**application.to_dict())


@router.get("/applications", response_model=List[ApplicationResponse])
async def list_applications(
    status: Optional[str] = Query(None),
    application_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List applications with filtering and pagination."""
    query = db.query(Application)
    
    # Filter by user (unless admin)
    if current_user.role != "admin":
        query = query.filter(Application.user_id == current_user.id)
    
    # Filter by status
    if status:
        query = query.filter(Application.status == status)
    
    # Filter by type
    if application_type:
        query = query.filter(Application.application_type == application_type)
    
    # Pagination
    offset = (page - 1) * limit
    applications = query.order_by(Application.created_at.desc()).offset(offset).limit(limit).all()
    
    return [ApplicationResponse(**app.to_dict()) for app in applications]


@router.post("/applications/{application_id}/create-deal")
async def create_deal_from_application(
    application_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a deal from an approved application.
    
    Args:
        application_id: The application ID.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The created deal.
    """
    try:
        from app.services.deal_service import DealService
        from app.db.models import Application, ApplicationStatus
        
        # Verify application exists
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Application {application_id} not found"}
            )
        
        # Check permission (user can only create deals from their own applications, or admin)
        if application.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "Not authorized to create deal from this application"}
            )
        
        # Check if application is approved
        if application.status != ApplicationStatus.APPROVED.value:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Application must be approved to create a deal. Current status: {application.status}"}
            )
        
        # Check if deal already exists for this application
        existing_deal = db.query(Deal).filter(Deal.application_id == application_id).first()
        if existing_deal:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": f"Deal already exists for this application: {existing_deal.deal_id}"}
            )
        
        # Create deal using DealService
        deal_service = DealService(db)
        deal = deal_service.create_deal_from_application(
            application_id=application_id,
            deal_type=None,  # Will be inferred from application type
            deal_data=application.application_data
        )
        
        db.commit()
        db.refresh(deal)
        
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="deal",
            target_id=deal.id,
            user_id=current_user.id,
            metadata={"application_id": application_id, "deal_id": deal.deal_id},
            request=request
        )
        
        logger.info(f"Created deal {deal.deal_id} from application {application_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Deal created successfully",
            "deal": deal.to_dict()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": str(e)}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deal from application: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create deal: {str(e)}"}
        )


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get application by ID."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this application")
    
    return ApplicationResponse(**application.to_dict())


@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    request: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an application."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this application")
    
    # Only allow updates if status is DRAFT or SUBMITTED
    if application.status not in [ApplicationStatus.DRAFT.value, ApplicationStatus.SUBMITTED.value]:
        raise HTTPException(status_code=400, detail="Cannot update application in current status")
    
    # Update fields
    if request.application_data is not None:
        application.application_data = request.application_data
    if request.business_data is not None:
        application.business_data = request.business_data
    if request.individual_data is not None:
        application.individual_data = request.individual_data
    
    db.commit()
    db.refresh(application)
    
    log_audit_action(db, AuditAction.UPDATE, "application", application.id, current_user.id)
    
    return ApplicationResponse(**application.to_dict())


@router.post("/applications/{application_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit an application for review."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Check authorization
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this application")
    
    if application.status != ApplicationStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Application can only be submitted from DRAFT status")
    
    application.status = ApplicationStatus.SUBMITTED.value
    application.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    
    log_audit_action(db, AuditAction.UPDATE, "application", application.id, current_user.id, metadata={"action": "submit"})
    
    return ApplicationResponse(**application.to_dict())


@router.post("/applications/{application_id}/approve", response_model=ApplicationResponse)
async def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Approve an application (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application.status = ApplicationStatus.APPROVED.value
    application.approved_at = datetime.utcnow()
    application.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    
    log_audit_action(db, AuditAction.APPROVE, "application", application.id, current_user.id)
    
    return ApplicationResponse(**application.to_dict())


@router.post("/applications/{application_id}/reject", response_model=ApplicationResponse)
async def reject_application(
    application_id: int,
    rejection_reason: str = Query(..., description="Reason for rejection"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Reject an application (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application.status = ApplicationStatus.REJECTED.value
    application.rejected_at = datetime.utcnow()
    application.reviewed_at = datetime.utcnow()
    application.rejection_reason = rejection_reason
    db.commit()
    db.refresh(application)
    
    log_audit_action(db, AuditAction.REJECT, "application", application.id, current_user.id, metadata={"rejection_reason": rejection_reason})
    
    return ApplicationResponse(**application.to_dict())


# ============================================================================
# Inquiry Management API Endpoints
# ============================================================================


class InquiryCreate(BaseModel):
    """Request model for creating an inquiry."""
    inquiry_type: str = Field(..., description="Type: 'general', 'application_status', 'technical_support', 'sales'")
    subject: str = Field(..., description="Inquiry subject")
    message: str = Field(..., description="Inquiry message")
    application_id: Optional[int] = Field(None, description="Optional linked application ID")
    priority: Optional[str] = Field("normal", description="Priority: 'low', 'normal', 'high', 'urgent'")


class InquiryUpdate(BaseModel):
    """Request model for updating an inquiry."""
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    response_message: Optional[str] = None


class InquiryResponse(BaseModel):
    """Response model for inquiry."""
    id: int
    inquiry_type: str
    status: str
    priority: str
    application_id: Optional[int]
    user_id: Optional[int]
    email: str
    name: str
    subject: str
    message: str
    assigned_to: Optional[int]
    resolved_at: Optional[str]
    resolved_by: Optional[int]
    response_message: Optional[str]
    created_at: str
    updated_at: str


@router.post("/inquiries", response_model=InquiryResponse)
async def create_inquiry(
    request: InquiryCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new inquiry."""
    inquiry = Inquiry(
        inquiry_type=request.inquiry_type,
        status=InquiryStatus.NEW.value,
        priority=request.priority or "normal",
        application_id=request.application_id,
        user_id=current_user.id if current_user else None,
        email=current_user.email if current_user else "",
        name=current_user.display_name if current_user else "",
        subject=request.subject,
        message=request.message
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    if current_user:
        log_audit_action(db, AuditAction.CREATE, "inquiry", inquiry.id, current_user.id)
    
    return InquiryResponse(**inquiry.to_dict())


@router.get("/inquiries", response_model=List[InquiryResponse])
async def list_inquiries(
    status: Optional[str] = Query(None),
    inquiry_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List inquiries with filtering and pagination."""
    query = db.query(Inquiry)
    
    # Filter by user (unless admin)
    if current_user.role != "admin":
        query = query.filter(Inquiry.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Inquiry.status == status)
    if inquiry_type:
        query = query.filter(Inquiry.inquiry_type == inquiry_type)
    if priority:
        query = query.filter(Inquiry.priority == priority)
    
    # Pagination
    offset = (page - 1) * limit
    inquiries = query.order_by(Inquiry.created_at.desc()).offset(offset).limit(limit).all()
    
    return [InquiryResponse(**inq.to_dict()) for inq in inquiries]


@router.get("/inquiries/{inquiry_id}", response_model=InquiryResponse)
async def get_inquiry(
    inquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inquiry by ID."""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    # Check authorization
    if current_user.role != "admin" and inquiry.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this inquiry")
    
    return InquiryResponse(**inquiry.to_dict())


@router.put("/inquiries/{inquiry_id}", response_model=InquiryResponse)
async def update_inquiry(
    inquiry_id: int,
    request: InquiryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an inquiry."""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    # Check authorization
    if current_user.role != "admin" and inquiry.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this inquiry")
    
    # Update fields
    if request.status is not None:
        inquiry.status = request.status
    if request.priority is not None:
        inquiry.priority = request.priority
    if request.assigned_to is not None and current_user.role == "admin":
        inquiry.assigned_to = request.assigned_to
    if request.response_message is not None:
        inquiry.response_message = request.response_message
    
    db.commit()
    db.refresh(inquiry)
    
    log_audit_action(db, AuditAction.UPDATE, "inquiry", inquiry.id, current_user.id)
    
    return InquiryResponse(**inquiry.to_dict())


@router.post("/inquiries/{inquiry_id}/assign", response_model=InquiryResponse)
async def assign_inquiry(
    inquiry_id: int,
    user_id: int = Query(..., description="User ID to assign inquiry to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Assign an inquiry to a user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    inquiry.assigned_to = user_id
    inquiry.status = InquiryStatus.IN_PROGRESS.value
    db.commit()
    db.refresh(inquiry)
    
    log_audit_action(db, AuditAction.UPDATE, "inquiry", inquiry.id, current_user.id, metadata={"action": "assign", "assigned_to": user_id})
    
    return InquiryResponse(**inquiry.to_dict())


@router.post("/inquiries/{inquiry_id}/resolve", response_model=InquiryResponse)
async def resolve_inquiry(
    inquiry_id: int,
    response_message: str = Query(..., description="Response message"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Resolve an inquiry."""
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    # Check authorization
    if current_user.role != "admin" and inquiry.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to resolve this inquiry")
    
    inquiry.status = InquiryStatus.RESOLVED.value
    inquiry.resolved_at = datetime.utcnow()
    inquiry.resolved_by = current_user.id
    inquiry.response_message = response_message
    db.commit()
    db.refresh(inquiry)
    
    log_audit_action(db, AuditAction.UPDATE, "inquiry", inquiry.id, current_user.id, metadata={"action": "resolve"})
    
    return InquiryResponse(**inquiry.to_dict())


# ============================================================================
# Meeting Management API Endpoints
# ============================================================================


class MeetingCreate(BaseModel):
    """Request model for creating a meeting."""
    title: str = Field(..., description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    scheduled_at: str = Field(..., description="Scheduled date/time (ISO 8601)")
    duration_minutes: int = Field(30, ge=15, le=480, description="Duration in minutes")
    meeting_type: Optional[str] = Field(None, description="Meeting type")
    application_id: Optional[int] = Field(None, description="Optional linked application ID")
    attendees: Optional[List[dict]] = Field(None, description="List of attendees {email, name, status}")
    meeting_link: Optional[str] = Field(None, description="Zoom/Teams meeting link")


class MeetingUpdate(BaseModel):
    """Request model for updating a meeting."""
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    meeting_type: Optional[str] = None
    attendees: Optional[List[dict]] = None
    meeting_link: Optional[str] = None


class MeetingResponse(BaseModel):
    """Response model for meeting."""
    id: int
    title: str
    description: Optional[str]
    scheduled_at: str
    duration_minutes: int
    meeting_type: Optional[str]
    application_id: Optional[int]
    organizer_id: int
    attendees: Optional[List[dict]]
    meeting_link: Optional[str]
    ics_file_path: Optional[str]
    created_at: str
    updated_at: str


@router.post("/meetings", response_model=MeetingResponse)
async def create_meeting(
    request: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new meeting."""
    # Parse scheduled_at
    try:
        scheduled_at = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scheduled_at format. Use ISO 8601 format.")
    
    # Validate scheduled_at is in future
    if scheduled_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
    
    meeting = Meeting(
        title=request.title,
        description=request.description,
        scheduled_at=scheduled_at,
        duration_minutes=request.duration_minutes,
        meeting_type=request.meeting_type,
        application_id=request.application_id,
        organizer_id=current_user.id,
        attendees=request.attendees,
        meeting_link=request.meeting_link
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    log_audit_action(db, AuditAction.CREATE, "meeting", meeting.id, current_user.id)
    
    return MeetingResponse(**meeting.to_dict())


@router.get("/meetings", response_model=List[MeetingResponse])
async def list_meetings(
    application_id: Optional[int] = Query(None),
    organizer_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List meetings with filtering."""
    query = db.query(Meeting)
    
    # Filter by application
    if application_id:
        query = query.filter(Meeting.application_id == application_id)
    
    # Filter by organizer
    if organizer_id:
        query = query.filter(Meeting.organizer_id == organizer_id)
    elif current_user.role != "admin":
        # Non-admins only see their own meetings
        query = query.filter(Meeting.organizer_id == current_user.id)
    
    # Filter by date range
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Meeting.scheduled_at >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Meeting.scheduled_at <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    meetings = query.order_by(Meeting.scheduled_at.asc()).all()
    
    return [MeetingResponse(**mtg.to_dict()) for mtg in meetings]


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get meeting by ID."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization (organizer or admin)
    if current_user.role != "admin" and meeting.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this meeting")
    
    return MeetingResponse(**meeting.to_dict())


@router.put("/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    request: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Update a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization (organizer or admin)
    if current_user.role != "admin" and meeting.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this meeting")
    
    # Update fields
    if request.title is not None:
        meeting.title = request.title
    if request.description is not None:
        meeting.description = request.description
    if request.scheduled_at is not None:
        try:
            scheduled_at = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))
            if scheduled_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
            meeting.scheduled_at = scheduled_at
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format")
    if request.duration_minutes is not None:
        meeting.duration_minutes = request.duration_minutes
    if request.meeting_type is not None:
        meeting.meeting_type = request.meeting_type
    if request.attendees is not None:
        meeting.attendees = request.attendees
    if request.meeting_link is not None:
        meeting.meeting_link = request.meeting_link
    
    db.commit()
    db.refresh(meeting)
    
    log_audit_action(db, AuditAction.UPDATE, "meeting", meeting.id, current_user.id)
    
    return MeetingResponse(**meeting.to_dict())


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Delete a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization (organizer or admin)
    if current_user.role != "admin" and meeting.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this meeting")
    
    log_audit_action(db, AuditAction.DELETE, "meeting", meeting.id, current_user.id)
    
    db.delete(meeting)
    db.commit()
    
    return {"message": "Meeting deleted successfully"}


@router.post("/meetings/{meeting_id}/generate-ics")
async def generate_meeting_ics(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate .ics file for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization
    if current_user.role != "admin" and meeting.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to generate ICS for this meeting")
    
    # Generate and save ICS file
    file_path = save_ics_file(meeting, db)
    
    return {"message": "ICS file generated successfully", "file_path": file_path}


@router.get("/meetings/{meeting_id}/ics")
async def download_meeting_ics(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download .ics file for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check authorization
    if current_user.role != "admin" and meeting.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to download ICS for this meeting")
    
    # Get or generate ICS file
    file_path = get_ics_file_path(meeting)
    if not file_path:
        # Generate if doesn't exist
        file_path = save_ics_file(meeting, db)
    
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="ICS file not found")
    
    return FileResponse(
        path=str(path),
        filename=f"meeting_{meeting_id}.ics",
        media_type="text/calendar"
    )


# ============================================================================
# Wallet Authentication API Endpoints
# ============================================================================


class WalletAuthRequest(BaseModel):
    """Request model for wallet authentication."""
    wallet_address: str = Field(..., description="Ethereum wallet address")
    signature: str = Field(..., description="Signed message signature")
    message: str = Field(..., description="Message that was signed")


class AutoLoginRequest(BaseModel):
    """Request model for wallet auto-login (hot login)."""
    wallet_address: str = Field(..., description="Ethereum wallet address")


class WalletSignupRequest(BaseModel):
    """Request model for wallet signup with enhanced user information."""
    wallet_address: str = Field(..., description="Ethereum wallet address")
    signature: str = Field(..., description="Signed message signature")
    message: str = Field(..., description="Message that was signed")
    email: Optional[str] = Field(None, description="User email address (optional but recommended)")
    display_name: Optional[str] = Field(None, description="User display name (optional but recommended)")


@router.post("/auth/wallet/nonce")
async def get_wallet_nonce(
    request: dict,
    db: Session = Depends(get_db)
):
    """Get nonce for wallet authentication."""
    import secrets
    from datetime import datetime, timedelta
    
    wallet_address = request.get("wallet_address", "").lower()
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address is required")
    
    # Generate nonce
    nonce = secrets.token_hex(16)
    
    # Create message to sign
    message = f"CreditNexus Authentication\n\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {datetime.utcnow().isoformat()}"
    
    # Store nonce temporarily (in production, use Redis or similar)
    # For now, we'll include it in the message
    
    return {
        "nonce": nonce,
        "message": message,
        "wallet_address": wallet_address
    }


@router.post("/auth/wallet")
async def wallet_authentication(
    request: WalletAuthRequest,
    db: Session = Depends(get_db)
):
    """Authenticate using wallet signature with cryptographic verification."""
    from app.utils.crypto_verification import (
        verify_ethereum_signature,
        normalize_wallet_address,
        validate_wallet_address
    )
    
    # Normalize wallet address to checksum format
    normalized_address = normalize_wallet_address(request.wallet_address)
    
    # Validate wallet address format
    if not validate_wallet_address(normalized_address):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format"
        )
    
    # Verify signature cryptographically
    is_valid = verify_ethereum_signature(
        message=request.message,
        signature=request.signature,
        wallet_address=normalized_address
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature. Signature does not match wallet address."
        )
    
    # Find existing user by wallet address
    user = db.query(User).filter(User.wallet_address == normalized_address.lower()).first()
    
    if not user:
        # Create new user with wallet address
        user = User(
            email=f"{normalized_address[:8]}@wallet.local",
            display_name=f"Wallet {normalized_address[:8]}",
            wallet_address=normalized_address.lower(),
            role="viewer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Generate JWT tokens (using existing auth system)
    from app.auth.jwt_auth import create_access_token, create_refresh_token
    
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    log_audit_action(db, AuditAction.LOGIN, "user", user.id, user.id, metadata={"method": "wallet"})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.post("/auth/wallet/auto-login")
async def wallet_auto_login(
    request: AutoLoginRequest,
    db: Session = Depends(get_db)
):
    """Auto-login endpoint for wallet-based hot login (session persistence).
    
    This endpoint allows users to automatically log in if they have a valid
    refresh token. If no valid token exists, returns signup_required status
    to prompt for full authentication.
    
    Args:
        request: AutoLoginRequest with wallet_address
        
    Returns:
        - If user exists and has valid refresh token: tokens and user data
        - If user doesn't exist: signup_required status
        - If no valid token: authentication_required status
    """
    from app.utils.crypto_verification import normalize_wallet_address, validate_wallet_address
    from app.auth.jwt_auth import create_access_token, create_refresh_token
    from app.db.models import RefreshToken
    from datetime import datetime
    
    # Normalize and validate wallet address
    normalized_address = normalize_wallet_address(request.wallet_address)
    
    if not validate_wallet_address(normalized_address):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format"
        )
    
    # Find user by wallet address
    user = db.query(User).filter(User.wallet_address == normalized_address.lower()).first()
    
    if not user:
        # User doesn't exist - requires signup
        return {
            "status": "signup_required",
            "message": "Wallet not registered. Please complete signup.",
            "wallet_address": normalized_address
        }
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    # Check for valid refresh token (not revoked and not expired)
    valid_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).order_by(RefreshToken.expires_at.desc()).first()
    
    if valid_refresh_token:
        # User has valid session - generate new tokens
        access_token = create_access_token({"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token({"sub": str(user.id)}, db)
        
        log_audit_action(
            db, 
            AuditAction.LOGIN, 
            "user", 
            user.id, 
            user.id, 
            metadata={"method": "wallet_auto_login"}
        )
        
        return {
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.to_dict()
        }
    else:
        # No valid session - requires full authentication
        return {
            "status": "authentication_required",
            "message": "No valid session found. Please sign in with your wallet.",
            "wallet_address": normalized_address
        }


@router.post("/auth/wallet/signup")
async def wallet_signup(
    request: WalletSignupRequest,
    db: Session = Depends(get_db)
):
    """Signup endpoint for wallet-based authentication with enhanced user information.
    
    This endpoint allows new users to create an account using their wallet address.
    Users can optionally provide email and display_name for a better experience.
    
    Args:
        request: WalletSignupRequest with wallet_address, signature, message, and optional email/display_name
        
    Returns:
        - If successful: tokens and user data
        - If user already exists: error indicating user exists
        - If signature invalid: authentication error
    """
    from app.utils.crypto_verification import (
        verify_ethereum_signature,
        normalize_wallet_address,
        validate_wallet_address
    )
    from app.auth.jwt_auth import create_access_token, create_refresh_token
    
    # Normalize wallet address to checksum format
    normalized_address = normalize_wallet_address(request.wallet_address)
    
    # Validate wallet address format
    if not validate_wallet_address(normalized_address):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format"
        )
    
    # Verify signature cryptographically
    is_valid = verify_ethereum_signature(
        message=request.message,
        signature=request.signature,
        wallet_address=normalized_address
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature. Signature does not match wallet address."
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.wallet_address == normalized_address.lower()).first()
    
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "user_exists",
                "message": "A user with this wallet address already exists. Please use login instead.",
                "wallet_address": normalized_address
            }
        )
    
    # Validate email format if provided
    email = request.email
    if email:
        # Basic email validation
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )
        # Check if email is already in use
        email_user = db.query(User).filter(User.email == email.lower()).first()
        if email_user:
            raise HTTPException(
                status_code=409,
                detail="Email address is already registered"
            )
    else:
        # Generate default email if not provided
        email = f"{normalized_address[:8]}@wallet.local"
    
    # Use provided display_name or generate default
    display_name = request.display_name or f"Wallet {normalized_address[:8]}"
    
    # Create new user
    user = User(
        email=email.lower() if email else f"{normalized_address[:8]}@wallet.local",
        display_name=display_name,
        wallet_address=normalized_address.lower(),
        role="viewer",  # Default role
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate JWT tokens
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)}, db)
    
    # Log signup action
    log_audit_action(
        db,
        AuditAction.CREATE,
        "user",
        user.id,
        user.id,
        metadata={
            "method": "wallet_signup",
            "email_provided": bool(request.email),
            "display_name_provided": bool(request.display_name)
        }
    )
    
    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user.to_dict(),
        "message": "Account created successfully"
    }


# ============================================================================
# Deals API
# ============================================================================

@router.get("/deals")
async def list_deals(
    status: Optional[str] = Query(None, description="Filter by status"),
    deal_type: Optional[str] = Query(None, description="Filter by deal type"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo status"),
    search: Optional[str] = Query(None, description="Search by deal_id or applicant"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List deals with filtering and pagination.
    
    Args:
        status: Optional filter by status.
        deal_type: Optional filter by deal type.
        is_demo: Optional filter by demo status.
        search: Optional search term for deal_id or applicant.
        limit: Maximum number of results.
        offset: Pagination offset.
        db: Database session.
        current_user: The current user (optional, but required for filtering).
        
    Returns:
        List of deals.
    """
    try:
        # Require authentication
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail={"status": "error", "message": "Authentication required"}
            )
        
        query = db.query(Deal)
        
        # Filter by user (unless admin)
        if current_user.role != "admin":
            query = query.filter(Deal.applicant_id == current_user.id)
        
        # Apply filters
        if status:
            query = query.filter(Deal.status == status)
        if deal_type:
            query = query.filter(Deal.deal_type == deal_type)
        if is_demo is not None:
            query = query.filter(Deal.is_demo == is_demo)
        if search:
            search_term = f"%{search}%"
            # Join with User table for search
            query = query.join(User, Deal.applicant_id == User.id).filter(
                (Deal.deal_id.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.display_name.ilike(search_term))
            )
        
        total = query.count()
        deals = query.order_by(Deal.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "deals": [deal.to_dict() for deal in deals]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing deals: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list deals: {str(e)}"}
        )


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a specific deal with related data.
    
    Args:
        deal_id: The deal ID.
        db: Database session.
        current_user: The current user (optional, but required for authorization).
        
    Returns:
        The deal with documents, notes, and timeline.
    """
    try:
        # Require authentication
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail={"status": "error", "message": "Authentication required"}
            )
        
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Deal {deal_id} not found"}
            )
        
        # Check permission (user can only view their own deals, or admin)
        if deal.applicant_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "Not authorized to view this deal"}
            )
        
        # Get attached documents
        documents = db.query(Document).filter(Document.deal_id == deal_id).all()
        
        # Get notes
        notes = db.query(DealNote).filter(DealNote.deal_id == deal_id).order_by(DealNote.created_at.desc()).limit(10).all()
        
        # Get timeline using DealService
        deal_service = DealService(db)
        timeline = deal_service.get_deal_timeline(deal_id)
        
        return {
            "status": "success",
            "deal": deal.to_dict(),
            "documents": [doc.to_dict() for doc in documents],
            "notes": [note.to_dict() for note in notes],
            "timeline": timeline
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deal {deal_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get deal: {str(e)}"}
        )


@router.get("/deals/{deal_id}/template-recommendations")
async def get_deal_template_recommendations(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get template recommendations for a deal.
    
    Args:
        deal_id: The deal ID.
        db: Database session.
        current_user: The current user (optional, but required for authorization).
        
    Returns:
        Template recommendations with missing required, optional, and generated templates.
    """
    try:
        # Require authentication
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail={"status": "error", "message": "Authentication required"}
            )
        
        from app.services.template_recommendation_service import TemplateRecommendationService
        
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Deal {deal_id} not found"}
            )
        
        # Check permission (user can only view their own deals, or admin)
        if deal.applicant_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "Not authorized to view this deal"}
            )
        
        # Get template recommendations
        recommendation_service = TemplateRecommendationService(db)
        recommendations = recommendation_service.recommend_templates(deal_id)
        
        if recommendations.get("error"):
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "message": recommendations.get("error", "Failed to get recommendations")}
            )
        
        return {
            "status": "success",
            "recommendations": recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template recommendations for deal {deal_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get template recommendations: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Error getting deal: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get deal: {str(e)}"}
        )


# ============================================================================
# Deal Notes API
# ============================================================================

class CreateDealNoteRequest(BaseModel):
    """Request model for creating a deal note."""
    content: str = Field(..., description="Note content")
    note_type: Optional[str] = Field(None, description="Note type (general, verification, status_change, etc.)")
    metadata: Optional[dict] = Field(None, description="Additional note metadata")


class UpdateDealNoteRequest(BaseModel):
    """Request model for updating a deal note."""
    content: Optional[str] = Field(None, description="Updated note content")
    note_type: Optional[str] = Field(None, description="Updated note type")
    metadata: Optional[dict] = Field(None, description="Updated metadata")


@router.post("/deals/{deal_id}/notes")
async def create_deal_note(
    deal_id: int,
    note_request: CreateDealNoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new note for a deal.
    
    Args:
        deal_id: The deal ID.
        note_request: CreateDealNoteRequest containing note data.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The created note.
    """
    try:
        # Verify deal exists
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Deal {deal_id} not found"}
            )
        
        # Create note in database
        note = DealNote(
            deal_id=deal_id,
            user_id=current_user.id,
            content=note_request.content,
            note_type=note_request.note_type,
            note_metadata=note_request.metadata,
        )
        db.add(note)
        db.flush()
        
        # Store note in file system
        file_storage = FileStorageService()
        try:
            file_storage.store_deal_document(
                user_id=deal.applicant_id,
                deal_id=deal.deal_id,
                document_id=note.id,
                filename=f"note_{note.id}.txt",
                content=note_request.content.encode('utf-8'),
                subdirectory="notes"
            )
        except Exception as e:
            logger.warning(f"Failed to store note in file system: {e}")
        
        # Index note in ChromaDB
        try:
            retrieval_service = DocumentRetrievalService(collection_name="creditnexus_deal_notes")
            retrieval_service.add_document(
                document_id=note.id,
                cdm_data={"content": note_request.content, "note_type": note_request.note_type or "general"},
                metadata={
                    "deal_id": str(deal_id),
                    "deal_deal_id": deal.deal_id,
                    "user_id": str(current_user.id),
                    "note_type": note_request.note_type or "general",
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to index note in ChromaDB: {e}")
        
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="deal_note",
            target_id=note.id,
            user_id=current_user.id,
            metadata={"deal_id": deal_id, "note_type": note_request.note_type},
            request=request
        )
        
        db.commit()
        db.refresh(note)
        
        # Re-index deal in ChromaDB after note creation
        try:
            from app.chains.document_retrieval_chain import add_deal
            # Get documents and notes for indexing
            documents = [doc.to_dict() for doc in db.query(Document).filter(Document.deal_id == deal_id).limit(10).all()]
            notes = [n.to_dict() for n in db.query(DealNote).filter(DealNote.deal_id == deal_id).order_by(DealNote.created_at.desc()).limit(10).all()]
            add_deal(
                deal_id=deal.id,
                deal_data=deal.to_dict(),
                documents=documents,
                notes=notes
            )
            logger.info(f"Re-indexed deal {deal.id} in ChromaDB after note creation")
        except Exception as e:
            logger.warning(f"Failed to re-index deal in ChromaDB: {e}")
            # Don't fail note creation if indexing fails
        
        logger.info(f"Created deal note {note.id} for deal {deal_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Deal note created successfully",
            "note": note.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating deal note: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to create deal note: {str(e)}"}
        )


@router.get("/deals/{deal_id}/notes")
async def list_deal_notes(
    deal_id: int,
    note_type: Optional[str] = Query(None, description="Filter by note type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """List notes for a deal.
    
    Args:
        deal_id: The deal ID.
        note_type: Optional filter by note type.
        limit: Maximum number of results.
        offset: Pagination offset.
        db: Database session.
        current_user: The current user.
        
    Returns:
        List of notes.
    """
    try:
        # Verify deal exists
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Deal {deal_id} not found"}
            )
        
        query = db.query(DealNote).filter(DealNote.deal_id == deal_id)
        
        if note_type:
            query = query.filter(DealNote.note_type == note_type)
        
        total = query.count()
        notes = query.order_by(DealNote.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "notes": [note.to_dict() for note in notes]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing deal notes: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list deal notes: {str(e)}"}
        )


@router.get("/deals/{deal_id}/notes/{note_id}")
async def get_deal_note(
    deal_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get a specific deal note.
    
    Args:
        deal_id: The deal ID.
        note_id: The note ID.
        db: Database session.
        current_user: The current user.
        
    Returns:
        The note.
    """
    try:
        note = db.query(DealNote).filter(
            DealNote.id == note_id,
            DealNote.deal_id == deal_id
        ).first()
        
        if not note:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Note {note_id} not found for deal {deal_id}"}
            )
        
        return {
            "status": "success",
            "note": note.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deal note: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get deal note: {str(e)}"}
        )


@router.put("/deals/{deal_id}/notes/{note_id}")
async def update_deal_note(
    deal_id: int,
    note_id: int,
    note_request: UpdateDealNoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Update a deal note.
    
    Args:
        deal_id: The deal ID.
        note_id: The note ID.
        note_request: UpdateDealNoteRequest containing updated data.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The updated note.
    """
    try:
        note = db.query(DealNote).filter(
            DealNote.id == note_id,
            DealNote.deal_id == deal_id
        ).first()
        
        if not note:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Note {note_id} not found for deal {deal_id}"}
            )
        
        # Check permission (user can only update their own notes, or admin)
        if note.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "Not authorized to update this note"}
            )
        
        # Update fields
        if note_request.content is not None:
            note.content = note_request.content
        if note_request.note_type is not None:
            note.note_type = note_request.note_type
        if note_request.metadata is not None:
            note.note_metadata = note_request.metadata
        
        note.updated_at = datetime.utcnow()
        
        # Update file system
        if note_request.content is not None:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                file_storage = FileStorageService()
                try:
                    file_storage.store_deal_document(
                        user_id=deal.applicant_id,
                        deal_id=deal.deal_id,
                        document_id=note.id,
                        filename=f"note_{note.id}.txt",
                        content=note_request.content.encode('utf-8'),
                        subdirectory="notes"
                    )
                except Exception as e:
                    logger.warning(f"Failed to update note in file system: {e}")
        
        # Re-index in ChromaDB
        if note_request.content is not None:
            try:
                retrieval_service = DocumentRetrievalService(collection_name="creditnexus_deal_notes")
                retrieval_service.add_document(
                    document_id=note.id,
                    cdm_data={"content": note.content, "note_type": note.note_type or "general"},
                    metadata={
                        "deal_id": str(deal_id),
                        "deal_deal_id": deal.deal_id,
                        "user_id": str(note.user_id),
                        "note_type": note.note_type or "general",
                        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to re-index note in ChromaDB: {e}")
        
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="deal_note",
            target_id=note.id,
            user_id=current_user.id,
            metadata={"deal_id": deal_id},
            request=request
        )
        
        db.commit()
        db.refresh(note)
        
        logger.info(f"Updated deal note {note_id} for deal {deal_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Deal note updated successfully",
            "note": note.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating deal note: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to update deal note: {str(e)}"}
        )


@router.delete("/deals/{deal_id}/notes/{note_id}")
async def delete_deal_note(
    deal_id: int,
    note_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Delete a deal note.
    
    Args:
        deal_id: The deal ID.
        note_id: The note ID.
        request: The HTTP request.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        Success message.
    """
    try:
        note = db.query(DealNote).filter(
            DealNote.id == note_id,
            DealNote.deal_id == deal_id
        ).first()
        
        if not note:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"Note {note_id} not found for deal {deal_id}"}
            )
        
        # Check permission (user can only delete their own notes, or admin)
        if note.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"status": "error", "message": "Not authorized to delete this note"}
            )
        
        # Delete from ChromaDB
        try:
            retrieval_service = DocumentRetrievalService(collection_name="creditnexus_deal_notes")
            retrieval_service.delete_document(note_id)
        except Exception as e:
            logger.warning(f"Failed to delete note from ChromaDB: {e}")
        
        log_audit_action(
            db=db,
            action=AuditAction.DELETE,
            target_type="deal_note",
            target_id=note.id,
            user_id=current_user.id,
            metadata={"deal_id": deal_id},
            request=request
        )
        
        db.delete(note)
        db.commit()
        
        logger.info(f"Deleted deal note {note_id} for deal {deal_id} by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Deal note deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting deal note: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to delete deal note: {str(e)}"}
        )


# ============================================================================
# Profile Extraction API Endpoints
# ============================================================================


@router.post("/profile/extract")
# Rate limiting: Uses slowapi default_limits (60/minute) from server.py
# Profile extraction may benefit from custom limits based on user role
async def extract_profile_from_documents(
    files: List[UploadFile] = File(...),
    role: str = Form(...),
    existing_profile: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Extract structured profile data from uploaded documents.
    
    This endpoint:
    1. Extracts text from uploaded files (PDFs and images)
    2. Uses LLM to extract structured profile data
    3. Merges with existing profile data if provided
    4. Returns structured UserProfileData
    
    Args:
        files: List of uploaded files (PDF, PNG, JPEG, etc.)
        role: User role (applicant, banker, law_officer, accountant)
        existing_profile: Optional existing profile data as JSON string
        db: Database session
        current_user: Authenticated user (optional, for signup flow)
        
    Returns:
        Profile extraction result with structured profile data
    """
    from app.services.profile_extraction_service import ProfileExtractionService
    from app.models.user_profile import UserProfileData
    import json
    
    try:
        # Parse existing profile if provided
        existing_profile_dict = None
        if existing_profile:
            try:
                existing_profile_dict = json.loads(existing_profile)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid existing_profile JSON: {existing_profile}")
        
        # Initialize profile extraction service
        profile_service = ProfileExtractionService(db)
        
        # Process all files
        file_contents = []
        filenames = []
        
        for file in files:
            filename = file.filename or "document"
            content = await file.read()
            file_contents.append((content, filename))
            filenames.append(filename)
        
        if len(file_contents) == 0:
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "No files provided"}
            )
        
        # Extract profile from multiple documents
        if len(file_contents) == 1:
            # Single file
            content, filename = file_contents[0]
            profile_data = profile_service.extract_profile_from_document(
                file_content=content,
                filename=filename,
                role=role,
                existing_profile=existing_profile_dict
            )
        else:
            # Multiple files
            files_list = [(content, filename) for content, filename in file_contents]
            profile_data = profile_service.extract_profile_from_multiple_documents(
                files=files_list,
                role=role,
                existing_profile=existing_profile_dict
            )
        
        # Convert to dict for JSON response
        profile_dict = profile_data.model_dump(exclude_none=True)
        
        # Index user profile in ChromaDB if user_id provided
        if current_user:
            try:
                add_user_profile(
                    user_id=current_user.id,
                    profile_data=profile_dict,
                    role=current_user.role,
                    email=current_user.email
                )
                logger.info(f"Indexed user profile {current_user.id} in ChromaDB after profile extraction")
            except Exception as e:
                logger.warning(f"Failed to index user profile in ChromaDB: {e}")
                # Don't fail extraction if indexing fails
        
        logger.info(f"Extracted profile data from {len(files)} document(s) for role {role}")
        
        return {
            "status": "success",
            "message": "Profile data extracted successfully",
            "profile_data": profile_dict,
            "extracted_from": filenames
        }
        
    except ValueError as e:
        logger.warning(f"Profile extraction validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error extracting profile data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to extract profile data: {str(e)}"}
        )


# ============================================================================
# Admin Signup Management API Endpoints
# ============================================================================


@router.get("/admin/signups")
async def list_pending_signups(
    status: Optional[str] = Query(None, description="Filter by signup status (pending, approved, rejected)"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """List pending signups (admin only).
    
    Returns a paginated list of user signups with their profile data.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    
    try:
        query = db.query(User)
        
        # Filter by status
        if status:
            query = query.filter(User.signup_status == status)
        else:
            # Default to pending if no status specified
            query = query.filter(User.signup_status == "pending")
        
        # Filter by role
        if role:
            query = query.filter(User.role == role)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        users = query.order_by(User.signup_submitted_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "status": "success",
            "data": [user.to_dict() for user in users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Error listing signups: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to list signups: {str(e)}"}
        )


@router.get("/admin/signups/{user_id}")
async def get_signup_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get signup details for a specific user (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"User {user_id} not found"}
            )
        
        return {
            "status": "success",
            "data": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signup details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get signup details: {str(e)}"}
        )


class SignupRejectRequest(BaseModel):
    """Request model for rejecting a signup."""
    reason: str = Field(..., description="Reason for rejection", min_length=10)


@router.post("/admin/signups/{user_id}/approve")
async def approve_signup(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Approve a user signup (admin only).
    
    Activates the user account and sets signup_status to 'approved'.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"User {user_id} not found"}
            )
        
        if user.signup_status == "approved":
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "User is already approved"}
            )
        
        # Approve user
        user.signup_status = "approved"
        user.is_active = True
        user.signup_reviewed_at = datetime.utcnow()
        user.signup_reviewed_by = current_user.id
        user.signup_rejection_reason = None
        
        db.commit()
        db.refresh(user)
        
        # Index user profile in ChromaDB if profile_data exists
        if user.profile_data:
            try:
                add_user_profile(
                    user_id=user.id,
                    profile_data=user.profile_data,
                    role=user.role,
                    email=user.email
                )
                logger.info(f"Indexed user profile {user.id} in ChromaDB after signup approval")
            except Exception as e:
                logger.warning(f"Failed to index user profile in ChromaDB: {e}")
                # Don't fail approval if indexing fails
        
        # Audit log
        log_audit_action(
            db=db,
            action=AuditAction.APPROVE,
            target_type="user",
            target_id=user.id,
            user_id=current_user.id,
            metadata={"signup_approval": True},
            request=request
        )
        
        logger.info(f"User {user_id} signup approved by admin {current_user.id}")
        
        return {
            "status": "success",
            "message": "User signup approved successfully",
            "data": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving signup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to approve signup: {str(e)}"}
        )


@router.post("/admin/signups/{user_id}/reject")
async def reject_signup(
    user_id: int,
    reject_request: SignupRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Reject a user signup (admin only).
    
    Sets signup_status to 'rejected' and stores the rejection reason.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": f"User {user_id} not found"}
            )
        
        if user.signup_status == "rejected":
            raise HTTPException(
                status_code=400,
                detail={"status": "error", "message": "User is already rejected"}
            )
        
        # Reject user
        user.signup_status = "rejected"
        user.is_active = False
        user.signup_reviewed_at = datetime.utcnow()
        user.signup_reviewed_by = current_user.id
        user.signup_rejection_reason = reject_request.reason
        
        db.commit()
        db.refresh(user)
        
        # Audit log
        log_audit_action(
            db=db,
            action=AuditAction.REJECT,
            target_type="user",
            target_id=user.id,
            user_id=current_user.id,
            metadata={"signup_rejection": True, "reason": reject_request.reason},
            request=request
        )
        
        logger.info(f"User {user_id} signup rejected by admin {current_user.id}: {reject_request.reason}")
        
        return {
            "status": "success",
            "message": "User signup rejected",
            "data": user.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting signup: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to reject signup: {str(e)}"}
        )


# ============================================================================
# User Profile Search API Endpoints
# ============================================================================

class UserSearchRequest(BaseModel):
    """Request model for user profile search."""
    query: str = Field(..., description="Search query (company name, role, job title, etc.)")
    role: Optional[str] = Field(None, description="Filter by user role")
    company_name: Optional[str] = Field(None, description="Filter by company name")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return (default: 10, max: 50)")


@router.post("/users/search")
async def search_users(
    request: UserSearchRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Search for users by profile data using semantic search.
    
    This endpoint uses ChromaDB to perform semantic search on user profiles,
    allowing you to find users by company, role, job title, or other profile attributes.
    
    Args:
        request: UserSearchRequest with search query and optional filters
        db: Database session
        current_user: Authenticated user (optional, but recommended for access control)
        
    Returns:
        List of matching user profiles with similarity scores
    """
    try:
        # Prepare filter metadata
        filter_metadata = {}
        if request.role:
            filter_metadata["role"] = request.role
        if request.company_name:
            filter_metadata["company_name"] = request.company_name
        
        # Search user profiles in ChromaDB
        try:
            search_results = search_user_profiles(
                query=request.query,
                top_k=request.top_k,
                filter_metadata=filter_metadata if filter_metadata else None
            )
        except ImportError as e:
            logger.error(f"ChromaDB not available: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "message": "User search service is not available. ChromaDB is not installed."
                }
            )
        except Exception as e:
            logger.error(f"User search failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"User search failed: {str(e)}"
                }
            )
        
        # Load full user data from database for each result
        user_results = []
        for result in search_results:
            user_id = result.get("user_id")
            if user_id:
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        # Check permissions (users can only see their own profile or admin can see all)
                        if current_user and (current_user.id == user_id or current_user.role == "admin"):
                            user_results.append({
                                "user_id": user.id,
                                "email": user.email,
                                "display_name": user.display_name,
                                "role": user.role,
                                "profile_data": user.profile_data,
                                "similarity_score": result.get("similarity_score", 0.0),
                                "distance": result.get("distance", 1.0),
                                "metadata": result.get("metadata", {}),
                            })
                        elif not current_user:
                            # Unauthenticated access - return limited info
                            user_results.append({
                                "user_id": user.id,
                                "display_name": user.display_name,
                                "role": user.role,
                                "similarity_score": result.get("similarity_score", 0.0),
                                "metadata": result.get("metadata", {}),
                            })
                except Exception as e:
                    logger.warning(f"Failed to load user {user_id} from database: {e}")
                    # Continue with other results
        
        # Audit log (if user is authenticated)
        if current_user:
            try:
                log_audit_action(
                    db=db,
                    action=AuditAction.VIEW,
                    target_type="user_search",
                    user_id=current_user.id,
                    metadata={
                        "query": request.query[:200],
                        "results_count": len(user_results),
                        "filters": filter_metadata,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to log user search audit: {e}")
        
        return {
            "status": "success",
            "query": request.query,
            "results_count": len(user_results),
            "users": user_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during user search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to search users: {str(e)}"}
        )


# ============================================================================
# Demo Data Seeding Endpoints
# ============================================================================

class DemoSeedRequest(BaseModel):
    """Request model for demo data seeding."""
    seed_users: bool = True
    seed_templates: bool = True
    seed_policies: bool = True
    seed_policy_templates: bool = True
    generate_deals: bool = False
    deal_count: int = 12
    dry_run: bool = False


class DemoSeedResponse(BaseModel):
    """Response model for demo data seeding."""
    status: str
    created: Dict[str, int] = {}
    updated: Dict[str, int] = {}
    errors: Dict[str, List[str]] = {}
    preview: Optional[Dict[str, Any]] = None
    user_credentials: Optional[List[Dict[str, str]]] = None


class SeedingStatusResponse(BaseModel):
    """Response model for seeding status."""
    stage: Optional[str] = None
    progress: float = 0.0
    total: int = 0
    current: int = 0
    errors: List[str] = []
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    all_stages: Optional[Dict[str, Any]] = None


@router.post("/demo/seed", response_model=DemoSeedResponse)
async def seed_demo_data(
    request: DemoSeedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Seed demo data (users, templates, policies).
    
    Requires admin authentication.
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    
    try:
        from app.services.demo_data_service import DemoDataService
        
        service = DemoDataService(db)
        results = service.seed_all(
            seed_users=request.seed_users,
            seed_templates=request.seed_templates,
            seed_policies=request.seed_policies,
            seed_policy_templates=request.seed_policy_templates,
            dry_run=request.dry_run
        )
        
        # Generate deals if requested
        if request.generate_deals and not request.dry_run:
            try:
                # Verify applicant users exist before generating deals
                from app.db.models import User, UserRole
                applicant_count = db.query(User).filter(User.role == UserRole.APPLICANT.value).count()
                if applicant_count == 0:
                    # Try to seed users with force=True if no applicants exist
                    logger.warning("No applicant users found. Attempting to seed users with force=True...")
                    user_result = service.seed_users(force=True, dry_run=False)
                    applicant_count = db.query(User).filter(User.role == UserRole.APPLICANT.value).count()
                    if applicant_count == 0:
                        raise ValueError(
                            "No applicant users found. Please seed demo users first. "
                            "User seeding returned 0 created/updated. "
                            "You may need to manually create users with APPLICANT role."
                        )
                    logger.info(f"Seeded users: {user_result['created']} created, {user_result['updated']} updated")
                    # Update results with user seeding info
                    if "users" not in results:
                        results["users"] = user_result
                    else:
                        results["users"]["created"] += user_result.get("created", 0)
                        results["users"]["updated"] += user_result.get("updated", 0)
                
                logger.info(f"Generating {request.deal_count} demo deals... (found {applicant_count} applicant users)")
                deals = service.create_demo_deals(count=request.deal_count)
                results["deals"] = {
                    "created": len(deals),
                    "updated": 0,
                    "errors": []
                }
                logger.info(f"Successfully generated {len(deals)} demo deals")
            except Exception as e:
                logger.error(f"Error generating demo deals: {e}", exc_info=True)
                results["deals"] = {
                    "created": 0,
                    "updated": 0,
                    "errors": [str(e)]
                }
        
        # Format response
        created = {k: v.get("created", 0) for k, v in results.items()}
        updated = {k: v.get("updated", 0) for k, v in results.items()}
        errors = {k: v.get("errors", []) for k, v in results.items()}
        
        # Extract user credentials if users were seeded
        user_credentials = None
        if "users" in results and "user_credentials" in results["users"]:
            user_credentials = results["users"]["user_credentials"]
        
        # Audit log
        try:
            log_audit_action(
                db=db,
                action=AuditAction.CREATE,
                target_type="demo_data",
                user_id=current_user.id,
                metadata={
                    "seed_users": request.seed_users,
                    "seed_templates": request.seed_templates,
                    "seed_policies": request.seed_policies,
                    "seed_policy_templates": request.seed_policy_templates,
                    "dry_run": request.dry_run,
                    "created": created,
                    "updated": updated,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log demo data seeding audit: {e}")
        
        return DemoSeedResponse(
            status="success" if not any(errors.values()) else "partial",
            created=created,
            updated=updated,
            errors=errors,
            preview=results if request.dry_run else None,
            user_credentials=user_credentials
        )
        
    except Exception as e:
        logger.error(f"Error seeding demo data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to seed demo data: {str(e)}"}
        )


@router.get("/demo/seed/status", response_model=SeedingStatusResponse)
async def get_seeding_status(
    stage: Optional[str] = Query(None, description="Specific stage to get status for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current seeding status.
    
    Returns status for a specific stage or all stages.
    """
    try:
        from app.services.demo_data_service import DemoDataService
        
        service = DemoDataService(db)
        status = service.get_seeding_status(stage=stage)
        
        if stage:
            if status:
                return SeedingStatusResponse(**status)
            else:
                raise HTTPException(
                    status_code=404,
                    detail={"status": "error", "message": f"Status not found for stage: {stage}"}
                )
        else:
            return SeedingStatusResponse(all_stages=status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting seeding status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get seeding status: {str(e)}"}
        )


@router.post("/demo/seed/users", response_model=DemoSeedResponse)
async def seed_users(
    force: bool = Query(False, description="Force update existing users"),
    dry_run: bool = Query(False, description="Preview without committing"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Seed demo users only."""
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from app.services.demo_data_service import DemoDataService
        
        service = DemoDataService(db)
        result = service.seed_users(force=force, dry_run=dry_run)
        
        return DemoSeedResponse(
            status="success" if not result["errors"] else "partial",
            created={"users": result["created"]},
            updated={"users": result["updated"]},
            errors={"users": result["errors"]},
            user_credentials=result.get("user_credentials")
        )
    except Exception as e:
        logger.error(f"Error seeding users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to seed users: {str(e)}")


@router.post("/demo/seed/templates", response_model=DemoSeedResponse)
async def seed_templates(
    dry_run: bool = Query(False, description="Preview without committing"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Seed templates only."""
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from app.services.demo_data_service import DemoDataService
        
        service = DemoDataService(db)
        result = service.seed_templates(dry_run=dry_run)
        
        return DemoSeedResponse(
            status="success" if not result["errors"] else "partial",
            created={"templates": result["created"]},
            updated={"templates": result["updated"]},
            errors={"templates": result["errors"]}
        )
    except Exception as e:
        logger.error(f"Error seeding templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to seed templates: {str(e)}")


@router.post("/demo/seed/policies", response_model=DemoSeedResponse)
async def seed_policies(
    dry_run: bool = Query(False, description="Preview without committing"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Seed policies only."""
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from app.services.demo_data_service import DemoDataService
        
        service = DemoDataService(db)
        result = service.seed_policies(dry_run=dry_run)
        
        return DemoSeedResponse(
            status="success" if not result["errors"] else "partial",
            created={"policies": result["created"]},
            updated={"policies": result["updated"]},
            errors={"policies": result["errors"]}
        )
    except Exception as e:
        logger.error(f"Error seeding policies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to seed policies: {str(e)}")


@router.delete("/demo/seed/reset")
async def reset_demo_data(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Reset demo data (delete all demo deals, documents, etc.).
    
    WARNING: This will delete all demo data. Use with caution.
    """
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Delete demo deals and related data
        demo_deals = db.query(Deal).filter(Deal.is_demo == True).all()
        
        deleted_count = 0
        for deal in demo_deals:
            # Delete related data in correct order (respecting foreign key constraints)
            # 1. Get all documents for this deal
            doc_ids = [d.id for d in db.query(Document).filter(Document.deal_id == deal.id).all()]
            
            # 2. Delete policy decisions that reference documents (must be before document deletion)
            if doc_ids:
                db.query(PolicyDecision).filter(PolicyDecision.document_id.in_(doc_ids)).delete(synchronize_session=False)
            
            # 3. Delete document versions first (they reference documents)
            if doc_ids:
                db.query(DocumentVersion).filter(DocumentVersion.document_id.in_(doc_ids)).delete(synchronize_session=False)
            
            # 4. Delete workflows (they reference documents)
            if doc_ids:
                db.query(Workflow).filter(Workflow.document_id.in_(doc_ids)).delete(synchronize_session=False)
            
            # 5. Delete documents (now safe since policy_decisions referencing them are deleted)
            if doc_ids:
                db.query(Document).filter(Document.id.in_(doc_ids)).delete(synchronize_session=False)
            
            # 6. Delete green finance assessments (no CASCADE, must delete explicitly)
            db.query(GreenFinanceAssessment).filter(GreenFinanceAssessment.deal_id == deal.id).delete(synchronize_session=False)
            
            # 7. Delete policy decisions by deal_id (for any remaining that reference deal but not documents)
            db.query(PolicyDecision).filter(PolicyDecision.deal_id == deal.id).delete(synchronize_session=False)
            
            # 8. DealNote has CASCADE, but delete explicitly to be safe
            db.query(DealNote).filter(DealNote.deal_id == deal.id).delete(synchronize_session=False)
            
            # 9. Finally delete the deal
            db.delete(deal)
            deleted_count += 1
        
        db.commit()
        
        # Audit log
        try:
            log_audit_action(
                db=db,
                action=AuditAction.DELETE,
                target_type="demo_data",
                user_id=current_user.id,
                metadata={"deleted_deals": deleted_count}
            )
        except Exception as e:
            logger.warning(f"Failed to log demo data reset audit: {e}")
        
        return {
            "status": "success",
            "message": f"Reset {deleted_count} demo deal(s) and related data"
        }
        
    except Exception as e:
        logger.error(f"Error resetting demo data: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset demo data: {str(e)}")

# Recovery endpoints
class RecoverySMSRequest(BaseModel):
    """Request model for sending recovery SMS."""
    phone: str = Field(..., description="Recipient phone number")
    message: str = Field(..., description="SMS message content")

@router.post("/recovery/send-sms")
async def send_recovery_sms(
    request: RecoverySMSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Send recovery SMS message."""
    from app.services.twilio_service import TwilioService
    
    try:
        twilio_service = TwilioService()
        result = twilio_service.send_sms(request.phone, request.message)
        
        # Log the action
        log_audit_action(
            db=db,
            action=AuditAction.CREATE,
            target_type="recovery_sms",
            user_id=current_user.id,
            metadata={"phone": request.phone, "status": result["status"]}
        )
        db.commit()
        
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"Error sending recovery SMS: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to send SMS: {str(e)}"}
        )
