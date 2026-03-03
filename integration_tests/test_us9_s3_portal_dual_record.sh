#!/bin/bash
# Feature 009/010 - US3: Portal Profile Creation and Invite Flow E2E Test
# Updated: 2026-03-03 — Migrated from real.estate.tenant to thedevkitchen.estate.profile
# Context: Feature 010 removed real.estate.tenant (ADR-024 Profile Unification).
#          Portal users are now thedevkitchen.estate.profile with profile_type=9 (tenant).
#
# Scenarios:
# 1. Profile creation missing birthdate (400)
# 2. Profile creation missing document (400)
# 3. Create tenant profile + invite with profile_id (201)
# 4. Verify thedevkitchen.estate.profile record exists with correct data
# 5. Verify portal user belongs to correct company
# 6. Verify portal user has portal group only
# 7. Duplicate document on same company+type (409)
# 8. Portal user set-password and login (success)
#
# Author: TheDevKitchen
# ADRs: ADR-003 (Testing Standards), ADR-011 (Security), ADR-017 (Multi-tenancy), ADR-024 (Profile Unification)

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

RUN_ID="$(date +%s)"
CPF_COUNTER=0

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

next_cpf() {
    CPF_COUNTER=$((CPF_COUNTER + 1))
    python3 -c "
import random, time
random.seed(int(time.time() * 1000) + $CPF_COUNTER + $RANDOM)
def gen():
    nums = [random.randint(0,9) for _ in range(9)]
    s = sum((10-i)*d for i,d in enumerate(nums))
    d1 = 0 if (11-(s%11))>=10 else (11-(s%11))
    nums.append(d1)
    s = sum((11-i)*d for i,d in enumerate(nums))
    d2 = 0 if (11-(s%11))>=10 else (11-(s%11))
    nums.append(d2)
    cpf = ''.join(map(str,nums))
    if len(set(cpf))==1: return None
    return cpf
result = None
while not result:
    result = gen()
print(result)
"
}

next_email() {
    local prefix="$1"
    echo "portal_test_${prefix}_${RUN_ID}@example.com"
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

    docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
        DELETE FROM thedevkitchen_password_token
        WHERE user_id IN (
            SELECT id FROM res_users WHERE login LIKE 'portal_test_%@example.com'
        );
        DELETE FROM thedevkitchen_estate_profile WHERE email LIKE 'portal_test_%@example.com';
        DELETE FROM res_users WHERE login LIKE 'portal_test_%@example.com';
        DELETE FROM res_partner WHERE email LIKE 'portal_test_%@example.com';
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
# Prerequisite: Login as Owner to get auth tokens
# ============================================================
log_info "Setting up authentication as Owner..."

OAUTH_RESPONSE=$(curl -s -X POST "$API_BASE/auth/token" \
    -H "Content-Type: application/json" \
    -d "{
        \"client_id\": \"$OAUTH_CLIENT_ID\",
        \"client_secret\": \"$OAUTH_CLIENT_SECRET\",
        \"grant_type\": \"client_credentials\"
    }")

BEARER_TOKEN=$(echo "$OAUTH_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$BEARER_TOKEN" ]; then
    log_error "Failed to obtain OAuth token"
    echo "Response: $OAUTH_RESPONSE"
    exit 1
fi

LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d "{
        \"login\": \"$TEST_USER_OWNER\",
        \"password\": \"$TEST_PASSWORD_OWNER\"
    }")

SESSION_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.session_id // empty')
AGENT_COMPANY_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.default_company_id // empty')

if [ -z "$SESSION_ID" ] || [ -z "$AGENT_COMPANY_ID" ]; then
    log_error "Failed to authenticate as Owner. Check TEST_USER_OWNER/TEST_PASSWORD_OWNER in 18.0/.env"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

log_info "Owner authentication successful (Company ID: $AGENT_COMPANY_ID)"

# ============================================================
# Test 1: Profile creation missing birthdate → 400
# ============================================================
test_scenario "Profile creation missing birthdate returns 400"

MISSING_BIRTHDATE_PROFILE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $SESSION_ID" \
    -H "X-Company-ID: $AGENT_COMPANY_ID" \
    -d "{
        \"profile_type_id\": 9,
        \"company_id\": $AGENT_COMPANY_ID,
        \"name\": \"Portal Test Missing Birthdate\",
        \"document\": \"$(next_cpf)\",
        \"email\": \"$(next_email missing_birthdate)\",
        \"phone\": \"+5511999887766\"
    }")

MISSING_BIRTHDATE_STATUS=$(echo "$MISSING_BIRTHDATE_PROFILE_RESPONSE" | tail -n 1)
assert_status 400 "$MISSING_BIRTHDATE_STATUS" "Profile without birthdate rejected"

# ============================================================
# Test 2: Profile creation missing document → 400
# ============================================================
test_scenario "Profile creation missing document returns 400"

MISSING_DOC_PROFILE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $SESSION_ID" \
    -H "X-Company-ID: $AGENT_COMPANY_ID" \
    -d "{
        \"profile_type_id\": 9,
        \"company_id\": $AGENT_COMPANY_ID,
        \"name\": \"Portal Test Missing Document\",
        \"email\": \"$(next_email missing_doc)\",
        \"phone\": \"+5511999887766\",
        \"birthdate\": \"1990-01-01\"
    }")

MISSING_DOC_STATUS=$(echo "$MISSING_DOC_PROFILE_RESPONSE" | tail -n 1)
assert_status 400 "$MISSING_DOC_STATUS" "Profile without document rejected"

# ============================================================
# Test 3: Create tenant profile + invite with profile_id (201)
# ============================================================
test_scenario "Create tenant profile and invite with profile_id"

TENANT_EMAIL="$(next_email tenant)"
TENANT_DOCUMENT="$(next_cpf)"

# Step 3a: Create the tenant profile
PROFILE_CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $SESSION_ID" \
    -H "X-Company-ID: $AGENT_COMPANY_ID" \
    -d "{
        \"profile_type_id\": 9,
        \"company_id\": $AGENT_COMPANY_ID,
        \"name\": \"Portal Test Tenant\",
        \"document\": \"$TENANT_DOCUMENT\",
        \"email\": \"$TENANT_EMAIL\",
        \"phone\": \"+5511988776655\",
        \"birthdate\": \"1985-05-15\",
        \"occupation\": \"Software Engineer\"
    }")

PROFILE_CREATE_BODY=$(echo "$PROFILE_CREATE_RESPONSE" | sed '$d')
PROFILE_CREATE_STATUS=$(echo "$PROFILE_CREATE_RESPONSE" | tail -n 1)

assert_status 201 "$PROFILE_CREATE_STATUS" "Tenant profile created"
assert_field "$PROFILE_CREATE_BODY" "id" "Profile ID returned"

TENANT_PROFILE_ID=$(echo "$PROFILE_CREATE_BODY" | jq -r '.id')
log_info "Tenant profile created with ID: $TENANT_PROFILE_ID"

# Step 3b: Invite the profile
PORTAL_INVITE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $SESSION_ID" \
    -H "X-Company-ID: $AGENT_COMPANY_ID" \
    -d "{
        \"profile_id\": $TENANT_PROFILE_ID
    }")

PORTAL_INVITE_BODY=$(echo "$PORTAL_INVITE_RESPONSE" | sed '$d')
PORTAL_INVITE_STATUS=$(echo "$PORTAL_INVITE_RESPONSE" | tail -n 1)

assert_status 201 "$PORTAL_INVITE_STATUS" "Portal tenant invite created"
assert_field "$PORTAL_INVITE_BODY" "data.id" "User ID returned"
assert_field "$PORTAL_INVITE_BODY" "data.email" "Email field present"
assert_field "$PORTAL_INVITE_BODY" "data.profile" "Profile field present"
assert_field "$PORTAL_INVITE_BODY" "data.profile_id" "Profile ID returned"

PORTAL_USER_ID=$(echo "$PORTAL_INVITE_BODY" | jq -r '.data.id')
RETURNED_PROFILE_ID=$(echo "$PORTAL_INVITE_BODY" | jq -r '.data.profile_id')
log_info "Portal user created with ID: $PORTAL_USER_ID, Profile ID: $RETURNED_PROFILE_ID"

# ============================================================
# Test 4: Verify thedevkitchen.estate.profile record exists
# ============================================================
test_scenario "Verify thedevkitchen.estate.profile record exists with correct data"

assert_sql_result \
    "SELECT COUNT(*) FROM thedevkitchen_estate_profile WHERE id = $TENANT_PROFILE_ID;" \
    "1" \
    "Profile record exists in DB"

assert_sql_result \
    "SELECT document FROM thedevkitchen_estate_profile WHERE id = $TENANT_PROFILE_ID;" \
    "$TENANT_DOCUMENT" \
    "Profile document matches"

assert_sql_result \
    "SELECT TRIM(email) FROM thedevkitchen_estate_profile WHERE id = $TENANT_PROFILE_ID;" \
    "$TENANT_EMAIL" \
    "Profile email matches"

assert_sql_result \
    "SELECT TRIM(phone) FROM thedevkitchen_estate_profile WHERE id = $TENANT_PROFILE_ID;" \
    "+5511988776655" \
    "Profile phone matches"

assert_sql_result \
    "SELECT birthdate::text FROM thedevkitchen_estate_profile WHERE id = $TENANT_PROFILE_ID;" \
    "1985-05-15" \
    "Profile birthdate matches"

# ============================================================
# Test 5: Verify portal user has correct company
# ============================================================
test_scenario "Verify portal user belongs to owner's company"

assert_sql_result \
    "SELECT company_id FROM res_users WHERE id = $PORTAL_USER_ID;" \
    "$AGENT_COMPANY_ID" \
    "Portal user belongs to owner's company"

# ============================================================
# Test 6: Verify portal user has portal group
# ============================================================
test_scenario "Verify portal user has portal group assigned"

# Invite controller assigns base.group_portal (Odoo standard portal)
PORTAL_GROUP_ID=$(docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -t -c \
    "SELECT res_id FROM ir_model_data WHERE model = 'res.groups' AND module = 'base' AND name = 'group_portal';" | xargs)

log_info "Portal group ID: $PORTAL_GROUP_ID"

assert_sql_result \
    "SELECT COUNT(*) FROM res_groups_users_rel WHERE gid = $PORTAL_GROUP_ID AND uid = $PORTAL_USER_ID;" \
    "1" \
    "User has portal group assigned"

# ============================================================
# Test 7: Duplicate profile (same document+company+type) returns 409
# ============================================================
test_scenario "Duplicate profile creation (same document+company+type) returns 409"

DUPLICATE_PROFILE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $SESSION_ID" \
    -H "X-Company-ID: $AGENT_COMPANY_ID" \
    -d "{
        \"profile_type_id\": 9,
        \"company_id\": $AGENT_COMPANY_ID,
        \"name\": \"Portal Test Tenant Duplicate\",
        \"document\": \"$TENANT_DOCUMENT\",
        \"email\": \"$(next_email dup)\",
        \"phone\": \"+5511988775544\",
        \"birthdate\": \"1992-03-20\"
    }")

DUPLICATE_PROFILE_STATUS=$(echo "$DUPLICATE_PROFILE_RESPONSE" | tail -n 1)
assert_status 409 "$DUPLICATE_PROFILE_STATUS" "Duplicate profile document+company+type rejected"

# ============================================================
# Test 8: Portal user set-password succeeds
# ============================================================
log_info "Simulating set-password flow for portal user..."

RAW_PORTAL_TOKEN=$(python3 -c 'import uuid; print(uuid.uuid4().hex)')
PORTAL_TOKEN_HASH=$(echo -n "$RAW_PORTAL_TOKEN" | shasum -a 256 | awk '{print $1}')

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

# ============================================================
# Test 9: Portal user login after set-password
# ============================================================
test_scenario "Portal user login after set-password succeeds"

PORTAL_LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d "{
        \"login\": \"$TENANT_EMAIL\",
        \"password\": \"portalpassword123\"
    }")

PORTAL_LOGIN_BODY=$(echo "$PORTAL_LOGIN_RESPONSE" | sed '$d')
PORTAL_LOGIN_STATUS=$(echo "$PORTAL_LOGIN_RESPONSE" | tail -n 1)

assert_status 200 "$PORTAL_LOGIN_STATUS" "Portal user login successful"
assert_field "$PORTAL_LOGIN_BODY" "session_id" "Session ID returned"
assert_field "$PORTAL_LOGIN_BODY" "user.id" "User data returned"
assert_field "$PORTAL_LOGIN_BODY" "user.email" "User email returned"

# ============================================================
# Test Summary
# ============================================================
echo ""
echo "=========================================="
echo "Test Summary - US9-S3 Portal Dual Record"
echo "=========================================="
echo "Tests Run:    $TESTS_RUN scenarios"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED assertions${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED assertions${NC}"
echo "=========================================="

# Cleanup after tests
cleanup_test_data

# Exit with appropriate code
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ TEST FAILED: US9-S3 Portal Profile and Invite Flow${NC}"
    exit 1
else
    echo -e "${GREEN}✅ TEST PASSED: US9-S3 Portal Profile and Invite Flow${NC}"
    exit 0
fi
