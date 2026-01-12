import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from typing import Optional

from sqlmodel import create_engine, Session, select

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.db.models import Deal, User, PaymentSchedule, LoanDefault, DealStatus, LoanDefaultSeverity, LoanDefaultStatus, DealType
from app.models.loan_asset import LoanAsset, RiskStatus
from app.auth.jwt_auth import get_password_hash # Import for dummy user password hashing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

def simulate_overdue_loan(
    db_session: Session,
    deal_id: Optional[str] = None,
    loan_id: Optional[str] = None,
    days_overdue: int = 30
):
    """
    Simulates an overdue loan by updating a LoanAsset and creating a LoanDefault entry.
    
    Args:
        db_session: The database session.
        deal_id: The external deal ID of the loan to make overdue.
        loan_id: The external loan ID of the loan asset.
        days_overdue: The number of days the loan should be overdue.
    """
    logger.info(f"Attempting to simulate overdue loan for deal_id={deal_id}, loan_id={loan_id} for {days_overdue} days.")

    loan_asset: Optional[LoanAsset] = None
    if loan_id:
        loan_asset = db_session.exec(select(LoanAsset).where(LoanAsset.loan_id == loan_id)).first()
        if not loan_asset:
            logger.warning(f"LoanAsset with loan_id '{loan_id}' not found.")
            return

    # If loan_asset is not found by loan_id, try to find/create via deal_id
    deal: Optional[Deal] = None
    if deal_id:
        deal = db_session.exec(select(Deal).where(Deal.deal_id == deal_id)).first()
        if not deal:
            logger.warning(f"Deal with deal_id '{deal_id}' not found.")
            return
        
        if not loan_asset: # Only try to find/create if loan_asset wasn't found by its own loan_id
            loan_asset = db_session.exec(select(LoanAsset).where(LoanAsset.loan_id == deal.deal_id)).first()
            if not loan_asset:
                logger.info(f"No existing LoanAsset for deal '{deal_id}'. Creating a new one.")
                loan_asset = LoanAsset(
                    loan_id=deal.deal_id, # Use deal_id as loan_id for simplicity
                    risk_status=RiskStatus.COMPLIANT, # Initial status
                    base_interest_rate=5.0,
                    current_interest_rate=5.0,
                    penalty_bps=50.0,
                    asset_metadata={}
                )
                db_session.add(loan_asset)
                db_session.commit()
                db_session.refresh(loan_asset)
                logger.info(f"Created new LoanAsset with ID: {loan_asset.id} for loan_id: {loan_asset.loan_id}")

    if not loan_asset:
        logger.error("Could not find or create a LoanAsset to simulate overdue status. Exiting.")
        return

    # 1. Update LoanAsset to reflect a breach/overdue status
    loan_asset.risk_status = RiskStatus.BREACH
    loan_asset.last_verified_at = datetime.utcnow() - timedelta(days=days_overdue + 5) # Set verification date in the past
    loan_asset.current_interest_rate = loan_asset.base_interest_rate + (loan_asset.penalty_bps / 100)
    if loan_asset.asset_metadata is None:
        loan_asset.asset_metadata = {}
    loan_asset.asset_metadata["penalty_payment_required"] = True
    loan_asset.asset_metadata["penalty_payment_triggered_at"] = datetime.utcnow().isoformat()
    loan_asset.asset_metadata["breach_simulation_days_overdue"] = days_overdue
    
    db_session.add(loan_asset)
    db_session.commit()
    db_session.refresh(loan_asset)
    logger.info(f"Updated LoanAsset {loan_asset.id} (loan_id: {loan_asset.loan_id}) to BREACH status.")

    # 2. Create or update a PaymentSchedule entry to be overdue
    payment_schedule = db_session.exec(
        select(PaymentSchedule).where(PaymentSchedule.loan_asset_id == loan_asset.id)
    ).first()

    if not payment_schedule:
        logger.info(f"No existing PaymentSchedule for LoanAsset {loan_asset.id}. Creating a new overdue entry.")
        payment_schedule = PaymentSchedule(
            loan_asset_id=loan_asset.id,
            amount=1000.00,  # Dummy overdue amount
            currency="USD",
            payment_type="principal",
            scheduled_date=datetime.utcnow() - timedelta(days=days_overdue),
            status="pending", # Still pending, but overdue
        )
        db_session.add(payment_schedule)
        db_session.commit()
        db_session.refresh(payment_schedule)
        logger.info(f"Created overdue PaymentSchedule entry for LoanAsset {loan_asset.id}.")
    else:
        logger.info(f"Updating existing PaymentSchedule {payment_schedule.id} to be overdue.")
        payment_schedule.scheduled_date = datetime.utcnow() - timedelta(days=days_overdue)
        payment_schedule.status = "pending"
        db_session.add(payment_schedule)
        db_session.commit()
        db_session.refresh(payment_schedule)
        logger.info(f"Updated PaymentSchedule {payment_schedule.id} to overdue.")


    # 3. Create a LoanDefault entry
    existing_loan_default = db_session.exec(
        select(LoanDefault).where(
            LoanDefault.loan_id == loan_asset.loan_id,
            LoanDefault.status == LoanDefaultStatus.OPEN.value
        )
    ).first()

    if existing_loan_default:
        logger.info(f"Existing open LoanDefault entry found for loan_id {loan_asset.loan_id}. Updating it.")
        loan_default = existing_loan_default
    else:
        logger.info(f"Creating a new LoanDefault entry for loan_id {loan_asset.loan_id}.")
        loan_default = LoanDefault(loan_id=loan_asset.loan_id)
        db_session.add(loan_default)

    loan_default.deal_id = (deal.id if deal else None) # Link to Deal if found
    loan_default.default_type = "payment_default"
    loan_default.default_date = datetime.utcnow() - timedelta(days=days_overdue)
    loan_default.default_reason = f"Simulated overdue for {days_overdue} days."
    loan_default.amount_overdue = payment_schedule.amount if payment_schedule else 1000.00
    loan_default.days_past_due = days_overdue
    loan_default.severity = LoanDefaultSeverity.HIGH.value
    loan_default.status = LoanDefaultStatus.OPEN.value
    loan_default.extra_data = {"simulation_triggered_at": datetime.utcnow().isoformat()}

    db_session.add(loan_default)
    db_session.commit()
    db_session.refresh(loan_default)
    logger.info(f"Created/Updated LoanDefault entry {loan_default.id} for loan_id: {loan_asset.loan_id}.")
    logger.info(f"Simulation complete for loan_id: {loan_asset.loan_id}. Loan is now overdue.")


def main():
    logger.info("Starting overdue loan simulation script...")
    init_db() # Ensure tables are created if not already
    
    with Session(engine) as session:
        # Example: Find an existing deal to simulate on
        # You might want to get this dynamically or from an argument
        # For demonstration, let's try to find an existing 'loan_application' deal
        deal_to_simulate = session.exec(
            select(Deal).where(
                Deal.deal_type == DealType.LOAN_APPLICATION,
                Deal.status == DealStatus.ACTIVE
            )
        ).first()

        if not deal_to_simulate:
            logger.warning("No active 'loan_application' deal found. Creating a new demo deal.")
            # Create a dummy user for the deal if none exists
            dummy_user = session.exec(select(User).limit(1)).first()
            if not dummy_user:
                logger.info("No user found in the database. Creating a dummy user.")
                # from app.auth.jwt_auth import get_password_hash # Already imported
                dummy_user = User(
                    email="demo_applicant@creditnexus.app",
                    password_hash=get_password_hash("DemoApplicant123!"),
                    display_name="Demo Applicant",
                    role="applicant",
                    is_active=True,
                    is_email_verified=True
                )
                session.add(dummy_user)
                session.commit()
                session.refresh(dummy_user)
                logger.info(f"Created dummy user: {dummy_user.email}")

            deal_to_simulate = Deal(
                deal_id=f"DEMO_LOAN_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                applicant_id=dummy_user.id,
                status=DealStatus.ACTIVE.value,
                deal_type=DealType.LOAN_APPLICATION.value,
                is_demo=True,
                deal_data={"loan_amount": 100000.00, "currency": "USD"}
            )
            session.add(deal_to_simulate)
            session.commit()
            session.refresh(deal_to_simulate)
            logger.info(f"Created new demo deal: {deal_to_simulate.deal_id}")
        
        simulate_overdue_loan(session, deal_id=deal_to_simulate.deal_id, days_overdue=45)

if __name__ == "__main__":
    main()
