#!/bin/bash

################################################################################
# Test Script: US4-S2 Manager Reassigns Properties
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 4 - Manager Oversees All Company Operations
# Scenario: 2 - Manager can reassign properties between agents
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
echo "US4-S2: Manager Reassigns Properties"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="CompanyTest_US4S2_${TIMESTAMP}"
MANAGER_LOGIN="manager.us4s2.${TIMESTAMP}@company.com"
AGENT1_LOGIN="agent1.us4s2.${TIMESTAMP}@company.com"
AGENT2_LOGIN="agent2.us4s2.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "24681357"
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
# Step 1: Admin Login & Create Company
################################################################################
echo "=========================================="
echo "Step 1: Admin login and create company"
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
    exit 1
fi

echo "✓ Admin logged in (UID: $ADMIN_UID)"

ADMIN_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')

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
echo "✓ Company created: ID=$COMPANY_ID"

################################################################################
# Step 2: Create Manager and Agents
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create manager and agents"
echo "=========================================="

# Create Manager
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
                \"name\": \"Manager US4S2\",
                \"login\": \"$MANAGER_LOGIN\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [17]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

MANAGER_UID=$(echo "$MANAGER_RESPONSE" | jq -r '.result')
echo "✓ Manager created: UID=$MANAGER_UID"

# Create Agent 1
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
                \"name\": \"Agent 1 US4S2\",
                \"login\": \"$AGENT1_LOGIN\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [23]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT1_UID=$(echo "$AGENT1_USER_RESPONSE" | jq -r '.result')
echo "✓ Agent 1 user created: UID=$AGENT1_UID"

# Generate CPF for Agent 1
CPF_AGENT1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "11122233"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

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
                \"name\": \"Agent 1 US4S2\",
                \"user_id\": $AGENT1_UID,
                \"cpf\": \"$CPF_AGENT1\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT1_ID=$(echo "$AGENT1_RECORD_RESPONSE" | jq -r '.result')
echo "✓ Agent 1 record created: ID=$AGENT1_ID"

# Create Agent 2
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
                \"name\": \"Agent 2 US4S2\",
                \"login\": \"$AGENT2_LOGIN\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [23]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT2_UID=$(echo "$AGENT2_USER_RESPONSE" | jq -r '.result')
echo "✓ Agent 2 user created: UID=$AGENT2_UID"

# Generate CPF for Agent 2
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
                \"name\": \"Agent 2 US4S2\",
                \"user_id\": $AGENT2_UID,
                \"cpf\": \"$CPF_AGENT2\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

AGENT2_ID=$(echo "$AGENT2_RECORD_RESPONSE" | jq -r '.result')
echo "✓ Agent 2 record created: ID=$AGENT2_ID"

################################################################################
# Step 3: Retrieve Reference Data
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Retrieve reference data"
echo "=========================================="

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
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

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
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

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
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id')
echo "✓ State ID: $STATE_ID"

################################################################################
# Step 4: Create Property Assigned to Agent 1
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Create property assigned to Agent 1"
echo "=========================================="

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
        \"name\": \"Test Property Reassignment\",
        \"property_type_id\": $PROPERTY_TYPE_ID,
        \"location_type_id\": $LOCATION_TYPE_ID,
        \"zip_code\": \"01310-100\",
        \"state_id\": $STATE_ID,
        \"city\": \"São Paulo\",
        \"street\": \"Av Paulista\",
        \"street_number\": \"1000\",
        \"area\": 100.0,
        \"price\": 500000.0,
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
    echo "❌ Property creation failed"
    exit 1
fi

echo "✓ Property created: ID=$PROPERTY_ID (assigned to Agent 1)"

################################################################################
# Step 5: Manager Login
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Manager login"
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
    exit 1
fi

echo "✓ Manager logged in: UID=$MANAGER_LOGIN_UID"

MANAGER_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')

################################################################################
# Step 6: Manager Reads Property (Before Reassignment)
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Manager reads property before reassignment"
echo "=========================================="

PROPERTY_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"read\",
            \"args\": [[$PROPERTY_ID]],
            \"kwargs\": {
                \"fields\": [\"name\", \"agent_id\"]
            }
        },
        \"id\": 1
    }")

CURRENT_AGENT_ID=$(echo "$PROPERTY_READ_RESPONSE" | jq -r '.result[0].agent_id[0]')
CURRENT_AGENT_NAME=$(echo "$PROPERTY_READ_RESPONSE" | jq -r '.result[0].agent_id[1]')

echo "✓ Property currently assigned to: $CURRENT_AGENT_NAME (ID=$CURRENT_AGENT_ID)"

if [ "$CURRENT_AGENT_ID" != "$AGENT1_ID" ]; then
    echo "❌ Property should be assigned to Agent 1 ($AGENT1_ID), but is assigned to $CURRENT_AGENT_ID"
    exit 1
fi

################################################################################
# Step 7: Manager Reassigns Property to Agent 2
################################################################################
echo ""
echo "=========================================="
echo "Step 7: Manager reassigns property to Agent 2"
echo "=========================================="

UPDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [[$PROPERTY_ID], {
                \"agent_id\": $AGENT2_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

UPDATE_RESULT=$(echo "$UPDATE_RESPONSE" | jq -r '.result')

if [ "$UPDATE_RESULT" != "true" ]; then
    echo "❌ Manager failed to reassign property"
    echo "Response: $UPDATE_RESPONSE"
    exit 1
fi

echo "✓ Manager successfully reassigned property to Agent 2"

################################################################################
# Step 8: Verify Reassignment
################################################################################
echo ""
echo "=========================================="
echo "Step 8: Verify reassignment"
echo "=========================================="

VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"read\",
            \"args\": [[$PROPERTY_ID]],
            \"kwargs\": {
                \"fields\": [\"name\", \"agent_id\"]
            }
        },
        \"id\": 1
    }")

NEW_AGENT_ID=$(echo "$VERIFY_RESPONSE" | jq -r '.result[0].agent_id[0]')
NEW_AGENT_NAME=$(echo "$VERIFY_RESPONSE" | jq -r '.result[0].agent_id[1]')

echo "✓ Property now assigned to: $NEW_AGENT_NAME (ID=$NEW_AGENT_ID)"

if [ "$NEW_AGENT_ID" != "$AGENT2_ID" ]; then
    echo "❌ Property should be assigned to Agent 2 ($AGENT2_ID), but is assigned to $NEW_AGENT_ID"
    exit 1
fi

################################################################################
# Step 9: Test Complete
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US4-S2 Manager Reassigns Properties"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Property initially assigned to Agent 1 (ID=$AGENT1_ID)"
echo "  - Manager successfully reassigned property to Agent 2 (ID=$AGENT2_ID)"
echo "  - Manager has write permissions on properties"
echo "  - Property reassignment working correctly"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
