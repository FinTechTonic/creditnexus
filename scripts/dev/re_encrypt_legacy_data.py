"""
Re-encrypt legacy data to eliminate encryption token warnings.

This script:
1. Scans all encrypted columns in the database
2. Attempts to decrypt with current key
3. Re-encrypts with current key if successful
4. Logs failures for manual review

The warnings "Invalid encryption token" occur when:
- Legacy data exists with a different encryption key
- Plain text data was created before encryption was enabled
- Encryption keys have been rotated

Usage:
    python scripts/dev/re_encrypt_legacy_data.py [--dry-run] [--batch-size=100]

Options:
    --dry-run: Preview what would be re-encrypted without making changes
    --batch-size: Number of records to process per batch (default: 100)
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import (
    User, Document, DocumentVersion, StagedExtraction, 
    AuditLog, PolicyDecision, LoanAsset
)
from app.services.encryption_service import get_encryption_service
from app.core.config import settings
from app.db.encrypted_types import EncryptedString, EncryptedText, EncryptedJSON

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def re_encrypt_user_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt User model encrypted fields."""
    logger.info("Re-encrypting User data...")
    users = db.query(User).all()
    count = 0
    errors = 0
    
    for user in users:
        try:
            # Access encrypted fields - this will trigger re-encryption if decryption succeeds
            # The EncryptedString/EncryptedJSON types handle re-encryption automatically
            _ = user.email
            _ = user.display_name
            if user.wallet_address:
                _ = user.wallet_address
            if user.profile_data:
                _ = user.profile_data
            
            if not dry_run:
                db.add(user)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} users...")
            else:
                logger.debug(f"Would re-encrypt User {user.id}: {user.email}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt User {user.id}: {e}")
            if "Invalid encryption token" in str(e) or "InvalidToken" in str(type(e).__name__):
                logger.warning(f"  User {user.id} has legacy/invalid encryption - may need manual review")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} User records ({errors} errors)")
    return count, errors


def re_encrypt_document_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt Document model encrypted fields."""
    logger.info("Re-encrypting Document data...")
    documents = db.query(Document).all()
    count = 0
    errors = 0
    
    for doc in documents:
        try:
            # Access encrypted fields
            if doc.cdm_data:
                _ = doc.cdm_data
            if doc.extracted_data:
                _ = doc.extracted_data
            
            if not dry_run:
                db.add(doc)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} documents...")
            else:
                logger.debug(f"Would re-encrypt Document {doc.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt Document {doc.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} Document records ({errors} errors)")
    return count, errors


def re_encrypt_document_version_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt DocumentVersion model encrypted fields."""
    logger.info("Re-encrypting DocumentVersion data...")
    versions = db.query(DocumentVersion).all()
    count = 0
    errors = 0
    
    for version in versions:
        try:
            # Access encrypted fields
            if version.extracted_data:
                _ = version.extracted_data
            if version.original_text:
                _ = version.original_text
            if version.source_filename:
                _ = version.source_filename
            
            if not dry_run:
                db.add(version)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} document versions...")
            else:
                logger.debug(f"Would re-encrypt DocumentVersion {version.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt DocumentVersion {version.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} DocumentVersion records ({errors} errors)")
    return count, errors


def re_encrypt_staged_extraction_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt StagedExtraction model encrypted fields."""
    logger.info("Re-encrypting StagedExtraction data...")
    extractions = db.query(StagedExtraction).all()
    count = 0
    errors = 0
    
    for extraction in extractions:
        try:
            # Access encrypted fields
            if extraction.agreement_data:
                _ = extraction.agreement_data
            if extraction.original_text:
                _ = extraction.original_text
            if extraction.source_filename:
                _ = extraction.source_filename
            
            if not dry_run:
                db.add(extraction)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} staged extractions...")
            else:
                logger.debug(f"Would re-encrypt StagedExtraction {extraction.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt StagedExtraction {extraction.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} StagedExtraction records ({errors} errors)")
    return count, errors


def re_encrypt_audit_log_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt AuditLog model encrypted fields."""
    logger.info("Re-encrypting AuditLog data...")
    logs = db.query(AuditLog).all()
    count = 0
    errors = 0
    
    for log in logs:
        try:
            # Access encrypted fields
            if log.action_metadata:
                _ = log.action_metadata
            if log.ip_address:
                _ = log.ip_address
            
            if not dry_run:
                db.add(log)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} audit logs...")
            else:
                logger.debug(f"Would re-encrypt AuditLog {log.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt AuditLog {log.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} AuditLog records ({errors} errors)")
    return count, errors


def re_encrypt_policy_decision_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt PolicyDecision model encrypted fields."""
    logger.info("Re-encrypting PolicyDecision data...")
    decisions = db.query(PolicyDecision).all()
    count = 0
    errors = 0
    
    for decision in decisions:
        try:
            # Access encrypted fields
            if decision.trace:
                _ = decision.trace
            if decision.matched_rules:
                _ = decision.matched_rules
            if decision.cdm_events:
                _ = decision.cdm_events
            if decision.additional_metadata:
                _ = decision.additional_metadata
            
            if not dry_run:
                db.add(decision)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} policy decisions...")
            else:
                logger.debug(f"Would re-encrypt PolicyDecision {decision.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt PolicyDecision {decision.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} PolicyDecision records ({errors} errors)")
    return count, errors


def re_encrypt_loan_asset_data(db: Session, dry_run: bool = False, batch_size: int = 100):
    """Re-encrypt LoanAsset model encrypted fields."""
    logger.info("Re-encrypting LoanAsset data...")
    assets = db.query(LoanAsset).all()
    count = 0
    errors = 0
    
    for asset in assets:
        try:
            # Access encrypted fields
            if asset.asset_metadata:
                _ = asset.asset_metadata
            if asset.spt_data:
                _ = asset.spt_data
            if asset.cdm_data:
                _ = asset.cdm_data
            
            if not dry_run:
                db.add(asset)
                if count % batch_size == 0:
                    db.commit()
                    logger.info(f"Processed {count} loan assets...")
            else:
                logger.debug(f"Would re-encrypt LoanAsset {asset.id}")
            
            count += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to re-encrypt LoanAsset {asset.id}: {e}")
    
    if not dry_run:
        db.commit()
    
    logger.info(f"Re-encrypted {count} LoanAsset records ({errors} errors)")
    return count, errors


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Re-encrypt legacy data to eliminate encryption warnings')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of records per batch')
    args = parser.parse_args()
    
    if not settings.ENCRYPTION_ENABLED:
        logger.error("Encryption is not enabled. Cannot re-encrypt data.")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        total_count = 0
        total_errors = 0
        
        # Re-encrypt all models with encrypted fields
        count, errors = re_encrypt_user_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_document_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_document_version_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_staged_extraction_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_audit_log_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_policy_decision_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        count, errors = re_encrypt_loan_asset_data(db, args.dry_run, args.batch_size)
        total_count += count
        total_errors += errors
        
        logger.info("=" * 60)
        logger.info(f"Migration complete: {total_count} records processed, {total_errors} errors")
        if total_errors > 0:
            logger.warning(f"{total_errors} records could not be re-encrypted - may need manual review")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
