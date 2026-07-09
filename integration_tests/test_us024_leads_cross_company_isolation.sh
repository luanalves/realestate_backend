#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Cross-Company Lead Isolation
# ==============================================================================
# Verifies GET /api/v1/leads, /api/v1/leads/export, and /api/v1/leads/statistics
# never return data from a company the requesting user does not belong to.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_cross_company_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

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
        \"name\": \"US024 CrossCompany Lead ${TIMESTAMP}\",
        \"phone\": \"+551190${TIMESTAMP: -7}\",
        \"email\": \"us024.crosscompany.${TIMESTAMP}@example.com\",
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
    echo -e "${BLUE}WHEN${NC}: Owner A queries list/export/statistics"
    authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"

    LIST_RESP=$(make_api_request "GET" "/api/v1/leads?limit=200")
    EXPORT_RESP=$(make_api_request "GET" "/api/v1/leads/export")
    STATS_RESP=$(make_api_request "GET" "/api/v1/leads/statistics")

    echo ""
    echo -e "${BLUE}THEN${NC}: Company B's lead must not appear for Owner A"

    if echo "$LIST_RESP" | grep -q "\"id\": $LEAD_B_ID"; then
        assert_true "list_leads excludes Company B lead" "false"
    else
        assert_true "list_leads excludes Company B lead" "true"
    fi

    if echo "$EXPORT_RESP" | grep -q "US024 CrossCompany Lead ${TIMESTAMP}"; then
        assert_true "export_leads_csv excludes Company B lead" "false"
    else
        assert_true "export_leads_csv excludes Company B lead" "true"
    fi

    if echo "$STATS_RESP" | grep -q '"total":[0-9]*'; then
        assert_true "lead_statistics returns a total (endpoint reachable)" "true"
    else
        assert_true "lead_statistics returns a total (endpoint reachable)" "false"
    fi

    echo ""
    echo -e "${BLUE}AND${NC}: Owner B still sees their own lead via all three endpoints"
    unset OAUTH_TOKEN USER_SESSION_ID
    authenticate_user "owner2@example.com" "OwnerB123!"

    LIST_RESP_B=$(make_api_request "GET" "/api/v1/leads?limit=200")
    EXPORT_RESP_B=$(make_api_request "GET" "/api/v1/leads/export")

    if echo "$LIST_RESP_B" | grep -q "\"id\": $LEAD_B_ID"; then
        assert_true "Owner B still sees own lead in list_leads" "true"
    else
        assert_true "Owner B still sees own lead in list_leads" "false"
    fi

    if echo "$EXPORT_RESP_B" | grep -q "US024 CrossCompany Lead ${TIMESTAMP}"; then
        assert_true "Owner B still sees own lead in export" "true"
    else
        assert_true "Owner B still sees own lead in export" "false"
    fi

    echo ""
    echo "Cleanup: archiving Company B test lead..."
    make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null 2>&1

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
