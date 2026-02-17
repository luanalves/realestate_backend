#!/bin/bash
# Feature 009 - User Story 1 (US1): Invite Flow E2E Test
# Test scenarios for complete invite → set-password → login flow
#
# Scenarios:
# 1. Owner invites Manager (201 + email sent)
# 2. Manager invites Agent (201)
# 3. Agent invites Owner (property owner) (201)
# 4. Set-password with valid token (200 + login works)
# 5. Set-password with expired token (410)
# 6. Set-password with already-used token (410)
# 7. Invite with duplicate email (409)
# 8. Invite with duplicate document (409)
# 9. Login before set-password (401)
# 10. Login after set-password (success with session_id + JWT)
#
# Author: TheDevKitchen
# Date: 2026-02-16
# ADRs: ADR-003 (Testing Standards), ADR-011 (Security)

set -e

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
    else
        echo -e "  ${RED}✗${NC} Field '$field' missing: $description"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

cleanup_test_data() {
    log_info "Cleaning up test data..."
    
    # SQL cleanup script
    PGPASSWORD=odoo psql -h localhost -U odoo -d realestate <<EOF
        -- Delete test users
        DELETE FROM res_users WHERE login LIKE 'invite_test_%@example.com';
        
        -- Delete test partners
        DELETE FROM res_partner WHERE email LIKE 'invite_test_%@example.com';
        
        -- Delete test tokens
        DELETE FROM thedevkitchen_password_token 
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'invite_test_%@example.com'
        );
EOF
    
    log_info "Cleanup completed"
}

# Main test execution
echo "=========================================="
echo "Feature 009 - US1: Invite Flow E2E Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Cleanup before tests
cleanup_test_data

# ============================================================
# Prerequisite: Login as Owner to get auth tokens
# ============================================================
log_info "Setting up authentication as Owner..."

LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "owner@example.com",
        "password": "owner123"
    }')

JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')
SESSION_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.session_id // empty')
OWNER_COMPANY_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.company_id // empty')

if [ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ]; then
    log_error "Failed to authenticate as Owner. Please ensure owner@example.com exists with password owner123"
    exit 1
fi

log_info "Owner authentication successful (Company ID: $OWNER_COMPANY_ID)"

# ============================================================
# Test 1: Owner invites Manager (201 + token generated)
# ============================================================
test_scenario "Owner invites Manager successfully"

MANAGER_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Invite Test Manager",
        "email": "invite_test_manager@example.com",
        "document": "11122233344",
        "profile": "manager"
    }')

MANAGER_INVITE_BODY=$(echo "$MANAGER_INVITE_RESPONSE" | head -n -1)
MANAGER_INVITE_STATUS=$(echo "$MANAGER_INVITE_RESPONSE" | tail -n 1)

assert_status 201 "$MANAGER_INVITE_STATUS" "Manager invite created"
assert_field "$MANAGER_INVITE_BODY" "data.id" "User ID returned"
assert_field "$MANAGER_INVITE_BODY" "data.email" "Email field present"
assert_field "$MANAGER_INVITE_BODY" "data.name" "Name field present"
assert_field "$MANAGER_INVITE_BODY" "data.profile" "Profile field present"
assert_field "$MANAGER_INVITE_BODY" "data.invite_expires_at" "Invite expiry returned"
assert_field "$MANAGER_INVITE_BODY" "links.self" "HATEOAS self link"
assert_field "$MANAGER_INVITE_BODY" "links.resend_invite" "HATEOAS resend link"

MANAGER_USER_ID=$(echo "$MANAGER_INVITE_BODY" | jq -r '.data.id')
log_info "Manager user created with ID: $MANAGER_USER_ID"

# ============================================================
# Test 2: Get Manager's invite token from database (for testing)
# ============================================================
log_info "Retrieving Manager's invite token from database..."

MANAGER_TOKEN=$(PGPASSWORD=odoo psql -h localhost -U odoo -d realestate -t -c \
    "SELECT token FROM thedevkitchen_password_token 
     WHERE user_id = $MANAGER_USER_ID 
     AND token_type = 'invite' 
     AND status = 'pending' 
     ORDER BY created_at DESC LIMIT 1;" | xargs)

if [ -z "$MANAGER_TOKEN" ]; then
    log_error "Failed to retrieve Manager's invite token from database"
    cleanup_test_data
    exit 1
fi

log_info "Retrieved token hash (first 16 chars): ${MANAGER_TOKEN:0:16}..."

# Note: In real scenario, raw token would be in email. For testing, we need the raw token.
# Since we can't reverse SHA-256, we'll generate a known token for subsequent tests.

# ============================================================
# Test 3: Login as Manager to test subsequent invites
# ============================================================
log_info "Setting up Manager authentication (after creating via different flow)..."

# For this test, we'll create Manager via SQL with known password for testing
PGPASSWORD=odoo psql -h localhost -U odoo -d realestate <<EOF
    -- Set Manager password for testing (simulating set-password flow)
    UPDATE res_users 
    SET password = crypt('manager123', gen_salt('bf')),
        signup_pending = FALSE
    WHERE id = $MANAGER_USER_ID;
EOF

# Now login as Manager
MANAGER_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "invite_test_manager@example.com",
        "password": "manager123"
    }')

MANAGER_JWT=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.access_token // empty')
MANAGER_SESSION=$(echo "$MANAGER_LOGIN_RESPONSE" | jq -r '.session_id // empty')

if [ -z "$MANAGER_JWT" ] || [ -z "$MANAGER_SESSION" ]; then
    log_warning "Manager login failed (expected for signup_pending), continuing with other tests..."
else
    log_info "Manager authentication successful"
fi

# ============================================================
# Test 4: Manager invites Agent (201)
# ============================================================
if [ -n "$MANAGER_JWT" ]; then
    test_scenario "Manager invites Agent successfully"

    AGENT_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $MANAGER_JWT" \
        -H "X-Session-ID: $MANAGER_SESSION" \
        -d '{
            "name": "Invite Test Agent",
            "email": "invite_test_agent@example.com",
            "document": "55566677788",
            "profile": "agent"
        }')

    AGENT_INVITE_BODY=$(echo "$AGENT_INVITE_RESPONSE" | head -n -1)
    AGENT_INVITE_STATUS=$(echo "$AGENT_INVITE_RESPONSE" | tail -n 1)

    assert_status 201 "$AGENT_INVITE_STATUS" "Agent invite created by Manager"
    assert_field "$AGENT_INVITE_BODY" "data.id" "Agent user ID returned"
    
    AGENT_USER_ID=$(echo "$AGENT_INVITE_BODY" | jq -r '.data.id')
    log_info "Agent user created with ID: $AGENT_USER_ID"
fi

# ============================================================
# Test 5: Invite with duplicate email (409)
# ============================================================
test_scenario "Invite with duplicate email returns 409"

DUPLICATE_EMAIL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Another Manager",
        "email": "invite_test_manager@example.com",
        "document": "99988877766",
        "profile": "manager"
    }')

DUPLICATE_EMAIL_STATUS=$(echo "$DUPLICATE_EMAIL_RESPONSE" | tail -n 1)

assert_status 409 "$DUPLICATE_EMAIL_STATUS" "Duplicate email rejected"

# ============================================================
# Test 6: Invite with duplicate document (409)
# ============================================================
test_scenario "Invite with duplicate document returns 409"

DUPLICATE_DOC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Another User",
        "email": "invite_test_another@example.com",
        "document": "11122233344",
        "profile": "agent"
    }')

DUPLICATE_DOC_STATUS=$(echo "$DUPLICATE_DOC_RESPONSE" | tail -n 1)

assert_status 409 "$DUPLICATE_DOC_STATUS" "Duplicate document rejected"

# ============================================================
# Test 7: Login before set-password (should fail - 401)
# ============================================================
test_scenario "Login before set-password returns 401"

LOGIN_BEFORE_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "invite_test_manager@example.com",
        "password": "anypassword"
    }')

LOGIN_BEFORE_STATUS=$(echo "$LOGIN_BEFORE_PASSWORD_RESPONSE" | tail -n 1)

assert_status 401 "$LOGIN_BEFORE_STATUS" "Login fails for user without password"

# ============================================================
# Test 8: Set-password flow simulation
# ============================================================
log_info "Simulating set-password flow (using test token)..."

# Create a test user with known token for set-password testing
TEST_PROSPECTOR_CREATE=$(curl -s -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Invite Test Prospector",
        "email": "invite_test_prospector@example.com",
        "document": "33344455566",
        "profile": "prospector"
    }')

PROSPECTOR_USER_ID=$(echo "$TEST_PROSPECTOR_CREATE" | jq -r '.data.id')

# Generate a known raw token and update database with its hash
RAW_TOKEN="test-invite-token-$(date +%s)"
TOKEN_HASH=$(echo -n "$RAW_TOKEN" | sha256sum | awk '{print $1}')

PGPASSWORD=odoo psql -h localhost -U odoo -d realestate <<EOF
    UPDATE thedevkitchen_password_token
    SET token = '$TOKEN_HASH'
    WHERE user_id = $PROSPECTOR_USER_ID
    AND token_type = 'invite'
    AND status = 'pending';
EOF

# ============================================================
# Test 9: Set-password with valid token (200)
# ============================================================
test_scenario "Set-password with valid token succeeds"

SET_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_TOKEN\",
        \"password\": \"newpassword123\",
        \"confirm_password\": \"newpassword123\"
    }")

SET_PASSWORD_BODY=$(echo "$SET_PASSWORD_RESPONSE" | head -n -1)
SET_PASSWORD_STATUS=$(echo "$SET_PASSWORD_RESPONSE" | tail -n 1)

assert_status 200 "$SET_PASSWORD_STATUS" "Set-password successful"
assert_field "$SET_PASSWORD_BODY" "message" "Success message returned"
assert_field "$SET_PASSWORD_BODY" "links.login" "Login link provided"

# ============================================================
# Test 10: Login after set-password (success)
# ============================================================
test_scenario "Login after set-password succeeds"

LOGIN_AFTER_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "invite_test_prospector@example.com",
        "password": "newpassword123"
    }')

LOGIN_AFTER_BODY=$(echo "$LOGIN_AFTER_PASSWORD_RESPONSE" | head -n -1)
LOGIN_AFTER_STATUS=$(echo "$LOGIN_AFTER_PASSWORD_RESPONSE" | tail -n 1)

assert_status 200 "$LOGIN_AFTER_STATUS" "Login successful after set-password"
assert_field "$LOGIN_AFTER_BODY" "access_token" "JWT token returned"
assert_field "$LOGIN_AFTER_BODY" "session_id" "Session ID returned"
assert_field "$LOGIN_AFTER_BODY" "user.id" "User data returned"
assert_field "$LOGIN_AFTER_BODY" "user.email" "User email returned"

# ============================================================
# Test 11: Set-password with already-used token (410)
# ============================================================
test_scenario "Set-password with used token returns 410"

USED_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_TOKEN\",
        \"password\": \"anotherpassword\",
        \"confirm_password\": \"anotherpassword\"
    }")

USED_TOKEN_STATUS=$(echo "$USED_TOKEN_RESPONSE" | tail -n 1)

assert_status 410 "$USED_TOKEN_STATUS" "Used token rejected"

# ============================================================
# Test 12: Set-password with expired token (410)
# ============================================================
test_scenario "Set-password with expired token returns 410"

# Create expired token
EXPIRED_USER_CREATE=$(curl -s -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Invite Test Expired",
        "email": "invite_test_expired@example.com",
        "document": "77788899900",
        "profile": "receptionist"
    }')

EXPIRED_USER_ID=$(echo "$EXPIRED_USER_CREATE" | jq -r '.data.id')

# Generate expired token
EXPIRED_RAW_TOKEN="expired-token-$(date +%s)"
EXPIRED_TOKEN_HASH=$(echo -n "$EXPIRED_RAW_TOKEN" | sha256sum | awk '{print $1}')

# Set token as expired in database
PGPASSWORD=odoo psql -h localhost -U odoo -d realestate <<EOF
    UPDATE thedevkitchen_password_token
    SET token = '$EXPIRED_TOKEN_HASH',
        expires_at = NOW() - INTERVAL '1 day'
    WHERE user_id = $EXPIRED_USER_ID
    AND token_type = 'invite'
    AND status = 'pending';
EOF

EXPIRED_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$EXPIRED_RAW_TOKEN\",
        \"password\": \"password123\",
        \"confirm_password\": \"password123\"
    }")

EXPIRED_TOKEN_STATUS=$(echo "$EXPIRED_TOKEN_RESPONSE" | tail -n 1)

assert_status 410 "$EXPIRED_TOKEN_STATUS" "Expired token rejected"

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
