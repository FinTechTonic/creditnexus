import sys

def check_indentation(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('if ') and stripped.endswith(':\n'):
            # Check the next non-empty non-comment line
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.lstrip()
                if next_stripped and not next_stripped.startswith('#'):
                    # Check indentation
                    indent = len(line) - len(stripped)
                    next_indent = len(next_line) - len(next_stripped)
                    if next_indent <= indent:
                        print(f"Potential IndentationError at line {i+1}:")
                        print(f"{i+1}: {line.strip()}")
                        print(f"{j+1}: {next_line.strip()}")
                    break
                j += 1

if __name__ == "__main__":
    check_indentation('app/services/filing_service.py')
