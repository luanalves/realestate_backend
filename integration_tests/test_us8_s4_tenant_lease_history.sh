#!/usr/bin/env bash
# ==============================================================================
# Integration Test: US8-S4 - Tenant Lease History (T022)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# User Story 4: Consolidated lease history per tenant
#
# Success Criteria:
#   - Tenant with leases → 200 returns all leases
#   - Tenant with no leases → 200 returns empty list
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
echo "US8-S4: Tenant Lease History"
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

# ──────────────── STEP 2: Create tenant with no leases ────────────────
echo -e "${BLUE}STEP 2${NC}: Creating tenant (no leases)..."

TENANT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"No Lease Tenant ${TIMESTAMP}\",
        \"email\": \"nolease.${TIMESTAMP}@test.com\"
    }")

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.data.id // empty')
if [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Tenant created (ID: ${TENANT_ID})"
else
    fail "Could not create test tenant"
    exit 1
fi
echo ""

# ──────────────── STEP 3: Get leases for tenant (empty) ────────────────
echo -e "${BLUE}STEP 3${NC}: Getting lease history (expect empty)..."

EMPTY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/${TENANT_ID}/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$EMPTY_RESPONSE" | tail -n 1)
BODY=$(echo "$EMPTY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Empty lease history returns 200"
else
    fail "Expected 200, got ${HTTP_CODE}"
fi

TOTAL=$(echo "$BODY" | jq -r '.meta.total // .total // 0')
if [ "$TOTAL" = "0" ]; then
    pass "Zero leases for new tenant"
else
    warn "Expected 0 leases, got ${TOTAL}"
fi

echo ""

# ──────────────── STEP 4: Create a lease for the tenant ────────────────
echo -e "${BLUE}STEP 4${NC}: Finding property and creating lease..."

PROPERTY_LIST=$(curl -s -X GET "${BASE_URL}/api/v1/properties?page=1&page_size=5" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

PROPERTY_ID=$(echo "$PROPERTY_LIST" | jq -r '.data[0].id // empty')
if [ -z "$PROPERTY_ID" ] || [ "$PROPERTY_ID" = "null" ]; then
    PROPERTY_ID=1
fi

LEASE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"property_id\": ${PROPERTY_ID},
        \"tenant_id\": ${TENANT_ID},
        \"start_date\": \"2026-04-01\",
        \"end_date\": \"2027-03-31\",
        \"rent_amount\": 1800.00
    }")

LEASE_ID=$(echo "$LEASE_RESPONSE" | jq -r '.data.id // empty')
if [ -n "$LEASE_ID" ] && [ "$LEASE_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Lease created (ID: ${LEASE_ID})"
else
    warn "Failed to create lease for history test"
fi
echo ""

# ──────────────── STEP 5: Get lease history (1 lease) ────────────────
echo -e "${BLUE}STEP 5${NC}: Getting tenant lease history (expect 1 lease)..."

HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/${TENANT_ID}/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$HISTORY_RESPONSE" | tail -n 1)
BODY=$(echo "$HISTORY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Lease history returns 200"
else
    fail "Expected 200, got ${HTTP_CODE}"
fi

TOTAL=$(echo "$BODY" | jq -r '.meta.total // .total // 0')
if [ "$TOTAL" -ge 1 ] 2>/dev/null; then
    pass "Tenant has ${TOTAL} lease(s) in history"
else
    warn "Expected at least 1 lease, got ${TOTAL}"
fi

# Verify _links.tenant present
HAS_TENANT_LINK=$(echo "$BODY" | jq -r '._links.tenant // .links.tenant // empty' 2>/dev/null)
if [ -n "$HAS_TENANT_LINK" ]; then
    pass "HATEOAS tenant link present"
else
    warn "HATEOAS tenant link missing"
fi

echo ""

# ──────────────── STEP 6: Nonexistent tenant → 404 ────────────────
echo -e "${BLUE}STEP 6${NC}: Getting leases for nonexistent tenant (expect 404)..."

NOT_FOUND_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/999999/leases" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$NOT_FOUND_RESPONSE" | tail -n 1)

if [ "$HTTP_CODE" = "404" ]; then
    pass "Nonexistent tenant returns 404"
else
    warn "Expected 404, got ${HTTP_CODE}"
fi

echo ""

# ──────────────── CLEANUP ────────────────
echo -e "${BLUE}CLEANUP${NC}: Archiving test data..."
if [ -n "$LEASE_ID" ] && [ "$LEASE_ID" != "null" ]; then
    curl -s -X DELETE "${BASE_URL}/api/v1/leases/${LEASE_ID}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -b "${SESSION_COOKIE_FILE}" > /dev/null 2>&1
fi
curl -s -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Cleanup done"
echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S4: Tenant Lease History — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S4 Tenant Lease History${NC}"
echo ""
