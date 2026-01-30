"""KYC and Identity Verification API routes."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.jwt_auth import require_auth
from app.db.models import User, KYCDocument
from app.services.kyc_service import KYCService

logger = logging.getLogger(__name__)

kyc_router = APIRouter(prefix="/kyc", tags=["kyc"])


class InitiateKYCRequest(BaseModel):
    level: str = "basic"


class KYCDocumentUploadRequest(BaseModel):
    document_id: int
    document_type: str
    document_category: str


class LicenseUploadRequest(BaseModel):
    license_type: str
    license_number: str
    license_category: str
    issuing_authority: str
    document_id: Optional[int] = None


@kyc_router.post("/initiate")
async def initiate_kyc(
    payload: InitiateKYCRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Initiate KYC verification process."""
    service = KYCService(db)
    verification = service.initiate_kyc_verification(current_user.id, level=payload.level)
    return {"status": "success", "verification": verification.to_dict()}


@kyc_router.post("/documents/upload")
async def upload_kyc_document(
    payload: KYCDocumentUploadRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Link an uploaded document to KYC verification."""
    service = KYCService(db)
    doc = service.upload_kyc_document(
        current_user.id, payload.document_id, payload.document_type, payload.document_category
    )
    return {"status": "success", "document": doc.to_dict()}


@kyc_router.post("/licenses/upload")
async def upload_license(
    payload: LicenseUploadRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add a professional license."""
    service = KYCService(db)
    license = service.upload_license(
        user_id=current_user.id,
        license_type=payload.license_type,
        license_number=payload.license_number,
        category=payload.license_category,
        issuing_authority=payload.issuing_authority,
        document_id=payload.document_id
    )
    return {"status": "success", "license": license.to_dict()}


@kyc_router.get("/status")
async def get_kyc_status(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get current user's KYC status with latest policy evaluation, if available."""
    service = KYCService(db)
    if not current_user.kyc_verification:
        return {"status": "not_initiated"}

    # Re-evaluate KYC so policy rules see latest documents/licenses
    evaluation = service.evaluate_kyc_compliance(current_user.id)
    verification = current_user.kyc_verification.to_dict()
    return {
        "status": "success",
        "verification": verification,
        "evaluation": evaluation,
    }


@kyc_router.get("/requirements/{deal_type}")
async def get_kyc_requirements(
    deal_type: str,
    db: Session = Depends(get_db),
):
    """Get KYC requirements for a specific deal type."""
    service = KYCService(db)
    requirements = service.get_kyc_requirements(deal_type)
    return {"status": "success", "requirements": requirements}


@kyc_router.post("/evaluate")
async def evaluate_kyc(
    deal_type: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """User KYC evaluation (current user). For profile/compliance KYC use POST /api/compliance/kyc/evaluate."""
    service = KYCService(db)
    result = service.evaluate_kyc_compliance(current_user.id, deal_type=deal_type)
    return {"status": "success", "evaluation": result}


# --- Admin KYC (instance administrator) ---

def _require_admin_or_reviewer(user: User) -> None:
    if getattr(user, "role", None) not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin or reviewer access required"},
        )


class VerifyDocumentRequest(BaseModel):
    """Request body for verifying a KYC document."""
    verification_status: str = Field(..., description="verified or rejected")


class KYCReviewRequest(BaseModel):
    """Request body for completing KYC review."""
    kyc_status: str = Field(..., description="completed or rejected")
    rejection_reason: Optional[str] = Field(None, description="Reason when kyc_status is rejected")


@kyc_router.get("/admin/pending-documents")
async def list_pending_kyc_documents(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List KYC documents with verification_status pending (admin/reviewer)."""
    _require_admin_or_reviewer(current_user)
    query = db.query(KYCDocument).filter(KYCDocument.verification_status == "pending")
    if user_id is not None:
        query = query.filter(KYCDocument.user_id == user_id)
    docs = query.order_by(KYCDocument.created_at.desc()).all()
    return {
        "status": "success",
        "documents": [
            {
                "id": d.id,
                "user_id": d.user_id,
                "document_type": d.document_type,
                "document_category": d.document_category,
                "document_id": d.document_id,
                "verification_status": d.verification_status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    }


@kyc_router.post("/admin/documents/{kyc_document_id}/verify")
async def verify_kyc_document(
    kyc_document_id: int,
    body: VerifyDocumentRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Set verification status of a KYC document (admin/reviewer)."""
    _require_admin_or_reviewer(current_user)
    if body.verification_status not in ("verified", "rejected"):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "verification_status must be verified or rejected"},
        )
    service = KYCService(db)
    try:
        doc = service.verify_kyc_document(
            kyc_document_id, body.verification_status, current_user.id
        )
        return {"status": "success", "document": doc.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": "error", "message": str(e)})


@kyc_router.post("/admin/users/{user_id}/kyc-review")
async def complete_kyc_review(
    user_id: int,
    body: KYCReviewRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Complete or reject a user's KYC verification (admin/reviewer)."""
    _require_admin_or_reviewer(current_user)
    if body.kyc_status not in ("completed", "rejected"):
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "kyc_status must be completed or rejected"},
        )
    service = KYCService(db)
    try:
        verification = service.complete_kyc_review(
            user_id, body.kyc_status, current_user.id, body.rejection_reason
        )
        return {"status": "success", "verification": verification.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": "error", "message": str(e)})
