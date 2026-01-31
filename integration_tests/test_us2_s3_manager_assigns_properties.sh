#!/bin/bash

################################################################################
# Test Script: US2-S3 Manager Assigns Properties
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 2 - Owner Creates Team Members with Different Roles
# Scenario: 3 - Manager assigns properties to agents
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

# Use unique temp file paths to avoid session conflicts
ADMIN_COOKIE_FILE="/tmp/odoo_us2s3_admin_$$.txt"
MANAGER_COOKIE_FILE="/tmp/odoo_us2s3_manager_$$.txt"

# Cleanup on exit
cleanup() {
    rm -f "$ADMIN_COOKIE_FILE" "$MANAGER_COOKIE_FILE" response.json
}
trap cleanup EXIT

echo "====================================="
echo "US2-S3: Manager Assigns Properties"
echo "====================================="

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US2S3_${TIMESTAMP}"
MANAGER_LOGIN_EMAIL="manager.us2s3.${TIMESTAMP}@company.com"
AGENT1_LOGIN="agent1.us2s3.${TIMESTAMP}@company.com"
AGENT2_LOGIN="agent2.us2s3.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "22333444"
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
echo "  Manager: $MANAGER_LOGIN_EMAIL"
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
# Step 3: Create Manager and Agents
################################################################################
echo ""
echo "Step 3: Creating manager and agent users..."

# Create Manager User
MANAGER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager US2S3\",
                \"login\": \"$MANAGER_LOGIN_EMAIL\",
                \"password\": \"manager123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [17]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

MANAGER_UID=$(echo "$MANAGER_RESPONSE" | jq -r '.result // empty')

if [ -z "$MANAGER_UID" ] || [ "$MANAGER_UID" == "null" ]; then
    echo "❌ Manager user creation failed"
    echo "Response: $MANAGER_RESPONSE"
    exit 1
fi

echo "✅ Manager created: UID=$MANAGER_UID"

# Create Agent 1 User
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
                \"name\": \"Agent 1 US2S3\",
                \"login\": \"$AGENT1_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

AGENT1_UID=$(echo "$AGENT1_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_UID" ] || [ "$AGENT1_UID" == "null" ]; then
    echo "❌ Agent 1 user creation failed"
    echo "Response: $AGENT1_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 created: UID=$AGENT1_UID"

# Create Agent 2 User
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
                \"name\": \"Agent 2 US2S3\",
                \"login\": \"$AGENT2_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT2_UID=$(echo "$AGENT2_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_UID" ] || [ "$AGENT2_UID" == "null" ]; then
    echo "❌ Agent 2 user creation failed"
    echo "Response: $AGENT2_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 created: UID=$AGENT2_UID"

# Generate valid CPFs for agent records
CPF_MANAGER=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)
base = "66677788"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
print(f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}")
PYTHON_EOF
)

CPF_AGENT1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)
base = "77788899"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
print(f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}")
PYTHON_EOF
)

CPF_AGENT2=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)
base = "88899900"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
print(f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}")
PYTHON_EOF
)

# Create Manager Agent Record
MANAGER_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager US2S3\",
                \"user_id\": $MANAGER_UID,
                \"cpf\": \"$CPF_MANAGER\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

MANAGER_AGENT_ID=$(echo "$MANAGER_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$MANAGER_AGENT_ID" ] || [ "$MANAGER_AGENT_ID" == "null" ]; then
    echo "❌ Manager agent record creation failed"
    echo "Response: $MANAGER_AGENT_RESPONSE"
    exit 1
fi

echo "✅ Manager agent record created: ID=$MANAGER_AGENT_ID"

# Create Agent 1 Record
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
                \"name\": \"Agent 1 US2S3\",
                \"user_id\": $AGENT1_UID,
                \"cpf\": \"$CPF_AGENT1\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

AGENT1_AGENT_ID=$(echo "$AGENT1_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_AGENT_ID" ] || [ "$AGENT1_AGENT_ID" == "null" ]; then
    echo "❌ Agent 1 record creation failed"
    echo "Response: $AGENT1_AGENT_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 record created: ID=$AGENT1_AGENT_ID"

# Create Agent 2 Record
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
                \"name\": \"Agent 2 US2S3\",
                \"user_id\": $AGENT2_UID,
                \"cpf\": \"$CPF_AGENT2\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 8
    }")

AGENT2_AGENT_ID=$(echo "$AGENT2_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_AGENT_ID" ] || [ "$AGENT2_AGENT_ID" == "null" ]; then
    echo "❌ Agent 2 record creation failed"
    echo "Response: $AGENT2_AGENT_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 record created: ID=$AGENT2_AGENT_ID"

################################################################################
# Step 4: Retrieve Reference Data for Properties
################################################################################
echo ""
echo "Step 4: Retrieving reference data for properties..."

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
            \"kwargs\": {\"fields\": [\"id\", \"name\"], \"limit\": 1}
        },
        \"id\": 10
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$PROPERTY_TYPE_ID" ] || [ "$PROPERTY_TYPE_ID" == "null" ]; then
    echo "❌ Failed to get property_type_id"
    echo "Response: $PROPERTY_TYPE_RESPONSE"
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
            \"kwargs\": {\"fields\": [\"id\", \"name\"], \"limit\": 1}
        },
        \"id\": 11
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$LOCATION_TYPE_ID" ] || [ "$LOCATION_TYPE_ID" == "null" ]; then
    echo "❌ Failed to get location_type_id"
    echo "Response: $LOCATION_TYPE_RESPONSE"
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
            \"kwargs\": {\"fields\": [\"id\", \"name\"], \"limit\": 1}
        },
        \"id\": 12
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$STATE_ID" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ Failed to get state_id"
    echo "Response: $STATE_RESPONSE"
    exit 1
fi

echo "✅ State ID: $STATE_ID"

################################################################################
# Step 5: Create Properties (as admin)
################################################################################
echo ""
echo "Step 5: Creating properties..."

PROPERTY1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property 1 US2S3\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"12345-678\",
                \"city\": \"São Paulo\",
                \"street\": \"Rua Teste\",
                \"street_number\": \"100\",
                \"area\": 80.0,
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 13
    }")

PROPERTY1_ID=$(echo "$PROPERTY1_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY1_ID" ] || [ "$PROPERTY1_ID" == "null" ]; then
    echo "❌ Property 1 creation failed"
    echo "Response: $PROPERTY1_RESPONSE"
    exit 1
fi

echo "✅ Property 1 created: ID=$PROPERTY1_ID"

PROPERTY2_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property 2 US2S3\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"12345-679\",
                \"city\": \"São Paulo\",
                \"street\": \"Rua Teste\",
                \"street_number\": \"200\",
                \"area\": 150.0,
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 14
    }")

PROPERTY2_ID=$(echo "$PROPERTY2_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY2_ID" ] || [ "$PROPERTY2_ID" == "null" ]; then
    echo "❌ Property 2 creation failed"
    echo "Response: $PROPERTY2_RESPONSE"
    exit 1
fi

echo "✅ Property 2 created: ID=$PROPERTY2_ID"

################################################################################
# Step 6: Manager Login
################################################################################
echo ""
echo "Step 6: Manager login..."

MANAGER_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_LOGIN_EMAIL\",
            \"password\": \"manager123\"
        },
        \"id\": 20
    }")

MANAGER_SESSION_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_SESSION_UID" ] || [ "$MANAGER_SESSION_UID" == "null" ] || [ "$MANAGER_SESSION_UID" == "false" ]; then
    echo "❌ Manager login failed"
    echo "Response: $MANAGER_LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Manager login successful (UID: $MANAGER_SESSION_UID)"

################################################################################
# Step 7: Manager Assigns Property 1 to Agent 1
################################################################################
echo ""
echo "Step 7: Manager assigning Property 1 to Agent 1..."

ASSIGN1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [[$PROPERTY1_ID], {\"agent_id\": $AGENT1_AGENT_ID}],
            \"kwargs\": {}
        },
        \"id\": 21
    }")

ASSIGN1_RESULT=$(echo "$ASSIGN1_RESPONSE" | jq -r '.result // empty')

if [ "$ASSIGN1_RESULT" == "true" ]; then
    echo "✅ Property 1 assigned to Agent 1"
else
    echo "❌ Failed to assign Property 1 to Agent 1"
    echo "Response: $ASSIGN1_RESPONSE"
    exit 1
fi

################################################################################
# Step 8: Manager Assigns Property 2 to Agent 2
################################################################################
echo ""
echo "Step 8: Manager assigning Property 2 to Agent 2..."

ASSIGN2_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [[$PROPERTY2_ID], {\"agent_id\": $AGENT2_AGENT_ID}],
            \"kwargs\": {}
        },
        \"id\": 22
    }")

ASSIGN2_RESULT=$(echo "$ASSIGN2_RESPONSE" | jq -r '.result // empty')

if [ "$ASSIGN2_RESULT" == "true" ]; then
    echo "✅ Property 2 assigned to Agent 2"
else
    echo "❌ Failed to assign Property 2 to Agent 2"
    echo "Response: $ASSIGN2_RESPONSE"
    exit 1
fi

################################################################################
# Step 9: Verify Assignments
################################################################################
echo ""
echo "Step 9: Verifying property assignments..."

PROPERTIES_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[[\"id\", \"in\", [$PROPERTY1_ID, $PROPERTY2_ID]]]],
            \"kwargs\": {\"fields\": [\"name\", \"agent_id\"]}
        },
        \"id\": 23
    }")

PROP1_AGENT=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY1_ID) | .agent_id[0] // empty")
PROP2_AGENT=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY2_ID) | .agent_id[0] // empty")

if [ "$PROP1_AGENT" == "$AGENT1_AGENT_ID" ]; then
    echo "✅ Property 1 correctly assigned to Agent 1"
else
    echo "❌ Property 1 assignment verification failed (expected: $AGENT1_AGENT_ID, got: $PROP1_AGENT)"
    exit 1
fi

if [ "$PROP2_AGENT" == "$AGENT2_AGENT_ID" ]; then
    echo "✅ Property 2 correctly assigned to Agent 2"
else
    echo "❌ Property 2 assignment verification failed (expected: $AGENT2_AGENT_ID, got: $PROP2_AGENT)"
    exit 1
fi

################################################################################
# Step 10: Manager Reassigns Property 1 to Agent 2
################################################################################
echo ""
echo "Step 10: Manager reassigning Property 1 from Agent 1 to Agent 2..."

REASSIGN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [[$PROPERTY1_ID], {\"agent_id\": $AGENT2_AGENT_ID}],
            \"kwargs\": {}
        },
        \"id\": 24
    }")

REASSIGN_RESULT=$(echo "$REASSIGN_RESPONSE" | jq -r '.result // empty')

if [ "$REASSIGN_RESULT" == "true" ]; then
    echo "✅ Property 1 reassigned to Agent 2"
else
    echo "❌ Failed to reassign Property 1"
    echo "Response: $REASSIGN_RESPONSE"
    exit 1
fi

################################################################################
# Step 11: Verify Reassignment
################################################################################
echo ""
echo "Step 11: Verifying reassignment..."

FINAL_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[[\"id\", \"=\", $PROPERTY1_ID]]],
            \"kwargs\": {\"fields\": [\"name\", \"agent_id\"]}
        },
        \"id\": 25
    }")

FINAL_AGENT=$(echo "$FINAL_CHECK" | jq -r '.result[0].agent_id[0] // empty')

if [ "$FINAL_AGENT" == "$AGENT2_AGENT_ID" ]; then
    echo "✅ Property 1 now correctly assigned to Agent 2"
else
    echo "❌ Reassignment verification failed"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US2-S3 Manager Assigns Properties"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Manager can assign properties to agents"
echo "  - Manager can reassign properties between agents"
echo "  - All assignments correctly persisted"
echo ""

exit 0
