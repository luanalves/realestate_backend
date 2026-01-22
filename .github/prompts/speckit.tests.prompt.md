---
mode: agent
description: Generate test code based on acceptance scenarios from spec.md using Test Strategy and Test Executor agents
agent: speckit.tests
---

# Speckit Tests Agent

Generate all tests for a feature specification based on acceptance scenarios.

## Usage

```
@speckit.tests [feature-name]
```

## Example

```
@speckit.tests 005-rbac-user-profiles
```

## What it does

1. Reads spec.md and extracts ALL acceptance scenarios
2. Applies "Regra de Ouro" (ADR-003) to determine test type for each
3. Generates test code (curl/bash, Cypress, or unittest)
4. Creates test files in correct locations
5. Marks test generation tasks as complete in tasks.md
6. Hands off to speckit.implement for code implementation

## Output

- `integration_tests/test_us*_*.sh` - E2E API tests
- `cypress/e2e/test_us*_*.cy.js` - E2E UI tests
- `tests/unit/test_*_unit.py` - Unit tests
- `integration_tests/run_all_tests.sh` - Test runner

## Workflow Integration

```mermaid
graph LR
    A[@speckit.tasks] --> B[@speckit.tests]
    B --> C[@speckit.implement]
    C --> D[Validation]
```

1. `@speckit.tasks` - Generate tasks.md with test tasks
2. `@speckit.tests` - Generate ALL test code (this agent)
3. `@speckit.implement` - Implement features (TDD: tests first)
4. Run tests to validate implementation
