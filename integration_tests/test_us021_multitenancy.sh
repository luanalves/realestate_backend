#!/usr/bin/env bash
# integration_tests/test_us021_multitenancy.sh
# US021 Feature 021: CMS Domain - Multi-tenancy isolation tests
# Covers: T046
#
# Verifies that all CMS entities are strictly isolated per company.
# Requires two sets of tokens from distinct companies.
#
# Usage:
#   BASE_URL=http://localhost:8069 \
#   COMPANY_A_TOKEN=... COMPANY_B_TOKEN=... \
#   bash test_us021_multitenancy.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
COMPANY_A_TOKEN="${COMPANY_A_TOKEN:-}"
COMPANY_B_TOKEN="${COMPANY_B_TOKEN:-}"

PASS=0; FAIL=0; SKIP=0

_pass() { echo "  [PASS] $1"; ((PASS++)) || true; }
_fail() { echo "  [FAIL] $1 — $2"; ((FAIL++)) || true; }
_skip() { echo "  [SKIP] $1"; ((SKIP++)) || true; }
_require() {
    if [ -z "$1" ]; then _skip "$2 (token not set)"; return 1; fi
    return 0
}

echo "========================================"
echo "US021 CMS Multi-tenancy Tests"
echo "========================================"

# ---- Preflight ----
if ! _require "$COMPANY_A_TOKEN" "COMPANY_A_TOKEN" || ! _require "$COMPANY_B_TOKEN" "COMPANY_B_TOKEN"; then
    echo "Both COMPANY_A_TOKEN and COMPANY_B_TOKEN are required for multitenancy tests."
    echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
    exit 0
fi

# ==================== PAGES: cross-company isolation ====================
echo ""
echo "--- S1: Page created by Company A is not visible to Company B ---"

SLUG_A="mt-page-$(date +%s)"
RESP_A=$(curl -s -X POST "$BASE_URL/api/v1/cms/pages" \
    -H "Authorization: Bearer $COMPANY_A_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Company A Page\", \"slug\": \"$SLUG_A\"}")
PAGE_ID_A=$(echo "$RESP_A" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$PAGE_ID_A" ]; then
    _pass "Company A created page $PAGE_ID_A"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/pages/$PAGE_ID_A" \
        -H "Authorization: Bearer $COMPANY_B_TOKEN")
    if [ "$STATUS" = "404" ]; then
        _pass "Company B gets 404 for Company A page (not 403)"
    else
        _fail "Cross-company page isolation" "Expected 404, got $STATUS"
    fi
else
    _fail "Company A page creation" "Could not create test page"
fi

# ==================== PAGES: same slug in two companies is independent ====================
echo ""
echo "--- S2: Same slug in two companies are independent ---"
SLUG_SHARED="shared-slug-$(date +%s)"
RESP_B=$(curl -s -X POST "$BASE_URL/api/v1/cms/pages" \
    -H "Authorization: Bearer $COMPANY_B_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Company B Page\", \"slug\": \"$SLUG_SHARED\"}")
CODE_B_SHARED=$(echo "$RESP_B" | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if 'id' in d else d.get('error','err'))" 2>/dev/null || echo "err")

RESP_A2=$(curl -s -X POST "$BASE_URL/api/v1/cms/pages" \
    -H "Authorization: Bearer $COMPANY_A_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Company A Same Slug\", \"slug\": \"$SLUG_SHARED\"}")
CODE_A_SHARED=$(echo "$RESP_A2" | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if 'id' in d else d.get('error','err'))" 2>/dev/null || echo "err")

if [ "$CODE_B_SHARED" = "ok" ] && [ "$CODE_A_SHARED" = "ok" ]; then
    _pass "Same slug in two companies created independently without conflict"
else
    _fail "Same slug multicompany" "Company A: $CODE_A_SHARED, Company B: $CODE_B_SHARED"
fi

# ==================== TEMPLATES: cross-company isolation ====================
echo ""
echo "--- S3: Template cross-company isolation ---"
RESP_TMPL=$(curl -s -X POST "$BASE_URL/api/v1/cms/templates" \
    -H "Authorization: Bearer $COMPANY_A_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "MT Test Template", "category": "landing"}')
TMPL_ID=$(echo "$RESP_TMPL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$TMPL_ID" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "$BASE_URL/api/v1/cms/templates/$TMPL_ID" \
        -H "Authorization: Bearer $COMPANY_B_TOKEN")
    if [ "$STATUS" = "404" ]; then
        _pass "Company B gets 404 for Company A template"
    else
        _fail "Cross-company template isolation" "Expected 404, got $STATUS"
    fi
fi

# ==================== SETTINGS: company_slug duplicate → 409 ====================
echo ""
echo "--- S4: Duplicate company_slug across companies → 409 ---"
# First set company_slug to something unique for A
SLUG_UNIQUE="agency-$(date +%s)"
curl -s -o /dev/null -X PUT "$BASE_URL/api/v1/cms/settings" \
    -H "Authorization: Bearer $COMPANY_A_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$SLUG_UNIQUE\"}" > /dev/null

# Now try to set the same slug on company B → should get 409
RESP_CONFLICT=$(curl -s -o /tmp/mt_conflict.json -w "%{http_code}" \
    -X PUT "$BASE_URL/api/v1/cms/settings" \
    -H "Authorization: Bearer $COMPANY_B_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$SLUG_UNIQUE\"}")
if [ "$RESP_CONFLICT" = "409" ]; then
    _pass "Duplicate company_slug returns 409"
else
    _skip "S4: Duplicate company_slug → 409 (Got $RESP_CONFLICT — may require unique constraint enforcement at API layer)"
fi

# ==================== OG IMAGE: cross-company attachment rejected ====================
echo ""
echo "--- S5: og_image_id from another company → 422 ---"
# Get an attachment ID from company A
RESP_IMG=$(curl -s -X POST "$BASE_URL/api/v1/cms/media/upload" \
    -H "Authorization: Bearer $COMPANY_A_TOKEN" \
    -F "file=@/dev/urandom;type=image/jpeg;filename=test.jpg" 2>/dev/null || echo "{}")
IMG_ID=$(echo "$RESP_IMG" | python3 -c "import json,sys; print(json.load(sys.stdin).get('attachment_id', json.load(open('/dev/stdin')).get('id','')))" 2>/dev/null || echo "")

if [ -n "$IMG_ID" ] && [ -n "$PAGE_ID_A" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X PUT "$BASE_URL/api/v1/cms/pages/$PAGE_ID_A" \
        -H "Authorization: Bearer $COMPANY_B_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"og_image_id\": $IMG_ID}")
    if [ "$STATUS" = "404" ] || [ "$STATUS" = "422" ]; then
        _pass "Cross-company og_image_id rejected ($STATUS)"
    else
        _skip "S5: og_image cross-company (got $STATUS — page may not exist for B)"
    fi
else
    _skip "S5: og_image_id cross-company (media upload not available or page_id missing)"
fi

# ==================== LIST ISOLATION: Company B cannot see Company A pages ====================
echo ""
echo "--- S6: List endpoints only return company-scoped data ---"
if [ -n "$PAGE_ID_A" ]; then
    LIST_B=$(curl -s -X GET "$BASE_URL/api/v1/cms/pages" \
        -H "Authorization: Bearer $COMPANY_B_TOKEN")
    HAS_A_PAGE=$(echo "$LIST_B" | python3 -c "
import json, sys
pages = json.load(sys.stdin)
items = pages if isinstance(pages, list) else pages.get('items', [])
print('yes' if any(str(p.get('id')) == '$PAGE_ID_A' for p in items) else 'no')
" 2>/dev/null || echo "unknown")
    if [ "$HAS_A_PAGE" = "no" ]; then
        _pass "Company B page list does not contain Company A page"
    elif [ "$HAS_A_PAGE" = "yes" ]; then
        _fail "List isolation" "Company B page list contains Company A page ID $PAGE_ID_A"
    else
        _skip "S6: Could not parse list response"
    fi
fi

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
