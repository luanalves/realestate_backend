#!/bin/bash

################################################################################
# Test Script: US4-S1 Manager Sees All Company Data
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 4 - Manager Oversees All Company Operations
# Scenario: 1 - Manager sees all properties, agents, and sales from their company
################################################################################

# Load configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-realestate}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

echo "====================================="
echo "US4-S1: Manager Sees All Company Data"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="CompanyTest_US4S1_${TIMESTAMP}"
MANAGER_LOGIN="manager.us4s1.${TIMESTAMP}@company.com"
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
echo "  Manager: $MANAGER_LOGIN"
echo "  Agent 1: $AGENT1_LOGIN"
echo "  Agent 2: $AGENT2_LOGIN"
echo ""

################################################################################
# Step 1: Admin Login & Setup
################################################################################
echo "=========================================="
echo "Step 1: Admin login and setup"
echo "=========================================="

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
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

if [ -z "$ADMIN_UID" ] || [ "$ADMIN_UID" == "null" ]; then
    echo "❌ Admin login failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✓ Admin logged in (UID: $ADMIN_UID)"

ADMIN_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')
echo "✓ Session ID: ${ADMIN_SESSION:0:20}..."

################################################################################
# Step 2: Create Company
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create company"
echo "=========================================="

COMPANY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
        \"id\": 1
    }")

COMPANY_ID=$(echo "$COMPANY_RESPONSE" | jq -r '.result')

if [ -z "$COMPANY_ID" ] || [ "$COMPANY_ID" == "null" ]; then
    echo "❌ Company creation failed"
    echo "Response: $COMPANY_RESPONSE"
    exit 1
fi

echo "✓ Company created: ID=$COMPANY_ID"

################################################################################
# Step 3: Create Manager User
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Create manager user"
echo "=========================================="

# Get Manager security group ID (17)
MANAGER_GROUP_ID=17

MANAGER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager US4S1\",
                \"login\": \"$MANAGER_LOGIN\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [$MANAGER_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

MANAGER_UID=$(echo "$MANAGER_RESPONSE" | jq -r '.result')

if [ -z "$MANAGER_UID" ] || [ "$MANAGER_UID" == "null" ]; then
    echo "❌ Manager user creation failed"
    echo "Response: $MANAGER_RESPONSE"
    exit 1
fi

echo "✓ Manager created: UID=$MANAGER_UID"

################################################################################
# Step 4: Create Agent 1 User & Agent Record
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Create Agent 1"
echo "=========================================="

# Get Agent security group ID (23)
AGENT_GROUP_ID=23

AGENT1_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
                \"groups_id\": [[6, 0, [$AGENT_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT1_UID=$(echo "$AGENT1_USER_RESPONSE" | jq -r '.result')

if [ -z "$AGENT1_UID" ] || [ "$AGENT1_UID" == "null" ]; then
    echo "❌ Agent 1 user creation failed"
    echo "Response: $AGENT1_USER_RESPONSE"
    exit 1
fi

echo "✓ Agent 1 user created: UID=$AGENT1_UID"

# Generate valid CPF for Agent 1
CPF_AGENT1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "12345678"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

echo "✓ CPF for Agent 1: $CPF_AGENT1"

# Create agent record for Agent 1
AGENT1_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
        \"id\": 1
    }")

AGENT1_ID=$(echo "$AGENT1_RECORD_RESPONSE" | jq -r '.result')

if [ -z "$AGENT1_ID" ] || [ "$AGENT1_ID" == "null" ]; then
    echo "❌ Agent 1 record creation failed"
    echo "Response: $AGENT1_RECORD_RESPONSE"
    exit 1
fi

echo "✓ Agent 1 record created: ID=$AGENT1_ID"

################################################################################
# Step 5: Create Agent 2 User & Agent Record
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Create Agent 2"
echo "=========================================="

AGENT2_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
                \"groups_id\": [[6, 0, [$AGENT_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT2_UID=$(echo "$AGENT2_USER_RESPONSE" | jq -r '.result')

if [ -z "$AGENT2_UID" ] || [ "$AGENT2_UID" == "null" ]; then
    echo "❌ Agent 2 user creation failed"
    echo "Response: $AGENT2_USER_RESPONSE"
    exit 1
fi

echo "✓ Agent 2 user created: UID=$AGENT2_UID"

# Generate valid CPF for Agent 2
CPF_AGENT2=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "98765432"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

echo "✓ CPF for Agent 2: $CPF_AGENT2"

# Create agent record for Agent 2
AGENT2_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
        \"id\": 1
    }")

AGENT2_ID=$(echo "$AGENT2_RECORD_RESPONSE" | jq -r '.result')

if [ -z "$AGENT2_ID" ] || [ "$AGENT2_ID" == "null" ]; then
    echo "❌ Agent 2 record creation failed"
    echo "Response: $AGENT2_RECORD_RESPONSE"
    exit 1
fi

echo "✓ Agent 2 record created: ID=$AGENT2_ID"

################################################################################
# Step 6: Retrieve Reference Data for Properties
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Retrieve reference data for properties"
echo "=========================================="

# Get first property type
PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.property.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

# Get first location type
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.location.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

# Get first state
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.state",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id')
echo "✓ State ID: $STATE_ID"

# Validate all reference data retrieved
if [ "$PROPERTY_TYPE_ID" == "null" ] || [ "$LOCATION_TYPE_ID" == "null" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ Failed to retrieve reference data"
    echo "Property Type: $PROPERTY_TYPE_ID"
    echo "Location Type: $LOCATION_TYPE_ID"
    echo "State: $STATE_ID"
    exit 1
fi

echo "✓ All reference data retrieved successfully"

################################################################################
# Step 7: Create Properties Assigned to Agent 1 (3 properties)
################################################################################
echo ""
echo "=========================================="
echo "Step 7: Create 3 properties for Agent 1"
echo "=========================================="

for i in 1 2 3; do
    PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
      -H "Content-Type: application/json" \
      -H "Cookie: session_id=$ADMIN_SESSION" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
          \"model\": \"real.estate.property\",
          \"method\": \"create\",
          \"args\": [{
            \"name\": \"Agent1 Property $i\",
            \"property_type_id\": $PROPERTY_TYPE_ID,
            \"location_type_id\": $LOCATION_TYPE_ID,
            \"zip_code\": \"01310-10$i\",
            \"state_id\": $STATE_ID,
            \"city\": \"São Paulo\",
            \"street\": \"Av Paulista\",
            \"street_number\": \"100$i\",
            \"area\": $((80 + i * 10)).0,
            \"price\": $((300000 + i * 50000)).0,
            \"property_status\": \"available\",
            \"company_ids\": [[6, 0, [$COMPANY_ID]]],
            \"agent_id\": $AGENT1_ID
          }],
          \"kwargs\": {}
        },
        \"id\": 1
      }")

    PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.result')
    
    if [ "$PROPERTY_ID" == "null" ] || [ -z "$PROPERTY_ID" ]; then
        echo "❌ Agent1 Property $i creation failed"
        echo "Response: $PROPERTY_RESPONSE"
        exit 1
    fi
    
    echo "✓ Agent1 Property $i created: ID=$PROPERTY_ID"
done

################################################################################
# Step 8: Create Properties Assigned to Agent 2 (2 properties)
################################################################################
echo ""
echo "=========================================="
echo "Step 8: Create 2 properties for Agent 2"
echo "=========================================="

for i in 1 2; do
    PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
      -H "Content-Type: application/json" \
      -H "Cookie: session_id=$ADMIN_SESSION" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
          \"model\": \"real.estate.property\",
          \"method\": \"create\",
          \"args\": [{
            \"name\": \"Agent2 Property $i\",
            \"property_type_id\": $PROPERTY_TYPE_ID,
            \"location_type_id\": $LOCATION_TYPE_ID,
            \"zip_code\": \"01310-20$i\",
            \"state_id\": $STATE_ID,
            \"city\": \"Rio de Janeiro\",
            \"street\": \"Av Atlântica\",
            \"street_number\": \"200$i\",
            \"area\": $((70 + i * 10)).0,
            \"price\": $((250000 + i * 40000)).0,
            \"property_status\": \"available\",
            \"company_ids\": [[6, 0, [$COMPANY_ID]]],
            \"agent_id\": $AGENT2_ID
          }],
          \"kwargs\": {}
        },
        \"id\": 1
      }")

    PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.result')
    
    if [ "$PROPERTY_ID" == "null" ] || [ -z "$PROPERTY_ID" ]; then
        echo "❌ Agent2 Property $i creation failed"
        echo "Response: $PROPERTY_RESPONSE"
        exit 1
    fi
    
    echo "✓ Agent2 Property $i created: ID=$PROPERTY_ID"
done

################################################################################
# Step 9: Manager Login
################################################################################
echo ""
echo "=========================================="
echo "Step 9: Manager login"
echo "=========================================="

rm -f cookies.txt

MANAGER_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_LOGIN\",
            \"password\": \"manager123\"
        },
        \"id\": 1
    }")

MANAGER_LOGIN_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_LOGIN_UID" ] || [ "$MANAGER_LOGIN_UID" == "null" ]; then
    echo "❌ Manager login failed"
    echo "Response: $MANAGER_LOGIN_RESPONSE"
    exit 1
fi

echo "✓ Manager logged in: UID=$MANAGER_LOGIN_UID"

MANAGER_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')
echo "✓ Manager session: ${MANAGER_SESSION:0:20}..."

################################################################################
# Step 10: Manager Views All Properties (Should see 5: 3 from Agent 1 + 2 from Agent 2)
################################################################################
echo ""
echo "=========================================="
echo "Step 10: Manager views all company properties"
echo "=========================================="

MANAGER_PROPERTIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"agent_id\"],
                \"limit\": 100
            }
        },
        \"id\": 1
    }")

MANAGER_PROPERTY_COUNT=$(echo "$MANAGER_PROPERTIES_RESPONSE" | jq -r '.result | length')

echo "Manager sees $MANAGER_PROPERTY_COUNT properties"

if [ "$MANAGER_PROPERTY_COUNT" -lt 5 ]; then
    echo "❌ Manager should see at least 5 properties (3 from Agent1 + 2 from Agent2), but sees $MANAGER_PROPERTY_COUNT"
    echo "Response: $MANAGER_PROPERTIES_RESPONSE"
    exit 1
fi

echo "✓ Manager can see all company properties ($MANAGER_PROPERTY_COUNT total)"

# Verify Manager sees properties from both agents
AGENT1_PROPERTIES=$(echo "$MANAGER_PROPERTIES_RESPONSE" | jq -r "[.result[] | select(.agent_id and .agent_id[0] == $AGENT1_ID)] | length")
AGENT2_PROPERTIES=$(echo "$MANAGER_PROPERTIES_RESPONSE" | jq -r "[.result[] | select(.agent_id and .agent_id[0] == $AGENT2_ID)] | length")

echo "  - Properties from Agent 1: $AGENT1_PROPERTIES"
echo "  - Properties from Agent 2: $AGENT2_PROPERTIES"

if [ "$AGENT1_PROPERTIES" -lt 3 ]; then
    echo "❌ Manager should see 3 properties from Agent 1, but sees $AGENT1_PROPERTIES"
    exit 1
fi

if [ "$AGENT2_PROPERTIES" -lt 2 ]; then
    echo "❌ Manager should see 2 properties from Agent 2, but sees $AGENT2_PROPERTIES"
    exit 1
fi

echo "✓ Manager can see properties from both agents"

################################################################################
# Step 11: Manager Views All Agents (Should see 2: Agent 1 + Agent 2)
################################################################################
echo ""
echo "=========================================="
echo "Step 11: Manager views all company agents"
echo "=========================================="

MANAGER_AGENTS_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"user_id\"],
                \"limit\": 100
            }
        },
        \"id\": 1
    }")

MANAGER_AGENT_COUNT=$(echo "$MANAGER_AGENTS_RESPONSE" | jq -r '.result | length')

echo "Manager sees $MANAGER_AGENT_COUNT agents"

if [ "$MANAGER_AGENT_COUNT" -lt 2 ]; then
    echo "❌ Manager should see at least 2 agents, but sees $MANAGER_AGENT_COUNT"
    echo "Response: $MANAGER_AGENTS_RESPONSE"
    exit 1
fi

echo "✓ Manager can see all company agents ($MANAGER_AGENT_COUNT total)"

################################################################################
# Step 12: Test Complete
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US4-S1 Manager Sees All Company Data"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Manager created and logged in successfully"
echo "  - Manager can see all $MANAGER_PROPERTY_COUNT properties from the company"
echo "  - Manager can see properties from Agent 1 ($AGENT1_PROPERTIES properties)"
echo "  - Manager can see properties from Agent 2 ($AGENT2_PROPERTIES properties)"
echo "  - Manager can see all $MANAGER_AGENT_COUNT agents from the company"
echo "  - Manager has full visibility of company operations"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
