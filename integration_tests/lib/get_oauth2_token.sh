#!/usr/bin/env bash
# Helper function to get OAuth2 JWT access token
# Uses /api/v1/auth/token with client_credentials grant
# 
# Usage:
#   source lib/get_oauth2_token.sh
#   ACCESS_TOKEN=$(get_oauth2_token)
#   curl -X POST "$BASE_URL/api/v1/owners" \
#     -H "Authorization: Bearer $ACCESS_TOKEN" \
#     -H "Content-Type: application/json"

get_oauth2_token() {
    BASE_URL="${BASE_URL:-http://localhost:8069}"

    # Callers that don't source 18.0/.env themselves would otherwise fall
    # through to the stale hardcoded secret below and get invalid_client.
    if [ -z "${OAUTH_CLIENT_SECRET:-}" ]; then
        _lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        [ -f "${_lib_dir}/../../18.0/.env" ] && source "${_lib_dir}/../../18.0/.env" || true
    fi

    # OAuth2 credentials (from seed data - see 18.0/extra-addons/quicksol_estate/data/oauth2_seed.xml)
    CLIENT_ID="${OAUTH_CLIENT_ID:-test-client-id}"
    CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-test-client-secret-12345}"
    
    # Request OAuth2 token using client_credentials grant
    TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}")
    
    # Extract access_token from JSON response
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
    
    if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
        echo "ERROR: Failed to get OAuth2 access token" >&2
        echo "Response: $TOKEN_RESPONSE" >&2
        return 1
    fi
    
    # Return the access token (JWT)
    echo "$ACCESS_TOKEN"
    return 0
}
