#!/usr/bin/env bash
# =============================================================================
# test_admin_api_block.sh — Feature 022 / ADR-029
# =============================================================================
# Verifies that the REST API login endpoint blocks System Admin users with
# HTTP 401 (anti-enumeration).
#
# Authentication layers:
#   Layer 1 — @require_jwt (JWT middleware): Blocks requests without Bearer.
#             Returns {"error": "unauthorized", ...} — admin cannot login.
#   Layer 2 — Controller guard (new code in Feature 022): With a valid OAuth2
#             JWT, checks has_group('base.group_system') and returns
#             {"error": {"status": 401, "message": "Invalid credentials"}}.
#             Also creates audit log entry.
#
# Layer 1 runs always. Layer 2 requires APP_JWT_TOKEN.
#
# Usage:
#   ./integration_tests/test_admin_api_block.sh
#   APP_JWT_TOKEN=<jwt> BUSINESS_EMAIL=o@c.com BUSINESS_PASSWORD=s \
#     ./integration_tests/test_admin_api_block.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
BUSINESS_EMAIL="${BUSINESS_EMAIL:-}"
BUSINESS_PASSWORD="${BUSINESS_PASSWORD:-}"
APP_JWT_TOKEN="${APP_JWT_TOKEN:-}"
COMPOSE_FILE_DIR="${COMPOSE_FILE_DIR:-$(dirname "$0")/../18.0}"

PASS=0
FAIL=0

green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label (expected='$expected' actual='$actual')"; FAIL=$((FAIL+1)); fi
}
assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label (expected '$needle' in response)"; FAIL=$((FAIL+1)); fi
}
assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if ! echo "$haystack" | grep -q "$needle"; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label (unexpected '$needle' found in response)"; FAIL=$((FAIL+1)); fi
}

# Layer 1 tests ---------------------------------------------------------------

test_layer1_blocked() {
    echo ""
    yellow "=== [Layer 1] Admin login without OAuth JWT → 401 (SC-004) ==="
    HTTP_STATUS=$(curl -s -o /tmp/f022_l1.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)
    BODY=$(cat /tmp/f022_l1.json 2>/dev/null || echo "")
    assert_eq    "HTTP 401"                          "401" "$HTTP_STATUS"
    assert_contains "Response contains error key"   '"error"' "$BODY"
    assert_not_contains "No session_id leaked"      '"session_id"' "$BODY"
    assert_not_contains "No token leaked"           '"token"' "$BODY"
}

test_layer1_anti_enum() {
    echo ""
    yellow "=== [Layer 1] Admin block indistinguishable from bad credentials ==="
    ADM_STATUS=$(curl -s -o /tmp/f022_adm.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)
    BAD_STATUS=$(curl -s -o /tmp/f022_bad.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"no-such-user@example.com","password":"wrongpassword"}' 2>/dev/null)
    ADM_BODY=$(cat /tmp/f022_adm.json 2>/dev/null || echo "")
    BAD_BODY=$(cat /tmp/f022_bad.json 2>/dev/null || echo "")
    assert_eq "HTTP status is identical (anti-enumeration)" "$BAD_STATUS" "$ADM_STATUS"
    assert_eq "Response body is identical (anti-enumeration)" "$BAD_BODY" "$ADM_BODY"
}

# Layer 2 tests (controller guard, requires APP_JWT_TOKEN) ---------------------

test_layer2_controller_guard() {
    echo ""
    yellow "=== [Layer 2] Controller guard — has_group('base.group_system') check ==="
    if [[ -z "$APP_JWT_TOKEN" ]]; then
        yellow "  ⚠ Skipped: set APP_JWT_TOKEN=<oauth2_jwt> to run Layer 2 tests."
        return
    fi
    HTTP_STATUS=$(curl -s -o /tmp/f022_l2.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT_TOKEN}" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)
    BODY=$(cat /tmp/f022_l2.json 2>/dev/null || echo "")
    assert_eq    "HTTP 401 from controller guard"               "401" "$HTTP_STATUS"
    assert_contains "Response contains 'Invalid credentials'"  '"Invalid credentials"' "$BODY"
    assert_not_contains "No session_id leaked"                 '"session_id"' "$BODY"
}

test_layer2_audit_log() {
    echo ""
    yellow "=== [Layer 2] Blocked admin login creates audit log entry (SC-005) ==="
    if [[ -z "$APP_JWT_TOKEN" ]]; then
        yellow "  ⚠ Skipped: APP_JWT_TOKEN not set."; return; fi
    BEFORE_TS=$(date -u +"%Y-%m-%d %H:%M:%S")
    curl -s -o /dev/null \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT_TOKEN}" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null
    CNT=$(docker compose -f "${COMPOSE_FILE_DIR}/docker-compose.yml" exec -T db \
        psql -U odoo -d realestate -t -c \
        "SELECT COUNT(*) FROM thedevkitchen_failed_login_log
         WHERE login_email='${ADMIN_EMAIL}'
           AND reason LIKE '%Admin API login blocked%'
           AND failed_at>='${BEFORE_TS}';" 2>/dev/null | tr -d ' \n' || echo "0")
    assert_eq "Audit log entry created" "1" "$([ "${CNT:-0}" -ge 1 ] && echo 1 || echo 0)"
}

test_layer2_business_ok() {
    echo ""
    yellow "=== [Layer 2] Business user login unaffected (regression guard) ==="
    if [[ -z "$APP_JWT_TOKEN" || -z "$BUSINESS_EMAIL" ]]; then
        yellow "  ⚠ Skipped: APP_JWT_TOKEN + BUSINESS_EMAIL + BUSINESS_PASSWORD required."; return; fi
    HTTP_STATUS=$(curl -s -o /tmp/f022_biz.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT_TOKEN}" \
        -d "{\"email\":\"${BUSINESS_EMAIL}\",\"password\":\"${BUSINESS_PASSWORD}\"}" 2>/dev/null)
    BODY=$(cat /tmp/f022_biz.json 2>/dev/null || echo "")
    assert_eq    "Business user HTTP 200"                  "200" "$HTTP_STATUS"
    assert_contains "Business user gets session_id"        '"session_id"' "$BODY"
}

print_summary() {
    echo ""
    echo "========================================"
    echo " Feature 022 — Admin API Block Results  "
    echo "========================================"
    green " PASS: $PASS"
    [[ $FAIL -gt 0 ]] && red " FAIL: $FAIL" || echo " FAIL: $FAIL"
    [[ -z "$APP_JWT_TOKEN" ]] && yellow " NOTE: Layer 2 tests skipped (APP_JWT_TOKEN not set)."
    echo "========================================"
    [[ $FAIL -gt 0 ]] && exit 1 || exit 0
}

echo "Feature 022 — Admin API Block Integration Tests"
echo "Base URL : ${BASE_URL}"
echo "Admin    : ${ADMIN_EMAIL}"
echo "Layer 2  : $([ -n "$APP_JWT_TOKEN" ] && echo 'ENABLED (APP_JWT_TOKEN set)' || echo 'SKIPPED (APP_JWT_TOKEN not set)')"

test_layer1_blocked
test_layer1_anti_enum
test_layer2_controller_guard
test_layer2_audit_log
test_layer2_business_ok
print_summary
