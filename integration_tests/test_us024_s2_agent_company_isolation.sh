#!/bin/bash
# ==============================================================================
# Integration Test: US024-S2 - Agent Company/Agent Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 2: Agent only sees their own assigned leads, scoped within
# their company. Verifies pedro@imobiliaria.com (Agent, Company A) sees
# lead A1-1/A1-2 (his own) but NOT A2-1 (same company, different agent)
# and NOT B1-1 (different company entirely).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s2_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"
exec > >(tee "$TEST_LOG") 2>&1

FAILED=0

assert_contains() {
    local haystack="$1"; local needle="$2"; local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${GREEN}✓${NC} $label"
    else
        echo -e "${RED}✗ FAIL${NC}: $label"; FAILED=1
    fi
}

assert_not_contains() {
    local haystack="$1"; local needle="$2"; local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${RED}✗ FAIL${NC}: $label (unexpectedly found: $needle)"; FAILED=1
    else
        echo -e "${GREEN}✓${NC} $label"
    fi
}

echo "=========================================="
echo "US024-S2: Agent Company/Agent Isolation"
echo "=========================================="
echo ""

echo "=== Test Started: $(date) ==="

echo -e "${BLUE}STEP 1${NC}: Authenticating as Agent pedro (Company A)..."
authenticate_user "pedro@imobiliaria.com" "agent123"
AGENT_TOKEN="$OAUTH_TOKEN"
AGENT_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓${NC} Agent authenticated"
echo ""

echo -e "${BLUE}WHEN${NC}: Agent pedro calls GET /api/v1/leads..."
AGENT_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
    -H "Authorization: Bearer $AGENT_TOKEN" \
    -H "X-Openerp-Session-Id: $AGENT_SESSION")

assert_contains "$AGENT_LEADS" "Seed024 Lead A1-1" "Agent pedro sees his own lead A1-1"
assert_contains "$AGENT_LEADS" "Seed024 Lead A1-2" "Agent pedro sees his own lead A1-2"
assert_not_contains "$AGENT_LEADS" "Seed024 Lead A2-1" "Agent pedro does NOT see agent2's lead A2-1 (same company)"
assert_not_contains "$AGENT_LEADS" "Seed024 Lead B1-1" "Agent pedro does NOT see carmen's lead B1-1 (different company)"

echo ""
echo -e "${BLUE}WHEN${NC}: Agent pedro calls GET /api/v1/leads/export..."
AGENT_CSV=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/export" \
    -H "Authorization: Bearer $AGENT_TOKEN" \
    -H "X-Openerp-Session-Id: $AGENT_SESSION")

assert_contains "$AGENT_CSV" "Seed024 Lead A1-1" "Agent pedro CSV export includes his own lead A1-1"
assert_not_contains "$AGENT_CSV" "Seed024 Lead A2-1" "Agent pedro CSV export excludes agent2's lead A2-1"
assert_not_contains "$AGENT_CSV" "Seed024 Lead B1-1" "Agent pedro CSV export excludes carmen's lead B1-1"

echo ""
echo -e "${BLUE}WHEN${NC}: Manager filters list_leads by agent_id=pedro (regression check for FR2.3)..."
authenticate_user "manager024@imobiliaria.com" "manager123seed024"
MANAGER_TOKEN="$OAUTH_TOKEN"
MANAGER_SESSION="$USER_SESSION_ID"

# NOTE: /web/dataset/call_kw requires a native Odoo session cookie
# (obtained via /web/session/authenticate), which is incompatible with
# this test suite's JWT + X-Openerp-Session-Id auth scheme (it returns
# "Odoo Session Expired" regardless of the bearer token/session header
# supplied). Derive pedro's agent_id from the already-fetched AGENT_LEADS
# response (his own leads carry his agent_id) instead of a fresh call_kw
# lookup.
PEDRO_AGENT_ID=$(echo "$AGENT_LEADS" | jq -r '.leads[0].agent_id // empty')

MANAGER_FILTERED=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&agent_id=$PEDRO_AGENT_ID&limit=100" \
    -H "Authorization: Bearer $MANAGER_TOKEN" \
    -H "X-Openerp-Session-Id: $MANAGER_SESSION")

assert_contains "$MANAGER_FILTERED" "Seed024 Lead A1-1" "Manager agent_id filter still returns pedro's lead A1-1"
assert_not_contains "$MANAGER_FILTERED" "Seed024 Lead A2-1" "Manager agent_id filter correctly excludes agent2's lead A2-1"

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

exit $FAILED
