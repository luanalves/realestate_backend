#!/usr/bin/env bash
# Feature 009 - US9-S2: Set Password via Invite Token - T28
# E2E test for POST /api/v1/auth/set-password
#
# Covers (FR2 + FR2.10):
#   T28-1  Valid token                     → 200
#   T28-2  Token already used              → 410 token_used
#   T28-3  Token expired                   → 410 token_expired
#   T28-4  Token not found                 → 404
#   T28-5  Malformed token (not 32 hex)    → 400 validation_error
#   T28-6  Password too short              → 400 validation_error
#   T28-7  Password mismatch               → 400 validation_error
#   T28-8  Missing fields                  → 400 validation_error
#   T28-9  Reset token in set-password     → 404  (cross-type abuse)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
DB_NAME="${DB_NAME:-realestate}"
DB_USER="${POSTGRES_USER:-odoo}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_HOST="${POSTGRES_HOST:-localhost}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ $1${NC}"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}✗ $1${NC}"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}→ $1${NC}"; }

echo "========================================"
echo "US9-S2: Set Password via Invite Token"
echo "========================================"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Execute SQL against the database (via docker exec or psql)
run_sql() {
    local sql="$1"
    if command -v docker &>/dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -q '18.0-db-1\|realestate_db\|_db_'; then
        local container
        container=$(docker ps --format '{{.Names}}' | grep -E '18.0-db-1|realestate_db|_db_' | head -1)
        docker exec -i "$container" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "$sql" 2>/dev/null
    else
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "$sql" 2>/dev/null
    fi
}

# Compute SHA-256 hex of a string
sha256_hex() {
    echo -n "$1" | sha256sum | awk '{print $1}'
}

# Insert a token directly for testing (bypasses email flow)
# Args: <raw_token> <user_id> <status> <expires_offset_minutes>
insert_test_token() {
    local raw="$1"
    local user_id="$2"
    local status="$3"
    local offset_minutes="$4"  # positive = future, negative = past

    local token_hash
    token_hash=$(sha256_hex "$raw")

    local expires_sql
    if [ "$offset_minutes" -ge 0 ]; then
        expires_sql="NOW() + INTERVAL '${offset_minutes} minutes'"
    else
        local abs_offset=$(( -1 * offset_minutes ))
        expires_sql="NOW() - INTERVAL '${abs_offset} minutes'"
    fi

    local used_at_sql="NULL"
    if [ "$status" = "used" ]; then
        used_at_sql="NOW() - INTERVAL '5 minutes'"
    fi

    run_sql "
        INSERT INTO thedevkitchen_password_token
            (user_id, token, token_type, status, expires_at, used_at, active, create_date, write_date)
        VALUES
            ($user_id, '$token_hash', 'invite', '$status', $expires_sql, $used_at_sql, true, NOW(), NOW())
    " > /dev/null
}

# Insert a RESET token for cross-type abuse test
insert_reset_token() {
    local raw="$1"
    local user_id="$2"

    local token_hash
    token_hash=$(sha256_hex "$raw")

    run_sql "
        INSERT INTO thedevkitchen_password_token
            (user_id, token, token_type, status, expires_at, active, create_date, write_date)
        VALUES
            ($user_id, '$token_hash', 'reset', 'pending', NOW() + INTERVAL '120 minutes', true, NOW(), NOW())
    " > /dev/null
}

# Get or create a test user for token tests
get_test_user_id() {
    local email="setpwd_test_$(date +%s)@integration.test"
    local uid
    uid=$(run_sql "SELECT id FROM res_users WHERE login = '$email' LIMIT 1;" | tr -d '[:space:]')
    if [ -z "$uid" ] || [ "$uid" = "" ]; then
        # Create minimal res.users (portal group) — password=False means hashed empty
        local partner_id
        partner_id=$(run_sql "
            INSERT INTO res_partner (name, email, active, create_date, write_date)
            VALUES ('SetPwd Test', '$email', true, NOW(), NOW())
            RETURNING id;
        " | tr -d '[:space:]')

        uid=$(run_sql "
            INSERT INTO res_users (partner_id, login, active, signup_pending, create_date, write_date)
            VALUES ($partner_id, '$email', true, true, NOW(), NOW())
            RETURNING id;
        " | tr -d '[:space:]')
    fi
    echo "$uid"
}

# Clean up tokens created by this test run
cleanup_tokens() {
    local user_id="$1"
    run_sql "DELETE FROM thedevkitchen_password_token WHERE user_id = $user_id;" > /dev/null 2>&1 || true
}

post_set_password() {
    local token="$1"
    local password="$2"
    local confirm="$3"

    curl -s -o /tmp/sp_body.json -w "%{http_code}" -X POST "$API_BASE/auth/set-password" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"$token\", \"password\": \"$password\", \"confirm_password\": \"$confirm\"}"
}

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

info "Setting up test user..."
TEST_USER_ID=$(get_test_user_id)
if [ -z "$TEST_USER_ID" ] || [ "$TEST_USER_ID" = "" ]; then
    echo -e "${RED}FATAL: Could not create test user${NC}"
    exit 1
fi
info "Test user ID: $TEST_USER_ID"

# ── T28-1: Valid token ──────────────────────────────────────────────────────
echo ""
echo "T28-1: Valid invite token → 200"
VALID_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_test_token "$VALID_TOKEN" "$TEST_USER_ID" "pending" 1440

HTTP=$(post_set_password "$VALID_TOKEN" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "200" ] && echo "$BODY" | jq -e '.success == true' >/dev/null 2>&1; then
    pass "T28-1: Valid token → 200"
else
    fail "T28-1: Expected 200, got $HTTP | $BODY"
fi

# ── T28-2: Token already used ───────────────────────────────────────────────
echo ""
echo "T28-2: Already-used token → 410"
USED_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_test_token "$USED_TOKEN" "$TEST_USER_ID" "used" 1440

HTTP=$(post_set_password "$USED_TOKEN" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "410" ] && echo "$BODY" | jq -e '.error == "token_used"' >/dev/null 2>&1; then
    pass "T28-2: Used token → 410 token_used"
else
    fail "T28-2: Expected 410 token_used, got $HTTP | $BODY"
fi

# ── T28-3: Expired token ────────────────────────────────────────────────────
echo ""
echo "T28-3: Expired token → 410"
EXPIRED_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_test_token "$EXPIRED_TOKEN" "$TEST_USER_ID" "pending" -60  # expired 1h ago

HTTP=$(post_set_password "$EXPIRED_TOKEN" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "410" ] && echo "$BODY" | jq -e '.error == "token_expired"' >/dev/null 2>&1; then
    pass "T28-3: Expired token → 410 token_expired"
else
    fail "T28-3: Expected 410 token_expired, got $HTTP | $BODY"
fi

# ── T28-4: Token not found ──────────────────────────────────────────────────
echo ""
echo "T28-4: Non-existent token → 404"
NONEXISTENT_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"  # not inserted

HTTP=$(post_set_password "$NONEXISTENT_TOKEN" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "404" ] && echo "$BODY" | jq -e '.error == "not_found"' >/dev/null 2>&1; then
    pass "T28-4: Non-existent token → 404"
else
    fail "T28-4: Expected 404, got $HTTP | $BODY"
fi

# ── T28-5: Malformed token ──────────────────────────────────────────────────
echo ""
echo "T28-5: Malformed token (not 32 hex) → 400"
HTTP=$(post_set_password "not-a-valid-hex-token!!" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "400" ] && echo "$BODY" | jq -e '.error == "validation_error"' >/dev/null 2>&1; then
    pass "T28-5: Malformed token → 400 validation_error"
else
    fail "T28-5: Expected 400 validation_error, got $HTTP | $BODY"
fi

# ── T28-5b: Token too short ─────────────────────────────────────────────────
HTTP=$(post_set_password "abc123" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "400" ]; then
    pass "T28-5b: Too-short token → 400"
else
    fail "T28-5b: Expected 400, got $HTTP | $BODY"
fi

# ── T28-6: Password too short ───────────────────────────────────────────────
echo ""
echo "T28-6: Password too short → 400"
SHORT_PWD_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_test_token "$SHORT_PWD_TOKEN" "$TEST_USER_ID" "pending" 1440

HTTP=$(post_set_password "$SHORT_PWD_TOKEN" "abc" "abc")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "400" ] && echo "$BODY" | jq -e '.error == "validation_error"' >/dev/null 2>&1; then
    pass "T28-6: Short password → 400 validation_error"
else
    fail "T28-6: Expected 400 validation_error, got $HTTP | $BODY"
fi

# ── T28-7: Password mismatch ────────────────────────────────────────────────
echo ""
echo "T28-7: Password mismatch → 400"
MISMATCH_TOKEN="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_test_token "$MISMATCH_TOKEN" "$TEST_USER_ID" "pending" 1440

HTTP=$(post_set_password "$MISMATCH_TOKEN" "StrongPass1!" "DifferentPass2!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "400" ] && echo "$BODY" | jq -e '.error == "validation_error"' >/dev/null 2>&1; then
    pass "T28-7: Password mismatch → 400 validation_error"
else
    fail "T28-7: Expected 400 validation_error, got $HTTP | $BODY"
fi

# ── T28-8: Missing fields ───────────────────────────────────────────────────
echo ""
echo "T28-8: Missing required fields → 400"
HTTP=$(curl -s -o /tmp/sp_body.json -w "%{http_code}" -X POST "$API_BASE/auth/set-password" \
    -H "Content-Type: application/json" \
    -d '{"password": "StrongPass1!"}')
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "400" ] && echo "$BODY" | jq -e '.error == "validation_error"' >/dev/null 2>&1; then
    pass "T28-8: Missing fields → 400 validation_error"
else
    fail "T28-8: Expected 400 validation_error, got $HTTP | $BODY"
fi

# ── T28-9: Reset token used in set-password (cross-type abuse) ──────────────
echo ""
echo "T28-9: Reset token in set-password endpoint → 404 (cross-type blocked)"
RESET_TOKEN_RAW="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
insert_reset_token "$RESET_TOKEN_RAW" "$TEST_USER_ID"

HTTP=$(post_set_password "$RESET_TOKEN_RAW" "StrongPass1!" "StrongPass1!")
BODY=$(cat /tmp/sp_body.json)
if [ "$HTTP" = "404" ]; then
    pass "T28-9: Reset token blocked in set-password → 404"
else
    fail "T28-9: Expected 404 (cross-type blocked), got $HTTP | $BODY"
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
info "Cleaning up test tokens for user $TEST_USER_ID..."
cleanup_tokens "$TEST_USER_ID"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "Results: ${GREEN}${PASS} passed${NC} | ${FAIL} failed"
echo "========================================"

[ "$FAIL" -eq 0 ]
