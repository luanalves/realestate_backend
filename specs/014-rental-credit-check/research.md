# Research: Rental Credit Check (spec 014)

**Date**: 2026-04-29
**Branch**: `014-rental-credit-check`
**Purpose**: Resolve all NEEDS CLARIFICATION items from Technical Context before Phase 1 design.

---

## Decision 1 — Module name and model naming

**Decision**: `thedevkitchen_estate_credit_check` (module dir) — model `thedevkitchen.estate.credit.check`

**Rationale**: ADR-004 mandates `thedevkitchen_<categoria>_<entidade>` for module dirs and `thedevkitchen.<categoria>.<entidade>` for `_name`. The category is `estate` (same as proposal/property/agent). Table auto-generated: `thedevkitchen_estate_credit_check`.

**Alternatives considered**:
- `thedevkitchen_rental_credit_check` — rejected, "rental" is a sub-domain; ADR-004 examples use `estate` as the category umbrella.
- Embedding `CreditCheck` inside `thedevkitchen_estate_proposals` module — rejected; separate module enables independent deployment and avoids bloating the proposals module.

---

## Decision 2 — FSM extension approach (adding `credit_check_pending`)

**Decision**: Extend the existing `thedevkitchen.estate.proposal` model via **inheritance** (`_inherit`) inside the new module. Add `credit_check_pending` as a new `Selection` value and override the transition guard method.

**Rationale**: Odoo 18.0 supports `_inherit` for extending existing models without forking them. Keeps all proposal FSM logic traceable. Follows the pattern used by `thedevkitchen_user_onboarding` which inherits `res.users`.

**Alternatives considered**:
- Forking the proposal model — rejected; creates maintenance burden and violates spec 013 ownership.
- Monkey-patching the selection field — rejected; brittle and not ADR-001 compliant.

---

## Decision 3 — Concurrent `pending` guard (one active check per proposal)

**Decision**: PostgreSQL **partial unique index** as defense-in-depth + application-level check before insert.

```sql
CREATE UNIQUE INDEX credit_check_one_pending_per_proposal
ON thedevkitchen_estate_credit_check (proposal_id)
WHERE result = 'pending' AND active = true;
```

**Rationale**: ADR-027 establishes the two-layer pattern (application check + DB index) for queue invariants. Same approach used in spec 013 for the one-active-proposal-per-property invariant. `EXCLUDE USING gist` would require `btree_gist` extension; a partial unique index on `(proposal_id) WHERE result='pending'` achieves the same guarantee with zero extension dependency.

**Alternatives considered**:
- `@api.constrains` only — rejected; race condition possible between check and write.
- `SELECT FOR UPDATE` on the proposal row — considered; sufficient for high concurrency but over-engineered for the expected 1-per-proposal volume. Partial unique index alone is sufficient.

---

## Decision 4 — FSM transition guard: `credit_check_pending` block on counter-proposal

**Decision**: Override `_can_create_counter_proposal()` guard in the proposal model (or equivalent action method) to check if `state == 'credit_check_pending'` and raise `UserError` if so.

**Rationale**: Spec 013 (FR-018) already has a transition guard for counter-proposals. Adding a `credit_check_pending` check to the existing guard keeps the logic co-located. No new architectural pattern required.

---

## Decision 5 — Cron extension for `credit_check_pending` expiry

**Decision**: Extend the existing `ir.cron` record (from spec 013) to call a new service method `_expire_credit_check_pending_proposals()` in the same daily job, or add `credit_check_pending` to the existing expiry query's `state IN (...)` clause.

**Rationale**: ADR-021 mandates reuse of existing background jobs where possible. A single daily cron for proposal expiry is simpler to monitor (Flower, logs) than two separate crons. The new method: (1) marks `CreditCheck.result = 'cancelled'`, (2) transitions proposal to `expired`, (3) promotes next queued proposal (same mechanism as spec 013 FR-011).

**Alternatives considered**:
- New `ir.cron` record — rejected; duplicates scheduling infrastructure for semantically related work.

---

## Decision 6 — Notification pattern (approved/rejected)

**Decision**: Use ADR-021 Outbox pattern via `EventBus.emit('credit_check.result_registered', {...})`. The `celery_notification_worker` handles email dispatch asynchronously. Falls back to synchronous `mail.template` if Celery is unavailable (dev environment fail-open).

**Rationale**: Spec 013 FR-041a already mandates this pattern. Spec 014 FR-019 explicitly references it. Re-using `mail.template` records (new templates for `credit_check.approved` and `credit_check.rejected` events) keeps email templates centralized and translatable.

---

## Decision 7 — Agent scope for `GET /clients/{id}/credit-history`

**Decision**: Agent authorization check: `partner_id` must appear in at least one `thedevkitchen.estate.proposal` where `agent_id = current_user.agent_id` (any state, including terminal). If no such proposal exists, return HTTP 404 (anti-enumeration, ADR-008).

**Rationale**: Confirmed in clarification session 2026-04-29 (Q4). Anti-enumeration (ADR-008) requires 404 instead of 403 to avoid revealing client existence to unauthorized agents.

---

## Decision 8 — `credit_history_summary` computation

**Decision**: Computed field `credit_history_summary` on `thedevkitchen.estate.proposal` — `store=False` (real-time), computed via `_compute_credit_history_summary()`. Fetches `COUNT` of `approved`/`rejected` checks for the proposal's `partner_id` across all proposals in the same `company_id`.

**Rationale**: `store=False` avoids stale data when new checks are added to other proposals for the same client. The query is cheap (indexed on `partner_id`, `company_id`, `result`). For 1,000 checks/company (SC-004 bound), a single aggregation query is sub-millisecond.

---

## Decision 9 — Odoo UI: `<list>` + no `attrs` (ADR-001)

**Decision**: All views use `<list>` tag (not `<tree>`). Column visibility via `optional="show"/"hide"` attribute (KB-10). No `attrs`, no `column_invisible` with Python expressions. Button visibility controlled by `states` attribute or `invisible="state not in [...]"` domain syntax (Odoo 18.0 compatible).

**Rationale**: ADR-001 explicitly mandates this. Odoo 18.0 deprecated `<tree>` in favour of `<list>`. `attrs` is deprecated in 17.0+.

---

## Summary Table

| # | Unknown | Decision | ADR Refs |
|---|---------|----------|----------|
| 1 | Module & model naming | `thedevkitchen_estate_credit_check` / `thedevkitchen.estate.credit.check` | ADR-004 |
| 2 | FSM extension approach | `_inherit` on proposal model | ADR-001 |
| 3 | Concurrent pending guard | Partial unique index + app check | ADR-027 |
| 4 | Counter-proposal block | Override transition guard | ADR-001 |
| 5 | Cron extension | Extend existing spec 013 cron | ADR-021 |
| 6 | Notification pattern | Outbox / EventBus → celery_notification_worker | ADR-021 |
| 7 | Agent history scope | Any proposal (any state) in same company | ADR-008 |
| 8 | credit_history_summary | Computed `store=False`, aggregate query | ADR-004 |
| 9 | Odoo UI patterns | `<list>`, `optional`, no `attrs` | ADR-001 |
