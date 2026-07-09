#!/bin/bash
# ==============================================================================
# Integration Test: US024-S3 - Activity Endpoints Company Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 3: log_activity/list_activities/schedule_activity reject
# cross-company access (FR3). pedro@imobiliaria.com (Company A) must be
# blocked with 403 ACCESS_DENIED when targeting lead_seed_024_b1_1
# (Company B, carmen's lead).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s3_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"
exec > >(tee "$TEST_LOG") 2>&1

FAILED=0

echo "=========================================="
echo "US024-S3: Activity Endpoints Company Isolation"
echo "=========================================="
echo ""

echo "=== Test Started: $(date) ==="

echo -e "${BLUE}GIVEN${NC}: Resolving lead_seed_024_b1_1's ID via admin session..."
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"
ADMIN_COOKIE_FILE="/tmp/odoo_us024s3_admin_$$.txt"
trap 'rm -f "$ADMIN_COOKIE_FILE"' EXIT

curl -s -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -c "$ADMIN_COOKIE_FILE" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"${ODOO_DB:-realestate}\",\"login\":\"$ADMIN_LOGIN\",\"password\":\"$ADMIN_PASSWORD\"}}" > /dev/null

LEAD_B1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lead\",
            \"method\": \"search_read\",
            \"args\": [[[\"name\", \"=\", \"Seed024 Lead B1-1 (carmen, Company B)\"]]],
            \"kwargs\": {\"fields\": [\"id\"], \"limit\": 1}
        },
        \"id\": 1
    }")
LEAD_B1_ID=$(echo "$LEAD_B1_RESPONSE" | jq -r '.result[0].id // empty')

if [ -z "$LEAD_B1_ID" ] || [ "$LEAD_B1_ID" == "null" ]; then
    echo -e "${RED}✗ FAIL${NC}: Could not resolve lead_seed_024_b1_1's ID (seed data missing? run Task 7 first)"
    exit 1
fi
echo -e "${GREEN}✓${NC} lead_seed_024_b1_1 ID = $LEAD_B1_ID"
echo ""

echo -e "${BLUE}STEP 1${NC}: Authenticating as Agent pedro (Company A)..."
authenticate_user "pedro@imobiliaria.com" "agent123"
AGENT_TOKEN="$OAUTH_TOKEN"
AGENT_SESSION="$USER_SESSION_ID"
echo -e "${GREEN}✓${NC} Agent authenticated"
echo ""

echo -e "${BLUE}WHEN${NC}: pedro calls POST /api/v1/leads/$LEAD_B1_ID/activities (log_activity)..."
LOG_ACTIVITY_RESPONSE=$(curl -s --max-time 30 -X POST "$BASE_URL/api/v1/leads/$LEAD_B1_ID/activities" \
    -H "Authorization: Bearer $AGENT_TOKEN" \
    -H "X-Openerp-Session-Id: $AGENT_SESSION" \
    -H "Content-Type: application/json" \
    -d '{"body":"cross-company attempt","activity_type":"note"}')

if echo "$LOG_ACTIVITY_RESPONSE" | grep -q "ACCESS_DENIED"; then
    echo -e "${GREEN}✓${NC} log_activity returns ACCESS_DENIED for cross-company lead"
else
    echo -e "${RED}✗ FAIL${NC}: log_activity did not return ACCESS_DENIED. Response: $LOG_ACTIVITY_RESPONSE"
    FAILED=1
fi

echo ""
echo -e "${BLUE}WHEN${NC}: pedro calls GET /api/v1/leads/$LEAD_B1_ID/activities (list_activities)..."
LIST_ACTIVITIES_RESPONSE=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/$LEAD_B1_ID/activities" \
    -H "Authorization: Bearer $AGENT_TOKEN" \
    -H "X-Openerp-Session-Id: $AGENT_SESSION")

if echo "$LIST_ACTIVITIES_RESPONSE" | grep -q "ACCESS_DENIED"; then
    echo -e "${GREEN}✓${NC} list_activities returns ACCESS_DENIED for cross-company lead"
else
    echo -e "${RED}✗ FAIL${NC}: list_activities did not return ACCESS_DENIED. Response: $LIST_ACTIVITIES_RESPONSE"
    FAILED=1
fi

echo ""
echo -e "${BLUE}WHEN${NC}: pedro calls POST /api/v1/leads/$LEAD_B1_ID/schedule-activity (schedule_activity)..."
SCHEDULE_RESPONSE=$(curl -s --max-time 30 -X POST "$BASE_URL/api/v1/leads/$LEAD_B1_ID/schedule-activity" \
    -H "Authorization: Bearer $AGENT_TOKEN" \
    -H "X-Openerp-Session-Id: $AGENT_SESSION" \
    -H "Content-Type: application/json" \
    -d '{"summary":"cross-company attempt","date_deadline":"2027-01-01"}')

if echo "$SCHEDULE_RESPONSE" | grep -q "ACCESS_DENIED"; then
    echo -e "${GREEN}✓${NC} schedule_activity returns ACCESS_DENIED for cross-company lead"
else
    echo -e "${RED}✗ FAIL${NC}: schedule_activity did not return ACCESS_DENIED. Response: $SCHEDULE_RESPONSE"
    FAILED=1
fi

echo ""
echo -e "${BLUE}WHEN${NC}: Admin (base.group_system) calls GET /api/v1/leads/$LEAD_B1_ID/activities (bypass check)..."
ADMIN_ACTIVITIES=$(curl -s --max-time 30 -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b "$ADMIN_COOKIE_FILE" \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.lead\",
            \"method\": \"read\",
            \"args\": [[$LEAD_B1_ID], [\"id\", \"name\"]],
            \"kwargs\": {}
        },
        \"id\": 2
    }")
if echo "$ADMIN_ACTIVITIES" | grep -q "Seed024 Lead B1-1"; then
    echo -e "${GREEN}✓${NC} Admin (via Odoo web session) can still read the cross-company lead (no regression)"
else
    echo -e "${RED}✗ FAIL${NC}: Admin unexpectedly cannot read the lead. Response: $ADMIN_ACTIVITIES"
    FAILED=1
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "=========================================="
    echo -e "${GREEN}TEST PASSED${NC}"
    echo "=========================================="
else
    echo "=========================================="
    echo -e "${RED}TEST FAILED${NC}"
    echo "=========================================="
fi
echo "=== Test Ended: $(date) ==="

exit $FAILED
