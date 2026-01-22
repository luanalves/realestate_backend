---
description: Generate test code based on acceptance scenarios from spec.md using Test Strategy and Test Executor agents
handoffs: 
  - label: Implement Project
    agent: speckit.implement
    prompt: Tests generated. Start the implementation
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute.

2. **Load required documents**:
   - **Required**: Read spec.md - extract ALL acceptance scenarios from ALL user stories
   - **Required**: Read ADR-003 (docs/adr/ADR-003-mandatory-test-coverage.md) - apply "Regra de Ouro"
   - **Optional**: Read tasks.md - find test generation tasks (T***.A, T***.B, etc.)
   - **Required**: Read 18.0/.env - get test credentials (NEVER hardcode)

3. **Parse all acceptance scenarios**:
   For each User Story in spec.md:
   - Extract story name and priority (P1, P2, P3)
   - Extract all acceptance scenarios (Given/When/Then format)
   - Extract involved code (models, controllers, record rules)
   - Create scenario list:
     ```
     US1-S1: "Given a SaaS admin creates..."
     US1-S2: "Given an owner is logged in..."
     US1-S3: "Given an owner from Company A..."
     US2-S1: "Given an owner is logged in, When they create a new user..."
     ...
     ```

4. **Apply Test Strategy (Regra de Ouro) for each scenario**:
   
   For each scenario, determine test type:
   
   **Precisa de banco de dados?**
   
   ❌ **NÃO** → Teste Unitário (unittest.mock)
   - Validações de campo (required, constraints)
   - Cálculos e lógica pura
   - Transformações de dados
   - Location: `18.0/extra-addons/quicksol_estate/tests/unit/test_*.py`
   
   ✅ **SIM** → Teste E2E
   - **API operations** → curl/bash script
     - OAuth authentication
     - CRUD via REST API
     - Multi-tenancy isolation
     - Record rules validation
     - Location: `integration_tests/test_*.sh`
   
   - **UI workflows** → Cypress
     - Login/logout flows
     - Form interactions
     - Menu visibility per role
     - Navigation between modules
     - Location: `cypress/e2e/*.cy.js`

5. **Generate test code for each scenario**:

   **For E2E API tests (curl/bash)**:
   ```bash
   #!/bin/bash
   set -e
   
   # =============================================================
   # Test: [US ID] - [Scenario description]
   # Generated: [date]
   # Spec: specs/[feature]/spec.md
   # =============================================================
   
   # Load credentials from .env (NEVER hardcode)
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   source "$SCRIPT_DIR/../18.0/.env"
   
   BASE_URL="${TEST_BASE_URL:-http://localhost:8069}"
   
   echo "========================================="
   echo "[US ID] [Scenario name]"
   echo "========================================="
   
   # Setup: Admin login
   ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
     -H "Content-Type: application/json" \
     -d "{
       \"grant_type\": \"password\",
       \"username\": \"$TEST_USER_ADMIN\",
       \"password\": \"$TEST_PASSWORD_ADMIN\",
       \"database\": \"$TEST_DATABASE\"
     }" | jq -r '.access_token')
   
   [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ] && { echo "❌ Admin login failed"; exit 1; }
   echo "✅ Admin login successful"
   
   # [Test steps based on Given/When/Then]
   
   # Cleanup (if needed)
   
   echo "========================================="
   echo "✅ All tests passed!"
   echo "========================================="
   ```

   **For E2E UI tests (Cypress)**:
   ```javascript
   // =============================================================
   // Test: [US ID] - [Scenario description]
   // Generated: [date]
   // Spec: specs/[feature]/spec.md
   // =============================================================
   
   describe('[US ID] - [Story name]', () => {
     beforeEach(() => {
       cy.login(Cypress.env('TEST_USER_ADMIN'), Cypress.env('TEST_PASSWORD_ADMIN'));
     });
   
     it('[Scenario description]', () => {
       // Given: [setup]
       // When: [action]
       // Then: [assertion]
     });
   });
   ```

   **For Unit tests (Python)**:
   ```python
   # =============================================================
   # Test: [US ID] - [Scenario description]
   # Generated: [date]
   # Spec: specs/[feature]/spec.md
   # =============================================================
   
   import unittest
   from unittest.mock import Mock, patch
   
   class Test[FeatureName](unittest.TestCase):
       def test_[scenario_name](self):
           """[Scenario description]"""
           # Given: [setup with mocks]
           # When: [call function]
           # Then: [assertions]
           pass
   
   if __name__ == '__main__':
       unittest.main()
   ```

6. **Create test files**:
   - Create `integration_tests/` directory if not exists
   - Create each test file with executable permissions
   - Use naming convention: `test_[us_id]_[scenario_id]_[short_name].sh`
   - Add README.md to integration_tests/ with execution instructions

7. **Update tasks.md**:
   - Mark all test generation tasks as completed [X]
   - Add file paths to each completed task

8. **Generate execution script**:
   Create `integration_tests/run_all_tests.sh`:
   ```bash
   #!/bin/bash
   set -e
   
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   PASSED=0
   FAILED=0
   
   echo "Running all integration tests..."
   
   for test in "$SCRIPT_DIR"/test_*.sh; do
     echo ">>> Running: $(basename $test)"
     if bash "$test"; then
       ((PASSED++))
     else
       ((FAILED++))
       echo "❌ FAILED: $(basename $test)"
     fi
   done
   
   echo "========================================="
   echo "Results: $PASSED passed, $FAILED failed"
   echo "========================================="
   
   [ $FAILED -eq 0 ] || exit 1
   ```

9. **Report**:
   Output summary:
   - Total scenarios found
   - Tests generated per type (Unit, E2E API, E2E UI)
   - File paths created
   - Tasks marked as complete
   - Command to run all tests: `bash integration_tests/run_all_tests.sh`

## Test Generation Rules

**CRITICAL**: Follow ADR-003 strictly

1. **Regra de Ouro**: If needs database → E2E, else → Unit
2. **Never use HttpCase**: It runs in read-only transactions (ADR-002)
3. **Never hardcode credentials**: Always read from .env
4. **Always include cleanup**: Tests should be idempotent
5. **Test isolation**: Each test should be independent
6. **Descriptive names**: Test name should describe scenario

## Context

Feature specification to process: $ARGUMENTS

This agent generates ALL tests for a feature spec, then hands off to speckit.implement for code implementation.
