#!/usr/bin/env bash
# Feature 007 - US7-S6: Owner Auto-Company Binding Investigation
# Tests whether a newly created owner is automatically linked to any company.
#
# Success Criteria:
# - Create Owner → 201 response
# - Response includes company_count and companies fields
# - Investigate: is owner automatically linked to a company not specified in the request?

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================"
echo "US7-S6: Owner Auto-Company Binding Investigation"
echo "============================================"

# Step 1: Get OAuth2 token
echo ""
echo "Step 1: Getting OAuth2 token..."
ACCESS_TOKEN=$(get_oauth2_token)

if [ $? -ne 0 ] || [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}✗ Failed to get OAuth2 token${NC}"
    exit 1
fi

echo -e "${GREEN}✓ OAuth2 token obtained${NC}"

# Step 2: Create owner WITHOUT specifying any company
echo ""
echo "Step 2: Creating owner WITHOUT specifying any company..."
TIMESTAMP=$(date +%s)
TEST_EMAIL="owner_auto_company_${TIMESTAMP}@test.com"

TEST_CPF=$(python3 -c "
import random
b=f'{random.randint(100,999)}{random.randint(100,999)}{random.randint(100,999)}'
w1=[10,9,8,7,6,5,4,3,2]; s=sum(int(d)*w for d,w in zip(b,w1)); d1=0 if (11-s%11)>=10 else (11-s%11)
w2=[11,10,9,8,7,6,5,4,3,2]; s=sum(int(d)*w for d,w in zip(b+str(d1),w2)); d2=0 if (11-s%11)>=10 else (11-s%11)
print(f'{b[:3]}.{b[3:6]}.{b[6:9]}-{d1}{d2}')
")

echo -e "${BLUE}  Payload: name, email, cpf, password only (no company_id)${NC}"

CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/owners" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -d "{
        \"name\": \"Auto Company Test Owner\",
        \"email\": \"${TEST_EMAIL}\",
        \"cpf\": \"${TEST_CPF}\",
        \"password\": \"secure123456\"
    }")

OWNER_ID=$(echo "$CREATE_RESPONSE" | jq -r '.data.id // empty')
SUCCESS=$(echo "$CREATE_RESPONSE" | jq -r '.success // empty')

if [ -z "$OWNER_ID" ] || [ "$OWNER_ID" = "null" ] || [ "$SUCCESS" != "true" ]; then
    echo -e "${RED}✗ Failed to create owner${NC}"
    echo "Response: $CREATE_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Owner created: ID=${OWNER_ID}${NC}"

# Step 3: Inspect company data from creation response
echo ""
echo "Step 3: Inspecting company data from creation response..."
COMPANY_COUNT=$(echo "$CREATE_RESPONSE" | jq -r '.data.company_count // empty')
COMPANIES=$(echo "$CREATE_RESPONSE" | jq -r '.data.companies // empty')
COMPANIES_LENGTH=$(echo "$CREATE_RESPONSE" | jq '.data.companies | length')

echo -e "${BLUE}  company_count : ${COMPANY_COUNT}${NC}"
echo -e "${BLUE}  companies     : ${COMPANIES}${NC}"
echo -e "${BLUE}  companies[]   : ${COMPANIES_LENGTH} item(s)${NC}"

if [ "$COMPANY_COUNT" = "0" ] && [ "$COMPANIES_LENGTH" = "0" ]; then
    echo -e "${GREEN}✓ RESULT: Owner created with NO automatic company binding${NC}"
    AUTO_COMPANY_RESULT="no_auto_binding"
elif [ "$COMPANY_COUNT" -gt "0" ] 2>/dev/null; then
    echo -e "${YELLOW}⚠  RESULT: Owner was automatically linked to ${COMPANY_COUNT} company(ies)${NC}"
    echo -e "${YELLOW}   Companies: $(echo "$CREATE_RESPONSE" | jq -c '.data.companies')${NC}"
    AUTO_COMPANY_RESULT="auto_bound"
else
    echo -e "${YELLOW}⚠  RESULT: Inconclusive — company_count=${COMPANY_COUNT}${NC}"
    AUTO_COMPANY_RESULT="inconclusive"
fi

# Step 4: Cross-check via database
echo ""
echo "Step 4: Cross-checking via database (res_company_users_rel)..."
DB_RESULT=$(docker compose -f "${SCRIPT_DIR}/../18.0/docker-compose.yml" exec -T db \
    psql -U odoo -d "${POSTGRES_DB:-realestate}" -t -A -c \
    "SELECT c.name FROM res_company c
     JOIN res_company_users_rel rel ON rel.cid = c.id
     WHERE rel.user_id = ${OWNER_ID};" 2>/dev/null || echo "DB_QUERY_FAILED")

if [ "$DB_RESULT" = "DB_QUERY_FAILED" ] || [ -z "$DB_RESULT" ]; then
    echo -e "${YELLOW}⚠  DB query unavailable or owner has no company links in DB${NC}"
    DB_COMPANIES="(not available)"
else
    echo -e "${BLUE}  DB companies linked: ${DB_RESULT}${NC}"
    DB_COMPANIES="$DB_RESULT"
fi

# Step 5: Cross-check company_id (default single-company field)
echo ""
echo "Step 5: Checking default company_id via database..."
DB_DEFAULT_COMPANY=$(docker compose -f "${SCRIPT_DIR}/../18.0/docker-compose.yml" exec -T db \
    psql -U odoo -d "${POSTGRES_DB:-realestate}" -t -A -c \
    "SELECT c.name FROM res_company c
     JOIN res_users u ON u.company_id = c.id
     WHERE u.id = ${OWNER_ID};" 2>/dev/null || echo "DB_QUERY_FAILED")

if [ "$DB_DEFAULT_COMPANY" = "DB_QUERY_FAILED" ] || [ -z "$DB_DEFAULT_COMPANY" ]; then
    echo -e "${YELLOW}⚠  DB query unavailable${NC}"
else
    echo -e "${BLUE}  Default company_id: ${DB_DEFAULT_COMPANY}${NC}"
    echo -e "${YELLOW}  NOTE: Odoo requires a default company_id for res.users — this is set internally by the controller, not from the request payload.${NC}"
fi

# Final Summary
echo ""
echo "============================================"
echo "SUMMARY: US7-S6 Owner Auto-Company Binding"
echo "============================================"
echo "  Owner ID         : ${OWNER_ID}"
echo "  Email            : ${TEST_EMAIL}"
echo "  Response companies: ${COMPANY_COUNT} item(s)"
echo "  DB companies     : ${DB_COMPANIES}"
echo "  DB default co.   : ${DB_DEFAULT_COMPANY:-n/a}"
echo ""

case "$AUTO_COMPANY_RESULT" in
    "no_auto_binding")
        echo -e "${GREEN}✓ TEST PASSED: Owner is NOT automatically bound to any company in the API response.${NC}"
        echo -e "${YELLOW}  NOTE: Odoo internally sets a default company_id on res.users (required field).${NC}"
        echo -e "${YELLOW}        This is the Odoo default company (system), NOT a real estate company created by the user.${NC}"
        ;;
    "auto_bound")
        echo -e "${YELLOW}⚠  TEST FINDING: Owner IS automatically linked to ${COMPANY_COUNT} company(ies).${NC}"
        echo -e "${YELLOW}   This may be intentional (Odoo default company) or a bug.${NC}"
        echo -e "${YELLOW}   Investigate: is the linked company a real estate company or just the Odoo system default?${NC}"
        ;;
    "inconclusive")
        echo -e "${YELLOW}⚠  TEST INCONCLUSIVE: Could not determine binding status.${NC}"
        ;;
esac

echo ""
echo "Next steps:"
echo "  - Run: bash integration_tests/test_us7_s2_owner_company_link.sh"
echo ""
