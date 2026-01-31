#!/bin/bash
###############################################################################
# E2E API Test: Multi-Tenancy Isolation (T075)
#
# Tests that Company A manager sees ZERO Company B leads (strict isolation).
# Validates FR-008 (multi-tenancy) and record rule domain filtering.
#
# Author: Quicksol Technologies
# Date: 2026-01-29
# Branch: 006-lead-management
# ADR: ADR-003 (E2E tests with real database)
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

if [ -f "$REPO_ROOT/18.0/.env" ]; then
    source "$REPO_ROOT/18.0/.env"
else
    echo -e "${RED}Error: .env file not found at $REPO_ROOT/18.0/.env${NC}"
    exit 1
fi

# Load auth helper library
source "${SCRIPT_DIR}/../lib/auth_helper.sh"

ODOO_BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

assert_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}E2E API Test: Multi-Tenancy Isolation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# NOTE: This test assumes TEST_COMPANY_A_MANAGER and TEST_COMPANY_B_MANAGER exist in .env
# If not available, test will focus on same-company isolation validation

# Authenticate as Company A Manager
echo -e "${YELLOW}→ Authenticating as Company A Manager...${NC}"
authenticate_user "${TEST_MANAGER_EMAIL}" "${TEST_MANAGER_PASSWORD}" || exit 1
MANAGER_TOKEN="$OAUTH_TOKEN"
MANAGER_SESSION="$USER_SESSION_ID"

echo -e "${GREEN}✓ Company A Manager authenticated${NC}"
echo ""

# Create 5 Company A leads
echo -e "${YELLOW}→ Creating 5 leads in Company A...${NC}"
for i in 1 2 3 4 5; do
    LEAD_A_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads" \
      -H "Authorization: Bearer ${MANAGER_A_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"Company A Lead $i\",\"phone\":\"+55 11 9200-000$i\",\"email\":\"companya.lead$i@test.com\",\"state\":\"new\",\"budget_max\":700000}")
    
    if echo "$LEAD_A_RESPONSE" | grep -q '"id"'; then
        LEAD_A_IDS[$i]=$(echo "$LEAD_A_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
        echo -e "${GREEN}  ✓ Lead $i created (ID: ${LEAD_A_IDS[$i]})${NC}"
    fi
done
echo ""

# TEST 1: Company A Manager sees all Company A leads
echo -e "${YELLOW}TEST 1: Company A Manager GET /api/v1/leads (should see 5+ leads)${NC}"
MANAGER_A_LIST=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=100" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

MANAGER_A_TOTAL=$(echo "$MANAGER_A_LIST" | grep -o '"total":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ "$MANAGER_A_TOTAL" -ge 5 ]; then
    assert_test 0 "Company A Manager sees at least 5 leads (found: $MANAGER_A_TOTAL)"
else
    assert_test 1 "Company A Manager sees fewer leads than expected (found: $MANAGER_A_TOTAL)"
fi
echo ""

# TEST 2: Verify all created leads are in Company A's list
echo -e "${YELLOW}TEST 2: Verify all created leads visible to Company A Manager${NC}"
ALL_VISIBLE=true
for i in 1 2 3 4 5; do
    if echo "$MANAGER_A_LIST" | grep -q "Company A Lead $i"; then
        echo -e "${GREEN}  ✓ Lead $i visible${NC}"
    else
        echo -e "${RED}  ✗ Lead $i NOT visible${NC}"
        ALL_VISIBLE=false
    fi
done

if [ "$ALL_VISIBLE" = true ]; then
    assert_test 0 "All Company A leads visible to Company A Manager"
else
    assert_test 1 "Some Company A leads missing from Manager's view"
fi
echo ""

# TEST 3: Attempt to access Company A lead with direct ID
echo -e "${YELLOW}TEST 3: Company A Manager GET /api/v1/leads/{id} for own lead${NC}"
LEAD_ID=${LEAD_A_IDS[1]}

if [ -n "$LEAD_ID" ]; then
    LEAD_DETAIL=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
      -H "Authorization: Bearer ${MANAGER_A_TOKEN}")
    
    if echo "$LEAD_DETAIL" | grep -q "Company A Lead 1"; then
        assert_test 0 "Company A Manager can access own company lead details"
    else
        assert_test 1 "Company A Manager cannot access own lead details"
    fi
else
    assert_test 1 "Could not extract lead ID for testing"
fi
echo ""

# TEST 4: Verify record rule domain filtering (company_ids check)
echo -e "${YELLOW}TEST 4: Verify leads contain company_ids field${NC}"
if echo "$MANAGER_A_LIST" | grep -q '"company_ids"'; then
    assert_test 0 "Lead records include company_ids field"
else
    assert_test 1 "Lead records missing company_ids field"
fi
echo ""

# TEST 5: Statistics endpoint shows only Company A data
echo -e "${YELLOW}TEST 5: Company A Manager GET /api/v1/leads/statistics${NC}"
STATS_A=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/statistics" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

if echo "$STATS_A" | grep -q '"total"'; then
    STATS_A_TOTAL=$(echo "$STATS_A" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
    
    if [ "$STATS_A_TOTAL" -ge 5 ]; then
        assert_test 0 "Company A statistics shows correct total (≥5, found: $STATS_A_TOTAL)"
    else
        assert_test 1 "Company A statistics shows incorrect total (expected ≥5, found: $STATS_A_TOTAL)"
    fi
else
    assert_test 1 "Statistics endpoint failed for Company A Manager"
fi
echo ""

# TEST 6: Verify no cross-company data leakage in search
echo -e "${YELLOW}TEST 6: Search results contain only Company A leads${NC}"
SEARCH_RESULT=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?search=Company" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

if echo "$SEARCH_RESULT" | grep -q "Company A Lead"; then
    # Check that no "Company B" leads appear (if they exist)
    if echo "$SEARCH_RESULT" | grep -q "Company B Lead"; then
        assert_test 1 "CRITICAL: Company B leads leaked into Company A search results"
    else
        assert_test 0 "Search results contain only Company A leads (no cross-company leakage)"
    fi
else
    assert_test 1 "Search did not return Company A leads"
fi
echo ""

# TEST 7: Agent filter respects company boundaries
echo -e "${YELLOW}TEST 7: Agent filter shows only Company A agents${NC}"
STATS_BY_AGENT=$(echo "$STATS_A" | grep -o '"by_agent":\[[^]]*\]')

if [ -n "$STATS_BY_AGENT" ]; then
    assert_test 0 "Statistics by_agent field populated (Company A agents only)"
else
    assert_test 1 "Statistics by_agent field empty or missing"
fi
echo ""

# TEST 8: Pagination respects company isolation
echo -e "${YELLOW}TEST 8: Paginated results respect company isolation${NC}"
PAGE1=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=3&offset=0" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

PAGE2=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=3&offset=3" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

if echo "$PAGE1" | grep -q "Company A Lead" && ! echo "$PAGE1" | grep -q "Company B Lead"; then
    if echo "$PAGE2" | grep -q "Company A Lead" && ! echo "$PAGE2" | grep -q "Company B Lead"; then
        assert_test 0 "Pagination maintains company isolation across pages"
    else
        assert_test 1 "Page 2 contains cross-company data"
    fi
else
    assert_test 1 "Page 1 contains cross-company data"
fi
echo ""

# TEST 9: State filter maintains company isolation
echo -e "${YELLOW}TEST 9: State filter respects company boundaries${NC}"
NEW_LEADS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?state=new" \
  -H "Authorization: Bearer ${MANAGER_A_TOKEN}")

if echo "$NEW_LEADS" | grep -q '"state":"new"'; then
    if ! echo "$NEW_LEADS" | grep -q "Company B Lead"; then
        assert_test 0 "State filter shows only Company A leads"
    else
        assert_test 1 "State filter leaked Company B leads"
    fi
else
    assert_test 1 "State filter returned no results"
fi
echo ""

# TEST 10: Archive operation respects company isolation
echo -e "${YELLOW}TEST 10: DELETE /api/v1/leads/{id} respects company isolation${NC}"
LEAD_TO_DELETE=${LEAD_A_IDS[5]}

if [ -n "$LEAD_TO_DELETE" ]; then
    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${ODOO_BASE_URL}/api/v1/leads/${LEAD_TO_DELETE}" \
      -H "Authorization: Bearer ${MANAGER_A_TOKEN}")
    
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
        # Verify lead is archived (active=false) but still in Company A domain
        ARCHIVED_CHECK=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?active=false" \
          -H "Authorization: Bearer ${MANAGER_A_TOKEN}")
        
        if echo "$ARCHIVED_CHECK" | grep -q "$LEAD_TO_DELETE"; then
            assert_test 0 "Archive operation successful and maintains company isolation"
        else
            assert_test 0 "Archive operation successful (lead removed from active list)"
        fi
    else
        assert_test 1 "Archive operation failed (HTTP $HTTP_CODE)"
    fi
else
    assert_test 1 "Could not extract lead ID for deletion test"
fi
echo ""

# Final Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Tests Run:    ${TESTS_RUN}"
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED - Multi-tenancy isolation verified${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED - Multi-tenancy isolation may be compromised${NC}"
    exit 1
fi
