---
description: "Tasks for feature 015 — Service Pipeline (Atendimentos)"
---

# Tasks: Service Pipeline Management (Atendimentos)

**Feature**: `015-service-pipeline-atendimentos`
**Input**: Design documents from `specs/015-service-pipeline-atendimentos/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml)

**Tests**: Tests are **REQUIRED** for this feature per Constitution v1.6.0 Principle II (Test Coverage Mandatory, NON-NEGOTIABLE — minimum 80% coverage; ADR-003).

**Organization**: Tasks grouped by user story (US1–US5) for clarity and to allow parallel work across teams. **All 80 tasks will be developed in this delivery** — there is no MVP cut.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Parallelizable (different files, no incomplete dependencies)
- **[Story]**: User story tag (US1–US5). Setup/Foundational/Polish tasks have no story tag.
- All file paths are repository-relative.

## Path Conventions (from plan.md)

- Models: `18.0/extra-addons/quicksol_estate/models/`
- Controllers: `18.0/extra-addons/quicksol_estate/controllers/`
- Services: `18.0/extra-addons/quicksol_estate/services/`
- Security: `18.0/extra-addons/quicksol_estate/security/`
- Data XML: `18.0/extra-addons/quicksol_estate/data/`
- Views: `18.0/extra-addons/quicksol_estate/views/`
- Migrations: `18.0/extra-addons/quicksol_estate/migrations/18.0.x.x.x/`
- Hooks: `18.0/extra-addons/quicksol_estate/hooks/`
- Unit tests: `18.0/extra-addons/quicksol_estate/tests/unit/`
- API tests: `18.0/extra-addons/quicksol_estate/tests/api/`
- Integration shell tests: `integration_tests/`
- Cypress: `cypress/e2e/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create skeleton files, register new models in the addon, prepare migration scaffold.

- [X] T001 Create directory scaffolding under `18.0/extra-addons/quicksol_estate/` for new files (`migrations/18.0.x.x.x/`, `hooks/`, `tests/unit/`, `tests/api/` if missing) and add empty `__init__.py` where needed
- [X] T002 Update `18.0/extra-addons/quicksol_estate/__manifest__.py` — bump version, add new data files (sequence, sources, tags, settings, cron, record rules, views, menus, seed) in `data` key; declare `post_init_hook='post_init'` and `pre_init_hook=None`; ensure `depends` lists `mail`, `thedevkitchen_apigateway`, `thedevkitchen_user_onboarding`
- [X] T003 [P] Create `18.0/extra-addons/quicksol_estate/migrations/18.0.x.x.x/pre-migrate.py` with the PostgreSQL `EXCLUDE` constraint creation script (research R1) — idempotent (`IF NOT EXISTS`)
- [X] T004 [P] Create `18.0/extra-addons/quicksol_estate/hooks/post_init.py` with `post_init(env)` iterating `res.company` to create singleton settings + system tag `closed` + the four default non-system tags (`Follow Up`, `Qualificado`, `Lançamento`, `Parceria`) + 5 default sources per company (research R6 / data-model.md E2 · E3 · E5); idempotent via `xml_id` lookup
- [X] T005 [P] Create `18.0/extra-addons/quicksol_estate/data/service_sequence_data.xml` defining sequence `quicksol_estate.service.seq` with prefix `ATD/%(year)s/` and padding 5

**Checkpoint**: Skeleton ready, addon manifest updated, migration scaffold in place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Models, security primitives, sequences. NOTHING in user-story phases can be implemented until this phase is complete.

**⚠️ CRITICAL**: All user-story work blocks on Phase 2 completion.

### 2.A Models

- [X] T006 [P] Create `18.0/extra-addons/quicksol_estate/models/service_tag.py` — model `real.estate.service.tag` per data-model.md E2 (fields, `_sql_constraints` for unique name+company and color regex, `@api.constrains` blocking writes when `is_system=True` without admin context)
- [X] T007 [P] Create `18.0/extra-addons/quicksol_estate/models/service_source.py` — model `real.estate.service.source` per data-model.md E3 (fields + `_sql_constraints` unique code per company)
- [X] T008 [P] Create `18.0/extra-addons/quicksol_estate/models/partner_phone.py` — model `real.estate.partner.phone` per data-model.md E4 (fields + `@api.constrains` for at-most-one primary per partner) AND extend `res.partner` with `phone_ids = One2many('real.estate.partner.phone','partner_id')` in same file
- [X] T009 [P] Create `18.0/extra-addons/quicksol_estate/models/service_settings.py` — singleton `thedevkitchen.service.settings` per data-model.md E5 (fields, `@api.constrains` ranges, `get_settings()` class method)
- [X] T010 Create `18.0/extra-addons/quicksol_estate/models/service.py` — main model `real.estate.service` per data-model.md E1 (all fields, `mail.thread` + `mail.activity.mixin` inherits, `_track_visibility='onchange'` on `stage`, sequence-driven `name`, computed `last_activity_date` and `is_pending` and `is_orphan_agent` per research R2; depends on T006–T009)
- [X] T011 Modify `18.0/extra-addons/quicksol_estate/models/proposal.py` — add additive nullable field `service_id = fields.Many2one('real.estate.service', ondelete='set null', index=True)` (research R3); update `_inherit` chain only if needed; ensure backward compatible
- [X] T012 Update `18.0/extra-addons/quicksol_estate/models/__init__.py` to import the 5 new model modules in correct dependency order

### 2.B Python Constraints (stage gates) — on `real.estate.service`

- [X] T013 Implement in service.py: `_check_proposal_stage_requires_property` (FR-004), `_check_formalization_requires_approved_proposal` (FR-005, R3), `_check_lost_requires_reason` (FR-006), `_check_closed_tag_locks_stage` (FR-007), `_check_orphan_agent_blocks_stage_change` (FR-024a), `_check_terminal_stages_require_explicit_reopen` (FR-003a)

### 2.C Security baseline

- [X] T014 Update `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv` — add ACLs for the 5 new models per profile group (Owner/Manager: full; Agent: read+write own; Reception: read all + create services; Prospector: read+write own services); reference profile groups from `thedevkitchen_user_onboarding`
- [X] T015 [P] Create `18.0/extra-addons/quicksol_estate/security/service_record_rules.xml` — record rules per data-model.md (company isolation + agent_own + prospector_own); register file in manifest

### 2.D Data XML defaults

- [X] T016 [P] Create `18.0/extra-addons/quicksol_estate/data/service_tags_data.xml` defining the system tag `closed` with `is_system=True` and stable `xml_id` `seed_service_tag_closed` (used by post_init hook)
- [X] T017 [P] Create `18.0/extra-addons/quicksol_estate/data/service_cron_data.xml` defining a daily cron job `service_recompute_pendency_cron` running at 03:00 UTC to recompute `is_pending` for active services (FR-015)

**Checkpoint**: Models load, constraints fire, ACLs/record rules in place. User story phases can begin in parallel.

---

## Phase 3: User Story 1 — Agent creates and moves through pipeline (Priority: P1)

**Goal**: Authenticated agent can create a service, attach client + property, and move through pipeline stages with full audit and validation.

**Independent Test**: Agent logs in, creates a service, walks `no_service → in_service → visit → proposal → formalization → won` (with property + accepted proposal), and a separate flow `→ lost` with reason. Agent does not see other agents' services.

### Tests for US1 (write FIRST, ensure FAIL before implementation)

- [X] T018 [P] [US1] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_service_pipeline.py` — covers stage gates (FR-004, FR-005, FR-006, FR-007), forward jumps with gates (clarification Q1), **rollback transitions** from any non-terminal stage with audit (FR-003), audit message creation in mail.thread on transition, terminal stages reject non-reopen transitions (FR-003a), **lead independence** — transitions to `won`/`lost` MUST NOT mutate any field on the linked `real.estate.lead` (FR-001a), and **concurrent stage transitions** — simulate two simultaneous PATCH /stage operations on the same record and assert the last-writer-wins outcome with both attempts present in the mail.thread audit trail
- [X] T019 [P] [US1] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_service_uniqueness.py` — verifies EXCLUDE constraint blocks duplicate active service (client+type+agent), allows historical duplicates (won/lost), allows same property in multiple active services (FR-008a)
- [X] T020 [P] [US1] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_service_tag_system.py` — verifies `is_system` immutability and `closed` tag locks pipeline movement (FR-007)
- [X] T021 [P] [US1] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_orphan_agent.py` — verifies `is_orphan_agent` computed and FR-024a blocking stage transitions
- [X] T022 [P] [US1] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_endpoints.py` — covers POST/GET/PUT/DELETE/PATCH stage on `/api/v1/services`, HATEOAS links presence, error codes 400/401/403/404/409/422/423
- [X] T023 [P] [US1] Integration shell test `integration_tests/test_us15_s1_agent_creates_service_lifecycle.sh` — full lifecycle: auth → POST → walk all stages → verify audit timeline (uses seeded data)

### Implementation for US1

- [X] T024 [US1] Create `18.0/extra-addons/quicksol_estate/services/partner_dedup_service.py` — function `find_or_create_partner(env, name, email, phones)` deduplicating by phone OR email; reuses existing partner if match (FR-022); writes `phone_ids` if new. **Conflict resolution per FR-022**: (a) phone match takes precedence over email match; (b) if a single provided phone matches multiple distinct partners, raise a domain error mapped by the controller to HTTP 409 with the candidate partner IDs; (c) if phone and email map to different partners, prefer the phone match and post an audit `mail.message` on the new service noting the divergence
- [X] T025 [US1] Create `18.0/extra-addons/quicksol_estate/services/service_pipeline_service.py` — business-logic helpers: `change_stage(service, target_stage, comment, lost_reason)`, `reassign(service, new_agent_id, reason)`, `compute_summary(env, filters)`; encapsulates audit message posting via `service.message_post(...)` (depends on T010, T013)
- [X] T026 [US1] Create `18.0/extra-addons/quicksol_estate/controllers/service_controller.py` — endpoints: POST `/api/v1/services`, GET `/api/v1/services` (basic — filters wired in US2/US3), GET `/api/v1/services/{id}`, PUT `/api/v1/services/{id}`, DELETE `/api/v1/services/{id}`, PATCH `/api/v1/services/{id}/stage`. All use triple decorator `@require_jwt + @require_session + @require_company` per ADR-011. Returns HATEOAS responses per ADR-007 and contract `openapi.yaml`. Uses `service_pipeline_service.py` for business logic. Uses `partner_dedup_service.py` on create
- [X] T027 [US1] Add validation schemas (ADR-018) inside controller or in `18.0/extra-addons/quicksol_estate/services/service_schemas.py` — schemas for `ServiceCreateInput`, `ServiceUpdateInput`, `StageChangeInput` matching `contracts/openapi.yaml`; map errors to `{error:'validation_error', details:[]}` 400 response
- [X] T028 [US1] Update `18.0/extra-addons/quicksol_estate/controllers/__init__.py` to import `service_controller`
- [X] T029 [US1] Update `18.0/extra-addons/quicksol_estate/services/__init__.py` (create if missing) to import `partner_dedup_service` and `service_pipeline_service`
- [X] T030 [US1] Register new endpoints in Swagger via DB (`thedevkitchen_api_endpoint`) — add data XML entries for the 6 US1 endpoints per ADR-005 / skill swagger-updater
- [X] T031 [US1] Run T018–T023 and confirm GREEN

**Checkpoint** ✅: US1 fully functional. Agent can create + move + close services with multi-tenancy + RBAC enforced.

---

## Phase 4: User Story 2 — Manager visualizes, filters, reassigns (Priority: P2)

**Goal**: Manager sees all company services with kanban summary; can reassign services across agents.

**Independent Test**: Manager fetches `/summary` and `/services?stage=...&agent_id=...`, then PATCHes `/reassign` on a service; system updates agent and posts audit; non-managers receive 403.

### Tests for US2

- [X] T032 [P] [US2] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_summary.py` — verifies `/api/v1/services/summary` returns counts per stage scoped by company, respects RBAC visibility (Agent/Prospector get only own counts), latency budget < 100 ms (smoke timing)
- [X] T033 [P] [US2] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_rbac.py` — exercises full authorization matrix (FR-010) for all 5 profiles × 7 operations (create/read/update/delete/stage/reassign/manage-tags)
- [X] T034 [P] [US2] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_isolation.py` — multi-tenant isolation tests (Company A user cannot see/modify Company B services; same for tags/sources/settings)
- [X] T035 [P] [US2] Integration shell test `integration_tests/test_us15_s2_manager_reassigns_service.sh` — full reassign flow + verifies audit message + verifies `mail.activity` notifications created for both previous and new agent (FR-024b) + non-manager gets 403
- [X] T036 [P] [US2] Integration shell test `integration_tests/test_us15_s5_multitenancy_isolation.sh` — cross-company access tests (404 expected)
- [X] T037 [P] [US2] Integration shell test `integration_tests/test_us15_s6_rbac_matrix.sh` — exercises matrix end-to-end via HTTP

### Implementation for US2

- [X] T038 [US2] Add to `service_controller.py`: GET `/api/v1/services/summary` endpoint using `read_group()` over `(company_id, stage)` with `orphan_agent` extra count (research R4 — no Redis cache initially); return matches `SummaryOutput` schema with HATEOAS `links` to filtered list
- [X] T039 [US2] Add to `service_controller.py`: PATCH `/api/v1/services/{id}/reassign` endpoint — validates `new_agent_id` belongs to same company, blocks reassign on terminal stages (409), posts audit message, **and posts `mail.activity` notifications to BOTH the previous and the new agent** (FR-024 + FR-024b)
- [X] T040 [US2] Add Manager-only authorization check (`current_user has Owner OR Manager group`) inside reassign + delete + tags/sources writes; return 403 otherwise
- [X] T041 [US2] Update Swagger DB entries for `/summary` and `/reassign` endpoints (skill swagger-updater pattern)
- [X] T042 [US2] Run T032–T037 and confirm GREEN

**Checkpoint** ✅: US1 + US2 work independently. Managers have full operational visibility.

---

## Phase 5: User Story 3 — Filters, ordering, search (Priority: P2)

**Goal**: Service list endpoint supports rich filtering, ordering, search, pagination — usable for kanban + dashboards.

**Independent Test**: Apply combinations of `operation_type`, `stage`, `agent_id`, `tag_ids`, `source_id`, `is_pending`, `q`, `archived`, `ordering`, `page`, `per_page` and verify results match expected domain.

### Tests for US3

- [X] T043 [P] [US3] API test in `tests/api/test_service_endpoints.py` — extend with filter/ordering/pagination cases (or new file `test_service_filters.py`) covering each filter param + each ordering value
- [X] T044 [P] [US3] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_service_pendency.py` — verifies `last_activity_date` computation per research R2 (write_date + user-authored mail.message, excluding system messages and computed-field recomputes) and `is_pending` recompute respects `service.settings.pendency_threshold_days`
- [X] T045 [P] [US3] Integration shell test `integration_tests/test_us15_s3_filters_and_summary.sh` — full filter + ordering coverage end-to-end, including pendency ordering edge cases

### Implementation for US3

- [X] T046 [US3] Extend `service_controller.py` GET `/api/v1/services` to parse all filter query params per `contracts/openapi.yaml`, build Odoo domain, apply ordering map (`pendency` → `last_activity_date asc`, `recent` → `write_date desc`, `oldest` → `create_date asc`), apply pagination + total count, return `ListResponse` with HATEOAS pagination links
- [X] T047 [US3] Implement search `q` param: domain `OR` over `client_partner_id.name|email|phone_ids.number|property_ids.name`; case-insensitive; ensure indexes (T071) cover key columns
- [X] T048 [US3] Confirm `is_pending` cron job (T017) runs and recomputes correctly; add `_recompute_pendency()` method on the model triggered by cron
- [X] T049 [US3] Update Swagger DB entry for GET `/api/v1/services` to reflect full filter set
- [X] T050 [US3] Run T043–T045 and confirm GREEN

**Checkpoint** ✅: Kanban-grade filtering and ordering operational.

---

## Phase 6: User Story 4 — Tags & Sources configurable (Priority: P2)

**Goal**: Owner/Manager performs full CRUD on tags and sources scoped to their company; system tag `closed` is immutable.

**Independent Test**: Owner creates/edits/archives tags and sources; Agent receives 403 on writes; deleting a system tag returns 403.

### Tests for US4

- [X] T051 [P] [US4] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_tags_endpoints.py` — full CRUD tags including `is_system` immutability + 403 for non-Owner/Manager + multi-tenant isolation
- [X] T052 [P] [US4] API test `18.0/extra-addons/quicksol_estate/tests/api/test_service_sources_endpoints.py` — full CRUD sources + RBAC + isolation
- [X] T053 [P] [US4] Integration shell test `integration_tests/test_us15_s4_tags_and_sources_crud.sh`

### Implementation for US4

- [X] T054 [P] [US4] Create `18.0/extra-addons/quicksol_estate/controllers/service_tag_controller.py` — endpoints GET/POST `/api/v1/service-tags`, PUT/DELETE `/api/v1/service-tags/{id}`. Triple decorator + role check (Owner/Manager for writes; everyone authenticated for reads). Soft delete via `active=False` (FR-019). Reject writes when target tag has `is_system=True` (FR-018) returning 403
- [X] T055 [P] [US4] Create `18.0/extra-addons/quicksol_estate/controllers/service_source_controller.py` — endpoints GET/POST `/api/v1/service-sources`, PUT/DELETE `/api/v1/service-sources/{id}` with same patterns
- [X] T056 [US4] Update `controllers/__init__.py` to import the two new controllers
- [X] T057 [US4] Add Swagger DB entries for the 8 tag+source endpoints
- [X] T058 [US4] Run T051–T053 and confirm GREEN

**Checkpoint** ✅: Tag/source administration available to Owners/Managers.

---

## Phase 7: User Story 5 — Multi-phone client + dedup (Priority: P3)

**Goal**: Service creation accepts multiple phones; existing clients are reused via phone OR email match.

**Independent Test**: POST `/services` with two phones for a new client, then POST again with the same phone but different name — second call reuses partner.

### Tests for US5

- [X] T059 [P] [US5] Unit test `18.0/extra-addons/quicksol_estate/tests/unit/test_partner_dedup.py` — covers phone-only match, email-only match, both match (consistent partner), no match (creates new), invalid phone_type rejected, **conflict cases per FR-022**: (i) single phone matches multiple partners → raises mapped to 409 with candidate IDs; (ii) phone matches partner A while email matches partner B → prefers partner A and audit message recorded
- [X] T060 [P] [US5] Integration shell test `integration_tests/test_us15_s7_partner_dedup_multiphone.sh` — two consecutive POSTs reuse same partner

### Implementation for US5

- [X] T061 [US5] Verify `partner_dedup_service.py` (T024) handles all dedup paths; add edge-case handling for normalized phone comparison (strip non-digits) and case-insensitive email match
- [X] T062 [US5] Update validation schema for `phones[].type` to enforce enum (`mobile|home|work|whatsapp|fax`) returning 400 on invalid (FR-023)
- [X] T063 [US5] Run T059–T060 and confirm GREEN

**Checkpoint** ✅: All 5 user stories independently functional.

---

## Phase 8: Admin UI (Odoo Web — admin only, KB-10 compliant)

**Purpose**: Provide Odoo Web interface for the platform admin per Constitution Principle VI.

- [X] T064 [P] Create `18.0/extra-addons/quicksol_estate/views/service_views.xml` — list (`<list>`, NOT `<tree>`), form, kanban, search views per data-model.md; uses `optional="show|hide"` for columns (KB-10); NO `attrs`, NO `column_invisible` with Python expressions; menus declared without `groups` attribute
- [X] T065 [P] Create `18.0/extra-addons/quicksol_estate/views/service_tag_views.xml` — list + form
- [X] T066 [P] Create `18.0/extra-addons/quicksol_estate/views/service_source_views.xml` — list + form
- [X] T067 [P] Create `18.0/extra-addons/quicksol_estate/views/service_settings_views.xml` — singleton form (auto-open one record per company)
- [X] T068 [P] Create `18.0/extra-addons/quicksol_estate/views/service_menu.xml` — top-level "Atendimentos" menu + child menus for Services / Tags / Sources / Settings (no `groups` attribute — admin only)
- [X] T069 [P] Create `18.0/extra-addons/quicksol_estate/wizards/service_reassign_wizard.py` + matching XML view — Manager reassign action wizard
- [X] T070 [P] Cypress E2E spec `cypress/e2e/015_services_admin.cy.js` — login as admin, open list, open form, open settings (validators trigger), create tag, assert zero console errors

---

## Phase 9: Polish & Cross-Cutting

**Purpose**: Performance, lint, docs, ADR, seed expansion, post-impl artifacts.

- [ ] T071 [P] Add database indexes per data-model.md (`idx_service_company_stage`, `idx_service_company_agent`, `idx_service_company_lastactivity`, partial `idx_service_active`) via the same `pre-migrate.py` (T003) or new migration step; idempotent
- [ ] T072 [P] Create `18.0/extra-addons/quicksol_estate/data/seed_services_data.xml` per spec-idea.md Seed Data section — 5 profiles × 2 companies × all 7 stages with `seed_*` xml_id prefix; idempotent
- [ ] T073 [P] Run linters: `cd 18.0 && ./lint.sh` (Python: black, isort, flake8, pylint ≥ 8.0; XML: `lint_xml.sh`); fix issues
- [ ] T074 [P] Performance verification: run `integration_tests/test_us15_s3_filters_and_summary.sh` and `integration_tests/test_us15_s1_agent_creates_service_lifecycle.sh` capturing latencies; assert GET list < 300ms p95 (10k rows), GET /summary < 100ms p95, **PATCH /services/{id}/stage end-to-end < 1s p95 (SC-002)**; if /summary fails budget, revisit research R4 and add Redis caching
- [ ] T075 Run full quickstart end-to-end: follow [quickstart.md](./quickstart.md) section by section against a fresh Docker stack; record any deviations
- [ ] T076 Generate Postman collection `docs/postman/feature015_services_v1.0_postman_collection.json` per ADR-016 (skill postman-collection-manager) — covers all 9 endpoints + OAuth flow + auto-save tokens
- [ ] T077 [P] Sync Swagger from DB end-to-end: upgrade module on dev DB, verify all entries present in `/api/docs` (skill swagger-updater); export YAML diff for review
- [ ] T078 [P] Create `docs/adr/ADR-028-service-pipeline-domain-boundaries.md` documenting why `real.estate.service` is distinct from `real.estate.lead` and the lifecycle independence rule (clarifies clarification 5)
- [ ] T079 Update `.github/copilot-instructions.md` (already auto-updated by setup script — review and trim if needed)
- [ ] T080 Final test run — execute all unit + api + integration + Cypress test suites; assert ≥ 80% coverage (ADR-003 / Constitution Principle II)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies, runs first
- **Phase 2 (Foundational)** → depends on Phase 1; **BLOCKS** all user stories
- **Phases 3–7 (User Stories)** → depend only on Phase 2; can run in parallel after Phase 2 completes
- **Phase 8 (Admin UI)** → depends on Phase 2 (models exist); can run in parallel with US phases (different files)
- **Phase 9 (Polish)** → depends on the user stories you intend to ship

### Within Each User Story

- Tests written **first** (must fail), then implementation, then re-run tests (must pass)
- Models → Services → Controllers → Schemas → Swagger registration
- Each US ends with checkpoint validation

### MVP Strategy

_Not applicable for this feature — all 80 tasks across all 9 phases will be implemented in this delivery._

---

## Parallel Opportunities

### Setup parallelism

T003, T004, T005 can run in parallel (different files).

### Foundational parallelism

- T006, T007, T008, T009 — model files independent (T010 depends on all 4)
- T015, T016, T017 — independent data/security files

### User Story parallelism (after Phase 2 ready)

All five user stories (US1–US5) have **independent test/impl files** so a team can split:

- Dev A → Phase 3 (US1) + Phase 8 admin UI
- Dev B → Phase 4 (US2 manager) + Phase 5 (US3 filters)
- Dev C → Phase 6 (US4 tags/sources) + Phase 7 (US5 dedup)

### Within-story parallelism

All `[P]` tests in a single story (e.g., T018–T023 in US1) can be authored concurrently by the same or different devs.

---

## Format Validation

- ✅ All tasks use `- [ ]` checkbox
- ✅ Sequential T001…T080 IDs
- ✅ `[P]` markers only on truly parallel tasks (different files, no in-flight deps)
- ✅ `[US1]`–`[US5]` story tags only on user-story phase tasks (Phases 3–7); Setup/Foundational/Admin UI/Polish have NO story tag
- ✅ Every task includes a clear file path
- ✅ Test tasks listed BEFORE implementation tasks within each user story
- ✅ Constitution v1.6.0 mandates tests (Principle II NON-NEGOTIABLE) — tests included throughout

---

## Summary

| Stat | Value |
|------|-------|
| Total tasks | 80 |
| Setup (Phase 1) | 5 |
| Foundational (Phase 2) | 12 |
| US1 (Phase 3) | 14 |
| US2 — Manager view (Phase 4) | 11 |
| US3 — Filters (Phase 5) | 8 |
| US4 — Tags/Sources (Phase 6) | 8 |
| US5 — Multi-phone dedup (Phase 7) | 5 |
| Admin UI (Phase 8) | 7 |
| Polish (Phase 9) | 10 |
| Parallelizable tasks | ~50 (`[P]` marker) |
| Independent test points | 5 user stories, each independently verifiable |

**Suggested MVP scope**: not applicable — the full 80-task scope ships together as a single delivery.
