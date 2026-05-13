#!/usr/bin/env bash
# Feature 019 - US019-S4: Report Date Range (Accumulated Period) - T035
#
# Success Criteria:
# - GET report?date_from=2026-01-01&date_to=2026-03-31 → 200
# - period.mode = "accumulated"
# - period.date_from / period.date_to present
# - year/month absent from period

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ $1${NC}"; ((PASS++)); }
fail() { echo -e "${RED}✗ $1${NC}"; ((FAIL++)); }

echo "========================================"
echo "US019-S4: Report — Accumulated Date Range"
echo "========================================"

echo ""
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "$BEARER_TOKEN" ]; then echo -e "${RED}✗ OAuth2 failed${NC}"; exit 1; fi
pass "Bearer token obtained"

MANAGER_EMAIL="${TEST_MANAGER_EMAIL:-manager_019@example.com}"
MANAGER_PASS="${TEST_MANAGER_PASS:-ManagerPass019!}"

MGR_RESP=$(curl -s -X POST "$API_BASE/users/login" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -d "{\"login\": \"$MANAGER_EMAIL\", \"password\": \"$MANAGER_PASS\"}")

MGR_SID=$(echo "$MGR_RESP" | jq -r '.session_id // empty')
MGR_CID=$(echo "$MGR_RESP" | jq -r '.user.default_company_id // empty')

if [ -z "$MGR_SID" ]; then echo -e "${RED}✗ Manager login failed${NC}"; exit 1; fi
pass "Manager logged in"

report_call() {
    local qs="$1"
    curl -s -o /tmp/019_daterange_resp.json -w "%{http_code}" \
        -X GET "$API_BASE/goals/report?$qs" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Odoo-Session-Id: $MGR_SID" \
        -H "X-Company-Id: $MGR_CID"
}

# ── T1: 3-month accumulated report → 200 ─────────────────────────────────────
echo ""
echo "Step 1: GET report?date_from=2026-01-01&date_to=2026-03-31 → expect 200..."
HTTP=$(report_call "date_from=2026-01-01&date_to=2026-03-31")
if [ "$HTTP" = "200" ]; then
    MODE=$(jq -r '.period.mode' /tmp/019_daterange_resp.json)
    DATE_FROM=$(jq -r '.period.date_from' /tmp/019_daterange_resp.json)
    DATE_TO=$(jq -r '.period.date_to' /tmp/019_daterange_resp.json)
    if [ "$MODE" = "accumulated" ]; then
        pass "Accumulated report → 200 (mode=$MODE, from=$DATE_FROM, to=$DATE_TO)"
    else
        fail "period.mode expected 'accumulated', got '$MODE'"
    fi
    # Validate date_from and date_to present in period
    if [ "$DATE_FROM" = "2026-01-01" ] && [ "$DATE_TO" = "2026-03-31" ]; then
        pass "period.date_from=2026-01-01 and period.date_to=2026-03-31 ✓"
    else
        fail "period dates wrong: from=$DATE_FROM to=$DATE_TO"
    fi
    # Validate year/month absent in accumulated mode
    HAS_YEAR=$(jq 'has("year")' /tmp/019_daterange_resp.json 2>/dev/null || echo false)
    PERIOD_HAS_YEAR=$(jq '.period | has("year")' /tmp/019_daterange_resp.json 2>/dev/null || echo false)
    if [ "$PERIOD_HAS_YEAR" = "false" ] || [ "$(jq -r '.period.year' /tmp/019_daterange_resp.json)" = "null" ]; then
        pass "period.year absent in accumulated mode ✓"
    else
        fail "period.year should be absent in accumulated mode"
    fi
else
    fail "Accumulated report → expected 200, got $HTTP"
    cat /tmp/019_daterange_resp.json
fi

# ── T2: Exactly 366 days → 200 (boundary) ─────────────────────────────────
echo ""
echo "Step 2: Exactly 366 days (2025-01-01 to 2026-01-01) → expect 200..."
HTTP=$(report_call "date_from=2025-01-01&date_to=2026-01-01")
if [ "$HTTP" = "200" ]; then
    pass "366-day range → 200 (boundary valid) ✓"
else
    fail "366-day range → expected 200, got $HTTP"
fi

# ── T3: 367 days → 400 (SEC-6) ────────────────────────────────────────────
echo ""
echo "Step 3: 367 days → expect 400 (SEC-6)..."
HTTP=$(report_call "date_from=2025-01-01&date_to=2026-01-03")
if [ "$HTTP" = "400" ]; then
    ERROR=$(jq -r '.error' /tmp/019_daterange_resp.json)
    pass "367-day range → 400 (error=$ERROR) ✓"
else
    fail "367-day range → expected 400, got $HTTP"
fi

# ── T4: date_to < date_from → 400 ─────────────────────────────────────────
echo ""
echo "Step 4: date_to < date_from → expect 400..."
HTTP=$(report_call "date_from=2026-03-01&date_to=2026-01-01")
if [ "$HTTP" = "400" ]; then
    pass "Reversed date range → 400 ✓"
else
    fail "Reversed date range → expected 400, got $HTTP"
fi

# ── T5: Invalid date format → 400 ─────────────────────────────────────────
echo ""
echo "Step 5: Invalid date format → expect 400..."
HTTP=$(report_call "date_from=01-01-2026&date_to=03-31-2026")
if [ "$HTTP" = "400" ]; then
    pass "Invalid date format → 400 ✓"
else
    fail "Invalid date format → expected 400, got $HTTP"
fi

echo ""
echo "========================================"
echo "US019-S4 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then exit 1; fi
