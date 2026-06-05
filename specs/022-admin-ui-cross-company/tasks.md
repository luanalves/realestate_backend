# Tasks: Admin UI — Cross-Company Access for System Admin

**Input**: Design documents from `/specs/022-admin-ui-cross-company/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to user story from spec.md — [US1], [US2], [US3], [US4]
- File paths are absolute within the repository

---

## Phase 1: Setup

**Purpose**: Confirm the working environment before any source changes

- [X] - [X] T001 Verify Docker services running (`docker compose up -d` from `18.0/`) and confirm `022-admin-ui-cross-company` branch is active

---

## Phase 2: Foundational (Convention Artefacts — FR-008)

**Purpose**: Create the ADR and knowledge base checklist that define the canonical record-rule override pattern used in every US1 task. All developers working on Phase 3+ tasks should read these first.

⚠️ **These tasks are prerequisites for any reviewer verifying the XML pattern; they are NOT blockers for parallel XML authoring if the pattern in `data-model.md` is used directly.**

- [X] - [X] T002 [P] Create ADR that formalises the `base.group_system` channel separation convention and cross-module checklist obligation in `docs/adr/ADR-029-saas-admin-channel-separation.md`
- [X] - [X] T003 [P] Create developer checklist for new modules (always include System Admin record rule override) in `knowledge_base/13-saas-admin-module-checklist.md`

**Checkpoint**: Pattern documented — US1 XML tasks can proceed

---

## Phase 3: User Story 1 — Admin Views All Company Data (Priority: P1)

**Goal**: System Admin sees all records from all tenant companies in the Odoo web interface via `[(1,'=',1)]` record rule overrides assigned to `base.group_system`.

**Independent Test**: Log in as System Admin → navigate to Real Estate → Properties list → records from all companies appear. If they do, the entire cross-company visibility mechanism is working and delivers the "oversight" value independently.

### Implementation for User Story 1

- [X] T004 [P] [US1] Append new `<data noupdate="0">` block to `18.0/extra-addons/quicksol_estate/security/record_rules.xml` with admin override rules for 9 models: `real.estate.property`, `real.estate.agent`, `real.estate.lease`, `real.estate.sale`, `real.estate.agent.property.assignment`, `real.estate.commission.rule`, `real.estate.commission.transaction`, `real.estate.lease.renewal.history`, `thedevkitchen.estate.profile` — use canonical pattern from `data-model.md`
- [X] T005 [P] [US1] Append admin override rule for `real.estate.proposal` inside the existing `<data>` block of `18.0/extra-addons/quicksol_estate/security/proposal_record_rules.xml` (noupdate="0" — append directly)
- [X] T006 [P] [US1] Append admin override rules for `real.estate.service`, `real.estate.service.tag`, `real.estate.service.source`, `thedevkitchen.service.settings` inside the existing `<data>` block of `18.0/extra-addons/quicksol_estate/security/service_record_rules.xml` (noupdate="0" — append directly)
- [X] T007 [P] [US1] Append new `<data noupdate="0">` block to `18.0/extra-addons/thedevkitchen_cms/security/cms_record_rules.xml` with admin override rules for `thedevkitchen.cms.page`, `thedevkitchen.cms.media`, `thedevkitchen.cms.settings`
- [X] T008 [P] [US1] Append admin override rule for `thedevkitchen.estate.goal` inside the existing `<data>` block of `18.0/extra-addons/thedevkitchen_estate_goals/security/record_rules.xml` (noupdate="0" — append directly)
- [X] T009 [P] [US1] Append new `<data noupdate="0">` block to `18.0/extra-addons/thedevkitchen_estate_credit_check/security/record_rules.xml` with admin override rule for `thedevkitchen.estate.credit.check`
- [X] T010 [P] [US1] Append new `<data noupdate="0">` block to `18.0/extra-addons/thedevkitchen_user_onboarding/security/record_rules.xml` with admin override rule for `thedevkitchen.password.token`
- [X] T011 [US1] Upgrade affected modules (`quicksol_estate`, `thedevkitchen_cms`, `thedevkitchen_estate_goals`, `thedevkitchen_estate_credit_check`, `thedevkitchen_user_onboarding`) via Docker and verify Properties list shows all tenant companies' records in Odoo UI — confirms SC-001 and SC-007
- [X] T012 [US1] Create Cypress E2E test for cross-company read visibility (SC-001, AC-1 to AC-3) in `cypress/e2e/views/admin_cross_company.cy.js` — cover Properties, Leases, Agents, CMS Pages, Goals, Proposals

**Checkpoint**: System Admin can see all records across all companies in the Odoo UI — US1 delivers independently

---

## Phase 4: User Story 4 — API Login Blocked for System Admin (Priority: P2)

**Goal**: Any REST API login attempt with System Admin credentials returns HTTP 401 (identical to bad-credential response) and creates an audit log entry. Business users are unaffected.

**Independent Test**: `curl POST /api/v1/users/login` with valid admin credentials must return 401 with `"Invalid credentials"` body — no session token issued.

### Implementation for User Story 4

- [X] T013 [US4] Inject `has_group('base.group_system')` guard in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` — place after `if not user.active` check, before session creation; call `AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')` and return HTTP 401 `{"error": {"status": 401, "message": "Invalid credentials"}}` (see `contracts/login-block.md` for exact insertion point and response shape)
- [X] T014 [US4] Create integration test `integration_tests/test_admin_api_block.sh` — verify HTTP 401 for admin credentials, generic response body (no token/session_id), audit log entry presence, and HTTP 200 for a valid business-user login (SC-004, SC-005)

**Checkpoint**: System Admin cannot authenticate via REST API; business users unaffected — US4 delivers independently

---

## Phase 5: User Story 2 — Admin Manages Data Across All Companies (Priority: P2)

**Goal**: System Admin can create, edit, and delete records belonging to any tenant company via the Odoo web interface.

> **Note**: US2 has **no implementation tasks**. The `[(1,'=',1)]` record rules added in US1 apply to all CRUD operations (read + write + create + delete) — write access is already unlocked by Phase 3. This phase adds test coverage to confirm SC-002 explicitly.

**Independent Test**: Edit a property record from a different company in Odoo UI and save successfully.

### Implementation for User Story 2

- [X] T015 [US2] Extend `cypress/e2e/views/admin_cross_company.cy.js` with write access scenarios: edit a record from a foreign company and save (SC-002 AC-1), create a new record for a foreign company (SC-002 AC-2), delete a record from a foreign company (SC-002 AC-3)

**Checkpoint**: System Admin write access confirmed across all companies — US2 delivers independently

---

## Phase 6: User Story 3 — Admin Sees All Navigation Menus (Priority: P3)

**Goal**: All Real Estate module menus, including `menu_real_estate_lead` (Leads), are visible to System Admin.

**Independent Test**: Log in as System Admin → Real Estate navigation shows the Leads menu item without any access error.

### Implementation for User Story 3

- [X] T016 [US3] Add `base.group_system` to the `groups` attribute of `menu_real_estate_lead` in `18.0/extra-addons/quicksol_estate/views/real_estate_menus.xml` — existing line: `groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager"` → append `,base.group_system`
- [X] T017 [US3] Extend `cypress/e2e/views/admin_cross_company.cy.js` with menu visibility scenarios: all sub-menus visible including Leads (SC-003 AC-1), Leads page loads with all-company records (SC-003 AC-2)

**Checkpoint**: All navigation menus visible to System Admin — US3 delivers independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration test for FR-007 convention verification, full end-to-end validation, and final test run.

- [X] T018 [P] Create integration test `integration_tests/test_admin_invite_block.sh` — verify that attempting to use the REST API invite endpoint to invite a `base.group_system` user is rejected by Feature 009's authorization matrix (FR-007 — no new guard code, existing matrix enforces this)
- [X] T019 Run full quickstart.md validation: upgrade all affected modules, verify UI cross-company access, verify API 401 block, run all three test files (Cypress + `test_admin_api_block.sh` + `test_admin_invite_block.sh`) per `specs/022-admin-ui-cross-company/quickstart.md`
- [X] T020 Confirm SC-001 through SC-007 all pass: cross-company visibility (SC-001), write access (SC-002), menu visibility (SC-003), API block 401 (SC-004), audit log (SC-005), business-user isolation unchanged (SC-006), no manual DB intervention needed (SC-007)
- [X] T021 [P] Create integration test `integration_tests/test_business_user_isolation.sh` — log in as a business-role user (e.g., Owner of Company A), assert that records belonging exclusively to Company B are absent from all list responses (SC-006); assert record count is identical before and after deploying this feature (zero cross-company leakage)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependencies — T002 and T003 are independent of Phase 1 and of each other
- **User Story 1 (Phase 3)**: T004–T010 can begin immediately after Phase 1; T011 requires T004–T010; T012 requires T011
- **User Story 4 (Phase 4)**: T013 is independent of Phase 3 (different module); T014 requires T013
- **User Story 2 (Phase 5)**: T015 requires T012 (extends the same Cypress file)
- **User Story 3 (Phase 6)**: T016 is independent; T017 requires T012 and T016
- **Polish (Phase 7)**: T018 is independent; T021 is independent; T019 requires T011 + T013 + T016 (all deployed); T020 requires T019

### User Story Dependencies

```
T001 (env)
  ↓
T002 ‖ T003 (convention docs — in parallel)
  ↓
T004 ‖ T005 ‖ T006 ‖ T007 ‖ T008 ‖ T009 ‖ T010 ‖ T013  ← all parallel
  ↓                                                ↓
T011                                              T014
  ↓
T012
  ↓
T015 ‖ T017 (after T012; T017 also needs T016)
         T016 (independent of T012)
  ↓
T018 (independent)
T019 (after T011 + T013 + T016)
T020 (after T019)
```

### Parallel Opportunities

**Maximum parallelism** (once T001 complete):
- Launch T002 + T003 together (documentation, no file conflicts)
- Launch T004 through T010 + T013 together (7 XML files + 1 Python file — all different)
- After T004–T010 done → T011; after T011 → T012
- After T013 done → T014
- T015, T016, T018 can all run in parallel once T012 is done (different files)

---

## Parallel Example: User Story 1 (Phase 3)

```bash
# All 7 XML edits can be done simultaneously — different files, no shared state:
Task T004: quicksol_estate/security/record_rules.xml
Task T005: quicksol_estate/security/proposal_record_rules.xml
Task T006: quicksol_estate/security/service_record_rules.xml
Task T007: thedevkitchen_cms/security/cms_record_rules.xml
Task T008: thedevkitchen_estate_goals/security/record_rules.xml
Task T009: thedevkitchen_estate_credit_check/security/record_rules.xml
Task T010: thedevkitchen_user_onboarding/security/record_rules.xml

# In parallel with T004-T010, a second developer can work on:
Task T013: thedevkitchen_apigateway/controllers/user_auth_controller.py (US4)
```

---

## Implementation Strategy

### Execution Order

1. Complete Phase 1 (Setup) + Phase 2 (Foundational docs)
2. Complete Phase 3 (US1) + Phase 4 (US4) — T004–T010 and T013 fully parallel
3. Complete Phase 5 (US2) + Phase 6 (US3) — after T012
4. Complete Phase 7 (Polish) — final validation confirms all SC-001–SC-007

### Parallel Team Strategy

With two developers:
- **Developer A**: T004–T010 (XML record rules — US1)
- **Developer B**: T013 + T014 (controller guard — US4) in parallel
- Both merge → T011 (module upgrade) → T012 (Cypress) → remaining phases

---

## Task Count Summary

| Phase | Tasks | User Story | Parallelizable |
|-------|-------|-----------|----------------|
| Phase 1: Setup | 1 (T001) | — | No |
| Phase 2: Foundational | 2 (T002–T003) | — | Yes (both) |
| Phase 3: US1 (P1) | 9 (T004–T012) | US1 | T004–T010 parallel |
| Phase 4: US4 (P2) | 2 (T013–T014) | US4 | T013 parallel with T004–T010 |
| Phase 5: US2 (P2) | 1 (T015) | US2 | No |
| Phase 6: US3 (P3) | 2 (T016–T017) | US3 | T016 parallel with T012 |
| Phase 7: Polish | 4 (T018–T021) | — | T018, T021 parallel |
| **Total** | **21** | | **15 parallelizable** |

---

## Notes

- `[P]` tasks touch **different files** with no shared state — safe to run simultaneously
- US2 has zero implementation tasks — the `[(1,'=',1)]` rules from US1 cover all CRUD access
- noupdate strategy: files with `noupdate="1"` (T004, T007, T009, T010) need a **new** `<data noupdate="0">` block; files with `noupdate="0"` (T005, T006, T008) append inside the existing block — see `research.md` R-002 table
- Canonical rule pattern for all XML tasks: see `data-model.md` § Record Rule Pattern
- Controller guard insertion point: after `if not user.active` block, before "Invalidar sessões antigas" — see `research.md` R-004 and `contracts/login-block.md`
- FR-007 (admin not invitable via API) requires no new guard code — T018 is a verification test only
