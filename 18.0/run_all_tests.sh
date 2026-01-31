#!/bin/bash
# Comprehensive Test Execution Script
# Phase 5 & 6 Tests for Lead Management
# Date: 2026-01-30

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/test_logs"
mkdir -p "${LOG_DIR}"

echo "========================================"
echo "Lead Management Test Suite"
echo "========================================"
echo "Start Time: $(date)"
echo ""

# Load environment variables
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(cat "${SCRIPT_DIR}/.env" | grep -v '^#' | xargs)
fi

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run test and capture result
run_test() {
    local test_name="$1"
    local test_command="$2"
    local log_file="${LOG_DIR}/${test_name}.log"
    
    echo "→ Running: ${test_name}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "${test_command}" > "${log_file}" 2>&1; then
        echo "  ✓ PASS: ${test_name}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo "  ✗ FAIL: ${test_name}"
        echo "  Log: ${log_file}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# ===========================================
# Phase 5: Activity Tracking Tests
# ===========================================

echo ""
echo "=== Phase 5: Activity Tracking ==="
echo ""

# E2E API Test
cd "${SCRIPT_DIR}/extra-addons/quicksol_estate/tests/api"
run_test "phase5_e2e_activities" "bash test_lead_activities_api.sh"

# Unit Tests (via Odoo test runner)
cd "${SCRIPT_DIR}"
run_test "phase5_unit_activity_tracking" \
    "docker compose exec -T odoo odoo -d realestate --test-enable --test-tags quicksol_estate.test_activity_tracking --stop-after-init --log-level=test"

# ===========================================
# Phase 6: Advanced Search & Filters Tests
# ===========================================

echo ""
echo "=== Phase 6: Advanced Search & Filters ==="
echo ""

# E2E API Test
cd "${SCRIPT_DIR}/extra-addons/quicksol_estate/tests/api"
run_test "phase6_e2e_search_filters" "bash test_lead_search_filters_api.sh"

# Unit Tests
cd "${SCRIPT_DIR}"
run_test "phase6_unit_advanced_search" \
    "docker compose exec -T odoo odoo -d realestate --test-enable --test-tags quicksol_estate.test_advanced_search --stop-after-init --log-level=test"

run_test "phase6_unit_saved_filters" \
    "docker compose exec -T odoo odoo -d realestate --test-enable --test-tags quicksol_estate.test_saved_filters --stop-after-init --log-level=test"

# ===========================================
# Summary
# ===========================================

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo "Total Tests:  ${TOTAL_TESTS}"
echo "Passed:       ${PASSED_TESTS}"
echo "Failed:       ${FAILED_TESTS}"
echo "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
echo ""
echo "End Time: $(date)"
echo "========================================"

# Exit with error if any tests failed
if [ ${FAILED_TESTS} -gt 0 ]; then
    echo ""
    echo "⚠️  Some tests failed. Check logs in ${LOG_DIR}/"
    exit 1
else
    echo ""
    echo "✅ All tests passed!"
    exit 0
fi
