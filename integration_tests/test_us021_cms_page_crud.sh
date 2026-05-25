#!/usr/bin/env bash
# integration_tests/test_us021_cms_page_crud.sh
# US021 - Feature 021: CMS Domain - Page CRUD + State Machine integration tests
# Covers: T016 (US1 + US4)

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

echo "=========================================="
echo "US021 CMS Page CRUD + State Machine Tests"
echo "=========================================="

# ── OAuth2 token ─────────────────────────────────────────────────────────────
BEARER_TOKEN=$(get_oauth2_token) || { echo "Failed to get OAuth2 token"; exit 1; }

login_user() {
    local email="$1" pass="$2"
    local resp=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$pass\"}")
    local sid=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
    local cid=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('user',{}).get('default_company_id',''))" 2>/dev/null)
    if [ -z "$sid" ]; then echo ""; return 1; fi
    echo "$sid|$cid"
}

OWNER_DATA=$(login_user "owner@seed.com.br" "seed123") || { echo "Owner login failed"; exit 1; }
OWNER_SID=$(echo "$OWNER_DATA" | cut -d'|' -f1)
OWNER_CID=$(echo "$OWNER_DATA" | cut -d'|' -f2)

AGENT_DATA=$(login_user "agent@seed.com.br" "seed123") || AGENT_DATA=""
AGENT_SID=$(echo "$AGENT_DATA" | cut -d'|' -f1)
AGENT_CID=$(echo "$AGENT_DATA" | cut -d'|' -f2)

cms_req() {
    local method="$1" url="$2" sid="$3" cid="$4"; shift 4
    curl -s "${@}" -X "$method" "$url" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $sid" \
        -H "X-Company-Id: $cid"
}

PAGE_ID=""

# ---- S1: Create page ----
echo ""
echo "S1: POST /api/v1/cms/pages — create page"
SLUG="test-page-$(date +%s)"
RESP=$(cms_req POST "$API_BASE/cms/pages" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/cms_create.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Test Page\", \"slug\": \"$SLUG\", \"title\": \"Test Title\"}")
if [ "$RESP" = "201" ]; then
    PAGE_ID=$(python3 -c "import json; print(json.load(open('/tmp/cms_create.json'))['id'])" 2>/dev/null || echo "")
    _pass "POST /pages returns 201 (id=$PAGE_ID)"
else
    _fail "POST /pages" "Expected 201, got $RESP — $(cat /tmp/cms_create.json)"
fi

# ---- S2: Update metadata ----
echo ""
echo "S2: PUT /api/v1/cms/pages/:id — update metadata"
if [ -n "$PAGE_ID" ]; then
    RESP=$(cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/cms_update.json -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d '{"meta_description": "Updated description"}')
    [ "$RESP" = "200" ] && _pass "PUT /pages/:id returns 200" || _fail "PUT /pages/:id" "Expected 200, got $RESP — $(cat /tmp/cms_update.json)"
else
    _skip "S2: no PAGE_ID available"
fi

# ---- S3: State machine transitions ----
echo ""
echo "S3: State machine — draft→pending_review→published→archived→draft"
if [ -n "$PAGE_ID" ]; then
    for TRANSITION in "pending_review" "published" "archived" "draft"; do
        RESP=$(cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
            -o /tmp/cms_status.json -w "%{http_code}" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"$TRANSITION\"}")
        [ "$RESP" = "200" ] && _pass "status=$TRANSITION → 200" || _fail "status=$TRANSITION" "Expected 200, got $RESP — $(cat /tmp/cms_status.json)"
    done
else
    _skip "S3: no PAGE_ID"
fi

# ---- S4: Invalid transition draft→archived → 422 ----
echo ""
echo "S4: Invalid transition draft→archived → expect 422"
if [ -n "$PAGE_ID" ]; then
    RESP=$(cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/cms_bad_trans.json -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d '{"status": "archived"}')
    if [ "$RESP" = "422" ]; then
        _pass "draft→archived returns 422"
        ERROR_CODE=$(python3 -c "import json; print(json.load(open('/tmp/cms_bad_trans.json')).get('error',''))" 2>/dev/null || echo "")
        [ "$ERROR_CODE" = "invalid_status_transition" ] && _pass "Error=invalid_status_transition" || _fail "Error envelope" "Expected invalid_status_transition, got '$ERROR_CODE'"
    else
        _fail "draft→archived" "Expected 422, got $RESP"
    fi
else
    _skip "S4: no PAGE_ID"
fi

# ---- S5: List pages ----
echo ""
echo "S5: GET /api/v1/cms/pages — listagem sem campo content"
RESP=$(cms_req GET "$API_BASE/cms/pages" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/cms_list.json -w "%{http_code}")
if [ "$RESP" = "200" ]; then
    _pass "GET /pages returns 200"
    HAS_CONTENT=$(python3 -c "
import json
data = json.load(open('/tmp/cms_list.json'))
items = data.get('items', data if isinstance(data, list) else [])
print('yes' if any('content' in item for item in items) else 'no')
" 2>/dev/null || echo "unknown")
    [ "$HAS_CONTENT" = "no" ] && _pass "Listagem não inclui campo 'content'" || _fail "Listagem" "Campo 'content' não deveria aparecer"
else
    _fail "GET /pages" "Expected 200, got $RESP"
fi

# ---- S6: GET by id ----
echo ""
echo "S6: GET /api/v1/cms/pages/:id — com campo content"
if [ -n "$PAGE_ID" ]; then
    RESP=$(cms_req GET "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/cms_get.json -w "%{http_code}")
    if [ "$RESP" = "200" ]; then
        _pass "GET /pages/:id returns 200"
        HAS_CONTENT=$(python3 -c "import json; print('yes' if 'content' in json.load(open('/tmp/cms_get.json')) else 'no')" 2>/dev/null || echo "no")
        [ "$HAS_CONTENT" = "yes" ] && _pass "GET /:id inclui campo 'content'" || _fail "GET /:id" "Campo 'content' deveria aparecer"
    else
        _fail "GET /pages/:id" "Expected 200, got $RESP"
    fi
else
    _skip "S6: no PAGE_ID"
fi

# ---- S7: Duplicate ----
echo ""
echo "S7: POST /api/v1/cms/pages/:id/duplicate"
if [ -n "$PAGE_ID" ]; then
    RESP=$(cms_req POST "$API_BASE/cms/pages/$PAGE_ID/duplicate" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/cms_dup.json -w "%{http_code}")
    if [ "$RESP" = "201" ]; then
        DUP_ID=$(python3 -c "import json; print(json.load(open('/tmp/cms_dup.json'))['id'])" 2>/dev/null || echo "")
        _pass "POST /duplicate returns 201 (new id=$DUP_ID)"
        SLUG_DUP=$(python3 -c "import json; print(json.load(open('/tmp/cms_dup.json')).get('slug',''))" 2>/dev/null || echo "")
        echo "$SLUG_DUP" | grep -q "\-copy" && _pass "Slug do duplicate contém '-copy'" || _fail "Slug duplicate" "Esperado -copy, got '$SLUG_DUP'"
    else
        _fail "POST /duplicate" "Expected 201, got $RESP — $(cat /tmp/cms_dup.json)"
    fi
else
    _skip "S7: no PAGE_ID"
fi

# ---- S8: DELETE (soft delete) ----
echo ""
echo "S8: DELETE /api/v1/cms/pages/:id — soft delete"
if [ -n "$PAGE_ID" ]; then
    RESP=$(cms_req DELETE "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/cms_delete.json -w "%{http_code}")
    [ "$RESP" = "200" ] || [ "$RESP" = "204" ] && _pass "DELETE /pages/:id returns 200/204" || _fail "DELETE /pages/:id" "Expected 200/204, got $RESP"
else
    _skip "S8: no PAGE_ID"
fi

# ---- S9: Agent POST → 403 ----
echo ""
echo "S9: Agent POST /api/v1/cms/pages → 403"
if [ -n "$AGENT_SID" ]; then
    RESP=$(cms_req POST "$API_BASE/cms/pages" "$AGENT_SID" "$AGENT_CID" \
        -o /tmp/cms_agent_post.json -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d '{"name": "Agent Page", "slug": "agent-page-test"}')
    [ "$RESP" = "403" ] && _pass "Agent POST returns 403" || _fail "Agent POST /pages" "Expected 403, got $RESP"
else
    _skip "S9: Agent session not available"
fi

echo ""
echo "=========================================="
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "=========================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
