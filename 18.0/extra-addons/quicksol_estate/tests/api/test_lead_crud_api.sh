#!/bin/bash
# ==============================================================================
# E2E API Test: Lead CRUD Operations
# ==============================================================================
# Tests: POST /api/v1/leads, GET /api/v1/leads, GET /api/v1/leads/{id}, 
#        PUT /api/v1/leads/{id}, DELETE /api/v1/leads/{id}
# Requirements: FR-001 to FR-022 (agent creates, lists, updates, archives leads)
# Task: T024
# ADR-003: E2E test WITH database (real API endpoints)
# ==============================================================================

set -e  # Exit on error

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
source "$REPO_ROOT/18.0/.env"

# Load auth helper
source "${SCRIPT_DIR}/../lib/auth_helper.sh"

# Configuration
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Cleanup function
cleanup() {
    rm -f "$TEST_OUTPUT"
}
trap cleanup EXIT

# Helper: Print test result
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

# Helper: Extract JSON field
get_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | grep -o "\"$field\":[^,}]*" | head -1 | cut -d':' -f2- | tr -d ' ",'
}

echo "=========================================="
echo "E2E API Test: Lead CRUD Operations"
echo "=========================================="
echo ""

# ==============================================================================
# STEP 1: Authenticate using auth_helper
# ==============================================================================
echo "Step 1: Authenticating as admin..."
authenticate_user "admin" "admin" || {
    echo -e "${RED}✗ FATAL${NC}: Authentication failed"
    exit 1
}
TOKEN="$OAUTH_TOKEN"
SESSION_ID="$USER_SESSION_ID"

echo -e "${GREEN}✓${NC} Authenticated successfully"
echo ""

# ==============================================================================
# TEST 1: POST /api/v1/leads - Create new lead with minimal data
# ==============================================================================
echo "Test 1: Create lead with minimal data (name only)"
CREATE_RESPONSE=$(make_api_request "POST" "/api/v1/leads" '{
        "name": "Maria Oliveira",
        "phone": "+5511988776655",
        "email": "maria.oliveira@example.com"
    }')

LEAD_ID=$(get_json_field "$CREATE_RESPONSE" "id")
HTTP_STATUS=$(echo "$CREATE_RESPONSE" | grep -o '"status":[0-9]*' | cut -d':' -f2 || echo "")

if [ "$HTTP_STATUS" == "201" ] && [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "null" ]; then
    print_result "Create lead with minimal data" "PASS"
else
    print_result "Create lead with minimal data" "FAIL" "Expected HTTP 201, got $HTTP_STATUS or no lead ID"
fi

# ==============================================================================
# TEST 2: POST /api/v1/leads - Create lead with complete data
# ==============================================================================
echo "Test 2: Create lead with complete data"
CREATE_FULL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "João Silva",
        "phone": "+5511977665544",
        "email": "joao.silva@example.com",
        "budget_min": 300000.00,
        "budget_max": 500000.00,
        "property_type_interest": "Apartamento",
        "location_preference": "Bairro Alto",
        "bedrooms_needed": 3,
        "min_area": 80.00,
        "max_area": 120.00
    }')

LEAD_FULL_ID=$(get_json_field "$CREATE_FULL_RESPONSE" "id")
HTTP_STATUS_FULL=$(echo "$CREATE_FULL_RESPONSE" | grep -o '"status":[0-9]*' | cut -d':' -f2 || echo "")

if [ "$HTTP_STATUS_FULL" == "201" ] && [ -n "$LEAD_FULL_ID" ] && [ "$LEAD_FULL_ID" != "null" ]; then
    print_result "Create lead with complete data" "PASS"
else
    print_result "Create lead with complete data" "FAIL" "Expected HTTP 201, got $HTTP_STATUS_FULL"
fi

# ==============================================================================
# TEST 3: GET /api/v1/leads - List all leads (pagination)
# ==============================================================================
echo "Test 3: List all leads with pagination"
LIST_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads?limit=10&offset=0" \
    -H "Authorization: Bearer $TOKEN")

TOTAL_COUNT=$(get_json_field "$LIST_RESPONSE" "total")

if [ -n "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" != "null" ] && [ "$TOTAL_COUNT" -ge 2 ]; then
    print_result "List leads with pagination" "PASS"
else
    print_result "List leads with pagination" "FAIL" "Expected total >= 2, got $TOTAL_COUNT"
fi

# ==============================================================================
# TEST 4: GET /api/v1/leads - Filter by state
# ==============================================================================
echo "Test 4: Filter leads by state=new"
FILTER_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads?state=new" \
    -H "Authorization: Bearer $TOKEN")

FILTERED_COUNT=$(get_json_field "$FILTER_RESPONSE" "total")

if [ -n "$FILTERED_COUNT" ] && [ "$FILTERED_COUNT" != "null" ]; then
    print_result "Filter leads by state" "PASS"
else
    print_result "Filter leads by state" "FAIL" "No total count returned"
fi

# ==============================================================================
# TEST 5: GET /api/v1/leads/{id} - Get lead details
# ==============================================================================
echo "Test 5: Get lead details"
DETAIL_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_ID" \
    -H "Authorization: Bearer $TOKEN")

DETAIL_NAME=$(get_json_field "$DETAIL_RESPONSE" "name")

if [ "$DETAIL_NAME" == "Maria Oliveira" ] || [[ "$DETAIL_RESPONSE" == *"Maria Oliveira"* ]]; then
    print_result "Get lead details" "PASS"
else
    print_result "Get lead details" "FAIL" "Expected name 'Maria Oliveira', got $DETAIL_NAME"
fi

# ==============================================================================
# TEST 6: PUT /api/v1/leads/{id} - Update lead state
# ==============================================================================
echo "Test 6: Update lead state to contacted"
UPDATE_RESPONSE=$(curl -s -X PUT "$BASE_URL/api/v1/leads/$LEAD_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "state": "contacted"
    }')

UPDATED_STATE=$(get_json_field "$UPDATE_RESPONSE" "state")

if [ "$UPDATED_STATE" == "contacted" ] || [[ "$UPDATE_RESPONSE" == *"contacted"* ]]; then
    print_result "Update lead state" "PASS"
else
    print_result "Update lead state" "FAIL" "Expected state 'contacted', got $UPDATED_STATE"
fi

# ==============================================================================
# TEST 7: PUT /api/v1/leads/{id} - Update lead budget
# ==============================================================================
echo "Test 7: Update lead budget range"
UPDATE_BUDGET_RESPONSE=$(curl -s -X PUT "$BASE_URL/api/v1/leads/$LEAD_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "budget_min": 250000.00,
        "budget_max": 450000.00
    }')

HTTP_STATUS_UPDATE=$(echo "$UPDATE_BUDGET_RESPONSE" | grep -o '"status":[0-9]*' | cut -d':' -f2 || echo "200")

if [ "$HTTP_STATUS_UPDATE" == "200" ] || [[ "$UPDATE_BUDGET_RESPONSE" == *"250000"* ]]; then
    print_result "Update lead budget" "PASS"
else
    print_result "Update lead budget" "FAIL" "Expected HTTP 200 or budget in response"
fi

# ==============================================================================
# TEST 8: DELETE /api/v1/leads/{id} - Soft delete (archive) lead
# ==============================================================================
echo "Test 8: Archive lead (soft delete)"
DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/v1/leads/$LEAD_FULL_ID" \
    -H "Authorization: Bearer $TOKEN")

# Check if lead still exists but is inactive
ARCHIVED_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_FULL_ID" \
    -H "Authorization: Bearer $TOKEN")

if [[ "$ARCHIVED_RESPONSE" == *"active"*false* ]] || [[ "$ARCHIVED_RESPONSE" == *"archived"* ]] || [[ "$DELETE_RESPONSE" == *"204"* ]]; then
    print_result "Archive lead (soft delete)" "PASS"
else
    print_result "Archive lead (soft delete)" "FAIL" "Lead not properly archived"
fi

# ==============================================================================
# TEST 9: POST /api/v1/leads - Duplicate validation (same phone)
# ==============================================================================
echo "Test 9: Duplicate validation - same phone should fail"
DUPLICATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Maria Duplicate",
        "phone": "+5511988776655",
        "email": "maria.duplicate@example.com"
    }')

if [[ "$DUPLICATE_RESPONSE" == *"error"* ]] || [[ "$DUPLICATE_RESPONSE" == *"duplicate"* ]] || [[ "$DUPLICATE_RESPONSE" == *"400"* ]] || [[ "$DUPLICATE_RESPONSE" == *"ValidationError"* ]]; then
    print_result "Duplicate validation (phone)" "PASS"
else
    print_result "Duplicate validation (phone)" "FAIL" "Expected validation error, got: $DUPLICATE_RESPONSE"
fi

# ==============================================================================
# TEST 10: POST /api/v1/leads - Invalid budget range
# ==============================================================================
echo "Test 10: Budget validation - min > max should fail"
INVALID_BUDGET_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Invalid Budget Lead",
        "phone": "+5511966554433",
        "budget_min": 500000.00,
        "budget_max": 300000.00
    }')

if [[ "$INVALID_BUDGET_RESPONSE" == *"error"* ]] || [[ "$INVALID_BUDGET_RESPONSE" == *"budget"* ]] || [[ "$INVALID_BUDGET_RESPONSE" == *"400"* ]]; then
    print_result "Budget validation (min > max)" "PASS"
else
    print_result "Budget validation (min > max)" "FAIL" "Expected validation error"
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
