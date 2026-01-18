#!/bin/bash
# Automated script to help fix TypeScript errors
# This script provides helper functions and can be run incrementally

set -e

echo "TypeScript Error Fix Helper Script"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "client/tsconfig.json" ]; then
    echo "Error: Must be run from project root"
    exit 1
fi

# Function to remove unused React imports
remove_unused_react_imports() {
    echo "Removing unused React imports..."
    find client/src -name "*.tsx" -type f | while read file; do
        # Only remove if React is imported but not used (basic check)
        if grep -q "^import React" "$file" && ! grep -q "React\." "$file" && ! grep -q "<React\." "$file"; then
            echo "  Removing unused React import from: $file"
            sed -i.bak '/^import React,/d' "$file"
            sed -i.bak '/^import React from/d' "$file"
            sed -i.bak '/^import \* as React/d' "$file"
        fi
    done
    echo "Done. Backup files created with .bak extension"
}

# Function to show error summary
show_error_summary() {
    echo "Running TypeScript check..."
    cd client
    npm run build 2>&1 | grep -E "error TS" | head -20
    cd ..
}

# Function to create a fix checklist
create_checklist() {
    echo "Creating fix checklist..."
    python3 scripts/analyze_typescript_errors.py > typescript_fix_checklist.txt
    echo "Checklist created: typescript_fix_checklist.txt"
}

case "$1" in
    remove-react)
        remove_unused_react_imports
        ;;
    summary)
        show_error_summary
        ;;
    checklist)
        create_checklist
        ;;
    *)
        echo "Usage: $0 {remove-react|summary|checklist}"
        echo ""
        echo "Commands:"
        echo "  remove-react  - Remove unused React imports (creates .bak backups)"
        echo "  summary       - Show current error summary"
        echo "  checklist     - Generate detailed fix checklist"
        exit 1
        ;;
esac
