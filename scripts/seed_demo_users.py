"""
Script to seed demo users with different roles for CreditNexus application.

Usage:
    Set environment variables to control which users are seeded:
    - SEED_DEMO_USERS=true (enables seeding)
    - SEED_AUDITOR=true (seed auditor user)
    - SEED_BANKER=true (seed banker user)
    - SEED_LAW_OFFICER=true (seed law officer user)
    - SEED_ACCOUNTANT=true (seed accountant user)
    - SEED_APPLICANT=true (seed applicant user)
    
    Or run directly:
    python scripts/seed_demo_users.py
    uv run python scripts/seed_demo_users.py
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.db.models import User, UserRole
from app.auth.jwt_auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Demo user definitions
DEMO_USERS = [
    {
        "email": "auditor@creditnexus.app",
        "password": "Auditor123!",
        "display_name": "Demo Auditor",
        "role": UserRole.AUDITOR,
        "profile_data": {
            "phone": "+1-555-0101",
            "company": "CreditNexus Audit Department",
            "job_title": "Senior Auditor",
            "address": "123 Audit Street, Financial District, NY 10001"
        }
    },
    {
        "email": "banker@creditnexus.app",
        "password": "Banker123!",
        "display_name": "Demo Banker",
        "role": UserRole.BANKER,
        "profile_data": {
            "phone": "+1-555-0102",
            "company": "CreditNexus Bank",
            "job_title": "Credit Analyst",
            "address": "456 Banking Avenue, Wall Street, NY 10005"
        }
    },
    {
        "email": "lawofficer@creditnexus.app",
        "password": "LawOfficer123!",
        "display_name": "Demo Law Officer",
        "role": UserRole.LAW_OFFICER,
        "profile_data": {
            "phone": "+1-555-0103",
            "company": "CreditNexus Legal Department",
            "job_title": "Senior Legal Counsel",
            "address": "789 Legal Boulevard, Law District, NY 10010"
        }
    },
    {
        "email": "accountant@creditnexus.app",
        "password": "Accountant123!",
        "display_name": "Demo Accountant",
        "role": UserRole.ACCOUNTANT,
        "profile_data": {
            "phone": "+1-555-0104",
            "company": "CreditNexus Finance Department",
            "job_title": "Senior Accountant",
            "address": "321 Finance Way, Accounting Plaza, NY 10015"
        }
    },
    {
        "email": "applicant@creditnexus.app",
        "password": "Applicant123!",
        "display_name": "Demo Applicant",
        "role": UserRole.APPLICANT,
        "profile_data": {
            "phone": "+1-555-0105",
            "company": "ACME Corporation",
            "job_title": "Business Owner",
            "address": "654 Business Road, Commerce Center, NY 10020"
        }
    },
]


def seed_demo_users(db, force: bool = False) -> int:
    """
    Seed demo users into database.
    
    Args:
        db: Database session
        force: If True, update existing users. If False, skip existing users.
        
    Returns:
        Number of users created/updated
    """
    created_count = 0
    updated_count = 0
    
    # Check which users to seed based on environment flags
    seed_all = os.getenv("SEED_DEMO_USERS", "false").lower() == "true"
    seed_auditor = os.getenv("SEED_AUDITOR", "false").lower() == "true"
    seed_banker = os.getenv("SEED_BANKER", "false").lower() == "true"
    seed_law_officer = os.getenv("SEED_LAW_OFFICER", "false").lower() == "true"
    seed_accountant = os.getenv("SEED_ACCOUNTANT", "false").lower() == "true"
    seed_applicant = os.getenv("SEED_APPLICANT", "false").lower() == "true"
    
    # Role flag mapping
    role_flags = {
        UserRole.AUDITOR: seed_auditor,
        UserRole.BANKER: seed_banker,
        UserRole.LAW_OFFICER: seed_law_officer,
        UserRole.ACCOUNTANT: seed_accountant,
        UserRole.APPLICANT: seed_applicant,
    }
    
    for user_data in DEMO_USERS:
        role = user_data["role"]
        
        # Check if this user should be seeded
        if not seed_all and not role_flags.get(role, False):
            logger.debug(f"Skipping {user_data['email']} (not enabled via environment flags)")
            continue
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        
        if existing_user:
            if force:
                # Update existing user
                existing_user.display_name = user_data["display_name"]
                existing_user.role = role.value
                existing_user.profile_data = user_data.get("profile_data")
                existing_user.is_active = True
                existing_user.is_email_verified = True
                db.commit()
                updated_count += 1
                logger.info(f"Updated user: {user_data['email']}")
            else:
                logger.debug(f"User {user_data['email']} already exists, skipping")
            continue
        
        try:
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                display_name=user_data["display_name"],
                role=role.value,
                profile_data=user_data.get("profile_data"),
                is_active=True,
                is_email_verified=True,  # Mark as verified for convenience
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_count += 1
            logger.info(f"Created user: {user_data['email']} ({role.value})")
        except Exception as e:
            logger.error(f"Failed to seed user {user_data['email']}: {e}")
            db.rollback()
            continue
    
    logger.info(f"User seeding complete: {created_count} created, {updated_count} updated")
    return created_count + updated_count


def main():
    """Main function to seed demo users."""
    # Check if seeding is enabled
    seed_enabled = os.getenv("SEED_DEMO_USERS", "false").lower() == "true"
    force = os.getenv("SEED_DEMO_USERS_FORCE", "false").lower() == "true"
    
    # Also check individual role flags
    has_role_flags = any([
        os.getenv("SEED_AUDITOR", "false").lower() == "true",
        os.getenv("SEED_BANKER", "false").lower() == "true",
        os.getenv("SEED_LAW_OFFICER", "false").lower() == "true",
        os.getenv("SEED_ACCOUNTANT", "false").lower() == "true",
        os.getenv("SEED_APPLICANT", "false").lower() == "true",
    ])
    
    if not seed_enabled and not has_role_flags:
        logger.info("User seeding is disabled. Set SEED_DEMO_USERS=true or individual role flags to enable.")
        return
    
    logger.info("Starting demo user seeding...")
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        user_count = seed_demo_users(db, force=force)
        
        if user_count > 0:
            logger.info(f"Demo user seeding complete: {user_count} user(s) processed")
            logger.info("=" * 60)
            logger.info("Demo user credentials:")
            for user_data in DEMO_USERS:
                logger.info(f"  {user_data['email']} / {user_data['password']} ({user_data['role'].value})")
            logger.info("=" * 60)
        else:
            logger.info("All demo users already exist in database")
    except Exception as e:
        logger.error(f"Error during user seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
