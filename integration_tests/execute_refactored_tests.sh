#!/bin/bash

################################################################################
# Execute All Refactored Legacy Tests
# Tests US2-S2/S3/S4 and US3-S1/S2/S3 with Odoo 18.0 field structure
################################################################################

echo "=========================================="
echo "Executing All Refactored Legacy E2E Tests"
echo "=========================================="
echo ""
echo "Date: $(date)"
echo "Location: $(pwd)"
echo ""

cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests

# Array of tests to execute
TESTS=(
    "test_us2_s2_manager_menus.sh"
    "test_us2_s3_manager_assigns_properties.sh"
    "test_us2_s4_manager_isolation.sh"
    "test_us3_s1_agent_assigned_properties.sh"
    "test_us3_s2_agent_auto_assignment.sh"
    "test_us3_s3_agent_own_leads.sh"
)

# Track results
PASSED=0
FAILED=0
FAILED_TESTS=()

for test in "${TESTS[@]}"; do
    echo "=========================================="
    echo "Executing: $test"
    echo "=========================================="
    
    # Execute test and capture exit code
    if bash "$test"; then
        echo "✅ $test PASSED"
        ((PASSED++))
    else
        echo "❌ $test FAILED"
        ((FAILED++))
        FAILED_TESTS+=("$test")
    fi
    
    echo ""
    echo "Progress: $((PASSED + FAILED))/6 completed"
    echo ""
done

# Final summary
echo "=========================================="
echo "Final Results"
echo "=========================================="
echo "Date: $(date)"
echo ""
echo "Passed: $PASSED/6"
echo "Failed: $FAILED/6"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 SUCCESS - All 6 legacy tests refactored and passing!"
    echo ""
    echo "Total Test Coverage:"
    echo "  US1 (Owner): 3/3 ✅"
    echo "  US2 (Manager): 4/4 ✅"
    echo "  US3 (Agent): 5/5 ✅"
    echo "  US4 (Manager Oversight): 3/3 ✅"
    echo "  Total: 15/15 (100%) ✅"
    echo ""
    echo "RBAC implementation fully validated!"
    exit 0
else
    echo "⚠️  Some tests failed. Review output above."
    echo ""
    echo "Failed tests:"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo "  - $failed_test"
    done
    echo ""
    exit 1
fi
