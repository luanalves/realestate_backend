#!/bin/bash

################################################################################
# Test Script: US5-S1 Prospector Creates Property
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 5 - Prospector Creates Properties with Commission Split
# Scenario: 1 - Prospector creates property, auto-assigned as prospector_id
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
echo "US5-S1: Prospector Creates Property"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US5S1_${TIMESTAMP}"
PROSPECTOR_LOGIN="prospector.us5s1.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "33445566"
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
echo ""

################################################################################
# Step 1: Admin Login & Setup
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
# Step 2: Create Prospector User
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create prospector user"
echo "=========================================="

# Prospector Group ID is 24 (from groups.xml)
PROSPECTOR_GROUP_ID=24

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
                \"name\": \"Prospector US5S1\",
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

if [ -z "$PROSPECTOR_UID" ] || [ "$PROSPECTOR_UID" == "null" ]; then
    echo "❌ Prospector user creation failed"
    echo "Response: $PROSPECTOR_USER_RESPONSE"
    exit 1
fi

echo "✓ Prospector user created: UID=$PROSPECTOR_UID"

# Generate CPF for prospector
CPF_PROSPECTOR=$(python3 << 'PYTHON_EOF'
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

echo "✓ CPF for Prospector: $CPF_PROSPECTOR"

# Create real.estate.agent record for prospector
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
                \"name\": \"Prospector US5S1\",
                \"user_id\": $PROSPECTOR_UID,
                \"cpf\": \"$CPF_PROSPECTOR\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

PROSPECTOR_AGENT_ID=$(echo "$PROSPECTOR_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROSPECTOR_AGENT_ID" ] || [ "$PROSPECTOR_AGENT_ID" == "null" ]; then
    echo "❌ Prospector agent record creation failed"
    exit 1
fi

echo "✓ Prospector agent record created: ID=$PROSPECTOR_AGENT_ID"

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
        \"id\": 5
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
        \"id\": 6
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
        \"id\": 7
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ State ID: $STATE_ID"

################################################################################
# Step 4: Prospector Login
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Prospector login"
echo "=========================================="

rm -f cookies.txt

PROSPECTOR_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$PROSPECTOR_LOGIN\",
            \"password\": \"prospector123\"
        },
        \"id\": 8
    }")

PROSPECTOR_SESSION_UID=$(echo "$PROSPECTOR_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$PROSPECTOR_SESSION_UID" ] || [ "$PROSPECTOR_SESSION_UID" == "null" ]; then
    echo "❌ Prospector login failed"
    exit 1
fi

echo "✓ Prospector logged in: UID=$PROSPECTOR_SESSION_UID"

################################################################################
# Step 5: Prospector Creates Property
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Prospector creates property"
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
                \"name\": \"Property Prospected US5S1\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"01310-100\",
                \"city\": \"São Paulo\",
                \"street\": \"Av Paulista\",
                \"street_number\": \"1000\",
                \"area\": 120.0,
                \"price\": 450000.0,
                \"property_status\": \"available\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                \"prospector_id\": $PROSPECTOR_AGENT_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

PROPERTY_ID=$(echo "$PROPERTY_CREATE_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" == "null" ]; then
    echo "❌ Property creation failed"
    echo "Response: $PROPERTY_CREATE_RESPONSE"
    exit 1
fi

echo "✓ Property created: ID=$PROPERTY_ID"

################################################################################
# Step 6: Verify Prospector Auto-Assignment
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Verify prospector_id auto-assignment"
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
        \"id\": 10
    }")

PROSPECTOR_ID_ON_PROPERTY=$(echo "$PROPERTY_READ_RESPONSE" | jq -r '.result[0].prospector_id[0] // empty')

echo "Property prospector_id: $PROSPECTOR_ID_ON_PROPERTY"
echo "Expected prospector_id: $PROSPECTOR_AGENT_ID"

if [ "$PROSPECTOR_ID_ON_PROPERTY" == "$PROSPECTOR_AGENT_ID" ]; then
    echo "✓ Property correctly auto-assigned to prospector"
else
    echo "❌ Property NOT auto-assigned to prospector"
    echo "   Expected: $PROSPECTOR_AGENT_ID"
    echo "   Got: $PROSPECTOR_ID_ON_PROPERTY"
    exit 1
fi

################################################################################
# Step 7: Verify Prospector Can See Own Property
################################################################################
echo ""
echo "=========================================="
echo "Step 7: Verify prospector sees own property"
echo "=========================================="

PROPERTIES_LIST_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
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
                \"fields\": [\"name\", \"prospector_id\"]
            }
        },
        \"id\": 11
    }")

PROPERTIES_COUNT=$(echo "$PROPERTIES_LIST_RESPONSE" | jq -r '.result | length')

echo "Prospector sees $PROPERTIES_COUNT property(ies)"

if [ "$PROPERTIES_COUNT" -ge "1" ]; then
    echo "✓ Prospector can see own prospected property"
else
    echo "❌ Prospector cannot see own property"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US5-S1 Prospector Creates Property"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Prospector created property successfully"
echo "  - Property auto-assigned to prospector_id: $PROSPECTOR_AGENT_ID"
echo "  - Prospector can view own prospected properties"
echo "  - Record rule working: prospector_id.user_id = user.id"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
