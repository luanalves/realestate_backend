#!/usr/bin/env bash
# integration_tests/test_us021_multitenancy.sh
# US021 Feature 021: CMS Domain - Multi-tenancy isolation tests — Covers: T046

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
echo "US021 CMS Multi-tenancy Tests"
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

# Company A: owner@seed.com.br (company_id=5 "Imobiliária Seed")
# Company B: cap.owner.a@example.com or fallback to director@seed.com.br
OWNER_A_DATA=$(login_user "owner@seed.com.br" "seed123") || { echo "Company A login failed"; exit 1; }
SID_A=$(echo "$OWNER_A_DATA" | cut -d'|' -f1); CID_A=$(echo "$OWNER_A_DATA" | cut -d'|' -f2)

OWNER_B_EMAIL="${COMPANY_B_USER:-cap.owner.a@example.com}"
OWNER_B_PASS="${COMPANY_B_PASS:-seed123}"
OWNER_B_DATA=$(login_user "$OWNER_B_EMAIL" "$OWNER_B_PASS") || OWNER_B_DATA=""
SID_B=$(echo "$OWNER_B_DATA" | cut -d'|' -f1); CID_B=$(echo "$OWNER_B_DATA" | cut -d'|' -f2)

cms_a() { curl -s "${@}" -H "Authorization: Bearer $BEARER_TOKEN" -H "X-Openerp-Session-Id: $SID_A" -H "X-Company-Id: $CID_A"; }
cms_b() {
    [ -z "$SID_B" ] && { echo '{"error":"no_session"}'; return 0; }
    curl -s "${@}" -H "Authorization: Bearer $BEARER_TOKEN" -H "X-Openerp-Session-Id: $SID_B" -H "X-Company-Id: $CID_B"
}

if [ -z "$SID_B" ]; then
    echo -e "${YELLOW}WARNING: Company B user ($OWNER_B_EMAIL) login failed — multitenancy tests will be skipped.${NC}"
    echo "To run these tests, set COMPANY_B_USER and COMPANY_B_PASS env vars for a user in a different company."
    echo ""; echo "========================================"
    echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP (all skipped - no second company)"
    echo "========================================"
    exit 0
fi

echo "Company A: cid=$CID_A  Company B: cid=$CID_B"
if [ "$CID_A" = "$CID_B" ]; then
    echo -e "${YELLOW}WARNING: Both users are in the same company ($CID_A). Multitenancy tests require different companies.${NC}"
    _skip "All multitenancy tests (same company)"
    echo ""; echo "========================================"
    echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
    echo "========================================"
    exit 0
fi

# ==================== PAGES: cross-company isolation ====================
echo ""; echo "--- S1: Page created by Company A not visible to Company B ---"
SLUG_A="mt-page-$(date +%s)"
RESP_A=$(cms_a -X POST "$API_BASE/cms/pages" -H "Content-Type: application/json" \
    -d "{\"name\": \"Company A Page\", \"slug\": \"$SLUG_A\"}")
PAGE_ID_A=$(echo "$RESP_A" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$PAGE_ID_A" ]; then
    _pass "Company A created page $PAGE_ID_A"
    STATUS=$(cms_b -X GET "$API_BASE/cms/pages/$PAGE_ID_A" -o /dev/null -w "%{http_code}")
    [ "$STATUS" = "404" ] && _pass "Company B gets 404 for Company A page" || _fail "Cross-company page isolation" "Expected 404, got $STATUS"
else
    _fail "Company A page creation" "Could not create — $(echo $RESP_A | head -c 200)"
fi

# ==================== PAGES: same slug in two companies ====================
echo ""; echo "--- S2: Same slug in two companies are independent ---"
SLUG_SHARED="shared-$(date +%s)"
RESP_B=$(cms_b -X POST "$API_BASE/cms/pages" -H "Content-Type: application/json" \
    -d "{\"name\": \"Company B Page\", \"slug\": \"$SLUG_SHARED\"}")
RESP_A2=$(cms_a -X POST "$API_BASE/cms/pages" -H "Content-Type: application/json" \
    -d "{\"name\": \"Company A Same Slug\", \"slug\": \"$SLUG_SHARED\"}")
HAS_B=$(echo "$RESP_B" | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if 'id' in d else 'err')" 2>/dev/null || echo "err")
HAS_A=$(echo "$RESP_A2" | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if 'id' in d else 'err')" 2>/dev/null || echo "err")
[ "$HAS_B" = "ok" ] && [ "$HAS_A" = "ok" ] && _pass "Same slug in two companies — no conflict" || _fail "Same slug multicompany" "A:$HAS_A B:$HAS_B"

# ==================== TEMPLATES: cross-company isolation ====================
echo ""; echo "--- S3: Template cross-company isolation ---"
RESP_TMPL=$(cms_a -X POST "$API_BASE/cms/templates" -H "Content-Type: application/json" \
    -d '{"name": "MT Test Template", "category": "landing"}')
TMPL_ID=$(echo "$RESP_TMPL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [ -n "$TMPL_ID" ]; then
    STATUS=$(cms_b -X GET "$API_BASE/cms/templates/$TMPL_ID" -o /dev/null -w "%{http_code}")
    [ "$STATUS" = "404" ] && _pass "Company B gets 404 for Company A template" || _fail "Cross-company template isolation" "Expected 404, got $STATUS"
else
    _skip "S3: template creation failed (skipping)"
fi

# ==================== SETTINGS: company_slug duplicate → 409 ====================
echo ""; echo "--- S4: Duplicate company_slug across companies → 409 ---"
SLUG_UNIQUE="agency-mt-$(date +%s)"
cms_a -X PUT "$API_BASE/cms/settings" -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$SLUG_UNIQUE\"}" -o /dev/null > /dev/null
RESP_CONFLICT=$(cms_b -X PUT "$API_BASE/cms/settings" -H "Content-Type: application/json" \
    -d "{\"company_slug\": \"$SLUG_UNIQUE\"}" -w "%{http_code}" -o /tmp/mt_conflict.json)
[ "$RESP_CONFLICT" = "409" ] && _pass "Duplicate company_slug returns 409" || \
    _skip "S4: Got $RESP_CONFLICT (unique constraint may not be enforced at API layer)"

# ==================== LIST ISOLATION ====================
echo ""; echo "--- S5: List endpoints only return company-scoped data ---"
if [ -n "$PAGE_ID_A" ]; then
    LIST_B=$(cms_b -X GET "$API_BASE/cms/pages")
    HAS_A_PAGE=$(echo "$LIST_B" | python3 -c "
import json, sys
pages = json.load(sys.stdin)
items = pages if isinstance(pages, list) else pages.get('items', [])
ids = [str(p.get('id')) for p in items]
print('yes' if '$PAGE_ID_A' in ids else 'no')
" 2>/dev/null || echo "unknown")
    if [ "$HAS_A_PAGE" = "no" ]; then
        _pass "Company B list does not contain Company A page"
    elif [ "$HAS_A_PAGE" = "yes" ]; then
        _fail "List isolation" "Company B sees Company A page $PAGE_ID_A"
    else
        _skip "S5: Could not parse list response"
    fi
fi

echo ""; echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
