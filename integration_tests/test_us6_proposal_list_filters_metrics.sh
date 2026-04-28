#!/usr/bin/env bash
# Feature 013 - T055: List Filters and Stats/Metrics
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
echo "T055: List Filters and Stats/Metrics"
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

# Seed at least one draft proposal
curl -s -o /dev/null -X POST "$API_BASE/proposals" "${AUTH_HEADERS[@]}" \
  -d "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Cliente Teste\", \"client_document\": \"52998224725\", \"agent_id\": ${TEST_AGENT_ID:-8}, \"proposal_type\": \"sale\", \"proposal_value\": 100000}"

echo "--- Filter: ?state=draft ---"
DRAFT_RESP=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals?state=draft")
DRAFT_ROWS=$(echo "$DRAFT_RESP" | jq '[.data // .results // [] | .[]] | length')
[ "${DRAFT_ROWS:-0}" -gt 0 ] \
  && pass "?state=draft returns $DRAFT_ROWS proposal(s)" \
  || fail "?state=draft returned 0 proposals"

NON_DRAFT=$(echo "$DRAFT_RESP" | jq '[.data // .results // [] | .[] | select(.state != "draft")] | length')
[ "${NON_DRAFT:-0}" -eq 0 ] \
  && pass "All returned proposals have state=draft" \
  || fail "$NON_DRAFT non-draft proposals leaked through filter"

echo "--- Filter: ?property_id=$PROPERTY_ID ---"
PROP_RESP=$(curl -s "${AUTH_HEADERS[@]}" "$API_BASE/proposals?property_id=$PROPERTY_ID")
PROP_ROWS=$(echo "$PROP_RESP" | jq '[.data // .results // [] | .[]] | length')
[ "${PROP_ROWS:-0}" -gt 0 ] \
  && pass "?property_id=$PROPERTY_ID returns $PROP_ROWS proposal(s)" \
  || fail "?property_id filter returned 0 results"

WRONG_PROP=$(echo "$PROP_RESP" | jq "[.data // .results // [] | .[] | select((.property_id != $PROPERTY_ID) and (.property.id != $PROPERTY_ID))] | length")
[ "${WRONG_PROP:-0}" -eq 0 ] \
  && pass "All returned proposals belong to property_id=$PROPERTY_ID" \
  || fail "$WRONG_PROP proposals with wrong property_id in result"

echo "--- Stats endpoint ---"
STATS_CODE=$(curl -s -o /tmp/f013_stats.json -w "%{http_code}" \
  "${AUTH_HEADERS[@]}" "$API_BASE/proposals/stats")
[ "$STATS_CODE" = "200" ] \
  && pass "GET /proposals/stats returns 200" \
  || fail "GET /proposals/stats returned $STATS_CODE"

STATS_VALID=$(jq 'type == "object" and length > 0' /tmp/f013_stats.json 2>/dev/null || echo false)
[ "$STATS_VALID" = "true" ] \
  && pass "Stats response is a non-empty object" \
  || fail "Stats response invalid: $(cat /tmp/f013_stats.json)"
rm -f /tmp/f013_stats.json

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
