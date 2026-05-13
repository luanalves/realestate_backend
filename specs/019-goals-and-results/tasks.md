# Tasks: Goals and Results (Metas e Resultados — Feature 019)

**Input**: Design documents from `/specs/019-goals-and-results/`
**Branch**: `019-goals-and-results`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ (5 files) | quickstart.md ✅

**Module**: `thedevkitchen_estate_goals`  
**Model**: `thedevkitchen.estate.goal`  
**User Stories**: US1 (P1) — Goal CRUD · US2 (P2) — Agent Self-View · US3 (P3) — Team Report · US4 (P4) — Admin UI  
**Phase Mapping** (plan.md → tasks.md): P1 Foundation → Phases 1+2 | P2+P3 Achievement+API → Phases 3+4+5 | P4 Admin UI → Phase 6 | P5+P6 Testing+Docs → Phase 7

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (independent file, no incomplete dependencies)
- **[US1..US4]**: Story label — matches user stories from spec.md
- All paths relative to repo root unless otherwise noted

---

## Phase 1: Setup

**Purpose**: Create module skeleton — must complete before any story work.

- [ ] T001 Create module directory `18.0/extra-addons/thedevkitchen_estate_goals/` with `__init__.py`
- [ ] T002 Create `18.0/extra-addons/thedevkitchen_estate_goals/__manifest__.py` declaring name, version, author, depends (`quicksol_estate`, `thedevkitchen_apigateway`), data files, installable
- [ ] T003 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/models/__init__.py`
- [ ] T004 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/controllers/__init__.py`
- [ ] T005 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/services/__init__.py`
- [ ] T006 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/tests/__init__.py` and `tests/unit/__init__.py`

**Checkpoint**: Module directory structure exists; `__manifest__.py` is valid Python.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model, security files, and Swagger data — MUST be complete before any user story endpoint is implemented.

**⚠️ CRITICAL**: No US1–US4 work can begin until this phase is complete.

- [ ] T007 Implement `thedevkitchen.estate.goal` model in `18.0/extra-addons/thedevkitchen_estate_goals/models/estate_goal.py`:
  - Fields: `active`, `company_id`, `user_id`, `year`, `month`, `metric_type`, `operation_type`, `target_count`, `target_vgv`, `currency_id`
  - `_sql_constraints`: unique(user_id, company_id, year, month, metric_type, operation_type) + CHECK constraints for year ≥ 2000, month 1-12, target_count ≥ 0, target_vgv ≥ 0
  - `@api.constrains` for VGV applicability (only captacao/propostas/fechamento)
  - `_auto_init()` to create composite index `(company_id, year, month)` via raw SQL (Odoo 18.0 has no `_indexes` attribute)
  - `_name = 'thedevkitchen.estate.goal'`

- [ ] T008 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/security/ir.model.access.csv` with read ACL for `base.group_user` and full ACL for `base.group_system`

- [ ] T009 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/security/record_rules.xml`:
  - Rule 1 (all users): company isolation `[('company_id', '=', user.company_id.id)]`
  - Rule 2 (agent group): own-only restriction `[('user_id', '=', user.id)]`

- [ ] T010 [P] Create `18.0/extra-addons/thedevkitchen_estate_goals/data/api_endpoints_data.xml` seeding all 5 endpoints in `thedevkitchen_api_endpoint` table:
  - `POST /api/v1/goals` — Create Goal
  - `PUT /api/v1/goals/<id>` — Update Goal
  - `DELETE /api/v1/goals/<id>` — Delete Goal
  - `GET /api/v1/goals` — List Goals
  - `GET /api/v1/goals/report` — Goals Report

- [ ] T011 Update `18.0/extra-addons/thedevkitchen_estate_goals/__manifest__.py` to include `security/ir.model.access.csv`, `security/record_rules.xml`, `data/api_endpoints_data.xml` in the `data` list

**Checkpoint**: Module installs cleanly (`docker compose exec odoo odoo --update thedevkitchen_estate_goals --stop-after-init`). Table `thedevkitchen_estate_goal` exists in DB. No import errors.

---

## Phase 3: User Story 1 — Manager Sets Monthly Goal (Priority: P1)

**Goal**: Managers can create, update, list, and soft-delete goals via REST API. RBAC enforced (403 for agents). Unique constraint prevents duplicates (409). Multitenancy isolation enforced.

**Independent Test**:
```bash
bash integration_tests/test_us019_s1_create_goals.sh
bash integration_tests/test_us019_s2_goal_lifecycle.sh
```
Expected: 201 on create, 200 on update/list, 200 on delete, 409 on duplicate, 403 for agent role.

### Implementation for User Story 1

- [ ] T012 [US1] Create `18.0/extra-addons/thedevkitchen_estate_goals/controllers/goals_controller.py` with class `GoalsController(http.Controller)` and stub routes for all 5 endpoints decorated with `@require_jwt`, `@require_session`, `@require_company`

- [ ] T013 [US1] Implement `POST /api/v1/goals` in `goals_controller.py`:
  - Parse and validate request body (user_id, year, month, metric_type, operation_type, target_count, target_vgv)
  - RBAC check: 403 if caller is not Owner/Director/Manager
  - Call `env['thedevkitchen.estate.goal'].create({...})`
  - Return 201 with goal data + HATEOAS links per ADR-007
  - Return 409 on `IntegrityError` (unique constraint); 422 on `ValidationError`; 400 on missing fields
  - **Exception handler pattern** (apply to all 5 endpoints): wrap each handler body in `try/except Exception as e`; catch-all returns `{"error": "internal_error", "detail": "An unexpected error occurred"}` with HTTP 500; log full traceback via `_logger.exception("goals endpoint error: %s", e)` — never expose stack trace or DB schema details to caller (SEC-10)

- [ ] T014 [US1] Implement `PUT /api/v1/goals/<int:goal_id>` in `goals_controller.py`:
  - Look up goal by ID with company scope (404 if not found or inactive)
  - RBAC check: 403 if caller is not Owner/Director/Manager
  - Update `target_count` and/or `target_vgv` (identity fields immutable)
  - Return 200 with updated goal data + HATEOAS links

- [ ] T015 [US1] Implement `DELETE /api/v1/goals/<int:goal_id>` in `goals_controller.py`:
  - Look up goal by ID with company scope (404 if not found or already inactive)
  - RBAC check: 403 if caller is not Owner/Director/Manager
  - Set `active=False` (never hard-delete)
  - Return 200 with `{"success": true, "message": "Goal archived successfully", "links": [...]}`

- [ ] T016 [US1] Implement `GET /api/v1/goals` in `goals_controller.py`:
  - Parse optional query params: `user_id`, `year`, `month`, `metric_type`, `operation_type`
  - Build ORM domain (always include `active=True`, company scope from `@require_company`)
  - **RBAC** (SEC-2, SEC-3):
    - Receptionist and Prospector profiles: return 403 immediately
    - Agent: if `user_id` param is explicitly provided AND does not match `request.env.user.id` → return 403; if `user_id` param is absent, default to own user (`user_id = request.env.user.id`)
    - Owner/Director/Manager: no restriction on `user_id` param
  - Return 200 with `{"count": N, "results": [...], "links": [...]}`

- [ ] T017 [US1] Write unit tests in `18.0/extra-addons/thedevkitchen_estate_goals/tests/unit/test_estate_goal.py`:
  - `test_goal_unique_constraint()` — IntegrityError on duplicate (user, year, month, metric, operation)
  - `test_goal_target_count_non_negative()` — ValidationError on target_count < 0
  - `test_goal_target_count_zero_is_valid()` — target_count=0 creates successfully (FR1.6 boundary)
  - `test_goal_month_range_valid()` — ValidationError on month=0 and month=13
  - `test_goal_year_min_2000()` — ValidationError on year=1999
  - `test_vgv_forbidden_for_visitas_novos_clientes()` — ValidationError when target_vgv set on visitas or novos_clientes
  - `test_goal_soft_delete()` — active=False after write; record still in DB

- [ ] T018 [US1] Write integration test `integration_tests/test_us019_s1_create_goals.sh`:
  - Obtain JWT as Manager
  - POST goal → assert 201 + id in response
  - POST same goal again → assert 409
  - POST as Agent → assert 403
  - POST with month=13 → assert 400 or 422
  - GET list as Agent (no `user_id` param) → assert 200 (own data only)
  - GET list as Agent with own `user_id` param → assert 200
  - GET list as Agent with another user's `user_id` param → assert 403 (SEC-3)

- [ ] T019 [US1] Write integration test `integration_tests/test_us019_s2_goal_lifecycle.sh`:
  - Create goal → GET list (assert present) → PUT to update target → GET list (assert updated) → DELETE → GET list (assert gone from active)

**Checkpoint**: US1 is fully functional. Managers can manage goals via API. Agents receive 403. Duplicates return 409. Deleted goals are soft-deleted.

---

## Phase 4: User Story 2 — Agent Views Own Results Report (Priority: P2)

**Goal**: Agent can query `GET /api/v1/goals/report?user_id={self.id}&year=…&month=…` and see their own metrics. 403 if `user_id` refers to another user. Achievement data computed from existing entities.

**Independent Test**:
```bash
bash integration_tests/test_us019_s3_report_single_month.sh
```
Expected: 200 with per-metric rows (target, achievement, completion_pct). Agent gets 403 when requesting another user's data.

### Implementation for User Story 2

- [ ] T020 [US2] Create `18.0/extra-addons/thedevkitchen_estate_goals/services/goals_report_service.py` with class `GoalsReportService` and method `compute_report(env, company_id, user_ids, date_from, date_to, operation_type)` returning a dict
  - **Guard** (SEC-1): at the top of `compute_report()`, if `not user_ids: return {"users": [], "totals": {metric: {"conquista": 0, "meta_count": None, ...} for metric in METRICS}, "period": ...}` — prevents `IN ()` SQL syntax error; PostgreSQL rejects empty tuple literals and raises `psycopg2.ProgrammingError`

- [ ] T021 [US2] Implement `_query_captacao(env, company_id, user_ids, date_from, date_to, operation_type)` in `goals_report_service.py`:
  - Raw SQL joining `real_estate_property` → `real_estate_agent` → `res.users`
  - Filter by `for_sale`/`for_rent` booleans based on `operation_type`
  - Return `{user_id: {"count": N, "vgv": V}}` per researched D003 SQL pattern

- [ ] T022 [US2] Implement `_query_novos_clientes(env, company_id, user_ids, date_from, date_to, operation_type)` in `goals_report_service.py`:
  - Raw SQL on `real_estate_service` with `create_date` in range
  - Filter by `operation_type` field directly (`= 'sale'` or `= 'rent'`; no filter for `all`)
  - Attribution: `agent_id` is direct FK to `res.users` (D001)
  - Return `{user_id: {"count": N}}`

- [ ] T023 [US2] Implement `_query_visitas(env, company_id, user_ids, date_from, date_to, operation_type)` in `goals_report_service.py`:
  - Raw SQL joining `real_estate_service` → `mail_message` → `mail_tracking_value` → `ir_model_fields`
  - Filter: `imf.name = 'stage'`, `mtv.new_value_char = 'visit'`, `mtv.create_date` in range
  - Use `COUNT(DISTINCT rs.id)` per D002 key detail
  - Return `{user_id: {"count": N}}`

- [ ] T024 [US2] Implement `_query_propostas(env, company_id, user_ids, date_from, date_to, operation_type)` in `goals_report_service.py`:
  - Raw SQL on `real_estate_proposal` → `real_estate_agent` → `res.users`
  - Map `operation_type='rent'` → `proposal_type='lease'` (D004 mapping constant `OP_TYPE_TO_PROPOSAL_TYPE`)
  - Return `{user_id: {"count": N, "vgv": V}}`

- [ ] T025 [US2] Implement `_query_fechamento(env, company_id, user_ids, date_from, date_to, operation_type)` in `goals_report_service.py`:
  - ⚠️ **Before implementing**: run `\d real_estate_proposal` in DB to confirm `service_id` FK exists; if absent, document fallback join strategy in research.md D004-addendum and update the JOIN accordingly
  - Raw SQL joining `real_estate_service` (stage→`won` via `mail_tracking_value`) + LEFT JOIN `real_estate_proposal` (state=`accepted`, linked via `service_id`)
  - Return `{user_id: {"count": N, "vgv": V}}` — VGV from accepted proposals linked to won services

- [ ] T026 [US2] Implement `_resolve_period(year, month, date_from, date_to)` helper in `goals_report_service.py`:
  - Single-month mode: year + month → date_from = first day, date_to = first day of next month
  - Accumulated mode: parse ISO 8601 date strings → datetime with UTC midnight
  - Raise `ValidationError` if year missing in single-month mode; if date_to without date_from
  - Raise `ValidationError` if `(date_to_dt - date_from_dt).days > 366` — maximum 12-month range; prevents DoS from open-ended date scans over `mail.tracking.value` (SEC-6)

- [ ] T027 [US2] Implement `_compute_user_row(user_id, goals, achievements)` in `goals_report_service.py`:
  - Map goals to metric dict; merge with achievement data
  - Compute `completion_pct = (achievement / target) * 100` per metric (null if no goal)
  - Determine `goal_status`: `complete` / `in_progress` / `no_goals` per D009 rules
  - Resolve `profile` string: check `user.groups_id` against known group XML IDs in descending hierarchy (`group_real_estate_owner` → `group_real_estate_director` → `group_real_estate_manager` → `group_real_estate_agent`); return first match as label (`"Owner"` / `"Director"` / `"Manager"` / `"Agent"`) or `null` if none match

- [ ] T028 [US2] Implement `GET /api/v1/goals/report` endpoint in `goals_controller.py`:
  - Parse query params: `year`, `month`, `date_from`, `date_to`, `operation_type`, `user_id`
  - **RBAC** (SEC-2, SEC-3):
    - Receptionist and Prospector profiles: return 403 immediately
    - Agent: if `user_id` param is provided and does not match `request.env.user.id` → 403; if absent, scope to own user
    - Manager/Owner/Director: can query any user in company or full company
  - Resolve `user_ids` list from company scope (filtered by `user_id` param if provided)
  - Hard cap: count `user_ids`; return 422 if > 200 (D006)
  - Call `GoalsReportService.compute_report(...)` and return 200 with response shape per spec

- [ ] T029 [US2] Write unit tests in `test_estate_goal.py`:
  - `test_resolve_period_single_month()` — year+month → correct date range boundaries
  - `test_resolve_period_accumulated()` — date_from/date_to → correct datetimes; year ignored
  - `test_resolve_period_missing_year_raises()` — ValidationError when year absent in single-month mode
  - `test_goal_status_complete_all_set_goals_met()` — all set goals met → `complete`
  - `test_goal_status_no_goals_zero_goals_set()` — zero goals → `no_goals` (not `complete`)
  - `test_goal_status_null_metrics_neutral()` — unset metrics don't affect `complete` status
  - `test_operation_type_all_excluded_from_filtered_report()` — `all`-goals absent from `sale` view
  - `test_totals_metric_aggregation_sums_across_users()` — two users each with captacoes.conquista=2 → totals.captacoes.conquista=4; null meta_count handled correctly (null if all null, sum if any non-null)

- [ ] T047 [P] Write unit tests for all 5 SQL query methods in `test_estate_goal.py`:
  - `test_query_captacao_sale_counts_for_sale_properties()` — `for_sale=True` property attributed to user appears in captacao count
  - `test_query_captacao_rent_counts_for_rent_properties()` — `for_rent=True` property counted; sale property excluded
  - `test_query_novos_clientes_filters_by_operation_type()` — service with `operation_type='sale'` counted; rent excluded
  - `test_query_visitas_counts_distinct_services()` — service with stage→`visit` tracking record counted once (DISTINCT)
  - `test_query_propostas_maps_rent_to_lease()` — `operation_type='rent'` queries `proposal_type='lease'` (OP_TYPE_TO_PROPOSAL_TYPE mapping)
  - `test_query_fechamento_vgv_from_accepted_proposal()` — won service with accepted proposal returns VGV; no proposal returns VGV=0
  - `test_query_methods_exclude_other_company_records()` — records from company B not included in company A queries

- [ ] T048 [P] Create seed data script `integration_tests/seeds/019_goals_seed.py` (create `integration_tests/seeds/` directory if absent):
  - 2 companies: `Imobiliária Seed A (019)` and `Imobiliária Seed B (019)`
  - 5 users with `seed_019_` prefix logins (owner, director, manager, agent per company A; owner_b for isolation)
  - 2 `for_sale` properties + 1 `for_rent` property attributed to agent_a (May 2026)
  - 3 services created in May 2026 by agent_a; 1 with `visit` tracking, 1 with `won` tracking
  - 2 proposals by agent_a (May 2026, `proposal_type='sale'`); 1 accepted linked to won service
  - 6 goals for agent_a (May 2026) per spec Seed Data section
  - Idempotent: check-before-create using `search([('login', '=', ...)])` for users

- [ ] T030 [US2] Write integration test `integration_tests/test_us019_s3_report_single_month.sh`:
  - Create goal + seed a service record, a property record for the agent
  - GET report?year=…&month=… as Agent (own user_id) → assert 200, metric rows present
  - GET report with another user_id as Agent → assert 403
  - GET report with no goals set → assert `goal_status=no_goals`, `target=null`

**Checkpoint**: US2 functional. Agent can see own report. Achievement SQL queries return correct counts. 403 enforced for cross-user access.

---

## Phase 5: User Story 3 — Manager Views Team Report (Priority: P3)

**Goal**: Manager can query the full team report with filters (operation_type, user_id, goal_status). Response includes `totals` object. `operation_type=all` goals excluded from `sale`/`rent`-filtered views.

**Independent Test**:
```bash
bash integration_tests/test_us019_s4_report_date_range.sh
bash integration_tests/test_us019_s5_rbac_matrix.sh
```
Expected: 200 with all company users, `totals` present, filters applied correctly.

### Implementation for User Story 3

- [ ] T031 [US3] Implement `_compute_totals(user_rows)` in `goals_report_service.py`:
  - For each of the 5 metrics: sum `conquista` across all user rows; sum `meta_count` only for rows where it is non-null (null = no goal set)
  - For VGV metrics (captacoes, propostas, fechamento): sum `conquista_vgv` and `meta_vgv` (null if ALL users have null meta_vgv for that metric)
  - `meta_count` in totals: `null` if ALL users have null for that metric; otherwise sum of non-null values only
  - Return dict matching spec `totals` JSON shape: `{"captacoes": {"conquista": N, "meta_count": X|null, "conquista_vgv": V, "meta_vgv": W|null}, ...}`

- [ ] T032 [US3] Implement `operation_type` exclusion logic in `compute_report()`:
  - When `operation_type='sale'` or `='rent'`: filter goal lookup to `goal.operation_type = param` (excludes `all` goals per D007)
  - When `operation_type='all'`: include all goals regardless of their `operation_type`

- [ ] T033 [US3] Implement accumulated period mode in `compute_report()`:
  - When `date_from` + `date_to` provided: sum goals across all months in the range (multiple monthly goal records)
  - Sum achievement queries across the full date window (single SQL call, not per-month)
  - `year`/`month` ignored when `date_from`/`date_to` present

- [ ] T034 [US3] Extend `GET /api/v1/goals/report` in `goals_controller.py` with manager-scope user resolution:
  - When no `user_id` param: resolve `user_ids` = all active `res.users` in company (excluding system users)
  - Apply 200-user hard cap before executing SQL (422 with count in error message per spec error table)
  - After `GoalsReportService.compute_report()`: apply `goal_status` filter param if provided
    - `goal_status=complete` → keep rows where `row['goal_status'] == 'complete'`
    - `goal_status=incomplete` → keep rows where `row['goal_status'] in ('in_progress', 'no_goals')`
  - Recompute `totals` on the filtered list (call `_compute_totals()` again after filtering)
  - Return full `users` list + `totals` + `period` in response

- [ ] T045 [US3] Implement `profile` filter in `goals_report_service.py` and `goals_controller.py`:
  - Parse `profile` query param (full group XML ID, e.g. `quicksol_estate.group_real_estate_agent`)
  - In controller: **validate `profile` format before `env.ref()`** (SEC-9): must match regex `^[a-z0-9_]+\.[a-z0-9_]+$` and be ≤ 128 chars; return 400 immediately if not (`{"error": "bad_request", "detail": "Invalid profile format. Expected: module.xml_id"}`)
  - In controller: resolve group record via `env.ref(profile_param)`; 400 if XML ID not found
  - In `compute_report()`: filter `user_ids` to only users belonging to the resolved group (`user.groups_id`)
  - Add `profile` to the `filters` block in the response JSON
  - Extend T036 integration test: GET report?profile=quicksol_estate.group_real_estate_agent → assert only agents in response

- [ ] T035 [US3] Write integration test `integration_tests/test_us019_s4_report_date_range.sh`:
  - Set up goals for Jan + Feb + Mar
  - GET report?date_from=2026-01-01&date_to=2026-03-31 → assert goals summed across 3 months
  - Assert `period.date_from` = "2026-01-01", `period.date_to` = "2026-03-31"
  - Assert `year`/`month` absent or null in response period

- [ ] T036 [US3] Write integration test `integration_tests/test_us019_s5_rbac_matrix.sh`:
  - Login as Owner → GET report → 200 (all company users)
  - Login as Manager → GET report → 200 (all company users)
  - Login as Agent → GET report without user_id → 200 (own data only, single user)
  - Login as Agent → GET report?user_id=other → 403
  - GET report?operation_type=sale → goals with `operation_type=all` absent from targets

**Checkpoint**: US3 functional. Manager sees full team with totals. Date-range accumulation correct. `all`-goals correctly excluded from filtered views.

---

## Phase 6: User Story 4 — Admin Manages Goals in Odoo UI (Priority: P4)

**Goal**: Odoo admin can manage goals from Odoo back-office list and form views. No JS errors. Views use Odoo 18.0 syntax (`<list>`, no `attrs`).

**Independent Test**:
```bash
# Manual: open http://localhost:8069/web as admin
# Navigate to: Real Estate → Metas
# Assert: list loads, form opens, create works
```

### Implementation for User Story 4

- [ ] T037 [US4] Create `18.0/extra-addons/thedevkitchen_estate_goals/views/estate_goal_views.xml`:
  - List view (`<list>`) with columns: user_id, year, month, metric_type, operation_type, target_count, target_vgv, active
  - Form view with all fields; `target_vgv` visible only for captacao/propostas/fechamento (use `invisible` attribute)
  - Menu item under Real Estate app: "Metas" linking to list action
  - Action `ir.actions.act_window` with proper domain (`active=True` default)
  - Views must use `<list>` (not `<tree>`); no `attrs` attribute; `optional="show"` for less common columns

- [ ] T038 [US4] Update `__manifest__.py` to include `views/estate_goal_views.xml` in the `data` list

- [ ] T039 [US4] Write Cypress E2E test `18.0/cypress/e2e/goals/test_goals_admin_ui.cy.js`:
  - `test_goals_menu_loads_without_errors()` — navigate to Metas menu, no Odoo "Oops!" screen, DevTools console zero errors
  - `test_goals_list_view_loads()` — list renders with expected column headers
  - `test_goals_form_create()` — open form, fill required fields, save → record appears in list

**Checkpoint**: US4 functional. Admin can open "Metas" menu in Odoo UI. List and form views render without errors. Create workflow works.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration test runner, multitenancy validation, Swagger verification, install validation.

- [ ] T040 [P] Write `integration_tests/test_us019_s6_multitenancy.sh`:
  - Create goals as Manager of Company A
  - Login as Manager of Company B → GET /api/v1/goals → assert Company A goals not visible
  - GET /api/v1/goals/report as Company B → assert Company A users not in response

- [ ] T041 [P] Write `integration_tests/run_feature019_tests.sh` orchestrator script that runs all 6 integration tests in order and reports pass/fail per test

- [ ] T042 Verify Swagger registration post-install:
  - `curl -s http://localhost:8069/api/docs/openapi.json | python3 -c "import sys,json; paths=[p for p in json.load(sys.stdin)['paths'] if '/api/v1/goals' in p]; print(len(paths), paths)"`
  - Assert output count = 5 (all 5 route paths present)
  - If missing: check `data/api_endpoints_data.xml` XML validity and re-run `--update`

- [ ] T043 [P] Run full unit test suite and confirm zero failures:
  - `docker compose exec odoo odoo -d realestate_test --test-enable --test-tags thedevkitchen_estate_goals --stop-after-init --no-http`
  - Fix any failures before marking tasks complete

- [ ] T044 [P] Run full integration test suite and confirm zero failures:
  - `bash integration_tests/run_feature019_tests.sh`
  - Fix any failures before marking tasks complete

- [ ] T046 [P] Generate Postman collection for Feature 019 via `thedevkitchen.postman` agent:
  - Run agent: all 5 endpoints (`POST /api/v1/goals`, `PUT /api/v1/goals/<id>`, `DELETE /api/v1/goals/<id>`, `GET /api/v1/goals`, `GET /api/v1/goals/report`)
  - Output: `docs/postman/feature019_goals_results_v1.0_postman_collection.json` (ADR-016)
  - Include OAuth token flow, session management, auto-save token scripts, and GET/POST header conventions

---

## Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundation — T007-T011)
            ├── Phase 3 / US1 (Goal CRUD API — T012-T019)
            │       └── Phase 4 / US2 (Agent Self-Report — T020-T030)
            │               └── Phase 5 / US3 (Team Report — T031-T036)
            └── Phase 6 / US4 (Admin UI — T037-T039)  ← can run in parallel with US1-US3
Phase 7 (Polish) ← after all phases complete
```

**Parallel opportunities within phases**:
- T003, T004, T005, T006 (Phase 1) — all independent init files
- T008, T009, T010 (Phase 2) — security + data files independent of each other
- T021, T022, T023, T024, T025, T026 (Phase 4) — each SQL query method independent
- T040, T041, T043, T044 (Phase 7) — independent validations

---

## Implementation Strategy

Implement phases in order: Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7.

US4 (Admin UI) can be developed in parallel with US1–US3 once Phase 2 is complete.

---

## Task Summary

| Phase | User Story | Tasks | Parallel Opportunities |
|-------|-----------|-------|----------------------|
| Phase 1: Setup | — | T001-T006 | T003, T004, T005, T006 |
| Phase 2: Foundation | — | T007-T011 | T008, T009, T010 |
| Phase 3 | US1 (P1) | T012-T019 | T017-T018 (tests) |
| Phase 4 | US2 (P2) | T020-T030, T047, T048 | T021-T026 (query methods), T047, T048 |
| Phase 5 | US3 (P3) | T031-T036, T045 | T035-T036 (tests) |
| Phase 6 | US4 (P4) | T037-T039 | — |
| Phase 7 | Polish | T040-T044, T046 | T040, T041, T043, T044, T046 |
| **Total** | | **48 tasks** | |

**Format validation**: All 48 tasks follow `- [ ] T### [P?] [US?] Description with file path` format.
