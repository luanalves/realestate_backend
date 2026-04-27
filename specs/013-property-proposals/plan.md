# Implementation Plan: Property Proposals Management

**Branch**: `013-property-proposals` | **Date**: 2026-04-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-property-proposals/spec.md`

## Summary

Implement a complete proposal management capability for properties, including an 8-state FSM (Draft, Queued, Sent, Negotiation, Accepted, Rejected, Expired, Cancelled), strict FIFO active-slot enforcement (one active proposal per property + automatic queue), counter-proposal versioning, lead auto-capture with source `proposal`, document attachments, daily expiration cron, and asynchronous email notifications via Outbox pattern. The technical approach reuses the existing `quicksol_estate` Odoo module (siblings: `real.estate.lead`, `real.estate.property`, `real.estate.agent`, `real.estate.lease`, `real.estate.sale`), adds a new `real.estate.proposal` model with a partial unique index for the active slot constraint and pessimistic row locking on the parent property to eliminate concurrent-creation races. REST endpoints follow the project's mandatory triple-decorator security model (`@require_jwt` + `@require_session` + `@require_company`) with HATEOAS links conditional on state and role. All non-blocking side effects (emails, notifications) flow through Celery via the existing `notification_events` queue.

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0)
**Primary Dependencies**: Odoo 18.0 framework, `quicksol_estate` (existing module — property, lead, agent), `thedevkitchen_apigateway` (auth: JWT + session + company), `mail` (Odoo built-in: `mail.thread`, `mail.template`, `mail.activity.mixin`), Celery 5.3.4 with Redis backend, `psycopg2` (PostgreSQL driver)
**Storage**: PostgreSQL 14+ (primary persistence; partial unique index + `SELECT FOR UPDATE` row locking), Redis 7-alpine (DB index 1 for Odoo sessions/cache, DB 2 for Celery results), `ir.attachment` for documents (Odoo's built-in filestore)
**Testing**: `odoo.tests.common.TransactionCase` (unit + integration), Bash integration scripts in `integration_tests/` (E2E API), Cypress 13+ (E2E UI per ADR-002)
**Target Platform**: Linux server (Docker Compose), Odoo Web UI for internal/manager users + REST API for headless SSR frontend (per Constitution VI Headless Architecture)
**Project Type**: Single Odoo module (extends existing `quicksol_estate`) with API controllers in `controllers/` subfolder — follows ADR-001 flat structure
**Performance Goals**: List endpoint p95 < 1s for orgs with 50k proposals (SC-005); metrics endpoint p95 < 200ms (SC-006); auto-promotion after slot release < 5s (SC-002); daily expiration cron < 5min for 10k active proposals (SC-010); email dispatch < 30s under nominal load (SC-011)
**Constraints**: 100% multi-tenant isolation via `company_id` + record rules (Constitution IV); soft-delete only (ADR-015) — no hard deletes; cancelled/expired records remain queryable; strict 1-active-proposal-per-property invariant must hold under arbitrary concurrency (SC-003: 100 trials with 10 parallel writes); Brazilian Portuguese (pt_BR) for all user-facing strings; CPF/CNPJ document validation only
**Scale/Scope**: Targeting up to ~50,000 proposals per organization with ~200 organizations; ~10 user-facing endpoints; 1 new model (`real.estate.proposal`) + 2 model extensions (`real.estate.lead.source`, `real.estate.lead.proposal_ids`); 7 mail templates (pt_BR); 4 Odoo views (list/form/kanban/search); 1 daily cron

## Constitution Check

*Gate evaluation against [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.3.0.*

| Principle | Status | Notes |
|---|---|---|
| **I. Security First (NON-NEGOTIABLE)** | ✅ PASS | All authenticated endpoints will use triple decorators (`@require_jwt` + `@require_session` + `@require_company`). No public endpoints in this feature. Session fingerprinting (ADR-017) inherited from `thedevkitchen_apigateway`. |
| **II. Test Coverage Mandatory (NON-NEGOTIABLE)** | ✅ PASS | Plan includes unit tests (FSM, validations, queue, race), integration tests (Bash scripts in `integration_tests/`), and Cypress E2E for the 4 Odoo views. Target ≥80% per ADR-003. |
| **III. API-First Design (NON-NEGOTIABLE)** | ✅ PASS | OpenAPI 3.0 spec produced in `contracts/openapi.yaml`; HATEOAS links conditional on state/role (ADR-007); Postman collection delivered post-development per ADR-016. |
| **IV. Multi-Tenancy by Design (NON-NEGOTIABLE)** | ✅ PASS | `company_id` required on every proposal; record rules enforce isolation; `@require_company` on every endpoint; SC-009 = 0 cross-org leakage; isolation tests planned. |
| **V. ADR Governance** | ⚠️ ACTION REQUIRED | New pattern: pessimistic row locking + partial unique index for FIFO queue. **Must create ADR-027 "Pessimistic Locking for Resource Queues" before implementation.** Captured in Complexity Tracking. |
| **VI. Headless Architecture (NON-NEGOTIABLE)** | ✅ PASS | REST endpoints serve the SSR frontend; Odoo views serve internal managers. Both interfaces designed in this plan. No coupling between them. |

**Async Processing (ADR-021)**: Notifications flow through `celery_notification_worker` via `notification_events` queue (Outbox pattern, per Q2 clarification). State transitions remain synchronous; emails are decoupled.

**Forbidden Patterns Audit**: No `.sudo()` planned in controllers; no `auth='public'`; no single-decorator endpoints; no hardcoded credentials.

**Initial Gate Result**: PASS with one mandatory pre-implementation deliverable (ADR-027). Re-evaluation after Phase 1 design at end of plan.

### Post-Design Re-Check (after Phase 1 artifacts)

After producing [research.md](research.md), [data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml), and [quickstart.md](quickstart.md), the design was re-evaluated against the same six principles:

| Principle | Re-Check | Notes |
|---|---|---|
| I. Security First | ✅ PASS | OpenAPI declares `jwtBearer` + `sessionCookie` security globally; every operation defaults to triple auth (no `security: []` overrides). All controller paths in `data-model.md` validate company scope and role per FR-043/FR-044. |
| II. Test Coverage | ✅ PASS | `quickstart.md §4` enumerates 9 integration scripts (US1–US8 + race) and Cypress E2E spec; `data-model.md §6` cross-references each FR to its enforcement point and test target. |
| III. API-First | ✅ PASS | `contracts/openapi.yaml` is the authoritative contract for 10 endpoints with full request/response schemas, error catalogue, and HATEOAS shape. Postman collection deferred per ADR-016 (post-development deliverable). |
| IV. Multi-Tenancy | ✅ PASS | `data-model.md §1.6` defines 5 record rules; `company_id` is required on every record; `@require_company` on every endpoint. |
| V. ADR Governance | ⚠️ ACTION OPEN | ADR-027 still pending — same deliverable as initial check; tracked in Complexity Tracking. No new ADRs introduced by Phase 1 design beyond the originally-identified one. |
| VI. Headless Architecture | ✅ PASS | REST contract serves SSR frontend; Odoo views serve internal users. No coupling. |

**Post-Design Gate Result**: PASS. No new violations introduced by Phase 1. The single open action (author ADR-027) remains the only blocker before `/speckit.tasks` and implementation.

## Project Structure

### Documentation (this feature)

```text
specs/013-property-proposals/
├── plan.md                  # This file
├── research.md              # Phase 0 output: research decisions
├── data-model.md            # Phase 1 output: entities, fields, constraints
├── quickstart.md            # Phase 1 output: developer onboarding
├── contracts/
│   └── openapi.yaml         # Phase 1 output: OpenAPI 3.0 contract
├── checklists/
│   └── requirements.md      # Spec quality checklist
└── tasks.md                 # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

This feature extends the existing `quicksol_estate` Odoo module (siblings to `real.estate.lead`, `real.estate.property`, `real.estate.agent`). Per ADR-001, structure is flat (no nested package folders).

```text
18.0/extra-addons/quicksol_estate/
├── models/
│   ├── proposal.py                       # NEW: real.estate.proposal model + FSM logic
│   ├── lead.py                           # EXTEND: add 'source' field selection + proposal_ids One2many
│   └── property.py                       # EXTEND: add proposal_ids One2many + archive cascade hook
├── controllers/
│   └── proposal_controller.py            # NEW: REST endpoints (10 routes) with triple auth
├── views/
│   ├── proposal_views.xml                # NEW: list, form, kanban, search views
│   └── proposal_menus.xml                # NEW: menu entries
├── security/
│   ├── ir.model.access.csv               # EXTEND: ACL for real.estate.proposal
│   └── proposal_record_rules.xml         # NEW: company isolation + agent-own rules
├── data/
│   ├── proposal_sequence.xml             # NEW: ir.sequence for PRP### codes
│   ├── proposal_cron.xml                 # NEW: daily expiration cron
│   └── mail_templates_proposal.xml       # NEW: 7 pt_BR transactional templates
├── migrations/
│   └── 18.0.1.x.0/
│       ├── pre-migrate.py                # OPTIONAL: lead source data migration
│       └── post-migrate.py               # Create partial unique index
├── tests/
│   ├── test_proposal_model.py            # NEW: unit tests (FSM, constraints, queue, race)
│   ├── test_proposal_controller.py       # NEW: API tests (auth, validation, RBAC)
│   └── test_proposal_lead_integration.py # NEW: lead auto-creation tests
└── __manifest__.py                       # EXTEND: add new files + bump version

integration_tests/
├── test_us1_proposal_create_send.sh                # NEW: US1 E2E
├── test_us2_proposal_fifo_queue.sh                 # NEW: US2 E2E
├── test_us3_proposal_counter.sh                    # NEW: US3 E2E
├── test_us4_proposal_accept_reject.sh              # NEW: US4 E2E (incl. supersede)
├── test_us5_proposal_lead_capture.sh               # NEW: US5 E2E
├── test_us6_proposal_list_filters_metrics.sh       # NEW: US6 E2E
├── test_us7_proposal_attachments.sh                # NEW: US7 E2E
├── test_us8_proposal_expiration.sh                 # NEW: US8 E2E
└── test_us_proposal_concurrent_creation.sh         # NEW: race-condition load test (SC-003)

cypress/e2e/views/
└── proposals.cy.js                                 # NEW: Odoo views E2E

docs/
├── adr/
│   └── ADR-027-pessimistic-locking-resource-queues.md   # NEW (mandatory before implementation)
├── openapi/
│   └── proposals.yaml                              # POST-DEV: ADR-005 publishing
└── postman/
    └── feature013_property_proposals_v1.0_postman_collection.json   # POST-DEV: ADR-016
```

**Structure Decision**: Single Odoo module (`quicksol_estate`) extension — chosen because (a) Proposal is a real-estate domain entity tightly coupled to existing siblings (`Property`, `Lead`, `Agent`); (b) ADR-004 naming convention `real.estate.*` is reserved for this module; (c) extracting into a separate module would force cross-module dependencies for record rules and would not improve testability. Web frontend lives outside this repo (consumed via REST). Internal Odoo views are part of the same module for managers/owners.

## Complexity Tracking

| Violation / New Pattern | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Pessimistic row locking (`SELECT FOR UPDATE`) on `real.estate.property`** during proposal creation | Guarantee single-active-proposal invariant under arbitrary concurrent writes (SC-003). | Optimistic concurrency (re-check + retry): requires retry budget and produces non-deterministic latency under contention; partial unique index alone catches the violation but produces a 500-equivalent IntegrityError that the user has to recover from instead of the system handling it gracefully into Queued state. Pessimistic lock makes the FIFO assignment deterministic and atomic. |
| **Partial unique index** (`WHERE state IN (active states) AND active=true`) | Defense-in-depth against the same invariant if application logic is bypassed (e.g., direct SQL, future bug). | Pure application-level check: would not protect against future regressions or multi-process deployments without table-level guarantee. PostgreSQL partial unique index is a low-cost belt-and-suspenders measure. |
| **Outbox-style async email dispatch** (Q2) | Decouple critical state transitions (acceptance, supersede) from a non-critical I/O dependency (SMTP) so a transient email outage cannot block the business outcome. | Synchronous email send in the same transaction: blocks the user, couples persistence to network availability, and contradicts ADR-021 (which mandates async for notifications). |
| **New ADR-027 (Pessimistic Locking for Resource Queues)** | Formalizes the locking pattern so it is reusable (e.g., for similar future single-resource queues such as inspection slots, agent assignments) and reviewable in code review. | No ADR + comment in code: violates Constitution V (ADR Governance) which requires new patterns to be documented as ADRs before implementation. |
