# Manual Execution Guide - US4 Tests

## Current Situation

The terminal environment is experiencing persistent issues (hung state). The US4 tests have been created and are ready for execution, but cannot be run through the automated tool.

## Tests Ready for Execution

1. **test_us4_s2_manager_reassign_properties.sh** ✅ CREATED
2. **test_us4_s4_manager_multitenancy.sh** ✅ CREATED

## Manual Execution Instructions

### Prerequisites

1. Ensure Odoo 18.0 is running:
   ```bash
   cd /opt/homebrew/var/www/realestate/realestate_backend/18.0
   docker compose ps
   # Should show odoo and db containers running
   ```

2. Navigate to integration tests directory:
   ```bash
   cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests
   ```

### Execute US4-S2 (Manager Reassigns Properties)

```bash
# Make executable (if needed)
chmod +x test_us4_s2_manager_reassign_properties.sh

# Execute test
bash test_us4_s2_manager_reassign_properties.sh

# Expected output (last lines):
# ==========================================
# ✅ TEST PASSED: US4-S2 Manager Reassigns Properties
# ==========================================
```

**Test validates:**
- Manager creates property assigned to Agent 1
- Manager reads property assignment
- Manager updates agent_id to Agent 2
- Verification confirms reassignment successful
- Manager has write permissions on all company properties

### Execute US4-S4 (Manager Multi-Tenancy Isolation)

```bash
# Make executable (if needed)
chmod +x test_us4_s4_manager_multitenancy.sh

# Execute test
bash test_us4_s4_manager_multitenancy.sh

# Expected output (last lines):
# ==========================================
# ✅ TEST PASSED: US4-S4 Manager Multi-Tenancy Isolation
# ==========================================
```

**Test validates:**
- Company A with Manager A and 2 properties
- Company B with Manager B and 2 properties
- Manager A cannot see Company B properties
- Manager B cannot see Company A properties
- Multi-tenancy isolation working correctly

## Troubleshooting

### Common Issues

1. **Database Connection Error:**
   ```bash
   # Check if database is ready
   cd ../18.0
   docker compose logs db | tail -20
   ```

2. **Odoo Not Ready:**
   ```bash
   # Check Odoo logs
   docker compose logs odoo | tail -50
   ```

3. **Test Fails with "Company Not Found":**
   - This is expected on first run
   - Tests create new companies dynamically
   - Should pass on clean database state

### Expected Behavior

**US4-S2 Should:**
- Create 1 property initially for Agent 1
- Manager successfully reassigns to Agent 2
- Final validation shows property belongs to Agent 2
- Test passes with "✅ TEST PASSED" message

**US4-S4 Should:**
- Create 2 separate companies with 2 properties each
- Manager A sees only Company A data (2 properties)
- Manager B sees only Company B data (2 properties)
- No cross-company visibility
- Test passes with "✅ TEST PASSED" message

## After Successful Execution

1. **Update STATUS.md:**
   ```bash
   # Edit integration_tests/STATUS.md
   # Change US4-S2 and US4-S4 from "CREATED" to "✅ PASSING"
   ```

2. **Commit Results:**
   ```bash
   git add integration_tests/test_us4_s2_manager_reassign_properties.sh
   git add integration_tests/test_us4_s4_manager_multitenancy.sh
   git add integration_tests/STATUS.md
   git commit -m "test(us4): validate US4-S2 and US4-S4 - Manager oversight tests passing"
   git push origin 005-rbac-user-profiles
   ```

3. **Update Test Coverage:**
   - Total tests: 15
   - Passing: 9/15 (60%) if both pass
   - US4 complete: 3/3 ✅

## Next Steps After Tests Pass

Three options recommended:

1. **Option A: Implement US5 (Prospector)** - RECOMMENDED
   - Prospector creates leads, auto-assignment
   - Commission split (30% prospector, 70% agent)
   - Time: ~3-4 hours

2. **Option B: Fix Legacy Tests**
   - Refactor 6 tests following US3-S5 pattern
   - Achieve 100% test coverage
   - Time: ~2 hours (documented in GITHUB_ISSUE_LEGACY_TESTS.md)

3. **Option C: Continue US6-10**
   - Other profiles (Receptionist, Financial, Legal, Director)
   - Lower priority (P3)

## Terminal Recovery

If terminal issues persist in VS Code:

1. **Close all terminals:**
   - Click "X" on each terminal tab
   - Or: Terminal → Close All Terminals

2. **Open fresh terminal:**
   - Terminal → New Terminal
   - Or: Ctrl+` (backtick)

3. **Navigate and execute:**
   ```bash
   cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests
   bash test_us4_s2_manager_reassign_properties.sh
   bash test_us4_s4_manager_multitenancy.sh
   ```

## Contact / Questions

If tests fail:
1. Check docker containers are running
2. Verify database is accessible
3. Review Odoo logs for errors
4. Check that all US4-S1 prerequisites are met (ACL entries, record rules)

The tests follow the proven US3-S5 pattern and include all required fields with correct Odoo 18.0 syntax.
