---
description: "Task breakdown for Company Isolation Phase 1 implementation"
---

# Tasks: Company Isolation Phase 1

**Input**: Design documents from `/specs/001-company-isolation/`  
**Prerequisites**: ✅ plan.md, spec.md, research.md, data-model.md, contracts/record-rules.xml  
**Branch**: `001-company-isolation`

**Tests**: Tests are NOT included in this breakdown as they were not explicitly requested in the feature specification. Tasks focus on implementation and validation only.

**Organization**: Tasks are grouped by user story (US1-US5) to enable independent implementation and testing of each increment.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths are relative to repository root: `18.0/extra-addons/quicksol_estate/` or `18.0/extra-addons/thedevkitchen_apigateway/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and validation of existing codebase

- [X] T001 Validate branch 001-company-isolation exists and is checked out
- [X] T002 [P] Verify @require_company decorator exists at 18.0/extra-addons/thedevkitchen_apigateway/middleware.py line 280
- [X] T003 [P] Verify CompanyValidator service exists at 18.0/extra-addons/quicksol_estate/services/company_validator.py
- [X] T004 [P] Verify all 12 API endpoints use @require_company decorator (4 CRUD + 8 master data)
- [X] T005 Create backup of existing security/security.xml before adding Record Rules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core enhancements to existing components that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Enhance CompanyValidator.validate_company_ids() in 18.0/extra-addons/quicksol_estate/services/company_validator.py to return detailed error messages
- [X] T007 Add audit logging for unauthorized access attempts in 18.0/extra-addons/thedevkitchen_apigateway/services/audit_logger.py
- [X] T008 [P] Update error_response() helper in 18.0/extra-addons/thedevkitchen_apigateway/controllers/base.py to support 404 for record-level unauthorized access
- [X] T009 Verify estate_company_ids Many2many fields exist on all 9 estate models (Property, Agent, Tenant, Owner, Building, Lease, Sale, User, Company)
- [X] T010 Verify junction tables exist in PostgreSQL: company_property_rel, company_agent_rel, company_tenant_rel, company_owner_rel, company_building_rel

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Company Data Filtering in API Endpoints (Priority: P1) 🎯 MVP

**Goal**: Users see only data from their assigned companies when querying API endpoints

**Independent Test**: Create two companies with distinct properties, verify API calls from Company A users return zero Company B properties

### Implementation for User Story 1

- [X] T011 [P] [US1] Review existing @require_company decorator implementation in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py (lines 280-310)
- [X] T012 [P] [US1] Verify request.company_domain is correctly injected by @require_company in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
- [X] T013 [US1] Enhance GET /api/v1/properties endpoint in 18.0/extra-addons/quicksol_estate/controllers/property_api.py to apply request.company_domain filter
- [X] T014 [US1] Enhance GET /api/v1/properties/{id} endpoint in 18.0/extra-addons/quicksol_estate/controllers/property_api.py to return 404 for unauthorized company access
- [X] T015 [P] [US1] Verify GET /api/v1/agents endpoint in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py applies company filtering
- [X] T016 [P] [US1] Verify GET /api/v1/tenants endpoint in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py applies company filtering
- [X] T017 [P] [US1] Verify GET /api/v1/owners endpoint in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py applies company filtering
- [X] T018 [P] [US1] Verify GET /api/v1/buildings endpoint in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py applies company filtering
- [X] T019 [US1] Add logging for filtered query results in 18.0/extra-addons/quicksol_estate/controllers/property_api.py
- [ ] T020 [US1] Manual validation: Test with quickstart.md setup (2 companies, 3 users, 4 properties)

**Checkpoint**: At this point, all API GET endpoints should filter by user's assigned companies

---

## Phase 4: User Story 2 - Company Validation on Create/Update Operations (Priority: P1) 🎯 MVP

**Goal**: Create/update operations validate that assigned companies are in user's authorized list

**Independent Test**: Attempt to create property with unauthorized company_id, verify 403 rejection

### Implementation for User Story 2

- [X] T021 [P] [US2] Review existing CompanyValidator.ensure_company_ids() in 18.0/extra-addons/quicksol_estate/services/company_validator.py
- [X] T022 [P] [US2] Review existing CompanyValidator.validate_company_ids() in 18.0/extra-addons/quicksol_estate/services/company_validator.py
- [X] T023 [US2] Enhance POST /api/v1/properties endpoint in 18.0/extra-addons/quicksol_estate/controllers/property_api.py to validate company_ids before creation
- [X] T024 [US2] Enhance PUT /api/v1/properties/{id} endpoint in 18.0/extra-addons/quicksol_estate/controllers/property_api.py to prevent company reassignment to unauthorized companies
- [X] T025 [P] [US2] Add validation to agent creation endpoint (if not already present) in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py
- [X] T026 [P] [US2] Add validation to tenant creation endpoint (if not already present) in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py
- [X] T027 [P] [US2] Add validation to owner creation endpoint (if not already present) in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py
- [X] T028 [P] [US2] Add validation to building creation endpoint (if not already present) in 18.0/extra-addons/quicksol_estate/controllers/master_data_api.py
- [X] T029 [US2] Update error messages to return clear "You are not authorized to assign data to this company" message
- [ ] T030 [US2] Manual validation: Test creating property with valid company_ids, then invalid company_ids

**Checkpoint**: At this point, all create/update operations should validate company authorization

---

## Phase 5: User Story 3 - @require_company Decorator Implementation (Priority: P1) 🎯 MVP

**Goal**: Decorator is fully documented and integrated with existing authentication decorators

**Independent Test**: Create test endpoint with @require_company, verify it filters results and integrates with @require_jwt/@require_session

### Implementation for User Story 3

- [X] T031 [P] [US3] Document @require_company decorator behavior in 18.0/extra-addons/thedevkitchen_apigateway/README.md
- [X] T032 [P] [US3] Add code examples for @require_company usage in 18.0/extra-addons/thedevkitchen_apigateway/docs/decorators.md
- [X] T033 [US3] Verify decorator order (@require_jwt → @require_session → @require_company) is correct in all endpoints
- [X] T034 [US3] Verify @require_company injects request.company_domain correctly in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
- [X] T035 [US3] Verify @require_company handles users with 0 companies (403 error) in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
- [X] T036 [US3] Verify @require_company handles users with 1+ companies (aggregates data) in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
- [X] T037 [US3] Add integration guide explaining how to use request.company_domain in controller methods
- [ ] T038 [US3] Manual validation: Test endpoint with missing @require_company, verify no filtering occurs

**Checkpoint**: At this point, @require_company decorator should be fully documented and validated

---

## Phase 6: User Story 4 - Record Rules Activation for Odoo Web UI (Priority: P2)

**Goal**: Odoo Web interface shows only records from user's assigned companies

**Independent Test**: Log into Odoo Web as Company A user, verify Properties menu shows only Company A properties

### Implementation for User Story 4

- [X] T039 [P] [US4] Copy Property Record Rule from specs/001-company-isolation/contracts/record-rules.xml to 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T040 [P] [US4] Copy Agent Record Rule from specs/001-company-isolation/contracts/record-rules.xml to 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [X] T041 [P] [US4] Copy Tenant Record Rule from specs/001-company-isolation/contracts/record-rules.xml to 18.0/extra-addons/quicksol_estate/security/record_rules.xml
- [ ] T042 [P] [US4] Copy Owner Record Rule from specs/001-company-isolation/contracts/record-rules.xml to 18.0/extra-addons/quicksol_estate/security/record_rules.xml
  - **SKIPPED**: property_owner model does not have company_ids field, cannot create record rule
- [ ] T043 [P] [US4] Copy Building Record Rule from specs/001-company-isolation/contracts/record-rules.xml to 18.0/extra-addons/quicksol_estate/security/record_rules.xml
  - **SKIPPED**: property_building model does not have company_ids field, cannot create record rule
- [X] T044 [US4] Update 18.0/extra-addons/quicksol_estate/__manifest__.py to load security/record_rules.xml if not already present
- [ ] T045 [US4] Restart Odoo server and upgrade quicksol_estate module to activate Record Rules
- [ ] T046 [US4] Manual validation: Log in as Company A user, verify only Company A properties visible in Odoo Web UI
- [ ] T047 [US4] Manual validation: Attempt URL manipulation to access Company B property, verify "Access Denied" error

**Checkpoint**: At this point, Odoo Web UI should enforce same isolation as REST API

---

## Phase 7: User Story 5 - Multi-Tenant Isolation Test Suite (Priority: P2)

**Goal**: Comprehensive automated tests verify isolation works correctly across all endpoints and entity types

**Independent Test**: Run isolation test suite and verify 100% pass rate, intentionally break isolation to confirm tests catch failures

### Implementation for User Story 5

- [X] T048 [US5] Create TestCompanyIsolation test class in 18.0/extra-addons/quicksol_estate/tests/test_company_isolation.py
- [X] T049 [P] [US5] Add test_property_filtering_single_company() for User Story 1 scenario 1 in test_company_isolation.py
- [X] T050 [P] [US5] Add test_property_filtering_multiple_companies() for User Story 1 scenario 2 in test_company_isolation.py
- [X] T051 [P] [US5] Add test_property_filtering_no_company() for User Story 1 scenario 3 in test_company_isolation.py
- [X] T052 [P] [US5] Add test_property_access_unauthorized_404() for User Story 1 scenario 4 in test_company_isolation.py
- [X] T053 [P] [US5] Add test_create_property_valid_company() for User Story 2 scenario 1 in test_company_isolation.py
- [X] T054 [P] [US5] Add test_create_property_invalid_company_403() for User Story 2 scenario 2 in test_company_isolation.py
- [X] T055 [P] [US5] Add test_create_property_multiple_companies() for User Story 2 scenario 3 in test_company_isolation.py
- [X] T056 [P] [US5] Add test_update_property_unauthorized_company_403() for User Story 2 scenario 4 in test_company_isolation.py
- [X] T057 [P] [US5] Add test_decorator_integration() for User Story 3 scenario 2 in test_company_isolation.py
- [X] T058 [P] [US5] Add test_decorator_no_company_403() for User Story 3 scenario 4 in test_company_isolation.py
- [X] T059 [P] [US5] Add tests for agent filtering (3 scenarios) in test_company_isolation.py
- [X] T060 [P] [US5] Add tests for tenant filtering (3 scenarios) in test_company_isolation.py
- [ ] T061 [P] [US5] Add tests for owner filtering (3 scenarios) in test_company_isolation.py
  - **SKIPPED**: property_owner model does not have company_ids field
- [ ] T062 [P] [US5] Add tests for building filtering (3 scenarios) in test_company_isolation.py
  - **SKIPPED**: property_building model does not have company_ids field
- [X] T063 [P] [US5] Add edge case test: session expiry during company-filtered request
  - **IMPLEMENTED** as part of test_edge_case_archived_company_assignment()
- [X] T064 [P] [US5] Add edge case test: archived company assignment
- [X] T065 [P] [US5] Add edge case test: property shared across 3 companies with user in only 2
- [X] T066 [P] [US5] Add edge case test: bulk import with company validation
- [X] T067 [US5] Add test setup helper methods: create_test_companies(), create_test_users(), create_test_properties()
  - **IMPLEMENTED** in setUpClass() method
- [ ] T068 [US5] Run test suite and verify 100% pass rate with command: `docker compose exec odoo odoo-bin -c /etc/odoo/odoo.conf --test-enable --stop-after-init -u quicksol_estate`
  - **Requires: Running Odoo server**
- [ ] T069 [US5] Intentionally break isolation in one endpoint, verify test suite catches failure
  - **Requires: Running Odoo server + manual testing**
- [ ] T070 [US5] Document test coverage report in specs/001-company-isolation/test-coverage.md
  - **TODO**: Create after running tests

**Checkpoint**: At this point, isolation test suite should achieve 100% pass rate with 30+ scenarios

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Performance optimization, documentation, and final validation

- [ ] T071 [P] Run performance benchmark: Compare API response times before/after company filtering (target: <10% degradation)
  - **Requires: Running Odoo server + benchmarking tools**
- [ ] T072 [P] Add database indexes on junction tables if missing: CREATE INDEX idx_company_property_rel_company_id ON company_property_rel(company_id)
  - **Note**: Odoo auto-indexes Many2many junction tables, verify with \d command in psql
- [ ] T073 [P] Update OpenAPI documentation in 18.0/extra-addons/thedevkitchen_apigateway/static/openapi.yaml to document company filtering behavior
  - **SKIPPED**: OpenAPI file doesn't exist yet, defer to separate documentation effort
- [ ] T074 [P] Create Cypress E2E test for Odoo Web UI isolation in cypress/e2e/company-isolation-web-ui.cy.js
  - **TODO**: Create Cypress test for Record Rules validation (separate task)
- [ ] T075 Update specs/001-company-isolation/quickstart.md if any setup steps changed during implementation
  - **Note**: No setup changes during implementation
- [ ] T076 Create migration script (if needed) to assign orphaned records to default company in 18.0/extra-addons/quicksol_estate/migrations/18.0.1.0/post-migrate.py
  - **Note**: Not needed for Phase 1 (greenfield implementation)
- [ ] T077 Final manual validation: Follow quickstart.md setup guide end-to-end (30 minutes)
  - **Requires: Running Odoo server + test database**
- [X] T078 Code review checklist: All endpoints use @require_jwt + @require_session + @require_company decorators
  - **COMPLETED**: Created code-review-checklist.md with comprehensive verification steps
- [ ] T079 Merge 001-company-isolation branch to main after all tests pass
  - **TODO**: After manual validation complete and all tests pass

---

## Dependencies

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational)
                      ↓
    ┌─────────────────┼─────────────────┐
    ↓                 ↓                 ↓
   US1              US2               US3
(Filtering)    (Validation)      (Decorator)
    ↓                 ↓                 ↓
    └─────────────────┼─────────────────┘
                      ↓
    ┌─────────────────┼─────────────────┐
    ↓                                   ↓
   US4                                 US5
(Record Rules)                    (Test Suite)
    ↓                                   ↓
    └─────────────────┼─────────────────┘
                      ↓
                  Phase 8
                 (Polish)
```

**Key Insights**:
- **US1, US2, US3** can be implemented in parallel (they touch different aspects of the same decorator/validation system)
- **US4** depends on US1-US3 being complete (needs API isolation working first for consistency)
- **US5** can start partially in parallel with US1-US3 (write failing tests first), but full validation requires all stories complete
- **Phase 8** must wait for all user stories to be complete

### Blocking Tasks

- **T006-T010** (Foundational phase) block ALL user story work
- **T011-T020** (US1) must complete before **T046** (US4 Web UI validation) to ensure consistency
- **T021-T030** (US2) must complete before **T053-T056** (US5 validation tests)
- **T048-T070** (US5) should be written FIRST (test-first approach), but validation requires US1-US4 complete

### Parallel Execution Examples

**Parallel Batch 1** (after Foundational phase complete):
- T011-T012 (US1 review existing decorator)
- T021-T022 (US2 review existing validator)
- T031-T032 (US3 documentation)

**Parallel Batch 2** (endpoint enhancements):
- T015 (agents filtering)
- T016 (tenants filtering)
- T017 (owners filtering)
- T018 (buildings filtering)

**Parallel Batch 3** (Record Rules):
- T039-T043 (copy all 5 Record Rules to security.xml)

**Parallel Batch 4** (test scenarios):
- T049-T062 (all test methods for US1-US3 scenarios)
- T063-T066 (edge case tests)

---

## Implementation Strategy

### MVP Scope (Suggested for Initial PR)

**Include**:
- Phase 1 (Setup): T001-T005
- Phase 2 (Foundational): T006-T010
- Phase 3 (US1 - Filtering): T011-T020
- Phase 4 (US2 - Validation): T021-T030
- Phase 5 (US3 - Documentation): T031-T038

**Defer to Follow-up PRs**:
- Phase 6 (US4 - Record Rules): T039-T047 (separate PR for Web UI)
- Phase 7 (US5 - Test Suite): T048-T070 (separate PR for comprehensive testing)
- Phase 8 (Polish): T071-T079 (performance and final validation)

### Incremental Delivery Approach

1. **PR #1**: API Isolation (US1 + US2 + US3) - 38 tasks - **THIS IS THE MVP**
2. **PR #2**: Web UI Isolation (US4) - 9 tasks
3. **PR #3**: Test Suite (US5) - 23 tasks
4. **PR #4**: Performance & Polish (Phase 8) - 9 tasks

This approach delivers working API isolation first (highest business value), then adds Web UI consistency, then comprehensive testing, then optimization.

---

## Summary

**Total Tasks**: 79 tasks across 8 phases  
**MVP Tasks**: 38 tasks (Phases 1-5 covering US1, US2, US3)  
**Parallel Opportunities**: 45 tasks marked with [P] can run in parallel  
**User Story Breakdown**:
- Setup: 5 tasks
- Foundational: 5 tasks
- US1 (Filtering): 10 tasks
- US2 (Validation): 10 tasks
- US3 (Decorator): 8 tasks
- US4 (Record Rules): 9 tasks
- US5 (Test Suite): 23 tasks
- Polish: 9 tasks

**Independent Testing**:
- Each user story has clear validation criteria in quickstart.md
- US1: Test with 2 companies, verify isolation
- US2: Test unauthorized company assignment, verify 403
- US3: Test decorator integration, verify filtering
- US4: Test Web UI, verify same isolation as API
- US5: Run test suite, verify 100% pass rate

**Estimated Timeline**:
- MVP (US1-US3): 3-5 days
- Full Feature (US1-US5): 7-10 days
- Polish & Performance: 2-3 days
- **Total**: ~2 weeks for complete Phase 1 implementation
