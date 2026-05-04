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

_json_get() {
    python3 -c "import json,sys; data=json.load(sys.stdin); cur=data; [cur := cur.get(p, {}) if isinstance(cur, dict) else {} for p in '$1'.split('.')]; print(cur if cur not in ({}, None) else '')"
}

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

_assert_json_eq() {
    local label="$1" file="$2" path="$3" expected="$4" actual
    actual=$(python3 -c "import json,sys; data=json.load(open('$file')); cur=data; [cur := cur.get(p, {}) if isinstance(cur, dict) else {} for p in '$path'.split('.')]; print(cur)" 2>/dev/null || echo "")
    if [ "$actual" = "$expected" ]; then
        _pass "$label"
    else
        _fail "$label (expected '$expected', got '$actual')"
    fi
}

AUTH=$(_auth) || { _fail "Auth failed"; exit 1; }
JWT="${AUTH%%|*}"
REST="${AUTH#*|}"
SID="${REST%%|*}"
COMPANY_ID="${REST#*|}"
H=(-H "Authorization: Bearer $JWT" -H "X-Openerp-Session-Id: $SID" -H "Content-Type: application/json")
_pass "Auth"

PROPERTY_TYPE_ID=$(curl -s "$BASE_URL/api/v1/property-types" "${H[@]}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")
LOCATION_TYPE_ID=$(curl -s "$BASE_URL/api/v1/location-types" "${H[@]}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")
STATE_ID=$(curl -s "$BASE_URL/api/v1/states?country_id=31" "${H[@]}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data[0]['id'] if data else '')")

[ -n "$PROPERTY_TYPE_ID" ] && [ -n "$LOCATION_TYPE_ID" ] && [ -n "$STATE_ID" ] || {
    _fail "Required master data not found"
    exit 1
}

TS=$(date +%Y%m%d%H%M%S)
CREATE_PAYLOAD=$(cat <<JSON
{
  "name": "US16 Mapping Property $TS",
  "property_type_id": $PROPERTY_TYPE_ID,
  "area": 120,
  "zip_code": "01310-100",
  "state_id": $STATE_ID,
  "city": "Sao Paulo",
  "street": "Rua Original",
  "street_number": "100",
  "location_type_id": $LOCATION_TYPE_ID,
  "company_ids": [$COMPANY_ID],
  "owner_email": "owner.us16.$TS@example.com",
  "owner_home_phone": "(11) 3333-4444",
  "source_medium": "website",
  "send_activities_to_owner": true,
  "search_street": "Rua API Mapping",
  "registered_by": "Integration US16",
  "alternative_reference": "ALT-$TS",
  "intention": "sale",
  "iptu_payment_condition": "annual",
  "iptu_value": "1200.00",
  "rental_guarantee_insurance": "required",
  "fire_insurance": "included",
  "exclusivity": true,
  "property_situation": "available",
  "year_of_renovation": "2020",
  "zoning": "residential",
  "internal_comments": "internal api note",
  "tags": ["US16 Mapping", "Property API"],
  "key_location": "front desk",
  "advertise": true,
  "featured_property": true,
  "virtual_tour": "https://example.com/tour",
  "sign_on_site": true,
  "super_featured": false,
  "youtube_video": "https://youtube.com/watch?v=abc123",
  "commission_type": "percentage",
  "captured_intention": "sale",
  "included_in_commission_date": "2026-05-04",
  "commercial_condition": "standard",
  "iptu_code": "IPTU-$TS",
  "registration_number": "REG-$TS",
  "electricity_network_code": "ELEC-$TS",
  "water_network_code": "WATER-$TS",
  "titles_rights": "ok",
  "approved_environmental_agency": true,
  "approved_project": true,
  "documentation_observations": "docs ok"
}
JSON
)

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/properties" "${H[@]}" -d "$CREATE_PAYLOAD")
CREATE_CODE=$(echo "$CREATE_RESPONSE" | tail -1)
echo "$CREATE_RESPONSE" | sed '$d' > /tmp/us16_property_create.json
_assert_code "Create property with mapping fields" 201 "$CREATE_CODE"
PROPERTY_ID=$(python3 -c "import json; print(json.load(open('/tmp/us16_property_create.json')).get('id',''))" 2>/dev/null || echo "")

if [ -n "$PROPERTY_ID" ]; then
    _assert_json_eq "Create returns owner_email" /tmp/us16_property_create.json owner_email "owner.us16.$TS@example.com"
    _assert_json_eq "Create returns search_street alias" /tmp/us16_property_create.json search_street "Rua API Mapping"
    _assert_json_eq "Create returns documentation flag" /tmp/us16_property_create.json approved_project "True"

    DETAIL_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/properties/$PROPERTY_ID" "${H[@]}")
    DETAIL_CODE=$(echo "$DETAIL_RESPONSE" | tail -1)
    echo "$DETAIL_RESPONSE" | sed '$d' > /tmp/us16_property_detail.json
    _assert_code "Get property detail" 200 "$DETAIL_CODE"
    _assert_json_eq "Detail returns commission date" /tmp/us16_property_detail.json included_in_commission_date "2026-05-04"

    LIST_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/properties?company_ids=$COMPANY_ID&limit=5" "${H[@]}")
    LIST_CODE=$(echo "$LIST_RESPONSE" | tail -1)
    _assert_code "List properties includes mapping schema" 200 "$LIST_CODE"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/properties/$PROPERTY_ID" "${H[@]}" \
        -d '{"owner_email":"updated.us16@example.com","send_activities_to_owner":false,"tags":["US16 Updated"]}')
    UPDATE_CODE=$(echo "$UPDATE_RESPONSE" | tail -1)
    echo "$UPDATE_RESPONSE" | sed '$d' > /tmp/us16_property_update.json
    _assert_code "Update mapping fields" 200 "$UPDATE_CODE"
    _assert_json_eq "Update returns owner_email" /tmp/us16_property_update.json owner_email "updated.us16@example.com"

    BAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/properties/$PROPERTY_ID" "${H[@]}" \
        -d '{"owner_email":"not-an-email"}')
    BAD_CODE=$(echo "$BAD_RESPONSE" | tail -1)
    _assert_code "Invalid email rejected" 400 "$BAD_CODE"
else
    _fail "Property ID not returned"
fi

echo "US16 Property Mapping Fields: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
