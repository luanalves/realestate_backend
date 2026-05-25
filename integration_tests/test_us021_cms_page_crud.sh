#!/usr/bin/env bash
# integration_tests/test_us021_cms_page_crud.sh
# US021 - Feature 021: CMS Domain - Page CRUD + State Machine integration tests
# Covers: T016 (US1 + US4)
#
# Prerequisites:
#   - Odoo running at BASE_URL with thedevkitchen_cms installed
#   - OWNER_TOKEN, AGENT_TOKEN, MANAGER_TOKEN set as env vars or derived from login
#   - At least 2 companies: COMPANY_A_ID, COMPANY_B_ID (cross-company isolation)
#
# Usage:
#   BASE_URL=http://localhost:8069 OWNER_TOKEN=... bash test_us021_cms_page_crud.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"
AGENT_TOKEN="${AGENT_TOKEN:-}"
COMPANY_A_ID="${COMPANY_A_ID:-1}"
COMPANY_B_ID="${COMPANY_B_ID:-2}"

PASS=0
FAIL=0
SKIP=0

_pass() { echo "  [PASS] $1"; ((PASS++)) || true; }
_fail() { echo "  [FAIL] $1 — $2"; ((FAIL++)) || true; }
_skip() { echo "  [SKIP] $1 — $2"; ((SKIP++)) || true; }

_require_token() {
    if [ -z "$1" ]; then
        echo "  [SKIP] Token not available ($2)"; ((SKIP++)) || true; return 1
    fi
    return 0
}

echo "=========================================="
echo "US021 CMS Page CRUD + State Machine Tests"
echo "=========================================="

# ---- S1: Create page ----
echo ""
echo "S1: POST /api/v1/cms/pages — create page"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    SLUG="test-page-$(date +%s)"
    RESP=$(curl -s -o /tmp/cms_create.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Test Page\", \"slug\": \"$SLUG\", \"title\": \"Test Title\"}")
    if [ "$RESP" = "201" ]; then
        PAGE_ID=$(python3 -c "import json,sys; print(json.load(open('/tmp/cms_create.json'))['id'])" 2>/dev/null || echo "")
        _pass "POST /pages returns 201"
    else
        _fail "POST /pages" "Expected 201, got $RESP — $(cat /tmp/cms_create.json)"
        PAGE_ID=""
    fi
fi

# ---- S2: Update metadata ----
echo ""
echo "S2: PUT /api/v1/cms/pages/:id — update metadata"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PAGE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/cms_update.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"meta_description": "Updated description"}')
    if [ "$RESP" = "200" ]; then
        _pass "PUT /pages/:id returns 200"
    else
        _fail "PUT /pages/:id" "Expected 200, got $RESP — $(cat /tmp/cms_update.json)"
    fi
fi

# ---- S3: State machine transitions ----
echo ""
echo "S3: State machine — draft→pending_review→published→archived→draft"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PAGE_ID:-}" ]; then
    for TRANSITION in "pending_review" "published" "archived" "draft"; do
        RESP=$(curl -s -o /tmp/cms_status.json -w "%{http_code}" \
            -X PUT "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
            -H "Authorization: Bearer $OWNER_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"$TRANSITION\"}")
        if [ "$RESP" = "200" ]; then
            _pass "PUT status=$TRANSITION returns 200"
        else
            _fail "PUT status=$TRANSITION" "Expected 200, got $RESP — $(cat /tmp/cms_status.json)"
        fi
    done
fi

# ---- S4: Invalid transition ----
echo ""
echo "S4: Invalid transition draft→archived → expect 422"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PAGE_ID:-}" ]; then
    # page is back to draft (from S3)
    RESP=$(curl -s -o /tmp/cms_bad_trans.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"status": "archived"}')
    if [ "$RESP" = "422" ]; then
        _pass "draft→archived returns 422"
        # Verify error envelope
        ERROR_CODE=$(python3 -c "import json,sys; print(json.load(open('/tmp/cms_bad_trans.json')).get('error',''))" 2>/dev/null || echo "")
        if [ "$ERROR_CODE" = "invalid_status_transition" ]; then
            _pass "Error envelope has error=invalid_status_transition"
        else
            _fail "Error envelope" "Expected error=invalid_status_transition, got '$ERROR_CODE'"
        fi
    else
        _fail "draft→archived" "Expected 422, got $RESP"
    fi
fi

# ---- S5: List pages — no content field ----
echo ""
echo "S5: GET /api/v1/cms/pages — listagem sem campo content"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/cms_list.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET /pages returns 200"
        # Verify content is not in response items
        HAS_CONTENT=$(python3 -c "
import json, sys
data = json.load(open('/tmp/cms_list.json'))
items = data.get('items', data if isinstance(data, list) else [])
has = any('content' in item for item in items)
print('yes' if has else 'no')
" 2>/dev/null || echo "unknown")
        if [ "$HAS_CONTENT" = "no" ]; then
            _pass "Listagem não inclui campo 'content'"
        else
            _fail "Listagem" "Campo 'content' não deveria aparecer na listagem"
        fi
    else
        _fail "GET /pages" "Expected 200, got $RESP"
    fi
fi

# ---- S6: GET by id — with content ----
echo ""
echo "S6: GET /api/v1/cms/pages/:id — com campo content"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PAGE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/cms_get.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET /pages/:id returns 200"
        HAS_CONTENT=$(python3 -c "
import json
data = json.load(open('/tmp/cms_get.json'))
print('yes' if 'content' in data else 'no')
" 2>/dev/null || echo "unknown")
        if [ "$HAS_CONTENT" = "yes" ]; then
            _pass "GET /:id inclui campo 'content'"
        else
            _fail "GET /:id" "Campo 'content' deveria aparecer no detalhe"
        fi
    else
        _fail "GET /pages/:id" "Expected 200, got $RESP"
    fi
fi

# ---- S7: DELETE (soft delete) ----
echo ""
echo "S7: DELETE /api/v1/cms/pages/:id — soft delete"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PAGE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/cms_delete.json -w "%{http_code}" \
        -X DELETE "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ] || [ "$RESP" = "204" ]; then
        _pass "DELETE /pages/:id returns 200/204"
    else
        _fail "DELETE /pages/:id" "Expected 200/204, got $RESP — $(cat /tmp/cms_delete.json)"
    fi
fi

# ---- S8: Cross-company access → 404 ----
echo ""
echo "S8: Cross-company access → should return 404"
_skip "S8: Cross-company access" "Requires two companies with distinct tokens — configure OWNER_B_TOKEN and COMPANY_B_ID"

# ---- S9: Agent POST → 403 ----
echo ""
echo "S9: Agent POST /api/v1/cms/pages → 403"
if _require_token "$AGENT_TOKEN" "AGENT_TOKEN"; then
    RESP=$(curl -s -o /tmp/cms_agent_post.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name": "Agent Page", "slug": "agent-page-test"}')
    if [ "$RESP" = "403" ]; then
        _pass "Agent POST returns 403"
    else
        _fail "Agent POST /pages" "Expected 403, got $RESP"
    fi
else
    _skip "S9: Agent 403" "AGENT_TOKEN not set"
fi

echo ""
echo "=========================================="
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "=========================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
