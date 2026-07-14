#!/usr/bin/env bash
# Feature 019 - US019-S1: Create Goals (CRUD + RBAC matrix) - T018
#
# Success Criteria:
# - Manager POST goal → 201 + id in response
# - POST same goal again → 409
# - Agent POST goal → 403
# - POST with month=13 → 422
# - GET list as Agent (no user_id) → 200 (own data only)
# - GET list as Agent with own user_id → 200
# - GET list as Agent with another user_id → 403 (SEC-3)

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

pass() { echo -e "${GREEN}✓ $1${NC}"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}✗ $1${NC}"; FAIL=$((FAIL + 1)); }
info() { echo -e "${YELLOW}  $1${NC}"; }

echo "========================================"
echo "US019-S1: Create Goals — RBAC Matrix"
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

# ── Helper: login and extract session + company ─────────────────────────────
login_user() {
    local email="$1" pass="$2"
    local resp=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$pass\"}")
    local sid=$(echo "$resp" | jq -r '.session_id // empty')
    local cid=$(echo "$resp" | jq -r '.user.default_company_id // empty')
    local uid=$(echo "$resp" | jq -r '.user.id // empty')
    if [ -z "$sid" ]; then echo ""; return 1; fi
    echo "$sid|$cid|$uid"
}

# ── Credentials from env or defaults ───────────────────────────────────────
MANAGER_EMAIL="${US019_MANAGER_EMAIL:-manager_019@example.com}"
MANAGER_PASS="${US019_MANAGER_PASS:-ManagerPass019!}"
AGENT_EMAIL="${US019_AGENT_EMAIL:-agent_019@example.com}"
AGENT_PASS="${US019_AGENT_PASS:-AgentPass019!}"

# ── Login as Manager ────────────────────────────────────────────────────────
echo ""
echo "Step 1: Login as Manager..."
MGR_DATA=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASS")
if [ -z "$MGR_DATA" ]; then
    echo -e "${RED}✗ Manager login failed — is seed data loaded? Run seeds/019_goals_seed.py${NC}"
    exit 1
fi
MGR_SID=$(echo "$MGR_DATA" | cut -d'|' -f1)
MGR_CID=$(echo "$MGR_DATA" | cut -d'|' -f2)
MGR_UID=$(echo "$MGR_DATA" | cut -d'|' -f3)
pass "Manager logged in (uid=$MGR_UID)"

# ── Login as Agent ───────────────────────────────────────────────────────────
echo ""
echo "Step 2: Login as Agent..."
AGT_DATA=$(login_user "$AGENT_EMAIL" "$AGENT_PASS")
if [ -z "$AGT_DATA" ]; then
    echo -e "${RED}✗ Agent login failed — is seed data loaded?${NC}"
    exit 1
fi
AGT_SID=$(echo "$AGT_DATA" | cut -d'|' -f1)
AGT_CID=$(echo "$AGT_DATA" | cut -d'|' -f2)
AGT_UID=$(echo "$AGT_DATA" | cut -d'|' -f3)
pass "Agent logged in (uid=$AGT_UID)"

# ── Helper: call goals API ───────────────────────────────────────────────────
goals_request() {
    local method="$1" url="$2" sid="$3" cid="$4" body="$5"
    local args=(-s -X "$method" "$url"
        -H "Authorization: Bearer $BEARER_TOKEN"
        -H "X-Openerp-Session-Id: $sid"
        -H "X-Company-Id: $cid")
    if [ -n "$body" ]; then
        args+=(-H "Content-Type: application/json" -d "$body")
    fi
    curl "${args[@]}"
}

# ── T1: Manager creates goal → 201 ─────────────────────────────────────────
echo ""
echo "Step 3: Manager creates goal → expect 201..."
CREATE_BODY=$(jq -n \
    --argjson uid "$AGT_UID" \
    '{user_id: $uid, year: 2026, month: 8, metric_type: "captacao",
      operation_type: "sale", target_count: 10}')

RESP=$(curl -s -o /tmp/019_create_resp.json -w "%{http_code}" \
    -X POST "$API_BASE/goals" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MGR_SID" \
    -H "X-Company-Id: $MGR_CID" \
    -H "Content-Type: application/json" \
    -d "$CREATE_BODY")

if [ "$RESP" = "201" ]; then
    GOAL_ID=$(jq -r '.id' /tmp/019_create_resp.json)
    pass "Manager POST goal → 201 (goal_id=$GOAL_ID)"
elif [ "$RESP" = "409" ]; then
    # (user, year, month, metric_type, operation_type) already exists from a
    # previous run of this script (not cleaned up between runs) - look it up
    # instead of treating this as a failure.
    EXISTING=$(curl -s "$API_BASE/goals?user_id=${AGT_UID}&year=2026&month=8&metric_type=captacao&operation_type=sale" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $MGR_SID" \
        -H "X-Company-Id: $MGR_CID")
    GOAL_ID=$(echo "$EXISTING" | jq -r '.results[0].id // empty' 2>/dev/null)
    if [ -n "$GOAL_ID" ]; then
        pass "Goal already existed (from a prior run) → goal_id=$GOAL_ID"
    else
        fail "Manager POST goal → 409, and lookup of existing goal failed"
        GOAL_ID=""
    fi
else
    fail "Manager POST goal → expected 201, got $RESP"
    cat /tmp/019_create_resp.json
    GOAL_ID=""
fi

# ── T2: Duplicate goal → 409 ─────────────────────────────────────────────────
echo ""
echo "Step 4: Duplicate goal → expect 409..."
RESP=$(curl -s -o /tmp/019_dup_resp.json -w "%{http_code}" \
    -X POST "$API_BASE/goals" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MGR_SID" \
    -H "X-Company-Id: $MGR_CID" \
    -H "Content-Type: application/json" \
    -d "$CREATE_BODY")

if [ "$RESP" = "409" ]; then
    pass "Duplicate goal → 409 (conflict)"
else
    fail "Duplicate goal → expected 409, got $RESP"
    cat /tmp/019_dup_resp.json
fi

# ── T3: Agent POST goal → 403 ─────────────────────────────────────────────────
echo ""
echo "Step 5: Agent POST goal → expect 403..."
AGENT_BODY=$(jq -n \
    --argjson uid "$AGT_UID" \
    '{user_id: $uid, year: 2026, month: 6, metric_type: "captacao",
      operation_type: "sale", target_count: 5}')

RESP=$(curl -s -o /tmp/019_agent_post_resp.json -w "%{http_code}" \
    -X POST "$API_BASE/goals" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $AGT_SID" \
    -H "X-Company-Id: $AGT_CID" \
    -H "Content-Type: application/json" \
    -d "$AGENT_BODY")

if [ "$RESP" = "403" ]; then
    pass "Agent POST goal → 403 (forbidden)"
else
    fail "Agent POST goal → expected 403, got $RESP"
    cat /tmp/019_agent_post_resp.json
fi

# ── T4: Invalid month=13 → 422 ─────────────────────────────────────────────
echo ""
echo "Step 6: month=13 → expect 422..."
INVALID_BODY=$(jq -n \
    --argjson uid "$AGT_UID" \
    '{user_id: $uid, year: 2026, month: 13, metric_type: "novos_clientes",
      operation_type: "all", target_count: 5}')

RESP=$(curl -s -o /tmp/019_invalid_resp.json -w "%{http_code}" \
    -X POST "$API_BASE/goals" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MGR_SID" \
    -H "X-Company-Id: $MGR_CID" \
    -H "Content-Type: application/json" \
    -d "$INVALID_BODY")

if [ "$RESP" = "422" ] || [ "$RESP" = "400" ]; then
    pass "month=13 → ${RESP} (validation error)"
else
    fail "month=13 → expected 422, got $RESP"
    cat /tmp/019_invalid_resp.json
fi

# ── T5: GET as Agent (no user_id) → 200 own data ──────────────────────────
echo ""
echo "Step 7: Agent GET /api/v1/goals (no user_id) → expect 200..."
RESP=$(curl -s -o /tmp/019_agent_list.json -w "%{http_code}" \
    -X GET "$API_BASE/goals" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $AGT_SID" \
    -H "X-Company-Id: $AGT_CID")

if [ "$RESP" = "200" ]; then
    COUNT=$(jq -r '.count' /tmp/019_agent_list.json)
    pass "Agent GET goals → 200 (count=$COUNT)"
else
    fail "Agent GET goals → expected 200, got $RESP"
    cat /tmp/019_agent_list.json
fi

# ── T6: Agent GET with own user_id → 200 ──────────────────────────────────
echo ""
echo "Step 8: Agent GET /api/v1/goals?user_id=own → expect 200..."
RESP=$(curl -s -o /tmp/019_agent_own.json -w "%{http_code}" \
    -X GET "$API_BASE/goals?user_id=$AGT_UID" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $AGT_SID" \
    -H "X-Company-Id: $AGT_CID")

if [ "$RESP" = "200" ]; then
    pass "Agent GET goals with own user_id → 200"
else
    fail "Agent GET goals with own user_id → expected 200, got $RESP"
    cat /tmp/019_agent_own.json
fi

# ── T7: Agent GET with other user_id → 403 (SEC-3) ────────────────────────
echo ""
echo "Step 9: Agent GET /api/v1/goals?user_id=manager → expect 403 (SEC-3)..."
RESP=$(curl -s -o /tmp/019_agent_other.json -w "%{http_code}" \
    -X GET "$API_BASE/goals?user_id=$MGR_UID" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $AGT_SID" \
    -H "X-Company-Id: $AGT_CID")

if [ "$RESP" = "403" ]; then
    pass "Agent GET goals with other user_id → 403 (SEC-3)"
else
    fail "Agent GET goals with other user_id → expected 403, got $RESP"
    cat /tmp/019_agent_other.json
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "US019-S1 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
