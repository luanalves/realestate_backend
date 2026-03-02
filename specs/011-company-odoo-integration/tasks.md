# Tasks: Feature 011 — Company–Odoo Integration

**Input**: Design documents from `/specs/011-company-odoo-integration/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Required — Constitution mandates ≥80% coverage. 29+ test files must be updated. Test tasks included within each user story.

**Organization**: Tasks grouped by user story (7 stories: US1–US7). Dependencies between stories documented.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US7)
- Exact file paths included in descriptions

## Path Conventions

- **Source code**: `18.0/extra-addons/{module}/` (Odoo modules)
- **Tests**: `18.0/extra-addons/{module}/tests/` (Python unittest)
- **Integration tests**: `integration_tests/` (shell/curl scripts)
- **Documentation**: `docs/adr/`, `docs/architecture/`, `knowledge_base/`
- **Seed data**: `18.0/extra-addons/quicksol_estate/data/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clean environment preparation

- [ ] T001 Run database reset to start clean: `cd 18.0 && bash reset_db.sh`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model changes that MUST complete before ANY user story work. Without these, the codebase won't load.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Rewrite `company.py` as `_inherit = 'res.company'` with fields (`is_real_estate`, `cnpj`, `creci`, `legal_name`, `foundation_date`, `description`), computed counts, CNPJ validation, and SQL constraints in `18.0/extra-addons/quicksol_estate/models/company.py`
- [ ] T003 [P] Delete `state.py` — eliminate `real.estate.state` model entirely in `18.0/extra-addons/quicksol_estate/models/state.py`
- [ ] T004 [P] Delete `data/states.xml` — seed data for eliminated model in `18.0/extra-addons/quicksol_estate/data/states.xml`
- [ ] T005 Update `__manifest__.py`: remove `states.xml` and obsolete data file refs from `data` list, verify `depends` includes `'base'`, remove `real.estate.state` model import in `18.0/extra-addons/quicksol_estate/__manifest__.py`
- [ ] T006 [P] Update `models/__init__.py`: remove `state` import, verify `company` import still present in `18.0/extra-addons/quicksol_estate/models/__init__.py`
- [ ] T007 [P] Update base test fixtures: replace `env['thedevkitchen.estate.company']` with `env['res.company']` and add `is_real_estate=True` to company creation in `18.0/extra-addons/quicksol_estate/tests/base_company_test.py` and `18.0/extra-addons/quicksol_estate/tests/base_test.py`

**Checkpoint**: Module loads without errors — `docker compose restart odoo && docker compose logs -f odoo`

---

## Phase 3: User Story 1 — Company as res.company (Priority: P1) 🎯 MVP

**Goal**: `thedevkitchen.estate.company` fully eliminated; `res.company` extended with real estate fields; Company CRUD API works; `/states` uses native `res.country.state`.

**Independent Test**: `env['res.company'].create({'name': 'Test', 'is_real_estate': True, 'cnpj': '12.345.678/0001-00'})` — verify `cnpj` column exists in `res_company` table, `thedevkitchen_estate_company` table does NOT exist.

### Implementation for User Story 1

- [ ] T008 [US1] Rewrite company views as inherited `res.company` form/tree/search views in `18.0/extra-addons/quicksol_estate/views/company_views.xml`
- [ ] T009 [P] [US1] Update menus and actions to target `res.company` with `is_real_estate` domain filter in `18.0/extra-addons/quicksol_estate/views/real_estate_menus.xml`
- [ ] T010 [P] [US1] Rewrite company seed data: create `res.company` records with `is_real_estate=True`, `cnpj`, `creci` in `18.0/extra-addons/quicksol_estate/data/company_seed.xml`
- [ ] T011 [US1] Update `company_api.py` (6 endpoints): `env['thedevkitchen.estate.company']` → `env['res.company']`, add `is_real_estate=True` on create, domain filter `[('is_real_estate','=',True)]`, `zip_code`↔`zip` field mapping, auto-linkage via native `company_ids` in `18.0/extra-addons/quicksol_estate/controllers/company_api.py`
- [ ] T012 [P] [US1] Update `master_data_api.py`: `env['real.estate.state']` → `env['res.country.state']`, preserve response JSON shape in `18.0/extra-addons/quicksol_estate/controllers/master_data_api.py`

### Tests for User Story 1

- [ ] T013 [US1] Rewrite company unit tests for `res.company` `_inherit` model (create, read, computed counts, defaults) in `18.0/extra-addons/quicksol_estate/tests/unit/test_company_unit.py`
- [ ] T014 [P] [US1] Rewrite company validation tests: CNPJ checksum, uniqueness constraint, `is_real_estate` default on `res.company` in `18.0/extra-addons/quicksol_estate/tests/unit/test_company_validations.py`
- [ ] T015 [P] [US1] Update company API test: env refs, `is_real_estate` filter, `zip_code`↔`zip` mapping in `18.0/extra-addons/quicksol_estate/tests/api/test_company_api.py`
- [ ] T016 [P] [US1] Update master data API test: `real.estate.state` → `res.country.state` in `18.0/extra-addons/quicksol_estate/tests/api/test_masterdata.py` and `18.0/extra-addons/quicksol_estate/tests/api/test_master_data_api.py`

**Checkpoint**: Company CRUD API returns correct JSON. `/states` endpoint works. `thedevkitchen_estate_company` table does not exist.

---

## Phase 4: User Story 2 — User Association via Native company_ids (Priority: P1)

**Goal**: `estate_company_ids` eliminated from `res.users`; all business models use `company_id = Many2one('res.company')`; M2M relation tables dropped; `state_id` references migrated to `res.country.state`.

**Independent Test**: `user.write({'company_ids': [(4, company.id)]})` → `company.id in user.company_ids.ids` is True. No `estate_company_ids` field exists.

### Implementation — res.users

- [ ] T017 [US2] Update `res_users.py`: remove `estate_company_ids` M2M, remove `main_estate_company_id` M2O, adapt `owner_company_ids` to compute from `company_ids.filtered(lambda c: c.is_real_estate)`, update `write()` agent sync to use native `company_ids` in `18.0/extra-addons/quicksol_estate/models/res_users.py`

### Implementation — Business Models (M2M → M2O)

- [ ] T018 [P] [US2] Update `property.py`: drop M2M `company_ids`, add/keep M2O `company_id = Many2one('res.company', required=True)`, change `state_id` comodel to `res.country.state` in `18.0/extra-addons/quicksol_estate/models/property.py`
- [ ] T019 [P] [US2] Update `agent.py`: remove deprecated M2M `company_ids`, change `company_id` comodel to `res.company`, update `_onchange_user_id()` to read `user.company_ids`, update `create()`/`write()` overrides in `18.0/extra-addons/quicksol_estate/models/agent.py`
- [ ] T020 [P] [US2] Update `lead.py`: drop M2M `company_ids`, add M2O `company_id = Many2one('res.company', required=True)` in `18.0/extra-addons/quicksol_estate/models/lead.py`
- [ ] T021 [P] [US2] Update `lease.py`: drop M2M `company_ids`, add M2O `company_id = Many2one('res.company', required=True)` in `18.0/extra-addons/quicksol_estate/models/lease.py`
- [ ] T022 [P] [US2] Update `sale.py`: remove M2M `company_ids`, change existing M2O `company_id` comodel to `res.company` in `18.0/extra-addons/quicksol_estate/models/sale.py`

### Implementation — M2O Comodel Changes

- [ ] T023 [P] [US2] Update `commission_rule.py`: `company_id` comodel → `res.company` in `18.0/extra-addons/quicksol_estate/models/commission_rule.py`
- [ ] T024 [P] [US2] Update `commission_transaction.py`: `company_id` comodel → `res.company` in `18.0/extra-addons/quicksol_estate/models/commission_transaction.py`
- [ ] T025 [P] [US2] Update `profile.py`: `company_id` comodel → `res.company` in `18.0/extra-addons/quicksol_estate/models/profile.py`
- [ ] T026 [P] [US2] Update `assignment.py`: `company_id` comodel → `res.company`, simplify validation from `agent.company_id not in property.company_ids` to `agent.company_id != property.company_id` in `18.0/extra-addons/quicksol_estate/models/assignment.py`

### Implementation — state_id Comodel Changes

- [ ] T027 [P] [US2] Update `property_owner.py`: `state_id` comodel → `res.country.state` in `18.0/extra-addons/quicksol_estate/models/property_owner.py`
- [ ] T028 [P] [US2] Update `property_building.py`: `state_id` comodel → `res.country.state` in `18.0/extra-addons/quicksol_estate/models/property_building.py`

### Implementation — Observer

- [ ] T029 [US2] Update `user_company_validator_observer.py`: validate writes on `company_ids` (native) instead of `estate_company_ids`, browse `res.company` for error messages in `18.0/extra-addons/quicksol_estate/models/observers/user_company_validator_observer.py`

### Tests for User Story 2

- [ ] T030 [US2] Update observer tests: `estate_company_ids` → `company_ids` native validation in `18.0/extra-addons/quicksol_estate/tests/observers/test_user_company_validator_observer.py`
- [ ] T031 [P] [US2] Update observer unit test: field references and company model in `18.0/extra-addons/quicksol_estate/tests/unit/test_user_company_validator_observer_unit.py`
- [ ] T032 [P] [US2] Update agent unit test: M2M→M2O field access, company comodel in `18.0/extra-addons/quicksol_estate/tests/unit/test_agent_unit.py`
- [ ] T033 [P] [US2] Update assignment unit test: simplified validation logic in `18.0/extra-addons/quicksol_estate/tests/unit/test_assignment_unit.py`
- [ ] T034 [P] [US2] Update lead company validation test: `company_ids` → `company_id` M2O in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_validation.py`
- [ ] T035 [P] [US2] Update base agent test fixture: company refs in `18.0/extra-addons/quicksol_estate/tests/base_agent_test.py`
- [ ] T036 [P] [US2] Update unit base company test fixture: env refs in `18.0/extra-addons/quicksol_estate/tests/unit/base_company_test.py`

**Checkpoint**: All models use `company_id` M2O → `res.company`. No M2M company tables remain. `estate_company_ids` field does not exist on `res.users`.

---

## Phase 5: User Story 3 — Record Rules with Native Multi-Company (Priority: P2)

**Goal**: All 15+ record rules use `[('company_id', 'in', company_ids)]` native pattern. Obsolete ACLs removed.

**Independent Test**: User of company A cannot see properties of company B. Company default (ID=1, `is_real_estate=False`) sees no estate data.

### Implementation for User Story 3

- [ ] T037 [US3] Rewrite `record_rules.xml`: replace all `user.estate_company_ids.ids` with native `company_ids`; M2M domain `('company_ids', 'in', ...)` → M2O domain `('company_id', 'in', company_ids)`; company-self rules add `('is_real_estate', '=', True)` in `18.0/extra-addons/quicksol_estate/security/record_rules.xml`
- [ ] T038 [P] [US3] Update `ir.model.access.csv`: remove 7 ACL rows for `model_thedevkitchen_estate_company` and 5 rows for `model_real_estate_state` in `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv`

### Tests for User Story 3

- [ ] T039 [US3] Update company isolation API test: verify cross-company data leakage prevented by native rules in `18.0/extra-addons/quicksol_estate/tests/api/test_company_isolation_api.py`
- [ ] T040 [P] [US3] Update RBAC multi-tenancy integration test: `estate_company_ids` → `company_ids` in `18.0/extra-addons/quicksol_estate/tests/integration/test_rbac_multi_tenancy.py`
- [ ] T041 [P] [US3] Update schema validation test: table names, column names for new schema in `18.0/extra-addons/quicksol_estate/tests/integration/test_schema_validation.py`

**Checkpoint**: Record rules enforce isolation via native Odoo mechanism. No `estate_company_ids` in any rule domain.

---

## Phase 6: User Story 4 — Middleware @require_company Adapted (Priority: P2)

**Goal**: `@require_company` validates against `user.company_ids` (native), checks `is_real_estate`, calls `request.update_env(company=...)` for proper context propagation.

**Independent Test**: Request with valid `X-Company-ID` → `self.env.company` = that company. Invalid/non-RE company → 403/404.

### Implementation for User Story 4

- [ ] T042 [US4] Rewrite `require_company` decorator: validate `X-Company-ID` against `user.company_ids`, check `company.is_real_estate == True`, call `request.update_env(company=company_id)`, keep `request.user_company_ids` for backward compat in `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`

### Tests for User Story 4

- [ ] T043 [US4] Update middleware/auth tests: `estate_company_ids` → `company_ids`, `update_env()` assertions in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_user_auth.py`

**Checkpoint**: Middleware correctly sets native Odoo company context. All 16+ endpoints using `@require_company` work.

---

## Phase 7: User Story 5 — Controllers Updated (Priority: P2)

**Goal**: ALL controllers use `env['res.company']` and `company_ids` native. Zero breaking API changes. Login/me payloads correct.

**Independent Test**: Login → payload `companies[]` from `company_ids.filtered(is_real_estate)`. `GET /api/v1/me` returns same shape. All CRUD operations use native company context.

### Implementation — APIgateway Controllers

- [ ] T044 [US5] Update `user_auth_controller.py`: `_build_user_response` iterates `company_ids.filtered(lambda c: c.is_real_estate)`, fix latent bug `getattr(c, 'vat', None)` → `c.cnpj`, `default_company_id` from `user.company_id.id` in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py`
- [ ] T045 [P] [US5] Update `me_controller.py`: companies from `company_ids.filtered(lambda c: c.is_real_estate)`, `default_company_id` from `user.company_id.id` in `18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py`

### Implementation — Estate Controllers

- [ ] T046 [P] [US5] Update `property_api.py`: replace `request.company_domain` usage with native ORM filtering via `request.env.company`, update env refs and error strings in `18.0/extra-addons/quicksol_estate/controllers/property_api.py`
- [ ] T047 [P] [US5] Update `sale_api.py`: replace `estate_company_ids` refs, `request.company_domain` → native filtering in `18.0/extra-addons/quicksol_estate/controllers/sale_api.py`
- [ ] T048 [P] [US5] Update `agent_api.py`: env refs, company domain → native in `18.0/extra-addons/quicksol_estate/controllers/agent_api.py`
- [ ] T049 [P] [US5] Update `owner_api.py`: env refs → `res.company` in `18.0/extra-addons/quicksol_estate/controllers/owner_api.py`

### Implementation — Onboarding Module

- [ ] T050 [P] [US5] Update `invite_controller.py`: `env['thedevkitchen.estate.company']` → `env['res.company']`, company association via `company_ids += (4, id)` in `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py`
- [ ] T051 [P] [US5] Update `invite_service.py`: env refs → `res.company`, company search filter in `18.0/extra-addons/thedevkitchen_user_onboarding/services/invite_service.py`
- [ ] T052 [P] [US5] Update `password_token.py`: `company_id` comodel → `Many2one('res.company')` in `18.0/extra-addons/thedevkitchen_user_onboarding/models/password_token.py`

### Implementation — Services

- [ ] T053 [P] [US5] Update `assignment_service.py`: env refs → `res.company`, company domain refs in `18.0/extra-addons/quicksol_estate/services/assignment_service.py`
- [ ] T054 [P] [US5] Update `performance_service.py`: env refs → `res.company` in `18.0/extra-addons/quicksol_estate/services/performance_service.py`

### Tests for User Story 5

- [ ] T055 [US5] Update login API test: company payload from native `company_ids`, `cnpj` field correct in `18.0/extra-addons/quicksol_estate/tests/api/test_user_login.py`
- [ ] T056 [P] [US5] Update property API auth test: company domain assertions in `18.0/extra-addons/quicksol_estate/tests/api/test_property_api_auth.py`
- [ ] T057 [P] [US5] Update owner API test: env refs in `18.0/extra-addons/quicksol_estate/tests/api/test_owner_api.py`
- [ ] T058 [P] [US5] Update sale API test: env refs, company domain in `18.0/extra-addons/quicksol_estate/tests/api/test_sale_api.py`
- [ ] T059 [P] [US5] Update lease API test: env refs, `company_ids` → `company_id` in `18.0/extra-addons/quicksol_estate/tests/api/test_lease_api.py`
- [ ] T060 [P] [US5] Update tenant API test: company refs in `18.0/extra-addons/quicksol_estate/tests/api/test_tenant_api.py`
- [ ] T061 [P] [US5] Update profile tests: `company_id` comodel changes in `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_authorization_unit.py` and `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_sync_unit.py`

**Checkpoint**: ALL controllers use `res.company` and `company_ids` native. Login/me payloads verified. Zero `thedevkitchen.estate.company` refs in controllers.

---

## Phase 8: User Story 6 — ADR & Knowledge Base Updates (Priority: P2)

**Goal**: All documentation reflects new architecture. Zero obsolete references to `estate_company_ids` or `thedevkitchen.estate.company`.

**Independent Test**: `grep -r 'estate_company_ids\|thedevkitchen.estate.company' docs/ knowledge_base/` returns 0 results.

### Implementation for User Story 6

- [ ] T062 [P] [US6] Update ADR-004: clarify prefix scope — `thedevkitchen` for table/module names only, not fields on `_inherit` models in `docs/adr/ADR-004-nomenclatura-modulos-tabelas.md`
- [ ] T063 [P] [US6] Update ADR-008: replace `estate_company_ids` → `company_ids` native throughout in `docs/adr/ADR-008-api-security-multi-tenancy.md`
- [ ] T064 [P] [US6] Update ADR-009: update `estate_company_ids` reference in "Positivas" section in `docs/adr/ADR-009-headless-authentication-user-context.md`
- [ ] T065 [P] [US6] Update ADR-019: rewrite ALL record rule examples to native `company_ids`, update onboarding journey, replace `Many2one('thedevkitchen.estate.company')` → `Many2one('res.company')` in `docs/adr/ADR-019-rbac-perfis-acesso-multi-tenancy.md`
- [ ] T066 [P] [US6] Update ADR-020: update `UserCompanyValidatorObserver` code examples — `estate_company_ids` → `company_ids` in `docs/adr/ADR-020-observer-pattern-odoo-event-driven-architecture.md`
- [ ] T067 [P] [US6] Update ADR-024: change profile FK `company_id` to `Many2one('res.company')` in Phase 2 section in `docs/adr/ADR-024-profile-unification.md`
- [ ] T068 [P] [US6] Update KB-07: add `_inherit` best practices section covering `_inherit` vs `_inherits` vs `_name` + `_inherit`, `is_real_estate` discriminator pattern in `knowledge_base/07-programming-in-odoo.md`
- [ ] T069 [P] [US6] Rewrite `DATABASE_ARCHITECTURE_USERS.md`: update ER diagrams, field tables, relationship descriptions — 20+ refs to custom model in `docs/architecture/DATABASE_ARCHITECTURE_USERS.md`

**Checkpoint**: US6 complete — `grep` confirms zero obsolete references in docs.

---

## Phase 9: User Story 7 — Reset & Seed + Integration Tests (Priority: P3)

**Goal**: Dev environment resets cleanly with new schema, seeds load correctly, all integration test scripts pass.

**Independent Test**: `reset_db.sh` → module update → system boots → login works → `SELECT tablename FROM pg_tables WHERE tablename = 'thedevkitchen_estate_company'` returns 0 rows.

### Implementation for User Story 7

- [ ] T070 [US7] Verify/update `reset_db.sh` for new schema — ensure no refs to obsolete tables in `18.0/reset_db.sh`
- [ ] T071 [P] [US7] Update remaining seed/demo data files: ensure all `thedevkitchen.estate.company` refs → `res.company` with `is_real_estate=True` in `18.0/extra-addons/quicksol_estate/data/`
- [ ] T072 [US7] Update integration test shell scripts (14 files): SQL queries `thedevkitchen_estate_company` → `res_company WHERE is_real_estate`, `thedevkitchen_user_company_rel` → `res_company_users_rel`, `estate_company_ids` → `company_ids` in `integration_tests/`
- [ ] T073 [US7] Run full reset and validate: `reset_db.sh` → module update → login → seed companies have `is_real_estate=True` → verify 8 obsolete tables do NOT exist

**Checkpoint**: US7 complete — dev environment fully operational with new schema.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Integration test updates, remaining test files, final validation

- [ ] T074 [P] Update RBAC integration tests (6 files): company refs in `18.0/extra-addons/quicksol_estate/tests/integration/test_rbac_agent.py`, `test_rbac_prospector.py`, `test_rbac_portal.py`, `test_rbac_legal.py`, `test_rbac_director.py`, `test_rbac_receptionist.py`
- [ ] T075 [P] Update remaining integration tests: commission, assignment, performance tests in `18.0/extra-addons/quicksol_estate/tests/integration/test_commission_calculation.py`, `test_commission_split.py`, `test_assignment.py`, `test_api_performance.py`, `test_performance.py`
- [ ] T076 [P] Update APIgateway-specific tests: session, OAuth tests that may reference company fields in `18.0/extra-addons/thedevkitchen_apigateway/tests/`
- [ ] T077 [P] Update Postman collection description texts (no endpoint changes, update model references) in `docs/postman/`
- [ ] T078 Verify zero occurrences of `thedevkitchen.estate.company` as `_name` or comodel in entire Python/XML codebase: `grep -r 'thedevkitchen.estate.company' 18.0/extra-addons/`
- [ ] T079 Verify zero occurrences of `estate_company_ids` as stored field: `grep -r 'estate_company_ids' 18.0/extra-addons/`
- [ ] T080 Run full integration test suite and validate ≥80% coverage: `cd integration_tests && bash run_all_tests.sh`
- [ ] T081 Validate against quickstart.md cheat sheet commands — verify all DB checks pass (M2M tables dropped, `is_real_estate` flag, record rules native)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────> Phase 2: Foundational (BLOCKING)
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      ▼
            Phase 3: US1 (P1)                    Phase 4: US2 (P1)
            Company Model                        User Association
                    │                                      │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            Phase 5: US3    Phase 6: US4    Phase 8: US6
            Record Rules    Middleware      Documentation
                    │              │              │
                    └──────┬───────┘              │
                           ▼                      │
                    Phase 7: US5                   │
                    Controllers                    │
                           │                      │
                    ┌──────┴──────────────────────┘
                    ▼
            Phase 9: US7
            Reset & Seed
                    │
                    ▼
            Phase 10: Polish
```

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2) — Can start immediately after
- **US2 (P1)**: Depends on Foundational (Phase 2) — Can run in parallel with US1 (different files)
- **US3 (P2)**: Depends on US1 + US2 completion (M2O fields must exist for native rules)
- **US4 (P2)**: Depends on US2 completion (native `company_ids` must exist on users)
- **US5 (P2)**: Depends on US3 + US4 (record rules + middleware must be native before controller updates)
- **US6 (P2)**: Can start after US2 (documentation can parallel with US3-US5)
- **US7 (P3)**: Depends on US1-US5 completion (full reset only after all code changes)

### Within Each User Story

- Models before services
- Services before controllers
- Core implementation before tests
- Tests verify each story independently

### Parallel Opportunities

**Phase 2**: T003, T004, T006, T007 can all run in parallel (different files)

**Phase 3**: T009, T010, T012 can run in parallel. T015, T016 can run in parallel with each other.

**Phase 4**: T018–T028 can ALL run in parallel (each modifies a different model file). T030–T036 can all run in parallel (different test files).

**Phase 5**: T038 can parallel with T037. T040, T041 can parallel.

**Phase 7**: T045–T054 can ALL run in parallel (different controller/service files). T056–T061 can all run in parallel.

**Phase 8**: T062–T069 can ALL run in parallel (all different documentation files).

**Phase 10**: T074–T077 can run in parallel.

---

## Parallel Example: User Story 2 (Maximum Parallelism)

```bash
# Launch ALL model updates together (11 different files):
T018: property.py
T019: agent.py
T020: lead.py
T021: lease.py
T022: sale.py
T023: commission_rule.py
T024: commission_transaction.py
T025: profile.py
T026: assignment.py
T027: property_owner.py
T028: property_building.py

# Then observer (depends on above conceptually):
T029: user_company_validator_observer.py

# Then ALL tests in parallel (7 different test files):
T030-T036: Each modifies a different test file
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (reset DB)
2. Complete Phase 2: Foundational (company.py _inherit, delete state.py, update manifest)
3. Complete Phase 3: US1 (views, seeds, company API, states API, tests)
4. **STOP and VALIDATE**: Company CRUD works, `/states` works, `thedevkitchen_estate_company` table gone
5. This is the minimum viable demonstration of the migration

### Incremental Delivery

1. Setup + Foundational → Module loads ✅
2. US1 → Company model + API works (MVP!) ✅
3. US2 → All models migrated, user association native ✅
4. US3 + US4 → Security layer fully native ✅
5. US5 → All controllers updated ✅
6. US6 → Documentation aligned ✅
7. US7 → Dev environment reset works ✅
8. Polish → Final validation and cleanup ✅

Each increment adds value without breaking previous increments.

### Full Sequential Strategy

With a single developer, execute phases 1→10 in order. Total: 81 tasks. Estimated effort: Medium-to-large refactoring (no new features, but extensive file changes).

---

## Notes

- **[P] tasks** = different files, no dependencies on incomplete tasks in same phase
- **[Story] label** maps task to specific user story for traceability
- **File count**: 82 files modified across 3 modules + docs + integration tests
- **Tables dropped**: 8 (verified via `SELECT tablename FROM pg_tables WHERE tablename LIKE 'thedevkitchen_%'`)
- **Models eliminated**: 2 (`thedevkitchen.estate.company`, `real.estate.state`)
- **Zero breaking changes**: All API contracts preserved per FR-014
- **Key mapping**: `zip_code` (API) ↔ `zip` (res.company) — controller must translate both directions
- **Key filter**: `is_real_estate=True` must be added to every domain that previously targeted the custom model
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
