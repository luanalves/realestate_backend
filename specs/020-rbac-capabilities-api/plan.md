# Implementation Plan: RBAC Capabilities API

**Branch**: `020-rbac-capabilities-api` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-rbac-capabilities-api/spec.md`

## Summary

Introduce `GET /api/v1/me/capabilities`, a new authenticated endpoint that returns a minimal
two-key payload — `user` and `rules` — so the headless frontend can bootstrap CASL-safe,
role-aware navigation in a single request without hardcoding role logic or exposing Odoo
internals. The implementation is strictly additive: a new `CapabilityService` inside
`quicksol_estate/services/` holds the declarative `ROLE_RULES` matrix and projection logic; a
new `CapabilitiesController` in `quicksol_estate/controllers/` exposes the route with the
required triple-decorator stack (`@require_jwt + @require_session + @require_company`). No new
database tables or migrations are introduced. Rule ordering is deterministic by backend
declarative contract (business/navigation subject order, semantic action progression), not
alphabetical. The existing `GET /api/v1/me` contract remains unchanged.

## Technical Context

**Language/Version**: Python 3.11, Odoo 18.0  
**Primary Dependencies**:
- `quicksol_estate` — RBAC group definitions (`quicksol_estate.group_real_estate_*`), service + controller host
- `thedevkitchen_apigateway` — middleware decorators (`require_jwt`, `require_session`, `require_company`)
- `thedevkitchen_observability` — `@trace_http_request` (already applied to all authenticated endpoints)

**Storage**: No new PostgreSQL tables; `ROLE_RULES` lives in code; resolved context comes from `res.users` + `res.company` already in memory from authenticated request  
**Testing**: Odoo `TestCase` for pure unit tests; `TransactionCase` / `HttpCase` for integration; bash shell scripts for E2E API journeys (existing project convention)  
**Target Platform**: Linux server (Docker Compose, Odoo 18.0)  
**Project Type**: Single Odoo add-on addendum (API-only within existing module)  
**Performance Goals**: ≥95% of capability requests complete within 1 second total (SC-005); endpoint is read-only and stateless — no DB writes, no cache required for MVP  
**Constraints**:
- No new DB migrations
- No changes to `/api/v1/me` response shape
- No static Swagger file edits — OpenAPI registration via DB-backed `thedevkitchen_api_endpoint` records (ADR-005)
- No Odoo views, menus, or actions
- `ROLE_RULES` is code-declared, not DB-configured

**Scale/Scope**: 10 RBAC roles × N companies; stateless per-request projection; read-only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|---------|
| I. Security First | ✅ PASS | Triple decorators `@require_jwt + @require_session + @require_company` on the endpoint; session fingerprint validation inherited from `require_session`; generic error responses — no RBAC internals leak |
| II. Test Coverage | ✅ PASS | Unit tests: `test_capability_service.py` (deduplication, ordering, omission, whitelist enforcement); E2E API: full 10-role matrix, multi-company isolation, non-leakage assertions; bash regression guard for `/api/v1/me` |
| III. API-First | ✅ PASS | REST `GET` endpoint; OpenAPI 3.0 contract in `contracts/capabilities.yaml` (reference); Swagger registered via DB per ADR-005; Postman collection planned post-implementation per ADR-016 |
| IV. Multi-Tenancy | ✅ PASS | `@require_company` enforces company isolation before controller runs; `user.company_id` is the active authenticated context; no cross-company identifiers in payload; 403 for unauthorized company context |
| V. ADR Governance | ✅ PASS | ADR-003 (tests mandatory), ADR-004 (module/model naming), ADR-005 (Swagger DB-driven), ADR-008 (security/multi-tenancy), ADR-011 (triple decorator), ADR-017 (session fingerprint), ADR-018 (input validation — no body accepted), ADR-019 (RBAC taxonomy) |
| VI. Headless Architecture | ✅ PASS | API-only endpoint purpose-built for SSR/headless frontend CASL adapter; no Odoo UI changes; endpoint inaccessible from Odoo web UI |

**Gate result: ALL PASS — no violations. Phase 0 may proceed.**

**Post-design re-check (Phase 1)**: Confirmed. No new deviations. Virtual response only, no new DB models, no static Swagger edits, no `/api/v1/me` mutations.

## Project Structure

### Documentation (this feature)

```text
specs/020-rbac-capabilities-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── capabilities.yaml            # Phase 1 output: OpenAPI 3.0 contract reference
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── controllers/
│   ├── __init__.py                   # Add capabilities_controller import
│   └── capabilities_controller.py   # NEW — GET /api/v1/me/capabilities
├── services/
│   └── capability_service.py        # NEW — ROLE_RULES + projection logic
└── tests/
    ├── api/
    │   └── test_capabilities_api.py # NEW — E2E integration tests (curl/shell)
    └── unit/
        └── test_capability_service_unit.py  # NEW — Unit tests (unittest + mock)

18.0/extra-addons/thedevkitchen_apigateway/
└── controllers/
    └── me_controller.py             # Refactor: consume shared role_resolver
                                     # to eliminate duplicate role_map and prevent drift
```

**Structure Decision**: Controller and service both live in `quicksol_estate` because:
1. The `ROLE_RULES` matrix directly references `quicksol_estate.group_real_estate_*` XML IDs for role detection; the service must run inside a module that can call `user.has_group('quicksol_estate.group_real_estate_owner')`.
2. All existing business controllers (`owner_api.py`, `agent_api.py`, etc.) follow the same pattern: import middleware from `thedevkitchen_apigateway`, keep domain logic in `quicksol_estate`.
3. `thedevkitchen_apigateway` has no declared dependency on `quicksol_estate`; placing the new controller there would create an architectural inversion.
4. The new route `/api/v1/me/capabilities` is a domain endpoint (capabilities are determined by estate RBAC groups) even though it shares a URI prefix with `/api/v1/me`.

**`role_resolver.py` Architecture Decision (I1 resolution)**: `role_resolver.py` lives in `thedevkitchen_apigateway/services/` and **embeds the canonical `quicksol_estate.group_real_estate_*` XML IDs** as its internal `ESTATE_ROLE_MAP` ordered constant. This formalises an existing implicit runtime dependency: `me_controller.py` already references these XML IDs inline. To make the dependency Odoo-compliant, `quicksol_estate` is added to `thedevkitchen_apigateway/__manifest__.py` `depends`. Only the generic role-resolution utility (no HTTP surface, no business logic) crosses into the gateway module; all domain controllers and services remain in `quicksol_estate`, preserving the gateway-as-middleware boundary.

## Interface Contracts

### `role_resolver.resolve_role(user)`

Canonical signature for the shared utility created in T003 and consumed by T004 (me_controller refactor) and T024 (cross-module migration):

```python
def resolve_role(user) -> str | None:
    """Return the first matching estate role label for the user, or None.

    Iterates ESTATE_ROLE_MAP (an ordered dict of xml_id -> role_label) and
    returns the label of the first group the user belongs to via has_group().
    Returns None if the user matches no estate group (e.g. portal user, system
    admin with no real-estate profile). Callers MUST handle None explicitly:
    map to role=null and rules=[] in API responses (FR-007); use
    `resolve_role(user) or 'unknown'` only in non-API fallback contexts.

    Parameters
    ----------
    user : odoo.models.Model  (res.users record)
        The authenticated Odoo user (request.env.user).

    Returns
    -------
    str | None
        One of: "owner", "director", "manager", "agent", "prospector",
        "receptionist", "financial", "legal", "property_owner", "tenant",
        or None.
    """
```

All callers import as:
```python
from odoo.addons.thedevkitchen_apigateway.services.role_resolver import resolve_role
```

---

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
