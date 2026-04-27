# Tasks: Property Proposals Management

**Feature Branch**: `013-property-proposals`
**Module**: `quicksol_estate` (Odoo 18.0)
**Input**: Design documents from [specs/013-property-proposals/](specs/013-property-proposals/)
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: INCLUDED — Constitution II (Test Coverage) is non-negotiable; spec defines 12 measurable success criteria requiring automated verification.

**Organization**: Tasks are grouped by user story so each P1 story can be delivered as an independent MVP increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: User story label (US1–US8); omitted for Setup/Foundational/Polish
- All paths assume repo root = `/opt/homebrew/var/www/realestate/realestate_backend`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository, ADR, and module manifest groundwork. Blocks Phase 2.

- [ ] T001 Author ADR-027 in [docs/adr/ADR-027-pessimistic-locking-resource-queues.md](docs/adr/ADR-027-pessimistic-locking-resource-queues.md) — document `SELECT FOR UPDATE` + partial unique index pattern as standard for active-slot resource queues (Constitution V mandate from plan.md Complexity Tracking)
- [ ] T002 [P] Bump module manifest version in [18.0/extra-addons/quicksol_estate/__manifest__.py](18.0/extra-addons/quicksol_estate/__manifest__.py) to `18.0.1.x.0` (next available) and add `'mail'` to `depends` if missing
- [ ] T003 [P] Create migration directory [18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/](18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/) with empty `pre-migrate.py` and `post-migrate.py` scaffolds
- [ ] T004 [P] Create test directory scaffold under [18.0/extra-addons/quicksol_estate/tests/](18.0/extra-addons/quicksol_estate/tests/) (ensure `__init__.py` exists; add empty `test_proposal_*.py` placeholders that will be filled per story)
- [ ] T005 [P] Add OpenAPI contract reference in module `__manifest__.py` `description` field linking to [specs/013-property-proposals/contracts/openapi.yaml](specs/013-property-proposals/contracts/openapi.yaml)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema, sequence, security groups, record rules, base lead/property extensions, and email templates. **No user-story task may start until this phase completes.**

### Schema & sequence

- [ ] T006 Create base `real.estate.proposal` model in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) with all 30+ fields per [data-model.md §1.1](specs/013-property-proposals/data-model.md) (state Selection, FSM placeholders, parent/superseded references, valid_until, cancellation/rejection reasons, computed `queue_position`, `is_active_proposal`, `documents_count`); inherit `mail.thread`, `mail.activity.mixin`; **do not** implement transition logic yet
- [ ] T007 [P] Add `_sql_constraints` and partial unique index migration in [18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/post-migrate.py](18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/post-migrate.py) — create `real_estate_proposal_one_active_per_property` (unique on `property_id` WHERE `state IN ('draft','sent','negotiation','accepted') AND active=true AND parent_proposal_id IS NULL`) per [data-model.md §1.4](specs/013-property-proposals/data-model.md)
- [ ] T008 [P] Add proposal sequence in [18.0/extra-addons/quicksol_estate/data/proposal_sequence.xml](18.0/extra-addons/quicksol_estate/data/proposal_sequence.xml) (`code='real.estate.proposal'`, `prefix='PRP'`, padding 5)
- [ ] T009 [P] Add lead `source` Selection field migration in [18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/pre-migrate.py](18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/pre-migrate.py) — backfill existing rows to `'manual'`
- [ ] T010 Extend [18.0/extra-addons/quicksol_estate/models/lead.py](18.0/extra-addons/quicksol_estate/models/lead.py) — add `source` Selection field (`'manual'|'proposal'|'website'|'import'`) and `proposal_ids` One2many back-reference per [data-model.md §2.1](specs/013-property-proposals/data-model.md)
- [ ] T011 [P] Extend [18.0/extra-addons/quicksol_estate/models/property.py](18.0/extra-addons/quicksol_estate/models/property.py) — add `proposal_ids` One2many, `active_proposal_id` computed reference, and `write()` override that auto-cancels active+queued proposals when `active` flips to False (FR-046, FR-046a) per [data-model.md §2.2](specs/013-property-proposals/data-model.md)

### Security & RBAC

- [ ] T012 [P] Create record rules in [18.0/extra-addons/quicksol_estate/security/proposal_record_rules.xml](18.0/extra-addons/quicksol_estate/security/proposal_record_rules.xml) — six rules per [data-model.md §1.6](specs/013-property-proposals/data-model.md): (1) company-isolation (`base.group_user`), (2) owner-all-company (`group_estate_owner`), (3) manager-all-company (`group_estate_manager`), (4) agent-own-only (`group_estate_agent`, domain `[('agent_id.user_id','=',user.id)]`), (5) **receptionist-read-only** (`group_estate_receptionist`, domain `[('company_id','in',company_ids)]`, `perm_read=1, perm_write=0, perm_create=0, perm_unlink=0`) per FR-036/FR-044, (6) prospector-deny (no rule — access removed in ACL)
- [ ] T013 [P] Add CRUD ACL rows in [18.0/extra-addons/quicksol_estate/security/ir.model.access.csv](18.0/extra-addons/quicksol_estate/security/ir.model.access.csv) for `real.estate.proposal` — five rows: owner (`1,1,1,1`), manager (`1,1,1,1`), agent (`1,1,1,0`), **receptionist (`1,0,0,0` — read-only per FR-036)**, prospector (omitted/no row)
- [ ] T014 Register security/data files in [18.0/extra-addons/quicksol_estate/__manifest__.py](18.0/extra-addons/quicksol_estate/__manifest__.py) `data` list: ir.model.access.csv, proposal_record_rules.xml, proposal_sequence.xml

### Email templates

- [ ] T015 [P] Create **seven** `mail.template` records in [18.0/extra-addons/quicksol_estate/data/mail_templates_proposal.xml](18.0/extra-addons/quicksol_estate/data/mail_templates_proposal.xml) covering all FR-041 events (Portuguese pt_BR; context vars per [research.md R5](specs/013-property-proposals/research.md)):
  1. `email_template_proposal_sent` — buyer notified when proposal sent
  2. `email_template_proposal_countered` — buyer notified when counter-proposal generated
  3. `email_template_proposal_accepted` — buyer + agent notified on acceptance
  4. `email_template_proposal_rejected` — buyer + agent notified on rejection (includes `rejection_reason`)
  5. `email_template_proposal_expired` — agent notified when validity expires (cron)
  6. `email_template_proposal_superseded` — losing-side agents notified when their proposal is auto-cancelled by an acceptance (includes back-link to winner)
  7. `email_template_proposal_promoted` — agent notified when their queued proposal is auto-promoted to draft

### Controller scaffolding

- [ ] T016 Create [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) with `ProposalController(http.Controller)` class — empty methods stubbed for the 10 endpoints from [contracts/openapi.yaml](specs/013-property-proposals/contracts/openapi.yaml); each stub MUST have `@require_jwt + @require_session + @require_company` decorator stack (Constitution I, ADR-011) and return 501 Not Implemented placeholder; ensure controller is imported in `controllers/__init__.py`
- [ ] T017 [P] Add JSON Schema validators directory [18.0/extra-addons/quicksol_estate/schemas/](18.0/extra-addons/quicksol_estate/schemas/) with `proposal_create.json`, `proposal_update.json`, `proposal_reject.json`, `proposal_counter.json`, `proposal_cancel.json` derived from openapi.yaml (ADR-018)

### Foundational tests

- [ ] T018 [P] Add base test fixtures in [18.0/extra-addons/quicksol_estate/tests/common.py](18.0/extra-addons/quicksol_estate/tests/common.py) — `ProposalTestCase(common.TransactionCase)` with helpers to create company, property, agent, manager, owner, partner

**Checkpoint**: After T018 completes (run `odoo -d realestate -u quicksol_estate --stop-after-init` cleanly), all 8 user stories may begin in parallel.

---

## Phase 3: User Story 1 — Agent registers and sends a proposal (P1) 🎯 MVP

**Goal**: Agent creates a draft proposal for a property, fills client+value+validity, then sends it (transitions to `sent`); buyer receives email; competitors are auto-queued.

**Independent Test**: From scratch, an agent can `POST /proposals` followed by `POST /proposals/{id}/send`; email delivered (visible in MailHog); listing the property's queue shows this proposal as active.

### Tests for US1

- [ ] T019 [P] [US1] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_create.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_create.py) — create returns draft, code auto-generated, validity bounds enforced, RBAC denies portal, partner auto-resolution by document, **CPF/CNPJ format validation rejects malformed documents (FR-033)**
- [ ] T020 [P] [US1] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_send.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_send.py) — draft→sent transition only, sent_date stamped, email queued via Outbox, attempting send on terminal state raises UserError
- [ ] T021 [P] [US1] Integration test [integration_tests/test_us1_proposal_create_send.sh](integration_tests/test_us1_proposal_create_send.sh) — POST /proposals (201), POST /proposals/{id}/send (200), assert MailHog receives email
- [ ] T022 [P] [US1] Cypress E2E [cypress/e2e/views/proposals.cy.js](cypress/e2e/views/proposals.cy.js) — agent navigates to property → creates proposal → clicks Send → sees status badge change

### Implementation for US1

- [ ] T022a [US1] Implement CPF/CNPJ validation in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) (FR-033) — add `@api.constrains('partner_id')` method `_check_document_format` that calls `validate_document(partner_id.vat)` from `utils/validators.py` (raises `ValidationError` if neither valid CPF nor valid CNPJ); also normalize via `normalize_document()` at controller boundary in `proposal_create.json` schema validation step (T026), so leading zeros / punctuation are accepted in input
- [ ] T023 [US1] Implement `create()` override in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — acquire `SELECT FOR UPDATE` on `real_estate_property` row, decide initial state (`draft` if no active competitor, `queued` if exists), generate `proposal_code` from sequence, resolve/create partner via `client_document` ([research.md R1](specs/013-property-proposals/research.md))
- [ ] T024 [US1] Implement `_validate_valid_until()` constraint in same file — bounds `today < x ≤ today+90d`, default 7 days when null (FR-025a, [research.md R6](specs/013-property-proposals/research.md))
- [ ] T025 [US1] Implement `action_send()` method on the model — assert state==`draft`, set state=`sent`, stamp `sent_date`, emit Outbox event `proposal.sent` (FR-013, [research.md R5](specs/013-property-proposals/research.md))
- [ ] T026 [US1] Wire controller `POST /api/v1/proposals` (createProposal) in [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) — JSON Schema validate against `proposal_create.json`, build vals dict, call `create()`, return serialized proposal with HATEOAS links
- [ ] T027 [US1] Wire controller `POST /api/v1/proposals/{id}/send` (sendProposal) — call `action_send()`, return updated proposal; 422 on invalid state, 403 on RBAC
- [ ] T028 [US1] Wire controller `GET /api/v1/proposals/{id}` (getProposal) — return full Proposal schema including `proposal_chain` and `attachments`
- [ ] T029 [P] [US1] Add Outbox event consumer task `send_proposal_email_task` in [18.0/celery_worker/tasks/proposal_tasks.py](18.0/celery_worker/tasks/proposal_tasks.py) — picks `proposal.sent` event, renders `email_template_proposal_sent`, on failure logs to chatter without rolling back DB transaction (FR-041a)
- [ ] T030 [P] [US1] Add proposal form/list/kanban views in [18.0/extra-addons/quicksol_estate/views/proposal_views.xml](18.0/extra-addons/quicksol_estate/views/proposal_views.xml) — register in `__manifest__.py` data list

**Checkpoint**: US1 fully functional. Run T019–T022 — all green.

---

## Phase 4: User Story 2 — FIFO queue on the same property (P1)

**Goal**: When ≥2 proposals exist for the same property, exactly one occupies the active slot; others are `queued` ordered by `created_date ASC`; the next queued auto-promotes when the active one moves to a non-active terminal (rejected/expired/cancelled).

**Independent Test**: Concurrently POST 10 proposals on a single property; query `/queue` — exactly one with `state IN ('draft','sent','negotiation')`, rest `queued` in arrival order. Reject the active → next queued promotes to `draft`.

### Tests for US2

- [ ] T031 [P] [US2] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_queue.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_queue.py) — second concurrent create lands as `queued`; reject active promotes head of queue; cancel active promotes head; queue order is FIFO
- [ ] T032 [P] [US2] Concurrency stress test [integration_tests/test_us_proposal_concurrent_creation.sh](integration_tests/test_us_proposal_concurrent_creation.sh) — 100 trials × 10 parallel POSTs; assert exactly 1 active per trial (SC-003)
- [ ] T033 [P] [US2] Integration test [integration_tests/test_us2_proposal_fifo_queue.sh](integration_tests/test_us2_proposal_fifo_queue.sh) — full lifecycle: 5 sequential creates, verify queue ordering, reject active, verify auto-promotion

### Implementation for US2

- [ ] T034 [US2] Implement `_promote_next_queued()` private method in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — locks property row, finds oldest `queued` sibling, transitions it to `draft`, called from rejected/expired/cancelled hooks
- [ ] T035 [US2] Implement computed `queue_position` and `is_active_proposal` fields with stored compute + `@api.depends('property_id.proposal_ids.state', 'created_date')` per [data-model.md §1.3](specs/013-property-proposals/data-model.md) and [research.md R9](specs/013-property-proposals/research.md)
- [ ] T036 [US2] Wire controller `GET /api/v1/proposals/{id}/queue` (getProposalQueue) in [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) — return `{property_id, active_proposal, queue: [...]}`

**Checkpoint**: SC-003 (zero double-active under concurrency) verified by T032.

---

## Phase 5: User Story 3 — Counter-proposals (P1)

**Goal**: Agent or buyer (via agent) issues a counter; parent moves to `negotiation`, child takes the active slot, both share `proposal_chain` lineage. Accepting any node in the chain auto-supersedes all siblings.

**Independent Test**: Send proposal A (active) → POST /proposals/A/counter → A becomes `negotiation`, B is `draft` active; partial unique index ignores B because parent_proposal_id IS NOT NULL... wait — re-read [research.md R4](specs/013-property-proposals/research.md). Actually B is the active record for that property and WILL hit the unique index — see clarification below.

> **Implementation note (from R4)**: The partial unique index excludes children (`parent_proposal_id IS NULL` clause). When A → `negotiation`, A is no longer in `('draft','sent')` so unique constraint allows B to take active slot as a child whose state is `draft`. Only one child per chain may be active at a time, enforced by `_check_one_active_in_chain` Python constraint.

### Tests for US3

- [ ] T037 [P] [US3] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_counter.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_counter.py) — counter creates child with parent set, parent transitions to `negotiation`, accept on child supersedes parent, accept on parent supersedes child, chain reads chronologically
- [ ] T038 [P] [US3] Integration test [integration_tests/test_us3_proposal_counter.sh](integration_tests/test_us3_proposal_counter.sh) — A→counter B→counter C lineage, accept C, verify A and B set to `superseded_by_id=C` and state=`cancelled`

### Implementation for US3

- [ ] T039 [US3] Implement `action_counter(vals)` method in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — assert state in (`sent`,`negotiation`), transition self to `negotiation`, create child with `parent_proposal_id=self.id`, copy property/lead/agent/client; emit `proposal.countered` event
- [ ] T040 [US3] Add `_check_one_active_in_chain` Python `@api.constrains` ensuring only one record per chain has state in active set
- [ ] T041 [US3] Implement `proposal_chain` computed (recurse via `parent_proposal_id`) in same file
- [ ] T042 [US3] Wire controller `POST /api/v1/proposals/{id}/counter` (counterProposal) — validate body against `proposal_counter.json`, call `action_counter()`, return 201 with new child

---

## Phase 6: User Story 4 — Accept or reject (P1)

**Goal**: Manager/owner accepts (auto-cancels competitors and chain siblings; emits HATEOAS link to create-contract) or rejects (with reason; promotes next queued; emails buyer).

**Independent Test**: Accept A → all other proposals on the same property (including queued and chain siblings) become `cancelled` with `superseded_by_id=A`. Reject A with reason → buyer email sent, queued head promoted.

### Tests for US4

- [ ] T043 [P] [US4] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_accept_reject.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_accept_reject.py) — accept supersedes all property proposals, accept emits `proposal.accepted` event with HATEOAS link, reject requires reason, reject promotes next queued, agent cannot accept (only manager/owner — FR-043)
- [ ] T044 [P] [US4] Integration test [integration_tests/test_us4_proposal_accept_reject.sh](integration_tests/test_us4_proposal_accept_reject.sh) — full happy path + RBAC denials

### Implementation for US4

- [ ] T045 [US4] Implement `action_accept()` in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — assert state in (`sent`,`negotiation`), assert `env.user` has manager/owner group, set state=`accepted`/`accepted_date`, batch-update siblings (same property OR same chain) to `cancelled` with `superseded_by_id=self.id`, archive lead automatically, emit `proposal.accepted` event including `_links: [{rel:'create-contract', href:'/api/v1/contracts?from_proposal=ID', method:'POST'}]`
- [ ] T046 [US4] Implement `action_reject(reason)` — assert state in (`sent`,`negotiation`), require reason, set state=`rejected`/`rejected_date`/`rejection_reason`, call `_promote_next_queued()`, emit `proposal.rejected` event
- [ ] T047 [US4] Wire controller `POST /api/v1/proposals/{id}/accept` (acceptProposal)
- [ ] T048 [US4] Wire controller `POST /api/v1/proposals/{id}/reject` (rejectProposal) — validate body against `proposal_reject.json`
- [ ] T049 [US4] Wire controller `DELETE /api/v1/proposals/{id}` (cancelProposal) — soft-cancel with reason; same promotion logic as reject

---

## Phase 7: User Story 5 — Lead capture from proposal contact (P2)

**Goal**: When proposal is created with a `client_document` not matching any existing lead in the company, auto-create `real.estate.lead` with `source='proposal'` and link via `lead_id`.

**Independent Test**: POST /proposals with new CPF → assert a new lead record exists with that CPF, `source='proposal'`, `state='new'`, linked back via `lead.proposal_ids`.

### Tests for US5

- [ ] T050 [P] [US5] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_lead_integration.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_lead_integration.py) — new doc creates lead, existing doc reuses lead, lead source set correctly, lead state mapping per [research.md R2](specs/013-property-proposals/research.md)
- [ ] T051 [P] [US5] Integration test [integration_tests/test_us5_proposal_lead_capture.sh](integration_tests/test_us5_proposal_lead_capture.sh)

### Implementation for US5

- [ ] T052 [US5] Implement `_resolve_or_create_lead(client_document, ...)` helper in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — search by `(company_id, partner_id.vat==document)`, create with `source='proposal'`, `state='new'`, `assigned_agent_id=agent_id` if missing
- [ ] T053 [US5] Hook `_resolve_or_create_lead` into `create()` override (extends T023)

---

## Phase 8: User Story 6 — Listing, filtering, and metrics (P1)

**Goal**: Authenticated users list proposals scoped to their company with filters (state, agent, property, partner, search, date range) and aggregated `/stats` (counts per state).

**Independent Test**: GET /proposals?state=sent&agent_id=X returns only matching records of caller's company; GET /proposals/stats returns 8 buckets summing to total.

### Tests for US6

- [ ] T054 [P] [US6] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_list.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_list.py) — pagination, filters, multi-tenant scoping (FR-044), search across code/client/property, **receptionist sees full org list with no mutation links in `_links` (FR-036)**, agent sees only own proposals (FR-035)
- [ ] T055 [P] [US6] Integration test [integration_tests/test_us6_proposal_list_filters_metrics.sh](integration_tests/test_us6_proposal_list_filters_metrics.sh)

### Implementation for US6

- [ ] T056 [US6] Wire controller `GET /api/v1/proposals` (listProposals) in [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) — build domain from query params, apply pagination (max page_size=100), return `{data, _meta, _links}`
- [ ] T057 [US6] Wire controller `GET /api/v1/proposals/stats` (getProposalStats) — `read_group` by state, return `{total, by_state}`
- [ ] T058 [P] [US6] Wire controller `PUT /api/v1/proposals/{id}` (updateProposal) — validate against `proposal_update.json`, allow only in non-terminal states, RBAC: agent on own/draft, manager/owner on any non-terminal

---

## Phase 9: User Story 7 — Document attachments (P2)

**Goal**: Users attach documents (PDF/JPG/PNG, ≤10 MB each) to proposals; downloaded via signed URLs; visible in proposal detail.

**Independent Test**: POST /proposals/{id}/attachments with multipart file → 201 returns AttachmentRef; GET /proposals/{id} includes attachment in `attachments[]`; >10 MB returns 413.

### Tests for US7

- [ ] T059 [P] [US7] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_attachments.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_attachments.py) — accepted mimetypes, size limit, RBAC, ir.attachment company scoping
- [ ] T060 [P] [US7] Integration test [integration_tests/test_us7_proposal_attachments.sh](integration_tests/test_us7_proposal_attachments.sh)

### Implementation for US7

- [ ] T061 [US7] Wire controller `POST /api/v1/proposals/{id}/attachments` (uploadProposalAttachment) in [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) — validate mimetype whitelist (FR-039: **PDF `application/pdf`, JPEG `image/jpeg`, PNG `image/png`, DOC `application/msword`, DOCX `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, XLS `application/vnd.ms-excel`, XLSX `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`** — reject any other type with 400), enforce 10 MB per-file cap (413 PayloadTooLarge), create `ir.attachment` linked via `res_model='real.estate.proposal'`, `res_id`, scope `company_id`, return AttachmentRef
- [ ] T062 [US7] Add `documents_count` computed field and `attachments` getter in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — query `ir.attachment` filtered by model+id+company

---

## Phase 10: User Story 8 — Automatic expiration (P3)

**Goal**: A scheduled cron transitions any proposal where `valid_until < today` and state ∈ (`draft`,`sent`,`negotiation`) to `expired`; promotes next queued; emails owner.

**Independent Test**: Create proposal with `valid_until=yesterday` (via SQL), trigger cron, assert state=`expired` and queued head promoted.

### Tests for US8

- [ ] T063 [P] [US8] Unit tests in [18.0/extra-addons/quicksol_estate/tests/test_proposal_expiration.py](18.0/extra-addons/quicksol_estate/tests/test_proposal_expiration.py) — cron picks expired-eligible only, promotes queue, emits event
- [ ] T064 [P] [US8] Integration test [integration_tests/test_us8_proposal_expiration.sh](integration_tests/test_us8_proposal_expiration.sh)

### Implementation for US8

- [ ] T065 [US8] Implement `_cron_expire_proposals()` class method in [18.0/extra-addons/quicksol_estate/models/proposal.py](18.0/extra-addons/quicksol_estate/models/proposal.py) — search expired-eligible records (chunked, batch=200), set state=`expired`, call `_promote_next_queued()`, emit `proposal.expired` events
- [ ] T066 [P] [US8] Define cron in [18.0/extra-addons/quicksol_estate/data/proposal_cron.xml](18.0/extra-addons/quicksol_estate/data/proposal_cron.xml) — `ir.cron` runs hourly; register in manifest

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, observability, performance, and final validation across all user stories.

- [ ] T067 [P] Publish OpenAPI spec at [docs/openapi/proposals.yaml](docs/openapi/proposals.yaml) (copy + diff vs contracts/openapi.yaml — ADR-005)
- [ ] T068 [P] Generate Postman collection [docs/postman/feature013_property_proposals_v1.0_postman_collection.json](docs/postman/feature013_property_proposals_v1.0_postman_collection.json) with environment variables `base_url`, `access_token`, `session_id` (ADR-016) — invoke `thedevkitchen.postman` agent for compliance
- [ ] T069 [P] Add OpenTelemetry spans on all 10 controller endpoints in [18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py](18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py) — span attrs: `proposal.id`, `proposal.state_from`, `proposal.state_to`, `company.id`
- [ ] T070 [P] Index audit — confirm DB indexes from [data-model.md §1.5](specs/013-property-proposals/data-model.md) exist via `\d+ real_estate_proposal` (composite `(company_id, state)`, `(property_id, state, created_date)`, `(parent_proposal_id)`)
- [ ] T071 Run full test suite end-to-end: `docker compose exec odoo odoo -d realestate --test-tags /quicksol_estate --stop-after-init` plus all `./integration_tests/test_us[1-8]_proposal_*.sh` plus race test plus `npx cypress run --spec 'cypress/e2e/views/proposals.cy.js'`
- [ ] T072 Validate every Success Criterion (SC-001 through SC-012) from [spec.md §Success Criteria](specs/013-property-proposals/spec.md) — produce a results matrix in PR description
- [ ] T073 Bump constitution to v1.4.0 in [.specify/memory/constitution.md](.specify/memory/constitution.md) — add Concurrency Patterns section referencing ADR-027
- [ ] T074 Walk through [quickstart.md](specs/013-property-proposals/quickstart.md) §5 manually as final acceptance gate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; T001 (ADR-027) is a documentation task and not a code blocker, but ADR-027 MUST be authored before Phase 11 PR review
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phases 3–10 (User Stories)**: All depend on Phase 2 completion; mostly independent of each other
- **Phase 11 (Polish)**: Depends on all desired user stories

### Cross-story dependencies

- **US3 (Counter)** depends conceptually on US1 (creation/send) — share `proposal.py` model file
- **US4 (Accept/Reject)** depends conceptually on US2 (queue promotion) — `_promote_next_queued()` is implemented in US2 (T034) and consumed by US4 (T046, T049)
- **US5 (Lead capture)** depends on US1's `create()` override (extends T023 in T053)
- **US8 (Expiration)** depends on US2's `_promote_next_queued()` helper (T034)

### Within Each User Story

- Tests are written first; verify they FAIL before implementation
- Model methods → controller wiring → views
- Migration tasks (Phase 2) precede any code that references new schema

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005 in parallel after T001
- **Phase 2**: T006 first; then T007, T008, T009, T011, T012, T013, T015, T017, T018 in parallel; T010 depends on T009; T014 depends on T012, T013, T015; T016 last (depends on group definitions)
- **Cross-phase**: After T018 completes, **all 8 user-story phases (3–10) can be assigned to different developers in parallel**
- **Within each story**: Test tasks (marked [P]) run in parallel; implementation tasks generally sequential due to shared file `proposal.py`

---

## Parallel Example: After Foundational checkpoint

```bash
# Three developers in parallel (T018 just finished):
# Dev A: T019, T020, T021, T022 (US1 tests) → T023..T030 (US1 impl)
# Dev B: T031, T032, T033          (US2 tests) → T034..T036 (US2 impl)
# Dev C: T037, T038                (US3 tests) → T039..T042 (US3 impl)

# Then converge for US4 (needs US2's _promote_next_queued):
# Any dev: T043, T044 → T045..T049
```

---

## Implementation Strategy

### MVP scope (recommended)

**Phases 1 + 2 + 3 + 4 + 6 + 8** (Setup + Foundational + US1 + US2 + US4 + US6) deliver the core P1 value:
- Create, send, accept, reject proposals
- FIFO queue with auto-promotion
- List/filter/metrics

This is the minimum viable increment that exercises the active-slot invariant (the most architecturally novel piece) and all RBAC paths. Counter-proposals (US3) and lead capture (US5) can ship in a fast-follow because they don't change the queue invariant.

### Incremental delivery sequence

1. **Sprint 1 (MVP)**: Phases 1 → 2 → 3 → 4 → 6 → 8 → minimal Polish (T067, T071, T072)
2. **Sprint 2**: Phase 5 (US3 Counter) + Phase 7 (US5 Lead capture) + Phase 9 (US7 Attachments)
3. **Sprint 3**: Phase 10 (US8 Expiration) + remaining Polish

---

## Format Validation Checklist

All tasks above conform to: `- [ ] TXXX [P?] [USx?] Description with file path`

- ✅ Every task has a markdown checkbox `- [ ]`
- ✅ Every task has a sequential ID (T001–T074)
- ✅ Setup/Foundational/Polish tasks have **no** `[USx]` label
- ✅ Every task in Phases 3–10 has a `[USx]` label
- ✅ `[P]` marker only on tasks with no dependency on incomplete prior tasks AND distinct file targets
- ✅ Every task references at least one absolute or workspace-relative file path
- ✅ All 10 OpenAPI endpoints (T026, T027, T028, T036, T042, T047, T048, T049, T056, T057, T058, T061) covered
- ✅ All 8 user stories have at least one test task and one implementation task
- ✅ All Foundational schema tasks (T006–T015) precede first model logic task (T023)

---

**Total Tasks**: 75
**Per User Story**: US1=13 (T019–T030 + T022a), US2=6 (T031–T036), US3=6 (T037–T042), US4=7 (T043–T049), US5=4 (T050–T053), US6=5 (T054–T058), US7=4 (T059–T062), US8=4 (T063–T066)
**Setup**: 5 | **Foundational**: 13 | **Polish**: 8

**Suggested MVP scope**: Phases 1 + 2 + 3 + 4 + 6 + 8 (T001–T036 + T043–T049 + T054–T058 + T063–T066 + minimal polish)
