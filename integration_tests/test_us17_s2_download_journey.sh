#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S2 — Download journey
# Feature 017 — Property Attachments Upload API
# Task: T017
# FRs: FR2.3, FR2.4, FR6.9
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@imob-a.com OWNER_PASS=owner123 \
#   OAUTH_CLIENT_ID=xxx OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_ID=1 \
#   bash integration_tests/test_us17_s2_download_journey.sh
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

JPEG_FILE=$(mktemp /tmp/f017_dl_XXXX.jpg)
python3 -c "open('$JPEG_FILE','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')"
trap "rm -f $JPEG_FILE" EXIT

# Step 1 — Auth
_log "Step 1: Authenticate as owner"
AUTH_DATA=$(_two_step_auth "$OWNER_EMAIL" "$OWNER_PASS")
JWT_TOKEN=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ] && { _fail "Auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Auth OK"
AUTH_HEADERS=(-H "Authorization: Bearer $JWT_TOKEN" -H "X-Openerp-Session-Id: $SESSION_ID")

# Step 2 — Upload a test image to get an attachment ID
_log "Step 2: Upload test image to get attachment ID"
UP_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
    "${AUTH_HEADERS[@]}" \
    -F "file=@$JPEG_FILE;type=image/jpeg" \
    -F "attachment_type=image")
UP_CODE=$(echo "$UP_RESP" | tail -1)
UP_BODY=$(echo "$UP_RESP" | sed '$d')
_assert_code "Upload test image" 201 "$UP_CODE"
ATT_ID=$(echo "$UP_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")
if [ -z "$ATT_ID" ]; then
    _fail "No attachment ID from upload — cannot continue download tests"
    echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1
fi
_log "Attachment ID=$ATT_ID"

# Step 3 — Download the attachment
_log "Step 3: Download attachment $ATT_ID"
DL_HEADERS_FILE=$(mktemp /tmp/f017_headers_XXXX.txt)
DL_BODY_FILE=$(mktemp /tmp/f017_body_XXXX.bin)
trap "rm -f $JPEG_FILE $DL_HEADERS_FILE $DL_BODY_FILE" EXIT

HTTP_CODE=$(curl -s -D "$DL_HEADERS_FILE" -o "$DL_BODY_FILE" -w "%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATT_ID/download" \
    "${AUTH_HEADERS[@]}")

_assert_code "GET /attachments/$ATT_ID/download" 200 "$HTTP_CODE"

# Step 4 — Verify security headers
_log "Step 4: Verify security headers (FR2.4)"
if grep -qi "Content-Security-Policy:.*default-src 'none'" "$DL_HEADERS_FILE"; then
    _pass "Content-Security-Policy: default-src 'none' present"
else
    _fail "Content-Security-Policy header missing or incorrect"
    grep -i "Content-Security-Policy" "$DL_HEADERS_FILE" || true
fi

if grep -qi "X-Content-Type-Options: nosniff" "$DL_HEADERS_FILE"; then
    _pass "X-Content-Type-Options: nosniff present"
else
    _fail "X-Content-Type-Options: nosniff missing"
fi

if grep -qi "Content-Disposition: attachment" "$DL_HEADERS_FILE"; then
    _pass "Content-Disposition: attachment present"
else
    _fail "Content-Disposition: attachment missing"
fi

# Step 5 — Verify response is binary (not a JSON redirect to /web/content/)
_log "Step 5: Verify response is binary, not a /web/content/ redirect"
if file "$DL_BODY_FILE" | grep -qi "JPEG\|image"; then
    _pass "Downloaded file is binary image data"
else
    FIRST_BYTES=$(head -c 20 "$DL_BODY_FILE" 2>/dev/null || echo "")
    if echo "$FIRST_BYTES" | grep -q "web/content"; then
        _fail "Response body contains /web/content/ redirect (FR2.4 violation)"
    else
        _pass "Response body does not contain /web/content/ redirect"
    fi
fi

# Step 6 — Verify 404 for nonexistent attachment
_log "Step 6: Verify 404 for nonexistent attachment"
NF_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/9999999/download" \
    "${AUTH_HEADERS[@]}")
NF_CODE=$(echo "$NF_RESP" | tail -1)
NF_BODY=$(echo "$NF_RESP" | sed '$d')
_assert_code "GET nonexistent attachment" 404 "$NF_CODE"
ERR_CODE_VAL=$(echo "$NF_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null || echo "")
[ "$ERR_CODE_VAL" = "not_found" ] && _pass "Error code is 'not_found'" || _fail "Error code expected 'not_found', got '$ERR_CODE_VAL'"

# Summary
echo ""
echo "============================================================"
echo "Feature 017 US17 S2 Download Journey — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
