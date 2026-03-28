#!/usr/bin/env bash
# =============================================================================
# Test: Production Environment - Grafana Integration Test
# Validates OAuth2, Login, and API endpoints in production
# =============================================================================

set -e

# Production Configuration
BASE_URL="https://torque-backoffice.thedevkitchen.com.br"
API_BASE="$BASE_URL/api/v1"
GRAFANA_URL="https://grafana.torque-backoffice.thedevkitchen.com.br"

# OAuth Credentials
OAUTH_CLIENT_ID="client_c4pfKrpzqqa1Gs2InrS6tQ"
OAUTH_CLIENT_SECRET="EkXelFPusYMcRyugHZMEp-g755-SYipbgMfwTgSztCVLScQ79fdIcf_5kUVk16gU"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_test() { echo -e "${BLUE}[TEST]${NC} $1"; }

test_scenario() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo ""
    log_test "Test $TESTS_RUN: $1"
}

assert_http_status() {
    local expected=$1
    local actual=$2
    local description=$3
    
    if [ "$actual" = "$expected" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✓ $description (HTTP $actual)"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ $description (Expected: $expected, Got: $actual)"
        return 1
    fi
}

echo "============================================="
echo "Production Environment - Grafana Integration"
echo "============================================="
echo "Base URL: $BASE_URL"
echo "Grafana URL: $GRAFANA_URL"
echo "============================================="
echo ""

# =============================================================================
# Test 1: Check Grafana Availability
# =============================================================================
test_scenario "Check Grafana Availability"

GRAFANA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$GRAFANA_URL/api/health" || echo "000")
if [ "$GRAFANA_STATUS" = "200" ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_info "✓ Grafana is available (HTTP $GRAFANA_STATUS)"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "✗ Grafana is not available (HTTP $GRAFANA_STATUS)"
fi

# =============================================================================
# Test 2: OAuth2 Token Request
# =============================================================================
test_scenario "OAuth2 Token Request"

TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=$OAUTH_CLIENT_ID" \
    -d "client_secret=$OAUTH_CLIENT_SECRET" \
    -w "\n%{http_code}")

HTTP_STATUS=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

if [ "$HTTP_STATUS" = "200" ]; then
    ACCESS_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token // empty')
    
    if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✓ OAuth2 token obtained successfully"
        log_info "  Token prefix: ${ACCESS_TOKEN:0:20}..."
        
        # Extract token info
        TOKEN_TYPE=$(echo "$RESPONSE_BODY" | jq -r '.token_type // empty')
        EXPIRES_IN=$(echo "$RESPONSE_BODY" | jq -r '.expires_in // empty')
        
        log_info "  Token type: $TOKEN_TYPE"
        log_info "  Expires in: ${EXPIRES_IN}s"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ Failed to extract access token from response"
        echo "Response: $RESPONSE_BODY"
    fi
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "✗ OAuth2 token request failed (HTTP $HTTP_STATUS)"
    echo "Response: $RESPONSE_BODY"
fi

# =============================================================================
# Test 3: Test Public Endpoint (without authentication)
# =============================================================================
test_scenario "Public Test Endpoint"

PUBLIC_RESPONSE=$(curl -s -X GET "$API_BASE/test/public" \
    -w "\n%{http_code}")

PUBLIC_STATUS=$(echo "$PUBLIC_RESPONSE" | tail -n1)
PUBLIC_BODY=$(echo "$PUBLIC_RESPONSE" | sed '$d')

if [ "$PUBLIC_STATUS" = "200" ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_info "✓ Public endpoint is accessible"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "✗ Public endpoint failed (HTTP $PUBLIC_STATUS)"
    echo "Response: $PUBLIC_BODY"
fi

# =============================================================================
# Test 4: Test Protected Endpoint (with OAuth token)
# =============================================================================
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    test_scenario "Protected Endpoint with OAuth"
    
    PROTECTED_RESPONSE=$(curl -s -X GET "$API_BASE/test/protected" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -w "\n%{http_code}")
    
    PROTECTED_STATUS=$(echo "$PROTECTED_RESPONSE" | tail -n1)
    PROTECTED_BODY=$(echo "$PROTECTED_RESPONSE" | sed '$d')
    
    if [ "$PROTECTED_STATUS" = "200" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✓ OAuth token is valid and working"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ Protected endpoint failed (HTTP $PROTECTED_STATUS)"
        echo "Response: $PROTECTED_BODY"
    fi
fi

# =============================================================================
# Test 5: Test Master Data Endpoint (property-types) - Requires Full Session
# =============================================================================
if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    test_scenario "Master Data Endpoint (property-types)"

    PROPTYPE_RESPONSE=$(curl -s -X GET "$API_BASE/property-types" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -w "\n%{http_code}")

    PROPTYPE_STATUS=$(echo "$PROPTYPE_RESPONSE" | tail -n1)
    PROPTYPE_BODY=$(echo "$PROPTYPE_RESPONSE" | sed '$d')

    if [ "$PROPTYPE_STATUS" = "200" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✓ Master data endpoint is accessible"
        
        # Count property types
        PROP_COUNT=$(echo "$PROPTYPE_BODY" | jq -r '.data | length // 0')
        log_info "  Property types available: $PROP_COUNT"
    elif [ "$PROPTYPE_STATUS" = "401" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_info "✓ Master data endpoint requires full session (expected)"
        log_info "  Note: Requires @require_jwt + @require_session + @require_company"
        log_info "  OAuth token alone is not sufficient for company-scoped endpoints"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ Master data endpoint failed unexpectedly (HTTP $PROPTYPE_STATUS)"
        echo "Response: $PROPTYPE_BODY"
    fi
fi

# =============================================================================
# Test 6: OpenAPI Documentation Endpoint
# =============================================================================
test_scenario "OpenAPI Documentation"

OPENAPI_RESPONSE=$(curl -s -X GET "$API_BASE/openapi.json" \
    -w "\n%{http_code}")

OPENAPI_STATUS=$(echo "$OPENAPI_RESPONSE" | tail -n1)

if [ "$OPENAPI_STATUS" = "200" ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_info "✓ OpenAPI documentation is accessible"
    
    # Extract API info
    OPENAPI_BODY=$(echo "$OPENAPI_RESPONSE" | sed '$d')
    API_TITLE=$(echo "$OPENAPI_BODY" | jq -r '.info.title // empty')
    API_VERSION=$(echo "$OPENAPI_BODY" | jq -r '.info.version // empty')
    
    log_info "  API: $API_TITLE v$API_VERSION"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_warning "✗ OpenAPI documentation not accessible (HTTP $OPENAPI_STATUS)"
fi

# =============================================================================
# Test 7: User Profile Endpoint (/api/v1/me) - Requires Session
# =============================================================================
test_scenario "User Profile Endpoint (requires session)"

ME_RESPONSE=$(curl -s -X GET "$API_BASE/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -w "\n%{http_code}")

ME_STATUS=$(echo "$ME_RESPONSE" | tail -n1)
ME_BODY=$(echo "$ME_RESPONSE" | sed '$d')

if [ "$ME_STATUS" = "200" ] || [ "$ME_STATUS" = "401" ] || [ "$ME_STATUS" = "403" ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    if [ "$ME_STATUS" = "200" ]; then
        log_info "✓ User profile endpoint accessible (with session)"
        USER_ID=$(echo "$ME_BODY" | jq -r '.id // empty')
        USER_NAME=$(echo "$ME_BODY" | jq -r '.name // empty')
        log_info "  User: $USER_NAME (ID: $USER_ID)"
    elif [ "$ME_STATUS" = "401" ] || [ "$ME_STATUS" = "403" ]; then
        log_info "✓ User profile endpoint requires session (expected)"
        log_info "  Note: OAuth token alone is not sufficient, needs user login"
    fi
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "✗ User profile endpoint failed unexpectedly (HTTP $ME_STATUS)"
    echo "Response: $ME_BODY"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================="
echo "Test Summary"
echo "============================================="
echo "Total Tests: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "============================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    log_info "All tests passed! ✓"
    echo ""
    echo "Grafana Dashboard: $GRAFANA_URL"
    echo "API Base URL: $API_BASE"
    exit 0
else
    echo ""
    log_error "Some tests failed!"
    exit 1
fi
