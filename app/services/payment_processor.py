"""
Background Task Processor for Scheduled Payments.

Processes scheduled payments via x402 payment service.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging

from sqlalchemy.orm import Session
from app.db.models import PaymentSchedule
from app.models.loan_asset import LoanAsset
from app.models.loan_asset import LoanAsset as LoanAssetModel
from app.services.x402_payment_service import X402PaymentService
from app.models.cdm import Party, Money, Currency
from app.models.cdm_payment import PaymentEvent, PaymentType, PaymentMethod
from app.db.models import PaymentEvent as PaymentEventModel
from app.api.routes import get_credit_agreement_for_loan, get_party_by_id

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Background task processor for scheduled payments."""
    
    def __init__(self, payment_service: X402PaymentService, db: Session):
        """
        Initialize payment processor.
        
        Args:
            payment_service: x402 payment service instance
            db: Database session
        """
        self.payment_service = payment_service
        self.db = db
    
    async def process_scheduled_payments(self) -> Dict[str, Any]:
        """
        Process all due scheduled payments.
        
        Queries payment_schedules for payments that are due and processes them.
        
        Returns:
            Processing results
        """
        try:
            # Query for due payments (scheduled_date <= now, status = pending)
            due_payments = self.db.query(PaymentSchedule).filter(
                PaymentSchedule.scheduled_date <= datetime.utcnow(),
                PaymentSchedule.status == "pending"
            ).all()
            
            if not due_payments:
                return {
                    "status": "success",
                    "processed": 0,
                    "failed": 0,
                    "message": "No due payments found"
                }
            
            processed = 0
            failed = 0
            results = []
            
            for schedule in due_payments:
                try:
                    result = await self.process_payment(schedule)
                    if result.get("status") == "success":
                        processed += 1
                        # Update schedule status
                        schedule.status = "processed"
                        schedule.processed_at = datetime.utcnow()
                    else:
                        failed += 1
                        schedule.status = "failed"
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing payment schedule {schedule.id}: {e}")
                    failed += 1
                    schedule.status = "failed"
                    results.append({
                        "schedule_id": schedule.id,
                        "status": "error",
                        "error": str(e)
                    })
            
            self.db.commit()
            
            return {
                "status": "success",
                "processed": processed,
                "failed": failed,
                "total": len(due_payments),
                "results": results
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing scheduled payments: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_payment(self, schedule: PaymentSchedule) -> Dict[str, Any]:
        """
        Process a single scheduled payment.
        
        Args:
            schedule: PaymentSchedule record
            
        Returns:
            Processing result
        """
        try:
            # Step 1: Get loan asset
            loan_asset = self.db.query(LoanAsset).filter(
                LoanAsset.id == schedule.loan_asset_id
            ).first()
            
            if not loan_asset:
                return {
                    "status": "error",
                    "message": f"Loan asset {schedule.loan_asset_id} not found"
                }
            
            # Step 2: Get credit agreement
            credit_agreement = get_credit_agreement_for_loan(loan_asset.loan_id, self.db)
            
            if not credit_agreement:
                return {
                    "status": "error",
                    "message": f"Credit agreement not found for loan {loan_asset.loan_id}"
                }
            
            # Step 3: Extract parties
            borrower = None
            lender = None
            
            if credit_agreement.parties:
                for party in credit_agreement.parties:
                    role_lower = party.role.lower()
                    if "borrower" in role_lower:
                        borrower = party
                    elif "lender" in role_lower or "creditor" in role_lower:
                        lender = party
            
            if not borrower or not lender:
                return {
                    "status": "error",
                    "message": "Missing borrower or lender in credit agreement"
                }
            
            # Step 4: Determine payer and receiver based on payment type
            # For interest payments: borrower pays lender
            # For principal repayments: borrower pays lender
            payer = borrower
            receiver = lender
            
            # Step 5: Process payment via x402
            currency = Currency(schedule.currency)
            amount = Decimal(str(schedule.amount))
            
            payment_type_map = {
                "interest": PaymentType.INTEREST_PAYMENT,
                "principal": PaymentType.PRINCIPAL_REPAYMENT,
                "penalty": PaymentType.PENALTY_PAYMENT
            }
            
            payment_type = payment_type_map.get(schedule.payment_type, PaymentType.INTEREST_PAYMENT)
            
            # Note: For scheduled payments, we would need payment_payload from borrower's wallet
            # In a production system, this would be stored or requested automatically
            # For now, we'll return a payment request (402)
            payment_result = await self.payment_service.process_payment_flow(
                amount=amount,
                currency=currency,
                payer=payer,
                receiver=receiver,
                payment_type=payment_type.value,
                payment_payload=None,  # Would be provided by borrower's wallet
                cdm_reference={
                    "loan_id": loan_asset.loan_id,
                    "schedule_id": schedule.id,
                    "payment_type": schedule.payment_type
                }
            )
            
            # If payment not provided, return payment request
            if payment_result.get("status") != "settled":
                return {
                    "status": "payment_required",
                    "schedule_id": schedule.id,
                    "payment_request": payment_result.get("payment_request"),
                    "message": "Payment payload required from borrower's wallet"
                }
            
            # Step 6: Create CDM PaymentEvent
            payment_event = PaymentEvent.from_cdm_party(
                payer=payer,
                receiver=receiver,
                amount=Money(amount=amount, currency=currency),
                payment_type=payment_type,
                payment_method=PaymentMethod.X402
            )
            
            # Update with loan and schedule references
            payment_event = payment_event.model_copy(update={
                "relatedLoanId": loan_asset.loan_id,
                "x402PaymentDetails": {
                    "settlement": payment_result.get("settlement")
                },
                "transactionHash": payment_result.get("transaction_hash")
            })
            
            # Transition through state machine
            payment_event = payment_event.transition_to_verified()
            payment_event = payment_event.transition_to_settled(payment_result.get("transaction_hash", ""))
            
            # Step 7: Save payment event to database
            payment_event_db = PaymentEventModel(
                payment_id=payment_event.paymentIdentifier.assignedIdentifier[0]["identifier"]["value"],
                payment_method=payment_event.paymentMethod.value,
                payment_type=payment_event.paymentType.value,
                payer_id=payment_event.payerPartyReference.globalReference,
                payer_name=payer.name,
                receiver_id=payment_event.receiverPartyReference.globalReference,
                receiver_name=receiver.name,
                amount=payment_event.paymentAmount.amount,
                currency=payment_event.paymentAmount.currency.value,
                status=payment_event.paymentStatus.value,
                x402_settlement=payment_result.get("settlement"),
                transaction_hash=payment_result.get("transaction_hash"),
                related_loan_id=loan_asset.loan_id,
                cdm_event=payment_event.to_cdm_json(),
                settled_at=datetime.utcnow()
            )
            self.db.add(payment_event_db)
            self.db.commit()
            
            logger.info(
                f"Processed scheduled payment: schedule_id={schedule.id}, "
                f"payment_id={payment_event_db.payment_id}"
            )
            
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "payment_id": payment_event_db.payment_id,
                "transaction_hash": payment_result.get("transaction_hash")
            }
            
        except Exception as e:
            logger.error(f"Error processing payment schedule {schedule.id}: {e}", exc_info=True)
            return {
                "status": "error",
                "schedule_id": schedule.id,
                "error": str(e)
            }
















