#!/usr/bin/env bash
# Feature 010 E2E Tests - Test Runner with Auto Cleanup
# Executes Feature 010 tests with automatic cleanup before and after
#
# Usage:
#   ./run_feature010_tests.sh [test_numbers...]
#
# Examples:
#   ./run_feature010_tests.sh           # Run all tests
#   ./run_feature010_tests.sh 21 22     # Run only T21 and T22
#   ./run_feature010_tests.sh 26-28     # Run T26 through T28

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Make cleanup script executable
chmod +x "$SCRIPT_DIR/cleanup_test_data.sh"

# Test definitions (bash 3.2 compatible)
get_test_file() {
    local test_num=$1
    case $test_num in
        21) echo "test_us10_s1_create_profile.sh" ;;
        22) echo "test_us10_s2_list_profiles.sh" ;;
        23) echo "test_us10_s3_update_profile.sh" ;;
        24) echo "test_us10_s4_deactivate_profile.sh" ;;
        25) echo "test_us10_s5_feature009_integration.sh" ;;
        26) echo "test_us10_s6_rbac_matrix.sh" ;;
        27) echo "test_us10_s7_multitenancy.sh" ;;
        28) echo "test_us10_s8_compound_unique.sh" ;;
        *) echo "" ;;
    esac
}

get_test_name() {
    local test_num=$1
    case $test_num in
        21) echo "US10-S1: Create Profile" ;;
        22) echo "US10-S2: List/Get Profiles" ;;
        23) echo "US10-S3: Update Profile" ;;
        24) echo "US10-S4: Soft Delete" ;;
        25) echo "US10-S5: Feature 009 Integration" ;;
        26) echo "US10-S6: RBAC Matrix" ;;
        27) echo "US10-S7: Multi-tenancy" ;;
        28) echo "US10-S8: Compound Unique + Pagination" ;;
        *) echo "Unknown Test" ;;
    esac
}

# Determine which tests to run
TESTS_TO_RUN=()

if [ $# -eq 0 ]; then
    # Run all tests
    TESTS_TO_RUN=(21 22 23 24 25 26 27 28)
else
    # Parse arguments
    for arg in "$@"; do
        if [[ $arg =~ ^([0-9]+)-([0-9]+)$ ]]; then
            # Range: 26-28
            start=${BASH_REMATCH[1]}
            end=${BASH_REMATCH[2]}
            for i in $(seq $start $end); do
                test_file=$(get_test_file $i)
                if [[ -n "$test_file" ]]; then
                    TESTS_TO_RUN+=($i)
                fi
            done
        elif [[ $arg =~ ^[0-9]+$ ]]; then
            # Single test: 21
            test_file=$(get_test_file $arg)
            if [[ -n "$test_file" ]]; then
                TESTS_TO_RUN+=($arg)
            fi
        else
            echo -e "${RED}Invalid test number: $arg${NC}"
            exit 1
        fi
    done
fi

if [ ${#TESTS_TO_RUN[@]} -eq 0 ]; then
    echo -e "${RED}No valid tests specified${NC}"
    exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Feature 010 E2E Test Suite${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${BLUE}Tests to run: ${TESTS_TO_RUN[*]}${NC}"
echo ""

# Initial cleanup
echo -e "${YELLOW}Running pre-test cleanup...${NC}"
"$SCRIPT_DIR/cleanup_test_data.sh" --all
echo ""

# Track results (simple arrays for bash 3.2 compatibility)
RESULT_TESTS=()
RESULT_STATUS=()
PASSED=0
FAILED=0
SKIPPED=0

# Function to store result
store_result() {
    local test_num=$1
    local status=$2
    RESULT_TESTS+=($test_num)
    RESULT_STATUS+=("$status")
}

# Function to get result
get_result() {
    local test_num=$1
    local i=0
    for t in "${RESULT_TESTS[@]}"; do
        if [ "$t" -eq "$test_num" ]; then
            echo "${RESULT_STATUS[$i]}"
            return
        fi
        i=$((i + 1))
    done
    echo "UNKNOWN"
}

# Run tests
for test_num in "${TESTS_TO_RUN[@]}"; do
    test_file=$(get_test_file $test_num)
    test_name=$(get_test_name $test_num)
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Running T${test_num}: $test_name${NC}"
    echo -e "${CYAN}========================================${NC}"
    
    # Run test and capture output
    test_output=$(bash "$SCRIPT_DIR/$test_file" 2>&1)
    test_exit=$?
    
    echo "$test_output"
    echo ""
    
    # Analyze result
    if [ $test_exit -eq 0 ]; then
        if echo "$test_output" | grep -q "PARTIAL PASS"; then
            store_result $test_num "SKIPPED"
            SKIPPED=$((SKIPPED + 1))
            echo -e "${YELLOW}⊘ T${test_num} PARTIAL/SKIPPED${NC}"
        else
            store_result $test_num "PASS"
            PASSED=$((PASSED + 1))
            echo -e "${GREEN}✓ T${test_num} PASSED${NC}"
        fi
    else
        store_result $test_num "FAIL"
        FAILED=$((FAILED + 1))
        echo -e "${RED}✗ T${test_num} FAILED${NC}"
    fi
    
    echo ""
    
    # Cleanup between tests
    echo -e "${YELLOW}Cleaning up test data...${NC}"
    "$SCRIPT_DIR/cleanup_test_data.sh" --all > /dev/null 2>&1 || true
    echo ""
done

# Final cleanup
echo -e "${YELLOW}Running post-test cleanup...${NC}"
"$SCRIPT_DIR/cleanup_test_data.sh" --all
echo ""

# Summary
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test Results Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

TOTAL=${#TESTS_TO_RUN[@]}
echo -e "${BLUE}Tests Run: $TOTAL${NC}"
echo -e "${GREEN}Passed:    $PASSED${NC}"
echo -e "${RED}Failed:    $FAILED${NC}"
echo -e "${YELLOW}Skipped:   $SKIPPED${NC}"
echo ""

echo -e "${BLUE}Detailed Results:${NC}"
for test_num in "${TESTS_TO_RUN[@]}"; do
    result=$(get_result $test_num)
    test_name=$(get_test_name $test_num)
    
    case $result in
        PASS)
            echo -e "  ${GREEN}✓ T${test_num}: $test_name${NC}"
            ;;
        FAIL)
            echo -e "  ${RED}✗ T${test_num}: $test_name${NC}"
            ;;
        SKIPPED)
            echo -e "  ${YELLOW}⊘ T${test_num}: $test_name${NC}"
            ;;
    esac
done

echo ""
echo -e "${CYAN}========================================${NC}"

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Some tests failed${NC}"
    exit 1
elif [ $SKIPPED -gt 0 ] && [ $PASSED -eq 0 ]; then
    echo -e "${YELLOW}All tests were skipped${NC}"
    exit 2
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
