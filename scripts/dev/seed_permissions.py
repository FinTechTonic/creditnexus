"""
Script to seed permission definitions and role-permission mappings into database.

Loads permission definitions from permission_config.py and creates Permission and RolePermission records.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.db.models import Permission, RolePermission
from app.core.permission_config import (
    get_permission_definitions,
    get_role_permission_mappings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_permissions(db, force: bool = False) -> int:
    """
    Seed permission definitions into database.
    
    Args:
        db: Database session
        force: If True, update existing permissions. If False, skip existing.
        
    Returns:
        Number of permissions created/updated
    """
    created_count = 0
    updated_count = 0
    
    permission_definitions = get_permission_definitions()
    
    for perm_name, perm_description, perm_category in permission_definitions:
        # Check if permission already exists
        existing = db.query(Permission).filter(Permission.name == perm_name).first()
        
        if existing:
            if force:
                # Update existing permission
                existing.description = perm_description
                existing.category = perm_category
                db.commit()
                updated_count += 1
                logger.info(f"Updated permission: {perm_name}")
            else:
                logger.debug(f"Permission {perm_name} already exists, skipping")
            continue
        
        try:
            # Create new permission
            permission = Permission(
                name=perm_name,
                description=perm_description,
                category=perm_category,
            )
            db.add(permission)
            db.commit()
            db.refresh(permission)
            created_count += 1
            logger.info(f"Created permission: {perm_name} ({perm_category})")
        except Exception as e:
            logger.error(f"Failed to seed permission {perm_name}: {e}")
            db.rollback()
            continue
    
    logger.info(f"Permission seeding complete: {created_count} created, {updated_count} updated")
    return created_count + updated_count


def seed_role_permissions(db, force: bool = False) -> int:
    """
    Seed role-permission mappings into database.
    
    Args:
        db: Database session
        force: If True, update existing mappings. If False, skip existing.
        
    Returns:
        Number of role-permission mappings created/updated
    """
    created_count = 0
    updated_count = 0
    
    role_permission_mappings = get_role_permission_mappings()
    
    for role, permissions in role_permission_mappings.items():
        for perm_name in permissions:
            # Get permission ID
            permission = db.query(Permission).filter(Permission.name == perm_name).first()
            if not permission:
                logger.warning(f"Permission {perm_name} not found, skipping role mapping for {role}")
                continue
            
            # Check if mapping already exists
            existing = db.query(RolePermission).filter(
                RolePermission.role == role,
                RolePermission.permission_id == permission.id
            ).first()
            
            if existing:
                if force:
                    # Mapping already exists, no update needed
                    updated_count += 1
                    logger.debug(f"Role-permission mapping {role} -> {perm_name} already exists")
                else:
                    logger.debug(f"Role-permission mapping {role} -> {perm_name} already exists, skipping")
                continue
            
            try:
                # Create new role-permission mapping
                role_perm = RolePermission(
                    role=role,
                    permission_id=permission.id,
                )
                db.add(role_perm)
                db.commit()
                created_count += 1
                logger.debug(f"Created role-permission mapping: {role} -> {perm_name}")
            except Exception as e:
                logger.error(f"Failed to seed role-permission mapping {role} -> {perm_name}: {e}")
                db.rollback()
                continue
    
    logger.info(f"Role-permission seeding complete: {created_count} created, {updated_count} updated")
    return created_count + updated_count


def main():
    """Main function to seed permissions and role-permission mappings."""
    # Check if seeding is enabled
    seed_enabled = os.getenv("SEED_PERMISSIONS", "false").lower() == "true"
    force = os.getenv("SEED_PERMISSIONS_FORCE", "false").lower() == "true"
    
    if not seed_enabled:
        logger.info("Permission seeding is disabled. Set SEED_PERMISSIONS=true to enable.")
        return
    
    logger.info("Starting permission seeding...")
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        # Seed permission definitions
        perm_count = seed_permissions(db, force=force)
        
        # Seed role-permission mappings
        role_perm_count = seed_role_permissions(db, force=force)
        
        logger.info(f"Permission seeding complete: {perm_count} permissions, {role_perm_count} role-permission mappings")
    except Exception as e:
        logger.error(f"Error during permission seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
