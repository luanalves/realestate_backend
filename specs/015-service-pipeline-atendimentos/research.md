# Phase 0 — Research: Service Pipeline (Atendimentos)

**Date**: 2026-05-03
**Feature**: 015-service-pipeline-atendimentos

## Method

The technical context for this feature was largely resolved during the spec phase (`spec-idea.md`) and through the 5 clarifications captured in `spec.md` (Session 2026-05-03). This document records the **remaining technical research questions** that arose while drafting `plan.md`, plus the rationale for each design decision so they survive into the implementation.

## R1 — How to declare a partial-uniqueness constraint in Odoo 18.0?

**Question**: Conditional uniqueness "one active service per (client, operation_type, agent), ignoring archived/terminal records" — can `_sql_constraints` express this?

**Decision**: Use a **PostgreSQL `EXCLUDE` constraint** created via an Odoo migration script (pre-migrate hook), not via `_sql_constraints`. Validate uniqueness defensively in Python service layer before INSERT and translate `IntegrityError` into HTTP 409 Conflict.

**Rationale**:
- Odoo's `_sql_constraints` only supports plain UNIQUE / CHECK / NOT NULL — no `WHERE` predicate, no `EXCLUDE USING gist`.
- Native UNIQUE without WHERE would forbid historical duplicates (won/lost), violating spec.
- `EXCLUDE` provides the exact semantics needed and is enforced at the DB level (strongest guarantee).
- Migration script pattern is already used in this codebase for non-trivial DDL.

**Alternatives considered**:
- *Python-only validation in @api.constrains*: Race-condition-prone under concurrent writes; rejected.
- *Trigger function*: More complex, harder to reason about, reinvents PostgreSQL's native EXCLUDE.

**Implementation note**:
```sql
-- migrations/18.0.x.x.x/pre-migrate.py executes:
ALTER TABLE real_estate_service
  ADD CONSTRAINT real_estate_service_unique_active_per_client_type_agent
  EXCLUDE (
    client_partner_id WITH =,
    operation_type WITH =,
    agent_id WITH =
  ) WHERE (active AND stage NOT IN ('won','lost'));
```

## R2 — How to compute `last_activity_date` consistently with the clarified definition?

**Question**: Spec clarification defines interaction as `max(manual write_date, latest user-posted mail.message)`. How to compute this efficiently and avoid recursive triggers when computed fields write back?

**Decision**: Use a **stored compute** field with `@api.depends('write_date','message_ids.create_date','message_ids.author_id')` filtering messages with non-null `author_id` (system messages have `author_id IS NULL`). Mark `compute_sudo=True` so Odoo doesn't trigger recompute on every read. Crucially: do **not** include `last_activity_date` in `_track_visibility` to avoid mail.thread feedback loops.

**Rationale**:
- Stored computed avoids GROUP BY at query time (good for `?ordering=pendency` performance).
- Filtering `author_id` excludes audit trail messages (system-generated), so a stage transition's audit message does NOT count as a separate interaction beyond the write itself — keeping the metric meaningful per the clarification.
- `is_pending` derives from `last_activity_date` and `service.settings.pendency_threshold_days` — also stored, recomputed nightly via cron + on write.

**Alternatives considered**:
- *Pure SQL VIEW*: Lose ORM integration, harder to filter via Odoo domains.
- *Recompute on every read*: Performance disaster for `/summary` and lists.

## R3 — How to enforce stage gates without coupling the constrains to the proposal model directly?

**Question**: FR-005 requires a service in stage `formalization` to have an approved proposal vinculated. How to express this constraint without creating a hard dependency that would break test isolation?

**Decision**: Use `@api.constrains('stage','proposal_ids.state')` and **soft-check via filtered set**:
```python
@api.constrains('stage','proposal_ids')
def _check_formalization_requires_approved_proposal(self):
    for r in self:
        if r.stage == 'formalization' and not r.proposal_ids.filtered(lambda p: p.state == 'accepted'):
            raise ValidationError(_('Etapa Formalização exige proposta aceita vinculada.'))
```

The `proposal_ids` is a **One2many** with `inverse_name='service_id'` requiring a new field on `real.estate.proposal` (additive, nullable). Decision: add the inverse field to `real.estate.proposal` in this same module/branch.

**Rationale**:
- Looser coupling than checking proposal model directly.
- Reuses existing proposal state machine (013) — no duplication.
- Adding a nullable field to proposal is a backward-compatible additive change.
- Tests can construct in-memory proposals without invoking the full proposal lifecycle.

**Alternatives considered**:
- *Many2many*: Less semantic (a proposal belongs to exactly one service).
- *Cross-model service check*: More fragile, harder to test.

## R4 — Should the `/summary` endpoint use Redis cache from day one?

**Question**: Constitution v1.6.0 documents Redis cache as "optional" for the aggregation pattern. Should we ship with cache or without?

**Decision**: **Ship without Redis cache initially.** Implement using a single SQL `GROUP BY` query through Odoo ORM `read_group()`. Add Redis layer **only if** measured latency exceeds the < 100 ms (p95) target at the design scale (10k services per company).

**Rationale**:
- `read_group` on an indexed `(company_id, stage)` covering ~10k rows typically returns in < 30 ms on modern PostgreSQL — well below the 100 ms budget with headroom.
- Redis cache adds invalidation complexity (must invalidate on every write) and a new failure mode (stale counts).
- YAGNI: defer the cache until measured.
- Constitution explicitly tagged the cache as optional in the pattern.

**Alternatives considered**:
- *Materialized view*: Refresh complexity outweighs the benefit at this scale.
- *Pre-aggregated counter table*: Premature optimization.

**Indexes required** (data-model.md): `idx_service_company_stage`, `idx_service_company_agent`, `idx_service_company_lastactivity`.

## R5 — Cypress test scope for the admin UI

**Question**: Constitution requires E2E tests; Cypress folder targets admin Odoo UI. What's the minimum viable Cypress coverage?

**Decision**: One E2E spec file `015_services_admin.cy.js` covering:
1. Login as admin, open Services list — assert no console errors.
2. Open form view of a seeded service — assert all fields render.
3. Create a tag in the tag list — assert appears in service form.
4. Open settings form — assert validators trigger on invalid range.

**Rationale**: Matches scope of similar features (007/009/013). Heavier UI coverage is unnecessary because the primary surface is the headless API (covered exhaustively by integration tests).

## R6 — Migration ordering & data backfill

**Question**: Existing companies will get the new module on upgrade. How are default sources/tags/settings created per company?

**Decision**: Use Odoo `noupdate=False` data XML with **`company_id="ref(...)"` only on per-company defaults**. For multi-company defaults, use a **post-init hook** that iterates `env['res.company'].search([])` and creates a settings singleton + system tag (`closed`) + 5 default sources per company. This idempotency ensures upgrades on existing tenants pick up defaults without operator action.

**Rationale**:
- Static XML can't iterate companies.
- Post-init hooks are the standard Odoo pattern for per-company seed.
- Idempotent via `xml_id` lookup (skip if already created).

**Alternative considered**:
- *Manual operator action per company*: Fragile, error-prone in multi-tenant SaaS.

## R7 — `lead_id` linkage given clarification "independent lifecycles"

**Question**: Clarification 5 said Lead and Service have independent lifecycles. What's the technical implication on the `lead_id` field?

**Decision**: `lead_id` is `Many2one('real.estate.lead')` **optional**, **`ondelete='set null'`**, **no inverse field on lead** (avoid pulling service lifecycle into lead's compute graph). No automatic state propagation in either direction. UI displays the link for traceability only.

**Rationale**: Honors the clarification literally — service may reference a lead origin for audit, but neither entity reacts to the other's transitions.

---

## Summary of Decisions

| ID | Topic | Decision |
|----|-------|----------|
| R1 | Conditional uniqueness | PostgreSQL EXCLUDE via migration script |
| R2 | `last_activity_date` compute | Stored compute, filter user-authored messages, no track_visibility |
| R3 | Formalization stage gate | `@api.constrains` with `proposal_ids.filtered(state=accepted)` + add inverse field on proposal |
| R4 | `/summary` cache | No cache initially; defer to measured need |
| R5 | Cypress scope | Single spec, smoke admin UI coverage |
| R6 | Per-company defaults | Post-init hook iterating companies (idempotent) |
| R7 | `lead_id` linkage | Optional M2O, set null on delete, no automatic propagation |

All decisions carry no further `NEEDS CLARIFICATION`. Ready for Phase 1.
