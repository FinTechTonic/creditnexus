#!/bin/bash
set -e

echo "CreditNexus Setup Script"
echo "========================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.11+ is required"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
    echo "Error: Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js 20+ is required"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20+ is required (found v$NODE_VERSION)"
    exit 1
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd client
npm install
cd ..

# Setup .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ""
        echo "Please edit .env file with your configuration"
    else
        echo "Warning: .env.example not found, creating basic .env file"
        cat > .env << EOF
# Database
DATABASE_URL=postgresql://user:password@localhost/creditnexus

# JWT
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
JWT_REFRESH_SECRET_KEY=your-refresh-secret-key-here-min-32-chars

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your-api-key-here
EOF
        echo "Created basic .env file - please update with your values"
    fi
fi

# Initialize database
echo "Initializing database..."
if command -v alembic &> /dev/null || [ -f "venv/bin/alembic" ]; then
    alembic upgrade head
else
    echo "Warning: Alembic not found, skipping database migration"
    echo "Run 'alembic upgrade head' manually after activating venv"
fi

echo ""
echo "Setup complete!"
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  python server.py"
echo ""
echo "In another terminal:"
echo "  cd client && npm run dev"
