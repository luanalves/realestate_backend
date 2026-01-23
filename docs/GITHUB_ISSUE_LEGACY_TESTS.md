# GitHub Issue: Refactor Legacy E2E Tests for Odoo 18.0 Compatibility

## 📋 Issue Summary

**Title:** Refactor legacy E2E tests (US2-S2/S3/S4, US3-S1/S2/S3) with Odoo 18.0 field structure

**Labels:** `technical-debt`, `testing`, `refactoring`, `P2`

**Milestone:** RBAC User Profiles - Phase Cleanup

---

## 🎯 Context

6 E2E tests were created before Odoo 18.0 model updates and need comprehensive refactoring to match current field structure. These tests currently fail to create properties due to missing required fields and outdated field names.

**Current Status:** 6/12 tests passing (50%) - RBAC implementation is validated and working correctly. The issue is with test structure, not the actual implementation.

---

## 📂 Affected Files

### Tests Requiring Refactoring

1. `integration_tests/test_us2_s2_manager_menus.sh` - Manager menu access
2. `integration_tests/test_us2_s3_manager_assigns_properties.sh` - Manager property assignment
3. `integration_tests/test_us2_s4_manager_isolation.sh` - Manager multi-tenancy
4. `integration_tests/test_us3_s1_agent_assigned_properties.sh` - Agent property visibility
5. `integration_tests/test_us3_s2_agent_auto_assignment.sh` - Agent auto-assignment
6. `integration_tests/test_us3_s3_agent_own_leads.sh` - Agent lead management

---

## 🐛 Problems Identified

### 1. Missing Step 3.5: Reference Data Retrieval

**Issue:** Tests attempt to create properties without first retrieving required reference IDs

**Impact:** Properties fail to create (IDs return empty), test assertions fail

**Required References:**
- `property_type_id` (Many2one to real.estate.property.type)
- `location_type_id` (Many2one to real.estate.location.type)
- `state_id` (Many2one to real.estate.state)

### 2. Missing Required Fields

**Issue:** Property creation missing mandatory fields added in Odoo 18.0

**Missing Fields:**
```json
{
  "zip_code": "string (required)",
  "state_id": "integer (required, Many2one)",
  "city": "string (required)",
  "street": "string (required)",
  "street_number": "string (required)",
  "area": "float (required)",
  "property_type_id": "integer (required, Many2one)",
  "location_type_id": "integer (required, Many2one)"
}
```

### 3. Outdated Field Names

**Issue:** Tests using old field names from pre-18.0 models

**Required Mappings:**
- ❌ `property_type: "apartment"` → ✅ `property_type_id: $PROPERTY_TYPE_ID`
- ❌ `selling_price: 300000` → ✅ `price: 300000`
- ❌ `state: "available"` → ✅ `property_status: "available"`

### 4. Incorrect Relationship Structure

**Issue:** Using Many2one syntax for Many2many field

**Required Change:**
- ❌ `company_id: $COMPANY_ID` → ✅ `company_ids: [[6, 0, [$COMPANY_ID]]]`

---

## ✅ Solution Template

### Reference Implementation

**File:** `integration_tests/test_us3_s5_agent_company_isolation.sh` (commit 761401c)

This test demonstrates the correct structure and serves as the template for all corrections.

### Step 3.5: Retrieve Reference Data (Lines 260-333)

```bash
echo "=========================================="
echo "Step 3.5: Retrieve Reference Data for Properties"
echo "=========================================="

# Get first property type
PROPERTY_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.property.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

PROPERTY_TYPE_ID=$(echo "$PROPERTY_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Property Type ID: $PROPERTY_TYPE_ID"

# Get first location type
LOCATION_TYPE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.location.type",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

LOCATION_TYPE_ID=$(echo "$LOCATION_TYPE_RESPONSE" | jq -r '.result[0].id')
echo "✓ Location Type ID: $LOCATION_TYPE_ID"

# Get first state
STATE_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "model": "real.estate.state",
      "method": "search_read",
      "args": [[]],
      "kwargs": {
        "fields": ["id", "name"],
        "limit": 1
      }
    },
    "id": 1
  }')

STATE_ID=$(echo "$STATE_RESPONSE" | jq -r '.result[0].id')
echo "✓ State ID: $STATE_ID"

# Validate all reference data retrieved
if [ "$PROPERTY_TYPE_ID" == "null" ] || [ "$LOCATION_TYPE_ID" == "null" ] || [ "$STATE_ID" == "null" ]; then
    echo "❌ Failed to retrieve reference data"
    echo "Property Type: $PROPERTY_TYPE_ID"
    echo "Location Type: $LOCATION_TYPE_ID"
    echo "State: $STATE_ID"
    exit 1
fi

echo "✓ All reference data retrieved successfully"
```

### Property Creation with All Required Fields (Lines 347-384)

```bash
PROPERTY_A1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=$ADMIN_SESSION" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"call\",
    \"params\": {
      \"model\": \"real.estate.property\",
      \"method\": \"create\",
      \"args\": [{
        \"name\": \"Property A1\",
        \"property_type_id\": $PROPERTY_TYPE_ID,
        \"location_type_id\": $LOCATION_TYPE_ID,
        \"zip_code\": \"01310-100\",
        \"state_id\": $STATE_ID,
        \"city\": \"São Paulo\",
        \"street\": \"Av Paulista\",
        \"street_number\": \"1001\",
        \"area\": 80.0,
        \"price\": 300000.0,
        \"property_status\": \"available\",
        \"company_ids\": [[6, 0, [$COMPANY_A_ID]]],
        \"agent_id\": $AGENT_A_ID
      }],
      \"kwargs\": {}
    },
    \"id\": 1
  }")

PROPERTY_A1_ID=$(echo "$PROPERTY_A1_RESPONSE" | jq -r '.result')
echo "Property A1 created: ID=$PROPERTY_A1_ID"

if [ "$PROPERTY_A1_ID" == "null" ] || [ -z "$PROPERTY_A1_ID" ]; then
    echo "❌ Property A1 creation failed"
    echo "Response: $PROPERTY_A1_RESPONSE"
    exit 1
fi
```

### Company IDs (Many2many Syntax)

```bash
# Correct syntax for Many2many field
"company_ids": [[6, 0, [$COMPANY_ID]]]

# NOT this (Many2one syntax):
"company_id": $COMPANY_ID
```

---

## 🔧 Implementation Checklist

For each of the 6 tests:

- [ ] Add Step 3.5 after company/user creation
- [ ] Retrieve `property_type_id` from `real.estate.property.type`
- [ ] Retrieve `location_type_id` from `real.estate.location.type`
- [ ] Retrieve `state_id` from `real.estate.state`
- [ ] Validate all reference IDs are not null
- [ ] Update property creation to include ALL required fields:
  - [ ] `property_type_id` (not `property_type`)
  - [ ] `location_type_id`
  - [ ] `zip_code`
  - [ ] `state_id`
  - [ ] `city`
  - [ ] `street`
  - [ ] `street_number`
  - [ ] `area`
  - [ ] `price` (not `selling_price`)
  - [ ] `property_status` (not `state`)
  - [ ] `company_ids` (not `company_id`)
  - [ ] `agent_id` (if applicable)
- [ ] Test property creation returns valid ID
- [ ] Verify test assertions pass

---

## 📊 Partial Corrections Already Applied

**Commit:** `b6cb70d` - "fix(tests): remove invalid state field from US2/US3 tests"

### What Was Fixed:
1. ✅ Removed invalid `state` field from company creation
2. ✅ Updated field names via sed:
   - `property_type` → `property_type_id`
   - `selling_price` → `price`
   - `state` → `property_status`

### What Still Needs Fixing:
1. ❌ Add Step 3.5 for reference data retrieval
2. ❌ Add missing required fields (zip_code, state_id, city, street, etc.)
3. ❌ Change `company_id` to `company_ids`

---

## 🎯 Success Criteria

### Before:
- 6/12 tests passing (50%)
- Properties fail to create (empty IDs)
- Assertions fail due to missing data

### After:
- 12/12 tests passing (100%)
- All properties created successfully
- All assertions pass
- Complete test coverage for RBAC implementation

---

## ⏱️ Estimated Effort

**Time:** ~2 hours

**Breakdown:**
- 6 tests × 15 minutes each = 90 minutes
- Testing and validation = 30 minutes

---

## 📚 Related Documentation

- **Working Test:** [test_us3_s5_agent_company_isolation.sh](../integration_tests/test_us3_s5_agent_company_isolation.sh) (commit 761401c)
- **Status Report:** [STATUS.md](../integration_tests/STATUS.md)
- **Execution Summary:** [EXECUTION_SUMMARY_2026-01-23.md](../integration_tests/EXECUTION_SUMMARY_2026-01-23.md)
- **Commits:**
  - `ffc7f6f` - P0 security fix (16 record rules)
  - `761401c` - US3-S5 complete fix (template)
  - `b6cb70d` - Partial US2/US3 corrections
  - `8e7d4bc` - Documentation update

---

## 🔗 Dependencies

**Blocked By:** None - can start immediately

**Blocks:**
- Complete E2E test coverage documentation
- Final validation of RBAC implementation
- US2/US3 acceptance criteria validation

---

## 📝 Notes

- RBAC implementation is **correct and working** - this is purely a test infrastructure issue
- 50% of tests already passing validates the core implementation
- Template is documented and proven (US3-S5)
- Can be tackled incrementally (1 test at a time)
- Not blocking new feature development (US4+)

---

## ✅ Acceptance Criteria

1. All 6 legacy tests execute without errors
2. All property creation calls return valid IDs
3. All test assertions pass
4. Test output matches expected results
5. No regression in currently passing tests
6. Documentation updated (STATUS.md, tasks.md)

---

**Created:** 2026-01-23  
**Priority:** P2 (after US4 implementation)  
**Assignee:** TBD  
**Related Branch:** `005-rbac-user-profiles`
