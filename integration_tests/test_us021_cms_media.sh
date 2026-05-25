#!/usr/bin/env bash
# integration_tests/test_us021_cms_media.sh
# US021 Feature 021: CMS Domain - Media Library integration tests
# Covers: T021 (US2)

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
echo "US021 CMS Media Library Tests"
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
OWNER_SID=$(echo "$OWNER_DATA" | cut -d'|' -f1)
OWNER_CID=$(echo "$OWNER_DATA" | cut -d'|' -f2)

cms_req() {
    local method="$1" url="$2"; shift 2
    curl -s "${@}" -X "$method" "$url" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SID" \
        -H "X-Company-Id: $OWNER_CID"
}

MEDIA_ID=""

# ---- S1: Upload valid jpg ----
echo ""
echo "S1: POST /api/v1/cms/media/upload — valid jpg"
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00' > /tmp/test_valid.jpg
RESP=$(cms_req POST "$API_BASE/cms/media/upload" \
    -o /tmp/media_upload.json -w "%{http_code}" \
    -F "file=@/tmp/test_valid.jpg;type=image/jpeg" \
    -F "name=test_valid.jpg")
if [ "$RESP" = "201" ]; then
    MEDIA_ID=$(python3 -c "import json; print(json.load(open('/tmp/media_upload.json'))['id'])" 2>/dev/null || echo "")
    _pass "POST /upload returns 201"
    URL=$(python3 -c "import json; print(json.load(open('/tmp/media_upload.json')).get('url',''))" 2>/dev/null || echo "")
    [ -n "$URL" ] && _pass "Upload response includes url" || _fail "Upload url" "No 'url' in response"
else
    _fail "POST /upload" "Expected 201, got $RESP — $(cat /tmp/media_upload.json)"
fi
rm -f /tmp/test_valid.jpg

# ---- S2: Upload forbidden MIME ----
echo ""
echo "S2: POST /api/v1/cms/media/upload — MIME forbidden (text/html)"
echo "<html>test</html>" > /tmp/test_html.html
RESP=$(cms_req POST "$API_BASE/cms/media/upload" \
    -o /tmp/media_bad_mime.json -w "%{http_code}" \
    -F "file=@/tmp/test_html.html;type=text/html")
[ "$RESP" = "415" ] && _pass "text/html returns 415" || _fail "MIME forbidden" "Expected 415, got $RESP"
rm -f /tmp/test_html.html

# ---- S3: Magic bytes mismatch ----
echo ""
echo "S3: POST /api/v1/cms/media/upload — magic bytes mismatch"
printf '%%PDF-1.4 fake pdf content' > /tmp/test_mismatch.jpg
RESP=$(cms_req POST "$API_BASE/cms/media/upload" \
    -o /tmp/media_mismatch.json -w "%{http_code}" \
    -F "file=@/tmp/test_mismatch.jpg;type=image/jpeg")
if [ "$RESP" = "415" ]; then
    ERROR=$(python3 -c "import json; print(json.load(open('/tmp/media_mismatch.json')).get('error',''))" 2>/dev/null || echo "")
    _pass "mime_mismatch returns 415"
    [ "$ERROR" = "mime_mismatch" ] && _pass "Error=mime_mismatch" || _fail "Error envelope" "Expected mime_mismatch, got '$ERROR'"
else
    _fail "MIME mismatch" "Expected 415, got $RESP"
fi
rm -f /tmp/test_mismatch.jpg

# ---- S4: GET list ----
echo ""
echo "S4: GET /api/v1/cms/media — list"
RESP=$(cms_req GET "$API_BASE/cms/media" -o /tmp/media_list.json -w "%{http_code}")
[ "$RESP" = "200" ] && _pass "GET /media returns 200" || _fail "GET /media" "Expected 200, got $RESP"

# ---- S5: GET by id metadata ----
echo ""
echo "S5: GET /api/v1/cms/media/:id — metadata"
if [ -n "$MEDIA_ID" ]; then
    RESP=$(cms_req GET "$API_BASE/cms/media/$MEDIA_ID" -o /tmp/media_get.json -w "%{http_code}")
    [ "$RESP" = "200" ] && _pass "GET /media/:id returns 200" || _fail "GET /media/:id" "Expected 200, got $RESP — $(cat /tmp/media_get.json)"
else
    _skip "S5: no MEDIA_ID"
fi

# ---- S6: DELETE removes ir.attachment ----
echo ""
echo "S6: DELETE /api/v1/cms/media/:id"
if [ -n "$MEDIA_ID" ]; then
    RESP=$(cms_req DELETE "$API_BASE/cms/media/$MEDIA_ID" -o /tmp/media_delete.json -w "%{http_code}")
    if [ "$RESP" = "200" ] || [ "$RESP" = "204" ]; then
        _pass "DELETE /media/:id returns 200/204"
        RESP2=$(cms_req GET "$API_BASE/cms/media/$MEDIA_ID" -o /dev/null -w "%{http_code}")
        [ "$RESP2" = "404" ] && _pass "Deleted media returns 404" || _fail "Deleted media" "Expected 404, got $RESP2"
    else
        _fail "DELETE /media/:id" "Expected 200/204, got $RESP"
    fi
else
    _skip "S6: no MEDIA_ID"
fi

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
