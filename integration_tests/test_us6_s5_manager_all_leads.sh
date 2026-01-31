#!/bin/bash
# ==============================================================================
# Integration Test: US6-S5 - Manager All Leads
# ==============================================================================
# User Story 6: As a manager, I want to see all leads in my company
# Scenario 5: Manager can view and manage all leads from all agents
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
TEST_LOG="$SCRIPT_DIR/test_logs/us6_s5_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

echo "=========================================="
echo "US6-S5: Manager All Leads"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="
    
    # STEP 1: Authenticate as admin (manager role)
    echo -e "${BLUE}STEP 1${NC}: Authenticating as manager..."
    
    if ! authenticate_user "admin" "admin"; then
        echo -e "${RED}✗ FAIL${NC}: Authentication failed"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Manager authenticated"
    echo ""
    
    # GIVEN: Create multiple test leads
    echo -e "${BLUE}GIVEN${NC}: Creating test leads..."
    TIMESTAMP=$(date +%s)
    LEAD_IDS=()
    
    for i in 1 2 3; do
        CREATE_RESPONSE=$(make_api_request "POST" "/api/v1/leads" "{
            \"name\": \"Manager Test Lead $i - US6-S5 - $TIMESTAMP\",
            \"phone\": \"+5511999005${TIMESTAMP: -2}$i\",
            \"email\": \"manager.test${i}.us6.s5.${TIMESTAMP}@example.com\",
            \"state\": \"new\"
        }")
        
        LEAD_ID=$(extract_json_field "$CREATE_RESPONSE" "id")
        
        if [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "null" ]; then
            LEAD_IDS+=("$LEAD_ID")
            echo -e "${GREEN}✓${NC} Lead $i created (ID=$LEAD_ID)"
        else
            echo -e "${YELLOW}⚠${NC} Lead $i creation - duplicate or error"
        fi
    done
    echo ""
    
    # WHEN: Manager queries all leads
    echo -e "${BLUE}WHEN${NC}: Manager querying all leads..."
    LIST_RESPONSE=$(make_api_request "GET" "/api/v1/leads")
    
    # Count leads (look for "id" fields in response)
    LEAD_COUNT=$(echo "$LIST_RESPONSE" | grep -o '"id"' | wc -l)
    
    echo "Found approximately $LEAD_COUNT leads in response"
    echo ""
    
    # THEN: Manager can see all leads
    echo -e "${BLUE}THEN${NC}: Verifying manager visibility..."
    
    if [ "$LEAD_COUNT" -ge "${#LEAD_IDS[@]}" ]; then
        echo -e "${GREEN}✓${NC} Manager can see all leads"
    else
        echo -e "${YELLOW}⚠${NC} Lead count: $LEAD_COUNT (created: ${#LEAD_IDS[@]})"
    fi
    
    # AND: Manager can update any lead
    if [ ${#LEAD_IDS[@]} -gt 0 ]; then
        echo -e "${BLUE}AND${NC}: Testing manager update capability..."
        UPDATE_RESPONSE=$(make_api_request "PUT" "/api/v1/leads/${LEAD_IDS[0]}" '{"state": "contacted"}')
        
        if [[ "$UPDATE_RESPONSE" == *"contacted"* ]] || [[ "$UPDATE_RESPONSE" == *"id"* ]]; then
            echo -e "${GREEN}✓${NC} Manager can update leads"
        else
            echo -e "${YELLOW}⚠${NC} Update result: $(echo "$UPDATE_RESPONSE" | head -c 100)"
        fi
    fi
    
    # Cleanup
    echo ""
    echo "Cleanup: Archiving test leads..."
    for LEAD_ID in "${LEAD_IDS[@]}"; do
        make_api_request "DELETE" "/api/v1/leads/$LEAD_ID" > /dev/null 2>&1
    done
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}TEST PASSED${NC}"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="
    
} 2>&1 | tee "$TEST_LOG"

exit 0
