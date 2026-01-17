# CreditNexus Setup Script for Windows
# Run with: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "CreditNexus Setup Script" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python 3.11+ is required" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "Error: Python 3.11+ is required (found $pythonVersion)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Warning: Could not parse Python version" -ForegroundColor Yellow
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Green
    python -m venv venv
}

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Green
python -m pip install --upgrade pip
pip install -r requirements.txt

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Node.js 20+ is required" -ForegroundColor Red
    exit 1
}

$nodeVersion = node --version
$nodeVersionMatch = $nodeVersion -match "v(\d+)"
if ($nodeVersionMatch) {
    $nodeMajor = [int]$matches[1]
    if ($nodeMajor -lt 20) {
        Write-Host "Error: Node.js 20+ is required (found $nodeVersion)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Warning: Could not parse Node.js version" -ForegroundColor Yellow
}

# Install frontend dependencies
Write-Host "Installing frontend dependencies..." -ForegroundColor Green
Set-Location client
npm install
Set-Location ..

# Setup .env file
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Green
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host ""
        Write-Host "Please edit .env file with your configuration" -ForegroundColor Yellow
    } else {
        Write-Host "Warning: .env.example not found, creating basic .env file" -ForegroundColor Yellow
        @"
# Database
DATABASE_URL=postgresql://user:password@localhost/creditnexus

# JWT
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
JWT_REFRESH_SECRET_KEY=your-refresh-secret-key-here-min-32-chars

# LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your-api-key-here
"@ | Out-File -FilePath ".env" -Encoding utf8
        Write-Host "Created basic .env file - please update with your values" -ForegroundColor Yellow
    }
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Green
if (Get-Command alembic -ErrorAction SilentlyContinue) {
    alembic upgrade head
} elseif (Test-Path "venv\Scripts\alembic.exe") {
    & "venv\Scripts\alembic.exe" upgrade head
} else {
    Write-Host "Warning: Alembic not found, skipping database migration" -ForegroundColor Yellow
    Write-Host "Run 'alembic upgrade head' manually after activating venv" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "To start the application:" -ForegroundColor Cyan
Write-Host "  venv\Scripts\Activate.ps1"
Write-Host "  python server.py"
Write-Host ""
Write-Host "In another terminal:"
Write-Host "  cd client"
Write-Host "  npm run dev"
