#!/usr/bin/env bash
# integration_tests/test_us021_rbac_matrix.sh
# US021 Feature 021: CMS Domain - RBAC Matrix integration tests
# Covers: T045
#
# Tests all role × endpoint combinations for the CMS domain.
# Verifies: 200/201 for granted permissions, 403 for denied.
# Restricted roles (receptionist, prospector, property_owner, portal) → 403 on all.
#
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_TOKEN=... DIRECTOR_TOKEN=... MANAGER_TOKEN=... AGENT_TOKEN=... \
#   RECEPTIONIST_TOKEN=... PROSPECTOR_TOKEN=... PROPERTY_OWNER_TOKEN=... PORTAL_TOKEN=... \
#   bash test_us021_rbac_matrix.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"

PASS=0; FAIL=0; SKIP=0

_pass() { echo "  [PASS] $1"; ((PASS++)) || true; }
_fail() { echo "  [FAIL] $1"; ((FAIL++)) || true; }
_skip() { echo "  [SKIP] $1"; ((SKIP++)) || true; }

_check() {
    local label="$1" token="$2" method="$3" url="$4" expected="$5"
    shift 5
    if [ -z "$token" ]; then _skip "$label (token not set)"; return; fi
    local resp
    resp=$(curl -s -o /dev/null -w "%{http_code}" \
        -X "$method" "$BASE_URL$url" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        "$@")
    if [ "$resp" = "$expected" ]; then
        _pass "$label → $resp"
    else
        _fail "$label → expected $expected, got $resp"
    fi
}

echo "========================================"
echo "US021 CMS RBAC Matrix Tests"
echo "========================================"

# ---- Create a test page as owner for read/update/delete tests ----
PAGE_ID=""
if [ -n "${OWNER_TOKEN:-}" ]; then
    SLUG="rbac-test-$(date +%s)"
    RESP_BODY=$(curl -s -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"RBAC Test Page\", \"slug\": \"$SLUG\"}")
    PAGE_ID=$(echo "$RESP_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
fi

TEMPLATE_ID=""
if [ -n "${OWNER_TOKEN:-}" ]; then
    RESP_BODY=$(curl -s -X POST "$BASE_URL/api/v1/cms/templates" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name": "RBAC Test Template", "category": "landing"}')
    TEMPLATE_ID=$(echo "$RESP_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
fi

# ==================== PAGES ====================
echo ""
echo "--- Pages ---"

_check "owner  POST /cms/pages" "${OWNER_TOKEN:-}" POST /api/v1/cms/pages 201 \
    -d "{\"name\": \"Owner Page\", \"slug\": \"owner-$(date +%s%N)\"}"
_check "director POST /cms/pages" "${DIRECTOR_TOKEN:-}" POST /api/v1/cms/pages 201 \
    -d "{\"name\": \"Dir Page\", \"slug\": \"dir-$(date +%s%N)\"}"
_check "manager POST /cms/pages" "${MANAGER_TOKEN:-}" POST /api/v1/cms/pages 201 \
    -d "{\"name\": \"Mgr Page\", \"slug\": \"mgr-$(date +%s%N)\"}"
_check "agent  POST /cms/pages → 403" "${AGENT_TOKEN:-}" POST /api/v1/cms/pages 403 \
    -d "{\"name\": \"Agent Page\", \"slug\": \"agt-$(date +%s%N)\"}"

_check "owner  GET /cms/pages" "${OWNER_TOKEN:-}" GET /api/v1/cms/pages 200
_check "director GET /cms/pages" "${DIRECTOR_TOKEN:-}" GET /api/v1/cms/pages 200
_check "manager GET /cms/pages" "${MANAGER_TOKEN:-}" GET /api/v1/cms/pages 200
_check "agent  GET /cms/pages" "${AGENT_TOKEN:-}" GET /api/v1/cms/pages 200

if [ -n "$PAGE_ID" ]; then
    _check "owner  GET /cms/pages/:id" "${OWNER_TOKEN:-}" GET "/api/v1/cms/pages/$PAGE_ID" 200
    _check "agent  GET /cms/pages/:id" "${AGENT_TOKEN:-}" GET "/api/v1/cms/pages/$PAGE_ID" 200
    _check "owner  PUT /cms/pages/:id" "${OWNER_TOKEN:-}" PUT "/api/v1/cms/pages/$PAGE_ID" 200 \
        -d '{"title": "Updated"}'
    _check "agent  PUT /cms/pages/:id → 403" "${AGENT_TOKEN:-}" PUT "/api/v1/cms/pages/$PAGE_ID" 403 \
        -d '{"title": "Hacked"}'
fi

# ==================== TEMPLATES ====================
echo ""
echo "--- Templates ---"

_check "owner   POST /cms/templates" "${OWNER_TOKEN:-}" POST /api/v1/cms/templates 201 \
    -d "{\"name\": \"OTmpl-$(date +%s%N)\", \"category\": \"landing\"}"
_check "manager POST /cms/templates" "${MANAGER_TOKEN:-}" POST /api/v1/cms/templates 201 \
    -d "{\"name\": \"MTmpl-$(date +%s%N)\", \"category\": \"about\"}"
_check "agent   POST /cms/templates → 403" "${AGENT_TOKEN:-}" POST /api/v1/cms/templates 403 \
    -d "{\"name\": \"ATmpl-$(date +%s%N)\", \"category\": \"landing\"}"

_check "owner   GET /cms/templates" "${OWNER_TOKEN:-}" GET /api/v1/cms/templates 200
_check "agent   GET /cms/templates → 403" "${AGENT_TOKEN:-}" GET /api/v1/cms/templates 403

if [ -n "$TEMPLATE_ID" ]; then
    _check "owner   GET /cms/templates/:id" "${OWNER_TOKEN:-}" GET "/api/v1/cms/templates/$TEMPLATE_ID" 200
    _check "agent   GET /cms/templates/:id → 403" "${AGENT_TOKEN:-}" GET "/api/v1/cms/templates/$TEMPLATE_ID" 403
fi

# ==================== MEDIA ====================
echo ""
echo "--- Media ---"
_check "owner   GET /cms/media" "${OWNER_TOKEN:-}" GET /api/v1/cms/media 200
_check "agent   GET /cms/media" "${AGENT_TOKEN:-}" GET /api/v1/cms/media 200
_check "manager GET /cms/media" "${MANAGER_TOKEN:-}" GET /api/v1/cms/media 200

# ==================== SETTINGS ====================
echo ""
echo "--- Settings ---"
_check "owner   GET /cms/settings" "${OWNER_TOKEN:-}" GET /api/v1/cms/settings 200
_check "director GET /cms/settings" "${DIRECTOR_TOKEN:-}" GET /api/v1/cms/settings 200
_check "manager GET /cms/settings" "${MANAGER_TOKEN:-}" GET /api/v1/cms/settings 200
_check "agent   GET /cms/settings → 403" "${AGENT_TOKEN:-}" GET /api/v1/cms/settings 403

_check "owner   PUT /cms/settings" "${OWNER_TOKEN:-}" PUT /api/v1/cms/settings 200 \
    -d '{"og_default_title": "Test"}'
_check "agent   PUT /cms/settings → 403" "${AGENT_TOKEN:-}" PUT /api/v1/cms/settings 403 \
    -d '{"og_default_title": "Hacked"}'

# ==================== RESTRICTED ROLES: ALL MUST 403 ====================
echo ""
echo "--- Restricted roles (receptionist, prospector, property_owner, portal) ---"

for ROLE_LABEL in "receptionist:${RECEPTIONIST_TOKEN:-}" "prospector:${PROSPECTOR_TOKEN:-}" "property_owner:${PROPERTY_OWNER_TOKEN:-}" "portal:${PORTAL_TOKEN:-}"; do
    ROLE="${ROLE_LABEL%%:*}"
    TOKEN="${ROLE_LABEL##*:}"
    _check "$ROLE GET /cms/pages → 403" "$TOKEN" GET /api/v1/cms/pages 403
    _check "$ROLE GET /cms/media → 403" "$TOKEN" GET /api/v1/cms/media 403
    _check "$ROLE GET /cms/settings → 403" "$TOKEN" GET /api/v1/cms/settings 403
    _check "$ROLE GET /cms/templates → 403" "$TOKEN" GET /api/v1/cms/templates 403
done

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
