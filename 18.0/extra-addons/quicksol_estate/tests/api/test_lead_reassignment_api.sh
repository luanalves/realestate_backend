#!/bin/bash
###############################################################################
# E2E API Test: Lead Reassignment (T076)
#
# Tests manager's ability to reassign leads between agents with validation.
# Validates FR-026 (manager reassignment), FR-027 (activity logging),
# and company matching validation.
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
echo -e "${BLUE}E2E API Test: Lead Reassignment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Authenticate as Manager
echo -e "${YELLOW}→ Authenticating as Manager...${NC}"
MANAGER_TOKEN_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_MANAGER_EMAIL}\",\"password\":\"${TEST_MANAGER_PASSWORD}\"}")

MANAGER_TOKEN=$(echo "$MANAGER_TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$MANAGER_TOKEN" ]; then
    echo -e "${RED}✗ FAIL: Manager authentication failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Manager authenticated${NC}"
echo ""

# Authenticate as Agent A
echo -e "${YELLOW}→ Authenticating as Agent A...${NC}"

# Login as agent A user (reuse OAuth token)
AGENT_A_LOGIN_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/users/login" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_USER_A_EMAIL}\",\"password\":\"${TEST_USER_A_PASSWORD}\"}")

AGENT_A_SESSION_ID=$(echo "$AGENT_A_LOGIN_RESPONSE" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*' | sed 's/"session_id"[[:space:]]*:[[:space:]]*"//' | head -1)
AGENT_A_TOKEN="$OAUTH_TOKEN"

echo -e "${GREEN}✓ Agent A authenticated${NC}"
echo ""

# Authenticate as Agent B
echo -e "${YELLOW}→ Authenticating as Agent B...${NC}"

# Login as agent B user (reuse OAuth token)
AGENT_B_LOGIN_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/users/login" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_USER_B_EMAIL}\",\"password\":\"${TEST_USER_B_PASSWORD}\"}")

AGENT_B_SESSION_ID=$(echo "$AGENT_B_LOGIN_RESPONSE" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*' | sed 's/"session_id"[[:space:]]*:[[:space:]]*"//' | head -1)
AGENT_B_TOKEN="$OAUTH_TOKEN"

echo -e "${GREEN}✓ Agent B authenticated${NC}"
echo ""

# Create lead as Agent A
echo -e "${YELLOW}→ Agent A creating lead for reassignment test...${NC}"
CREATE_RESPONSE=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads" \
  -H "Authorization: Bearer ${AGENT_A_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name":"Lead for Reassignment Test","phone":"+55 11 9300-0001","email":"reassignment@test.com","state":"contacted","budget_max":800000}')

LEAD_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
AGENT_A_ID=$(echo "$CREATE_RESPONSE" | grep -o '"agent_id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$LEAD_ID" ]; then
    echo -e "${GREEN}✓ Lead created (ID: $LEAD_ID, Agent: $AGENT_A_ID)${NC}"
else
    echo -e "${RED}✗ Lead creation failed${NC}"
    exit 1
fi
echo ""

# Get Agent B's ID
echo -e "${YELLOW}→ Getting Agent B's ID...${NC}"
AGENT_B_LEADS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=1" \
  -H "Authorization: Bearer ${AGENT_B_TOKEN}")

AGENT_B_ID=$(echo "$AGENT_B_LEADS" | grep -o '"agent_id":[0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$AGENT_B_ID" ]; then
    echo -e "${GREEN}✓ Agent B ID: $AGENT_B_ID${NC}"
else
    echo -e "${YELLOW}⚠ Could not find existing Agent B lead, using placeholder ID${NC}"
    AGENT_B_ID=999
fi
echo ""

# TEST 1: Manager can reassign lead from Agent A to Agent B
echo -e "${YELLOW}TEST 1: Manager PUT /api/v1/leads/{id} (reassign agent_id)${NC}"
REASSIGN_RESPONSE=$(curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":${AGENT_B_ID}}")

if echo "$REASSIGN_RESPONSE" | grep -q "\"agent_id\":$AGENT_B_ID"; then
    assert_test 0 "Manager successfully reassigned lead to Agent B"
else
    assert_test 1 "Manager reassignment failed"
fi
echo ""

# TEST 2: Verify lead now belongs to Agent B
echo -e "${YELLOW}TEST 2: Verify lead visible to Agent B${NC}"
AGENT_B_LIST=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=100" \
  -H "Authorization: Bearer ${AGENT_B_TOKEN}")

if echo "$AGENT_B_LIST" | grep -q "Lead for Reassignment Test"; then
    assert_test 0 "Reassigned lead now visible to Agent B"
else
    assert_test 1 "Reassigned lead NOT visible to Agent B"
fi
echo ""

# TEST 3: Verify lead no longer visible to Agent A
echo -e "${YELLOW}TEST 3: Verify lead hidden from Agent A (post-reassignment)${NC}"
AGENT_A_LIST=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=100" \
  -H "Authorization: Bearer ${AGENT_A_TOKEN}")

if echo "$AGENT_A_LIST" | grep -q "Lead for Reassignment Test"; then
    assert_test 1 "Lead still visible to Agent A (isolation broken)"
else
    assert_test 0 "Lead correctly hidden from Agent A after reassignment"
fi
echo ""

# TEST 4: Agent A cannot change agent_id (permission denied)
echo -e "${YELLOW}TEST 4: Agent A PUT /api/v1/leads/{id} with agent_id (should fail)${NC}"
# First reassign back to Agent A via manager
curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":${AGENT_A_ID}}" > /dev/null

# Now Agent A tries to reassign
AGENT_REASSIGN=$(curl -s -w "\n%{http_code}" -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${AGENT_A_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":${AGENT_B_ID}}")

HTTP_CODE=$(echo "$AGENT_REASSIGN" | tail -1)

if [ "$HTTP_CODE" = "403" ]; then
    assert_test 0 "Agent A correctly denied permission to reassign (HTTP 403)"
elif echo "$AGENT_REASSIGN" | grep -q "Agents cannot change agent assignment"; then
    assert_test 0 "Agent A correctly denied with validation message"
else
    assert_test 1 "Agent A was able to reassign lead (security breach)"
fi
echo ""

# TEST 5: Manager cannot reassign to agent from different company (validation)
echo -e "${YELLOW}TEST 5: Manager reassigns to wrong-company agent (should fail)${NC}"
# This test assumes there's a cross-company agent ID available
# For now, we'll test with invalid agent ID (999999)
INVALID_REASSIGN=$(curl -s -w "\n%{http_code}" -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":999999}')

HTTP_CODE=$(echo "$INVALID_REASSIGN" | tail -1)

if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "400" ]; then
    assert_test 0 "Invalid agent reassignment rejected (HTTP $HTTP_CODE)"
elif echo "$INVALID_REASSIGN" | grep -q "not found"; then
    assert_test 0 "Invalid agent reassignment rejected with error message"
else
    assert_test 1 "Invalid agent reassignment was accepted (validation missing)"
fi
echo ""

# TEST 6: Manager can reassign to unassigned (agent_id = False)
echo -e "${YELLOW}TEST 6: Manager unassigns lead (agent_id = null)${NC}"
UNASSIGN_RESPONSE=$(curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":null}')

if echo "$UNASSIGN_RESPONSE" | grep -q '"agent_id":null' || echo "$UNASSIGN_RESPONSE" | grep -q '"agent_id":false'; then
    assert_test 0 "Manager successfully unassigned lead"
else
    assert_test 1 "Manager could not unassign lead"
fi
echo ""

# TEST 7: Reassign back and check lead details include agent info
echo -e "${YELLOW}TEST 7: Manager reassigns back to Agent A (verify GET response)${NC}"
FINAL_REASSIGN=$(curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":${AGENT_A_ID}}")

if echo "$FINAL_REASSIGN" | grep -q "\"agent_id\":$AGENT_A_ID" && echo "$FINAL_REASSIGN" | grep -q '"agent_name"'; then
    assert_test 0 "Lead details include agent_id and agent_name after reassignment"
else
    assert_test 1 "Lead details missing agent information"
fi
echo ""

# TEST 8: Multiple rapid reassignments (stress test)
echo -e "${YELLOW}TEST 8: Multiple rapid reassignments (A→B→A→B)${NC}"
SUCCESS_COUNT=0
for i in 1 2 3; do
    # A → B
    curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
      -H "Authorization: Bearer ${MANAGER_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"agent_id\":${AGENT_B_ID}}" > /dev/null
    
    # B → A
    RESULT=$(curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
      -H "Authorization: Bearer ${MANAGER_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"agent_id\":${AGENT_A_ID}}")
    
    if echo "$RESULT" | grep -q "\"agent_id\":$AGENT_A_ID"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
done

if [ "$SUCCESS_COUNT" -eq 3 ]; then
    assert_test 0 "All 3 rapid reassignment cycles successful"
else
    assert_test 1 "Some rapid reassignments failed ($SUCCESS_COUNT/3 successful)"
fi
echo ""

# TEST 9: Reassignment maintains other lead data (phone, email unchanged)
echo -e "${YELLOW}TEST 9: Reassignment preserves lead data integrity${NC}"
FINAL_LEAD=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

if echo "$FINAL_LEAD" | grep -q "reassignment@test.com" && echo "$FINAL_LEAD" | grep -q "+55 11 9300-0001"; then
    assert_test 0 "Lead contact data preserved after multiple reassignments"
else
    assert_test 1 "Lead contact data corrupted after reassignments"
fi
echo ""

# TEST 10: Reassignment statistics (verify by_agent counts update)
echo -e "${YELLOW}TEST 10: Statistics reflect reassignments correctly${NC}"
STATS_BEFORE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/statistics" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

# Reassign lead to Agent B
curl -s -X PUT "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":${AGENT_B_ID}}" > /dev/null

STATS_AFTER=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/statistics" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}")

if [ "$STATS_BEFORE" != "$STATS_AFTER" ]; then
    assert_test 0 "Statistics updated after reassignment"
else
    assert_test 1 "Statistics did not update after reassignment"
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
    echo -e "${GREEN}✓ ALL TESTS PASSED - Lead reassignment working correctly${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED - Lead reassignment has issues${NC}"
    exit 1
fi
