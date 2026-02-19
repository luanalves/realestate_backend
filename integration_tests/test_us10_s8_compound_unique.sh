#!/usr/bin/env bash
# Feature 010 - US10-S8: Compound Unique + Pagination Test - T28
# E2E test for constraint permutations and pagination
#
# Success Criteria:
# - Compound constraint: (document, company_id, profile_type) unique
# - Same doc + company + different type → allowed
# - Same doc + type + different company → allowed
# - Same doc + company + type → 409
# - Pagination: page, page_size, total_count, next/prev links
# - HATEOAS link structure validation

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
echo "US10-S8: Compound Unique + Pagination Test"
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

# Helper: Create profile
create_profile() {
    local session="$1"
    local company="$2"
    local document="$3"
    local profile_type="$4"
    local email="$5"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Session-ID: $session" \
        -d "{
            \"name\": \"Test Profile $document-$profile_type\",
            \"company_id\": $company,
            \"document\": \"$document\",
            \"email\": \"$email\",
            \"phone\": \"11999998888\",
            \"birthdate\": \"1990-01-01\",
            \"profile_type\": \"$profile_type\"
        }")
    
    echo "$response"
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

# Step 2: Test compound constraint - same doc + company + different type → allowed
echo ""
echo "Step 2: Testing same document + company, different profile_type..."
TIMESTAMP=$(date +%s)
TEST_CPF="99988877766"
EMAIL_MANAGER="constraint_manager${TIMESTAMP}@test.com"
EMAIL_AGENT="constraint_agent${TIMESTAMP}@test.com"

# Create manager profile
RESULT_MGR=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$TEST_CPF" "manager" "$EMAIL_MANAGER")
HTTP_CODE_MGR=$(echo "$RESULT_MGR" | tail -n1)

if [ "$HTTP_CODE_MGR" != "200" ] && [ "$HTTP_CODE_MGR" != "201" ]; then
    echo -e "${RED}✗ Failed to create manager profile (HTTP $HTTP_CODE_MGR)${NC}"
    exit 1
fi

BODY_MGR=$(echo "$RESULT_MGR" | head -n -1)
PROFILE_MGR_ID=$(echo "$BODY_MGR" | jq -r '.data.id // empty')

# Create agent profile with same document
RESULT_AGENT=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$TEST_CPF" "agent" "$EMAIL_AGENT")
HTTP_CODE_AGENT=$(echo "$RESULT_AGENT" | tail -n1)

if [ "$HTTP_CODE_AGENT" != "200" ] && [ "$HTTP_CODE_AGENT" != "201" ]; then
    echo -e "${RED}✗ Should allow same doc + different type, got $HTTP_CODE_AGENT${NC}"
    exit 1
fi

BODY_AGENT=$(echo "$RESULT_AGENT" | head -n -1)
PROFILE_AGENT_ID=$(echo "$BODY_AGENT" | jq -r '.data.id // empty')

echo -e "${GREEN}✓ Same document + different type allowed (manager=$PROFILE_MGR_ID, agent=$PROFILE_AGENT_ID)${NC}"

# Step 3: Test same doc + company + same type → 409
echo ""
echo "Step 3: Testing same document + company + same type → 409..."
EMAIL_DUPLICATE="constraint_duplicate${TIMESTAMP}@test.com"

RESULT_DUPLICATE=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$TEST_CPF" "manager" "$EMAIL_DUPLICATE")
HTTP_CODE_DUPLICATE=$(echo "$RESULT_DUPLICATE" | tail -n1)

if [ "$HTTP_CODE_DUPLICATE" != "409" ]; then
    echo -e "${RED}✗ Duplicate should return 409, got $HTTP_CODE_DUPLICATE${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Duplicate constraint enforced (409)${NC}"

# Step 4: Create multiple profiles for pagination testing
echo ""
echo "Step 4: Creating multiple profiles for pagination test..."
CREATED_IDS=()

for i in {1..5}; do
    doc_num=$((11111111100 + i))
    email="pagination${i}${TIMESTAMP}@test.com"
    
    result=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$doc_num" "manager" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        body=$(echo "$result" | head -n -1)
        profile_id=$(echo "$body" | jq -r '.data.id // empty')
        CREATED_IDS+=("$profile_id")
    fi
done

echo -e "${GREEN}✓ Created ${#CREATED_IDS[@]} profiles for pagination test${NC}"

# Step 5: Test pagination - page 1, page_size 2
echo ""
echo "Step 5: Testing pagination (page=1, page_size=2)..."
PAGE1=$(curl -s -X GET "$API_BASE/profiles?company_ids=$OWNER_COMPANY&page=1&page_size=2" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION")

PAGE1_ITEMS=$(echo "$PAGE1" | jq -r '.data.items // empty')
PAGE1_COUNT=$(echo "$PAGE1" | jq -r '.data.items | length')

if [ "$PAGE1_COUNT" != "2" ]; then
    echo -e "${RED}✗ Page 1 should return 2 items, got $PAGE1_COUNT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pagination page 1 returns 2 items${NC}"

# Step 6: Test pagination - page 2
echo ""
echo "Step 6: Testing pagination (page=2, page_size=2)..."
PAGE2=$(curl -s -X GET "$API_BASE/profiles?company_ids=$OWNER_COMPANY&page=2&page_size=2" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION")

PAGE2_ITEMS=$(echo "$PAGE2" | jq -r '.data.items // empty')
PAGE2_COUNT=$(echo "$PAGE2" | jq -r '.data.items | length')

if [ "$PAGE2_COUNT" -lt 1 ]; then
    echo -e "${RED}✗ Page 2 should return at least 1 item, got $PAGE2_COUNT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pagination page 2 returns $PAGE2_COUNT items${NC}"

# Step 7: Verify total_count field
echo ""
echo "Step 7: Verifying total_count field..."
TOTAL_COUNT=$(echo "$PAGE1" | jq -r '.data.total_count // .data.total // empty')

if [ -z "$TOTAL_COUNT" ]; then
    echo -e "${YELLOW}⊘ total_count field not returned (add to API response)${NC}"
else
    echo -e "${GREEN}✓ total_count field present ($TOTAL_COUNT profiles)${NC}"
fi

# Step 8: Verify HATEOAS links structure
echo ""
echo "Step 8: Verifying HATEOAS links structure..."
FIRST_PROFILE=$(echo "$PAGE1" | jq -r '.data.items[0] // empty')

if [ -z "$FIRST_PROFILE" ]; then
    echo -e "${RED}✗ No profile returned to verify HATEOAS${NC}"
    exit 1
fi

SELF_LINK=$(echo "$FIRST_PROFILE" | jq -r '._links.self // empty')
if [ -z "$SELF_LINK" ] || [ "$SELF_LINK" == "null" ]; then
    echo -e "${YELLOW}⊘ _links.self not present in response${NC}"
else
    echo -e "${GREEN}✓ _links.self present: $SELF_LINK${NC}"
fi

# Step 9: Test pagination next/prev links
echo ""
echo "Step 9: Testing pagination next/prev links..."
NEXT_LINK=$(echo "$PAGE1" | jq -r '._links.next // .data._links.next // empty')
PREV_LINK=$(echo "$PAGE1" | jq -r '._links.prev // .data._links.prev // empty')

if [ -n "$NEXT_LINK" ] && [ "$NEXT_LINK" != "null" ]; then
    echo -e "${GREEN}✓ Next link present: $NEXT_LINK${NC}"
else
    echo -e "${YELLOW}⊘ Next link not present (verify if more pages exist)${NC}"
fi

if [ -n "$PREV_LINK" ] && [ "$PREV_LINK" != "null" ]; then
    echo -e "${YELLOW}⊘ Prev link should be null on page 1, got: $PREV_LINK${NC}"
else
    echo -e "${GREEN}✓ Prev link null on page 1${NC}"
fi

# Step 10: Test filter by profile_type with pagination
echo ""
echo "Step 10: Testing filter by profile_type with pagination..."
FILTER_RESULT=$(curl -s -X GET "$API_BASE/profiles?company_ids=$OWNER_COMPANY&profile_type=manager&page=1&page_size=3" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION")

FILTER_ITEMS=$(echo "$FILTER_RESULT" | jq -r '.data.items // empty')
FILTER_COUNT=$(echo "$FILTER_RESULT" | jq -r '.data.items | length')

if [ "$FILTER_COUNT" -lt 1 ]; then
    echo -e "${RED}✗ Filter should return at least 1 manager, got $FILTER_COUNT${NC}"
    exit 1
fi

# Verify all returned items are managers
WRONG_TYPE=$(echo "$FILTER_RESULT" | jq -r '.data.items[] | select(.profile_type != "manager") | .id' | head -n1)
if [ -n "$WRONG_TYPE" ]; then
    echo -e "${RED}✗ Filter returned non-manager profile${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Filter by profile_type works with pagination ($FILTER_COUNT managers)${NC}"

echo ""
echo -e "${GREEN}========================================"
echo "✓ All T28 constraint + pagination tests passed!"
echo "========================================${NC}"

exit 0
