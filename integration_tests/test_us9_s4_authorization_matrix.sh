#!/bin/bash
# Feature 009 - User Story 4 (US4): Authorization Matrix E2E Test
# Test scenarios for RBAC enforcement in user invitation
#
# Authorization Matrix:
# - Owner: Can invite all 9 profiles (owner, manager, director, agent, prospector, receptionist, financial, legal, portal)
# - Manager: Can invite 5 operational profiles (agent, prospector, receptionist, financial, legal)
# - Director: Inherits Manager permissions (5 operational profiles)
# - Agent: Can invite 2 profiles (owner, portal)
# - Prospector: Cannot invite anyone (403)
# - Receptionist: Cannot invite anyone (403)
# - Financial: Cannot invite anyone (403)
# - Legal: Cannot invite anyone (403)
# - Portal: Cannot invite anyone (403)
#
# Scenarios:
# 1. Owner invites each of 9 profiles (all 201)
# 2. Manager invites 5 operational profiles (all 201)
# 3. Manager tries to invite owner (403)
# 4. Manager tries to invite manager (403)
# 5. Manager tries to invite director (403)
# 6. Manager tries to invite portal (403)
# 7. Director invites 5 operational profiles (all 201)
# 8. Agent invites owner (201)
# 9. Agent invites portal (201)
# 10. Agent tries to invite manager (403)
# 11. Agent tries to invite agent (403)
# 12. Prospector tries to invite anyone (403)
# 13. Receptionist tries to invite anyone (403)
# 14. Financial tries to invite anyone (403)
# 15. Legal tries to invite anyone (403)
#
# Author: TheDevKitchen
# Date: 2026-02-16
# ADRs: ADR-003 (Testing Standards), ADR-011 (Security), ADR-017 (Multi-tenancy)

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

cleanup_test_data() {
    log_info "Cleaning up test data..."
    
    # SQL cleanup script
    docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
        -- Delete test users
        DELETE FROM res_users WHERE login LIKE 'rbac_test_%@example.com';
        
        -- Delete test partners
        DELETE FROM res_partner WHERE email LIKE 'rbac_test_%@example.com';
        
        -- Delete test tokens
        DELETE FROM thedevkitchen_password_token 
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'rbac_test_%@example.com'
        );
EOF
    
    log_info "Cleanup completed"
}

# Main test execution
echo "=========================================="
echo "Feature 009 - US4: Authorization Matrix E2E Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Cleanup before tests
cleanup_test_data

# ============================================================
# Prerequisite: Login as Owner to get auth tokens
# ============================================================
log_info "Setting up authentication as Owner..."

OWNER_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "'"$TEST_USER_OWNER"'",
        "password": "'"$TEST_PASSWORD_OWNER"'"
    }')

OWNER_JWT=$(echo "$OWNER_LOGIN" | jq -r '.access_token // empty')
OWNER_SESSION=$(echo "$OWNER_LOGIN" | jq -r '.session_id // empty')
OWNER_COMPANY=$(echo "$OWNER_LOGIN" | jq -r '.company_id // empty')

if [ -z "$OWNER_JWT" ] || [ -z "$OWNER_SESSION" ]; then
    log_error "Failed to authenticate as Owner"
    exit 1
fi

log_info "Owner authentication successful (Company: $OWNER_COMPANY)"

# ============================================================
# Test 1-9: Owner invites all 9 profiles (all 201)
# ============================================================
declare -a PROFILES=("owner" "manager" "director" "agent" "prospector" "receptionist" "financial" "legal" "portal")
COUNTER=1

for profile in "${PROFILES[@]}"; do
    test_scenario "Owner invites $profile (201)"
    
    # Build request body
    if [ "$profile" == "portal" ]; then
        REQUEST_BODY="{
            \"name\": \"RBAC Test $profile\",
            \"email\": \"rbac_test_owner_${profile}@example.com\",
            \"document\": \"5000000000$COUNTER\",
            \"profile\": \"$profile\",
            \"phone\": \"+5511988775544\",
            \"birthdate\": \"1990-01-01\",
            \"occupation\": \"Test\"
        }"
    else
        REQUEST_BODY="{
            \"name\": \"RBAC Test $profile\",
            \"email\": \"rbac_test_owner_${profile}@example.com\",
            \"document\": \"5000000000$COUNTER\",
            \"profile\": \"$profile\"
        }"
    fi
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OWNER_JWT" \
        -H "X-Session-ID: $OWNER_SESSION" \
        -d "$REQUEST_BODY")
    
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    assert_status 201 "$STATUS" "Owner can invite $profile"
    
    COUNTER=$((COUNTER + 1))
done

# ============================================================
# Prerequisite: Login as Manager
# ============================================================
log_info "Setting up authentication as Manager..."

MANAGER_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "manager@example.com",
        "password": "manager123"
    }')

MANAGER_JWT=$(echo "$MANAGER_LOGIN" | jq -r '.access_token // empty')
MANAGER_SESSION=$(echo "$MANAGER_LOGIN" | jq -r '.session_id // empty')

if [ -z "$MANAGER_JWT" ] || [ -z "$MANAGER_SESSION" ]; then
    log_error "Failed to authenticate as Manager"
    exit 1
fi

log_info "Manager authentication successful"

# ============================================================
# Test 10-14: Manager invites 5 operational profiles (all 201)
# ============================================================
declare -a MANAGER_ALLOWED=("agent" "prospector" "receptionist" "financial" "legal")
COUNTER=1

for profile in "${MANAGER_ALLOWED[@]}"; do
    test_scenario "Manager invites $profile (201)"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $MANAGER_JWT" \
        -H "X-Session-ID: $MANAGER_SESSION" \
        -d "{
            \"name\": \"RBAC Test Manager Invites $profile\",
            \"email\": \"rbac_test_manager_${profile}@example.com\",
            \"document\": \"6000000000$COUNTER\",
            \"profile\": \"$profile\"
        }")
    
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    assert_status 201 "$STATUS" "Manager can invite $profile"
    
    COUNTER=$((COUNTER + 1))
done

# ============================================================
# Test 15-18: Manager tries to invite forbidden profiles (403)
# ============================================================
declare -a MANAGER_FORBIDDEN=("owner" "manager" "director" "portal")
COUNTER=1

for profile in "${MANAGER_FORBIDDEN[@]}"; do
    test_scenario "Manager tries to invite $profile (403)"
    
    # Build request body
    if [ "$profile" == "portal" ]; then
        REQUEST_BODY="{
            \"name\": \"RBAC Test Manager Forbidden $profile\",
            \"email\": \"rbac_test_manager_forbidden_${profile}@example.com\",
            \"document\": \"7000000000$COUNTER\",
            \"profile\": \"$profile\",
            \"phone\": \"+5511988775544\",
            \"birthdate\": \"1990-01-01\"
        }"
    else
        REQUEST_BODY="{
            \"name\": \"RBAC Test Manager Forbidden $profile\",
            \"email\": \"rbac_test_manager_forbidden_${profile}@example.com\",
            \"document\": \"7000000000$COUNTER\",
            \"profile\": \"$profile\"
        }"
    fi
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $MANAGER_JWT" \
        -H "X-Session-ID: $MANAGER_SESSION" \
        -d "$REQUEST_BODY")
    
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    assert_status 403 "$STATUS" "Manager cannot invite $profile"
    
    COUNTER=$((COUNTER + 1))
done

# ============================================================
# Prerequisite: Login as Director
# ============================================================
log_info "Setting up authentication as Director..."

# First check if director exists, if not skip these tests
DIRECTOR_CHECK=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
    "SELECT COUNT(*) FROM res_users WHERE login = 'director@example.com';" | xargs)

if [ "$DIRECTOR_CHECK" == "0" ]; then
    log_warning "Director user does not exist, skipping Director tests"
    log_warning "Director should inherit Manager permissions (5 operational profiles)"
else
    DIRECTOR_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -d '{
            "login": "director@example.com",
            "password": "director123"
        }')

    DIRECTOR_JWT=$(echo "$DIRECTOR_LOGIN" | jq -r '.access_token // empty')
    DIRECTOR_SESSION=$(echo "$DIRECTOR_LOGIN" | jq -r '.session_id // empty')

    if [ -n "$DIRECTOR_JWT" ] && [ -n "$DIRECTOR_SESSION" ]; then
        log_info "Director authentication successful"

        # Test 19-23: Director invites 5 operational profiles (all 201)
        COUNTER=1
        for profile in "${MANAGER_ALLOWED[@]}"; do
            test_scenario "Director invites $profile (201)"
            
            RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $DIRECTOR_JWT" \
                -H "X-Session-ID: $DIRECTOR_SESSION" \
                -d "{
                    \"name\": \"RBAC Test Director Invites $profile\",
                    \"email\": \"rbac_test_director_${profile}@example.com\",
                    \"document\": \"8000000000$COUNTER\",
                    \"profile\": \"$profile\"
                }")
            
            STATUS=$(echo "$RESPONSE" | tail -n 1)
            assert_status 201 "$STATUS" "Director can invite $profile"
            
            COUNTER=$((COUNTER + 1))
        done
    else
        log_warning "Failed to authenticate as Director, skipping tests"
    fi
fi

# ============================================================
# Prerequisite: Login as Agent
# ============================================================
log_info "Setting up authentication as Agent..."

AGENT_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "agent@example.com",
        "password": "agent123"
    }')

AGENT_JWT=$(echo "$AGENT_LOGIN" | jq -r '.access_token // empty')
AGENT_SESSION=$(echo "$AGENT_LOGIN" | jq -r '.session_id // empty')

if [ -z "$AGENT_JWT" ] || [ -z "$AGENT_SESSION" ]; then
    log_error "Failed to authenticate as Agent"
    exit 1
fi

log_info "Agent authentication successful"

# ============================================================
# Test: Agent invites owner (201)
# ============================================================
test_scenario "Agent invites owner (201)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AGENT_JWT" \
    -H "X-Session-ID: $AGENT_SESSION" \
    -d '{
        "name": "RBAC Test Agent Invites Owner",
        "email": "rbac_test_agent_owner@example.com",
        "document": "90000000001",
        "profile": "owner"
    }')

STATUS=$(echo "$RESPONSE" | tail -n 1)
assert_status 201 "$STATUS" "Agent can invite owner"

# ============================================================
# Test: Agent invites portal (201)
# ============================================================
test_scenario "Agent invites portal (201)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AGENT_JWT" \
    -H "X-Session-ID: $AGENT_SESSION" \
    -d '{
        "name": "RBAC Test Agent Invites Portal",
        "email": "rbac_test_agent_portal@example.com",
        "document": "90000000002",
        "profile": "portal",
        "phone": "+5511988775544",
        "birthdate": "1990-01-01",
        "occupation": "Tenant"
    }')

STATUS=$(echo "$RESPONSE" | tail -n 1)
assert_status 201 "$STATUS" "Agent can invite portal"

# ============================================================
# Test: Agent tries to invite forbidden profiles (403)
# ============================================================
declare -a AGENT_FORBIDDEN=("manager" "director" "agent" "prospector" "receptionist" "financial" "legal")
COUNTER=1

for profile in "${AGENT_FORBIDDEN[@]}"; do
    test_scenario "Agent tries to invite $profile (403)"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $AGENT_JWT" \
        -H "X-Session-ID: $AGENT_SESSION" \
        -d "{
            \"name\": \"RBAC Test Agent Forbidden $profile\",
            \"email\": \"rbac_test_agent_forbidden_${profile}@example.com\",
            \"document\": \"9100000000$COUNTER\",
            \"profile\": \"$profile\"
        }")
    
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    assert_status 403 "$STATUS" "Agent cannot invite $profile"
    
    COUNTER=$((COUNTER + 1))
done

# ============================================================
# Test: Restricted profiles cannot invite anyone (403)
# ============================================================
declare -a RESTRICTED_PROFILES=("prospector" "receptionist" "financial" "legal")

for restricted_profile in "${RESTRICTED_PROFILES[@]}"; do
    # Try to login as restricted profile
    log_info "Testing $restricted_profile authorization..."
    
    RESTRICTED_LOGIN=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"login\": \"${restricted_profile}@example.com\",
            \"password\": \"${restricted_profile}123\"
        }")
    
    RESTRICTED_JWT=$(echo "$RESTRICTED_LOGIN" | jq -r '.access_token // empty')
    RESTRICTED_SESSION=$(echo "$RESTRICTED_LOGIN" | jq -r '.session_id // empty')
    
    if [ -z "$RESTRICTED_JWT" ] || [ -z "$RESTRICTED_SESSION" ]; then
        log_warning "Failed to authenticate as $restricted_profile, skipping"
        continue
    fi
    
    # Try to invite agent (should be 403)
    test_scenario "$restricted_profile tries to invite agent (403)"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $RESTRICTED_JWT" \
        -H "X-Session-ID: $RESTRICTED_SESSION" \
        -d "{
            \"name\": \"RBAC Test ${restricted_profile} Forbidden\",
            \"email\": \"rbac_test_${restricted_profile}_forbidden@example.com\",
            \"document\": \"9200000000$((COUNTER++))\",
            \"profile\": \"agent\"
        }")
    
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    assert_status 403 "$STATUS" "$restricted_profile cannot invite anyone"
done

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
