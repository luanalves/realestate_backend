#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S5 — Multi-tenancy isolation
# Feature 017 — Property Attachments Upload API
# Task: T020
# FRs: FR4.1, FR4.2, FR4.3
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_A_EMAIL=owner@imob-a.com OWNER_A_PASS=ownerA123 \
#   OWNER_B_EMAIL=owner@imob-b.com OWNER_B_PASS=ownerB123 \
#   OAUTH_CLIENT_ID=xxx OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_A_ID=1 PROPERTY_B_ID=2 \
#   bash integration_tests/test_us17_s5_multitenancy_isolation.sh
#
# Note: OWNER_A and OWNER_B must belong to different companies.
#       PROPERTY_A_ID must belong to company A; PROPERTY_B_ID to company B.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_A_EMAIL="${OWNER_A_EMAIL:?'OWNER_A_EMAIL is required'}"
OWNER_A_PASS="${OWNER_A_PASS:?'OWNER_A_PASS is required'}"
OWNER_B_EMAIL="${OWNER_B_EMAIL:?'OWNER_B_EMAIL is required'}"
OWNER_B_PASS="${OWNER_B_PASS:?'OWNER_B_PASS is required'}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:?'OAUTH_CLIENT_ID is required'}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:?'OAUTH_CLIENT_SECRET is required'}"
PROPERTY_A_ID="${PROPERTY_A_ID:?'PROPERTY_A_ID is required (company A property)'}"
PROPERTY_B_ID="${PROPERTY_B_ID:?'PROPERTY_B_ID is required (company B property)'}"
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

JPEG_FILE=$(mktemp /tmp/f017_mt_XXXX.jpg)
python3 -c "open('$JPEG_FILE','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')"
trap "rm -f $JPEG_FILE" EXIT

# Step 1 — Auth as Owner A
_log "Step 1: Auth as Owner A ($OWNER_A_EMAIL)"
AUTH_A=$(_two_step_auth "$OWNER_A_EMAIL" "$OWNER_A_PASS")
JWT_A=$(echo "$AUTH_A" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID_A=$(echo "$AUTH_A" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$JWT_A" ] || [ -z "$SID_A" ] && { _fail "Owner A auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Owner A auth OK"

# Step 2 — Auth as Owner B
_log "Step 2: Auth as Owner B ($OWNER_B_EMAIL)"
AUTH_B=$(_two_step_auth "$OWNER_B_EMAIL" "$OWNER_B_PASS")
JWT_B=$(echo "$AUTH_B" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID_B=$(echo "$AUTH_B" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$JWT_B" ] || [ -z "$SID_B" ] && { _fail "Owner B auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Owner B auth OK"

# Step 3 — Owner A uploads attachment on property A
_log "Step 3: Owner A uploads image on Property A (ID=$PROPERTY_A_ID)"
UP_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_A_ID/attachments" \
    -H "Authorization: Bearer $JWT_A" -H "X-Openerp-Session-Id: $SID_A" \
    -F "file=@$JPEG_FILE;type=image/jpeg" -F "attachment_type=image")
UP_CODE=$(echo "$UP_RESP" | tail -1)
UP_BODY=$(echo "$UP_RESP" | sed '$d')
_assert_code "Owner A upload on Property A" 201 "$UP_CODE"
ATT_A_ID=$(echo "$UP_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")
[ -z "$ATT_A_ID" ] && { _fail "No ATT_A_ID returned"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_log "Company A attachment ID=$ATT_A_ID on Property $PROPERTY_A_ID"

# Step 4 — Owner B tries to access Company A's property — expect 404
_log "Step 4: Owner B tries to access Property A ($PROPERTY_A_ID) — expect 404 (multi-tenancy isolation FR4.1)"
LIST_B_ON_A=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_A_ID/attachments" \
    -H "Authorization: Bearer $JWT_B" -H "X-Openerp-Session-Id: $SID_B")
LIST_B_CODE=$(echo "$LIST_B_ON_A" | tail -1)
_assert_code "Owner B cannot list attachments on Company A property" 404 "$LIST_B_CODE"

# Step 5 — Owner B tries to download Company A's attachment via attachment ID — expect 404
_log "Step 5: Owner B tries to download Company A's attachment — expect 404 (FR4.2)"
DL_B_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_A_ID/attachments/$ATT_A_ID/download" \
    -H "Authorization: Bearer $JWT_B" -H "X-Openerp-Session-Id: $SID_B")
DL_B_CODE=$(echo "$DL_B_RESP" | tail -1)
_assert_code "Owner B cannot download Company A's attachment" 404 "$DL_B_CODE"

# Step 6 — Owner B tries to delete Company A's attachment — expect 404
_log "Step 6: Owner B tries to delete Company A's attachment — expect 404 (FR4.3)"
DEL_B_RESP=$(curl -s -w "\n%{http_code}" -X DELETE \
    "$BASE_URL/api/v1/properties/$PROPERTY_A_ID/attachments/$ATT_A_ID" \
    -H "Authorization: Bearer $JWT_B" -H "X-Openerp-Session-Id: $SID_B")
DEL_B_CODE=$(echo "$DEL_B_RESP" | tail -1)
_assert_code "Owner B cannot delete Company A's attachment" 404 "$DEL_B_CODE"

# Step 7 — Owner B can upload on their own property B
_log "Step 7: Owner B uploads image on Property B ($PROPERTY_B_ID) — should succeed (201)"
UP_B_RESP=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/v1/properties/$PROPERTY_B_ID/attachments" \
    -H "Authorization: Bearer $JWT_B" -H "X-Openerp-Session-Id: $SID_B" \
    -F "file=@$JPEG_FILE;type=image/jpeg" -F "attachment_type=image")
UP_B_CODE=$(echo "$UP_B_RESP" | tail -1)
_assert_code "Owner B can upload on own property B" 201 "$UP_B_CODE"

# Step 8 — Owner A cannot see Company B's property B — expect 404
_log "Step 8: Owner A cannot access Property B ($PROPERTY_B_ID) — expect 404"
LIST_A_ON_B=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_B_ID/attachments" \
    -H "Authorization: Bearer $JWT_A" -H "X-Openerp-Session-Id: $SID_A")
LIST_A_CODE=$(echo "$LIST_A_ON_B" | tail -1)
_assert_code "Owner A cannot list attachments on Company B property" 404 "$LIST_A_CODE"

# Summary
echo ""
echo "============================================================"
echo "Feature 017 US17 S5 Multi-tenancy Isolation — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
