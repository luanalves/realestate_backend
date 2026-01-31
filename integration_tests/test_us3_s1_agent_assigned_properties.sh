#!/bin/bash

################################################################################
# Test Script: US3-S1 Agent Assigned Properties
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 3 - Agent Manages Their Own Properties and Leads
# Scenario: 1 - Agent sees only properties assigned to them
################################################################################

set -e

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-${POSTGRES_DB:-realestate}}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

# Use unique temp file paths to avoid conflicts
ADMIN_COOKIE_FILE="/tmp/odoo_us3s1_admin_$$.txt"
AGENT1_COOKIE_FILE="/tmp/odoo_us3s1_agent1_$$.txt"
AGENT2_COOKIE_FILE="/tmp/odoo_us3s1_agent2_$$.txt"

# Cleanup on exit
cleanup() {
    rm -f "$ADMIN_COOKIE_FILE" "$AGENT1_COOKIE_FILE" "$AGENT2_COOKIE_FILE" response.json
}
trap cleanup EXIT

echo "====================================="
echo "US3-S1: Agent Assigned Properties"
echo "====================================="

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US3S1_${TIMESTAMP}"
AGENT1_LOGIN="agent1.us3s1.${TIMESTAMP}@company.com"
AGENT2_LOGIN="agent2.us3s1.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "11223344"
branch = "0001"
cnpj_partial = base + branch
w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
d1 = calc_cnpj_digit(cnpj_partial, w1)
cnpj_partial += d1
w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
d2 = calc_cnpj_digit(cnpj_partial, w2)
cnpj = f"{base[:2]}.{base[2:5]}.{base[5:]}/{branch}-{d1}{d2}"
print(cnpj)
PYTHON_EOF
)

echo "Test data:"
echo "  Company: $COMPANY_NAME"
echo "  CNPJ: $CNPJ"
echo "  Agent 1: $AGENT1_LOGIN"
echo "  Agent 2: $AGENT2_LOGIN"
echo ""

################################################################################
# Step 1: Admin Login & Setup
################################################################################
echo "Step 1: Admin login and setup..."

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$ADMIN_LOGIN\",
            \"password\": \"$ADMIN_PASSWORD\"
        },
        \"id\": 1
    }")

ADMIN_UID=$(echo "$LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$ADMIN_UID" ] || [ "$ADMIN_UID" == "null" ] || [ "$ADMIN_UID" == "false" ]; then
    echo "❌ Admin login failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Admin login successful (UID: $ADMIN_UID)"

################################################################################
# Step 2: Create Company
################################################################################
echo ""
echo "Step 2: Creating company..."

COMPANY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"$COMPANY_NAME\",
                \"cnpj\": \"$CNPJ\"
            }],
            \"kwargs\": {}
        },
        \"id\": 2
    }")

COMPANY_ID=$(echo "$COMPANY_RESPONSE" | jq -r '.result // empty')

if [ -z "$COMPANY_ID" ] || [ "$COMPANY_ID" == "null" ]; then
    echo "❌ Company creation failed"
    echo "Response: $COMPANY_RESPONSE"
    exit 1
fi

echo "✅ Company created: ID=$COMPANY_ID"

################################################################################
# Step 3: Create Agent Users
################################################################################
echo ""
echo "Step 3: Creating agent users..."

AGENT1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 1 US3S1\",
                \"login\": \"$AGENT1_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

AGENT1_UID=$(echo "$AGENT1_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_UID" ] || [ "$AGENT1_UID" == "null" ]; then
    echo "❌ Agent 1 user creation failed"
    echo "Response: $AGENT1_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 created: UID=$AGENT1_UID"

AGENT2_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 2 US3S1\",
                \"login\": \"$AGENT2_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

AGENT2_UID=$(echo "$AGENT2_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_UID" ] || [ "$AGENT2_UID" == "null" ]; then
    echo "❌ Agent 2 user creation failed"
    echo "Response: $AGENT2_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 created: UID=$AGENT2_UID"

# Create agent records with CPF for Agent1 and Agent2
CPF_AGENT1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "33344455"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

AGENT1_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 1 US3S1\",
                \"user_id\": $AGENT1_UID,
                \"cpf\": \"$CPF_AGENT1\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT1_AGENT_ID=$(echo "$AGENT1_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_AGENT_ID" ] || [ "$AGENT1_AGENT_ID" == "null" ]; then
    echo "❌ Agent 1 agent record creation failed"
    echo "Response: $AGENT1_AGENT_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 agent record created: ID=$AGENT1_AGENT_ID"

CPF_AGENT2=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "44455566"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

AGENT2_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 2 US3S1\",
                \"user_id\": $AGENT2_UID,
                \"cpf\": \"$CPF_AGENT2\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

AGENT2_AGENT_ID=$(echo "$AGENT2_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_AGENT_ID" ] || [ "$AGENT2_AGENT_ID" == "null" ]; then
    echo "❌ Agent 2 agent record creation failed"
    echo "Response: $AGENT2_AGENT_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 agent record created: ID=$AGENT2_AGENT_ID"

################################################################################
# Step 3.5: Retrieve Reference Data for Properties
################################################################################
echo ""
echo "=========================================="
echo "Step 3.5: Retrieve Reference Data for Properties"
echo "=========================================="

# Get first property type
PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property.type\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"],
                \"limit\": 1
            }
        },
        \"id\": 42
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$PROPERTY_TYPE_ID" ] || [ "$PROPERTY_TYPE_ID" == "null" ]; then
    echo "❌ Property type not found"
    exit 1
fi

echo "✅ Property Type ID: $PROPERTY_TYPE_ID"

# Get location type
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.location.type\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"],
                \"limit\": 1
            }
        },
        \"id\": 43
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$LOCATION_TYPE_ID" ] || [ "$LOCATION_TYPE_ID" == "null" ]; then
    echo "❌ Location type not found"
    exit 1
fi

echo "✅ Location Type ID: $LOCATION_TYPE_ID"

# Get state
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.state\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"],
                \"limit\": 1
            }
        },
        \"id\": 44
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$STATE_ID" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ State not found"
    exit 1
fi

echo "✅ State ID: $STATE_ID"

################################################################################
# Step 4: Create Properties Assigned to Each Agent
################################################################################
echo ""
echo "Step 4: Creating properties..."

# Properties for Agent 1 (5 properties)
AGENT1_PROPERTIES=()
for i in 1 2 3 4 5; do
    PROP_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.property\",
                \"method\": \"create\",
                \"args\": [{
                    \"name\": \"Property Agent1-$i US3S1\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"12345-678\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua Teste\",
                    \"street_number\": \"$((100 + i))\",
                    \"num_rooms\": 2,
                    \"num_bathrooms\": 1,
                    \"num_parking\": 1,
                    \"area\": 80.0,
                    \"price\": 300000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                    \"agent_id\": $AGENT1_AGENT_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((10 + i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    
    if [ -z "$PROP_ID" ] || [ "$PROP_ID" == "null" ]; then
        echo "❌ Property Agent1-$i creation failed"
        echo "Response: $PROP_RESPONSE"
        exit 1
    fi
    
    AGENT1_PROPERTIES+=($PROP_ID)
    echo "✅ Property Agent1-$i created: ID=$PROP_ID"
done

# Properties for Agent 2 (3 properties)
AGENT2_PROPERTIES=()
for i in 1 2 3; do
    PROP_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.property\",
                \"method\": \"create\",
                \"args\": [{
                    \"name\": \"Property Agent2-$i US3S1\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"12345-678\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua Teste\",
                    \"street_number\": \"$((200 + i))\",
                    \"num_rooms\": 3,
                    \"num_bathrooms\": 2,
                    \"num_parking\": 2,
                    \"area\": 150.0,
                    \"price\": 500000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                    \"agent_id\": $AGENT2_AGENT_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((20 + i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    
    if [ -z "$PROP_ID" ] || [ "$PROP_ID" == "null" ]; then
        echo "❌ Property Agent2-$i creation failed"
        echo "Response: $PROP_RESPONSE"
        exit 1
    fi
    
    AGENT2_PROPERTIES+=($PROP_ID)
    echo "✅ Property Agent2-$i created: ID=$PROP_ID"
done

################################################################################
# Step 5: Agent 1 Login
################################################################################
echo ""
echo "Step 5: Agent 1 login..."

AGENT1_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$AGENT1_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$AGENT1_LOGIN\",
            \"password\": \"agent123\"
        },
        \"id\": 30
    }")

AGENT1_SESSION_UID=$(echo "$AGENT1_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$AGENT1_SESSION_UID" ] || [ "$AGENT1_SESSION_UID" == "null" ] || [ "$AGENT1_SESSION_UID" == "false" ]; then
    echo "❌ Agent 1 login failed"
    echo "Response: $AGENT1_LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 login successful (UID: $AGENT1_SESSION_UID)"

################################################################################
# Step 6: Agent 1 Views Properties
################################################################################
echo ""
echo "Step 6: Agent 1 viewing properties..."

AGENT1_PROPS_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$AGENT1_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"agent_id\"]
            }
        },
        \"id\": 31
    }")

AGENT1_VISIBLE_COUNT=$(echo "$AGENT1_PROPS_CHECK" | jq -r '.result | length')
AGENT1_PROPS_IDS=$(echo "$AGENT1_PROPS_CHECK" | jq -r '.result[].id')

echo "Agent 1 sees $AGENT1_VISIBLE_COUNT properties"

# Verify Agent 1 sees exactly 5 properties
if [ "$AGENT1_VISIBLE_COUNT" -ne "5" ]; then
    echo "❌ Agent 1 should see 5 properties, but sees $AGENT1_VISIBLE_COUNT"
    exit 1
fi

# Verify all visible properties belong to Agent 1
ALL_BELONG_TO_AGENT1=true
for prop_id in $AGENT1_PROPS_IDS; do
    AGENT_OF_PROP=$(echo "$AGENT1_PROPS_CHECK" | jq -r ".result[] | select(.id == $prop_id) | .agent_id[0] // empty")
    if [ "$AGENT_OF_PROP" != "$AGENT1_AGENT_ID" ]; then
        ALL_BELONG_TO_AGENT1=false
        echo "⚠️  Property $prop_id not assigned to Agent 1 (has agent_id: $AGENT_OF_PROP)"
    fi
done

if [ "$ALL_BELONG_TO_AGENT1" = true ]; then
    echo "✅ Agent 1 sees only their 5 assigned properties"
else
    echo "❌ Agent 1 sees properties not assigned to them"
    exit 1
fi

################################################################################
# Step 7: Agent 2 Login and Verification
################################################################################
echo ""
echo "Step 7: Agent 2 login and verification..."

AGENT2_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$AGENT2_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$AGENT2_LOGIN\",
            \"password\": \"agent123\"
        },
        \"id\": 32
    }")

AGENT2_SESSION_UID=$(echo "$AGENT2_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$AGENT2_SESSION_UID" ] || [ "$AGENT2_SESSION_UID" == "null" ] || [ "$AGENT2_SESSION_UID" == "false" ]; then
    echo "❌ Agent 2 login failed"
    exit 1
fi

echo "✅ Agent 2 login successful (UID: $AGENT2_SESSION_UID)"

AGENT2_PROPS_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$AGENT2_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"agent_id\"]
            }
        },
        \"id\": 33
    }")

AGENT2_VISIBLE_COUNT=$(echo "$AGENT2_PROPS_CHECK" | jq -r '.result | length')
echo "Agent 2 sees $AGENT2_VISIBLE_COUNT properties"

if [ "$AGENT2_VISIBLE_COUNT" -ne "3" ]; then
    echo "❌ Agent 2 should see 3 properties, but sees $AGENT2_VISIBLE_COUNT"
    exit 1
fi

echo "✅ Agent 2 sees only their 3 assigned properties"

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US3-S1 Agent Assigned Properties"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Agent 1 sees only their 5 assigned properties"
echo "  - Agent 2 sees only their 3 assigned properties"
echo "  - Agents cannot see each other's properties"
echo ""

exit 0
