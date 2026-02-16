#!/usr/bin/env bash
# Run US7 integration tests
# Only runs tests that are 100% ready (S1, S2, S3)

set -e

cd /opt/homebrew/var/www/realestate/realestate_backend

echo "=========================================="
echo "Running US7 Integration Tests"
echo "=========================================="
echo ""

# Test S1
echo "========== TEST S1: Owner CRUD =========="
bash integration_tests/test_us7_s1_owner_crud.sh
echo ""
echo ""

# Test S2
echo "========== TEST S2: Owner-Company Linking =========="
bash integration_tests/test_us7_s2_owner_company_link.sh
echo ""
echo ""

# Test S3
echo "========== TEST S3: Company CRUD =========="
bash integration_tests/test_us7_s3_company_crud.sh
echo ""
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="
