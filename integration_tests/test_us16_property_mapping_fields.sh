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

_assert_json_true() {
    local label="$1" file="$2" expression="$3"
    if python3 -c "import json; data=json.load(open('$file')); assert bool($expression)" 2>/dev/null; then
        _pass "$label"
    else
        _fail "$label"
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
  "total_area": 250,
  "private_area": 180,
  "land_area": 320,
  "zip_code": "01310-100",
  "state_id": $STATE_ID,
  "city": "Sao Paulo",
  "street": "Rua Original",
  "street_number": "100",
  "complement": "Suite 12",
  "neighborhood": "Bela Vista",
  "location_type_id": $LOCATION_TYPE_ID,
  "company_ids": [$COMPANY_ID],
  "description": "<p>US16 complete property description</p>",
  "description_short": "US16 short description",
  "price": 850000,
  "rent_price": 4200,
  "property_status": "available",
  "property_purpose": "residential",
  "condition": "excellent",
  "num_rooms": 4,
  "num_suites": 1,
  "num_bathrooms": 3,
  "num_parking": 2,
  "construction_year": 2012,
  "for_sale": true,
  "for_rent": true,
  "accepts_financing": true,
  "accepts_fgts": true,
  "floor_number": 8,
  "unit_number": "81B",
  "num_floors": 18,
  "iptu_annual": 3600,
  "insurance_value": 980,
  "condominium_fee": 750,
  "authorization_start_date": "2026-01-15",
  "authorization_end_date": "2026-12-15",
  "owner_email": "owner.us16.$TS@example.com",
  "owner_home_phone": "(11) 3333-4444",
  "owner_business_phone": "(11) 2222-3333",
  "owner_mobile_phone": "(11) 98888-7777",
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
  "zoning_restrictions": "US16 zoning restriction note",
  "internal_comments": "internal api note",
  "tags": ["US16 Mapping", "Property API"],
  "key_location": "front desk",
  "advertise": true,
  "featured_property": true,
  "virtual_tour": "https://example.com/tour",
  "sign_on_site": true,
  "super_featured": false,
  "youtube_video": "https://youtube.com/watch?v=abc123",
  "meta_title": "US16 Meta Title",
  "meta_description": "US16 meta description",
  "meta_keywords": "us16,property,mapping",
  "sign_type": "sale",
  "sign_installation_date": "2026-02-01",
  "sign_removal_date": "2026-11-30",
  "sign_notes": "US16 sign note",
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
  "documentation_observations": "docs ok",
  "property_files": [
    {
      "name": "us16-document.txt",
      "file_name": "us16-document.txt",
      "file": "VVMxNiBkb2N1bWVudCBjb250ZW50",
      "document_type": "other",
      "description": "US16 API document"
    }
  ]
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
    _assert_json_eq "Create returns price" /tmp/us16_property_create.json price "850000.0"
    _assert_json_eq "Create returns description" /tmp/us16_property_create.json description "<p>US16 complete property description</p>"
    _assert_json_eq "Create returns bedrooms" /tmp/us16_property_create.json features.bedrooms "4"
    _assert_json_eq "Create returns suites" /tmp/us16_property_create.json features.suites "1"
    _assert_json_eq "Create returns bathrooms" /tmp/us16_property_create.json features.bathrooms "3"
    _assert_json_eq "Create returns parking spaces" /tmp/us16_property_create.json features.parking_spaces "2"
    _assert_json_eq "Create returns total_area" /tmp/us16_property_create.json features.total_area "250.0"
    _assert_json_eq "Create returns owner_home_phone" /tmp/us16_property_create.json owner_home_phone "(11) 3333-4444"
    _assert_json_eq "Create returns owner_business_phone" /tmp/us16_property_create.json owner_business_phone "(11) 2222-3333"
    _assert_json_eq "Create returns owner_mobile_phone" /tmp/us16_property_create.json owner_mobile_phone "(11) 98888-7777"
    _assert_json_eq "Create returns source_medium" /tmp/us16_property_create.json source_medium "website"
    _assert_json_eq "Create returns send_activities_to_owner" /tmp/us16_property_create.json send_activities_to_owner "True"
    _assert_json_eq "Create returns search_street alias" /tmp/us16_property_create.json search_street "Rua API Mapping"
    _assert_json_eq "Create returns registered_by" /tmp/us16_property_create.json registered_by "Integration US16"
    _assert_json_eq "Create returns alternative_reference" /tmp/us16_property_create.json alternative_reference "ALT-$TS"
    _assert_json_eq "Create returns intention" /tmp/us16_property_create.json intention "sale"
    _assert_json_eq "Create returns iptu_payment_condition" /tmp/us16_property_create.json iptu_payment_condition "annual"
    _assert_json_eq "Create returns iptu_value" /tmp/us16_property_create.json iptu_value "1200.00"
    _assert_json_eq "Create returns rental_guarantee_insurance" /tmp/us16_property_create.json rental_guarantee_insurance "required"
    _assert_json_eq "Create returns fire_insurance" /tmp/us16_property_create.json fire_insurance "included"
    _assert_json_eq "Create returns exclusivity" /tmp/us16_property_create.json exclusivity "True"
    _assert_json_eq "Create returns property_situation" /tmp/us16_property_create.json property_situation "available"
    _assert_json_eq "Create returns year_of_renovation" /tmp/us16_property_create.json year_of_renovation "2020"
    _assert_json_eq "Create returns zoning" /tmp/us16_property_create.json zoning "residential"
    _assert_json_eq "Create returns internal_comments" /tmp/us16_property_create.json internal_comments "internal api note"
    _assert_json_true "Create returns tags" /tmp/us16_property_create.json "'US16 Mapping' in data.get('tags', []) and 'Property API' in data.get('tags', [])"
    _assert_json_eq "Create returns key_location" /tmp/us16_property_create.json key_location "front desk"
    _assert_json_eq "Create returns advertise" /tmp/us16_property_create.json advertise "True"
    _assert_json_eq "Create returns featured_property" /tmp/us16_property_create.json featured_property "True"
    _assert_json_eq "Create returns virtual_tour" /tmp/us16_property_create.json virtual_tour "https://example.com/tour"
    _assert_json_eq "Create returns sign_on_site" /tmp/us16_property_create.json sign_on_site "True"
    _assert_json_eq "Create returns super_featured" /tmp/us16_property_create.json super_featured "False"
    _assert_json_eq "Create returns youtube_video" /tmp/us16_property_create.json youtube_video "https://youtube.com/watch?v=abc123"
    _assert_json_eq "Create returns commission_type" /tmp/us16_property_create.json commission_type "percentage"
    _assert_json_eq "Create returns captured_intention" /tmp/us16_property_create.json captured_intention "sale"
    _assert_json_eq "Create returns included_in_commission_date" /tmp/us16_property_create.json included_in_commission_date "2026-05-04"
    _assert_json_eq "Create returns commercial_condition" /tmp/us16_property_create.json commercial_condition "standard"
    _assert_json_eq "Create returns iptu_code" /tmp/us16_property_create.json iptu_code "IPTU-$TS"
    _assert_json_eq "Create returns registration_number" /tmp/us16_property_create.json registration_number "REG-$TS"
    _assert_json_eq "Create returns electricity_network_code" /tmp/us16_property_create.json electricity_network_code "ELEC-$TS"
    _assert_json_eq "Create returns water_network_code" /tmp/us16_property_create.json water_network_code "WATER-$TS"
    _assert_json_eq "Create returns titles_rights" /tmp/us16_property_create.json titles_rights "ok"
    _assert_json_eq "Create returns approved_environmental_agency" /tmp/us16_property_create.json approved_environmental_agency "True"
    _assert_json_eq "Create returns approved_project" /tmp/us16_property_create.json approved_project "True"
    _assert_json_eq "Create returns documentation_observations" /tmp/us16_property_create.json documentation_observations "docs ok"
    _assert_json_true "Create returns property_files metadata" /tmp/us16_property_create.json "len(data.get('property_files', [])) == 1 and data['property_files'][0].get('name') == 'us16-document.txt' and data['property_files'][0].get('size', 0) > 0 and bool(data['property_files'][0].get('download_url'))"

    DETAIL_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/properties/$PROPERTY_ID" "${H[@]}")
    DETAIL_CODE=$(echo "$DETAIL_RESPONSE" | tail -1)
    echo "$DETAIL_RESPONSE" | sed '$d' > /tmp/us16_property_detail.json
    _assert_code "Get property detail" 200 "$DETAIL_CODE"
    _assert_json_eq "Detail returns commission date" /tmp/us16_property_detail.json included_in_commission_date "2026-05-04"
    _assert_json_true "Detail returns files metadata" /tmp/us16_property_detail.json "len(data.get('property_files', [])) == 1"

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
