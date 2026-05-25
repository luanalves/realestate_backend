#!/usr/bin/env bash
# integration_tests/test_us021_cms_templates.sh
# US021 Feature 021: CMS Domain - Templates integration tests
# Covers: T027 (US5)
#
# Usage:
#   BASE_URL=http://localhost:8069 OWNER_TOKEN=... AGENT_TOKEN=... bash test_us021_cms_templates.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"
AGENT_TOKEN="${AGENT_TOKEN:-}"

PASS=0
FAIL=0
SKIP=0

_pass() { echo "  [PASS] $1"; ((PASS++)) || true; }
_fail() { echo "  [FAIL] $1 — $2"; ((FAIL++)) || true; }
_skip() { echo "  [SKIP] $1 — $2"; ((SKIP++)) || true; }
_require_token() {
    if [ -z "$1" ]; then echo "  [SKIP] Token not available ($2)"; ((SKIP++)) || true; return 1; fi
    return 0
}

echo "========================================"
echo "US021 CMS Templates Tests"
echo "========================================"

TEMPLATE_ID=""
SLUG="from-template-$(date +%s)"

# ---- S1: Create template ----
echo ""
echo "S1: POST /api/v1/cms/templates — create"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/tpl_create.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/templates" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name": "Landing Test Template", "category": "landing", "content": "{\"type\":\"landing\"}"}')
    if [ "$RESP" = "201" ]; then
        TEMPLATE_ID=$(python3 -c "import json; print(json.load(open('/tmp/tpl_create.json'))['id'])" 2>/dev/null || echo "")
        _pass "POST /templates returns 201"
    else
        _fail "POST /templates" "Expected 201, got $RESP — $(cat /tmp/tpl_create.json)"
    fi
fi

# ---- S2: List templates (no content) ----
echo ""
echo "S2: GET /api/v1/cms/templates — listagem sem content"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/tpl_list.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/templates" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET /templates returns 200"
        HAS_CONTENT=$(python3 -c "
import json
data = json.load(open('/tmp/tpl_list.json'))
items = data.get('items', [])
print('yes' if any('content' in i for i in items) else 'no')
" 2>/dev/null || echo "unknown")
        if [ "$HAS_CONTENT" = "no" ]; then
            _pass "Listagem n\u00e3o inclui campo 'content'"
        else
            _fail "Listagem" "Campo 'content' n\u00e3o deveria aparecer"
        fi
    else
        _fail "GET /templates" "Expected 200, got $RESP"
    fi
fi

# ---- S3: GET template/:id with content ----
echo ""
echo "S3: GET /api/v1/cms/templates/:id — com content"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${TEMPLATE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/tpl_get.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/templates/$TEMPLATE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET /templates/:id returns 200"
        HAS_CONTENT=$(python3 -c "
import json
data = json.load(open('/tmp/tpl_get.json'))
print('yes' if 'content' in data else 'no')
" 2>/dev/null || echo "unknown")
        if [ "$HAS_CONTENT" = "yes" ]; then
            _pass "GET /:id inclui campo 'content'"
        else
            _fail "GET /:id" "Campo 'content' deveria aparecer no detalhe"
        fi
    else
        _fail "GET /templates/:id" "Expected 200, got $RESP — $(cat /tmp/tpl_get.json)"
    fi
fi

# ---- S4: Create page from template ----
echo ""
echo "S4: POST /api/v1/cms/pages com template_id — content copiado"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${TEMPLATE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/page_from_tpl.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"From Template Page\", \"slug\": \"$SLUG\", \"template_id\": $TEMPLATE_ID}")
    if [ "$RESP" = "201" ]; then
        PAGE_ID=$(python3 -c "import json; print(json.load(open('/tmp/page_from_tpl.json'))['id'])" 2>/dev/null || echo "")
        _pass "POST /pages com template_id returns 201"
        # Verify content was copied
        RESP2=$(curl -s -o /tmp/page_content_check.json -w "%{http_code}" \
            -X GET "$BASE_URL/api/v1/cms/pages/$PAGE_ID" \
            -H "Authorization: Bearer $OWNER_TOKEN")
        if [ "$RESP2" = "200" ]; then
            CONTENT=$(python3 -c "import json; print(json.load(open('/tmp/page_content_check.json')).get('content',''))" 2>/dev/null || echo "")
            if echo "$CONTENT" | python3 -c "import json,sys; json.loads(sys.stdin.read()); sys.exit(0)" 2>/dev/null; then
                _pass "Content da p\u00e1gina \u00e9 JSON v\u00e1lido (copiado do template)"
            else
                _fail "Content" "Content n\u00e3o parece ter sido copiado do template"
            fi
        fi
    else
        _fail "POST /pages com template_id" "Expected 201, got $RESP — $(cat /tmp/page_from_tpl.json)"
        PAGE_ID=""
    fi
fi

# ---- S5: Create page with template from another company → 422 ----
_skip "S5: template_id de outra imobili\u00e1ria → 422" "Requires two companies"

# ---- S6: Agent GET /templates → 403 ----
echo ""
echo "S6: Agent GET /api/v1/cms/templates → 403"
if _require_token "$AGENT_TOKEN" "AGENT_TOKEN"; then
    RESP=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/templates" \
        -H "Authorization: Bearer $AGENT_TOKEN")
    if [ "$RESP" = "403" ]; then
        _pass "Agent GET /templates returns 403"
    else
        _fail "Agent GET /templates" "Expected 403, got $RESP"
    fi
fi

# ---- S7: DELETE template ----
echo ""
echo "S7: DELETE /api/v1/cms/templates/:id"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${TEMPLATE_ID:-}" ]; then
    RESP=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "$BASE_URL/api/v1/cms/templates/$TEMPLATE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ] || [ "$RESP" = "204" ]; then
        _pass "DELETE /templates/:id returns 200/204"
    else
        _fail "DELETE /templates/:id" "Expected 200/204, got $RESP"
    fi
fi

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
