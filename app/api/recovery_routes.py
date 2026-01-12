"""Loan recovery API routes for managing defaults and recovery actions."""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import sqlalchemy as sa

from app.db import get_db
from app.db.models import LoanDefault, RecoveryAction, BorrowerContact, User
from app.auth.jwt_auth import get_current_user, require_auth
from app.services.loan_recovery_service import LoanRecoveryService
from app.services.twilio_service import TwilioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


# Pydantic models for request/response
class LoanDefaultResponse(BaseModel):
    id: int
    loan_id: str
    deal_id: Optional[int]
    default_type: str
    default_date: datetime
    default_reason: Optional[str]
    amount_overdue: Optional[float]
    days_past_due: int
    severity: str
    status: str
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    cdm_events: Optional[dict]
    extra_data: Optional[dict]
    created_at: datetime
    updated_at: datetime


class RecoveryActionResponse(BaseModel):
    id: int
    loan_default_id: int
    action_type: str
    communication_method: str
    recipient_phone: Optional[str]
    recipient_email: Optional[str]
    message_content: str
    twilio_message_sid: Optional[str]
    twilio_call_sid: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    response_received_at: Optional[datetime]
    error_message: Optional[str]
    created_by: Optional[int]
    extra_data: Optional[dict]
    created_at: datetime
    updated_at: datetime


class BorrowerContactResponse(BaseModel):
    id: int
    deal_id: int
    user_id: Optional[int]
    contact_name: str
    phone_number: Optional[str]
    email: Optional[str]
    preferred_contact_method: str
    contact_preferences: Optional[dict]
    is_primary: bool
    is_active: bool
    extra_data: Optional[dict]
    created_at: datetime
    updated_at: datetime


class DetectDefaultsRequest(BaseModel):
    deal_id: Optional[int] = None


class RecoveryActionCreate(BaseModel):
    action_types: Optional[List[str]] = None


@router.get("/defaults", response_model=List[LoanDefaultResponse])
async def get_loan_defaults(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get active loan defaults with optional filters."""
    try:
        recovery_service = LoanRecoveryService(db)
        defaults = recovery_service.get_active_defaults(deal_id=deal_id, status=status)
        
        return [LoanDefaultResponse(**default.to_dict()) for default in defaults]
    
    except Exception as e:
        logger.error(f"Error getting loan defaults: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve loan defaults")


@router.post("/defaults/detect", response_model=List[LoanDefaultResponse])
async def detect_loan_defaults(
    request: DetectDefaultsRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Detect payment defaults for specified deals."""
    try:
        recovery_service = LoanRecoveryService(db)
        defaults = recovery_service.detect_payment_defaults(deal_id=request.deal_id)
        
        # Log audit action
        from app.api.routes import log_audit_action
        for default in defaults:
            log_audit_action(
                db=db,
                action="CREATE",
                target_type="loan_default",
                target_id=default.id,
                user_id=current_user.id,
                metadata={"loan_id": default.loan_id, "severity": default.severity}
            )
        
        db.commit()
        return [LoanDefaultResponse(**default.to_dict()) for default in defaults]
    
    except Exception as e:
        logger.error(f"Error detecting loan defaults: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect loan defaults")


@router.get("/defaults/{default_id}", response_model=LoanDefaultResponse)
async def get_loan_default(
    default_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get details of a specific loan default including related recovery actions."""
    try:
        default = db.query(LoanDefault).get(default_id)
        if not default:
            raise HTTPException(status_code=404, detail="Loan default not found")
        
        return LoanDefaultResponse(**default.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting loan default {default_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve loan default")


@router.post("/defaults/{default_id}/actions", response_model=List[RecoveryActionResponse])
async def trigger_recovery_actions(
    default_id: int,
    request: RecoveryActionCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Trigger recovery actions for a loan default."""
    try:
        recovery_service = LoanRecoveryService(db)
        actions = recovery_service.trigger_recovery_actions(
            default_id=default_id,
            action_types=request.action_types
        )
        
        # Log audit actions
        from app.api.routes import log_audit_action
        for action in actions:
            log_audit_action(
                db=db,
                action="CREATE",
                target_type="recovery_action",
                target_id=action.id,
                user_id=current_user.id,
                metadata={
                    "loan_default_id": action.loan_default_id,
                    "action_type": action.action_type,
                    "status": action.status
                }
            )
        
        db.commit()
        return [RecoveryActionResponse(**action.to_dict()) for action in actions]
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering recovery actions for default {default_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger recovery actions")


@router.get("/actions", response_model=List[RecoveryActionResponse])
async def get_recovery_actions(
    default_id: Optional[int] = Query(None, description="Filter by default ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get recovery actions with optional filters."""
    try:
        query = db.query(RecoveryAction)
        
        if default_id:
            query = query.filter(RecoveryAction.loan_default_id == default_id)
        
        if status:
            query = query.filter(RecoveryAction.status == status)
        
        if deal_id:
            # Join with loan_defaults to filter by deal_id
            query = query.join(LoanDefault) \
                .filter(LoanDefault.deal_id == deal_id)
        
        actions = query.order_by(RecoveryAction.created_at.desc()).all()
        return [RecoveryActionResponse(**action.to_dict()) for action in actions]
    
    except Exception as e:
        logger.error(f"Error getting recovery actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recovery actions")


@router.post("/actions/{action_id}/execute", response_model=RecoveryActionResponse)
async def execute_recovery_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Manually execute a pending recovery action."""
    try:
        recovery_service = LoanRecoveryService(db)
        action = recovery_service.execute_recovery_action(action_id)
        
        # Log audit action
        from app.api.routes import log_audit_action
        log_audit_action(
            db=db,
            action="UPDATE",
            target_type="recovery_action",
            target_id=action.id,
            user_id=current_user.id,
            metadata={
                "status": action.status,
                "communication_method": action.communication_method
            }
        )
        
        db.commit()
        return RecoveryActionResponse(**action.to_dict())
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing recovery action {action_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute recovery action")


@router.get("/actions/{action_id}", response_model=RecoveryActionResponse)
async def get_recovery_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get details of a specific recovery action."""
    try:
        action = db.query(RecoveryAction).get(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Recovery action not found")
        
        return RecoveryActionResponse(**action.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting recovery action {action_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recovery action")


@router.post("/actions/scheduled/process")
async def process_scheduled_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Process all scheduled recovery actions that are due for execution."""
    try:
        recovery_service = LoanRecoveryService(db)
        result = recovery_service.process_scheduled_actions()
        
        # Log audit action
        from app.api.routes import log_audit_action
        log_audit_action(
            db=db,
            action="UPDATE",
            target_type="recovery_actions",
            user_id=current_user.id,
            metadata={
                "processed_count": result["total_processed"],
                "success_count": result["success_count"]
            }
        )
        
        db.commit()
        return {
            "status": "success",
            "message": "Scheduled actions processed successfully",
            **result
        }
    
    except Exception as e:
        logger.error(f"Error processing scheduled actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to process scheduled actions")


@router.post("/trigger-one-day-overdue-sms-reminders")
async def trigger_one_day_overdue_sms_reminders_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Triggers SMS reminders for all loans that are exactly 1 day overdue.
    This endpoint calls the LoanRecoveryService to identify and send reminders.
    """
    try:
        recovery_service = LoanRecoveryService(db)
        result = recovery_service.trigger_one_day_overdue_sms_reminders()
        
        # Log audit action for triggering
        from app.api.routes import log_audit_action
        log_audit_action(
            db=db,
            action="CREATE",
            target_type="recovery_sms_reminders",
            user_id=current_user.id,
            metadata={
                "event_type": "1_day_overdue",
                "triggered_count": result.get("sms_reminders_triggered")
            }
        )
        
        db.commit()
        return {
            "status": "success",
            "message": "One-day overdue SMS reminders triggered successfully",
            **result
        }
    except Exception as e:
        logger.error(f"Error triggering one-day overdue SMS reminders: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger one-day overdue SMS reminders")


@router.get("/contacts", response_model=List[BorrowerContactResponse])
async def get_borrower_contacts(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get borrower contacts with optional filters."""
    try:
        query = db.query(BorrowerContact)
        
        if deal_id:
            query = query.filter(BorrowerContact.deal_id == deal_id)
        
        contacts = query.order_by(BorrowerContact.is_primary.desc()).all()
        return [BorrowerContactResponse(**contact.to_dict()) for contact in contacts]
    
    except Exception as e:
        logger.error(f"Error getting borrower contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve borrower contacts")


@router.post("/contacts", response_model=BorrowerContactResponse)
async def create_borrower_contact(
    contact_data: BorrowerContactResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Create a new borrower contact."""
    try:
        # Convert Pydantic model to dict and create BorrowerContact
        contact_dict = contact_data.dict()
        contact = BorrowerContact(**contact_dict)
        
        db.add(contact)
        db.flush()
        
        # Log audit action
        from app.api.routes import log_audit_action
        log_audit_action(
            db=db,
            action="CREATE",
            target_type="borrower_contact",
            target_id=contact.id,
            user_id=current_user.id,
            metadata={"deal_id": contact.deal_id, "contact_name": contact.contact_name}
        )
        
        db.commit()
        return BorrowerContactResponse(**contact.to_dict())
    
    except Exception as e:
        logger.error(f"Error creating borrower contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to create borrower contact")


@router.put("/contacts/{contact_id}", response_model=BorrowerContactResponse)
async def update_borrower_contact(
    contact_id: int,
    contact_data: BorrowerContactResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Update an existing borrower contact."""
    try:
        contact = db.query(BorrowerContact).get(contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Borrower contact not found")
        
        # Update contact with new data
        for key, value in contact_data.dict().items():
            setattr(contact, key, value)
        
        # Log audit action
        from app.api.routes import log_audit_action
        log_audit_action(
            db=db,
            action="UPDATE",
            target_type="borrower_contact",
            target_id=contact.id,
            user_id=current_user.id,
            metadata={"deal_id": contact.deal_id, "contact_name": contact.contact_name}
        )
        
        db.commit()
        return BorrowerContactResponse(**contact.to_dict())
    
    except Exception as e:
        logger.error(f"Error updating borrower contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update borrower contact")


@router.get("/summary")
async def get_recovery_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get summary statistics for loan recovery."""
    try:
        # Count defaults by status
        defaults_by_status = db.query(
            LoanDefault.status,
            sa.func.count(LoanDefault.id)
        ).group_by(LoanDefault.status).all()
        
        # Count defaults by severity
        defaults_by_severity = db.query(
            LoanDefault.severity,
            sa.func.count(LoanDefault.id)
        ).group_by(LoanDefault.severity).all()
        
        # Count actions by status
        actions_by_status = db.query(
            RecoveryAction.status,
            sa.func.count(RecoveryAction.id)
        ).group_by(RecoveryAction.status).all()
        
        return {
            "defaults_by_status": {status: count for status, count in defaults_by_status},
            "defaults_by_severity": {severity: count for severity, count in defaults_by_severity},
            "actions_by_status": {status: count for status, count in actions_by_status},
            "total_defaults": sum(count for _, count in defaults_by_status),
            "total_actions": sum(count for _, count in actions_by_status)
        }
    
    except Exception as e:
        logger.error(f"Error getting recovery summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recovery summary")