#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S4 — List pagination
# Feature 017 — Property Attachments Upload API
# Task: T019
# FRs: FR7.1, FR7.2, FR7.3, FR7.4
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@imob-a.com OWNER_PASS=owner123 \
#   OAUTH_CLIENT_ID=xxx OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_ID=1 \
#   bash integration_tests/test_us17_s4_list_pagination.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_EMAIL="${OWNER_EMAIL:?'OWNER_EMAIL is required'}"
OWNER_PASS="${OWNER_PASS:?'OWNER_PASS is required'}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:?'OAUTH_CLIENT_ID is required'}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:?'OAUTH_CLIENT_SECRET is required'}"
PROPERTY_ID="${PROPERTY_ID:?'PROPERTY_ID is required'}"
PASS=0; FAIL=0

_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }
_assert_code() { local l="$1" e="$2" a="$3"; [ "$a" -eq "$e" ] && _pass "$l (HTTP $a)" || _fail "$l (expected $e, got $a)"; }

_two_step_auth() {
    local email="$1" pass="$2"
    local jwt; jwt=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"$OAUTH_CLIENT_ID\",\"client_secret\":\"$OAUTH_CLIENT_SECRET\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    [ -z "$jwt" ] && echo "" && return 1
    local sid; sid=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
        -H "Content-Type: application/json" -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    echo "{\"access_token\":\"$jwt\",\"session_id\":\"$sid\"}"
}

JPEG_FILE=$(mktemp /tmp/f017_list_XXXX.jpg)
PDF_FILE=$(mktemp /tmp/f017_list_XXXX.pdf)
python3 -c "open('$JPEG_FILE','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')"
printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 2\n0000000000 65535 f\n0000000009 00000 n\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n0\n%%%%EOF\n' > "$PDF_FILE"
trap "rm -f $JPEG_FILE $PDF_FILE" EXIT

# Step 1 — Auth
_log "Step 1: Authenticate as owner"
AUTH_DATA=$(_two_step_auth "$OWNER_EMAIL" "$OWNER_PASS")
JWT_TOKEN=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ] && { _fail "Auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Auth OK"
AUTH_HEADERS=(-H "Authorization: Bearer $JWT_TOKEN" -H "X-Openerp-Session-Id: $SESSION_ID")

# Step 2 — Upload 3 images to ensure total >= 3 for pagination test
_log "Step 2: Upload 3 images for pagination test"
for i in 1 2 3; do
    curl -s -X POST "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
        "${AUTH_HEADERS[@]}" -F "file=@$JPEG_FILE;type=image/jpeg" -F "attachment_type=image" > /dev/null
    _log "  Uploaded image $i"
done
_pass "Uploaded 3 images"

# Step 3 — Upload 2 documents
_log "Step 3: Upload 2 documents"
for i in 1 2; do
    curl -s -X POST "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
        "${AUTH_HEADERS[@]}" -F "file=@$PDF_FILE;type=application/pdf" -F "attachment_type=document" > /dev/null
    _log "  Uploaded document $i"
done
_pass "Uploaded 2 documents"

# Step 4 — List images with limit=1: total must be >= 3, items must be 1 (FR7.4)
_log "Step 4: List images limit=1, verify total >= 3 (search_count invariant FR7.4)"
LIST_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=image&limit=1&offset=0" \
    "${AUTH_HEADERS[@]}")
LIST_CODE=$(echo "$LIST_RESP" | tail -1)
LIST_BODY=$(echo "$LIST_RESP" | sed '$d')
_assert_code "GET /attachments?type=image&limit=1" 200 "$LIST_CODE"

PAGE_TOTAL=$(echo "$LIST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d.get('data', d)
print(data.get('pagination', {}).get('total', -1))
" 2>/dev/null || echo "-1")
PAGE_LIMIT=$(echo "$LIST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d.get('data', d)
print(data.get('pagination', {}).get('limit', -1))
" 2>/dev/null || echo "-1")
ITEMS_LEN=$(echo "$LIST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
data = d.get('data', d)
print(len(data.get('items', [])))
" 2>/dev/null || echo "-1")

[ "$PAGE_TOTAL" -ge 3 ] 2>/dev/null && _pass "pagination.total >= 3 (search_count, not page len) = $PAGE_TOTAL" || _fail "pagination.total expected >= 3, got $PAGE_TOTAL"
[ "$PAGE_LIMIT" -eq 1 ] 2>/dev/null && _pass "pagination.limit = 1" || _fail "pagination.limit expected 1, got $PAGE_LIMIT"
[ "$ITEMS_LEN" -eq 1 ] 2>/dev/null && _pass "items[] has 1 item (page size respected)" || _fail "items[] expected 1 item, got $ITEMS_LEN"

# Step 5 — Filter by attachment_type=document: items must be documents only
_log "Step 5: Filter by attachment_type=document, verify all items are documents"
DOC_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=document" \
    "${AUTH_HEADERS[@]}")
DOC_CODE=$(echo "$DOC_RESP" | tail -1)
DOC_BODY=$(echo "$DOC_RESP" | sed '$d')
_assert_code "GET /attachments?type=document" 200 "$DOC_CODE"
ALL_DOCS=$(echo "$DOC_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', d).get('items', [])
bad = [i.get('attachment_type') for i in items if i.get('attachment_type') != 'document']
print(len(bad))
" 2>/dev/null || echo "-1")
[ "$ALL_DOCS" -eq 0 ] && _pass "All filtered items are 'document'" || _fail "Some items are not 'document' type"

DOC_TOTAL=$(echo "$DOC_BODY" | python3 -c "
import sys, json; d=json.load(sys.stdin)
print(d.get('data',d).get('pagination',{}).get('total',-1))
" 2>/dev/null || echo "-1")
[ "$DOC_TOTAL" -ge 2 ] 2>/dev/null && _pass "document total >= 2" || _fail "document total expected >= 2, got $DOC_TOTAL"

# Step 6 — Pagination: offset=1 returns different page
_log "Step 6: Verify offset pagination (page 1 != page 2)"
PAGE1_RESP=$(curl -s "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=image&limit=1&offset=0" "${AUTH_HEADERS[@]}")
PAGE2_RESP=$(curl -s "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=image&limit=1&offset=1" "${AUTH_HEADERS[@]}")
ID1=$(echo "$PAGE1_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',d).get('items',[]); print(items[0].get('id','') if items else '')" 2>/dev/null || echo "")
ID2=$(echo "$PAGE2_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('data',d).get('items',[]); print(items[0].get('id','') if items else '')" 2>/dev/null || echo "")
if [ -n "$ID1" ] && [ -n "$ID2" ] && [ "$ID1" != "$ID2" ]; then
    _pass "offset=0 and offset=1 return different records ($ID1 vs $ID2)"
else
    _fail "Pagination offset not working correctly (ID1=$ID1, ID2=$ID2)"
fi

# Step 7 — Pagination structure has total + limit + offset fields
_log "Step 7: Verify pagination structure has required fields"
STRUCT_CHECK=$(echo "$LIST_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
pag = d.get('data', d).get('pagination', {})
missing = [f for f in ('total', 'limit', 'offset') if f not in pag]
print(','.join(missing) if missing else 'OK')
" 2>/dev/null || echo "parse_error")
[ "$STRUCT_CHECK" = "OK" ] && _pass "pagination has total + limit + offset" || _fail "pagination missing fields: $STRUCT_CHECK"

# Summary
echo ""
echo "============================================================"
echo "Feature 017 US17 S4 List Pagination — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
