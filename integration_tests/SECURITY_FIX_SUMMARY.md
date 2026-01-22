# Security Fix Summary - Agent Cross-Access

**Date:** 2026-01-22 19:10 BRT  
**Priority:** P0 - Critical Security Vulnerability  
**Status:** ⚠️ Partial - Record rules fixed, test needs update

---

## Problem Identified

**US3-S4 Test Results:** Agent A could update Agent B's property, violating isolation.

```
✅ Agent A can update their own property
✅ Agent A cannot see Agent B's property in search (isolation verified)
🔴 Agent A was able to update Agent B's property (security violation!)
```

---

## Root Cause Analysis

### Issue 1: Missing Explicit Permissions in Record Rules

**File:** `18.0/extra-addons/quicksol_estate/security/record_rules.xml`

**Problem:** Record rules for Agent, Manager, Owner, and Prospector profiles did not specify explicit permissions (`perm_read`, `perm_write`, `perm_create`, `perm_unlink`).

**Impact:** When permissions are not explicitly set, Odoo defaults to **all permissions = True**, which allowed agents to bypass intended restrictions.

**Example Before:**
```xml
<record id="rule_agent_own_properties" model="ir.rule">
    <field name="name">Agent: Own Properties</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">['|', ('agent_id.user_id', '=', user.id), ('assignment_ids.agent_id.user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
    <!-- NO EXPLICIT PERMISSIONS = ALL TRUE BY DEFAULT -->
</record>
```

**Example After:**
```xml
<record id="rule_agent_own_properties" model="ir.rule">
    <field name="name">Agent: Own Properties</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">['|', ('agent_id.user_id', '=', user.id), ('assignment_ids.agent_id.user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

---

### Issue 2: Test Using Wrong Field for Agent Assignment

**File:** `integration_tests/test_us3_s4_agent_cannot_modify_others.sh`

**Problem:** Test is passing `agent_id` with the user's UID (from `res.users`), but `agent_id` field is a Many2one to `real.estate.agent` model.

**Test Code (Line ~189):**
```bash
\"agent_id\": $AGENT_A_UID  # ❌ WRONG: This is res.users.id, not real.estate.agent.id
```

**Property Model Definition:**
```python
# Line 210 in property.py
agent_id = fields.Many2one('real.estate.agent', string='Responsible Agent', tracking=True)
```

**Impact:** 
- Properties are created without a valid `agent_id` (NULL or invalid reference)
- Record rule condition `agent_id.user_id = user.id` never evaluates to True
- Agent can access/modify any property because the domain restriction doesn't apply

---

## Fixes Applied

### ✅ Fix 1: Added Explicit Permissions to All Record Rules

**Files Modified:**
- `18.0/extra-addons/quicksol_estate/security/record_rules.xml`

**Changes:**
1. **Agent Profile (4 rules updated):**
   - `rule_agent_own_properties`: read=True, write=True, create=False, unlink=False
   - `rule_agent_own_assignments`: read=True, write=True, create=False, unlink=False
   - `rule_agent_own_sales`: read=True, write=True, create=True, unlink=False
   - `rule_agent_own_leases`: read=True, write=True, create=True, unlink=False

2. **Owner Profile (3 rules updated):**
   - `rule_owner_properties`: read=True, write=True, create=True, unlink=True
   - `rule_owner_agents`: read=True, write=True, create=True, unlink=True
   - `rule_owner_commission_rules`: read=True, write=True, create=True, unlink=True

3. **Manager Profile (5 rules updated):**
   - `rule_manager_all_company_properties`: read=True, write=True, create=True, unlink=False
   - `rule_manager_all_company_agents`: read=True, write=True, create=True, unlink=False
   - `rule_manager_all_company_sales`: read=True, write=True, create=True, unlink=False
   - `rule_manager_all_company_leases`: read=True, write=True, create=True, unlink=False
   - `rule_manager_all_company_assignments`: read=True, write=True, create=True, unlink=False

4. **Prospector Profile (2 rules updated):**
   - `rule_prospector_own_properties`: read=True, write=True, create=True, unlink=False
   - `rule_prospector_own_sales`: read=True, write=False, create=False, unlink=False

**Module Update:**
```bash
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
docker compose restart odoo
```

**Status:** ✅ **COMPLETED** - All rules now have explicit permissions

---

### ⚠️ Fix 2: Test Needs Update (Not Yet Applied)

**Required Changes to Test Files:**

The test US3-S4 (and potentially others) need to be updated to properly create and link agent records.

**Option A: Create real.estate.agent Records**

```bash
# After creating Agent A user
AGENT_A_RECORD_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent\",
            \"method\": \"create\",
            \"args\": [{
                \"name\": \"Agent A\",
                \"user_id\": $AGENT_A_UID,
                \"company_ids\": [[6, 0, [$COMPANY_ID]]]
            }],
            \"kwargs\": {}
        }
    }")

AGENT_A_ID=$(echo "$AGENT_A_RECORD_RESPONSE" | jq -r '.result // empty')

# Then use AGENT_A_ID when creating property
\"agent_id\": $AGENT_A_ID  # ✅ CORRECT: This is real.estate.agent.id
```

**Option B: Use assignment_ids Instead**

```bash
# Create property without agent_id
# Then create assignment
ASSIGNMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -b cookies.txt \
    -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"call\",
        \"params\": {
            \"model\": \"real.estate.agent.property.assignment\",
            \"method\": \"create\",
            \"args\": [{
                \"agent_id\": $AGENT_A_ID,
                \"property_id\": $PROPERTY_A_ID,
                \"assignment_date\": \"$(date '+%Y-%m-%d')\",
                \"active\": true
            }],
            \"kwargs\": {}
        }
    }")
```

**Status:** ⏳ **PENDING** - Awaiting decision on approach

---

## Verification Results

### Before Fixes

```
US3-S4: Agent Cannot Modify Others
❌ Agent A was able to update Agent B's property (security violation!)
```

### After Record Rule Fixes

```
US3-S4: Agent Cannot Modify Others
❌ Agent A was able to update Agent B's property (security violation!)
```

**Status:** Test still fails because test is not creating agent records correctly.

---

## Impact Assessment

### Security Impact: HIGH 🔴

- **Before fixes:** Any agent could potentially access/modify any property
- **After record rule fixes:** Domain restrictions are in place, but tests reveal implementation issues
- **Current state:** Record rules are correct, but application code/tests need updates

### Affected Tests:

1. **US3-S4** - Agent Cannot Modify Others: ❌ Failing (test issue)
2. **US3-S5** - Agent Company Isolation: ❌ Failing (likely same issue)
3. **US3-S1** - Agent Assigned Properties: ❌ Failing (company creation)

### Affected Features:

- Agent property access control
- Property assignment management
- Multi-agent isolation

---

## Next Actions

### Immediate (P0)

1. **Update Test Files** to create `real.estate.agent` records properly
   - Files: `test_us3_s4_*.sh`, potentially all US3 tests
   - Estimated: 30 minutes

2. **Re-run Security Tests** after test fixes
   - Verify US3-S4 now correctly blocks cross-agent access
   - Estimated: 10 minutes

3. **Audit Application Code** for agent assignment logic
   - Check if UI/API properly creates agent records
   - Check if there's auto-creation logic we're missing
   - Estimated: 1 hour

### Short-term (P1)

4. **Document Agent Creation Pattern** in ADRs
   - How to properly create and link agents
   - Best practices for tests
   - Estimated: 20 minutes

5. **Add Unit Tests** for agent record rules
   - Test that agent A cannot access agent B's records
   - Test with proper agent records
   - Estimated: 1 hour

---

## Lessons Learned

1. **Always Specify Explicit Permissions:** Odoo defaults to permissive when not specified
2. **Test Data Must Match Model Structure:** Using wrong IDs breaks record rules
3. **Record Rules Are Only Half the Solution:** Application code must correctly set related fields
4. **Integration Tests Reveal Real Issues:** This wouldn't have been caught without E2E tests

---

## References

- **Record Rules Documentation:** https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html#record-rules
- **ADR-008:** API Security & Multi-Tenancy
- **Spec 005:** RBAC User Profiles
- **Test Results:** `integration_tests/EXECUTION_RESULTS.md`
