#!/usr/bin/env bash
# Feature 013 - T051: Lead Capture on Proposal Creation
set -e
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
echo "T051: Lead Capture on Proposal Creation"
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

PROPERTY_ID="${PROPOSAL_TEST_PROPERTY_ID:-$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/properties?limit=1&company_ids=${COMPANY_ID:-2}" \
  | jq -r '.data[0].id // .results[0].id // 1')}"

echo "Step 1: Create first proposal with client_document=52998224725..."
PA_RESP=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000}")
PA_ID=$(echo "$PA_RESP" | jq -r '.id')
[ -n "$PA_ID" ] && [ "$PA_ID" != "null" ] || { fail "Failed to create proposal A"; exit 1; }

# lead_id may be in create response or in GET
PA_LEAD=$(echo "$PA_RESP" | jq -r '.lead_id // empty')
if [ -z "$PA_LEAD" ] || [ "$PA_LEAD" = "null" ]; then
  PA_LEAD=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$PA_ID" | jq -r '.lead_id // empty')
fi
[ -n "$PA_LEAD" ] && [ "$PA_LEAD" != "null" ] \
  && pass "Lead created on first proposal (lead_id=$PA_LEAD)" \
  || fail "No lead_id on first proposal"

echo "Step 2: Create second proposal with same client_document..."
PB_RESP=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 98000}")
PB_ID=$(echo "$PB_RESP" | jq -r '.id')
[ -n "$PB_ID" ] && [ "$PB_ID" != "null" ] || { fail "Failed to create proposal B"; exit 1; }

PB_LEAD=$(echo "$PB_RESP" | jq -r '.lead_id // empty')
if [ -z "$PB_LEAD" ] || [ "$PB_LEAD" = "null" ]; then
  PB_LEAD=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$PB_ID" | jq -r '.lead_id // empty')
fi
[ -n "$PB_LEAD" ] && [ "$PB_LEAD" != "null" ] \
  && pass "Lead present on second proposal (lead_id=$PB_LEAD)" \
  || fail "No lead_id on second proposal"

[ "$PA_LEAD" = "$PB_LEAD" ] \
  && pass "Both proposals share the same lead_id ($PA_LEAD)" \
  || fail "Different lead IDs: A=$PA_LEAD, B=$PB_LEAD (expected same)"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
