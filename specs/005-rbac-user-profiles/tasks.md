# Tasks: RBAC User Profiles System

**Input**: Design documents from `/specs/005-rbac-user-profiles/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md
**Feature Branch**: `005-rbac-user-profiles`

**Tests Strategy (ADR-002 + ADR-003)**: This feature requires 3 types of automated tests:

1. **Linting (Flake8)** - MANDATORY before any code execution
   - Run: `./lint.sh` or `flake8 18.0/extra-addons/quicksol_estate/`
   - Must pass with 0 errors/warnings
   
2. **Unit Tests (Python unittest with mocks)** - MANDATORY for all validations
   - ✅ Use `unittest.mock` (NO database, NO Odoo framework)
   - ✅ Test ONLY business logic and validations
   - ✅ 100% coverage of all validations (required, constraints, compute)
   - ✅ Execution: < 1 second per test suite
   - ✅ Location: `tests/unit/test_*.py`
   - ❌ NEVER use `odoo.tests.TransactionCase` or `HttpCase` for unit tests
   
3. **E2E Tests** - MANDATORY for user-facing features
   - ✅ Cypress for UI workflows: `cypress/e2e/*.cy.js`
   - ✅ **curl scripts** for API endpoints (NOT HttpCase!)
   - ✅ Test against REAL running services (not test transactions)
   - ✅ Location: `integration_tests/test_*.sh` (curl commands)
   - ❌ NEVER use `odoo.tests.HttpCase` - it runs in read-only transactions

**CRITICAL**: HttpCase is PROHIBITED (ADR-002) - it executes in read-only transactions and breaks OAuth/sessions.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Odoo addon**: `18.0/extra-addons/quicksol_estate/`
- **Unit Tests** (mocks, no DB): `18.0/extra-addons/quicksol_estate/tests/unit/`
- **Integration Tests** (TransactionCase): `18.0/extra-addons/quicksol_estate/tests/integration/`
- **E2E Tests** (Cypress UI): `cypress/e2e/`
- **API Tests** (curl scripts): `integration_tests/` (root level)

**Test Directory Structure (REQUIRED):**
```
quicksol_estate/
├── tests/
│   ├── __init__.py
│   ├── unit/                          # Unit tests with mocks (NO database)
│   │   ├── __init__.py
│   │   ├── test_*_unit.py            # Pure logic tests
│   │   └── run_unit_tests.py         # unittest runner
│   ├── integration/                   # Integration tests (WITH database)
│   │   ├── __init__.py
│   │   └── test_*_integration.py     # TransactionCase tests
│   └── observers/                     # Observer tests (can be unit or integration)
│       ├── __init__.py
│       └── test_*_observer.py
└── integration_tests/                 # API E2E tests (curl scripts)
    ├── test_properties_api.sh
    ├── test_auth_api.sh
    └── README.md
```

**Test Execution Commands:**
```bash
# 1. Linting (FIRST - before any code)
./lint.sh

# 2. Unit Tests (fast - no database)
cd 18.0/extra-addons/quicksol_estate/tests/unit
python3 run_unit_tests.py

# 3. Integration Tests (Odoo framework + database)
docker compose run --rm odoo odoo --test-enable --test-tags=quicksol_estate --stop-after-init

# 4. E2E Cypress Tests (UI workflows)
npm run cypress:run

# 5. API Tests (curl against running server)
docker compose up -d  # Start services first
cd integration_tests
bash test_properties_api.sh
bash test_auth_api.sh
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Infrastructure services and event-driven architecture foundation

**⚠️ VALIDATION CHECKPOINT**: Before executing T002-T009, verify if RabbitMQ/Celery infrastructure already exists from previous session:
```bash
grep -A 10 "rabbitmq:" 18.0/docker-compose.yml
grep -A 10 "celery_" 18.0/docker-compose.yml
```
If services already exist, mark T002-T009 as completed or adjust to incremental updates only.

- [ ] T001 Update __manifest__.py version to 18.0.2.0.0 and add dependencies in 18.0/extra-addons/quicksol_estate/__manifest__.py
- [X] T002 [P] Update docker-compose.yml with RabbitMQ service (rabbitmq:3-management-alpine, ports 5672/15672) in 18.0/docker-compose.yml
- [X] T003 [P] Add celery_commission_worker service (2 workers, commission_events queue) to 18.0/docker-compose.yml
- [X] T004 [P] Add celery_audit_worker service (1 worker, audit_events queue) to 18.0/docker-compose.yml
- [X] T005 [P] Add celery_notification_worker service (1 worker, notification_events queue) to 18.0/docker-compose.yml
- [X] T006 [P] Add Flower monitoring service (port 5555, mher/flower:2.0) to 18.0/docker-compose.yml
- [X] T007 [P] Update .env with RabbitMQ credentials (RABBITMQ_USER, RABBITMQ_PASSWORD) in 18.0/.env
- [X] T008 [P] Add Celery configuration to .env (CELERY_BROKER_URL, CELERY_RESULT_BACKEND) in 18.0/.env
- [X] T009 [P] Add Flower credentials to .env (FLOWER_USER, FLOWER_PASSWORD) in 18.0/.env
- [X] T010 [P] Create celery_worker directory structure in 18.0/celery_worker/
- [X] T011 Create Celery worker Dockerfile (Python 3.11-slim, celery[redis,amqp]) in 18.0/celery_worker/Dockerfile
- [X] T012 Create Celery requirements.txt (celery==5.3.4, redis==5.0.1, kombu==5.3.4) in 18.0/celery_worker/requirements.txt
- [X] T013 Create Celery tasks.py with process_event_task implementation in 18.0/celery_worker/tasks.py
- [X] T014 Create pre-migrate.py script to backup current group assignments in 18.0/extra-addons/quicksol_estate/migrations/18.0.2.0.0/pre-migrate.py
- [X] T015 Create post-migrate.py script to add prospector_id column and indexes in 18.0/extra-addons/quicksol_estate/migrations/18.0.2.0.0/post-migrate.py

**Checkpoint**: Infrastructure services configured, migration scripts ready ✅

---

## ⚠️ TESTING ANTI-PATTERNS (Do NOT Do This!)

**According to ADR-002 and ADR-003, the following are PROHIBITED:**

### ❌ DO NOT Use HttpCase for API Tests
```python
# ❌ WRONG - HttpCase runs in read-only transaction
from odoo.tests.common import HttpCase

class TestPropertyAPI(HttpCase):
    def test_create_property(self):
        # This will FAIL because HttpCase doesn't persist data
        response = self.url_open('/api/v1/properties', data=...)
        # OAuth tokens won't be saved
        # Sessions won't work
        # Gets 401 Unauthorized
```

**Why it fails:**
- HttpCase executes in read-only transaction
- INSERT/UPDATE/DELETE are blocked
- OAuth tokens cannot be persisted
- Sessions don't work correctly

**✅ CORRECT - Use curl against real server:**
```bash
# integration_tests/test_properties_api.sh
TOKEN=$(curl -X POST http://localhost:8069/api/v1/auth/token \
  -d '{"client_id":"...", "client_secret":"..."}' | jq -r '.access_token')

curl -X POST http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test Property"}' \
  | jq '.id'  # Should return property ID
```

### ❌ DO NOT Use TransactionCase for Unit Tests
```python
# ❌ WRONG - Too slow, tests business logic with database
from odoo.tests.common import TransactionCase

class TestPropertyValidations(TransactionCase):
    def test_price_must_be_positive(self):
        # This works but is SLOW (uses database)
        with self.assertRaises(ValidationError):
            self.env['real.estate.property'].create({'expected_price': -1000})
```

**✅ CORRECT - Use unittest.mock:**
```python
# ✅ CORRECT - Fast, pure logic test
import unittest
from unittest.mock import Mock

class TestPropertyValidations(unittest.TestCase):
    def test_price_must_be_positive(self):
        # Fast mock test (< 0.001s)
        mock_property = Mock()
        mock_property.expected_price = -1000
        
        with self.assertRaises(ValidationError):
            if mock_property.expected_price < 0:
                raise ValidationError("Price must be positive")
```

### ❌ DO NOT Mix Test Types
```python
# ❌ WRONG - Unit test using Odoo framework
class TestCommissionCalculation(TransactionCase):  # Should be unittest.TestCase
    def test_30_70_split(self):
        # Testing pure logic doesn't need database
        result = calculate_commission_split(1000, 0.30)
        self.assertEqual(result, (300, 700))
```

**✅ CORRECT - Separate concerns:**
```python
# tests/unit/test_commission_unit.py - Pure logic
class TestCommissionCalculation(unittest.TestCase):
    def test_30_70_split(self):
        result = calculate_commission_split(1000, 0.30)
        self.assertEqual(result, (300, 700))

# tests/integration/test_commission_integration.py - Database integration
class TestCommissionDB(TransactionCase):
    def test_commission_persisted_correctly(self):
        commission = self.env['real.estate.commission'].create({...})
        self.assertEqual(commission.state, 'pending')
```

### Summary: 3 Test Types, 3 Different Tools

| Test Type | Tool | Purpose | Speed | Database |
|-----------|------|---------|-------|----------|
| **Unit** | `unittest.mock` | Validate business logic | < 1s | ❌ No |
| **Integration** | `TransactionCase` | Validate ACLs, DB constraints | ~10s | ✅ Yes |
| **E2E API** | `curl scripts` | Validate REST endpoints | ~30s | ✅ Yes (real) |
| **E2E UI** | `Cypress` | Validate user workflows | ~2min | ✅ Yes (real) |

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Observer pattern implementation (ADR-020 + ADR-021) - MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until EventBus and AbstractObserver are implemented

**Test Structure Setup (FIRST - create directories):**
- [X] T015.1 [P] Create tests/unit/ directory structure in 18.0/extra-addons/quicksol_estate/tests/unit/
- [X] T015.2 [P] Create tests/integration/ directory structure in 18.0/extra-addons/quicksol_estate/tests/integration/
- [X] T015.3 [P] Create integration_tests/ directory at repository root with README.md
- [X] T015.4 [P] Create tests/unit/run_unit_tests.py runner script
- [X] T015.5 [P] Update tests/__init__.py to NOT auto-discover unit tests (they run separately)

**Implementation Tasks:**
- [X] T016 Create models/observers/ directory in 18.0/extra-addons/quicksol_estate/models/observers/
- [X] T017 Create EventBus model with emit() and emit_async() methods in 18.0/extra-addons/quicksol_estate/models/event_bus.py
- [X] T018 [P] Create AbstractObserver base class with handle() and can_handle() methods in 18.0/extra-addons/quicksol_estate/models/abstract_observer.py
- [X] T019 Configure ASYNC_EVENTS dict mapping events to queue names in EventBus (18.0/extra-addons/quicksol_estate/models/event_bus.py)
- [X] T020 [P] Create __init__.py to register event_bus and abstract_observer in 18.0/extra-addons/quicksol_estate/models/__init__.py
- [X] T021 Update models/__init__.py to import observers directory in 18.0/extra-addons/quicksol_estate/models/__init__.py

**Tests for Foundational Phase (MANDATORY)**:

**Unit Tests (unittest with mocks - NO Odoo framework):**
- [X] T022 [P] Create tests/unit/test_event_bus_unit.py with EventBus mock tests (emit, singleton pattern)
- [X] T023 [P] Create tests/unit/test_abstract_observer_unit.py with Observer mock tests (can_handle, handle)
- [X] T024 [P] Add mock validation tests for sync/async event routing

**Integration Tests (Odoo TransactionCase - WITH database):**
- [X] T024.1 [P] Create tests/integration/test_event_bus_integration.py with real EventBus tests
- [X] T024.2 [P] Test EventBus.emit() with real observers and database persistence
- [X] T024.3 [P] Test async event queuing with RabbitMQ

**Checkpoint**: EventBus and AbstractObserver tested and working - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Owner Onboards New Real Estate Company (Priority: P1) 🎯 MVP

**Goal**: Enable company owners to set up their company and manage their team with full access to all company data

**Independent Test**: Create company, assign owner user, verify owner can log in and access all company data with full CRUD permissions. Verify multi-tenant isolation (cannot see other companies).

### Test Generation for User Story 1 🤖

**Run `@speckit.tests 005-rbac-user-profiles` to auto-generate all tests below:**

- [X] T024.A [US1] E2E Test: Owner logs in and sees full access → `integration_tests/test_us1_s1_owner_login.sh` ✅ PASSING
- [X] T024.B [US1] E2E Test: Owner can CRUD all company records → `integration_tests/test_us1_s2_owner_crud.sh` ✅ PASSING
- [X] T024.C [US1] E2E Test: Multi-tenancy isolation (no cross-company access) → `integration_tests/test_us1_s3_multitenancy.sh` ✅ PASSING

### Implementation for User Story 1

- [X] T025 [P] [US1] Create group_real_estate_owner definition in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T026 [P] [US1] Add Owner ACL entries (~10 models × CRUD) to 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv
- [X] T027 [P] [US1] Create record rule for Owner to manage own company users in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T028 [US1] Create UserCompanyValidatorObserver to enforce owner can only assign users to their companies in 18.0/extra-addons/quicksol_estate/models/observers/user_company_validator_observer.py
- [X] T029 [US1] Modify res_users.py to emit user.before_create and user.before_write events in 18.0/extra-addons/quicksol_estate/models/res_users.py
- [X] T030 [US1] Update models/observers/__init__.py to register UserCompanyValidatorObserver in 18.0/extra-addons/quicksol_estate/models/observers/__init__.py

### Tests for User Story 1 (MANDATORY)

**Unit Tests (unittest with mocks - validation logic only):**
- [X] T031 [P] [US1] Create tests/unit/test_owner_validations_unit.py with mock tests for owner permissions
- [X] T032 [P] [US1] Add mock tests: owner can create users in own company
- [X] T033 [P] [US1] Add mock tests: owner CANNOT assign users to other companies (ValidationError)
- [X] T034 [P] [US1] Create tests/unit/test_user_company_validator_observer_unit.py
- [X] T035 [P] [US1] Add observer mock tests with validation logic (no database)

**Integration Tests (Odoo TransactionCase - real database + ACLs):**
- [X] T036 [P] [US1] Create tests/integration/test_rbac_owner_integration.py
- [X] T037 [P] [US1] Test owner full CRUD access to all company models
- [X] T038 [P] [US1] Test multi-tenancy: owner cannot see other companies' data

**E2E Tests (Cypress - real UI workflows):**
- [X] T038.1 [P] [US1] Create cypress/e2e/rbac-owner-setup.cy.js
- [X] T038.2 [P] [US1] Test: Owner logs in, creates company, adds team members
- [X] T038.3 [P] [US1] Test: Owner verifies full access to all company features

### E2E Tests for User Story 1

- [X] T036 [P] [US1] Create rbac-owner-onboarding.cy.js with owner creates company scenario in cypress/e2e/rbac-owner-onboarding.cy.js
- [X] T037 [P] [US1] Add owner assigns users test to rbac-owner-onboarding.cy.js
- [X] T038 [P] [US1] Add negative test: owner cannot assign to other companies in rbac-owner-onboarding.cy.js

**Checkpoint**: User Story 1 (Owner Profile) complete - Owner can manage company with full CRUD, users isolated by company ✅
- [ ] T038 [P] [US1] Add multi-tenant isolation test (Company A owner cannot see Company B) to rbac-owner-onboarding.cy.js

**Checkpoint**: Owner profile fully functional - can create company, assign users, manage all data. Multi-tenancy enforced.

---

## Phase 4: User Story 2 - Owner Creates Team Members with Different Roles (Priority: P1)

**Goal**: Enable owners to delegate work by creating user accounts with specialized profiles (Agent, Manager, Receptionist, etc.)

**Independent Test**: Owner creates users with different profiles, each user logs in and sees only what their role permits. Verify role-based filtering works correctly.

### Test Generation for User Story 2 🤖

**Run `@speckit.tests 005-rbac-user-profiles` to auto-generate all tests below:**

- [X] T038.A [US2] E2E Test: Manager creates agent → `integration_tests/test_us2_s1_manager_creates_agent.sh` ✅ PASSING (expected restriction)
- [ ] T038.B [US2] E2E Test: Manager menus → `integration_tests/test_us2_s2_manager_menus.sh` ⚠️ NEEDS REFACTOR (legacy fields)
- [ ] T038.C [US2] E2E Test: Manager assigns properties → `integration_tests/test_us2_s3_manager_assigns_properties.sh` ⚠️ NEEDS REFACTOR
- [ ] T038.D [US2] E2E Test: Manager isolation → `integration_tests/test_us2_s4_manager_isolation.sh` ⚠️ NEEDS REFACTOR

### Implementation for User Story 2

- [X] T039 [P] [US2] Create group_real_estate_director definition (inherits Manager) in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T040 [P] [US2] Create group_real_estate_receptionist definition (inherits User) in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T041 [P] [US2] Create group_real_estate_financial definition (inherits User) in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T042 [P] [US2] Create group_real_estate_legal definition (inherits User) in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T043 [P] [US2] Update group_real_estate_manager comments and implied_ids in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T044 [P] [US2] Update group_real_estate_user comments in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T045 [US2] Add Director ACL entries to ir.model.access.csv (inherit Manager + financial reports)
- [X] T046 [US2] Add Receptionist ACL entries (read properties, CRUD leases/keys) to ir.model.access.csv
- [X] T047 [US2] Add Financial ACL entries (read-only sales, CRUD commissions) to ir.model.access.csv
- [X] T048 [US2] Add Legal ACL entries (read-only contracts) to ir.model.access.csv

### Tests for User Story 2 (MANDATORY)

- [X] T049 [P] [US2] Create test_rbac_director.py with director inherits manager tests in 18.0/extra-addons/quicksol_estate/tests/test_rbac_director.py
- [X] T050 [P] [US2] Create test_rbac_receptionist.py with receptionist lease CRUD tests in 18.0/extra-addons/quicksol_estate/tests/test_rbac_receptionist.py
- [X] T051 [P] [US2] Create test_rbac_financial.py with financial commission access tests in 18.0/extra-addons/quicksol_estate/tests/test_rbac_financial.py
- [X] T052 [P] [US2] Create test_rbac_legal.py with legal read-only contract tests in 18.0/extra-addons/quicksol_estate/tests/test_rbac_legal.py
- [X] T053 [P] [US2] Add negative tests: receptionist cannot edit properties in test_rbac_receptionist.py
- [X] T054 [P] [US2] Add negative tests: legal cannot modify contract financial terms in test_rbac_legal.py

**Checkpoint**: All 5 new profiles (Owner, Director, Receptionist, Financial, Legal) working with correct permissions ✅

---

## Phase 5: User Story 3 - Agent Manages Their Own Properties and Leads (Priority: P1)

**Goal**: Enable agents to create properties (auto-assigned to them), view only their properties, and manage their leads

**Independent Test**: Agent creates properties, verify they can only see their own properties. Agent cannot see other agents' properties.

### Test Generation for User Story 3 🤖

**Run `@speckit.tests 005-rbac-user-profiles` to auto-generate all tests below:**

- [ ] T054.A [US3] E2E Test: Agent assigned properties → `integration_tests/test_us3_s1_agent_assigned_properties.sh` ⚠️ NEEDS REFACTOR
- [ ] T054.B [US3] E2E Test: Agent auto-assignment → `integration_tests/test_us3_s2_agent_auto_assignment.sh` ⚠️ NEEDS REFACTOR
- [ ] T054.C [US3] E2E Test: Agent own leads → `integration_tests/test_us3_s3_agent_own_leads.sh` ⚠️ NEEDS REFACTOR
- [X] T054.D [US3] E2E Test: Cannot modify others → `integration_tests/test_us3_s4_agent_cannot_modify_others.sh` ✅ PASSING
- [X] T054.E [US3] E2E Test: Multi-company isolation → `integration_tests/test_us3_s5_agent_company_isolation.sh` ✅ PASSING (commit 761401c)

### Implementation for User Story 3

- [X] T055 [P] [US3] Update group_real_estate_agent comments in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T056 [P] [US3] Add Agent ACL entries (CRUD own properties/leads) to 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv
- [X] T057 [P] [US3] Create record rule: Agent sees properties where agent_id.user_id = user.id in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T058 [P] [US3] Create record rule: Agent sees properties in assignment_ids in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T059 [P] [US3] Create record rule: Agent sees own leads in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T060 [P] [US3] Create record rule: Agent sees own assignments in 18.0/extra-addons/quicksol_estate/security/record_rules.xml

### Tests for User Story 3 (MANDATORY)

- [X] T061 [P] [US3] Create test_rbac_agent.py with agent creates property test in 18.0/extra-addons/quicksol_estate/tests/test_rbac_agent.py
- [X] T062 [P] [US3] Add agent sees only own properties test to test_rbac_agent.py
- [X] T063 [P] [US3] Add agent cannot modify other agent's property test to test_rbac_agent.py
- [X] T064 [P] [US3] Add agent manages own leads test to test_rbac_agent.py

### E2E Tests for User Story 3

- [X] T065 [P] [US3] Create rbac-agent-property-access.cy.js with agent creates property scenario in cypress/e2e/rbac-agent-property-access.cy.js
- [X] T066 [P] [US3] Add agent sees only own properties test to rbac-agent-property-access.cy.js
- [X] T067 [P] [US3] Add agent isolation test (Agent A cannot see Agent B properties) to rbac-agent-property-access.cy.js

**Checkpoint**: Agent profile fully functional - can create properties, sees only own records ✅

---

## Phase 6: User Story 4 - Manager Oversees All Company Operations (Priority: P2)

**Goal**: Enable managers to view all company data, reassign leads, and generate reports

**Independent Test**: Manager creates properties/leads for various agents, verify manager sees all company data. Manager can reassign leads.

### Implementation for User Story 4

- [ ] T068 [P] [US4] Add Manager ACL entries (CRUD all models except users) to 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv
- [ ] T069 [P] [US4] Create record rule: Manager sees all company properties in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [ ] T070 [P] [US4] Create record rule: Manager sees all company leads in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [ ] T071 [P] [US4] Create record rule: Manager sees all company contracts in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [ ] T072 [P] [US4] Create record rule: Manager sees all company agents in 18.0/extra-addons/quicksol_estate/security/record_rules.xml

### Tests for User Story 4 (MANDATORY)

- [X] T073 [P] [US4] Create test_rbac_manager.py with manager sees all company data test in 18.0/extra-addons/quicksol_estate/tests/test_rbac_manager.py
- [X] T074 [P] [US4] Add manager can reassign leads test to test_rbac_manager.py
- [X] T075 [P] [US4] Add manager cannot create users test (negative) to test_rbac_manager.py
- [X] T076 [P] [US4] Add multi-tenant isolation test (Manager Company A cannot see Company B) to test_rbac_manager.py

### E2E Tests for User Story 4

- [X] T077 [P] [US4] Create rbac-manager-oversight.cy.js with manager views all data scenario in cypress/e2e/rbac-manager-oversight.cy.js
- [X] T078 [P] [US4] Add manager reassigns leads test to rbac-manager-oversight.cy.js

**Checkpoint**: Manager profile fully functional - can oversee all company operations

---

## Phase 7: User Story 5 - Prospector Creates Properties with Commission Split (Priority: P2)

**Goal**: Enable prospectors to register new properties and earn commission split with selling agent

**Independent Test**: Prospector creates property, verify prospector_id auto-assigned. Manager assigns selling agent, verify commission split calculation.

### Implementation for User Story 5

- [X] T079 [P] [US5] Create group_real_estate_prospector definition in 18.0/extra-addons/quicksol_estate/security/groups.xml
- [X] T080 [P] [US5] Add Prospector ACL entries (create properties, read own) to 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv
- [X] T081 [P] [US5] Create record rule: Prospector sees only prospector_id.user_id = user.id in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T082 [US5] Add prospector_id field (Many2one to real.estate.agent) to property model in 18.0/extra-addons/quicksol_estate/models/property.py
- [X] T083 [US5] Modify property.py to emit property.before_create event in 18.0/extra-addons/quicksol_estate/models/property.py
- [X] T084 [US5] Modify property.py to emit property.created event in 18.0/extra-addons/quicksol_estate/models/property.py
- [X] T085 [US5] Create ProspectorAutoAssignObserver to auto-populate prospector_id in 18.0/extra-addons/quicksol_estate/models/observers/prospector_auto_assign_observer.py
- [X] T086 [US5] Create CommissionSplitObserver to calculate split when sale completes in 18.0/extra-addons/quicksol_estate/models/observers/commission_split_observer.py
- [X] T087 [US5] Add calculate_split_commission() method to commission_rule.py in 18.0/extra-addons/quicksol_estate/models/commission_rule.py
- [X] T088 [US5] Create system parameter quicksol_estate.prospector_commission_percentage (default 0.30) via XML data in 18.0/extra-addons/quicksol_estate/data/system_parameters.xml (Note: Ensure this file is registered in __manifest__.py 'data' section)
- [X] T088.1 [US5] Configure audit log tracking for prospector_id field changes in property model (FR-071 requirement) in 18.0/extra-addons/quicksol_estate/models/property.py
- [X] T089 [US5] Update models/observers/__init__.py to register ProspectorAutoAssignObserver and CommissionSplitObserver in 18.0/extra-addons/quicksol_estate/models/observers/__init__.py

### Tests for User Story 5 (MANDATORY)

- [X] T090 [P] [US5] Create test_rbac_prospector.py with prospector creates property test in 18.0/extra-addons/quicksol_estate/tests/test_rbac_prospector.py
- [X] T091 [P] [US5] Add prospector_id auto-assigned test to test_rbac_prospector.py
- [X] T092 [P] [US5] Add prospector sees only own properties test to test_rbac_prospector.py
- [X] T093 [P] [US5] Create test_commission_split.py with calculate_split_commission() tests in 18.0/extra-addons/quicksol_estate/tests/test_commission_split.py
- [X] T094 [P] [US5] Add commission split 30/70 default test to test_commission_split.py
- [X] T095 [P] [US5] Add commission split configurable percentage test to test_commission_split.py
- [X] T096 [P] [US5] Create test_prospector_auto_assign_observer.py in 18.0/extra-addons/quicksol_estate/tests/observers/test_prospector_auto_assign_observer.py
- [X] T097 [P] [US5] Create test_commission_split_observer.py in 18.0/extra-addons/quicksol_estate/tests/observers/test_commission_split_observer.py
- [X] T098 [P] [US5] Add observer handles event with force_sync=True tests in test_prospector_auto_assign_observer.py
- [X] T099 [P] [US5] Add observer creates commission transactions test in test_commission_split_observer.py

### E2E Tests for User Story 5

- [X] T100 [P] [US5] Create rbac-prospector-commission.cy.js with prospector registers property scenario in cypress/e2e/rbac-prospector-commission.cy.js
- [X] T101 [P] [US5] Add manager assigns selling agent test to rbac-prospector-commission.cy.js
- [X] T102 [P] [US5] Add commission split calculation test (30% prospector, 70% agent) to rbac-prospector-commission.cy.js

**Checkpoint**: Prospector profile fully functional - commission split working correctly

---

## Phase 8: User Story 6 - Receptionist Manages Contracts and Keys (Priority: P3)

**Goal**: Enable receptionists to handle administrative tasks like creating contracts and managing keys

**Independent Test**: Receptionist creates lease contract, manages keys, verify they can view all properties but only edit contracts/keys.

### Implementation for User Story 6

- [X] T103 [P] [US6] Create record rule: Receptionist read all company properties in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T104 [P] [US6] Create record rule: Receptionist CRUD leases in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T104.1 [P] [US6] Add Receptionist ACL entries for real.estate.key model (FR-040 requirement) - NOTE: Verify if model exists; if not, document as future scope in 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv
- [X] T105 [P] [US6] Create record rule: Receptionist CRUD keys in 18.0/extra-addons/quicksol_estate/security/record_rules.xml

### Tests for User Story 6 (MANDATORY)

- [X] T106 [P] [US6] Add receptionist creates lease test to test_rbac_receptionist.py
- [X] T107 [P] [US6] Add receptionist views all properties (read-only) test to test_rbac_receptionist.py
- [X] T108 [P] [US6] Add receptionist cannot edit property details test (negative) to test_rbac_receptionist.py
- [X] T109 [P] [US6] Add receptionist cannot modify commissions test (negative) to test_rbac_receptionist.py

**Checkpoint**: Receptionist profile fully functional - can manage contracts/keys, read properties

---

## Phase 9: User Story 7 - Financial Staff Processes Commissions (Priority: P3)

**Goal**: Enable financial staff to calculate, review, and process commission payments

**Independent Test**: Financial user views commissions, marks as paid, generates reports. Verify they cannot edit properties.

### Implementation for User Story 7

- [X] T110 [P] [US7] Create record rule: Financial read all sales/leases in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T111 [P] [US7] Create record rule: Financial CRUD commissions in 18.0/extra-addons/quicksol_estate/security/record_rules.xml

### Tests for User Story 7 (MANDATORY)

- [X] T112 [P] [US7] Add financial views all commissions test to test_rbac_financial.py
- [X] T113 [P] [US7] Add financial marks commission as paid test to test_rbac_financial.py
- [X] T114 [P] [US7] Add financial generates commission report test to test_rbac_financial.py
- [X] T115 [P] [US7] Add financial cannot edit properties test (negative) to test_rbac_financial.py

**Checkpoint**: Financial profile fully functional - can process commissions, view sales data

---

## Phase 10: User Story 8 - Legal Reviews Contracts (Priority: P3)

**Goal**: Enable legal staff to review contracts for compliance and add legal opinions without modifying financial terms

**Independent Test**: Legal user views contracts, adds legal notes, verify financial fields are read-only.

### Implementation for User Story 8

- [X] T116 [P] [US8] Create record rule: Legal read all contracts in 18.0/extra-addons/quicksol_estate/security/record_rules.xml

### Tests for User Story 8 (MANDATORY)

- [X] T117 [P] [US8] Add legal views all contracts test to test_rbac_legal.py
- [X] T118 [P] [US8] Add legal adds opinion/note test to test_rbac_legal.py
- [X] T119 [P] [US8] Add legal cannot modify contract value test (negative) to test_rbac_legal.py
- [X] T120 [P] [US8] Add legal cannot modify property details test (negative) to test_rbac_legal.py

**Checkpoint**: Legal profile fully functional - can review contracts, add notes

---

## Phase 11: User Story 9 - Director Views Executive Dashboards (Priority: P3)

**Goal**: Enable directors to access high-level business intelligence and executive reports

**Independent Test**: Director views executive dashboards, generates BI reports, verify they have manager permissions plus financial insights.

### Implementation for User Story 9

- [X] T121 [P] [US9] Add Director inherits Manager test to test_rbac_director.py
- [X] T122 [P] [US9] Add Director views financial reports test to test_rbac_director.py
- [X] T123 [P] [US9] Add Director accesses BI dashboards test to test_rbac_director.py

**Checkpoint**: Director profile fully functional - executive reporting access

---

## Phase 12: User Story 10 - Portal User Views Their Own Contracts (Priority: P3)

**Goal**: Enable clients to access portal to view their contracts and upload documents

**Independent Test**: Portal user logs in, views only contracts where partner_id matches, cannot see other clients' data.

### Implementation for User Story 10

- [X] T124 [P] [US10] Create record rule: Portal user sees only partner_id = user.partner_id contracts in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T125 [P] [US10] Create record rule: Portal user sees only own assignments in 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T126 [P] [US10] Add Portal User ACL entries (read-only own contracts) to 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv

### Tests for User Story 10 (MANDATORY)

- [X] T127 [P] [US10] Create test_rbac_portal.py with portal user sees own contracts test in 18.0/extra-addons/quicksol_estate/tests/test_rbac_portal.py
- [X] T128 [P] [US10] Add portal user uploads document test to test_rbac_portal.py
- [X] T129 [P] [US10] Add portal user cannot see other clients test (negative) to test_rbac_portal.py
- [X] T130 [P] [US10] Add portal user views public property listings test to test_rbac_portal.py

**Portal Implementation Completed**: ✅ Partner relationship fields added to Sale, Tenant, and PropertyOwner models. Record rules enabled and tests passing.

### E2E Tests for User Story 10

- [ ] T131 [P] [US10] Create rbac-portal-user-isolation.cy.js with portal user login scenario in cypress/e2e/rbac-portal-user-isolation.cy.js
- [ ] T132 [P] [US10] Add portal user views own contracts test to rbac-portal-user-isolation.cy.js
- [ ] T133 [P] [US10] Add portal user isolation test (cannot see other clients) to rbac-portal-user-isolation.cy.js

**Checkpoint**: All 10 user stories implemented and independently testable

---

## Phase 13: Cross-Cutting Concerns & Integration Tests

**Purpose**: Security audit observer, multi-tenancy tests, integration scenarios

- [X] T134 [P] Create SecurityGroupAuditObserver for LGPD compliance logging in 18.0/extra-addons/quicksol_estate/models/observers/security_group_audit_observer.py
- [X] T135 [P] Modify res_users.py to emit user.updated event when groups change in 18.0/extra-addons/quicksol_estate/models/res_users.py
- [X] T136 [P] Update models/observers/__init__.py to register SecurityGroupAuditObserver in 18.0/extra-addons/quicksol_estate/models/observers/__init__.py
- [X] T137 [P] Create test_security_group_audit_observer.py in 18.0/extra-addons/quicksol_estate/tests/observers/test_security_group_audit_observer.py
- [X] T138 [P] Create test_rbac_multi_tenancy.py with cross-company isolation tests in 18.0/extra-addons/quicksol_estate/tests/test_rbac_multi_tenancy.py
- [X] T139 [P] Add Company A user cannot see Company B data test to test_rbac_multi_tenancy.py
- [X] T140 [P] Add multi-company user sees combined data test to test_rbac_multi_tenancy.py
- [ ] T141 [P] Create rbac-multi-tenancy-isolation.cy.js with cross-company tests in cypress/e2e/rbac-multi-tenancy-isolation.cy.js

**Checkpoint**: Security audit working, multi-tenancy verified across all profiles

---

## Phase 14: Polish & Documentation

**Purpose**: Final documentation, README updates, deployment validation

- [X] T142 [P] Update README.md with RBAC system overview in 18.0/extra-addons/quicksol_estate/README.md
- [X] T143 [P] Add RBAC profiles table to README.md (9 profiles with permissions summary)
- [X] T144 [P] Create default_groups.xml with demo data for each profile in 18.0/extra-addons/quicksol_estate/data/default_groups.xml
- [X] T145 Run pytest coverage report and verify ≥80% coverage target
- [X] T146 Run all Cypress E2E tests and verify all scenarios pass
- [X] T147 [P] Update OpenAPI/Swap docs with async event endpoints (if applicable) in docs/openapi/
- [X] T148 [P] Update Postman collection with RBAC testing requests in docs/postman/
- [X] T149 Validate quickstart.md implementation steps against actual code
- [X] T150 Start all infrastructure services (docker-compose up -d) and verify healthchecks
- [X] T151 Access Flower UI (localhost:5555) and verify 3 workers connected
- [X] T152 Access RabbitMQ UI (localhost:15672) and verify 4 queues created
- [X] T153 Create deployment checklist document in docs/deployment-rbac-checklist.md

**Checkpoint**: All documentation complete, coverage verified, deployment validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T015) completion - BLOCKS all user stories
- **User Stories (Phase 3-12)**: All depend on Foundational phase (T016-T024) completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order: US1 → US2 → US3 (P1), then US4 → US5 (P2), then US6-10 (P3)
- **Cross-Cutting (Phase 13)**: Depends on all user stories being complete
- **Polish (Phase 14)**: Depends on all previous phases

### User Story Dependencies

**No inter-story dependencies** - All user stories are independently implementable after Foundational phase:

- **User Story 1 (Owner)**: Can start after T024 ✅ - No dependencies on other stories
- **User Story 2 (Team Members)**: Can start after T024 ✅ - Independent (just creates new groups)
- **User Story 3 (Agent)**: Can start after T024 ✅ - Independent (record rules for agents)
- **User Story 4 (Manager)**: Can start after T024 ✅ - Independent (manager record rules)
- **User Story 5 (Prospector)**: Can start after T024 ✅ - Independent (prospector_id field + observers)
- **User Story 6 (Receptionist)**: Can start after T024 ✅ - Independent (receptionist record rules)
- **User Story 7 (Financial)**: Can start after T024 ✅ - Independent (commission record rules)
- **User Story 8 (Legal)**: Can start after T024 ✅ - Independent (legal read-only rules)
- **User Story 9 (Director)**: Can start after T024 ✅ - Independent (inherits manager)
- **User Story 10 (Portal)**: Can start after T024 ✅ - Independent (portal partner filtering)

### Within Each User Story

- Tests SHOULD be written alongside implementation (TDD approach recommended but not enforced)
- Groups before ACLs before record rules
- Models/fields before observers
- Observer registration after observer implementation
- Core implementation before integration tests
- Story complete before E2E tests

### Parallel Opportunities

**Phase 1 (Setup)**: Can run in parallel:
- T002-T006 (docker-compose services) ✅
- T007-T009 (.env updates) ✅
- T010-T013 (Celery worker files) ✅

**Phase 2 (Foundational)**: Can run in parallel:
- T017 (EventBus) + T018 (AbstractObserver) ✅
- T022-T024 (All foundational tests) ✅

**User Story 3 (Agent)**: Can run in parallel:
- T055-T060 (All agent record rules and ACLs) ✅
- T061-T064 (All agent tests) ✅
- T065-T067 (All agent E2E tests) ✅

**User Story 5 (Prospector)**: Can run in parallel:
- T079-T081 (Prospector groups/ACLs/rules) ✅
- T090-T099 (All prospector and commission tests) ✅
- T100-T102 (All prospector E2E tests) ✅

**Cross-Cutting (Phase 13)**: Can run in parallel:
- T134-T137 (SecurityGroupAuditObserver + tests) ✅
- T138-T141 (Multi-tenancy tests) ✅

**Polish (Phase 14)**: Can run in parallel:
- T142-T144 (Documentation updates) ✅
- T147-T148 (API docs updates) ✅

### Critical Path

```
Setup (T001-T015, ~3 hours)
  ↓
Foundational (T016-T024, ~4 hours) ← BLOCKING
  ↓
┌─────────────────────────────────────────┐
│ All User Stories in Parallel (optional) │
├─────────────────────────────────────────┤
│ US1 (T025-T038, ~6 hours)              │
│ US2 (T039-T054, ~4 hours)              │
│ US3 (T055-T067, ~5 hours)              │
│ US4 (T068-T078, ~4 hours)              │
│ US5 (T079-T102, ~8 hours) ← Most complex│
│ US6 (T103-T109, ~3 hours)              │
│ US7 (T110-T115, ~3 hours)              │
│ US8 (T116-T120, ~2 hours)              │
│ US9 (T121-T123, ~2 hours)              │
│ US10 (T124-T133, ~4 hours)             │
└─────────────────────────────────────────┘
  ↓
Cross-Cutting (T134-T141, ~3 hours)
  ↓
Polish (T142-T153, ~4 hours)
```

**Total Sequential Estimate**: ~55 hours (1.5 weeks solo)  
**Total Parallel Estimate** (3 developers): ~22 hours (3 days with team)

---

## Parallel Example: User Story 5 (Prospector)

If working with multiple developers on User Story 5:

```bash
# Developer 1: Security setup (groups, ACLs, rules)
T079 → T080 → T081

# Developer 2: Observer implementation
T085 → T086 → T087 → T089

# Developer 3: Model changes and tests
T082 → T083 → T084 → T088 → T088.1 → T090-T099

# Developer 4: E2E tests
T100 → T101 → T102

# All merge once complete
```

**Estimated time with 4 developers**: 2-3 hours (vs 8 hours solo)

---

## MVP Scope Recommendation

**Suggested MVP**: User Story 1 + User Story 3 + User Story 5 (Owner, Agent, Prospector)

**Rationale**:
- **US1 (Owner)**: Required foundation - enables company setup and team management
- **US3 (Agent)**: Core revenue-generating workflow - agents create/manage properties
- **US5 (Prospector)**: Key differentiator - commission split demonstrates event-driven architecture

**Tasks for MVP**: T001-T024 (Infrastructure) + T025-T038 (US1) + T055-T067 (US3) + T079-T102 (US5)  
**MVP Estimate**: ~26 hours solo, ~13 hours with 2 developers (includes T088.1 audit tracking)

**Post-MVP Delivery**:
- **Phase 2a**: US2 (Team Members) + US4 (Manager) - Operational coordination (12 hours)
- **Phase 2b**: US6-10 (Specialized Roles) - Advanced workflows (18 hours)

---

## Implementation Strategy

**Approach**: Incremental delivery by user story priority

1. **Sprint 1** (Week 1): Infrastructure + US1 + US3 (Owner + Agent MVP)
2. **Sprint 2** (Week 2): US2 + US4 + US5 (Team collaboration + Commission split)
3. **Sprint 3** (Week 3): US6-10 (Specialized roles) + Cross-cutting + Polish

**Acceptance Criteria per Sprint**:
- End of Sprint 1: Owners can onboard companies, agents can manage properties ✅
- End of Sprint 2: Full team collaboration, commission split working ✅
- End of Sprint 3: All 9 profiles functional, 80% coverage, production-ready ✅

---

## Validation Checklist

Before marking feature complete:

**Code Quality:**
- [ ] Linting passes: `./lint.sh` (0 errors/warnings)
- [ ] All 160+ tasks completed and marked [X]

**Unit Tests (Pure Logic - NO Database):**
- [ ] All unit tests pass: `python3 tests/unit/run_unit_tests.py`
- [ ] 100% coverage of validations (required, constraints, compute)
- [ ] Execution time < 5 seconds total
- [ ] No database connection in unit tests

**Integration Tests (Odoo Framework + Database):**
- [ ] Integration tests pass: `docker compose run --rm odoo odoo --test-enable --test-tags=quicksol_estate`
- [ ] All ACL rules tested with TransactionCase
- [ ] Multi-tenancy isolation verified
- [ ] Record rules enforce company boundaries

**E2E Tests (Real Services):**
- [ ] Cypress UI tests pass: `npm run cypress:run`
- [ ] All API curl tests pass: `bash integration_tests/test_*.sh`
- [ ] Tests run against real database (not test transactions)
- [ ] OAuth authentication working correctly

**Infrastructure:**
- [ ] RabbitMQ + 3 Celery workers + Flower healthy (`docker-compose ps`)
- [ ] Flower UI accessible at http://localhost:5555
- [ ] RabbitMQ UI shows 4 queues (security_events, commission_events, audit_events, notification_events)
- [ ] All observers tested with force_sync=True
- [ ] Async events return task_id correctly

**Security & Data:**
- [ ] All 9 security groups visible in Odoo UI
- [ ] All record rules enforce multi-tenancy (Company A isolation verified)
- [ ] No .sudo() calls in security-critical code
- [ ] Commission split calculator tested with 30/70 default
- [ ] Migration scripts tested on staging database

**Documentation:**
- [ ] quickstart.md validated against actual implementation
- [ ] ADR-020 and ADR-021 referenced in code comments
- [ ] API documentation updated (if applicable)
- [ ] README.md includes test execution instructions

**⚠️ CRITICAL VERIFICATION:**
- [ ] ❌ NO HttpCase tests present (prohibited by ADR-002)
- [ ] ❌ NO manual testing documented (only automated tests)
- [ ] ✅ Unit tests use unittest.mock (no Odoo framework)
- [ ] ✅ API tests use curl scripts (not HttpCase)
- [ ] ✅ All 3 test types present (linting + unit + E2E)

---

**Total Tasks**: 155 tasks (153 original + 2 remediation: T088.1 audit log, T104.1 keys ACL)  
**Estimated Effort**: 56 hours (solo) / 23 hours (team of 3)  
**Coverage Target**: ≥80% (ADR-003 compliant)  
**Branch**: `005-rbac-user-profiles`  
**Target Version**: `18.0.2.0.0`
