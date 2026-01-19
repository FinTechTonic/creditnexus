"""Script to increase audit_logs.ip_address column length from 50 to 255.

This fixes the issue where encrypted IP addresses exceed the 50 character limit.
Run this script directly: python scripts/fix_audit_logs_ip_address_length.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
from sqlalchemy import text

def fix_ip_address_column():
    """Alter the ip_address column to increase its length."""
    if engine is None:
        print("ERROR: Database engine is not initialized")
        return False
    
    try:
        with engine.connect() as conn:
            # Check current column type
            result = conn.execute(text("""
                SELECT data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'audit_logs' AND column_name = 'ip_address'
            """))
            row = result.fetchone()
            
            if row is None:
                print("ERROR: audit_logs table or ip_address column not found")
                return False
            
            current_type = row[0]
            current_length = row[1]
            
            print(f"Current ip_address column: {current_type}({current_length})")
            
            if current_length and current_length < 255:
                print(f"Altering ip_address column from {current_type}({current_length}) to VARCHAR(255)...")
                conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN ip_address TYPE VARCHAR(255)"))
                conn.commit()
                print("SUCCESS: ip_address column length increased to 255")
                return True
            elif current_length is None:
                # Column might be TEXT or BYTEA, check if we need to change it
                print(f"Column type is {current_type} (no length limit)")
                # If it's already TEXT or unlimited, we're good
                if 'text' in current_type.lower() or 'bytea' in current_type.lower():
                    print("Column already supports unlimited length - no change needed")
                    return True
                else:
                    print(f"Converting {current_type} to VARCHAR(255)...")
                    conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN ip_address TYPE VARCHAR(255)"))
                    conn.commit()
                    print("SUCCESS: ip_address column converted to VARCHAR(255)")
                    return True
            else:
                print(f"Column is already {current_type}({current_length}) - no change needed")
                return True
                
    except Exception as e:
        print(f"ERROR: Failed to alter column: {e}")
        return False

if __name__ == "__main__":
    success = fix_ip_address_column()
    sys.exit(0 if success else 1)
