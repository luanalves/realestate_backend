#!/usr/bin/env bash
# ============================================================
# Integration test: US3 — Filters, ordering, summary
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T045
# FRs: FR-009, FR-012, FR-013, FR-014, FR-015
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
_assert_field() {
    local label="$1" field="$2" response="$3"
    echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null \
        && _pass "$label — '$field' present" || _fail "$label — '$field' missing"
}

# ------------------------------------------------------------------ #
# Step 1 — Auth                                                       #
# ------------------------------------------------------------------ #
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

# ------------------------------------------------------------------ #
# Step 2 — GET /services — pagination meta                            #
# ------------------------------------------------------------------ #
_log "Step 2: List services with pagination"
LIST=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/services?page=1&per_page=5" "${H[@]}")
LIST_CODE=$(echo "$LIST" | tail -1)
LIST_BODY=$(echo "$LIST" | head -n -1)
_assert_code "GET /services" 200 "$LIST_CODE"
_assert_field "Pagination meta.total" "meta" "$LIST_BODY"
_assert_field "Pagination links" "links" "$LIST_BODY"

# ------------------------------------------------------------------ #
# Step 3 — Filter by operation_type=rent                              #
# ------------------------------------------------------------------ #
_log "Step 3: Filter by operation_type=rent"
FILT=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services?operation_type=rent" "${H[@]}")
_assert_code "Filter operation_type=rent" 200 "$FILT"

# ------------------------------------------------------------------ #
# Step 4 — Filter by stage                                            #
# ------------------------------------------------------------------ #
_log "Step 4: Filter by stage=no_service"
SFILT=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services?stage=no_service" "${H[@]}")
_assert_code "Filter stage=no_service" 200 "$SFILT"

# ------------------------------------------------------------------ #
# Step 5 — Ordering: pendency (oldest activity first)                 #
# ------------------------------------------------------------------ #
_log "Step 5: Ordering=pendency"
ORD=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services?ordering=pendency" "${H[@]}")
_assert_code "Ordering=pendency" 200 "$ORD"

# ------------------------------------------------------------------ #
# Step 6 — Free-text search q=                                        #
# ------------------------------------------------------------------ #
_log "Step 6: Free-text search q=test"
SQ=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services?q=test" "${H[@]}")
_assert_code "Search q=test" 200 "$SQ"

# ------------------------------------------------------------------ #
# Step 7 — Summary structure                                          #
# ------------------------------------------------------------------ #
_log "Step 7: GET /services/summary structure"
SUM=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/services/summary" "${H[@]}")
SUM_CODE=$(echo "$SUM" | tail -1)
SUM_BODY=$(echo "$SUM" | head -n -1)
_assert_code "GET /services/summary" 200 "$SUM_CODE"
_assert_field "Summary total" "total" "$SUM_BODY"
_assert_field "Summary orphan_agent" "orphan_agent" "$SUM_BODY"
_assert_field "Summary by_stage" "by_stage" "$SUM_BODY"

# ------------------------------------------------------------------ #
# Step 8 — is_pending filter                                          #
# ------------------------------------------------------------------ #
_log "Step 8: Filter is_pending=true"
IP=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/v1/services?is_pending=true" "${H[@]}")
_assert_code "Filter is_pending=true" 200 "$IP"

echo ""
echo "================================================================"
echo "Feature 015 US3 Filters Test — Results: PASS=$PASS FAIL=$FAIL"
echo "================================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
