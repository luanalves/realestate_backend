#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../18.0/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
else
    echo "ERROR: .env file not found at $ENV_FILE"
    exit 1
fi

BASE_URL="${BASE_URL:-${ODOO_BASE_URL:-http://localhost:8069}}"
API_USER_EMAIL="${OWNER_EMAIL:-${SEED_OWNER_EMAIL:-${TEST_MANAGER_EMAIL:-}}}"
API_USER_PASS="${OWNER_PASS:-${SEED_OWNER_PASSWORD:-${TEST_MANAGER_PASSWORD:-}}}"
: "${API_USER_EMAIL:?OWNER_EMAIL, SEED_OWNER_EMAIL, or TEST_MANAGER_EMAIL is required in 18.0/.env}"
: "${API_USER_PASS:?OWNER_PASS, SEED_OWNER_PASSWORD, or TEST_MANAGER_PASSWORD is required in 18.0/.env}"
: "${OAUTH_CLIENT_ID:?OAUTH_CLIENT_ID is required in 18.0/.env}"
: "${OAUTH_CLIENT_SECRET:?OAUTH_CLIENT_SECRET is required in 18.0/.env}"

PASS=0
FAIL=0

_log() { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { _log "PASS: $*"; PASS=$((PASS + 1)); }
_fail() { _log "FAIL: $*"; FAIL=$((FAIL + 1)); }

_auth() {
    local jwt sid company_id response
    jwt=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"$OAUTH_CLIENT_ID\",\"client_secret\":\"$OAUTH_CLIENT_SECRET\"}" \
        | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
    [ -z "$jwt" ] && return 1

    response=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt" \
        -d "{\"email\":\"$API_USER_EMAIL\",\"password\":\"$API_USER_PASS\"}")
    sid=$(echo "$response" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
    company_id=$(echo "$response" | python3 -c "import json,sys; data=json.load(sys.stdin); print((data.get('user') or {}).get('company_id') or data.get('company_id') or '')" 2>/dev/null || echo "")
    [ -z "$sid" ] && return 1
    [ -z "$company_id" ] && company_id="${TEST_COMPANY_ID:-1}"
    echo "$jwt|$sid|$company_id"
}

_assert_code() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        _pass "$label (HTTP $actual)"
    else
        _fail "$label (expected HTTP $expected, got $actual)"
    fi
}

_assert_json_true() {
    local label="$1" file="$2" expression="$3"
    if python3 -c "import json; data=json.load(open('$file')); assert bool($expression)" 2>/dev/null; then
        _pass "$label"
    else
        _fail "$label"
    fi
}

UNAUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/properties/options")
_assert_code "Options requires auth" 401 "$UNAUTH_CODE"

AUTH=$(_auth) || { _fail "Auth failed"; exit 1; }
JWT="${AUTH%%|*}"
REST="${AUTH#*|}"
SID="${REST%%|*}"
COMPANY_ID="${REST#*|}"
H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID" -H "X-Company-Id: $COMPANY_ID" -H "Content-Type: application/json")
_pass "Auth"

OPTIONS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/properties/options" "${H[@]}")
OPTIONS_CODE=$(echo "$OPTIONS_RESPONSE" | tail -1)
echo "$OPTIONS_RESPONSE" | sed '$d' > /tmp/us16_property_options.json
_assert_code "List property options" 200 "$OPTIONS_CODE"

_assert_json_true "source_medium includes website" /tmp/us16_property_options.json "any(item.get('value') == 'website' and item.get('label') == 'Website' for item in data.get('source_medium', []))"
_assert_json_true "zoning includes residential" /tmp/us16_property_options.json "any(item.get('value') == 'residential' for item in data.get('zoning', []))"
_assert_json_true "property_status includes available" /tmp/us16_property_options.json "any(item.get('value') == 'available' for item in data.get('property_status', []))"
_assert_json_true "condition includes excellent" /tmp/us16_property_options.json "any(item.get('value') == 'excellent' for item in data.get('condition', []))"
_assert_json_true "tags points to options endpoint" /tmp/us16_property_options.json "any(item.get('field') == 'tags' and item.get('options_endpoint') == '/api/v1/tags' and 'string' in item.get('accepted_values', []) and 'integer' in item.get('accepted_values', []) for item in data.get('multi_value_fields', []))"
_assert_json_true "image and file arrays are documented" /tmp/us16_property_options.json "all(field in {item.get('field') for item in data.get('multi_value_fields', [])} for field in ('property_images', 'property_files'))"
_assert_json_true "related option endpoints are exposed" /tmp/us16_property_options.json "data.get('related_options', {}).get('property_type_id') == '/api/v1/property-types' and data.get('related_options', {}).get('tags') == '/api/v1/tags'"

TAGS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/tags" "${H[@]}")
TAGS_CODE=$(echo "$TAGS_RESPONSE" | tail -1)
_assert_code "Tags options endpoint remains available" 200 "$TAGS_CODE"

echo "US16 Property Options: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
