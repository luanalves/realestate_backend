#!/usr/bin/env bash
# Feature 019 - US019-S2: Goal Lifecycle (Create → Update → Delete) - T019
#
# Success Criteria:
# - Create goal → GET list (present) → PUT update target → GET (updated) → DELETE → GET (absent from active)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ $1${NC}"; ((PASS++)); }
fail() { echo -e "${RED}✗ $1${NC}"; ((FAIL++)); }

echo "========================================"
echo "US019-S2: Goal Lifecycle"
echo "========================================"

# ── OAuth2 token ───────────────────────────────────────────────────────────
echo ""
echo "Step 0: Getting OAuth2 bearer token..."
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get OAuth2 token${NC}"
    exit 1
fi
pass "Bearer token obtained"

# ── Login as Manager ────────────────────────────────────────────────────────
MANAGER_EMAIL="${TEST_MANAGER_EMAIL:-manager_019@example.com}"
MANAGER_PASS="${TEST_MANAGER_PASS:-ManagerPass019!}"

MGR_RESP=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d "{\"login\": \"$MANAGER_EMAIL\", \"password\": \"$MANAGER_PASS\"}")

MGR_SID=$(echo "$MGR_RESP" | jq -r '.session_id // empty')
MGR_CID=$(echo "$MGR_RESP" | jq -r '.user.default_company_id // empty')
MGR_UID=$(echo "$MGR_RESP" | jq -r '.user.id // empty')

if [ -z "$MGR_SID" ]; then
    echo -e "${RED}✗ Manager login failed${NC}"
    exit 1
fi
pass "Manager logged in (uid=$MGR_UID)"

# ── Helper ─────────────────────────────────────────────────────────────────
goals_call() {
    local method="$1" path="$2" body="$3"
    local out_file="/tmp/019_lifecycle_resp.json"
    local args=(-s -o "$out_file" -w "%{http_code}"
        -X "$method" "$API_BASE$path"
        -H "Authorization: Bearer $BEARER_TOKEN"
        -H "X-Odoo-Session-Id: $MGR_SID"
        -H "X-Company-Id: $MGR_CID")
    if [ -n "$body" ]; then
        args+=(-H "Content-Type: application/json" -d "$body")
    fi
    curl "${args[@]}"
}

# ── Step 1: Create goal ─────────────────────────────────────────────────────
echo ""
echo "Step 1: Create a new goal for lifecycle test..."

# Use a unique month to avoid conflict with S1 test
CREATE_BODY=$(jq -n --argjson uid "$MGR_UID" \
    '{user_id: $uid, year: 2026, month: 7, metric_type: "visitas",
      operation_type: "all", target_count: 15}')

HTTP=$(goals_call POST "/goals" "$CREATE_BODY")
if [ "$HTTP" = "201" ]; then
    GOAL_ID=$(jq -r '.id' /tmp/019_lifecycle_resp.json)
    pass "Create goal → 201 (goal_id=$GOAL_ID)"
else
    fail "Create goal → expected 201, got $HTTP"
    cat /tmp/019_lifecycle_resp.json
    exit 1
fi

# ── Step 2: GET list — goal present ─────────────────────────────────────────
echo ""
echo "Step 2: GET /api/v1/goals → goal present..."
HTTP=$(goals_call GET "/goals?user_id=$MGR_UID&year=2026&month=7&metric_type=visitas")
if [ "$HTTP" = "200" ]; then
    COUNT=$(jq -r '.count' /tmp/019_lifecycle_resp.json)
    FOUND=$(jq --argjson id "$GOAL_ID" '[.results[] | select(.id == $id)] | length' /tmp/019_lifecycle_resp.json)
    if [ "$FOUND" -ge 1 ]; then
        pass "GET goals → goal id=$GOAL_ID present (count=$COUNT)"
    else
        fail "GET goals → goal id=$GOAL_ID not found in results"
        jq '.results' /tmp/019_lifecycle_resp.json
    fi
else
    fail "GET goals → expected 200, got $HTTP"
fi

# ── Step 3: PUT update target_count ─────────────────────────────────────────
echo ""
echo "Step 3: PUT /api/v1/goals/$GOAL_ID → update target_count to 25..."
UPDATE_BODY='{"target_count": 25}'
HTTP=$(goals_call PUT "/goals/$GOAL_ID" "$UPDATE_BODY")
if [ "$HTTP" = "200" ]; then
    NEW_COUNT=$(jq -r '.target_count' /tmp/019_lifecycle_resp.json)
    if [ "$NEW_COUNT" = "25" ]; then
        pass "PUT goal → 200 (target_count=$NEW_COUNT)"
    else
        fail "PUT goal → 200 but target_count=$NEW_COUNT (expected 25)"
    fi
else
    fail "PUT goal → expected 200, got $HTTP"
    cat /tmp/019_lifecycle_resp.json
fi

# ── Step 4: GET list — confirm updated ──────────────────────────────────────
echo ""
echo "Step 4: GET goals → confirm target_count updated..."
HTTP=$(goals_call GET "/goals?user_id=$MGR_UID&year=2026&month=7&metric_type=visitas")
if [ "$HTTP" = "200" ]; then
    NEW_TARGET=$(jq --argjson id "$GOAL_ID" \
        '[.results[] | select(.id == $id) | .target_count] | first' \
        /tmp/019_lifecycle_resp.json)
    if [ "$NEW_TARGET" = "25" ]; then
        pass "GET goals after update → target_count=25 ✓"
    else
        fail "GET goals after update → target_count=$NEW_TARGET (expected 25)"
    fi
else
    fail "GET goals (after update) → expected 200, got $HTTP"
fi

# ── Step 5: DELETE goal ─────────────────────────────────────────────────────
echo ""
echo "Step 5: DELETE /api/v1/goals/$GOAL_ID → soft delete..."
HTTP=$(goals_call DELETE "/goals/$GOAL_ID")
if [ "$HTTP" = "200" ]; then
    ACTIVE=$(jq -r '.active' /tmp/019_lifecycle_resp.json)
    if [ "$ACTIVE" = "false" ]; then
        pass "DELETE goal → 200 (active=false)"
    else
        fail "DELETE goal → 200 but active=$ACTIVE (expected false)"
    fi
else
    fail "DELETE goal → expected 200, got $HTTP"
    cat /tmp/019_lifecycle_resp.json
fi

# ── Step 6: GET list — goal absent from active list ─────────────────────────
echo ""
echo "Step 6: GET goals → deleted goal absent from active list..."
HTTP=$(goals_call GET "/goals?user_id=$MGR_UID&year=2026&month=7&metric_type=visitas")
if [ "$HTTP" = "200" ]; then
    FOUND=$(jq --argjson id "$GOAL_ID" '[.results[] | select(.id == $id)] | length' /tmp/019_lifecycle_resp.json)
    if [ "$FOUND" = "0" ]; then
        pass "GET goals after delete → goal absent from active list ✓"
    else
        fail "GET goals after delete → goal still visible (active=True)"
    fi
else
    fail "GET goals (after delete) → expected 200, got $HTTP"
fi

# ── Step 7: DELETE again → 404 ─────────────────────────────────────────────
echo ""
echo "Step 7: DELETE goal again → expect 404..."
HTTP=$(goals_call DELETE "/goals/$GOAL_ID")
if [ "$HTTP" = "404" ]; then
    pass "DELETE soft-deleted goal → 404 ✓"
else
    fail "DELETE soft-deleted goal → expected 404, got $HTTP"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "US019-S2 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
