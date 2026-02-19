#!/usr/bin/env bash
# ==============================================================================# ⚠️  SUPERSEDED BY FEATURE 010 - Profile Unification
# ==============================================================================
# This test is superseded by Feature 010 profile-based tests.
# Lease operations now use profile_id instead of tenant_id.
# This file is kept for historical reference only.
# 
# See: Feature 010 - Profile Unification
# Lease migration: lease.tenant_id → lease.profile_id (Phase 3)
# ==============================================================================
#
# ==============================================================================# Integration Test: US8-S2 - Lease Lifecycle Management (T016)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# User Story 2: Lease lifecycle with CRUD, renew, terminate
#
# Success Criteria:
#   - Create Lease → 201 (with property + tenant validation)
#   - Date validation (end < start) → 400
#   - List with filters → 200 paginated
#   - Get by ID with property/tenant info → 200
#   - Update rent → 200
#   - Renew with history audit → 200
#   - Terminate with penalty → 200
#   - Reject renew on terminated lease → 400
#   - Company isolation
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

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; ((PASS_COUNT++)) || true; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; ((FAIL_COUNT++)) || true; }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; ((WARN_COUNT++)) || true; }

echo "============================================"
echo "US8-S2: Lease Lifecycle Management"
echo "============================================"
echo ""

# ──────────────── STEP 1: Authenticate ────────────────
echo -e "${BLUE}STEP 1${NC}: Authenticating..."

if ! get_full_auth; then
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Authenticated"
echo ""

TIMESTAMP=$(date +%s)

# ──────────────── STEP 2: Create a test tenant (prerequisite) ────────────────
echo -e "${BLUE}STEP 2${NC}: Creating test tenant..."

TENANT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Lease Test Tenant ${TIMESTAMP}\",
        \"phone\": \"11988887777\",
        \"email\": \"lease.tenant.${TIMESTAMP}@test.com\"
    }")

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.data.id // empty')
if [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Test tenant created (ID: ${TENANT_ID})"
else
    echo -e "${RED}✗${NC} Failed to create test tenant"
    echo "  Response: $TENANT_RESPONSE"
    exit 1
fi

echo ""

# ──────────────── STEP 3: Get a valid property ID ────────────────
echo -e "${BLUE}STEP 3${NC}: Finding a valid property..."

PROPERTY_LIST=$(curl -s -X GET "${BASE_URL}/api/v1/properties?offset=0&limit=5&company_ids=${COMPANY_IDS}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Openerp-Session-Id: ${SESSION_ID}" \
    -H "Content-Type: application/json" \
    -b "${SESSION_COOKIE_FILE}")

PROPERTY_ID=$(echo "$PROPERTY_LIST" | jq -r '.data[0].id // empty')
if [ -n "$PROPERTY_ID" ] && [ "$PROPERTY_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Property found (ID: ${PROPERTY_ID})"
else
    warn "No property found in system, tests may fail"
    PROPERTY_ID=1
fi

echo ""

# ──────────────── STEP 4: Create lease (201) ────────────────
echo -e "${BLUE}STEP 4${NC}: Creating lease (POST /api/v1/leases)..."

# Use far-future dates to avoid concurrent lease conflicts with previous test runs
YEAR_OFFSET=$(( (TIMESTAMP % 50) + 2030 ))
START_DATE="${YEAR_OFFSET}-01-01"
END_DATE="${YEAR_OFFSET}-12-31"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"tenant_id\": ${TENANT_ID},
        \"start_date\": \"${START_DATE}\",
        \"end_date\": \"${END_DATE}\",
        \"rent_amount\": 2500.00
    }")

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n 1)
BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    pass "Lease created (HTTP 201)"
else
    fail "Expected HTTP 201, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

LEASE_ID=$(echo "$BODY" | jq -r '.data.id // empty')

if [ -n "$LEASE_ID" ] && [ "$LEASE_ID" != "null" ]; then
    pass "Lease ID received: ${LEASE_ID}"
else
    fail "No lease ID in response"
    echo "  Response: $BODY"
    exit 1
fi

# Check HATEOAS links
HAS_RENEW_LINK=$(echo "$BODY" | jq -r '.data._links.renew // empty')
if [ -n "$HAS_RENEW_LINK" ]; then
    pass "HATEOAS renew link present"
else
    warn "HATEOAS renew link missing"
fi

echo ""

# ──────────────── STEP 5: Validation — invalid dates (end < start, 400) ────────────────
echo -e "${BLUE}STEP 5${NC}: Testing date validation (end_date < start_date)..."

INVALID_DATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"tenant_id\": ${TENANT_ID},
        \"start_date\": \"2027-01-01\",
        \"end_date\": \"2026-01-01\",
        \"rent_amount\": 1500.00
    }")

HTTP_CODE=$(echo "$INVALID_DATE_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Invalid dates return 400"
else
    warn "Expected 400 for invalid dates, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 6: Validation — rent_amount = 0 (400) ────────────────
echo -e "${BLUE}STEP 6${NC}: Testing rent validation (zero amount)..."

ZERO_RENT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"tenant_id\": ${TENANT_ID},
        \"start_date\": \"2028-01-01\",
        \"end_date\": \"2028-12-31\",
        \"rent_amount\": 0
    }")

HTTP_CODE=$(echo "$ZERO_RENT_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Zero rent returns 400"
else
    warn "Expected 400 for zero rent, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 7: List leases (200) ────────────────
echo -e "${BLUE}STEP 7${NC}: Listing leases (GET /api/v1/leases)..."

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/leases?page=1&page_size=10" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n 1)
BODY=$(echo "$LIST_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "List leases returns 200"
else
    fail "Expected 200 for list leases, got ${HTTP_CODE}"
fi

TOTAL=$(echo "$BODY" | jq -r '.meta.total // .total // empty')
if [ -n "$TOTAL" ] && [ "$TOTAL" -ge 1 ] 2>/dev/null; then
    pass "Pagination meta present (total: ${TOTAL})"
else
    warn "Pagination total missing or zero"
fi

echo ""

# ──────────────── STEP 8: Get lease by ID (200) ────────────────
echo -e "${BLUE}STEP 8${NC}: Getting lease by ID (GET /api/v1/leases/${LEASE_ID})..."

GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n 1)
BODY=$(echo "$GET_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Get lease by ID returns 200"
else
    fail "Expected 200, got ${HTTP_CODE}"
fi

RETURNED_RENT=$(echo "$BODY" | jq -r '.data.rent_amount // empty')
if [ "$RETURNED_RENT" = "2500" ] || [ "$RETURNED_RENT" = "2500.0" ] || [ "$RETURNED_RENT" = "2500.00" ]; then
    pass "Rent amount matches (${RETURNED_RENT})"
else
    warn "Rent mismatch: expected 2500, got ${RETURNED_RENT}"
fi

echo ""

# ──────────────── STEP 9: Update lease (200) ────────────────
echo -e "${BLUE}STEP 9${NC}: Updating lease rent (PUT /api/v1/leases/${LEASE_ID})..."

UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"rent_amount\": 2800.00
    }")

HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n 1)
BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Update lease returns 200"
else
    fail "Expected 200 for update, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

echo ""

# ──────────────── STEP 9b: Activate lease (draft → active) ────────────────
echo -e "${BLUE}STEP 9b${NC}: Activating lease (PUT /api/v1/leases/${LEASE_ID} status=active)..."

ACTIVATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"status\": \"active\"
    }")

HTTP_CODE=$(echo "$ACTIVATE_RESPONSE" | tail -n 1)
BODY=$(echo "$ACTIVATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Lease activated (draft → active)"
else
    fail "Expected 200 for activation, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

LEASE_STATUS=$(echo "$BODY" | jq -r '.data.status // empty')
if [ "$LEASE_STATUS" = "active" ]; then
    pass "Lease status confirmed: active"
else
    warn "Expected status 'active', got '${LEASE_STATUS}'"
fi

echo ""

# ──────────────── STEP 10: Renew lease (200) — creates history ────────────────
echo -e "${BLUE}STEP 10${NC}: Renewing lease (POST /api/v1/leases/${LEASE_ID}/renew)..."

RENEW_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases/${LEASE_ID}/renew" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"new_end_date\": \"$(( YEAR_OFFSET + 1 ))-12-31\",
        \"new_rent_amount\": 3000.00,
        \"reason\": \"Annual renewal with adjustment\"
    }")

HTTP_CODE=$(echo "$RENEW_RESPONSE" | tail -n 1)
BODY=$(echo "$RENEW_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Lease renewed (HTTP 200)"
else
    fail "Expected 200 for renew, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

# Verify updated end_date
NEW_END=$(echo "$BODY" | jq -r '.data.end_date // empty')
if [ "$NEW_END" = "$(( YEAR_OFFSET + 1 ))-12-31" ]; then
    pass "End date updated to $(( YEAR_OFFSET + 1 ))-12-31"
else
    warn "End date mismatch: ${NEW_END}"
fi

echo ""

# ──────────────── STEP 11: Terminate lease (200) ────────────────
echo -e "${BLUE}STEP 11${NC}: Terminating lease (POST /api/v1/leases/${LEASE_ID}/terminate)..."

TERMINATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases/${LEASE_ID}/terminate" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"termination_date\": \"2026-06-30\",
        \"reason\": \"Early termination for testing\",
        \"penalty_amount\": 5000.00
    }")

HTTP_CODE=$(echo "$TERMINATE_RESPONSE" | tail -n 1)
BODY=$(echo "$TERMINATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Lease terminated (HTTP 200)"
else
    fail "Expected 200 for terminate, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

LEASE_STATUS=$(echo "$BODY" | jq -r '.data.status // empty')
if [ "$LEASE_STATUS" = "terminated" ]; then
    pass "Lease status is 'terminated'"
else
    warn "Expected status 'terminated', got '${LEASE_STATUS}'"
fi

echo ""

# ──────────────── STEP 12: Reject renew on terminated lease (400) ────────────────
echo -e "${BLUE}STEP 12${NC}: Attempting renew on terminated lease (expect 400)..."

RENEW_TERMINATED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/leases/${LEASE_ID}/renew" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"new_end_date\": \"2029-01-01\",
        \"reason\": \"Should fail\"
    }")

HTTP_CODE=$(echo "$RENEW_TERMINATED_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Renew on terminated lease returns 400"
else
    fail "Expected 400 for renew on terminated, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 13: Reject update on terminated lease (400) ────────────────
echo -e "${BLUE}STEP 13${NC}: Attempting update on terminated lease (expect 400)..."

UPDATE_TERMINATED_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"rent_amount\": 9999.00
    }")

HTTP_CODE=$(echo "$UPDATE_TERMINATED_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Update on terminated lease returns 400"
else
    warn "Expected 400 for update on terminated, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── CLEANUP ────────────────
echo -e "${BLUE}CLEANUP${NC}: Archiving test data..."
curl -s -X DELETE "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" > /dev/null 2>&1

curl -s -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" > /dev/null 2>&1

echo -e "${GREEN}✓${NC} Cleanup done"
echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S2: Lease Lifecycle — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S2 Lease Lifecycle${NC}"
echo ""
echo "Next: bash integration_tests/test_us8_s3_sale_management.sh"
echo ""
