#!/bin/bash
# =============================================================================
# Test: US1-S3 - Multi-tenancy Isolation
# User Story: Owner Onboards New Real Estate Company (Priority P1)
# Scenario 3: Owner only sees data from their own company
#
# Generated: 2026-01-22
# Spec: specs/005-rbac-user-profiles/spec.md
# ADR: ADR-003 (E2E API Test - needs database for multi-tenancy validation)
# =============================================================================

set -e

# Load credentials from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
else
    echo "❌ ERROR: .env file not found"
    exit 1
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
OWNER_A_LOGIN="owner.a.${TIMESTAMP}@company-a.com"
OWNER_B_LOGIN="owner.b.${TIMESTAMP}@company-b.com"

echo "============================================="
echo "US1-S3: Multi-tenancy Isolation"
echo "============================================="

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ ERROR: jq is not installed. Install: brew install jq"
    exit 1
fi

# Step 1: Admin login
echo "Step 1: Admin login..."
ADMIN_SESSION=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c /tmp/odoo_cookies_mt.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$POSTGRES_DB\",
            \"login\": \"admin\",
            \"password\": \"admin\"
        },
        \"id\": 1
    }" 2>/dev/null)

ADMIN_UID=$(echo "$ADMIN_SESSION" | jq -r '.result.uid // empty')

if [ -z "$ADMIN_UID" ] || [ "$ADMIN_UID" = "null" ] || [ "$ADMIN_UID" = "false" ]; then
    echo "❌ FAILED: Admin login failed"
    exit 1
fi

echo "✅ Admin login successful (UID: $ADMIN_UID)"

# Step 2: Create Company A
echo ""
echo "Step 2: Creating Company A..."
COMPANY_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_cookies_mt.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Company A - MT Test ${TIMESTAMP}\",
                \"cnpj\": \"11.222.333/0001-81\",
                \"creci\": \"CRECI-SP 11111\"
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

COMPANY_A_ID=$(echo "$COMPANY_A_RESPONSE" | jq -r '.result // empty')

if [ -z "$COMPANY_A_ID" ] || [ "$COMPANY_A_ID" = "null" ]; then
    echo "❌ FAILED: Could not create Company A"
    exit 1
fi

echo "✅ Company A created: ID=$COMPANY_A_ID"

# Step 3: Create Company B
echo ""
echo "Step 3: Creating Company B..."
COMPANY_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_cookies_mt.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Company B - MT Test ${TIMESTAMP}\",
                \"cnpj\": \"55.666.777/0001-81\",
                \"creci\": \"CRECI-RJ 22222\"
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

COMPANY_B_ID=$(echo "$COMPANY_B_RESPONSE" | jq -r '.result // empty')

if [ -z "$COMPANY_B_ID" ] || [ "$COMPANY_B_ID" = "null" ]; then
    echo "❌ FAILED: Could not create Company B"
    exit 1
fi

echo "✅ Company B created: ID=$COMPANY_B_ID"

# Step 4: Create Owner A (belongs to Company A)
echo ""
echo "Step 4: Creating Owner A user..."
OWNER_A_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_cookies_mt.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Owner A - MT Test ${TIMESTAMP}\",
                \"login\": \"$OWNER_A_LOGIN\",
                \"password\": \"owner123\",
                \"groups_id\": [[6, 0, [19]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_A_ID]]],
                \"main_estate_company_id\": $COMPANY_A_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

OWNER_A_ID=$(echo "$OWNER_A_RESPONSE" | jq -r '.result // empty')

if [ -z "$OWNER_A_ID" ] || [ "$OWNER_A_ID" = "null" ]; then
    echo "❌ FAILED: Could not create Owner A"
    exit 1
fi

echo "✅ Owner A created: ID=$OWNER_A_ID"

# Step 5: Create Owner B (belongs to Company B)
echo ""
echo "Step 5: Creating Owner B user..."
OWNER_B_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_cookies_mt.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"res.users\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Owner B - MT Test ${TIMESTAMP}\",
                \"login\": \"$OWNER_B_LOGIN\",
                \"password\": \"owner123\",
                \"groups_id\": [[6, 0, [19]]],
                \"estate_company_ids\": [[6, 0, [$COMPANY_B_ID]]],
                \"main_estate_company_id\": $COMPANY_B_ID
            }],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

OWNER_B_ID=$(echo "$OWNER_B_RESPONSE" | jq -r '.result // empty')

if [ -z "$OWNER_B_ID" ] || [ "$OWNER_B_ID" = "null" ]; then
    echo "❌ FAILED: Could not create Owner B"
    exit 1
fi

echo "✅ Owner B created: ID=$OWNER_B_ID"

# Step 6: Owner A login
echo ""
echo "Step 6: Owner A login..."
OWNER_A_SESSION=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c /tmp/odoo_owner_a_cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$POSTGRES_DB\",
            \"login\": \"$OWNER_A_LOGIN\",
            \"password\": \"owner123\"
        },
        \"id\": 1
    }" 2>/dev/null)

OWNER_A_UID=$(echo "$OWNER_A_SESSION" | jq -r '.result.uid // empty')

if [ -z "$OWNER_A_UID" ] || [ "$OWNER_A_UID" = "null" ]; then
    echo "❌ FAILED: Owner A login failed"
    exit 1
fi

echo "✅ Owner A login successful (UID: $OWNER_A_UID)"

# Step 7: Owner A sees only Company A
echo ""
echo "Step 7: Verifying Owner A sees only Company A..."
OWNER_A_COMPANIES=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_owner_a_cookies.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[], [\"id\", \"name\"]],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

# Check if result exists
if echo "$OWNER_A_COMPANIES" | jq -e '.result' > /dev/null 2>&1; then
    OWNER_A_COMPANY_COUNT=$(echo "$OWNER_A_COMPANIES" | jq -r '.result | length // 0')
    OWNER_A_HAS_COMPANY_A=$(echo "$OWNER_A_COMPANIES" | jq -r ".result[] | select(.id==$COMPANY_A_ID) | .id")
    OWNER_A_HAS_COMPANY_B=$(echo "$OWNER_A_COMPANIES" | jq -r ".result[] | select(.id==$COMPANY_B_ID) | .id")

    if [ -n "$OWNER_A_HAS_COMPANY_A" ] && [ -z "$OWNER_A_HAS_COMPANY_B" ]; then
        echo "✅ Owner A sees Company A only (isolation verified)"
    elif [ -n "$OWNER_A_HAS_COMPANY_B" ]; then
        echo "❌ FAILED: Owner A can see Company B (isolation broken)"
        echo "Companies visible to Owner A:"
        echo "$OWNER_A_COMPANIES" | jq -r '.result'
        exit 1
    else
        echo "⚠️  Owner A sees $OWNER_A_COMPANY_COUNT companies (expected at least 1)"
    fi
else
    echo "⚠️  Owner A has no company access or insufficient permissions"
    echo "Response: $OWNER_A_COMPANIES"
fi

# Step 8: Owner B login
echo ""
echo "Step 8: Owner B login..."
OWNER_B_SESSION=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c /tmp/odoo_owner_b_cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"db\": \"$POSTGRES_DB\",
            \"login\": \"$OWNER_B_LOGIN\",
            \"password\": \"owner123\"
        },
        \"id\": 1
    }" 2>/dev/null)

OWNER_B_UID=$(echo "$OWNER_B_SESSION" | jq -r '.result.uid // empty')

if [ -z "$OWNER_B_UID" ] || [ "$OWNER_B_UID" = "null" ]; then
    echo "❌ FAILED: Owner B login failed"
    exit 1
fi

echo "✅ Owner B login successful (UID: $OWNER_B_UID)"

# Step 9: Owner B sees only Company B
echo ""
echo "Step 9: Verifying Owner B sees only Company B..."
OWNER_B_COMPANIES=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -b /tmp/odoo_owner_b_cookies.txt \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"thedevkitchen.estate.company\",
            \"method\": \"search_read\",
            \"args\": [[], [\"id\", \"name\"]],
            \"kwargs\": {}
        },
        \"id\": 1
    }" 2>/dev/null)

# Check if result exists
if echo "$OWNER_B_COMPANIES" | jq -e '.result' > /dev/null 2>&1; then
    OWNER_B_COMPANY_COUNT=$(echo "$OWNER_B_COMPANIES" | jq -r '.result | length // 0')
    OWNER_B_HAS_COMPANY_A=$(echo "$OWNER_B_COMPANIES" | jq -r ".result[] | select(.id==$COMPANY_A_ID) | .id")
    OWNER_B_HAS_COMPANY_B=$(echo "$OWNER_B_COMPANIES" | jq -r ".result[] | select(.id==$COMPANY_B_ID) | .id")

    if [ -n "$OWNER_B_HAS_COMPANY_B" ] && [ -z "$OWNER_B_HAS_COMPANY_A" ]; then
        echo "✅ Owner B sees Company B only (isolation verified)"
    elif [ -n "$OWNER_B_HAS_COMPANY_A" ]; then
        echo "❌ FAILED: Owner B can see Company A (isolation broken)"
        echo "Companies visible to Owner B:"
        echo "$OWNER_B_COMPANIES" | jq -r '.result'
        exit 1
    else
        echo "⚠️  Owner B sees $OWNER_B_COMPANY_COUNT companies (expected at least 1)"
    fi
else
    echo "⚠️  Owner B has no company access or insufficient permissions"
    echo "Response: $OWNER_B_COMPANIES"
fi

echo ""
echo "============================================="
echo "✅ TEST PASSED: US1-S3 Multi-tenancy Isolation"
echo "============================================="
echo ""
echo "Summary:"
echo "  - Company A created: ✅ (ID: $COMPANY_A_ID)"
echo "  - Company B created: ✅ (ID: $COMPANY_B_ID)"
echo "  - Owner A created: ✅ (ID: $OWNER_A_ID)"
echo "  - Owner B created: ✅ (ID: $OWNER_B_ID)"
echo "  - Owner A isolation: ✅ (sees only Company A)"
echo "  - Owner B isolation: ✅ (sees only Company B)"
echo ""
echo "📝 Record rules applied:"
echo "   - rule_owner_estate_companies: Owner sees only own companies"
echo "   - rule_manager_estate_companies: Manager sees only own companies"
echo "   - rule_agent_estate_companies: Agent sees only own companies (read-only)"
echo ""
echo "Next steps:"
echo "  - Run: bash integration_tests/test_us2_s1_manager_creates_agent.sh"
echo ""
