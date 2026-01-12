# Quick launcher for OpenFin after backend/frontend are running
# Usage: .\launch_openfin.ps1

Write-Host "CreditNexus OpenFin Launcher" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

$projectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }

# Check if OpenFin CLI is installed
if (-not (Get-Command openfin -ErrorAction SilentlyContinue)) {
    Write-Host "`nOpenFin CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g @openfin/cli
}

Write-Host "`nLaunching OpenFin application..." -ForegroundColor Green

$appConfigPath = Join-Path $projectRoot "openfin\app.json"

if (Test-Path $appConfigPath) {
    Write-Host "Config: $appConfigPath" -ForegroundColor Gray
    openfin launch --config "$appConfigPath"
} else {
    Write-Host "Launching via manifest URL..." -ForegroundColor Gray
    openfin launch --config "http://localhost:8000/openfin/app.json"
}
