#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S1 — Upload journey (image + document)
# Feature 017 — Property Attachments Upload API
# Task: T016
# FRs: FR1.1, FR1.2, FR1.3, FR1.5, FR6.9
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@imob-a.com \
#   OWNER_PASS=owner123 \
#   OAUTH_CLIENT_ID=xxx \
#   OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_ID=1 \
#   bash integration_tests/test_us17_s1_upload_journey.sh
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
PASS=0
FAIL=0

_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }

_assert_code() {
    local label="$1" expected="$2" actual="$3"
    [ "$actual" -eq "$expected" ] && _pass "$label (HTTP $actual)" || _fail "$label (expected $expected, got $actual)"
}

_assert_field() {
    local label="$1" field="$2" json="$3"
    echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in str(d)" 2>/dev/null \
        && _pass "$label — '$field' present" || _fail "$label — '$field' missing"
}

_assert_json_field() {
    local label="$1" field="$2" expected="$3" json="$4"
    local actual
    actual=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null || echo "")
    [ "$actual" = "$expected" ] && _pass "$label ($field=$expected)" || _fail "$label ($field expected '$expected', got '$actual')"
}

_two_step_auth() {
    local email="$1" pass="$2"
    local jwt
    jwt=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"$OAUTH_CLIENT_ID\",\"client_secret\":\"$OAUTH_CLIENT_SECRET\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    [ -z "$jwt" ] && echo "" && return 1
    local sid
    sid=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
        -H "Content-Type: application/json" -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    echo "{\"access_token\":\"$jwt\",\"session_id\":\"$sid\"}"
}

# Create minimal test files
JPEG_FILE=$(mktemp /tmp/f017_test_XXXX.jpg)
PDF_FILE=$(mktemp /tmp/f017_test_XXXX.pdf)
python3 -c "
import struct
# Minimal valid JPEG: SOI + APP0 + EOI
data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'
open('$JPEG_FILE', 'wb').write(data)
"
printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 2\n0000000000 65535 f\n0000000009 00000 n\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n0\n%%%%EOF\n' > "$PDF_FILE"
trap "rm -f $JPEG_FILE $PDF_FILE" EXIT

# ------------------------------------------------------------------ #
# Step 1 — Authenticate as owner                                       #
# ------------------------------------------------------------------ #
_log "Step 1: Authenticate as owner $OWNER_EMAIL"
AUTH_DATA=$(_two_step_auth "$OWNER_EMAIL" "$OWNER_PASS")
JWT_TOKEN=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

if [ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ]; then
    _fail "Auth failed — JWT or session missing"
    echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1
fi
_pass "Two-step auth OK (JWT + session)"

AUTH_HEADERS=(-H "Authorization: Bearer $JWT_TOKEN" -H "X-Openerp-Session-Id: $SESSION_ID")

# ------------------------------------------------------------------ #
# Step 2 — Upload image (201)                                          #
# ------------------------------------------------------------------ #
_log "Step 2: Upload image on property $PROPERTY_ID"
UPLOAD_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
    "${AUTH_HEADERS[@]}" \
    -F "file=@$JPEG_FILE;type=image/jpeg" \
    -F "attachment_type=image")
UPLOAD_CODE=$(echo "$UPLOAD_RESP" | tail -1)
UPLOAD_BODY=$(echo "$UPLOAD_RESP" | sed '$d')

_assert_code "POST /attachments (image)" 201 "$UPLOAD_CODE"
_assert_field "Upload image response has 'id'" "id" "$UPLOAD_BODY"
_assert_field "Upload image response has 'links'" "links" "$UPLOAD_BODY"

# Verify links.download uses /api/v1/ not /web/content/
DOWNLOAD_URL=$(echo "$UPLOAD_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
links = d.get('data', d).get('links', {})
print(links.get('download', ''))
" 2>/dev/null || echo "")
if echo "$DOWNLOAD_URL" | grep -q "/api/v1/"; then
    _pass "links.download uses /api/v1/ (FR2.4)"
else
    _fail "links.download does NOT use /api/v1/ — got: $DOWNLOAD_URL"
fi
if echo "$DOWNLOAD_URL" | grep -q "/web/content/"; then
    _fail "links.download contains /web/content/ (FR2.4 violation)"
else
    _pass "links.download does not contain /web/content/"
fi

IMAGE_ATTACHMENT_ID=$(echo "$UPLOAD_BODY" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print(d.get('data', d).get('id', ''))
" 2>/dev/null || echo "")
_log "Created image attachment ID=$IMAGE_ATTACHMENT_ID"

# ------------------------------------------------------------------ #
# Step 3 — Upload document (201)                                       #
# ------------------------------------------------------------------ #
_log "Step 3: Upload PDF document on property $PROPERTY_ID"
DOC_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
    "${AUTH_HEADERS[@]}" \
    -F "file=@$PDF_FILE;type=application/pdf" \
    -F "attachment_type=document")
DOC_CODE=$(echo "$DOC_RESP" | tail -1)
DOC_BODY=$(echo "$DOC_RESP" | sed '$d')

_assert_code "POST /attachments (document)" 201 "$DOC_CODE"
_assert_json_field "Document attachment_type is 'document'" "attachment_type" "document" "$(echo "$DOC_BODY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get("data",d)))' 2>/dev/null || echo '{}')"

# ------------------------------------------------------------------ #
# Step 4 — Verify FR6.9 error envelope: missing file                  #
# ------------------------------------------------------------------ #
_log "Step 4: Verify 400 missing_file error code"
ERR_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
    "${AUTH_HEADERS[@]}" \
    -F "attachment_type=image")
ERR_CODE=$(echo "$ERR_RESP" | tail -1)
ERR_BODY=$(echo "$ERR_RESP" | sed '$d')

_assert_code "POST /attachments missing file" 400 "$ERR_CODE"
_assert_json_field "Error code is missing_file" "error" "missing_file" "$ERR_BODY"
if echo "$ERR_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'detail' in d" 2>/dev/null; then
    _pass "Error envelope has 'detail' key (FR6.9)"
else
    _fail "Error envelope missing 'detail' key (FR6.9 violation)"
fi

# ------------------------------------------------------------------ #
# Step 5 — Verify FR6.9 error envelope: invalid attachment_type       #
# ------------------------------------------------------------------ #
_log "Step 5: Verify 400 invalid_attachment_type with 'received' field"
INVALID_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
    "${AUTH_HEADERS[@]}" \
    -F "file=@$JPEG_FILE;type=image/jpeg" \
    -F "attachment_type=video")
INVALID_CODE=$(echo "$INVALID_RESP" | tail -1)
INVALID_BODY=$(echo "$INVALID_RESP" | sed '$d')

_assert_code "POST /attachments invalid type" 400 "$INVALID_CODE"
_assert_json_field "Error code is invalid_attachment_type" "error" "invalid_attachment_type" "$INVALID_BODY"
if echo "$INVALID_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('received')=='video'" 2>/dev/null; then
    _pass "invalid_attachment_type response has 'received' field = 'video'"
else
    _fail "invalid_attachment_type response missing 'received' field"
fi

# ------------------------------------------------------------------ #
# Summary                                                              #
# ------------------------------------------------------------------ #
echo ""
echo "============================================================"
echo "Feature 017 US17 S1 Upload Journey — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
