#!/bin/bash
# ==============================================================================
# E2E API Test: Agent Isolation (Record Rules)
# ==============================================================================
# Tests: Agents see only their own leads, cannot access other agents' leads
# Requirements: FR-019 (agent isolation), FR-022 (cannot change agent_id)
# Task: T026
# ADR-003: E2E test WITH database (real API endpoints + record rules)
# ==============================================================================

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
source "$PROJECT_ROOT/18.0/.env"

# Configuration
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
AGENT_A_EMAIL="${TEST_USER_A_EMAIL:-joao@imobiliaria.com}"
AGENT_A_PASSWORD="${TEST_USER_A_PASSWORD:-test123}"
AGENT_B_EMAIL="${TEST_USER_B_EMAIL:-pedro@imobiliaria.com}"
AGENT_B_PASSWORD="${TEST_USER_B_PASSWORD:-test123}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Helpers
print_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" == "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name - $message"
        ((FAILED++))
    fi
}

get_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | grep -o "\"$field\":[^,}]*" | head -1 | cut -d':' -f2- | tr -d ' ",'
}

echo "=========================================="
echo "E2E API Test: Agent Isolation"
echo "=========================================="
echo ""

# ==============================================================================
# STEP 1: Authenticate Agent A
# ==============================================================================
echo "Step 1: Authenticating Agent A..."
AUTH_A_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$AGENT_A_EMAIL\", \"password\": \"$AGENT_A_PASSWORD\"}")

TOKEN_A=$(get_json_field "$AUTH_A_RESPONSE" "access_token")

if [ -z "$TOKEN_A" ] || [ "$TOKEN_A" == "null" ]; then
    echo -e "${RED}✗ FATAL${NC}: Agent A authentication failed"
    exit 1
fi

echo -e "${GREEN}✓${NC} Agent A authenticated"

# ==============================================================================
# STEP 2: Authenticate Agent B
# ==============================================================================
echo "Step 2: Authenticating Agent B..."
AUTH_B_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$AGENT_B_EMAIL\", \"password\": \"$AGENT_B_PASSWORD\"}")

TOKEN_B=$(get_json_field "$AUTH_B_RESPONSE" "access_token")

if [ -z "$TOKEN_B" ] || [ "$TOKEN_B" == "null" ]; then
    echo -e "${RED}✗ FATAL${NC}: Agent B authentication failed"
    exit 1
fi

echo -e "${GREEN}✓${NC} Agent B authenticated"
echo ""

# ==============================================================================
# TEST 1: Agent A creates a lead
# ==============================================================================
echo "Test 1: Agent A creates lead"
CREATE_A_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN_A" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Lead belonging to Agent A",
        "phone": "+5511933221100",
        "email": "lead.agentA@example.com"
    }')

LEAD_A_ID=$(get_json_field "$CREATE_A_RESPONSE" "id")

if [ -n "$LEAD_A_ID" ] && [ "$LEAD_A_ID" != "null" ]; then
    print_result "Agent A creates lead" "PASS"
else
    print_result "Agent A creates lead" "FAIL" "No lead ID returned"
    exit 1
fi

# ==============================================================================
# TEST 2: Agent B creates a lead
# ==============================================================================
echo "Test 2: Agent B creates lead"
CREATE_B_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN_B" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Lead belonging to Agent B",
        "phone": "+5511922110099",
        "email": "lead.agentB@example.com"
    }')

LEAD_B_ID=$(get_json_field "$CREATE_B_RESPONSE" "id")

if [ -n "$LEAD_B_ID" ] && [ "$LEAD_B_ID" != "null" ]; then
    print_result "Agent B creates lead" "PASS"
else
    print_result "Agent B creates lead" "FAIL" "No lead ID returned"
    exit 1
fi

# ==============================================================================
# TEST 3: Agent A lists leads - should see only own lead
# ==============================================================================
echo "Test 3: Agent A lists leads (should see only own)"
LIST_A_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN_A")

TOTAL_A=$(get_json_field "$LIST_A_RESPONSE" "total")

# Agent A should see their own leads but NOT Agent B's lead
if [[ "$LIST_A_RESPONSE" == *"$LEAD_A_ID"* ]] && [[ "$LIST_A_RESPONSE" != *"$LEAD_B_ID"* ]]; then
    print_result "Agent A sees only own leads" "PASS"
elif [ -n "$TOTAL_A" ] && [ "$TOTAL_A" != "null" ]; then
    # Fallback: If agent A has leads, check if agent B's lead is NOT in the list
    if [[ "$LIST_A_RESPONSE" != *"Lead belonging to Agent B"* ]]; then
        print_result "Agent A sees only own leads" "PASS"
    else
        print_result "Agent A sees only own leads" "FAIL" "Agent A can see Agent B's lead"
    fi
else
    print_result "Agent A sees only own leads" "FAIL" "Cannot determine isolation"
fi

# ==============================================================================
# TEST 4: Agent B lists leads - should see only own lead
# ==============================================================================
echo "Test 4: Agent B lists leads (should see only own)"
LIST_B_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN_B")

# Agent B should see their own leads but NOT Agent A's lead
if [[ "$LIST_B_RESPONSE" == *"$LEAD_B_ID"* ]] && [[ "$LIST_B_RESPONSE" != *"$LEAD_A_ID"* ]]; then
    print_result "Agent B sees only own leads" "PASS"
elif [[ "$LIST_B_RESPONSE" != *"Lead belonging to Agent A"* ]]; then
    print_result "Agent B sees only own leads" "PASS"
else
    print_result "Agent B sees only own leads" "FAIL" "Agent B can see Agent A's lead"
fi

# ==============================================================================
# TEST 5: Agent A tries to GET Agent B's lead directly (should fail)
# ==============================================================================
echo "Test 5: Agent A tries to access Agent B's lead"
ACCESS_B_LEAD_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_B_ID" \
    -H "Authorization: Bearer $TOKEN_A")

if [[ "$ACCESS_B_LEAD_RESPONSE" == *"error"* ]] || [[ "$ACCESS_B_LEAD_RESPONSE" == *"403"* ]] || [[ "$ACCESS_B_LEAD_RESPONSE" == *"404"* ]] || [[ "$ACCESS_B_LEAD_RESPONSE" == *"not found"* ]]; then
    print_result "Agent A cannot access Agent B's lead" "PASS"
else
    print_result "Agent A cannot access Agent B's lead" "FAIL" "Agent A accessed Agent B's lead"
fi

# ==============================================================================
# TEST 6: Agent B tries to GET Agent A's lead directly (should fail)
# ==============================================================================
echo "Test 6: Agent B tries to access Agent A's lead"
ACCESS_A_LEAD_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_A_ID" \
    -H "Authorization: Bearer $TOKEN_B")

if [[ "$ACCESS_A_LEAD_RESPONSE" == *"error"* ]] || [[ "$ACCESS_A_LEAD_RESPONSE" == *"403"* ]] || [[ "$ACCESS_A_LEAD_RESPONSE" == *"404"* ]] || [[ "$ACCESS_A_LEAD_RESPONSE" == *"not found"* ]]; then
    print_result "Agent B cannot access Agent A's lead" "PASS"
else
    print_result "Agent B cannot access Agent A's lead" "FAIL" "Agent B accessed Agent A's lead"
fi

# ==============================================================================
# TEST 7: Agent A tries to UPDATE Agent B's lead (should fail)
# ==============================================================================
echo "Test 7: Agent A tries to update Agent B's lead"
UPDATE_B_LEAD_RESPONSE=$(curl -s -X PUT "$BASE_URL/api/v1/leads/$LEAD_B_ID" \
    -H "Authorization: Bearer $TOKEN_A" \
    -H "Content-Type: application/json" \
    -d '{"state": "contacted"}')

if [[ "$UPDATE_B_LEAD_RESPONSE" == *"error"* ]] || [[ "$UPDATE_B_LEAD_RESPONSE" == *"403"* ]] || [[ "$UPDATE_B_LEAD_RESPONSE" == *"404"* ]]; then
    print_result "Agent A cannot update Agent B's lead" "PASS"
else
    print_result "Agent A cannot update Agent B's lead" "FAIL" "Update succeeded (should have failed)"
fi

# ==============================================================================
# TEST 8: Agent A tries to DELETE Agent B's lead (should fail)
# ==============================================================================
echo "Test 8: Agent A tries to delete Agent B's lead"
DELETE_B_LEAD_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/v1/leads/$LEAD_B_ID" \
    -H "Authorization: Bearer $TOKEN_A")

if [[ "$DELETE_B_LEAD_RESPONSE" == *"error"* ]] || [[ "$DELETE_B_LEAD_RESPONSE" == *"403"* ]] || [[ "$DELETE_B_LEAD_RESPONSE" == *"404"* ]]; then
    print_result "Agent A cannot delete Agent B's lead" "PASS"
else
    print_result "Agent A cannot delete Agent B's lead" "FAIL" "Delete succeeded (should have failed)"
fi

# ==============================================================================
# TEST 9: Agent cannot change agent_id on their own lead (FR-022)
# ==============================================================================
echo "Test 9: Agent A tries to change agent_id (should fail)"
CHANGE_AGENT_RESPONSE=$(curl -s -X PUT "$BASE_URL/api/v1/leads/$LEAD_A_ID" \
    -H "Authorization: Bearer $TOKEN_A" \
    -H "Content-Type: application/json" \
    -d '{"agent_id": 999}')

# Verify agent_id was not changed
VERIFY_AGENT_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_A_ID" \
    -H "Authorization: Bearer $TOKEN_A")

if [[ "$VERIFY_AGENT_RESPONSE" == *"agent_id"* ]] && [[ "$VERIFY_AGENT_RESPONSE" != *"999"* ]]; then
    print_result "Agent cannot change agent_id" "PASS"
elif [[ "$CHANGE_AGENT_RESPONSE" == *"error"* ]]; then
    print_result "Agent cannot change agent_id" "PASS"
else
    print_result "Agent cannot change agent_id" "FAIL" "Agent changed agent_id"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Total: $((PASSED + FAILED)) tests"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
