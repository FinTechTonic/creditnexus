"""Twilio webhook routes for handling SMS and voice call status updates."""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import RecoveryAction
from app.services.twilio_service import TwilioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])


@router.post("/webhook/sms")
async def twilio_sms_webhook(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle Twilio SMS status webhooks."""
    logger.info(f"Received Twilio SMS webhook for MessageSid: {MessageSid}, Status: {MessageStatus}")
    
    try:
        # Update recovery action status
        action = db.query(RecoveryAction) \
            .filter(RecoveryAction.twilio_message_sid == MessageSid) \
            .first()
        
        if action:
            action.status = MessageStatus
            if MessageStatus == "delivered":
                action.delivered_at = datetime.now()
            elif MessageStatus == "failed":
                action.error_message = f"SMS delivery failed: {MessageStatus}"
            
            db.commit()
            logger.info(f"Updated recovery action {action.id} status to {MessageStatus}")
        else:
            logger.warning(f"No recovery action found for MessageSid: {MessageSid}")
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing Twilio SMS webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.post("/webhook/voice")
async def twilio_voice_webhook(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle Twilio voice call status webhooks."""
    logger.info(f"Received Twilio voice webhook for CallSid: {CallSid}, Status: {CallStatus}")
    
    try:
        # Update recovery action status
        action = db.query(RecoveryAction) \
            .filter(RecoveryAction.twilio_call_sid == CallSid) \
            .first()
        
        if action:
            # Map Twilio call status to our recovery action status
            status_mapping = {
                "completed": "delivered",
                "in-progress": "sent",
                "busy": "failed",
                "failed": "failed",
                "no-answer": "failed",
                "canceled": "failed"
            }
            
            action.status = status_mapping.get(CallStatus, "failed")
            
            if CallStatus == "completed":
                action.delivered_at = datetime.now()
            elif CallStatus in ["busy", "failed", "no-answer", "canceled"]:
                action.error_message = f"Call failed: {CallStatus}"
            
            db.commit()
            logger.info(f"Updated recovery action {action.id} status to {action.status}")
        else:
            logger.warning(f"No recovery action found for CallSid: {CallSid}")
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing Twilio voice webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.post("/webhook/status")
async def twilio_status_webhook(
    request: Request,
    MessageSid: Optional[str] = Form(None),
    CallSid: Optional[str] = Form(None),
    MessageStatus: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Handle Twilio status webhooks (unified endpoint for both SMS and voice)."""
    logger.info(f"Received Twilio status webhook")
    
    try:
        action = None
        
        # Determine if this is for SMS or voice
        if MessageSid:
            action = db.query(RecoveryAction) \
                .filter(RecoveryAction.twilio_message_sid == MessageSid) \
                .first()
            if action and MessageStatus:
                action.status = MessageStatus
                if MessageStatus == "delivered":
                    action.delivered_at = datetime.now()
        
        elif CallSid:
            action = db.query(RecoveryAction) \
                .filter(RecoveryAction.twilio_call_sid == CallSid) \
                .first()
            if action and CallStatus:
                status_mapping = {
                    "completed": "delivered",
                    "in-progress": "sent",
                    "busy": "failed",
                    "failed": "failed",
                    "no-answer": "failed",
                    "canceled": "failed"
                }
                action.status = status_mapping.get(CallStatus, "failed")
                if CallStatus == "completed":
                    action.delivered_at = datetime.now()
        
        if action:
            db.commit()
            logger.info(f"Updated recovery action {action.id} status to {action.status}")
        else:
            logger.warning("No recovery action found for the provided SID")
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing Twilio status webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/webhook/test")
async def test_twilio_webhook():
    """Test endpoint for Twilio webhook configuration."""
    return {
        "status": "success",
        "message": "Twilio webhook endpoint is working",
        "endpoints": {
            "sms": "/api/twilio/webhook/sms",
            "voice": "/api/twilio/webhook/voice",
            "status": "/api/twilio/webhook/status"
        }
    }