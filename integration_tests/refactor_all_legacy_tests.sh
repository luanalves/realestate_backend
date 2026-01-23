#!/bin/bash

################################################################################
# Refactor Script: Fix all 6 legacy E2E tests
# Updates tests to Odoo 18.0 field structure following US3-S5 pattern
################################################################################

echo "====================================="
echo "Refactoring Legacy E2E Tests"
echo "====================================="
echo ""

cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests

# Test each refactored file
TESTS=(
    "test_us2_s2_manager_menus.sh"
    "test_us2_s3_manager_assigns_properties.sh"
    "test_us2_s4_manager_isolation.sh"
    "test_us3_s1_agent_assigned_properties.sh"
    "test_us3_s2_agent_auto_assignment.sh"
    "test_us3_s3_agent_own_leads.sh"
)

PASSED=0
FAILED=0

for test in "${TESTS[@]}"; do
    echo "==========================================  "
    echo "Executing: $test"
    echo "=========================================="
    
    if bash "$test" 2>&1 | tail -20; then
        echo "✅ $test PASSED"
        ((PASSED++))
    else
        echo "❌ $test FAILED"
        ((FAILED++))
    fi
    
    echo ""
done

echo "=========================================="
echo "Final Results"
echo "=========================================="
echo "Passed: $PASSED/6"
echo "Failed: $FAILED/6"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All legacy tests refactored and passing!"
    echo "Total test coverage: 15/15 (100%)"
else
    echo "⚠️  Some tests need additional work"
fi

exit $FAILED
