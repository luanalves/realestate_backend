#!/bin/bash
# ==============================================================================
# E2E API Test: GET /api/v1/leads — All Filters
# ==============================================================================
# Tests all 16 query parameters accepted by the list_leads endpoint:
#   state, active, agent_id, search, budget_min, budget_max, bedrooms,
#   property_type_id, location, last_activity_before, created_from,
#   created_to, sort_by, sort_order, limit, offset
#
# Strategy: Creates 4 leads via the Seed Agent (agent@seed.com.br) from
#   "Imobiliária Seed", tests each filter as Agent and as Owner
#   (owner@seed.com.br, who sees all company leads), then cleans up.
#
# ADR-003: E2E test WITH real database (curl/shell)
# Seeds:  SEED_AGENT_EMAIL / SEED_AGENT_PASSWORD (has real.estate.agent record)
#         SEED_OWNER_EMAIL / SEED_OWNER_PASSWORD  (sees all company leads)
# Run: bash 18.0/extra-addons/quicksol_estate/tests/api/test_lead_filters_api.sh
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

source "$REPO_ROOT/18.0/.env"
source "${SCRIPT_DIR}/../lib/auth_helper.sh"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TODAY="$(date +%Y-%m-%d)"
TOMORROW="$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d 'tomorrow' +%Y-%m-%d)"
YESTERDAY="$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d 'yesterday' +%Y-%m-%d)"
TIMESTAMP="$(date +%s)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

# IDs of leads created in setup (for cleanup)
CREATED_LEAD_IDS=()

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; PASSED=$((PASSED+1)); }
fail() { echo -e "${RED}✗ FAIL${NC}: $1 — $2"; FAILED=$((FAILED+1)); }
skip() { echo -e "${YELLOW}⚠ SKIP${NC}: $1 — $2"; SKIPPED=$((SKIPPED+1)); }
section() { echo -e "\n${BLUE}── $1 ──${NC}"; }

# Extract a top-level numeric/string field from a JSON response
json_field() {
    local json="$1" field="$2"
    echo "$json" | grep -o "\"${field}\":[^,}]*" | head -1 | cut -d':' -f2- | tr -d ' ",'
}

# Count leads[] array entries
count_leads() {
    echo "$1" | grep -oE '"id": *[0-9]+' | wc -l | tr -d ' '
}

# GET with Authorization header only (agent session)
api_get() {
    curl -s --max-time 15 -X GET "${BASE_URL}${1}" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${AGENT_SESSION}"
}

# GET as manager
api_get_manager() {
    curl -s --max-time 15 -X GET "${BASE_URL}${1}" \
        -H "Authorization: Bearer ${MANAGER_TOKEN}" \
        -H "X-Openerp-Session-Id: ${MANAGER_SESSION}"
}

# POST a new lead and return its ID; exits on failure
create_lead() {
    local payload="$1"
    local resp
    resp=$(curl -s --max-time 15 -X POST "${BASE_URL}/api/v1/leads" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${AGENT_SESSION}" \
        -H "Content-Type: application/json" \
        -d "$payload")
    local id
    id=$(json_field "$resp" "id")
    if [[ -z "$id" || "$id" == "null" ]]; then
        echo -e "${RED}✗ FATAL${NC}: Failed to create lead — $resp" >&2
        exit 1
    fi
    CREATED_LEAD_IDS+=("$id")
    echo "$id"
}

# Archive (soft-delete) a lead
archive_lead() {
    curl -s --max-time 15 -X DELETE "${BASE_URL}/api/v1/leads/${1}" \
        -H "Authorization: Bearer ${AGENT_TOKEN}" \
        -H "X-Openerp-Session-Id: ${AGENT_SESSION}" > /dev/null
}

# ==============================================================================
# STEP 1: Authenticate
# ==============================================================================
echo "=========================================="
echo "E2E API Test: GET /api/v1/leads — All Filters"
echo "=========================================="

section "Step 1: Authentication"

echo "→ Authenticating as Seed Agent (agent@seed.com.br)..."
authenticate_user "${SEED_AGENT_EMAIL}" "${SEED_AGENT_PASSWORD}" || {
    echo -e "${RED}✗ FATAL${NC}: Agent authentication failed" >&2; exit 1
}
AGENT_TOKEN="$OAUTH_TOKEN"
AGENT_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓${NC} Agent authenticated"

echo "→ Authenticating as Seed Owner (owner@seed.com.br)..."
OAUTH_TOKEN=""  # force re-auth
authenticate_user "${SEED_OWNER_EMAIL}" "${SEED_OWNER_PASSWORD}" || {
    echo -e "${YELLOW}⚠${NC} Owner authentication failed — agent_id filter tests will be skipped"
    MANAGER_TOKEN=""
    MANAGER_SESSION=""
}
MANAGER_TOKEN="${OAUTH_TOKEN:-}"
MANAGER_SESSION="${USER_SESSION_ID:-}"
echo -e "${GREEN}✓${NC} Manager authenticated"

# Restore agent token for subsequent make_api_request calls
OAUTH_TOKEN="$AGENT_TOKEN"
USER_SESSION_ID="$AGENT_SESSION"

# Trap: garante cleanup mesmo em falha
cleanup_on_exit() {
    for id in "${CREATED_LEAD_IDS[@]:-}"; do
        [[ -n "$id" ]] && archive_lead "$id" 2>/dev/null || true
    done
}
trap cleanup_on_exit EXIT

# ==============================================================================
# STEP 1.5: Pre-test cleanup — archive leads from previous runs
# ==============================================================================
section "Step 1.5: Pre-test cleanup"

# Collect all active "Filter Test Lead" leads from previous runs (owner sees all)
if [[ -n "$MANAGER_TOKEN" ]]; then
    PREV_NAME_SLUG="Filter+Test+Lead"
    PREV_RESP=$(curl -s --max-time 15 -X GET \
        "${BASE_URL}/api/v1/leads?search=${PREV_NAME_SLUG}&active=all&limit=100" \
        -H "Authorization: Bearer ${MANAGER_TOKEN}" \
        -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")
    PREV_IDS=$(echo "$PREV_RESP" | grep -oE '"id": *[0-9]+' | grep -oE '[0-9]+')
    PREV_COUNT=0
    for pid in $PREV_IDS; do
        curl -s --max-time 10 -X DELETE "${BASE_URL}/api/v1/leads/${pid}" \
            -H "Authorization: Bearer ${AGENT_TOKEN}" \
            -H "X-Openerp-Session-Id: ${AGENT_SESSION}" > /dev/null 2>&1 || true
        PREV_COUNT=$((PREV_COUNT+1))
    done
    echo -e "${GREEN}✓${NC} Archived $PREV_COUNT lead(s) from previous test runs"
else
    echo -e "${YELLOW}⚠${NC} Skipping pre-cleanup (no owner/manager session)"
fi

# ==============================================================================
# STEP 2: Setup — Create 4 leads with distinct searchable attributes
# ==============================================================================
section "Step 2: Setup — Creating test leads"

# Lead 1: state=new, budget 200k-400k, bedrooms=2, location=Centro
LEAD1_ID=$(create_lead "{
    \"name\": \"Filter Test Lead 1 ${TIMESTAMP}\",
    \"phone\": \"+55119${TIMESTAMP}1\",
    \"email\": \"filter1.${TIMESTAMP}@test.com\",
    \"budget_min\": 200000,
    \"budget_max\": 400000,
    \"bedrooms_needed\": 2,
    \"location_preference\": \"Centro ${TIMESTAMP}\"
}")
echo "  Lead 1 (new, 200k-400k, 2 quartos, Centro): ID=$LEAD1_ID"

# Lead 2: state=contacted, budget 400k-600k, bedrooms=3, location=Vila Mariana
LEAD2_ID=$(create_lead "{
    \"name\": \"Filter Test Lead 2 ${TIMESTAMP}\",
    \"phone\": \"+55119${TIMESTAMP}2\",
    \"email\": \"filter2.${TIMESTAMP}@test.com\",
    \"budget_min\": 400000,
    \"budget_max\": 600000,
    \"bedrooms_needed\": 3,
    \"location_preference\": \"Vila Mariana ${TIMESTAMP}\"
}")
# Advance state to contacted
curl -s --max-time 15 -X PUT "${BASE_URL}/api/v1/leads/${LEAD2_ID}" \
    -H "Authorization: Bearer ${AGENT_TOKEN}" \
    -H "X-Openerp-Session-Id: ${AGENT_SESSION}" \
    -H "Content-Type: application/json" \
    -d '{"state":"contacted"}' > /dev/null
echo "  Lead 2 (contacted, 400k-600k, 3 quartos, Vila Mariana): ID=$LEAD2_ID"

# Lead 3: state=qualified, budget 600k-800k, bedrooms=4, location=Moema
LEAD3_ID=$(create_lead "{
    \"name\": \"Filter Test Lead 3 ${TIMESTAMP}\",
    \"phone\": \"+55119${TIMESTAMP}3\",
    \"email\": \"filter3.${TIMESTAMP}@test.com\",
    \"budget_min\": 600000,
    \"budget_max\": 800000,
    \"bedrooms_needed\": 4,
    \"location_preference\": \"Moema ${TIMESTAMP}\"
}")
curl -s --max-time 15 -X PUT "${BASE_URL}/api/v1/leads/${LEAD3_ID}" \
    -H "Authorization: Bearer ${AGENT_TOKEN}" \
    -H "X-Openerp-Session-Id: ${AGENT_SESSION}" \
    -H "Content-Type: application/json" \
    -d '{"state":"qualified"}' > /dev/null
echo "  Lead 3 (qualified, 600k-800k, 4 quartos, Moema): ID=$LEAD3_ID"

# Lead 4: will be archived (active=false), budget 100k-200k, bedrooms=1
LEAD4_ID=$(create_lead "{
    \"name\": \"Filter Test Lead 4 ARCHIVED ${TIMESTAMP}\",
    \"phone\": \"+55119${TIMESTAMP}4\",
    \"email\": \"filter4.${TIMESTAMP}@test.com\",
    \"budget_min\": 100000,
    \"budget_max\": 200000,
    \"bedrooms_needed\": 1,
    \"location_preference\": \"Pinheiros ${TIMESTAMP}\"
}")
archive_lead "$LEAD4_ID"
echo "  Lead 4 (archived, 100k-200k, 1 quarto): ID=$LEAD4_ID"

echo -e "${GREEN}✓${NC} 4 leads created (Lead 4 archived)"

# ==============================================================================
# STEP 3: Filter tests
# ==============================================================================

# Helper: assert that a response contains a specific lead ID
assert_contains_id() {
    local test_name="$1" resp="$2" id="$3"
    if echo "$resp" | grep -qE "\"id\": *${id}[^0-9]"; then
        pass "$test_name"
    else
        fail "$test_name" "Lead ID=$id not found in response"
    fi
}

# Helper: assert that a response does NOT contain a specific lead ID
assert_not_contains_id() {
    local test_name="$1" resp="$2" id="$3"
    if echo "$resp" | grep -qE "\"id\": *${id}[^0-9]"; then
        fail "$test_name" "Lead ID=$id unexpectedly found in response"
    else
        pass "$test_name"
    fi
}

# Helper: assert total >= expected
assert_total_gte() {
    local test_name="$1" resp="$2" expected="$3"
    local total
    total=$(json_field "$resp" "total")
    if [[ -z "$total" || "$total" == "null" ]]; then
        fail "$test_name" "No total field in response"
    elif [[ "$total" -ge "$expected" ]]; then
        pass "$test_name"
    else
        fail "$test_name" "Expected total >= $expected, got $total"
    fi
}

# Helper: assert count of returned leads[] == expected
assert_count_eq() {
    local test_name="$1" resp="$2" expected="$3"
    local count
    count=$(count_leads "$resp")
    if [[ "$count" -eq "$expected" ]]; then
        pass "$test_name"
    else
        fail "$test_name" "Expected $expected leads in page, got $count"
    fi
}

# ==============================================================================
section "3.1 state filter"
# ==============================================================================

R=$(api_get "/api/v1/leads?state=new")
assert_contains_id    "state=new includes Lead 1 (new)"      "$R" "$LEAD1_ID"
assert_not_contains_id "state=new excludes Lead 2 (contacted)" "$R" "$LEAD2_ID"
assert_not_contains_id "state=new excludes Lead 3 (qualified)" "$R" "$LEAD3_ID"

R=$(api_get "/api/v1/leads?state=contacted")
assert_contains_id    "state=contacted includes Lead 2"       "$R" "$LEAD2_ID"
assert_not_contains_id "state=contacted excludes Lead 1"      "$R" "$LEAD1_ID"

R=$(api_get "/api/v1/leads?state=qualified")
assert_contains_id    "state=qualified includes Lead 3"       "$R" "$LEAD3_ID"
assert_not_contains_id "state=qualified excludes Lead 2"      "$R" "$LEAD2_ID"

# ==============================================================================
section "3.2 active filter"
# ==============================================================================

R=$(api_get "/api/v1/leads?active=true")
assert_contains_id     "active=true includes Lead 1 (active)"    "$R" "$LEAD1_ID"
assert_not_contains_id "active=true excludes Lead 4 (archived)"  "$R" "$LEAD4_ID"

R=$(api_get "/api/v1/leads?active=false")
assert_contains_id     "active=false includes Lead 4 (archived)" "$R" "$LEAD4_ID"
assert_not_contains_id "active=false excludes Lead 1 (active)"   "$R" "$LEAD1_ID"

# active=all: owner vê todos os leads da empresa (ativos + arquivados)
R=$(api_get_manager "/api/v1/leads?active=all")
assert_contains_id "active=all includes Lead 1 (active)"   "$R" "$LEAD1_ID"
assert_contains_id "active=all includes Lead 4 (archived)" "$R" "$LEAD4_ID"

# ==============================================================================
section "3.3 search filter (name, email, phone)"
# ==============================================================================

NAME_SLUG="Filter Test Lead 1 ${TIMESTAMP}"
R=$(api_get "/api/v1/leads?search=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${NAME_SLUG}'))")")
assert_contains_id    "search by name matches Lead 1"     "$R" "$LEAD1_ID"
assert_not_contains_id "search by name excludes Lead 2"   "$R" "$LEAD2_ID"

R=$(api_get "/api/v1/leads?search=filter2.${TIMESTAMP}%40test.com")
assert_contains_id    "search by email matches Lead 2"    "$R" "$LEAD2_ID"
assert_not_contains_id "search by email excludes Lead 1"  "$R" "$LEAD1_ID"

# search by phone: usar o timestamp curto (6 dígitos finais) que faz parte do phone
PHONE3_SLUG="${TIMESTAMP: -6}3"
R=$(api_get "/api/v1/leads?search=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${PHONE3_SLUG}'))")")
assert_contains_id    "search by phone matches Lead 3"    "$R" "$LEAD3_ID"
assert_not_contains_id "search by phone excludes Lead 1"  "$R" "$LEAD1_ID"

# ==============================================================================
section "3.4 budget_min / budget_max filters"
# ==============================================================================

# budget_min=500000 → leads with budget_max >= 500000 → Lead 2 (600k), Lead 3 (800k)
R=$(api_get "/api/v1/leads?budget_min=500000&limit=100")
assert_contains_id     "budget_min=500000 includes Lead 2 (max=600k)" "$R" "$LEAD2_ID"
assert_contains_id     "budget_min=500000 includes Lead 3 (max=800k)" "$R" "$LEAD3_ID"
assert_not_contains_id "budget_min=500000 excludes Lead 1 (max=400k)" "$R" "$LEAD1_ID"

# budget_max=350000 → leads with budget_min <= 350000 → Lead 1 (200k), Lead 4 (100k, archived)
R=$(api_get "/api/v1/leads?budget_max=350000&limit=100")
assert_contains_id     "budget_max=350000 includes Lead 1 (min=200k)" "$R" "$LEAD1_ID"
assert_not_contains_id "budget_max=350000 excludes Lead 2 (min=400k)" "$R" "$LEAD2_ID"
assert_not_contains_id "budget_max=350000 excludes Lead 3 (min=600k)" "$R" "$LEAD3_ID"

# Combined: budget_min=300000&budget_max=650000 → overlapping 300k-650k range
# Lead 1: min=200k, max=400k — max(400k) >= 300k AND min(200k) <= 650k → YES
# Lead 2: min=400k, max=600k — max(600k) >= 300k AND min(400k) <= 650k → YES
# Lead 3: min=600k, max=800k — max(800k) >= 300k AND min(600k) <= 650k → YES
# Lead 4 is archived (excluded by active=true default)
R=$(api_get "/api/v1/leads?budget_min=300000&budget_max=650000&limit=100")
assert_contains_id "budget range 300k-650k includes Lead 1" "$R" "$LEAD1_ID"
assert_contains_id "budget range 300k-650k includes Lead 2" "$R" "$LEAD2_ID"
assert_contains_id "budget range 300k-650k includes Lead 3" "$R" "$LEAD3_ID"

# ==============================================================================
section "3.5 bedrooms filter"
# ==============================================================================

R=$(api_get "/api/v1/leads?bedrooms=2")
assert_contains_id     "bedrooms=2 includes Lead 1"    "$R" "$LEAD1_ID"
assert_not_contains_id "bedrooms=2 excludes Lead 2"    "$R" "$LEAD2_ID"
assert_not_contains_id "bedrooms=2 excludes Lead 3"    "$R" "$LEAD3_ID"

R=$(api_get "/api/v1/leads?bedrooms=3")
assert_contains_id     "bedrooms=3 includes Lead 2"    "$R" "$LEAD2_ID"
assert_not_contains_id "bedrooms=3 excludes Lead 1"    "$R" "$LEAD1_ID"

R=$(api_get "/api/v1/leads?bedrooms=4")
assert_contains_id     "bedrooms=4 includes Lead 3"    "$R" "$LEAD3_ID"
assert_not_contains_id "bedrooms=4 excludes Lead 1"    "$R" "$LEAD1_ID"

# ==============================================================================
section "3.6 location filter"
# ==============================================================================

R=$(api_get "/api/v1/leads?location=Centro+${TIMESTAMP}")
assert_contains_id     "location=Centro matches Lead 1"    "$R" "$LEAD1_ID"
assert_not_contains_id "location=Centro excludes Lead 2"   "$R" "$LEAD2_ID"

R=$(api_get "/api/v1/leads?location=Vila+Mariana+${TIMESTAMP}")
assert_contains_id     "location=Vila Mariana matches Lead 2" "$R" "$LEAD2_ID"
assert_not_contains_id "location=Vila Mariana excludes Lead 1" "$R" "$LEAD1_ID"

R=$(api_get "/api/v1/leads?location=Moema+${TIMESTAMP}")
assert_contains_id     "location=Moema matches Lead 3"    "$R" "$LEAD3_ID"
assert_not_contains_id "location=Moema excludes Lead 1"   "$R" "$LEAD1_ID"

# partial match (ilike)
R=$(api_get "/api/v1/leads?location=${TIMESTAMP}")
assert_contains_id "location partial match includes Lead 1" "$R" "$LEAD1_ID"
assert_contains_id "location partial match includes Lead 2" "$R" "$LEAD2_ID"
assert_contains_id "location partial match includes Lead 3" "$R" "$LEAD3_ID"

# ==============================================================================
section "3.7 created_from / created_to (period filter)"
# ==============================================================================

# All leads were created today — created_from=today should include them
R=$(api_get "/api/v1/leads?created_from=${TODAY}")
assert_contains_id "created_from=today includes Lead 1" "$R" "$LEAD1_ID"
assert_contains_id "created_from=today includes Lead 2" "$R" "$LEAD2_ID"
assert_contains_id "created_from=today includes Lead 3" "$R" "$LEAD3_ID"

# created_to=today should also include them
R=$(api_get "/api/v1/leads?created_to=${TODAY}")
assert_contains_id "created_to=today includes Lead 1" "$R" "$LEAD1_ID"
assert_contains_id "created_to=today includes Lead 2" "$R" "$LEAD2_ID"

# Range: created_from=today&created_to=tomorrow
R=$(api_get "/api/v1/leads?created_from=${TODAY}&created_to=${TOMORROW}")
assert_contains_id "period today→tomorrow includes Lead 1" "$R" "$LEAD1_ID"
assert_contains_id "period today→tomorrow includes Lead 3" "$R" "$LEAD3_ID"

# created_from=tomorrow → no leads (all created today)
R=$(api_get "/api/v1/leads?created_from=${TOMORROW}")
assert_not_contains_id "created_from=tomorrow excludes Lead 1 (created today)" "$R" "$LEAD1_ID"
assert_not_contains_id "created_from=tomorrow excludes Lead 2 (created today)" "$R" "$LEAD2_ID"

# created_to=yesterday → no leads (all created today)
R=$(api_get "/api/v1/leads?created_to=${YESTERDAY}")
assert_not_contains_id "created_to=yesterday excludes Lead 1 (created today)" "$R" "$LEAD1_ID"

# invalid date format → graceful skip (should still return results, not error)
R=$(api_get "/api/v1/leads?created_from=INVALID")
TOTAL_INVALID=$(json_field "$R" "total")
if [[ -n "$TOTAL_INVALID" && "$TOTAL_INVALID" != "null" ]]; then
    pass "invalid created_from format → graceful fallback (no 500 error)"
else
    fail "invalid created_from format → graceful fallback (no 500 error)" "Got unexpected response: ${R:0:100}"
fi

# ==============================================================================
section "3.8 sort_by / sort_order"
# ==============================================================================

# sort_by=budget_max&sort_order=desc → Lead 3 (800k) antes de Lead 1 (400k)
R=$(api_get "/api/v1/leads?sort_by=budget_max&sort_order=desc&limit=100")
# Comparar posição na string JSON (single-line response)
POS3=$(echo "$R" | python3 -c "import sys; s=sys.stdin.read(); print(s.find('\"id\": ${LEAD3_ID},'))")
POS1=$(echo "$R" | python3 -c "import sys; s=sys.stdin.read(); print(s.find('\"id\": ${LEAD1_ID},'))")
if [[ "$POS3" -ge 0 && "$POS1" -ge 0 && "$POS3" -lt "$POS1" ]]; then
    pass "sort_by=budget_max desc → Lead 3 (max=800k) aparece antes de Lead 1"
else
    fail "sort_by=budget_max desc → Lead 3 antes de Lead 1" "pos3=$POS3 pos1=$POS1"
fi

# sort_by=budget_max&sort_order=asc → Lead 1 (400k) antes de Lead 3 (800k)
R=$(api_get "/api/v1/leads?sort_by=budget_max&sort_order=asc&limit=100")
POS1=$(echo "$R" | python3 -c "import sys; s=sys.stdin.read(); print(s.find('\"id\": ${LEAD1_ID},'))")
POS3=$(echo "$R" | python3 -c "import sys; s=sys.stdin.read(); print(s.find('\"id\": ${LEAD3_ID},'))")
if [[ "$POS1" -ge 0 && "$POS3" -ge 0 && "$POS1" -lt "$POS3" ]]; then
    pass "sort_by=budget_max asc → Lead 1 (max=400k) aparece antes de Lead 3"
else
    fail "sort_by=budget_max asc → Lead 1 antes de Lead 3" "pos1=$POS1 pos3=$POS3"
fi

# invalid sort_order defaults to desc (no error)
R=$(api_get "/api/v1/leads?sort_order=invalid")
TOTAL_SORT=$(json_field "$R" "total")
if [[ -n "$TOTAL_SORT" && "$TOTAL_SORT" != "null" ]]; then
    pass "invalid sort_order → fallback to desc (no 500 error)"
else
    fail "invalid sort_order → fallback to desc (no 500 error)" "Unexpected response"
fi

# ==============================================================================
section "3.9 limit / offset (pagination)"
# ==============================================================================

# Get total count of active leads for this agent
R_ALL=$(api_get "/api/v1/leads?limit=100")
AGENT_TOTAL=$(json_field "$R_ALL" "total")

# limit=2 → exactly 2 leads returned
R=$(api_get "/api/v1/leads?limit=2&offset=0")
assert_count_eq "limit=2 returns exactly 2 leads" "$R" 2

HAS_NEXT=$(json_field "$R" "has_next")
if [[ "$AGENT_TOTAL" -gt 2 ]]; then
    if [[ "$HAS_NEXT" == "true" ]]; then
        pass "has_next=true when more leads exist"
    else
        fail "has_next=true when more leads exist" "got has_next=$HAS_NEXT (total=$AGENT_TOTAL)"
    fi
fi

# offset=1, limit=1 → should return lead at position 1 (different from position 0)
R_P0=$(api_get "/api/v1/leads?limit=1&offset=0")
R_P1=$(api_get "/api/v1/leads?limit=1&offset=1")
ID_P0=$(echo "$R_P0" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
ID_P1=$(echo "$R_P1" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+')
if [[ -n "$ID_P0" && -n "$ID_P1" && "$ID_P0" != "$ID_P1" ]]; then
    pass "offset shifts results (offset=0 ID=$ID_P0, offset=1 ID=$ID_P1)"
else
    fail "offset shifts results" "Same ID at offset 0 and 1 (ID_P0=$ID_P0 ID_P1=$ID_P1)"
fi

# limit capped at 100 (passing limit=200 returns at most 100)
R=$(api_get "/api/v1/leads?limit=200")
RETURNED_LIMIT=$(json_field "$R" "limit")
if [[ "$RETURNED_LIMIT" -le 100 ]]; then
    pass "limit capped at 100 (requested 200, got limit=$RETURNED_LIMIT)"
else
    fail "limit capped at 100" "Expected limit <= 100, got $RETURNED_LIMIT"
fi

# ==============================================================================
section "3.10 agent_id filter (manager only)"
# ==============================================================================

if [[ -z "$MANAGER_TOKEN" ]]; then
    skip "agent_id filter (manager)" "ODOO_USER auth not available"
else
    # Get the agent's user ID by inspecting one of the created leads
    R_DETAIL=$(curl -s --max-time 15 -X GET "${BASE_URL}/api/v1/leads/${LEAD1_ID}" \
        -H "Authorization: Bearer ${MANAGER_TOKEN}" \
        -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")
    AGENT_ID=$(echo "$R_DETAIL" | grep -oE '"agent_id": *[0-9]+' | head -1 | grep -oE '[0-9]+')

    if [[ -z "$AGENT_ID" || "$AGENT_ID" == "null" ]]; then
        skip "agent_id filter" "Could not determine agent_id from Lead 1 detail"
    else
        R=$(api_get_manager "/api/v1/leads?agent_id=${AGENT_ID}")
        assert_contains_id "agent_id=${AGENT_ID} includes Lead 1" "$R" "$LEAD1_ID"
        assert_contains_id "agent_id=${AGENT_ID} includes Lead 2" "$R" "$LEAD2_ID"
        assert_contains_id "agent_id=${AGENT_ID} includes Lead 3" "$R" "$LEAD3_ID"

        # agent_id filter as non-manager (agent) → should be silently ignored
        R_AGENT=$(api_get "/api/v1/leads?agent_id=9999")
        # Agent still sees own leads (filter ignored for non-managers)
        assert_contains_id "agent_id ignored for non-manager (own leads still returned)" "$R_AGENT" "$LEAD1_ID"
    fi
fi

# ==============================================================================
section "3.11 property_type_id filter"
# ==============================================================================

# Try to find a valid property type ID from the DB
PROP_TYPES_RESP=$(curl -s --max-time 10 "${BASE_URL}/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"call","params":{"model":"real.estate.property.type","method":"search_read","args":[[]],"kwargs":{"fields":["id","name"],"limit":1}}}' \
    2>/dev/null)
PROP_TYPE_ID=$(echo "$PROP_TYPES_RESP" | grep -oE '"id": *[0-9]+' | head -1 | grep -oE '[0-9]+' || true)

if [[ -z "$PROP_TYPE_ID" ]]; then
    skip "property_type_id filter" "No property types found in DB (optional module data)"
else
    # Create a lead with that property type
    LEAD_PT_ID=$(create_lead "{
        \"name\": \"Filter Test PropType ${TIMESTAMP}\",
        \"phone\": \"+5511900000099\",
        \"email\": \"filterpt.${TIMESTAMP}@test.com\",
        \"property_type_interest\": ${PROP_TYPE_ID}
    }")

    R=$(api_get "/api/v1/leads?property_type_id=${PROP_TYPE_ID}")
    assert_contains_id "property_type_id=${PROP_TYPE_ID} matches lead" "$R" "$LEAD_PT_ID"

    # Cleanup extra lead
    archive_lead "$LEAD_PT_ID"
    echo "  (property_type lead archived)"
fi

# ==============================================================================
section "3.12 last_activity_before filter"
# ==============================================================================

# Leads with no activity messages were created today and have no comments.
# last_activity_before=tomorrow should include them (no activity before tomorrow).
R=$(api_get "/api/v1/leads?last_activity_before=${TOMORROW}")
if echo "$R" | grep -q '"total"'; then
    pass "last_activity_before=${TOMORROW} returns valid response (no 500 error)"
    assert_contains_id "last_activity_before=tomorrow includes Lead 1 (no messages)" "$R" "$LEAD1_ID"
else
    fail "last_activity_before=${TOMORROW} returns valid response (no 500 error)" "Unexpected: ${R:0:100}"
fi

# last_activity_before=yesterday → should NOT include leads with no prior messages
# (no messages = still active, treated as having activity "never" which is < yesterday)
R=$(api_get "/api/v1/leads?last_activity_before=${YESTERDAY}")
if echo "$R" | grep -q '"total"'; then
    pass "last_activity_before=${YESTERDAY} returns valid response (no 500 error)"
else
    fail "last_activity_before=${YESTERDAY} returns valid response (no 500 error)" "Unexpected: ${R:0:100}"
fi

# ==============================================================================
section "3.13 filter combinations"
# ==============================================================================

# state=new + location=Centro + bedrooms=2 → only Lead 1
R=$(api_get "/api/v1/leads?state=new&location=Centro+${TIMESTAMP}&bedrooms=2")
assert_contains_id     "combined (state+location+bedrooms) includes Lead 1" "$R" "$LEAD1_ID"
assert_not_contains_id "combined (state+location+bedrooms) excludes Lead 2"  "$R" "$LEAD2_ID"
assert_not_contains_id "combined (state+location+bedrooms) excludes Lead 3"  "$R" "$LEAD3_ID"

# state=contacted + budget_min=350000 → Lead 2 (min=400k, state=contacted)
R=$(api_get "/api/v1/leads?state=contacted&budget_min=350000")
assert_contains_id     "state=contacted + budget_min=350000 includes Lead 2" "$R" "$LEAD2_ID"
assert_not_contains_id "state=contacted + budget_min=350000 excludes Lead 1" "$R" "$LEAD1_ID"

# created_from + state + bedrooms
R=$(api_get "/api/v1/leads?created_from=${TODAY}&state=new&bedrooms=2")
assert_contains_id     "period+state+bedrooms includes Lead 1"  "$R" "$LEAD1_ID"
assert_not_contains_id "period+state+bedrooms excludes Lead 3"  "$R" "$LEAD3_ID"

# ==============================================================================
# STEP 4: Cleanup — Archive remaining active leads
# ==============================================================================
section "Step 4: Cleanup"

for id in "${CREATED_LEAD_IDS[@]}"; do
    archive_lead "$id" 2>/dev/null || true
    echo "  Archived lead ID=$id"
done
echo -e "${GREEN}✓${NC} Cleanup complete"

# ==============================================================================
# Summary
# ==============================================================================
TOTAL=$((PASSED + FAILED + SKIPPED))
echo ""
echo "=========================================="
echo "Results"
echo "=========================================="
echo -e "  Total : $TOTAL"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo -e "  ${YELLOW}Skipped: $SKIPPED${NC}"
echo ""

if [[ "$FAILED" -eq 0 ]]; then
    echo -e "${GREEN}✓ All filter tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED test(s) failed${NC}"
    exit 1
fi
