# Tasks: Tenant, Lease & Sale API Endpoints

**Input**: Design documents from `/specs/008-tenant-lease-sale-api/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (tenant-api.yaml, lease-api.yaml, sale-api.yaml), quickstart.md

**Tests**: Included — SC-010 mandates "100% of validation constraints covered by automated tests" and Constitution Principle II requires ≥80% test coverage.

**Organization**: Tasks grouped by user story (5 stories from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Module root**: `18.0/extra-addons/quicksol_estate/`
- **Integration tests**: `integration_tests/`
- **E2E tests**: `cypress/e2e/`
- **Postman**: `docs/postman/`
- **Contracts**: `specs/008-tenant-lease-sale-api/contracts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module initialization — version bump and import wiring

- [X] T001 [P] Bump module version in 18.0/extra-addons/quicksol_estate/__manifest__.py
- [X] T002 [P] Add `lease_renewal_history` import to 18.0/extra-addons/quicksol_estate/models/__init__.py
- [X] T003 [P] Add `tenant_api`, `lease_api`, `sale_api` imports to 18.0/extra-addons/quicksol_estate/controllers/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: New model and security rules that MUST exist before any controller can function

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create `real.estate.lease.renewal.history` model in 18.0/extra-addons/quicksol_estate/models/lease_renewal_history.py per data-model.md (fields: lease_id, previous_end_date, previous_rent_amount, new_end_date, new_rent_amount, renewed_by_id, reason, renewal_date)
- [X] T005 [P] Add access rules for `real.estate.lease.renewal.history` model in 18.0/extra-addons/quicksol_estate/security/ir.model.access.csv (read for base.group_user, full CRUD for base.group_system)
- [X] T006 [P] Add company isolation record rule for `real.estate.lease.renewal.history` in 18.0/extra-addons/quicksol_estate/security/record_rules.xml (filter via parent lease's company_ids)

**Checkpoint**: Foundation ready — module upgradeable with new model registered, user story implementation can now begin

---

## Phase 3: User Story 1 — Tenant CRUD Management (Priority: P1) 🎯 MVP

**Goal**: Complete tenant registry with CRUD operations, company isolation, and RBAC agent filtering

**Independent Test**: Create tenant → list tenants → get by ID → update → archive → verify hidden from default list

**FRs covered**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-030, FR-031, FR-032, FR-033, FR-034, FR-037

### Implementation for User Story 1

- [X] T007 [P] [US1] Add `active` (Boolean, default=True), `deactivation_date` (Datetime), `deactivation_reason` (Text) fields to 18.0/extra-addons/quicksol_estate/models/tenant.py per data-model.md
- [X] T008 [P] [US1] Add `TENANT_CREATE_SCHEMA` (required: name; optional: phone, email, occupation, birthdate) and `TENANT_UPDATE_SCHEMA` to 18.0/extra-addons/quicksol_estate/controllers/utils/schema.py per contracts/tenant-api.yaml
- [X] T009 [US1] Create 18.0/extra-addons/quicksol_estate/controllers/tenant_api.py with 5 endpoints: GET /tenants (paginated list with company filter), POST /tenants (create with schema validation), GET /tenants/{id} (detail with lease refs), PUT /tenants/{id} (update), DELETE /tenants/{id} (soft archive). Include: triple auth decorators, HATEOAS links, RBAC agent filtering (transitive via property assignment per R3), company isolation per FR-030. Reference: owner_api.py pattern and contracts/tenant-api.yaml
- [X] T010 [US1] Create integration test in integration_tests/test_us8_s1_tenant_crud.sh — cover: create tenant (201), list with company filter (200), get by ID (200), update phone/email (200), archive (200), verify archived hidden from default list, multi-tenancy isolation (Company A cannot see Company B tenants), validation errors (missing name, invalid email)
- [X] T031 [P] [US1] Create unit tests in 18.0/extra-addons/quicksol_estate/tests/api/test_tenant_api.py — test tenant model fields (active default, deactivation fields), email validation constraint, TENANT_CREATE_SCHEMA and TENANT_UPDATE_SCHEMA validation per SC-010

**Checkpoint**: Tenant CRUD fully functional — can create, list, view, update, and archive tenants with company isolation

---

## Phase 4: User Story 2 — Lease Lifecycle Management (Priority: P1) 🎯 MVP

**Goal**: Complete lease lifecycle with CRUD, in-place renewal with audit history, and early termination

**Independent Test**: Create lease → view → renew (verify history entry) → terminate → verify status transitions

**FRs covered**: FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-030, FR-031, FR-032, FR-033, FR-034, FR-037

### Implementation for User Story 2

- [X] T011 [P] [US2] Add fields to 18.0/extra-addons/quicksol_estate/models/lease.py: `active` (Boolean, default=True), `status` (Selection: draft/active/terminated/expired, default=draft), `termination_date` (Date), `termination_reason` (Text), `termination_penalty` (Float), `renewal_history_ids` (One2many → lease.renewal.history). Add `@api.constrains` for: concurrent lease check (one active lease per property, FR-013), rent_amount > 0 (FR-011). Reference: data-model.md Lease entity
- [X] T012 [P] [US2] Add `LEASE_CREATE_SCHEMA` (required: property_id, tenant_id, start_date, end_date, rent_amount), `LEASE_UPDATE_SCHEMA`, `LEASE_RENEW_SCHEMA` (required: new_end_date; optional: new_rent_amount, reason), `LEASE_TERMINATE_SCHEMA` (required: termination_date; optional: reason, penalty_amount) to 18.0/extra-addons/quicksol_estate/controllers/utils/schema.py per contracts/lease-api.yaml
- [X] T013 [US2] Create 18.0/extra-addons/quicksol_estate/controllers/lease_api.py with 5 CRUD endpoints: GET /leases (paginated, filters: property_id, tenant_id, status), POST /leases (create with property/tenant validation per FR-012, concurrent check per FR-013, reject if property sold per FR-029), GET /leases/{id} (detail with property+tenant info), PUT /leases/{id} (update non-terminated only per FR-016), DELETE /leases/{id} (soft archive). Include: triple auth, HATEOAS links (self, collection, property, tenant, renew action, terminate action), RBAC agent filtering, company isolation. Reference: contracts/lease-api.yaml
- [X] T014 [US2] Add renew endpoint POST /leases/{id}/renew to 18.0/extra-addons/quicksol_estate/controllers/lease_api.py — validate lease status is 'active', create renewal history record in `real.estate.lease.renewal.history` (capture previous end_date, previous rent_amount, renewed_by, reason), update lease end_date and optionally rent_amount in-place per FR-017 and R5
- [X] T015 [US2] Add terminate endpoint POST /leases/{id}/terminate to 18.0/extra-addons/quicksol_estate/controllers/lease_api.py — validate lease status is 'active', set status='terminated', record termination_date, termination_reason, and optional termination_penalty per FR-018
- [X] T016 [US2] Create integration test in integration_tests/test_us8_s2_lease_lifecycle.sh — cover: create lease (201), date validation (end < start → 400), concurrent lease rejection (400), sold-property lease rejection (400), list with filters (200), get by ID (200), update rent (200), renew with history audit (200), terminate with penalty (200), reject renew on terminated lease (400), company isolation
- [X] T032 [P] [US2] Create unit tests in 18.0/extra-addons/quicksol_estate/tests/api/test_lease_api.py — test lease model constraints (rent_amount > 0, concurrent lease check, date ordering), status transitions (draft→active→terminated, renewal in-place), LEASE_CREATE_SCHEMA/LEASE_RENEW_SCHEMA/LEASE_TERMINATE_SCHEMA validation per SC-010

**Checkpoint**: Lease lifecycle fully functional — create, renew, terminate leases with full audit trail

---

## Phase 5: User Story 3 — Sale Registration & Management (Priority: P1) 🎯 MVP

**Goal**: Sale registration with buyer info, agent attribution, event emission, cancellation with property status management

**Independent Test**: Create sale → verify property marked "sold" → cancel sale → verify property reverted

**FRs covered**: FR-021, FR-022, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-034, FR-037

### Implementation for User Story 3

- [X] T017 [P] [US3] Add fields to 18.0/extra-addons/quicksol_estate/models/sale.py: `active` (Boolean, default=True), `status` (Selection: completed/cancelled, default=completed), `cancellation_date` (Date), `cancellation_reason` (Text). Add `@api.constrains` for sale_price > 0 (FR-022). Enhance existing `create()` override to set `property_id.state = 'sold'` per FR-029. Add cancel method to revert property status per R6
- [X] T018 [P] [US3] Add `SALE_CREATE_SCHEMA` (required: property_id, company_id, buyer_name, sale_date, sale_price; optional: buyer_phone, buyer_email, agent_id, lead_id), `SALE_UPDATE_SCHEMA`, `SALE_CANCEL_SCHEMA` (required: reason) to 18.0/extra-addons/quicksol_estate/controllers/utils/schema.py per contracts/sale-api.yaml
- [X] T019 [US3] Create 18.0/extra-addons/quicksol_estate/controllers/sale_api.py with 5 endpoints: GET /sales (paginated, filters: property_id, agent_id, status, min_price, max_price), POST /sales (create with agent company validation per FR-023, emit sale.created event per FR-028), GET /sales/{id} (detail with property+agent+lead info), PUT /sales/{id} (update non-cancelled only per FR-026), POST /sales/{id}/cancel (cancel with reason, revert property status per FR-029). Include: triple auth, HATEOAS links (self, collection, property, agent, cancel action), RBAC agent filtering (agent sees own sales only), company isolation. Reference: contracts/sale-api.yaml
- [X] T020 [US3] Create integration test in integration_tests/test_us8_s3_sale_management.sh — cover: create sale (201), verify property marked "sold", price validation (zero → 400), agent company mismatch (400), list with filters (200), get by ID (200), update buyer info (200), cancel with reason (200), verify property status reverted after cancel, reject update on cancelled sale (400), company isolation
- [X] T033 [P] [US3] Create unit tests in 18.0/extra-addons/quicksol_estate/tests/api/test_sale_api.py — test sale model constraints (sale_price > 0), create() override (property→sold status), cancel method (property status revert), SALE_CREATE_SCHEMA/SALE_CANCEL_SCHEMA validation per SC-010

**Checkpoint**: Sale management fully functional — create, track, cancel sales with property status side effects and event emission

---

## Phase 6: User Story 4 — Tenant Lease History (Priority: P2)

**Goal**: Consolidated lease history view per tenant via dedicated sub-resource endpoint

**Independent Test**: Get tenant's lease list — returns all leases (active + historical) for that tenant

**FRs covered**: FR-008

### Implementation for User Story 4

- [X] T021 [US4] Add GET /tenants/{id}/leases endpoint to 18.0/extra-addons/quicksol_estate/controllers/tenant_api.py — return paginated list of all leases for the given tenant (both active and historical), filtered by company_ids. Include triple auth, HATEOAS links, RBAC agent filtering. Reference: contracts/tenant-api.yaml getTenantLeases operation
- [X] T022 [US4] Create integration test in integration_tests/test_us8_s4_tenant_lease_history.sh — cover: tenant with multiple leases returns all (200), tenant with no leases returns empty list (200), company isolation

**Checkpoint**: Tenant profile includes full lease history via sub-resource

---

## Phase 7: User Story 5 — Soft Delete & Record Recovery (Priority: P2)

**Goal**: Query inactive records and reactivate archived tenants/leases/sales

**Independent Test**: Archive record → verify hidden from default list → query with is_active=false → verify visible → reactivate → verify back in default list

**FRs covered**: FR-007, FR-035, FR-036

### Implementation for User Story 5

- [X] T023 [US5] Add `is_active` query parameter support to list endpoints in 18.0/extra-addons/quicksol_estate/controllers/tenant_api.py, lease_api.py, and sale_api.py — when `is_active=false`, use `with_context(active_test=False)` to include inactive records per ADR-015 and FR-036
- [X] T024 [US5] Add reactivation (unarchive) support to tenant_api.py, lease_api.py, and sale_api.py — implement PUT endpoint logic to set `active=True`, clear `deactivation_date`/`deactivation_reason` (tenant), reset fields as appropriate per FR-007
- [X] T025 [US5] Create integration test in integration_tests/test_us8_s5_soft_delete.sh — cover: archive tenant/lease/sale (200), verify hidden from default GET list, query with is_active=false shows archived record, reactivate (200), verify visible again in default list

**Checkpoint**: Complete soft delete lifecycle — archive, query inactive, reactivate across all 3 entities

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, E2E tests, and final validation

- [X] T026 [P] Create Postman collection in docs/postman/feature008_tenant_lease_sale_v1.0_postman_collection.json per ADR-016 — include OAuth token endpoint with auto-save script, session management, all 18 endpoints organized by entity folder (Tenants, Leases, Sales), required variables (base_url, access_token, session_id). Reference: feature007_owner_company_v1.0_postman_collection.json as template
- [X] T027 [P] Create Cypress E2E test in cypress/e2e/tenant-management.cy.js — complete tenant CRUD journey: create, list, view, update, archive
- [X] T028 [P] Create Cypress E2E test in cypress/e2e/lease-management.cy.js — complete lease lifecycle journey: create, renew, terminate
- [X] T029 [P] Create Cypress E2E test in cypress/e2e/sale-management.cy.js — complete sale journey: create, view, cancel
- [X] T030 Run quickstart.md validation — verify all 18 endpoints respond correctly, HATEOAS links present, pagination works, company isolation enforced, test coverage ≥80%
- [X] T034 [P] Create/update unit tests in 18.0/extra-addons/quicksol_estate/tests/utils/test_validators.py — test email format validation, phone validation, and all new schema constraint lambdas (rent > 0, price > 0, email format) per SC-010

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. All 3 tasks are [P] parallel (different files)
- **Foundational (Phase 2)**: Depends on T002 (model import). T004 first, then T005+T006 in parallel
- **US1 (Phase 3)**: Depends on Phase 2 completion. T007+T008 in parallel, then T009, then T010
- **US2 (Phase 4)**: Depends on Phase 2 completion (needs lease_renewal_history model). T011+T012 in parallel, then T013→T014→T015, then T016
- **US3 (Phase 5)**: Depends on Phase 2 completion. T017+T018 in parallel, then T019, then T020
- **US4 (Phase 6)**: Depends on US1 (T009 — tenant_api.py must exist) and US2 (leases must exist for test data)
- **US5 (Phase 7)**: Depends on US1+US2+US3 (all 3 controllers must exist to add is_active filter)
- **Polish (Phase 8)**: Depends on all user stories. T026-T029 are [P] parallel (different files)

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependencies on other stories ✅
- **US2 (P1)**: After Phase 2 — no dependencies on other stories ✅
- **US3 (P1)**: After Phase 2 — no dependencies on other stories ✅
- **US4 (P2)**: Depends on US1 (tenant_api.py) + US2 (lease data for testing)
- **US5 (P2)**: Depends on US1 + US2 + US3 (all controllers must exist)

### Parallel Opportunities per Phase

**Phase 1** — All 3 tasks parallel:
```
T001 ─┐
T002 ─┼─ all different files
T003 ─┘
```

**Phase 3 (US1)** — Model + Schema parallel, then controller, then test:
```
T007 ─┐
      ├─ T009 ─── T010
T008 ─┘
```

**Phase 4 (US2)** — Model + Schema parallel, then CRUD → renew → terminate, then test:
```
T011 ─┐
      ├─ T013 ─── T014 ─── T015 ─── T016
T012 ─┘
```

**Phase 5 (US3)** — Model + Schema parallel, then controller, then test:
```
T017 ─┐
      ├─ T019 ─── T020
T018 ─┘
```

**Phase 8** — Postman + 3 Cypress tests parallel:
```
T026 ─┐
T027 ─┤
T028 ─┼─ all different files
T029 ─┤
      └─ T030 (after all above)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3)

1. Complete Phase 1: Setup (3 tasks, ~10 min)
2. Complete Phase 2: Foundational (3 tasks, ~20 min)
3. Complete Phase 3: US1 — Tenant CRUD (4 tasks)
4. **STOP and VALIDATE**: Test tenant CRUD independently
5. Complete Phase 4: US2 — Lease Lifecycle (6 tasks)
6. **STOP and VALIDATE**: Test lease lifecycle independently
7. Complete Phase 5: US3 — Sale Management (4 tasks)
8. **STOP and VALIDATE**: Test sale management independently
9. **MVP COMPLETE**: 18 core endpoints functional

### Incremental Delivery

1. Setup + Foundational → Module upgradeable
2. Add US1 → Tenant registry works → **Deliverable**
3. Add US2 → Lease lifecycle works → **Deliverable**
4. Add US3 → Sale tracking works → **MVP Deliverable** (all P1 stories)
5. Add US4 → Tenant lease history → **Enhanced**
6. Add US5 → Soft delete recovery → **Enhanced**
7. Polish → Postman + E2E → **Production Ready**

### Parallel Team Strategy

With multiple developers after Phase 2:
- **Developer A**: US1 (Tenant) → US4 (Tenant Lease History)
- **Developer B**: US2 (Lease Lifecycle)
- **Developer C**: US3 (Sale Management) → US5 (Soft Delete)
- **All**: Phase 8 Polish (parallel Postman + Cypress)

---

## Notes

- All controllers use triple auth: `@require_jwt` + `@require_session` + `@require_company`
- All responses use `success_response()`, `error_response()`, `paginated_response()` from utils/responses.py
- All responses include HATEOAS links via `build_hateoas_links()`
- RBAC agent filtering: transitive via property assignment (R3) — implemented in each controller's list/get methods
- Schema validation: `SchemaValidator` class in controllers/utils/schema.py
- Soft delete: `active = fields.Boolean(default=True)` + `with_context(active_test=False)` for inactive queries
- Event bus: `quicksol.event.bus.emit('sale.created', ...)` already exists in sale.py create() override
- Reference implementation: Feature 007 owner_api.py for controller patterns
- Commit after each task or logical group
