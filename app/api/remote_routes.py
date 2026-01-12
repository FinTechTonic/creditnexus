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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),
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
    profile: RemoteAppProfile = Depends(lambda: None),
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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

    # Build file references
    file_references = []
    if request.include_files and request.file_categories:
        file_config = VerificationFileConfig()

        # Get enabled categories
        enabled_subdirs = file_config.get_enabled_subdirectories()

        for subdir in enabled_subdirs:
            # Simulate getting documents (TODO: actual implementation)
            if subdir == "documents":
                file_references.append(
                    {
                        "document_id": f"doc_{1}",
                        "filename": "credit_agreement.pdf",
                        "category": "legal",
                        "subdirectory": subdir,
                        "size": 1024000,
                        "download_url": f"/api/deals/{deal.id}/files/doc_1",
                    }
                )

    # Generate encrypted link payload
    payload_generator = LinkPayloadGenerator()
    encrypted_payload = payload_generator.generate_verification_link_payload(
        verification_id=verification.verification_id,
        deal_id=deal.id,
        deal_data=deal.deal_data or {},
        cdm_payload={},  # TODO: Get actual CDM payload
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


# ============================================================================
# Notarization Endpoints
# ============================================================================


@remote_router.post("/deals/{deal_id}/notarize")
async def create_notarization(
    deal_id: int,
    request: CreateNotarizationRequest,
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
    profile: RemoteAppProfile = Depends(lambda: None),  # TODO: Add real auth
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
