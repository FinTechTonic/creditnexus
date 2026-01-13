"""Loan recovery service for detecting defaults and managing recovery actions."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import LoanDefault, RecoveryAction, BorrowerContact, User, Deal
# from app.db.models import PaymentSchedule # Temporarily removed due to model removal
from app.services.twilio_service import TwilioService
from app.core.config import settings

logger = logging.getLogger(__name__)


class LoanRecoveryService:
    """Service for managing loan defaults and recovery actions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.twilio_service = TwilioService()
    
    # Temporarily commented out due to PaymentSchedule model removal
    # def detect_payment_defaults(self, deal_id: Optional[int] = None) -> List[LoanDefault]:
    #     """Detect payment defaults based on overdue payments."""
    #     logger.info(f"Detecting payment defaults for deal_id: {deal_id}")
        
    #     # Query for overdue payments
    #     query = self.db.query(PaymentSchedule) \
    #         .filter(PaymentSchedule.status == "pending") \
    #         .filter(PaymentSchedule.scheduled_date < datetime.now())
        
    #     if deal_id:
    #         query = query.filter(PaymentSchedule.deal_id == deal_id)
        
    #     overdue_payments = query.all()
    #     defaults = []
        
    #     for payment in overdue_payments:
    #         # Check if default already exists for this payment
    #         existing_default = self.db.query(LoanDefault) \
    #             .filter(LoanDefault.loan_id == payment.loan_id) \
    #             .filter(LoanDefault.default_type == "payment_default") \
    #             .filter(LoanDefault.status == "open") \
    #             .first()
            
    #         if not existing_default:
    #             days_past_due = (datetime.now() - payment.scheduled_date).days
    #             severity = self._determine_severity(days_past_due)
                
    #             default = LoanDefault(
    #                 loan_id=payment.loan_id,
    #                 deal_id=payment.deal_id,
    #                 default_type="payment_default",
    #                 default_date=datetime.now(),
    #                 amount_overdue=payment.amount,
    #                 days_past_due=days_past_due,
    #                 severity=severity,
    #                 status="open",
    #                 default_reason=f"Payment of {payment.amount} {payment.currency} was due on {payment.scheduled_date}"
    #             )
                
    #             self.db.add(default)
    #             self.db.flush()  # Get the ID for the default
    #             defaults.append(default)
    #             logger.info(f"Created new default for loan {payment.loan_id}: {severity} severity")
        
    #     self.db.commit()
    #     logger.info(f"Detected {len(defaults)} new payment defaults")
    #     return defaults
    
    def _determine_severity(self, days_past_due: int) -> str:
        """Determine severity based on days past due."""
        if days_past_due <= 7:
            return "low"
        elif days_past_due <= 30:
            return "medium"
        elif days_past_due <= 60:
            return "high"
        else:
            return "critical"
    
    def get_active_defaults(self, deal_id: Optional[int] = None, status: Optional[str] = None) -> List[LoanDefault]:
        """Get active loan defaults with optional filters."""
        query = self.db.query(LoanDefault)
        
        if deal_id:
            query = query.filter(LoanDefault.deal_id == deal_id)
        
        if status:
            query = query.filter(LoanDefault.status == status)
        else:
            # Default to non-resolved statuses
            query = query.filter(LoanDefault.status != "resolved")
        
        return query.order_by(LoanDefault.severity.desc(), LoanDefault.days_past_due.desc()).all()

    def get_one_day_overdue_defaults(self) -> List[LoanDefault]:
        """Get loan defaults that are exactly 1 day overdue and open."""
        logger.info("Getting 1-day overdue loan defaults")
        return self.db.query(LoanDefault) \
            .filter(LoanDefault.status == "open") \
            .filter(LoanDefault.days_past_due == 1) \
            .all()
    
    def trigger_recovery_actions(self, default_id: int, action_types: Optional[List[str]] = None) -> List[RecoveryAction]:
        """Trigger recovery actions for a loan default based on severity."""
        logger.info(f"Triggering recovery actions for default {default_id}")
        
        # Get the loan default
        loan_default = self.db.query(LoanDefault).get(default_id)
        if not loan_default:
            raise ValueError(f"Loan default with ID {default_id} not found")
        
        # Get borrower contact for this deal
        borrower_contact = self.db.query(BorrowerContact) \
            .filter(BorrowerContact.deal_id == loan_default.deal_id) \
            .filter(BorrowerContact.is_primary == True) \
            .first()
        
        if not borrower_contact:
            logger.warning(f"No borrower contact found for deal {loan_default.deal_id}")
            return []
        
        # Determine action types based on severity if not specified
        if not action_types:
            action_types = self._get_actions_for_severity(loan_default.severity, loan_default.days_past_due)
        
        actions = []
        for action_type in action_types:
            # Generate message based on action type
            message = self._generate_recovery_message(loan_default, action_type)
            
            # Determine communication method
            communication_method = self._get_communication_method(action_type, borrower_contact.preferred_contact_method)
            
            # Create recovery action
            action = RecoveryAction(
                loan_default_id=loan_default.id,
                action_type=action_type,
                communication_method=communication_method,
                recipient_phone=borrower_contact.phone_number,
                recipient_email=borrower_contact.email,
                message_content=message,
                status="pending",
                scheduled_at=datetime.now()  # Schedule for immediate execution
            )
            
            self.db.add(action)
            actions.append(action)
            logger.info(f"Created recovery action {action_type} for default {default_id}")
        
        self.db.commit()
        return actions
    
    def _get_actions_for_severity(self, severity: str, days_past_due: int) -> List[str]:
        """Determine appropriate recovery actions based on severity and days past due."""
        actions = []
        
        # Base actions for all severities
        actions.append("sms_reminder")
        
        # Add additional actions based on severity
        if severity in ["medium", "high", "critical"] or days_past_due >= 4:
            actions.append("voice_call")
        
        if severity in ["high", "critical"] or days_past_due >= 8:
            actions.append("escalation")
        
        if severity == "critical" or days_past_due >= 31:
            actions.append("legal_notice")
        
        return actions
    
    def _get_communication_method(self, action_type: str, preferred_method: str) -> str:
        """Determine communication method for an action type."""
        # Use preferred method if it matches the action type
        if action_type == "sms_reminder" and preferred_method == "sms":
            return "sms"
        elif action_type == "voice_call" and preferred_method == "voice":
            return "voice"
        
        # Fallback to appropriate method for action type
        if action_type in ["sms_reminder", "escalation"]:
            return "sms"
        elif action_type in ["voice_call", "legal_notice"]:
            return "voice"
        else:
            return "sms"  # Default to SMS
    
    def _generate_recovery_message(self, loan_default: LoanDefault, action_type: str) -> str:
        """Generate appropriate message for recovery action."""
        
        borrower_name = "Valued Customer"
        contact_phone = "+1234567890" # Default contact phone number
        
        # Try to get primary borrower contact
        if loan_default.deal_id:
            borrower_contact = self.db.query(BorrowerContact) \
                .filter(BorrowerContact.deal_id == loan_default.deal_id) \
                .filter(BorrowerContact.is_primary == True) \
                .first()
            
            if borrower_contact:
                borrower_name = borrower_contact.contact_name or borrower_name
                contact_phone = borrower_contact.phone_number or contact_phone
            else:
                # Fallback to deal applicant's name if no primary contact
                deal = self.db.query(Deal).filter(Deal.id == loan_default.deal_id).first()
                if deal and deal.applicant:
                    borrower_name = deal.applicant.display_name or borrower_name
        
        loan_id = loan_default.loan_id
        amount = f"${loan_default.amount_overdue:.2f}" if loan_default.amount_overdue else "the overdue amount"
        due_date = (datetime.now() - timedelta(days=loan_default.days_past_due)).strftime("%Y-%m-%d")
        
        if action_type == "sms_reminder":
            return (f"Hi {borrower_name}, your loan {loan_id} payment of {amount} "
                   f"is {loan_default.days_past_due} days overdue (due {due_date}). "
                   f"Please pay immediately to avoid further action. Contact us at {contact_phone}.")
        
        elif action_type == "voice_call":
            return (f"Hello {borrower_name}. This is an important message about "
                   f"your loan {loan_id}. Your payment of {amount}, which was due on {due_date}, "
                   f"is now {loan_default.days_past_due} days overdue. "
                   f"This is a serious matter that requires your immediate attention. "
                   f"Please contact our recovery department at {contact_phone} to arrange payment immediately.")
        
        elif action_type == "escalation":
            return (f"URGENT: {borrower_name}, your loan {loan_id} is in serious default. "
                   f"Payment of {amount} was due {loan_default.days_past_due} days ago on {due_date}. "
                   f"Failure to contact us immediately at {contact_phone} may result in legal action.")
        
        elif action_type == "legal_notice":
            return (f"LEGAL NOTICE: This is a formal notification that loan {loan_id} "
                   f"is in default. Payment of {amount} was due on {due_date} and remains unpaid. "
                   f"You must contact our legal department at {contact_phone} within 7 days to avoid legal proceedings.")
        
        else:
            return f"Regarding your overdue loan {loan_id}, please contact us immediately."
    
    def execute_recovery_action(self, action_id: int) -> RecoveryAction:
        """Execute a pending recovery action (send SMS or make voice call)."""
        logger.info(f"Executing recovery action {action_id}")
        
        action = self.db.query(RecoveryAction).get(action_id)
        if not action:
            raise ValueError(f"Recovery action with ID {action_id} not found")
        
        if action.status != "pending":
            logger.warning(f"Action {action_id} is not pending (status: {action.status})")
            return action
        
        # Execute based on communication method
        if action.communication_method == "sms":
            result = self._execute_sms_action(action)
        elif action.communication_method == "voice":
            result = self._execute_voice_action(action)
        else:
            logger.warning(f"Unknown communication method: {action.communication_method}")
            action.status = "failed"
            action.error_message = "Unknown communication method"
        
        # Update action status
        if result.get("status") == "sent" or result.get("status") == "initiated":
            action.status = result.get("status")
            action.sent_at = datetime.now()
            if result.get("message_sid"):
                action.twilio_message_sid = result.get("message_sid")
            if result.get("call_sid"):
                action.twilio_call_sid = result.get("call_sid")
        else:
            action.status = "failed"
            action.error_message = result.get("message", "Execution failed")
        
        self.db.commit()
        logger.info(f"Action {action_id} executed with status: {action.status}")
        return action
    
    def _execute_sms_action(self, action: RecoveryAction) -> dict:
        """Execute SMS recovery action."""
        if not action.recipient_phone:
            return {"status": "error", "message": "No recipient phone number"}
        
        status_callback_url = f"{settings.BASE_URL}/api/twilio/webhook/sms"
        
        return self.twilio_service.send_sms(
            to_phone=action.recipient_phone,
            message=action.message_content,
            status_callback=status_callback_url
        )
    
    def _execute_voice_action(self, action: RecoveryAction) -> dict:
        """Execute voice call recovery action."""
        if not action.recipient_phone:
            return {"status": "error", "message": "No recipient phone number"}
        
        status_callback_url = f"{settings.BASE_URL}/api/twilio/webhook/voice"
        
        return self.twilio_service.make_voice_call(
            to_phone=action.recipient_phone,
            message=action.message_content,
            status_callback=status_callback_url
        )
    
    def process_scheduled_actions(self) -> dict:
        """Process all pending recovery actions that are scheduled for execution."""
        logger.info("Processing scheduled recovery actions")
        
        pending_actions = self.db.query(RecoveryAction) \
            .filter(RecoveryAction.status == "pending") \
            .filter(RecoveryAction.scheduled_at <= datetime.now()) \
            .all()
        
        processed_count = 0
        success_count = 0
        
        for action in pending_actions:
            try:
                self.execute_recovery_action(action.id)
                if action.status in ["sent", "initiated"]:
                    success_count += 1
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process action {action.id}: {e}")
                action.status = "failed"
                action.error_message = str(e)
                self.db.commit()
        
        logger.info(f"Processed {processed_count} actions, {success_count} successful")
        return {
            "total_processed": processed_count,
            "success_count": success_count,
            "failure_count": processed_count - success_count
        }

    def trigger_one_day_overdue_sms_reminders(self) -> dict:
        """Trigger SMS reminders for all loans that are exactly 1 day overdue."""
        logger.info("Triggering SMS reminders for 1-day overdue loans")
        one_day_overdue_defaults = self.get_one_day_overdue_defaults()
        
        triggered_actions_count = 0
        for loan_default in one_day_overdue_defaults:
            try:
                self.trigger_recovery_actions(loan_default.id, action_types=["sms_reminder"])
                triggered_actions_count += 1
            except Exception as e:
                logger.error(f"Failed to trigger SMS reminder for loan default {loan_default.id}: {e}")
        
        logger.info(f"Triggered SMS reminders for {triggered_actions_count} 1-day overdue loans.")
        return {
            "one_day_overdue_defaults_found": len(one_day_overdue_defaults),
            "sms_reminders_triggered": triggered_actions_count
        }