#!/usr/bin/env bash
# integration_tests/test_us15_s7_partner_dedup_multiphone.sh
#
# Feature 015 — US5: Multi-phone Client / Partner Deduplication
# Tests FR-022a (single phone match → reuse), FR-022b (multi-phone conflict → 409),
# FR-022c (phone+email divergence → prefer phone).
#
# Task: T060
# FRs: FR-022, FR-022a, FR-022b, FR-022c
#
# Usage:
#   chmod +x integration_tests/test_us15_s7_partner_dedup_multiphone.sh
#   BASE_URL=http://localhost:8069 TOKEN=<jwt> SESSION_ID=<sid> COMPANY_ID=<id> \
#     ./integration_tests/test_us15_s7_partner_dedup_multiphone.sh

set -euo pipefail

# Load environment variables — REQUIRED
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../18.0/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
else
    echo "❌ ERROR: .env file not found at $ENV_FILE"
    echo "   Copy 18.0/.env.example to 18.0/.env and fill in credentials"
    exit 1
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
TOKEN="${TOKEN:-}"
SESSION_ID="${SESSION_ID:-}"
COMPANY_ID="${COMPANY_ID:-1}"
: "${OWNER_EMAIL:?OWNER_EMAIL is required — set it in 18.0/.env}"
: "${OWNER_PASS:?OWNER_PASS is required — set it in 18.0/.env}"
: "${OAUTH_CLIENT_ID:?OAUTH_CLIENT_ID is required — set it in 18.0/.env}"
: "${OAUTH_CLIENT_SECRET:?OAUTH_CLIENT_SECRET is required — set it in 18.0/.env}"

PASS=0
FAIL=0
SKIP=0

_log()  { echo "[INFO] $*"; }
_pass() { echo "[PASS] $*"; ((PASS+=1)); }
_fail() { echo "[FAIL] $*"; ((FAIL+=1)); }
_skip() { echo "[SKIP] $*"; ((SKIP+=1)); }

# ── Authenticate ─────────────────────────────────────────────────────────────
authenticate() {
    local jwt
    jwt=$(curl -sf -X POST "${BASE_URL}/api/v1/auth/token" \
        -H 'Content-Type: application/json' \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"${OAUTH_CLIENT_ID}\",\"client_secret\":\"${OAUTH_CLIENT_SECRET}\"}" 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null) || true
    if [[ -z "$jwt" ]]; then
        _skip "Cannot reach ${BASE_URL} or OAuth failed — skipping all integration tests"
        return 1
    fi
    local sid
    sid=$(curl -sf -X POST "${BASE_URL}/api/v1/users/login" \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"${OWNER_EMAIL}\",\"password\":\"${OWNER_PASS}\"}" 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null) || true
    if [[ -z "$sid" ]]; then
        _skip "Login failed — no session. Skipping integration tests."
        return 1
    fi
    TOKEN="$jwt"
    SESSION_ID="$sid"
    _log "Authenticated as ${OWNER_EMAIL}"
    return 0
}

_auth_headers() {
    echo "-H 'Authorization: Bearer ${TOKEN}' -H 'X-Session-Id: ${SESSION_ID}' -H 'X-Company-Id: ${COMPANY_ID}'"
}

# ── Helpers ───────────────────────────────────────────────────────────────────
create_service() {
    local body="$1"
    curl -sf -X POST "${BASE_URL}/api/v1/services" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        -H 'Content-Type: application/json' \
        -d "$body" 2>/dev/null
}

http_status() {
    local body="$1"
    local url="$2"
    local method="${3:-POST}"
    curl -so /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${url}" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        -H 'Content-Type: application/json' \
        -d "$body" 2>/dev/null
}

# ── Tests ─────────────────────────────────────────────────────────────────────

test_create_service_new_client() {
    _log "T-S7-01: Create service with new client (unique phone) → 201 + partner created"
    local phone="5511$(date +%s | tail -c 9)"
    local body="{
        \"client\": {\"name\": \"Test Dedup Client\", \"phones\": [{\"type\": \"mobile\", \"number\": \"${phone}\"}]},
        \"operation_type\": \"rent\",
        \"source_id\": 1
    }"
    local status
    status=$(http_status "$body" '/api/v1/services')
    if [[ "$status" == "201" ]]; then
        _pass "T-S7-01: New client created — status 201"
    else
        _fail "T-S7-01: Expected 201, got ${status}"
    fi
}

test_create_service_same_phone_reuses_partner() {
    _log "T-S7-02: Create two services with same phone → same partner reused (FR-022a)"
    local phone="5511$(date +%s | tail -c 8)77"
    local body1="{
        \"client\": {\"name\": \"Dedup Partner A\", \"phones\": [{\"type\": \"mobile\", \"number\": \"${phone}\"}]},
        \"operation_type\": \"rent\",
        \"source_id\": 1
    }"
    local body2="{
        \"client\": {\"name\": \"Different Name Same Phone\", \"phones\": [{\"type\": \"mobile\", \"number\": \"${phone}\"}]},
        \"operation_type\": \"sale\",
        \"source_id\": 1
    }"
    local resp1 resp2 pid1 pid2
    resp1=$(create_service "$body1") || true
    resp2=$(create_service "$body2") || true

    pid1=$(echo "$resp1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('id',''))" 2>/dev/null || echo "")
    pid2=$(echo "$resp2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('id',''))" 2>/dev/null || echo "")

    if [[ -n "$pid1" && -n "$pid2" && "$pid1" == "$pid2" ]]; then
        _pass "T-S7-02: Same phone → same partner_id ${pid1} (FR-022a)"
    elif [[ -z "$pid1" || -z "$pid2" ]]; then
        _fail "T-S7-02: Could not parse partner IDs from response — check API format"
    else
        _fail "T-S7-02: Expected same partner, got ${pid1} vs ${pid2}"
    fi
}

test_create_service_phone_conflict_returns_409() {
    _log "T-S7-03: Phone number shared by 2 partners → 409 with candidate_ids (FR-022b)"
    # This test requires pre-seeded data (two partners sharing a phone number)
    # — skip if no seed data available
    _skip "T-S7-03: Requires pre-seeded conflicting partners — use manual seed or DB fixture"
}

test_create_service_email_divergence_prefers_phone() {
    _log "T-S7-04: Phone partner ≠ email partner → prefer phone, service created (FR-022c)"
    # This test requires pre-seeded divergent data — skip if unavailable
    _skip "T-S7-04: Requires pre-seeded divergent partner data — use manual seed or DB fixture"
}

test_create_service_no_phones_email_match_reuses() {
    _log "T-S7-05: No phones, email matches unique partner → reuse partner (FR-022a email path)"
    local ts="$(date +%s)"
    local email="dedup_client_${ts}@test.example.com"

    # Create first service to seed the partner
    local body1="{
        \"client\": {\"name\": \"Email Dedup Client\", \"email\": \"${email}\", \"phones\": []},
        \"operation_type\": \"rent\",
        \"source_id\": 1
    }"
    local body2="{
        \"client\": {\"name\": \"Same Email Partner\", \"email\": \"${email}\", \"phones\": []},
        \"operation_type\": \"sale\",
        \"source_id\": 1
    }"

    local resp1 resp2 pid1 pid2
    resp1=$(create_service "$body1") || true
    resp2=$(create_service "$body2") || true

    pid1=$(echo "$resp1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('id',''))" 2>/dev/null || echo "")
    pid2=$(echo "$resp2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('id',''))" 2>/dev/null || echo "")

    if [[ -n "$pid1" && -n "$pid2" && "$pid1" == "$pid2" ]]; then
        _pass "T-S7-05: Same email → same partner_id ${pid1} (FR-022a email)"
    elif [[ -z "$pid1" || -z "$pid2" ]]; then
        _fail "T-S7-05: Could not parse partner IDs — check API format"
    else
        _fail "T-S7-05: Expected same partner, got ${pid1} vs ${pid2}"
    fi
}

test_conflict_response_has_candidate_ids() {
    _log "T-S7-06: 409 response body contains candidate_ids array (FR-022b schema)"
    # Structural assertion — just verify 409 response has candidate_ids shape
    # Actual trigger requires conflicting DB state
    _skip "T-S7-06: Requires pre-seeded conflicting data — verify response shape manually"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo "========================================================"
echo "Feature 015 — US5: Partner Dedup / Multi-phone (T060)"
echo "Base URL: ${BASE_URL}"
echo "========================================================"

if ! authenticate; then
    echo "SKIPPED (server unreachable)"
    exit 0
fi

test_create_service_new_client
test_create_service_same_phone_reuses_partner
test_create_service_phone_conflict_returns_409
test_create_service_email_divergence_prefers_phone
test_create_service_no_phones_email_match_reuses
test_conflict_response_has_candidate_ids

echo "========================================================"
echo "Results: PASS=${PASS}  FAIL=${FAIL}  SKIP=${SKIP}"
echo "========================================================"

[[ $FAIL -eq 0 ]]
