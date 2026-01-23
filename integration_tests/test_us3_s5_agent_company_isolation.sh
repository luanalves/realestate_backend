#!/bin/bash

################################################################################
# Test Script: US3-S5 Agent Company Isolation
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 3 - Agent Manages Their Own Properties and Leads
# Scenario: 5 - Agent sees only properties from their company
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
echo "US3-S5: Agent Company Isolation"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_A_NAME="CompanyA_US3S5_${TIMESTAMP}"
COMPANY_B_NAME="CompanyB_US3S5_${TIMESTAMP}"
AGENT_A_LOGIN="agenta.us3s5.${TIMESTAMP}@companya.com"
AGENT_B_LOGIN="agentb.us3s5.${TIMESTAMP}@companyb.com"

# Generate valid CNPJs
CNPJ_A=$(python3 << 'PYTHON_EOF'
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

CNPJ_B=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "86420975"
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
echo "  Company A: $COMPANY_A_NAME (CNPJ: $CNPJ_A)"
echo "  Company B: $COMPANY_B_NAME (CNPJ: $CNPJ_B)"
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
# Step 2: Create Companies
################################################################################
echo ""
echo "Step 2: Creating companies..."

COMPANY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"$COMPANY_A_NAME\",
                \"cnpj\": \"$CNPJ_A\"
            }],
            \"kwargs\": {}
        },
        \"id\": 2
    }")

COMPANY_A_ID=$(echo "$COMPANY_A_RESPONSE" | jq -r '.result // empty')
echo "✅ Company A created: ID=$COMPANY_A_ID"

COMPANY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"$COMPANY_B_NAME\",
                \"cnpj\": \"$CNPJ_B\"
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

COMPANY_B_ID=$(echo "$COMPANY_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Company B created: ID=$COMPANY_B_ID"

################################################################################
# Step 3: Create Agent Users
################################################################################
echo ""
echo "Step 3: Creating agent users..."

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
                \"name\": \"Agent A US3S5\",
                \"login\": \"$AGENT_A_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_A_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

AGENT_A_UID=$(echo "$AGENT_A_RESPONSE" | jq -r '.result // empty')
echo "✅ Agent A created: UID=$AGENT_A_UID (assigned to Company A)"

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
                \"name\": \"Agent A US3S5\",
                \"user_id\": $AGENT_A_UID,
                \"cpf\": \"111.222.333-44\",
                \"company_ids\": [[6, 0, [$COMPANY_A_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 40
    }")

AGENT_A_ID=$(echo "$AGENT_A_RECORD_RESPONSE" | jq -r '.result // empty')
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
                \"name\": \"Agent B US3S5\",
                \"login\": \"$AGENT_B_LOGIN\",
                \"password\": \"agent123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_B_ID]]],
                \"groups_id\": [[6, 0, [23]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT_B_UID=$(echo "$AGENT_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Agent B created: UID=$AGENT_B_UID (assigned to Company B)"

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
                \"name\": \"Agent B US3S5\",
                \"user_id\": $AGENT_B_UID,
                \"cpf\": \"555.666.777-88\",
                \"company_ids\": [[6, 0, [$COMPANY_B_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 41
    }")

AGENT_B_ID=$(echo "$AGENT_B_RECORD_RESPONSE" | jq -r '.result // empty')
echo "✅ Agent B record created: ID=$AGENT_B_ID"

################################################################################
# Step 3.5: Get Reference Data (Property Type, Location Type, State)
################################################################################
echo ""
echo "Step 3.5: Retrieving reference data..."

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
        \"id\": 42
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✅ Property Type ID: $PROPERTY_TYPE_ID"

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
        \"id\": 43
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✅ Location Type ID: $LOCATION_TYPE_ID"

# Get state (São Paulo)
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
        \"id\": 44
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✅ State ID: $STATE_ID"

################################################################################
# Step 4: Create Properties in Both Companies
################################################################################
echo ""
echo "Step 4: Creating properties..."

# 3 Properties for Company A
COMPANY_A_PROPERTIES=()
for i in 1 2 3; do
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
                    \"name\": \"Property CompanyA-$i US3S5\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"zip_code\": \"01310-100\",
                    \"state_id\": $STATE_ID,
                    \"city\": \"São Paulo\",
                    \"street\": \"Av Paulista\",
                    \"street_number\": \"$((1000 + $i))\",
                    \"area\": 80.0,
                    \"price\": 300000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_A_ID]]],
                    \"agent_id\": $AGENT_A_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((5 + $i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    COMPANY_A_PROPERTIES+=($PROP_ID)
    echo "✅ Property A-$i created: ID=$PROP_ID (Company A, Agent A)"
done

# 2 Properties for Company B
COMPANY_B_PROPERTIES=()
for i in 1 2; do
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
                    \"name\": \"Property CompanyB-$i US3S5\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"zip_code\": \"04571-000\",
                    \"state_id\": $STATE_ID,
                    \"city\": \"São Paulo\",
                    \"street\": \"Av Brigadeiro\",
                    \"street_number\": \"$((2000 + $i))\",
                    \"area\": 150.0,
                    \"price\": 500000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_B_ID]]],
                    \"agent_id\": $AGENT_B_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((8 + $i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    COMPANY_B_PROPERTIES+=($PROP_ID)
    echo "✅ Property B-$i created: ID=$PROP_ID (Company B, Agent B)"
done

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
        \"id\": 11
    }")

AGENT_A_SESSION_UID=$(echo "$AGENT_A_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✅ Agent A login successful (UID: $AGENT_A_SESSION_UID)"

################################################################################
# Step 6: Agent A Views Properties
################################################################################
echo ""
echo "Step 6: Agent A viewing properties..."

AGENT_A_PROPS=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"company_ids\", \"agent_id\"]
            }
        },
        \"id\": 12
    }")

AGENT_A_VISIBLE_COUNT=$(echo "$AGENT_A_PROPS" | jq -r '.result | length')
AGENT_A_PROPS_IDS=$(echo "$AGENT_A_PROPS" | jq -r '.result[].id')

echo "Agent A sees $AGENT_A_VISIBLE_COUNT properties"

# Verify Agent A sees exactly 3 properties (all from Company A)
if [ "$AGENT_A_VISIBLE_COUNT" -ne "3" ]; then
    echo "❌ Agent A should see 3 properties, but sees $AGENT_A_VISIBLE_COUNT"
    exit 1
fi

# Verify all visible properties belong to Company A
ALL_FROM_COMPANY_A=true
for prop_id in $AGENT_A_PROPS_IDS; do
    COMPANY_OF_PROP=$(echo "$AGENT_A_PROPS" | jq -r ".result[] | select(.id == $prop_id) | .company_ids[0] // empty")
    if [ "$COMPANY_OF_PROP" != "$COMPANY_A_ID" ]; then
        ALL_FROM_COMPANY_A=false
        echo "⚠️  Property $prop_id not from Company A (company: $COMPANY_OF_PROP)"
    fi
done

if [ "$ALL_FROM_COMPANY_A" = true ]; then
    echo "✅ Agent A sees only Company A properties (isolation verified)"
else
    echo "❌ Agent A sees properties from other companies"
    exit 1
fi

################################################################################
# Step 7: Agent A Tries to Access Company B Property Directly
################################################################################
echo ""
echo "Step 7: Agent A trying to access Company B property..."

COMPANY_B_PROP_ID=${COMPANY_B_PROPERTIES[0]}

DIRECT_ACCESS=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $COMPANY_B_PROP_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"]
            }
        },
        \"id\": 13
    }")

ACCESS_RESULTS=$(echo "$DIRECT_ACCESS" | jq -r '.result | length')

if [ "$ACCESS_RESULTS" -eq "0" ]; then
    echo "✅ Agent A cannot access Company B property (isolation verified)"
else
    echo "❌ Agent A can access Company B property (multi-tenancy violation!)"
    exit 1
fi

################################################################################
# Step 8: Agent B Login and Verification
################################################################################
echo ""
echo "Step 8: Agent B login and verification..."

rm -f cookies.txt

AGENT_B_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$AGENT_B_LOGIN\",
            \"password\": \"agent123\"
        },
        \"id\": 14
    }")

AGENT_B_SESSION_UID=$(echo "$AGENT_B_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✅ Agent B login successful (UID: $AGENT_B_SESSION_UID)"

AGENT_B_PROPS=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"company_ids\", \"agent_id\"]
            }
        },
        \"id\": 15
    }")

AGENT_B_VISIBLE_COUNT=$(echo "$AGENT_B_PROPS" | jq -r '.result | length')
echo "Agent B sees $AGENT_B_VISIBLE_COUNT properties"

if [ "$AGENT_B_VISIBLE_COUNT" -ne "2" ]; then
    echo "❌ Agent B should see 2 properties, but sees $AGENT_B_VISIBLE_COUNT"
    exit 1
fi

# Verify all belong to Company B
AGENT_B_PROPS_IDS=$(echo "$AGENT_B_PROPS" | jq -r '.result[].id')
ALL_FROM_COMPANY_B=true
for prop_id in $AGENT_B_PROPS_IDS; do
    COMPANY_OF_PROP=$(echo "$AGENT_B_PROPS" | jq -r ".result[] | select(.id == $prop_id) | .company_ids[0] // empty")
    if [ "$COMPANY_OF_PROP" != "$COMPANY_B_ID" ]; then
        ALL_FROM_COMPANY_B=false
    fi
done

if [ "$ALL_FROM_COMPANY_B" = true ]; then
    echo "✅ Agent B sees only Company B properties (isolation verified)"
else
    echo "❌ Agent B sees properties from other companies"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US3-S5 Agent Company Isolation"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Agent A sees only Company A properties (3 properties)"
echo "  - Agent A cannot access Company B properties"
echo "  - Agent B sees only Company B properties (2 properties)"
echo "  - Multi-tenancy isolation working correctly for Agents"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
