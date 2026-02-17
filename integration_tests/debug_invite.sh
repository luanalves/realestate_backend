#!/bin/bash
# Debug script for invite endpoint

cd "$(dirname "$0")/../18.0"
source .env

echo "=== Testing Invite Endpoint with Detailed Logging ==="
echo "1. Getting OAuth token..."

BEARER_TOKEN=$(curl -s -X POST "http://localhost:8069/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"$OAUTH_CLIENT_ID\", \"client_secret\":\"$OAUTH_CLIENT_SECRET\", \"grant_type\":\"client_credentials\"}" \
  | jq -r '.access_token')

if [ -z "$BEARER_TOKEN" ] || [ "$BEARER_TOKEN" = "null" ]; then
  echo "ERROR: Failed to get OAuth token"
  exit 1
fi
echo "✓ OAuth token acquired"

echo "2. Logging in as Owner..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8069/api/v1/users/login" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"login\":\"$TEST_USER_OWNER\",\"password\":\"$TEST_PASSWORD_OWNER\"}")

SESSION_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.session_id')
COMPANY_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.default_company_id')

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  echo "ERROR: Failed to login"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi
echo "✓ Logged in (Company: $COMPANY_ID)"

echo "3. Calling invite endpoint..."
INVITE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "http://localhost:8069/api/v1/users/invite" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "X-Company-ID: $COMPANY_ID" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"email\":\"debug-test@example.com\",\"document\":\"52998224725\",\"profile\":\"manager\",\"name\":\"Debug Test Manager\"}")

RESPONSE_BODY=$(echo "$INVITE_RESPONSE" | sed '$d')
HTTP_CODE=$(echo "$INVITE_RESPONSE" | tail -n 1 | cut -d: -f2)

echo "HTTP Status: $HTTP_CODE"
echo "Response Body:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"

echo ""
echo "4. Checking Odoo logs for [INVITE] entries..."
docker logs odoo18 2>&1 | grep "\[INVITE" | tail -30
