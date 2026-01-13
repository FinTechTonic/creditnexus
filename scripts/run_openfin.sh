#!/bin/bash
# Bash script to run CreditNexus backend and frontend for OpenFin (for Unix/Linux/Mac)
# Usage: ./scripts/run_openfin.sh

echo "========================================"
echo "CreditNexus OpenFin Startup"
echo "========================================"

# Get project root (one level up from scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
echo ""
echo "Project root: $PROJECT_ROOT"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "ERROR: .env file not found at $PROJECT_ROOT/.env"
    echo "Please create a .env file with required environment variables."
    exit 1
fi

echo ""
echo "1. Starting Backend Server..."
echo "   Port: http://127.0.0.1:8000"

# Start backend
cd "$PROJECT_ROOT"
python scripts/run_dev.py &
BACKEND_PID=$!
echo "   Backend process ID: $BACKEND_PID"

# Wait for backend to start
sleep 3

echo ""
echo "2. Starting Frontend Development Server..."
echo "   Building and starting Vite dev server..."

# Start frontend
cd "$PROJECT_ROOT/client"
npm run dev &
FRONTEND_PID=$!
echo "   Frontend process ID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

echo ""
echo "3. Ready for OpenFin Launch"
echo ""
echo "========================================"
echo "All services are running!"
echo "========================================"
echo ""
echo "Services running:"
echo "  • Backend: http://127.0.0.1:8000"
echo "  • Frontend (dev): http://localhost:5173"
echo "  • OpenFin config: $PROJECT_ROOT/openfin/app.json"
echo ""
echo "To launch OpenFin, open the manifest URL in your browser:"
echo "  http://localhost:8000/openfin/app.json"
echo ""
echo "Or use the OpenFin RVM directly (if installed):"
echo "  The OpenFin Runtime will be downloaded automatically by RVM if not already installed."
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
wait
