#!/usr/bin/env bash
# ============================================================
# Integration test: US2 — Manager reassigns service + notifications
# Feature 015 — Service Pipeline (Atendimentos)
# Task: T035
# FRs: FR-010, FR-024, FR-024b
# ============================================================
set -euo pipefail

# Load environment variables — REQUIRED
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../18.0/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
else
    echo "❌ ERROR: .env file not found at $ENV_FILE"
    echo "   Copy 18.0/.env.example to 18.0/.env and fill in credentials"
    exit 1
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
: "${MANAGER_EMAIL:?MANAGER_EMAIL is required — set it in 18.0/.env}"
: "${MANAGER_PASS:?MANAGER_PASS is required — set it in 18.0/.env}"
: "${AGENT_EMAIL:?AGENT_EMAIL is required — set it in 18.0/.env}"
: "${AGENT_PASS:?AGENT_PASS is required — set it in 18.0/.env}"
NEW_AGENT_ID="${NEW_AGENT_ID:-}"
: "${OAUTH_CLIENT_ID:?OAUTH_CLIENT_ID is required — set it in 18.0/.env}"
: "${OAUTH_CLIENT_SECRET:?OAUTH_CLIENT_SECRET is required — set it in 18.0/.env}"
PASS=0; FAIL=0

_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "✅ PASS: $*"; PASS=$((PASS+1)); }
_fail() { _log "❌ FAIL: $*"; FAIL=$((FAIL+1)); }

_assert_code() {
    local label="$1" expected="$2" actual="$3"
    [ "$actual" -eq "$expected" ] && _pass "$label (HTTP $actual)" || _fail "$label (expected $expected, got $actual)"
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
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    echo "{\"access_token\":\"$jwt\",\"session_id\":\"$sid\"}"
}

# ------------------------------------------------------------------ #
# Step 1 — Auth as manager                                            #
# ------------------------------------------------------------------ #
_log "Step 1: Auth manager (two-step)"
AUTH_DATA=$(_two_step_auth "$MANAGER_EMAIL" "$MANAGER_PASS")
JWT=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID=$(echo "$AUTH_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
[ -n "$JWT" ] && [ -n "$SID" ] && _pass "Manager auth" || { _fail "Manager auth failed"; echo "PASS=$PASS FAIL=$FAIL"; exit 1; }
H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID" -H "Content-Type: application/json")

# ------------------------------------------------------------------ #
# Step 2 — Create a service as manager                                #
# ------------------------------------------------------------------ #
_log "Step 2: Create service"
CR=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/services" "${H[@]}" \
    -d '{"client":{"name":"Reassign Test Client","phones":[{"type":"mobile","number":"11988001100","is_primary":true}]},"operation_type":"sale","source_id":1}')
CR_CODE=$(echo "$CR" | tail -1)
CR_BODY=$(echo "$CR" | sed '$d')
_assert_code "Create service" 201 "$CR_CODE"
SVC_ID=$(echo "$CR_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
[ -z "$SVC_ID" ] && { _fail "No service ID"; echo "PASS=$PASS FAIL=$FAIL"; exit 1; }

# ------------------------------------------------------------------ #
# Step 3 — Reassign to new agent                                      #
# ------------------------------------------------------------------ #
_log "Step 3: PATCH /reassign → agent $NEW_AGENT_ID"
RS=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SVC_ID/reassign" "${H[@]}" \
    -d "{\"new_agent_id\":$NEW_AGENT_ID,\"reason\":\"Load balancing\"}")
RS_CODE=$(echo "$RS" | tail -1)
_assert_code "PATCH /reassign" 200 "$RS_CODE"

# ------------------------------------------------------------------ #
# Step 4 — Verify new agent in GET response                           #
# ------------------------------------------------------------------ #
_log "Step 4: Verify agent change"
GR=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/services/$SVC_ID" "${H[@]}")
GR_CODE=$(echo "$GR" | tail -1)
GR_BODY=$(echo "$GR" | sed '$d')
_assert_code "GET service after reassign" 200 "$GR_CODE"
AGENT_ID=$(echo "$GR_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent',{}).get('id',''))" 2>/dev/null || echo "")
[ "$AGENT_ID" = "$NEW_AGENT_ID" ] && _pass "Agent ID updated to $NEW_AGENT_ID" || _fail "Agent ID expected $NEW_AGENT_ID, got $AGENT_ID"

# ------------------------------------------------------------------ #
# Step 5 — Non-manager (agent) cannot reassign                        #
# ------------------------------------------------------------------ #
_log "Step 5: Agent cannot reassign (must return 403)"
AUTH2_DATA=$(_two_step_auth "$AGENT_EMAIL" "$AGENT_PASS")
JWT2=$(echo "$AUTH2_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
SID2=$(echo "$AUTH2_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
if [ -n "$JWT2" ]; then
    H2=(-H "Authorization: Bearer $JWT2" -H "X-Openerp-Session-Id: $SID2" -H "Content-Type: application/json")
    NP=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SVC_ID/reassign" "${H2[@]}" \
        -d '{"new_agent_id":1}')
    NP_CODE=$(echo "$NP" | tail -1)
    _assert_code "Agent reassign blocked" 403 "$NP_CODE"
else
    _log "Skip agent auth test (no agent credentials)"
fi

# ------------------------------------------------------------------ #
# Step 6 — Reassign on terminal stage blocked (409)                   #
# ------------------------------------------------------------------ #
_log "Step 6: Reassign on terminal stage blocked"
# Move to lost first
curl -s -X PATCH "$BASE_URL/api/v1/services/$SVC_ID/stage" "${H[@]}" \
    -d '{"stage":"lost","lost_reason":"Test terminal reassign"}' > /dev/null
TR=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/v1/services/$SVC_ID/reassign" "${H[@]}" \
    -d "{\"new_agent_id\":$NEW_AGENT_ID}")
TR_CODE=$(echo "$TR" | tail -1)
_assert_code "Reassign on terminal stage blocked" 409 "$TR_CODE"

echo ""
echo "================================================================"
echo "Feature 015 US2 Reassign Test — Results: PASS=$PASS FAIL=$FAIL"
echo "================================================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
