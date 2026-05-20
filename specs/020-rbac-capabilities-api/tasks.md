# Tasks: RBAC Capabilities API

**Input**: Design documents from `/specs/020-rbac-capabilities-api/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/capabilities.yaml`, `quickstart.md`

**Tests**: Mandatory per `spec.md`, ADR-003, and constitution. This plan keeps the feature **API-only**: add unit tests plus real API endpoint coverage, **do not add Cypress UI tests** for this feature.
<!-- Cypress waiver: API-only feature — no Odoo UI surface exists. Constitution Principle II (E2E Cypress) is satisfied by bash API E2E tests in `test_capabilities_api.py` and the performance script in `test_us020_s4_performance.sh`. No Cypress exemption ADR required for headless-only endpoints. -->

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`)
- Every task includes exact file path(s)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the feature scaffolding before shared logic and tests are filled in.

- [X] T001 [P] Create source scaffolding in `18.0/extra-addons/thedevkitchen_apigateway/services/role_resolver.py`, `18.0/extra-addons/quicksol_estate/services/capability_service.py`, and `18.0/extra-addons/quicksol_estate/controllers/capabilities_controller.py`
- [X] T002 [P] Create test and seed scaffolding in `18.0/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py`, `18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py`, and `18.0/extra-addons/quicksol_estate/data/seed_capabilities_data.xml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared resolver, capability contract skeleton, and reusable fixtures that block all user stories.

- [X] T003 Implement the shared effective-role resolver in `18.0/extra-addons/thedevkitchen_apigateway/services/role_resolver.py`
- [X] T004 Refactor `18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py` to consume the shared resolver without changing the `/api/v1/me` response contract
- [X] T005 Implement `ALLOWED_ACTIONS`, `ALLOWED_SUBJECTS`, canonical ordering comments, and the projection skeleton in `18.0/extra-addons/quicksol_estate/services/capability_service.py`
- [X] T006 Register `18.0/extra-addons/quicksol_estate/data/seed_capabilities_data.xml` in `18.0/extra-addons/quicksol_estate/__manifest__.py`
- [X] T007 Populate reusable capability fixtures for 2 companies, 10 roles, a multi-role user, and minimal domain records in `18.0/extra-addons/quicksol_estate/data/seed_capabilities_data.xml` and `18.0/extra-addons/quicksol_estate/tests/api/utils.py`

**Checkpoint**: Shared role resolution, capability contract skeleton, and test fixtures are ready.

---

## Phase 3: User Story 1 - Bootstrap Safe UI Capabilities (Priority: P1) 🎯 MVP

**Goal**: Deliver `GET /api/v1/me/capabilities` so the frontend can bootstrap from `user` + `rules`.

**Independent Test**: Authenticate as a supported role, call `GET /api/v1/me/capabilities`, and verify the response returns exactly `user` and `rules` with valid auth guards.

### Tests for User Story 1

- [X] T008 [P] [US1] Write unit tests for resolver parity, deduplication, ordering, and whitelist enforcement in `18.0/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py`
- [X] T009 [P] [US1] Write real-endpoint API tests for 200 contract shape and 401/403 auth guards in `18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py`

### Implementation for User Story 1

- [X] T010 [US1] Implement ordered `get_rules()` projection and controller-facing service methods in `18.0/extra-addons/quicksol_estate/services/capability_service.py`
- [X] T011 [US1] Implement `GET /api/v1/me/capabilities` with `@require_jwt`, `@require_session`, `@require_company`, and `@trace_http_request` in `18.0/extra-addons/quicksol_estate/controllers/capabilities_controller.py`
- [X] T012 [US1] Register capability imports in `18.0/extra-addons/quicksol_estate/controllers/__init__.py` and `18.0/extra-addons/quicksol_estate/services/__init__.py`

**Checkpoint**: US1 is independently testable and delivers the MVP endpoint.

---

## Phase 4: User Story 2 - Render Role-Appropriate UX Without Leaking Internals (Priority: P1)

**Goal**: Return a conservative allow-list for all 10 roles with deny-by-omission and no RBAC internals leaked.

**Independent Test**: Compare owner, manager, agent, property_owner, and tenant responses and verify only safe rules are returned, in canonical order, with no internal artifacts.

### Tests for User Story 2

- [X] T013 [P] [US2] Add unit coverage for no-role fallback, allowed-subject enforcement, and allowed-action enforcement in `18.0/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py`
- [X] T014 [P] [US2] Add API matrix and non-leakage coverage for owner, agent, manager, property_owner, tenant, and 10-role smoke cases in `18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py`

### Implementation for User Story 2

- [X] T015 [US2] Encode the authoritative 10-role `ROLE_RULES` matrix in `18.0/extra-addons/quicksol_estate/services/capability_service.py` using the canonical order from `specs/020-rbac-capabilities-api/data-model.md`
- [X] T016 [US2] Tighten deny-by-omission payload shaping in `18.0/extra-addons/quicksol_estate/controllers/capabilities_controller.py` so XML IDs, group names, domains, model names, and security reasoning never appear in responses

**Checkpoint**: US2 is independently testable and the full conservative capability matrix is shipped.

---

## Phase 5: User Story 3 - Preserve Active Company Isolation and Existing Identity Contract (Priority: P1)

**Goal**: Enforce active-company isolation while keeping `/api/v1/me` unchanged.

**Independent Test**: Use mirrored users across two companies, verify `user.company_id` follows the active company, unauthorized company requests fail with 403, and `/api/v1/me` remains unchanged.

### Tests for User Story 3

- [X] T017 [P] [US3] Add API regression coverage for active-company selection, unauthorized-company 403s, cross-company payload isolation, and `/api/v1/me` parity in `18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py`
- [X] T018 [P] [US3] Extend mirrored company-B fixtures, minimal domain records, and multi-role parity helpers in `18.0/extra-addons/quicksol_estate/data/seed_capabilities_data.xml` and `18.0/extra-addons/quicksol_estate/tests/api/utils.py`

### Implementation for User Story 3

- [X] T019 [US3] Finalize active-company payload handling and generic 401/403/500 responses in `18.0/extra-addons/quicksol_estate/controllers/capabilities_controller.py`

**Checkpoint**: US3 is independently testable and multi-company isolation is verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish API documentation, Postman deliverables, versioning, and release validation.

- [X] T020 [P] Add DB-driven Swagger endpoint metadata and response schema for `/api/v1/me/capabilities` in `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml`
- [X] T021 [P] Update the main Postman collection from `docs/postman/quicksol_api_v1.32_postman_collection.json` to `docs/postman/quicksol_api_v1.33_postman_collection.json` with Authentication/User Management coverage for `/api/v1/me/capabilities`
- [X] T022 [P] Bump `quicksol_estate` to version `18.0.5.0.0` and verify `18.0/extra-addons/quicksol_estate/__manifest__.py` still loads the new capability seed and endpoint data
- [X] T023 Update `specs/020-rbac-capabilities-api/quickstart.md` with the final execution sequence, Postman collection version, Swagger sync step, and explicit API-only/no-Cypress validation note
- [X] T024 [P] Migrate all inline role-resolution maps across the codebase to consume `role_resolver.resolve_role(user)` — eliminating duplicate group→role dictionaries in three files:
  - `18.0/extra-addons/thedevkitchen_estate_goals/controllers/goals_controller.py`: remove `_GROUP_TO_PROFILE` constant and `_get_caller_profile()` function; replace all call sites with `role_resolver.resolve_role(user)`.
  - `18.0/extra-addons/thedevkitchen_estate_goals/services/goals_report_service.py`: remove `_GROUP_PROFILE_MAP` constant; replace the resolution loop at line 494 with `role_resolver.resolve_role(user).capitalize()` (this service uses Title-case labels for report display; `.capitalize()` is correct for all 8 single-word roles in scope — compound roles `property_owner`/`tenant` are not present in goals context).
  - `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py`: remove the inline `group_to_profile` fallback dict (lines 375–395); replace with `role_resolver.resolve_role(user) or 'unknown'` as the fallback — the primary partner_id lookup via `thedevkitchen.estate.profile` remains unchanged.
  - **Do NOT touch**: `invite_service.py` (`INVITE_AUTHORIZATION`, `PROFILE_TO_GROUP` are authorization matrices, not role resolution); `property_api.py`, `sale_api.py`, `agent_api.py`, `credit_check_service.py` (use `has_group()` for point-in-time access-control decisions, not role label resolution).
- [X] T026 [P] Validate SC-005 performance: run 100 sequential `GET /api/v1/me/capabilities` requests against the running Odoo instance in `18.0/integration_tests/test_us020_s4_performance.sh`; compute p95 response time; assert p95 < 1000 ms and exit non-zero if the threshold is exceeded
- [X] T025 Run the feature validation steps from `specs/020-rbac-capabilities-api/quickstart.md` and the repository quality gate in `18.0/lint.sh`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 -> Phase 2**: Setup must finish before shared resolver, contract skeleton, and fixtures are finalized
- **Phase 2 -> Phase 3**: US1 depends on shared resolver, capability skeleton, and seed fixtures
- **Phase 3 -> Phase 4**: US2 depends on the working endpoint/service from US1
- **Phase 4 -> Phase 5**: US3 depends on the working endpoint and full matrix behavior already in place
- **Phase 6**: Depends on all user stories being complete
- **T024 (role-map migration) → T003**: `role_resolver.py` must be created by T003 before T024 imports `resolve_role` from it; always execute T003 first

### User Story Dependencies

- **US1**: Starts after Foundational; no dependency on other stories
- **US2**: Depends on US1 because it fills the final authoritative matrix in the same service/controller surface
- **US3**: Depends on US1 and is sequenced after US2 here to avoid controller/test-file conflicts

### Within Each User Story

- Tests before implementation
- Shared service logic before controller wiring
- Controller behavior before documentation/versioning
- Story must pass its independent test before moving on

---

## Parallel Opportunities

- **Setup**: `T001` and `T002`
- **US1**: `T008` and `T009`
- **US2**: `T013` and `T014`
- **US3**: `T017` and `T018`
- **Polish**: `T020`, `T021`, `T022`, `T024`, and `T026`

---

## Parallel Example: User Story 1

```bash
Task: "T008 [US1] Write unit tests in 18.0/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py"
Task: "T009 [US1] Write API tests in 18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py"
```

## Parallel Example: User Story 2

```bash
Task: "T013 [US2] Add unit coverage in 18.0/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py"
Task: "T014 [US2] Add API matrix coverage in 18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py"
```

## Parallel Example: User Story 3

```bash
Task: "T017 [US3] Add company-isolation API tests in 18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py"
Task: "T018 [US3] Extend fixtures in 18.0/extra-addons/quicksol_estate/data/seed_capabilities_data.xml and 18.0/extra-addons/quicksol_estate/tests/api/utils.py"
```

---

## Implementation Strategy

### MVP First

1. Complete **Phase 1: Setup**
2. Complete **Phase 2: Foundational**
3. Complete **Phase 3: US1**
4. Validate `GET /api/v1/me/capabilities` contract and auth guards
5. Stop for MVP review

### Incremental Delivery

1. Ship MVP endpoint (`US1`)
2. Add full conservative 10-role matrix and non-leakage rules (`US2`)
3. Add company-isolation and `/api/v1/me` regression coverage (`US3`)
4. Finish Swagger, Postman, version bump, and validation (`Phase 6`)

### Scope Guard

- This feature remains **API-only**
- **No new Cypress files** should be added under `cypress/e2e/`
- Postman and Swagger are required deliverables in the final phase

---

## Summary

- **Target path**: `/opt/homebrew/var/www/realestate/odoo-docker/specs/020-rbac-capabilities-api/tasks.md`
- **Total tasks**: 26
- **Task count by user story**:
  - **US1**: 5
  - **US2**: 4
  - **US3**: 3
- **Parallel opportunities**: 13 tasks marked `[P]`
- **Independent test criteria**:
  - **US1**: endpoint returns exactly `user` + `rules` with valid auth guards
  - **US2**: full 10-role conservative matrix is ordered, safe, and non-leaking
  - **US3**: active-company isolation holds and `/api/v1/me` remains unchanged
- **Suggested MVP scope**: Phases 1-3 only
- **Format validation**: All tasks use the required checklist format with checkbox, sequential ID, optional `[P]`, required `[USx]` on story tasks, and exact file path(s)

**ADR/constitution gap handling included**:
- shared resolver parity with `/api/v1/me`
- authoritative capability-matrix work in `capability_service.py`
- DB-driven Swagger deliverable
- ADR-016-compliant Postman update of the main collection
- explicit API-only/no-Cypress validation for this feature
- T024: cross-module role-map deduplication — goals_controller, goals_report_service, invite_controller migrated to shared resolver
- T026: SC-005 performance gate (p95 < 1000 ms assertion via `test_us020_s4_performance.sh`)
