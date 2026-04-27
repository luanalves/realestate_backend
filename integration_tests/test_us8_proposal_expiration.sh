#!/usr/bin/env bash
# Feature 013 - T064: Proposal Expiration (past valid_until → state=expired)
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
echo "T064: Proposal Expiration"
echo "========================================"

if ! command -v jq &>/dev/null; then echo "ERROR: jq required"; exit 1; fi

BEARER_TOKEN=$(get_oauth2_token)
SESSION_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -d "{\"login\": \"${TEST_USER_OWNER:-owner@example.com}\", \"password\": \"${TEST_PASSWORD_OWNER:-SecurePass123!}\"}")
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id // empty')
AUTH_HEADERS=(-H "Authorization: Bearer $BEARER_TOKEN" -H "X-Session-Id: $SESSION_ID" -H "Content-Type: application/json")

PROPERTY_ID=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/properties?limit=1" \
  | jq -r '.data[0].id // .results[0].id // 1')

# Cross-platform yesterday
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d)
TOMORROW=$(date -v+1d  +%Y-%m-%d 2>/dev/null || date -d tomorrow  +%Y-%m-%d)

echo "--- Scenario: past valid_until ($YESTERDAY) ---"
P1=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \
       \"price\": 100000, \"valid_until\": \"$YESTERDAY\"}")
P1_ID=$(echo "$P1" | jq -r '.id')
[ -n "$P1_ID" ] && [ "$P1_ID" != "null" ] \
  && pass "Proposal with past valid_until created (id=$P1_ID)" \
  || { fail "Could not create proposal with past valid_until"; exit 1; }

# Attempt to trigger expiration cron (non-fatal if endpoint absent)
CRON_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/run-expiration-cron" "${AUTH_HEADERS[@]}" -d '{}')
if [ "$CRON_CODE" = "200" ] || [ "$CRON_CODE" = "204" ]; then
  pass "Expiration cron triggered via API ($CRON_CODE)"
else
  echo "  (cron endpoint returned $CRON_CODE — relying on lazy server-side expiration)"
fi

P1_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P1_ID" | jq -r '.state')
[ "$P1_STATE" = "expired" ] \
  && pass "Proposal state=expired for past valid_until" \
  || fail "Expected expired, got: $P1_STATE"

echo "--- Scenario: future valid_until ($TOMORROW) ---"
P2=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \
       \"price\": 100000, \"valid_until\": \"$TOMORROW\"}")
P2_ID=$(echo "$P2" | jq -r '.id')
[ -n "$P2_ID" ] && [ "$P2_ID" != "null" ] || { fail "Could not create proposal with future valid_until"; exit 1; }

P2_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P2_ID" | jq -r '.state')
[ "$P2_STATE" != "expired" ] \
  && pass "Future valid_until proposal NOT expired (state=$P2_STATE)" \
  || fail "Future proposal incorrectly marked as expired"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
