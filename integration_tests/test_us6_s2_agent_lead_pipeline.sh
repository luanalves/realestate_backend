#!/bin/bash
# ==============================================================================
# Integration Test: US6-S2 - Agent Lead Pipeline (State Transitions)
# ==============================================================================
# User Story 6: As an agent, I want to track leads through the sales pipeline
# Scenario 2: Agent moves lead through states: new → contacted → qualified → lost
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
TEST_LOG="$SCRIPT_DIR/test_logs/us6_s2_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

echo "=========================================="
echo "US6-S2: Agent Lead Pipeline"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="
    
    # STEP 1: Authenticate
    echo -e "${BLUE}STEP 1${NC}: Authenticating as admin..."
    
    if ! authenticate_user "admin" "admin"; then
        echo -e "${RED}✗ FAIL${NC}: Authentication failed"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Authenticated"
    echo ""
    
    # GIVEN: Create a new lead
    echo -e "${BLUE}GIVEN${NC}: Creating a new lead..."
    TIMESTAMP=$(date +%s)
    CREATE_RESPONSE=$(make_api_request "POST" "/api/v1/leads" "{
        \"name\": \"Pipeline Test Lead - US6-S2 - $TIMESTAMP\",
        \"phone\": \"+5511999000${TIMESTAMP: -3}\",
        \"email\": \"pipeline.us6.s2.${TIMESTAMP}@example.com\"
    }")
    
    LEAD_ID=$(extract_json_field "$CREATE_RESPONSE" "id")
    
    if [ -z "$LEAD_ID" ] || [ "$LEAD_ID" = "null" ]; then
        echo -e "${RED}✗ FAIL${NC}: Lead creation failed"
        echo "Response: $CREATE_RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Lead created (ID=$LEAD_ID, state=new)"
    echo ""
    
    # WHEN: Move lead to 'contacted' state
    echo -e "${BLUE}WHEN${NC}: Moving lead to 'contacted'..."
    UPDATE_RESPONSE=$(make_api_request "PUT" "/api/v1/leads/$LEAD_ID" '{"state": "contacted"}')
    
    DETAIL_RESPONSE=$(make_api_request "GET" "/api/v1/leads/$LEAD_ID")
    STATE=$(extract_json_field "$DETAIL_RESPONSE" "state")
    
    if [ "$STATE" = "contacted" ]; then
        echo -e "${GREEN}✓${NC} Lead moved to 'contacted'"
    else
        echo -e "${RED}✗ FAIL${NC}: Expected state='contacted', got '$STATE'"
        exit 1
    fi
    echo ""
    
    # WHEN: Move lead to 'qualified' state
    echo -e "${BLUE}WHEN${NC}: Qualifying the lead..."
    make_api_request "PUT" "/api/v1/leads/$LEAD_ID" '{"state": "qualified"}' > /dev/null
    
    DETAIL_RESPONSE=$(make_api_request "GET" "/api/v1/leads/$LEAD_ID")
    STATE=$(extract_json_field "$DETAIL_RESPONSE" "state")
    
    if [ "$STATE" = "qualified" ]; then
        echo -e "${GREEN}✓${NC} Lead moved to 'qualified'"
    else
        echo -e "${RED}✗ FAIL${NC}: Expected state='qualified', got '$STATE'"
        exit 1
    fi
    echo ""
    
    # WHEN: Mark lead as 'lost'
    echo -e "${BLUE}WHEN${NC}: Marking lead as 'lost'..."
    make_api_request "PUT" "/api/v1/leads/$LEAD_ID" '{"state": "lost", "lost_reason": "Client found cheaper option"}' > /dev/null
    
    DETAIL_RESPONSE=$(make_api_request "GET" "/api/v1/leads/$LEAD_ID")
    STATE=$(extract_json_field "$DETAIL_RESPONSE" "state")
    
    if [ "$STATE" = "lost" ]; then
        echo -e "${GREEN}✓${NC} Lead marked as 'lost'"
    else
        echo -e "${RED}✗ FAIL${NC}: Expected state='lost', got '$STATE'"
        exit 1
    fi
    
    # Cleanup
    echo ""
    echo "Cleanup: Archiving test lead..."
    make_api_request "DELETE" "/api/v1/leads/$LEAD_ID" > /dev/null 2>&1
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}TEST PASSED${NC}"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="
    
} 2>&1 | tee "$TEST_LOG"

exit 0
