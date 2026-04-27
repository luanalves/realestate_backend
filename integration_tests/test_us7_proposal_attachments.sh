#!/usr/bin/env bash
# Feature 013 - T060: Proposal Attachments (multipart upload)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then source "$SCRIPT_DIR/../18.0/.env"; fi
BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
PASS=0; FAIL=0
pass() { echo -e "${GREEN}✓ $1${NC}"; ((PASS++)); }
fail() { echo -e "${RED}✗ $1${NC}"; ((FAIL++)); }

echo "========================================"
echo "T060: Proposal Attachments"
echo "========================================"

if ! command -v jq &>/dev/null; then echo "ERROR: jq required"; exit 1; fi

BEARER_TOKEN=$(get_oauth2_token)
SESSION_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d "{\"login\": \"${TEST_USER_OWNER:-owner@example.com}\", \"password\": \"${TEST_PASSWORD_OWNER:-SecurePass123!}\"}")
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id // empty')
# Note: no Content-Type header here; it is set per-request below
AUTH_ONLY=(-H "Authorization: Bearer $BEARER_TOKEN" -H "X-Session-Id: $SESSION_ID")
AUTH_JSON=("${AUTH_ONLY[@]}" -H "Content-Type: application/json")

PROPERTY_ID=$(curl -s "${AUTH_JSON[@]}" "$API_BASE/properties?limit=1" \
  | jq -r '.data[0].id // .results[0].id // 1')

echo "Creating proposal..."
P1=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_JSON[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \"price\": 100000}")
P1_ID=$(echo "$P1" | jq -r '.id')
[ -n "$P1_ID" ] && [ "$P1_ID" != "null" ] \
  && pass "Proposal created (id=$P1_ID)" \
  || { fail "Could not create proposal"; exit 1; }

BEFORE_COUNT=$(curl -s "${AUTH_JSON[@]}" "$API_BASE/proposals/$P1_ID" \
  | jq -r '.documents_count // 0')

echo "Uploading attachment..."
TMP_FILE=$(mktemp /tmp/f013_attach_XXXXXX.txt)
echo "Test attachment – Feature 013 T060 – $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$TMP_FILE"

UPLOAD_CODE=$(curl -s -o /tmp/f013_upload.json -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$P1_ID/attachments" \
  "${AUTH_ONLY[@]}" \
  -F "file=@$TMP_FILE;type=text/plain" \
  -F "name=test_document.txt")
rm -f "$TMP_FILE"

[ "$UPLOAD_CODE" = "200" ] || [ "$UPLOAD_CODE" = "201" ] \
  && pass "File upload returns $UPLOAD_CODE" \
  || fail "File upload returned $UPLOAD_CODE: $(cat /tmp/f013_upload.json)"
rm -f /tmp/f013_upload.json

AFTER_DATA=$(curl -s "${AUTH_JSON[@]}" "$API_BASE/proposals/$P1_ID")
AFTER_COUNT=$(echo "$AFTER_DATA" | jq -r '.documents_count // 0')
[ "$AFTER_COUNT" -gt "$BEFORE_COUNT" ] \
  && pass "documents_count incremented ($BEFORE_COUNT → $AFTER_COUNT)" \
  || fail "documents_count did not increment (before=$BEFORE_COUNT, after=$AFTER_COUNT)"

ATTACH_LEN=$(echo "$AFTER_DATA" | jq '.attachments // [] | length' 2>/dev/null || echo 0)
[ "${ATTACH_LEN:-0}" -gt 0 ] \
  && pass "GET /proposals/$P1_ID includes attachments array ($ATTACH_LEN item(s))" \
  || fail "attachments array missing or empty in GET response"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
