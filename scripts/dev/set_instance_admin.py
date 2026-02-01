"""
Set is_instance_admin=True for an admin user (by email).
Required for admin-only actions like generating API keys (e.g. demo MCP launcher).
Works with or without ENCRYPTION_ENABLED (finds user by decrypted email when needed).

Usage:
    python scripts/dev/set_instance_admin.py demo@creditnexus.app
    # or
    uv run python scripts/dev/set_instance_admin.py demo@creditnexus.app
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.db import SessionLocal, init_db
from app.db.models import User
from app.core.config import settings


def find_user_by_email(db, email: str):
    """Find user by email; when encryption is enabled, compare decrypted emails."""
    if not getattr(settings, "ENCRYPTION_ENABLED", False):
        return db.query(User).filter(User.email == email).first()
    all_users = db.query(User).all()
    for u in all_users:
        try:
            if getattr(u, "email", None) == email:
                return u
        except Exception:
            continue
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev/set_instance_admin.py <email>")
        sys.exit(1)
    email = sys.argv[1].strip()
    if not email:
        print("Usage: python scripts/dev/set_instance_admin.py <email>")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        user = find_user_by_email(db, email)
        if not user:
            print(f"No user found with email: {email}")
            print("Create the user first, e.g.: python scripts/dev/create_demo_user.py")
            sys.exit(1)
        if user.role != "admin":
            print(f"User {email} has role {user.role}; setting is_instance_admin anyway.")
        user.is_instance_admin = True
        db.commit()
        print(f"Set is_instance_admin=True for {email}. You can now use admin-only endpoints (e.g. generate-api-key).")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
