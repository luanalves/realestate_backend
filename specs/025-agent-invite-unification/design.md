# Design: Unify Agent Creation into the Invite Flow

**Feature Branch**: `025-agent-invite-unification`
**Created**: 2026-07-16
**Status**: Approved (brainstorming) — ready for `writing-plans`
**Source spec**: [spec-idea.md](spec-idea.md) (all 3 open decisions resolved there before this design session)

This document captures the architecture-level decisions made during brainstorming, refining `spec-idea.md`'s requirements into a concrete implementation shape. It does not repeat the full requirements/user-stories/test-coverage tables already in `spec-idea.md` — see that file for those.

---

## Scope of the implementation plan

The implementation plan (`plan-idea.md`) covers **all 5 phases**, including removal (Phase 5), not just the unify+deprecate phases. This means the plan should include the removal steps (delete `create_agent` route/controller, delete the `thedevkitchen.api.endpoint` registry row, delete superseded tests, regenerate OpenAPI/Postman to confirm absence) as concrete, ready-to-execute tasks — even though *actually running* Phase 5 is gated on real-world preconditions that can't be satisfied in one implementation session (a deprecation window elapsing, a production traffic check via the API access log). The plan should make this gating explicit: Phase 5's tasks are written and ready, but their execution is a separate, later trigger (manual, post-monitoring), not something `writing-plans`/`executing-plans` runs to completion in the same pass as Phases 1-4.

## Architecture

**Extended component (correction — not a new file)**: `quicksol_estate/services/agent_service.py` already exists, exposing a class `AgentService` (already imported at `services/__init__.py:6`) with a `create_agent(values, company_id=None)` method — but that method is currently **unused dead code**: `agent_api.py::create_agent` does not call it, and instead builds the profile+agent records inline. This design adds a new method, `AgentService.create_agent_from_profile(profile_record, agent_payload=None)`, to that existing class, rather than creating a new module. This still follows the cross-module service-import precedent already established by `thedevkitchen_user_onboarding`'s existing import of `quicksol_estate/services/role_resolver.py` (`quicksol_estate` is already a declared manifest dependency) — it just lands in an existing file instead of a new one.

The service is responsible for:
- Validating CRECI (format, normalization via `CreciValidator`, uniqueness within `company_id` — the model's own `@api.constrains` still enforces uniqueness at the DB layer; the service doesn't re-implement that, it just triggers `real.estate.agent.create()` and lets the constraint raise)
- Validating bank/pix fields per the same rules `AGENT_CREATE_SCHEMA` uses today
- Creating the `real.estate.agent` record from the profile's existing cadastral data plus any optional `agent` payload fields, reusing the `setdefault()` sync logic already present in `real.estate.agent.create()`

**`create_agent` is explicitly NOT refactored to call this new service.** It keeps its current, unmodified implementation for the entire deprecation window — only response headers (`Deprecation`, `Sunset`) are added. This was a deliberate choice over unifying both controllers onto the shared service immediately: `create_agent` is scheduled for deletion in Phase 5, so touching its internals now would add regression risk to code that's going away, for no lasting benefit. The temporary duplication this leaves (both `create_agent`'s inline logic and the new `agent_service.py` implement similar CRECI/bank validation) is accepted as a short-lived cost, bounded by the deprecation window.

**Schema layer**: a new `AGENT_INVITE_EXTRA_SCHEMA` is added to the existing `SchemaValidator` (`quicksol_estate/controllers/utils/schema.py`), validating the shape of the optional `agent` object on `POST /api/v1/users/invite` (required: none; optional: `creci`, `hire_date`, `bank_name`, `bank_account`, `pix_key`) before the service layer is invoked. This mirrors how `AGENT_CREATE_SCHEMA` is used today — schema-level type/shape validation, followed by model-level constraint validation for uniqueness.

**Modified controller**: `thedevkitchen_user_onboarding/controllers/invite_controller.py::invite_user` gains a conditional branch: when the target profile's `profile_type_id.code == 'agent'`, it validates the optional `agent` object via `AGENT_INVITE_EXTRA_SCHEMA`, then calls `agent_service.create_agent_from_profile()` in the same transaction as the `res.users` creation and invite-token generation.

## Data Flow (happy path, agent profile with optional `agent` object)

1. `invite_user` receives `profile_id` + optional `agent` object
2. Authorization check (ADR-024 matrix) and cross-company lookup — 404 if the profile isn't visible to the requester's active company
3. If `agent` payload is present, validate it via `AGENT_INVITE_EXTRA_SCHEMA` — 400 on failure, **before any record is created**
4. Create `res.users` (`signup_pending=True`, linked via `partner_id`)
5. Call `agent_service.create_agent_from_profile(env, profile, agent_payload)` → creates `real.estate.agent`; a CRECI uniqueness violation raises and is mapped to 409, rolling back the entire transaction (no orphaned `res.users`)
6. Generate the invite token (existing SHA-256-hashed token pattern, Feature 009)
7. Commit the transaction
8. Send the invite email (best-effort/non-blocking, per existing `force_send=False` pattern — email failure does not roll back the transaction)
9. Return 201 with `agent_id` in the response body and an `"agent"` link, alongside the existing `id`/`profile_id`

For non-`agent` profile types, or when the profile is `agent`-typed but the request omits the `agent` object, only step 5 differs: `create_agent_from_profile` is skipped entirely (non-agent types) or called with an empty `agent_payload` (agent type, no extra fields — still creates a bare `real.estate.agent` row from profile data only, per spec-idea.md's User Story 1 bug-fix requirement).

## Error Handling

| Code | Condition |
|------|-----------|
| 400 | `agent` object fails `AGENT_INVITE_EXTRA_SCHEMA` validation (shape/format) |
| 403 | Requester not authorized to invite this profile type (ADR-024, unchanged) |
| 404 | Profile not found, or belongs to a different company (anti-enumeration, ADR-008) |
| 409 | Profile already has a linked `res.users`, OR `agent.creci` already registered to another active agent in the same company |
| 500 | Unexpected error (uncategorized failures, including unexpected `agent_service` exceptions) |

All error paths roll back the entire transaction atomically (standard Odoo behavior on unhandled exception) — there is no code path that leaves a `res.users` without its corresponding `real.estate.agent` for an agent-typed invite.

## Testing Strategy

- **Unit tests** (`TransactionCase`): `agent_service.create_agent_from_profile()` tested in isolation (CRECI validation, bank fields optional, required-field sourcing from profile, uniqueness-conflict rollback) plus the `invite_user` conditional branch (agent vs. non-agent profile types, empty vs. populated `agent` payload).
- **E2E / integration tests** (`integration_tests/*.sh`, curl-based, per this project's existing convention of avoiding Odoo `HttpCase` due to its read-only-transaction limitation): full happy path (profile → invite w/ agent object → user + agent + token all exist), CRECI conflict (409, atomic rollback verified via `search()` returning empty), cross-company isolation (404), authorization boundary (agent-group requester forbidden), and a regression check that `create_agent`'s existing behavior and its own test suite are unaffected during the deprecation window.
- **Coverage target**: 100% of the new validations (`AGENT_INVITE_EXTRA_SCHEMA`, the profile-type branch, atomicity rollback), per ADR-003.
- Full test-case tables already enumerated in `spec-idea.md`'s User Stories 1, 2, and 4 — this design doc doesn't duplicate them.

## What's unchanged from `spec-idea.md`

Everything not called out above — the RBAC matrix (FR4), the deprecation header/OpenAPI/Postman mechanics (FR5), the removal preconditions and steps (FR6/User Story 4), the nested `agent` object request shape (Decision #3), the performance analysis (NFR2), and the data model (no schema changes) — carries forward unchanged from the spec. This design doc only resolves the *how* of implementation, not the *what* of requirements.
