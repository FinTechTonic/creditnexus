"""KYC and Identity Verification API routes."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db
from app.db.models import User
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiate KYC verification process."""
    service = KYCService(db)
    verification = service.initiate_kyc_verification(current_user.id, level=payload.level)
    return {"status": "success", "verification": verification.to_dict()}


@kyc_router.post("/documents/upload")
async def upload_kyc_document(
    payload: KYCDocumentUploadRequest,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run KYC compliance evaluation."""
    service = KYCService(db)
    result = service.evaluate_kyc_compliance(current_user.id, deal_type=deal_type)
    return {"status": "success", "evaluation": result}
