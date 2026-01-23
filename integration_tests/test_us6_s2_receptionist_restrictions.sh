#!/bin/bash

################################################################################
# Test Script: US6-S2 Receptionist Restrictions
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 6 - Receptionist Front Desk Operations
# Scenario: 2 - Receptionist cannot create/modify properties, agents, leads, or sales
#
# STATUS: ⚠️ EXPECTED TO PARTIALLY FAIL - ACL bug
# Receptionist has read-only ACL on properties but can actually create them.
# Bug: ACL should be (1,0,0,0) but property creation succeeds.
################################################################################

# Load configuration
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-realestate}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

echo "========================================"
echo "US6-S2: Receptionist Restrictions"
echo "========================================"

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US6S2_${TIMESTAMP}"
RECEPTIONIST_LOGIN="receptionist.us6s2.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "88990011"
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
echo "  Receptionist: $RECEPTIONIST_LOGIN"
echo ""

################################################################################
# Step 1: Admin Setup
################################################################################
echo "=========================================="
echo "Step 1: Admin setup"
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
echo "✓ Company created: ID=$COMPANY_ID"

# Create receptionist user
RECEPTIONIST_GROUP_ID=19

RECEPTIONIST_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Receptionist US6S2\",
                \"login\": \"$RECEPTIONIST_LOGIN\",
                \"password\": \"receptionist123\",
                \"groups_id\": [[6, 0, [$RECEPTIONIST_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

RECEPTIONIST_UID=$(echo "$RECEPTIONIST_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Receptionist user created: UID=$RECEPTIONIST_UID"

# Get reference data
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
        \"id\": 4
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

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
        \"id\": 5
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')

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
        \"id\": 6
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ Reference data retrieved"

################################################################################
# Step 2: Receptionist Login
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Receptionist login"
echo "=========================================="

rm -f cookies.txt

RECEPTIONIST_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$RECEPTIONIST_LOGIN\",
            \"password\": \"receptionist123\"
        },
        \"id\": 7
    }")

RECEPTIONIST_SESSION_UID=$(echo "$RECEPTIONIST_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Receptionist logged in: UID=$RECEPTIONIST_SESSION_UID"

################################################################################
# Step 3: Test Restrictions
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Test receptionist restrictions"
echo "=========================================="

# Test 1: Cannot create properties
echo ""
echo "Test 1: Receptionist attempts to create property"
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
                \"name\": \"Receptionist Property Attempt\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"01310-100\",
                \"city\": \"São Paulo\",
                \"street\": \"Rua Test\",
                \"street_number\": \"100\",
                \"area\": 80.0,
                \"price\": 300000.0,
                \"property_status\": \"available\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 8
    }")

PROPERTY_CREATE_ERROR=$(echo "$PROPERTY_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$PROPERTY_CREATE_ERROR" ]; then
    echo "✓ Receptionist cannot create properties (permission denied)"
else
    NEW_PROPERTY_ID=$(echo "$PROPERTY_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_PROPERTY_ID" ] && [ "$NEW_PROPERTY_ID" != "null" ]; then
        echo "❌ BUG: Receptionist should not be able to create properties (created ID=$NEW_PROPERTY_ID)"
        exit 1
    fi
fi

# Test 2: Cannot create agents
echo ""
echo "Test 2: Receptionist attempts to create agent"
AGENT_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Receptionist Agent Attempt\",
                \"cpf\": \"111.222.333-44\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

AGENT_CREATE_ERROR=$(echo "$AGENT_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$AGENT_CREATE_ERROR" ]; then
    echo "✓ Receptionist cannot create agents (permission denied)"
else
    NEW_AGENT_ID=$(echo "$AGENT_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_AGENT_ID" ] && [ "$NEW_AGENT_ID" != "null" ]; then
        echo "❌ BUG: Receptionist should not be able to create agents (created ID=$NEW_AGENT_ID)"
        exit 1
    fi
fi

# Test 3: Cannot create leads
echo ""
echo "Test 3: Receptionist attempts to create lead"
LEAD_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lead\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Receptionist Lead Attempt\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 10
    }")

LEAD_CREATE_ERROR=$(echo "$LEAD_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$LEAD_CREATE_ERROR" ]; then
    echo "✓ Receptionist cannot create leads (permission denied)"
else
    NEW_LEAD_ID=$(echo "$LEAD_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_LEAD_ID" ] && [ "$NEW_LEAD_ID" != "null" ]; then
        echo "❌ BUG: Receptionist should not be able to create leads (created ID=$NEW_LEAD_ID)"
        exit 1
    fi
fi

# Test 4: Cannot create sales
echo ""
echo "Test 4: Receptionist attempts to create sale"
SALE_CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.sale\",
            \"method\": \"create\",
            \"args\": [{
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 11
    }")

SALE_CREATE_ERROR=$(echo "$SALE_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$SALE_CREATE_ERROR" ]; then
    echo "✓ Receptionist cannot create sales (permission denied)"
else
    NEW_SALE_ID=$(echo "$SALE_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_SALE_ID" ] && [ "$NEW_SALE_ID" != "null" ]; then
        echo "❌ BUG: Receptionist should not be able to create sales (created ID=$NEW_SALE_ID)"
        exit 1
    fi
fi

# Test 5: Cannot access leads (read)
echo ""
echo "Test 5: Receptionist attempts to read leads"
LEAD_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lead\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"]
            }
        },
        \"id\": 12
    }")

LEAD_READ_ERROR=$(echo "$LEAD_READ_RESPONSE" | jq -r '.error.data.message // empty')
LEADS_COUNT=$(echo "$LEAD_READ_RESPONSE" | jq -r '.result | length // 0')

if [ -n "$LEAD_READ_ERROR" ] || [ "$LEADS_COUNT" == "0" ]; then
    echo "✓ Receptionist cannot access leads"
else
    echo "❌ BUG: Receptionist should not see leads (sees $LEADS_COUNT leads)"
    exit 1
fi

# Test 6: Cannot access sales (read)
echo ""
echo "Test 6: Receptionist attempts to read sales"
SALE_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.sale\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\"]
            }
        },
        \"id\": 13
    }")

SALE_READ_ERROR=$(echo "$SALE_READ_RESPONSE" | jq -r '.error.data.message // empty')
SALES_COUNT=$(echo "$SALE_READ_RESPONSE" | jq -r '.result | length // 0')

if [ -n "$SALE_READ_ERROR" ] || [ "$SALES_COUNT" == "0" ]; then
    echo "✓ Receptionist cannot access sales"
else
    echo "❌ BUG: Receptionist should not see sales (sees $SALES_COUNT sales)"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US6-S2 Receptionist Restrictions"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - ✓ Receptionist cannot create properties"
echo "  - ✓ Receptionist cannot create agents"
echo "  - ✓ Receptionist cannot create leads"
echo "  - ✓ Receptionist cannot create sales"
echo "  - ✓ Receptionist cannot access/read leads"
echo "  - ✓ Receptionist cannot access/read sales"
echo "  - ACL restrictions working correctly"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
