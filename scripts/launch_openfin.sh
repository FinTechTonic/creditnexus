#!/bin/bash
# Quick launcher for OpenFin after backend/frontend are running
# Usage: ./scripts/launch_openfin.sh
# 
# This script uses OpenFin RVM (Runtime Version Manager) to launch the application
# via manifest URL, eliminating the need for the deprecated openfin-cli package.
#
# Environment Variables:
#   BACKEND_URL - Backend server URL (default: http://localhost:8000)
#   FRONTEND_URL - Frontend dev server URL (default: http://localhost:5000, matches Vite in client)
#   OPENFIN_MANIFEST_URL - Full manifest URL (default: ${BACKEND_URL}/openfin/app.json). Use app-dev.json for dev (view at Vite).

echo "CreditNexus OpenFin Launcher"
echo "============================="

# Get project root (one level up from scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load configuration from environment or use defaults
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5000}"
MANIFEST_URL="${OPENFIN_MANIFEST_URL:-$BACKEND_URL/openfin/app.json}"

# Function to check if a service is ready
test_service_ready() {
    local url=$1
    local max_retries=${2:-5}
    local retry_delay=${3:-2}
    
    for ((i=0; i<max_retries; i++)); do
        if curl -s -f -o /dev/null --max-time 2 "$url" >/dev/null 2>&1; then
            return 0
        fi
        if [ $i -lt $((max_retries - 1)) ]; then
            echo "   Waiting for service... ($((i + 1))/$max_retries)"
            sleep $retry_delay
        fi
    done
    return 1
}

# Function to find OpenFin RVM
get_openfin_rvm() {
    local rvm_paths=(
        "$HOME/.local/share/OpenFin/RVM/OpenFinRVM"
        "$HOME/.openfin/RVM/OpenFinRVM"
        "/opt/openfin/RVM/OpenFinRVM"
        "/usr/local/bin/OpenFinRVM"
    )
    
    for path in "${rvm_paths[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    
    # Check if openfin CLI is available
    if command -v openfin > /dev/null 2>&1; then
        echo "openfin"
        return 0
    fi
    
    return 1
}

echo ""
echo "Checking services..."

# Check backend health
echo "   Checking backend ($BACKEND_URL)..."
BACKEND_HEALTH_URL="$BACKEND_URL/api/health"
if ! test_service_ready "$BACKEND_HEALTH_URL"; then
    echo "   WARNING: Backend health check failed, but continuing..."
fi

# Check frontend
echo "   Checking frontend ($FRONTEND_URL)..."
if ! test_service_ready "$FRONTEND_URL"; then
    echo "   WARNING: Frontend not ready, but continuing..."
fi

# Verify manifest is accessible
echo "   Checking manifest ($MANIFEST_URL)..."
if ! test_service_ready "$MANIFEST_URL"; then
    echo ""
    echo "ERROR: Manifest is not accessible at $MANIFEST_URL"
    echo "Please ensure the backend is running and serving the manifest."
    exit 1
fi

echo ""
echo "All services ready!"
echo ""
echo "Launching OpenFin application..."
echo "Using manifest URL: $MANIFEST_URL"

# Try to use RVM if available
RVM_PATH=$(get_openfin_rvm)
if [ -n "$RVM_PATH" ]; then
    echo "   Using OpenFin RVM: $RVM_PATH"
    if [ "$RVM_PATH" = "openfin" ]; then
        # Use openfin CLI
        if openfin --config "$MANIFEST_URL" 2>/dev/null; then
            echo "   OpenFin launch initiated via CLI."
            echo "   If this is the first launch, OpenFin Runtime may download automatically."
            exit 0
        else
            echo "   WARNING: CLI launch failed, trying URL method..."
        fi
    else
        # Use RVM executable
        # Run in background - background processes always return 0 immediately
        "$RVM_PATH" --config="$MANIFEST_URL" >/dev/null 2>&1 &
        RVM_PID=$!
        # Give it a moment to start, then check if process is still running
        sleep 0.5
        if kill -0 "$RVM_PID" 2>/dev/null || ps -p "$RVM_PID" >/dev/null 2>&1; then
            echo "   OpenFin launch initiated via RVM."
            echo "   If this is the first launch, OpenFin Runtime may download automatically."
            exit 0
        else
            echo "   WARNING: RVM launch failed, trying URL method..."
        fi
    fi
else
    echo "   RVM not found, using URL method..."
    echo "   Note: OpenFin Runtime will be downloaded automatically if not installed."
    echo "   Tip: Install OpenFin RVM for better reliability: https://openfin.co/download/"
fi

# Fallback to URL method
echo "   Launching via URL..."
if command -v xdg-open > /dev/null 2>&1; then
    # Linux
    xdg-open "$MANIFEST_URL" >/dev/null 2>&1 &
elif command -v open > /dev/null 2>&1; then
    # macOS
    open "$MANIFEST_URL" >/dev/null 2>&1
elif command -v start > /dev/null 2>&1; then
    # Windows (Git Bash)
    start "$MANIFEST_URL" >/dev/null 2>&1
else
    echo ""
    echo "ERROR: Could not find a command to open URL."
    echo "Please open manually: $MANIFEST_URL"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Ensure backend is running: $BACKEND_URL"
    echo "  2. Ensure frontend is running: $FRONTEND_URL"
    echo "  3. Verify manifest is accessible: $MANIFEST_URL"
    echo "  4. Install OpenFin RVM from: https://openfin.co/download/"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "   OpenFin launch initiated via URL."
    echo "   If this is the first launch, OpenFin Runtime may download automatically."
else
    echo ""
    echo "ERROR: Failed to launch OpenFin."
    echo ""
    echo "Troubleshooting:"
    echo "  1. Ensure backend is running: $BACKEND_URL"
    echo "  2. Ensure frontend is running: $FRONTEND_URL"
    echo "  3. Verify manifest is accessible: $MANIFEST_URL"
    echo "  4. Install OpenFin RVM from: https://openfin.co/download/"
    exit 1
fi
