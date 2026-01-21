#!/usr/bin/env python3
"""Analyze TypeScript errors from electron.log and categorize them."""

import re
from collections import defaultdict
from pathlib import Path

def parse_errors(log_file):
    """Parse TypeScript errors from log file."""
    errors = []
    current_error = None
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Match error line: "file:line:col - error TSXXXX: message"
            match = re.match(r'^([^:]+):(\d+):(\d+) - error (TS\d+): (.+)$', line.strip())
            if match:
                if current_error:
                    errors.append(current_error)
                
                file_path, line_num, col, error_code, message = match.groups()
                current_error = {
                    'file': file_path,
                    'line': int(line_num),
                    'col': int(col),
                    'code': error_code,
                    'message': message,
                    'context': []
                }
            elif current_error and line.strip():
                # Add context lines
                current_error['context'].append(line.strip())
    
    if current_error:
        errors.append(current_error)
    
    return errors

def categorize_errors(errors):
    """Categorize errors by type and file."""
    categories = {
        'unused_imports': [],  # TS6133, TS6192, TS6196
        'type_mismatches': [],  # TS2322, TS2345, TS2339, TS2362, TS2363, TS2367
        'missing_properties': [],  # TS2339 (property does not exist)
        'namespace_issues': [],  # TS2503
        'react_issues': [],  # TS2769
        'other': []
    }
    
    by_file = defaultdict(list)
    by_code = defaultdict(list)
    
    for error in errors:
        code = error['code']
        file = error['file']
        
        by_file[file].append(error)
        by_code[code].append(error)
        
        # Categorize
        if code in ['TS6133', 'TS6192', 'TS6196']:
            categories['unused_imports'].append(error)
        elif code in ['TS2322', 'TS2345', 'TS2362', 'TS2363', 'TS2367', 'TS2678', 'TS2774', 'TS2820']:
            categories['type_mismatches'].append(error)
        elif code == 'TS2339' and 'does not exist' in error['message']:
            categories['missing_properties'].append(error)
        elif code == 'TS2503':
            categories['namespace_issues'].append(error)
        elif code == 'TS2769':
            categories['react_issues'].append(error)
        else:
            categories['other'].append(error)
    
    return categories, by_file, by_code

def generate_report(categories, by_file, by_code):
    """Generate a comprehensive error report."""
    report = []
    report.append("=" * 80)
    report.append("TYPESCRIPT ERROR ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Summary
    total = sum(len(errors) for errors in categories.values())
    report.append(f"TOTAL ERRORS: {total}")
    report.append("")
    report.append("ERROR BREAKDOWN BY CATEGORY:")
    report.append("-" * 80)
    for category, errors in categories.items():
        report.append(f"  {category.replace('_', ' ').title()}: {len(errors)} errors")
    report.append("")
    
    # Error codes
    report.append("ERROR BREAKDOWN BY CODE:")
    report.append("-" * 80)
    for code in sorted(by_code.keys()):
        count = len(by_code[code])
        report.append(f"  {code}: {count} errors")
    report.append("")
    
    # Files with most errors
    report.append("TOP 20 FILES WITH MOST ERRORS:")
    report.append("-" * 80)
    sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    for file, errors in sorted_files:
        report.append(f"  {file}: {len(errors)} errors")
    report.append("")
    
    # Detailed breakdown by category
    report.append("=" * 80)
    report.append("DETAILED BREAKDOWN BY CATEGORY")
    report.append("=" * 80)
    report.append("")
    
    for category, errors in categories.items():
        if not errors:
            continue
        
        report.append(f"\n{category.replace('_', ' ').upper()}: {len(errors)} errors")
        report.append("-" * 80)
        
        # Group by file
        by_file_cat = defaultdict(list)
        for error in errors:
            by_file_cat[error['file']].append(error)
        
        for file, file_errors in sorted(by_file_cat.items(), key=lambda x: len(x[1]), reverse=True):
            report.append(f"\n  {file}: {len(file_errors)} errors")
            for error in file_errors[:5]:  # Show first 5 per file
                report.append(f"    Line {error['line']}: {error['code']} - {error['message']}")
            if len(file_errors) > 5:
                report.append(f"    ... and {len(file_errors) - 5} more")
    
    return "\n".join(report)

if __name__ == '__main__':
    log_file = Path('electron.log')
    if not log_file.exists():
        print(f"Error: {log_file} not found")
        exit(1)
    
    errors = parse_errors(log_file)
    categories, by_file, by_code = categorize_errors(errors)
    
    report = generate_report(categories, by_file, by_code)
    
    # Save report
    output_file = Path('typescript_error_analysis.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\nFull report saved to: {output_file}")
