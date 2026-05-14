#!/usr/bin/env bash
# Feature 019 — Run all integration tests in order (T041)
#
# Usage: bash integration_tests/run_feature019_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

run_test() {
    local name="$1" file="$2"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW} Running: $name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if bash "$SCRIPT_DIR/$file"; then
        echo -e "${GREEN}✓ PASSED: $name${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗ FAILED: $name${NC}"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo "Feature 019 — Goals & Results Tests"
echo "========================================"

# ── Pre-cleanup: remove test-created goals (keep seed month=5 data only) ──
echo ""
echo "Pre-cleanup: removing non-seed test goals (month != 5)..."
cd "$(dirname "$SCRIPT_DIR")/18.0" 2>/dev/null || true
docker compose exec -T db psql -U odoo -d realestate \
    -c "DELETE FROM thedevkitchen_estate_goal g USING res_users u WHERE g.user_id=u.id AND u.login LIKE '%019%' AND g.month != 5" \
    2>/dev/null | grep -v '^$' || echo "  (no cleanup needed or docker unavailable)"
cd - > /dev/null 2>&1 || true

run_test "US019-S1: Create Goals (RBAC)"   "test_us019_s1_create_goals.sh"
run_test "US019-S2: Goal Lifecycle"         "test_us019_s2_goal_lifecycle.sh"
run_test "US019-S3: Report Single Month"    "test_us019_s3_report_single_month.sh"
run_test "US019-S4: Report Date Range"      "test_us019_s4_report_date_range.sh"
run_test "US019-S5: RBAC Matrix"            "test_us019_s5_rbac_matrix.sh"
run_test "US019-S6: Multitenancy"           "test_us019_s6_multitenancy.sh"

echo ""
echo "========================================"
echo "Feature 019 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
