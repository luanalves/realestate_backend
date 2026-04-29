# Tasks: Rental Credit Check (spec 014)

**Input**: Design documents from `specs/014-rental-credit-check/`
**Branch**: `014-rental-credit-check`
**Generated**: 2026-04-29

**Prerequisites used**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/openapi.yaml ✅ · quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: User story label (US1–US5), maps to spec.md
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Module scaffold — must exist before any model, controller, or view code can be written.

- [X] T001 Create module scaffold: dirs + empty `__init__.py` files + stub `__manifest__.py` for `18.0/extra-addons/thedevkitchen_estate_credit_check/` (models/, controllers/, services/, views/, security/, data/, tests/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on. No US work can begin until this phase is complete.

**⚠️ CRITICAL**: T002–T004 can run in parallel (different files). T005 depends on T002 and T003 being complete.

- [X] T002 [P] Implement `thedevkitchen.estate.credit.check` model in `18.0/extra-addons/thedevkitchen_estate_credit_check/models/credit_check.py` — all fields (`proposal_id`, `company_id`, `partner_id`, `insurer_name`, `result`, `requested_by`, `requested_at`, `result_registered_by`, `result_registered_at`, `rejection_reason`, `check_date`, `active`), `@api.constrains` for rejection_reason, `_auto_init()` for partial unique index `WHERE result='pending' AND active=true`, `mail.thread` + `mail.activity.mixin`
- [X] T003 [P] Implement `_inherit 'real.estate.proposal'` in `18.0/extra-addons/thedevkitchen_estate_credit_check/models/proposal_extension.py` — add `credit_check_pending` to Selection field, add `credit_check_ids` One2many, add `credit_history_summary` computed field stub (returns empty string for now), override `_can_create_counter_proposal()` to block when `state == 'credit_check_pending'`
- [X] T004 [P] Create `18.0/extra-addons/thedevkitchen_estate_credit_check/security/ir.model.access.csv` (CRUD grants for Owner/Manager/Agent/Receptionist groups on `thedevkitchen.estate.credit.check`) and `security/record_rules.xml` (`rule_credit_check_company`: `[('company_id', 'in', user.company_ids.ids)]`)
- [X] T005 Implement `18.0/extra-addons/thedevkitchen_estate_credit_check/services/credit_check_service.py` skeleton — class `CreditCheckService`, `__init__(self, env)`, shared helper `_get_proposal_or_404(proposal_id)`, shared helper `_get_check_or_404(proposal_id, check_id)`, shared helper `_assert_agent_owns_proposal(proposal)` — all methods raise `NotImplementedError` (stubs filled in later phases)

**Checkpoint**: Foundation ready — all user story phases can begin. US1/US2/US5 can proceed in parallel after this checkpoint.

---

## Phase 3: User Story 1 — Agent Initiates Credit Check (Priority: P1) 🎯 MVP

**Goal**: Agent (via API) or Owner/Manager transitions a `sent`/`negotiation` lease proposal to `credit_check_pending` by creating a `CreditCheck` record with `result=pending`.

**Independent Test**: Create lease proposal in `sent` state → call `POST /api/v1/proposals/{id}/credit-checks` → verify proposal state is `credit_check_pending`, `CreditCheck` exists with `result=pending`, timeline entry added. Also verify: sale proposals blocked (HTTP 422), duplicate pending blocked (HTTP 409), terminal proposals blocked.

- [X] T006 [US1] Implement `action_initiate_credit_check(proposal_id, insurer_name)` in `18.0/extra-addons/thedevkitchen_estate_credit_check/services/credit_check_service.py` — guards: proposal type must be `lease`, state must be `sent` or `negotiation`, no existing `pending` check; creates `CreditCheck` with `result='pending'`, writes `proposal.state = 'credit_check_pending'`, posts timeline message via `proposal.message_post()`
- [X] T007 [P] [US1] Implement `POST /api/v1/proposals/{id}/credit-checks` in `18.0/extra-addons/thedevkitchen_estate_credit_check/controllers/credit_check_controller.py` — triple decorator (`@require_jwt` + `@require_session` + `@require_company`), parse + validate `insurer_name` (ADR-018), call `CreditCheckService.action_initiate_credit_check()`, return 201 with `CreditCheck` dict + HATEOAS `_links` (ADR-007)
- [X] T008 [P] [US1] Write unit tests for US1 in `18.0/extra-addons/thedevkitchen_estate_credit_check/tests/test_credit_check_model.py` — scenarios: initiate on `sent` lease succeeds, initiate on `negotiation` lease succeeds, initiate on sale proposal raises error, initiate with existing pending check raises error, initiate on terminal proposal raises error, agent blocked from other agent's proposal (6 scenarios)

---

## Phase 4: User Story 2 — Agent Registers Result (Priority: P1) 🎯 MVP

**Goal**: Owner, Manager, or Agent registers `approved`/`rejected`/`cancelled` on a pending `CreditCheck`. Approved → proposal `accepted` + competitors cancelled. Rejected → proposal `rejected` + next queue entry promoted.

**Independent Test**: Proposal in `credit_check_pending` → register `approved` → verify proposal is `accepted`, `accepted_date` set, competing proposals cancelled. Separately register `rejected` with reason → verify proposal is `rejected`, next queued promoted to `draft`. Verify: reject without reason blocked (HTTP 400), re-registering on resolved check blocked (HTTP 409).

- [X] T009 [US2] Implement `action_register_result(proposal_id, check_id, result, rejection_reason, check_date)` in `18.0/extra-addons/thedevkitchen_estate_credit_check/services/credit_check_service.py` — guards: check must be `pending` (immutability), `rejection_reason` required when `result='rejected'`; on approved: write `CreditCheck.result='approved'`, write `proposal.state='accepted'`, write `proposal.accepted_date`, call spec-013 competitor-cancel mechanism; on rejected: write `CreditCheck.result='rejected'`, write `proposal.state='rejected'`, call spec-013 queue-promotion mechanism; on cancelled (via API): write `CreditCheck.result='cancelled'`, write `proposal.state='sent'`, post timeline message (FR-007c); emit EventBus event `credit_check.result_registered` (ADR-021 Outbox); post timeline message
- [X] T010 [P] [US2] Implement `PATCH /api/v1/proposals/{id}/credit-checks/{check_id}` in `18.0/extra-addons/thedevkitchen_estate_credit_check/controllers/credit_check_controller.py` — triple decorator, parse + validate `result` / `rejection_reason` / `check_date` (ADR-018, `check_date` must not be future), call service, return 200 with updated `CreditCheck` dict + HATEOAS `_links`
- [X] T011 [P] [US2] Extend spec 013 daily cron in `18.0/extra-addons/thedevkitchen_estate_credit_check/models/proposal_extension.py` (or `data/` XML override) to call `_expire_credit_check_pending_proposals()`: find proposals where `state='credit_check_pending'` AND `valid_until < today`, mark their active `CreditCheck` as `cancelled`, write `proposal.state='expired'`, call queue-promotion, post timeline message (FR-007a)
- [X] T011b [P] [US2] Implement manual-cancel guard in `18.0/extra-addons/thedevkitchen_estate_credit_check/models/proposal_extension.py` — override `action_cancel()`: when `self.state == 'credit_check_pending'`, search for the active `pending` `CreditCheck` linked to the proposal and write `result='cancelled'` before calling `super().action_cancel()` (FR-007b)
- [X] T012 [P] [US2] Create `18.0/extra-addons/thedevkitchen_estate_credit_check/data/mail_templates.xml` — two `mail.template` records: `credit_check_approved_template` (subject: "Ficha aprovada — {{object.name}}", body includes proposal + client info) and `credit_check_rejected_template` (includes `rejection_reason`), both in Portuguese (pt_BR)
- [X] T013 [P] [US2] Write unit tests for US2 in `18.0/extra-addons/thedevkitchen_estate_credit_check/tests/test_credit_check_service.py` — scenarios: approve transitions proposal to `accepted`, approved cancels competing proposals, reject requires rejection_reason, reject transitions to `rejected` and promotes queue, re-registering on resolved check raises error, cancel via API sets `result='cancelled'` and reverts proposal to `sent` (FR-007c), check_date in future is rejected, manual cancel of proposal while pending marks check as cancelled (FR-007b), queue promotion elapsed time asserted ≤ 5 s (SC-002 — SC-008 is validated by T008 scenario 3), concurrent approve calls: only one succeeds and rest raise conflict error (SC-003 — use `threading.Thread` with 5 simultaneous approve calls on the same check) (10 scenarios)

---

## Phase 5: User Story 5 — Odoo UI for Owner/Manager (Priority: P1)

**Goal**: Owner and Manager can perform the full credit check flow (initiate + register result) directly in the Odoo proposal form, in a dedicated "Análise de Ficha" tab. No agent-facing Odoo views.

**Independent Test**: Open a lease proposal form as Manager in Odoo → verify "Análise de Ficha" tab visible → click "Iniciar Análise" button → verify proposal state updated in UI → register approved/rejected → verify state and timeline updated. Browser DevTools console must show 0 JS errors (SC-005).

- [ ] T014 [US5] Create `18.0/extra-addons/thedevkitchen_estate_credit_check/views/credit_check_views.xml` — `<list>` view (columns: insurer_name, result, requested_by, requested_at, check_date, rejection_reason with `optional="show"`) and `<form>` view (fields: proposal_id, insurer_name, result, check_date, rejection_reason, result_registered_by, result_registered_at); no `attrs`, no `column_invisible` with Python expressions (ADR-001); `groups` attribute restricts to Owner + Manager groups
- [ ] T015 [P] [US5] Create `18.0/extra-addons/thedevkitchen_estate_credit_check/views/menu.xml` — add "Análises de Ficha" menu item under the existing Proposals menu; restrict to Owner + Manager groups via `groups` attribute
- [ ] T016 [P] [US5] Extend proposal `<form>` view in `18.0/extra-addons/thedevkitchen_estate_credit_check/views/credit_check_views.xml` via `<record model="ir.ui.view" id="...">` `inherit_id` xpath — add "Análise de Ficha" `<page>` tab containing: `credit_check_ids` `<field widget="one2many_list">` using the credit check list view, `credit_history_summary` read-only display, "Iniciar Análise" button (visible only when `state in ['sent','negotiation']` and `proposal_type == 'lease'`), informational message when `proposal_type == 'sale'` (no `attrs`, use `invisible` domain syntax)

---

## Phase 6: User Story 3 — New Attempt After Rejection (Priority: P2)

**Goal**: Clarify and enforce that a rejected proposal is immutable (terminal). New insurer attempt requires a brand-new proposal. Queue promotion on rejection works correctly.

**Independent Test**: Reject a credit check → verify proposal is `rejected` terminal (all write operations blocked) → verify next queued proposal promoted → create new proposal for same client/property → verify new proposal enters queue normally → verify client credit history includes the rejected check.

- [ ] T017 [US3] Add immutability guard for `rejected` proposals in `18.0/extra-addons/thedevkitchen_estate_credit_check/services/credit_check_service.py` — `_assert_proposal_not_terminal(proposal)` helper: raise `UserError` if `proposal.state in ('rejected', 'accepted', 'expired', 'cancelled')` when attempting to initiate a new check; also override `write()` on `proposal_extension.py` to block non-system writes on terminal proposals (or rely on existing spec-013 guard — check and document)
- [ ] T018 [P] [US3] Add scenarios to existing `18.0/extra-addons/thedevkitchen_estate_credit_check/tests/test_credit_check_service.py` — scenarios: rejected proposal blocks new credit check initiation, rejected proposal blocks editing, new proposal for same client/property enters queue normally, client history includes check from rejected proposal (4 scenarios)

---

## Phase 7: User Story 4 — Client Credit History (Priority: P2)

**Goal**: Owner, Manager, or Agent can query full credit check history for a client across all proposals in the company. Agent scope: only clients from their own proposals (any state). Anti-enumeration: 404 for out-of-scope clients.

**Independent Test**: Create client with 3 checks in different proposals (1 approved, 2 rejected) → call `GET /api/v1/clients/{partner_id}/credit-history` as Owner → verify 3 checks returned with correct summary → call as Agent without that client in their proposals → verify 404 → verify company isolation (different company returns 404).

- [ ] T019 [US4] Implement `_compute_credit_history_summary()` in `18.0/extra-addons/thedevkitchen_estate_credit_check/models/proposal_extension.py` — `store=False` computed field, aggregates `approved`/`rejected` counts for `partner_id` + `company_id` across all `thedevkitchen.estate.credit.check` records; returns Portuguese string `"N aprovada(s) / M rejeitada(s)"`
- [ ] T020 [P] [US4] Implement `GET /api/v1/clients/{partner_id}/credit-history` in `18.0/extra-addons/thedevkitchen_estate_credit_check/controllers/credit_check_controller.py` — triple decorator, resolve agent scope (search proposals where `agent_id.user_id = env.user` for current company, any state), return 404 if client not in scope (ADR-008 anti-enumeration), return paginated list with `summary` dict (total, approved, rejected, pending, cancelled) + HATEOAS `_links`, max 100 per page
- [ ] T021 [P] [US4] Implement `GET /api/v1/proposals/{id}/credit-checks` in `18.0/extra-addons/thedevkitchen_estate_credit_check/controllers/credit_check_controller.py` — triple decorator, return all `CreditCheck` records for proposal ordered by `requested_at desc`, support `?result=` filter, pagination with limit/offset, HATEOAS `_links`
- [ ] T022 [P] [US4] Write unit tests for US4 in `18.0/extra-addons/thedevkitchen_estate_credit_check/tests/test_credit_check_controller.py` — scenarios: owner sees full history, manager sees full history, agent sees only their clients' history, agent 404 for unknown client (anti-enumeration), company isolation enforced (cross-company returns 404), empty history returns 200 with empty array, credit_history_summary correct counts, GET credit-history with 1,000 seed checks completes in < 300 ms (SC-004) (8 scenarios)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Swagger records, integration tests, Postman collection, E2E coverage, linting.

- [ ] T023 Create `18.0/extra-addons/thedevkitchen_estate_credit_check/data/api_endpoints_data.xml` — `thedevkitchen_api_endpoint` records for all 4 endpoints per ADR-005: `POST /api/v1/proposals/{id}/credit-checks`, `PATCH /api/v1/proposals/{id}/credit-checks/{check_id}`, `GET /api/v1/proposals/{id}/credit-checks`, `GET /api/v1/clients/{partner_id}/credit-history`
- [ ] T024 [P] Create `integration_tests/run_feature014_tests.sh` — shell integration test script covering: initiate credit check, register approved, register rejected (with reason), reject without reason blocked, client credit history (owner + agent scope), company isolation; follows pattern of existing `run_feature010_tests.sh`
- [ ] T025 [P] Create `docs/postman/feature014_credit_check_v1.0_postman_collection.json` per ADR-016 — includes OAuth flow, session management, all 4 endpoints with test scripts, auto-save tokens to collection variables, correct headers (GET uses `X-Openerp-Session-Id`, POST/PATCH use body)
- [ ] T026 [P] Create `cypress/e2e/feature014/credit_check_ui.cy.js` — E2E test for US5: open lease proposal as Manager, verify "Análise de Ficha" tab, initiate analysis, register approved result, verify state update; verify 0 JS console errors (SC-005)
- [ ] T027 Run linting (ADR-022) on all new Python files (`18.0/extra-addons/thedevkitchen_estate_credit_check/`) and XML views — fix all errors before PR

---

## Dependencies

```
T001 → T002, T003, T004 (all setup before models/security)
T002 + T003 → T005 (service needs both models to exist)
T005 → T006 (US1 service method needs service skeleton)
T005 → T009 (US2 service method needs service skeleton)
T006 → T007 (controller calls service)
T009 → T010 (controller calls service)
T003 → T011b (manual-cancel override extends proposal_extension.py created in T003)
T009 → T011 (cron calls same result logic)
T009 → T013 (tests cover implemented service)
T003 → T016 (extend proposal form needs proposal_extension loaded)
T009 → T017 (US3 immutability guard extends result registration)
T019 → T020 (history endpoint exposes computed field)
T002 + T005 → T021 (list endpoint only needs model + service skeleton, not the computed field)
T007 + T010 + T020 + T021 → T023 (Swagger records after endpoints exist)
T007 + T010 + T020 + T021 → T024 (integration tests after all endpoints)
T023 + T024 + T025 + T026 → T027 (lint last)
```

### Story Completion Order

```
[Foundation: T001–T005] → [US1: T006–T008] ─┐
                                              ├─► [US5: T014–T016] → [US3: T017–T018] → [US4: T019–T022] → [Polish: T023–T027]
                        → [US2: T009–T013] ──┘
```

US1 and US2 can be developed in parallel after T005.
US5 can begin after T002–T004 (views don't need service methods).
US3 depends on US2 (must have rejection to test terminal state).
US4 depends on US3 completion (history includes rejected checks).

---

## Parallel Execution Examples

### During Foundation (T002–T004)
```
Developer A: T002 — credit_check.py model
Developer B: T003 — proposal_extension.py
Developer C: T004 — security files
→ All three merge, then T005 (service skeleton)
```

### During US1 + US2 + US5 (after T005)
```
Developer A: T006 (US1 service) → T007 (US1 controller) → T008 (US1 tests)
Developer B: T009 (US2 service) → T010 (US2 controller) → T013 (US2 tests)
Developer C: T014 (US5 views) → T015 (menu) → T016 (proposal form tab)
```

### During US4 (T019–T022)
```
Developer A: T019 (computed field) → T020 (history endpoint)
Developer B: T021 (list endpoint)
Developer C: T022 (controller tests)
```

---

## Implementation Strategy

**MVP Scope (US1 + US2 only)**:

The minimum deliverable that closes the credit check loop is:
1. T001–T005 (foundation)
2. T006–T008 (US1: initiate)
3. T009–T013 (US2: register result)

This gives agents the ability to open and resolve a credit check via API, with full FSM enforcement, queue integration, and notifications. US5 (UI), US3 (new attempt clarity), and US4 (history endpoint) can follow in a second iteration.

**Incremental delivery order**: US1 → US2 → US5 → US3 → US4 → Polish

---

## Validation Checklist

- [ ] All 28 tasks have `- [ ]` checkbox, sequential T-ID, correct `[P]` / `[Story]` labels, and exact file paths
- [ ] Each user story phase has an Independent Test criterion defined
- [ ] Phase 2 Foundation has explicit checkpoint note
- [ ] No tasks reference spec-013 internals by assumption — integration points call existing public methods
- [ ] All 4 endpoints from `contracts/openapi.yaml` are covered (T007, T010, T020, T021)
- [ ] All 5 user stories have at least 2 tasks each
- [ ] Triple decorator (`@require_jwt` + `@require_session` + `@require_company`) referenced in T007, T010, T020, T021 (ADR-011)
- [ ] `<list>` not `<tree>`, no `attrs` referenced in T014, T016 (ADR-001)
- [ ] Soft-delete `active` field included in T002 (ADR-015)
- [ ] Partial unique index in T002 (ADR-027)
- [ ] Anti-enumeration 404 in T020 (ADR-008)
- [ ] Swagger records in T023 (ADR-005)
- [ ] Postman collection in T025 (ADR-016)
