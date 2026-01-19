# PowerShell script to test Twilio SMS using curl
# Usage: .\test_twilio_curl.ps1

# Try to load .env file if it exists
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from .env file..." -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)\s*=\s*(.+)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "Environment variables loaded." -ForegroundColor Green
    Write-Host ""
}

# Get credentials from environment
$ACCOUNT_SID = $env:TWILIO_ACCOUNT_SID
$AUTH_TOKEN = $env:TWILIO_AUTH_TOKEN
$FROM_PHONE = $env:TWILIO_PHONE_NUMBER
$TO_PHONE = "+xxxxx"

# Validate required environment variables
$missingVars = @()
if ([string]::IsNullOrWhiteSpace($ACCOUNT_SID)) {
    $missingVars += "TWILIO_ACCOUNT_SID"
}
if ([string]::IsNullOrWhiteSpace($AUTH_TOKEN)) {
    $missingVars += "TWILIO_AUTH_TOKEN"
}
if ([string]::IsNullOrWhiteSpace($FROM_PHONE)) {
    $missingVars += "TWILIO_PHONE_NUMBER"
}

if ($missingVars.Count -gt 0) {
    Write-Host "[ERROR] Missing required environment variables:" -ForegroundColor Red
    foreach ($var in $missingVars) {
        Write-Host "  - $var" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please set these variables before running the script:" -ForegroundColor Yellow
    Write-Host "  `$env:TWILIO_ACCOUNT_SID = 'your_account_sid'" -ForegroundColor Yellow
    Write-Host "  `$env:TWILIO_AUTH_TOKEN = 'your_auth_token'" -ForegroundColor Yellow
    Write-Host "  `$env:TWILIO_PHONE_NUMBER = '+1234567890'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or set them in your .env file and load with:" -ForegroundColor Yellow
    Write-Host "  Get-Content .env | ForEach-Object { if (`$_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable(`$matches[1], `$matches[2]) } }" -ForegroundColor Yellow
    exit 1
}

# Test message
$MESSAGE = "Test message from CreditNexus loan recovery system via curl."

Write-Host "=========================================="
Write-Host "Twilio SMS Test (curl)"
Write-Host "=========================================="
Write-Host "From: $FROM_PHONE"
Write-Host "To: $TO_PHONE"
Write-Host "Message: $MESSAGE"
Write-Host "=========================================="
Write-Host ""

# Create base64 encoded credentials
$bytes = [System.Text.Encoding]::ASCII.GetBytes("${ACCOUNT_SID}:${AUTH_TOKEN}")
$base64 = [System.Convert]::ToBase64String($bytes)

# Send SMS via Twilio API
$body = @{
    From = $FROM_PHONE
    To = $TO_PHONE
    Body = $MESSAGE
}

$headers = @{
    Authorization = "Basic $base64"
}

try {
    $response = Invoke-RestMethod -Uri "https://api.twilio.com/2010-04-01/Accounts/${ACCOUNT_SID}/Messages.json" `
        -Method Post `
        -Headers $headers `
        -Body $body `
        -ContentType "application/x-www-form-urlencoded"
    
    Write-Host "[SUCCESS] SMS sent successfully!"
    Write-Host "Message SID: $($response.sid)"
    Write-Host "Status: $($response.status)"
} catch {
    Write-Host "[ERROR] Failed to send SMS"
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)"
    }
}

Write-Host "=========================================="
