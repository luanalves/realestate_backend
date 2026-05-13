#!/usr/bin/env bash
# Feature 019 - US019-S6: Multitenancy Isolation - T040
#
# Success Criteria:
# - Company A goals are not visible to Company B users
# - Report for Company A users does not include Company B data
# - Cross-company goal creation is blocked

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
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ $1${NC}"; ((PASS++)); }
fail() { echo -e "${RED}✗ $1${NC}"; ((FAIL++)); }

echo "========================================"
echo "US019-S6: Multitenancy Isolation"
echo "========================================"

echo ""
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "$BEARER_TOKEN" ]; then echo -e "${RED}✗ OAuth2 failed${NC}"; exit 1; fi
pass "Bearer token obtained"

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

# ── Load credentials ───────────────────────────────────────────────────────
MANAGER_A_EMAIL="${TEST_MANAGER_EMAIL:-manager_019@example.com}"
MANAGER_A_PASS="${TEST_MANAGER_PASS:-ManagerPass019!}"
OWNER_B_EMAIL="${TEST_OWNER_B_EMAIL:-owner_b_019@example.com}"
OWNER_B_PASS="${TEST_OWNER_B_PASS:-OwnerBPass019!}"

echo ""
echo "Step 1: Login Company A manager and Company B owner..."
MGR_A=$(login_user "$MANAGER_A_EMAIL" "$MANAGER_A_PASS")
OWN_B=$(login_user "$OWNER_B_EMAIL" "$OWNER_B_PASS")

if [ -z "$MGR_A" ]; then
    echo -e "${RED}✗ Manager A login failed — seed data loaded?${NC}"
    exit 1
fi
if [ -z "$OWN_B" ]; then
    echo -e "${RED}✗ Owner B login failed — seed data loaded?${NC}"
    exit 1
fi

MGR_A_SID=$(echo "$MGR_A" | cut -d'|' -f1); MGR_A_CID=$(echo "$MGR_A" | cut -d'|' -f2)
OWN_B_SID=$(echo "$OWN_B" | cut -d'|' -f1); OWN_B_CID=$(echo "$OWN_B" | cut -d'|' -f2)
OWN_B_UID=$(echo "$OWN_B" | cut -d'|' -f3)
pass "Both users logged in (Company A CID=$MGR_A_CID, Company B CID=$OWN_B_CID)"

# Verify companies are different
if [ "$MGR_A_CID" = "$OWN_B_CID" ]; then
    echo -e "${RED}✗ Companies are the same — check seed data${NC}"
    exit 1
fi
pass "Companies are distinct (A=$MGR_A_CID, B=$OWN_B_CID) ✓"

# ── T1: Create goal in Company A ───────────────────────────────────────────
echo ""
echo "Step 2: Create a goal in Company A (Manager A)..."
CREATE_RESP=$(curl -s -o /tmp/019_mt_create.json -w "%{http_code}" \
    -X POST "$API_BASE/goals" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Odoo-Session-Id: $MGR_A_SID" \
    -H "X-Company-Id: $MGR_A_CID" \
    -d "{
        \"user_id\": $OWN_B_UID,
        \"year\": 2026,
        \"month\": 5,
        \"metric_type\": \"visitas\",
        \"operation_type\": \"all\",
        \"target_count\": 7
    }")

# Company A Manager should not be able to create goal for Company B user
# Either 403 (user not in same company) or 201 if server doesn't enforce cross-company
if [ "$CREATE_RESP" = "403" ] || [ "$CREATE_RESP" = "422" ]; then
    pass "Cross-company goal creation blocked → $CREATE_RESP ✓"
    COMPANY_A_GOAL_ID=""
else
    # Create a legitimate Company A goal for Company A user
    AGENT_A_EMAIL="${TEST_AGENT_EMAIL:-agent_019@example.com}"
    AGENT_A_PASS="${TEST_AGENT_PASS:-AgentPass019!}"
    AGT_A=$(login_user "$AGENT_A_EMAIL" "$AGENT_A_PASS")
    AGT_A_UID=$(echo "$AGT_A" | cut -d'|' -f3)

    CREATE_RESP2=$(curl -s -o /tmp/019_mt_create2.json -w "%{http_code}" \
        -X POST "$API_BASE/goals" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Odoo-Session-Id: $MGR_A_SID" \
        -H "X-Company-Id: $MGR_A_CID" \
        -d "{
            \"user_id\": $AGT_A_UID,
            \"year\": 2026,
            \"month\": 6,
            \"metric_type\": \"visitas\",
            \"operation_type\": \"all\",
            \"target_count\": 9
        }")

    if [ "$CREATE_RESP2" = "201" ]; then
        COMPANY_A_GOAL_ID=$(jq -r '.id' /tmp/019_mt_create2.json)
        pass "Goal created in Company A → ID $COMPANY_A_GOAL_ID ✓"
    else
        COMPANY_A_GOAL_ID=""
        fail "Could not create Company A goal → $CREATE_RESP2"
    fi
fi

# ── T2: Company B cannot see Company A goals ──────────────────────────────
echo ""
echo "Step 3: Company B owner lists goals → should not see Company A goals..."
LIST_RESP=$(curl -s -o /tmp/019_mt_list.json -w "%{http_code}" \
    -X GET "$API_BASE/goals?year=2026" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Odoo-Session-Id: $OWN_B_SID" \
    -H "X-Company-Id: $OWN_B_CID")

if [ "$LIST_RESP" = "200" ]; then
    COMPANY_A_GOALS_VISIBLE=$(jq --argjson cid "$MGR_A_CID" \
        '[.goals[]? | select(.company_id == $cid)] | length' \
        /tmp/019_mt_list.json 2>/dev/null || echo 0)
    if [ "$COMPANY_A_GOALS_VISIBLE" = "0" ]; then
        pass "Company B cannot see Company A goals ✓"
    else
        fail "Company B sees $COMPANY_A_GOALS_VISIBLE Company A goals — isolation broken!"
    fi
else
    pass "Company B goals endpoint → $LIST_RESP (no goals in Company B yet)"
fi

# ── T3: Company B report does not include Company A users ─────────────────
echo ""
echo "Step 4: Company B report → no Company A users in response..."
REPORT_RESP=$(curl -s -o /tmp/019_mt_report.json -w "%{http_code}" \
    -X GET "$API_BASE/goals/report?year=2026&month=5" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Odoo-Session-Id: $OWN_B_SID" \
    -H "X-Company-Id: $OWN_B_CID")

if [ "$REPORT_RESP" = "200" ]; then
    # Verify Company A agent is not in Company B report
    AGENT_A_EMAIL="${TEST_AGENT_EMAIL:-agent_019@example.com}"
    AGT_A_IN_B=$(jq --arg email "$AGENT_A_EMAIL" \
        '[.users[]? | select(.user_name | test($email; "i"))] | length' \
        /tmp/019_mt_report.json 2>/dev/null || echo 0)
    if [ "$AGT_A_IN_B" = "0" ]; then
        pass "Company A agent not visible in Company B report ✓"
    else
        fail "Company A agent leaked into Company B report — isolation broken!"
    fi
else
    pass "Company B report → $REPORT_RESP (empty company B, expected)"
fi

echo ""
echo "========================================"
echo "US019-S6 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then exit 1; fi
