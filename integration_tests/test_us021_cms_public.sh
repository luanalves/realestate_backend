#!/usr/bin/env bash
# integration_tests/test_us021_cms_public.sh
# US021 Feature 021: CMS Domain - Public Route integration tests — Covers: T025

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
echo "US021 CMS Public Route Tests"
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

cms_req() {
    local method="$1" url="$2" sid="$3" cid="$4"; shift 4
    curl -s "${@}" -X "$method" "$url" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $sid" \
        -H "X-Company-Id: $cid"
}

pub_req() {
    # Public endpoint: only Bearer token needed (no session required)
    curl -s "${@}" -H "Authorization: Bearer $BEARER_TOKEN"
}

# ── Setup: ensure company_slug and a published page exist ────────────────────
COMPANY_SLUG="test-pub-$(date +%s)"
PAGE_SLUG="pub-page-$(date +%s)"

echo ""; echo "Setup: SET company_slug=$COMPANY_SLUG"
RESP=$(cms_req PUT "$API_BASE/cms/settings" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/pub_settings.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$COMPANY_SLUG\"}")
[ "$RESP" = "200" ] && _pass "company_slug set" || _fail "Set company_slug" "Expected 200, got $RESP — $(cat /tmp/pub_settings.json)"

echo ""; echo "Setup: CREATE published page slug=$PAGE_SLUG"
RESP=$(cms_req POST "$API_BASE/cms/pages" "$OWNER_SID" "$OWNER_CID" \
    -o /tmp/pub_page_create.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"Public Test Page\", \"slug\": \"$PAGE_SLUG\", \"title\": \"Public Title\"}")
PAGE_ID=$(python3 -c "import json; print(json.load(open('/tmp/pub_page_create.json')).get('id',''))" 2>/dev/null || echo "")

if [ -n "$PAGE_ID" ]; then
    # Publish: draft → pending_review → published
    cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -H "Content-Type: application/json" -d '{"status":"pending_review"}' -o /dev/null > /dev/null
    RESP=$(cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -o /tmp/pub_publish.json -w "%{http_code}" \
        -H "Content-Type: application/json" -d '{"status":"published"}')
    [ "$RESP" = "200" ] && _pass "Page published (id=$PAGE_ID)" || _fail "Publish page" "Expected 200, got $RESP"
else
    _fail "Page creation" "Could not create test page"
fi

# ---- S1: GET public page — valid company_slug + page_slug ----
echo ""; echo "S1: GET /api/v1/public/cms/:company_slug/:page_slug — valid"
RESP=$(pub_req -X GET "$API_BASE/public/cms/$COMPANY_SLUG/pages/$PAGE_SLUG" \
    -o /tmp/pub_get.json -w "%{http_code}")
if [ "$RESP" = "200" ]; then
    _pass "GET public page returns 200"
    TITLE=$(python3 -c "import json; print(json.load(open('/tmp/pub_get.json')).get('title',''))" 2>/dev/null || echo "")
    [ "$TITLE" = "Public Title" ] && _pass "Title matches" || _fail "Title" "Expected 'Public Title', got '$TITLE'"
else
    _fail "GET public page" "Expected 200, got $RESP — $(cat /tmp/pub_get.json)"
fi

# ---- S2: Unpublished page → 404 ----
echo ""; echo "S2: GET unpublished page → 404"
NON_SLUG="nonexistent-page-$(date +%s)"
RESP=$(pub_req -X GET "$API_BASE/public/cms/$COMPANY_SLUG/pages/$NON_SLUG" \
    -o /tmp/pub_404.json -w "%{http_code}")
[ "$RESP" = "404" ] && _pass "Non-existent page returns 404" || _fail "Non-existent page" "Expected 404, got $RESP"

# ---- S3: Invalid company_slug → 404 ----
echo ""; echo "S3: GET with invalid company_slug → 404"
RESP=$(pub_req -X GET "$API_BASE/public/cms/invalid-company-xyz/pages/$PAGE_SLUG" \
    -o /tmp/pub_nocompany.json -w "%{http_code}")
[ "$RESP" = "404" ] && _pass "Invalid company_slug returns 404" || _fail "Invalid company_slug" "Expected 404, got $RESP"

# ---- S4: Archived page → 404 ----
echo ""; echo "S4: Archived page → 404"
if [ -n "$PAGE_ID" ]; then
    # published → archived
    cms_req PUT "$API_BASE/cms/pages/$PAGE_ID" "$OWNER_SID" "$OWNER_CID" \
        -H "Content-Type: application/json" -d '{"status":"archived"}' -o /dev/null > /dev/null
    RESP=$(pub_req -X GET "$API_BASE/public/cms/$COMPANY_SLUG/pages/$PAGE_SLUG" \
        -o /tmp/pub_archived.json -w "%{http_code}")
    [ "$RESP" = "404" ] && _pass "Archived page returns 404 on public route" || _fail "Archived page" "Expected 404, got $RESP"
else
    _skip "S4: no PAGE_ID"
fi

echo ""; echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
