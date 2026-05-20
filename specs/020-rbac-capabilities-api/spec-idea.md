# Feature Specification: RBAC Capabilities API

**Feature Branch**: `020-rbac-capabilities-api`  
**Created**: 2026-05-18  
**Status**: Draft  
**ADR References**: ADR-003, ADR-004, ADR-005, ADR-008, ADR-009, ADR-011, ADR-017, ADR-018, ADR-019, ADR-022  
**Related Specs**: Feature 005 (RBAC User Profiles), Feature 009 (User Onboarding & Password Management), Feature 010 (Profile Unification)  

---

## Executive Summary

This feature adds a new authenticated bootstrap endpoint, `GET /api/v1/me/capabilities`, so the headless frontend can render menus, routes, and action buttons using CASL-safe product rules instead of hardcoding role logic. The endpoint is intentionally UX-oriented only: it exposes a conservative whitelist of `action` + `subject` rules for the active session context, while real authorization remains enforced by existing backend decorators, record rules, and domain-specific validations.

The scope is strictly **API only**. The existing `GET /api/v1/me` contract remains unchanged; this feature only introduces a parallel capabilities endpoint that returns a minimal MVP contract with exactly two top-level keys: `user` and `rules`.

---

## Confirmed Scope & Decisions

1. **Solution type**: API only
2. **Artifact strategy**: Create a new spec; do not mutate unrelated feature scopes
3. **MVP roles**: `owner`, `director`, `manager`, `agent`, `prospector`, `receptionist`, `financial`, `legal`, `property_owner`, `tenant`
4. **Endpoint scope**: Add only `GET /api/v1/me/capabilities`; keep `GET /api/v1/me` unchanged
5. **Seed/test scope**: Include all security, matrix, isolation, and non-leakage cases described in the RBAC plan
6. **ROLE_RULES scope**: Propose a full conservative MVP matrix for all 10 roles
7. **MVP response contract**: Return only `user` + `rules`; do not reserve optional future fields
8. **Role resolution policy**: If a user has multiple groups/profiles, the effective role must follow the logged session context exactly as `/api/v1/me` does today
9. **Seed baseline**: Minimum dataset must include 2 companies, 10 users in company A (one per role), contrasting users in company B for isolation, minimal domain records, and non-leakage assertions

---

## Related Dependencies & Non-Goals

### Dependencies

- **Feature 005** defines the RBAC taxonomy and Odoo groups that back the 10 roles.
- **Feature 009** already establishes authenticated headless session flows and role-aware onboarding patterns.
- **Feature 010** is the canonical reference for profile normalization and cross-feature role semantics.
- **`thedevkitchen_apigateway/controllers/me_controller.py`** already resolves a user role for `/api/v1/me`; this feature must reuse that same effective-role logic instead of inventing a parallel resolver.

### Explicit Non-Goals

- Do **not** modify `/api/v1/me` response shape.
- Do **not** expose Odoo group XML IDs, record rules, domains, model names, or authorization reasons.
- Do **not** replace backend authorization with frontend CASL checks.
- Do **not** add Odoo views, menus, actions, or Cypress coverage; this is API-only.
- Do **not** edit static Swagger files; OpenAPI registration remains DB-driven per ADR-005.

---

## User Scenarios & Testing

### User Story 1: Authenticated User Bootstraps Safe UI Rules (Priority: P1) 🎯 MVP

**As a** logged-in headless user in one of the 10 RBAC roles  
**I want to** fetch my capabilities for the active session/company  
**So that** the frontend can build menus, routes, and action buttons without hardcoding role names

**Acceptance Criteria**:
- [ ] Given valid `@require_jwt` + `@require_session` + `@require_company`, when `GET /api/v1/me/capabilities`, then response is `200 OK`
- [ ] Given a valid session, when the endpoint responds, then the top-level JSON contains exactly `user` and `rules`
- [ ] Given a valid session, when the endpoint responds, then `user` contains only `id`, `role`, and `company_id`
- [ ] Given a user with multiple groups, when the endpoint responds, then `user.role` matches the same effective role returned by `/api/v1/me`
- [ ] Given denied actions, when the endpoint responds, then those actions are omitted instead of returned as `false`
- [ ] Given a supported role, when the endpoint responds, then every rule uses only CASL-safe product subjects and actions

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_role_resolver_matches_me_endpoint_order()` | Shared resolver preserves `/api/v1/me` precedence | ⚠️ Required |
| Unit | `test_capability_service_deduplicates_rules()` | No duplicate `action`+`subject` pairs | ⚠️ Required |
| Unit | `test_capability_service_omits_denied_rules()` | Missing permission = omitted rule | ⚠️ Required |
| Unit | `test_capability_service_stable_sort_order()` | Deterministic rule ordering for contract tests | ⚠️ Required |
| E2E (API) | `test_get_capabilities_returns_user_and_rules_only()` | Minimal contract shape | ⚠️ Required |
| E2E (API) | `test_get_capabilities_requires_jwt()` | Missing/invalid JWT → 401 | ⚠️ Required |
| E2E (API) | `test_get_capabilities_requires_session()` | Missing/invalid session → 401 | ⚠️ Required |
| E2E (API) | `test_get_capabilities_requires_company()` | Missing/invalid company → 403 | ⚠️ Required |

---

### User Story 2: Frontend Uses Rule Omission as Deny-by-Default (Priority: P1)

**As a** frontend application consuming CASL  
**I want to** receive a conservative whitelist of allowed actions  
**So that** any missing rule is interpreted as denied without exposing backend internals

**Acceptance Criteria**:
- [ ] Given an `owner`, when the endpoint responds, then `view MenuAdmin` is present
- [ ] Given an `agent`, when the endpoint responds, then `view MenuAdmin` is absent
- [ ] Given a `manager`, when the endpoint responds, then `reassign Lead` and `reassign Service` are present
- [ ] Given `property_owner` or `tenant`, when the endpoint responds, then only limited external-safe product rules are returned
- [ ] Given a session with no mapped real-estate role, when the endpoint responds, then `role` may be `null` and `rules` must be an empty array
- [ ] Given the response body, when inspected, then no XML IDs, Odoo group names, domains, model names, or record-rule fragments are present

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_only_whitelisted_subjects_are_serialized()` | Subject leak prevention | ⚠️ Required |
| Unit | `test_only_whitelisted_actions_are_serialized()` | Action enum enforcement | ⚠️ Required |
| E2E (API) | `test_owner_receives_menu_admin_rule()` | Positive matrix assertion | ⚠️ Required |
| E2E (API) | `test_agent_does_not_receive_menu_admin_rule()` | Negative matrix assertion | ⚠️ Required |
| E2E (API) | `test_manager_receives_reassign_rules()` | Manager-specific rule set | ⚠️ Required |
| E2E (API) | `test_external_roles_receive_limited_rules()` | `property_owner` and `tenant` scope | ⚠️ Required |
| E2E (API) | `test_no_internal_security_details_leak()` | Payload never contains XML IDs/domains | ⚠️ Required |
| E2E (API) | `test_all_ten_roles_matrix_smoke()` | One request per role validates contract and key grants | ⚠️ Required |

---

### User Story 3: Multi-Company Session Context Is Preserved (Priority: P1)

**As a** user working under multi-company isolation  
**I want to** receive capabilities for the active company/session only  
**So that** the frontend never infers or leaks permissions from another company context

**Acceptance Criteria**:
- [ ] Given company A is active in the session, when `GET /api/v1/me/capabilities`, then `user.company_id` equals company A
- [ ] Given company B is requested without authorization, when calling the endpoint, then `403 Forbidden` is returned by `@require_company`
- [ ] Given mirrored users in company A and company B, when each requests capabilities, then each response is scoped to its own company and contains no cross-company identifiers
- [ ] Given existing `GET /api/v1/me`, when this feature is implemented, then `/api/v1/me` remains unchanged
- [ ] Given internal backend failure, when the endpoint returns an error, then response is generic and does not reveal security internals

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_capabilities_respects_active_company()` | `user.company_id` follows session context | ⚠️ Required |
| E2E (API) | `test_capabilities_cross_company_forbidden()` | Invalid active company → 403 | ⚠️ Required |
| E2E (API) | `test_capabilities_no_cross_company_payload_leakage()` | No company B data in company A response | ⚠️ Required |
| E2E (API) | `test_me_endpoint_contract_unchanged()` | `/api/v1/me` regression guard | ⚠️ Required |
| E2E (API) | `test_capabilities_internal_error_is_generic()` | 500 without stack/group leakage | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Endpoint Contract**
- FR1.1: The system MUST expose `GET /api/v1/me/capabilities`
- FR1.2: The endpoint MUST require `@require_jwt + @require_session + @require_company`
- FR1.3: The endpoint MUST return a JSON object with exactly two top-level keys: `user` and `rules`
- FR1.4: The `user` object MUST contain only `id`, `role`, and `company_id`
- FR1.5: The endpoint MUST NOT modify or deprecate `GET /api/v1/me`

**FR2: Effective Role Resolution**
- FR2.1: Capability resolution MUST reuse the same effective-role policy as `/api/v1/me`
- FR2.2: The implementation SHOULD extract a shared resolver/helper so `/api/v1/me` and `/api/v1/me/capabilities` cannot drift
- FR2.3: Until a session-level active-role marker exists, the shared resolver MUST preserve current role precedence from `me_controller.py`: `owner` → `director` → `manager` → `agent` → `prospector` → `receptionist` → `financial` → `legal` → `property_owner` → `tenant`
- FR2.4: If no supported role is resolved, the endpoint MUST return `200 OK` with `user.role = null` and `rules = []`

**FR3: Safe Capability Projection**
- FR3.1: Rules MUST be emitted as CASL-safe objects with shape `{ "action": "<action>", "subject": "<subject>" }`
- FR3.2: The endpoint MUST omit denied rules; it MUST NOT emit boolean flags or technical deny reasons
- FR3.3: The service MUST emit only rules from a backend whitelist of allowed `action` and `subject` values
- FR3.4: The rule list MUST be deduplicated and returned in deterministic order
- FR3.5: The endpoint MUST NOT include XML IDs, record rules, Odoo domains, model names, raw group names, or stack traces

**FR4: Conservative MVP Whitelist**

**Allowed Actions (v1)**:
- `view`
- `create`
- `update`
- `delete`
- `reassign`
- `approve`
- `cancel`
- `export`

> `manage` is intentionally **not emitted in MVP**. Explicit actions are preferred so the frontend can distinguish buttons and routes precisely.

**Allowed Subjects (v1 whitelist)**:
- Menu subjects: `MenuCRM`, `MenuAdmin`, `MenuCMS`
- Product/domain subjects: `Dashboard`, `Property`, `Lead`, `Service`, `Proposal`, `Agent`, `Company`, `Settings`, `Appointment`, `Report`, `Goal`, `CMSPage`, `CMSMedia`

**MVP Grant Matrix (conservative)**:

| Role | Granted Rules |
|------|---------------|
| `owner` | `view MenuCRM`, `view MenuAdmin`, `view Dashboard`, `view/create/update/delete Property`, `view/create/update/delete/reassign Lead`, `view/create/update/delete/reassign/cancel Service`, `view/create/update/delete/approve/cancel Proposal`, `view/create/update/delete Agent`, `view/update Company`, `view/update Settings`, `view/export Report`, `view Goal` |
| `director` | `view MenuCRM`, `view Dashboard`, `view/create/update Property`, `view/create/update/reassign Lead`, `view/create/update/reassign/cancel Service`, `view/create/update/approve/cancel Proposal`, `view/update Agent`, `view Company`, `view/export Report`, `view Goal` |
| `manager` | `view MenuCRM`, `view Dashboard`, `view/create/update Property`, `view/create/update/reassign Lead`, `view/create/update/reassign/cancel Service`, `view/create/update/approve/cancel Proposal`, `view/update Agent`, `view Company`, `view/export Report`, `view Goal` |
| `agent` | `view MenuCRM`, `view Dashboard`, `view/create/update Property`, `view/create/update Lead`, `view/create/update/cancel Service`, `view/create/update/cancel Proposal`, `view Goal` |
| `prospector` | `view MenuCRM`, `view Dashboard`, `view/create/update Property` |
| `receptionist` | `view MenuCRM`, `view Property`, `view/create Service`, `view Proposal` |
| `financial` | `view MenuCRM`, `view Property`, `view Service`, `view Proposal`, `view Company`, `view/export Report` |
| `legal` | `view MenuCRM`, `view Property`, `view Service`, `view Proposal`, `view Company` |
| `property_owner` | `view Property`, `view Proposal` |
| `tenant` | `view Property`, `view Proposal` |

**Deliberate Omissions in conservative MVP**:
- No role receives `MenuCMS`, `CMSPage`, or `CMSMedia` until the CMS headless surface is productized
- No role receives `Appointment` rules in MVP because the plan does not require a dedicated appointment capability contract for the first delivery
- Only roles with explicit reporting use cases receive `Report`
- External roles (`property_owner`, `tenant`) receive only read-only product rules

**FR5: Company & Session Context**
- FR5.1: `user.company_id` MUST reflect the active company context already validated by `@require_company`
- FR5.2: The endpoint MUST NOT accept company identity from arbitrary body data; it follows the existing authenticated request context model
- FR5.3: The endpoint MUST be safe for users who belong to multiple companies; switching active company requires fetching capabilities again

**FR6: Service Layer**
- FR6.1: Capability mapping MUST be centralized in a dedicated service, e.g. `quicksol_estate/services/capability_service.py`
- FR6.2: The service MUST accept `env`, `user`, and the active company context
- FR6.3: The service MUST return only product-safe rules from a declarative `ROLE_RULES` mapping
- FR6.4: On ambiguity, the service MUST fail closed by omitting the rule

**FR7: Regression & Compatibility**
- FR7.1: `/api/v1/me` remains source-of-truth for current session user metadata and MUST remain backward-compatible
- FR7.2: The capabilities endpoint MUST be additive and non-breaking for current clients
- FR7.3: Frontend consumers MUST be able to build CASL abilities from `rules` alone, without branching on `role`

---

## Data Model (No New Persistent Entity in MVP)

This feature does **not** introduce a new database table or Odoo model in MVP. Capability projection is a **virtual contract** derived from existing authenticated context.

### Virtual Object: Capability Rule

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `action` | String | required, enum | Product action allowed in UI |
| `subject` | String | required, enum | Product subject allowed in UI |

### Existing Sources Reused

| Source | Purpose |
|--------|---------|
| `res.users` | Authenticated user identity |
| `res.company` | Active company isolation context |
| RBAC groups from `quicksol_estate` | Backing role taxonomy |
| Existing `/api/v1/me` role resolver | Effective role parity |

### Persistence Strategy

- `ROLE_RULES` is stored in code, not in the database, for MVP simplicity and auditability
- No migration is required
- No SQL constraints are added
- No `active`/soft-delete behavior is introduced because this feature is read-only

---

## API Endpoint

### Endpoint: `GET /api/v1/me/capabilities`

| Attribute | Value |
|-----------|-------|
| **Method** | `GET` |
| **Path** | `/api/v1/me/capabilities` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Any authenticated session; payload derived from resolved estate role |
| **Public?** | No |
| **Primary Consumer** | Headless frontend CASL adapter |

### Request

No request body.

Required authenticated context:
- `Authorization: Bearer <service token>` injected and validated via `@require_jwt`
- `X-Openerp-Session-Id: <session_id>` validated via `@require_session`
- `X-Company-ID: <company_id>` validated via `@require_company`

### Response Success (200)

```json
{
  "user": {
    "id": 42,
    "role": "agent",
    "company_id": 5
  },
  "rules": [
    { "action": "view", "subject": "MenuCRM" },
    { "action": "view", "subject": "Dashboard" },
    { "action": "view", "subject": "Property" },
    { "action": "create", "subject": "Property" },
    { "action": "update", "subject": "Property" },
    { "action": "view", "subject": "Lead" },
    { "action": "create", "subject": "Lead" },
    { "action": "update", "subject": "Lead" },
    { "action": "view", "subject": "Service" },
    { "action": "create", "subject": "Service" },
    { "action": "update", "subject": "Service" },
    { "action": "cancel", "subject": "Service" },
    { "action": "view", "subject": "Proposal" },
    { "action": "create", "subject": "Proposal" },
    { "action": "update", "subject": "Proposal" },
    { "action": "cancel", "subject": "Proposal" },
    { "action": "view", "subject": "Goal" }
  ]
}
```

### Contract Rules

- Response MUST contain only `user` + `rules`
- `rules` MUST be an array; use `[]`, never `null`
- Rule omission means deny
- Order MUST be deterministic for testing
- Duplicate rule pairs are forbidden

### Error Responses

| Code | Condition | Response |
|------|-----------|----------|
| `401` | Missing/invalid JWT | `{"error":"unauthorized"}` |
| `401` | Missing/invalid session | `{"error":"unauthorized"}` |
| `403` | Missing/invalid/unauthorized company context | `{"error":"forbidden"}` |
| `500` | Internal failure | `{"error":"internal_server_error"}` |

### OpenAPI / Swagger Handling

- Swagger is DB-driven; do **not** edit static YAML/JSON files
- After implementation, register/update the endpoint through the DB-backed Swagger workflow per ADR-005
- Postman collection generation is a post-development task per ADR-016

---

## Seed Data (MANDATORY)

Seeds exist to support complete API journeys, matrix assertions, and non-leakage checks.

### Seed: Companies

```python
company_a = env['res.company'].create({
    'name': 'seed_company_a',
    'is_real_estate': True,
})

company_b = env['res.company'].create({
    'name': 'seed_company_b',
    'is_real_estate': True,
})
```

### Seed: Users per Role

Minimum seed set:
- **Company A**: 10 users, one per role
- **Company B**: contrasting users for isolation; recommended mirror of the same 10 roles for full matrix parity

```python
seed_users = {
    'owner_a': {'login': 'seed_owner_a@test.com', 'role': 'owner', 'company': company_a},
    'director_a': {'login': 'seed_director_a@test.com', 'role': 'director', 'company': company_a},
    'manager_a': {'login': 'seed_manager_a@test.com', 'role': 'manager', 'company': company_a},
    'agent_a': {'login': 'seed_agent_a@test.com', 'role': 'agent', 'company': company_a},
    'prospector_a': {'login': 'seed_prospector_a@test.com', 'role': 'prospector', 'company': company_a},
    'receptionist_a': {'login': 'seed_receptionist_a@test.com', 'role': 'receptionist', 'company': company_a},
    'financial_a': {'login': 'seed_financial_a@test.com', 'role': 'financial', 'company': company_a},
    'legal_a': {'login': 'seed_legal_a@test.com', 'role': 'legal', 'company': company_a},
    'property_owner_a': {'login': 'seed_property_owner_a@test.com', 'role': 'property_owner', 'company': company_a},
    'tenant_a': {'login': 'seed_tenant_a@test.com', 'role': 'tenant', 'company': company_a},

    'owner_b': {'login': 'seed_owner_b@test.com', 'role': 'owner', 'company': company_b},
    'agent_b': {'login': 'seed_agent_b@test.com', 'role': 'agent', 'company': company_b},
    'tenant_b': {'login': 'seed_tenant_b@test.com', 'role': 'tenant', 'company': company_b},
}
```

> Recommended implementation seed mirrors all 10 roles in company B as well, even if only 3 are strictly required for minimum isolation checks.

### Seed: Multi-Role Session Parity User

```python
seed_multi_role = {
    'login': 'seed_multi_role@test.com',
    'company': company_a,
    'groups': ['manager', 'agent'],
}
```

Purpose:
- Validate shared resolver parity with `/api/v1/me`
- Assert that capability projection follows the same effective role order for the active session

### Seed: Minimal Domain Records

Create the smallest safe dataset in **each** company to prove the endpoint does not leak business records:

```python
seed_property_a = env['real.estate.property'].create({... 'company_id': company_a.id})
seed_lead_a = env['real.estate.lead'].create({... 'company_id': company_a.id})
seed_service_a = env['real.estate.service'].create({... 'company_id': company_a.id})
seed_proposal_a = env['real.estate.proposal'].create({... 'company_id': company_a.id})

seed_property_b = env['real.estate.property'].create({... 'company_id': company_b.id})
seed_lead_b = env['real.estate.lead'].create({... 'company_id': company_b.id})
seed_service_b = env['real.estate.service'].create({... 'company_id': company_b.id})
seed_proposal_b = env['real.estate.proposal'].create({... 'company_id': company_b.id})
```

### Required Non-Leakage Assertions

- Response for company A MUST NOT contain IDs, names, or counts of company B records
- Response MUST NOT contain seeded XML IDs or Odoo group XML IDs
- Response MUST NOT contain domain fragments such as `company_id`, `agent_id`, `user_id` logic
- Response MUST NOT contain record-rule expressions or backend model technical names

### Test Session Seeds

Tests should create a valid session per seeded user/role using project-standard auth flow and active company headers from `18.0/.env`.

---

## Non-Functional Requirements

**NFR1: Security**
- Triple decorators are mandatory: `@require_jwt + @require_session + @require_company`
- Capability payload is UX-only and MUST NOT weaken existing backend authorization
- Session hijacking protections from ADR-017 remain in force through `@require_session`
- Unsupported or ambiguous access MUST fail closed by omitting rules

**NFR2: Multi-Tenancy**
- Response company context MUST follow active session company
- No cross-company leakage is allowed
- Isolation tests are mandatory

**NFR3: Performance**
- Target response time: `< 100ms` for the endpoint under normal load
- Capability evaluation MUST be in-memory/declarative; no N+1 queries
- Rule generation SHOULD not depend on transactional searches of business records

**NFR4: Contract Stability**
- `/api/v1/me` remains unchanged
- `/api/v1/me/capabilities` contract is intentionally minimal and stable
- Responses must be deterministic to support contract testing and frontend caching

**NFR5: Quality**
- Python code must pass project linters per ADR-022
- Unit and E2E API tests are mandatory per ADR-003
- No hardcoded secrets in tests; use `18.0/.env`

---

## Technical Constraints

| Source | Requirement | Applied To |
|--------|-------------|------------|
| Constitution + ADR-011 | Authenticated company-scoped endpoints must use `@require_jwt + @require_session + @require_company` | Controller |
| ADR-009 | Active company and user session context come from authenticated request headers/session, not arbitrary request data | Contract |
| ADR-008 | Company isolation and no cross-company leakage | Endpoint behavior, tests |
| ADR-019 | Role names and RBAC semantics must align with the project RBAC taxonomy | ROLE_RULES |
| ADR-018 | Validate and normalize header/query-driven request context; generic errors only | Error handling |
| ADR-005 | Swagger is DB-driven; do not edit static files | Documentation |
| ADR-016 | Postman collection is generated after implementation | Documentation |
| ADR-022 | Linting/static analysis required before completion | Quality gates |
| Architecture Constraint | API-only feature for headless users; no Odoo UI/views/menus are specified | Scope |

### Implementation Pattern

- **Controller location**: extend `thedevkitchen_apigateway/controllers/me_controller.py` so `/api/v1/me*` stays co-located
- **Service location**: `18.0/extra-addons/quicksol_estate/services/capability_service.py`
- **Shared helper**: extract or reuse a role resolver to guarantee parity between `/api/v1/me` and `/api/v1/me/capabilities`

### ADR-007 Note

This MVP intentionally keeps the response contract to `user` + `rules` only, per confirmed scope. No extra hypermedia fields should be added to this endpoint in MVP even though ADR-007 was reviewed during specification.

---

## Success Criteria

### Backend
- [ ] `GET /api/v1/me/capabilities` exists
- [ ] Endpoint uses all three required decorators
- [ ] `/api/v1/me` remains unchanged
- [ ] Shared effective-role resolver prevents drift
- [ ] `rules` contains only whitelisted action/subject pairs
- [ ] Denied permissions are omitted, never serialized as booleans
- [ ] No internal security details leak in success or error payloads
- [ ] All 10 role matrices are covered by automated tests
- [ ] Multi-company isolation is verified

### Seeds & Tests
- [ ] Seed data covers 10 roles in company A
- [ ] Contrasting company B users exist for isolation assertions
- [ ] Multi-role parity seed exists
- [ ] Minimal domain records exist in both companies
- [ ] Non-leakage assertions are automated
- [ ] Tests read credentials/config from `18.0/.env`

### Documentation
- [ ] Spec references all applicable ADRs and related features
- [ ] Swagger registration is identified as DB-driven follow-up
- [ ] Postman collection is identified as post-development follow-up

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| CASL-safe capability projection | Backend returns product-safe `action` + `subject` rules for headless UX, without exposing Odoo internals | Security Requirements / Architectural Patterns | High |
| Shared role-resolution parity | Related identity endpoints must reuse one effective-role resolver to avoid drift | Security Requirements | High |
| Deny-by-omission UX contract | Missing rules represent denied access; no boolean deny map is exposed | API-First Design | Medium |

### New Entities/Relationships

| Entity | Related To | Relationship Type | Notes |
|--------|-----------|-------------------|-------|
| Capability Rule (virtual) | `res.users`, active company, RBAC groups | Derived 1:N | In-memory response object, not persisted |

### Architectural Decisions

| Decision | Rationale | ADR Required? |
|----------|-----------|---------------|
| Keep `/api/v1/me` unchanged and add `/api/v1/me/capabilities` in parallel | Avoid breaking clients and keep identity bootstrap separate from UX capability bootstrap | No |
| Centralize `ROLE_RULES` in a service under `quicksol_estate` | Keeps product authorization mapping declarative and testable | No |
| Reuse current `/api/v1/me` role precedence for MVP | Guarantees session-context parity and prevents inconsistent frontend behavior | No |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: MINOR
- **Sections to Update**:
  - [x] Security Requirements
  - [x] Architectural Patterns
  - [x] API-First Design
  - [ ] Quality & Testing Standards
  - [ ] Development Workflow

---

## Assumptions & Dependencies

**Assumptions**:
- Current effective-role behavior is the precedence-based role mapping already implemented in `thedevkitchen_apigateway/controllers/me_controller.py`
- Capability rules are UX hints only and do not replace backend authorization
- Unsupported or non-mapped sessions are safer as `rules: []` than as expanded technical errors
- Conservative MVP may intentionally under-grant UI affordances compared with some backend permissions; ambiguity must fail closed
- CMS and appointment capability subjects remain ungranted in MVP until product surfaces exist

**Dependencies**:
- Existing auth/session middleware in `thedevkitchen_apigateway`
- Existing RBAC groups from `quicksol_estate`
- Existing multi-company infrastructure (`@require_company`)
- Existing headless session lifecycle from Feature 009

---

## Implementation Phases

### Phase 1: Contract & Resolver
- Extract/reuse shared effective-role resolver
- Define action/subject whitelist
- Define conservative `ROLE_RULES`

### Phase 2: Service & Controller
- Implement `UserCapabilityService`
- Add `GET /api/v1/me/capabilities`
- Keep `/api/v1/me` behavior unchanged

### Phase 3: Tests & Seeds
- Add unit tests for resolver/mapping/whitelist/deduplication
- Add E2E API tests for auth, matrix, isolation, and non-leakage
- Add seed fixtures for companies, roles, multi-role user, and minimal domain records

### Phase 4: Documentation & Artifacts
- Register Swagger endpoint through DB-driven flow
- Generate/update Postman collection after implementation
- Review constitution update for new CASL-safe capability pattern

---

## Artifacts to Generate After Spec Approval

1. **Implementation plan** → `speckit.plan`
2. **Constitution update** → `thedevkitchen.constitution`
3. **Swagger registration/update** → DB-driven workflow per ADR-005
4. **Postman collection** → `thedevkitchen.postman`
5. **Test strategy + test generation** → follow mandatory ADR-003 flow

---

## Validation Checklist

### Backend Validation
- [ ] New endpoint only; `/api/v1/me` unchanged
- [ ] Triple decorators specified
- [ ] Multi-tenancy isolation specified
- [ ] All 10 roles included in conservative MVP matrix
- [ ] CASL-safe contract documented
- [ ] No technical Odoo leakage documented
- [ ] Shared resolver parity documented
- [ ] Seed data documented
- [ ] Unit + E2E API tests specified
- [ ] DB-driven Swagger follow-up documented

### API-Only Scope Validation
- [ ] No Odoo UI flows were specified for non-admin roles
- [ ] No Odoo views/menus/forms/actions are required
- [ ] No Cypress UI coverage was added
- [ ] Headless frontend integration is described only through API contract and CASL usage

