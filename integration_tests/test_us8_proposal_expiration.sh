#!/usr/bin/env bash
# Feature 013 - T064: Proposal Expiration (past valid_until → state=expired)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
if [ -f "$SCRIPT_DIR/../18.0/.env" ] && [ -z "${_PROPOSAL_TEST_ENV:-}" ]; then source "$SCRIPT_DIR/../18.0/.env"; fi
BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
PASS=0; FAIL=0
pass() { echo -e "${GREEN}✓ $1${NC}"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}✗ $1${NC}"; FAIL=$((FAIL+1)); }

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
COMPANY_ID=$(echo "$SESSION_RESPONSE" | jq -r '.user.default_company_id // empty')
AUTH_HEADERS=(-H "Authorization: Bearer $BEARER_TOKEN" -H "X-Openerp-Session-Id: $SESSION_ID" -H "Content-Type: application/json" -H "X-Company-ID: ${COMPANY_ID:-2}")

# The future-valid_until scenario needs a property with no pre-existing
# active proposal (otherwise the new one queues instead of becoming
# draft/sent). Reusing a shared property is unreliable once earlier proposal
# scripts in the same suite run have left one active on it. Create a
# brand-new property instead of deleting anything.
TS=$(date +%s)
PROPERTY_ID=$(curl -s -X POST "$API_BASE/properties" "${AUTH_HEADERS[@]}" \
  -d "{\"name\":\"Expiration Test Property ${TS}\",\"zip_code\":\"01000-000\",\"city\":\"Sao Paulo\",\"street\":\"Rua Teste\",\"street_number\":\"1\",\"area\":50,\"price\":100000,\"property_type_id\":1,\"location_type_id\":1,\"state_id\":1}" \
  | jq -r '.id // empty')
if [ -z "$PROPERTY_ID" ]; then
  echo "ERROR: could not create a fresh property for this test"
  exit 1
fi
curl -s -X POST "$API_BASE/assignments" "${AUTH_HEADERS[@]}" \
  -d "{\"agent_id\": ${TEST_AGENT_ID:-8}, \"property_id\": $PROPERTY_ID, \"responsibility_type\": \"primary\"}" \
  > /dev/null

# Cross-platform yesterday. TOMORROW uses +2 days (not +1) because the host
# running this script and the odoo container can be in different timezones
# (e.g. host UTC-3 vs container UTC) - a same-day-in-UTC "tomorrow" computed
# on the host can already be "today" from the container's point of view,
# which the API validates strictly ("must be after today").
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d)
TOMORROW=$(date -v+2d  +%Y-%m-%d 2>/dev/null || date -d '+2 days'  +%Y-%m-%d)

echo "--- Scenario: past valid_until rejected ($YESTERDAY) ---"
P1_RESP=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000, \"valid_until\": \"$YESTERDAY\"}")
P1_CODE=$(echo "$P1_RESP" | tail -1)
[ "$P1_CODE" = "400" ] || [ "$P1_CODE" = "422" ] \
  && pass "Proposal with past valid_until rejected (HTTP $P1_CODE)" \
  || fail "Expected 400/422 for past valid_until, got: $P1_CODE"

echo "--- Scenario: future valid_until ($TOMORROW) ---"
P2=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000, \"valid_until\": \"$TOMORROW\"}")
P2_ID=$(echo "$P2" | jq -r '.id')
[ -n "$P2_ID" ] && [ "$P2_ID" != "null" ] || { fail "Could not create proposal with future valid_until"; exit 1; }

P2_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P2_ID" | jq -r '.state')
[ "$P2_STATE" != "expired" ] \
  && pass "Future valid_until proposal NOT expired (state=$P2_STATE)" \
  || fail "Future proposal incorrectly marked as expired"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
