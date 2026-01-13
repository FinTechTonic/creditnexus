#!/bin/bash
# Quick launcher for OpenFin after backend/frontend are running
# Usage: ./scripts/launch_openfin.sh
# 
# This script uses OpenFin RVM (Runtime Version Manager) to launch the application
# via manifest URL, eliminating the need for the deprecated openfin-cli package.

echo "CreditNexus OpenFin Launcher"
echo "============================="

# Get project root (one level up from scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# #region agent log
LOG_DATA=$(cat <<EOF
{"sessionId":"openfin-migration","runId":"launch-script","hypothesisId":"A","location":"launch_openfin.sh:18","message":"Script execution started","data":{"projectRoot":"$PROJECT_ROOT","timestamp":"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"},"timestamp":$(date +%s)000}
EOF
)
echo "$LOG_DATA" >> "$PROJECT_ROOT/.cursor/debug.log" 2>/dev/null
# #endregion

echo ""
echo "Launching OpenFin application via RVM..."
echo "Using manifest URL: http://localhost:8000/openfin/app.json"
echo "Note: OpenFin Runtime will be downloaded automatically if not installed."

# Verify backend is running by checking if manifest is accessible
MANIFEST_URL="http://localhost:8000/openfin/app.json"

if curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$MANIFEST_URL" | grep -q "200\|301\|302"; then
    echo ""
    echo "Backend is running. Manifest accessible."
    
    # #region agent log
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$MANIFEST_URL")
    LOG_DATA=$(cat <<EOF
{"sessionId":"openfin-migration","runId":"launch-script","hypothesisId":"A","location":"launch_openfin.sh:35","message":"Backend manifest check successful","data":{"statusCode":$HTTP_CODE,"manifestUrl":"$MANIFEST_URL"},"timestamp":$(date +%s)000}
EOF
    )
    echo "$LOG_DATA" >> "$PROJECT_ROOT/.cursor/debug.log" 2>/dev/null
    # #endregion
    
    # Launch via URL - RVM will handle runtime download and app launch
    echo ""
    echo "Launching OpenFin application..."
    
    # Try to open URL using platform-specific command
    if command -v xdg-open > /dev/null; then
        # Linux
        xdg-open "$MANIFEST_URL" &
    elif command -v open > /dev/null; then
        # macOS
        open "$MANIFEST_URL"
    elif command -v start > /dev/null; then
        # Windows (Git Bash)
        start "$MANIFEST_URL"
    else
        echo "ERROR: Could not find a command to open URL. Please open manually: $MANIFEST_URL"
        exit 1
    fi
    
    # #region agent log
    LOG_DATA=$(cat <<EOF
{"sessionId":"openfin-migration","runId":"launch-script","hypothesisId":"A","location":"launch_openfin.sh:50","message":"OpenFin launch initiated","data":{"manifestUrl":"$MANIFEST_URL","launchMethod":"RVM_URL"},"timestamp":$(date +%s)000}
EOF
    )
    echo "$LOG_DATA" >> "$PROJECT_ROOT/.cursor/debug.log" 2>/dev/null
    # #endregion
    
    echo "OpenFin application launch initiated."
    echo "If this is the first launch, OpenFin Runtime may download automatically."
else
    echo ""
    echo "ERROR: Backend server is not running or manifest is not accessible."
    echo "Please ensure the backend is running on http://localhost:8000"
    
    # #region agent log
    LOG_DATA=$(cat <<EOF
{"sessionId":"openfin-migration","runId":"launch-script","hypothesisId":"A","location":"launch_openfin.sh:65","message":"Backend manifest check failed","data":{"error":"Connection failed","manifestUrl":"$MANIFEST_URL"},"timestamp":$(date +%s)000}
EOF
    )
    echo "$LOG_DATA" >> "$PROJECT_ROOT/.cursor/debug.log" 2>/dev/null
    # #endregion
    
    exit 1
fi
