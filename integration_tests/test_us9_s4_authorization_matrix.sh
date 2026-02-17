#!/bin/bash
# Feature 009 - User Story 4 (US4): Authorization Matrix E2E Test

set -e

if [ -f "../18.0/.env" ]; then
    source ../18.0/.env
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="${BASE_URL}/api/v1"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

RUN_ID="$(date +%s)"
CPF_COUNTER=100000
EMAIL_COUNTER=0

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }

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
        if [ -n "$BODY" ]; then
            echo "  Body: $BODY"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

split_body_and_status() {
    local response="$1"
    BODY="$(echo "$response" | sed '$d')"
    STATUS="$(echo "$response" | tail -n 1)"
}

generate_valid_cpf() {
    local seed="$1"
    local base
    base=$(printf "%09d" "$seed")

    local sum=0 d1 d2 i digit weight
    for ((i=0; i<9; i++)); do
        digit=${base:$i:1}
        weight=$((10 - i))
        sum=$((sum + digit * weight))
    done
    d1=$((11 - (sum % 11)))
    if [ "$d1" -ge 10 ]; then d1=0; fi

    sum=0
    for ((i=0; i<9; i++)); do
        digit=${base:$i:1}
        weight=$((11 - i))
        sum=$((sum + digit * weight))
    done
    sum=$((sum + d1 * 2))
    d2=$((11 - (sum % 11)))
    if [ "$d2" -ge 10 ]; then d2=0; fi

    echo "${base}${d1}${d2}"
}

next_cpf() {
    CPF_COUNTER=$((CPF_COUNTER + 1))
    local seed=$(( (RUN_ID + CPF_COUNTER + RANDOM) % 900000000 + 100000000 ))
    generate_valid_cpf "$seed"
}

next_email() {
    local prefix="$1"
    EMAIL_COUNTER=$((EMAIL_COUNTER + 1))
    echo "rbac_test_${prefix}_${RUN_ID}_${EMAIL_COUNTER}@example.com"
}

cleanup_test_data() {
    log_info "Cleaning up test data..."
    docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
        DELETE FROM res_users WHERE login LIKE 'rbac_test_%@example.com' OR login LIKE 'rbac_bootstrap_%@example.com';
        DELETE FROM res_partner WHERE email LIKE 'rbac_test_%@example.com' OR email LIKE 'rbac_bootstrap_%@example.com';
        DELETE FROM thedevkitchen_password_token
        WHERE user_id IN (
            SELECT id FROM res_users
            WHERE login LIKE 'rbac_test_%@example.com' OR login LIKE 'rbac_bootstrap_%@example.com'
        );
EOF
    log_info "Cleanup completed"
}

get_oauth_token() {
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
}

login_user() {
    local login="$1"
    local password="$2"

    local response
    response=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{
            \"login\": \"$login\",
            \"password\": \"$password\"
        }")

    local session_id
    session_id=$(echo "$response" | jq -r '.session_id // empty')
    local company_id
    company_id=$(echo "$response" | jq -r '.user.default_company_id // empty')

    if [ -z "$session_id" ] || [ -z "$company_id" ]; then
        echo ""
        return 1
    fi

    echo "$session_id|$company_id"
}

invite_user() {
    local jwt="$1"
    local session_id="$2"
    local company_id="$3"
    local profile="$4"
    local name="$5"
    local email="$6"
    local document="$7"
    local expected_status="$8"

    local payload
    if [ "$profile" = "portal" ]; then
        payload="{
            \"name\": \"$name\",
            \"email\": \"$email\",
            \"document\": \"$document\",
            \"profile\": \"portal\",
            \"company_id\": $company_id,
            \"phone\": \"+5511988776655\",
            \"birthdate\": \"1990-01-01\",
            \"occupation\": \"Tenant\"
        }"
    else
        payload="{
            \"name\": \"$name\",
            \"email\": \"$email\",
            \"document\": \"$document\",
            \"profile\": \"$profile\"
        }"
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt" \
        -H "X-Openerp-Session-Id: $session_id" \
        -H "X-Company-ID: $company_id" \
        -d "$payload")

    split_body_and_status "$response"
    assert_status "$expected_status" "$STATUS" "Invite $profile by $name"

    if [ "$STATUS" -eq 201 ]; then
        LAST_USER_ID=$(echo "$BODY" | jq -r '.data.id // empty')
    else
        LAST_USER_ID=""
    fi
}

set_password_for_invited_user() {
    local user_id="$1"
    local password="$2"

    local raw_token="s4-${user_id}-${RUN_ID}-$(date +%s%N)"
    local token_hash
    token_hash=$(printf "%s" "$raw_token" | shasum -a 256 | awk '{print $1}')

    docker compose -f ../18.0/docker-compose.yml exec -T db psql -U odoo -d realestate <<EOF
        WITH latest AS (
            SELECT id
            FROM thedevkitchen_password_token
            WHERE user_id = $user_id AND token_type = 'invite' AND status = 'pending'
            ORDER BY create_date DESC
            LIMIT 1
        )
        UPDATE thedevkitchen_password_token
        SET token = '$token_hash'
        WHERE id IN (SELECT id FROM latest);
EOF

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
        -H "Content-Type: application/json" \
        -d "{
            \"token\": \"$raw_token\",
            \"password\": \"$password\",
            \"confirm_password\": \"$password\"
        }")

    split_body_and_status "$response"
    if [ "$STATUS" -ne 200 ]; then
        log_error "Failed to set password for user $user_id (status $STATUS)"
        echo "Body: $BODY"
        exit 1
    fi
}

bootstrap_user() {
    local profile="$1"
    local email="$2"
    local password="$3"
    local name="$4"

    local document
    document=$(next_cpf)
    invite_user "$OWNER_JWT" "$OWNER_SESSION" "$OWNER_COMPANY" "$profile" "$name" "$email" "$document" 201

    if [ -z "$LAST_USER_ID" ]; then
        log_error "Bootstrap failed for $profile ($email): missing user id"
        exit 1
    fi

    set_password_for_invited_user "$LAST_USER_ID" "$password"
}

echo "=========================================="
echo "Feature 009 - US4: Authorization Matrix E2E Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

cleanup_test_data
get_oauth_token

OWNER_LOGIN_DATA=$(login_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER") || {
    log_error "Failed to authenticate as Owner"
    exit 1
}
OWNER_SESSION="${OWNER_LOGIN_DATA%%|*}"
OWNER_COMPANY="${OWNER_LOGIN_DATA##*|}"
OWNER_JWT="$BEARER_TOKEN"
log_info "Owner authentication successful (Company: $OWNER_COMPANY)"

MANAGER_EMAIL="rbac_bootstrap_manager@example.com"
MANAGER_PASSWORD="Manager123!"
DIRECTOR_EMAIL="rbac_bootstrap_director@example.com"
DIRECTOR_PASSWORD="Director123!"
AGENT_EMAIL="rbac_bootstrap_agent@example.com"
AGENT_PASSWORD="Agent123!"

PROSPECTOR_EMAIL="rbac_bootstrap_prospector@example.com"
PROSPECTOR_PASSWORD="Prospector123!"
RECEPTIONIST_EMAIL="rbac_bootstrap_receptionist@example.com"
RECEPTIONIST_PASSWORD="Receptionist123!"
FINANCIAL_EMAIL="rbac_bootstrap_financial@example.com"
FINANCIAL_PASSWORD="Financial123!"
LEGAL_EMAIL="rbac_bootstrap_legal@example.com"
LEGAL_PASSWORD="Legal123!"

log_info "Bootstrapping deterministic role users..."
bootstrap_user "manager" "$MANAGER_EMAIL" "$MANAGER_PASSWORD" "RBAC Bootstrap Manager"
bootstrap_user "director" "$DIRECTOR_EMAIL" "$DIRECTOR_PASSWORD" "RBAC Bootstrap Director"
bootstrap_user "agent" "$AGENT_EMAIL" "$AGENT_PASSWORD" "RBAC Bootstrap Agent"
bootstrap_user "prospector" "$PROSPECTOR_EMAIL" "$PROSPECTOR_PASSWORD" "RBAC Bootstrap Prospector"
bootstrap_user "receptionist" "$RECEPTIONIST_EMAIL" "$RECEPTIONIST_PASSWORD" "RBAC Bootstrap Receptionist"
bootstrap_user "financial" "$FINANCIAL_EMAIL" "$FINANCIAL_PASSWORD" "RBAC Bootstrap Financial"
bootstrap_user "legal" "$LEGAL_EMAIL" "$LEGAL_PASSWORD" "RBAC Bootstrap Legal"

MANAGER_LOGIN_DATA=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASSWORD") || { log_error "Manager login failed"; exit 1; }
MANAGER_SESSION="${MANAGER_LOGIN_DATA%%|*}"
MANAGER_COMPANY="${MANAGER_LOGIN_DATA##*|}"
MANAGER_JWT="$BEARER_TOKEN"

DIRECTOR_LOGIN_DATA=$(login_user "$DIRECTOR_EMAIL" "$DIRECTOR_PASSWORD") || { log_error "Director login failed"; exit 1; }
DIRECTOR_SESSION="${DIRECTOR_LOGIN_DATA%%|*}"
DIRECTOR_COMPANY="${DIRECTOR_LOGIN_DATA##*|}"
DIRECTOR_JWT="$BEARER_TOKEN"

AGENT_LOGIN_DATA=$(login_user "$AGENT_EMAIL" "$AGENT_PASSWORD") || { log_error "Agent login failed"; exit 1; }
AGENT_SESSION="${AGENT_LOGIN_DATA%%|*}"
AGENT_COMPANY="${AGENT_LOGIN_DATA##*|}"
AGENT_JWT="$BEARER_TOKEN"

PROSPECTOR_LOGIN_DATA=$(login_user "$PROSPECTOR_EMAIL" "$PROSPECTOR_PASSWORD") || { log_error "Prospector login failed"; exit 1; }
PROSPECTOR_SESSION="${PROSPECTOR_LOGIN_DATA%%|*}"
PROSPECTOR_COMPANY="${PROSPECTOR_LOGIN_DATA##*|}"

RECEPTIONIST_LOGIN_DATA=$(login_user "$RECEPTIONIST_EMAIL" "$RECEPTIONIST_PASSWORD") || { log_error "Receptionist login failed"; exit 1; }
RECEPTIONIST_SESSION="${RECEPTIONIST_LOGIN_DATA%%|*}"
RECEPTIONIST_COMPANY="${RECEPTIONIST_LOGIN_DATA##*|}"

FINANCIAL_LOGIN_DATA=$(login_user "$FINANCIAL_EMAIL" "$FINANCIAL_PASSWORD") || { log_error "Financial login failed"; exit 1; }
FINANCIAL_SESSION="${FINANCIAL_LOGIN_DATA%%|*}"
FINANCIAL_COMPANY="${FINANCIAL_LOGIN_DATA##*|}"

LEGAL_LOGIN_DATA=$(login_user "$LEGAL_EMAIL" "$LEGAL_PASSWORD") || { log_error "Legal login failed"; exit 1; }
LEGAL_SESSION="${LEGAL_LOGIN_DATA%%|*}"
LEGAL_COMPANY="${LEGAL_LOGIN_DATA##*|}"

declare -a OWNER_ALLOWED=("owner" "manager" "director" "agent" "prospector" "receptionist" "financial" "legal" "portal")
for profile in "${OWNER_ALLOWED[@]}"; do
    test_scenario "Owner invites $profile (201)"
    invite_user "$OWNER_JWT" "$OWNER_SESSION" "$OWNER_COMPANY" "$profile" "Owner Invites $profile" "$(next_email "owner_${profile}")" "$(next_cpf)" 201
done

declare -a MANAGER_ALLOWED=("agent" "prospector" "receptionist" "financial" "legal")
for profile in "${MANAGER_ALLOWED[@]}"; do
    test_scenario "Manager invites $profile (201)"
    invite_user "$MANAGER_JWT" "$MANAGER_SESSION" "$MANAGER_COMPANY" "$profile" "Manager Invites $profile" "$(next_email "manager_${profile}")" "$(next_cpf)" 201
done

declare -a MANAGER_FORBIDDEN=("owner" "manager" "director" "portal")
for profile in "${MANAGER_FORBIDDEN[@]}"; do
    test_scenario "Manager tries to invite $profile (403)"
    invite_user "$MANAGER_JWT" "$MANAGER_SESSION" "$MANAGER_COMPANY" "$profile" "Manager Forbidden $profile" "$(next_email "manager_forbidden_${profile}")" "$(next_cpf)" 403
done

for profile in "${MANAGER_ALLOWED[@]}"; do
    test_scenario "Director invites $profile (201)"
    invite_user "$DIRECTOR_JWT" "$DIRECTOR_SESSION" "$DIRECTOR_COMPANY" "$profile" "Director Invites $profile" "$(next_email "director_${profile}")" "$(next_cpf)" 201
done

test_scenario "Agent invites owner (201)"
invite_user "$AGENT_JWT" "$AGENT_SESSION" "$AGENT_COMPANY" "owner" "Agent Invites Owner" "$(next_email "agent_owner")" "$(next_cpf)" 201

test_scenario "Agent invites portal (201)"
invite_user "$AGENT_JWT" "$AGENT_SESSION" "$AGENT_COMPANY" "portal" "Agent Invites Portal" "$(next_email "agent_portal")" "$(next_cpf)" 201

declare -a AGENT_FORBIDDEN=("manager" "director" "agent" "prospector" "receptionist" "financial" "legal")
for profile in "${AGENT_FORBIDDEN[@]}"; do
    test_scenario "Agent tries to invite $profile (403)"
    invite_user "$AGENT_JWT" "$AGENT_SESSION" "$AGENT_COMPANY" "$profile" "Agent Forbidden $profile" "$(next_email "agent_forbidden_${profile}")" "$(next_cpf)" 403
done

test_scenario "Prospector tries to invite agent (403)"
invite_user "$BEARER_TOKEN" "$PROSPECTOR_SESSION" "$PROSPECTOR_COMPANY" "agent" "Prospector Forbidden" "$(next_email "prospector_forbidden")" "$(next_cpf)" 403

test_scenario "Receptionist tries to invite agent (403)"
invite_user "$BEARER_TOKEN" "$RECEPTIONIST_SESSION" "$RECEPTIONIST_COMPANY" "agent" "Receptionist Forbidden" "$(next_email "receptionist_forbidden")" "$(next_cpf)" 403

test_scenario "Financial tries to invite agent (403)"
invite_user "$BEARER_TOKEN" "$FINANCIAL_SESSION" "$FINANCIAL_COMPANY" "agent" "Financial Forbidden" "$(next_email "financial_forbidden")" "$(next_cpf)" 403

test_scenario "Legal tries to invite agent (403)"
invite_user "$BEARER_TOKEN" "$LEGAL_SESSION" "$LEGAL_COMPANY" "agent" "Legal Forbidden" "$(next_email "legal_forbidden")" "$(next_cpf)" 403

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Tests Run:    $TESTS_RUN scenarios"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED assertions${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED assertions${NC}"
echo "=========================================="

cleanup_test_data

if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    log_info "All tests passed! ✓"
    exit 0
fi
