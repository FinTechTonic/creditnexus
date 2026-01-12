# PowerShell script to run CreditNexus in OpenFin
# This script starts the backend server and frontend, then launches OpenFin

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CreditNexus OpenFin Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Get the project root directory
$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Write-Host "`nProject root: $projectRoot" -ForegroundColor Yellow

# Check if .env exists
if (-not (Test-Path (Join-Path $projectRoot ".env"))) {
    Write-Host "`nERROR: .env file not found at $(Join-Path $projectRoot '.env')" -ForegroundColor Red
    Write-Host "Please ensure you're running this script from the project root." -ForegroundColor Red
    exit 1
}

Write-Host "`n1. Starting Backend Server..." -ForegroundColor Green
Write-Host "   Port: http://127.0.0.1:8000" -ForegroundColor Gray

# Start the backend server in a new PowerShell window
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; python scripts/run_dev.py" -PassThru -WindowStyle Normal
Write-Host "   Backend process ID: $($backendProcess.Id)" -ForegroundColor Gray

# Wait a moment for backend to start
Start-Sleep -Seconds 3

Write-Host "`n2. Starting Frontend Development Server..." -ForegroundColor Green
Write-Host "   Building and starting Vite dev server..." -ForegroundColor Gray

# Start the frontend in a new PowerShell window
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\client'; npm run dev" -PassThru -WindowStyle Normal
Write-Host "   Frontend process ID: $($frontendProcess.Id)" -ForegroundColor Gray

# Wait for frontend to start
Start-Sleep -Seconds 5

Write-Host "`n3. Launching OpenFin..." -ForegroundColor Green

# Launch OpenFin with the app.json configuration
try {
    $appConfigPath = Join-Path $projectRoot "openfin\app.json"
    
    if (-not (Test-Path $appConfigPath)) {
        Write-Host "   ERROR: OpenFin app.json not found at $appConfigPath" -ForegroundColor Red
        exit 1
    }
    
    # Try to launch with OpenFin Launcher if available
    if (Get-Command openfin -ErrorAction SilentlyContinue) {
        Write-Host "   Using OpenFin CLI launcher..." -ForegroundColor Gray
        & openfin launch --config "$appConfigPath"
    } else {
        Write-Host "   WARNING: OpenFin CLI not found." -ForegroundColor Yellow
        Write-Host "   Install with: npm install -g @openfin/cli" -ForegroundColor Gray
        Write-Host "   Attempting to serve manifest via backend..." -ForegroundColor Gray
        # The backend should be serving this from openfin/ directory
        Start-Process "http://localhost:8000/openfin/app.json"
    }
} catch {
    Write-Host "   ERROR launching OpenFin: $_" -ForegroundColor Red
    Write-Host "   Make sure OpenFin Runtime is installed." -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "All services are starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nServices running:" -ForegroundColor Yellow
Write-Host "  • Backend: http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "  • Frontend (dev): http://localhost:5173" -ForegroundColor Gray
Write-Host "  • OpenFin: creditnexus-platform" -ForegroundColor Gray
Write-Host "`nPress Ctrl+C in each window to stop services." -ForegroundColor Yellow
Write-Host "`nCleanup: When done, run: Stop-Process -Id $($backendProcess.Id), $($frontendProcess.Id) -Force" -ForegroundColor Gray

# Keep the script running
Read-Host "`nPress Enter to continue monitoring..."
