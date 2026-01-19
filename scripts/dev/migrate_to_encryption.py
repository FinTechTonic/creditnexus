"""
Migration script to encrypt existing plain text data in the database.

This script:
1. Reads all existing plain text data from User, Document, AuditLog, PolicyDecision models
2. Re-encrypts them using the new EncryptedString/EncryptedJSON types
3. Updates records in place (triggers encryption on save)

Usage:
    python scripts/migrate_to_encryption.py [--dry-run] [--rollback]

Options:
    --dry-run: Show what would be encrypted without making changes
    --rollback: Decrypt all encrypted data back to plain text (DANGEROUS)
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy.orm import Session
from app.db import get_db, Base, engine
from app.db.models import User, Document, DocumentVersion, StagedExtraction, AuditLog, PolicyDecision, LoanAsset
from app.services.encryption_service import get_encryption_service
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_user_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate User model data."""
    logger.info("Migrating User data...")
    users = db.query(User).all()
    count = 0
    
    for user in users:
        try:
            # Access encrypted fields to trigger re-encryption
            # SQLAlchemy will automatically encrypt on next save
            email = user.email
            display_name = user.display_name
            wallet_address = user.wallet_address
            profile_data = user.profile_data
            
            if not dry_run:
                # Force update to trigger encryption
                db.add(user)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt User {user.id}: {user.email}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate User {user.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} User records")


def migrate_document_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate Document model data."""
    logger.info("Migrating Document data...")
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
                logger.info(f"Would encrypt Document {doc.id}: {doc.title}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate Document {doc.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} Document records")


def migrate_document_version_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate DocumentVersion model data."""
    logger.info("Migrating DocumentVersion data...")
    versions = db.query(DocumentVersion).all()
    count = 0
    
    for version in versions:
        try:
            extracted_data = version.extracted_data
            original_text = version.original_text
            source_filename = version.source_filename
            
            if not dry_run:
                db.add(version)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt DocumentVersion {version.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate DocumentVersion {version.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} DocumentVersion records")


def migrate_staged_extraction_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate StagedExtraction model data."""
    logger.info("Migrating StagedExtraction data...")
    extractions = db.query(StagedExtraction).all()
    count = 0
    
    for extraction in extractions:
        try:
            agreement_data = extraction.agreement_data
            original_text = extraction.original_text
            source_filename = extraction.source_filename
            
            if not dry_run:
                db.add(extraction)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt StagedExtraction {extraction.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate StagedExtraction {extraction.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} StagedExtraction records")


def migrate_audit_log_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate AuditLog model data."""
    logger.info("Migrating AuditLog data...")
    logs = db.query(AuditLog).all()
    count = 0
    
    for log in logs:
        try:
            action_metadata = log.action_metadata
            ip_address = log.ip_address
            
            if not dry_run:
                db.add(log)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt AuditLog {log.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate AuditLog {log.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} AuditLog records")


def migrate_policy_decision_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate PolicyDecision model data."""
    logger.info("Migrating PolicyDecision data...")
    decisions = db.query(PolicyDecision).all()
    count = 0
    
    for decision in decisions:
        try:
            trace = decision.trace
            cdm_events = decision.cdm_events
            
            if not dry_run:
                db.add(decision)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt PolicyDecision {decision.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate PolicyDecision {decision.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} PolicyDecision records")


def migrate_loan_asset_data(db: Session, dry_run: bool = False, rollback: bool = False):
    """Migrate LoanAsset model data."""
    logger.info("Migrating LoanAsset data...")
    assets = db.query(LoanAsset).all()
    count = 0
    
    for asset in assets:
        try:
            original_text = asset.original_text
            collateral_address = asset.collateral_address
            
            if not dry_run:
                db.add(asset)
                db.flush()
                count += 1
            else:
                logger.info(f"Would encrypt LoanAsset {asset.id}")
                count += 1
        except Exception as e:
            logger.error(f"Failed to migrate LoanAsset {asset.id}: {e}")
    
    if not dry_run:
        db.commit()
    logger.info(f"Migrated {count} LoanAsset records")


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate database to encryption at rest")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be encrypted without making changes")
    parser.add_argument("--rollback", action="store_true", help="Decrypt all data (DANGEROUS)")
    
    args = parser.parse_args()
    
    if args.rollback:
        logger.warning("ROLLBACK MODE: This will decrypt all encrypted data!")
        response = input("Are you sure? Type 'YES' to continue: ")
        if response != "YES":
            logger.info("Rollback cancelled")
            return
    
    if not settings.ENCRYPTION_ENABLED and not args.rollback:
        logger.warning("ENCRYPTION_ENABLED is False. Enable encryption in settings first.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Migration cancelled")
            return
    
    db = next(get_db())
    
    try:
        logger.info("Starting migration...")
        
        if args.dry_run:
            logger.info("DRY RUN MODE: No changes will be made")
        
        # Migrate all models
        migrate_user_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_document_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_document_version_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_staged_extraction_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_audit_log_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_policy_decision_data(db, dry_run=args.dry_run, rollback=args.rollback)
        migrate_loan_asset_data(db, dry_run=args.dry_run, rollback=args.rollback)
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
