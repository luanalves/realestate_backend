#!/bin/bash

################################################################################
# Test Script: US2-S4 Manager Company Isolation
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 2 - Owner Creates Team Members with Different Roles
# Scenario: 4 - Manager cannot see/modify other companies' data
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
echo "US2-S4: Manager Company Isolation"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_A_NAME="CompanyA_US2S4_${TIMESTAMP}"
COMPANY_B_NAME="CompanyB_US2S4_${TIMESTAMP}"
MANAGER_A_LOGIN="managera.us2s4.${TIMESTAMP}@companya.com"
MANAGER_B_LOGIN="managerb.us2s4.${TIMESTAMP}@companyb.com"

# Generate valid CNPJs
CNPJ_A=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "44555666"
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

base = "66777888"
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
echo "  Manager A: $MANAGER_A_LOGIN"
echo "  Manager B: $MANAGER_B_LOGIN"
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
                \"cnpj\": \"$CNPJ_A\",
                \"state\": \"active\"
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
                \"cnpj\": \"$CNPJ_B\",
                \"state\": \"active\"
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

COMPANY_B_ID=$(echo "$COMPANY_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Company B created: ID=$COMPANY_B_ID"

################################################################################
# Step 3: Create Manager Users
################################################################################
echo ""
echo "Step 3: Creating manager users..."

MANAGER_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager A US2S4\",
                \"login\": \"$MANAGER_A_LOGIN\",
                \"password\": \"manager123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_A_ID]]],
                \"groups_id\": [[6, 0, [17]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

MANAGER_A_UID=$(echo "$MANAGER_A_RESPONSE" | jq -r '.result // empty')
echo "✅ Manager A created: UID=$MANAGER_A_UID (assigned to Company A)"

MANAGER_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager B US2S4\",
                \"login\": \"$MANAGER_B_LOGIN\",
                \"password\": \"manager123\",
                \"estate_company_ids\": [[6, 0, [$COMPANY_B_ID]]],
                \"groups_id\": [[6, 0, [17]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

MANAGER_B_UID=$(echo "$MANAGER_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Manager B created: UID=$MANAGER_B_UID (assigned to Company B)"

################################################################################
# Step 4: Create Properties in Both Companies
################################################################################
echo ""
echo "Step 4: Creating properties for both companies..."

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
                \"name\": \"Property Company A US2S4\",
                \"property_type\": \"apartment\",
                \"bedrooms\": 2,
                \"bathrooms\": 1,
                \"parking_spaces\": 1,
                \"area\": 80.0,
                \"selling_price\": 300000.0,
                \"state\": \"available\",
                \"company_id\": $COMPANY_A_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

PROPERTY_A_ID=$(echo "$PROPERTY_A_RESPONSE" | jq -r '.result // empty')
echo "✅ Property A created: ID=$PROPERTY_A_ID (belongs to Company A)"

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
                \"name\": \"Property Company B US2S4\",
                \"property_type\": \"house\",
                \"bedrooms\": 3,
                \"bathrooms\": 2,
                \"parking_spaces\": 2,
                \"area\": 150.0,
                \"selling_price\": 500000.0,
                \"state\": \"available\",
                \"company_id\": $COMPANY_B_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

PROPERTY_B_ID=$(echo "$PROPERTY_B_RESPONSE" | jq -r '.result // empty')
echo "✅ Property B created: ID=$PROPERTY_B_ID (belongs to Company B)"

################################################################################
# Step 5: Manager A Login
################################################################################
echo ""
echo "Step 5: Manager A login..."

rm -f cookies.txt

MANAGER_A_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_A_LOGIN\",
            \"password\": \"manager123\"
        },
        \"id\": 8
    }")

MANAGER_A_SESSION_UID=$(echo "$MANAGER_A_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_A_SESSION_UID" ] || [ "$MANAGER_A_SESSION_UID" == "null" ]; then
    echo "❌ Manager A login failed"
    exit 1
fi

echo "✅ Manager A login successful (UID: $MANAGER_A_SESSION_UID)"

################################################################################
# Step 6: Manager A Tries to Access Company A Data (Should Succeed)
################################################################################
echo ""
echo "Step 6: Manager A accessing Company A data..."

COMPANY_A_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $COMPANY_A_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"cnpj\"]
            }
        },
        \"id\": 9
    }")

COMPANY_A_DATA=$(echo "$COMPANY_A_CHECK" | jq -r '.result | length')

if [ "$COMPANY_A_DATA" -eq "1" ]; then
    echo "✅ Manager A can see Company A (expected)"
else
    echo "❌ Manager A cannot see Company A"
    exit 1
fi

################################################################################
# Step 7: Manager A Tries to Access Company B Data (Should Fail)
################################################################################
echo ""
echo "Step 7: Manager A trying to access Company B data..."

COMPANY_B_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"=\", $COMPANY_B_ID]
            ]],
            \"kwargs\": {
                \"fields\": [\"name\", \"cnpj\"]
            }
        },
        \"id\": 10
    }")

COMPANY_B_DATA=$(echo "$COMPANY_B_CHECK" | jq -r '.result | length')

if [ "$COMPANY_B_DATA" -eq "0" ]; then
    echo "✅ Manager A cannot see Company B (isolation verified)"
else
    echo "❌ Manager A can see Company B (multi-tenancy violation!)"
    exit 1
fi

################################################################################
# Step 8: Manager A Checks All Visible Companies
################################################################################
echo ""
echo "Step 8: Manager A checking all visible companies..."

ALL_COMPANIES_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"]
            }
        },
        \"id\": 11
    }")

VISIBLE_COMPANIES=$(echo "$ALL_COMPANIES_CHECK" | jq -r '.result | length')
CONTAINS_A=$(echo "$ALL_COMPANIES_CHECK" | jq -r ".result[] | select(.id == $COMPANY_A_ID) | .id")
CONTAINS_B=$(echo "$ALL_COMPANIES_CHECK" | jq -r ".result[] | select(.id == $COMPANY_B_ID) | .id")

echo "Manager A sees $VISIBLE_COMPANIES company(ies)"

if [ ! -z "$CONTAINS_A" ] && [ -z "$CONTAINS_B" ]; then
    echo "✅ Manager A sees only Company A"
else
    echo "❌ Manager A visibility check failed"
    exit 1
fi

################################################################################
# Step 9: Manager A Checks Properties
################################################################################
echo ""
echo "Step 9: Manager A checking properties..."

PROPERTIES_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[
                [\"id\", \"in\", [$PROPERTY_A_ID, $PROPERTY_B_ID]]
            ]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"company_id\"]
            }
        },
        \"id\": 12
    }")

PROPS_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r '.result | length')
PROP_A_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY_A_ID) | .id")
PROP_B_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY_B_ID) | .id")

if [ ! -z "$PROP_A_FOUND" ] && [ -z "$PROP_B_FOUND" ]; then
    echo "✅ Manager A sees only Property A (isolation verified)"
else
    echo "❌ Manager A property isolation failed (found $PROPS_FOUND properties)"
    exit 1
fi

################################################################################
# Step 10: Manager B Login and Verification
################################################################################
echo ""
echo "Step 10: Manager B login and verification..."

rm -f cookies.txt

MANAGER_B_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_B_LOGIN\",
            \"password\": \"manager123\"
        },
        \"id\": 13
    }")

MANAGER_B_SESSION_UID=$(echo "$MANAGER_B_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✅ Manager B login successful (UID: $MANAGER_B_SESSION_UID)"

# Manager B checks companies
MANAGER_B_COMPANIES=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"]
            }
        },
        \"id\": 14
    }")

MB_CONTAINS_A=$(echo "$MANAGER_B_COMPANIES" | jq -r ".result[] | select(.id == $COMPANY_A_ID) | .id")
MB_CONTAINS_B=$(echo "$MANAGER_B_COMPANIES" | jq -r ".result[] | select(.id == $COMPANY_B_ID) | .id")

if [ -z "$MB_CONTAINS_A" ] && [ ! -z "$MB_CONTAINS_B" ]; then
    echo "✅ Manager B sees only Company B (isolation verified)"
else
    echo "❌ Manager B company isolation failed"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "====================================="
echo "✅ TEST PASSED: US2-S4 Manager Company Isolation"
echo "====================================="
echo ""
echo "Summary:"
echo "  - Manager A sees only Company A data"
echo "  - Manager A cannot see Company B data"
echo "  - Manager B sees only Company B data"
echo "  - Manager B cannot see Company A data"
echo "  - Multi-tenancy isolation working correctly for Managers"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
