#!/usr/bin/env bash
# ============================================================
# Integration test: US4 — Tags and Sources CRUD
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T053
# FRs: FR-010, FR-018, FR-019
# ============================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_EMAIL="${OWNER_EMAIL:-owner@seed.com}"
OWNER_PASS="${OWNER_PASS:-owner123}"
PASS=0; FAIL=0

_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }
_assert_code() {
    [ "$3" -eq "$2" ] && _pass "$1 (HTTP $3)" || _fail "$1 (expected $2, got $3)"
}

_log "Step 1: Auth owner"
AUTH=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASS\"}")
CODE=$(echo "$AUTH" | tail -1); BODY=$(echo "$AUTH" | head -n -1)
_assert_code "Auth" 200 "$CODE"
JWT=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -z "$JWT" ] && { _fail "No JWT"; echo "PASS=$PASS FAIL=$FAIL"; exit 1; }
H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID" -H "Content-Type: application/json")

_log "Step 2: Create tag"
CT=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/service-tags" "${H[@]}" \
    -d '{"name":"Integration Tag","color":"#3498db"}')
CT_CODE=$(echo "$CT" | tail -1)
_assert_code "Create tag" 201 "$CT_CODE"
TAG_ID=$(echo "$CT" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$TAG_ID" ]; then
    _log "Step 3: Update tag"
    _assert_code "Update tag" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X PUT "$BASE_URL/api/v1/service-tags/$TAG_ID" "${H[@]}" -d '{"color":"#2ecc71"}')"

    _log "Step 4: Archive tag (soft delete)"
    _assert_code "Archive tag" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$BASE_URL/api/v1/service-tags/$TAG_ID" "${H[@]}")"
fi

_log "Step 5: Create source"
CS=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/service-sources" "${H[@]}" \
    -d '{"name":"Integration Source","code":"int_test"}')
CS_CODE=$(echo "$CS" | tail -1)
_assert_code "Create source" 201 "$CS_CODE"
SRC_ID=$(echo "$CS" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -n "$SRC_ID" ]; then
    _log "Step 6: Update source"
    _assert_code "Update source" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X PUT "$BASE_URL/api/v1/service-sources/$SRC_ID" "${H[@]}" -d '{"name":"Int Source Updated"}')"
fi

echo ""
echo "================================================================"
echo "Feature 015 US4 Tags/Sources CRUD Test — PASS=$PASS FAIL=$FAIL"
echo "================================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
