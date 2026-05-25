#!/usr/bin/env bash
# integration_tests/test_us021_cms_templates.sh
# US021 Feature 021: CMS Domain - Templates integration tests — Covers: T027

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; SKIP=0

_pass() { echo -e "${GREEN}  [PASS] $1${NC}"; ((PASS++)) || true; }
_fail() { echo -e "${RED}  [FAIL] $1 — $2${NC}"; ((FAIL++)) || true; }
_skip() { echo -e "${YELLOW}  [SKIP] $1${NC}"; ((SKIP++)) || true; }

echo "========================================"
echo "US021 CMS Templates Tests"
echo "========================================"

BEARER_TOKEN=$(get_oauth2_token) || { echo "Failed to get OAuth2 token"; exit 1; }

login_user() {
    local resp=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$1\", \"password\": \"$2\"}")
    local sid=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
    local cid=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('user',{}).get('default_company_id',''))" 2>/dev/null)
    [ -z "$sid" ] && { echo ""; return 1; }; echo "$sid|$cid"
}

OWNER_DATA=$(login_user "owner@seed.com.br" "seed123") || { echo "Owner login failed"; exit 1; }
OWNER_SID=$(echo "$OWNER_DATA" | cut -d'|' -f1); OWNER_CID=$(echo "$OWNER_DATA" | cut -d'|' -f2)

AGENT_DATA=$(login_user "agent@seed.com.br" "seed123") || AGENT_DATA=""
AGENT_SID=$(echo "$AGENT_DATA" | cut -d'|' -f1); AGENT_CID=$(echo "$AGENT_DATA" | cut -d'|' -f2)

cms_req() {
    local method="$1" url="$2" sid="$3" cid="$4"; shift 4
    curl -s "${@}" -X "$method" "$url" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $sid" \
        -H "X-Company-Id: $cid"
}

TMPL_ID=""
TMPL_NAME="Test Template $(date +%s)"

# ---- S1: Create template ----
echo ""; echo "S1: POST /api/v1/cms/templates — owner creates"
RESP=$(cms_req POST "$API_BASE/cms/templates" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/tmpl_create.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$TMPL_NAME\", \"category\": \"landing\"}")
if [ "$RESP" = "201" ]; then
    TMPL_ID=$(python3 -c "import json; print(json.load(open('/tmp/tmpl_create.json'))['id'])" 2>/dev/null || echo "")
    _pass "POST /templates returns 201 (id=$TMPL_ID)"
else
    _fail "POST /templates" "Expected 201, got $RESP — $(cat /tmp/tmpl_create.json)"
fi

# ---- S2: List templates ----
echo ""; echo "S2: GET /api/v1/cms/templates — owner list"
RESP=$(cms_req GET "$API_BASE/cms/templates" "$OWNER_SID" "$OWNER_CID" -o /tmp/tmpl_list.json -w "%{http_code}")
[ "$RESP" = "200" ] && _pass "GET /templates returns 200" || _fail "GET /templates" "Expected 200, got $RESP"

# ---- S3: GET by id ----
echo ""; echo "S3: GET /api/v1/cms/templates/:id"
if [ -n "$TMPL_ID" ]; then
    RESP=$(cms_req GET "$API_BASE/cms/templates/$TMPL_ID" "$OWNER_SID" "$OWNER_CID" -o /tmp/tmpl_get.json -w "%{http_code}")
    [ "$RESP" = "200" ] && _pass "GET /templates/:id returns 200" || _fail "GET /templates/:id" "Expected 200, got $RESP"
else
    _skip "S3: no TMPL_ID"
fi

# ---- S4: Update template ----
echo ""; echo "S4: PUT /api/v1/cms/templates/:id"
if [ -n "$TMPL_ID" ]; then
    RESP=$(cms_req PUT "$API_BASE/cms/templates/$TMPL_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/tmpl_update.json -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d '{"category": "about"}')
    [ "$RESP" = "200" ] && _pass "PUT /templates/:id returns 200" || _fail "PUT /templates/:id" "Expected 200, got $RESP — $(cat /tmp/tmpl_update.json)"
else
    _skip "S4: no TMPL_ID"
fi

# ---- S5: Agent GET → 403 ----
echo ""; echo "S5: Agent GET /api/v1/cms/templates → 403"
if [ -n "$AGENT_SID" ]; then
    RESP=$(cms_req GET "$API_BASE/cms/templates" "$AGENT_SID" "$AGENT_CID" -o /tmp/tmpl_agent.json -w "%{http_code}")
    [ "$RESP" = "403" ] && _pass "Agent GET /templates returns 403" || _fail "Agent GET /templates" "Expected 403, got $RESP"
else
    _skip "S5: Agent session not available"
fi

# ---- S6: Delete template ----
echo ""; echo "S6: DELETE /api/v1/cms/templates/:id"
if [ -n "$TMPL_ID" ]; then
    RESP=$(cms_req DELETE "$API_BASE/cms/templates/$TMPL_ID" "$OWNER_SID" "$OWNER_CID" -o /tmp/tmpl_delete.json -w "%{http_code}")
    [ "$RESP" = "200" ] || [ "$RESP" = "204" ] && _pass "DELETE /templates/:id returns 200/204" || _fail "DELETE /templates/:id" "Expected 200/204, got $RESP"
else
    _skip "S6: no TMPL_ID"
fi

echo ""; echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
