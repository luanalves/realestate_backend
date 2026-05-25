#!/usr/bin/env bash
# integration_tests/test_us021_cms_settings.sh
# US021 Feature 021: CMS Domain - Settings integration tests — Covers: T031

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
echo "US021 CMS Settings Tests"
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

MANAGER_DATA=$(login_user "manager@seed.com.br" "seed123") || MANAGER_DATA=""
MANAGER_SID=$(echo "$MANAGER_DATA" | cut -d'|' -f1); MANAGER_CID=$(echo "$MANAGER_DATA" | cut -d'|' -f2)

cms_req() {
    local method="$1" url="$2" sid="$3" cid="$4"; shift 4
    curl -s "${@}" -X "$method" "$url" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $sid" \
        -H "X-Company-Id: $cid"
}

# ---- S1: GET settings — auto-criação singleton ----
echo ""; echo "S1: GET /api/v1/cms/settings — auto-criação singleton"
RESP=$(cms_req GET "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" -o /tmp/settings_get.json -w "%{http_code}")
if [ "$RESP" = "200" ]; then
    _pass "GET /settings returns 200"
    RESP2=$(cms_req GET "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" -o /tmp/settings_get2.json -w "%{http_code}")
    ID1=$(python3 -c "import json; print(json.load(open('/tmp/settings_get.json')).get('id',''))" 2>/dev/null)
    ID2=$(python3 -c "import json; print(json.load(open('/tmp/settings_get2.json')).get('id',''))" 2>/dev/null)
    [ "$ID1" = "$ID2" ] && [ -n "$ID1" ] && _pass "Singleton retorna mesmo id ($ID1)" || _fail "Singleton" "IDs diferentes: $ID1 vs $ID2"
else
    _fail "GET /settings" "Expected 200, got $RESP — $(cat /tmp/settings_get.json)"
fi

# ---- S2: PUT company_slug válido ----
echo ""; echo "S2: PUT /api/v1/cms/settings — company_slug válido"
SLUG="test-agency-$(date +%s)"
RESP=$(cms_req PUT "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/settings_put.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$SLUG\"}")
[ "$RESP" = "200" ] && _pass "PUT company_slug returns 200" || _fail "PUT company_slug" "Expected 200, got $RESP — $(cat /tmp/settings_put.json)"

# ---- S3: CSS injection → 422 ----
echo ""; echo "S3: PUT custom_css com CSS injection → 422"
RESP=$(cms_req PUT "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/settings_css.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d '{"custom_css": "body { width: expression(alert(1)) }"}')
if [ "$RESP" = "422" ]; then
    ERROR=$(python3 -c "import json; print(json.load(open('/tmp/settings_css.json')).get('error',''))" 2>/dev/null || echo "")
    _pass "CSS injection returns 422"
    [ "$ERROR" = "css_injection_detected" ] && _pass "Error=css_injection_detected" || _fail "Error envelope" "Expected css_injection_detected, got '$ERROR'"
else
    _fail "CSS injection" "Expected 422, got $RESP — $(cat /tmp/settings_css.json)"
fi

# ---- S4: custom_js by manager → 403 ----
echo ""; echo "S4: PUT custom_js por manager → 403"
if [ -n "$MANAGER_SID" ]; then
    RESP=$(cms_req PUT "$API_BASE/cms/settings" "$MANAGER_SID" "$MANAGER_CID" \
        -o /tmp/settings_js_mgr.json -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d '{"custom_js": "console.log(\"test\")"}')
    [ "$RESP" = "403" ] && _pass "Manager PUT custom_js returns 403" || _fail "Manager custom_js" "Expected 403, got $RESP"
else
    _skip "S4: Manager session not available"
fi

# ---- S5: custom_js by owner → 200 com audit fields ----
echo ""; echo "S5: PUT custom_js por owner → 200 com audit fields"
RESP=$(cms_req PUT "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/settings_js_own.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d '{"custom_js": "console.log(\"ok\")"}')
if [ "$RESP" = "200" ]; then
    _pass "Owner PUT custom_js returns 200"
    AUDIT_BY=$(python3 -c "import json; print(json.load(open('/tmp/settings_js_own.json')).get('custom_js_last_modified_by',''))" 2>/dev/null || echo "")
    AUDIT_AT=$(python3 -c "import json; print(json.load(open('/tmp/settings_js_own.json')).get('custom_js_last_modified_at',''))" 2>/dev/null || echo "")
    [ -n "$AUDIT_BY" ] && [ "$AUDIT_BY" != "None" ] && [ "$AUDIT_BY" != "false" ] && _pass "custom_js_last_modified_by preenchido" || _fail "Audit by" "custom_js_last_modified_by vazio"
    [ -n "$AUDIT_AT" ] && [ "$AUDIT_AT" != "None" ] && [ "$AUDIT_AT" != "false" ] && _pass "custom_js_last_modified_at preenchido" || _fail "Audit at" "custom_js_last_modified_at vazio"
else
    _fail "Owner custom_js" "Expected 200, got $RESP — $(cat /tmp/settings_js_own.json)"
fi

# ---- S6: GET by manager — custom_js ausente ----
echo ""; echo "S6: GET settings por manager — custom_js ausente"
if [ -n "$MANAGER_SID" ]; then
    RESP=$(cms_req GET "$API_BASE/cms/settings" "$MANAGER_SID" "$MANAGER_CID" -o /tmp/settings_mgr_get.json -w "%{http_code}")
    if [ "$RESP" = "200" ]; then
        HAS_JS=$(python3 -c "import json; print('yes' if 'custom_js' in json.load(open('/tmp/settings_mgr_get.json')) else 'no')" 2>/dev/null || echo "unknown")
        [ "$HAS_JS" = "no" ] && _pass "Manager GET não inclui custom_js" || _fail "Manager GET" "custom_js não deveria estar presente"
    else
        _fail "Manager GET /settings" "Expected 200, got $RESP"
    fi
else
    _skip "S6: Manager session not available"
fi

echo ""; echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
