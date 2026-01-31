#!/bin/bash
###############################################################################
# E2E API Test: Manager All-Leads Access (T074)
#
# Tests that managers can view all company leads across all agents.
# Validates FR-024 (manager read access) and record rule filtering.
#
# Author: Quicksol Technologies
# Date: 2026-01-29
# Branch: 006-lead-management
# ADR: ADR-003 (E2E tests with real database)
###############################################################################

set -e

# Load auth helper library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
source "${SCRIPT_DIR}/../lib/auth_helper.sh"

# Load environment variables
if [ -f "$REPO_ROOT/18.0/.env" ]; then
    source "$REPO_ROOT/18.0/.env"
elif [ -f "${SCRIPT_DIR}/../../../../.env" ]; then
    source "${SCRIPT_DIR}/../../../../.env"
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

ODOO_BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test result function
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
echo -e "${BLUE}E2E API Test: Manager All-Leads Access${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Authenticate as Manager (TEST_MANAGER_EMAIL)
echo -e "${YELLOW}→ Authenticating as Manager...${NC}"
authenticate_user "${TEST_MANAGER_EMAIL}" "${TEST_MANAGER_PASSWORD}" || exit 1
MANAGER_TOKEN="$OAUTH_TOKEN"
MANAGER_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓ Manager authenticated successfully${NC}"
echo ""

# Authenticate as Agent A (TEST_USER_A_EMAIL)
echo -e "${YELLOW}→ Authenticating as Agent A...${NC}"
authenticate_user "${TEST_USER_A_EMAIL}" "${TEST_USER_A_PASSWORD}" || exit 1
AGENT_A_TOKEN="$OAUTH_TOKEN"
AGENT_A_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓ Agent A authenticated${NC}"
echo ""

# Authenticate as Agent B (TEST_USER_B_EMAIL)
echo -e "${YELLOW}→ Authenticating as Agent B...${NC}"
authenticate_user "${TEST_USER_B_EMAIL}" "${TEST_USER_B_PASSWORD}" || exit 1
AGENT_B_TOKEN="$OAUTH_TOKEN"
AGENT_B_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓ Agent B authenticated${NC}"
echo ""

# Create 3 leads as Agent A
echo -e "${YELLOW}→ Agent A creating 3 leads...${NC}"
for i in 1 2 3; do
    LEAD_A_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads" \
      -H "Authorization: Bearer ${AGENT_A_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"Agent A Lead $i\",\"phone\":\"+55 11 9000-000$i\",\"email\":\"agenta.lead$i@test.com\",\"state\":\"new\",\"budget_max\":500000}")
    
    if echo "$LEAD_A_RESPONSE" | grep -q '"id"'; then
        echo -e "${GREEN}  ✓ Lead $i created${NC}"
    fi
done
echo ""

# Create 2 leads as Agent B
echo -e "${YELLOW}→ Agent B creating 2 leads...${NC}"
for i in 1 2; do
    LEAD_B_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads" \
      -H "Authorization: Bearer ${AGENT_B_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"Agent B Lead $i\",\"phone\":\"+55 11 9100-000$i\",\"email\":\"agentb.lead$i@test.com\",\"state\":\"contacted\",\"budget_max\":600000}")
    
    if echo "$LEAD_B_RESPONSE" | grep -q '"id"'; then
        echo -e "${GREEN}  ✓ Lead $i created${NC}"
    fi
done
echo ""

# TEST 1: Manager views all leads (should see 5 total)
echo -e "${YELLOW}TEST 1: Manager GET /api/v1/leads (should see all company leads)${NC}"
MANAGER_LIST_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=100" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

MANAGER_TOTAL=$(echo "$MANAGER_LIST_RESPONSE" | grep -o '"total":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ "$MANAGER_TOTAL" -ge 5 ]; then
    assert_test 0 "Manager sees at least 5 leads (Agent A + Agent B leads)"
else
    assert_test 1 "Manager sees at least 5 leads (found: $MANAGER_TOTAL)"
fi
echo ""

# TEST 2: Manager list includes Agent A's leads
echo -e "${YELLOW}TEST 2: Manager list includes Agent A's leads${NC}"
if echo "$MANAGER_LIST_RESPONSE" | grep -q "Agent A Lead"; then
    assert_test 0 "Manager can see Agent A's leads"
else
    assert_test 1 "Manager cannot see Agent A's leads"
fi
echo ""

# TEST 3: Manager list includes Agent B's leads
echo -e "${YELLOW}TEST 3: Manager list includes Agent B's leads${NC}"
if echo "$MANAGER_LIST_RESPONSE" | grep -q "Agent B Lead"; then
    assert_test 0 "Manager can see Agent B's leads"
else
    assert_test 1 "Manager cannot see Agent B's leads"
fi
echo ""

# TEST 4: Manager can filter by agent_id (Agent A)
echo -e "${YELLOW}TEST 4: Manager filters by Agent A${NC}"
# Get Agent A's ID from one of their leads
AGENT_A_ID=$(echo "$MANAGER_LIST_RESPONSE" | grep -o '"agent_id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$AGENT_A_ID" ]; then
    FILTERED_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?agent_id=${AGENT_A_ID}" \
      -H "Authorization: Bearer ${MANAGER_TOKEN}")
    
    FILTERED_COUNT=$(echo "$FILTERED_RESPONSE" | grep -o '"total":[0-9]*' | head -1 | grep -o '[0-9]*')
    
    if [ "$FILTERED_COUNT" -ge 3 ]; then
        assert_test 0 "Manager filtered by Agent A (found $FILTERED_COUNT leads)"
    else
        assert_test 1 "Manager filter by Agent A failed (expected ≥3, found $FILTERED_COUNT)"
    fi
else
    assert_test 1 "Could not extract Agent A ID from response"
fi
echo ""

# TEST 5: Manager can filter by state (contacted)
echo -e "${YELLOW}TEST 5: Manager filters by state=contacted${NC}"
CONTACTED_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?state=contacted" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

if echo "$CONTACTED_RESPONSE" | grep -q '"state":"contacted"'; then
    assert_test 0 "Manager filtered by state=contacted (includes Agent B leads)"
else
    assert_test 1 "Manager filter by state=contacted failed"
fi
echo ""

# TEST 6: Manager can access individual lead by ID (Agent A's lead)
echo -e "${YELLOW}TEST 6: Manager GET /api/v1/leads/{id} for Agent A's lead${NC}"
LEAD_A1_ID=$(echo "$MANAGER_LIST_RESPONSE" | grep -B5 "Agent A Lead 1" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$LEAD_A1_ID" ]; then
    LEAD_DETAIL_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_A1_ID}" \
      -H "Authorization: Bearer ${MANAGER_TOKEN}")
    
    if echo "$LEAD_DETAIL_RESPONSE" | grep -q "Agent A Lead 1"; then
        assert_test 0 "Manager accessed Agent A's lead details (ID: $LEAD_A1_ID)"
    else
        assert_test 1 "Manager could not access Agent A's lead details"
    fi
else
    assert_test 1 "Could not extract Agent A's lead ID"
fi
echo ""

# TEST 7: Manager can update Agent B's lead (state change)
echo -e "${YELLOW}TEST 7: Manager PUT /api/v1/leads/{id} for Agent B's lead${NC}"
LEAD_B1_ID=$(echo "$MANAGER_LIST_RESPONSE" | grep -B5 "Agent B Lead 1" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$LEAD_B1_ID" ]; then
    UPDATE_RESPONSE=$(curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_B1_ID}" \
      -H "Authorization: Bearer ${MANAGER_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"state":"qualified"}')
    
    if echo "$UPDATE_RESPONSE" | grep -q '"state":"qualified"'; then
        assert_test 0 "Manager updated Agent B's lead state to qualified"
    else
        assert_test 1 "Manager could not update Agent B's lead"
    fi
else
    assert_test 1 "Could not extract Agent B's lead ID"
fi
echo ""

# TEST 8: Agent A still sees only own leads (not Agent B's)
echo -e "${YELLOW}TEST 8: Agent A isolation (should not see Agent B's leads)${NC}"
AGENT_A_LIST_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=100" \
  -H "Authorization: Bearer ${AGENT_A_TOKEN}")

AGENT_A_TOTAL=$(echo "$AGENT_A_LIST_RESPONSE" | grep -o '"total":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ "$AGENT_A_TOTAL" -eq 3 ]; then
    assert_test 0 "Agent A sees only own 3 leads (isolation preserved)"
elif echo "$AGENT_A_LIST_RESPONSE" | grep -q "Agent B Lead"; then
    assert_test 1 "Agent A can see Agent B's leads (isolation broken)"
else
    assert_test 0 "Agent A isolation maintained (found $AGENT_A_TOTAL leads)"
fi
echo ""

# TEST 9: Manager statistics endpoint includes all agents
echo -e "${YELLOW}TEST 9: Manager GET /api/v1/leads/statistics (all agents)${NC}"
STATS_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/statistics" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

if echo "$STATS_RESPONSE" | grep -q '"total"'; then
    STATS_TOTAL=$(echo "$STATS_RESPONSE" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
    
    if [ "$STATS_TOTAL" -ge 5 ]; then
        assert_test 0 "Manager statistics shows all company leads (total: $STATS_TOTAL)"
    else
        assert_test 1 "Manager statistics incomplete (expected ≥5, found $STATS_TOTAL)"
    fi
else
    assert_test 1 "Manager statistics endpoint failed"
fi
echo ""

# TEST 10: Manager can search across all leads (free-text)
echo -e "${YELLOW}TEST 10: Manager search across all leads${NC}"
SEARCH_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?search=Agent" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

if echo "$SEARCH_RESPONSE" | grep -q "Agent A Lead" && echo "$SEARCH_RESPONSE" | grep -q "Agent B Lead"; then
    assert_test 0 "Manager search returns leads from both agents"
else
    assert_test 1 "Manager search does not return all agent leads"
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
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
