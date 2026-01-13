"""Twilio webhook routes for handling SMS and voice call status updates."""

import logging
from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

from app.db import get_db
from app.db.models import RecoveryAction
from app.services.twilio_service import TwilioService
from app.core.config import settings # Import settings to get TWILIO_AUTH_TOKEN

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/twilio", tags=["twilio"])

# Initialize Twilio RequestValidator
# Ensure TWILIO_AUTH_TOKEN is set in environment variables or .env file
# Handle case where token might be None (for development without Twilio)
if settings.TWILIO_AUTH_TOKEN is None:
    validator = None
    logger.warning("TWILIO_AUTH_TOKEN not configured. Twilio webhook validation will be disabled.")
else:
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN.get_secret_value())

async def validate_twilio_request(request: Request, form_data: Dict[str, str] = Depends(lambda req: req.form())):
    """
    FastAPI dependency to validate incoming Twilio webhook requests.
    This ensures the request originated from Twilio and has not been tampered with.
    If TWILIO_AUTH_TOKEN is not configured, validation is skipped (for development).
    """
    # Skip validation if validator is None (Twilio not configured)
    if validator is None:
        logger.warning("Twilio webhook validation skipped - TWILIO_AUTH_TOKEN not configured")
        return
    
    signature = request.headers.get("X-Twilio-Signature")
    
    if not signature:
        logger.warning("Twilio webhook received without X-Twilio-Signature header.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No Twilio signature provided")
    
    # Construct the full request URL that Twilio called
    # Important: This URL must exactly match the URL configured in Twilio
    # For local development with ngrok, ensure BASE_URL is set to your ngrok URL.
    # Otherwise, request.url might show 'http' instead of 'https' if behind a proxy.
    request_url = str(request.url)
    
    # Twilio's validator expects the URL to be consistent with what was configured in Twilio
    # If the app is behind a proxy that changes the protocol from https to http,
    # or the host header, `request.url` might not match what Twilio signed.
    # A robust solution might involve constructing the URL from known BASE_URL
    # and path components, especially if BASE_URL includes the scheme and host.
    
    # For now, let's assume request.url accurately reflects what Twilio hit.
    # If this causes validation issues, we may need to use settings.BASE_URL
    # and request.url.path to construct the exact URL Twilio saw.
    
    is_valid = validator.validate(
        request_url,
        form_data, # Use the raw form_data dictionary
        signature
    )
    
    if not is_valid:
        logger.warning(f"Invalid Twilio signature for URL: {request_url}, Signature: {signature}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")
    
    logger.info("Twilio webhook signature validated successfully.")
    return True # Validation successful


@router.post("/webhook/sms")
async def twilio_sms_webhook(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    db: Session = Depends(get_db),
    validated: bool = Depends(validate_twilio_request) # Add validation dependency
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
    db: Session = Depends(get_db),
    validated: bool = Depends(validate_twilio_request) # Add validation dependency
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
    db: Session = Depends(get_db),
    validated: bool = Depends(validate_twilio_request) # Add validation dependency
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