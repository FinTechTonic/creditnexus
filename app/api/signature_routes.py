"""Native Signature Service API routes.

This module exposes the Phase 2 API surface for the
`InternalSignatureService`, including the public signer portal.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_auth
from app.auth.dependencies import get_db
from app.core.permissions import (
    has_permission,
    PERMISSION_SIGNATURE_COORDINATE,
    PERMISSION_SIGNATURE_EXECUTE,
)
from app.db.models import User, DocumentSignature, Document
from app.services.internal_signature_service import (
    InternalSignatureService,
    SignatureCoordinates,
)

logger = logging.getLogger(__name__)

signature_router = APIRouter(prefix="/signatures", tags=["signatures"])


class CreateInternalSignatureRequest(BaseModel):
    """Request payload to create an internal/native signature request."""

    document_id: int
    signer_email: EmailStr
    page: int = 0
    x: float = 50.0
    y: float = 50.0
    width: float = 200.0
    height: float = 80.0
    expires_in_days: int = 30
    require_metamask: bool = False


class CompleteInternalSignatureRequest(BaseModel):
    """Request payload to mark an internal signature as completed."""

    signature_id: int
    use_metamask: bool = False
    signer_wallet_address: Optional[str] = None


class PortalSignRequest(BaseModel):
    """Request payload for signing via the portal."""
    signature: str  # Base64 signature data


@signature_router.get("/my-pending", response_model=List[Dict[str, Any]])
async def get_my_pending_signatures(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get current user's pending signatures.
    
    Access control:
    - Requires `SIGNATURE_EXECUTE` permission
    """
    if not has_permission(current_user, PERMISSION_SIGNATURE_EXECUTE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    signatures = db.query(DocumentSignature).filter(
        DocumentSignature.signature_status == "pending"
    ).all()

    # Filter by email in signers list (simplified for now)
    my_signatures: List[Dict[str, Any]] = []
    match_count = 0
    for sig in signatures:
        signers = sig.signers or []
        for signer in signers:
            try:
                signer_email = (signer or {}).get("email")
                if signer_email and signer_email.lower() == (current_user.email or "").lower():
                    my_signatures.append(sig.to_dict())
                    match_count += 1
                    break
            except Exception:
                continue

    return my_signatures


@signature_router.get("/coordinated", response_model=List[Dict[str, Any]])
async def get_coordinated_signatures(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get all signature requests (for coordinators).
    
    Access control:
    - Requires `SIGNATURE_COORDINATE` permission
    """
    if not has_permission(current_user, PERMISSION_SIGNATURE_COORDINATE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    signatures = db.query(DocumentSignature).order_by(DocumentSignature.created_at.desc()).all()
    return [sig.to_dict() for sig in signatures]


@signature_router.post(
    "/internal",
    status_code=status.HTTP_201_CREATED,
)
async def create_internal_signature(
    payload: CreateInternalSignatureRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Create a native/internal signature request for a document.

    Access control:
    - Requires `SIGNATURE_COORDINATE` permission
    """
    if not has_permission(current_user, PERMISSION_SIGNATURE_COORDINATE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to coordinate signatures",
        )

    service = InternalSignatureService(db)

    coords = SignatureCoordinates(
        page=payload.page,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
    )

    try:
        signature = await service.create_signature_request(
            document_id=payload.document_id,
            signer_email=payload.signer_email,
            coordinates=coords,
            expires_in_days=payload.expires_in_days,
            require_metamask=payload.require_metamask,
        )

        return {
            "status": "success",
            "signature": signature.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating internal signature request: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@signature_router.get("/{signature_id}/status")
async def get_signature_status(
    signature_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Get status of a specific signature request."""
    signature = db.query(DocumentSignature).filter(DocumentSignature.id == signature_id).first()
    if not signature:
        raise HTTPException(status_code=404, detail="Signature request not found")
    
    # Optional: refresh status from provider if pending
    if signature.signature_status == "pending" and signature.signature_provider == "digisigner":
        try:
            from app.services.signature_service import SignatureService
            service = SignatureService(db)
            status_data = service.check_signature_status(signature.signature_request_id)
            if status_data.get("status") != signature.signature_status:
                service.update_signature_status(signature.id, status_data.get("status"))
                db.refresh(signature)
        except Exception as exc:
            logger.warning("Failed to refresh DigiSigner status for %s: %s", signature.id, exc)

    return {
        "status": "success",
        "signature": signature.to_dict()
    }


@signature_router.get("/{signature_id}/download")
async def download_signed_document(
    signature_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Download the signed document."""
    signature = db.query(DocumentSignature).filter(DocumentSignature.id == signature_id).first()
    if not signature:
        raise HTTPException(status_code=404, detail="Signature request not found")
    
    if signature.signature_status != "completed":
        raise HTTPException(status_code=400, detail="Document not yet fully signed")
    
    if signature.signature_provider == "internal":
        # Internal signed document download (stub for now)
        raise HTTPException(status_code=501, detail="Internal signed document download not yet implemented")
    
    # DigiSigner download
    try:
        from app.services.signature_service import SignatureService
        from fastapi.responses import StreamingResponse
        import io
        service = SignatureService(db)
        content = service.download_signed_document(signature.signature_request_id)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=signed_document_{signature_id}.pdf"}
        )
    except Exception as exc:
        logger.error("Error downloading signed document: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download signed document")


@signature_router.get("/portal/{token}")
async def get_portal_signature_request(
    token: str,
    db: Session = Depends(get_db),
):
    """Get signature request details for the public portal."""
    # access_token is EncryptedString, so SQLAlchemy filters won't work directly
    # We need to load signatures and decrypt access_token in Python to compare
    # For efficiency, filter by signature_provider="internal" and status="pending" first
    signatures = db.query(DocumentSignature).filter(
        DocumentSignature.signature_provider == "internal",
        DocumentSignature.signature_status == "pending"
    ).all()
    
    signature = None
    for sig in signatures:
        # access_token is automatically decrypted by EncryptedString when accessed
        if sig.access_token == token:
            signature = sig
            break

    if not signature:
        raise HTTPException(status_code=404, detail="Invalid or expired signing link")
    
    if signature.expires_at and signature.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Signing link has expired")
    
    if signature.signature_status == "completed":
        return {
            "status": "completed",
            "document_title": signature.document.title if signature.document else "Document",
            "signer_email": signature.signers[0].get("email") if signature.signers else None,
            "signer_name": signature.signers[0].get("name") if signature.signers and signature.signers[0].get("name") else None,
        }

    return {
        "status": signature.signature_status,
        "document_title": signature.document.title if signature.document else "Document",
        "signer_email": signature.signers[0].get("email") if signature.signers else None,
        "signer_name": signature.signers[0].get("name") if signature.signers and signature.signers[0].get("name") else None,
        "expires_at": signature.expires_at.isoformat() if signature.expires_at else None,
    }


@signature_router.post("/portal/{token}/sign")
async def sign_via_portal(
    token: str,
    payload: PortalSignRequest,
    db: Session = Depends(get_db),
):
    """Submit a signature via the public portal."""
    # access_token is EncryptedString, so SQLAlchemy filters won't work directly
    # We need to load signatures and decrypt access_token in Python to compare
    signatures = db.query(DocumentSignature).filter(
        DocumentSignature.signature_provider == "internal",
        DocumentSignature.signature_status == "pending"
    ).all()
    
    signature = None
    for sig in signatures:
        # access_token is automatically decrypted by EncryptedString when accessed
        if sig.access_token == token:
            signature = sig
            break
    
    if not signature:
        raise HTTPException(status_code=404, detail="Invalid or expired signing link")
    
    if signature.signature_status == "completed":
        raise HTTPException(status_code=400, detail="Document already signed")

    service = InternalSignatureService(db)
    try:
        # For portal signing, we mark as completed. 
        # Pass the base64 signature to complete_signature for PDF injection.
        updated_sig = service.complete_signature(
            signature_id=signature.id,
            signature_data_url=payload.signature
        )
        
        return {
            "status": "success",
            "signature_id": updated_sig.id,
        }
    except Exception as exc:
        logger.error("Error signing via portal: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record signature")
