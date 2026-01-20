# Run .nexus file transfer E2E test with PM2 dev stack.
# 1) Ensures PM2 stack is running (backend 8000, frontend 5000).
# 2) Waits for GET /api/health 200.
# 3) Runs tests/compatibility/test_nexus_file_transfer_e2e.py
#
# Usage: from project root:
#   .\scripts\dev\run_nexus_e2e.ps1

$ErrorActionPreference = "Stop"
$BaseUrl = if ($env:BASE_URL) { $env:BASE_URL.TrimEnd('/') } else { "http://127.0.0.1:8000" }
$HealthUrl = "$BaseUrl/api/health"

# Start PM2 if not already running
Write-Host "[run_nexus_e2e] Ensuring PM2 stack..."
& npm run dev:pm2 2>$null
Start-Sleep -Seconds 3

# Wait for backend health
$t = 0
$timeout = [int](if ($env:NEXUS_E2E_HEALTH_TIMEOUT) { $env:NEXUS_E2E_HEALTH_TIMEOUT } else { "60" })
while ($t -lt $timeout) {
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            Write-Host "[run_nexus_e2e] Backend healthy: $HealthUrl"
            break
        }
    } catch {
        Write-Host "[run_nexus_e2e] Waiting for backend... ($t/$timeout)"
    }
    Start-Sleep -Seconds 1
    $t++
}
if ($t -ge $timeout) {
    Write-Error "[run_nexus_e2e] Backend not healthy after ${timeout}s. Run: npm run dev:pm2"
    exit 2
}

# Run E2E
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Get-Item (Join-Path $scriptDir "..\..")).FullName
Push-Location $projectRoot
try {
    & uv run python tests/compatibility/test_nexus_file_transfer_e2e.py
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
