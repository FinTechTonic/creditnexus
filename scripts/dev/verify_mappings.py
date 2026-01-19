"""Quick script to verify field mappings were created correctly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.templates.registry import TemplateRegistry

db = SessionLocal()
try:
    template = TemplateRegistry.get_template_by_code(db, 'LMA-CL-FA-2024-EN')
    if template:
        mappings = TemplateRegistry.get_field_mappings(db, template.id)
        print(f'Found {len(mappings)} mappings for {template.template_code}:')
        for m in mappings[:15]:
            print(f"  {m.template_field} -> {m.cdm_field} (required: {m.is_required})")
    else:
        print("Template not found")
finally:
    db.close()
