"""Twilio service for loan recovery communications."""

import logging
import re
from typing import Optional
from urllib.parse import quote
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from twilio.twiml.voice_response import VoiceResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for sending SMS messages via Twilio."""
    
    def __init__(self):
        self.client = None
        self.phone_number = None
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format (E.164)."""
        # Basic E.164 validation: + followed by 8-15 digits
        pattern = r'^\+[1-9]\d{7,14}$'
        return re.match(pattern, phone_number) is not None
    
    def send_sms(self, to_phone: str, message: str, from_phone: Optional[str] = None, status_callback: Optional[str] = None) -> dict:
        """Send SMS message via Twilio."""
        if not self.client:
            return {"status": "error", "message": "Twilio not configured"}
        
        if not self.validate_phone_number(to_phone):
            return {"status": "error", "message": "Invalid phone number format"}
        
        try:
            from_number = from_phone or self.phone_number
            if not from_number:
                return {"status": "error", "message": "No sender phone number configured"}
            
            message_obj = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_phone,
                status_callback=status_callback
            )
            
            logger.info(f"SMS sent successfully: {message_obj.sid}")
            return {
                "status": "sent",
                "message_sid": message_obj.sid,
                "to": to_phone,
                "error_code": None
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "error_code": getattr(e, 'code', 'unknown')
            }
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return {"status": "error", "message": "Failed to send SMS", "error_code": "unknown"}
    
    def generate_twiml_response(self, message: str, language: str = "en-US") -> str:
        """Generate TwiML for voice response."""
        response = VoiceResponse()
        response.say(message, voice='alice', language=language)
        return str(response)
    
    def make_voice_call(self, to_phone: str, message: str, status_callback: Optional[str] = None) -> dict:
        """Make a voice call using Twilio."""
        if not self.client:
            return {"status": "error", "message": "Twilio not configured"}
        
        if not self.validate_phone_number(to_phone):
            return {"status": "error", "message": "Invalid phone number format"}
        
        try:
            # Generate TwiML for voice message
            twiml = self.generate_twiml_response(message)
            
            # For simplicity, we'll use a direct call with a TwiML URL
            # In production, you would host this TwiML on a web server
            call = self.client.calls.create(
                twiml=twiml,
                to=to_phone,
                from_=self.phone_number,
                status_callback=status_callback
            )
            
            logger.info(f"Voice call initiated successfully: {call.sid}")
            return {
                "status": "initiated",
                "call_sid": call.sid,
                "to": to_phone,
                "error_code": None
            }
            
        except TwilioException as e:
            logger.error(f"Twilio voice call failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "error_code": getattr(e, 'code', 'unknown')
            }
        except Exception as e:
            logger.error(f"Unexpected error making voice call: {e}")
            return {"status": "error", "message": "Failed to make voice call", "error_code": "unknown"}

