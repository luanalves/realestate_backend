#!/bin/bash

################################################################################
# Test Script: US3-S2 Agent Auto-Assignment
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 3 - Agent Manages Their Own Properties and Leads
# Scenario: 2 - Property automatically assigns to agent when they create it
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
echo "US3-S2: Agent Auto-Assignment"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US3S2_${TIMESTAMP}"
AGENT_LOGIN="agent.us3s2.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "55667788"
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
echo "  Agent: $AGENT_LOGIN"
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
                \"cnpj\": \"$CNPJ\",
                \"state\": \"active\"
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

echo "✅ Company created: ID=$COMPANY_ID"

################################################################################
# Step 3: Create Agent User
################################################################################
echo ""
echo "Step 3: Creating agent user..."

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
                \"name\": \"Agent US3S2\",
                \"login\": \"$AGENT_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

AGENT_UID=$(echo "$AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$AGENT_UID" ] || [ "$AGENT_UID" == "null" ]; then
    echo "❌ Agent user creation failed"
    exit 1
fi

echo "✅ Agent created: UID=$AGENT_UID"

################################################################################
# Step 4: Agent Login
################################################################################
echo ""
echo "Step 4: Agent login..."

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
        \"id\": 4
    }")

AGENT_SESSION_UID=$(echo "$AGENT_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$AGENT_SESSION_UID" ] || [ "$AGENT_SESSION_UID" == "null" ]; then
    echo "❌ Agent login failed"
    exit 1
fi

echo "✅ Agent login successful (UID: $AGENT_SESSION_UID)"

################################################################################
# Step 5: Agent Creates Property WITHOUT Specifying agent_id
################################################################################
echo ""
echo "Step 5: Agent creating property (without specifying agent_id)..."

PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Auto-Assigned Property US3S2\",
                \"property_type\": \"apartment\",
                \"bedrooms\": 2,
                \"bathrooms\": 1,
                \"parking_spaces\": 1,
                \"area\": 85.0,
                \"selling_price\": 350000.0,
                \"state\": \"available\",
                \"company_id\": $COMPANY_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.result // empty')
ERROR_MESSAGE=$(echo "$PROPERTY_RESPONSE" | jq -r '.error.data.message // empty')

if [ ! -z "$ERROR_MESSAGE" ] && [ "$ERROR_MESSAGE" != "null" ]; then
    echo "⚠️  Property creation failed: $ERROR_MESSAGE"
    echo "This may indicate agents don't have create permissions"
    exit 1
fi

if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" == "null" ]; then
    echo "❌ Property creation failed"
    echo "Response: $PROPERTY_RESPONSE"
    exit 1
fi

echo "✅ Property created: ID=$PROPERTY_ID"

################################################################################
# Step 6: Verify Property is Auto-Assigned to Agent
################################################################################
echo ""
echo "Step 6: Verifying auto-assignment..."

PROPERTY_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $PROPERTY_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"agent_id\", \"company_id\"]
            }
        },
        \"id\": 6
    }")

ASSIGNED_AGENT=$(echo "$PROPERTY_CHECK" | jq -r '.result[0].agent_id[0] // empty')

if [ -z "$ASSIGNED_AGENT" ] || [ "$ASSIGNED_AGENT" == "null" ]; then
    echo "⚠️  Property was created but agent_id is not set"
    echo "This may indicate auto-assignment logic is not implemented"
    echo "Property data: $(echo "$PROPERTY_CHECK" | jq -r '.result[0]')"
    
    echo ""
    echo "====================================="
    echo "⚠️  TEST INCOMPLETE: Auto-assignment not working"
    echo "====================================="
    echo ""
    echo "Expected: Property should automatically get agent_id=$AGENT_UID"
    echo "Actual: agent_id is empty"
    echo ""
    echo "This is expected if auto-assignment hasn't been implemented yet."
    echo "Implement auto-assignment in the create() method of real.estate.property:"
    echo "  - Check if agent_id is not set"
    echo "  - Check if current user has Real Estate Agent group"
    echo "  - If yes, set agent_id = current user's ID"
    echo ""
    
    exit 1
fi

if [ "$ASSIGNED_AGENT" == "$AGENT_UID" ]; then
    echo "✅ Property automatically assigned to agent (agent_id=$AGENT_UID)"
else
    echo "❌ Property assigned to wrong agent"
    echo "Expected: $AGENT_UID, Got: $ASSIGNED_AGENT"
    exit 1
fi

################################################################################
# Step 7: Create Multiple Properties and Verify All Auto-Assigned
################################################################################
echo ""
echo "Step 7: Creating multiple properties to verify consistent auto-assignment..."

ALL_ASSIGNED=true

for i in 2 3 4; do
    PROP_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b cookies.txt \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.property\",
                \"method\": \"create\",
                \"args\": [{
                    \"name\": \"Property $i US3S2\",
                    \"property_type\": \"apartment\",
                    \"bedrooms\": 2,
                    \"bathrooms\": 1,
                    \"parking_spaces\": 1,
                    \"area\": 80.0,
                    \"selling_price\": 300000.0,
                    \"state\": \"available\",
                    \"company_id\": $COMPANY_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((6 + $i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    
    if [ ! -z "$PROP_ID" ] && [ "$PROP_ID" != "null" ]; then
        # Verify assignment
        PROP_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
            -H "Content-Type: application/json" \
            -b cookies.txt \
            -d "{
                \"jsonrpc\": \"2.0\",
                \"method\": \"call\",
                \"params\": {
                    \"model\": \"real.estate.property\",
                    \"method\": \"search_read\",
                    \"args\": [[
                        [\"id\", \"=\", $PROP_ID]
                    ]],
                    \"kwargs\": {
                        \"fields\": [\"agent_id\"]
                    }
                },
                \"id\": $((9 + $i))
            }")
        
        PROP_AGENT=$(echo "$PROP_CHECK" | jq -r '.result[0].agent_id[0] // empty')
        
        if [ "$PROP_AGENT" == "$AGENT_UID" ]; then
            echo "✅ Property $i auto-assigned correctly"
        else
            echo "❌ Property $i not correctly assigned (expected: $AGENT_UID, got: $PROP_AGENT)"
            ALL_ASSIGNED=false
        fi
    fi
done

if [ "$ALL_ASSIGNED" = false ]; then
    echo "❌ Not all properties were correctly auto-assigned"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US3-S2 Agent Auto-Assignment"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Agent created property without specifying agent_id"
echo "  - Property was automatically assigned to the creating agent"
echo "  - Multiple properties all auto-assigned correctly"
echo "  - Auto-assignment logic working as expected"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
