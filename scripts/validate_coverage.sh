#!/bin/bash
# ==============================================================================
# Test Coverage Validation Script
# ==============================================================================
# Purpose: Run the test suite following the flow mandated by ADR-003
#          (docs/adr/ADR-003-mandatory-test-coverage.md)
# Constitution: Principle II - Test Coverage Mandatory (NON-NEGOTIABLE)
#
# ADR-003 execution order:
#   1. Unit tests   - unittest + mock, NO database, run via each module's own
#                      tests/run_unit_tests.py (or tests/unit/run_unit_tests.py)
#                      inside the odoo container.
#   2. E2E API      - curl scripts in integration_tests/, against a live Odoo.
#   3. E2E UI       - Cypress (optional, opt-in via --cypress).
#
# NOTE: pytest is intentionally NOT used. Odoo's HttpCase runs requests in
# read-only transactions (breaks anything that persists data), and unit tests
# are plain unittest.TestCase so they don't require an Odoo/DB bootstrap.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTRA_ADDONS="$PROJECT_ROOT/18.0/extra-addons"
COMPOSE="docker compose -f $PROJECT_ROOT/18.0/docker-compose.yml"
DB_NAME="${DB_NAME:-realestate}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Test Validation (ADR-003 flow)"
echo "=============================================="
echo ""

# ==============================================================================
# Phase 1: Unit Tests (unittest + mock, no DB) - run inside the odoo container
# ==============================================================================
echo -e "${BLUE}Phase 1: Unit Tests${NC}"
echo "--------------------------------------------"

UNIT_MODULES_PASSED=0
UNIT_MODULES_FAILED=0
UNIT_MODULES_SKIPPED=0

for module_dir in "$EXTRA_ADDONS"/*/; do
    module=$(basename "$module_dir")
    tests_dir="$module_dir/tests"
    [ -d "$tests_dir" ] || continue

    runner=""
    if [ -f "$tests_dir/run_unit_tests.py" ]; then
        runner="/mnt/extra-addons/$module/tests/run_unit_tests.py"
    elif [ -f "$tests_dir/unit/run_unit_tests.py" ]; then
        runner="/mnt/extra-addons/$module/tests/unit/run_unit_tests.py"
    fi

    if [ -n "$runner" ]; then
        echo -n "  $module (run_unit_tests.py)... "
        if $COMPOSE exec -T odoo python3 "$runner" > /tmp/unit_${module}.log 2>&1; then
            echo -e "${GREEN}PASS${NC}"
            ((UNIT_MODULES_PASSED++))
        else
            echo -e "${RED}FAIL${NC} (see /tmp/unit_${module}.log)"
            ((UNIT_MODULES_FAILED++))
        fi

        # run_unit_tests.py deliberately only covers pure unittest.TestCase
        # files (no DB). Any TransactionCase-based tests wired into this
        # module's own tests/__init__.py (e.g. tests/integration/) still need
        # Odoo's native runner, or they'd never execute anywhere.
        if [ -d "$tests_dir/integration" ]; then
            echo -n "  $module (tests/integration -> odoo test-enable)... "
            if $COMPOSE exec -T odoo odoo -d "$DB_NAME" -u "$module" \
                --test-enable --stop-after-init --log-level=test \
                --http-port=8988 \
                > /tmp/integration_${module}.log 2>&1; then
                echo -e "${GREEN}PASS${NC}"
                ((UNIT_MODULES_PASSED++))
            else
                echo -e "${RED}FAIL${NC} (see /tmp/integration_${module}.log)"
                ((UNIT_MODULES_FAILED++))
            fi
        fi
        continue
    fi

    # No dedicated runner: pick a test root (tests/unit/ if present, else
    # tests/ itself) and route by what the files actually subclass - not by
    # directory name. A file under tests/unit/ can still be a TransactionCase
    # (needs Odoo's own test loader), and a file directly under tests/ can be
    # a plain unittest.TestCase (needs no DB at all).
    if [ -d "$tests_dir/unit" ]; then
        test_root="$tests_dir/unit"
        tests_subdir="tests/unit"
    elif find "$tests_dir" -maxdepth 1 -name "test_*.py" | grep -q .; then
        test_root="$tests_dir"
        tests_subdir="tests"
    else
        ((UNIT_MODULES_SKIPPED++))
        continue
    fi

    # Scan every .py under test_root (not just test_*.py) - a test class can
    # inherit TransactionCase indirectly through a shared base in common.py.
    if grep -rl "TransactionCase" "$test_root" --include="*.py" > /dev/null 2>&1; then
        echo -n "  $module (TransactionCase -> odoo test-enable)... "
        if $COMPOSE exec -T odoo odoo -d "$DB_NAME" -u "$module" \
            --test-enable --stop-after-init --log-level=test \
            --http-port=8988 \
            > /tmp/unit_${module}.log 2>&1; then
            if grep -q "0 tests" /tmp/unit_${module}.log; then
                echo -e "${YELLOW}WARN${NC} - ran but discovered 0 tests (check tests/__init__.py imports)"
                ((UNIT_MODULES_FAILED++))
            else
                echo -e "${GREEN}PASS${NC}"
                ((UNIT_MODULES_PASSED++))
            fi
        else
            echo -e "${RED}FAIL${NC} (see /tmp/unit_${module}.log)"
            ((UNIT_MODULES_FAILED++))
        fi
    else
        echo -n "  $module (unittest discover)... "
        if $COMPOSE exec -T odoo python3 /mnt/extra-addons/_test_tools/run_generic_unit_tests.py \
            "$module" "$tests_subdir" \
            > /tmp/unit_${module}.log 2>&1; then
            echo -e "${GREEN}PASS${NC}"
            ((UNIT_MODULES_PASSED++))
        else
            echo -e "${RED}FAIL${NC} (see /tmp/unit_${module}.log)"
            ((UNIT_MODULES_FAILED++))
        fi
    fi
done

echo ""
echo "Unit Test Modules: $UNIT_MODULES_PASSED passed, $UNIT_MODULES_FAILED failed, $UNIT_MODULES_SKIPPED skipped (no tests/unit)"
echo ""

# ==============================================================================
# Phase 2: E2E API Tests (curl, against a live Odoo instance)
# ==============================================================================
echo -e "${BLUE}Phase 2: E2E API Tests (curl)${NC}"
echo "--------------------------------------------"

INTEGRATION_DIR="$PROJECT_ROOT/integration_tests"
E2E_PASSED=0
E2E_FAILED=0

if [ -d "$INTEGRATION_DIR" ]; then
    for test_file in "$INTEGRATION_DIR"/test_*.sh; do
        [ -f "$test_file" ] || continue
        test_name=$(basename "$test_file")
        echo -n "  $test_name... "
        if bash "$test_file" > "/tmp/e2e_${test_name}.log" 2>&1; then
            echo -e "${GREEN}PASS${NC}"
            ((E2E_PASSED++))
        else
            echo -e "${RED}FAIL${NC} (see /tmp/e2e_${test_name}.log)"
            ((E2E_FAILED++))
        fi
    done
    echo ""
    echo "E2E API Results: $E2E_PASSED passed, $E2E_FAILED failed"
else
    echo -e "${YELLOW}⚠ integration_tests/ not found${NC}"
fi
echo ""

# ==============================================================================
# Phase 3: E2E UI Tests (Cypress) - optional, opt-in
# ==============================================================================
CYPRESS_PASSED=0
CYPRESS_FAILED=0
if [ "$1" == "--cypress" ]; then
    echo -e "${BLUE}Phase 3: E2E UI Tests (Cypress)${NC}"
    echo "--------------------------------------------"
    if npx cypress run --spec "$PROJECT_ROOT/cypress/e2e/*.cy.js" > /tmp/cypress.log 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        CYPRESS_PASSED=1
    else
        echo -e "${RED}FAIL${NC} (see /tmp/cypress.log)"
        CYPRESS_FAILED=1
    fi
    echo ""
else
    echo -e "${YELLOW}Phase 3: E2E UI Tests (Cypress) skipped — pass --cypress to run${NC}"
    echo ""
fi

# ==============================================================================
# Summary
# ==============================================================================
echo "=============================================="
echo "Summary"
echo "=============================================="
TOTAL_FAILED=$((UNIT_MODULES_FAILED + E2E_FAILED + CYPRESS_FAILED))

echo "  Unit test modules : $UNIT_MODULES_PASSED passed, $UNIT_MODULES_FAILED failed, $UNIT_MODULES_SKIPPED skipped"
echo "  E2E API tests      : $E2E_PASSED passed, $E2E_FAILED failed"
if [ "$1" == "--cypress" ]; then
    echo "  E2E UI (Cypress)   : $([ $CYPRESS_FAILED -eq 0 ] && echo PASS || echo FAIL)"
fi
echo ""

if [ "$TOTAL_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ $TOTAL_FAILED failure(s) - see logs above${NC}"
fi

exit $TOTAL_FAILED
