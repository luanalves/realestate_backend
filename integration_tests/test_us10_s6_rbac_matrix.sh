#!/usr/bin/env bash
# Feature 010 - US10-S6: RBAC Matrix Test - T26
# E2E test for comprehensive authorization testing
#
# Authorization Matrix:
# - Owner → can create all 9 profiles (201)
# - Manager → can create 5 operational types (201), admin types (403)
# - Agent → can create owner+portal (201), others (403)
#
# 9 Profile Types: owner, manager, agent, receptionist, prospector, 
#                  administrator, legal, financial, portal

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
echo "US10-S6: RBAC Matrix Authorization Test"
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
    local profile_type="$3"
    local name="$4"
    local document="$5"
    local email="$6"
    
    local response=$(curl -s -m 30 -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $session" \
        -d "{
            \"name\": \"$name\",
            \"company_id\": $company,
            \"document\": \"$document\",
            \"email\": \"$email\",
            \"phone\": \"11999998888\",
            \"birthdate\": \"1990-01-01\",
            \"profile_type\": \"$profile_type\"
        }")
    
    echo "$response"
}

# Function to generate valid CPF
generate_cpf() {
    local base=$1
    local digits=$(echo "$base" | sed 's/./& /g')
    
    # First check digit
    local sum1=0
    local weight=10
    for d in $digits; do
        sum1=$((sum1 + d * weight))
        weight=$((weight - 1))
    done
    local digit1=$(( (sum1 * 10) % 11 ))
    if [ $digit1 -eq 10 ]; then digit1=0; fi
    
    # Second check digit
    local sum2=0
    weight=11
    for d in $digits; do
        sum2=$((sum2 + d * weight))
        weight=$((weight - 1))
    done
    sum2=$((sum2 + digit1 * 2))
    local digit2=$(( (sum2 * 10) % 11 ))
    if [ $digit2 -eq 10 ]; then digit2=0; fi
    
    echo "${base}${digit1}${digit2}"
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

# Step 2: Owner creates all 9 profile types → 201
echo ""
echo "Step 2: Testing Owner can create all 9 profile types..."
TIMESTAMP=$(date +%s)
PROFILE_TYPES=("owner" "director" "manager" "agent" "receptionist" "prospector" "financial" "legal" "portal")
PASSED=0

for idx in "${!PROFILE_TYPES[@]}"; do
    ptype="${PROFILE_TYPES[$idx]}"
    # Generate unique CPF base using timestamp and index (random 9-digit number)
    doc_base=$(printf "%09d" $(( (TIMESTAMP % 100000000) + idx * 1000 )))
    doc_num=$(generate_cpf "$doc_base")
    email="owner_creates_${ptype}_${TIMESTAMP}@test.com"
    
    result=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$ptype" "Owner Creates ${ptype}" "$doc_num" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        PASSED=$((PASSED + 1))
    else
        response_body=$(echo "$result" | sed '$d')
        echo -e "${RED}✗ Owner failed to create $ptype (HTTP $http_code)${NC}"
        echo "  Response: $response_body"
    fi
done

if [ $PASSED -ne 9 ]; then
    echo -e "${RED}✗ Owner should create all 9 types, got $PASSED/9${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Owner created all 9 profile types (9/9)${NC}"

# ============================================================
# Step 3: Setup Manager user via invite flow
# ============================================================
echo ""
echo "Step 3: Setting up Manager user via invite flow..."

# Create Manager profile first
MANAGER_PROFILE_DOC=$(generate_cpf "$(printf "%09d" $(( (TIMESTAMP % 100000000) + 9001 )))")
MANAGER_EMAIL="rbac_manager_${TIMESTAMP}@test.com"

MANAGER_PROFILE_RESPONSE=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "manager" "RBAC Test Manager" "$MANAGER_PROFILE_DOC" "$MANAGER_EMAIL")
MANAGER_PROFILE_HTTP=$(echo "$MANAGER_PROFILE_RESPONSE" | tail -n1)

if [ "$MANAGER_PROFILE_HTTP" != "200" ] && [ "$MANAGER_PROFILE_HTTP" != "201" ]; then
    echo -e "${RED}✗ Failed to create Manager profile (HTTP $MANAGER_PROFILE_HTTP)${NC}"
    exit 1
fi

MANAGER_PROFILE_ID=$(echo "$MANAGER_PROFILE_RESPONSE" | sed '$d' | jq -r '.data.id // empty')
echo -e "${GREEN}✓ Manager profile created (ID=$MANAGER_PROFILE_ID)${NC}"

# Invite Manager via Feature 009 API
MANAGER_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -H "X-Company-ID: $OWNER_COMPANY" \
    -d "{
        \"name\": \"RBAC Test Manager\",
        \"email\": \"$MANAGER_EMAIL\",
        \"document\": \"$MANAGER_PROFILE_DOC\",
        \"profile\": \"manager\"
    }")

MANAGER_INVITE_HTTP=$(echo "$MANAGER_INVITE_RESPONSE" | tail -n1)
if [ "$MANAGER_INVITE_HTTP" != "200" ] && [ "$MANAGER_INVITE_HTTP" != "201" ]; then
    echo -e "${RED}✗ Failed to invite Manager (HTTP $MANAGER_INVITE_HTTP)${NC}"
    echo "Response body:"
    echo "$MANAGER_INVITE_RESPONSE" | sed '$d' | jq '.'
    exit 1
fi

MANAGER_USER_ID=$(echo "$MANAGER_INVITE_RESPONSE" | sed '$d' | jq -r '.data.id // empty')
echo -e "${GREEN}✓ Manager invited (user_id=$MANAGER_USER_ID)${NC}"

# Generate known token for testing (simulate email token)
MANAGER_RAW_TOKEN="rbac-manager-${TIMESTAMP}-${MANAGER_USER_ID}"
MANAGER_TOKEN_HASH=$(printf "%s" "$MANAGER_RAW_TOKEN" | shasum -a 256 | awk '{print $1}')

# Update token in database
docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF > /dev/null 2>&1
    UPDATE thedevkitchen_password_token
    SET token = '$MANAGER_TOKEN_HASH'
    WHERE user_id = $MANAGER_USER_ID
    AND token_type = 'invite'
    AND status = 'pending';
EOF

# Set Manager password
MANAGER_PASSWORD="Manager123!"
MANAGER_SET_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$MANAGER_RAW_TOKEN\",
        \"password\": \"$MANAGER_PASSWORD\",
        \"confirm_password\": \"$MANAGER_PASSWORD\"
    }")

MANAGER_SET_PASSWORD_HTTP=$(echo "$MANAGER_SET_PASSWORD_RESPONSE" | tail -n1)
if [ "$MANAGER_SET_PASSWORD_HTTP" != "200" ]; then
    echo -e "${RED}✗ Failed to set Manager password (HTTP $MANAGER_SET_PASSWORD_HTTP)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Manager password set${NC}"

# Login as Manager
MANAGER_LOGIN_DATA=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASSWORD")
if [ -z "$MANAGER_LOGIN_DATA" ]; then
    echo -e "${RED}✗ Manager login failed${NC}"
    exit 1
fi

MANAGER_SESSION="${MANAGER_LOGIN_DATA%%|*}"
MANAGER_COMPANY="${MANAGER_LOGIN_DATA##*|}"
echo -e "${GREEN}✓ Manager logged in (company_id=$MANAGER_COMPANY)${NC}"

# ============================================================
# Step 4: Test Manager RBAC - Allowed profiles (5 types)
# ============================================================
echo ""
echo "Step 4: Testing Manager can create 5 operational types..."
MANAGER_ALLOWED=("agent" "prospector" "receptionist" "financial" "legal")
MANAGER_ALLOWED_PASSED=0

for idx in "${!MANAGER_ALLOWED[@]}"; do
    ptype="${MANAGER_ALLOWED[$idx]}"
    doc_base=$(printf "%09d" $(( (TIMESTAMP % 100000000) + 10000 + idx )))
    doc_num=$(generate_cpf "$doc_base")
    email="manager_creates_${ptype}_${TIMESTAMP}@test.com"
    
    result=$(create_profile "$MANAGER_SESSION" "$MANAGER_COMPANY" "$ptype" "Manager Creates ${ptype}" "$doc_num" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        MANAGER_ALLOWED_PASSED=$((MANAGER_ALLOWED_PASSED + 1))
    else
        response_body=$(echo "$result" | sed '$d')
        echo -e "${RED}✗ Manager failed to create $ptype (HTTP $http_code)${NC}"
        echo "  Response: $response_body"
    fi
done

if [ $MANAGER_ALLOWED_PASSED -ne 5 ]; then
    echo -e "${RED}✗ Manager should create 5 types, got $MANAGER_ALLOWED_PASSED/5${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Manager created all 5 allowed types (5/5)${NC}"

# ============================================================
# Step 5: Test Manager RBAC - Forbidden profiles (4 types)
# ============================================================
echo ""
echo "Step 5: Testing Manager cannot create 4 admin types (403)..."
MANAGER_FORBIDDEN=("owner" "director" "manager" "portal")
MANAGER_FORBIDDEN_PASSED=0

for idx in "${!MANAGER_FORBIDDEN[@]}"; do
    ptype="${MANAGER_FORBIDDEN[$idx]}"
    doc_base=$(printf "%09d" $(( (TIMESTAMP % 100000000) + 20000 + idx )))
    doc_num=$(generate_cpf "$doc_base")
    email="manager_forbidden_${ptype}_${TIMESTAMP}@test.com"
    
    result=$(create_profile "$MANAGER_SESSION" "$MANAGER_COMPANY" "$ptype" "Manager Forbidden ${ptype}" "$doc_num" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "403" ]; then
        MANAGER_FORBIDDEN_PASSED=$((MANAGER_FORBIDDEN_PASSED + 1))
    else
        response_body=$(echo "$result" | sed '$d')
        echo -e "${RED}✗ Manager should get 403 for $ptype, got HTTP $http_code${NC}"
        echo "  Response: $response_body"
    fi
done

if [ $MANAGER_FORBIDDEN_PASSED -ne 4 ]; then
    echo -e "${RED}✗ Manager should be blocked from 4 types, got $MANAGER_FORBIDDEN_PASSED/4${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Manager blocked from all 4 forbidden types (4/4 = 403)${NC}"

# ============================================================
# Step 6: Setup Agent user via invite flow
# ============================================================
echo ""
echo "Step 6: Setting up Agent user via invite flow..."

# Create Agent profile
AGENT_PROFILE_DOC=$(generate_cpf "$(printf "%09d" $(( (TIMESTAMP % 100000000) + 30001 )))")
AGENT_EMAIL="rbac_agent_${TIMESTAMP}@test.com"

AGENT_PROFILE_RESPONSE=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "agent" "RBAC Test Agent" "$AGENT_PROFILE_DOC" "$AGENT_EMAIL")
AGENT_PROFILE_HTTP=$(echo "$AGENT_PROFILE_RESPONSE" | tail -n1)

if [ "$AGENT_PROFILE_HTTP" != "200" ] && [ "$AGENT_PROFILE_HTTP" != "201" ]; then
    echo -e "${RED}✗ Failed to create Agent profile (HTTP $AGENT_PROFILE_HTTP)${NC}"
    exit 1
fi

AGENT_PROFILE_ID=$(echo "$AGENT_PROFILE_RESPONSE" | sed '$d' | jq -r '.data.id // empty')
echo -e "${GREEN}✓ Agent profile created (ID=$AGENT_PROFILE_ID)${NC}"

# Invite Agent
AGENT_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $OWNER_SESSION" \
    -H "X-Company-ID: $OWNER_COMPANY" \
    -d "{
        \"name\": \"RBAC Test Agent\",
        \"email\": \"$AGENT_EMAIL\",
        \"document\": \"$AGENT_PROFILE_DOC\",
        \"profile\": \"agent\"
    }")

AGENT_INVITE_HTTP=$(echo "$AGENT_INVITE_RESPONSE" | tail -n1)
if [ "$AGENT_INVITE_HTTP" != "200" ] && [ "$AGENT_INVITE_HTTP" != "201" ]; then
    echo -e "${RED}✗ Failed to invite Agent (HTTP $AGENT_INVITE_HTTP)${NC}"
    echo "Response body:"
    echo "$AGENT_INVITE_RESPONSE" | sed '$d' | jq '.'
    exit 1
fi

AGENT_USER_ID=$(echo "$AGENT_INVITE_RESPONSE" | sed '$d' | jq -r '.data.id // empty')
echo -e "${GREEN}✓ Agent invited (user_id=$AGENT_USER_ID)${NC}"

# Generate token for Agent
AGENT_RAW_TOKEN="rbac-agent-${TIMESTAMP}-${AGENT_USER_ID}"
AGENT_TOKEN_HASH=$(printf "%s" "$AGENT_RAW_TOKEN" | shasum -a 256 | awk '{print $1}')

docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF > /dev/null 2>&1
    UPDATE thedevkitchen_password_token
    SET token = '$AGENT_TOKEN_HASH'
    WHERE user_id = $AGENT_USER_ID
    AND token_type = 'invite'
    AND status = 'pending';
EOF

# Set Agent password
AGENT_PASSWORD="Agent123!"
AGENT_SET_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$AGENT_RAW_TOKEN\",
        \"password\": \"$AGENT_PASSWORD\",
        \"confirm_password\": \"$AGENT_PASSWORD\"
    }")

AGENT_SET_PASSWORD_HTTP=$(echo "$AGENT_SET_PASSWORD_RESPONSE" | tail -n1)
if [ "$AGENT_SET_PASSWORD_HTTP" != "200" ]; then
    echo -e "${RED}✗ Failed to set Agent password (HTTP $AGENT_SET_PASSWORD_HTTP)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Agent password set${NC}"

# Login as Agent
AGENT_LOGIN_DATA=$(login_user "$AGENT_EMAIL" "$AGENT_PASSWORD")
if [ -z "$AGENT_LOGIN_DATA" ]; then
    echo -e "${RED}✗ Agent login failed${NC}"
    exit 1
fi

AGENT_SESSION="${AGENT_LOGIN_DATA%%|*}"
AGENT_COMPANY="${AGENT_LOGIN_DATA##*|}"
echo -e "${GREEN}✓ Agent logged in (company_id=$AGENT_COMPANY)${NC}"

# ============================================================
# Step 7: Test Agent RBAC - Allowed profiles (2 types)
# ============================================================
echo ""
echo "Step 7: Testing Agent can create 2 types (owner=property owner, portal=tenant)..."
AGENT_ALLOWED=("owner" "portal")
AGENT_ALLOWED_PASSED=0

for idx in "${!AGENT_ALLOWED[@]}"; do
    ptype="${AGENT_ALLOWED[$idx]}"
    doc_base=$(printf "%09d" $(( (TIMESTAMP % 100000000) + 40000 + idx )))
    doc_num=$(generate_cpf "$doc_base")
    email="agent_creates_${ptype}_${TIMESTAMP}@test.com"
    
    if [ "$ptype" == "portal" ]; then
        # Portal requires additional fields
        result=$(curl -s -m 30 -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $BEARER_TOKEN" \
            -H "X-Openerp-Session-Id: $AGENT_SESSION" \
            -d "{
                \"name\": \"Agent Creates ${ptype}\",
                \"company_id\": $AGENT_COMPANY,
                \"document\": \"$doc_num\",
                \"email\": \"$email\",
                \"phone\": \"11999998888\",
                \"birthdate\": \"1990-01-01\",
                \"profile_type\": \"$ptype\",
                \"occupation\": \"Tenant\"
            }")
    else
        result=$(create_profile "$AGENT_SESSION" "$AGENT_COMPANY" "$ptype" "Agent Creates ${ptype}" "$doc_num" "$email")
    fi
    
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        AGENT_ALLOWED_PASSED=$((AGENT_ALLOWED_PASSED + 1))
    else
        response_body=$(echo "$result" | sed '$d')
        echo -e "${RED}✗ Agent failed to create $ptype (HTTP $http_code)${NC}"
        echo "  Response: $response_body"
    fi
done

if [ $AGENT_ALLOWED_PASSED -ne 2 ]; then
    echo -e "${RED}✗ Agent should create 2 types, got $AGENT_ALLOWED_PASSED/2${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Agent created all 2 allowed types (2/2)${NC}"

# ============================================================
# Step 8: Test Agent RBAC - Forbidden profiles (7 types)
# ============================================================
echo ""
echo "Step 8: Testing Agent cannot create 7 other types (403)..."
AGENT_FORBIDDEN=("director" "manager" "agent" "prospector" "receptionist" "financial" "legal")
AGENT_FORBIDDEN_PASSED=0

for idx in "${!AGENT_FORBIDDEN[@]}"; do
    ptype="${AGENT_FORBIDDEN[$idx]}"
    doc_base=$(printf "%09d" $(( (TIMESTAMP % 100000000) + 50000 + idx )))
    doc_num=$(generate_cpf "$doc_base")
    email="agent_forbidden_${ptype}_${TIMESTAMP}@test.com"
    
    result=$(create_profile "$AGENT_SESSION" "$AGENT_COMPANY" "$ptype" "Agent Forbidden ${ptype}" "$doc_num" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "403" ]; then
        AGENT_FORBIDDEN_PASSED=$((AGENT_FORBIDDEN_PASSED + 1))
    else
        response_body=$(echo "$result" | sed '$d')
        echo -e "${RED}✗ Agent should get 403 for $ptype, got HTTP $http_code${NC}"
        echo "  Response: $response_body"
    fi
done

if [ $AGENT_FORBIDDEN_PASSED -ne 7 ]; then
    echo -e "${RED}✗ Agent should be blocked from 7 types, got $AGENT_FORBIDDEN_PASSED/7${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Agent blocked from all 7 forbidden types (7/7 = 403)${NC}"

# ============================================================
# Summary
# ============================================================
echo ""
echo -e "${GREEN}========================================"
echo "✓ T26 RBAC Authorization tests passed!"
echo "========================================${NC}"
echo ""
echo "Summary:"
echo "  ✓ Owner: Can create all 9 profile types (9/9)"
echo "  ✓ Manager: Can create 5 operational types (5/5), blocked from 4 admin types (4/4)"
echo "  ✓ Agent: Can create 2 types (owner+portal) (2/2), blocked from 7 types (7/7)"
echo ""

exit 0
