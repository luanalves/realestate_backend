# Tasks: Company & Owner Management System

**Feature**: 007-company-owner-management  
**Input**: Design documents from `/specs/007-company-owner-management/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included per ADR-003 (80% coverage requirement) and Constitution Principle II.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths relative to `18.0/extra-addons/quicksol_estate/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure and configuration updates

- [ ] T001 Update `__manifest__.py` to include new view files in data list
- [ ] T002 [P] Update `controllers/__init__.py` to import company_api and owner_api modules
- [ ] T003 [P] Create helper module `utils/validators.py` for reusable CNPJ/email validation functions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add computed field `owner_company_ids` to `models/res_users.py` for Owner identification
- [ ] T005 [P] Add email validation constraint to `models/company.py` if not already present
- [ ] T006 [P] Create `security/record_rules.xml` entry for Owner management rule (`rule_owner_manage_owners`)
- [ ] T007 [P] Create base response helpers in `utils/responses.py` for HATEOAS links (success_response, error_response)
- [ ] T008 Create `views/company_views.xml` with form, list, search views and `action_company`
- [ ] T009 Update `views/real_estate_menus.xml` to fix `action_company` reference

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Owner Creates New Real Estate Company (Priority: P1) 🎯 MVP

**Goal**: Owner can create companies via API with CNPJ validation and auto-linkage

**Independent Test**: POST /api/v1/companies as Owner → company created + Owner linked via estate_company_ids

### Tests for User Story 1

- [ ] T010 [P] [US1] Create unit test `tests/unit/test_company_validations.py` for CNPJ format/check digits
- [ ] T011 [P] [US1] Create unit test `tests/unit/test_company_validations.py::TestEmailValidation` for email format
- [ ] T012 [P] [US1] Create integration test `tests/api/test_company_api.py::TestCreateCompany` with success/error scenarios

### Implementation for User Story 1

- [ ] T013 [US1] Create `controllers/company_api.py` with POST /api/v1/companies endpoint
- [ ] T014 [US1] Add CNPJ uniqueness check (including soft-deleted) to company creation logic
- [ ] T015 [US1] Implement auto-linkage: add created company to creator's estate_company_ids
- [ ] T016 [US1] Add GET /api/v1/companies endpoint with multi-tenancy filtering
- [ ] T017 [US1] Add GET /api/v1/companies/{id} endpoint with HATEOAS links
- [ ] T018 [US1] Add PUT /api/v1/companies/{id} endpoint with Owner authorization check
- [ ] T019 [US1] Add DELETE /api/v1/companies/{id} endpoint (soft delete, active=False)
- [ ] T020 [US1] Create shell test `integration_tests/test_us7_s1_owner_creates_company.sh`

**Checkpoint**: User Story 1 complete - Owner can create and manage companies via API

---

## Phase 4: User Story 2 - Owner Manages Other Owners (Priority: P1) 🎯 MVP

**Goal**: Owner can create/edit/remove other Owners within their companies

**Independent Test**: POST /api/v1/companies/{id}/owners as Owner → new Owner created with correct group

### Tests for User Story 2

- [ ] T021 [P] [US2] Create unit test `tests/unit/test_owner_validations.py::TestLastOwnerProtection`
- [ ] T022 [P] [US2] Create unit test `tests/unit/test_owner_validations.py::TestPasswordValidation`
- [ ] T023 [P] [US2] Create integration test `tests/api/test_owner_api.py::TestCreateOwner`
- [ ] T024 [P] [US2] Create integration test `tests/api/test_owner_api.py::TestOwnerRBAC`

### Implementation for User Story 2

- [ ] T025 [US2] Create `controllers/owner_api.py` with POST /api/v1/companies/{company_id}/owners
- [ ] T026 [US2] Implement Owner creation: assign group_real_estate_owner + estate_company_ids
- [ ] T027 [US2] Add GET /api/v1/companies/{company_id}/owners endpoint
- [ ] T028 [US2] Add GET /api/v1/companies/{company_id}/owners/{owner_id} endpoint
- [ ] T029 [US2] Add PUT /api/v1/companies/{company_id}/owners/{owner_id} endpoint
- [ ] T030 [US2] Add DELETE /api/v1/companies/{company_id}/owners/{owner_id} with last-owner protection
- [ ] T031 [US2] Implement last-owner check: query active Owners before allowing delete
- [ ] T032 [US2] Create shell test `integration_tests/test_us7_s2_owner_creates_owner.sh`

**Checkpoint**: User Story 2 complete - Owner can manage other Owners via API

---

## Phase 5: User Story 3 - SaaS Admin Manages via Odoo Web (Priority: P1) 🎯 MVP

**Goal**: SaaS Admin can manage all companies/owners via Odoo Web interface

**Independent Test**: Login as admin → Real Estate > Companies → create company and owner

### Tests for User Story 3

- [ ] T033 [P] [US3] Create Cypress test `cypress/e2e/admin-company-management.cy.js` for company CRUD
- [ ] T034 [P] [US3] Create Cypress test `cypress/e2e/admin-owner-management.cy.js` for owner CRUD

### Implementation for User Story 3

- [ ] T035 [US3] Add "Create Owner" smart button to company form view in `views/company_views.xml`
- [ ] T036 [US3] Create Owner list action accessible from company form
- [ ] T037 [US3] Add filter "Estate Owners" to Users list view (extend res.users views)
- [ ] T038 [US3] Verify Admin group bypasses multi-tenancy filters (base.group_system check)

**Checkpoint**: User Story 3 complete - SaaS Admin has full control via Odoo Web

---

## Phase 6: User Story 4 - Director/Manager Read-Only Access (Priority: P2)

**Goal**: Director/Manager can view company info but not modify or access owners

**Independent Test**: GET /api/v1/companies as Manager → success; POST → 403

### Tests for User Story 4

- [ ] T039 [P] [US4] Create integration test `tests/api/test_company_api.py::TestManagerReadOnly`
- [ ] T040 [P] [US4] Create shell test `integration_tests/test_us7_s3_company_rbac.sh`

### Implementation for User Story 4

- [ ] T041 [US4] Add RBAC check in company_api.py: Manager/Director → read-only
- [ ] T042 [US4] Add RBAC check in owner_api.py: Manager/Director → 403 Forbidden
- [ ] T043 [US4] Verify record rules in Odoo Web enforce read-only for Manager/Director

**Checkpoint**: User Story 4 complete - RBAC correctly enforced

---

## Phase 7: User Story 5 - Self-Registration as Owner (Priority: P2)

**Goal**: New user can self-register as Owner and create first company

**Independent Test**: POST /api/v1/auth/register → login → create company

### Tests for User Story 5

- [ ] T044 [P] [US5] Create integration test `tests/api/test_company_api.py::TestNewOwnerFlow`

### Implementation for User Story 5

- [ ] T045 [US5] Verify registration endpoint assigns group_real_estate_owner (existing auth module)
- [ ] T046 [US5] Add check for Owner without company: return guidance message on other API calls
- [ ] T047 [US5] Document self-registration flow in quickstart.md

**Checkpoint**: User Story 5 complete - Self-service onboarding works

---

## Phase 8: Multi-Tenancy & Integration Testing

**Purpose**: Comprehensive testing of isolation and cross-story integration

- [ ] T048 [P] Create shell test `integration_tests/test_us7_s4_company_multitenancy.sh`
- [ ] T049 Verify 404 (not 403) returned for inaccessible companies
- [ ] T050 Test Owner from Company A cannot access Company B data
- [ ] T051 Test Owner from Company A cannot create Owner for Company B

**Checkpoint**: Multi-tenancy isolation verified

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, final validation

- [ ] T052 [P] Update `docs/postman/` with Company & Owner collection
- [ ] T053 [P] Add OpenAPI schema to `docs/openapi/007-company-owner.yaml` (copy from contracts/)
- [ ] T054 Run `./lint.sh` and fix any linting issues
- [ ] T055 Validate all tests pass with `./run_all_tests.sh`
- [ ] T056 Run quickstart.md validation (follow steps, verify all commands work)
- [ ] T057 Update README.md with new endpoints documentation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────┐
                                          ↓
Phase 2 (Foundational) ──────────────────┤ BLOCKS ALL USER STORIES
                                          ↓
         ┌────────────────────────────────┼────────────────────────────────┐
         ↓                                ↓                                ↓
Phase 3 (US1: Company API)    Phase 4 (US2: Owner API)    Phase 5 (US3: Odoo Web)
         │                                │                                │
         └────────────────────────────────┼────────────────────────────────┘
                                          ↓
                              Phase 6 (US4: RBAC)
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
| US1 (Company API) | Phase 2 | US2, US3 (after Phase 2) |
| US2 (Owner API) | Phase 2 | US1, US3 (after Phase 2) |
| US3 (Odoo Web) | Phase 2 | US1, US2 (after Phase 2) |
| US4 (RBAC) | US1 (RBAC check in company_api) | - |
| US5 (Self-Reg) | US1 (create company flow) | - |

### Parallel Opportunities

**After Phase 2 completes**, the following can run in parallel:

```bash
# Team can split: 
# Developer A: US1 (T010-T020)
# Developer B: US2 (T021-T032)
# Developer C: US3 (T033-T038)
```

**Within each story**, tests can run in parallel:

```bash
# US1 tests (T010, T011, T012) can all run simultaneously
# US2 tests (T021, T022, T023, T024) can all run simultaneously
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 = P1 Stories)

1. Complete Phase 1 + Phase 2 (Setup + Foundational)
2. Complete Phase 3 (US1: Company API)
3. Complete Phase 4 (US2: Owner API)
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
| Phase 3: US1 | 11 | 3 |
| Phase 4: US2 | 12 | 4 |
| Phase 5: US3 | 6 | 2 |
| Phase 6: US4 | 5 | 2 |
| Phase 7: US5 | 4 | 1 |
| Phase 8: Multi-Tenancy | 4 | 1 |
| Phase 9: Polish | 6 | 2 |
| **TOTAL** | **57** | **21** |

---

## Notes

- All paths relative to `18.0/extra-addons/quicksol_estate/` unless otherwise specified
- Tests MUST use credentials from `.env` per Constitution
- All controllers MUST have `@require_jwt`, `@require_session`, `@require_company` decorators
- Soft delete pattern: set `active=False`, never hard delete
- Return 404 (not 403) for inaccessible resources (security through obscurity)
- HATEOAS links in all responses per ADR-007
