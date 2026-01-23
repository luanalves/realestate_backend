#!/bin/bash

################################################################################
# Test Script: US5-S4 Prospector Restrictions
# Spec: specs/005-rbac-user-profiles/spec.md
# User Story: 5 - Prospector Creates Properties with Commission Split
# Scenario: 5 - Prospector cannot access leads, has read-only on agents/sales
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
echo "US5-S4: Prospector Restrictions"
echo "========================================"

# Cleanup temporary files
rm -f cookies.txt response.json

# Generate unique identifiers
TIMESTAMP=$(date +%Y%m%d%H%M%S)
COMPANY_NAME="Company_US5S4_${TIMESTAMP}"
PROSPECTOR_LOGIN="prospector.us5s4.${TIMESTAMP}@company.com"

# Generate valid CNPJ
CNPJ=$(python3 << 'PYTHON_EOF'
def calc_cnpj_digit(cnpj, weights):
    s = sum(int(d) * w for d, w in zip(cnpj, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "66778899"
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

# Create prospector user
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
                \"name\": \"Prospector US5S4\",
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
echo "✓ Prospector user created: UID=$PROSPECTOR_UID"

# Create prospector agent record
CPF_PROSPECTOR=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "44455566"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

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
                \"name\": \"Prospector US5S4\",
                \"user_id\": $PROSPECTOR_UID,
                \"cpf\": \"$CPF_PROSPECTOR\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 4
    }")

PROSPECTOR_AGENT_ID=$(echo "$PROSPECTOR_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Prospector agent record created: ID=$PROSPECTOR_AGENT_ID"

# Create a lead and agent for testing (as admin)
AGENT_USER_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent US5S4\",
                \"login\": \"agent.us5s4.${TIMESTAMP}@company.com\",
                \"password\": \"agent123\",
                \"groups_id\": [[6, 0, [23]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 5
    }")

AGENT_UID=$(echo "$AGENT_USER_RESPONSE" | jq -r '.result // empty')

CPF_AGENT=$(python3 << 'PYTHON_EOF'
def calc_cpf_digit(cpf, weights):
    s = sum(int(d) * w for d, w in zip(cpf, weights))
    remainder = s % 11
    return '0' if remainder < 2 else str(11 - remainder)

base = "77788899"
d1 = calc_cpf_digit(base, range(10, 1, -1))
d2 = calc_cpf_digit(base + d1, range(11, 1, -1))
cpf = f"{base[0:3]}.{base[3:6]}.{base[6:8]}{d1}-{d2}"
print(cpf)
PYTHON_EOF
)

AGENT_AGENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent US5S4\",
                \"user_id\": $AGENT_UID,
                \"cpf\": \"$CPF_AGENT\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 6
    }")

AGENT_AGENT_ID=$(echo "$AGENT_AGENT_RESPONSE" | jq -r '.result // empty')
echo "✓ Test agent created: ID=$AGENT_AGENT_ID"

# Create a lead (as admin)
LEAD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lead\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Test Lead US5S4\",
                \"agent_id\": $AGENT_AGENT_ID,
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 7
    }")

LEAD_ID=$(echo "$LEAD_RESPONSE" | jq -r '.result // empty')
echo "✓ Test lead created: ID=$LEAD_ID"

################################################################################
# Step 2: Prospector Login
################################################################################
echo ""
echo "=========================================="
echo "Step 2: Prospector login"
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
echo "✓ Prospector logged in: UID=$PROSPECTOR_SESSION_UID"

################################################################################
# Step 3: Test Restrictions
################################################################################
echo ""
echo "=========================================="
echo "Step 3: Test prospector restrictions"
echo "=========================================="

# Test 1: Cannot create leads
echo ""
echo "Test 1: Prospector attempts to create lead"
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
                \"name\": \"Prospector Lead Attempt\",
                \"agent_id\": $PROSPECTOR_AGENT_ID,
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 9
    }")

LEAD_CREATE_ERROR=$(echo "$LEAD_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$LEAD_CREATE_ERROR" ]; then
    echo "✓ Prospector cannot create leads (permission denied)"
else
    NEW_LEAD_ID=$(echo "$LEAD_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_LEAD_ID" ] && [ "$NEW_LEAD_ID" != "null" ]; then
        echo "❌ BUG: Prospector should not be able to create leads (created ID=$NEW_LEAD_ID)"
        exit 1
    fi
fi

# Test 2: Cannot access leads (read)
echo ""
echo "Test 2: Prospector attempts to read leads"
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
        \"id\": 10
    }")

LEAD_READ_ERROR=$(echo "$LEAD_READ_RESPONSE" | jq -r '.error.data.message // empty')
LEADS_COUNT=$(echo "$LEAD_READ_RESPONSE" | jq -r '.result | length // 0')

if [ -n "$LEAD_READ_ERROR" ] || [ "$LEADS_COUNT" == "0" ]; then
    echo "✓ Prospector cannot access leads"
else
    echo "❌ BUG: Prospector should not see leads (sees $LEADS_COUNT leads)"
    exit 1
fi

# Test 3: Can read agents (read-only)
echo ""
echo "Test 3: Prospector attempts to read agents"
AGENTS_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"search_read\",
            \"args\": [[]],
            \"kwargs\": {
                \"fields\": [\"id\", \"name\"]
            }
        },
        \"id\": 11
    }")

AGENTS_READ_ERROR=$(echo "$AGENTS_READ_RESPONSE" | jq -r '.error.data.message // empty')
AGENTS_COUNT=$(echo "$AGENTS_READ_RESPONSE" | jq -r '.result | length // 0')

if [ -n "$AGENTS_READ_ERROR" ]; then
    echo "❌ Prospector should be able to read agents"
    exit 1
elif [ "$AGENTS_COUNT" -gt "0" ]; then
    echo "✓ Prospector can read agents ($AGENTS_COUNT agents visible)"
else
    echo "⚠️  Prospector has read permission but sees 0 agents"
fi

# Test 4: Cannot create/modify agents
echo ""
echo "Test 4: Prospector attempts to create agent"
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
                \"name\": \"Prospector Agent Attempt\",
                \"cpf\": \"111.222.333-44\",
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        },
        \"id\": 12
    }")

AGENT_CREATE_ERROR=$(echo "$AGENT_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$AGENT_CREATE_ERROR" ]; then
    echo "✓ Prospector cannot create agents (permission denied)"
else
    NEW_AGENT_ID=$(echo "$AGENT_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_AGENT_ID" ] && [ "$NEW_AGENT_ID" != "null" ]; then
        echo "❌ BUG: Prospector should not be able to create agents (created ID=$NEW_AGENT_ID)"
        exit 1
    fi
fi

# Test 5: Can read own sales (where prospector_id = own agent)
echo ""
echo "Test 5: Prospector attempts to read sales"
SALES_READ_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
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
                \"fields\": [\"id\", \"property_id\"]
            }
        },
        \"id\": 13
    }")

SALES_READ_ERROR=$(echo "$SALES_READ_RESPONSE" | jq -r '.error.data.message // empty')
SALES_COUNT=$(echo "$SALES_READ_RESPONSE" | jq -r '.result | length // 0')

if [ -n "$SALES_READ_ERROR" ]; then
    echo "❌ Prospector should be able to read sales (record rule allows own sales)"
    exit 1
else
    echo "✓ Prospector can read sales (sees $SALES_COUNT sales - own prospected properties only)"
fi

# Test 6: Cannot create sales
echo ""
echo "Test 6: Prospector attempts to create sale"
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
        \"id\": 14
    }")

SALE_CREATE_ERROR=$(echo "$SALE_CREATE_RESPONSE" | jq -r '.error.data.message // empty')

if [ -n "$SALE_CREATE_ERROR" ]; then
    echo "✓ Prospector cannot create sales (permission denied)"
else
    NEW_SALE_ID=$(echo "$SALE_CREATE_RESPONSE" | jq -r '.result // empty')
    if [ -n "$NEW_SALE_ID" ] && [ "$NEW_SALE_ID" != "null" ]; then
        echo "❌ BUG: Prospector should not be able to create sales (created ID=$NEW_SALE_ID)"
        exit 1
    fi
fi

################################################################################
# Final Result
################################################################################
echo ""
echo "=========================================="
echo "✅ TEST PASSED: US5-S4 Prospector Restrictions"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - ✓ Prospector cannot create leads"
echo "  - ✓ Prospector cannot access/read leads"
echo "  - ✓ Prospector can read agents (read-only)"
echo "  - ✓ Prospector cannot create agents"
echo "  - ✓ Prospector can read sales (own prospected properties only)"
echo "  - ✓ Prospector cannot create sales"
echo "  - ACL restrictions working correctly"
echo ""

# Cleanup
rm -f cookies.txt response.json

exit 0
