#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Agent-Only-Own-Leads on list_leads
# ==============================================================================
# Verifies GET /api/v1/leads only returns an agent's own leads
# (agent_id.user_id = self), even within the same company. Creates a second,
# same-company agent fixture on the fly since demo_users.xml only seeds one
# Agent per company.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-${POSTGRES_DB:-realestate}}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"
ADMIN_COOKIE_FILE="/tmp/odoo_us024_agent_admin_$$.txt"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_agent_isolation_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

assert_true() {
    local label="$1" condition="$2"
    if [ "$condition" = "true" ]; then
        echo -e "${GREEN}✓${NC} $label"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label"
        FAIL=$((FAIL+1))
    fi
}

cleanup() { rm -f "$ADMIN_COOKIE_FILE"; }
trap cleanup EXIT

admin_rpc() {
    local model="$1" method="$2" args="$3"
    local kwargs="$4"
    [ -z "$kwargs" ] && kwargs='{}'
    curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"model\":\"$model\",\"method\":\"$method\",\"args\":$args,\"kwargs\":$kwargs}}"
}

{
    echo "=== Test Started: $(date) ==="
    TIMESTAMP=$(date +%s)

    echo -e "${BLUE}SETUP${NC}: Admin login (native Odoo session, fixture creation only)"
    LOGIN_RESP=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
        -H "Content-Type: application/json" \
        -c "$ADMIN_COOKIE_FILE" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"$DB_NAME\",\"login\":\"$ADMIN_LOGIN\",\"password\":\"$ADMIN_PASSWORD\"},\"id\":1}")
    ADMIN_UID=$(echo "$LOGIN_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result',{}).get('uid') or '')")
    if [ -z "$ADMIN_UID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Admin login failed"
        exit 1
    fi
    echo "Admin UID: $ADMIN_UID"

    echo ""
    echo -e "${BLUE}GIVEN${NC}: Pedro's existing agent record, plus a fresh second agent in the same company"
    PEDRO_AGENT_RESP=$(admin_rpc "real.estate.agent" "search_read" "[[[\"email\",\"=\",\"pedro@imobiliaria.com\"]]]" "{\"fields\":[\"id\",\"company_id\"]}")
    PEDRO_AGENT_ID=$(echo "$PEDRO_AGENT_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['id'] if d else '')")
    PEDRO_COMPANY_ID=$(echo "$PEDRO_AGENT_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['company_id'][0] if d else '')")
    echo "Pedro agent_id=$PEDRO_AGENT_ID company_id=$PEDRO_COMPANY_ID"

    if [ -z "$PEDRO_AGENT_ID" ] || [ -z "$PEDRO_COMPANY_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not resolve pedro@imobiliaria.com's agent record — check demo_users.xml seed data"
        exit 1
    fi

    AGENT_GROUP_RESP=$(admin_rpc "ir.model.data" "search_read" "[[[\"module\",\"=\",\"quicksol_estate\"],[\"name\",\"=\",\"group_real_estate_agent\"],[\"model\",\"=\",\"res.groups\"]]]" "{\"fields\":[\"res_id\"]}")
    AGENT_GROUP_ID=$(echo "$AGENT_GROUP_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['res_id'] if d else '')")

    USER_GROUP_RESP=$(admin_rpc "ir.model.data" "search_read" "[[[\"module\",\"=\",\"base\"],[\"name\",\"=\",\"group_user\"],[\"model\",\"=\",\"res.groups\"]]]" "{\"fields\":[\"res_id\"]}")
    USER_GROUP_ID=$(echo "$USER_GROUP_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['res_id'] if d else '')")

    if [ -z "$AGENT_GROUP_ID" ] || [ -z "$USER_GROUP_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not resolve required res.groups ids via ir.model.data"
        exit 1
    fi

    NEW_AGENT_LOGIN="us024.otheragent.${TIMESTAMP}@imobiliaria.com"
    NEW_USER_RESP=$(admin_rpc "res.users" "create" "[{\"name\":\"US024 Other Agent\",\"login\":\"$NEW_AGENT_LOGIN\",\"password\":\"agent123\",\"company_id\":$PEDRO_COMPANY_ID,\"company_ids\":[[6,0,[$PEDRO_COMPANY_ID]]],\"groups_id\":[[6,0,[$AGENT_GROUP_ID,$USER_GROUP_ID]]]}]")
    NEW_USER_ID=$(echo "$NEW_USER_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")
    echo "New agent user_id=$NEW_USER_ID"

    CPF=$(python3 -c "
def d(cpf, w):
    s = sum(int(c) * x for c, x in zip(cpf, w)); r = s % 11
    return '0' if r < 2 else str(11 - r)
base = str(${TIMESTAMP})[-9:].zfill(9)
d1 = d(base, range(10, 1, -1)); d2 = d(base + d1, range(11, 1, -1))
print(f'{base[0:3]}.{base[3:6]}.{base[6:9]}-{d1}{d2}')
")
    NEW_AGENT_REC_RESP=$(admin_rpc "real.estate.agent" "create" "[{\"name\":\"US024 Other Agent\",\"user_id\":$NEW_USER_ID,\"company_id\":$PEDRO_COMPANY_ID,\"email\":\"$NEW_AGENT_LOGIN\",\"cpf\":\"$CPF\"}]")
    NEW_AGENT_ID=$(echo "$NEW_AGENT_REC_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")
    echo "New agent real.estate.agent id=$NEW_AGENT_ID"

    if [ -z "$NEW_USER_ID" ] || [ -z "$NEW_AGENT_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create fixture agent (see raw responses above)"
        exit 1
    fi

    PEDRO_LEAD_RESP=$(admin_rpc "real.estate.lead" "create" "[{\"name\":\"US024 Pedro Own Lead ${TIMESTAMP}\",\"agent_id\":$PEDRO_AGENT_ID,\"company_id\":$PEDRO_COMPANY_ID}]")
    PEDRO_LEAD_ID=$(echo "$PEDRO_LEAD_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")

    OTHER_LEAD_RESP=$(admin_rpc "real.estate.lead" "create" "[{\"name\":\"US024 OtherAgent Lead ${TIMESTAMP}\",\"agent_id\":$NEW_AGENT_ID,\"company_id\":$PEDRO_COMPANY_ID}]")
    OTHER_LEAD_ID=$(echo "$OTHER_LEAD_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")

    echo "Pedro's lead=$PEDRO_LEAD_ID  Other agent's lead=$OTHER_LEAD_ID"

    if [ -z "$PEDRO_LEAD_ID" ] || [ -z "$OTHER_LEAD_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create fixture leads"
        exit 1
    fi

    echo ""
    echo -e "${BLUE}WHEN${NC}: Pedro (agent) lists leads via GET /api/v1/leads"
    authenticate_user "pedro@imobiliaria.com" "agent123"
    LIST_RESP=$(make_api_request "GET" "/api/v1/leads?limit=200")

    echo ""
    echo -e "${BLUE}THEN${NC}: Pedro sees his own lead but not the other agent's lead"
    if echo "$LIST_RESP" | grep -Eq "\"id\": *$PEDRO_LEAD_ID[,}]"; then
        assert_true "Pedro sees his own lead" "true"
    else
        assert_true "Pedro sees his own lead" "false"
    fi

    if echo "$LIST_RESP" | grep -Eq "\"id\": *$OTHER_LEAD_ID[,}]"; then
        assert_true "Pedro does not see the other agent's lead" "false"
    else
        assert_true "Pedro does not see the other agent's lead" "true"
    fi

    echo ""
    echo "Cleanup: deactivating fixture leads and agent..."
    admin_rpc "real.estate.lead" "write" "[[$PEDRO_LEAD_ID,$OTHER_LEAD_ID],{\"active\":false}]" > /dev/null
    admin_rpc "real.estate.agent" "write" "[[$NEW_AGENT_ID],{\"active\":false}]" > /dev/null
    admin_rpc "res.users" "write" "[[$NEW_USER_ID],{\"active\":false}]" > /dev/null

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
