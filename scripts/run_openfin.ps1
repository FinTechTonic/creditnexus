# PowerShell script to run CreditNexus in OpenFin
# This script starts the backend server and frontend, then launches OpenFin
# Usage: .\scripts\run_openfin.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CreditNexus OpenFin Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Get project root (one level up from scripts directory)
$projectRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }
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

# Launch OpenFin using RVM (Runtime Version Manager) via manifest URL
# This method eliminates the need for the deprecated openfin-cli package
try {
    $appConfigPath = Join-Path $projectRoot "openfin\app.json"
    
    if (-not (Test-Path $appConfigPath)) {
        Write-Host "   ERROR: OpenFin app.json not found at $appConfigPath" -ForegroundColor Red
        
        # #region agent log
        $logData = @{
            sessionId = "openfin-migration"
            runId = "run-script"
            hypothesisId = "B"
            location = "run_openfin.ps1:46"
            message = "Manifest file not found"
            data = @{
                expectedPath = $appConfigPath
            }
            timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        $logJson = $logData | ConvertTo-Json -Compress -Depth 10
        Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
        # #endregion
        
        exit 1
    }
    
    $manifestUrl = "http://localhost:8000/openfin/app.json"
    
    # #region agent log
    $logData = @{
        sessionId = "openfin-migration"
        runId = "run-script"
        hypothesisId = "B"
        location = "run_openfin.ps1:60"
        message = "Preparing OpenFin launch"
        data = @{
            manifestUrl = $manifestUrl
            launchMethod = "RVM_URL"
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $logJson = $logData | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
    # #endregion
    
    # Verify backend is serving the manifest
    try {
        $response = Invoke-WebRequest -Uri $manifestUrl -Method Head -TimeoutSec 2 -ErrorAction Stop
        Write-Host "   Backend manifest accessible. Launching via RVM..." -ForegroundColor Gray
        
        # #region agent log
        $logData = @{
            sessionId = "openfin-migration"
            runId = "run-script"
            hypothesisId = "B"
            location = "run_openfin.ps1:75"
            message = "Backend manifest check successful"
            data = @{
                statusCode = $response.StatusCode
            }
            timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        $logJson = $logData | ConvertTo-Json -Compress -Depth 10
        Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
        # #endregion
        
        # Launch via URL - RVM handles runtime download and app launch
        Start-Process $manifestUrl
        
        # #region agent log
        $logData = @{
            sessionId = "openfin-migration"
            runId = "run-script"
            hypothesisId = "B"
            location = "run_openfin.ps1:88"
            message = "OpenFin launch initiated via RVM"
            data = @{
                manifestUrl = $manifestUrl
            }
            timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        $logJson = $logData | ConvertTo-Json -Compress -Depth 10
        Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
        # #endregion
        
        Write-Host "   OpenFin application launch initiated." -ForegroundColor Green
        Write-Host "   Note: If this is the first launch, OpenFin Runtime may download automatically." -ForegroundColor Yellow
    } catch {
        Write-Host "   WARNING: Backend may not be ready yet. Retrying in 2 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        
        try {
            $response = Invoke-WebRequest -Uri $manifestUrl -Method Head -TimeoutSec 2 -ErrorAction Stop
            Start-Process $manifestUrl
            Write-Host "   OpenFin application launch initiated (retry successful)." -ForegroundColor Green
        } catch {
            Write-Host "   ERROR: Backend server is not accessible at $manifestUrl" -ForegroundColor Red
            Write-Host "   Please ensure the backend is running on http://localhost:8000" -ForegroundColor Yellow
            
            # #region agent log
            $logData = @{
                sessionId = "openfin-migration"
                runId = "run-script"
                hypothesisId = "B"
                location = "run_openfin.ps1:110"
                message = "Backend manifest check failed after retry"
                data = @{
                    error = $_.Exception.Message
                }
                timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
            }
            $logJson = $logData | ConvertTo-Json -Compress -Depth 10
            Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
            # #endregion
        }
    }
} catch {
    Write-Host "   ERROR launching OpenFin: $_" -ForegroundColor Red
    Write-Host "   Make sure OpenFin Runtime is installed (RVM will download it automatically)." -ForegroundColor Yellow
    
    # #region agent log
    $logData = @{
        sessionId = "openfin-migration"
        runId = "run-script"
        hypothesisId = "B"
        location = "run_openfin.ps1:125"
        message = "OpenFin launch error"
        data = @{
            error = $_.Exception.Message
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $logJson = $logData | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
    # #endregion
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
