# Quick launcher for OpenFin after backend/frontend are running
# Usage: .\scripts\launch_openfin.ps1
# 
# This script uses OpenFin RVM (Runtime Version Manager) to launch the application
# via manifest URL, eliminating the need for the deprecated openfin-cli package.
#
# Environment Variables:
#   BACKEND_URL - Backend server URL (default: http://localhost:8000)
#   FRONTEND_URL - Frontend dev server URL (default: http://localhost:5173)
#   OPENFIN_MANIFEST_URL - Full manifest URL (default: ${BACKEND_URL}/openfin/app.json)

Write-Host "CreditNexus OpenFin Launcher" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# Get project root (one level up from scripts directory)
$projectRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }

# Load configuration from environment or use defaults
$BACKEND_URL = if ($env:BACKEND_URL) { $env:BACKEND_URL } else { "http://localhost:8000" }
$FRONTEND_URL = if ($env:FRONTEND_URL) { $env:FRONTEND_URL } else { "http://localhost:5173" }
$MANIFEST_URL = if ($env:OPENFIN_MANIFEST_URL) { $env:OPENFIN_MANIFEST_URL } else { "$BACKEND_URL/openfin/app.json" }

# Function to check if a service is ready
function Test-ServiceReady {
    param(
        [string]$Url,
        [int]$MaxRetries = 5,
        [int]$RetryDelay = 2
    )
    
    for ($i = 0; $i -lt $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            if ($i -lt $MaxRetries - 1) {
                Write-Host "   Waiting for service... ($($i + 1)/$MaxRetries)" -ForegroundColor Yellow
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    return $false
}

# Function to find OpenFin RVM
function Get-OpenFinRVM {
    $rvmPaths = @(
        "$env:LOCALAPPDATA\OpenFin\RVM\OpenFinRVM.exe",
        "$env:ProgramFiles\OpenFin\RVM\OpenFinRVM.exe",
        "$env:ProgramFiles(x86)\OpenFin\RVM\OpenFinRVM.exe"
    )
    
    foreach ($path in $rvmPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

Write-Host "`nChecking services..." -ForegroundColor Green

# Check backend health
Write-Host "   Checking backend ($BACKEND_URL)..." -ForegroundColor Gray
$backendHealthUrl = "$BACKEND_URL/api/health"
if (-not (Test-ServiceReady -Url $backendHealthUrl)) {
    Write-Host "   WARNING: Backend health check failed, but continuing..." -ForegroundColor Yellow
}

# Check frontend
Write-Host "   Checking frontend ($FRONTEND_URL)..." -ForegroundColor Gray
if (-not (Test-ServiceReady -Url $FRONTEND_URL)) {
    Write-Host "   WARNING: Frontend not ready, but continuing..." -ForegroundColor Yellow
}

# Verify manifest is accessible
Write-Host "   Checking manifest ($MANIFEST_URL)..." -ForegroundColor Gray
if (-not (Test-ServiceReady -Url $MANIFEST_URL)) {
    Write-Host "`nERROR: Manifest is not accessible at $MANIFEST_URL" -ForegroundColor Red
    Write-Host "Please ensure the backend is running and serving the manifest." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nAll services ready!" -ForegroundColor Green
Write-Host "`nLaunching OpenFin application..." -ForegroundColor Green
Write-Host "Using manifest URL: $MANIFEST_URL" -ForegroundColor Gray

# Try to use RVM if available
$rvmPath = Get-OpenFinRVM
if ($rvmPath) {
    Write-Host "   Using OpenFin RVM: $rvmPath" -ForegroundColor Gray
    try {
        Start-Process $rvmPath -ArgumentList "--config=$MANIFEST_URL" -ErrorAction Stop
        Write-Host "   OpenFin launch initiated via RVM." -ForegroundColor Green
        Write-Host "   If this is the first launch, OpenFin Runtime may download automatically." -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "   WARNING: RVM launch failed, trying URL method..." -ForegroundColor Yellow
        Write-Host "   Error: $_" -ForegroundColor Gray
    }
} else {
    Write-Host "   RVM not found, using URL method..." -ForegroundColor Yellow
    Write-Host "   Note: OpenFin Runtime will be downloaded automatically if not installed." -ForegroundColor Yellow
    Write-Host "   Tip: Install OpenFin RVM for better reliability: https://openfin.co/download/" -ForegroundColor Gray
}

# Fallback to URL method
try {
    Start-Process $MANIFEST_URL
    Write-Host "   OpenFin launch initiated via URL." -ForegroundColor Green
    Write-Host "   If this is the first launch, OpenFin Runtime may download automatically." -ForegroundColor Yellow
} catch {
    Write-Host "`nERROR: Failed to launch OpenFin." -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure backend is running: $BACKEND_URL" -ForegroundColor Gray
    Write-Host "  2. Ensure frontend is running: $FRONTEND_URL" -ForegroundColor Gray
    Write-Host "  3. Verify manifest is accessible: $MANIFEST_URL" -ForegroundColor Gray
    Write-Host "  4. Install OpenFin RVM from: https://openfin.co/download/" -ForegroundColor Gray
    Write-Host "  5. Check OpenFin RVM logs at: $env:LOCALAPPDATA\OpenFin\logs\rvm.log" -ForegroundColor Gray
    exit 1
}
