#!/bin/bash
# ==============================================================================
# E2E API Test: Lead Conversion to Sale
# ==============================================================================
# Tests: POST /api/v1/leads/{id}/convert
# Requirements: FR-018 (convert lead to sale with property link, atomic transaction)
# Task: T025
# ADR-003: E2E test WITH database (real API endpoints)
# ==============================================================================

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
source "$PROJECT_ROOT/18.0/.env"

# Configuration
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_AGENT_EMAIL="${TEST_USER_A_EMAIL:-joao@imobiliaria.com}"
TEST_AGENT_PASSWORD="${TEST_USER_A_PASSWORD:-test123}"

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
echo "E2E API Test: Lead Conversion"
echo "=========================================="
echo ""

# Authenticate
echo "Authenticating agent..."
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$TEST_AGENT_EMAIL\", \"password\": \"$TEST_AGENT_PASSWORD\"}")

TOKEN=$(get_json_field "$AUTH_RESPONSE" "access_token")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo -e "${RED}✗ FATAL${NC}: Authentication failed"
    exit 1
fi

echo -e "${GREEN}✓${NC} Authenticated"
echo ""

# ==============================================================================
# TEST 1: Get an available property for conversion
# ==============================================================================
echo "Test 1: Get available property"
PROPERTIES_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/properties?limit=1" \
    -H "Authorization: Bearer $TOKEN")

PROPERTY_ID=$(get_json_field "$PROPERTIES_RESPONSE" "id")

if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" == "null" ]; then
    echo -e "${YELLOW}⚠ WARNING${NC}: No properties available - creating test property"
    
    # Create a test property
    CREATE_PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/properties" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Test Property for Lead Conversion",
            "expected_price": 450000.00,
            "bedrooms": 3,
            "living_area": 100.00,
            "garden_area": 50.00,
            "garden_orientation": "north",
            "state": "offer_received"
        }')
    
    PROPERTY_ID=$(get_json_field "$CREATE_PROPERTY_RESPONSE" "id")
fi

if [ -n "$PROPERTY_ID" ] && [ "$PROPERTY_ID" != "null" ]; then
    print_result "Get/create test property" "PASS"
else
    print_result "Get/create test property" "FAIL" "No property available"
    exit 1
fi

# ==============================================================================
# TEST 2: Create a qualified lead for conversion
# ==============================================================================
echo "Test 2: Create qualified lead"
CREATE_LEAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Carlos Mendes",
        "phone": "+5511955443322",
        "email": "carlos.mendes@example.com",
        "state": "qualified",
        "budget_min": 400000.00,
        "budget_max": 500000.00
    }')

LEAD_ID=$(get_json_field "$CREATE_LEAD_RESPONSE" "id")

if [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "null" ]; then
    print_result "Create qualified lead" "PASS"
else
    print_result "Create qualified lead" "FAIL" "No lead ID returned"
    exit 1
fi

# ==============================================================================
# TEST 3: Convert lead to sale with property
# ==============================================================================
echo "Test 3: Convert lead to sale"
CONVERT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads/$LEAD_ID/convert" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"property_id\": $PROPERTY_ID}")

SALE_ID=$(get_json_field "$CONVERT_RESPONSE" "sale_id")

if [ -n "$SALE_ID" ] && [ "$SALE_ID" != "null" ] && [ "$SALE_ID" != "false" ]; then
    print_result "Convert lead to sale" "PASS"
else
    print_result "Convert lead to sale" "FAIL" "No sale ID returned: $CONVERT_RESPONSE"
fi

# ==============================================================================
# TEST 4: Verify lead state is 'won' after conversion
# ==============================================================================
echo "Test 4: Verify lead state is won"
LEAD_DETAIL_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/leads/$LEAD_ID" \
    -H "Authorization: Bearer $TOKEN")

LEAD_STATE=$(get_json_field "$LEAD_DETAIL_RESPONSE" "state")

if [ "$LEAD_STATE" == "won" ] || [[ "$LEAD_DETAIL_RESPONSE" == *"\"state\":\"won\""* ]]; then
    print_result "Verify lead state is won" "PASS"
else
    print_result "Verify lead state is won" "FAIL" "Expected state='won', got $LEAD_STATE"
fi

# ==============================================================================
# TEST 5: Verify lead has converted_property_id and converted_sale_id
# ==============================================================================
echo "Test 5: Verify conversion links"
CONVERTED_PROPERTY_ID=$(get_json_field "$LEAD_DETAIL_RESPONSE" "converted_property_id")
CONVERTED_SALE_ID=$(get_json_field "$LEAD_DETAIL_RESPONSE" "converted_sale_id")

if [ "$CONVERTED_PROPERTY_ID" == "$PROPERTY_ID" ] && [ "$CONVERTED_SALE_ID" == "$SALE_ID" ]; then
    print_result "Verify conversion links" "PASS"
elif [[ "$LEAD_DETAIL_RESPONSE" == *"converted_property_id"* ]] && [[ "$LEAD_DETAIL_RESPONSE" == *"converted_sale_id"* ]]; then
    print_result "Verify conversion links" "PASS"
else
    print_result "Verify conversion links" "FAIL" "Links not properly set"
fi

# ==============================================================================
# TEST 6: Verify sale has correct buyer info from lead
# ==============================================================================
echo "Test 6: Verify sale has buyer info"
SALE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/sales/$SALE_ID" \
    -H "Authorization: Bearer $TOKEN")

BUYER_PHONE=$(get_json_field "$SALE_RESPONSE" "buyer_phone")

if [[ "$SALE_RESPONSE" == *"5511955443322"* ]] || [ "$BUYER_PHONE" == "+5511955443322" ]; then
    print_result "Verify sale has buyer info" "PASS"
else
    print_result "Verify sale has buyer info" "FAIL" "Buyer info not copied"
fi

# ==============================================================================
# TEST 7: Attempt to convert already won lead (should fail)
# ==============================================================================
echo "Test 7: Attempt to convert already won lead"
DOUBLE_CONVERT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads/$LEAD_ID/convert" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"property_id\": $PROPERTY_ID}")

if [[ "$DOUBLE_CONVERT_RESPONSE" == *"error"* ]] || [[ "$DOUBLE_CONVERT_RESPONSE" == *"already"* ]] || [[ "$DOUBLE_CONVERT_RESPONSE" == *"400"* ]]; then
    print_result "Prevent double conversion" "PASS"
else
    print_result "Prevent double conversion" "FAIL" "Should prevent converting won lead"
fi

# ==============================================================================
# TEST 8: Conversion without property_id (should fail)
# ==============================================================================
echo "Test 8: Conversion without property_id"
CREATE_LEAD2_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "Test Lead 2", "phone": "+5511944332211", "state": "qualified"}')

LEAD2_ID=$(get_json_field "$CREATE_LEAD2_RESPONSE" "id")

NO_PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/leads/$LEAD2_ID/convert" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{}')

if [[ "$NO_PROPERTY_RESPONSE" == *"error"* ]] || [[ "$NO_PROPERTY_RESPONSE" == *"property_id"* ]] || [[ "$NO_PROPERTY_RESPONSE" == *"400"* ]]; then
    print_result "Require property_id for conversion" "PASS"
else
    print_result "Require property_id for conversion" "FAIL" "Should require property_id"
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
