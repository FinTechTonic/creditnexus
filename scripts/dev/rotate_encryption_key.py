"""
Key rotation script for encryption at rest.

This script re-encrypts all encrypted data with a new encryption key.
This is necessary when:
- The encryption key has been compromised
- Key rotation is required for compliance
- Migrating to a new key management system

Usage:
    python scripts/rotate_encryption_key.py --old-key OLD_KEY --new-key NEW_KEY [--dry-run]

WARNING: This operation is irreversible without the old key!
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import User, Document, DocumentVersion, StagedExtraction, AuditLog, PolicyDecision, LoanAsset
from app.services.encryption_service import EncryptionService
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rotate_user_data(db: Session, old_service: EncryptionService, new_service: EncryptionService, dry_run: bool = False):
    """Rotate encryption key for User model."""
    logger.info("Rotating User data...")
    users = db.query(User).all()
    count = 0
    
    for user in users:
        try:
            # Decrypt with old key, re-encrypt with new key
            # Access fields to trigger decryption
            email = user.email
            display_name = user.display_name
            wallet_address = user.wallet_address
            profile_data = user.profile_data
            
            # Force re-encryption by updating
            if not dry_run:
                db.add(user)
                db.flush()
                count += 1
            else:
                logger.info(f"Would rotate User {user.id}: {user.email}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to rotate User {user.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Rotated {count} User records")


def rotate_document_data(db: Session, old_service: EncryptionService, new_service: EncryptionService, dry_run: bool = False):
    """Rotate encryption key for Document model."""
    logger.info("Rotating Document data...")
    documents = db.query(Document).all()
    count = 0
    
    for doc in documents:
        try:
            borrower_name = doc.borrower_name
            borrower_lei = doc.borrower_lei
            source_cdm_data = doc.source_cdm_data
            
            if not dry_run:
                db.add(doc)
                db.flush()
                count += 1
            else:
                logger.info(f"Would rotate Document {doc.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to rotate Document {doc.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Rotated {count} Document records")


def rotate_all_models(db: Session, old_service: EncryptionService, new_service: EncryptionService, dry_run: bool = False):
    """Rotate encryption key for all models."""
    rotate_user_data(db, old_service, new_service, dry_run)
    rotate_document_data(db, old_service, new_service, dry_run)
    
    # Rotate other models similarly
    logger.info("Rotating DocumentVersion data...")
    versions = db.query(DocumentVersion).all()
    for version in versions:
        try:
            _ = version.extracted_data
            _ = version.original_text
            _ = version.source_filename
            if not dry_run:
                db.add(version)
                db.flush()
        except Exception as e:
            logger.error(f"Failed to rotate DocumentVersion {version.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info("Rotating StagedExtraction data...")
    extractions = db.query(StagedExtraction).all()
    for extraction in extractions:
        try:
            _ = extraction.agreement_data
            _ = extraction.original_text
            _ = extraction.source_filename
            if not dry_run:
                db.add(extraction)
                db.flush()
        except Exception as e:
            logger.error(f"Failed to rotate StagedExtraction {extraction.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info("Rotating AuditLog data...")
    logs = db.query(AuditLog).all()
    for log in logs:
        try:
            _ = log.action_metadata
            _ = log.ip_address
            if not dry_run:
                db.add(log)
                db.flush()
        except Exception as e:
            logger.error(f"Failed to rotate AuditLog {log.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info("Rotating PolicyDecision data...")
    decisions = db.query(PolicyDecision).all()
    for decision in decisions:
        try:
            _ = decision.trace
            _ = decision.cdm_events
            if not dry_run:
                db.add(decision)
                db.flush()
        except Exception as e:
            logger.error(f"Failed to rotate PolicyDecision {decision.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info("Rotating LoanAsset data...")
    assets = db.query(LoanAsset).all()
    for asset in assets:
        try:
            _ = asset.original_text
            _ = asset.collateral_address
            if not dry_run:
                db.add(asset)
                db.flush()
        except Exception as e:
            logger.error(f"Failed to rotate LoanAsset {asset.id}: {e}")
    
    if not dry_run:
        db.commit()


def main():
    """Main key rotation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Rotate encryption key for all encrypted data")
    parser.add_argument("--old-key", required=True, help="Old encryption key (Fernet key)")
    parser.add_argument("--new-key", required=True, help="New encryption key (Fernet key)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be rotated without making changes")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No changes will be made")
    
    logger.warning("KEY ROTATION: This will re-encrypt all data with the new key!")
    logger.warning("Ensure you have a backup and the old key is correct!")
    response = input("Continue? Type 'YES' to proceed: ")
    if response != "YES":
        logger.info("Key rotation cancelled")
        return
    
    # Create encryption services with old and new keys
    old_service = EncryptionService(encryption_key=args.old_key)
    new_service = EncryptionService(encryption_key=args.new_key)
    
    # Temporarily set new key in settings for SQLAlchemy types
    original_key = settings.ENCRYPTION_KEY
    try:
        # Update settings to use new key
        settings.ENCRYPTION_KEY = args.new_key
        
        db = next(get_db())
        
        try:
            logger.info("Starting key rotation...")
            rotate_all_models(db, old_service, new_service, dry_run=args.dry_run)
            logger.info("Key rotation completed successfully!")
            
            if not args.dry_run:
                logger.warning("IMPORTANT: Update ENCRYPTION_KEY in your environment/config to the new key!")
                
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
            settings.ENCRYPTION_KEY = original_key
            
    except Exception as e:
        logger.error(f"Key rotation failed: {e}")
        raise


if __name__ == "__main__":
    main()
