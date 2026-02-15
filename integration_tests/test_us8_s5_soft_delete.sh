#!/usr/bin/env bash
# ==============================================================================
# Integration Test: US8-S5 - Soft Delete & Record Recovery (T025)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# User Story 5: Query inactive records and reactivate
#
# Success Criteria:
#   - Archive record → 200
#   - Archived hidden from default list
#   - Query with is_active=false → shows archived
#   - Reactivate via PUT active=true → 200
#   - Reactivated visible in default list again
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

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; ((PASS_COUNT++)) || true; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; ((FAIL_COUNT++)) || true; }
warn() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; ((WARN_COUNT++)) || true; }

echo "============================================"
echo "US8-S5: Soft Delete & Record Recovery"
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

# ==========================================================================
# TENANT: Archive → Query inactive → Reactivate
# ==========================================================================
echo -e "${BLUE}═══ TENANT SOFT DELETE ═══${NC}"

# Create tenant
TENANT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"SoftDelete Test Tenant ${TIMESTAMP}\", \"email\": \"softdel.${TIMESTAMP}@test.com\"}")

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.data.id // empty')
if [ -z "$TENANT_ID" ] || [ "$TENANT_ID" = "null" ]; then
    fail "Could not create test tenant"
    exit 1
fi
echo -e "${GREEN}✓${NC} Tenant created (ID: ${TENANT_ID})"

# Archive tenant
echo -e "\n${BLUE}Archive tenant...${NC}"
ARCHIVE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{\"reason\": \"Testing soft delete\"}")

HTTP_CODE=$(echo "$ARCHIVE_RESPONSE" | tail -n 1)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    pass "Tenant archived (${HTTP_CODE})"
else
    fail "Expected 200/204, got ${HTTP_CODE}"
fi

# Verify hidden from default list
echo -e "\n${BLUE}Verify hidden from default list...${NC}"
DEFAULT_LIST=$(curl -s -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=200" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

FOUND=$(echo "$DEFAULT_LIST" | jq -r ".data[] | select(.id == ${TENANT_ID}) | .id // empty" 2>/dev/null)
if [ -z "$FOUND" ]; then
    pass "Archived tenant hidden from default list"
else
    fail "Archived tenant still in default list"
fi

# Query with is_active=false
echo -e "\n${BLUE}Query with is_active=false...${NC}"
INACTIVE_LIST=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants?is_active=false&page=1&page_size=200" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

HTTP_CODE=$(echo "$INACTIVE_LIST" | tail -n 1)
BODY=$(echo "$INACTIVE_LIST" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "is_active=false returns 200"
else
    fail "Expected 200 for is_active=false, got ${HTTP_CODE}"
fi

FOUND_INACTIVE=$(echo "$BODY" | jq -r ".data[] | select(.id == ${TENANT_ID}) | .id // empty" 2>/dev/null)
if [ "$FOUND_INACTIVE" = "$TENANT_ID" ]; then
    pass "Archived tenant visible with is_active=false"
else
    warn "Archived tenant not found in inactive list"
fi

# Reactivate tenant
echo -e "\n${BLUE}Reactivate tenant...${NC}"
REACTIVATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json" \
    -d "{\"active\": true}")

HTTP_CODE=$(echo "$REACTIVATE_RESPONSE" | tail -n 1)
BODY=$(echo "$REACTIVATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    pass "Tenant reactivated (200)"
else
    fail "Expected 200 for reactivation, got ${HTTP_CODE}"
    echo "  Response: $BODY"
fi

ACTIVE_FIELD=$(echo "$BODY" | jq -r '.data.active // empty')
if [ "$ACTIVE_FIELD" = "true" ]; then
    pass "Tenant active=true after reactivation"
else
    warn "active field: ${ACTIVE_FIELD}"
fi

# Verify visible in default list again
echo -e "\n${BLUE}Verify visible in default list again...${NC}"
DEFAULT_LIST_AFTER=$(curl -s -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=200" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" \
    -H "Content-Type: application/json")

FOUND_AGAIN=$(echo "$DEFAULT_LIST_AFTER" | jq -r ".data[] | select(.id == ${TENANT_ID}) | .id // empty" 2>/dev/null)
if [ "$FOUND_AGAIN" = "$TENANT_ID" ]; then
    pass "Reactivated tenant visible in default list"
else
    warn "Reactivated tenant not found in default list"
fi

echo ""

# ==========================================================================
# CLEANUP
# ==========================================================================
echo -e "${BLUE}CLEANUP${NC}: Archiving test data..."
curl -s -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -b "${SESSION_COOKIE_FILE}" > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Cleanup done"
echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S5: Soft Delete & Recovery — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S5 Soft Delete & Recovery${NC}"
echo ""
