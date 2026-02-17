#!/bin/bash
# Feature 009 - User Story 3 (US3): Portal Dual Record E2E Test
# Test scenarios for portal user creation with dual record (res.users + real.estate.tenant)
#
# Scenarios:
# 1. Agent invites portal tenant with all required fields (201 + tenant_id)
# 2. Verify real.estate.tenant record exists with correct partner_id linkage
# 3. Portal invite missing phone (400)
# 4. Portal invite missing birthdate (400)
# 5. Portal invite missing company_id (400)
# 6. Portal invite with existing document for unlinked tenant (409)
# 7. Portal user set-password and login (success)
# 8. Verify portal user has portal group only
# 9. Verify tenant record has correct company isolation
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
        -- Delete test tenants
        DELETE FROM real_estate_tenant WHERE email LIKE 'portal_test_%@example.com';
        
        -- Delete test users
        DELETE FROM res_users WHERE login LIKE 'portal_test_%@example.com';
        
        -- Delete test partners
        DELETE FROM res_partner WHERE email LIKE 'portal_test_%@example.com';
        
        -- Delete test tokens
        DELETE FROM thedevkitchen_password_token 
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'portal_test_%@example.com'
        );
EOF
    
    log_info "Cleanup completed"
}

# Main test execution
echo "=========================================="
echo "Feature 009 - US3: Portal Dual Record E2E Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Cleanup before tests
cleanup_test_data

# ============================================================
# Prerequisite: Login as Agent to get auth tokens
# ============================================================
log_info "Setting up authentication as Agent..."

LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "agent@example.com",
        "password": "agent123"
    }')

SESSION_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.session_id // empty')
AGENT_COMPANY_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.company_id // empty')

if [ -z "$JWT_TOKEN" ] || [ -z "$SESSION_ID" ]; then
    log_error "Failed to authenticate as Agent. Please ensure agent@example.com exists with password agent123"
    exit 1
fi

log_info "Agent authentication successful (Company ID: $AGENT_COMPANY_ID)"

# ============================================================
# Test 1: Portal invite missing phone (400)
# ============================================================
test_scenario "Portal invite missing phone returns 400"

MISSING_PHONE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Portal Test Missing Phone",
        "email": "portal_test_missing_phone@example.com",
        "document": "11111111111",
        "profile": "portal",
        "birthdate": "1990-01-01"
    }')

MISSING_PHONE_BODY=$(echo "$MISSING_PHONE_RESPONSE" | head -n -1)
MISSING_PHONE_STATUS=$(echo "$MISSING_PHONE_RESPONSE" | tail -n 1)

assert_status 400 "$MISSING_PHONE_STATUS" "Portal invite without phone rejected"

# ============================================================
# Test 2: Portal invite missing birthdate (400)
# ============================================================
test_scenario "Portal invite missing birthdate returns 400"

MISSING_BIRTHDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Portal Test Missing Birthdate",
        "email": "portal_test_missing_birthdate@example.com",
        "document": "22222222222",
        "profile": "portal",
        "phone": "+5511999887766"
    }')

MISSING_BIRTHDATE_BODY=$(echo "$MISSING_BIRTHDATE_RESPONSE" | head -n -1)
MISSING_BIRTHDATE_STATUS=$(echo "$MISSING_BIRTHDATE_RESPONSE" | tail -n 1)

assert_status 400 "$MISSING_BIRTHDATE_STATUS" "Portal invite without birthdate rejected"

# ============================================================
# Test 3: Agent invites portal tenant with all required fields (201)
# ============================================================
test_scenario "Agent invites portal tenant with all required fields"

PORTAL_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Portal Test Tenant",
        "email": "portal_test_tenant@example.com",
        "document": "33333333333",
        "profile": "portal",
        "phone": "+5511988776655",
        "birthdate": "1985-05-15",
        "occupation": "Software Engineer"
    }')

PORTAL_INVITE_BODY=$(echo "$PORTAL_INVITE_RESPONSE" | head -n -1)
PORTAL_INVITE_STATUS=$(echo "$PORTAL_INVITE_RESPONSE" | tail -n 1)

assert_status 201 "$PORTAL_INVITE_STATUS" "Portal tenant invite created"
assert_field "$PORTAL_INVITE_BODY" "data.id" "User ID returned"
assert_field "$PORTAL_INVITE_BODY" "data.email" "Email field present"
assert_field "$PORTAL_INVITE_BODY" "data.profile" "Profile field present"
TENANT_ID=$(assert_field "$PORTAL_INVITE_BODY" "data.tenant_id" "Tenant ID returned")

PORTAL_USER_ID=$(echo "$PORTAL_INVITE_BODY" | jq -r '.data.id')
log_info "Portal user created with ID: $PORTAL_USER_ID, Tenant ID: $TENANT_ID"

# ============================================================
# Test 4: Verify real.estate.tenant record exists
# ============================================================
test_scenario "Verify real.estate.tenant record exists with correct linkage"

# Check tenant record exists
assert_sql_result \
    "SELECT COUNT(*) FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "1" \
    "Tenant record exists"

# Check partner_id linkage
USER_PARTNER_ID=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
    "SELECT partner_id FROM res_users WHERE id = $PORTAL_USER_ID;" | xargs)

TENANT_PARTNER_ID=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
    "SELECT partner_id FROM real_estate_tenant WHERE id = $TENANT_ID;" | xargs)

log_info "User partner_id: $USER_PARTNER_ID, Tenant partner_id: $TENANT_PARTNER_ID"

assert_sql_result \
    "SELECT CASE WHEN $USER_PARTNER_ID = $TENANT_PARTNER_ID THEN 'true' ELSE 'false' END;" \
    "true" \
    "User and tenant share same partner_id"

# Check tenant document
assert_sql_result \
    "SELECT document FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "33333333333" \
    "Tenant document matches invite data"

# Check tenant phone
assert_sql_result \
    "SELECT phone FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "+5511988776655" \
    "Tenant phone matches invite data"

# Check tenant birthdate
assert_sql_result \
    "SELECT birthdate::text FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "1985-05-15" \
    "Tenant birthdate matches invite data"

# Check tenant occupation
assert_sql_result \
    "SELECT occupation FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "Software Engineer" \
    "Tenant occupation matches invite data"

# ============================================================
# Test 5: Verify tenant has correct company isolation
# ============================================================
test_scenario "Verify tenant has correct company isolation"

assert_sql_result \
    "SELECT company_id FROM real_estate_tenant WHERE id = $TENANT_ID;" \
    "$AGENT_COMPANY_ID" \
    "Tenant belongs to agent's company"

# ============================================================
# Test 6: Verify portal user has portal group only
# ============================================================
test_scenario "Verify portal user has portal group only"

# Get portal group ID
PORTAL_GROUP_ID=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
    "SELECT id FROM res_groups WHERE category_id = (SELECT id FROM ir_module_category WHERE name = 'Technical') AND name = 'Portal';" | xargs)

if [ -z "$PORTAL_GROUP_ID" ]; then
    # Fallback: get portal group by XML ID
    PORTAL_GROUP_ID=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
        "SELECT res_id FROM ir_model_data WHERE model = 'res.groups' AND name = 'group_portal';" | xargs)
fi

log_info "Portal group ID: $PORTAL_GROUP_ID"

# Check user has portal group
assert_sql_result \
    "SELECT COUNT(*) FROM res_groups_users_rel WHERE gid = $PORTAL_GROUP_ID AND uid = $PORTAL_USER_ID;" \
    "1" \
    "User has portal group assigned"

# ============================================================
# Test 7: Portal invite with existing document for unlinked tenant (409)
# ============================================================
test_scenario "Portal invite with existing document for unlinked tenant returns 409"

# First, create an unlinked tenant in database (tenant without res.users)
docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
    INSERT INTO res_partner (name, email, phone, company_id, create_date, write_date)
    VALUES ('Unlinked Tenant Partner', 'portal_test_unlinked@example.com', '+5511999887766', $AGENT_COMPANY_ID, NOW(), NOW())
    RETURNING id;
    
    INSERT INTO real_estate_tenant (partner_id, document, email, phone, birthdate, company_id, create_date, write_date)
    SELECT id, '44444444444', 'portal_test_unlinked@example.com', '+5511999887766', '1990-01-01', $AGENT_COMPANY_ID, NOW(), NOW()
    FROM res_partner WHERE email = 'portal_test_unlinked@example.com';
EOF

# Try to invite with same document
EXISTING_DOC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{
        "name": "Another Portal User",
        "email": "portal_test_another@example.com",
        "document": "44444444444",
        "profile": "portal",
        "phone": "+5511988775544",
        "birthdate": "1992-03-20"
    }')

EXISTING_DOC_STATUS=$(echo "$EXISTING_DOC_RESPONSE" | tail -n 1)

assert_status 409 "$EXISTING_DOC_STATUS" "Duplicate document for existing tenant rejected"

# ============================================================
# Test 8: Portal user set-password and login
# ============================================================
log_info "Simulating set-password flow for portal user..."

# Generate known token for portal user
RAW_PORTAL_TOKEN="portal-invite-token-$(date +%s)"
PORTAL_TOKEN_HASH=$(echo -n "$RAW_PORTAL_TOKEN" | sha256sum | awk '{print $1}')

docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
    UPDATE thedevkitchen_password_token
    SET token = '$PORTAL_TOKEN_HASH'
    WHERE user_id = $PORTAL_USER_ID
    AND token_type = 'invite'
    AND status = 'pending';
EOF

test_scenario "Portal user set-password succeeds"

PORTAL_SET_PASSWORD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$RAW_PORTAL_TOKEN\",
        \"password\": \"portalpassword123\",
        \"confirm_password\": \"portalpassword123\"
    }")

PORTAL_SET_PASSWORD_STATUS=$(echo "$PORTAL_SET_PASSWORD_RESPONSE" | tail -n 1)

assert_status 200 "$PORTAL_SET_PASSWORD_STATUS" "Portal user set-password successful"

test_scenario "Portal user login after set-password succeeds"

PORTAL_LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -d '{
        "login": "portal_test_tenant@example.com",
        "password": "portalpassword123"
    }')

PORTAL_LOGIN_BODY=$(echo "$PORTAL_LOGIN_RESPONSE" | head -n -1)
PORTAL_LOGIN_STATUS=$(echo "$PORTAL_LOGIN_RESPONSE" | tail -n 1)

assert_status 200 "$PORTAL_LOGIN_STATUS" "Portal user login successful"
assert_field "$PORTAL_LOGIN_BODY" "access_token" "JWT token returned"
assert_field "$PORTAL_LOGIN_BODY" "session_id" "Session ID returned"
assert_field "$PORTAL_LOGIN_BODY" "user.id" "User data returned"
assert_field "$PORTAL_LOGIN_BODY" "user.email" "User email returned"

# Verify profile is portal
PORTAL_PROFILE=$(echo "$PORTAL_LOGIN_BODY" | jq -r '.user.profile // empty')
if [ "$PORTAL_PROFILE" == "portal" ]; then
    echo -e "  ${GREEN}✓${NC} User profile is 'portal'"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "  ${RED}✗${NC} Expected profile 'portal' but got '$PORTAL_PROFILE'"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

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
