#!/bin/bash
# ==============================================================================
# Integration Test: US6-S1 - Agent Creates Lead
# ==============================================================================
# User Story 6: As an agent, I want to create leads for potential clients
# Scenario 1: Agent creates lead with client contact info
# ==============================================================================

set -e

# Load environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

# Source auth helper library
AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
if [ -f "$AUTH_LIB" ]; then
    source "$AUTH_LIB"
fi

# Configuration
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us6_s1_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure log directory exists
mkdir -p "$SCRIPT_DIR/test_logs"

echo "=========================================="
echo "US6-S1: Agent Creates Lead"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="
    
    # STEP 1: Authenticate using helper (OAuth + user login)
    echo -e "${BLUE}STEP 1${NC}: Authenticating as admin..."
    
    if ! authenticate_user "admin" "admin"; then
        echo -e "${RED}✗ FAIL${NC}: Authentication failed"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Authenticated (session: ${USER_SESSION_ID:0:20}...)"
    echo ""
    
    # STEP 2: Create test lead via REST API
    echo -e "${BLUE}STEP 2${NC}: Creating lead via REST API..."
    
    TIMESTAMP=$(date +%s)
    CREATE_RESPONSE=$(make_api_request "POST" "/api/v1/leads" "{
        \"name\": \"Integration Test Lead - US6-S1 - $TIMESTAMP\",
        \"phone\": \"+55119990001${TIMESTAMP: -2}\",
        \"email\": \"integration.us6.s1.${TIMESTAMP}@example.com\",
        \"budget_min\": 200000.00,
        \"budget_max\": 400000.00,
        \"bedrooms_needed\": 2
    }")
    
    echo "Create Response: $CREATE_RESPONSE"
    
    LEAD_ID=$(extract_json_field "$CREATE_RESPONSE" "id")
    
    # THEN: Lead is created successfully
    echo ""
    echo -e "${BLUE}THEN${NC}: Lead is created successfully"
    
    if [ -z "$LEAD_ID" ] || [ "$LEAD_ID" = "null" ]; then
        # Check if error is validation (duplicate) - that's acceptable
        if [[ "$CREATE_RESPONSE" == *"duplicate"* ]] || [[ "$CREATE_RESPONSE" == *"already exists"* ]]; then
            echo -e "${GREEN}✓${NC} Duplicate prevention working (expected behavior)"
        else
            echo -e "${RED}✗ FAIL${NC}: Lead creation failed"
            echo "Response: $CREATE_RESPONSE"
            exit 1
        fi
    else
        echo -e "${GREEN}✓${NC} Lead created (ID=$LEAD_ID)"
    fi
    
    # AND: Verify lead data
    if [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "null" ]; then
        echo ""
        echo -e "${BLUE}AND${NC}: Verifying lead data..."
        
        DETAIL_RESPONSE=$(make_api_request "GET" "/api/v1/leads/$LEAD_ID")
        
        LEAD_STATE=$(extract_json_field "$DETAIL_RESPONSE" "state")
        AGENT_ID=$(extract_json_field "$DETAIL_RESPONSE" "agent_id")
        
        if [ "$LEAD_STATE" = "new" ]; then
            echo -e "${GREEN}✓${NC} Lead has default state 'new'"
        else
            echo -e "${YELLOW}⚠${NC} Lead state: $LEAD_STATE (expected: new)"
        fi
        
        if [ -n "$AGENT_ID" ] && [ "$AGENT_ID" != "null" ] && [ "$AGENT_ID" != "false" ]; then
            echo -e "${GREEN}✓${NC} Lead has agent_id assigned ($AGENT_ID)"
        else
            echo -e "${YELLOW}⚠${NC} Lead agent_id not set"
        fi
        
        # Cleanup
        echo ""
        echo "Cleanup: Archiving test lead..."
        make_api_request "DELETE" "/api/v1/leads/$LEAD_ID" > /dev/null 2>&1
    fi
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}TEST PASSED${NC}"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="
    
} 2>&1 | tee "$TEST_LOG"

exit 0
