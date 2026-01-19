#!/usr/bin/env python3
"""
Update all dates before 2026-01-14 in documentation files.
"""

import os
import re
from pathlib import Path

def update_dates_in_file(file_path: Path):
    """Update dates in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace "2024-12-XX" with "2026-01-14"
        content = re.sub(r'2024-12-XX', '2026-01-14', content)
        
        # Replace copyright years 2024 with 2026
        content = re.sub(r'Copyright \(c\) 2024', 'Copyright (c) 2026', content)
        content = re.sub(r'Copyright \(c\) 202[0-5]', 'Copyright (c) 2026', content)
        content = re.sub(r'© 2024', '© 2026', content)
        content = re.sub(r'© 202[0-5]', '© 2026', content)
        
        # Replace example dates in documentation (2024 dates -> 2026 dates)
        # Dates like "2024-12-01" -> "2026-01-15"
        content = re.sub(r'2024-12-01', '2026-01-15', content)
        content = re.sub(r'2024-12-10', '2026-01-20', content)
        content = re.sub(r'2024-12-31', '2026-12-31', content)
        content = re.sub(r'2024-01-01', '2026-01-15', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Update all documentation files."""
    root = Path(__file__).parent.parent
    
    # Update docs directory
    docs_dir = root / 'docs'
    updated_count = 0
    
    if docs_dir.exists():
        for file_path in docs_dir.rglob('*.mdx'):
            if update_dates_in_file(file_path):
                updated_count += 1
        for file_path in docs_dir.rglob('*.md'):
            if update_dates_in_file(file_path):
                updated_count += 1
    
    # Update root level files
    root_files = [
        root / 'LICENCE.md',
        root / 'RAIL.md',
        root / 'SECURITY.md',
        root / 'docs' / 'SECURITY.md',
        root / 'docs' / 'VULNERABILITY_MANAGEMENT.md',
        root / 'docs' / 'INCIDENT_RESPONSE.md',
        root / 'docs' / 'CONTRIBUTING.md',
    ]
    
    for file_path in root_files:
        if file_path.exists():
            if update_dates_in_file(file_path):
                updated_count += 1
    
    print(f"\nTotal files updated: {updated_count}")

if __name__ == '__main__':
    main()
