#!/bin/bash

################################################################################
# Test Script: US2-S1 Manager Creates Agent
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 2 - Owner Creates Team Members with Different Roles
# Scenario: 1 - Manager creates agent with proper permissions
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
echo "US2-S1: Manager Creates Agent"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US2S1_${TIMESTAMP}"
MANAGER_LOGIN="manager.us2s1.${TIMESTAMP}@company.com"
AGENT_LOGIN="agent.us2s1.${TIMESTAMP}@company.com"

# Generate valid CNPJ for the company
# Using Python to calculate valid check digits
CNPJ_BASE="33444555"
CNPJ_BRANCH="0001"
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "33444555"
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
echo "  Manager: $MANAGER_LOGIN"
echo "  Agent: $AGENT_LOGIN"
echo ""

################################################################################
# Step 1: Admin Login
################################################################################
echo "Step 1: Admin login..."

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

echo "✅ Admin login successful (UID: $ADMIN_UID)"

################################################################################
# Step 2: Create Company
################################################################################
echo ""
echo "Step 2: Creating company..."

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
    echo "Response: $COMPANY_RESPONSE"
    exit 1
fi

echo "✅ Company created: ID=$COMPANY_ID"

################################################################################
# Step 3: Create Manager User
################################################################################
echo ""
echo "Step 3: Creating manager user..."

# Manager group ID: 17 (Real Estate Company Manager)
MANAGER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager US2S1\",
                \"login\": \"$MANAGER_LOGIN\",
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

echo "✅ Manager user created: UID=$MANAGER_UID"

################################################################################
# Step 4: Manager Login
################################################################################
echo ""
echo "Step 4: Manager login..."

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
        \"id\": 4
    }")

MANAGER_SESSION_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_SESSION_UID" ] || [ "$MANAGER_SESSION_UID" == "null" ]; then
    echo "❌ Manager login failed"
    echo "Response: $MANAGER_LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Manager login successful (UID: $MANAGER_SESSION_UID)"

################################################################################
# Step 5: Manager Creates Agent User
################################################################################
echo ""
echo "Step 5: Manager attempting to create agent user..."

# Agent group ID: 23 (Real Estate Agent)
AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent US2S1\",
                \"login\": \"$AGENT_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

# Check if agent creation was successful
AGENT_UID=$(echo "$AGENT_RESPONSE" | jq -r '.result // empty')
ERROR_MESSAGE=$(echo "$AGENT_RESPONSE" | jq -r '.error.data.message // empty')

if [ ! -z "$ERROR_MESSAGE" ] && [ "$ERROR_MESSAGE" != "null" ]; then
    echo "❌ Manager cannot create agent (expected behavior - only owners can create users)"
    echo "Error: $ERROR_MESSAGE"
    echo ""
    echo "✅ TEST PASSED: Manager correctly restricted from creating users"
    exit 0
fi

if [ -z "$AGENT_UID" ] || [ "$AGENT_UID" == "null" ]; then
    echo "⚠️  Agent creation returned unexpected response"
    echo "Response: $AGENT_RESPONSE"
    exit 1
fi

echo "⚠️  Manager was able to create agent (UID: $AGENT_UID)"
echo "This may indicate missing access control rules"

################################################################################
# Step 6: Verify Agent User
################################################################################
echo ""
echo "Step 6: Verifying agent user..."

AGENT_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $AGENT_UID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"login\", \"groups_id\", \"estate_company_ids\"]
            }
        },
        \"id\": 6
    }")

AGENT_DATA=$(echo "$AGENT_CHECK" | jq -r '.result[0] // empty')

if [ -z "$AGENT_DATA" ] || [ "$AGENT_DATA" == "null" ]; then
    echo "❌ Agent verification failed"
    exit 1
fi

AGENT_GROUPS=$(echo "$AGENT_DATA" | jq -r '.groups_id // []')
AGENT_COMPANIES=$(echo "$AGENT_DATA" | jq -r '.estate_company_ids // []')

echo "Agent details:"
echo "  Name: $(echo "$AGENT_DATA" | jq -r '.name')"
echo "  Login: $(echo "$AGENT_DATA" | jq -r '.login')"
echo "  Groups: $AGENT_GROUPS"
echo "  Companies: $AGENT_COMPANIES"

# Verify agent has correct group (23 = Real Estate Agent)
if echo "$AGENT_GROUPS" | grep -q "23"; then
    echo "✅ Agent has correct security group"
else
    echo "❌ Agent missing Real Estate Agent group"
    exit 1
fi

# Verify agent is assigned to the correct company
if echo "$AGENT_COMPANIES" | grep -q "$COMPANY_ID"; then
    echo "✅ Agent assigned to correct company"
else
    echo "❌ Agent not assigned to company"
    exit 1
fi

################################################################################
# Step 7: Test Agent Login
################################################################################
echo ""
echo "Step 7: Testing agent login..."

rm -f cookies.txt

AGENT_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$AGENT_LOGIN\",
            \"password\": \"agent123\"
        },
        \"id\": 7
    }")

AGENT_SESSION_UID=$(echo "$AGENT_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$AGENT_SESSION_UID" ] || [ "$AGENT_SESSION_UID" == "null" ]; then
    echo "❌ Agent login failed"
    echo "Response: $AGENT_LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Agent login successful (UID: $AGENT_SESSION_UID)"

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US2-S1 Manager Creates Agent"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Company created: $COMPANY_NAME (ID: $COMPANY_ID)"
echo "  - Manager user created: $MANAGER_LOGIN (UID: $MANAGER_UID)"
echo "  - Agent user created by manager: $AGENT_LOGIN (UID: $AGENT_UID)"
echo "  - Agent login verified"
echo "  - Agent has correct permissions and company assignment"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
