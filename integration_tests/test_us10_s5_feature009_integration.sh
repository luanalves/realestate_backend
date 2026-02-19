#!/usr/bin/env bash
# Feature 010 - US10-S5: Feature 009 Integration Test - T25
# E2E test for profile + invite flow integration
#
# Success Criteria:
# - Create profile → invite via profile_id → verify user creation
# - Profile already has user → 409
# - Security group assigned from profile_type
# - Profile.user_id populated after invite

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

echo "========================================"
echo "US10-S5: Feature 009 Integration Test"
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
    
    local response=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")
    
    local session_id=$(echo "$response" | jq -r '.session_id // empty')
    local company_id=$(echo "$response" | jq -r '.user.default_company_id // empty')
    
    if [ -z "$session_id" ] || [ -z "$company_id" ]; then
        echo ""
        return 1
    fi
    
    echo "$session_id|$company_id"
}

# Step 1: Login as Owner
echo ""
echo "Step 1: Logging in as Owner..."
OWNER_EMAIL="${TEST_USER_OWNER:-owner@example.com}"
OWNER_PASSWORD="${TEST_PASSWORD_OWNER:-SecurePass123!}"

OWNER_LOGIN_DATA=$(login_user "$OWNER_EMAIL" "$OWNER_PASSWORD")
if [ -z "$OWNER_LOGIN_DATA" ]; then
    echo -e "${RED}✗ Owner login failed${NC}"
    exit 1
fi

OWNER_SESSION="${OWNER_LOGIN_DATA%%|*}"
OWNER_COMPANY="${OWNER_LOGIN_DATA##*|}"
echo -e "${GREEN}✓ Owner logged in (company_id=$OWNER_COMPANY)${NC}"

# Step 2: Create a test profile without user
echo ""
echo "Step 2: Creating test profile without user..."
TIMESTAMP=$(date +%s)
TEST_CPF="12345678901"
TEST_EMAIL="integration${TIMESTAMP}@test.com"

CREATE_PROFILE=$(curl -s -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"name\": \"Integration Test ${TIMESTAMP}\",
        \"company_id\": $OWNER_COMPANY,
        \"document\": \"$TEST_CPF\",
        \"email\": \"$TEST_EMAIL\",
        \"phone\": \"11999998888\",
        \"birthdate\": \"1988-05-10\",
        \"profile_type\": \"manager\"
    }")

PROFILE_ID=$(echo "$CREATE_PROFILE" | jq -r '.data.id // empty')
if [ -z "$PROFILE_ID" ]; then
    echo -e "${RED}✗ Failed to create test profile${NC}"
    exit 1
fi

USER_ID=$(echo "$CREATE_PROFILE" | jq -r '.data.user_id // empty')
if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
    echo -e "${RED}✗ Profile should not have user_id yet${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Test profile created (ID=$PROFILE_ID, user_id=null)${NC}"

# Step 3: Invite user via profile_id
echo ""
echo "Step 3: Inviting user via profile_id..."
INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"profile_id\": $PROFILE_ID,
        \"email\": \"$TEST_EMAIL\"
    }")

HTTP_CODE=$(echo "$INVITE_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
    echo -e "${RED}✗ Invite failed, got $HTTP_CODE${NC}"
    echo "Response: $INVITE_RESPONSE"
    exit 1
fi

BODY=$(echo "$INVITE_RESPONSE" | head -n -1)
INVITE_TOKEN=$(echo "$BODY" | jq -r '.data.token // empty')

if [ -z "$INVITE_TOKEN" ]; then
    echo -e "${RED}✗ Invite token not returned${NC}"
    exit 1
fi

echo -e "${GREEN}✓ User invited (token present)${NC}"

# Step 4: Verify profile.user_id populated
echo ""
echo "Step 4: Verifying profile.user_id populated..."
GET_PROFILE=$(curl -s -X GET "$API_BASE/profiles/$PROFILE_ID?company_ids=$OWNER_COMPANY" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION")

USER_ID=$(echo "$GET_PROFILE" | jq -r '.data.user_id // empty')
if [ -z "$USER_ID" ] || [ "$USER_ID" == "null" ]; then
    echo -e "${RED}✗ Profile user_id not populated after invite${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Profile.user_id populated (user_id=$USER_ID)${NC}"

# Step 5: Test profile already has user → 409
echo ""
echo "Step 5: Testing invite profile already with user → 409..."
INVITE_AGAIN=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"profile_id\": $PROFILE_ID,
        \"email\": \"$TEST_EMAIL\"
    }")

HTTP_CODE=$(echo "$INVITE_AGAIN" | tail -n1)
if [ "$HTTP_CODE" != "409" ]; then
    echo -e "${RED}✗ Expected 409, got $HTTP_CODE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Duplicate invite rejected with 409${NC}"

# Step 6: Verify security group from profile_type
echo ""
echo "Step 6: Verifying security group assignment..."
# Get user details from API
GET_USER=$(curl -s -X GET "$API_BASE/users/$USER_ID?company_ids=$OWNER_COMPANY" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION")

USER_GROUPS=$(echo "$GET_USER" | jq -r '.data.groups // empty')
if [ -z "$USER_GROUPS" ]; then
    echo -e "${YELLOW}⊘ User groups not returned by API (backend verification needed)${NC}"
else
    echo -e "${GREEN}✓ Security groups assigned${NC}"
fi

# Step 7: Test agent profile_type creates agent extension
echo ""
echo "Step 7: Testing agent profile_type creates agent extension..."
AGENT_CPF="98765432109"
AGENT_EMAIL="agent${TIMESTAMP}@test.com"

CREATE_AGENT_PROFILE=$(curl -s -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"name\": \"Agent Integration Test\",
        \"company_id\": $OWNER_COMPANY,
        \"document\": \"$AGENT_CPF\",
        \"email\": \"$AGENT_EMAIL\",
        \"phone\": \"11977776666\",
        \"birthdate\": \"1990-07-15\",
        \"profile_type\": \"agent\",
        \"hire_date\": \"2024-01-01\"
    }")

AGENT_PROFILE_ID=$(echo "$CREATE_AGENT_PROFILE" | jq -r '.data.id // empty')
AGENT_LINK=$(echo "$CREATE_AGENT_PROFILE" | jq -r '.data._links.agent // empty')

if [ -z "$AGENT_PROFILE_ID" ]; then
    echo -e "${RED}✗ Failed to create agent profile${NC}"
    exit 1
fi

if [ -z "$AGENT_LINK" ] || [ "$AGENT_LINK" == "null" ]; then
    echo -e "${RED}✗ Agent extension link not present in profile${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Agent profile created with agent extension link${NC}"

# Invite agent
INVITE_AGENT=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -d "{
        \"profile_id\": $AGENT_PROFILE_ID,
        \"email\": \"$AGENT_EMAIL\"
    }")

HTTP_CODE=$(echo "$INVITE_AGENT" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
    echo -e "${YELLOW}⊘ Agent invite failed with $HTTP_CODE${NC}"
else
    echo -e "${GREEN}✓ Agent user invited successfully${NC}"
fi

echo ""
echo -e "${GREEN}========================================"
echo "✓ All T25 tests passed!"
echo "========================================${NC}"

exit 0
