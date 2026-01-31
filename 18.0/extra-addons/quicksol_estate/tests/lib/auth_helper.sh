#!/bin/bash
# ==============================================================================
# Authentication Helper Library
# ==============================================================================
# Provides reusable functions for OAuth 2.0 + User Login flow
# Usage: source tests/lib/auth_helper.sh
# ==============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# Function: get_oauth_token
# Description: Obtains OAuth 2.0 client_credentials token
# Returns: OAuth access token (sets $OAUTH_TOKEN global variable)
# ==============================================================================
get_oauth_token() {
    local base_url="${1:-${ODOO_BASE_URL}}"
    local client_id="${2:-${OAUTH_CLIENT_ID}}"
    local client_secret="${3:-${OAUTH_CLIENT_SECRET}}"
    
    if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
        echo -e "${RED}✗ ERROR: OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be set${NC}" >&2
        return 1
    fi
    
    local oauth_response=$(curl -s -X POST "${base_url}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"${client_id}\",\"client_secret\":\"${client_secret}\"}")
    
    OAUTH_TOKEN=$(echo "$oauth_response" | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*' | sed 's/"access_token"[[:space:]]*:[[:space:]]*"//' | head -1)
    
    if [ -z "$OAUTH_TOKEN" ]; then
        echo -e "${RED}✗ ERROR: Failed to get OAuth token${NC}" >&2
        echo "Response: $oauth_response" >&2
        return 1
    fi
    
    echo "$OAUTH_TOKEN"
    return 0
}

# ==============================================================================
# Function: user_login
# Description: Logs in a user with OAuth token (Step 2 of auth flow)
# Parameters: 
#   $1 - User email
#   $2 - User password
#   $3 - Base URL (optional, defaults to ODOO_BASE_URL)
#   $4 - OAuth token (optional, uses global $OAUTH_TOKEN if not provided)
# Returns: Session ID (sets $USER_SESSION_ID global variable)
# ==============================================================================
user_login() {
    local email="$1"
    local password="$2"
    local base_url="${3:-${ODOO_BASE_URL}}"
    local oauth_token="${4:-${OAUTH_TOKEN}}"
    
    if [ -z "$email" ] || [ -z "$password" ]; then
        echo -e "${RED}✗ ERROR: Email and password are required${NC}" >&2
        return 1
    fi
    
    if [ -z "$oauth_token" ]; then
        echo -e "${RED}✗ ERROR: OAuth token not provided. Call get_oauth_token first.${NC}" >&2
        return 1
    fi
    
    local login_response=$(curl -s -X POST "${base_url}/api/v1/users/login" \
        -H "Authorization: Bearer ${oauth_token}" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")
    
    USER_SESSION_ID=$(echo "$login_response" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*' | sed 's/"session_id"[[:space:]]*:[[:space:]]*"//' | head -1)
    
    if [ -z "$USER_SESSION_ID" ]; then
        echo -e "${RED}✗ ERROR: Failed to login user ${email}${NC}" >&2
        echo "Response: $login_response" >&2
        return 1
    fi
    
    echo "$USER_SESSION_ID"
    return 0
}

# ==============================================================================
# Function: authenticate_user
# Description: Complete authentication flow (OAuth + User Login)
# Parameters:
#   $1 - User email
#   $2 - User password
#   $3 - Base URL (optional)
# Returns: Sets global variables OAUTH_TOKEN and USER_SESSION_ID
# ==============================================================================
authenticate_user() {
    local email="$1"
    local password="$2"
    local base_url="${3:-${ODOO_BASE_URL}}"
    
    # Step 1: Get OAuth token (only once per script)
    if [ -z "$OAUTH_TOKEN" ]; then
        get_oauth_token "$base_url" || return 1
    fi
    
    # Step 2: User login
    user_login "$email" "$password" "$base_url" "$OAUTH_TOKEN" || return 1
    
    return 0
}

# ==============================================================================
# Function: make_api_request
# Description: Makes authenticated API request with proper headers
# Parameters:
#   $1 - HTTP method (GET, POST, PUT, DELETE)
#   $2 - Endpoint path (e.g., /api/v1/leads)
#   $3 - JSON data (optional, for POST/PUT)
#   $4 - Base URL (optional)
# Returns: API response
# ==============================================================================
make_api_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local base_url="${4:-${ODOO_BASE_URL}}"
    
    if [ -z "$OAUTH_TOKEN" ]; then
        echo -e "${RED}✗ ERROR: Not authenticated. Call authenticate_user first.${NC}" >&2
        return 1
    fi
    
    if [ -z "$USER_SESSION_ID" ]; then
        echo -e "${RED}✗ ERROR: No session ID. Call authenticate_user first.${NC}" >&2
        return 1
    fi
    
    local curl_cmd="curl -s -X ${method} ${base_url}${endpoint}"
    curl_cmd="${curl_cmd} -H \"Authorization: Bearer ${OAUTH_TOKEN}\""
    curl_cmd="${curl_cmd} -H \"X-Openerp-Session-Id: ${USER_SESSION_ID}\""
    curl_cmd="${curl_cmd} -H \"Content-Type: application/json\""
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -d '${data}'"
    fi
    
    eval "$curl_cmd"
}

# ==============================================================================
# Function: extract_json_field
# Description: Extracts field value from JSON response
# Parameters:
#   $1 - JSON string
#   $2 - Field name
# Returns: Field value
# ==============================================================================
extract_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*[^,}]*" | head -1 | sed "s/\"$field\"[[:space:]]*:[[:space:]]*//" | tr -d '", '
}

# ==============================================================================
# Example Usage:
# ==============================================================================
# #!/bin/bash
# source tests/lib/auth_helper.sh
# 
# # Authenticate manager
# authenticate_user "admin" "admin"
# MANAGER_TOKEN="$OAUTH_TOKEN"
# MANAGER_SESSION="$USER_SESSION_ID"
# 
# # Authenticate agent
# authenticate_user "agent@example.com" "password"
# AGENT_TOKEN="$OAUTH_TOKEN"
# AGENT_SESSION="$USER_SESSION_ID"
# 
# # Make API request
# RESPONSE=$(make_api_request "GET" "/api/v1/leads?limit=10")
# LEAD_COUNT=$(extract_json_field "$RESPONSE" "total")
# echo "Total leads: $LEAD_COUNT"
# ==============================================================================
