# Quick launcher for OpenFin after backend/frontend are running
# Usage: .\scripts\launch_openfin.ps1
# 
# This script uses OpenFin RVM (Runtime Version Manager) to launch the application
# via manifest URL, eliminating the need for the deprecated openfin-cli package.

Write-Host "CreditNexus OpenFin Launcher" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# Get project root (one level up from scripts directory)
$projectRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }

# #region agent log
$logData = @{
    sessionId = "openfin-migration"
    runId = "launch-script"
    hypothesisId = "A"
    location = "launch_openfin.ps1:18"
    message = "Script execution started"
    data = @{
        projectRoot = $projectRoot
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
}
$logJson = $logData | ConvertTo-Json -Compress -Depth 10
Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
# #endregion

Write-Host "`nLaunching OpenFin application via RVM..." -ForegroundColor Green
Write-Host "Using manifest URL: http://localhost:8000/openfin/app.json" -ForegroundColor Gray
Write-Host "Note: OpenFin Runtime will be downloaded automatically if not installed." -ForegroundColor Yellow

# Verify backend is running by checking if manifest is accessible
$manifestUrl = "http://localhost:8000/openfin/app.json"
try {
    $response = Invoke-WebRequest -Uri $manifestUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-Host "`nBackend is running. Manifest accessible." -ForegroundColor Green
    
    # #region agent log
    $logData = @{
        sessionId = "openfin-migration"
        runId = "launch-script"
        hypothesisId = "A"
        location = "launch_openfin.ps1:35"
        message = "Backend manifest check successful"
        data = @{
            statusCode = $response.StatusCode
            manifestUrl = $manifestUrl
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $logJson = $logData | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
    # #endregion
    
    # Launch via URL - RVM will handle runtime download and app launch
    Write-Host "`nLaunching OpenFin application..." -ForegroundColor Green
    Start-Process $manifestUrl
    
    # #region agent log
    $logData = @{
        sessionId = "openfin-migration"
        runId = "launch-script"
        hypothesisId = "A"
        location = "launch_openfin.ps1:50"
        message = "OpenFin launch initiated"
        data = @{
            manifestUrl = $manifestUrl
            launchMethod = "RVM_URL"
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $logJson = $logData | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
    # #endregion
    
    Write-Host "OpenFin application launch initiated." -ForegroundColor Green
    Write-Host "If this is the first launch, OpenFin Runtime may download automatically." -ForegroundColor Yellow
} catch {
    Write-Host "`nERROR: Backend server is not running or manifest is not accessible." -ForegroundColor Red
    Write-Host "Please ensure the backend is running on http://localhost:8000" -ForegroundColor Yellow
    Write-Host "Error: $_" -ForegroundColor Red
    
    # #region agent log
    $logData = @{
        sessionId = "openfin-migration"
        runId = "launch-script"
        hypothesisId = "A"
        location = "launch_openfin.ps1:65"
        message = "Backend manifest check failed"
        data = @{
            error = $_.Exception.Message
            manifestUrl = $manifestUrl
        }
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    }
    $logJson = $logData | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path "$projectRoot\.cursor\debug.log" -Value $logJson -ErrorAction SilentlyContinue
    # #endregion
    
    exit 1
}
