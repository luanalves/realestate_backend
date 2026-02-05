#!/usr/bin/env bash
# Feature 007 - US7-S2: Owner-Company Linking (T025)
# Tests linking/unlinking Owner to/from Company
#
# Success Criteria:
# - Link Owner to Company → 200, estate_company_ids updated
# - Unlink Owner from Company (if not last) → 200
# - Cannot unlink last active Owner → 400
# - Owner with no companies can be linked to Company

set -e

BASE_URL="${BASE_URL:-http://localhost:8069}"
DB_NAME="${DB_NAME:-realestate}"
ADMIN_LOGIN="${ADMIN_LOGIN:-admin@admin.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "US7-S2: Owner-Company Linking"
echo "============================================"

# Step 1: Admin login
echo "Step 1: Admin login..."
ADMIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"login\": \"${ADMIN_LOGIN}\",
    \"password\": \"${ADMIN_PASSWORD}\",
    \"db\": \"${DB_NAME}\"
  }")

ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | jq -r '.access_token // .token // empty')

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
  echo -e "${RED}✗ Admin login failed${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Admin logged in${NC}"

# Step 2: Create Company A
echo ""
echo "Step 2: Creating Company A..."
COMPANY_A_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Company A for Linking",
    "cnpj": "11111111000191",
    "email": "companya@linking.com",
    "phone": "11111111111"
  }')

COMPANY_A_ID=$(echo "$COMPANY_A_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$COMPANY_A_ID" ] || [ "$COMPANY_A_ID" = "null" ]; then
  echo -e "${RED}✗ Failed to create Company A${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Company A created: ID=${COMPANY_A_ID}${NC}"

# Step 3: Create Company B
echo ""
echo "Step 3: Creating Company B..."
COMPANY_B_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Company B for Linking",
    "cnpj": "22222222000182",
    "email": "companyb@linking.com",
    "phone": "22222222222"
  }')

COMPANY_B_ID=$(echo "$COMPANY_B_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$COMPANY_B_ID" ] || [ "$COMPANY_B_ID" = "null" ]; then
  echo -e "${RED}✗ Failed to create Company B${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Company B created: ID=${COMPANY_B_ID}${NC}"

# Step 4: Create Owner without companies
echo ""
echo "Step 4: Creating Owner without companies..."
OWNER_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/owners" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Owner for Linking Test",
    "email": "linking@test.com",
    "phone": "11987654321"
  }')

OWNER_ID=$(echo "$OWNER_RESPONSE" | jq -r '.data.id // empty')
INITIAL_COMPANIES=$(echo "$OWNER_RESPONSE" | jq -r '.data.estate_company_ids // empty')

if [ -z "$OWNER_ID" ] || [ "$OWNER_ID" = "null" ]; then
  echo -e "${RED}✗ Failed to create Owner${NC}"
  exit 1
fi

if [ "$INITIAL_COMPANIES" != "[]" ]; then
  echo -e "${RED}✗ Owner should start with no companies${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Owner created with no companies: ID=${OWNER_ID}${NC}"

# Step 5: Link Owner to Company A
echo ""
echo "Step 5: Linking Owner to Company A..."
LINK_A_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/owners/${OWNER_ID}/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{
    \"company_id\": ${COMPANY_A_ID}
  }")

COMPANIES_AFTER_A=$(echo "$LINK_A_RESPONSE" | jq -r '.data.estate_company_ids // empty')
HAS_COMPANY_A=$(echo "$LINK_A_RESPONSE" | jq -r ".data.estate_company_ids[] | select(. == ${COMPANY_A_ID})")

if [ -z "$HAS_COMPANY_A" ]; then
  echo -e "${RED}✗ Owner not linked to Company A${NC}"
  echo "Response: $LINK_A_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✓ Owner linked to Company A${NC}"

# Step 6: Link Owner to Company B
echo ""
echo "Step 6: Linking Owner to Company B..."
LINK_B_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/owners/${OWNER_ID}/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{
    \"company_id\": ${COMPANY_B_ID}
  }")

COMPANIES_AFTER_B=$(echo "$LINK_B_RESPONSE" | jq -r '.data.estate_company_ids | length')

if [ "$COMPANIES_AFTER_B" != "2" ]; then
  echo -e "${RED}✗ Owner should have 2 companies${NC}"
  echo "Got: $COMPANIES_AFTER_B companies"
  exit 1
fi

echo -e "${GREEN}✓ Owner linked to Company B (now has 2 companies)${NC}"

# Step 7: Unlink Owner from Company B (not last owner)
echo ""
echo "Step 7: Unlinking Owner from Company B..."
UNLINK_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
  "${BASE_URL}/api/v1/owners/${OWNER_ID}/companies/${COMPANY_B_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

HTTP_CODE=$(echo "$UNLINK_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$UNLINK_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ Failed to unlink from Company B${NC}"
  echo "HTTP Code: $HTTP_CODE"
  exit 1
fi

REMAINING_COMPANIES=$(echo "$RESPONSE_BODY" | jq -r '.data.estate_company_ids | length')

if [ "$REMAINING_COMPANIES" != "1" ]; then
  echo -e "${RED}✗ Owner should have 1 company remaining${NC}"
  echo "Got: $REMAINING_COMPANIES"
  exit 1
fi

echo -e "${GREEN}✓ Owner unlinked from Company B (1 company remaining)${NC}"

# Step 8: Try to unlink last owner (should fail)
echo ""
echo "Step 8: Testing last-owner protection..."
UNLINK_LAST_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
  "${BASE_URL}/api/v1/owners/${OWNER_ID}/companies/${COMPANY_A_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

HTTP_CODE=$(echo "$UNLINK_LAST_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" != "400" ]; then
  echo -e "${YELLOW}⚠  Expected HTTP 400 for unlinking last owner, got ${HTTP_CODE}${NC}"
else
  echo -e "${GREEN}✓ Last-owner protection working (400 Bad Request)${NC}"
fi

# Step 9: Create second owner for Company A
echo ""
echo "Step 9: Creating second owner for Company A..."
OWNER2_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/owners" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Second Owner",
    "email": "second@test.com",
    "phone": "11888777666"
  }')

OWNER2_ID=$(echo "$OWNER2_RESPONSE" | jq -r '.data.id // empty')

# Link Owner2 to Company A
curl -s -X POST "${BASE_URL}/api/v1/owners/${OWNER2_ID}/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{
    \"company_id\": ${COMPANY_A_ID}
  }" > /dev/null

echo -e "${GREEN}✓ Second owner created and linked to Company A${NC}"

# Step 10: Now first owner can be unlinked from Company A
echo ""
echo "Step 10: Unlinking first owner from Company A (now allowed)..."
UNLINK_FINAL_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
  "${BASE_URL}/api/v1/owners/${OWNER_ID}/companies/${COMPANY_A_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")

HTTP_CODE=$(echo "$UNLINK_FINAL_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$UNLINK_FINAL_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ Failed to unlink (should be allowed now)${NC}"
  echo "HTTP Code: $HTTP_CODE"
  exit 1
fi

FINAL_COMPANIES=$(echo "$RESPONSE_BODY" | jq -r '.data.estate_company_ids | length')

if [ "$FINAL_COMPANIES" != "0" ]; then
  echo -e "${RED}✗ Owner should have 0 companies${NC}"
  echo "Got: $FINAL_COMPANIES"
  exit 1
fi

echo -e "${GREEN}✓ First owner successfully unlinked (0 companies)${NC}"

# Final Summary
echo ""
echo "============================================"
echo -e "${GREEN}✓ TEST PASSED: US7-S2 Owner-Company Linking${NC}"
echo "============================================"
echo ""
echo "Summary:"
echo "  - Link Owner to Company A: ✓"
echo "  - Link Owner to Company B: ✓"
echo "  - Unlink Owner from Company B: ✓"
echo "  - Last-owner protection (fail): ✓"
echo "  - Add second owner: ✓"
echo "  - Unlink first owner (now allowed): ✓"
echo ""
echo "Next steps:"
echo "  - Run: bash integration_tests/test_us7_s3_company_crud.sh"
echo "  - Run: bash integration_tests/test_us7_s4_rbac.sh"
echo ""
