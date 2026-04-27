#!/usr/bin/env bash
# Feature 013 - T044: Accept and Reject Proposals
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
echo "T044: Accept and Reject Proposals"
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

echo "--- Scenario: Accept ---"
P1=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \"price\": 200000}")
P1_ID=$(echo "$P1" | jq -r '.id')

curl -s -o /dev/null -X POST "$API_BASE/proposals/$P1_ID/send" "${AUTH_HEADERS[@]}" -d '{}'

ACCEPT_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$P1_ID/accept" "${AUTH_HEADERS[@]}" -d '{}')
[ "$ACCEPT_CODE" = "200" ] || [ "$ACCEPT_CODE" = "204" ] \
  && pass "Accept returns $ACCEPT_CODE" \
  || fail "Accept returned $ACCEPT_CODE"

P1_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P1_ID" | jq -r '.state')
[ "$P1_STATE" = "accepted" ] \
  && pass "Proposal state=accepted" \
  || fail "Expected accepted, got: $P1_STATE"

# Double-accept must be rejected
DOUBLE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$P1_ID/accept" "${AUTH_HEADERS[@]}" -d '{}')
[ "$DOUBLE_CODE" = "422" ] || [ "$DOUBLE_CODE" = "409" ] \
  && pass "Double-accept returns $DOUBLE_CODE (idempotency enforced)" \
  || fail "Double-accept returned $DOUBLE_CODE (expected 422 or 409)"

echo "--- Scenario: Reject with reason ---"
P2=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \"price\": 150000}")
P2_ID=$(echo "$P2" | jq -r '.id')

curl -s -o /dev/null -X POST "$API_BASE/proposals/$P2_ID/send" "${AUTH_HEADERS[@]}" -d '{}'

REJECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$P2_ID/reject" \
  "${AUTH_HEADERS[@]}" -d '{"reason": "Price too low"}')
[ "$REJECT_CODE" = "200" ] || [ "$REJECT_CODE" = "204" ] \
  && pass "Reject returns $REJECT_CODE" \
  || fail "Reject returned $REJECT_CODE"

P2_DATA=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P2_ID")
P2_STATE=$(echo "$P2_DATA" | jq -r '.state')
P2_REASON=$(echo "$P2_DATA" | jq -r '.reject_reason // empty')
[ "$P2_STATE"  = "rejected" ] && pass "Proposal state=rejected"            || fail "Expected rejected, got: $P2_STATE"
[ -n "$P2_REASON" ]           && pass "reject_reason stored: '$P2_REASON'" || fail "reject_reason missing in GET response"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
