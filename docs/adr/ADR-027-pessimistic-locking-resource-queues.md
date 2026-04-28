# ADR-027: Pessimistic Locking for Resource Queues

**Date**: 2026-04-27
**Status**: Accepted
**Feature**: 013-property-proposals
**Authors**: TheDevKitchen
**Supersedes**: —
**Related**: ADR-015 (Soft Delete), ADR-021 (Async Processing)

---

## Context

The platform's property proposal feature requires a strict invariant: **at most one "active" proposal** (state in `draft`, `sent`, `accepted`) may exist per property at any given time. Additional proposals are queued (FIFO by creation timestamp) and promoted automatically when the active slot is released.

Under concurrent workloads (multiple agents submitting proposals for the same currently-empty property simultaneously) a simple application-level check — read → check → write — is insufficient because two requests can interleave at the read step and both observe an empty slot, leading to two active proposals for the same property (invariant violation).

We considered three options:

1. **Optimistic concurrency with retry** — each writer reads the current state, writes, and retries on `IntegrityError`. Deterministic only with a retry loop whose depth must be bounded; produces non-deterministic latency under contention; UX complexity for backoff handling.
2. **Application-level advisory locks** — `pg_try_advisory_lock()` on the property ID. Works, but is not rolled back automatically on transaction abort, requiring explicit `pg_advisory_unlock()` calls; harder to reason about in ORM code.
3. **Pessimistic row locking (`SELECT FOR UPDATE`)** combined with a **partial unique index as defense-in-depth** — lock the property row before deciding the new proposal's initial state; the partial unique index at the DB level catches any code-path bypass.

Option 3 was chosen.

---

## Decision

For any resource that has a **single-active-slot queue invariant**, the following two-layer pattern MUST be used:

### Layer 1 — Pessimistic row lock (application)

Before deciding the initial state of a new queue entry, acquire an exclusive row lock on the parent resource row:

```python
# models/proposal.py  create()
self.env.cr.execute(
    "SELECT id FROM real_estate_property WHERE id = %s FOR UPDATE NOWAIT",
    (property_id,)
)
```

`NOWAIT` surfaces a `psycopg2.errors.LockNotAvailable` immediately if the row is already locked; callers retry or queue according to their own logic. The lock is held for the duration of the current transaction and released on commit/rollback.

Within the same transaction, inspect the current slot state and write the correct initial state (`draft` or `queued`) atomically.

### Layer 2 — Partial unique index (database)

Create a partial unique index that encodes the single-active invariant at the storage layer:

```sql
CREATE UNIQUE INDEX real_estate_proposal_one_active_per_property
ON real_estate_proposal (property_id)
WHERE state IN ('draft', 'sent', 'accepted')
  AND active = true
  AND parent_proposal_id IS NULL;
```

**Why `negotiation` is excluded**: When a counter-proposal is created, the parent moves to `negotiation` and the child (counter) becomes the active `draft`. The parent no longer competes for the active slot. Including `negotiation` would prevent the child from being inserted.

**Why `parent_proposal_id IS NULL`**: Counter-proposals (children) hold the active slot while their parent is in `negotiation`. The partial index needs to ignore children so they don't collide with each other's partial unique constraint.

**Why `active = true`**: Cancelled proposals are soft-deleted (`active = false`) per ADR-015 and must not occupy the slot check.

### Optional Layer 3 — Python `@api.constrains` mirror

For defense-in-depth at the Odoo application layer, add an `@api.constrains` Python check that mirrors the DB invariant. This fires after every write that changes `state` or `active` and provides a human-readable error message before the DB constraint would trip.

---

## Applicability

This pattern applies to any model that:

- Has a **parent resource** that can hold exactly one "active" child record at a time.
- Requires **automatic promotion** (FIFO or otherwise) when the active record terminates.
- Is exposed to **concurrent writes** in production workloads.

Examples where this pattern applies or may be needed in the future:

| Resource | Active-slot child | Queue type |
|---|---|---|
| `real.estate.property` | `real.estate.proposal` | FIFO (creation timestamp) |
| Inspection calendar slot | `real.estate.inspection` (future) | FIFO or priority |
| Agent assignment | `real.estate.agent.assignment` | Single-active |

---

## Consequences

**Positive**:
- The invariant is enforced at two independent layers (application + DB), making it robust against code-path bypasses and future regressions.
- No retry logic needed in the application; each concurrent writer either succeeds or queues atomically.
- `SELECT FOR UPDATE NOWAIT` has negligible overhead under normal workloads (property-level lock = fine-grained).

**Negative / trade-offs**:
- `FOR UPDATE NOWAIT` will raise an exception if the property row is already locked by a concurrent transaction. The controller must catch `psycopg2.errors.LockNotAvailable` (or `OperationalError`) and handle it by briefly retrying or returning an appropriate 409/503 response. In practice, contention on a single property is rare.
- The partial unique index must be created via a DB migration (`post-migrate.py`) rather than an ORM `_sql_constraints` entry because Odoo's constraint system does not support `WHERE` clauses.
- Developers adding new state values or changing the active-slot semantics MUST update the partial unique index definition. This ADR serves as the single authoritative reference.

---

## Implementation Reference

- **Model**: `18.0/extra-addons/quicksol_estate/models/proposal.py` — `create()` override
- **Migration**: `18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/post-migrate.py`
- **Tests**: `test_proposal_queue.py` + `integration_tests/test_us_proposal_concurrent_creation.sh`
- **Spec FR**: FR-008, FR-009, FR-016 (SC-003)
