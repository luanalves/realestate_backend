#!/usr/bin/env bash
# integration_tests/test_us021_cms_public.sh
# US021 Feature 021: CMS Domain - Public route integration tests
# Covers: T025 (US3)
#
# Usage:
#   BASE_URL=http://localhost:8069 OWNER_TOKEN=... bash test_us021_cms_public.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"
COMPANY_SLUG="${COMPANY_SLUG:-test-agency}"

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
echo "US021 CMS Public Route Tests"
echo "========================================"

# Setup: ensure a published page exists with known slug
PAGE_SLUG="test-public-$(date +%s)"
PUBLISHED_PAGE_ID=""

if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    # Create + publish a page
    RESP=$(curl -s -o /tmp/pub_create.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Public Test Page\", \"slug\": \"$PAGE_SLUG\", \"title\": \"Public Page\"}")
    if [ "$RESP" = "201" ]; then
        PUBLISHED_PAGE_ID=$(python3 -c "import json; print(json.load(open('/tmp/pub_create.json'))['id'])" 2>/dev/null || echo "")
        # Publish it
        curl -s -o /dev/null \
            -X PUT "$BASE_URL/api/v1/cms/pages/$PUBLISHED_PAGE_ID" \
            -H "Authorization: Bearer $OWNER_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"status": "pending_review"}'
        curl -s -o /dev/null \
            -X PUT "$BASE_URL/api/v1/cms/pages/$PUBLISHED_PAGE_ID" \
            -H "Authorization: Bearer $OWNER_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"status": "published"}'
        # Set company_slug
        curl -s -o /dev/null \
            -X PUT "$BASE_URL/api/v1/cms/settings" \
            -H "Authorization: Bearer $OWNER_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"company_slug\": \"$COMPANY_SLUG\"}"
    fi
fi

# ---- S1: GET public route with valid JWT + published page ----
echo ""
echo "S1: GET /api/v1/public/cms/:slug/pages/:page_slug — valid JWT + published"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PUBLISHED_PAGE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/pub_get.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/public/cms/$COMPANY_SLUG/pages/$PAGE_SLUG" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        _pass "GET public route returns 200"
    else
        _fail "GET public" "Expected 200, got $RESP — $(cat /tmp/pub_get.json)"
    fi
fi

# ---- S2: Without JWT → 401 ----
echo ""
echo "S2: GET without JWT → 401"
RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X GET "$BASE_URL/api/v1/public/cms/$COMPANY_SLUG/pages/$PAGE_SLUG")
if [ "$RESP" = "401" ]; then
    _pass "No JWT returns 401"
else
    _fail "No JWT" "Expected 401, got $RESP"
fi

# ---- S3: Draft page → 404 ----
echo ""
echo "S3: Draft page → 404"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    DRAFT_SLUG="draft-test-$(date +%s)"
    RESP=$(curl -s -o /tmp/draft_create.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"Draft\", \"slug\": \"$DRAFT_SLUG\"}")
    if [ "$RESP" = "201" ]; then
        RESP2=$(curl -s -o /dev/null -w "%{http_code}" \
            -X GET "$BASE_URL/api/v1/public/cms/$COMPANY_SLUG/pages/$DRAFT_SLUG" \
            -H "Authorization: Bearer $OWNER_TOKEN")
        if [ "$RESP2" = "404" ]; then
            _pass "Draft page returns 404 on public route"
        else
            _fail "Draft page" "Expected 404, got $RESP2"
        fi
    fi
fi

# ---- S4: Unknown company_slug → 404 ----
echo ""
echo "S4: Unknown company_slug → 404"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    RESP=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/public/cms/nonexistent-slug-xyz/pages/home" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "404" ]; then
        _pass "Unknown company_slug returns 404"
    else
        _fail "Unknown company_slug" "Expected 404, got $RESP"
    fi
fi

# ---- S5: Verify forbidden fields absent ----
echo ""
echo "S5: Verify forbidden fields absent from public payload"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${PUBLISHED_PAGE_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/pub_fields.json -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/public/cms/$COMPANY_SLUG/pages/$PAGE_SLUG" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ]; then
        python3 - <<'EOF'
import json, sys
data = json.load(open('/tmp/pub_fields.json'))
forbidden = ['status', 'created_at', 'updated_at', 'custom_js', 'custom_css', 'company_id']
found = [f for f in forbidden if f in data]
if found:
    print(f"  [FAIL] Forbidden fields present: {found}")
    sys.exit(1)
else:
    print("  [PASS] No forbidden fields in public payload")
EOF
        if [ $? -eq 0 ]; then
            ((PASS++)) || true
        else
            ((FAIL++)) || true
        fi
    fi
fi

# Cleanup
if [ -n "${PUBLISHED_PAGE_ID:-}" ] && [ -n "$OWNER_TOKEN" ]; then
    curl -s -o /dev/null \
        -X DELETE "$BASE_URL/api/v1/cms/pages/$PUBLISHED_PAGE_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN" || true
fi

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
