#!/usr/bin/env bash
# ==============================================================================
# Integration Test: US8-S1 - Tenant CRUD Operations (T010)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# User Story 1: Tenant CRUD management with company isolation + RBAC
#
# Success Criteria:
#   - Create Tenant → 201 with HATEOAS links
#   - List with company filter → 200 paginated
#   - Get by ID → 200 with full tenant data
#   - Update phone/email → 200
#   - Archive (DELETE) → 200 soft-delete
#   - Archived hidden from default list
#   - Validation errors (missing name, invalid email) → 400
# ==============================================================================

set -e

# Load helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
source "${SCRIPT_DIR}/lib/get_auth_headers.sh"

# Load .env
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    set -a
    source "$SCRIPT_DIR/../18.0/.env"
    set +a
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
DB_NAME="${POSTGRES_DB:-realestate}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; ((PASS_COUNT++)); }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; ((FAIL_COUNT++)); }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; ((WARN_COUNT++)); }

echo "============================================"
echo "US8-S1: Tenant CRUD Operations"
echo "============================================"
echo ""

# ──────────────── STEP 1: Authenticate ────────────────
echo -e "${BLUE}STEP 1${NC}: Authenticating..."

if ! get_full_auth; then
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Authenticated (token: ${#ACCESS_TOKEN} chars)"
echo ""

TIMESTAMP=$(date +%s)

# ──────────────── STEP 2: Create tenant (201) ────────────────
echo -e "${BLUE}STEP 2${NC}: Creating tenant (POST /api/v1/tenants)..."

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Integration Test Tenant ${TIMESTAMP}\",
        \"phone\": \"11987654321\",
        \"email\": \"tenant.${TIMESTAMP}@test.com\",
        \"occupation\": \"Engineer\"
    }")

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n 1)
BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    pass "Tenant created (HTTP 201)"
else
    fail "Expected HTTP 201, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

TENANT_ID=$(echo "$BODY" | jq -r '.data.id // empty')

if [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ]; then
    pass "Tenant ID received: ${TENANT_ID}"
else
    fail "No tenant ID in response"
    echo "  Response: $BODY"
    exit 1
fi

# Check HATEOAS links
HAS_LINKS=$(echo "$BODY" | jq -r '.data._links.self // empty')
if [ -n "$HAS_LINKS" ]; then
    pass "HATEOAS _links present in response"
else
    warn "HATEOAS _links missing"
fi

echo ""

# ──────────────── STEP 3: Validation — missing name (400) ────────────────
echo -e "${BLUE}STEP 3${NC}: Testing validation — missing name..."

VALIDATION_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"phone\": \"11999999999\"
    }")

HTTP_CODE=$(echo "$VALIDATION_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Missing name returns 400"
else
    fail "Expected HTTP 400 for missing name, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 4: Validation — invalid email (400) ────────────────
echo -e "${BLUE}STEP 4${NC}: Testing validation — invalid email..."

INVALID_EMAIL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Bad Email Tenant\",
        \"email\": \"not-an-email\"
    }")

HTTP_CODE=$(echo "$INVALID_EMAIL_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Invalid email returns 400"
else
    warn "Expected HTTP 400 for invalid email, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 5: List tenants (200) ────────────────
echo -e "${BLUE}STEP 5${NC}: Listing tenants (GET /api/v1/tenants)..."

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=10" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n 1)
BODY=$(echo "$LIST_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "List tenants returns 200"
else
    fail "Expected HTTP 200 for list, got ${HTTP_CODE}"
fi

TOTAL=$(echo "$BODY" | jq -r '.meta.total // .total // empty')
if [ -n "$TOTAL" ] && [ "$TOTAL" -ge 1 ] 2>/dev/null; then
    pass "Pagination meta present (total: ${TOTAL})"
else
    warn "Pagination total missing or zero"
fi

echo ""

# ──────────────── STEP 6: Get tenant by ID (200) ────────────────
echo -e "${BLUE}STEP 6${NC}: Getting tenant by ID (GET /api/v1/tenants/${TENANT_ID})..."

GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n 1)
BODY=$(echo "$GET_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Get tenant by ID returns 200"
else
    fail "Expected HTTP 200, got ${HTTP_CODE}"
fi

RETURNED_NAME=$(echo "$BODY" | jq -r '.data.name // empty')
if [[ "$RETURNED_NAME" == *"Integration Test Tenant"* ]]; then
    pass "Tenant name matches"
else
    warn "Tenant name mismatch: ${RETURNED_NAME}"
fi

echo ""

# ──────────────── STEP 7: Update tenant (200) ────────────────
echo -e "${BLUE}STEP 7${NC}: Updating tenant (PUT /api/v1/tenants/${TENANT_ID})..."

UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"phone\": \"11900001111\",
        \"email\": \"updated.${TIMESTAMP}@test.com\"
    }")

HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n 1)
BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Update tenant returns 200"
else
    fail "Expected HTTP 200 for update, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

UPDATED_PHONE=$(echo "$BODY" | jq -r '.data.phone // empty')
if [ "$UPDATED_PHONE" = "11900001111" ]; then
    pass "Phone updated correctly"
else
    warn "Phone not updated: ${UPDATED_PHONE}"
fi

echo ""

# ──────────────── STEP 8: Archive tenant (DELETE → 200) ────────────────
echo -e "${BLUE}STEP 8${NC}: Archiving tenant (DELETE /api/v1/tenants/${TENANT_ID})..."

DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    pass "Archive tenant returns ${HTTP_CODE}"
else
    fail "Expected HTTP 200/204 for archive, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 9: Verify archived hidden from default list ────────────────
echo -e "${BLUE}STEP 9${NC}: Verifying archived tenant hidden from default list..."

LIST_AFTER_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=100" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

FOUND_ARCHIVED=$(echo "$LIST_AFTER_RESPONSE" | jq -r ".data[] | select(.id == ${TENANT_ID}) | .id // empty" 2>/dev/null)
if [ -z "$FOUND_ARCHIVED" ]; then
    pass "Archived tenant hidden from default list"
else
    fail "Archived tenant still visible in default list"
fi

echo ""

# ──────────────── STEP 10: Get archived tenant → 404 ────────────────
echo -e "${BLUE}STEP 10${NC}: Verifying GET archived tenant returns 404..."

GET_ARCHIVED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$GET_ARCHIVED_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "404" ]; then
    pass "Archived tenant returns 404 on GET"
else
    warn "Expected 404 for archived tenant GET, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S1: Tenant CRUD — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S1 Tenant CRUD${NC}"
echo ""
echo "Next: bash integration_tests/test_us8_s2_lease_lifecycle.sh"
echo ""
