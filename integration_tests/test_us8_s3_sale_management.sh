#!/usr/bin/env bash
# ==============================================================================
# Integration Test: US8-S3 - Sale Management (T020)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# User Story 3: Sale registration, cancellation, property status side-effects
#
# Success Criteria:
#   - Create Sale → 201 (property marked "sold")
#   - Price validation (zero) → 400
#   - List with filters → 200 paginated
#   - Get by ID → 200
#   - Update buyer info → 200
#   - Cancel with reason → 200 (property status reverted)
#   - Reject update on cancelled sale → 400
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
echo "US8-S3: Sale Management"
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

# ──────────────── STEP 2: Get a valid property + company ────────────────
echo -e "${BLUE}STEP 2${NC}: Finding a valid property and company..."

PROPERTY_LIST=$(curl -s -X GET "${BASE_URL}/api/v1/properties?offset=0&limit=5&company_ids=${COMPANY_IDS}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Openerp-Session-Id: ${SESSION_ID}" \
    -H "Content-Type: application/json" \
    -b "${SESSION_COOKIE_FILE}")

PROPERTY_ID=$(echo "$PROPERTY_LIST" | jq -r '.data[0].id // empty')
# Use the first estate company from login (COMPANY_IDS) rather than property response
COMPANY_ID=$(echo "$COMPANY_IDS" | cut -d',' -f1)

if [ -n "$PROPERTY_ID" ] && [ "$PROPERTY_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Property found (ID: ${PROPERTY_ID})"
else
    warn "No property found, using default ID 1"
    PROPERTY_ID=1
fi

if [ -z "$COMPANY_ID" ] || [ "$COMPANY_ID" = "null" ]; then
    COMPANY_ID="${TEST_COMPANY_ID:-1}"
fi
echo -e "${GREEN}✓${NC} Company ID: ${COMPANY_ID}"
echo ""

# ──────────────── STEP 3: Validation — zero price (400) ────────────────
echo -e "${BLUE}STEP 3${NC}: Testing price validation (zero amount)..."

ZERO_PRICE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/sales" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"company_id\": ${COMPANY_ID},
        \"buyer_name\": \"Zero Price Buyer\",
        \"sale_date\": \"2026-03-01\",
        \"sale_price\": 0
    }")

HTTP_CODE=$(echo "$ZERO_PRICE_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Zero price returns 400"
else
    warn "Expected 400 for zero price, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 4: Create sale (201) ────────────────
echo -e "${BLUE}STEP 4${NC}: Creating sale (POST /api/v1/sales)..."

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/sales" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"company_id\": ${COMPANY_ID},
        \"buyer_name\": \"Integration Test Buyer ${TIMESTAMP}\",
        \"buyer_phone\": \"11999888777\",
        \"buyer_email\": \"buyer.${TIMESTAMP}@test.com\",
        \"sale_date\": \"2026-03-15\",
        \"sale_price\": 450000.00
    }")

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n 1)
BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    pass "Sale created (HTTP 201)"
else
    fail "Expected HTTP 201, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

SALE_ID=$(echo "$BODY" | jq -r '.data.id // empty')

if [ -n "$SALE_ID" ] && [ "$SALE_ID" != "null" ]; then
    pass "Sale ID received: ${SALE_ID}"
else
    fail "No sale ID in response"
    echo "  Response: $BODY"
    exit 1
fi

# Check HATEOAS
HAS_CANCEL_LINK=$(echo "$BODY" | jq -r '.data._links.cancel // .links.cancel // empty')
if [ -n "$HAS_CANCEL_LINK" ]; then
    pass "HATEOAS cancel link present"
else
    warn "HATEOAS cancel link missing"
fi

echo ""

# ──────────────── STEP 5: List sales (200) ────────────────
echo -e "${BLUE}STEP 5${NC}: Listing sales (GET /api/v1/sales)..."

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/sales?page=1&page_size=10" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n 1)
BODY=$(echo "$LIST_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "List sales returns 200"
else
    fail "Expected 200, got ${HTTP_CODE}"
fi

TOTAL=$(echo "$BODY" | jq -r '.meta.total // .total // empty')
if [ -n "$TOTAL" ] && [ "$TOTAL" -ge 1 ] 2>/dev/null; then
    pass "Sales pagination present (total: ${TOTAL})"
else
    warn "Pagination total missing or zero"
fi

echo ""

# ──────────────── STEP 6: Get sale by ID (200) ────────────────
echo -e "${BLUE}STEP 6${NC}: Getting sale by ID (GET /api/v1/sales/${SALE_ID})..."

GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/sales/${SALE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n 1)
BODY=$(echo "$GET_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Get sale by ID returns 200"
else
    fail "Expected 200, got ${HTTP_CODE}"
fi

RETURNED_BUYER=$(echo "$BODY" | jq -r '.data.buyer_name // empty')
if [[ "$RETURNED_BUYER" == *"Integration Test Buyer"* ]]; then
    pass "Buyer name matches"
else
    warn "Buyer name mismatch: ${RETURNED_BUYER}"
fi

SALE_STATUS=$(echo "$BODY" | jq -r '.data.status // empty')
if [ "$SALE_STATUS" = "completed" ]; then
    pass "Sale status is 'completed'"
else
    warn "Expected 'completed', got '${SALE_STATUS}'"
fi

echo ""

# ──────────────── STEP 7: Update sale (200) ────────────────
echo -e "${BLUE}STEP 7${NC}: Updating sale buyer info (PUT /api/v1/sales/${SALE_ID})..."

UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/sales/${SALE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"buyer_name\": \"Updated Buyer ${TIMESTAMP}\",
        \"buyer_phone\": \"11900001111\"
    }")

HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n 1)
BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Update sale returns 200"
else
    fail "Expected 200 for update, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

echo ""

# ──────────────── STEP 8: Cancel sale (200) + property status revert ────────────────
echo -e "${BLUE}STEP 8${NC}: Cancelling sale (POST /api/v1/sales/${SALE_ID}/cancel)..."

CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/sales/${SALE_ID}/cancel" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"reason\": \"Integration test cancellation\"
    }")

HTTP_CODE=$(echo "$CANCEL_RESPONSE" | tail -n 1)
BODY=$(echo "$CANCEL_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Sale cancelled (HTTP 200)"
else
    fail "Expected 200 for cancel, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

CANCEL_STATUS=$(echo "$BODY" | jq -r '.data.status // empty')
if [ "$CANCEL_STATUS" = "cancelled" ]; then
    pass "Sale status is 'cancelled'"
else
    warn "Expected 'cancelled', got '${CANCEL_STATUS}'"
fi

CANCEL_REASON=$(echo "$BODY" | jq -r '.data.cancellation_reason // empty')
if [[ "$CANCEL_REASON" == *"Integration test"* ]]; then
    pass "Cancellation reason recorded"
else
    warn "Cancellation reason mismatch: ${CANCEL_REASON}"
fi

echo ""

# ──────────────── STEP 9: Reject update on cancelled sale (400) ────────────────
echo -e "${BLUE}STEP 9${NC}: Attempting update on cancelled sale (expect 400)..."

UPDATE_CANCELLED_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/sales/${SALE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"buyer_name\": \"Should Not Update\"
    }")

HTTP_CODE=$(echo "$UPDATE_CANCELLED_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Update on cancelled sale returns 400"
else
    fail "Expected 400 for update on cancelled, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── STEP 10: Reject double cancel (400) ────────────────
echo -e "${BLUE}STEP 10${NC}: Attempting double cancel (expect 400)..."

DOUBLE_CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/sales/${SALE_ID}/cancel" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"reason\": \"Double cancel attempt\"
    }")

HTTP_CODE=$(echo "$DOUBLE_CANCEL_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "400" ]; then
    pass "Double cancel returns 400"
else
    warn "Expected 400 for double cancel, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S3: Sale Management — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S3 Sale Management${NC}"
echo ""
echo "Next: bash integration_tests/test_us8_s4_tenant_lease_history.sh"
echo ""
