#!/bin/bash

################################################################################
# Test Script: US3-S4 Agent Cannot Modify Others' Properties
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 3 - Agent Manages Their Own Properties and Leads
# Scenario: 4 - Agent cannot modify properties assigned to other agents
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
echo "US3-S4: Agent Cannot Modify Others"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US3S4_${TIMESTAMP}"
AGENT_A_LOGIN="agenta.us3s4.${TIMESTAMP}@company.com"
AGENT_B_LOGIN="agentb.us3s4.${TIMESTAMP}@company.com"

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
echo "  Company: $COMPANY_NAME"
echo "  CNPJ: $CNPJ"
echo "  Agent A: $AGENT_A_LOGIN"
echo "  Agent B: $AGENT_B_LOGIN"
echo ""

################################################################################
# Step 1: Admin Login & Setup
################################################################################
echo "Step 1: Admin login and setup..."

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

echo "✅ Admin login successful (UID: $ADMIN_UID)"

################################################################################
# Step 2: Create Company and Agents
################################################################################
echo ""
echo "Step 2: Creating company and agents..."

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
echo "✅ Company created: ID=$COMPANY_ID"

AGENT_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent A US3S4\",
                \"login\": \"$AGENT_A_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

AGENT_A_UID=$(echo "$AGENT_A_RESPONSE" | jq -r '.result // empty')
echo "✅ Agent A created: UID=$AGENT_A_UID"

# Create real.estate.agent record for Agent A
AGENT_A_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent A US3S4\",
                \"user_id\": $AGENT_A_UID,
                \"cpf\": \"123.456.789-01\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 30
    }")

AGENT_A_ID=$(echo "$AGENT_A_RECORD_RESPONSE" | jq -r '.result // empty')
if [ -z "$AGENT_A_ID" ] || [ "$AGENT_A_ID" = "null" ]; then
    echo "❌ Agent A record creation failed"
    echo "Raw Response: $AGENT_A_RECORD_RESPONSE"
    exit 1
fi
echo "✅ Agent A record created: ID=$AGENT_A_ID"

AGENT_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent B US3S4\",
                \"login\": \"$AGENT_B_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

AGENT_B_UID=$(echo "$AGENT_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Agent B created: UID=$AGENT_B_UID"

# Create real.estate.agent record for Agent B
AGENT_B_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent B US3S4\",
                \"user_id\": $AGENT_B_UID,
                \"cpf\": \"987.654.321-09\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 31
    }")

AGENT_B_ID=$(echo "$AGENT_B_RECORD_RESPONSE" | jq -r '.result // empty')
if [ -z "$AGENT_B_ID" ] || [ "$AGENT_B_ID" = "null" ]; then
    echo "❌ Agent B record creation failed"
    echo "Response: $AGENT_B_RECORD_RESPONSE" | jq '.'
    exit 1
fi
echo "✅ Agent B record created: ID=$AGENT_B_ID"

################################################################################
# Step 3: Get reference data IDs (property_type, location_type, state)
################################################################################
echo ""
echo "Step 3: Getting reference data..."

# Get property_type_id (Apartment)
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
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\", \"name\"]}
        },
        \"id\": 5
    }")
PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

# Get location_type_id (Urban)
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.location.type\",
            \"method\": \"search_read\",
            \"args\": [[[\"code\", \"=\", \"urban\"]]],
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\", \"name\"]}
        },
        \"id\": 6
    }")
LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

# Get state_id (São Paulo)
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.state\",
            \"method\": \"search_read\",
            \"args\": [[[\"code\", \"=\", \"SP\"]]],
            \"kwargs\": {\"limit\": 1, \"fields\": [\"id\", \"name\"]}
        },
        \"id\": 7
    }")
STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$PROPERTY_TYPE_ID" ] || [ "$PROPERTY_TYPE_ID" = "null" ]; then
    echo "❌ Failed to get property_type_id"
    exit 1
fi
if [ -z "$LOCATION_TYPE_ID" ] || [ "$LOCATION_TYPE_ID" = "null" ]; then
    echo "❌ Failed to get location_type_id"
    exit 1
fi
if [ -z "$STATE_ID" ] || [ "$STATE_ID" = "null" ]; then
    echo "❌ Failed to get state_id"
    exit 1
fi

echo "✅ Reference data retrieved:"
echo "   Property Type: $PROPERTY_TYPE_ID"
echo "   Location Type: $LOCATION_TYPE_ID"
echo "   State (SP): $STATE_ID"

################################################################################
# Step 4: Create Properties (as admin)
################################################################################
echo ""
echo "Step 4: Creating properties..."

# Property assigned to Agent A
PROPERTY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property Agent A US3S4\",
                \"agent_id\": $AGENT_A_ID,
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"zip_code\": \"01310-100\",
                \"state_id\": $STATE_ID,
                \"city\": \"São Paulo\",
                \"street\": \"Avenida Paulista\",
                \"street_number\": \"1000\",
                \"area\": 100.0
            }],
            \"kwargs\": {}
        },
        \"id\": 8
    }")

PROPERTY_A_ID=$(echo "$PROPERTY_A_RESPONSE" | jq -r '.result // empty')
if [ -z "$PROPERTY_A_ID" ] || [ "$PROPERTY_A_ID" = "null" ]; then
    echo "❌ Property A creation failed"
    echo "Response: $PROPERTY_A_RESPONSE"
    exit 1
fi
echo "✅ Property A created: ID=$PROPERTY_A_ID (assigned to Agent A)"

# Property assigned to Agent B
PROPERTY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property Agent B US3S4\",
                \"agent_id\": $AGENT_B_ID,
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"zip_code\": \"01311-100\",
                \"state_id\": $STATE_ID,
                \"city\": \"São Paulo\",
                \"street\": \"Avenida Paulista\",
                \"street_number\": \"2000\",
                \"area\": 120.0
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

PROPERTY_B_ID=$(echo "$PROPERTY_B_RESPONSE" | jq -r '.result // empty')
if [ -z "$PROPERTY_B_ID" ] || [ "$PROPERTY_B_ID" = "null" ]; then
    echo "❌ Property B creation failed"
    echo "Response: $PROPERTY_B_RESPONSE"
    exit 1
fi
echo "✅ Property B created: ID=$PROPERTY_B_ID (assigned to Agent B)"

################################################################################
# Step 5: Agent A Login
################################################################################
echo ""
echo "Step 5: Agent A login..."

rm -f cookies.txt

AGENT_A_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$AGENT_A_LOGIN\",
            \"password\": \"agent123\"
        },
        \"id\": 7
    }")

AGENT_A_SESSION_UID=$(echo "$AGENT_A_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✅ Agent A login successful (UID: $AGENT_A_SESSION_UID)"

################################################################################
# Step 6: Agent A Can Update Their Own Property
################################################################################
echo ""
echo "Step 6: Agent A updating their own property..."

UPDATE_OWN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [
                [$PROPERTY_A_ID],
                {
                    \"price\": 320000.0,
                    \"property_status\": \"occupied\"
                }
            ],
            \"kwargs\": {}
        },
        \"id\": 8
    }")

UPDATE_OWN_RESULT=$(echo "$UPDATE_OWN_RESPONSE" | jq -r '.result // empty')

if [ "$UPDATE_OWN_RESULT" == "true" ]; then
    echo "✅ Agent A can update their own property"
else
    echo "❌ Agent A cannot update their own property"
    echo "Response: $UPDATE_OWN_RESPONSE"
    exit 1
fi

################################################################################
# Step 7: Agent A Tries to Search for Agent B's Property
################################################################################
echo ""
echo "Step 7: Agent A searching for properties..."

SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $PROPERTY_B_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"agent_id\"]
            }
        },
        \"id\": 9
    }")

SEARCH_RESULTS=$(echo "$SEARCH_RESPONSE" | jq -r '.result | length')

if [ "$SEARCH_RESULTS" -eq "0" ]; then
    echo "✅ Agent A cannot see Agent B's property in search (isolation verified)"
else
    echo "❌ Agent A can see Agent B's property (isolation failed)"
    exit 1
fi

################################################################################
# Step 8: Agent A Tries to Update Agent B's Property Directly (SECURITY TEST)
################################################################################
echo ""
echo "Step 8: Agent A trying to update Agent B's property (should FAIL)..."

UPDATE_OTHER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"write\",
            \"args\": [
                [$PROPERTY_B_ID],
                {\"selling_price\": 999999.0}
            ],
            \"kwargs\": {}
        },
        \"id\": 10
    }")

ERROR_MSG=$(echo "$UPDATE_OTHER_RESPONSE" | jq -r '.error.data.message // empty')
UPDATE_OTHER_RESULT=$(echo "$UPDATE_OTHER_RESPONSE" | jq -r '.result // empty')

if [ ! -z "$ERROR_MSG" ] && [ "$ERROR_MSG" != "null" ]; then
    echo "✅ Agent A prevented from updating Agent B's property (error: access denied)"
elif [ "$UPDATE_OTHER_RESULT" == "false" ] || [ -z "$UPDATE_OTHER_RESULT" ] || [ "$UPDATE_OTHER_RESULT" == "null" ]; then
    echo "✅ Agent A cannot update Agent B's property"
else
    echo "❌ Agent A was able to update Agent B's property (security violation!)"
    exit 1
fi

################################################################################
# Step 9: Verify Property B Unchanged
################################################################################
echo ""
echo "Step 9: Verifying Property B was not modified..."

rm -f cookies.txt

# Admin login to verify
ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
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
        \"id\": 11
    }")

PROPERTY_B_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $PROPERTY_B_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"price\", \"agent_id\"]
            }
        },
        \"id\": 12
    }")

PROPERTY_B_PRICE=$(echo "$PROPERTY_B_CHECK" | jq -r '.result[0].price // "null"')
PROPERTY_B_AGENT=$(echo "$PROPERTY_B_CHECK" | jq -r '.result[0].agent_id[0] // empty')

# Property B was created without a price (0.0 or null/false), and with Agent B assigned
# If price is still 0.0/null/false and agent is still Agent B, then it's unchanged
if ([ "$PROPERTY_B_PRICE" == "0" ] || [ "$PROPERTY_B_PRICE" == "0.0" ] || [ "$PROPERTY_B_PRICE" == "null" ] || [ "$PROPERTY_B_PRICE" == "false" ]) && [ "$PROPERTY_B_AGENT" == "$AGENT_B_ID" ]; then
    echo "✅ Property B unchanged - still at original price (0.0) and assigned to Agent B"
else
    echo "❌ Property B was modified (price: $PROPERTY_B_PRICE, agent: $PROPERTY_B_AGENT, expected agent: $AGENT_B_ID)"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US3-S4 Agent Cannot Modify Others"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Agent A can update their own property"
echo "  - Agent A cannot see Agent B's property in searches"
echo "  - Agent A cannot update Agent B's property"
echo "  - Property isolation working correctly between agents"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
