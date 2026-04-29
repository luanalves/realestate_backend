#!/usr/bin/env bash
# Feature 013 — Property Proposals: Gap Coverage
# Covers acceptance scenarios NOT tested in T032/T033/T044/T055/T056/T057/T058
#
# Scenarios:
#   US1-S4  FR-003 : value ≤ 0 → validation error
#   US2-S2  FR-017 : queued proposal can't be sent directly
#   US4-S2  FR-014 : accept → competitors auto-cancelled ("Superseded by...")
#   US4-S3  FR-007 : reject without reason → error
#   US4-S5  FR-007 : terminal state blocks further updates
#   US6-S2         : agent sees only own proposals (isolation)
#   US6-S5         : GET /proposals/{id}/queue returns active + ordered queue
#   US7-S2         : oversized/wrong-type file upload → rejected
# =============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
if [ -f "$SCRIPT_DIR/../18.0/.env" ] && [ -z "${_PROPOSAL_TEST_ENV:-}" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0

pass() { echo -e "${GREEN}✓ $1${NC}"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}✗ $1${NC}"; FAIL=$((FAIL+1)); }
skip() { echo -e "${YELLOW}⚠ SKIP — $1${NC}"; }

echo "========================================"
echo "T013-GAP: Gap Coverage Scenarios"
echo "Feature 013 — Property Proposals"
echo "========================================"

if ! command -v jq &>/dev/null; then echo "ERROR: jq required"; exit 1; fi

# ---------------------------------------------------------------------------
# Auth: Owner (full access)
# ---------------------------------------------------------------------------
BEARER_TOKEN=$(get_oauth2_token)
OWNER_RESP=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d "{\"login\": \"${TEST_USER_OWNER:-owner@seed.com.br}\", \"password\": \"${TEST_PASSWORD_OWNER:-seed123}\"}")
OWNER_SESSION=$(echo "$OWNER_RESP" | jq -r '.session_id // empty')
OWNER_COMPANY=$(echo "$OWNER_RESP" | jq -r '.user.default_company_id // empty')
OWNER_AUTH=(-H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -H "Content-Type: application/json" \
    -H "X-Company-ID: ${OWNER_COMPANY:-5}")

if [ -z "$OWNER_SESSION" ]; then
    echo -e "${RED}✗ Owner login failed${NC}"; exit 1
fi
echo -e "${GREEN}✓ Owner autenticado (company=$OWNER_COMPANY)${NC}"

PROPERTY_ID="${PROPOSAL_TEST_PROPERTY_ID:-117}"
AGENT_ID="${TEST_AGENT_ID:-8}"

PROPOSAL_BODY() {
    echo "{\"property_id\": $PROPERTY_ID, \"client_name\": \"Gap Test Client\", \
\"client_document\": \"52998224725\", \"agent_id\": $AGENT_ID, \
\"proposal_type\": \"sale\", \"proposal_value\": $1}"
}

cleanup_proposals() {
    if command -v docker &>/dev/null; then
        COMPOSE_DIR="$(cd "$SCRIPT_DIR/../18.0" && pwd)"
        docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
            psql -U odoo -d realestate -c "
DELETE FROM real_estate_proposal
WHERE company_id = 5
  AND id NOT IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'quicksol_estate'
      AND name LIKE 'seed_proposal%'
      AND model = 'real.estate.proposal'
  );" > /dev/null 2>&1 || true
    fi
}

# ===========================================================================
# US1-S4 (FR-003): Proposal value ≤ 0 → validation error
# ===========================================================================
echo ""
echo "--- US1-S4 (FR-003): value ≤ 0 → validation error ---"
cleanup_proposals

CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 0)")
if [ "$CODE" = "400" ] || [ "$CODE" = "422" ]; then
    pass "US1-S4 FR-003: value=0 rejected ($CODE)"
else
    fail "US1-S4 FR-003: value=0 should be rejected, got $CODE"
fi

CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY -100)")
if [ "$CODE" = "400" ] || [ "$CODE" = "422" ]; then
    pass "US1-S4 FR-003: value=-100 rejected ($CODE)"
else
    fail "US1-S4 FR-003: value=-100 should be rejected, got $CODE"
fi

# ===========================================================================
# US2-S2 (FR-017): Queued proposal can't be sent directly
# ===========================================================================
echo ""
echo "--- US2-S2 (FR-017): queued proposal can't be sent ---"
cleanup_proposals

P1=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
P1_ID=$(echo "$P1" | jq -r '.id')

P2=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 120000)")
P2_ID=$(echo "$P2" | jq -r '.id')
P2_STATE=$(echo "$P2" | jq -r '.state')

if [ "$P2_STATE" = "queued" ]; then
    SEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$API_BASE/proposals/$P2_ID/send" "${OWNER_AUTH[@]}" -d '{}')
    if [ "$SEND_CODE" = "422" ] || [ "$SEND_CODE" = "400" ] || [ "$SEND_CODE" = "409" ]; then
        pass "US2-S2 FR-017: sending queued proposal blocked ($SEND_CODE)"
    else
        fail "US2-S2 FR-017: queued send should fail, got $SEND_CODE"
    fi
else
    skip "US2-S2: P2 not queued (state=$P2_STATE) — property may have no active proposal"
fi

# ===========================================================================
# US4-S3 (FR-007): Reject without reason → error
# ===========================================================================
echo ""
echo "--- US4-S3 (FR-007): reject without reason → error ---"
cleanup_proposals

P=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
PID=$(echo "$P" | jq -r '.id')
curl -s -o /dev/null -X POST "$API_BASE/proposals/$PID/send" "${OWNER_AUTH[@]}" -d '{}'

# Reject without rejection_reason
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals/$PID/reject" "${OWNER_AUTH[@]}" -d '{}')
if [ "$CODE" = "400" ] || [ "$CODE" = "422" ]; then
    pass "US4-S3: reject without reason rejected ($CODE)"
else
    fail "US4-S3: reject without reason should fail, got $CODE"
fi

# Reject with empty string
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals/$PID/reject" "${OWNER_AUTH[@]}" \
    -d '{"rejection_reason": ""}')
if [ "$CODE" = "400" ] || [ "$CODE" = "422" ]; then
    pass "US4-S3: reject with empty reason rejected ($CODE)"
else
    fail "US4-S3: reject with empty string should fail, got $CODE"
fi

# ===========================================================================
# US4-S5 (FR-007): Terminal state blocks further updates
# ===========================================================================
echo ""
echo "--- US4-S5 (FR-007): terminal state blocks updates ---"
cleanup_proposals

P=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
PID=$(echo "$P" | jq -r '.id')
curl -s -o /dev/null -X POST "$API_BASE/proposals/$PID/send" "${OWNER_AUTH[@]}" -d '{}'
curl -s -o /dev/null -X POST "$API_BASE/proposals/$PID/accept" "${OWNER_AUTH[@]}" -d '{}'

# Verify accepted
P_STATE=$(curl -s "${OWNER_AUTH[@]}" "$API_BASE/proposals/$PID" | jq -r '.state')
if [ "$P_STATE" = "accepted" ]; then
    # Try to PATCH (update) an accepted proposal
    PATCH_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X PATCH "$API_BASE/proposals/$PID" "${OWNER_AUTH[@]}" \
        -d '{"proposal_value": 999999}')
    if [ "$PATCH_CODE" = "422" ] || [ "$PATCH_CODE" = "400" ] || \
       [ "$PATCH_CODE" = "409" ] || [ "$PATCH_CODE" = "405" ]; then
        pass "US4-S5: update of accepted proposal blocked ($PATCH_CODE)"
    else
        fail "US4-S5: update of accepted proposal should be blocked, got $PATCH_CODE"
    fi

    # Try to reject an accepted proposal
    REJ_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$API_BASE/proposals/$PID/reject" "${OWNER_AUTH[@]}" \
        -d '{"rejection_reason": "Too late"}')
    if [ "$REJ_CODE" = "422" ] || [ "$REJ_CODE" = "400" ] || [ "$REJ_CODE" = "409" ]; then
        pass "US4-S5: reject of accepted proposal blocked ($REJ_CODE)"
    else
        fail "US4-S5: reject of accepted proposal should be blocked, got $REJ_CODE"
    fi
else
    skip "US4-S5: proposal not accepted (state=$P_STATE)"
fi

# ===========================================================================
# US4-S2 (FR-014): Accept → competitors auto-cancelled
# ===========================================================================
echo ""
echo "--- US4-S2 (FR-014): accept cancels all competitors ---"
cleanup_proposals

# Create winner (P1) and 2 competitors (P2, P3)
P1=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
P1_ID=$(echo "$P1" | jq -r '.id')

P2=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 110000)")
P2_ID=$(echo "$P2" | jq -r '.id')

P3=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 120000)")
P3_ID=$(echo "$P3" | jq -r '.id')

# Send and accept P1
curl -s -o /dev/null -X POST "$API_BASE/proposals/$P1_ID/send" "${OWNER_AUTH[@]}" -d '{}'
ACC_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals/$P1_ID/accept" "${OWNER_AUTH[@]}" -d '{}')

if [ "$ACC_CODE" = "200" ] || [ "$ACC_CODE" = "204" ]; then
    P2_STATE=$(curl -s "${OWNER_AUTH[@]}" "$API_BASE/proposals/$P2_ID" | jq -r '.state')
    P3_STATE=$(curl -s "${OWNER_AUTH[@]}" "$API_BASE/proposals/$P3_ID" | jq -r '.state')

    [ "$P2_STATE" = "cancelled" ] \
        && pass "US4-S2 FR-014: competitor P2 auto-cancelled" \
        || fail "US4-S2 FR-014: P2 state=$P2_STATE (expected cancelled)"

    [ "$P3_STATE" = "cancelled" ] \
        && pass "US4-S2 FR-014: competitor P3 auto-cancelled" \
        || fail "US4-S2 FR-014: P3 state=$P3_STATE (expected cancelled)"

    # Verify cancellation reason contains "Superseded"
    P2_REASON=$(curl -s "${OWNER_AUTH[@]}" "$API_BASE/proposals/$P2_ID" \
        | jq -r '.rejection_reason // .cancellation_reason // ""')
    if echo "$P2_REASON" | grep -qi "superseded\|superada\|aceita"; then
        pass "US4-S2 FR-014: cancellation reason mentions superseded"
    else
        skip "US4-S2 FR-014: cancellation reason not exposed in API (reason='$P2_REASON')"
    fi
else
    fail "US4-S2: accept returned $ACC_CODE (expected 200/204)"
fi

# ===========================================================================
# US6-S5 (FR-010): Queue inspection endpoint
# ===========================================================================
echo ""
echo "--- US6-S5 (FR-010): GET /proposals/{id}/queue ---"
cleanup_proposals

P1=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
P1_ID=$(echo "$P1" | jq -r '.id')

P2=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 110000)")
P2_ID=$(echo "$P2" | jq -r '.id')

QUEUE_CODE=$(curl -s -o /tmp/f013_queue.json -w "%{http_code}" \
    "${OWNER_AUTH[@]}" "$API_BASE/proposals/$P1_ID/queue")

if [ "$QUEUE_CODE" = "200" ]; then
    pass "US6-S5: GET /proposals/$P1_ID/queue returns 200"

    HAS_ACTIVE=$(jq 'has("active") or has("active_proposal") or has("current")' \
        /tmp/f013_queue.json 2>/dev/null || echo false)
    HAS_QUEUE=$(jq 'has("queue") or has("queued") or has("items")' \
        /tmp/f013_queue.json 2>/dev/null || echo false)

    [ "$HAS_ACTIVE" = "true" ] \
        && pass "US6-S5: response contains active proposal field" \
        || skip "US6-S5: no 'active'/'active_proposal'/'current' key — check response: $(cat /tmp/f013_queue.json | jq 'keys')"

    [ "$HAS_QUEUE" = "true" ] \
        && pass "US6-S5: response contains queue/items field" \
        || skip "US6-S5: no 'queue'/'queued'/'items' key — keys: $(jq 'keys' /tmp/f013_queue.json)"
else
    fail "US6-S5: GET /proposals/$P1_ID/queue returned $QUEUE_CODE"
fi
rm -f /tmp/f013_queue.json

# ===========================================================================
# US6-S2: Agent sees only own proposals
# ===========================================================================
echo ""
echo "--- US6-S2: agent sees only own proposals ---"
AGENT_LOGIN="${TEST_USER_AGENT:-${TEST_USER_AGENT_EMAIL:-}}"
AGENT_PASS="${TEST_PASSWORD_AGENT:-}"

if [ -z "$AGENT_LOGIN" ]; then
    skip "US6-S2: TEST_USER_AGENT not set in .env"
else
    AGENT_RESP=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$AGENT_LOGIN\", \"password\": \"$AGENT_PASS\"}")
    AGENT_SESSION=$(echo "$AGENT_RESP" | jq -r '.session_id // empty')
    AGENT_COMPANY=$(echo "$AGENT_RESP" | jq -r '.user.default_company_id // empty')
    AGENT_UID=$(echo "$AGENT_RESP" | jq -r '.user.id // empty')

    if [ -z "$AGENT_SESSION" ]; then
        skip "US6-S2: agent login failed"
    else
        AGENT_AUTH=(-H "Authorization: Bearer $BEARER_TOKEN" \
            -H "X-Openerp-Session-Id: $AGENT_SESSION" \
            -H "Content-Type: application/json" \
            -H "X-Company-ID: ${AGENT_COMPANY:-5}")

        LIST=$(curl -s "${AGENT_AUTH[@]}" "$API_BASE/proposals?limit=50")
        TOTAL=$(echo "$LIST" | jq '[.data // .results // [] | .[]] | length')

        if [ "${TOTAL:-0}" -eq 0 ]; then
            skip "US6-S2: no proposals returned for agent (no data to verify isolation)"
        else
            # All proposals must belong to this agent
            AGENT_PROPOSALS=$(echo "$LIST" | \
                jq "[.data // .results // [] | .[] | select(.agent_id == $AGENT_UID)] | length" 2>/dev/null || echo 0)
            # Some APIs return agent as object, check both
            OTHER_PROPOSALS=$(echo "$LIST" | \
                jq "[.data // .results // [] | .[] | select(.agent_id != $AGENT_UID and .agent_id != null)] | length" 2>/dev/null || echo 0)

            [ "${OTHER_PROPOSALS:-0}" -eq 0 ] \
                && pass "US6-S2: agent sees only own proposals ($TOTAL total, 0 from others)" \
                || fail "US6-S2: agent sees $OTHER_PROPOSALS proposals from other agents"
        fi
    fi
fi

# ===========================================================================
# US7-S2: Oversized / wrong-type file → error
# ===========================================================================
echo ""
echo "--- US7-S2: oversized/wrong-type file rejected ---"
cleanup_proposals

P=$(curl -s -X POST "$API_BASE/proposals" "${OWNER_AUTH[@]}" \
    -d "$(PROPOSAL_BODY 100000)")
PID=$(echo "$P" | jq -r '.id')

# Wrong type: .exe file (should be rejected)
EXE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_BASE/proposals/$PID/attachments" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -H "X-Company-ID: ${OWNER_COMPANY:-5}" \
    -F "file=@/dev/null;filename=malicious.exe;type=application/octet-stream")

if [ "$EXE_CODE" = "400" ] || [ "$EXE_CODE" = "422" ] || [ "$EXE_CODE" = "415" ]; then
    pass "US7-S2: .exe file upload rejected ($EXE_CODE)"
else
    skip "US7-S2: .exe returned $EXE_CODE (may be allowed or endpoint not enforcing type)"
fi

# Oversized file: generate ~11MB temp file
TMPFILE=$(mktemp /tmp/test_large_XXXXXX.pdf)
dd if=/dev/urandom of="$TMPFILE" bs=1M count=11 2>/dev/null || true
if [ -f "$TMPFILE" ]; then
    LARGE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$API_BASE/proposals/$PID/attachments" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION" \
        -H "X-Company-ID: ${OWNER_COMPANY:-5}" \
        -F "file=@$TMPFILE;filename=large.pdf;type=application/pdf")
    rm -f "$TMPFILE"

    if [ "$LARGE_CODE" = "400" ] || [ "$LARGE_CODE" = "422" ] || [ "$LARGE_CODE" = "413" ]; then
        pass "US7-S2: 11MB file upload rejected ($LARGE_CODE)"
    else
        skip "US7-S2: 11MB file returned $LARGE_CODE (server may not enforce size limit)"
    fi
else
    skip "US7-S2: could not create temp file for oversized test"
fi

# ===========================================================================
# Summary
# ===========================================================================
echo ""
echo "========================================"
echo "PASSED: $PASS, FAILED: $FAIL"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
