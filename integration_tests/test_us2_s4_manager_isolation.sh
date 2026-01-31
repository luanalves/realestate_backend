#!/bin/bash

################################################################################
# Test Script: US2-S4 Manager Company Isolation
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 2 - Owner Creates Team Members with Different Roles
# Scenario: 4 - Manager cannot see/modify other companies' data
################################################################################

set -e

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-${POSTGRES_DB:-realestate}}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

# Use unique temp file paths to avoid conflicts
COOKIE_FILE="/tmp/odoo_us2s4_cookies_$$.txt"
ADMIN_COOKIE_FILE="/tmp/odoo_us2s4_admin_$$.txt"

# Cleanup on exit
cleanup() {
    rm -f "$COOKIE_FILE" "$ADMIN_COOKIE_FILE" response.json
}
trap cleanup EXIT

echo "====================================="
echo "US2-S4: Manager Company Isolation"
echo "====================================="

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
    -c "$ADMIN_COOKIE_FILE" \
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

if [ -z "$ADMIN_UID" ] || [ "$ADMIN_UID" == "null" ] || [ "$ADMIN_UID" == "false" ]; then
    echo "❌ Admin login failed"
    echo "Response: $LOGIN_RESPONSE"
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
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$COMPANY_A_ID" ] || [ "$COMPANY_A_ID" == "null" ]; then
    echo "❌ Company A creation failed"
    echo "Response: $COMPANY_A_RESPONSE"
    exit 1
fi

echo "✅ Company A created: ID=$COMPANY_A_ID"

COMPANY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$COMPANY_B_ID" ] || [ "$COMPANY_B_ID" == "null" ]; then
    echo "❌ Company B creation failed"
    echo "Response: $COMPANY_B_RESPONSE"
    exit 1
fi

echo "✅ Company B created: ID=$COMPANY_B_ID"

################################################################################
# Step 3: Create Manager Users
################################################################################
echo ""
echo "Step 3: Creating manager users..."

MANAGER_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$MANAGER_A_UID" ] || [ "$MANAGER_A_UID" == "null" ]; then
    echo "❌ Manager A creation failed"
    echo "Response: $MANAGER_A_RESPONSE"
    exit 1
fi

echo "✅ Manager A created: UID=$MANAGER_A_UID (assigned to Company A)"

MANAGER_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$MANAGER_B_UID" ] || [ "$MANAGER_B_UID" == "null" ]; then
    echo "❌ Manager B creation failed"
    echo "Response: $MANAGER_B_RESPONSE"
    exit 1
fi

echo "✅ Manager B created: UID=$MANAGER_B_UID (assigned to Company B)"

# Create agent records with CPF for both managers
CPF_MANAGER_A=$(python3 << 'PYTHON_EOF'
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

MANAGER_A_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager A US2S4\",
                \"user_id\": $MANAGER_A_UID,
                \"cpf\": \"$CPF_MANAGER_A\",
                \"company_ids\": [[6, 0, [$COMPANY_A_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

MANAGER_A_AGENT_ID=$(echo "$MANAGER_A_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$MANAGER_A_AGENT_ID" ] || [ "$MANAGER_A_AGENT_ID" == "null" ]; then
    echo "⚠️  Manager A agent record creation failed (optional)"
    MANAGER_A_AGENT_ID=""
else
    echo "✅ Manager A agent record created: ID=$MANAGER_A_AGENT_ID"
fi

CPF_MANAGER_B=$(python3 << 'PYTHON_EOF'
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

MANAGER_B_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager B US2S4\",
                \"user_id\": $MANAGER_B_UID,
                \"cpf\": \"$CPF_MANAGER_B\",
                \"company_ids\": [[6, 0, [$COMPANY_B_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

MANAGER_B_AGENT_ID=$(echo "$MANAGER_B_AGENT_RESPONSE" | jq -r '.result // empty')

if [ -z "$MANAGER_B_AGENT_ID" ] || [ "$MANAGER_B_AGENT_ID" == "null" ]; then
    echo "⚠️  Manager B agent record creation failed (optional)"
    MANAGER_B_AGENT_ID=""
else
    echo "✅ Manager B agent record created: ID=$MANAGER_B_AGENT_ID"
fi

################################################################################
# Step 3.5: Retrieve Reference Data for Properties
################################################################################
echo ""
echo "=========================================="
echo "Step 3.5: Retrieve Reference Data for Properties"
echo "=========================================="

# Get first property type
PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$PROPERTY_TYPE_ID" ] || [ "$PROPERTY_TYPE_ID" == "null" ]; then
    echo "❌ Property type not found - need to seed reference data"
    exit 1
fi
echo "✅ Property Type ID: $PROPERTY_TYPE_ID"

# Get location type
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$LOCATION_TYPE_ID" ] || [ "$LOCATION_TYPE_ID" == "null" ]; then
    echo "❌ Location type not found - need to seed reference data"
    exit 1
fi
echo "✅ Location Type ID: $LOCATION_TYPE_ID"

# Get state (São Paulo)
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
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

if [ -z "$STATE_ID" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ State not found - need to seed reference data"
    exit 1
fi
echo "✅ State ID: $STATE_ID"

################################################################################
# Step 4: Create Properties in Both Companies
################################################################################
echo ""
echo "Step 4: Creating properties for both companies..."

PROPERTY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property Company A US2S4\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"12345-678\",
                \"city\": \"São Paulo\",
                \"street\": \"Rua Teste\",
                \"street_number\": \"100\",
                \"num_rooms\": 2,
                \"num_bathrooms\": 1,
                \"num_parking\": 1,
                \"area\": 80.0,
                \"price\": 300000.0,
                \"property_status\": \"available\",
                \"company_ids\": [[6, 0, [$COMPANY_A_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 8
    }")

PROPERTY_A_ID=$(echo "$PROPERTY_A_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY_A_ID" ] || [ "$PROPERTY_A_ID" == "null" ]; then
    echo "❌ Property A creation failed"
    echo "Response: $PROPERTY_A_RESPONSE"
    exit 1
fi

echo "✅ Property A created: ID=$PROPERTY_A_ID (belongs to Company A)"

PROPERTY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Property Company B US2S4\",
                \"property_type_id\": $PROPERTY_TYPE_ID,
                \"location_type_id\": $LOCATION_TYPE_ID,
                \"state_id\": $STATE_ID,
                \"zip_code\": \"12345-678\",
                \"city\": \"São Paulo\",
                \"street\": \"Rua Teste\",
                \"street_number\": \"200\",
                \"num_rooms\": 3,
                \"num_bathrooms\": 2,
                \"num_parking\": 2,
                \"area\": 150.0,
                \"price\": 500000.0,
                \"property_status\": \"available\",
                \"company_ids\": [[6, 0, [$COMPANY_B_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

PROPERTY_B_ID=$(echo "$PROPERTY_B_RESPONSE" | jq -r '.result // empty')

if [ -z "$PROPERTY_B_ID" ] || [ "$PROPERTY_B_ID" == "null" ]; then
    echo "❌ Property B creation failed"
    echo "Response: $PROPERTY_B_RESPONSE"
    exit 1
fi

echo "✅ Property B created: ID=$PROPERTY_B_ID (belongs to Company B)"

################################################################################
# Step 5: Manager A Login
################################################################################
echo ""
echo "Step 5: Manager A login..."

MANAGER_A_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_A_LOGIN\",
            \"password\": \"manager123\"
        },
        \"id\": 10
    }")

MANAGER_A_SESSION_UID=$(echo "$MANAGER_A_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_A_SESSION_UID" ] || [ "$MANAGER_A_SESSION_UID" == "null" ] || [ "$MANAGER_A_SESSION_UID" == "false" ]; then
    echo "❌ Manager A login failed"
    echo "Response: $MANAGER_A_LOGIN_RESPONSE"
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
    -b "$COOKIE_FILE" \
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
        \"id\": 11
    }")

COMPANY_A_DATA=$(echo "$COMPANY_A_CHECK" | jq -r '.result | length')

if [ "$COMPANY_A_DATA" -eq "1" ]; then
    echo "✅ Manager A can see Company A (expected)"
else
    echo "❌ Manager A cannot see Company A"
    echo "Response: $COMPANY_A_CHECK"
    exit 1
fi

################################################################################
# Step 7: Manager A Tries to Access Company B Data (Should Fail)
################################################################################
echo ""
echo "Step 7: Manager A trying to access Company B data..."

COMPANY_B_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE" \
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
        \"id\": 12
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
    -b "$COOKIE_FILE" \
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
        \"id\": 13
    }")

VISIBLE_COMPANIES=$(echo "$ALL_COMPANIES_CHECK" | jq -r '.result | length')
CONTAINS_A=$(echo "$ALL_COMPANIES_CHECK" | jq -r ".result[] | select(.id == $COMPANY_A_ID) | .id")
CONTAINS_B=$(echo "$ALL_COMPANIES_CHECK" | jq -r ".result[] | select(.id == $COMPANY_B_ID) | .id")

echo "Manager A sees $VISIBLE_COMPANIES company(ies)"

if [ ! -z "$CONTAINS_A" ] && [ -z "$CONTAINS_B" ]; then
    echo "✅ Manager A sees only Company A"
else
    echo "❌ Manager A visibility check failed"
    echo "Contains A: '$CONTAINS_A', Contains B: '$CONTAINS_B'"
    exit 1
fi

################################################################################
# Step 9: Manager A Checks Properties
################################################################################
echo ""
echo "Step 9: Manager A checking properties..."

PROPERTIES_CHECK=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE" \
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
                \"fields\": [\"id\", \"name\", \"company_ids\"]
            }
        },
        \"id\": 14
    }")

PROPS_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r '.result | length')
PROP_A_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY_A_ID) | .id")
PROP_B_FOUND=$(echo "$PROPERTIES_CHECK" | jq -r ".result[] | select(.id == $PROPERTY_B_ID) | .id")

if [ ! -z "$PROP_A_FOUND" ] && [ -z "$PROP_B_FOUND" ]; then
    echo "✅ Manager A sees only Property A (isolation verified)"
else
    echo "❌ Manager A property isolation failed"
    echo "  Found $PROPS_FOUND properties"
    echo "  Prop A found: '$PROP_A_FOUND'"
    echo "  Prop B found: '$PROP_B_FOUND'"
    exit 1
fi

################################################################################
# Step 10: Manager B Login and Verification
################################################################################
echo ""
echo "Step 10: Manager B login and verification..."

MANAGER_B_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$DB_NAME\",
            \"login\": \"$MANAGER_B_LOGIN\",
            \"password\": \"manager123\"
        },
        \"id\": 15
    }")

MANAGER_B_SESSION_UID=$(echo "$MANAGER_B_LOGIN_RESPONSE" | jq -r '.result.uid // empty')

if [ -z "$MANAGER_B_SESSION_UID" ] || [ "$MANAGER_B_SESSION_UID" == "null" ] || [ "$MANAGER_B_SESSION_UID" == "false" ]; then
    echo "❌ Manager B login failed"
    exit 1
fi

echo "✅ Manager B login successful (UID: $MANAGER_B_SESSION_UID)"

# Manager B checks companies
MANAGER_B_COMPANIES=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE" \
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
        \"id\": 16
    }")

MB_CONTAINS_A=$(echo "$MANAGER_B_COMPANIES" | jq -r ".result[] | select(.id == $COMPANY_A_ID) | .id")
MB_CONTAINS_B=$(echo "$MANAGER_B_COMPANIES" | jq -r ".result[] | select(.id == $COMPANY_B_ID) | .id")

if [ -z "$MB_CONTAINS_A" ] && [ ! -z "$MB_CONTAINS_B" ]; then
    echo "✅ Manager B sees only Company B (isolation verified)"
else
    echo "❌ Manager B company isolation failed"
    echo "  MB Contains A: '$MB_CONTAINS_A'"
    echo "  MB Contains B: '$MB_CONTAINS_B'"
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

exit 0
