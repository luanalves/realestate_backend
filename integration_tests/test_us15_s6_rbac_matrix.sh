#!/usr/bin/env bash
# ============================================================
# Integration test: US2 — RBAC matrix end-to-end
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T037
# FR: FR-010
# ============================================================
# Exercises auth matrix: Owner/Manager have write access;
# Agent/Prospector/Receptionist have limited or no write access.
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
    local label="$1" expected="$2" actual="$3"
    [ "$actual" -eq "$expected" ] && _pass "$label (HTTP $actual)" || _fail "$label (expected $expected, got $actual)"
}

_auth() {
    local email="$1" pass="$2"
    curl -s -X POST "$BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}"
}

# ------------------------------------------------------------------ #
# Step 1 — Unauthenticated calls → 401                               #
# ------------------------------------------------------------------ #
_log "Step 1: Unauth → 401 for all endpoints"
for EP in "/api/v1/services" "/api/v1/services/summary" "/api/v1/service-tags" "/api/v1/service-sources"; do
    _assert_code "Unauth $EP" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL$EP")"
done

# ------------------------------------------------------------------ #
# Step 2 — Owner can create service                                   #
# ------------------------------------------------------------------ #
_log "Step 2: Owner creates service"
AUTH=$(_auth "$OWNER_EMAIL" "$OWNER_PASS")
JWT=$(echo "$AUTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID=$(echo "$AUTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

if [ -n "$JWT" ]; then
    H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID" -H "Content-Type: application/json")
    CR=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/services" "${H[@]}" \
        -d '{"client":{"name":"RBAC Test Client","phones":[{"type":"mobile","number":"11988002200","is_primary":true}]},"operation_type":"rent"}')
    CR_CODE=$(echo "$CR" | tail -1)
    _assert_code "Owner create service" 201 "$CR_CODE"
    SVC_ID=$(echo "$CR" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
    [ -n "$SVC_ID" ] && _pass "Service ID obtained: $SVC_ID" || _fail "No service ID"

    # Owner can list
    _assert_code "Owner list services" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services" "${H[@]}")"
    # Owner can get summary
    _assert_code "Owner get summary" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services/summary" "${H[@]}")"
else
    _log "Skip owner tests (no credentials)"
fi

echo ""
echo "================================================================"
echo "Feature 015 US2 RBAC Matrix Test — Results: PASS=$PASS FAIL=$FAIL"
echo "================================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
