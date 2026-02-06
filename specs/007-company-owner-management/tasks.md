# Tasks: Company & Owner Management System

**Feature**: 007-company-owner-management  
**Input**: Design documents from `/specs/007-company-owner-management/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included per ADR-003 (80% coverage requirement) and Constitution Principle II.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**⚠️ Architecture Change**: Owner API is **independent** (not nested under Company). Owner is created WITHOUT a company and linked later via `/api/v1/owners/{id}/companies`. This enables Owner-first development priority.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths relative to `18.0/extra-addons/quicksol_estate/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure and configuration updates

- [X] T001 Update `__manifest__.py` to include new view files in data list
- [X] T002 [P] Update `controllers/__init__.py` to import owner_api and company_api modules
- [X] T003 [P] Create helper module `utils/validators.py` for reusable CNPJ/email/CRECI validation functions
- [X] T003a [P] Implement CRECI format validation per Brazilian state (SP, RJ, MG, etc.) in `utils/validators.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add computed field `owner_company_ids` to `models/res_users.py` for Owner identification
- [X] T005 [P] Add email validation constraint to `models/company.py` if not already present
- [X] T006 [P] Create `security/record_rules.xml` entry for Owner management rule (`rule_owner_manage_owners`)
- [X] T007 [P] Create base response helpers in `utils/responses.py` for HATEOAS links (success_response, error_response)
- [X] T008 Create `views/company_views.xml` with form, list, search views and `action_company`
- [X] T009 Update `views/real_estate_menus.xml` to fix `action_company` reference

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Owner CRUD via Independent API (Priority: P1) 🎯 MVP PRIORITY

**Goal**: Create, read, update, delete Owners via independent API (not nested under Company)

**Independent Test**: POST /api/v1/owners → Owner created without company; POST /owners/{id}/companies → linked

### Tests for User Story 1

- [X] T010 [P] [US1] Create unit test `tests/unit/test_owner_validations.py::TestCreatorValidation` (Owner or Admin only)
- [X] T011 [P] [US1] Create unit test `tests/unit/test_owner_validations.py::TestLastOwnerProtection`
- [X] T012 [P] [US1] Create integration test `tests/api/test_owner_api.py::TestCreateOwnerIndependent`
- [X] T013 [P] [US1] Create integration test `tests/api/test_owner_api.py::TestLinkOwnerToCompany`

### Implementation for User Story 1

- [X] T014 [US1] Create `controllers/owner_api.py` with POST /api/v1/owners endpoint (no company required)
- [X] T015 [US1] Implement Owner creation: assign group_real_estate_owner, estate_company_ids=[]
- [X] T016 [US1] Add RBAC check: only Owner (for their companies) or Admin can create Owners
- [X] T017 [US1] Add GET /api/v1/owners endpoint with multi-tenancy filtering (all Owners from user's companies)
- [X] T018 [US1] Add GET /api/v1/owners/{id} endpoint with HATEOAS links
- [X] T019 [US1] Add PUT /api/v1/owners/{id} endpoint with authorization check
- [X] T020 [US1] Add DELETE /api/v1/owners/{id} endpoint (soft delete) with last-owner protection
- [X] T021 [US1] Implement last-owner check: prevent delete if Owner is only Owner of any company
- [X] T022 [US1] Add POST /api/v1/owners/{id}/companies endpoint to link Owner to Company
- [X] T023 [US1] Add DELETE /api/v1/owners/{id}/companies/{company_id} endpoint to unlink Owner
- [X] T024 [US1] Create shell test `integration_tests/test_us7_s1_owner_crud.sh`
- [X] T025 [US1] Create shell test `integration_tests/test_us7_s2_owner_company_link.sh`

**Checkpoint**: User Story 1 complete - Owner can be created/managed independently

---

## Phase 4: User Story 2 - Owner Creates New Real Estate Company (Priority: P1) 🎯 MVP

**Goal**: Owner can create companies via API with CNPJ validation and auto-linkage

**Independent Test**: POST /api/v1/companies as Owner → company created + Owner linked via estate_company_ids

### Tests for User Story 2

- [X] T026 [P] [US2] Create unit test `tests/unit/test_company_validations.py::TestCNPJValidation` (format + check digits)
- [X] T027 [P] [US2] Create unit test `tests/unit/test_company_validations.py::TestEmailValidation`
- [X] T028 [P] [US2] Create integration test `tests/api/test_company_api.py::TestCreateCompany`

### Implementation for User Story 2

- [X] T029 [US2] Create `controllers/company_api.py` with POST /api/v1/companies endpoint
- [X] T030 [US2] Add CNPJ uniqueness check (including soft-deleted) to company creation logic
- [X] T031 [US2] Implement auto-linkage: add created company to creator's estate_company_ids
- [X] T032 [US2] Add GET /api/v1/companies endpoint with multi-tenancy filtering
- [X] T033 [US2] Add GET /api/v1/companies/{id} endpoint with HATEOAS links
- [X] T034 [US2] Add PUT /api/v1/companies/{id} endpoint with Owner authorization check
- [X] T035 [US2] Add DELETE /api/v1/companies/{id} endpoint (soft delete, active=False)
- [X] T036 [US2] Create shell test `integration_tests/test_us7_s3_company_crud.sh`

**Checkpoint**: User Story 2 complete - Owner can create and manage companies via API

---

## Phase 5: User Story 3 - SaaS Admin Manages via Odoo Web (Priority: P1) 🎯 MVP

**Goal**: SaaS Admin can manage all companies/owners via Odoo Web interface

**Independent Test**: Login as admin → Real Estate > Companies → create company and owner

### Tests for User Story 3

- [ ] T037 [P] [US3] Create Cypress test `cypress/e2e/admin-owner-management.cy.js` for owner CRUD
- [ ] T038 [P] [US3] Create Cypress test `cypress/e2e/admin-company-management.cy.js` for company CRUD

### Implementation for User Story 3

- [X] T039 [US3] Add "Owners" smart button to company form view in `views/company_views.xml`
- [X] T040 [US3] Create Owner list action accessible from company form
- [X] T041 [US3] Add filter "Estate Owners" to Users list view (extend res.users views)
- [X] T042 [US3] Verify Admin group bypasses multi-tenancy filters (base.group_system check)

**Checkpoint**: User Story 3 complete - SaaS Admin has full control via Odoo Web

---

## Phase 6: User Story 4 - Director/Manager Read-Only Access (Priority: P2)

**Goal**: Director/Manager can view company info but not modify or access owners

**Independent Test**: GET /api/v1/companies as Manager → success; POST → 403

### Tests for User Story 4

- [X] T043 [P] [US4] Create integration test `tests/api/test_company_api.py::TestManagerReadOnly`
- [X] T044 [P] [US4] Create integration test `tests/api/test_owner_api.py::TestManagerNoAccess`
- [X] T045 [P] [US4] Create shell test `integration_tests/test_us7_s4_rbac.sh`

### Implementation for User Story 4

- [X] T046 [US4] Add RBAC check in company_api.py: Manager/Director → read-only
- [X] T047 [US4] Add RBAC check in owner_api.py: Manager/Director → 403 Forbidden
- [X] T048 [US4] Verify record rules in Odoo Web enforce read-only for Manager/Director

**Checkpoint**: User Story 4 complete - RBAC correctly enforced

---

## Phase 7: User Story 5 - Self-Registration as Owner (Priority: P2)

**Goal**: New user can self-register as Owner (without company), then create/link companies

**Independent Test**: POST /api/v1/auth/register → login → POST /api/v1/companies

### Tests for User Story 5

- [X] T049 [P] [US5] Create integration test `tests/api/test_owner_api.py::TestNewOwnerWithoutCompany`

### Implementation for User Story 5

- [ ] T050 [US5] Verify registration endpoint assigns group_real_estate_owner (existing auth module) - **BLOCKED**: No registration endpoint in thedevkitchen_apigateway
- [X] T051 [US5] Add graceful handling for Owner without company on GET /owners (empty list for their companies)
- [X] T052 [US5] Document self-registration flow in quickstart.md

**Checkpoint**: User Story 5 complete - Self-service onboarding works

---

## Phase 8: Multi-Tenancy & Integration Testing

**Purpose**: Comprehensive testing of isolation and cross-story integration

- [X] T053 [P] Create shell test `integration_tests/test_us7_s5_multitenancy.sh`
- [X] T054 Verify 404 (not 403) returned for inaccessible companies/owners
- [X] T055 Test Owner from Company A cannot access Company B data
- [X] T056 Test Owner linked to multiple companies sees all their Owners

**Checkpoint**: Multi-tenancy isolation verified

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, final validation

- [ ] T057 [P] Update `docs/postman/` with Owner & Company collection (Owner endpoints first) - **DEFERRED** (P3 - documentation)
- [ ] T058 [P] Add OpenAPI schema to `docs/openapi/007-company-owner.yaml` (copy from contracts/) - **DEFERRED** (P3 - documentation)
- [ ] T059 Run `./lint.sh` and fix any linting issues - **SKIPPED** (flake8 not in container)
- [ ] T060 Validate all tests pass with `./run_all_tests.sh` - **IN PROGRESS**: Owner API refactored (667→400 lines), seed data created, Docker image rebuilding with email-validator
- [ ] T061 Run quickstart.md validation (follow steps, verify all commands work) - **IN PROGRESS**: Awaiting Docker build + DB initialization
- [X] T062 Update README.md with new endpoints documentation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────┐
                                          ↓
Phase 2 (Foundational) ──────────────────┤ BLOCKS ALL USER STORIES
                                          ↓
                              Phase 3 (US1: Owner API) ← PRIORITY 1
                                          ↓
         ┌────────────────────────────────┼────────────────────────────────┐
         ↓                                ↓                                ↓
Phase 4 (US2: Company API)    Phase 5 (US3: Odoo Web)    Phase 6 (US4: RBAC)
         │                                │                                │
         └────────────────────────────────┼────────────────────────────────┘
                                          ↓
                              Phase 7 (US5: Self-Reg)
                                          ↓
                              Phase 8 (Multi-Tenancy Tests)
                                          ↓
                              Phase 9 (Polish)
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (Owner API) | Phase 2 | - (PRIORITY - do first) |
| US2 (Company API) | Phase 2, US1 recommended | US3 (after US1) |
| US3 (Odoo Web) | Phase 2, US1 | US2 (after US1) |
| US4 (RBAC) | US1 (Owner API) **AND** US2 (Company API) | - (must wait for both) |
| US5 (Self-Reg) | US1 (Owner without company flow) | - |

### Parallel Opportunities

**After Phase 2 + Phase 3 (US1) complete**, the following can run in parallel:

```bash
# Team can split: 
# Developer A: US2 (T026-T036)
# Developer B: US3 (T037-T042)
# Developer C: US4 (T043-T048)
```

**Within each story**, tests can run in parallel:

```bash
# US1 tests (T010, T011, T012, T013) can all run simultaneously
# US2 tests (T026, T027, T028) can all run simultaneously
```

---

## Implementation Strategy

### MVP First (US1 Priority + US2 + US3 = P1 Stories)

1. Complete Phase 1 + Phase 2 (Setup + Foundational)
2. **PRIORITY**: Complete Phase 3 (US1: Owner API - independent)
3. Complete Phase 4 (US2: Company API)
4. Complete Phase 5 (US3: Odoo Web)
5. **STOP and VALIDATE**: Test all P1 stories
6. Deploy MVP

### Incremental Delivery After MVP

7. Add Phase 6 (US4: RBAC for Manager/Director)
8. Add Phase 7 (US5: Self-Registration)
9. Complete Phase 8 + Phase 9 (Tests + Polish)

---

## Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| Phase 1: Setup | 3 | 2 |
| Phase 2: Foundational | 6 | 4 |
| Phase 3: US1 (Owner API) | 16 | 4 |
| Phase 4: US2 (Company API) | 11 | 3 |
| Phase 5: US3 (Odoo Web) | 6 | 2 |
| Phase 6: US4 (RBAC) | 6 | 3 |
| Phase 7: US5 (Self-Reg) | 4 | 1 |
| Phase 8: Multi-Tenancy | 4 | 1 |
| Phase 9: Polish | 6 | 2 |
| **TOTAL** | **62** | **22** |

---

## Notes

- All paths relative to `18.0/extra-addons/quicksol_estate/` unless otherwise specified
- Tests MUST use credentials from `.env` per Constitution
- All controllers MUST have `@require_jwt`, `@require_session`, `@require_company` decorators
- Soft delete pattern: set `active=False`, never hard delete
- Return 404 (not 403) for inaccessible resources (security through obscurity)
- HATEOAS links in all responses per ADR-007
- **Owner API is independent**: `/api/v1/owners` (not nested under company)
- **Owner can exist without company**: link via POST `/api/v1/owners/{id}/companies`
