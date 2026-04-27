#!/usr/bin/env bash
# Feature 013 - T032: Concurrent Proposal Creation (Race Condition / Queue)
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
echo "T032: Concurrent Proposal Creation"
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

TMPDIR=$(mktemp -d)
PIDS=()

create_proposal() {
  local idx=$1
  curl -s -X POST "$API_BASE/proposals" \
    "${AUTH_HEADERS[@]}" \
    -d "{\"property_id\": $PROPERTY_ID, \"client_document\": \"52998224725\", \"price\": 100000}" \
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
    draft)  ((DRAFT_COUNT++)) ;;
    queued) ((QUEUED_COUNT++)) ;;
  esac
done
rm -rf "$TMPDIR"

[ "$DRAFT_COUNT"  -eq 1 ] \
  && pass "Exactly 1 proposal in state=draft" \
  || fail "Expected 1 draft, got $DRAFT_COUNT"
[ "$QUEUED_COUNT" -eq 9 ] \
  && pass "Remaining 9 proposals in state=queued" \
  || fail "Expected 9 queued, got $QUEUED_COUNT"

echo ""
echo "PASSED: $PASS, FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
