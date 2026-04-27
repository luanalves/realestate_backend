# Phase 0 Research: Property Proposals Management

**Feature**: 013-property-proposals
**Date**: 2026-04-27
**Purpose**: Resolve all NEEDS CLARIFICATION items, document key technical decisions, and capture rationale for design choices that affect implementation.

---

## R1. Concurrency Strategy for Single-Active-Proposal Invariant

**Decision**: Use PostgreSQL pessimistic row locking (`SELECT FOR UPDATE`) on the parent `real.estate.property` row during proposal creation, combined with a partial unique index on `(property_id) WHERE state IN ('draft','sent','negotiation','accepted') AND active=true` for defense-in-depth.

**Rationale**:

- The invariant "exactly one active proposal per property" must hold under arbitrary concurrent writes (FR-016, SC-003: 100 trial runs, 10 parallel agents, never two actives).
- Pessimistic locking yields deterministic FIFO ordering: the first transaction to acquire the lock writes Draft; later transactions see the existing active row and write Queued. No retry logic, no jitter, no ambiguity in queue position.
- The partial unique index serves as a database-level safety net: even if a future code path bypasses the locking logic (direct SQL, future controller, ORM mistake), the database refuses to commit a second active row.
- Both PostgreSQL and Odoo's ORM support `FOR UPDATE` cleanly via `cr.execute("SELECT id FROM real_estate_property WHERE id = %s FOR UPDATE", [property_id])` inside the transaction handling proposal creation.

**Alternatives considered**:

- **Optimistic concurrency (read → check → write → retry on conflict)**: Rejected. Produces non-deterministic latency under contention; no clean way to bias FIFO ordering across retries; and turns IntegrityError into a user-visible failure instead of a graceful queueing.
- **Application-level lock (Redis/Redlock)**: Rejected. Adds a separate failure domain; only protects against clients that opt in; doesn't survive process restarts. PostgreSQL row locks are already transactional.
- **Advisory locks (`pg_advisory_xact_lock`)**: Considered. Equally valid but less idiomatic in Odoo; row locking is more discoverable in code review.

**Action**: Create `ADR-027 Pessimistic Locking for Resource Queues` capturing this pattern before implementation begins (Constitution V mandate).

---

## R2. Lead State Mapping for De-duplication (FR-030/FR-031)

**Decision**: A lead is considered "active" (and thus reused for a new proposal without duplication) when `real.estate.lead.state IN ('new','contacted','qualified','won')` AND `active = true`. Leads in `state='lost'` or with `active=false` (soft-deleted) are treated as non-existent and a new lead with `source='proposal'` is created.

**Rationale**:

- Inspection of the existing `real.estate.lead` model (`18.0/extra-addons/quicksol_estate/models/lead.py`) confirms the actual selection values: `new`, `contacted`, `qualified`, `won`, `lost`. The clarification answer (Q1) used illustrative names that do not match the project; this research item maps them correctly.
- `won` corresponds to a successfully converted lead but the contact may legitimately re-enter the pipeline for a new property — re-using a `won` lead preserves history and contact relationship without distorting the original conversion.
- `lost` represents a closed/dead opportunity; re-engaging warrants a fresh lead with proper source attribution (`proposal`) for funnel analytics.
- Soft-deleted leads are excluded by every Odoo default search; treating them as non-existent matches user expectations and the existing project pattern.

**Alternatives considered**:

- Treat only `new` and `contacted` as active: too restrictive — would create duplicates whenever the lead has progressed at all.
- Always link to the latest matching lead regardless of state: too permissive — would re-attach to dead leads, polluting the pipeline.

**Schema Impact**:

- The `real.estate.lead` model currently has no `source` field. This feature must add a `source` Selection field (data migration adds default 'proposal' option plus existing standard sources to be defined in spec extension). Captured in `data-model.md`.

---

## R3. FSM Implementation Approach

**Decision**: Encode the 8-state FSM as a Python `dict` mapping `(from_state, to_state) → callable_guard` and expose explicit action methods (`action_send`, `action_accept`, `action_reject`, `action_counter`, `action_cancel`, `action_promote_from_queue`). State writes go through a single private `_set_state(new_state, **kwargs)` that runs the guard, persists the state change, fires `mail.thread` message, and enqueues notifications via Celery.

**Rationale**:

- A single chokepoint for state changes makes guard enforcement, audit logging, and async notification dispatch consistent and testable.
- Explicit action methods (vs. raw `state = 'X'` writes) align with Odoo conventions, give meaningful button targets in form views, and produce readable controller code.
- Using a transition table (rather than scattered `if state == 'X'`) makes the FSM self-documenting and adding a new state is a one-line change.

**Alternatives considered**:

- Using `state_machine` Python library: adds an external dependency for ~50 lines of logic; rejected.
- `mail.thread.message_post` only without explicit action methods: works but loses the ergonomics of named buttons in views.

---

## R4. Counter-Proposal Modeling

**Decision**: Counter-proposals are represented as new `real.estate.proposal` records with `parent_proposal_id` set. The parent transitions to `negotiation`. The counter occupies the property's active slot (replacing the parent) — guard logic in `_check_one_active_per_property` recognises (parent in negotiation + child in any non-terminal state) as the same logical slot via a computed `slot_holder_id` field.

**Rationale**:

- Stores full negotiation history immutably (each counter is a separate row with its own `proposal_value`, `valid_until`, etc.).
- The `proposal_chain_ids` computed field traverses the `parent_proposal_id` graph recursively to expose the full chain.
- Treating parent + child as the same logical slot avoids the otherwise-required exception in the partial unique index. Implementation: the partial unique index is on `(property_id) WHERE state IN ('draft','sent','accepted')` (excluding `negotiation`), which means a parent in `negotiation` does NOT count for the active-slot check, while the child counter (in `draft`/`sent`) is the unique active row.

**Alternatives considered**:

- Versioning fields on a single proposal record (mutating value/valid_until in place with a JSON history field): loses individual records as first-class entities; counter-proposals can't have their own attachments or be queried independently; rejected.
- Allowing both parent (negotiation) and child to count as active and waiving the unique index for negotiation: weakens the invariant; rejected.

---

## R5. Email Dispatch via Outbox Pattern

**Decision**: All emails dispatched through Celery's existing `notification_events` queue (per ADR-021). The proposal model emits an event via `EventBus.emit('proposal.notification', payload)` after each state transition; the existing `celery_notification_worker` consumes the event, renders `mail.template`, sends via `mail.mail`. Failures are retried with exponential backoff (3 attempts) and the final failure writes a `mail.message` of subtype "Notification failed" to the proposal's chatter.

**Rationale**:

- Preserves the contract from Q2 clarification: state transition always succeeds; email is decoupled.
- Uses existing infrastructure (RabbitMQ + Celery + Redis DB 2 backend); no new components.
- `mail.template` keeps copy editable by non-developers (per Constitution security patterns).
- Logging failure to the chatter of the originating proposal makes diagnosis straightforward.

**Alternatives considered**:

- Synchronous `mail.send_mail`: rejected per Q2.
- Database-backed Outbox table: redundant given ADR-021 already provides RabbitMQ-backed durable queues.

---

## R6. Validity Date Bounds (FR-025a)

**Decision**: Enforce `valid_until > today` AND `valid_until <= create_date + 90 days` via an `@api.constrains` Python method with a clear `ValidationError` message. Default value (when omitted on `/send`): `sent_date + 7 days`.

**Rationale**:

- Aligns with Brazilian real estate norms (proposals usually 7-30 days, rarely beyond 90).
- Server-side validation prevents bypass via direct API calls or import flows.
- Schema validation (ADR-018) at the controller layer additionally rejects malformed dates before they reach the model.

**Edge case**: If `valid_until` is set on creation (state `draft` or `queued`), the bound is applied at creation time. If left unset and the proposal is later sent, the default kicks in.

---

## R7. Property Archive Cascade (FR-046a)

**Decision**: Override `real.estate.property.write()` to detect archival (`active` becoming `False`), then iterate non-terminal proposals tied to that property, calling each one's `action_cancel(reason="Property withdrawn from market", auto=True)`. Each cancellation is atomic, fires the same email notification path as manual cancellation, and recalculates queue positions if any queued items remain (which would be unusual but possible if the property was archived while the active was being decided).

**Rationale**:

- Centralizing the cascade in the property model rather than scattering "if property archived" checks across the proposal model is more discoverable and matches Odoo conventions.
- Atomic per-proposal cancellation preserves audit trail (each gets a chatter entry, each agent gets an email).
- Re-using `action_cancel` ensures cancellation reasons are correctly recorded and timeline events are consistent regardless of trigger.

**Alternatives considered**:

- Trigger via Odoo Observer (ADR-020): viable, but adds an indirection layer that obscures the dependency. Reserved for future cross-cutting concerns; direct override is sufficient for this single rule.

---

## R8. RBAC Implementation

**Decision**: Use Odoo `ir.rule` records (record rules) for read/list scoping (per ADR-008) plus controller-level role checks (using `thedevkitchen_apigateway` session helpers) for write actions. The authorization matrix from spec FR-044 is encoded as:

- Owner / Manager: record rule allows all proposals in their `company_id`s; controllers permit all mutation actions.
- Agent: record rule restricts to `[('agent_id.user_id', '=', user.id)]`; controllers additionally check property assignment for create.
- Receptionist: record rule allows read on all org proposals; controllers reject all mutations with HTTP 403.
- Prospector: record rule denies access; controllers reject with 403.

**Rationale**:

- ir.rule provides defense-in-depth at the ORM layer (also covers Odoo Web UI access for managers).
- Controller-level check provides clear HTTP error semantics and avoids leaking 404 vs 403 ambiguity for write attempts.

**Reference Implementation**: `quicksol_estate/security/lead_record_rules.xml` (existing Lead module).

---

## R9. Queue Position Computation

**Decision**: `queue_position` is a stored computed field with `compute='_compute_queue_position'` triggered on `(property_id, state, create_date, active)`. Computation logic:

1. If `state` is terminal (accepted/rejected/expired/cancelled): position = NULL.
2. If `state` in non-terminal active set ('draft','sent','negotiation','accepted'): position = 0.
3. If `state == 'queued'`: position = 1-based rank among queued siblings ordered by `create_date ASC` for the same property.

**Rationale**:

- Stored computed avoids re-computing on every read. Index on `(property_id, state, create_date)` makes the rank query O(N) where N = queue depth (rarely >5 in practice).
- Recomputed via Odoo's `@api.depends` whenever a sibling's state changes, so promotion/cancellation automatically updates positions.

**Alternatives considered**:

- Non-stored computed field: re-computes on every read; under listing of large datasets this is wasteful.
- Application-level cron to recompute: introduces eventual consistency and complicates UI display.

---

## R10. Document Attachments

**Decision**: Use Odoo's built-in `ir.attachment` with `res_model='real.estate.proposal'` and `res_id=<proposal_id>`. A whitelist of mimetypes (`application/pdf`, `image/jpeg`, `image/png`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) and a 10 MB size cap are enforced at the controller. `documents_count` is a stored computed field on the proposal.

**Rationale**:

- `ir.attachment` is the standard Odoo storage layer (filestore on disk by default; can be S3 with addon).
- Bypassing it would lose Odoo's built-in access controls and the `ir.attachment` access matrix.
- Mimetype + size validation at the controller layer provides clear HTTP errors (400 / 413).

---

## R11. OpenAPI 3.0 Contract Strategy

**Decision**: Author a single `contracts/openapi.yaml` covering the 10 REST endpoints with full schema definitions, error responses, and HATEOAS link examples. Per ADR-005, the published version (post-development) lives in `docs/openapi/proposals.yaml` and is exposed via `/api/docs`.

**Rationale**:

- Single source of truth for request/response shapes; consumed by the SSR frontend team for typed clients.
- Doubles as input for `speckit.tasks` task generation (each operation maps to ≥1 task).

**Format**: OpenAPI 3.0.3 YAML.

---

## R12. Internationalization

**Decision**: All user-facing strings are pt_BR. Mail templates use Odoo's `${object.lang}` or hardcoded `lang="pt_BR"` for Brazilian users. Validation error messages are wrapped in Odoo `_()` for future i18n extensibility but only pt_BR translations are provided in this feature.

**Rationale**: Aligns with the project's primary market (Brazilian real estate) and Q5/spec assumptions. Multi-language support is explicitly out of scope.

---

## Outcomes

- **All NEEDS CLARIFICATION resolved**: yes (Q1–Q5 from clarify session; Q6–Q12 internal research items above).
- **No remaining unknowns blocking Phase 1.**
- **Pre-implementation deliverable**: ADR-027 must be authored before Phase 2 (tasks/implementation). Captured in plan Complexity Tracking.
