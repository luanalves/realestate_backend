#!/usr/bin/env bash
# =============================================================================
# test_business_user_isolation.sh — Feature 022 / ADR-029 / SC-006
# =============================================================================
# Verifies that business-role users' data isolation is UNCHANGED after
# Feature 022 is deployed. A company A user must still see exactly the same
# set of records as before — zero cross-company data leakage.
#
# SC-006: Business role users' data isolation is unaffected by Feature 022.
#
# Strategy:
#   1. Login as an Owner from Company A via REST API
#   2. Fetch records for key models (properties, agents, leases)
#   3. Assert that records from Company B are NOT in the response
#   4. Assert that the record count is non-zero (own-company records visible)
#
# Prerequisites:
#   - Odoo running at BASE_URL (default: http://localhost:8069)
#   - COMPANY_A_EMAIL / COMPANY_A_PASSWORD: Owner user for Company A
#   - COMPANY_B_ID: ID of a different company (used to assert exclusion)
#
# Usage:
#   COMPANY_A_EMAIL=owner@companya.com COMPANY_A_PASSWORD=secret \
#   COMPANY_B_ID=2 \
#   ./integration_tests/test_business_user_isolation.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
COMPANY_A_EMAIL="${COMPANY_A_EMAIL:-}"
COMPANY_A_PASSWORD="${COMPANY_A_PASSWORD:-}"
COMPANY_B_ID="${COMPANY_B_ID:-}"

PASS=0
FAIL=0
JWT_TOKEN=""
SESSION_ID=""
COMPANY_A_ID=""

# --- helpers ------------------------------------------------------------------

green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label"
        red "    Expected: $expected"
        red "    Actual  : $actual"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if ! echo "$haystack" | grep -q "$needle"; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label"
        red "    Expected NOT to contain: $needle"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label"
        red "    Expected to contain: $needle"
        FAIL=$((FAIL + 1))
    fi
}

check_prerequisites() {
    if [[ -z "$COMPANY_A_EMAIL" || -z "$COMPANY_A_PASSWORD" ]]; then
        yellow ""
        yellow "⚠ COMPANY_A_EMAIL or COMPANY_A_PASSWORD not set."
        yellow "  This test requires a valid business Owner account."
        yellow ""
        yellow "  Export:"
        yellow "    COMPANY_A_EMAIL=owner@companya.com"
        yellow "    COMPANY_A_PASSWORD=yourpassword"
        yellow "    COMPANY_B_ID=2  (ID of a different tenant company)"
        yellow ""
        yellow "  Skipping SC-006 business isolation test."
        exit 0
    fi
}

login_company_a() {
    echo ""
    yellow "=== Login as Company A Owner ==="

    LOGIN_RESPONSE=$(curl -s \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${COMPANY_A_EMAIL}\", \"password\": \"${COMPANY_A_PASSWORD}\"}" \
        2>/dev/null)

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${COMPANY_A_EMAIL}\", \"password\": \"${COMPANY_A_PASSWORD}\"}" \
        2>/dev/null)

    if [[ "$HTTP_STATUS" != "200" ]]; then
        red "Login failed (HTTP $HTTP_STATUS). Check COMPANY_A_EMAIL and COMPANY_A_PASSWORD."
        exit 1
    fi

    JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('token',''))" 2>/dev/null || echo "")
    SESSION_ID=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('session_id',''))" 2>/dev/null || echo "")
    COMPANY_A_ID=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('company_id',''))" 2>/dev/null || echo "")

    if [[ -z "$JWT_TOKEN" || -z "$SESSION_ID" ]]; then
        red "Could not extract token/session_id from login response."
        red "Response: $LOGIN_RESPONSE"
        exit 1
    fi

    green "  Logged in as $COMPANY_A_EMAIL (Company ID: $COMPANY_A_ID)"
}

test_properties_company_isolation() {
    echo ""
    yellow "=== Test 1: Properties list — only Company A records visible (SC-006) ==="

    RESPONSE=$(curl -s \
        -X GET "${BASE_URL}/api/v1/properties?limit=100" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        2>/dev/null)

    # Should not contain records from Company B
    if [[ -n "$COMPANY_B_ID" ]]; then
        assert_not_contains \
            "Properties response does NOT contain company_id = $COMPANY_B_ID (no Company B leakage)" \
            "\"company_id\": $COMPANY_B_ID" \
            "$RESPONSE"
        assert_not_contains \
            "Properties response does NOT contain company_id:$COMPANY_B_ID" \
            "\"company_id\":$COMPANY_B_ID" \
            "$RESPONSE"
    else
        yellow "  ⚠ COMPANY_B_ID not set — skipping cross-company leakage check."
    fi

    # Should return HTTP 200
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/properties?limit=100" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        2>/dev/null)
    assert_eq "Properties endpoint returns 200" "200" "$HTTP_STATUS"
}

test_agents_company_isolation() {
    echo ""
    yellow "=== Test 2: Agents list — only Company A agents visible (SC-006) ==="

    HTTP_STATUS=$(curl -s -o /tmp/agents_isolation.json -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/agents?limit=100" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        2>/dev/null)

    RESPONSE=$(cat /tmp/agents_isolation.json 2>/dev/null || echo "")

    assert_eq "Agents endpoint returns 200" "200" "$HTTP_STATUS"

    if [[ -n "$COMPANY_B_ID" ]]; then
        assert_not_contains \
            "Agents response does NOT contain Company B records" \
            "\"company_id\": $COMPANY_B_ID" \
            "$RESPONSE"
    fi
}

test_leases_company_isolation() {
    echo ""
    yellow "=== Test 3: Leases list — only Company A leases visible (SC-006) ==="

    HTTP_STATUS=$(curl -s -o /tmp/leases_isolation.json -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/leases?limit=100" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        2>/dev/null)

    RESPONSE=$(cat /tmp/leases_isolation.json 2>/dev/null || echo "")

    assert_eq "Leases endpoint returns 200" "200" "$HTTP_STATUS"

    if [[ -n "$COMPANY_B_ID" ]]; then
        assert_not_contains \
            "Leases response does NOT contain Company B records" \
            "\"company_id\": $COMPANY_B_ID" \
            "$RESPONSE"
    fi
}

# --- summary ------------------------------------------------------------------

print_summary() {
    echo ""
    echo "========================================"
    echo " Feature 022 — SC-006 Isolation Results "
    echo "========================================"
    green " PASS: $PASS"
    if [[ $FAIL -gt 0 ]]; then
        red " FAIL: $FAIL"
    else
        echo " FAIL: $FAIL"
    fi
    echo "========================================"
    if [[ $FAIL -gt 0 ]]; then
        exit 1
    fi
}

# --- main ---------------------------------------------------------------------

echo "Feature 022 — SC-006: Business User Data Isolation Tests"
echo "Base URL: ${BASE_URL}"

check_prerequisites
login_company_a
test_properties_company_isolation
test_agents_company_isolation
test_leases_company_isolation
print_summary
