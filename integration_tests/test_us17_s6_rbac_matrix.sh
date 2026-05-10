#!/usr/bin/env bash
# ============================================================
# Integration test: US17 S6 — RBAC matrix
# Feature 017 — Property Attachments Upload API
# Task: T021
# FRs: FR3.1, FR3.3
#
# RBAC Matrix (FR3.1):
#   Role     | Upload | Download | List | Delete
#   ---------|--------|----------|------|-------
#   Owner    |   201  |   200    |  200 |  204
#   Manager  |   201  |   200    |  200 |  204
#   Agent    |   403  |   200    |  200 |  403
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@imob-a.com OWNER_PASS=owner123 \
#   MANAGER_EMAIL=manager@imob-a.com MANAGER_PASS=manager123 \
#   AGENT_EMAIL=agent@imob-a.com AGENT_PASS=agent123 \
#   OAUTH_CLIENT_ID=xxx OAUTH_CLIENT_SECRET=xxx \
#   PROPERTY_ID=1 \
#   bash integration_tests/test_us17_s6_rbac_matrix.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_EMAIL="${OWNER_EMAIL:?'OWNER_EMAIL is required'}"
OWNER_PASS="${OWNER_PASS:?'OWNER_PASS is required'}"
MANAGER_EMAIL="${MANAGER_EMAIL:?'MANAGER_EMAIL is required'}"
MANAGER_PASS="${MANAGER_PASS:?'MANAGER_PASS is required'}"
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
    curl -s -w "\n%{http_code}" -X POST \
        "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
        -H "Authorization: Bearer $jwt" -H "X-Openerp-Session-Id: $sid" \
        -F "file=@$file;type=image/jpeg" -F "attachment_type=image"
}

JPEG_FILE=$(mktemp /tmp/f017_rbac_XXXX.jpg)
python3 -c "open('$JPEG_FILE','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')"
trap "rm -f $JPEG_FILE" EXIT

# Step 1 — Auth all roles
_log "Step 1: Authenticate all three roles"
OWNER_DATA=$(_two_step_auth "$OWNER_EMAIL" "$OWNER_PASS")
OWNER_JWT=$(echo "$OWNER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
OWNER_SID=$(echo "$OWNER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$OWNER_JWT" ] && { _fail "Owner auth failed"; exit 1; }
_pass "Owner auth OK"

MANAGER_DATA=$(_two_step_auth "$MANAGER_EMAIL" "$MANAGER_PASS")
MANAGER_JWT=$(echo "$MANAGER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
MANAGER_SID=$(echo "$MANAGER_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$MANAGER_JWT" ] && { _fail "Manager auth failed"; exit 1; }
_pass "Manager auth OK"

AGENT_DATA=$(_two_step_auth "$AGENT_EMAIL" "$AGENT_PASS")
AGENT_JWT=$(echo "$AGENT_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
AGENT_SID=$(echo "$AGENT_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$AGENT_JWT" ] && { _fail "Agent auth failed"; exit 1; }
_pass "Agent auth OK"

# ------------------------------------------------------------------ #
# Step 2 — UPLOAD matrix                                              #
# ------------------------------------------------------------------ #
_log "Step 2: Upload RBAC matrix"

# Owner → 201
UP_OWNER=$(_upload_image "$OWNER_JWT" "$OWNER_SID" "$JPEG_FILE")
UP_OWNER_CODE=$(echo "$UP_OWNER" | tail -1)
UP_OWNER_BODY=$(echo "$UP_OWNER" | sed '$d')
_assert_code "Owner upload" 201 "$UP_OWNER_CODE"
OWNER_ATT_ID=$(echo "$UP_OWNER_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")

# Manager → 201
UP_MGMT=$(_upload_image "$MANAGER_JWT" "$MANAGER_SID" "$JPEG_FILE")
UP_MGMT_CODE=$(echo "$UP_MGMT" | tail -1)
UP_MGMT_BODY=$(echo "$UP_MGMT" | sed '$d')
_assert_code "Manager upload" 201 "$UP_MGMT_CODE"
MANAGER_ATT_ID=$(echo "$UP_MGMT_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null || echo "")

# Agent → 403
UP_AGENT=$(_upload_image "$AGENT_JWT" "$AGENT_SID" "$JPEG_FILE")
UP_AGENT_CODE=$(echo "$UP_AGENT" | tail -1)
_assert_code "Agent upload (forbidden)" 403 "$UP_AGENT_CODE"

# ------------------------------------------------------------------ #
# Step 3 — LIST matrix                                                #
# ------------------------------------------------------------------ #
_log "Step 3: List RBAC matrix"

for role_name in "Owner" "Manager" "Agent"; do
    case "$role_name" in
        "Owner")   jwt="$OWNER_JWT"   sid="$OWNER_SID"   ;;
        "Manager") jwt="$MANAGER_JWT" sid="$MANAGER_SID" ;;
        "Agent")   jwt="$AGENT_JWT"   sid="$AGENT_SID"   ;;
    esac
    LIST_RESP=$(curl -s -w "\n%{http_code}" \
        "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
        -H "Authorization: Bearer $jwt" -H "X-Openerp-Session-Id: $sid")
    LIST_CODE=$(echo "$LIST_RESP" | tail -1)
    _assert_code "$role_name list (read-only, allowed)" 200 "$LIST_CODE"
done

# ------------------------------------------------------------------ #
# Step 4 — DOWNLOAD matrix (use owner's uploaded attachment)          #
# ------------------------------------------------------------------ #
_log "Step 4: Download RBAC matrix"

if [ -n "$OWNER_ATT_ID" ]; then
    for role_name in "Owner" "Manager" "Agent"; do
        case "$role_name" in
            "Owner")   jwt="$OWNER_JWT"   sid="$OWNER_SID"   ;;
            "Manager") jwt="$MANAGER_JWT" sid="$MANAGER_SID" ;;
            "Agent")   jwt="$AGENT_JWT"   sid="$AGENT_SID"   ;;
        esac
        DL_RESP=$(curl -s -w "\n%{http_code}" -o /dev/null \
            "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$OWNER_ATT_ID/download" \
            -H "Authorization: Bearer $jwt" -H "X-Openerp-Session-Id: $sid")
        _assert_code "$role_name download (read-only, allowed)" 200 "$DL_RESP"
    done
else
    _fail "Skipping download matrix — OWNER_ATT_ID not available"
fi

# ------------------------------------------------------------------ #
# Step 5 — DELETE matrix                                              #
# ------------------------------------------------------------------ #
_log "Step 5: Delete RBAC matrix"

# Agent tries to delete owner's attachment → 403
if [ -n "$OWNER_ATT_ID" ]; then
    DEL_AGENT=$(curl -s -w "\n%{http_code}" -X DELETE \
        "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$OWNER_ATT_ID" \
        -H "Authorization: Bearer $AGENT_JWT" -H "X-Openerp-Session-Id: $AGENT_SID")
    _assert_code "Agent delete (forbidden)" 403 "$(echo "$DEL_AGENT" | tail -1)"
fi

# Manager deletes manager's own upload → 204
if [ -n "$MANAGER_ATT_ID" ]; then
    DEL_MGR=$(curl -s -w "\n%{http_code}" -X DELETE \
        "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$MANAGER_ATT_ID" \
        -H "Authorization: Bearer $MANAGER_JWT" -H "X-Openerp-Session-Id: $MANAGER_SID")
    _assert_code "Manager delete own attachment" 204 "$(echo "$DEL_MGR" | tail -1)"
fi

# Owner deletes owner's attachment → 204
if [ -n "$OWNER_ATT_ID" ]; then
    DEL_OWN=$(curl -s -w "\n%{http_code}" -X DELETE \
        "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$OWNER_ATT_ID" \
        -H "Authorization: Bearer $OWNER_JWT" -H "X-Openerp-Session-Id: $OWNER_SID")
    _assert_code "Owner delete own attachment" 204 "$(echo "$DEL_OWN" | tail -1)"
fi

# Summary
echo ""
echo "============================================================"
echo "Feature 017 US17 S6 RBAC Matrix — Results"
echo "RBAC matrix covered: Owner/Manager/Agent × Upload/List/Download/Delete"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
