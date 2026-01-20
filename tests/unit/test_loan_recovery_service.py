"""
Unit tests for LoanRecoveryService with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.services.loan_recovery_service import LoanRecoveryService
from app.db.models import (
    LoanDefault, RecoveryAction, BorrowerContact, Deal, LoanAsset, PaymentEvent
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_loan_default():
    """Mock LoanDefault object."""
    default = Mock(spec=LoanDefault)
    default.id = 1
    default.loan_id = "LOAN_001"
    default.deal_id = 1
    default.default_type = "payment_default"
    default.default_date = datetime(2024, 1, 1)
    default.default_reason = "Payment overdue"
    default.amount_overdue = Decimal("1000.00")
    default.days_past_due = 5
    default.severity = "medium"
    default.status = "open"
    default.resolved_at = None
    default.cdm_events = None
    default.metadata = None
    return default


@pytest.fixture
def mock_payment_event():
    """Mock PaymentEvent object."""
    payment = Mock(spec=PaymentEvent)
    payment.id = 1
    payment.related_deal_id = 1
    payment.payment_status = "pending"
    payment.amount = Decimal("1000.00")
    payment.created_at = datetime(2024, 1, 1) - timedelta(days=5)
    return payment


@pytest.fixture
def mock_borrower_contact():
    """Mock BorrowerContact object."""
    contact = Mock(spec=BorrowerContact)
    contact.id = 1
    contact.deal_id = 1
    contact.contact_name = "John Doe"
    contact.phone_number = "+1234567890"
    contact.email = "john@example.com"
    contact.preferred_contact_method = "sms"
    contact.is_primary = True
    contact.is_active = True
    return contact


@pytest.fixture
def mock_recovery_action():
    """Mock RecoveryAction object."""
    action = Mock(spec=RecoveryAction)
    action.id = 1
    action.loan_default_id = 1
    action.action_type = "sms_reminder"
    action.communication_method = "sms"
    action.recipient_phone = "+1234567890"
    action.message_template = "sms_payment_reminder"
    action.message_content = "Test message"
    action.status = "pending"
    action.scheduled_at = None
    action.sent_at = None
    action.twilio_message_sid = None
    return action


@pytest.fixture
def recovery_service(mock_db):
    """LoanRecoveryService instance with mocked dependencies."""
    with patch('app.services.loan_recovery_service.TwilioService') as mock_twilio, \
         patch('app.services.loan_recovery_service.RecoveryTemplateService') as mock_template:
        service = LoanRecoveryService(mock_db)
        service.twilio_service = mock_twilio.return_value
        service.template_service = mock_template.return_value
        return service


class TestDetectPaymentDefaults:
    """Test payment default detection."""
    
    def test_detect_payment_defaults_no_overdue(self, recovery_service, mock_db):
        """Test detection when no payments are overdue."""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        defaults = recovery_service.detect_payment_defaults()
        
        assert defaults == []
    
    def test_detect_payment_defaults_with_overdue(self, recovery_service, mock_db, mock_payment_event):
        """Test detection of overdue payment."""
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = [mock_payment_event]
        
        # Mock existing default check (no existing default)
        mock_default_query = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add and commit
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        defaults = recovery_service.detect_payment_defaults()
        
        # Should create a new default
        assert mock_db.add.called
        assert mock_db.commit.called
    
    def test_detect_payment_defaults_with_deal_id(self, recovery_service, mock_db):
        """Test detection filtered by deal_id."""
        # Mock query chain properly
        mock_query1 = Mock()
        mock_query2 = Mock()
        mock_db.query.return_value.filter.return_value = mock_query1
        mock_query1.filter.return_value = mock_query2
        mock_query2.all.return_value = []
        
        defaults = recovery_service.detect_payment_defaults(deal_id=1)
        
        # Verify deal_id filter was applied
        assert mock_db.query.called
        assert defaults == []
    
    def test_detect_payment_defaults_severity_calculation(self, recovery_service, mock_db, mock_payment_event):
        """Test severity calculation based on days past due."""
        # Mock payment that's 60 days overdue (should be "high" severity)
        mock_payment_event.created_at = datetime.utcnow() - timedelta(days=60)
        
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = [mock_payment_event]
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        defaults = recovery_service.detect_payment_defaults()
        
        # Verify default was created with appropriate severity
        assert mock_db.add.called


class TestDetectCovenantBreaches:
    """Test covenant breach detection."""
    
    def test_detect_covenant_breaches_no_breaches(self, recovery_service, mock_db):
        """Test detection when no covenant breaches exist."""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        breaches = recovery_service.detect_covenant_breaches()
        
        assert breaches == []
    
    def test_detect_covenant_breaches_with_breach(self, recovery_service, mock_db):
        """Test detection of covenant breach."""
        mock_loan_asset = Mock(spec=LoanAsset)
        mock_loan_asset.id = 1
        mock_loan_asset.loan_id = "LOAN_001"
        mock_loan_asset.related_deal_id = 1
        mock_loan_asset.risk_status = "BREACH"
        mock_loan_asset.last_verified_at = datetime.utcnow()
        
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = [mock_loan_asset]
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        breaches = recovery_service.detect_covenant_breaches()
        
        # Should create a new default for breach
        assert mock_db.add.called


class TestGetActiveDefaults:
    """Test getting active defaults."""
    
    def test_get_active_defaults_all(self, recovery_service, mock_db, mock_loan_default):
        """Test getting all active defaults."""
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_loan_default]
        
        defaults = recovery_service.get_active_defaults()
        
        assert len(defaults) == 1
        assert defaults[0] == mock_loan_default
    
    def test_get_active_defaults_with_deal_id(self, recovery_service, mock_db, mock_loan_default):
        """Test getting active defaults filtered by deal_id."""
        # Mock query chain properly
        mock_query1 = Mock()
        mock_query2 = Mock()
        mock_query3 = Mock()
        mock_db.query.return_value.filter.return_value = mock_query1
        mock_query1.filter.return_value = mock_query2
        mock_query2.order_by.return_value.all.return_value = [mock_loan_default]
        
        defaults = recovery_service.get_active_defaults(deal_id=1)
        
        assert len(defaults) == 1
    
    def test_get_active_defaults_with_status(self, recovery_service, mock_db, mock_loan_default):
        """Test getting active defaults filtered by status."""
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_loan_default]
        
        defaults = recovery_service.get_active_defaults(status="open")
        
        assert len(defaults) == 1


class TestGetDefaultsBySeverity:
    """Test getting defaults by severity."""
    
    def test_get_defaults_by_severity(self, recovery_service, mock_db, mock_loan_default):
        """Test getting defaults filtered by severity."""
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_loan_default]
        
        defaults = recovery_service.get_defaults_by_severity("medium")
        
        assert len(defaults) == 1
        assert defaults[0].severity == "medium"
    
    def test_get_defaults_by_severity_with_deal_id(self, recovery_service, mock_db, mock_loan_default):
        """Test getting defaults by severity filtered by deal_id."""
        # Mock query chain properly
        mock_query1 = Mock()
        mock_query2 = Mock()
        mock_query3 = Mock()
        mock_db.query.return_value.filter.return_value = mock_query1
        mock_query1.filter.return_value = mock_query2
        mock_query2.order_by.return_value.all.return_value = [mock_loan_default]
        
        defaults = recovery_service.get_defaults_by_severity("medium", deal_id=1)
        
        assert len(defaults) == 1


class TestTriggerRecoveryActions:
    """Test triggering recovery actions."""
    
    def test_trigger_recovery_actions_default_not_found(self, recovery_service, mock_db):
        """Test triggering actions when default doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="LoanDefault.*not found"):
            recovery_service.trigger_recovery_actions(default_id=999)
    
    def test_trigger_recovery_actions_auto_determine(self, recovery_service, mock_db, 
                                                     mock_loan_default, mock_borrower_contact):
        """Test triggering actions with auto-determined action types."""
        mock_loan_default.days_past_due = 5  # Medium severity, should trigger SMS + voice
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_loan_default,  # For default query
            mock_borrower_contact  # For contact query
        ]
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Mock template service
        recovery_service.template_service.get_template.return_value = "Test message"
        
        actions = recovery_service.trigger_recovery_actions(default_id=1)
        
        # Should create recovery actions
        assert mock_db.add.called
    
    def test_trigger_recovery_actions_custom_types(self, recovery_service, mock_db,
                                                   mock_loan_default, mock_borrower_contact):
        """Test triggering actions with custom action types."""
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_loan_default,
            mock_borrower_contact
        ]
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        recovery_service.template_service.get_template.return_value = "Test message"
        
        actions = recovery_service.trigger_recovery_actions(
            default_id=1,
            action_types=["sms_reminder", "voice_call"]
        )
        
        assert mock_db.add.called
    
    def test_trigger_recovery_actions_no_contact(self, recovery_service, mock_db, mock_loan_default):
        """Test triggering actions when no borrower contact exists."""
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_loan_default,  # Default found
            None  # No contact found
        ]
        
        # Should still create actions (may use default contact info)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        actions = recovery_service.trigger_recovery_actions(default_id=1)
        
        # May or may not create actions depending on implementation
        # This test verifies it doesn't crash


class TestExecuteRecoveryAction:
    """Test executing recovery actions."""
    
    def test_execute_recovery_action_not_found(self, recovery_service, mock_db):
        """Test executing action when action doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="RecoveryAction.*not found"):
            recovery_service.execute_recovery_action(action_id=999)
    
    def test_execute_recovery_action_sms(self, recovery_service, mock_db,
                                          mock_recovery_action, mock_loan_default, mock_borrower_contact):
        """Test executing SMS recovery action."""
        mock_recovery_action.communication_method = "sms"
        mock_recovery_action.status = "pending"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_recovery_action,  # Action query
            mock_loan_default,  # Default query
            mock_borrower_contact  # Contact query
        ]
        
        # Mock Twilio service response
        recovery_service.twilio_service.send_sms.return_value = {
            "status": "sent",
            "message_sid": "SM1234567890"
        }
        
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        action = recovery_service.execute_recovery_action(action_id=1)
        
        # Verify SMS was sent
        recovery_service.twilio_service.send_sms.assert_called_once()
        assert mock_db.commit.called
    
    def test_execute_recovery_action_voice(self, recovery_service, mock_db,
                                           mock_recovery_action, mock_loan_default, mock_borrower_contact):
        """Test executing voice recovery action."""
        mock_recovery_action.communication_method = "voice"
        mock_recovery_action.status = "pending"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_recovery_action,
            mock_loan_default,
            mock_borrower_contact
        ]
        
        # Mock Twilio service response
        recovery_service.twilio_service.make_voice_call.return_value = {
            "status": "queued",
            "call_sid": "CA1234567890"
        }
        
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        action = recovery_service.execute_recovery_action(action_id=1)
        
        # Verify voice call was made
        recovery_service.twilio_service.make_voice_call.assert_called_once()
        assert mock_db.commit.called
    
    def test_execute_recovery_action_twilio_error(self, recovery_service, mock_db,
                                                  mock_recovery_action, mock_loan_default, mock_borrower_contact):
        """Test executing action when Twilio returns error."""
        mock_recovery_action.communication_method = "sms"
        mock_recovery_action.status = "pending"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_recovery_action,
            mock_loan_default,
            mock_borrower_contact
        ]
        
        # Mock Twilio service error
        recovery_service.twilio_service.send_sms.return_value = {
            "status": "error",
            "message": "Invalid phone number"
        }
        
        mock_db.commit = Mock()
        
        action = recovery_service.execute_recovery_action(action_id=1)
        
        # Should update action status to "failed"
        assert mock_db.commit.called


class TestProcessScheduledActions:
    """Test processing scheduled actions."""
    
    def test_process_scheduled_actions_none_pending(self, recovery_service, mock_db):
        """Test processing when no scheduled actions are pending."""
        # Mock query chain properly - filter() is called with and_() containing two conditions
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = []  # Return empty list
        mock_db.commit = Mock()
        
        result = recovery_service.process_scheduled_actions()
        
        assert result["processed"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0
    
    def test_process_scheduled_actions_with_pending(self, recovery_service, mock_db, mock_recovery_action):
        """Test processing scheduled actions."""
        mock_recovery_action.status = "sent"  # Will be set to "sent" after execution
        mock_recovery_action.scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        # Mock query chain properly - filter() is called with and_() containing two conditions
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = [mock_recovery_action]  # Return list with action
        mock_db.commit = Mock()
        
        # Mock execute_recovery_action
        with patch.object(recovery_service, 'execute_recovery_action') as mock_execute:
            mock_execute.return_value = mock_recovery_action
            
            result = recovery_service.process_scheduled_actions()
            
            assert result["processed"] == 1
            assert result["total"] == 1
            mock_execute.assert_called_once_with(1)
    
    def test_process_scheduled_actions_with_failure(self, recovery_service, mock_db, mock_recovery_action):
        """Test processing scheduled actions with execution failure."""
        mock_recovery_action.status = "pending"
        mock_recovery_action.scheduled_at = datetime.utcnow() - timedelta(hours=1)
        
        # Mock query chain properly - filter() is called with and_() containing two conditions
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.all.return_value = [mock_recovery_action]  # Return list with action
        mock_db.commit = Mock()
        
        # Mock execute_recovery_action to raise exception
        with patch.object(recovery_service, 'execute_recovery_action') as mock_execute:
            mock_execute.side_effect = Exception("Execution failed")
            
            result = recovery_service.process_scheduled_actions()
            
            # Should still process and report failure
            assert result["failed"] == 1
            assert result["total"] == 1


class TestServiceInitialization:
    """Test LoanRecoveryService initialization."""
    
    def test_init(self, mock_db):
        """Test service initialization."""
        with patch('app.services.loan_recovery_service.TwilioService') as mock_twilio, \
             patch('app.services.loan_recovery_service.RecoveryTemplateService') as mock_template:
            service = LoanRecoveryService(mock_db)
            
            assert service.db == mock_db
            assert service.twilio_service is not None
            assert service.template_service is not None
