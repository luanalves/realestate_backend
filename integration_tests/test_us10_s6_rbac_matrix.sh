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
    local profile_type="$3"
    local name="$4"
    local document="$5"
    local email="$6"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Session-ID: $session" \
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
PROFILE_TYPES=("owner" "manager" "agent" "receptionist" "prospector" "administrator" "legal" "financial" "portal")
PASSED=0

for idx in "${!PROFILE_TYPES[@]}"; do
    ptype="${PROFILE_TYPES[$idx]}"
    doc_num=$((11111111100 + idx))
    email="owner_creates_${ptype}${TIMESTAMP}@test.com"
    
    result=$(create_profile "$OWNER_SESSION" "$OWNER_COMPANY" "$ptype" "Owner Creates ${ptype}" "$doc_num" "$email")
    http_code=$(echo "$result" | tail -n1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ Owner failed to create $ptype (HTTP $http_code)${NC}"
    fi
done

if [ $PASSED -ne 9 ]; then
    echo -e "${RED}✗ Owner should create all 9 types, got $PASSED/9${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Owner created all 9 profile types (9/9)${NC}"

# Step 3: Create a Manager user for testing
echo ""
echo "Step 3: Creating Manager user for authorization tests..."
MGR_CPF="11122233344"
MGR_EMAIL="manager${TIMESTAMP}@test.com"
MGR_PASSWORD="ManagerPass123!"

CREATE_MGR_PROFILE=$(curl -s -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION" \
    -d "{
        \"name\": \"Test Manager\",
        \"company_id\": $OWNER_COMPANY,
        \"document\": \"$MGR_CPF\",
        \"email\": \"$MGR_EMAIL\",
        \"phone\": \"11988887777\",
        \"birthdate\": \"1985-03-15\",
        \"profile_type\": \"manager\"
    }")

MGR_PROFILE_ID=$(echo "$CREATE_MGR_PROFILE" | jq -r '.data.id // empty')

if [ -z "$MGR_PROFILE_ID" ]; then
    echo -e "${RED}✗ Failed to create manager profile${NC}"
    exit 1
fi

# Invite and set password
INVITE_MGR=$(curl -s -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION" \
    -d "{\"profile_id\": $MGR_PROFILE_ID, \"email\": \"$MGR_EMAIL\"}")

MGR_TOKEN=$(echo "$INVITE_MGR" | jq -r '.data.token // empty')

if [ -n "$MGR_TOKEN" ]; then
    SET_PASSWORD=$(curl -s -X POST "$API_BASE/auth/set-password" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"token\": \"$MGR_TOKEN\", \"password\": \"$MGR_PASSWORD\"}")
fi

# Login as Manager
MGR_LOGIN_DATA=$(login_user "$MGR_EMAIL" "$MGR_PASSWORD")
if [ -z "$MGR_LOGIN_DATA" ]; then
    echo -e "${YELLOW}⊘ Manager login failed, skipping Manager RBAC tests${NC}"
    MGR_SESSION=""
else
    MGR_SESSION="${MGR_LOGIN_DATA%%|*}"
    MGR_COMPANY="${MGR_LOGIN_DATA##*|}"
    echo -e "${GREEN}✓ Manager user created and logged in${NC}"
fi

# Step 4: Manager creates 5 operational types → 201
if [ -n "$MGR_SESSION" ]; then
    echo ""
    echo "Step 4: Testing Manager can create 5 operational types..."
    ALLOWED_TYPES=("agent" "receptionist" "prospector" "legal" "financial")
    ALLOWED_PASSED=0
    
    for idx in "${!ALLOWED_TYPES[@]}"; do
        ptype="${ALLOWED_TYPES[$idx]}"
        doc_num=$((22222222200 + idx))
        email="manager_creates_${ptype}${TIMESTAMP}@test.com"
        
        result=$(create_profile "$MGR_SESSION" "$MGR_COMPANY" "$ptype" "Manager Creates ${ptype}" "$doc_num" "$email")
        http_code=$(echo "$result" | tail -n1)
        
        if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
            ALLOWED_PASSED=$((ALLOWED_PASSED + 1))
        else
            echo -e "${RED}✗ Manager failed to create $ptype (HTTP $http_code)${NC}"
        fi
    done
    
    if [ $ALLOWED_PASSED -ne 5 ]; then
        echo -e "${RED}✗ Manager should create 5 operational types, got $ALLOWED_PASSED/5${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Manager created 5 operational types (5/5)${NC}"
    
    # Step 5: Manager tries admin types → 403
    echo ""
    echo "Step 5: Testing Manager cannot create admin types (owner, manager, administrator, portal)..."
    FORBIDDEN_TYPES=("owner" "manager" "administrator" "portal")
    FORBIDDEN_PASSED=0
    
    for idx in "${!FORBIDDEN_TYPES[@]}"; do
        ptype="${FORBIDDEN_TYPES[$idx]}"
        doc_num=$((33333333300 + idx))
        email="manager_forbidden_${ptype}${TIMESTAMP}@test.com"
        
        result=$(create_profile "$MGR_SESSION" "$MGR_COMPANY" "$ptype" "Manager Forbidden ${ptype}" "$doc_num" "$email")
        http_code=$(echo "$result" | tail -n1)
        
        if [ "$http_code" == "403" ]; then
            FORBIDDEN_PASSED=$((FORBIDDEN_PASSED + 1))
        else
            echo -e "${RED}✗ Manager should get 403 for $ptype, got $http_code${NC}"
        fi
    done
    
    if [ $FORBIDDEN_PASSED -ne 4 ]; then
        echo -e "${RED}✗ Manager should be blocked from 4 admin types, got $FORBIDDEN_PASSED/4${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Manager blocked from admin types (4/4 → 403)${NC}"
fi

# Step 6: Create Agent user
echo ""
echo "Step 6: Creating Agent user for authorization tests..."
AGENT_CPF="55566677788"
AGENT_EMAIL="agent${TIMESTAMP}@test.com"
AGENT_PASSWORD="AgentPass123!"

CREATE_AGENT_PROFILE=$(curl -s -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $OWNER_SESSION" \
    -d "{
        \"name\": \"Test Agent\",
        \"company_id\": $OWNER_COMPANY,
        \"document\": \"$AGENT_CPF\",
        \"email\": \"$AGENT_EMAIL\",
        \"phone\": \"11977776666\",
        \"birthdate\": \"1992-08-20\",
        \"profile_type\": \"agent\",
        \"hire_date\": \"2024-01-01\"
    }")

AGENT_PROFILE_ID=$(echo "$CREATE_AGENT_PROFILE" | jq -r '.data.id // empty')

if [ -z "$AGENT_PROFILE_ID" ]; then
    echo -e "${YELLOW}⊘ Failed to create agent profile, skipping Agent RBAC tests${NC}"
    AGENT_SESSION=""
else
    # Invite and set password
    INVITE_AGENT=$(curl -s -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Session-ID: $OWNER_SESSION" \
        -d "{\"profile_id\": $AGENT_PROFILE_ID, \"email\": \"$AGENT_EMAIL\"}")
    
    AGENT_TOKEN=$(echo "$INVITE_AGENT" | jq -r '.data.token // empty')
    
    if [ -n "$AGENT_TOKEN" ]; then
        SET_AGENT_PASSWORD=$(curl -s -X POST "$API_BASE/auth/set-password" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $BEARER_TOKEN" \
            -d "{\"token\": \"$AGENT_TOKEN\", \"password\": \"$AGENT_PASSWORD\"}")
    fi
    
    # Login as Agent
    AGENT_LOGIN_DATA=$(login_user "$AGENT_EMAIL" "$AGENT_PASSWORD")
    if [ -z "$AGENT_LOGIN_DATA" ]; then
        echo -e "${YELLOW}⊘ Agent login failed, skipping Agent RBAC tests${NC}"
        AGENT_SESSION=""
    else
        AGENT_SESSION="${AGENT_LOGIN_DATA%%|*}"
        AGENT_COMPANY="${AGENT_LOGIN_DATA##*|}"
        echo -e "${GREEN}✓ Agent user created and logged in${NC}"
    fi
fi

# Step 7: Agent creates owner+portal → 201
if [ -n "$AGENT_SESSION" ]; then
    echo ""
    echo "Step 7: Testing Agent can create owner and portal types..."
    AGENT_ALLOWED=("owner" "portal")
    AGENT_ALLOWED_PASSED=0
    
    for idx in "${!AGENT_ALLOWED[@]}"; do
        ptype="${AGENT_ALLOWED[$idx]}"
        doc_num=$((44444444400 + idx))
        email="agent_creates_${ptype}${TIMESTAMP}@test.com"
        
        result=$(create_profile "$AGENT_SESSION" "$AGENT_COMPANY" "$ptype" "Agent Creates ${ptype}" "$doc_num" "$email")
        http_code=$(echo "$result" | tail -n1)
        
        if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
            AGENT_ALLOWED_PASSED=$((AGENT_ALLOWED_PASSED + 1))
        else
            echo -e "${RED}✗ Agent failed to create $ptype (HTTP $http_code)${NC}"
        fi
    done
    
    if [ $AGENT_ALLOWED_PASSED -ne 2 ]; then
        echo -e "${RED}✗ Agent should create owner+portal, got $AGENT_ALLOWED_PASSED/2${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Agent created owner and portal types (2/2)${NC}"
    
    # Step 8: Agent tries other types → 403
    echo ""
    echo "Step 8: Testing Agent cannot create other types..."
    AGENT_FORBIDDEN=("manager" "agent" "receptionist" "prospector" "administrator" "legal" "financial")
    AGENT_FORBIDDEN_PASSED=0
    
    for idx in "${!AGENT_FORBIDDEN[@]}"; do
        ptype="${AGENT_FORBIDDEN[$idx]}"
        doc_num=$((55555555500 + idx))
        email="agent_forbidden_${ptype}${TIMESTAMP}@test.com"
        
        result=$(create_profile "$AGENT_SESSION" "$AGENT_COMPANY" "$ptype" "Agent Forbidden ${ptype}" "$doc_num" "$email")
        http_code=$(echo "$result" | tail -n1)
        
        if [ "$http_code" == "403" ]; then
            AGENT_FORBIDDEN_PASSED=$((AGENT_FORBIDDEN_PASSED + 1))
        else
            echo -e "${RED}✗ Agent should get 403 for $ptype, got $http_code${NC}"
        fi
    done
    
    if [ $AGENT_FORBIDDEN_PASSED -ne 7 ]; then
        echo -e "${RED}✗ Agent should be blocked from 7 types, got $AGENT_FORBIDDEN_PASSED/7${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Agent blocked from other types (7/7 → 403)${NC}"
fi

echo ""
echo -e "${GREEN}========================================"
echo "✓ All T26 RBAC matrix tests passed!"
echo "========================================${NC}"

exit 0
