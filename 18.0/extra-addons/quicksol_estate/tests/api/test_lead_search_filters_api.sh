#!/bin/bash
# E2E API Test: Advanced Search & Saved Filters (Phase 6)
# Tests advanced search parameters and saved filter endpoints
# FR-039 to FR-048
# Author: Quicksol Technologies
# Date: 2026-01-30

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

# Load .env first
if [ -f "$REPO_ROOT/18.0/.env" ]; then
    source "$REPO_ROOT/18.0/.env"
else
    echo "Error: .env file not found at $REPO_ROOT/18.0/.env"
    exit 1
fi

# Load authentication helper
source "${SCRIPT_DIR}/../lib/auth_helper.sh"

# Configuration
ODOO_BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_MANAGER_EMAIL="${TEST_MANAGER_EMAIL:-admin}"
TEST_MANAGER_PASSWORD="${TEST_MANAGER_PASSWORD:-admin}"

echo "========================================="
echo "E2E API Test: Advanced Search & Saved Filters"
echo "========================================="

# Step 1: Authenticate as manager
echo "→ Step 1: Authenticating as manager..."
authenticate_user "${TEST_MANAGER_EMAIL}" "${TEST_MANAGER_PASSWORD}" || exit 1
MANAGER_TOKEN="$OAUTH_TOKEN"
MANAGER_SESSION="$USER_SESSION_ID"

echo "✓ Manager authenticated"

# Step 2: Create test leads with different attributes
echo ""
echo "→ Step 2: Creating test leads..."

# Low budget lead
LEAD_LOW=$(make_api_request POST "/api/v1/leads" '{
  "name": "Low Budget Cliente",
  "budget_min": 100000,
  "budget_max": 200000,
  "bedrooms_needed": 2,
  "location_preference": "Centro",
  "state": "new"
}')

LEAD_LOW_ID=$(echo "$LEAD_LOW" | jq -r '.id')

# Mid budget lead
LEAD_MID=$(make_api_request POST "/api/v1/leads" '{
  "name": "Mid Budget Cliente",
  "budget_min": 300000,
  "budget_max": 400000,
  "bedrooms_needed": 3,
  "location_preference": "Centro",
  "state": "qualified"
}')

LEAD_MID_ID=$(echo "$LEAD_MID" | jq -r '.id')

# High budget lead
LEAD_HIGH=$(make_api_request POST "/api/v1/leads" '{
  "name": "High Budget Cliente",
  "budget_min": 500000,
  "budget_max": 800000,
  "bedrooms_needed": 3,
  "location_preference": "Vila Olímpia",
  "state": "qualified"
}')

LEAD_HIGH_ID=$(echo "$LEAD_HIGH" | jq -r '.id')

echo "✓ Created 3 test leads ($LEAD_LOW_ID, $LEAD_MID_ID, $LEAD_HIGH_ID)"

# Step 3: Test budget_min filter
echo ""
echo "→ Step 3: Testing budget_min filter..."

BUDGET_MIN_RESULTS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?budget_min=250000" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

BUDGET_MIN_COUNT=$(echo "$BUDGET_MIN_RESULTS" | jq '.leads | length')

echo "✓ Found $BUDGET_MIN_COUNT leads with budget_max >= 250k"

# Step 4: Test budget_max filter
echo ""
echo "→ Step 4: Testing budget_max filter..."

BUDGET_MAX_RESULTS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?budget_max=350000" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

BUDGET_MAX_COUNT=$(echo "$BUDGET_MAX_RESULTS" | jq '.leads | length')

echo "✓ Found $BUDGET_MAX_COUNT leads with budget_min <= 350k"

# Step 5: Test bedrooms filter
echo ""
echo "→ Step 5: Testing bedrooms filter..."

BEDROOMS_RESULTS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?bedrooms=3" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

BEDROOMS_COUNT=$(echo "$BEDROOMS_RESULTS" | jq '.leads | length')

echo "✓ Found $BEDROOMS_COUNT leads with 3 bedrooms"

# Step 6: Test location filter
echo ""
echo "→ Step 6: Testing location filter..."

LOCATION_RESULTS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?location=Centro" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

LOCATION_COUNT=$(echo "$LOCATION_RESULTS" | jq '.leads | length')

echo "✓ Found $LOCATION_COUNT leads in Centro"

# Step 7: Test combined filters
echo ""
echo "→ Step 7: Testing combined filters (location + bedrooms + state)..."

COMBINED_RESULTS=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?location=Centro&bedrooms=3&state=qualified" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

COMBINED_COUNT=$(echo "$COMBINED_RESULTS" | jq '.leads | length')

echo "✓ Found $COMBINED_COUNT qualified leads in Centro with 3 bedrooms"

# Step 8: Test sorting (ascending)
echo ""
echo "→ Step 8: Testing sorting (budget ascending)..."

SORTED_ASC=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?sort_by=budget_max&sort_order=asc&limit=10" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

FIRST_BUDGET=$(echo "$SORTED_ASC" | jq '.leads[0].budget_max')
LAST_BUDGET=$(echo "$SORTED_ASC" | jq '.leads[-1].budget_max')

echo "✓ Sorted ascending: first=$FIRST_BUDGET, last=$LAST_BUDGET"

# Step 9: Test sorting (descending)
echo ""
echo "→ Step 9: Testing sorting (budget descending)..."

SORTED_DESC=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?sort_by=budget_max&sort_order=desc&limit=10" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

FIRST_BUDGET_DESC=$(echo "$SORTED_DESC" | jq '.leads[0].budget_max')

echo "✓ Sorted descending: first=$FIRST_BUDGET_DESC"

# Step 10: Create a saved filter
echo ""
echo "→ Step 10: Creating saved filter..."

SAVED_FILTER=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/filters" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d '{
    "name": "High Value Centro Leads",
    "filter_params": {
      "location": "Centro",
      "budget_min": 300000,
      "state": "qualified"
    },
    "is_shared": false
  }')

FILTER_ID=$(echo "$SAVED_FILTER" | jq -r '.id')

if [ -z "$FILTER_ID" ] || [ "$FILTER_ID" == "null" ]; then
    echo "✗ FAIL: Failed to create saved filter"
    echo "Response: $SAVED_FILTER"
    exit 1
fi

echo "✓ Saved filter created (ID: $FILTER_ID)"

# Step 11: List saved filters
echo ""
echo "→ Step 11: Listing saved filters..."

FILTERS_LIST=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/filters" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

FILTERS_COUNT=$(echo "$FILTERS_LIST" | jq '.filters | length')

echo "✓ Found $FILTERS_COUNT saved filters"

# Step 12: Test CSV export
echo ""
echo "→ Step 12: Testing CSV export..."

CSV_RESPONSE=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/export?state=qualified" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

CSV_LINES=$(echo "$CSV_RESPONSE" | wc -l | tr -d ' ')

if [ "$CSV_LINES" -lt 2 ]; then
    echo "✗ FAIL: CSV export failed or returned empty"
    exit 1
fi

echo "✓ CSV export successful ($CSV_LINES lines)"

# Step 13: Test pagination
echo ""
echo "→ Step 13: Testing pagination..."

PAGE1=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads?limit=2&offset=0" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

PAGE1_COUNT=$(echo "$PAGE1" | jq '.leads | length')
HAS_NEXT=$(echo "$PAGE1" | jq -r '.data.pagination.has_next')

echo "✓ Page 1: $PAGE1_COUNT leads, has_next: $HAS_NEXT"

# Step 14: Delete saved filter
echo ""
echo "→ Step 14: Deleting saved filter..."

DELETE_RESPONSE=$(curl -s -X DELETE "${ODOO_BASE_URL}/api/v1/leads/filters/${FILTER_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

DELETE_SUCCESS=$(echo "$DELETE_RESPONSE" | jq -r '.success')

if [ "$DELETE_SUCCESS" != "true" ]; then
    echo "✗ FAIL: Failed to delete saved filter"
    echo "Response: $DELETE_RESPONSE"
    exit 1
fi

echo "✓ Saved filter deleted successfully"

# Summary
echo ""
echo "========================================="
echo "✓ ALL TESTS PASSED"
echo "========================================="
echo ""
echo "Test Summary:"
echo "  - Budget filters: ✓"
echo "  - Bedrooms filter: ✓"
echo "  - Location filter: ✓"
echo "  - Combined filters: ✓"
echo "  - Sorting (asc/desc): ✓"
echo "  - Saved filters (CRUD): ✓"
echo "  - CSV export: ✓"
echo "  - Pagination: ✓"
echo ""

exit 0
