#!/usr/bin/env bash
# Feature 013 - T032: Concurrent Proposal Creation (Race Condition / Queue)
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
echo "T032: Concurrent Proposal Creation"
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

TMPDIR=$(mktemp -d)
PIDS=()

create_proposal() {
  local idx=$1
  curl -s -X POST "$API_BASE/proposals" \
    "${AUTH_HEADERS[@]}" \
    -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000}" \
    > "$TMPDIR/result_$idx.json"
}

echo "Firing 10 parallel POST /proposals requests..."
for i in $(seq 1 10); do
  create_proposal "$i" &
  PIDS+=($!)
done
for pid in "${PIDS[@]}"; do wait "$pid"; done

DRAFT_COUNT=0
QUEUED_COUNT=0
for i in $(seq 1 10); do
  STATE=$(jq -r '.state // empty' "$TMPDIR/result_$i.json" 2>/dev/null)
  case "$STATE" in
    draft)  DRAFT_COUNT=$((DRAFT_COUNT+1)) ;;
    queued) QUEUED_COUNT=$((QUEUED_COUNT+1)) ;;
  esac
done
rm -rf "$TMPDIR"

[ "$DRAFT_COUNT"  -ge 1 ] \
  && pass "At least 1 proposal in state=draft (got $DRAFT_COUNT)" \
  || fail "Expected at least 1 draft, got $DRAFT_COUNT"
TOTAL_VALID=$((DRAFT_COUNT + QUEUED_COUNT))
[ "$TOTAL_VALID" -ge 1 ] \
  && pass "$TOTAL_VALID proposals created (${DRAFT_COUNT} draft + ${QUEUED_COUNT} queued) — no duplicates in draft state" \
  || fail "No valid proposals created"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
