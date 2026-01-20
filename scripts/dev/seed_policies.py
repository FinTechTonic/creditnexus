"""
Seed initial policies from YAML files into the database.

This script loads policy rules from YAML files and creates Policy records
that are visible in the Policy Editor and usable by the application.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import Policy, PolicyStatus, User
from app.core.config import Settings
from app.core.policy_config import PolicyConfigLoader
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


def get_policy_metadata(file_path: Path, yaml_content: dict) -> dict:
    """Extract policy metadata from file path and YAML content."""
    filename = file_path.stem
    
    # Determine category from directory
    category = 'regulatory'  # default
    file_path_str = str(file_path)
    if 'credit_risk' in file_path_str:
        category = 'credit_risk'
    elif 'compliance' in file_path_str or 'sanctions' in file_path_str:
        category = 'compliance'
    elif 'esg' in file_path_str:
        category = 'esg'
    elif 'regulatory' in file_path_str:
        category = 'regulatory'
    
    # Extract rule names from YAML
    rules = yaml_content if isinstance(yaml_content, list) else []
    rule_names = [rule.get('name', '') for rule in rules if isinstance(rule, dict) and 'name' in rule]
    
    return {
        'category': category,
        'rules_count': len(rules),
        'rule_names': rule_names,
        'source_file': str(file_path.relative_to(Path(__file__).parent.parent / 'app' / 'policies')),
        'is_system_policy': True
    }


def create_policy_name(filename: str, category: str) -> str:
    """Create a human-readable policy name from filename."""
    # Convert snake_case to Title Case
    name = filename.replace('_', ' ').title()
    
    # Add category prefix if needed
    if category == 'credit_risk':
        if 'basel' in filename.lower():
            return f"Basel III {name.replace('Basel Iii ', '')}"
        elif 'irb' in filename.lower():
            return f"IRB {name.replace('Irb ', '')}"
    
    return name


def create_policy_description(filename: str, category: str, metadata: dict) -> str:
    """Create policy description."""
    rules_count = metadata.get('rules_count', 0)
    base_desc = f"Policy rules for {category.replace('_', ' ')}"
    
    if rules_count > 0:
        base_desc += f' ({rules_count} rule{"s" if rules_count != 1 else ""})'
    
    return base_desc


def seed_policies_from_yaml(db: Session, admin_user_id: int = 1) -> int:
    """
    Seed policies from YAML files in the policies directory.
    
    Args:
        db: Database session
        admin_user_id: User ID to assign as creator (default: 1 for admin)
        
    Returns:
        Total number of policies created/updated
    """
    from app.core.config import Settings
    
    settings = Settings()
    policy_config_loader = PolicyConfigLoader(settings)
    
    # Get all policy rule files
    rule_files = settings.get_policy_rules_files()
    
    if not rule_files:
        logger.warning("No policy rule files found")
        return 0
    
    logger.info(f"Found {len(rule_files)} policy rule file(s)")
    
    policies_created = 0
    policies_updated = 0
    
    for rule_file in rule_files:
        try:
            # Load YAML content
            with open(rule_file, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            
            if not yaml_content:
                continue
            
            # Convert to YAML string for storage
            rules_yaml = yaml.dump(yaml_content, default_flow_style=False, sort_keys=False)
            
            # Get metadata
            metadata = get_policy_metadata(rule_file, yaml_content)
            
            # Create policy name and description
            filename = rule_file.stem
            policy_name = create_policy_name(filename, metadata['category'])
            policy_description = create_policy_description(filename, metadata['category'], metadata)
            
            # Check if policy already exists (by name and category, or by source_file in metadata)
            # First try to find by name and category
            existing = db.query(Policy).filter(
                Policy.name == policy_name,
                Policy.category == metadata['category'],
                Policy.deleted_at.is_(None)
            ).first()
            
            # If found, check if it's a system policy from the same source file
            if existing and existing.additional_metadata:
                existing_source = existing.additional_metadata.get('source_file')
                if existing_source != metadata['source_file']:
                    # Different source file, create new policy with unique name
                    policy_name = f"{policy_name} ({Path(metadata['source_file']).stem})"
                    existing = None
            
            if existing:
                # Update existing policy
                existing.category = metadata['category']
                existing.description = policy_description
                existing.rules_yaml = rules_yaml
                existing.additional_metadata = metadata
                existing.status = PolicyStatus.ACTIVE.value  # Auto-activate system policies
                policies_updated += 1
                logger.info(f"Updated policy: {policy_name}")
            else:
                # Create new policy
                policy = Policy(
                    name=policy_name,
                    category=metadata['category'],
                    description=policy_description,
                    rules_yaml=rules_yaml,
                    status=PolicyStatus.ACTIVE.value,  # Auto-activate system policies
                    version=1,
                    created_by=admin_user_id,
                    additional_metadata=metadata
                )
                db.add(policy)
                policies_created += 1
                logger.info(f"Created policy: {policy_name}")
        
        except Exception as e:
            logger.error(f"Failed to process policy file {rule_file}: {e}", exc_info=True)
            continue
    
    try:
        db.commit()
        total = policies_created + policies_updated
        
        logger.info(f"Seeded {policies_created} new policy(ies) and updated {policies_updated} existing policy(ies)")
        return total
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit policy seeding: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    from app.db import SessionLocal
    
    db = SessionLocal()
    try:
        # Get admin user ID
        admin = db.query(User).filter(User.role == 'admin').first()
        admin_user_id = admin.id if admin else 1
        
        total = seed_policies_from_yaml(db, admin_user_id)
        print(f"Successfully seeded {total} policy(ies)")
    finally:
        db.close()
