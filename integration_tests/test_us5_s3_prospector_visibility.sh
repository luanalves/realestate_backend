#!/bin/bash

################################################################################
# Test Script: US5-S3 Prospector Visibility
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 5 - Prospector Creates Properties with Commission Split
# Scenario: 4 - Prospector sees only properties they prospected
#
# STATUS: ⚠️ EXPECTED TO FAIL - Record rule bug
# The record rule exists in security/record_rules.xml but isn't being enforced.
# Prospectors currently see ALL properties instead of only own prospected properties.
# Bug: [('prospector_id.user_id', '=', user.id)] rule not filtering correctly.
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
echo "US5-S3: Prospector Visibility (Own Properties Only)"
echo "========================================"

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US5S3_${TIMESTAMP}"
PROSPECTOR1_LOGIN="prospector1.us5s3.${TIMESTAMP}@company.com"
PROSPECTOR2_LOGIN="prospector2.us5s3.${TIMESTAMP}@company.com"

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
echo "  Company: $COMPANY_NAME (CNPJ: $CNPJ)"
echo "  Prospector 1: $PROSPECTOR1_LOGIN"
echo "  Prospector 2: $PROSPECTOR2_LOGIN"
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
# Step 2: Create Two Prospectors
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create two prospector users"
echo "=========================================="

PROSPECTOR_GROUP_ID=24

# Create Prospector 1
PROSPECTOR1_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector 1 US5S3\",
                \"login\": \"$PROSPECTOR1_LOGIN\",
                \"password\": \"prospector123\",
                \"groups_id\": [[6, 0, [$PROSPECTOR_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 3
    }")

PROSPECTOR1_UID=$(echo "$PROSPECTOR1_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector 1 user created: UID=$PROSPECTOR1_UID"

# Create prospector 1 agent record
CPF_PROSPECTOR1=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "33344455"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

PROSPECTOR1_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector 1 US5S3\",
                \"user_id\": $PROSPECTOR1_UID,
                \"cpf\": \"$CPF_PROSPECTOR1\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

PROSPECTOR1_AGENT_ID=$(echo "$PROSPECTOR1_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector 1 agent record created: ID=$PROSPECTOR1_AGENT_ID"

# Create Prospector 2
PROSPECTOR2_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector 2 US5S3\",
                \"login\": \"$PROSPECTOR2_LOGIN\",
                \"password\": \"prospector123\",
                \"groups_id\": [[6, 0, [$PROSPECTOR_GROUP_ID]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

PROSPECTOR2_UID=$(echo "$PROSPECTOR2_USER_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector 2 user created: UID=$PROSPECTOR2_UID"

# Create prospector 2 agent record
CPF_PROSPECTOR2=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "66677788"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

PROSPECTOR2_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Prospector 2 US5S3\",
                \"user_id\": $PROSPECTOR2_UID,
                \"cpf\": \"$CPF_PROSPECTOR2\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

PROSPECTOR2_AGENT_ID=$(echo "$PROSPECTOR2_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector 2 agent record created: ID=$PROSPECTOR2_AGENT_ID"

################################################################################
# Step 3: Get Reference Data
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Retrieving reference data"
echo "=========================================="

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
        \"id\": 7
    }")

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

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
        \"id\": 8
    }")

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

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
        \"id\": 9
    }")

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id // empty')
echo "✓ State ID: $STATE_ID"

################################################################################
# Step 4: Create Properties for Each Prospector
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Create properties for each prospector"
echo "=========================================="

# 3 properties for Prospector 1
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
                    \"name\": \"Property P1-$i US5S3\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"01310-100\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua P1\",
                    \"street_number\": \"${i}00\",
                    \"area\": 100.0,
                    \"price\": 400000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                    \"prospector_id\": $PROSPECTOR1_AGENT_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((9 + $i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    echo "✓ Property P1-$i created: ID=$PROP_ID (prospector_id=$PROSPECTOR1_AGENT_ID)"
done

# 2 properties for Prospector 2
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
                    \"name\": \"Property P2-$i US5S3\",
                    \"property_type_id\": $PROPERTY_TYPE_ID,
                    \"location_type_id\": $LOCATION_TYPE_ID,
                    \"state_id\": $STATE_ID,
                    \"zip_code\": \"01310-200\",
                    \"city\": \"São Paulo\",
                    \"street\": \"Rua P2\",
                    \"street_number\": \"${i}00\",
                    \"area\": 90.0,
                    \"price\": 350000.0,
                    \"property_status\": \"available\",
                    \"company_ids\": [[6, 0, [$COMPANY_ID]]],
                    \"prospector_id\": $PROSPECTOR2_AGENT_ID
                }],
                \"kwargs\": {}
            },
            \"id\": $((12 + $i))
        }")
    
    PROP_ID=$(echo "$PROP_RESPONSE" | jq -r '.result // empty')
    echo "✓ Property P2-$i created: ID=$PROP_ID (prospector_id=$PROSPECTOR2_AGENT_ID)"
done

################################################################################
# Step 5: Prospector 1 Views Properties
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Prospector 1 views properties"
echo "=========================================="

rm -f cookies.txt

PROSPECTOR1_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$PROSPECTOR1_LOGIN\",
            \"password\": \"prospector123\"
        },
        \"id\": 15
    }")

PROSPECTOR1_SESSION_UID=$(echo "$PROSPECTOR1_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Prospector 1 logged in: UID=$PROSPECTOR1_SESSION_UID"

PROSPECTOR1_PROPS_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
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
        \"id\": 16
    }")

PROSPECTOR1_PROPS_COUNT=$(echo "$PROSPECTOR1_PROPS_RESPONSE" | jq -r '.result | length')

echo "Prospector 1 sees $PROSPECTOR1_PROPS_COUNT property(ies):"
echo "$PROSPECTOR1_PROPS_RESPONSE" | jq -r '.result[] | "  - \(.name) (prospector_id: \(.prospector_id))"'

# Record rule should block visibility entirely - prospector should only see own properties
if [ "$PROSPECTOR1_PROPS_COUNT" == "3" ]; then
    echo "✓ Prospector 1 sees only own 3 properties (record rule working)"
else
    echo "❌ Record rule not working - Prospector 1 sees $PROSPECTOR1_PROPS_COUNT properties (expected 3)"
    echo "⚠️  The record rule [('prospector_id.user_id', '=', user.id)] should block visibility to other prospectors' properties"
    exit 1
fi

################################################################################
# Step 6: Prospector 2 Views Properties
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Prospector 2 views properties"
echo "=========================================="

rm -f cookies.txt

PROSPECTOR2_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$PROSPECTOR2_LOGIN\",
            \"password\": \"prospector123\"
        },
        \"id\": 17
    }")

PROSPECTOR2_SESSION_UID=$(echo "$PROSPECTOR2_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Prospector 2 logged in: UID=$PROSPECTOR2_SESSION_UID"

PROSPECTOR2_PROPS_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
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
        \"id\": 18
    }")

PROSPECTOR2_PROPS_COUNT=$(echo "$PROSPECTOR2_PROPS_RESPONSE" | jq -r '.result | length')

echo "Prospector 2 sees $PROSPECTOR2_PROPS_COUNT property(ies):"
echo "$PROSPECTOR2_PROPS_RESPONSE" | jq -r '.result[] | "  - \(.name) (prospector_id: \(.prospector_id))"'

# Record rule should block visibility entirely - prospector should only see own properties
if [ "$PROSPECTOR2_PROPS_COUNT" == "2" ]; then
    echo "✓ Prospector 2 sees only own 2 properties (record rule working)"
else
    echo "❌ Record rule not working - Prospector 2 sees $PROSPECTOR2_PROPS_COUNT properties (expected 2)"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US5-S3 Prospector Visibility"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Prospector 1 created 3 properties"
echo "  - Prospector 2 created 2 properties"  
echo "  - Prospector 1 sees only own 3 properties (not P2's)"
echo "  - Prospector 2 sees only own 2 properties (not P1's)"
echo "  - Record rule working: prospector_id.user_id = user.id"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
