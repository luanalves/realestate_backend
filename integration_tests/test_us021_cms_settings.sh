#!/usr/bin/env bash
# integration_tests/test_us021_cms_settings.sh
# US021 Feature 021: CMS Domain - Settings integration tests
# Covers: T031 (US6)
#
# Usage:
#   BASE_URL=http://localhost:8069 OWNER_TOKEN=... MANAGER_TOKEN=... bash test_us021_cms_settings.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"
MANAGER_TOKEN="${MANAGER_TOKEN:-}"

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
echo "US021 CMS Settings Tests"
echo "========================================"

# ---- S1: GET settings — auto-creation singleton ----
echo ""
echo "S1: GET /api/v1/cms/settings — auto-criação singleton"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_get.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET /settings returns 200"
        # Second call should return same record (singleton)
        RESP2=$(curl -s -o /tmp/settings_get2.json -w "%{http_code}" \
            -X GET "$BASE_URL/api/v1/cms/settings" \
            -H "Authorization: Bearer $OWNER_TOKEN")
        if [ "$RESP2" = "200" ]; then
            ID1=$(python3 -c "import json; print(json.load(open('/tmp/settings_get.json')).get('id',''))" 2>/dev/null || echo "")
            ID2=$(python3 -c "import json; print(json.load(open('/tmp/settings_get2.json')).get('id',''))" 2>/dev/null || echo "")
            if [ "$ID1" = "$ID2" ] && [ -n "$ID1" ]; then
                _pass "Singleton retorna mesmo id em duas chamadas ($ID1)"
            else
                _fail "Singleton" "IDs diferentes: $ID1 vs $ID2"
            fi
        fi
    else
        _fail "GET /settings" "Expected 200, got $RESP — $(cat /tmp/settings_get.json)"
    fi
fi

# ---- S2: PUT company_slug válido ----
echo ""
echo "S2: PUT /api/v1/cms/settings — company_slug válido"
SLUG="test-agency-$(date +%s)"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_put.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"company_slug\": \"$SLUG\"}")
    if [ "$RESP" = "200" ]; then
        _pass "PUT company_slug returns 200"
    else
        _fail "PUT company_slug" "Expected 200, got $RESP — $(cat /tmp/settings_put.json)"
    fi
fi

# ---- S3: CSS injection → 422 ----
echo ""
echo "S3: PUT custom_css com CSS injection → 422"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_css.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"custom_css": "body { width: expression(alert(1)) }"}')
    if [ "$RESP" = "422" ]; then
        ERROR=$(python3 -c "import json; print(json.load(open('/tmp/settings_css.json')).get('error',''))" 2>/dev/null || echo "")
        _pass "CSS injection returns 422"
        if [ "$ERROR" = "css_injection_detected" ]; then
            _pass "Error envelope has css_injection_detected"
        else
            _fail "Error envelope" "Expected css_injection_detected, got '$ERROR'"
        fi
    else
        _fail "CSS injection" "Expected 422, got $RESP"
    fi
fi

# ---- S4: custom_js by manager → 403 ----
echo ""
echo "S4: PUT custom_js por manager → 403"
if _require_token "$MANAGER_TOKEN" "MANAGER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_js_mgr.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"custom_js": "console.log(\"test\")"}')
    if [ "$RESP" = "403" ]; then
        _pass "Manager PUT custom_js returns 403"
    else
        _fail "Manager custom_js" "Expected 403, got $RESP"
    fi
else
    _skip "S4: Manager custom_js 403" "MANAGER_TOKEN not set"
fi

# ---- S5: custom_js by owner → 200 + audit fields ----
echo ""
echo "S5: PUT custom_js por owner → 200 com audit fields"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_js_own.json -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"custom_js": "console.log(\"ok\")"}')
    if [ "$RESP" = "200" ]; then
        _pass "Owner PUT custom_js returns 200"
        AUDIT_BY=$(python3 -c "import json; print(json.load(open('/tmp/settings_js_own.json')).get('custom_js_last_modified_by',''))" 2>/dev/null || echo "")
        AUDIT_AT=$(python3 -c "import json; print(json.load(open('/tmp/settings_js_own.json')).get('custom_js_last_modified_at',''))" 2>/dev/null || echo "")
        if [ -n "$AUDIT_BY" ] && [ "$AUDIT_BY" != "None" ]; then
            _pass "custom_js_last_modified_by preenchido"
        else
            _fail "Audit by" "custom_js_last_modified_by deveria ser preenchido"
        fi
        if [ -n "$AUDIT_AT" ] && [ "$AUDIT_AT" != "None" ]; then
            _pass "custom_js_last_modified_at preenchido"
        else
            _fail "Audit at" "custom_js_last_modified_at deveria ser preenchido"
        fi
    else
        _fail "Owner custom_js" "Expected 200, got $RESP — $(cat /tmp/settings_js_own.json)"
    fi
fi

# ---- S6: GET by manager — custom_js ausente ----
echo ""
echo "S6: GET settings por manager — custom_js ausente"
if _require_token "$MANAGER_TOKEN" "MANAGER_TOKEN"; then
    RESP=$(curl -s -o /tmp/settings_mgr_get.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/settings" \
        -H "Authorization: Bearer $MANAGER_TOKEN")
    if [ "$RESP" = "200" ]; then
        HAS_JS=$(python3 -c "import json; print('yes' if 'custom_js' in json.load(open('/tmp/settings_mgr_get.json')) else 'no')" 2>/dev/null || echo "unknown")
        if [ "$HAS_JS" = "no" ]; then
            _pass "Manager GET settings não inclui custom_js"
        else
            _fail "Manager GET settings" "custom_js não deveria estar presente para manager"
        fi
    fi
else
    _skip "S6: Manager GET" "MANAGER_TOKEN not set"
fi

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
