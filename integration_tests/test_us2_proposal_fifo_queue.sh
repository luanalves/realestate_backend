#!/usr/bin/env bash
# Feature 013 - T033: FIFO Queue Ordering
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
echo "T033: FIFO Queue Ordering"
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

# Clean non-seed proposals so property starts fresh (P1 must start as draft)
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

BODY="{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000}"

echo "Creating 3 proposals sequentially for property $PROPERTY_ID..."
P1=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" -d "$BODY")
P2=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" -d "$BODY")
P3=$(curl -s -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" -d "$BODY")

P1_ID=$(echo "$P1" | jq -r '.id');    P1_STATE=$(echo "$P1" | jq -r '.state')
P2_ID=$(echo "$P2" | jq -r '.id');    P2_POS=$(echo "$P2" | jq -r '.queue_position')
P3_ID=$(echo "$P3" | jq -r '.id');    P3_POS=$(echo "$P3" | jq -r '.queue_position')

[ "$P1_STATE" = "draft" ] && pass "Proposal 1 is draft"         || fail "Proposal 1 state: $P1_STATE"
[ "$P2_POS"   = "0"     ] && pass "Proposal 2 queue_position=0" || fail "Proposal 2 queue_position=$P2_POS"
[ "$P3_POS"   = "1"     ] && pass "Proposal 3 queue_position=1" || fail "Proposal 3 queue_position=$P3_POS"

echo "Sending proposal 1 first, then rejecting (draft → sent → reject)..."
curl -s -o /dev/null -X POST "$API_BASE/proposals/$P1_ID/send" "${AUTH_HEADERS[@]}" -d '{}'
REJECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API_BASE/proposals/$P1_ID/reject" \
  "${AUTH_HEADERS[@]}" -d '{"rejection_reason": "Test FIFO reject"}')
[ "$REJECT_CODE" = "200" ] || [ "$REJECT_CODE" = "204" ] \
  && pass "Reject proposal 1 ($REJECT_CODE)" \
  || fail "Reject returned $REJECT_CODE"

NEW_P2_STATE=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P2_ID" | jq -r '.state')
[ "$NEW_P2_STATE" = "draft" ] \
  && pass "Proposal 2 promoted to draft after P1 rejection" \
  || fail "Proposal 2 state after rejection: $NEW_P2_STATE"

NEW_P3_POS=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals/$P3_ID" | jq -r '.queue_position')
[ "$NEW_P3_POS" = "0" ] \
  && pass "Proposal 3 queue_position shifted to 0 (now first in queue)" \
  || fail "Proposal 3 queue_position after shift: $NEW_P3_POS"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
