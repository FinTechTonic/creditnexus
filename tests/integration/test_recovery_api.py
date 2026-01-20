"""
Integration tests for recovery API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient

from app.db.models import User, UserRole, LoanDefault, RecoveryAction, BorrowerContact
from app.auth.jwt_auth import create_access_token
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.role = UserRole.ADMIN.value
    user.display_name = "Test User"
    user.is_active = True
    user.is_email_verified = True
    return user


@pytest.fixture
def auth_token(mock_user):
    """Create JWT token for user."""
    return create_access_token(mock_user.id, mock_user.email)


@pytest.fixture
def mock_loan_default():
    """Create mock LoanDefault."""
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
    default.to_dict = Mock(return_value={
        "id": 1,
        "loan_id": "LOAN_001",
        "deal_id": 1,
        "default_type": "payment_default",
        "default_date": "2026-01-15T00:00:00",
        "default_reason": "Payment overdue",
        "amount_overdue": "1000.00",
        "days_past_due": 5,
        "severity": "medium",
        "status": "open",
        "resolved_at": None,
        "cdm_events": None,
        "metadata": None,
        "created_at": "2026-01-15T00:00:00",
        "updated_at": "2026-01-15T00:00:00"
    })
    return default


@pytest.fixture
def mock_recovery_action():
    """Create mock RecoveryAction."""
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
    action.to_dict = Mock(return_value={
        "id": 1,
        "loan_default_id": 1,
        "action_type": "sms_reminder",
        "communication_method": "sms",
        "recipient_phone": "+1234567890",
        "message_template": "sms_payment_reminder",
        "message_content": "Test message",
        "status": "pending",
        "scheduled_at": None,
        "sent_at": None,
        "twilio_message_sid": None,
        "created_at": "2026-01-15T00:00:00",
        "updated_at": "2026-01-15T00:00:00"
    })
    return action


@pytest.fixture
def mock_borrower_contact():
    """Create mock BorrowerContact."""
    contact = Mock(spec=BorrowerContact)
    contact.id = 1
    contact.deal_id = 1
    contact.user_id = None
    contact.contact_name = "John Doe"
    contact.phone_number = "+1234567890"
    contact.email = "john@example.com"
    contact.preferred_contact_method = "sms"
    contact.is_primary = True
    contact.is_active = True
    contact.to_dict = Mock(return_value={
        "id": 1,
        "deal_id": 1,
        "user_id": None,
        "contact_name": "John Doe",
        "phone_number": "+1234567890",
        "email": "john@example.com",
        "preferred_contact_method": "sms",
        "is_primary": True,
        "is_active": True,
        "created_at": "2026-01-15T00:00:00",
        "updated_at": "2026-01-15T00:00:00"
    })
    return contact


class TestGetDefaults:
    """Test GET /api/recovery/defaults endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_get_defaults_success(self, mock_service_class, mock_get_user, 
                                   client, mock_user, mock_loan_default):
        """Test getting defaults successfully."""
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.get_active_defaults.return_value = [mock_loan_default]
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.all.return_value = []
            
            response = client.get(
                "/api/recovery/defaults",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "defaults" in data
            assert len(data["defaults"]) == 1
    
    @patch('app.api.recovery_routes.get_current_user')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_get_defaults_with_filters(self, mock_service_class, mock_get_user,
                                       client, mock_user, mock_loan_default):
        """Test getting defaults with filters."""
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.get_active_defaults.return_value = [mock_loan_default]
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.all.return_value = []
            
            response = client.get(
                "/api/recovery/defaults?deal_id=1&status=open&severity=medium",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
    
    def test_get_defaults_requires_authentication(self, client):
        """Test that getting defaults requires authentication."""
        response = client.get("/api/recovery/defaults")
        assert response.status_code == 401


class TestDetectDefaults:
    """Test POST /api/recovery/defaults/detect endpoint."""
    
    @patch('app.api.recovery_routes.require_auth')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_detect_defaults_success(self, mock_service_class, mock_require_auth,
                                     client, mock_loan_default):
        """Test detecting defaults successfully."""
        mock_require_auth.return_value = Mock(id=1, email="test@example.com")
        
        mock_service = Mock()
        mock_service.detect_payment_defaults.return_value = [mock_loan_default]
        mock_service.detect_covenant_breaches.return_value = []
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db, \
             patch('app.api.recovery_routes.log_audit_action'):
            response = client.post(
                "/api/recovery/defaults/detect",
                json={"deal_id": 1},
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_detect_defaults_requires_authentication(self, client):
        """Test that detecting defaults requires authentication."""
        response = client.post("/api/recovery/defaults/detect", json={})
        assert response.status_code == 401


class TestGetDefaultById:
    """Test GET /api/recovery/defaults/{default_id} endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_default_by_id_success(self, mock_get_user, client, mock_user, mock_loan_default):
        """Test getting default by ID successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = mock_loan_default
            mock_db.return_value.query.return_value.filter.return_value.all.return_value = []
            
            response = client.get(
                "/api/recovery/defaults/1",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_default_by_id_not_found(self, mock_get_user, client, mock_user):
        """Test getting default by ID when not found."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/recovery/defaults/999",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 404


class TestTriggerRecoveryActions:
    """Test POST /api/recovery/defaults/{default_id}/actions endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_trigger_actions_success(self, mock_service_class, mock_get_user,
                                     client, mock_user, mock_recovery_action):
        """Test triggering recovery actions successfully."""
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.trigger_recovery_actions.return_value = [mock_recovery_action]
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db, \
             patch('app.api.recovery_routes.log_audit_action'):
            response = client.post(
                "/api/recovery/defaults/1/actions",
                json={"action_types": ["sms_reminder"]},
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1


class TestGetActions:
    """Test GET /api/recovery/actions endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_actions_success(self, mock_get_user, client, mock_user, mock_recovery_action):
        """Test getting actions successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_query = Mock()
            mock_db.return_value.query.return_value.filter.return_value = mock_query
            mock_query.order_by.return_value.all.return_value = [mock_recovery_action]
            
            response = client.get(
                "/api/recovery/actions",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "actions" in data


class TestGetActionById:
    """Test GET /api/recovery/actions/{action_id} endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_action_by_id_success(self, mock_get_user, client, mock_user, mock_recovery_action):
        """Test getting action by ID successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = mock_recovery_action
            
            response = client.get(
                "/api/recovery/actions/1",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_action_by_id_not_found(self, mock_get_user, client, mock_user):
        """Test getting action by ID when not found."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/recovery/actions/999",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 404


class TestExecuteAction:
    """Test POST /api/recovery/actions/{action_id}/execute endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_execute_action_success(self, mock_service_class, mock_get_user,
                                   client, mock_user, mock_recovery_action):
        """Test executing action successfully."""
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.execute_recovery_action.return_value = mock_recovery_action
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db, \
             patch('app.api.recovery_routes.log_audit_action'):
            response = client.post(
                "/api/recovery/actions/1/execute",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1


class TestProcessScheduledActions:
    """Test POST /api/recovery/actions/scheduled/process endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    @patch('app.api.recovery_routes.LoanRecoveryService')
    def test_process_scheduled_actions_success(self, mock_service_class, mock_get_user,
                                               client, mock_user):
        """Test processing scheduled actions successfully."""
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.process_scheduled_actions.return_value = {
            "processed_count": 2,
            "success_count": 2,
            "failed_count": 0
        }
        mock_service_class.return_value = mock_service
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            response = client.post(
                "/api/recovery/actions/scheduled/process",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["processed_count"] == 2


class TestGetContacts:
    """Test GET /api/recovery/contacts endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_get_contacts_success(self, mock_get_user, client, mock_user, mock_borrower_contact):
        """Test getting contacts successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_query = Mock()
            mock_db.return_value.query.return_value.filter.return_value = mock_query
            mock_query.all.return_value = [mock_borrower_contact]
            
            response = client.get(
                "/api/recovery/contacts?deal_id=1",
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "contacts" in data


class TestCreateContact:
    """Test POST /api/recovery/contacts endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_create_contact_success(self, mock_get_user, client, mock_user, mock_borrower_contact):
        """Test creating contact successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db, \
             patch('app.api.recovery_routes.log_audit_action'):
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value.add = Mock()
            mock_db.return_value.commit = Mock()
            mock_db.return_value.refresh = Mock()
            
            # Create new contact instance
            new_contact = Mock(spec=BorrowerContact)
            new_contact.to_dict = Mock(return_value=mock_borrower_contact.to_dict.return_value)
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = new_contact
            
            response = client.post(
                "/api/recovery/contacts",
                json={
                    "deal_id": 1,
                    "contact_name": "John Doe",
                    "phone_number": "+1234567890",
                    "email": "john@example.com",
                    "preferred_contact_method": "sms"
                },
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            # May return 200 or 201 depending on implementation
            assert response.status_code in [200, 201]


class TestUpdateContact:
    """Test PUT /api/recovery/contacts/{contact_id} endpoint."""
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_update_contact_success(self, mock_get_user, client, mock_user, mock_borrower_contact):
        """Test updating contact successfully."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db, \
             patch('app.api.recovery_routes.log_audit_action'):
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = mock_borrower_contact
            mock_db.return_value.commit = Mock()
            mock_db.return_value.refresh = Mock()
            
            response = client.put(
                "/api/recovery/contacts/1",
                json={
                    "contact_name": "Jane Doe",
                    "phone_number": "+1987654321"
                },
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 200
    
    @patch('app.api.recovery_routes.get_current_user')
    def test_update_contact_not_found(self, mock_get_user, client, mock_user):
        """Test updating contact when not found."""
        mock_get_user.return_value = mock_user
        
        with patch('app.api.recovery_routes.get_db') as mock_db:
            mock_db.return_value.query.return_value.filter.return_value.first.return_value = None
            
            response = client.put(
                "/api/recovery/contacts/999",
                json={"contact_name": "Jane Doe"},
                headers={"Authorization": f"Bearer {create_access_token(1, 'test@example.com')}"}
            )
            
            assert response.status_code == 404
