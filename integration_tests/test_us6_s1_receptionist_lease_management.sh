#!/bin/bash

################################################################################
# Test Script: US6-S1 Receptionist Lease Management
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 6 - Receptionist Front Desk Operations
# Scenario: 1 - Receptionist can manage leases and tenants
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
echo "US6-S1: Receptionist Lease Management"
echo "========================================"

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US6S1_${TIMESTAMP}"
RECEPTIONIST_LOGIN="receptionist.us6s1.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "77889900"
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
                \"name\": \"Receptionist US6S1\",
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

# Get reference data (as admin)
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
echo "✓ Reference data retrieved: PropertyType=$PROPERTY_TYPE_ID, LocationType=$LOCATION_TYPE_ID, State=$STATE_ID"

# Create a property for leasing (as admin)
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
                \"name\": \"Property for Lease US6S1\",
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
        \"id\": 7
    }")

PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.result // empty')
echo "✓ Property created for leasing: ID=$PROPERTY_ID"

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
        \"id\": 8
    }")

RECEPTIONIST_SESSION_UID=$(echo "$RECEPTIONIST_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Receptionist logged in: UID=$RECEPTIONIST_SESSION_UID"

################################################################################
# Step 3: Receptionist Creates Tenant
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Receptionist creates tenant"
echo "=========================================="

TENANT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.tenant\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Tenant US6S1\",
                \"email\": \"tenant.us6s1.${TIMESTAMP}@example.com\",
                \"phone\": \"11987654321\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.result // empty')
TENANT_ERROR=$(echo "$TENANT_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$TENANT_ERROR" ]; then
    echo "❌ Receptionist cannot create tenant: $TENANT_ERROR"
    exit 1
elif [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ]; then
    echo "✓ Tenant created: ID=$TENANT_ID"
else
    echo "❌ Failed to create tenant"
    exit 1
fi

################################################################################
# Step 4: Receptionist Creates Lease
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Receptionist creates lease"
echo "=========================================="

LEASE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lease\",
            \"method\": \"create\",
            \"args\": [{
                \"property_id\": $PROPERTY_ID,
                \"tenant_id\": $TENANT_ID,
                \"rent_amount\": 3000.0,
                \"start_date\": \"2026-02-01\",
                \"end_date\": \"2027-02-01\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 10
    }")

LEASE_ID=$(echo "$LEASE_RESPONSE" | jq -r '.result // empty')
LEASE_ERROR=$(echo "$LEASE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$LEASE_ERROR" ]; then
    echo "❌ Receptionist cannot create lease: $LEASE_ERROR"
    exit 1
elif [ -n "$LEASE_ID" ] && [ "$LEASE_ID" != "null" ]; then
    echo "✓ Lease created: ID=$LEASE_ID"
else
    echo "❌ Failed to create lease"
    exit 1
fi

################################################################################
# Step 5: Receptionist Reads Leases
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Receptionist reads leases"
echo "=========================================="

LEASES_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lease\",
            \"method\": \"search_read\",
            \"args\": [[[\"id\", \"=\", $LEASE_ID]]],
            \"kwargs\": {
                \"fields\": [\"property_id\", \"tenant_id\", \"rent_amount\"]
            }
        },
        \"id\": 11
    }")

LEASES_COUNT=$(echo "$LEASES_READ_RESPONSE" | jq -r '.result | length')

if [ "$LEASES_COUNT" -ge "1" ]; then
    echo "✓ Receptionist can read leases (found $LEASES_COUNT lease(s))"
else
    echo "❌ Receptionist cannot read leases"
    exit 1
fi

################################################################################
# Step 6: Receptionist Updates Lease
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Receptionist updates lease"
echo "=========================================="

LEASE_UPDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lease\",
            \"method\": \"write\",
            \"args\": [[$LEASE_ID], {
                \"rent_amount\": 3500.0
            }],
            \"kwargs\": {}
        },
        \"id\": 12
    }")

LEASE_UPDATE_SUCCESS=$(echo "$LEASE_UPDATE_RESPONSE" | jq -r '.result // empty')
LEASE_UPDATE_ERROR=$(echo "$LEASE_UPDATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$LEASE_UPDATE_ERROR" ]; then
    echo "❌ Receptionist cannot update lease: $LEASE_UPDATE_ERROR"
    exit 1
elif [ "$LEASE_UPDATE_SUCCESS" == "true" ]; then
    echo "✓ Lease updated successfully"
else
    echo "❌ Failed to update lease"
    exit 1
fi

################################################################################
# Step 7: Receptionist Can Read Properties (Read-Only)
################################################################################
echo ""
echo "=========================================="
echo "Step 7: Receptionist reads properties"
echo "=========================================="

PROPERTIES_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[[\"id\", \"=\", $PROPERTY_ID]]],
            \"kwargs\": {
                \"fields\": [\"name\", \"property_status\"]
            }
        },
        \"id\": 13
    }")

PROPERTIES_COUNT=$(echo "$PROPERTIES_READ_RESPONSE" | jq -r '.result | length')

if [ "$PROPERTIES_COUNT" -ge "1" ]; then
    echo "✓ Receptionist can read properties (found $PROPERTIES_COUNT property/ies)"
else
    echo "❌ Receptionist cannot read properties"
    exit 1
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US6-S1 Receptionist Lease Management"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - ✓ Receptionist can create tenants"
echo "  - ✓ Receptionist can create leases"
echo "  - ✓ Receptionist can read leases"
echo "  - ✓ Receptionist can update leases"
echo "  - ✓ Receptionist can read properties (read-only)"
echo "  - Front desk operations working correctly"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
