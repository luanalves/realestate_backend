#!/bin/bash
# ==============================================================================
# Integration Test: US024-S1 - Manager/Owner Company Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 1: Manager/Owner sees only their own company's leads
# Verifies GET /api/v1/leads, /leads/export, /leads/statistics are all
# scoped by request.company_domain (FR1.1) and never leak Company B's
# (urban_properties) leads to a Company A (quicksol)-only Manager/Owner.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s1_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

FAILED=0

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${GREEN}✓${NC} $label"
    else
        echo -e "${RED}✗ FAIL${NC}: $label"
        FAILED=1
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${RED}✗ FAIL${NC}: $label (unexpectedly found: $needle)"
        FAILED=1
    else
        echo -e "${GREEN}✓${NC} $label"
    fi
}

echo "=========================================="
echo "US024-S1: Manager/Owner Company Isolation"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="

    # --------------------------------------------------------------------
    # Company A (quicksol) Manager
    # --------------------------------------------------------------------
    echo -e "${BLUE}STEP 1${NC}: Authenticating as Company A Manager..."
    authenticate_user "manager024@imobiliaria.com" "manager123seed024"
    MANAGER_TOKEN="$OAUTH_TOKEN"
    MANAGER_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Manager authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads..."
    MANAGER_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    assert_contains "$MANAGER_LEADS" "Seed024 Lead A1-1" "Manager sees Company A lead A1-1"
    assert_contains "$MANAGER_LEADS" "Seed024 Lead A1-2" "Manager sees Company A lead A1-2"
    assert_contains "$MANAGER_LEADS" "Seed024 Lead A2-1" "Manager sees Company A lead A2-1 (own-company, different agent)"
    assert_not_contains "$MANAGER_LEADS" "Seed024 Lead B1-1" "Manager does NOT see Company B lead B1-1"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads/export..."
    MANAGER_CSV=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/export" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    assert_contains "$MANAGER_CSV" "Seed024 Lead A1-1" "Manager CSV export includes Company A lead A1-1"
    assert_not_contains "$MANAGER_CSV" "Seed024 Lead B1-1" "Manager CSV export excludes Company B lead B1-1"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads/statistics..."
    MANAGER_STATS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/statistics" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    MANAGER_STATS_TOTAL=$(extract_json_field "$MANAGER_STATS" "total")
    echo "Manager statistics total: $MANAGER_STATS_TOTAL"
    if [ "$MANAGER_STATS_TOTAL" -ge 3 ]; then
        echo -e "${GREEN}✓${NC} Manager statistics total includes at least the 3 Company A seed leads"
    else
        echo -e "${RED}✗ FAIL${NC}: Manager statistics total ($MANAGER_STATS_TOTAL) is lower than expected"
        FAILED=1
    fi

    # --------------------------------------------------------------------
    # Company A (quicksol) Owner — same isolation semantics as Manager
    # --------------------------------------------------------------------
    echo ""
    echo -e "${BLUE}STEP 2${NC}: Authenticating as Company A Owner..."
    authenticate_user "owner024@imobiliaria.com" "owner123seed024"
    OWNER_TOKEN="$OAUTH_TOKEN"
    OWNER_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Owner authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: Owner calls GET /api/v1/leads..."
    OWNER_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION")

    assert_contains "$OWNER_LEADS" "Seed024 Lead A1-1" "Owner sees Company A lead A1-1"
    assert_not_contains "$OWNER_LEADS" "Seed024 Lead B1-1" "Owner does NOT see Company B lead B1-1"

    echo ""
    if [ "$FAILED" -eq 0 ]; then
        echo "=========================================="
        echo -e "${GREEN}TEST PASSED${NC}"
        echo "=========================================="
    else
        echo "=========================================="
        echo -e "${RED}TEST FAILED${NC}"
        echo "=========================================="
    fi
    echo "=== Test Ended: $(date) ==="

} 2>&1 | tee "$TEST_LOG"

exit $FAILED
