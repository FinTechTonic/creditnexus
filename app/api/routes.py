"""API routes for credit agreement extraction."""

import logging
import io
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.chains.extraction_chain import extract_data, extract_data_smart
from app.models.cdm import ExtractionResult
from app.db import get_db
from app.db.models import StagedExtraction, ExtractionStatus, Document, DocumentVersion, Workflow, WorkflowState, User
from app.auth.dependencies import get_current_user, get_optional_user

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
        if party.get("role") == "Borrower":
            metadata["borrower_name"] = party.get("legal_name")
            metadata["borrower_lei"] = party.get("lei")
            break
    
    facilities = agreement_data.get("facilities", [])
    if facilities:
        total = Decimal("0")
        currency = None
        for facility in facilities:
            if facility.get("commitment"):
                amount = facility["commitment"].get("amount")
                if amount:
                    total += Decimal(str(amount))
                if not currency and facility["commitment"].get("currency"):
                    currency = facility["commitment"]["currency"]
        if total > 0:
            metadata["total_commitment"] = total
            metadata["currency"] = currency
    
    sustainability = agreement_data.get("sustainability_provisions")
    if sustainability and isinstance(sustainability, dict):
        metadata["sustainability_linked"] = sustainability.get("is_sustainability_linked", False)
        metadata["esg_metadata"] = sustainability
    
    return metadata


@router.post("/documents")
async def create_document(
    request: CreateDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new document with its first version.
    
    Args:
        request: CreateDocumentRequest containing the document data.
        db: Database session.
        current_user: The authenticated user.
        
    Returns:
        The created document with its first version.
    """
    try:
        metadata = extract_document_metadata(request.agreement_data)
        
        doc = Document(
            title=request.title,
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
            extracted_data=request.agreement_data,
            original_text=request.original_text,
            source_filename=request.source_filename,
            extraction_method=request.extraction_method,
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
    current_user: User = Depends(get_optional_user)
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
    current_user: User = Depends(get_optional_user)
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
    current_user: User = Depends(get_optional_user)
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
    current_user: User = Depends(get_optional_user)
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
    request: CreateVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of a document.
    
    Args:
        document_id: The document ID.
        request: CreateVersionRequest containing the new version data.
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
            extracted_data=request.agreement_data,
            original_text=request.original_text,
            source_filename=request.source_filename,
            extraction_method=request.extraction_method,
            created_by=current_user.id,
        )
        db.add(version)
        db.flush()
        
        metadata = extract_document_metadata(request.agreement_data)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document and all its versions.
    
    Args:
        document_id: The document ID.
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
    current_user: User = Depends(get_optional_user)
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
