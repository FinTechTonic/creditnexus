"""Remote API routes for verification and notarization."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.db.models import RemoteAppProfile, VerificationRequest, NotarizationRecord, Deal, User, PaymentEvent as PaymentEventModel
from app.services.verification_service import VerificationService
from app.utils.link_payload import LinkPayloadGenerator
from app.core.verification_file_config import VerificationFileConfig
from app.utils.crypto_verification import verify_ethereum_signature
from app.auth.remote_auth import get_remote_profile
from app.auth.jwt_auth import require_auth as require_jwt_auth, get_current_user
from app.services.cdm_payload_generator import get_deal_cdm_payload
from app.services.notarization_service import NotarizationService
from app.services.notarization_payment_service import NotarizationPaymentService
from app.services.x402_payment_service import X402PaymentService
from app.models.cdm import Party, Money, Currency
from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
from app.core.config import settings
from app.utils.audit import log_audit_action, AuditAction

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
    required_signers: list[str] = Field(..., description="List of wallet addresses required to sign")
    message_prefix: Optional[str] = Field("CreditNexus Notarization", description="Message prefix for signing")
    payment_payload: Optional[dict] = Field(None, description="x402 payment payload (optional, required for non-admin)")
    skip_payment: Optional[bool] = Field(False, description="Skip payment (admin only, requires admin role)")


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

async def get_auth_user_or_profile(
    current_user: Optional[User] = Depends(get_current_user),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
    db: Session = Depends(get_db),
) -> tuple[Optional[User], Optional[RemoteAppProfile]]:
    """Get authenticated user (JWT) or remote profile (API key).
    
    Returns:
        Tuple of (user, profile) - one will be None
    """
    # Try JWT first
    if current_user:
        return (current_user, None)
    
    # Fall back to remote profile
    if api_key:
        try:
            profile = await get_remote_profile(api_key=api_key, request=request, db=db)
            return (None, profile)
        except HTTPException:
            pass
    
    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide JWT Bearer token or X-API-Key header"
    )


@remote_router.post("/deals/{deal_id}/notarize")
async def create_notarization(
    deal_id: int,
    request: CreateNotarizationRequest,
    auth_result: tuple[Optional[User], Optional[RemoteAppProfile]] = Depends(get_auth_user_or_profile),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Create notarization request with x402 payment requirement.
    
    Returns 402 Payment Required if payment_payload not provided (unless admin).
    Supports both JWT authentication (for internal users) and remote API key (for external apps).
    """
    current_user, profile = auth_result
    
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Get CDM payload
    cdm_payload = get_deal_cdm_payload(db, deal)

    # Create notarization service
    notarization_service = NotarizationService(db)

    # Create notarization request
    notarization = notarization_service.create_notarization_request(
        deal_id=deal_id,
        required_signers=request.required_signers,
        message_prefix=request.message_prefix
    )

    # Check if payment is required
    if settings.NOTARIZATION_FEE_ENABLED:
        # Get x402 payment service
        payment_service = None
        if http_request and hasattr(http_request.app.state, 'x402_payment_service'):
            payment_service = http_request.app.state.x402_payment_service
        
        payment_service_wrapper = NotarizationPaymentService(db, payment_service)
        
        # Check if admin can skip
        if current_user and payment_service_wrapper.can_skip_payment(current_user):
            # Admin skip - log audit action
            log_audit_action(
                db,
                AuditAction.UPDATE,
                "notarization",
                notarization.id,
                current_user.id,
                metadata={"payment_skipped": True, "reason": "admin_privilege"}
            )
            return {
                "status": "success",
                "notarization_id": notarization.id,
                "notarization_hash": notarization.notarization_hash,
                "payment_skipped": True,
                "payment_status": "skipped_admin"
            }
        
        # Extract payer and receiver from deal
        payer_name = current_user.display_name if current_user else (profile.profile_name if profile else "Unknown")
        payer = Party(
            id="notarization_payer",
            name=payer_name,
            lei=None
        )
        
        receiver = Party(
            id="creditnexus_notarization_service",
            name="CreditNexus Notarization Service",
            lei=None
        )
        
        # Check for payment payload in request
        payment_payload = request.payment_payload
        
        # Request payment
        payment_result = await payment_service_wrapper.request_notarization_payment(
            notarization=notarization,
            payer=payer,
            receiver=receiver,
            payment_payload=payment_payload
        )
        
        # If payment not provided, return 402
        if payment_payload is None or payment_result.get("status") != "settled":
            return JSONResponse(
                status_code=402,
                content={
                    "status": "Payment Required",
                    "notarization_id": notarization.id,
                    "payment_request": payment_result.get("payment_request"),
                    "amount": str(payment_service_wrapper.get_notarization_fee().amount),
                    "currency": payment_service_wrapper.get_notarization_fee().currency.value,
                    "payer": {
                        "id": payer.id,
                        "name": payer.name
                    },
                    "receiver": {
                        "id": receiver.id,
                        "name": receiver.name
                    },
                    "facilitator_url": payment_service.facilitator_url if payment_service else None
                }
            )
        
        # Payment successful - create CDM payment event
        fee = payment_service_wrapper.get_notarization_fee()
        payment_event = PaymentEvent.from_cdm_party(
            payer=payer,
            receiver=receiver,
            amount=Money(amount=fee.amount, currency=fee.currency),
            payment_type=PaymentType.NOTARIZATION_FEE,
            payment_method=PaymentMethod.X402,
            trade_id=None
        )
        
        payment_event = payment_event.model_copy(update={
            "x402PaymentDetails": {
                "payment_payload": payment_payload,
                "verification": payment_result.get("verification"),
                "settlement": payment_result.get("settlement")
            },
            "transactionHash": payment_result.get("transaction_hash")
        })
        
        payment_event = payment_event.transition_to_verified()
        payment_event = payment_event.transition_to_settled(payment_result.get("transaction_hash", ""))
        
        # Store payment event
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
            related_notarization_id=notarization.id,  # Link to notarization
            cdm_event=payment_event.to_cdm_json(),
            settled_at=datetime.utcnow()
        )
        db.add(payment_event_db)
        
        # Update notarization with payment info
        notarization.payment_event_id = payment_event_db.id
        notarization.payment_status = "paid"
        notarization.payment_transaction_hash = payment_result.get("transaction_hash")
        db.commit()
    
    return {
        "status": "success",
        "notarization_id": notarization.id,
        "notarization_hash": notarization.notarization_hash,
        "payment_status": "paid" if settings.NOTARIZATION_FEE_ENABLED else "not_required",
        "transaction_hash": payment_result.get("transaction_hash") if settings.NOTARIZATION_FEE_ENABLED else None
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


@remote_router.get("/notarization/{notarization_id}/payment-status")
async def get_notarization_payment_status(
    notarization_id: int,
    profile: RemoteAppProfile = Depends(get_remote_profile),
    db: Session = Depends(get_db),
):
    """Get payment status for notarization."""
    notarization = (
        db.query(NotarizationRecord)
        .filter(NotarizationRecord.id == notarization_id)
        .first()
    )
    
    if not notarization:
        raise HTTPException(status_code=404, detail="Notarization not found")
    
    payment_status = {
        "notarization_id": notarization_id,
        "payment_required": settings.NOTARIZATION_FEE_ENABLED,
        "payment_status": "not_required"
    }
    
    if settings.NOTARIZATION_FEE_ENABLED:
        # Check for payment event
        payment_event = (
            db.query(PaymentEventModel)
            .filter(PaymentEventModel.related_notarization_id == notarization_id)
            .order_by(PaymentEventModel.created_at.desc())
            .first()
        )
        
        if payment_event:
            payment_status.update({
                "payment_status": payment_event.status,
                "payment_id": payment_event.payment_id,
                "transaction_hash": payment_event.transaction_hash,
                "amount": str(payment_event.amount),
                "currency": payment_event.currency,
                "settled_at": payment_event.settled_at.isoformat() if payment_event.settled_at else None
            })
        elif notarization.payment_status == "skipped_admin":
            payment_status["payment_status"] = "skipped_admin"
        else:
            payment_status["payment_status"] = "pending"
    
    return payment_status


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
