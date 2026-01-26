"""
Deal Signature & Documentation Tracking API Routes.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.models import User, Deal
from app.auth.dependencies import get_current_user, get_db
from app.services.deal_signature_service import DealSignatureService
from app.core.permissions import has_permission, PERMISSION_DOCUMENT_VIEW

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deals", tags=["deal-signatures"])


class RequiredSignature(BaseModel):
    name: str
    email: str
    role: str


class InitializeSignaturesRequest(BaseModel):
    required_signatures: List[RequiredSignature]
    signature_deadline: Optional[datetime] = None


class RequiredDocument(BaseModel):
    document_type: str
    document_category: str
    required_by: Optional[str] = None


class InitializeDocumentationRequest(BaseModel):
    required_documents: List[RequiredDocument]
    documentation_deadline: Optional[datetime] = None


class UpdateSignatureRequest(BaseModel):
    signature_id: int
    signer_email: str


class UpdateDocumentationRequest(BaseModel):
    document_id: int


@router.post("/{deal_id}/signatures/initialize")
async def initialize_deal_signatures(
    deal_id: int,
    request: InitializeSignaturesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize signature requirements for a deal."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    
    required_signatures = [
        {
            "name": sig.name,
            "email": sig.email,
            "role": sig.role
        }
        for sig in request.required_signatures
    ]
    
    try:
        deal = service.initialize_deal_signatures(
            deal_id=deal_id,
            required_signatures=required_signatures,
            signature_deadline=request.signature_deadline
        )
        
        return {
            "status": "success",
            "deal_id": deal_id,
            "signature_status": deal.signature_status,
            "signature_progress": deal.signature_progress
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error initializing deal signatures: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{deal_id}/signature-status")
async def get_deal_signature_status(
    deal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get signature status for a deal."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    try:
        status = service.get_deal_signature_status(deal_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting deal signature status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{deal_id}/signatures/update")
async def update_deal_signature(
    deal_id: int,
    request: UpdateSignatureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update deal signature status (called when signature is completed)."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    try:
        deal = service.update_signature_status(
            deal_id=deal_id,
            signature_id=request.signature_id,
            signer_email=request.signer_email
        )
        
        return {
            "status": "success",
            "deal_id": deal_id,
            "signature_status": deal.signature_status,
            "signature_progress": deal.signature_progress
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating deal signature: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{deal_id}/documentation/initialize")
async def initialize_deal_documentation(
    deal_id: int,
    request: InitializeDocumentationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize documentation requirements for a deal."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    
    required_documents = [
        {
            "document_type": doc.document_type,
            "document_category": doc.document_category,
            "required_by": doc.required_by
        }
        for doc in request.required_documents
    ]
    
    try:
        deal = service.initialize_deal_documentation(
            deal_id=deal_id,
            required_documents=required_documents,
            documentation_deadline=request.documentation_deadline
        )
        
        return {
            "status": "success",
            "deal_id": deal_id,
            "documentation_status": deal.documentation_status,
            "documentation_progress": deal.documentation_progress
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error initializing deal documentation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{deal_id}/documentation-status")
async def get_deal_documentation_status(
    deal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get documentation status for a deal."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    try:
        status = service.get_deal_documentation_status(deal_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting deal documentation status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{deal_id}/documentation/update")
async def update_deal_documentation(
    deal_id: int,
    request: UpdateDocumentationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update deal documentation status (called when document is added)."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    try:
        deal = service.update_documentation_status(
            deal_id=deal_id,
            document_id=request.document_id
        )
        
        return {
            "status": "success",
            "deal_id": deal_id,
            "documentation_status": deal.documentation_status,
            "documentation_progress": deal.documentation_progress
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating deal documentation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{deal_id}/compliance-summary")
async def get_deal_compliance_summary(
    deal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive compliance summary for a deal."""
    if not has_permission(current_user, PERMISSION_DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Verify deal exists and user has access
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
    
    # Check if user is applicant or admin
    if deal.applicant_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = DealSignatureService(db)
    try:
        summary = service.get_deal_compliance_summary(deal_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting deal compliance summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
