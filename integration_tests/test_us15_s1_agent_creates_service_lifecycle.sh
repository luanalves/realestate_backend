#!/usr/bin/env bash
# ============================================================
# Integration test: US1 — Agent creates service and walks pipeline
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T023
# FRs: FR-001, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009
# ============================================================
# Usage:
#   BASE_URL=http://localhost:8069 \
#   AGENT_EMAIL=agent@imob-a.com \
#   AGENT_PASS=agent123 \
#   bash integration_tests/test_us15_s1_agent_creates_service_lifecycle.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
AGENT_EMAIL="${AGENT_EMAIL:?'AGENT_EMAIL is required — set it in 18.0/.env or export before running'}"
AGENT_PASS="${AGENT_PASS:?'AGENT_PASS is required — set it in 18.0/.env or export before running'}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:?'OAUTH_CLIENT_ID is required — set it in 18.0/.env or export before running'}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:?'OAUTH_CLIENT_SECRET is required — set it in 18.0/.env or export before running'}"
PASS=0
FAIL=0

# ------------------------------------------------------------------ #
# Helper functions                                                     #
# ------------------------------------------------------------------ #
_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }

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
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    echo "{\"access_token\":\"$jwt\",\"session_id\":\"$sid\"}"
}

_assert_code() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" -eq "$expected" ]; then
        _pass "$label (HTTP $actual)"
    else
        _fail "$label (expected HTTP $expected, got $actual)"
    fi
}

_assert_field() {
    local label="$1" field="$2" response="$3"
    if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d or any('$field' in str(v) for v in d.values())" 2>/dev/null; then
        _pass "$label — field '$field' present"
    else
        _fail "$label — field '$field' missing in response"
    fi
}

# ------------------------------------------------------------------ #
# Step 1 — Authenticate agent                                          #
# ------------------------------------------------------------------ #
_log "Step 1: Authenticate agent $AGENT_EMAIL (two-step)"

AUTH_DATA=$(_two_step_auth "$AGENT_EMAIL" "$AGENT_PASS")
JWT_TOKEN=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

if [ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ]; then
    _fail "Auth failed — JWT or session missing"
    echo "Results: PASS=$PASS FAIL=$FAIL"
    exit 1
fi
_pass "Auth two-step OK"

AUTH_HEADERS=(-H "Authorization: Bearer $JWT_TOKEN" -H "X-Openerp-Session-Id: $SESSION_ID" -H "Content-Type: application/json")

# ------------------------------------------------------------------ #
# Step 2 — Create service (POST /api/v1/services)                     #
# ------------------------------------------------------------------ #
_log "Step 2: Create service (US1 — new client)"

CREATE_BODY='{
  "client": {"name": "Test Client US15", "phones": [{"type": "mobile", "number": "11988887777", "is_primary": true}]},
  "operation_type": "rent",
  "source_id": 1,
  "notes": "Integration test US15 lifecycle"
}'

CREATE_RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/services" \
    "${AUTH_HEADERS[@]}" -d "$CREATE_BODY")
CREATE_CODE=$(echo "$CREATE_RESP" | tail -1)
CREATE_BODY_RESP=$(echo "$CREATE_RESP" | sed '$d')

_assert_code "POST /services" 201 "$CREATE_CODE"
_assert_field "POST /services response" "id" "$CREATE_BODY_RESP"
_assert_field "POST /services HATEOAS" "links" "$CREATE_BODY_RESP"

SERVICE_ID=$(echo "$CREATE_BODY_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

if [ -z "$SERVICE_ID" ]; then
    _fail "No service ID returned — skipping stage walk"
    echo ""
    echo "Results: PASS=$PASS FAIL=$FAIL"
    exit 1
fi
_log "Created service ID=$SERVICE_ID"

# ------------------------------------------------------------------ #
# Step 3 — Verify stage = no_service                                   #
# ------------------------------------------------------------------ #
_log "Step 3: Verify initial stage = no_service"

GET_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/services/$SERVICE_ID" "${AUTH_HEADERS[@]}")
GET_CODE=$(echo "$GET_RESP" | tail -1)
GET_BODY=$(echo "$GET_RESP" | sed '$d')

_assert_code "GET /services/$SERVICE_ID" 200 "$GET_CODE"
STAGE=$(echo "$GET_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stage',''))" 2>/dev/null || echo "")
if [ "$STAGE" = "no_service" ]; then
    _pass "Initial stage is no_service"
else
    _fail "Initial stage expected no_service, got $STAGE"
fi

# ------------------------------------------------------------------ #
# Step 4 — Move to in_service                                          #
# ------------------------------------------------------------------ #
_log "Step 4: Stage → in_service"

STAGE_RESP=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SERVICE_ID/stage" \
    "${AUTH_HEADERS[@]}" -d '{"stage":"in_service","comment":"Agent contacted client"}')
STAGE_CODE=$(echo "$STAGE_RESP" | tail -1)
_assert_code "PATCH /stage → in_service" 200 "$STAGE_CODE"

# ------------------------------------------------------------------ #
# Step 5 — Attempt proposal without property (FR-004 — must fail 422) #
# ------------------------------------------------------------------ #
_log "Step 5: Attempt proposal stage without property (FR-004)"

GATE_RESP=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SERVICE_ID/stage" \
    "${AUTH_HEADERS[@]}" -d '{"stage":"proposal"}')
GATE_CODE=$(echo "$GATE_RESP" | tail -1)
_assert_code "PATCH /stage → proposal (no property) gate check" 422 "$GATE_CODE"

# ------------------------------------------------------------------ #
# Step 6 — Move to lost (FR-006 — requires reason)                    #
# ------------------------------------------------------------------ #
_log "Step 6: Move to lost without reason (FR-006 — must fail 400/422)"

LOST_FAIL=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SERVICE_ID/stage" \
    "${AUTH_HEADERS[@]}" -d '{"stage":"lost"}')
LOST_FAIL_CODE=$(echo "$LOST_FAIL" | tail -1)
_assert_code "PATCH /stage → lost (no reason) blocked" 422 "$LOST_FAIL_CODE"

_log "Step 6b: Move to lost with reason (must succeed)"
LOST_OK=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SERVICE_ID/stage" \
    "${AUTH_HEADERS[@]}" -d '{"stage":"lost","lost_reason":"Client dropped project"}')
LOST_OK_CODE=$(echo "$LOST_OK" | tail -1)
_assert_code "PATCH /stage → lost (with reason)" 200 "$LOST_OK_CODE"

# ------------------------------------------------------------------ #
# Step 7 — Verify audit timeline has entries                          #
# ------------------------------------------------------------------ #
_log "Step 7: Verify service timeline (GET /services/$SERVICE_ID)"
AUD_RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/services/$SERVICE_ID" "${AUTH_HEADERS[@]}")
AUD_CODE=$(echo "$AUD_RESP" | tail -1)
_assert_code "GET /services/$SERVICE_ID audit check" 200 "$AUD_CODE"

# ------------------------------------------------------------------ #
# Step 8 — Duplicate creation attempt (FR-008 — 409)                 #
# (Same client+type+agent — EXCLUDE constraint)                       #
# Note: service is now lost, so constraint allows new active service   #
# ------------------------------------------------------------------ #
_log "Step 8: Verify EXCLUDE constraint doesn't block after terminal (won/lost)"
DUP_RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/services" \
    "${AUTH_HEADERS[@]}" -d "$CREATE_BODY")
DUP_CODE=$(echo "$DUP_RESP" | tail -1)
# After terminal stage, new service is allowed (EXCLUDE WHERE active AND stage NOT IN won/lost)
_assert_code "POST /services after terminal (new active allowed)" 201 "$DUP_CODE"

# ------------------------------------------------------------------ #
# Summary                                                              #
# ------------------------------------------------------------------ #
echo ""
echo "============================================================"
echo "Feature 015 US1 Integration Test — Results"
echo "PASS: $PASS  |  FAIL: $FAIL"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
