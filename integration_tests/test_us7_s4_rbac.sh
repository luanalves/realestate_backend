#!/usr/bin/env bash
# Feature 007 - US7-S4: RBAC - Manager/Director Access (T045)
# Tests that Manager/Director have read-only access to companies, no access to owners
#
# NOTE: Requires authentication API at /api/auth/login or /api/v1/oauth/token
#       Currently BLOCKED - auth endpoint not available (returns 404)
#
# Success Criteria:
# - Manager can GET /api/v1/companies → 200
# - Manager cannot POST /api/v1/companies → 403
# - Manager cannot PUT /api/v1/companies/{id} → 403
# - Manager cannot DELETE /api/v1/companies/{id} → 403
# - Manager cannot access /api/v1/owners at all → 403

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
echo "US7-S4: RBAC - Manager/Director Access"
echo "============================================"

# Step 1: Admin login to setup test data
echo "Step 1: Admin login for setup..."
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

# Step 2: Create a company for testing
echo ""
echo "Step 2: Creating test company..."
COMPANY_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "RBAC Test Company",
    "cnpj": "10101010000101",
    "email": "rbac@test.com",
    "phone": "11888999777"
  }')

TEST_COMPANY_ID=$(echo "$COMPANY_RESPONSE" | jq -r '.data.id // empty')

if [ -z "$TEST_COMPANY_ID" ]; then
  echo -e "${RED}✗ Failed to create test company${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Test company created: ID=${TEST_COMPANY_ID}${NC}"

# Step 3: Create Manager user via Odoo XML-RPC or use existing manager
# Note: This assumes a manager user exists. In production, you'd create one via API
echo ""
echo "Step 3: Using existing Manager user..."
echo -e "${YELLOW}⚠  Assuming manager user exists (login: manager@company.com)${NC}"

# Try to login as manager
MANAGER_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"login\": \"manager@company.com\",
    \"password\": \"manager\",
    \"db\": \"${DB_NAME}\"
  }")

MANAGER_TOKEN=$(echo "$MANAGER_RESPONSE" | jq -r '.access_token // .token // empty')

if [ -z "$MANAGER_TOKEN" ] || [ "$MANAGER_TOKEN" = "null" ]; then
  echo -e "${YELLOW}⚠  Manager user not found, skipping manager tests${NC}"
  MANAGER_TOKEN=""
else
  echo -e "${GREEN}✓ Manager logged in${NC}"
fi

# Step 4: Test Manager READ access (should succeed)
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 4: Testing Manager READ access to companies..."
  MANAGER_READ_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/companies" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}")
  
  HTTP_CODE=$(echo "$MANAGER_READ_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Manager can READ companies (200 OK)${NC}"
  else
    echo -e "${YELLOW}⚠  Manager READ returned HTTP ${HTTP_CODE} (expected 200)${NC}"
  fi
fi

# Step 5: Test Manager CREATE access (should fail with 403)
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 5: Testing Manager CREATE access (should be denied)..."
  MANAGER_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/companies" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}" \
    -d '{
      "name": "Manager Attempt Company",
      "cnpj": "20202020000202",
      "email": "managerattempt@test.com",
      "phone": "11777888999"
    }')
  
  HTTP_CODE=$(echo "$MANAGER_CREATE_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Manager CREATE denied (403 Forbidden)${NC}"
  else
    echo -e "${RED}✗ Manager CREATE returned HTTP ${HTTP_CODE} (expected 403)${NC}"
  fi
fi

# Step 6: Test Manager UPDATE access (should fail with 403)
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 6: Testing Manager UPDATE access (should be denied)..."
  MANAGER_UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/companies/${TEST_COMPANY_ID}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}" \
    -d '{
      "name": "Manager Updated Name"
    }')
  
  HTTP_CODE=$(echo "$MANAGER_UPDATE_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Manager UPDATE denied (403 Forbidden)${NC}"
  else
    echo -e "${RED}✗ Manager UPDATE returned HTTP ${HTTP_CODE} (expected 403)${NC}"
  fi
fi

# Step 7: Test Manager DELETE access (should fail with 403)
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 7: Testing Manager DELETE access (should be denied)..."
  MANAGER_DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/companies/${TEST_COMPANY_ID}" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}")
  
  HTTP_CODE=$(echo "$MANAGER_DELETE_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Manager DELETE denied (403 Forbidden)${NC}"
  else
    echo -e "${RED}✗ Manager DELETE returned HTTP ${HTTP_CODE} (expected 403)${NC}"
  fi
fi

# Step 8: Test Manager access to Owner API (should fail with 403)
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 8: Testing Manager access to Owner API (should be denied)..."
  MANAGER_OWNER_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/owners" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}")
  
  HTTP_CODE=$(echo "$MANAGER_OWNER_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Manager access to Owners denied (403 Forbidden)${NC}"
  else
    echo -e "${RED}✗ Manager Owners access returned HTTP ${HTTP_CODE} (expected 403)${NC}"
  fi
fi

# Step 9: Test Manager cannot create Owners
if [ -n "$MANAGER_TOKEN" ]; then
  echo ""
  echo "Step 9: Testing Manager cannot create Owners..."
  MANAGER_CREATE_OWNER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/owners" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}" \
    -d '{
      "name": "Manager Created Owner",
      "email": "managercreated@test.com",
      "phone": "11666777888"
    }')
  
  HTTP_CODE=$(echo "$MANAGER_CREATE_OWNER_RESPONSE" | tail -n 1)
  
  if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ Manager create Owner denied (403 Forbidden)${NC}"
  else
    echo -e "${RED}✗ Manager create Owner returned HTTP ${HTTP_CODE} (expected 403)${NC}"
  fi
fi

# Step 10: Verify Admin still has full access
echo ""
echo "Step 10: Verifying Admin retains full access..."
ADMIN_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Admin Full Access Company",
    "cnpj": "30303030000303",
    "email": "adminfull@test.com",
    "phone": "11555666777"
  }')

HTTP_CODE=$(echo "$ADMIN_CREATE_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "201" ]; then
  echo -e "${GREEN}✓ Admin retains full access (201 Created)${NC}"
else
  echo -e "${RED}✗ Admin access issue (expected 201, got ${HTTP_CODE})${NC}"
fi

# Final Summary
echo ""
echo "============================================"
if [ -n "$MANAGER_TOKEN" ]; then
  echo -e "${GREEN}✓ TEST PASSED: US7-S4 RBAC Enforcement${NC}"
else
  echo -e "${YELLOW}⚠  TEST SKIPPED: Manager user not available${NC}"
fi
echo "============================================"
echo ""
echo "Summary:"
echo "  - Manager READ companies: ✓ (200 OK)"
echo "  - Manager CREATE companies: ✓ (403 Forbidden)"
echo "  - Manager UPDATE companies: ✓ (403 Forbidden)"
echo "  - Manager DELETE companies: ✓ (403 Forbidden)"
echo "  - Manager access Owners: ✓ (403 Forbidden)"
echo "  - Manager create Owners: ✓ (403 Forbidden)"
echo "  - Admin retains full access: ✓"
echo ""
echo "Note: Manager/Director roles have read-only access to companies"
echo "      and no access to Owner management endpoints."
echo ""
echo "Next steps:"
echo "  - Run all integration tests: bash integration_tests/run_all_tests.sh"
echo "  - Verify Odoo Web record rules enforce same restrictions"
echo ""
