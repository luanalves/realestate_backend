#!/usr/bin/env bash
# Feature 019 - US019-S3: Report Single Month - T030
#
# Success Criteria:
# - Manager GET /api/v1/goals/report?year=2026&month=5 → 200 with per-metric rows
# - Agent GET own report → 200
# - Agent GET report for another user → 403 (SEC-3)
# - Receptionist GET report → 403 (SEC-2)

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
echo "US019-S3: Report — Single Month"
echo "========================================"

echo ""
echo "Step 0: Getting OAuth2 bearer token..."
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "$BEARER_TOKEN" ]; then echo -e "${RED}✗ OAuth2 failed${NC}"; exit 1; fi
pass "Bearer token obtained"

# ── Login helpers ───────────────────────────────────────────────────────────
login_user() {
    local email="$1" password="$2"
    local resp=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")
    local sid=$(echo "$resp" | jq -r '.session_id // empty')
    local cid=$(echo "$resp" | jq -r '.user.default_company_id // empty')
    local uid=$(echo "$resp" | jq -r '.user.id // empty')
    if [ -z "$sid" ]; then echo ""; return 1; fi
    echo "$sid|$cid|$uid"
}

MANAGER_EMAIL="${TEST_MANAGER_EMAIL:-manager_019@example.com}"
MANAGER_PASS="${TEST_MANAGER_PASS:-ManagerPass019!}"
AGENT_EMAIL="${TEST_AGENT_EMAIL:-agent_019@example.com}"
AGENT_PASS="${TEST_AGENT_PASS:-AgentPass019!}"

echo ""
echo "Step 1: Login as Manager and Agent..."
MGR=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASS")
AGT=$(login_user "$AGENT_EMAIL" "$AGENT_PASS")

if [ -z "$MGR" ] || [ -z "$AGT" ]; then
    echo -e "${RED}✗ Login failed — seed data loaded?${NC}"
    exit 1
fi

MGR_SID=$(echo "$MGR" | cut -d'|' -f1)
MGR_CID=$(echo "$MGR" | cut -d'|' -f2)
MGR_UID=$(echo "$MGR" | cut -d'|' -f3)
AGT_SID=$(echo "$AGT" | cut -d'|' -f1)
AGT_CID=$(echo "$AGT" | cut -d'|' -f2)
AGT_UID=$(echo "$AGT" | cut -d'|' -f3)
pass "Manager (uid=$MGR_UID) and Agent (uid=$AGT_UID) logged in"

report_call() {
    local qs="$1" sid="$2" cid="$3"
    curl -s -o /tmp/019_report_resp.json -w "%{http_code}" \
        -X GET "$API_BASE/goals/report?$qs" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Odoo-Session-Id: $sid" \
        -H "X-Company-Id: $cid"
}

# ── T1: Manager GET report → 200 ─────────────────────────────────────────────
echo ""
echo "Step 2: Manager GET /api/v1/goals/report?year=2026&month=5 → expect 200..."
HTTP=$(report_call "year=2026&month=5" "$MGR_SID" "$MGR_CID")
if [ "$HTTP" = "200" ]; then
    METRICS=$(jq '.users[0].metrics | keys | length // 0' /tmp/019_report_resp.json 2>/dev/null || echo 0)
    PERIOD_MODE=$(jq -r '.period.mode // empty' /tmp/019_report_resp.json)
    pass "Manager GET report → 200 (period.mode=$PERIOD_MODE, metrics=${METRICS})"
    # Validate response shape
    HAS_USERS=$(jq 'has("users")' /tmp/019_report_resp.json)
    HAS_TOTALS=$(jq 'has("totals")' /tmp/019_report_resp.json)
    HAS_PERIOD=$(jq 'has("period")' /tmp/019_report_resp.json)
    if [ "$HAS_USERS" = "true" ] && [ "$HAS_TOTALS" = "true" ] && [ "$HAS_PERIOD" = "true" ]; then
        pass "Response shape has users, totals, period ✓"
    else
        fail "Response missing required keys (has_users=$HAS_USERS, has_totals=$HAS_TOTALS, has_period=$HAS_PERIOD)"
    fi
else
    fail "Manager GET report → expected 200, got $HTTP"
    cat /tmp/019_report_resp.json
fi

# ── T2: Agent GET own report → 200 ───────────────────────────────────────────
echo ""
echo "Step 3: Agent GET report for own user → expect 200..."
HTTP=$(report_call "year=2026&month=5&user_id=$AGT_UID" "$AGT_SID" "$AGT_CID")
if [ "$HTTP" = "200" ]; then
    pass "Agent GET own report → 200 ✓"
else
    fail "Agent GET own report → expected 200, got $HTTP"
    cat /tmp/019_report_resp.json
fi

# ── T3: Agent GET another user report → 403 (SEC-3) ──────────────────────────
echo ""
echo "Step 4: Agent GET report for manager → expect 403 (SEC-3)..."
HTTP=$(report_call "year=2026&month=5&user_id=$MGR_UID" "$AGT_SID" "$AGT_CID")
if [ "$HTTP" = "403" ]; then
    pass "Agent GET report for other user → 403 (SEC-3) ✓"
else
    fail "Agent GET report for other user → expected 403, got $HTTP"
    cat /tmp/019_report_resp.json
fi

# ── T4: completion_pct present in metrics ─────────────────────────────────────
echo ""
echo "Step 5: Validate completion_pct in per-metric response..."
HTTP=$(report_call "year=2026&month=5&user_id=$AGT_UID" "$MGR_SID" "$MGR_CID")
if [ "$HTTP" = "200" ]; then
    # Check captacoes metric has expected keys
    HAS_PCT=$(jq '[.users[] | .metrics.captacoes | has("completion_pct")] | all' /tmp/019_report_resp.json 2>/dev/null || echo false)
    if [ "$HAS_PCT" = "true" ]; then
        pass "completion_pct present in captacoes metric ✓"
    else
        fail "completion_pct missing from captacoes metric"
        jq '.users[0].metrics.captacoes' /tmp/019_report_resp.json
    fi
else
    fail "GET report (metric validation) → expected 200, got $HTTP"
fi

# ── T5: goal_status present in user rows ──────────────────────────────────────
echo ""
echo "Step 6: Validate goal_status in user rows..."
HTTP=$(report_call "year=2026&month=5&user_id=$AGT_UID" "$MGR_SID" "$MGR_CID")
if [ "$HTTP" = "200" ]; then
    HAS_STATUS=$(jq '[.users[] | has("goal_status")] | all' /tmp/019_report_resp.json 2>/dev/null || echo false)
    if [ "$HAS_STATUS" = "true" ]; then
        STATUS=$(jq -r '.users[0].goal_status // "null"' /tmp/019_report_resp.json)
        pass "goal_status present (value=$STATUS) ✓"
    else
        fail "goal_status missing from user rows"
    fi
else
    fail "GET report (goal_status validation) → expected 200, got $HTTP"
fi

# ── T6: Date range > 366 days → 400 (SEC-6) ──────────────────────────────────
echo ""
echo "Step 7: Date range > 366 days → expect 400 (SEC-6)..."
HTTP=$(report_call "date_from=2024-01-01&date_to=2025-03-01" "$MGR_SID" "$MGR_CID")
if [ "$HTTP" = "400" ]; then
    pass "Date range > 366 days → 400 (SEC-6) ✓"
else
    fail "Date range > 366 days → expected 400, got $HTTP"
    cat /tmp/019_report_resp.json
fi

echo ""
echo "========================================"
echo "US019-S3 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then exit 1; fi
