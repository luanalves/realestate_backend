#!/usr/bin/env bash
# ============================================================
# Integration test: US2 — Multi-tenancy isolation
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T036
# FR: FR-011
# ============================================================
# Tests that Company A users cannot access Company B services.
# Expects: unauthenticated calls → 401; cross-company GET → 404.
# ============================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
COMPANY_A_EMAIL="${COMPANY_A_EMAIL:-owner_a@seed.com}"
COMPANY_A_PASS="${COMPANY_A_PASS:-owner123}"
COMPANY_B_SERVICE_ID="${COMPANY_B_SERVICE_ID:-}"  # must be set externally
PASS=0; FAIL=0

_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }
_assert_code() {
    local label="$1" expected="$2" actual="$3"
    [ "$actual" -eq "$expected" ] && _pass "$label (HTTP $actual)" || _fail "$label (expected $expected, got $actual)"
}

# ------------------------------------------------------------------ #
# Step 1 — Unauthenticated access → 401                               #
# ------------------------------------------------------------------ #
_log "Step 1: Unauthenticated access blocked"
_assert_code "Unauth GET /services" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services")"
_assert_code "Unauth GET /summary" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services/summary")"
_assert_code "Unauth GET /service-tags" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/service-tags")"
_assert_code "Unauth GET /service-sources" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/service-sources")"

# ------------------------------------------------------------------ #
# Step 2 — Cross-company service access (requires COMPANY_B_SERVICE_ID)
# ------------------------------------------------------------------ #
if [ -n "$COMPANY_B_SERVICE_ID" ]; then
    _log "Step 2: Auth Company A and attempt to access Company B service"
    AUTH=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$COMPANY_A_EMAIL\",\"password\":\"$COMPANY_A_PASS\"}")
    CODE=$(echo "$AUTH" | tail -1)
    BODY=$(echo "$AUTH" | head -n -1)
    _assert_code "Company A auth" 200 "$CODE"
    JWT=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    SID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

    if [ -n "$JWT" ]; then
        H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID")
        CROSS=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services/$COMPANY_B_SERVICE_ID" "${H[@]}")
        _assert_code "Cross-company GET blocked" 404 "$CROSS"
    fi
else
    _log "Step 2: Skipped (COMPANY_B_SERVICE_ID not set)"
fi

echo ""
echo "================================================================"
echo "Feature 015 US2 Isolation Test — Results: PASS=$PASS FAIL=$FAIL"
echo "================================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
