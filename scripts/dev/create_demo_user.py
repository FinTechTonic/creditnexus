"""
Script to create a demo user for testing the CreditNexus application.

Usage:
    python scripts/create_demo_user.py
    # or
    uv run python scripts/create_demo_user.py
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.db.models import User, UserRole
from app.auth.jwt_auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demo user credentials
DEMO_EMAIL = "demo@creditnexus.app"  # Using .app TLD for better email validation compatibility
DEMO_PASSWORD = "DemoPassword123!"  # Meets all requirements: 12+ chars, uppercase, lowercase, number, special char
DEMO_DISPLAY_NAME = "Demo User"


def create_demo_user():
    """Create a demo user if it doesn't exist."""
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check if demo user already exists
        existing_user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing_user:
            logger.info(f"Demo user already exists: {DEMO_EMAIL}")
            logger.info("You can log in with:")
            logger.info(f"  Email: {DEMO_EMAIL}")
            logger.info(f"  Password: {DEMO_PASSWORD}")
            return existing_user
        
        # Create demo user
        demo_user = User(
            email=DEMO_EMAIL,
            password_hash=get_password_hash(DEMO_PASSWORD),
            display_name=DEMO_DISPLAY_NAME,
            role=UserRole.ADMIN.value,  # Give admin role for full access
            is_active=True,
            is_email_verified=True,  # Mark as verified for convenience
        )
        
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        
        logger.info("=" * 60)
        logger.info("Demo user created successfully!")
        logger.info("=" * 60)
        logger.info("Login credentials:")
        logger.info(f"  Email: {DEMO_EMAIL}")
        logger.info(f"  Password: {DEMO_PASSWORD}")
        logger.info("=" * 60)
        logger.info("You can now log in to the application using these credentials.")
        
        return demo_user
        
    except Exception as e:
        logger.error(f"Error creating demo user: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_demo_user()

