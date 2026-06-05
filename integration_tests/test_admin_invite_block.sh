#!/usr/bin/env bash
# =============================================================================
# test_admin_invite_block.sh — Feature 022 / ADR-029 / FR-007
# =============================================================================
# Verifies that the REST API invite endpoint CANNOT be used to invite a user
# with the base.group_system profile. This is enforced by Feature 009's
# authorization matrix — no new guard code was added for Feature 022.
#
# FR-007: Admin cannot be invited via API (satisfied by Feature 009)
# Reference: specs/022-admin-ui-cross-company/spec.md §FR-007
#
# Prerequisites:
#   - Odoo running at BASE_URL (default: http://localhost:8069)
#   - A valid business Owner token available (OWNER_TOKEN env var)
#   - OWNER_SESSION_ID set (for @require_session)
#   - OWNER_COMPANY_ID set
#
# Usage:
#   OWNER_TOKEN=... OWNER_SESSION_ID=... OWNER_COMPANY_ID=... \
#     ./integration_tests/test_admin_invite_block.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"
OWNER_SESSION_ID="${OWNER_SESSION_ID:-}"
OWNER_COMPANY_ID="${OWNER_COMPANY_ID:-1}"

PASS=0
FAIL=0

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

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label"
        red "    Expected to contain: $needle"
        red "    Actual body        : $(echo "$haystack" | head -3)"
        FAIL=$((FAIL + 1))
    fi
}

check_prerequisites() {
    if [[ -z "$OWNER_TOKEN" || -z "$OWNER_SESSION_ID" ]]; then
        yellow ""
        yellow "⚠ OWNER_TOKEN or OWNER_SESSION_ID not set."
        yellow "  This test requires an authenticated Owner session."
        yellow ""
        yellow "  To obtain credentials:"
        yellow "    POST ${BASE_URL}/api/v1/users/login with Owner credentials"
        yellow "    Set OWNER_TOKEN=<jwt_token> OWNER_SESSION_ID=<session_id>"
        yellow ""
        yellow "  Skipping FR-007 invite test."
        exit 0
    fi
}

# --- test functions -----------------------------------------------------------

test_admin_profile_not_invitable() {
    echo ""
    yellow "=== Test 1: Attempting to invite base.group_system user is rejected (FR-007) ==="

    # Attempt to invite with profile that maps to base.group_system
    # The authorization matrix in Feature 009 restricts invitable profiles.
    # base.group_system is not in any invitable profile enum.
    # We test with a profile_type that would require admin (using a crafted request).
    HTTP_STATUS=$(curl -s -o /tmp/invite_admin_response.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${OWNER_TOKEN}" \
        -H "X-Openerp-Session-Id: ${OWNER_SESSION_ID}" \
        -d "{
            \"email\": \"fake_admin_invite_$(date +%s)@example.com\",
            \"name\": \"Fake Admin\",
            \"profile_type\": \"system_admin\",
            \"company_id\": ${OWNER_COMPANY_ID}
        }" \
        2>/dev/null)

    RESPONSE_BODY=$(cat /tmp/invite_admin_response.json 2>/dev/null || echo "")

    # Any status != 200 is a block (400 or 403 expected from Feature 009 matrix)
    assert_eq "Invite with system_admin profile is rejected (not 200)" \
        "1" "$([ "$HTTP_STATUS" != "200" ] && echo 1 || echo 0)"
    assert_contains "Response contains 'error'" '"error"' "$RESPONSE_BODY"
}

test_valid_profile_still_works() {
    echo ""
    yellow "=== Test 2: Inviting a valid profile (e.g. agent) still succeeds (regression guard) ==="

    # Only verify the endpoint accepts valid profile types (not blocked)
    # We use a non-existent email to avoid creating test data, expecting validation error,
    # NOT an authorization matrix rejection.
    HTTP_STATUS=$(curl -s -o /tmp/invite_agent_response.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${OWNER_TOKEN}" \
        -H "X-Openerp-Session-Id: ${OWNER_SESSION_ID}" \
        -d "{
            \"email\": \"test_agent_$(date +%s)@test-feature022.invalid\",
            \"name\": \"Test Agent Feature 022\",
            \"profile_type\": \"agent\",
            \"company_id\": ${OWNER_COMPANY_ID}
        }" \
        2>/dev/null)

    RESPONSE_BODY=$(cat /tmp/invite_agent_response.json 2>/dev/null || echo "")

    # Status should be 200 (created) or 400 (validation error for invalid domain email).
    # It must NOT be 403 (authorization matrix blocking the agent profile itself).
    assert_eq "Agent profile invite does NOT return 403 (not blocked by matrix)" \
        "1" "$([ "$HTTP_STATUS" != "403" ] && echo 1 || echo 0)"

    # Cleanup: if a user was created, it's safe to leave (test email domain is .invalid)
    echo "    Response status: ${HTTP_STATUS}"
}

# --- summary ------------------------------------------------------------------

print_summary() {
    echo ""
    echo "========================================"
    echo " Feature 022 — FR-007 Invite Block      "
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

echo "Feature 022 — FR-007: Admin Invite Block Integration Tests"
echo "Base URL: ${BASE_URL}"

check_prerequisites
test_admin_profile_not_invitable
test_valid_profile_still_works
print_summary
