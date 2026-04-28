#!/usr/bin/env bash
# Feature 013 - T038: Counter-Proposal Chain (A → counter B → counter C → accept)
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
echo "T038: Counter-Proposal Chain"
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

# Clean non-seed proposals so property starts with no blocking state
if command -v docker &>/dev/null; then
  COMPOSE_DIR="$(cd "$SCRIPT_DIR/../18.0" && pwd)"
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
    psql -U odoo -d realestate -c "
DELETE FROM real_estate_proposal
WHERE company_id = 5
  AND id NOT IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'quicksol_estate'
      AND name LIKE 'seed_proposal%'
      AND model = 'real.estate.proposal'
  );" > /dev/null 2>&1 || true
fi

# Proposal A
PA=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000}")
PA_ID=$(echo "$PA" | jq -r '.id')
[ -n "$PA_ID" ] && [ "$PA_ID" != "null" ] && pass "Proposal A created (id=$PA_ID)" || { fail "Failed to create proposal A"; exit 1; }

SEND_A=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$PA_ID/send" "${AUTH_HEADERS[@]}" -d '{}')
[ "$SEND_A" = "200" ] || [ "$SEND_A" = "204" ] && pass "Proposal A sent ($SEND_A)" || fail "Send A returned $SEND_A"

# Counter A → B
PB=$(curl -s -X POST "$API_BASE/proposals/$PA_ID/counter" "${AUTH_HEADERS[@]}" -d '{"proposal_value": 95000}')
PB_ID=$(echo "$PB" | jq -r '.id')
[ -n "$PB_ID" ] && [ "$PB_ID" != "null" ] && pass "Counter B created (id=$PB_ID)" || { fail "Failed to create counter B"; exit 1; }

SEND_B=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$PB_ID/send" "${AUTH_HEADERS[@]}" -d '{}')
[ "$SEND_B" = "200" ] || [ "$SEND_B" = "204" ] && pass "Proposal B sent ($SEND_B)" || fail "Send B returned $SEND_B"

# Counter B → C
PC=$(curl -s -X POST "$API_BASE/proposals/$PB_ID/counter" "${AUTH_HEADERS[@]}" -d '{"proposal_value": 92000}')
PC_ID=$(echo "$PC" | jq -r '.id')
[ -n "$PC_ID" ] && [ "$PC_ID" != "null" ] && pass "Counter C created (id=$PC_ID)" || { fail "Failed to create counter C"; exit 1; }

SEND_C=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$PC_ID/send" "${AUTH_HEADERS[@]}" -d '{}')
[ "$SEND_C" = "200" ] || [ "$SEND_C" = "204" ] && pass "Proposal C sent ($SEND_C)" || fail "Send C returned $SEND_C"

# Accept C
ACCEPT_C=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$PC_ID/accept" "${AUTH_HEADERS[@]}" -d '{}')
[ "$ACCEPT_C" = "200" ] || [ "$ACCEPT_C" = "204" ] && pass "Proposal C accepted ($ACCEPT_C)" || fail "Accept C returned $ACCEPT_C"

# A and B must be in terminal state
PA_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$PA_ID" | jq -r '.state')
PB_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$PB_ID" | jq -r '.state')
[[ "$PA_STATE" =~ ^(superseded|rejected|cancelled)$ ]] \
  && pass "Proposal A in terminal state ($PA_STATE)" \
  || fail "Proposal A expected terminal, got: $PA_STATE"
[[ "$PB_STATE" =~ ^(superseded|rejected|cancelled)$ ]] \
  && pass "Proposal B in terminal state ($PB_STATE)" \
  || fail "Proposal B expected terminal, got: $PB_STATE"

# Verify chain via proposal endpoint
CHAIN_RESP=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$PA_ID")
CHAIN_LEN=$(echo "$CHAIN_RESP" | jq '.proposal_chain | length // 0' 2>/dev/null || echo 0)
[ "$CHAIN_LEN" -ge 3 ] \
  && pass "Queue chain has $CHAIN_LEN items (≥3)" \
  || fail "Queue chain length: $CHAIN_LEN (expected ≥3)"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
