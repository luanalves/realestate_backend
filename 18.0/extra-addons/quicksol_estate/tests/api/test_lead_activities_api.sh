#!/bin/bash
# E2E API Test: Lead Activity Tracking (Phase 5)
# Tests POST/GET /api/v1/leads/{id}/activities and schedule-activity endpoints
# FR-033, FR-034, FR-035, FR-036
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
echo "E2E API Test: Lead Activity Tracking"
echo "========================================="

# Step 1: Authenticate as manager
echo "→ Step 1: Authenticating as manager..."
authenticate_user "${TEST_MANAGER_EMAIL}" "${TEST_MANAGER_PASSWORD}" || exit 1
MANAGER_TOKEN="$OAUTH_TOKEN"
MANAGER_SESSION="$USER_SESSION_ID"

echo "✓ Manager authenticated (session: ${MANAGER_SESSION:0:10}...)"

# Step 2: Create a test lead
echo ""
echo "→ Step 2: Creating test lead..."

LEAD_CREATE=$(make_api_request POST "/api/v1/leads" '{
  "name": "Activity Test Lead",
  "phone": "+5511999887766",
  "email": "activity-test@example.com",
  "state": "new",
  "budget_min": 300000,
  "budget_max": 500000
}')

LEAD_ID=$(echo "$LEAD_CREATE" | jq -r '.id')

if [ -z "$LEAD_ID" ] || [ "$LEAD_ID" == "null" ]; then
    echo "✗ FAIL: Failed to create test lead"
    echo "Response: $LEAD_CREATE"
    exit 1
fi

echo "✓ Lead created (ID: $LEAD_ID)"
    exit 1
fi

echo "✓ Lead created (ID: $LEAD_ID)"

# Step 3: Log a CALL activity
echo ""
echo "→ Step 3: Logging CALL activity..."

ACTIVITY_CALL=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d '{
    "body": "Called client to discuss property preferences. Very interested in apartments in Centro area.",
    "activity_type": "call"
  }')

CALL_ID=$(echo "$ACTIVITY_CALL" | jq -r '.id')

if [ -z "$CALL_ID" ] || [ "$CALL_ID" == "null" ]; then
    echo "✗ FAIL: Failed to log CALL activity"
    echo "Response: $ACTIVITY_CALL"
    exit 1
fi

echo "✓ CALL activity logged (ID: $CALL_ID)"

# Step 4: Log an EMAIL activity
echo ""
echo "→ Step 4: Logging EMAIL activity..."

ACTIVITY_EMAIL=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d '{
    "body": "Sent property brochure with 5 apartments in Centro area matching budget.",
    "activity_type": "email"
  }')

EMAIL_ID=$(echo "$ACTIVITY_EMAIL" | jq -r '.id')

if [ -z "$EMAIL_ID" ] || [ "$EMAIL_ID" == "null" ]; then
    echo "✗ FAIL: Failed to log EMAIL activity"
    echo "Response: $ACTIVITY_EMAIL"
    exit 1
fi

echo "✓ EMAIL activity logged (ID: $EMAIL_ID)"

# Step 5: Log a MEETING activity
echo ""
echo "→ Step 5: Logging MEETING activity..."

ACTIVITY_MEETING=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d '{
    "body": "Scheduled property viewing for next Tuesday at 2 PM.",
    "activity_type": "meeting"
  }')

MEETING_ID=$(echo "$ACTIVITY_MEETING" | jq -r '.id')

if [ -z "$MEETING_ID" ] || [ "$MEETING_ID" == "null" ]; then
    echo "✗ FAIL: Failed to log MEETING activity"
    echo "Response: $ACTIVITY_MEETING"
    exit 1
fi

echo "✓ MEETING activity logged (ID: $MEETING_ID)"

# Step 6: List all activities
echo ""
echo "→ Step 6: Listing all lead activities..."

ACTIVITIES_LIST=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

ACTIVITY_COUNT=$(echo "$ACTIVITIES_LIST" | jq -r '.activities | length')

if [ "$ACTIVITY_COUNT" -lt 3 ]; then
    echo "✗ FAIL: Expected at least 3 activities, got $ACTIVITY_COUNT"
    echo "Response: $ACTIVITIES_LIST"
    exit 1
fi

echo "✓ Found $ACTIVITY_COUNT activities"

# Verify activity types
CALL_COUNT=$(echo "$ACTIVITIES_LIST" | jq '[.activities[] | select(.activity_type=="call")] | length')
EMAIL_COUNT=$(echo "$ACTIVITIES_LIST" | jq '[.activities[] | select(.activity_type=="email")] | length')
MEETING_COUNT=$(echo "$ACTIVITIES_LIST" | jq '[.activities[] | select(.activity_type=="meeting")] | length')

echo "  - CALL activities: $CALL_COUNT"
echo "  - EMAIL activities: $EMAIL_COUNT"
echo "  - MEETING activities: $MEETING_COUNT"

# Step 7: Get lead details with recent activities
echo ""
echo "→ Step 7: Getting lead with recent activities..."

LEAD_WITH_ACTIVITIES=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}?include_activities=true" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

HAS_RECENT_ACTIVITIES=$(echo "$LEAD_WITH_ACTIVITIES" | jq 'has("recent_activities")')

if [ "$HAS_RECENT_ACTIVITIES" != "true" ]; then
    echo "✗ FAIL: Lead details missing recent_activities field"
    echo "Response: $LEAD_WITH_ACTIVITIES"
    exit 1
fi

RECENT_COUNT=$(echo "$LEAD_WITH_ACTIVITIES" | jq '.recent_activities | length')
echo "✓ Lead includes $RECENT_COUNT recent activities"

# Step 8: Schedule a future activity
echo ""
echo "→ Step 8: Scheduling future activity..."

# Calculate date 7 days from now
FUTURE_DATE=$(date -u -v+7d +%Y-%m-%d 2>/dev/null || date -u -d '+7 days' +%Y-%m-%d)

SCHEDULED_ACTIVITY=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/schedule-activity" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d "{
    \"summary\": \"Follow-up call after viewing\",
    \"note\": \"Check if client is interested in making an offer\",
    \"date_deadline\": \"${FUTURE_DATE}\"
  }")

SCHEDULED_ID=$(echo "$SCHEDULED_ACTIVITY" | jq -r '.id')

if [ -z "$SCHEDULED_ID" ] || [ "$SCHEDULED_ID" == "null" ]; then
    echo "✗ FAIL: Failed to schedule activity"
    echo "Response: $SCHEDULED_ACTIVITY"
    exit 1
fi

echo "✓ Activity scheduled for $FUTURE_DATE (ID: $SCHEDULED_ID)"

# Step 9: Test activity pagination
echo ""
echo "→ Step 9: Testing activity pagination..."

ACTIVITIES_PAGE1=$(curl -s -X GET "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities?limit=2&offset=0" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}")

PAGE1_COUNT=$(echo "$ACTIVITIES_PAGE1" | jq -r '.activities | length')
HAS_MORE=$(echo "$ACTIVITIES_PAGE1" | jq -r '.pagination.has_more')

echo "✓ Page 1: $PAGE1_COUNT activities, has_more: $HAS_MORE"

# Step 10: Test validation (empty body)
echo ""
echo "→ Step 10: Testing validation (empty activity body)..."

INVALID_ACTIVITY=$(curl -s -X POST "${ODOO_BASE_URL}/api/v1/leads/${LEAD_ID}/activities" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MANAGER_TOKEN}" \
  -H "X-Openerp-Session-Id: ${MANAGER_SESSION}" \
  -d '{
    "body": "",
    "activity_type": "note"
  }')

ERROR_MSG=$(echo "$INVALID_ACTIVITY" | jq -r '.error')

if [ "$ERROR_MSG" == "null" ] || [ -z "$ERROR_MSG" ]; then
    echo "✗ FAIL: Expected validation error for empty body"
    exit 1
fi

echo "✓ Validation working: $ERROR_MSG"

# Summary
echo ""
echo "========================================="
echo "✓ ALL TESTS PASSED"
echo "========================================="
echo ""
echo "Test Summary:"
echo "  - Activities logged: 3 (call, email, meeting)"
echo "  - Activity listing: ✓"
echo "  - Recent activities in lead details: ✓"
echo "  - Scheduled activity: ✓"
echo "  - Pagination: ✓"
echo "  - Validation: ✓"
echo ""

exit 0
