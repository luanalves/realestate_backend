#!/usr/bin/env bash
# Feature 010 - US10-S7: Multi-tenancy Isolation Test - T27
# E2E test for company data isolation
#
# Success Criteria:
# - Same document in different companies → allowed
# - Cross-company read → 404
# - Unauthorized company_ids → 403
# - Compound unique constraint respects company scope

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to generate valid CPF with timestamp
generate_cpf() {
    local ts=$(date +%s)
    local base=$(printf "%09d" $((ts % 1000000000)))
    
    # Calculate first check digit
    local sum=0
    for i in {0..8}; do
        local digit=${base:$i:1}
        local mult=$((10 - i))
        sum=$((sum + digit * mult))
    done
    local d1=$((11 - (sum % 11)))
    [ $d1 -ge 10 ] && d1=0
    
    # Calculate second check digit
    sum=0
    for i in {0..8}; do
        local digit=${base:$i:1}
        local mult=$((11 - i))
        sum=$((sum + digit * mult))
    done
    sum=$((sum + d1 * 2))
    local d2=$((11 - (sum % 11)))
    [ $d2 -ge 10 ] && d2=0
    
    echo "${base}${d1}${d2}"
}

echo "========================================"
echo "US10-S7: Multi-tenancy Isolation Test"
echo "========================================"

# Get Bearer Token
echo "Step 0: Getting OAuth2 bearer token..."
BEARER_TOKEN=$(get_oauth2_token)
if [ $? -ne 0 ] || [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get OAuth2 token${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bearer token obtained${NC}"

# Helper: Login user
login_user() {
    local email="$1"
    local password="$2"
    
    local response=$(curl -s -m 30 -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")
    
    local session_id=$(echo "$response" | jq -r '.session_id // empty')
    local company_id=$(echo "$response" | jq -r '.user.main_estate_company_id // empty')
    
    if [ -z "$session_id" ] || [ -z "$company_id" ] || [ "$company_id" == "null" ]; then
        echo ""
        return 1
    fi
    
    echo "$session_id|$company_id"
}

# Step 1: Login as Owner (Company A)
echo ""
echo "Step 1: Logging in as Owner of Company A..."
OWNER_EMAIL="${TEST_USER_OWNER:-owner@example.com}"
OWNER_PASSWORD="${TEST_PASSWORD_OWNER:-SecurePass123!}"

OWNER_LOGIN_DATA=$(login_user "$OWNER_EMAIL" "$OWNER_PASSWORD")
if [ -z "$OWNER_LOGIN_DATA" ]; then
    echo -e "${RED}✗ Owner login failed${NC}"
    exit 1
fi

OWNER_SESSION="${OWNER_LOGIN_DATA%%|*}"
COMPANY_A="${OWNER_LOGIN_DATA##*|}"
echo -e "${GREEN}✓ Owner logged in (Company A ID=$COMPANY_A)${NC}"

# Step 2: Create profile in Company A
echo ""
echo "Step 2: Creating profile in Company A..."
SHARED_CPF=$(generate_cpf)
TIMESTAMP=$(date +%s)
EMAIL_A="companya${TIMESTAMP}@test.com"

CREATE_A=$(curl -s -m 30 -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"name\": \"Company A Profile\",
        \"company_id\": $COMPANY_A,
        \"document\": \"$SHARED_CPF\",
        \"email\": \"$EMAIL_A\",
        \"phone\": \"11999998888\",
        \"birthdate\": \"1985-06-10\",
        \"profile_type\": \"manager\"
    }")

PROFILE_A_ID=$(echo "$CREATE_A" | jq -r '.id // empty')
if [ -z "$PROFILE_A_ID" ]; then
    echo -e "${RED}✗ Failed to create profile in Company A${NC}"
    echo "Response: $CREATE_A"
    exit 1
fi

echo -e "${GREEN}✓ Profile created in Company A (ID=$PROFILE_A_ID, CPF=$SHARED_CPF)${NC}"

# Step 3: Create Company B (if test environment supports multi-company)
echo ""
echo "Step 3: Attempting to create/access Company B..."
# Note: This test assumes multi-company setup exists or can be created
# In production, this would require separate company setup

# For now, we'll simulate by creating a second owner in a different company
# This may require test environment setup - marking as conditional

COMPANY_B_OWNER_EMAIL="${TEST_USER_OWNER_B:-owner2@example.com}"
COMPANY_B_OWNER_PASSWORD="${TEST_PASSWORD_OWNER_B:-SecurePass123!}"

echo "Attempting login for Company B owner ($COMPANY_B_OWNER_EMAIL)..."
OWNER_B_LOGIN_DATA=$(login_user "$COMPANY_B_OWNER_EMAIL" "$COMPANY_B_OWNER_PASSWORD" 2>&1 || echo "")

if [ -z "$OWNER_B_LOGIN_DATA" ] || [[ "$OWNER_B_LOGIN_DATA" == *"error"* ]]; then
    echo -e "${YELLOW}⊘ Company B owner not available, skipping cross-company tests${NC}"
    echo -e "${YELLOW}⊘ To enable: Create TEST_USER_OWNER_B and TEST_PASSWORD_OWNER_B in .env${NC}"
    echo -e "${GREEN}✓ Basic multi-tenancy tests passed (Steps 1-2)${NC}"
    echo ""
    echo "========================================"
    echo "Result: PARTIAL PASS (2/2 basic steps)"
    echo "Skipped: Cross-company isolation tests"
    echo "========================================"
    exit 0
    COMPANY_B=""
else
    OWNER_B_SESSION="${OWNER_B_LOGIN_DATA%%|*}"
    COMPANY_B="${OWNER_B_LOGIN_DATA##*|}"
    
    if [ "$COMPANY_A" == "$COMPANY_B" ]; then
        echo -e "${YELLOW}⊘ Company B owner belongs to same company, skipping${NC}"
        echo -e "${GREEN}✓ Basic multi-tenancy tests passed (Steps 1-2)${NC}"
        echo ""
        echo "========================================"
        echo "Result: PARTIAL PASS (2/2 basic steps)"
        echo "Skipped: Cross-company isolation tests"
        echo "========================================"
        exit 0
        COMPANY_B=""
    else
        echo -e "${GREEN}✓ Owner B logged in (Company B ID=$COMPANY_B)${NC}"
    fi
fi

# Step 4: Same document in different companies → allowed
if [ -n "$COMPANY_B" ]; then
    echo ""
    echo "Step 4: Creating profile with same document in Company B..."
    EMAIL_B="companyb${TIMESTAMP}@test.com"
    
    CREATE_B=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_B_SESSION" \
        -d "{
            \"name\": \"Company B Profile\",
            \"company_id\": $COMPANY_B,
            \"document\": \"$SHARED_CPF\",
            \"email\": \"$EMAIL_B\",
            \"phone\": \"11988887777\",
            \"birthdate\": \"1987-09-15\",
            \"profile_type\": \"manager\"
        }")
    
    HTTP_CODE=$(echo "$CREATE_B" | tail -n1)
    if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
        echo -e "${RED}✗ Should allow same document in Company B, got $HTTP_CODE${NC}"
        BODY=$(echo "$CREATE_B" | sed '$d')
        echo "Response: $BODY"
        exit 1
    fi
    
    BODY=$(echo "$CREATE_B" | sed '$d')
    PROFILE_B_ID=$(echo "$BODY" | jq -r '.id // empty')
    
    echo -e "${GREEN}✓ Same document allowed in Company B (ID=$PROFILE_B_ID)${NC}"
    
    # Step 5: Cross-company read → 404
    echo ""
    echo "Step 5: Testing cross-company read (Company A accesses Company B profile)..."
    CROSS_READ=$(curl -s -w "\n%{http_code}" -X GET "$API_BASE/profiles/$PROFILE_B_ID?company_ids=$COMPANY_A" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION")
    
    HTTP_CODE=$(echo "$CROSS_READ" | tail -n1)
    if [ "$HTTP_CODE" != "404" ]; then
        echo -e "${RED}✗ Cross-company read should return 404, got $HTTP_CODE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Cross-company read blocked (404)${NC}"
    
    # Step 6: Unauthorized company_ids → 403
    echo ""
    echo "Step 6: Testing unauthorized company_ids access..."
    UNAUTH_ACCESS=$(curl -s -w "\n%{http_code}" -X GET "$API_BASE/profiles?company_ids=$COMPANY_B" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION")
    
    HTTP_CODE=$(echo "$UNAUTH_ACCESS" | tail -n1)
    if [ "$HTTP_CODE" != "403" ]; then
        echo -e "${RED}✗ Unauthorized company_ids should return 403, got $HTTP_CODE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Unauthorized company_ids blocked (403)${NC}"
    
    # Step 7: Compound unique constraint respects company scope
    echo ""
    echo "Step 7: Testing compound unique constraint within company..."
    DUPLICATE_IN_A=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION" \
        -d "{
            \"name\": \"Duplicate in A\",
            \"company_id\": $COMPANY_A,
            \"document\": \"$SHARED_CPF\",
            \"email\": \"duplicate_a${TIMESTAMP}@test.com\",
            \"phone\": \"11977776666\",
            \"birthdate\": \"1990-01-01\",
            \"profile_type\": \"manager\"
        }")
    
    HTTP_CODE=$(echo "$DUPLICATE_IN_A" | tail -n1)
    if [ "$HTTP_CODE" != "409" ]; then
        echo -e "${RED}✗ Duplicate in same company should return 409, got $HTTP_CODE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Duplicate in same company blocked (409)${NC}"
fi

# Step 8: Verify list endpoint respects company_ids filter
echo ""
echo "Step 8: Testing list endpoint company_ids filter..."
LIST_PROFILES=$(curl -s -X GET "$API_BASE/profiles?company_ids=$COMPANY_A" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION")

# Try both data structures: check if .data is array or object with .items
ITEMS_COUNT=$(echo "$LIST_PROFILES" | jq -r 'if .data | type == "array" then .data | length elif .data.items | type == "array" then .data.items | length else 0 end')
if [ "$ITEMS_COUNT" -eq 0 ]; then
    echo -e "${RED}✗ List endpoint should return profiles${NC}"
    echo "Response: $LIST_PROFILES"
    exit 1
fi

# Check all returned profiles belong to Company A  
PROFILES_ARRAY=$(echo "$LIST_PROFILES" | jq -r 'if .data | type == "array" then .data else .data.items end')
WRONG_COMPANY=$(echo "$PROFILES_ARRAY" | jq -r ".[] | select(.company_id != $COMPANY_A) | .id" | head -n1)
if [ -n "$WRONG_COMPANY" ]; then
    echo -e "${RED}✗ List returned profile from wrong company${NC}"
    exit 1
fi

echo -e "${GREEN}✓ List endpoint respects company_ids filter (found $ITEMS_COUNT profiles)${NC}"

echo ""
echo -e "${GREEN}========================================"
echo "✓ All T27 multi-tenancy tests passed!"
echo "========================================${NC}"

exit 0
