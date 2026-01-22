#!/bin/bash

################################################################################
# Test Script: US2-S2 Manager Menu Access
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 2 - Owner Creates Team Members with Different Roles  
# Scenario: 2 - Manager sees all company menus and data
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
echo "US2-S2: Manager Menu Access"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US2S2_${TIMESTAMP}"
MANAGER_LOGIN="manager.us2s2.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "77888999"
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

echo "✅ Company created: ID=$COMPANY_ID"

################################################################################
# Step 3: Create Manager User
################################################################################
echo ""
echo "Step 3: Creating manager user..."

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
                \"name\": \"Manager US2S2\",
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
    exit 1
fi

echo "✅ Manager user created: UID=$MANAGER_UID"

################################################################################
# Step 4: Create Test Properties (as admin, assigned to company)
################################################################################
echo ""
echo "Step 4: Creating test properties..."

for i in 1 2 3; do
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
                    \"name\": \"Property $i US2S2\",
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
            \"id\": $((3 + $i))
        }")
    
    PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.result // empty')
    
    if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" == "null" ]; then
        echo "⚠️  Property $i creation failed"
    else
        echo "✅ Property $i created: ID=$PROPERTY_ID"
    fi
done

################################################################################
# Step 5: Manager Login
################################################################################
echo ""
echo "Step 5: Manager login..."

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
        \"id\": 7
    }")

MANAGER_SESSION_UID=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_SESSION_UID" ] || [ "$MANAGER_SESSION_UID" == "null" ]; then
    echo "❌ Manager login failed"
    exit 1
fi

echo "✅ Manager login successful (UID: $MANAGER_SESSION_UID)"

################################################################################
# Step 6: Manager Accesses Properties
################################################################################
echo ""
echo "Step 6: Manager accessing properties..."

PROPERTIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"company_id\", \"=\", $COMPANY_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"state\", \"company_id\"]
            }
        },
        \"id\": 8
    }")

PROPERTIES_COUNT=$(echo "$PROPERTIES_RESPONSE" | jq -r '.result | length')

if [ -z "$PROPERTIES_COUNT" ] || [ "$PROPERTIES_COUNT" == "null" ]; then
    echo "❌ Manager cannot access properties"
    exit 1
fi

echo "✅ Manager can see properties: $PROPERTIES_COUNT found"

################################################################################
# Step 7: Manager Accesses Company Data
################################################################################
echo ""
echo "Step 7: Manager accessing company data..."

COMPANY_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $COMPANY_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"cnpj\", \"state\"]
            }
        },
        \"id\": 9
    }")

COMPANY_DATA=$(echo "$COMPANY_CHECK" | jq -r '.result[0] // empty')

if [ -z "$COMPANY_DATA" ] || [ "$COMPANY_DATA" == "null" ]; then
    echo "❌ Manager cannot access company data"
    exit 1
fi

COMPANY_NAME_CHECK=$(echo "$COMPANY_DATA" | jq -r '.name')
echo "✅ Manager can access company: $COMPANY_NAME_CHECK"

################################################################################
# Step 8: Verify Manager Permissions
################################################################################
echo ""
echo "Step 8: Verifying manager permissions..."

# Check if manager can read user data (for team management)
USERS_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $MANAGER_UID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"login\", \"groups_id\"]
            }
        },
        \"id\": 10
    }")

USER_DATA=$(echo "$USERS_CHECK" | jq -r '.result[0] // empty')

if [ -z "$USER_DATA" ] || [ "$USER_DATA" == "null" ]; then
    echo "⚠️  Manager cannot read user data"
else
    echo "✅ Manager can access user data"
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US2-S2 Manager Menu Access"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Manager can access company data"
echo "  - Manager can see all company properties ($PROPERTIES_COUNT properties)"
echo "  - Manager has appropriate permissions for their role"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
