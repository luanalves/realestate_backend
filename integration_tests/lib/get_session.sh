#!/usr/bin/env bash
# Helper function to authenticate user and get session cookie
# Uses /api/v1/users/login (JSON-RPC endpoint) to establish session
# 
# Usage:
#   source lib/get_session.sh
#   SESSION_COOKIE=$(get_user_session)
#   curl -X GET "$BASE_URL/api/v1/owners" -H "Cookie: $SESSION_COOKIE"

get_user_session() {
    # Load credentials from .env (path relative to integration_tests/lib/)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    ENV_FILE="${SCRIPT_DIR}/../../../18.0/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        echo "ERROR: .env file not found at $ENV_FILE" >&2
        echo "SCRIPT_DIR was: $SCRIPT_DIR" >&2
        return 1
    fi
    
    # Source .env and extract TEST_USER credentials
    set -a
    source "$ENV_FILE"
    set +a
    
    # Use admin@admin.com/admin as default (Odoo default admin)
    USER_LOGIN="${TEST_USER_ADMIN_LOGIN:-admin@admin.com}"
    USER_PASSWORD="${TEST_USER_ADMIN_PASSWORD:-admin}"
    
    BASE_URL="${BASE_URL:-http://localhost:8069}"
    DB_NAME="${DB_NAME:-realestate}"
    
    # Call /api/v1/users/login (JSON-RPC)
    LOGIN_RESPONSE=$(curl -s -c /tmp/odoo_session_cookie.txt -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"login\": \"${USER_LOGIN}\",
                \"password\": \"${USER_PASSWORD}\",
                \"db\": \"${DB_NAME}\"
            },
            \"id\": 1
        }")
    
    # Extract session_id from cookie file
    if [ -f /tmp/odoo_session_cookie.txt ]; then
        SESSION_ID=$(grep "session_id" /tmp/odoo_session_cookie.txt | awk '{print $7}')
        if [ -n "$SESSION_ID" ]; then
            echo "session_id=$SESSION_ID"
            return 0
        fi
    fi
    
    echo "ERROR: Failed to get session cookie" >&2
    echo "Response: $LOGIN_RESPONSE" >&2
    return 1
}
