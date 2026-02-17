#!/bin/bash
# Feature 009 - User Story 2 (US2): Forgot/Reset Password E2E Test
# Test scenarios for forgot-password and reset-password flows
#
# Scenarios:
# 1. Forgot password with existing email (200 - anti-enumeration)
# 2. Forgot password with non-existing email (200 - anti-enumeration)
# 3. Reset password with valid token (200 + login works)
# 4. Reset password with expired token (410)
# 5. Reset password with already-used token (410)
# 6. Reset password with non-existent token (410)
# 7. Verify old session invalidated after reset
# 8. Verify password successfully changed after reset
# 9. Reset password with mismatched passwords (400)
# 10. Reset password with weak password (400)
#
# Author: TheDevKitchen
# Date: 2026-02-16
# ADRs: ADR-003 (Testing Standards), ADR-011 (Security)

set -e

# Load environment variables
if [ -f "../18.0/.env" ]; then
    source ../18.0/.env
fi

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="${BASE_URL}/api/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

test_scenario() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo ""
    log_info "Test $TESTS_RUN: $1"
}

assert_status() {
    local expected=$1
    local actual=$2
    local description=$3
    
    if [ "$actual" -eq "$expected" ]; then
        echo -e "  ${GREEN}✓${NC} Expected status $expected: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} Expected status $expected but got $actual: $description"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

assert_field() {
    local json=$1
    local field=$2
    local description=$3
    
    local value=$(echo "$json" | jq -r ".$field // empty")
    if [ -n "$value" ] && [ "$value" != "null" ]; then
        echo -e "  ${GREEN}✓${NC} Field '$field' exists: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "$value"
    else
        echo -e "  ${RED}✗${NC} Field '$field' missing: $description"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo ""
    fi
}

assert_sql_result() {
    local query=$1
    local expected=$2
    local description=$3
    
    local result=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c "$query" | xargs)
    
    if [ "$result" == "$expected" ]; then
        echo -e "  ${GREEN}✓${NC} SQL assertion passed: $description (got: $result)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} SQL assertion failed: $description (expected: $expected, got: $result)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

cleanup_test_data() {
    log_info "Cleaning up test data..."
    
    # SQL cleanup script
    docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
        -- Delete test users
        DELETE FROM res_users WHERE login LIKE 'reset_test_%@example.com';
        
        -- Delete test partners
        DELETE FROM res_partner WHERE email LIKE 'reset_test_%@example.com';
        
        -- Delete test tokens
        DELETE FROM thedevkitchen_password_token 
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'reset_test_%@example.com'
        );
        
        -- Delete test sessions
        DELETE FROM thedevkitchen_api_session
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'reset_test_%@example.com'
        );
EOF
    
    log_info "Cleanup completed"
}

# Main test execution
echo "=========================================="
echo "Feature 009 - US2: Forgot/Reset Password E2E Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Cleanup before tests
cleanup_test_data

# ============================================================
# Prerequisite: Create test user with active session
# ============================================================
log_info "Creating test user with active session..."

# Login as Owner to create test user
OWNER_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "'"$TEST_USER_OWNER"'",
        "password": "'"$TEST_PASSWORD_OWNER"'"
    }')

OWNER_JWT=$(echo "$OWNER_LOGIN" | jq -r '.access_token // empty')
OWNER_SESSION=$(echo "$OWNER_LOGIN" | jq -r '.session_id // empty')

# Create test user
TEST_USER_RESPONSE=$(curl -s -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OWNER_JWT" \
    -H "X-Session-ID: $OWNER_SESSION" \
    -d '{
        "name": "Reset Test User",
        "email": "reset_test_user@example.com",
        "document": "11111111111",
        "profile": "agent"
    }')

TEST_USER_ID=$(echo "$TEST_USER_RESPONSE" | jq -r '.data.id')
log_info "Test user created with ID: $TEST_USER_ID"

# Set password for test user directly via SQL
docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
    UPDATE res_users 
    SET password = crypt('originalpassword123', gen_salt('bf')),
        signup_pending = FALSE
    WHERE id = $TEST_USER_ID;
    
    -- Mark invite token as used
    UPDATE thedevkitchen_password_token
    SET status = 'used'
    WHERE user_id = $TEST_USER_ID AND token_type = 'invite';
EOF

# Login as test user to create active session
TEST_USER_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "reset_test_user@example.com",
        "password": "originalpassword123"
    }')

TEST_USER_JWT=$(echo "$TEST_USER_LOGIN" | jq -r '.access_token // empty')
TEST_USER_SESSION=$(echo "$TEST_USER_LOGIN" | jq -r '.session_id // empty')

if [ -z "$TEST_USER_JWT" ] || [ -z "$TEST_USER_SESSION" ]; then
    log_error "Failed to create test user session"
    cleanup_test_data
    exit 1
fi

log_info "Test user session created (Session ID: $TEST_USER_SESSION)"

# ============================================================
# Test 1: Forgot password with existing email (200 - anti-enumeration)
# ============================================================
test_scenario "Forgot password with existing email returns 200"

FORGOT_EXISTING_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/forgot-password" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "reset_test_user@example.com"
    }')

FORGOT_EXISTING_BODY=$(echo "$FORGOT_EXISTING_RESPONSE" | head -n -1)
FORGOT_EXISTING_STATUS=$(echo "$FORGOT_EXISTING_RESPONSE" | tail -n 1)

assert_status 200 "$FORGOT_EXISTING_STATUS" "Forgot password with existing email"
assert_field "$FORGOT_EXISTING_BODY" "message" "Success message returned"

# ============================================================
# Test 2: Forgot password with non-existing email (200 - anti-enumeration)
# ============================================================
test_scenario "Forgot password with non-existing email returns 200 (anti-enumeration)"

FORGOT_NONEXISTING_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/forgot-password" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "nonexistent_user_12345@example.com"
    }')

FORGOT_NONEXISTING_BODY=$(echo "$FORGOT_NONEXISTING_RESPONSE" | head -n -1)
FORGOT_NONEXISTING_STATUS=$(echo "$FORGOT_NONEXISTING_RESPONSE" | tail -n 1)

assert_status 200 "$FORGOT_NONEXISTING_STATUS" "Forgot password with non-existing email (anti-enumeration)"
assert_field "$FORGOT_NONEXISTING_BODY" "message" "Success message returned"

# Verify both responses have same structure (anti-enumeration)
EXISTING_FIELDS=$(echo "$FORGOT_EXISTING_BODY" | jq -r 'keys | sort | join(",")')
NONEXISTING_FIELDS=$(echo "$FORGOT_NONEXISTING_BODY" | jq -r 'keys | sort | join(",")')

if [ "$EXISTING_FIELDS" == "$NONEXISTING_FIELDS" ]; then
    echo -e "  ${GREEN}✓${NC} Response structure identical for existing and non-existing emails"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "  ${RED}✗${NC} Response structure differs (leaks user existence)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# ============================================================
# Test 3: Verify reset token was created for existing user
# ============================================================
test_scenario "Verify reset token created in database"

assert_sql_result \
    "SELECT COUNT(*) FROM thedevkitchen_password_token WHERE user_id = $TEST_USER_ID AND token_type = 'reset' AND status = 'pending';" \
    "1" \
    "Reset token created for user"

# ============================================================
# Test 4: Reset password with mismatched passwords (400)
# ============================================================
log_info "Simulating reset password with mismatched passwords..."

# Generate known token for testing
RAW_RESET_TOKEN="reset-token-$(date +%s)"
RESET_TOKEN_HASH=$(echo -n "$RAW_RESET_TOKEN" | sha256sum | awk '{print $1}')

docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
    UPDATE thedevkitchen_password_token
    SET token = '$RESET_TOKEN_HASH',
        expires_at = NOW() + INTERVAL '24 hours'
    WHERE user_id = $TEST_USER_ID
    AND token_type = 'reset'
    AND status = 'pending';
EOF

test_scenario "Reset password with mismatched passwords returns 400"

MISMATCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_RESET_TOKEN\",
        \"password\": \"newpassword123\",
        \"confirm_password\": \"differentpassword123\"
    }")

MISMATCH_STATUS=$(echo "$MISMATCH_RESPONSE" | tail -n 1)

assert_status 400 "$MISMATCH_STATUS" "Mismatched passwords rejected"

# ============================================================
# Test 5: Reset password with weak password (400)
# ============================================================
test_scenario "Reset password with weak password returns 400"

WEAK_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_RESET_TOKEN\",
        \"password\": \"weak\",
        \"confirm_password\": \"weak\"
    }")

WEAK_PASSWORD_STATUS=$(echo "$WEAK_PASSWORD_RESPONSE" | tail -n 1)

assert_status 400 "$WEAK_PASSWORD_STATUS" "Weak password rejected (< 8 chars)"

# ============================================================
# Test 6: Reset password with valid token (200)
# ============================================================
test_scenario "Reset password with valid token succeeds"

RESET_SUCCESS_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_RESET_TOKEN\",
        \"password\": \"newpassword123\",
        \"confirm_password\": \"newpassword123\"
    }")

RESET_SUCCESS_BODY=$(echo "$RESET_SUCCESS_RESPONSE" | head -n -1)
RESET_SUCCESS_STATUS=$(echo "$RESET_SUCCESS_RESPONSE" | tail -n 1)

assert_status 200 "$RESET_SUCCESS_STATUS" "Reset password successful"
assert_field "$RESET_SUCCESS_BODY" "message" "Success message returned"
assert_field "$RESET_SUCCESS_BODY" "links.login" "Login link provided"

# ============================================================
# Test 7: Verify token marked as used
# ============================================================
test_scenario "Verify reset token marked as used"

assert_sql_result \
    "SELECT status FROM thedevkitchen_password_token WHERE user_id = $TEST_USER_ID AND token_type = 'reset' ORDER BY created_at DESC LIMIT 1;" \
    "used" \
    "Reset token marked as used"

# ============================================================
# Test 8: Verify old session invalidated
# ============================================================
test_scenario "Verify old session invalidated after reset"

assert_sql_result \
    "SELECT is_active FROM thedevkitchen_api_session WHERE session_id = '$TEST_USER_SESSION';" \
    "f" \
    "Old session marked as inactive"

# ============================================================
# Test 9: Verify old password no longer works
# ============================================================
test_scenario "Verify old password no longer works"

OLD_PASSWORD_LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "reset_test_user@example.com",
        "password": "originalpassword123"
    }')

OLD_PASSWORD_STATUS=$(echo "$OLD_PASSWORD_LOGIN" | tail -n 1)

assert_status 401 "$OLD_PASSWORD_STATUS" "Old password rejected"

# ============================================================
# Test 10: Verify new password works
# ============================================================
test_scenario "Verify new password works after reset"

NEW_PASSWORD_LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "reset_test_user@example.com",
        "password": "newpassword123"
    }')

NEW_PASSWORD_BODY=$(echo "$NEW_PASSWORD_LOGIN" | head -n -1)
NEW_PASSWORD_STATUS=$(echo "$NEW_PASSWORD_LOGIN" | tail -n 1)

assert_status 200 "$NEW_PASSWORD_STATUS" "New password works"
assert_field "$NEW_PASSWORD_BODY" "access_token" "JWT token returned"
assert_field "$NEW_PASSWORD_BODY" "session_id" "Session ID returned"

# ============================================================
# Test 11: Reset password with already-used token (410)
# ============================================================
test_scenario "Reset password with used token returns 410"

USED_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_RESET_TOKEN\",
        \"password\": \"anotherpassword\",
        \"confirm_password\": \"anotherpassword\"
    }")

USED_TOKEN_STATUS=$(echo "$USED_TOKEN_RESPONSE" | tail -n 1)

assert_status 410 "$USED_TOKEN_STATUS" "Used token rejected"

# ============================================================
# Test 12: Reset password with expired token (410)
# ============================================================
test_scenario "Reset password with expired token returns 410"

# Request forgot-password again to get new token
curl -s -X POST "$API_BASE/auth/forgot-password" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "reset_test_user@example.com"
    }' > /dev/null

# Generate expired token
EXPIRED_RAW_TOKEN="expired-reset-token-$(date +%s)"
EXPIRED_TOKEN_HASH=$(echo -n "$EXPIRED_RAW_TOKEN" | sha256sum | awk '{print $1}')

docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
    UPDATE thedevkitchen_password_token
    SET token = '$EXPIRED_TOKEN_HASH',
        expires_at = NOW() - INTERVAL '1 day'
    WHERE user_id = $TEST_USER_ID
    AND token_type = 'reset'
    AND status = 'pending'
    ORDER BY created_at DESC
    LIMIT 1;
EOF

EXPIRED_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$EXPIRED_RAW_TOKEN\",
        \"password\": \"password123\",
        \"confirm_password\": \"password123\"
    }")

EXPIRED_TOKEN_STATUS=$(echo "$EXPIRED_TOKEN_RESPONSE" | tail -n 1)

assert_status 410 "$EXPIRED_TOKEN_STATUS" "Expired token rejected"

# ============================================================
# Test 13: Reset password with non-existent token (410)
# ============================================================
test_scenario "Reset password with non-existent token returns 410"

NONEXISTENT_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/reset-password" \
    -H "Content-Type: application/json" \
    -d '{
        "token": "nonexistent-token-12345",
        "password": "password123",
        "confirm_password": "password123"
    }')

NONEXISTENT_TOKEN_STATUS=$(echo "$NONEXISTENT_TOKEN_RESPONSE" | tail -n 1)

assert_status 410 "$NONEXISTENT_TOKEN_STATUS" "Non-existent token rejected"

# ============================================================
# Test Summary
# ============================================================
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Tests Run:    $TESTS_RUN scenarios"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED assertions${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED assertions${NC}"
echo "=========================================="

# Cleanup after tests
cleanup_test_data

# Exit with appropriate code
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    log_info "All tests passed! ✓"
    exit 0
fi
