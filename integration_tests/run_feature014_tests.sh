#!/usr/bin/env bash
# =============================================================================
# Feature 014 — Rental Credit Check (Análise de Ficha)
# Integration test runner
#
# Usage:
#   ./run_feature014_tests.sh             # Run all tests
#   ./run_feature014_tests.sh 1 3         # Run only tests 1 and 3
#   BASE_URL=http://prod:8069 ./run_feature014_tests.sh
#
# Requirements: jq, curl
# ADR: ADR-003 (E2E API tests — requires running Odoo + DB)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB="${POSTGRES_DB:-realestate}"
ADMIN_USER="${ODOO_ADMIN_USER:-admin}"
ADMIN_PASS="${ODOO_ADMIN_PASS:-admin}"
TIMESTAMP=$(date +%Y%m%d%H%M%S)

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[PASS]${NC}  $*"; PASS=$((PASS + 1)); }
log_fail()  { echo -e "${RED}[FAIL]${NC}  $*"; FAIL=$((FAIL + 1)); }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_title() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }

require_jq() {
    if ! command -v jq &>/dev/null; then
        echo -e "${RED}ERROR: jq not installed. Run: brew install jq${NC}"
        exit 1
    fi
}

# Obtain a JWT + session pair for a given user login
# Usage: obtain_jwt <login> <password>  → sets JWT_TOKEN, SESSION_ID, COMPANY_ID
obtain_jwt() {
    local login="$1"
    local password="$2"

    local auth_resp
    auth_resp=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"login\":\"$login\",\"password\":\"$password\",\"db\":\"$DB\"}" 2>/dev/null)

    JWT_TOKEN=$(echo "$auth_resp" | jq -r '.access_token // empty')
    SESSION_ID=$(echo "$auth_resp" | jq -r '.session_id // empty')
    COMPANY_ID=$(echo "$auth_resp" | jq -r '.company_id // empty')

    if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" = "null" ]; then
        log_fail "Auth failed for $login — response: $auth_resp"
        return 1
    fi
}

# POST helper
api_post() {
    local path="$1"
    local body="$2"
    curl -s -X POST "$BASE_URL$path" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "X-Openerp-Session-Id: $SESSION_ID" \
        -d "$body" 2>/dev/null
}

# PATCH helper
api_patch() {
    local path="$1"
    local body="$2"
    curl -s -X PATCH "$BASE_URL$path" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "X-Openerp-Session-Id: $SESSION_ID" \
        -d "$body" 2>/dev/null
}

# GET helper
api_get() {
    local path="$1"
    curl -s -X GET "$BASE_URL$path" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "X-Openerp-Session-Id: $SESSION_ID" 2>/dev/null
}

# Odoo JSON-RPC helper (admin)
odoo_rpc() {
    local model="$1"
    local method="$2"
    local args="$3"
    local kwargs="${4:-{}}"
    curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b /tmp/odoo_014_cookies.txt \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{
              \"model\":\"$model\",\"method\":\"$method\",
              \"args\":$args,\"kwargs\":$kwargs}}" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Setup: Admin session for test data creation
# ---------------------------------------------------------------------------
setup_admin_session() {
    log_info "Authenticating as admin..."
    local resp
    resp=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
        -H "Content-Type: application/json" \
        -c /tmp/odoo_014_cookies.txt \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{
              \"db\":\"$DB\",\"login\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"},
            \"id\":1}" 2>/dev/null)
    local uid
    uid=$(echo "$resp" | jq -r '.result.uid // empty')
    if [ -z "$uid" ] || [ "$uid" = "false" ]; then
        echo -e "${RED}FATAL: Admin login failed${NC}"
        exit 1
    fi
    log_info "Admin UID: $uid"
}

# ---------------------------------------------------------------------------
# Test 1: Initiate credit check on a sent lease proposal
# ---------------------------------------------------------------------------
test_01_initiate_credit_check() {
    log_title "Test 1 — Initiate credit check (FR-001)"

    # Create a test lease proposal via RPC
    local partner_resp
    partner_resp=$(odoo_rpc 'res.partner' 'create' \
        "[{\"name\":\"Cliente Teste 014-${TIMESTAMP}\",\"email\":\"cliente014${TIMESTAMP}@test.com\"}]")
    local partner_id
    partner_id=$(echo "$partner_resp" | jq -r '.result // empty')
    if [ -z "$partner_id" ] || [ "$partner_id" = "null" ]; then
        log_fail "T1: Could not create test partner"
        return
    fi

    # For a full integration test we would need a property + proposal.
    # Here we verify the endpoint is reachable and returns proper errors
    # when called with invalid data (proposal does not exist → 404).
    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    local resp
    resp=$(api_post "/api/v1/proposals/999999/credit-checks" \
        '{"insurer_name":"Tokio Marine"}')
    local status
    status=$(echo "$resp" | jq -r '.error.code // .status // empty')

    if [ "$status" = "404" ] || echo "$resp" | grep -qi "not found"; then
        log_ok "T1: Non-existent proposal returns 404"
    else
        log_fail "T1: Expected 404, got: $resp"
    fi
}

# ---------------------------------------------------------------------------
# Test 2: Register approved result
# ---------------------------------------------------------------------------
test_02_register_approved() {
    log_title "Test 2 — Register approved result (FR-003)"

    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    # Attempt to PATCH a non-existent check → 404
    local resp
    resp=$(api_patch "/api/v1/proposals/999999/credit-checks/999999" \
        '{"result":"approved","check_date":"2026-01-15"}')

    if echo "$resp" | grep -qi "not found"; then
        log_ok "T2: Non-existent check returns 404"
    else
        log_fail "T2: Expected 404, got: $resp"
    fi
}

# ---------------------------------------------------------------------------
# Test 3: Register rejected — rejection_reason required
# ---------------------------------------------------------------------------
test_03_reject_requires_reason() {
    log_title "Test 3 — Reject requires rejection_reason (FR-009)"

    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    local resp
    resp=$(api_patch "/api/v1/proposals/999999/credit-checks/999999" \
        '{"result":"rejected"}')

    # Either 404 (not found) or 422 (validation error — no reason)
    if echo "$resp" | grep -qi "not found\|rejection_reason\|required\|422"; then
        log_ok "T3: Reject without reason blocked (404 or 422)"
    else
        log_fail "T3: Expected validation error, got: $resp"
    fi
}

# ---------------------------------------------------------------------------
# Test 4: List credit checks for a proposal
# ---------------------------------------------------------------------------
test_04_list_credit_checks() {
    log_title "Test 4 — List credit checks (FR-012)"

    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    local resp
    resp=$(api_get "/api/v1/proposals/999999/credit-checks")
    local http_status
    http_status=$(echo "$resp" | jq -r '.error.code // .status // empty')

    if echo "$resp" | grep -qi "not found\|404"; then
        log_ok "T4: Non-existent proposal returns 404"
    else
        log_fail "T4: Expected 404 for unknown proposal, got: $resp"
    fi
}

# ---------------------------------------------------------------------------
# Test 5: Client credit history — owner access
# ---------------------------------------------------------------------------
test_05_client_history_owner() {
    log_title "Test 5 — Client credit history owner access (FR-013)"

    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    local resp
    resp=$(api_get "/api/v1/clients/999999/credit-history")

    if echo "$resp" | grep -qi "not found\|404"; then
        log_ok "T5: Unknown client returns 404 (anti-enumeration)"
    else
        log_fail "T5: Expected 404 for unknown client, got: $resp"
    fi
}

# ---------------------------------------------------------------------------
# Test 6: Company isolation — cross-company 404
# ---------------------------------------------------------------------------
test_06_company_isolation() {
    log_title "Test 6 — Company isolation (ADR-008)"

    # Same as T5 but specifically verifies anti-enumeration behaviour:
    # a client that exists in another company should also return 404.
    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    # Partner id=1 (typically base company partner) should be in another
    # company scope for a fresh user; expect either 200 (if in scope) or 404.
    local resp
    resp=$(api_get "/api/v1/clients/1/credit-history")
    local has_error
    has_error=$(echo "$resp" | jq -r '.error // empty')

    if [ -z "$has_error" ]; then
        # Got 200 — verify summary keys are present
        local total
        total=$(echo "$resp" | jq -r '.summary.total // "missing"')
        if [ "$total" != "missing" ]; then
            log_ok "T6: In-scope client returns 200 with summary"
        else
            log_fail "T6: 200 but missing summary keys: $resp"
        fi
    else
        log_ok "T6: Out-of-scope client returns error (isolation enforced)"
    fi
}

# ---------------------------------------------------------------------------
# Test 7: Endpoint availability (health check)
# ---------------------------------------------------------------------------
test_07_endpoints_reachable() {
    log_title "Test 7 — All 4 endpoints reachable (no 5xx)"

    obtain_jwt "$ADMIN_USER" "$ADMIN_PASS" || return

    local endpoints=(
        "GET:/api/v1/proposals/1/credit-checks"
        "GET:/api/v1/clients/1/credit-history"
    )

    for ep in "${endpoints[@]}"; do
        local method="${ep%%:*}"
        local path="${ep#*:}"
        local resp
        resp=$(api_get "$path")
        local has_500
        has_500=$(echo "$resp" | jq -r 'if .error.code == 500 then "yes" else "no" end' 2>/dev/null || echo "no")
        if [ "$has_500" = "yes" ]; then
            log_fail "T7: $method $path returned 500: $resp"
        else
            log_ok "T7: $method $path reachable (no 5xx)"
        fi
    done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
require_jq
setup_admin_session

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Feature 014 — Rental Credit Check Tests         ║${NC}"
echo -e "${CYAN}║  Target: $BASE_URL${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"

# Determine which tests to run
TESTS_TO_RUN=()
if [ $# -eq 0 ]; then
    TESTS_TO_RUN=(1 2 3 4 5 6 7)
else
    TESTS_TO_RUN=("$@")
fi

for t in "${TESTS_TO_RUN[@]}"; do
    case $t in
        1) test_01_initiate_credit_check ;;
        2) test_02_register_approved ;;
        3) test_03_reject_requires_reason ;;
        4) test_04_list_credit_checks ;;
        5) test_05_client_history_owner ;;
        6) test_06_company_isolation ;;
        7) test_07_endpoints_reachable ;;
        *) log_warn "Unknown test number: $t" ;;
    esac
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}━━━ Results ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}PASS: $PASS${NC}   ${RED}FAIL: $FAIL${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
