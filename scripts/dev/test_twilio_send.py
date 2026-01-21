#!/usr/bin/env python3
"""
Test script to send a test SMS message using Twilio configuration.

This script tests the Twilio integration by sending a test message
to the configured target phone number.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.twilio_service import TwilioService
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Send a test SMS message via Twilio."""
    target_phone = "+13022537220"  # User's test number
    test_message = "Test message from CreditNexus loan recovery system. This is a test of the Twilio integration."
    
    print("=" * 80)
    print("Twilio SMS Test Script")
    print("=" * 80)
    print(f"Target Phone: {target_phone}")
    print(f"Twilio Enabled: {settings.TWILIO_ENABLED}")
    print(f"SMS Enabled: {settings.TWILIO_SMS_ENABLED}")
    print(f"Voice Enabled: {settings.TWILIO_VOICE_ENABLED}")
    
    if settings.TWILIO_PHONE_NUMBER:
        print(f"From Phone: {settings.TWILIO_PHONE_NUMBER}")
    else:
        print("WARNING: TWILIO_PHONE_NUMBER not configured")
    
    if settings.TWILIO_ACCOUNT_SID:
        account_sid = settings.TWILIO_ACCOUNT_SID.get_secret_value() if hasattr(settings.TWILIO_ACCOUNT_SID, 'get_secret_value') else str(settings.TWILIO_ACCOUNT_SID)
        print(f"Account SID: {account_sid[:8]}...{account_sid[-4:] if len(account_sid) > 12 else '****'}")
    else:
        print("WARNING: TWILIO_ACCOUNT_SID not configured")
    
    print("=" * 80)
    print()
    
    # Check if Twilio is enabled
    if not settings.TWILIO_ENABLED:
        print("ERROR: Twilio is not enabled. Set TWILIO_ENABLED=true in .env")
        return 1
    
    if not settings.TWILIO_SMS_ENABLED:
        print("ERROR: Twilio SMS is not enabled. Set TWILIO_SMS_ENABLED=true in .env")
        return 1
    
    # Initialize Twilio service
    try:
        twilio_service = TwilioService()
        
        if not twilio_service.client:
            print("ERROR: Twilio client not initialized. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
            return 1
        
        print("[OK] Twilio service initialized successfully")
        print()
        
        # Validate phone number
        if not twilio_service.validate_phone_number(target_phone):
            print(f"ERROR: Invalid phone number format: {target_phone}")
            print("Phone number must be in E.164 format (e.g., +1234567890)")
            return 1
        
        print(f"[OK] Phone number validated: {target_phone}")
        print()
        
        # Send SMS
        print(f"Sending SMS to {target_phone}...")
        print(f"Message: {test_message}")
        print()
        
        result = twilio_service.send_sms(
            to_phone=target_phone,
            message=test_message,
            status_callback=settings.TWILIO_WEBHOOK_URL
        )
        
        print("=" * 80)
        print("Result:")
        print("=" * 80)
        
        if result["status"] == "sent":
            print("[SUCCESS] SMS sent successfully!")
            print(f"  Message SID: {result.get('message_sid', 'N/A')}")
            print(f"  To: {result.get('to', target_phone)}")
            print()
            print("Check your phone for the test message.")
            return 0
        else:
            print("[ERROR] Failed to send SMS")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Message: {result.get('message', 'No error message')}")
            if result.get('error_code'):
                print(f"  Error Code: {result['error_code']}")
            return 1
            
    except Exception as e:
        print("=" * 80)
        print("EXCEPTION:")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
