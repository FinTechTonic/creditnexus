"""
Script to update the demo user's email to a more standard format.

This fixes email validation issues with .local TLD.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.db.models import User

def update_demo_user_email():
    """Update demo user email from .local to .app"""
    db = SessionLocal()
    
    try:
        # Find user with old email
        old_user = db.query(User).filter(User.email == "demo@creditnexus.local").first()
        if old_user:
            old_user.email = "demo@creditnexus.app"
            db.commit()
            print("Updated demo user email from demo@creditnexus.local to demo@creditnexus.app")
        else:
            print("No user with email demo@creditnexus.local found")
        
        # Verify new email exists
        new_user = db.query(User).filter(User.email == "demo@creditnexus.app").first()
        if new_user:
            print(f"Demo user exists with email: {new_user.email}")
            print("Login credentials:")
            print("  Email: demo@creditnexus.app")
            print("  Password: DemoPassword123!")
        else:
            print("No demo user found. Run scripts/create_demo_user.py to create one.")
            
    except Exception as e:
        print(f"Error updating demo user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    update_demo_user_email()




