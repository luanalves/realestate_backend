#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Cross-Company Access Denial on Lead Activity Endpoints
# ==============================================================================
# Verifies log_activity, list_activities, and schedule_activity reject a user
# whose company does not match the lead's company.
#
# NOTE: log_activity and schedule_activity are `type="json"` Odoo routes that
# return a raw Response object. Odoo's JSON-RPC dispatcher does not forward
# such a Response's status code to the client — it always replies HTTP 200
# and stringifies the Response into the envelope's "result" field (a
# pre-existing bug affecting both success and error paths on these two
# endpoints, unrelated to and predating this feature; see
# specs/024-leads-company-isolation/spec.md's Known follow-up items). So for
# these two endpoints this test asserts HTTP 200 plus the actual status
# indicator inside the stringified body. list_activities is `type="http"` and
# correctly returns a real 403.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_activity_cross_company_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

assert_status() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $label (status=$actual)"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label (expected=$expected actual=$actual)"
        FAIL=$((FAIL+1))
    fi
}

assert_true() {
    local label="$1" condition="$2"
    if [ "$condition" = "true" ]; then
        echo -e "${GREEN}✓${NC} $label"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label"
        FAIL=$((FAIL+1))
    fi
}

{
    echo "=== Test Started: $(date) ==="
    TIMESTAMP=$(date +%s)

    echo -e "${BLUE}GIVEN${NC}: Pedro (agent in Company B) creates a lead — POST /api/v1/leads requires"
    echo "  the caller to have an associated real.estate.agent record, which Owner B lacks"
    authenticate_user "pedro@imobiliaria.com" "agent123"
    CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" "{
        \"name\": \"US024 Activity CrossCompany ${TIMESTAMP}\",
        \"phone\": \"+551192${TIMESTAMP: -7}\",
        \"email\": \"us024.activity.${TIMESTAMP}@example.com\",
        \"state\": \"new\"
    }")
    LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
    echo "Lead B ID: $LEAD_B_ID"

    if [ -z "$LEAD_B_ID" ] || [ "$LEAD_B_ID" = "null" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create Company B lead as pedro@imobiliaria.com — check demo_users.xml seed data"
        exit 1
    fi

    unset OAUTH_TOKEN USER_SESSION_ID
    echo ""
    echo -e "${BLUE}WHEN${NC}: Owner A (different company) calls the three activity endpoints"
    authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"

    LOG_BODY=$(curl -s -o /tmp/us024_log_cross.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"body":"cross-company note","activity_type":"note"}}')
    assert_status "log_activity: HTTP status is 200 (JSON-RPC envelope quirk)" "200" "$LOG_BODY"
    if grep -q "403 FORBIDDEN" /tmp/us024_log_cross.json; then
        assert_true "log_activity: response body indicates 403 FORBIDDEN" "true"
    else
        assert_true "log_activity: response body indicates 403 FORBIDDEN" "false"
    fi

    STATUS_LIST=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}")
    assert_status "list_activities rejects cross-company access" "403" "$STATUS_LIST"

    SCHEDULE_BODY=$(curl -s -o /tmp/us024_schedule_cross.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"cross-company activity","date_deadline":"2099-01-01"}}')
    assert_status "schedule_activity: HTTP status is 200 (JSON-RPC envelope quirk)" "200" "$SCHEDULE_BODY"
    if grep -q "403 FORBIDDEN" /tmp/us024_schedule_cross.json; then
        assert_true "schedule_activity: response body indicates 403 FORBIDDEN" "true"
    else
        assert_true "schedule_activity: response body indicates 403 FORBIDDEN" "false"
    fi

    echo ""
    echo -e "${BLUE}AND${NC}: the blocked cross-company writes were never actually persisted"
    unset OAUTH_TOKEN USER_SESSION_ID
    authenticate_user "owner2@example.com" "OwnerB123!"
    ACTIVITIES_AFTER_BLOCK=$(make_api_request "GET" "/api/v1/leads/${LEAD_B_ID}/activities")
    if echo "$ACTIVITIES_AFTER_BLOCK" | grep -q "cross-company note"; then
        assert_true "blocked log_activity did not create an activity" "false"
    else
        assert_true "blocked log_activity did not create an activity" "true"
    fi

    echo ""
    echo -e "${BLUE}AND${NC}: Owner B (same company) can still use all three endpoints"

    STATUS_LOG_OK=$(curl -s -o /tmp/us024_log_ok.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"body":"same-company note","activity_type":"note"}}')
    assert_status "log_activity: HTTP status is 200 for same-company call too" "200" "$STATUS_LOG_OK"
    if grep -q "201 CREATED" /tmp/us024_log_ok.json; then
        assert_true "log_activity: response body indicates 201 CREATED for same company" "true"
    else
        assert_true "log_activity: response body indicates 201 CREATED for same company" "false"
    fi

    STATUS_LIST_OK=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}")
    assert_status "list_activities still works for same company" "200" "$STATUS_LIST_OK"

    ACTIVITIES_FINAL=$(make_api_request "GET" "/api/v1/leads/${LEAD_B_ID}/activities")
    if echo "$ACTIVITIES_FINAL" | grep -q "same-company note"; then
        assert_true "the legitimate same-company activity was actually created" "true"
    else
        assert_true "the legitimate same-company activity was actually created" "false"
    fi

    STATUS_SCHEDULE_OK=$(curl -s -o /tmp/us024_schedule_ok.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"same-company activity","date_deadline":"2099-01-01"}}')
    assert_status "schedule_activity: HTTP status is 200 for same-company call too (envelope quirk)" "200" "$STATUS_SCHEDULE_OK"
    if grep -q "201 CREATED" /tmp/us024_schedule_ok.json; then
        assert_true "schedule_activity: response body indicates 201 CREATED for same company" "true"
    else
        assert_true "schedule_activity: response body indicates 201 CREATED for same company" "false"
    fi

    echo ""
    echo "Cleanup: archiving Company B test lead..."
    make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null 2>&1
    rm -f /tmp/us024_log_cross.json /tmp/us024_schedule_cross.json /tmp/us024_log_ok.json /tmp/us024_schedule_ok.json

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
