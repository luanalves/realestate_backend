# ADR-028: Service Pipeline Domain Boundaries

**Status**: Accepted  
**Date**: 2026-01-30  
**Author**: Platform Engineering  
**Feature**: 015 — Service Pipeline (Atendimentos)

---

## Context

The `quicksol_estate` addon already contains `real.estate.lead` (Feature 006), which also represents a sales/rental opportunity. Adding `real.estate.service` (Feature 015) raised the question: *why not reuse or extend `real.estate.lead` instead of creating a new model?*

---

## Decision

`real.estate.service` is an independent model, distinct from `real.estate.lead`, with only an optional soft-link (`service_id` FK on `real.estate.lead`) when they converge.

---

## Rationale

### 1. Different lifecycle semantics (Clarification 5)

| Concern | `real.estate.lead` | `real.estate.service` |
|---|---|---|
| Scope | Marketing/prospecting funnel | End-to-end client attendance (atendimento) |
| Stages | `new → qualified → converted → lost` | `no_service → prospecting → visit → proposal → negotiation → won/lost` |
| Terminal states | `converted`, `lost` | `won`, `lost` |
| Primary actor | Prospector / Manager | Receptionist, Agent, Manager, Owner |
| Client identity | Optional (anonymous leads) | Required (partner dedup FR-022) |
| Property link | Optional | Optional (same) |

Merging both into one model would require complex conditional logic, complicating permissions, constraints, and UI views.

### 2. Different business rules

- `real.estate.service` enforces a **uniqueness constraint** (EXCLUDE): a client cannot have two active services of the same operation type with the same agent (FR-003a).
- `real.estate.lead` has no such constraint — duplicate prospecting leads are permitted.

### 3. Different RBAC access

- Receptionists and prospectors have different access rights to each model.
- The access matrix was designed independently per ADR-011.

### 4. Different pendency / orphan logic

- `is_pending` and `is_orphan_agent` are service-specific computed fields with a cron job (`_cron_recompute_pendency`), driven by `thedevkitchen.service.settings` per company.
- Leads do not have a pendency concept.

### 5. Lifecycle independence

A service can exist with no corresponding lead (e.g., walk-in client). A lead can be converted to a service, but the two are otherwise independent. This is modelled by the nullable `service_id` on `real.estate.lead` — a lead may reference the resulting service, but the service itself has no mandatory lead reference.

---

## Consequences

- **Positive**: Clean domain separation; each model can evolve independently; RBAC and UI are simpler.
- **Positive**: The EXCLUDE constraint and pendency cron are self-contained in the service model.
- **Neutral**: Some duplication (both have `client_partner_id`, `operation_type`) — accepted as unavoidable given different constraints.
- **Negative**: Requires careful onboarding documentation to explain when to use leads vs services.

---

## Alternatives Considered

### Option A: Extend `real.estate.lead` with extra stages
Rejected because the stage FSM semantics are incompatible (leads represent pre-qualification; services represent the full post-qualification journey).

### Option B: Reuse `real.estate.lead` with a `type` flag
Rejected because it would add conditional logic throughout the codebase (constraints, views, RBAC) and make the code harder to maintain.

### Option C: Separate addon
Considered but rejected to keep the company's domain logic within a single `quicksol_estate` addon, reducing deployment complexity.

---

## References

- [Feature 015 spec](../../specs/015-service-pipeline-atendimentos/spec.md)
- [ADR-011 Security Decorator Patterns](ADR-011-security-decorator-patterns.md)
- [ADR-004 Module Naming](ADR-004-module-naming-conventions.md)
