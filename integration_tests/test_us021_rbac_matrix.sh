#!/usr/bin/env bash
# integration_tests/test_us021_rbac_matrix.sh
# US021 Feature 021: CMS Domain - RBAC Matrix integration tests — Covers: T045

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
echo "US021 CMS RBAC Matrix Tests"
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

AGENT_DATA=$(login_user "agent@seed.com.br" "seed123") || AGENT_DATA=""
AGENT_SID=$(echo "$AGENT_DATA" | cut -d'|' -f1); AGENT_CID=$(echo "$AGENT_DATA" | cut -d'|' -f2)

# _check: label, user_session_info (sid|cid or ""), method, path, expected_http_status [extra_curl_args...]
_check() {
    local label="$1" user_info="$2" method="$3" path="$4" expected="$5"; shift 5
    if [ -z "$user_info" ]; then
        _skip "$label (session not available)"; return 0
    fi
    local sid=$(echo "$user_info" | cut -d'|' -f1)
    local cid=$(echo "$user_info" | cut -d'|' -f2)
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$API_BASE$path" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $sid" \
        -H "X-Company-Id: $cid" \
        -H "Content-Type: application/json" \
        ${@+"${@}"})
    [ "$actual" = "$expected" ] && _pass "$label → $expected" || _fail "$label" "Expected $expected, got $actual"
}

# ── Setup: create a page and template to use for GET/PUT tests ───────────────
echo ""; echo "--- Setup: creating test fixtures ---"
PAGE_ID=""; TEMPLATE_ID=""

SETUP_RESP=$(curl -s -X POST "$API_BASE/cms/pages" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SID" -H "X-Company-Id: $OWNER_CID" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"RBAC Test Page\", \"slug\": \"rbac-page-$(date +%s)\"}")
PAGE_ID=$(echo "$SETUP_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$PAGE_ID" ] && _pass "Setup page created (id=$PAGE_ID)" || _fail "Setup page" "Could not create page — $(echo $SETUP_RESP | head -c 200)"

SETUP_TMPL=$(curl -s -X POST "$API_BASE/cms/templates" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SID" -H "X-Company-Id: $OWNER_CID" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"RBAC Tmpl $(date +%s)\", \"category\": \"landing\"}")
TEMPLATE_ID=$(echo "$SETUP_TMPL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -n "$TEMPLATE_ID" ] && _pass "Setup template created (id=$TEMPLATE_ID)" || _skip "Setup template failed (non-critical)"

# ==================== PAGES ====================
echo ""; echo "--- Pages ---"
_check "owner  POST /cms/pages" "$OWNER_DATA" POST /cms/pages 201 -d "{\"name\":\"RBACp$(date +%s%N)\",\"slug\":\"rbac-new-$(date +%s%N)\"}"
_check "manager POST /cms/pages" "$MANAGER_DATA" POST /cms/pages 201 -d "{\"name\":\"RBACm$(date +%s%N)\",\"slug\":\"rbac-mgr-$(date +%s%N)\"}"
_check "agent  POST /cms/pages → 403" "$AGENT_DATA" POST /cms/pages 403 -d "{\"name\":\"Agent\",\"slug\":\"agent-try\"}"

_check "owner  GET /cms/pages" "$OWNER_DATA" GET /cms/pages 200
_check "manager GET /cms/pages" "$MANAGER_DATA" GET /cms/pages 200
_check "agent  GET /cms/pages" "$AGENT_DATA" GET /cms/pages 200

if [ -n "$PAGE_ID" ]; then
    _check "owner  GET /cms/pages/:id" "$OWNER_DATA" GET /cms/pages/$PAGE_ID 200
    _check "agent  GET /cms/pages/:id" "$AGENT_DATA" GET /cms/pages/$PAGE_ID 200
    _check "owner  PUT /cms/pages/:id" "$OWNER_DATA" PUT /cms/pages/$PAGE_ID 200 -d '{"title":"Updated by RBAC test"}'
    _check "agent  PUT /cms/pages/:id → 403" "$AGENT_DATA" PUT /cms/pages/$PAGE_ID 403 -d '{"title":"Hacked"}'
fi

# ==================== TEMPLATES ====================
echo ""; echo "--- Templates ---"
_check "owner   POST /cms/templates" "$OWNER_DATA" POST /cms/templates 201 -d "{\"name\":\"OT$(date +%s%N)\",\"category\":\"landing\"}"
_check "manager POST /cms/templates" "$MANAGER_DATA" POST /cms/templates 201 -d "{\"name\":\"MT$(date +%s%N)\",\"category\":\"about\"}"
_check "agent   POST /cms/templates → 403" "$AGENT_DATA" POST /cms/templates 403 -d "{\"name\":\"AT\",\"category\":\"landing\"}"
_check "owner   GET /cms/templates" "$OWNER_DATA" GET /cms/templates 200
_check "agent   GET /cms/templates → 403" "$AGENT_DATA" GET /cms/templates 403

if [ -n "$TEMPLATE_ID" ]; then
    _check "owner   GET /cms/templates/:id" "$OWNER_DATA" GET /cms/templates/$TEMPLATE_ID 200
    _check "agent   GET /cms/templates/:id → 403" "$AGENT_DATA" GET /cms/templates/$TEMPLATE_ID 403
fi

# ==================== MEDIA ====================
echo ""; echo "--- Media ---"
_check "owner   GET /cms/media" "$OWNER_DATA" GET /cms/media 200
_check "agent   GET /cms/media" "$AGENT_DATA" GET /cms/media 200
_check "manager GET /cms/media" "$MANAGER_DATA" GET /cms/media 200

# ==================== SETTINGS ====================
echo ""; echo "--- Settings ---"
_check "owner   GET /cms/settings" "$OWNER_DATA" GET /cms/settings 200
_check "manager GET /cms/settings" "$MANAGER_DATA" GET /cms/settings 200
_check "agent   GET /cms/settings → 200" "$AGENT_DATA" GET /cms/settings 200
_check "owner   PUT /cms/settings" "$OWNER_DATA" PUT /cms/settings 200 -d '{"og_default_title":"RBAC Test"}'
_check "agent   PUT /cms/settings → 403" "$AGENT_DATA" PUT /cms/settings 403 -d '{"og_default_title":"Hacked"}'

echo ""; echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
