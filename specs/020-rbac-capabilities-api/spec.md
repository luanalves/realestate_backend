# Feature Specification: RBAC Capabilities API

**Feature Branch**: `020-rbac-capabilities-api`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Use the existing `spec-idea.md` in `specs/020-rbac-capabilities-api/` as the source input and preserve its constraints."  
**Source Document**: [spec-idea.md](./spec-idea.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap Safe UI Capabilities (Priority: P1)

As an authenticated headless user, I want to fetch the capabilities for my active session and company so the frontend can render the correct menus, routes, and actions without hardcoding role logic.

**Why this priority**: This is the core business value of the feature. Without it, the frontend cannot safely bootstrap role-aware navigation for the active user.

**Independent Test**: Authenticate as a supported role, call `GET /api/v1/me/capabilities`, and confirm the response can drive the initial UI state using only the returned `user` and `rules`.

**Acceptance Scenarios**:

1. **Given** a valid authenticated request with JWT, session, and company context, **When** the user requests `GET /api/v1/me/capabilities`, **Then** the system returns `200 OK`.
2. **Given** a successful response, **When** the payload is inspected, **Then** it contains exactly two top-level keys: `user` and `rules`.
3. **Given** a successful response, **When** the `user` object is inspected, **Then** it contains only `id`, `role`, and `company_id`.
4. **Given** a user who is allowed some actions but denied others, **When** capabilities are returned, **Then** only allowed rules are present and denied rules are omitted.
5. **Given** a user with multiple profiles, **When** capabilities are returned, **Then** the effective role matches the active session context already used by `/api/v1/me`.

---

### User Story 2 - Render Role-Appropriate UX Without Leaking Internals (Priority: P1)

As a frontend application, I want a conservative whitelist of allowed actions and subjects so I can show only the appropriate experience for each role without exposing backend RBAC internals.

**Why this priority**: The feature must improve UX while preserving security boundaries. A deny-by-omission contract prevents accidental disclosure of internal authorization logic.

**Independent Test**: Compare responses for roles such as owner, manager, agent, property owner, and tenant, and verify that each receives only the intended safe rules with no internal RBAC artifacts.

**Acceptance Scenarios**:

1. **Given** an owner user, **When** capabilities are returned, **Then** the response includes administrator-oriented capabilities such as access to administrative menu surfaces.
2. **Given** an agent user, **When** capabilities are returned, **Then** the response excludes administrator-only capabilities.
3. **Given** a manager user, **When** capabilities are returned, **Then** the response includes reassignment-oriented capabilities needed for team coordination.
4. **Given** a property owner or tenant user, **When** capabilities are returned, **Then** the response includes only limited external-safe capabilities.
5. **Given** any successful or failed response, **When** the payload is inspected, **Then** it contains no Odoo group names, XML IDs, record-rule fragments, domains, model names, or security reasoning.

---

### User Story 3 - Preserve Active Company Isolation and Existing Identity Contract (Priority: P1)

As a multi-company user, I want capabilities to reflect only my active company context so that the frontend never infers permissions or data from another company and existing identity flows remain stable.

**Why this priority**: Multi-tenancy isolation is non-negotiable in this repository. The new endpoint must be additive only and must not create regressions in the existing `/api/v1/me` contract.

**Independent Test**: Use mirrored users across two companies, call the endpoint with different active company contexts, and verify company-scoped results while confirming `/api/v1/me` stays unchanged.

**Acceptance Scenarios**:

1. **Given** company A is the active authenticated company, **When** the user requests capabilities, **Then** `user.company_id` matches company A.
2. **Given** a user requests capabilities for an unauthorized company context, **When** the request is processed, **Then** the system returns `403 Forbidden`.
3. **Given** equivalent users in company A and company B, **When** each requests capabilities, **Then** each response is limited to its own company context with no cross-company identifiers or leakage.
4. **Given** the feature is released, **When** existing clients continue using `/api/v1/me`, **Then** that endpoint remains unchanged.
5. **Given** an internal processing failure, **When** the endpoint responds, **Then** the error remains generic and reveals no security internals.

---

### Edge Cases

- A user has no supported real-estate role in the active session context.
- A user belongs to multiple profiles and the same effective-role precedence as `/api/v1/me` must be preserved.
- The request is missing or has an invalid JWT, session, or company context.
- A company switch occurs between requests and the frontend must refresh capabilities for the new active company.
- The role mapping contains duplicate or conflicting rules and the response must remain deterministic and duplicate-free.
- Internal RBAC constructs exist in the backend but must never appear in the response payload.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a new authenticated endpoint at `GET /api/v1/me/capabilities`.
- **FR-002**: The endpoint MUST remain protected by `@require_jwt`, `@require_session`, and `@require_company`.
- **FR-003**: The existing `GET /api/v1/me` contract MUST remain unchanged.
- **FR-004**: The capabilities response MUST contain exactly two top-level keys: `user` and `rules`.
- **FR-005**: The `user` object MUST contain only `id`, `role`, and `company_id`.
- **FR-006**: Effective role resolution for the capabilities response MUST follow the same active-session behavior as `GET /api/v1/me`, including multi-profile users.
- **FR-007**: If no supported role is resolved for the active session context, the system MUST return `200 OK` with `user.role = null` and `rules = []`.
- **FR-008**: The system MUST return capabilities as a conservative allow-list of `action` and `subject` rule pairs suitable for frontend ability building.
- **FR-009**: Denied capabilities MUST be omitted rather than represented as boolean flags, deny reasons, or internal authorization details.
- **FR-010**: The system MUST support the MVP role set already defined in the source idea: `owner`, `director`, `manager`, `agent`, `prospector`, `receptionist`, `financial`, `legal`, `property_owner`, and `tenant`.
- **FR-011**: The capabilities returned for each role MUST remain conservative and role-appropriate, including limited external-safe read access for `property_owner` and `tenant`.
- **FR-012**: The response MUST exclude internal RBAC artifacts, including Odoo group names, XML IDs, record rules, domains, model names, and stack traces.
- **FR-013**: `user.company_id` and all returned capabilities MUST reflect only the active authenticated company context.
- **FR-014**: Requests with unauthorized or invalid company context MUST be rejected without revealing cross-company information.
- **FR-015**: The response MUST be deterministic and free of duplicate `action` + `subject` pairs so that repeated frontend bootstrap and contract validation remain stable.
- **FR-016**: Error responses for authentication, authorization, and internal failures MUST remain generic and MUST NOT disclose security internals.
- **FR-017**: The feature scope MUST remain API-only; it MUST NOT change Odoo UI surfaces, MUST NOT modify `/api/v1/me`, and MUST NOT rely on static Swagger file edits.
- **FR-018**: Acceptance validation for this feature MUST cover the full 10-role matrix, multi-profile role parity, two-company isolation, and non-leakage scenarios captured in the source idea.

### Key Entities *(include if feature involves data)*

- **Capability Response**: The bootstrap payload returned to the authenticated frontend, composed only of `user` and `rules`.
- **Capability Rule**: A single allowed `action` + `subject` pair that communicates a safe UI permission without exposing backend internals.
- **Session Capability Context**: The authenticated user, resolved role, and active company context that determine which capability rules are returned.

### Dependencies & Assumptions

- This feature depends on the existing RBAC taxonomy and role semantics already established in earlier repository features and ADR-019.
- Existing authenticated session handling remains the source of truth for user identity, active company, and effective role behavior.
- The feature is intentionally additive: it introduces a parallel capabilities endpoint and does not replace backend authorization or the existing identity bootstrap endpoint.
- Swagger/OpenAPI handling remains DB-driven per project convention; any documentation registration is a follow-up workflow and not a static file edit.
- Active development context remains `18.0`, and the feature is intended for headless API consumers only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance validation, authenticated users representing all 10 supported roles can retrieve a usable capabilities response for their active company in a single request.
- **SC-002**: 100% of validated successful responses contain only the top-level keys `user` and `rules`, with no leaked internal RBAC artifacts.
- **SC-003**: Regression validation confirms that `GET /api/v1/me` remains unchanged after this feature is introduced.
- **SC-004**: All planned role-matrix, multi-profile parity, and multi-company isolation scenarios pass automated validation before the feature is considered ready.
- **SC-005**: Under normal operating conditions, at least 95% of capability requests complete quickly enough for the frontend to finish initial UI bootstrap in under 1 second.
