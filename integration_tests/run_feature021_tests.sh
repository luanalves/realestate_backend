#!/usr/bin/env bash
# integration_tests/run_feature021_tests.sh
# Feature 021 — CMS Domain: run all integration tests in order

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0

run_test() {
    local name="$1" file="$2"
    echo ""; echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW} Running: $name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if bash "$SCRIPT_DIR/$file"; then
        echo -e "${GREEN}✓ PASSED: $name${NC}"; PASS=$((PASS + 1))
    else
        echo -e "${RED}✗ FAILED: $name${NC}"; FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo "Feature 021 — CMS Domain Tests"
echo "========================================"

run_test "US021-01: Page CRUD + State Machine"  "test_us021_cms_page_crud.sh"
run_test "US021-02: Media Library"              "test_us021_cms_media.sh"
run_test "US021-03: Public Route"               "test_us021_cms_public.sh"
run_test "US021-04: Templates"                  "test_us021_cms_templates.sh"
run_test "US021-05: Settings"                   "test_us021_cms_settings.sh"
run_test "US021-06: RBAC Matrix"                "test_us021_rbac_matrix.sh"
run_test "US021-07: Multitenancy"               "test_us021_multitenancy.sh"

echo ""; echo "========================================"
echo "Feature 021 Results: ${PASS} passed, ${FAIL} failed"
echo "========================================"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
