"""Remote API routes for verification and notarization."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.db.models import RemoteAppProfile, VerificationRequest, NotarizationRecord, Deal, User
from app.services.verification_service import VerificationService
from app.utils.link_payload import LinkPayloadGenerator
from app.core.verification_file_config import VerificationFileConfig
from app.utils.crypto_verification import verify_ethereum_signature
from app.auth.remote_auth import get_remote_profile
from app.services.cdm_payload_generator import get_deal_cdm_payload

logger = logging.getLogger(__name__)

remote_router = APIRouter(prefix="/remote", tags=["remote"])


class GenerateVerificationLinkRequest(BaseModel):
    verification_id: str
    include_files: bool = True
    file_categories: Optional[list[str]] = None
    file_document_ids: Optional[list[int]] = None
    expires_in_hours: int = 72


class VerificationAcceptRequest(BaseModel):
    verifier_user_id: int
    metadata: Optional[dict] = None


class VerificationDeclineRequest(BaseModel):
    verifier_user_id: int
    reason: str


class CreateVerificationRequest(BaseModel):
    deal_id: Optional[int] = None
    verifier_user_id: Optional[int] = None
    expires_in_hours: int = 72


class NotarizationSignRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


class CreateNotarizationRequest(BaseModel):
    deal_id: int
    required_signers: list[str]
    message_prefix: Optional[str] = "CreditNexus Notarization"


# ============================================================================
# Health Check
# ============================================================================


@remote_router.get("/health")
async def health_check():
    """Health check endpoint for remote API."""
    return {"status": "healthy", "service": "creditnexus-remote-api"}


# ============================================================================
# Verification Endpoints
# ============================================================================


@remote_router.get("/verification/{verification_id}")
async def get_verification(
    verification_id: str,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Get verification details."""
    verification = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.verification_id == verification_id)
        .first()
    )

    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    return verification.to_dict()


@remote_router.post("/verification/{verification_id}/accept")
async def accept_verification(
    verification_id: str,
    request: VerificationAcceptRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Accept a verification."""
    service = VerificationService(db)

    try:
        verification = service.accept_verification(
            verification_id=verification_id,
            verifier_user_id=request.verifier_user_id,
            metadata=request.metadata,
        )
        return verification.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@remote_router.post("/verification/{verification_id}/decline")
async def decline_verification(
    verification_id: str,
    request: VerificationDeclineRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Decline a verification."""
    service = VerificationService(db)

    try:
        verification = service.decline_verification(
            verification_id=verification_id,
            verifier_user_id=request.verifier_user_id,
            reason=request.reason,
        )
        return verification.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@remote_router.post("/verifications")
async def create_verification(
    request: CreateVerificationRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Create a new verification request."""
    service = VerificationService(db)

    verification = service.create_verification_request(
        deal_id=request.deal_id,
        verifier_user_id=request.verifier_user_id,
        expires_in_hours=request.expires_in_hours,
        created_by=1,  # TODO: Use actual user ID
    )

    return {
        "verification": verification.to_dict(),
        "verification_link": service.generate_verification_link(verification),
    }


@remote_router.get("/verifications")
async def list_verifications(
    deal_id: Optional[int] = None,
    verifier_user_id: Optional[int] = None,
    status: Optional[str] = None,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """List verification requests."""
    service = VerificationService(db)

    verifications = service.list_verifications(
        deal_id=deal_id, verifier_user_id=verifier_user_id, status=status, limit=100
    )

    return {"verifications": [v.to_dict() for v in verifications], "count": len(verifications)}


@remote_router.get("/verifications/stats")
async def get_verification_stats(
    deal_id: Optional[int] = None,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Get verification statistics."""
    service = VerificationService(db)

    stats = service.get_verification_stats(deal_id=deal_id)

    return stats


# ============================================================================
# Link Generation with File References
# ============================================================================


@remote_router.post("/verification/{verification_id}/generate-link")
async def generate_verification_link(
    verification_id: str,
    request: GenerateVerificationLinkRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Generate self-contained verification link with file references."""
    from app.utils.link_payload import LinkPayloadGenerator

    verification = (
        db.query(VerificationRequest)
        .filter(VerificationRequest.verification_id == verification_id)
        .first()
    )

    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Get deal
    deal = db.query(Deal).filter(Deal.id == verification.deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Build file references from actual deal documents
    file_references = []
    if request.include_files:
        from app.db.models import Document, DocumentVersion
        from app.services.file_storage_service import FileStorageService
        from app.utils.verification_file_config import VerificationFileConfig
        
        file_config = VerificationFileConfig()
        
        # Get enabled categories
        enabled_subdirs = file_config.get_enabled_subdirectories()
        
        # Get documents associated with deal
        documents_query = db.query(Document).filter(Document.deal_id == verification.deal_id)
        documents = documents_query.all()
        
        for subdir in enabled_subdirs:
            if subdir == "documents":
                for doc in documents:
                    # Get latest version
                    latest_version = (
                        db.query(DocumentVersion)
                        .filter(DocumentVersion.document_id == doc.id)
                        .order_by(DocumentVersion.version_number.desc())
                        .first()
                    )
                    
                    if latest_version and latest_version.source_filename:
                        # Determine category
                        category = "legal"  # Default category
                        
                        # Filter by categories if specified
                        if request.file_categories and category not in request.file_categories:
                            continue
                        
                        # Get file size from filesystem
                        file_size = 0
                        try:
                            file_storage = FileStorageService()
                            deal_docs = file_storage.get_deal_documents(
                                user_id=deal.applicant_id if deal.applicant_id else 0,
                                deal_id=deal.deal_id,
                                subdirectory=subdir
                            )
                            # Find matching file
                            for stored_file in deal_docs:
                                if str(doc.id) in stored_file.get("filename", "") or latest_version.source_filename in stored_file.get("filename", ""):
                                    file_size = stored_file.get("size", 0)
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to get file size for document {doc.id}: {e}")
                        
                        # Build download URL
                        download_url = f"/api/deals/{deal.id}/files/{latest_version.source_filename}"
                        
                        file_references.append({
                            "document_id": doc.id,
                            "filename": latest_version.source_filename,
                            "category": category,
                            "subdirectory": subdir,
                            "size": file_size,
                            "download_url": download_url,
                            "title": doc.title or latest_version.source_filename
                        })

    # Generate encrypted link payload
    payload_generator = LinkPayloadGenerator()
    encrypted_payload = payload_generator.generate_verification_link_payload(
        verification_id=verification.verification_id,
        deal_id=deal.id,
        deal_data=deal.deal_data or {},
        cdm_payload=get_deal_cdm_payload(db, deal) if deal else {},
        file_references=file_references if file_references else None,
        expires_in_hours=request.expires_in_hours,
    )

    return {
        "status": "success",
        "link": encrypted_payload,
        "verification_id": verification_id,
        "expires_at": verification.expires_at.isoformat() if verification.expires_at else None,
        "files_included": len(file_references),
        "instructions": "Share this link via email, Slack, Teams, or any other channel",
    }


# ============================================================================
# Link Validation (No DB lookup)
# ============================================================================


@remote_router.get("/verify/{payload}")
async def verify_link_payload(payload: str, db: Session = Depends(get_db)):
    """Validate and parse verification link payload (self-contained)."""
    from app.utils.link_payload import LinkPayloadGenerator

    payload_generator = LinkPayloadGenerator()
    link_data = payload_generator.parse_verification_link_payload(payload)

    if not link_data:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    return {
        "status": "valid",
        "verification_id": link_data["verification_id"],
        "deal_id": link_data["deal_id"],
        "deal_data": link_data["deal_data"],
        "cdm_payload": link_data["cdm_payload"],
        "verifier_info": link_data["verifier_info"],
        "file_references": link_data.get("file_references", []),
        "expires_at": link_data["expires_at"],
    }


@remote_router.post("/verify/{payload}/process")
async def process_verification_link(
    payload: str,
    db: Session = Depends(get_db),
    profile: RemoteAppProfile = Depends(get_remote_profile),
):
    """Process verification link and update files in local Postgres.
    
    This endpoint:
    1. Parses the encrypted link payload
    2. Extracts file references
    3. Downloads files from URLs (if provided)
    4. Stores files in local Postgres via FileStorageService
    5. Updates deal documents
    6. Updates verification status
    
    Args:
        payload: Encrypted verification link payload
        db: Database session
        profile: Remote app profile (for authentication)
    
    Returns:
        Processing result with file metadata
    """
    from app.utils.link_payload import LinkPayloadGenerator
    from app.utils.file_downloader import download_file_from_url
    from app.services.verification_service import VerificationService
    from app.db.models import Document, DocumentVersion
    from datetime import datetime
    
    # Parse payload
    payload_generator = LinkPayloadGenerator()
    link_data = payload_generator.parse_verification_link_payload(payload)
    
    if not link_data:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    
    verification_id = link_data["verification_id"]
    deal_id = link_data["deal_id"]
    file_references = link_data.get("file_references", [])
    
    # Get verification
    verification_service = VerificationService(db)
    verification = verification_service.get_verification_by_id(verification_id)
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    # Process file references
    processed_files = []
    
    for file_ref in file_references:
        try:
            file_metadata = None
            
            # Download file if URL provided
            if "download_url" in file_ref:
                download_url = file_ref["download_url"]
                # If relative URL, construct full URL
                if download_url.startswith("/"):
                    from app.core.config import settings
                    base_url = getattr(settings, "API_BASE_URL", "http://localhost:8000")
                    download_url = f"{base_url}{download_url}"
                
                file_metadata = await download_file_from_url(
                    url=download_url,
                    deal_id=deal_id,
                    filename=file_ref.get("filename", "unknown"),
                    category=file_ref.get("category", "legal"),
                    subdirectory=file_ref.get("subdirectory", "documents"),
                    db=db
                )
            
            # If we have a document_id, update existing document
            if "document_id" in file_ref and file_ref["document_id"]:
                doc_id = file_ref["document_id"]
                if isinstance(doc_id, str) and doc_id.startswith("doc_"):
                    # Skip placeholder document IDs
                    continue
                
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    # Update document metadata if needed
                    if file_metadata:
                        # Document already exists, just update metadata
                        processed_files.append({
                            "document_id": doc.id,
                            "filename": doc.title,
                            "status": "updated",
                            "path": file_metadata.get("path")
                        })
                    else:
                        processed_files.append({
                            "document_id": doc.id,
                            "filename": doc.title,
                            "status": "exists"
                        })
            elif file_metadata:
                # Create new document entry if file was downloaded
                # Note: This is a simplified version - in production, you'd want
                # to create proper Document and DocumentVersion entries
                processed_files.append({
                    "filename": file_metadata["filename"],
                    "status": "downloaded",
                    "path": file_metadata["path"],
                    "size": file_metadata["size"]
                })
            
        except Exception as e:
            logger.error(f"Failed to process file {file_ref.get('filename')}: {e}")
            processed_files.append({
                "filename": file_ref.get("filename", "unknown"),
                "status": "error",
                "error": str(e)
            })
    
    # Update verification metadata
    if not verification.verification_metadata:
        verification.verification_metadata = {}
    verification.verification_metadata["files_processed"] = len(processed_files)
    verification.verification_metadata["processed_at"] = datetime.utcnow().isoformat()
    db.commit()
    
    return {
        "status": "success",
        "verification_id": verification_id,
        "deal_id": deal_id,
        "files_processed": len(processed_files),
        "files": processed_files
    }


# ============================================================================
# Notarization Endpoints
# ============================================================================


@remote_router.post("/deals/{deal_id}/notarize")
async def create_notarization(
    deal_id: int,
    request: CreateNotarizationRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Create notarization request."""
    from app.utils.crypto_verification import generate_nonce, compute_payload_hash

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Get or create CDM payload
    cdm_payload = {}  # TODO: Build from deal.deal_data

    # Generate hash
    notarization_hash = compute_payload_hash(cdm_payload)

    # Create notarization record
    notarization = NotarizationRecord(
        deal_id=deal_id,
        notarization_hash=notarization_hash,
        required_signers=request.required_signers,
        signatures=[],
        status="pending",
    )

    db.add(notarization)
    db.commit()
    db.refresh(notarization)

    return {
        "status": "success",
        "notarization_id": notarization.id,
        "notarization_hash": notarization_hash,
    }


@remote_router.get("/notarization/{notarization_id}")
async def get_notarization(
    notarization_id: int,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Get notarization details."""
    notarization = (
        db.query(NotarizationRecord).filter(NotarizationRecord.id == notarization_id).first()
    )

    if not notarization:
        raise HTTPException(status_code=404, detail="Notarization not found")

    return notarization.to_dict()


@remote_router.get("/notarization/{notarization_id}/nonce")
async def get_notarization_nonce(
    notarization_id: int,
    wallet_address: str,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Get nonce and message for notarization signing."""
    from app.utils.crypto_verification import generate_signing_message

    notarization = (
        db.query(NotarizationRecord).filter(NotarizationRecord.id == notarization_id).first()
    )

    if not notarization:
        raise HTTPException(status_code=404, detail="Notarization not found")

    nonce = generate_nonce()
    timestamp = datetime.utcnow().isoformat()

    message = generate_signing_message(
        nonce=nonce, timestamp=timestamp, deal_id=notarization.deal_id, verification_id=None
    )

    return {"message": message, "nonce": nonce, "notarization_hash": notarization.notarization_hash}


@remote_router.post("/notarization/{notarization_id}/sign")
async def sign_notarization(
    notarization_id: int,
    request: NotarizationSignRequest,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Sign notarization with MetaMask signature."""
    notarization = (
        db.query(NotarizationRecord).filter(NotarizationRecord.id == notarization_id).first()
    )

    if not notarization:
        raise HTTPException(status_code=404, detail="Notarization not found")

    # Verify signature
    is_valid = verify_ethereum_signature(
        message=request.message, signature=request.signature, wallet_address=request.wallet_address
    )

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Check if signer is required
    if request.wallet_address.lower() not in [s.lower() for s in notarization.required_signers]:
        raise HTTPException(status_code=400, detail="Signer not in required signers list")

    # Check if already signed
    signatures = notarization.signatures or []
    if any(
        s.get("wallet_address", "").lower() == request.wallet_address.lower() for s in signatures
    ):
        raise HTTPException(status_code=400, detail="Already signed")

    # Add signature
    signature_data = {
        "wallet_address": request.wallet_address.lower(),
        "signature": request.signature,
        "signed_at": datetime.utcnow().isoformat(),
        "message": request.message,
    }

    signatures.append(signature_data)

    # Check if all signers have signed
    if len(signatures) >= len(notarization.required_signers):
        notarization.status = "signed"
        notarization.completed_at = datetime.utcnow()

        # Generate CDM event
        # TODO: Generate actual CDM event
        # notarization.cdm_event_id = generate_cdm_notarization_event(...)

    db.commit()
    db.refresh(notarization)

    return {
        "status": "success",
        "notarization_status": notarization.status,
        "signatures_count": len(signatures),
        "signers_remaining": len(notarization.required_signers) - len(signatures),
    }
