#!/usr/bin/env bash
# Helper: Get OAuth2 Bearer token for API testing
#
# Usage:
#   source lib/get_token.sh
#   TOKEN=$(get_oauth_token)
#
# Environment variables (from 18.0/.env):
#   OAUTH_CLIENT_ID
#   OAUTH_CLIENT_SECRET
#   BASE_URL (default: http://localhost:8069)

get_oauth_token() {
    local base_url="${BASE_URL:-http://localhost:8069}"
    
    # Load credentials from .env if not set
    if [ -z "$OAUTH_CLIENT_ID" ] || [ -z "$OAUTH_CLIENT_SECRET" ]; then
        if [ -f "$(dirname "$0")/../18.0/.env" ]; then
            set -a
            source "$(dirname "$0")/../18.0/.env"
            set +a
        elif [ -f "../18.0/.env" ]; then
            set -a
            source "../18.0/.env"
            set +a
        fi
    fi
    
    if [ -z "$OAUTH_CLIENT_ID" ] || [ -z "$OAUTH_CLIENT_SECRET" ]; then
        echo "ERROR: OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be set in .env" >&2
        return 1
    fi
    
    # Request OAuth2 token
    local response=$(curl -s -X POST "${base_url}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{
            \"grant_type\": \"client_credentials\",
            \"client_id\": \"${OAUTH_CLIENT_ID}\",
            \"client_secret\": \"${OAUTH_CLIENT_SECRET}\"
        }")
    
    # Extract access_token
    local token=$(echo "$response" | jq -r '.access_token // empty')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        echo "ERROR: Failed to get OAuth token" >&2
        echo "Response: $response" >&2
        return 1
    fi
    
    echo "$token"
}
