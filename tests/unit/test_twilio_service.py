"""
Unit tests for TwilioService with mocked Twilio API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from twilio.base.exceptions import TwilioException, TwilioRestException

from app.services.twilio_service import TwilioService
from app.core.config import settings


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client."""
    client = MagicMock()
    return client


@pytest.fixture
def twilio_service_enabled(mock_twilio_client):
    """TwilioService with Twilio enabled and mocked client."""
    with patch('app.services.twilio_service.settings') as mock_settings, \
         patch('app.services.twilio_service.Client') as mock_client_class:
        mock_settings.TWILIO_ENABLED = True
        mock_settings.TWILIO_SMS_ENABLED = True
        mock_settings.TWILIO_VOICE_ENABLED = True
        mock_settings.TWILIO_PHONE_NUMBER = "+1234567890"
        mock_settings.TWILIO_ACCOUNT_SID = Mock(get_secret_value=lambda: "test_account_sid")
        mock_settings.TWILIO_AUTH_TOKEN = Mock(get_secret_value=lambda: "test_auth_token")
        
        mock_client_class.return_value = mock_twilio_client
        
        service = TwilioService()
        service.client = mock_twilio_client
        return service


@pytest.fixture
def twilio_service_disabled():
    """TwilioService with Twilio disabled."""
    with patch('app.services.twilio_service.settings') as mock_settings:
        mock_settings.TWILIO_ENABLED = False
        mock_settings.TWILIO_SMS_ENABLED = False
        mock_settings.TWILIO_VOICE_ENABLED = False
        
        service = TwilioService()
        return service


class TestPhoneNumberValidation:
    """Test phone number validation."""
    
    def test_validate_valid_e164_phone_number(self, twilio_service_enabled):
        """Test validation of valid E.164 phone numbers."""
        valid_numbers = [
            "+1234567890",
            "+441234567890",
            "+33123456789",
            "+8612345678901"
        ]
        
        for phone in valid_numbers:
            assert twilio_service_enabled.validate_phone_number(phone) is True
    
    def test_validate_invalid_phone_numbers(self, twilio_service_enabled):
        """Test validation of invalid phone numbers."""
        invalid_numbers = [
            "1234567890",  # Missing +
            "+12345678901234567890",  # Too long (>15 digits after +)
            "+0123456789",  # Starts with 0 (invalid country code)
            "123-456-7890",  # Wrong format
            "(123) 456-7890",  # Wrong format
            "+1-234-567-890",  # Contains dashes
            "+abc123",  # Contains letters
            "",  # Empty
            None,  # None
        ]
        
        for phone in invalid_numbers:
            if phone is not None:
                result = twilio_service_enabled.validate_phone_number(phone)
                assert result is False, f"Expected {phone} to be invalid, but validation returned {result}"


class TestSendSMS:
    """Test SMS sending functionality."""
    
    def test_send_sms_success(self, twilio_service_enabled, mock_twilio_client):
        """Test successful SMS sending."""
        # Mock message object
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890abcdef"
        mock_twilio_client.messages.create.return_value = mock_message
        
        result = twilio_service_enabled.send_sms(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "sent"
        assert result["message_sid"] == "SM1234567890abcdef"
        assert result["to"] == "+1234567890"
        assert result["error_code"] is None
        mock_twilio_client.messages.create.assert_called_once()
    
    def test_send_sms_with_status_callback(self, twilio_service_enabled, mock_twilio_client):
        """Test SMS sending with status callback URL."""
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890abcdef"
        mock_twilio_client.messages.create.return_value = mock_message
        
        result = twilio_service_enabled.send_sms(
            to_phone="+1234567890",
            message="Test message",
            status_callback="https://example.com/webhook"
        )
        
        assert result["status"] == "sent"
        call_args = mock_twilio_client.messages.create.call_args[1]
        assert call_args["status_callback"] == "https://example.com/webhook"
    
    def test_send_sms_invalid_phone_number(self, twilio_service_enabled):
        """Test SMS sending with invalid phone number."""
        result = twilio_service_enabled.send_sms(
            to_phone="1234567890",  # Missing +
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert "Invalid phone number format" in result["message"]
    
    def test_send_sms_twilio_disabled(self, twilio_service_disabled):
        """Test SMS sending when Twilio is disabled."""
        result = twilio_service_disabled.send_sms(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert "not enabled" in result["message"] or "not configured" in result["message"]
    
    def test_send_sms_twilio_rest_exception(self, twilio_service_enabled, mock_twilio_client):
        """Test SMS sending with Twilio REST exception."""
        error = TwilioRestException(
            status=400,
            uri="https://api.twilio.com/2010-04-01/Accounts/.../Messages.json",
            msg="Invalid phone number"
        )
        error.code = 21211
        mock_twilio_client.messages.create.side_effect = error
        
        result = twilio_service_enabled.send_sms(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert result["error_code"] == 21211
    
    def test_send_sms_twilio_exception(self, twilio_service_enabled, mock_twilio_client):
        """Test SMS sending with generic Twilio exception."""
        error = TwilioException("Connection error")
        mock_twilio_client.messages.create.side_effect = error
        
        result = twilio_service_enabled.send_sms(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert "Connection error" in result["message"]
    
    def test_send_sms_no_sender_phone(self, twilio_service_enabled):
        """Test SMS sending when no sender phone is configured."""
        with patch('app.services.twilio_service.settings') as mock_settings:
            mock_settings.TWILIO_ENABLED = True
            mock_settings.TWILIO_SMS_ENABLED = True
            mock_settings.TWILIO_PHONE_NUMBER = None
            
            result = twilio_service_enabled.send_sms(
                to_phone="+1234567890",
                message="Test message"
            )
            
            assert result["status"] == "error"
            assert "No sender phone number" in result["message"]


class TestMakeVoiceCall:
    """Test voice call functionality."""
    
    def test_make_voice_call_success(self, twilio_service_enabled, mock_twilio_client):
        """Test successful voice call."""
        mock_call = MagicMock()
        mock_call.sid = "CA1234567890abcdef"
        mock_call.status = "queued"
        mock_twilio_client.calls.create.return_value = mock_call
        
        result = twilio_service_enabled.make_voice_call(
            to_phone="+1234567890",
            message="Test voice message"
        )
        
        assert result["status"] == "queued"
        assert result["call_sid"] == "CA1234567890abcdef"
        assert result["to"] == "+1234567890"
        assert result["error_code"] is None
        mock_twilio_client.calls.create.assert_called_once()
    
    def test_make_voice_call_with_twiml_url(self, twilio_service_enabled, mock_twilio_client):
        """Test voice call with TwiML URL."""
        mock_call = MagicMock()
        mock_call.sid = "CA1234567890abcdef"
        mock_call.status = "queued"
        mock_twilio_client.calls.create.return_value = mock_call
        
        result = twilio_service_enabled.make_voice_call(
            to_phone="+1234567890",
            message="Test message",
            twiml_url="https://example.com/twiml"
        )
        
        assert result["status"] == "queued"
        call_args = mock_twilio_client.calls.create.call_args[1]
        assert call_args["url"] == "https://example.com/twiml"
        assert "twiml" not in call_args
    
    def test_make_voice_call_with_status_callback(self, twilio_service_enabled, mock_twilio_client):
        """Test voice call with status callback URL."""
        mock_call = MagicMock()
        mock_call.sid = "CA1234567890abcdef"
        mock_call.status = "queued"
        mock_twilio_client.calls.create.return_value = mock_call
        
        result = twilio_service_enabled.make_voice_call(
            to_phone="+1234567890",
            message="Test message",
            status_callback="https://example.com/webhook"
        )
        
        assert result["status"] == "queued"
        call_args = mock_twilio_client.calls.create.call_args[1]
        assert call_args["status_callback"] == "https://example.com/webhook"
    
    def test_make_voice_call_invalid_phone_number(self, twilio_service_enabled):
        """Test voice call with invalid phone number."""
        result = twilio_service_enabled.make_voice_call(
            to_phone="1234567890",  # Missing +
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert "Invalid phone number format" in result["message"]
    
    def test_make_voice_call_twilio_disabled(self, twilio_service_disabled):
        """Test voice call when Twilio is disabled."""
        result = twilio_service_disabled.make_voice_call(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert "not enabled" in result["message"] or "not configured" in result["message"]
    
    def test_make_voice_call_twilio_rest_exception(self, twilio_service_enabled, mock_twilio_client):
        """Test voice call with Twilio REST exception."""
        error = TwilioRestException(
            status=400,
            uri="https://api.twilio.com/2010-04-01/Accounts/.../Calls.json",
            msg="Invalid phone number"
        )
        error.code = 21211
        mock_twilio_client.calls.create.side_effect = error
        
        result = twilio_service_enabled.make_voice_call(
            to_phone="+1234567890",
            message="Test message"
        )
        
        assert result["status"] == "error"
        assert result["error_code"] == 21211


class TestGetMessageStatus:
    """Test message status checking."""
    
    def test_get_message_status_success(self, twilio_service_enabled, mock_twilio_client):
        """Test successful message status retrieval."""
        mock_message = MagicMock()
        mock_message.status = "delivered"
        mock_message.error_code = None
        mock_message.date_sent = datetime(2026, 1, 15, 12, 0, 0)
        mock_message.date_updated = datetime(2026, 1, 15, 12, 0, 1)
        
        mock_twilio_client.messages.return_value.fetch.return_value = mock_message
        
        result = twilio_service_enabled.get_message_status("SM1234567890abcdef")
        
        assert result["status"] == "delivered"
        assert result["error_code"] is None
        assert result["date_sent"] == "2026-01-15T12:00:00"
        assert result["date_updated"] == "2026-01-15T12:00:01"
    
    def test_get_message_status_twilio_exception(self, twilio_service_enabled, mock_twilio_client):
        """Test message status retrieval with Twilio exception."""
        error = TwilioException("Message not found")
        mock_twilio_client.messages.return_value.fetch.side_effect = error
        
        result = twilio_service_enabled.get_message_status("SM1234567890abcdef")
        
        assert result["status"] == "error"
        assert "Message not found" in result["message"]
    
    def test_get_message_status_not_configured(self):
        """Test message status when Twilio is not configured."""
        with patch('app.services.twilio_service.settings') as mock_settings:
            mock_settings.TWILIO_ENABLED = False
            service = TwilioService()
            
            result = service.get_message_status("SM1234567890abcdef")
            
            assert result["status"] == "error"
            assert "not configured" in result["message"]


class TestGetCallStatus:
    """Test call status checking."""
    
    def test_get_call_status_success(self, twilio_service_enabled, mock_twilio_client):
        """Test successful call status retrieval."""
        mock_call = MagicMock()
        mock_call.status = "completed"
        mock_call.duration = 120
        mock_call.start_time = datetime(2026, 1, 15, 12, 0, 0)
        mock_call.end_time = datetime(2026, 1, 15, 12, 2, 0)
        
        mock_twilio_client.calls.return_value.fetch.return_value = mock_call
        
        result = twilio_service_enabled.get_call_status("CA1234567890abcdef")
        
        assert result["status"] == "completed"
        assert result["duration"] == 120
        assert result["start_time"] == "2026-01-15T12:00:00"
        assert result["end_time"] == "2026-01-15T12:02:00"
    
    def test_get_call_status_twilio_exception(self, twilio_service_enabled, mock_twilio_client):
        """Test call status retrieval with Twilio exception."""
        error = TwilioException("Call not found")
        mock_twilio_client.calls.return_value.fetch.side_effect = error
        
        result = twilio_service_enabled.get_call_status("CA1234567890abcdef")
        
        assert result["status"] == "error"
        assert "Call not found" in result["message"]
    
    def test_get_call_status_not_configured(self):
        """Test call status when Twilio is not configured."""
        with patch('app.services.twilio_service.settings') as mock_settings:
            mock_settings.TWILIO_ENABLED = False
            service = TwilioService()
            
            result = service.get_call_status("CA1234567890abcdef")
            
            assert result["status"] == "error"
            assert "not configured" in result["message"]


class TestTwiMLGeneration:
    """Test TwiML generation."""
    
    def test_generate_twiml_response_basic(self, twilio_service_enabled):
        """Test basic TwiML response generation."""
        twiml = twilio_service_enabled.generate_twiml_response("Hello, this is a test message")
        
        assert "<?xml" in twiml
        assert "Response" in twiml
        assert "Say" in twiml
        assert "Hello, this is a test message" in twiml
    
    def test_generate_twiml_response_with_language(self, twilio_service_enabled):
        """Test TwiML response generation with language."""
        twiml = twilio_service_enabled.generate_twiml_response(
            "Bonjour",
            language="fr-FR"
        )
        
        assert "fr-FR" in twiml
    
    def test_generate_twiml_with_options_no_gather(self, twilio_service_enabled):
        """Test TwiML generation without digit gathering."""
        twiml = twilio_service_enabled.generate_twiml_with_options(
            "Press 1 to continue",
            gather_digits=False
        )
        
        assert "Say" in twiml
        assert "Press 1 to continue" in twiml
        assert "Gather" not in twiml
    
    def test_generate_twiml_with_options_gather_digits(self, twilio_service_enabled):
        """Test TwiML generation with digit gathering."""
        twiml = twilio_service_enabled.generate_twiml_with_options(
            "Press 1 to continue",
            gather_digits=True
        )
        
        assert "Gather" in twiml
        assert "Press 1 to continue" in twiml
        assert "numDigits" in twiml or "num_digits" in twiml.lower()


class TestServiceInitialization:
    """Test TwilioService initialization."""
    
    def test_init_with_credentials(self):
        """Test initialization with valid credentials."""
        with patch('app.services.twilio_service.settings') as mock_settings, \
             patch('app.services.twilio_service.Client') as mock_client_class:
            mock_settings.TWILIO_ENABLED = True
            mock_settings.TWILIO_ACCOUNT_SID = Mock(get_secret_value=lambda: "test_sid")
            mock_settings.TWILIO_AUTH_TOKEN = Mock(get_secret_value=lambda: "test_token")
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            service = TwilioService()
            
            assert service.client is not None
            mock_client_class.assert_called_once_with("test_sid", "test_token")
    
    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        with patch('app.services.twilio_service.settings') as mock_settings:
            mock_settings.TWILIO_ENABLED = False
            mock_settings.TWILIO_ACCOUNT_SID = None
            mock_settings.TWILIO_AUTH_TOKEN = None
            
            service = TwilioService()
            
            assert service.client is None
    
    def test_init_with_secretstr_credentials(self):
        """Test initialization with SecretStr credentials."""
        with patch('app.services.twilio_service.settings') as mock_settings, \
             patch('app.services.twilio_service.Client') as mock_client_class:
            mock_settings.TWILIO_ENABLED = True
            mock_sid = Mock()
            mock_sid.get_secret_value = lambda: "test_sid"
            mock_token = Mock()
            mock_token.get_secret_value = lambda: "test_token"
            mock_settings.TWILIO_ACCOUNT_SID = mock_sid
            mock_settings.TWILIO_AUTH_TOKEN = mock_token
            
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            service = TwilioService()
            
            assert service.client is not None
            mock_client_class.assert_called_once_with("test_sid", "test_token")
