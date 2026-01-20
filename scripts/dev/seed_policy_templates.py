"""
Seed initial policy templates into the database.

This script loads policy templates from YAML files and creates PolicyTemplate records.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import PolicyTemplate
import yaml


def load_yaml_file(file_path: Path) -> dict:
    """Load YAML file and return as dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_template_metadata(file_path: Path, yaml_content: dict) -> dict:
    """Extract template metadata from file path and YAML content."""
    filename = file_path.stem
    
    # Map filename to use case
    use_case_mapping = {
        'basel_iii_capital': 'basel_iii_capital',
        'irb_ratings': 'irb_ratings',
        'creditworthiness': 'creditworthiness',
        'collateral_requirements': 'collateral_requirements',
        'risk_rating': 'risk_rating',
        'stress_testing': 'stress_testing',
        'data_quality': 'data_quality',
        'model_validation': 'model_validation',
        'regulatory_compliance': 'regulatory_compliance',
        'sanctions_screening': 'sanctions_screening',
        'esg_compliance': 'esg_compliance',
    }
    
    use_case = use_case_mapping.get(filename, filename)
    
    # Determine category from directory
    category = 'credit_risk'  # default
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
        'use_case': use_case,
        'category': category,
        'rules_count': len(rules),
        'rule_names': rule_names,
        'complexity': 'medium' if len(rules) < 5 else 'high'
    }


def create_template_name(filename: str, category: str) -> str:
    """Create a human-readable template name from filename."""
    # Convert snake_case to Title Case
    name = filename.replace('_', ' ').title()
    
    # Add category prefix if needed
    if category == 'credit_risk':
        if 'basel' in filename.lower():
            return f"Basel III {name.replace('Basel Iii ', '')}"
        elif 'irb' in filename.lower():
            return f"IRB {name.replace('Irb ', '')}"
    
    return name


def create_template_description(filename: str, category: str, metadata: dict) -> str:
    """Create template description."""
    descriptions = {
        'basel_iii_capital': 'Basel III capital adequacy requirements and risk-weighted asset calculations',
        'irb_ratings': 'Internal Ratings-Based (IRB) approach for credit risk assessment',
        'creditworthiness': 'Creditworthiness assessment and borrower evaluation policies',
        'collateral_requirements': 'Collateral valuation and requirements policies',
        'risk_rating': 'Risk rating classification and assignment policies',
        'stress_testing': 'Stress testing and scenario analysis policies',
        'data_quality': 'Data quality management and validation policies',
        'model_validation': 'Model validation and backtesting policies',
        'regulatory_compliance': 'Regulatory compliance and reporting requirements',
        'sanctions_screening': 'Sanctions screening and AML compliance policies',
        'esg_compliance': 'ESG (Environmental, Social, Governance) compliance policies',
    }
    
    use_case = metadata.get('use_case', filename)
    base_desc = descriptions.get(use_case, f'Policy template for {filename.replace("_", " ")}')
    
    rules_count = metadata.get('rules_count', 0)
    if rules_count > 0:
        base_desc += f' ({rules_count} rule{"s" if rules_count != 1 else ""})'
    
    return base_desc


def seed_policy_templates(db: Session, admin_user_id: int = 1):
    """
    Seed policy templates from YAML files.
    
    Args:
        db: Database session
        admin_user_id: User ID to assign as creator (default: 1 for admin)
    """
    # Find all YAML files in policies directory
    policies_dir = Path(__file__).parent.parent / 'app' / 'policies'
    
    if not policies_dir.exists():
        print(f"Policies directory not found: {policies_dir}")
        return
    
    yaml_files = []
    
    # Find YAML files recursively
    for yaml_file in policies_dir.rglob('*.yaml'):
        yaml_files.append(yaml_file)
    
    print(f"Found {len(yaml_files)} YAML files")
    
    templates_created = 0
    templates_updated = 0
    
    for yaml_file in yaml_files:
        try:
            # Load YAML content
            yaml_content = load_yaml_file(yaml_file)
            
            # Convert to YAML string
            import yaml as yaml_lib
            rules_yaml = yaml_lib.dump(yaml_content, default_flow_style=False, sort_keys=False)
            
            # Get metadata
            metadata = get_template_metadata(yaml_file, yaml_content)
            
            # Create template name and description
            filename = yaml_file.stem
            template_name = create_template_name(filename, metadata['category'])
            template_description = create_template_description(filename, metadata['category'], metadata)
            
            # Check if template already exists
            existing = db.query(PolicyTemplate).filter(
                PolicyTemplate.name == template_name
            ).first()
            
            if existing:
                # Update existing template
                existing.category = metadata['category']
                existing.description = template_description
                existing.rules_yaml = rules_yaml
                existing.use_case = metadata.get('use_case')
                existing.metadata_ = metadata
                existing.is_system_template = True
                templates_updated += 1
                print(f"Updated template: {template_name}")
            else:
                # Create new template
                template = PolicyTemplate(
                    name=template_name,
                    category=metadata['category'],
                    description=template_description,
                    rules_yaml=rules_yaml,
                    use_case=metadata.get('use_case'),
                    metadata_=metadata,
                    is_system_template=True,
                    created_by=admin_user_id
                )
                db.add(template)
                templates_created += 1
                print(f"Created template: {template_name}")
        
        except Exception as e:
            print(f"Error processing {yaml_file}: {e}")
            continue
    
    # Commit all changes
    try:
        db.commit()
        total = templates_created + templates_updated
        print(f"\nSuccessfully seeded {templates_created} new templates and updated {templates_updated} existing templates")
        return total
    except Exception as e:
        db.rollback()
        print(f"Error committing templates: {e}")
        raise


if __name__ == '__main__':
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get admin user ID (or use 1 as default)
        from app.db.models import User
        admin = db.query(User).filter(User.role == 'admin').first()
        admin_user_id = admin.id if admin else 1
        
        seed_policy_templates(db, admin_user_id)
    finally:
        db.close()
