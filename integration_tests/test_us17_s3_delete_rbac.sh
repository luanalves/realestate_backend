#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S3 — Delete RBAC
# Feature 017 — Property Attachments Upload API
# Task: T018
# FRs: FR3.1, FR3.2, FR3.3
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@imob-a.com OWNER_PASS=owner123 \
#   AGENT_EMAIL=agent@imob-a.com AGENT_PASS=agent123 \
#   OAUTH_CLIENT_ID=xxx OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_ID=1 \
#   bash integration_tests/test_us17_s3_delete_rbac.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_EMAIL="${OWNER_EMAIL:?'OWNER_EMAIL is required'}"
OWNER_PASS="${OWNER_PASS:?'OWNER_PASS is required'}"
AGENT_EMAIL="${AGENT_EMAIL:?'AGENT_EMAIL is required'}"
AGENT_PASS="${AGENT_PASS:?'AGENT_PASS is required'}"
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

_upload_image() {
    local jwt="$1" sid="$2" file="$3"
    curl -s -X POST "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
        -H "Authorization: Bearer $jwt" -H "X-Openerp-Session-Id: $sid" \
        -F "file=@$file;type=image/jpeg" -F "attachment_type=image"
}

JPEG_FILE=$(mktemp /tmp/f017_del_XXXX.jpg)
python3 -c "open('$JPEG_FILE','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')"
trap "rm -f $JPEG_FILE" EXIT

# Step 1 — Auth as owner (manager-level)
_log "Step 1: Authenticate as owner $OWNER_EMAIL"
OWNER_DATA=$(_two_step_auth "$OWNER_EMAIL" "$OWNER_PASS")
OWNER_JWT=$(echo "$OWNER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
OWNER_SID=$(echo "$OWNER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$OWNER_JWT" ] || [ -z "$OWNER_SID" ] && { _fail "Owner auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Owner auth OK"

# Step 2 — Auth as agent
_log "Step 2: Authenticate as agent $AGENT_EMAIL"
AGENT_DATA=$(_two_step_auth "$AGENT_EMAIL" "$AGENT_PASS")
AGENT_JWT=$(echo "$AGENT_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
AGENT_SID=$(echo "$AGENT_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$AGENT_JWT" ] || [ -z "$AGENT_SID" ] && { _fail "Agent auth failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_pass "Agent auth OK"

# Step 3 — Owner uploads image to be tested
_log "Step 3: Owner uploads image to prepare delete test"
UP_BODY=$(_upload_image "$OWNER_JWT" "$OWNER_SID" "$JPEG_FILE")
ATT_ID=$(echo "$UP_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")
[ -z "$ATT_ID" ] && { _fail "Upload failed, no ATT_ID"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_log "Uploaded attachment ID=$ATT_ID"

# Step 4 — Agent tries to DELETE → expect 403
_log "Step 4: Agent tries to delete attachment $ATT_ID (expect 403 forbidden)"
AGENT_DEL_RESP=$(curl -s -w "\n%{http_code}" -X DELETE \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATT_ID" \
    -H "Authorization: Bearer $AGENT_JWT" -H "X-Openerp-Session-Id: $AGENT_SID")
AGENT_DEL_CODE=$(echo "$AGENT_DEL_RESP" | tail -1)
AGENT_DEL_BODY=$(echo "$AGENT_DEL_RESP" | sed '$d')
_assert_code "DELETE by agent" 403 "$AGENT_DEL_CODE"
ERR_VAL=$(echo "$AGENT_DEL_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null || echo "")
[ "$ERR_VAL" = "forbidden" ] && _pass "error='forbidden' in agent delete response" || _fail "Expected error='forbidden', got '$ERR_VAL'"

# Step 5 — Verify attachment still exists after failed delete
_log "Step 5: Verify attachment still exists after agent's failed delete attempt"
EXIST_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATT_ID/download" \
    -H "Authorization: Bearer $OWNER_JWT" -H "X-Openerp-Session-Id: $OWNER_SID")
EXIST_CODE=$(echo "$EXIST_RESP" | tail -1)
_assert_code "Attachment still exists after forbidden delete" 200 "$EXIST_CODE"

# Step 6 — Owner uploads a second image for the successful delete test
_log "Step 6: Owner uploads second image for successful delete"
UP_BODY2=$(_upload_image "$OWNER_JWT" "$OWNER_SID" "$JPEG_FILE")
ATT_ID2=$(echo "$UP_BODY2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")
[ -z "$ATT_ID2" ] && { _fail "Second upload failed"; echo "Results: PASS=$PASS FAIL=$FAIL"; exit 1; }
_log "Second attachment ID=$ATT_ID2"

# Step 7 — Owner deletes the second image → expect 204
_log "Step 7: Owner deletes attachment $ATT_ID2 (expect 204)"
DEL_RESP=$(curl -s -w "\n%{http_code}" -X DELETE \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATT_ID2" \
    -H "Authorization: Bearer $OWNER_JWT" -H "X-Openerp-Session-Id: $OWNER_SID")
DEL_CODE=$(echo "$DEL_RESP" | tail -1)
_assert_code "DELETE by owner" 204 "$DEL_CODE"

# Step 8 — Verify deleted attachment is gone (404)
_log "Step 8: Verify deleted attachment is gone (404)"
GONE_RESP=$(curl -s -w "\n%{http_code}" \
    "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATT_ID2/download" \
    -H "Authorization: Bearer $OWNER_JWT" -H "X-Openerp-Session-Id: $OWNER_SID")
GONE_CODE=$(echo "$GONE_RESP" | tail -1)
_assert_code "Deleted attachment returns 404 (hard-delete — FR3.2)" 404 "$GONE_CODE"

# Summary
echo ""
echo "============================================================"
echo "Feature 017 US17 S3 Delete RBAC — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
