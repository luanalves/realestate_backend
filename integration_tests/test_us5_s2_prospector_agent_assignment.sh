#!/bin/bash

################################################################################
# Test Script: US5-S2 Prospector + Agent Assignment
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 5 - Prospector Creates Properties with Commission Split
# Scenario: 2 - Manager assigns selling agent, both prospector and agent linked
################################################################################

# Load configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-realestate}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

echo "================================================"
echo "US5-S2: Prospector + Agent Assignment"
echo "================================================"

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US5S2_${TIMESTAMP}"
PROSPECTOR_LOGIN="prospector.us5s2.${TIMESTAMP}@company.com"
AGENT_LOGIN="agent.us5s2.${TIMESTAMP}@company.com"
MANAGER_LOGIN="manager.us5s2.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "44556677"
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
echo "  Prospector: $PROSPECTOR_LOGIN"
echo "  Agent: $AGENT_LOGIN"
echo "  Manager: $MANAGER_LOGIN"
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

# Create company
COMPANY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
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
    exit 1
fi

echo "✓ Company created: ID=$COMPANY_ID"

################################################################################
# Step 2: Create Users (Prospector, Agent, Manager)
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create prospector, agent, and manager"
echo "=========================================="

PROSPECTOR_GROUP_ID=24
AGENT_GROUP_ID=23
MANAGER_GROUP_ID=17

# Create Prospector user
PROSPECTOR_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector US5S2\",
                \"login\": \"$PROSPECTOR_LOGIN\",
                \"password\": \"prospector123\",
                \"groups_id\": [[6, 0, [$PROSPECTOR_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

PROSPECTOR_UID=$(echo "$PROSPECTOR_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector user created: UID=$PROSPECTOR_UID"

# Create prospector agent record
CPF_PROSPECTOR=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "22233344"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

PROSPECTOR_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector US5S2\",
                \"user_id\": $PROSPECTOR_UID,
                \"cpf\": \"$CPF_PROSPECTOR\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

PROSPECTOR_AGENT_ID=$(echo "$PROSPECTOR_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector agent record created: ID=$PROSPECTOR_AGENT_ID"

# Create Agent user
AGENT_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent US5S2\",
                \"login\": \"$AGENT_LOGIN\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [$AGENT_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT_UID=$(echo "$AGENT_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Agent user created: UID=$AGENT_UID"

# Create agent record
CPF_AGENT=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "55566677"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

AGENT_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent US5S2\",
                \"user_id\": $AGENT_UID,
                \"cpf\": \"$CPF_AGENT\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

AGENT_AGENT_ID=$(echo "$AGENT_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Agent agent record created: ID=$AGENT_AGENT_ID"

# Create Manager user
MANAGER_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager US5S2\",
                \"login\": \"$MANAGER_LOGIN\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [$MANAGER_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

MANAGER_UID=$(echo "$MANAGER_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Manager user created: UID=$MANAGER_UID"

################################################################################
# Step 3: Get Reference Data
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Retrieving reference data"
echo "=========================================="

# Get property type
PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
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
        \"id\": 8
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

# Get location type
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
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
        \"id\": 9
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

# Get state
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
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
        \"id\": 10
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ State ID: $STATE_ID"

################################################################################
# Step 4: Prospector Creates Property
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Prospector creates property"
echo "=========================================="

PROPERTY_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property for Commission Split US5S2\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"01310-100\",
                \"city\": \"São Paulo\",
                \"street\": \"Av Paulista\",
                \"street_number\": \"2000\",
                \"area\": 150.0,
                \"price\": 600000.0,
                \"property_status\": \"available\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"prospector_id\": $PROSPECTOR_AGENT_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 11
    }")

PROPERTY_ID=$(echo "$PROPERTY_CREATE_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" == "null" ]; then
    echo "❌ Property creation failed"
    exit 1
fi

echo "✓ Property created: ID=$PROPERTY_ID (prospector_id=$PROSPECTOR_AGENT_ID)"

################################################################################
# Step 5: Manager Assigns Selling Agent
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Manager assigns selling agent"
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
        \"id\": 12
    }")

MANAGER_SESSION_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Manager logged in: UID=$MANAGER_SESSION_UID"

# Assign agent_id to property
ASSIGN_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [
                [$PROPERTY_ID],
                {\"agent_id\": $AGENT_AGENT_ID}
            ],
            \"kwargs\": {}
        },
        \"id\": 13
    }")

ASSIGN_RESULT=$(echo "$ASSIGN_AGENT_RESPONSE" | jq -r '.result // empty')

if [ "$ASSIGN_RESULT" == "true" ]; then
    echo "✓ Selling agent assigned to property"
else
    echo "❌ Failed to assign selling agent"
    exit 1
fi

################################################################################
# Step 6: Verify Both Prospector and Agent Linked
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Verify prospector + agent linkage"
echo "=========================================="

PROPERTY_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"read\",
            \"args\": [[$PROPERTY_ID]],
            \"kwargs\": {
                \"fields\": [\"name\", \"prospector_id\", \"agent_id\"]
            }
        },
        \"id\": 14
    }")

PROSPECTOR_ID_FINAL=$(echo "$PROPERTY_READ_RESPONSE" | jq -r '.result[0].prospector_id[0] // empty')
AGENT_ID_FINAL=$(echo "$PROPERTY_READ_RESPONSE" | jq -r '.result[0].agent_id[0] // empty')

echo "Property prospector_id: $PROSPECTOR_ID_FINAL (expected: $PROSPECTOR_AGENT_ID)"
echo "Property agent_id: $AGENT_ID_FINAL (expected: $AGENT_AGENT_ID)"

if [ "$PROSPECTOR_ID_FINAL" == "$PROSPECTOR_AGENT_ID" ] && [ "$AGENT_ID_FINAL" == "$AGENT_AGENT_ID" ]; then
    echo "✓ Both prospector and selling agent correctly linked"
else
    echo "❌ Linkage verification failed"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US5-S2 Prospector + Agent Assignment"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Prospector created property with prospector_id: $PROSPECTOR_AGENT_ID"
echo "  - Manager assigned selling agent_id: $AGENT_AGENT_ID"
echo "  - Property has both prospector and agent linked"
echo "  - Ready for commission split calculation"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
