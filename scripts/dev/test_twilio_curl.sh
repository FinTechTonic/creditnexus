#!/bin/bash
# Test Twilio SMS using curl command
# Usage: ./test_twilio_curl.sh

# Load environment variables (adjust path as needed)
# source .env

# Get credentials from environment
ACCOUNT_SID="${TWILIO_ACCOUNT_SID}"
AUTH_TOKEN="${TWILIO_AUTH_TOKEN}"
FROM_PHONE="${TWILIO_PHONE_NUMBER}"
TO_PHONE="+xxxxx"

# Test message
MESSAGE="Test message from CreditNexus loan recovery system via curl."

echo "=========================================="
echo "Twilio SMS Test (curl)"
echo "=========================================="
echo "From: $FROM_PHONE"
echo "To: $TO_PHONE"
echo "Message: $MESSAGE"
echo "=========================================="
echo ""

# Send SMS via Twilio API
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/${ACCOUNT_SID}/Messages.json" \
  --data-urlencode "From=${FROM_PHONE}" \
  --data-urlencode "To=${TO_PHONE}" \
  --data-urlencode "Body=${MESSAGE}" \
  -u "${ACCOUNT_SID}:${AUTH_TOKEN}"

echo ""
echo "=========================================="
