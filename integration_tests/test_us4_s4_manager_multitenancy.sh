#!/bin/bash

################################################################################
# Test Script: US4-S4 Manager Multi-Tenancy Isolation
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 4 - Manager Oversees All Company Operations
# Scenario: 4 - Manager A cannot see Company B data (multi-tenancy)
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
echo "US4-S4: Manager Multi-Tenancy Isolation"
echo "====================================="

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_A_NAME="CompanyA_US4S4_${TIMESTAMP}"
COMPANY_B_NAME="CompanyB_US4S4_${TIMESTAMP}"
MANAGER_A_LOGIN="managera.us4s4.${TIMESTAMP}@companya.com"
MANAGER_B_LOGIN="managerb.us4s4.${TIMESTAMP}@companyb.com"

# Generate valid CNPJs
CNPJ_A=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "11111111"
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

base = "99999999"
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
# Step 1: Admin Login
################################################################################
echo "=========================================="
echo "Step 1: Admin login"
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

ADMIN_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')

################################################################################
# Step 2: Create Company A
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Create Company A"
echo "=========================================="

COMPANY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
        \"id\": 1
    }")

COMPANY_A_ID=$(echo "$COMPANY_A_RESPONSE" | jq -r '.result')
echo "✓ Company A created: ID=$COMPANY_A_ID"

################################################################################
# Step 3: Create Company B
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Create Company B"
echo "=========================================="

COMPANY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
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
        \"id\": 1
    }")

COMPANY_B_ID=$(echo "$COMPANY_B_RESPONSE" | jq -r '.result')
echo "✓ Company B created: ID=$COMPANY_B_ID"

################################################################################
# Step 4: Create Manager A
################################################################################
echo ""
echo "=========================================="
echo "Step 4: Create Manager A"
echo "=========================================="

MANAGER_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager A US4S4\",
                \"login\": \"$MANAGER_A_LOGIN\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [17]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_A_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

MANAGER_A_UID=$(echo "$MANAGER_A_RESPONSE" | jq -r '.result')
echo "✓ Manager A created: UID=$MANAGER_A_UID"

################################################################################
# Step 5: Create Manager B
################################################################################
echo ""
echo "=========================================="
echo "Step 5: Create Manager B"
echo "=========================================="

MANAGER_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$ADMIN_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Manager B US4S4\",
                \"login\": \"$MANAGER_B_LOGIN\",
                \"password\": \"manager123\",
                \"groups_id\": [[6, 0, [17]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_B_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }")

MANAGER_B_UID=$(echo "$MANAGER_B_RESPONSE" | jq -r '.result')
echo "✓ Manager B created: UID=$MANAGER_B_UID"

################################################################################
# Step 6: Retrieve Reference Data
################################################################################
echo ""
echo "=========================================="
echo "Step 6: Retrieve reference data"
echo "=========================================="

PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.property.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.location.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.state",
      "method": "search_read",
      "args": [[]],
      "kwargs": {"fields": ["id", "name"], "limit": 1}
    },
    "id": 1
  }')

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id')
echo "✓ State ID: $STATE_ID"

################################################################################
# Step 7: Create 2 Properties for Company A
################################################################################
echo ""
echo "=========================================="
echo "Step 7: Create 2 properties for Company A"
echo "=========================================="

for i in 1 2; do
    PROPERTY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
      -H "Content-Type: application/json" \
      -H "Cookie: session_id=$ADMIN_SESSION" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
          \"model\": \"real.estate.property\",
          \"method\": \"create\",
          \"args\": [{
            \"name\": \"Company A Property $i\",
            \"property_type_id\": $PROPERTY_TYPE_ID,
            \"location_type_id\": $LOCATION_TYPE_ID,
            \"zip_code\": \"01310-10$i\",
            \"state_id\": $STATE_ID,
            \"city\": \"São Paulo\",
            \"street\": \"Av Paulista\",
            \"street_number\": \"100$i\",
            \"area\": $((80 + i * 10)).0,
            \"price\": $((300000 + i * 50000)).0,
            \"property_status\": \"available\",
            \"company_ids\": [[6, 0, [$COMPANY_A_ID]]]
          }],
          \"kwargs\": {}
        },
        \"id\": 1
      }")

    PROPERTY_A_ID=$(echo "$PROPERTY_A_RESPONSE" | jq -r '.result')
    echo "✓ Company A Property $i created: ID=$PROPERTY_A_ID"
done

################################################################################
# Step 8: Create 2 Properties for Company B
################################################################################
echo ""
echo "=========================================="
echo "Step 8: Create 2 properties for Company B"
echo "=========================================="

for i in 1 2; do
    PROPERTY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
      -H "Content-Type: application/json" \
      -H "Cookie: session_id=$ADMIN_SESSION" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
          \"model\": \"real.estate.property\",
          \"method\": \"create\",
          \"args\": [{
            \"name\": \"Company B Property $i\",
            \"property_type_id\": $PROPERTY_TYPE_ID,
            \"location_type_id\": $LOCATION_TYPE_ID,
            \"zip_code\": \"20000-10$i\",
            \"state_id\": $STATE_ID,
            \"city\": \"Rio de Janeiro\",
            \"street\": \"Av Atlântica\",
            \"street_number\": \"200$i\",
            \"area\": $((70 + i * 10)).0,
            \"price\": $((250000 + i * 40000)).0,
            \"property_status\": \"available\",
            \"company_ids\": [[6, 0, [$COMPANY_B_ID]]]
          }],
          \"kwargs\": {}
        },
        \"id\": 1
      }")

    PROPERTY_B_ID=$(echo "$PROPERTY_B_RESPONSE" | jq -r '.result')
    echo "✓ Company B Property $i created: ID=$PROPERTY_B_ID"
done

################################################################################
# Step 9: Manager A Login
################################################################################
echo ""
echo "=========================================="
echo "Step 9: Manager A login"
echo "=========================================="

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
        \"id\": 1
    }")

MANAGER_A_LOGIN_UID=$(echo "$MANAGER_A_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Manager A logged in: UID=$MANAGER_A_LOGIN_UID"

MANAGER_A_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')

################################################################################
# Step 10: Manager A Views Properties (Should see only Company A)
################################################################################
echo ""
echo "=========================================="
echo "Step 10: Manager A views properties"
echo "=========================================="

MANAGER_A_PROPERTIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_A_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"company_ids\"],
                \"limit\": 100
            }
        },
        \"id\": 1
    }")

MANAGER_A_PROPERTY_COUNT=$(echo "$MANAGER_A_PROPERTIES_RESPONSE" | jq -r '.result | length')
echo "Manager A sees $MANAGER_A_PROPERTY_COUNT properties"

# Check if Manager A sees only Company A properties
COMPANY_B_VISIBLE=$(echo "$MANAGER_A_PROPERTIES_RESPONSE" | jq -r "[.result[] | select(.company_ids and ($COMPANY_B_ID | IN(.company_ids[])))] | length")

if [ "$COMPANY_B_VISIBLE" -gt 0 ]; then
    echo "❌ Manager A can see Company B properties (cross-company access violation)"
    exit 1
fi

echo "✓ Manager A cannot see Company B properties (multi-tenancy working)"

################################################################################
# Step 11: Manager A Views Company Records
################################################################################
echo ""
echo "=========================================="
echo "Step 11: Manager A views companies"
echo "=========================================="

MANAGER_A_COMPANIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_A_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"],
                \"limit\": 100
            }
        },
        \"id\": 1
    }")

MANAGER_A_COMPANY_COUNT=$(echo "$MANAGER_A_COMPANIES_RESPONSE" | jq -r '.result | length')
echo "Manager A sees $MANAGER_A_COMPANY_COUNT company(ies)"

# Check if Company B is visible
COMPANY_B_VISIBLE_COUNT=$(echo "$MANAGER_A_COMPANIES_RESPONSE" | jq -r "[.result[] | select(.id == $COMPANY_B_ID)] | length")

if [ "$COMPANY_B_VISIBLE_COUNT" -gt 0 ]; then
    echo "❌ Manager A can see Company B record (isolation violation)"
    exit 1
fi

echo "✓ Manager A cannot see Company B record (multi-tenancy working)"

################################################################################
# Step 12: Manager B Login and Verify
################################################################################
echo ""
echo "=========================================="
echo "Step 12: Manager B login and verify isolation"
echo "=========================================="

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
        \"id\": 1
    }")

MANAGER_B_LOGIN_UID=$(echo "$MANAGER_B_LOGIN_RESPONSE" | jq -r '.result.uid // empty')
echo "✓ Manager B logged in: UID=$MANAGER_B_LOGIN_UID"

MANAGER_B_SESSION=$(grep 'session_id' cookies.txt | awk '{print $NF}')

MANAGER_B_PROPERTIES_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -H "Cookie: session_id=$MANAGER_B_SESSION" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.property\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\", \"company_ids\"],
                \"limit\": 100
            }
        },
        \"id\": 1
    }")

MANAGER_B_PROPERTY_COUNT=$(echo "$MANAGER_B_PROPERTIES_RESPONSE" | jq -r '.result | length')
echo "Manager B sees $MANAGER_B_PROPERTY_COUNT properties"

# Check if Manager B sees Company A properties
COMPANY_A_VISIBLE=$(echo "$MANAGER_B_PROPERTIES_RESPONSE" | jq -r "[.result[] | select(.company_ids and ($COMPANY_A_ID | IN(.company_ids[])))] | length")

if [ "$COMPANY_A_VISIBLE" -gt 0 ]; then
    echo "❌ Manager B can see Company A properties (cross-company access violation)"
    exit 1
fi

echo "✓ Manager B cannot see Company A properties (multi-tenancy working)"

################################################################################
# Step 13: Test Complete
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US4-S4 Manager Multi-Tenancy Isolation"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Company A created with 2 properties"
echo "  - Company B created with 2 properties"
echo "  - Manager A sees only Company A data (not Company B)"
echo "  - Manager B sees only Company B data (not Company A)"
echo "  - Multi-tenancy isolation working correctly for Managers"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
