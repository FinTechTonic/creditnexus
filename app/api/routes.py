"""API routes for credit agreement extraction."""

import logging
import io
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
import pandas as pd

from app.chains.extraction_chain import extract_data, extract_data_smart
from app.models.cdm import ExtractionResult
from app.db import get_db
from app.db.models import StagedExtraction, ExtractionStatus, Document, DocumentVersion, Workflow, WorkflowState, User, AuditLog, AuditAction
from app.auth.jwt_auth import get_current_user, require_auth

logger = logging.getLogger(__name__)


def log_audit_action(
    db: Session,
    action: AuditAction,
    target_type: str,
    target_id: Optional[int] = None,
    user_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """Log an audit action to the database.
    
    Args:
        db: Database session.
        action: The type of action being logged.
        target_type: The type of entity being acted upon (e.g., 'document', 'workflow').
        target_id: The ID of the target entity.
        user_id: The ID of the user performing the action.
        metadata: Additional context data for the action.
        request: The HTTP request (to extract IP and user agent).
        
    Returns:
        The created AuditLog record.
    """
    ip_address = None
    user_agent = None
    
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action.value,
        target_type=target_type,
        target_id=target_id,
        action_metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)
    return audit_log


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


class CreateVersionRequest(BaseModel):
    """Request model for creating a new document version."""
    agreement_data: dict = Field(..., description="The updated extracted agreement data")
    original_text: Optional[str] = Field(None, description="The original document text")
    source_filename: Optional[str] = Field(None, description="The source file name")
    extraction_method: str = Field("simple", description="The extraction method used")


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
        )
        db.add(doc)
        db.flush()
        
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
        
        workflow = Workflow(
            document_id=doc.id,
            state=WorkflowState.DRAFT.value,
            priority="normal",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents with optional filtering.
    
    Args:
        search: Optional search term.
        limit: Maximum number of results (default 50, max 100).
        offset: Pagination offset.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        List of documents with summary information.
    """
    try:
        query = db.query(Document).options(
            joinedload(Document.workflow),
            joinedload(Document.uploaded_by_user)
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Document.title.ilike(search_term)) |
                (Document.borrower_name.ilike(search_term))
            )
        
        total = query.count()
        
        documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for doc in documents:
            doc_dict = doc.to_dict()
            doc_dict["workflow_state"] = doc.workflow.state if doc.workflow else None
            doc_dict["uploaded_by_name"] = doc.uploaded_by_user.display_name if doc.uploaded_by_user else None
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a document with all its versions.
    
    Args:
        document_id: The document ID.
        db: Database session.
        current_user: The current user (optional).
        
    Returns:
        The document with all versions.
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
        
        return {
            "status": "success",
            "document": doc_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": f"Failed to get document: {str(e)}"}
        )


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
