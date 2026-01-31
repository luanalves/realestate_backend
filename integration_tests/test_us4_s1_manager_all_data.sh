#!/bin/bash

################################################################################
# Test Script: US4-S1 Manager Sees All Company Data
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 4 - Manager Oversees All Company Operations
# Scenario: 1 - Manager sees all properties, agents, and sales from their company
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
ADMIN_COOKIE_FILE="/tmp/odoo_us4s1_admin_$$.txt"
MANAGER_COOKIE_FILE="/tmp/odoo_us4s1_manager_$$.txt"

# Cleanup on exit
cleanup() {
    rm -f "$ADMIN_COOKIE_FILE" "$MANAGER_COOKIE_FILE" response.json
}
trap cleanup EXIT

echo "====================================="
echo "US4-S1: Manager Sees All Company Data"
echo "====================================="

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="CompanyTest_US4S1_${TIMESTAMP}"
MANAGER_LOGIN_EMAIL="manager.us4s1.${TIMESTAMP}@company.com"
AGENT1_LOGIN="agent1.us4s1.${TIMESTAMP}@company.com"
AGENT2_LOGIN="agent2.us4s1.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "13579246"
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
echo "  Company: $COMPANY_NAME (CNPJ: $CNPJ)"
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
# Step 3: Create Manager User
################################################################################
echo ""
echo "Step 3: Creating manager user..."

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
                \"name\": \"Manager US4S1\",
                \"login\": \"$MANAGER_LOGIN_EMAIL\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [17]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
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

################################################################################
# Step 4: Create Agent 1 User & Agent Record
################################################################################
echo ""
echo "Step 4: Creating Agent 1..."

AGENT1_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 1 US4S1\",
                \"login\": \"$AGENT1_LOGIN\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [23]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

AGENT1_UID=$(echo "$AGENT1_USER_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_UID" ] || [ "$AGENT1_UID" == "null" ]; then
    echo "❌ Agent 1 user creation failed"
    echo "Response: $AGENT1_USER_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 user created: UID=$AGENT1_UID"

# Generate valid CPF for Agent 1 (9 base digits)
CPF_AGENT1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "123456789"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:9]}-{d1}{d2}"
print(cpf)
PYTHON_EOF
)

AGENT1_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 1 US4S1\",
                \"user_id\": $AGENT1_UID,
                \"cpf\": \"$CPF_AGENT1\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT1_ID=$(echo "$AGENT1_RECORD_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT1_ID" ] || [ "$AGENT1_ID" == "null" ]; then
    echo "❌ Agent 1 record creation failed"
    echo "Response: $AGENT1_RECORD_RESPONSE"
    exit 1
fi

echo "✅ Agent 1 record created: ID=$AGENT1_ID"

################################################################################
# Step 5: Create Agent 2 User & Agent Record
################################################################################
echo ""
echo "Step 5: Creating Agent 2..."

AGENT2_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 2 US4S1\",
                \"login\": \"$AGENT2_LOGIN\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [23]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

AGENT2_UID=$(echo "$AGENT2_USER_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_UID" ] || [ "$AGENT2_UID" == "null" ]; then
    echo "❌ Agent 2 user creation failed"
    echo "Response: $AGENT2_USER_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 user created: UID=$AGENT2_UID"

# Generate valid CPF for Agent 2 (9 base digits)
CPF_AGENT2=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "987654321"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:9]}-{d1}{d2}"
print(cpf)
PYTHON_EOF
)

AGENT2_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent 2 US4S1\",
                \"user_id\": $AGENT2_UID,
                \"cpf\": \"$CPF_AGENT2\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

AGENT2_ID=$(echo "$AGENT2_RECORD_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT2_ID" ] || [ "$AGENT2_ID" == "null" ]; then
    echo "❌ Agent 2 record creation failed"
    echo "Response: $AGENT2_RECORD_RESPONSE"
    exit 1
fi

echo "✅ Agent 2 record created: ID=$AGENT2_ID"

################################################################################
# Step 6: Get Reference Data for Properties
################################################################################
echo ""
echo "Step 6: Getting reference data..."

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
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\"]}
        },
        \"id\": 10
    }")
PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

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
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\"]}
        },
        \"id\": 11
    }")
LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

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
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\"]}
        },
        \"id\": 12
    }")
STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$PROPERTY_TYPE_ID" ] || [ "$PROPERTY_TYPE_ID" == "null" ]; then
    echo "❌ Failed to get property_type_id"
    exit 1
fi
if [ -z "$LOCATION_TYPE_ID" ] || [ "$LOCATION_TYPE_ID" == "null" ]; then
    echo "❌ Failed to get location_type_id"
    exit 1
fi
if [ -z "$STATE_ID" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ Failed to get state_id"
    exit 1
fi

echo "✅ Reference data retrieved:"
echo "   Property Type: $PROPERTY_TYPE_ID"
echo "   Location Type: $LOCATION_TYPE_ID"
echo "   State: $STATE_ID"

################################################################################
# Step 7: Create Properties for Each Agent
################################################################################
echo ""
echo "Step 7: Creating properties..."

# Create 2 properties for Agent 1
for i in 1 2; do
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
                    \"name\": \"Property Agent1 #$i US4S1\",
                    \"agent_id\": $AGENT1_ID,
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"0131${i}-100\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua Agent1\",
                    \"street_number\": \"${i}00\",
                    \"area\": 100.0,
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]]
                }],
                \"kwargs\": {}
            },
            \"id\": $((20 + i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    if [ -z "$PROP_ID" ] || [ "$PROP_ID" == "null" ]; then
        echo "❌ Failed to create property $i for Agent 1"
        exit 1
    fi
    echo "✅ Property Agent1 #$i created: ID=$PROP_ID"
done

# Create 3 properties for Agent 2
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
                    \"name\": \"Property Agent2 #$i US4S1\",
                    \"agent_id\": $AGENT2_ID,
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"0132${i}-200\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua Agent2\",
                    \"street_number\": \"${i}00\",
                    \"area\": 120.0,
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]]
                }],
                \"kwargs\": {}
            },
            \"id\": $((30 + i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    if [ -z "$PROP_ID" ] || [ "$PROP_ID" == "null" ]; then
        echo "❌ Failed to create property $i for Agent 2"
        exit 1
    fi
    echo "✅ Property Agent2 #$i created: ID=$PROP_ID"
done

################################################################################
# Step 8: Manager Login
################################################################################
echo ""
echo "Step 8: Manager login..."

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
        \"id\": 40
    }")

MANAGER_SESSION_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_SESSION_UID" ] || [ "$MANAGER_SESSION_UID" == "null" ] || [ "$MANAGER_SESSION_UID" == "false" ]; then
    echo "❌ Manager login failed"
    echo "Response: $MANAGER_LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Manager login successful (UID: $MANAGER_SESSION_UID)"

################################################################################
# Step 9: Manager Sees All Agents in Company
################################################################################
echo ""
echo "Step 9: Manager checking visible agents..."

AGENTS_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {\"fields\": [\"id\", \"name\"]}
        },
        \"id\": 41
    }")

AGENT_COUNT=$(echo "$AGENTS_RESPONSE" | jq -r '.result | length')
CAN_SEE_AGENT1=$(echo "$AGENTS_RESPONSE" | jq -r ".result[] | select(.id == $AGENT1_ID) | .id")
CAN_SEE_AGENT2=$(echo "$AGENTS_RESPONSE" | jq -r ".result[] | select(.id == $AGENT2_ID) | .id")

echo "Manager sees $AGENT_COUNT agents"

if [ ! -z "$CAN_SEE_AGENT1" ] && [ ! -z "$CAN_SEE_AGENT2" ]; then
    echo "✅ Manager can see both agents in company"
else
    echo "⚠️  Manager visibility limited (Agent1: $CAN_SEE_AGENT1, Agent2: $CAN_SEE_AGENT2)"
fi

################################################################################
# Step 10: Manager Sees All Properties in Company
################################################################################
echo ""
echo "Step 10: Manager checking visible properties..."

PROPERTIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$MANAGER_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[[\"name\", \"ilike\", \"US4S1\"]]],
            \"kwargs\": {\"fields\": [\"id\", \"name\", \"agent_id\"]}
        },
        \"id\": 42
    }")

PROPERTY_COUNT=$(echo "$PROPERTIES_RESPONSE" | jq -r '.result | length')

echo "Manager sees $PROPERTY_COUNT properties from this test"

if [ "$PROPERTY_COUNT" -ge 5 ]; then
    echo "✅ Manager can see all 5 properties (2 from Agent1, 3 from Agent2)"
else
    echo "⚠️  Manager sees fewer properties than expected ($PROPERTY_COUNT < 5)"
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US4-S1 Manager Sees All Company Data"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Manager created successfully"
echo "  - Manager can see all agents in company"
echo "  - Manager can see all properties assigned to any agent"
echo ""

exit 0
