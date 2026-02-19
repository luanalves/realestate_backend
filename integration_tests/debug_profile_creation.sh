#!/bin/bash
set -e

cd /opt/homebrew/var/www/realestate/realestate_backend/18.0
source .env

# Get OAuth token
BEARER=$(curl -s -X POST "http://localhost:8069/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${OAUTH_CLIENT_ID}&client_secret=${OAUTH_CLIENT_SECRET}" | jq -r '.access_token')

echo "Bearer token obtained"

# Login as Owner
LOGIN=$(curl -s -X POST "http://localhost:8069/api/v1/users/login" \
  -H "Authorization: Bearer $BEARER" \
  -H "Content-Type: application/json" \
  -d "{\"login\": \"$TEST_USER_OWNER\", \"password\": \"$TEST_PASSWORD_OWNER\"}")

SESSION_ID=$(echo "$LOGIN" | jq -r '.session_id')
COMPANY_ID=$(echo "$LOGIN" | jq -r '.user.main_estate_company_id')

echo "Session ID: $SESSION_ID"
echo "Company ID: $COMPANY_ID"

# Create profile
echo "Creating profile..."
curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "http://localhost:8069/api/v1/profiles" \
  -H "Authorization: Bearer $BEARER" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Debug Test Profile\",
    \"company_id\": $COMPANY_ID,
    \"document\": \"12312312387\",
    \"email\": \"debug@test.com\",
    \"phone\": \"11999998888\",
    \"birthdate\": \"1985-06-10\",
    \"profile_type\": \"manager\"
  }" | jq -r '.'
