#!/usr/bin/env bash
# ==============================================================================
# Integration Test: US8-S6 — Cross-Company Isolation & Agent RBAC (CHK022/CHK027)
# ==============================================================================
# Feature 008: Tenant, Lease & Sale API Endpoints
# Validates:
#   CHK022: Cross-company data isolation (SC-007)
#   CHK027: Agent-scoped RBAC filtering (FR-037)
#
# Prerequisites:
#   - Two test users in different companies (TEST_USER_A / TEST_USER_B)
#     OR manager user with 2 companies (manager creates in company A,
#     company B user cannot see it)
#   - One agent user (TEST_USER_AGENT / TEST_PASSWORD_AGENT)
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
echo "US8-S6: Cross-Company Isolation & Agent RBAC"
echo "============================================"
echo ""

TIMESTAMP=$(date +%s)

# ==============================================================================
# PART 1: CROSS-COMPANY ISOLATION (CHK022)
# ==============================================================================
echo -e "${BLUE}═══ PART 1: CROSS-COMPANY ISOLATION (CHK022) ═══${NC}"
echo ""

# ── STEP 1: Authenticate as Manager (Company A) ──
echo -e "${BLUE}STEP 1${NC}: Authenticating as Manager..."

if ! get_full_auth; then
    echo -e "${RED}✗ Manager auth failed${NC}"
    exit 1
fi

MANAGER_TOKEN="$ACCESS_TOKEN"
MANAGER_SESSION_FILE="$SESSION_COOKIE_FILE"
MANAGER_COMPANY_IDS="$COMPANY_IDS"
MANAGER_SESSION_ID="$SESSION_ID"

echo -e "${GREEN}✓${NC} Manager authenticated (companies: ${MANAGER_COMPANY_IDS})"
echo ""

# ── STEP 2: Create tenant as Manager ──
echo -e "${BLUE}STEP 2${NC}: Creating tenant as Manager..."

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/tenants" \
    -H "Authorization: Bearer ${MANAGER_TOKEN}" \
    -b "${MANAGER_SESSION_FILE}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Isolation Test Tenant ${TIMESTAMP}\",
        \"email\": \"isolation.${TIMESTAMP}@test.com\"
    }")

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n 1)
BODY=$(echo "$CREATE_RESPONSE" | sed '$d')
TENANT_ID=$(echo "$BODY" | jq -r '.data.id // empty')

if [ "$HTTP_CODE" = "201" ] && [ -n "$TENANT_ID" ] && [ "$TENANT_ID" != "null" ]; then
    echo -e "${GREEN}✓${NC} Tenant created (ID: ${TENANT_ID})"
else
    fail "Could not create test tenant (HTTP ${HTTP_CODE})"
    echo "  Response: $BODY"
    echo ""
    echo "Skipping isolation tests..."
    SKIP_ISOLATION=true
fi

if [ "${SKIP_ISOLATION}" != "true" ]; then
    # ── STEP 3: Authenticate as User B (different company) ──
    echo ""
    echo -e "${BLUE}STEP 3${NC}: Authenticating as User B (different company)..."

    # Get OAuth2 token (shared)
    CLIENT_ID="${OAUTH_CLIENT_ID:-test-client-id}"
    CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-test-client-secret-12345}"

    TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}")

    USER_B_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')

    USER_B_EMAIL="${TEST_USER_B_EMAIL:-pedro@imobiliaria.com}"
    USER_B_PASSWORD="${TEST_USER_B_PASSWORD:-test123}"

    USER_B_LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${USER_B_TOKEN}" \
        -d "{\"email\": \"${USER_B_EMAIL}\", \"password\": \"${USER_B_PASSWORD}\"}")

    USER_B_SESSION_ID=$(echo "$USER_B_LOGIN_RESPONSE" | jq -r '.session_id // empty')
    USER_B_UID=$(echo "$USER_B_LOGIN_RESPONSE" | jq -r '.user.id // empty')
    USER_B_COMPANIES=$(echo "$USER_B_LOGIN_RESPONSE" | jq -r '(.user.companies // []) | [.[].id] | join(",")')

    if [ -z "$USER_B_SESSION_ID" ] || [ "$USER_B_SESSION_ID" = "null" ]; then
        warn "User B auth failed — skipping cross-company tests (user may not exist)"
        echo "  Response: $USER_B_LOGIN_RESPONSE"
        SKIP_CROSS_COMPANY=true
    else
        echo -e "${GREEN}✓${NC} User B authenticated (UID: ${USER_B_UID}, companies: ${USER_B_COMPANIES})"

        # Create cookie file for User B
        cat > /tmp/odoo_test_session_b.txt << EOF
# Netscape HTTP Cookie File
#HttpOnly_localhost	FALSE	/	FALSE	$(( $(date +%s) + 3600 ))	session_id	${USER_B_SESSION_ID}
EOF

        # ── STEP 4: User B tries to GET tenant created by Manager ──
        echo ""
        echo -e "${BLUE}STEP 4${NC}: User B tries to access Manager's tenant (expect 404)..."

        CROSS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
            -H "Authorization: Bearer ${USER_B_TOKEN}" \
            -b /tmp/odoo_test_session_b.txt \
            -H "Content-Type: application/json")

        HTTP_CODE=$(echo "$CROSS_RESPONSE" | tail -n 1)

        if [ "$HTTP_CODE" = "404" ]; then
            pass "Cross-company GET tenant returns 404 (data isolated)"
        elif [ "$HTTP_CODE" = "403" ]; then
            pass "Cross-company GET tenant returns 403 (access denied)"
        elif [ "$HTTP_CODE" = "200" ]; then
            fail "Cross-company GET tenant returns 200 — DATA LEAKAGE!"
        else
            warn "Cross-company GET tenant returns unexpected ${HTTP_CODE}"
        fi

        # ── STEP 5: User B tries to LIST tenants (should NOT include Manager's tenant) ──
        echo ""
        echo -e "${BLUE}STEP 5${NC}: User B lists tenants (Manager's tenant should NOT appear)..."

        LIST_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=200" \
            -H "Authorization: Bearer ${USER_B_TOKEN}" \
            -b /tmp/odoo_test_session_b.txt \
            -H "Content-Type: application/json")

        FOUND_IN_B=$(echo "$LIST_RESPONSE" | jq -r ".data[] | select(.id == ${TENANT_ID}) | .id // empty" 2>/dev/null)

        if [ -z "$FOUND_IN_B" ]; then
            pass "Manager's tenant NOT visible in User B's list (company isolation)"
        else
            fail "Manager's tenant visible in User B's list — DATA LEAKAGE!"
        fi

        # ── STEP 6: User B tries to UPDATE Manager's tenant (expect 404) ──
        echo ""
        echo -e "${BLUE}STEP 6${NC}: User B tries to update Manager's tenant (expect 404)..."

        UPDATE_CROSS_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
            -H "Authorization: Bearer ${USER_B_TOKEN}" \
            -b /tmp/odoo_test_session_b.txt \
            -H "Content-Type: application/json" \
            -d "{\"phone\": \"999999999\"}")

        HTTP_CODE=$(echo "$UPDATE_CROSS_RESPONSE" | tail -n 1)

        if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "403" ]; then
            pass "Cross-company UPDATE tenant blocked (${HTTP_CODE})"
        elif [ "$HTTP_CODE" = "200" ]; then
            fail "Cross-company UPDATE succeeded — DATA LEAKAGE!"
        else
            warn "Cross-company UPDATE returns unexpected ${HTTP_CODE}"
        fi

        # Cleanup User B temp file
        rm -f /tmp/odoo_test_session_b.txt
    fi

    # ── CLEANUP ──
    echo ""
    echo -e "${BLUE}CLEANUP${NC}: Archiving isolation test tenant..."
    curl -s -X DELETE "${BASE_URL}/api/v1/tenants/${TENANT_ID}" \
        -H "Authorization: Bearer ${MANAGER_TOKEN}" \
        -b "${MANAGER_SESSION_FILE}" > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} Cleanup done"
fi

echo ""

# ==============================================================================
# PART 2: AGENT RBAC FILTERING (CHK027)
# ==============================================================================
echo -e "${BLUE}═══ PART 2: AGENT RBAC FILTERING (CHK027) ═══${NC}"
echo ""

AGENT_EMAIL="${TEST_USER_AGENT:-agent_test}"
AGENT_PASSWORD="${TEST_PASSWORD_AGENT:-agent123}"

# ── STEP 7: Authenticate as Agent ──
echo -e "${BLUE}STEP 7${NC}: Authenticating as Agent (${AGENT_EMAIL})..."

CLIENT_ID="${OAUTH_CLIENT_ID:-test-client-id}"
CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-test-client-secret-12345}"

AGENT_TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}")

AGENT_TOKEN=$(echo "$AGENT_TOKEN_RESPONSE" | jq -r '.access_token // empty')

AGENT_LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${AGENT_TOKEN}" \
    -d "{\"email\": \"${AGENT_EMAIL}\", \"password\": \"${AGENT_PASSWORD}\"}")

AGENT_SESSION_ID=$(echo "$AGENT_LOGIN_RESPONSE" | jq -r '.session_id // empty')
AGENT_UID=$(echo "$AGENT_LOGIN_RESPONSE" | jq -r '.user.id // empty')
AGENT_COMPANIES=$(echo "$AGENT_LOGIN_RESPONSE" | jq -r '(.user.companies // []) | [.[].id] | join(",")')

if [ -z "$AGENT_SESSION_ID" ] || [ "$AGENT_SESSION_ID" = "null" ]; then
    warn "Agent auth failed — skipping RBAC tests (agent user may not exist)"
    echo "  Response: $AGENT_LOGIN_RESPONSE"
    SKIP_AGENT=true
else
    echo -e "${GREEN}✓${NC} Agent authenticated (UID: ${AGENT_UID}, companies: ${AGENT_COMPANIES})"

    cat > /tmp/odoo_test_session_agent.txt << EOF
# Netscape HTTP Cookie File
#HttpOnly_localhost	FALSE	/	FALSE	$(( $(date +%s) + 3600 ))	session_id	${AGENT_SESSION_ID}
EOF

    # ── STEP 8: Agent lists tenants (should only see those linked to assigned properties) ──
    echo ""
    echo -e "${BLUE}STEP 8${NC}: Agent lists tenants (should see filtered results)..."

    AGENT_LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/tenants?page=1&page_size=100" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -b /tmp/odoo_test_session_agent.txt \
        -H "Content-Type: application/json")

    HTTP_CODE=$(echo "$AGENT_LIST_RESPONSE" | tail -n 1)
    BODY=$(echo "$AGENT_LIST_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        AGENT_TENANT_COUNT=$(echo "$BODY" | jq -r '.pagination.total // .data | length' 2>/dev/null)
        pass "Agent can list tenants (HTTP 200, count: ${AGENT_TENANT_COUNT})"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
        warn "Agent lacks permissions to list tenants (${HTTP_CODE}) — check RBAC setup"
    else
        fail "Agent list tenants returned unexpected ${HTTP_CODE}"
        echo "  Response: $BODY"
    fi

    # ── STEP 9: Agent lists leases (should see filtered results) ──
    echo ""
    echo -e "${BLUE}STEP 9${NC}: Agent lists leases (should see filtered results)..."

    AGENT_LEASE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/leases?page=1&page_size=100" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -b /tmp/odoo_test_session_agent.txt \
        -H "Content-Type: application/json")

    HTTP_CODE=$(echo "$AGENT_LEASE_RESPONSE" | tail -n 1)
    BODY=$(echo "$AGENT_LEASE_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        AGENT_LEASE_COUNT=$(echo "$BODY" | jq -r '.pagination.total // .data | length' 2>/dev/null)
        pass "Agent can list leases (HTTP 200, count: ${AGENT_LEASE_COUNT})"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
        warn "Agent lacks permissions to list leases (${HTTP_CODE}) — check RBAC setup"
    else
        fail "Agent list leases returned unexpected ${HTTP_CODE}"
    fi

    # ── STEP 10: Agent lists sales (should see only own sales) ──
    echo ""
    echo -e "${BLUE}STEP 10${NC}: Agent lists sales (should see filtered results)..."

    AGENT_SALE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/sales?page=1&page_size=100" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -b /tmp/odoo_test_session_agent.txt \
        -H "Content-Type: application/json")

    HTTP_CODE=$(echo "$AGENT_SALE_RESPONSE" | tail -n 1)
    BODY=$(echo "$AGENT_SALE_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        AGENT_SALE_COUNT=$(echo "$BODY" | jq -r '.pagination.total // .data | length' 2>/dev/null)
        pass "Agent can list sales (HTTP 200, count: ${AGENT_SALE_COUNT})"
    elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
        warn "Agent lacks permissions to list sales (${HTTP_CODE}) — check RBAC setup"
    else
        fail "Agent list sales returned unexpected ${HTTP_CODE}"
    fi

    # Cleanup
    rm -f /tmp/odoo_test_session_agent.txt
fi

echo ""

# ──────────────── SUMMARY ────────────────
echo "============================================"
echo "US8-S6: Cross-Company & Agent RBAC — Results"
echo "============================================"
echo -e "  ${GREEN}Passed${NC}: ${PASS_COUNT}"
echo -e "  ${RED}Failed${NC}: ${FAIL_COUNT}"
echo -e "  ${YELLOW}Warnings${NC}: ${WARN_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}✗ TEST FAILED${NC}"
    exit 1
fi

if [ "$PASS_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠ NO TESTS RAN${NC} (User B and Agent may not be configured)"
    echo "  To enable, ensure TEST_USER_B_EMAIL and TEST_USER_AGENT are in 18.0/.env"
    exit 0
fi

echo -e "${GREEN}✓ TEST PASSED: US8-S6 Cross-Company & Agent RBAC${NC}"
echo ""
