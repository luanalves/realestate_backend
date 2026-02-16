# Feature Specification: Tenant, Lease & Sale API Endpoints

**Feature Branch**: `008-tenant-lease-sale-api`
**Created**: 2026-02-14
**Status**: Draft
**Input**: User description: "Implementar endpoints REST completos para gerenciamento de Inquilinos (Tenants), Contratos de Aluguel (Leases) e Vendas (Sales). Estes endpoints seguem o padrão estabelecido nos demais módulos, com autenticação dual, multi-tenancy obrigatório via company_ids, e RBAC para controle de acesso por perfil."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant CRUD Management (Priority: P1) 🎯 MVP

A property manager needs to register and maintain records of all tenants associated with the company's properties. This includes creating new tenant profiles with contact information, viewing tenant details, updating tenant data, and archiving tenants who are no longer active. All operations respect company boundaries so managers only see tenants within their own organization.

**Why this priority**: Tenants are the foundational entity for lease management. Without tenant records, leases cannot be created or tracked. This is a prerequisite for the entire rental workflow.

**Independent Test**: Can be fully tested by creating a tenant, listing tenants, updating tenant data, and archiving — delivers a complete tenant registry independent of leases or sales.

**Acceptance Scenarios**:

1. **Given** an authenticated manager with a valid company, **When** they request the list of tenants for their company, **Then** the system returns a paginated list of tenants belonging to that company only
2. **Given** an authenticated manager, **When** they submit a new tenant with name, phone, and valid email, **Then** the system creates the tenant linked to the manager's company and returns the created record
3. **Given** an existing tenant, **When** a manager requests the tenant by ID, **Then** the system returns the full tenant details including contact information and related lease references
4. **Given** an existing tenant, **When** a manager updates the tenant's phone or email, **Then** the system persists the changes and returns the updated record
5. **Given** an existing tenant, **When** a manager deletes (archives) the tenant, **Then** the tenant is logically deactivated (not permanently removed) and no longer appears in default listings
6. **Given** a request without a company identifier, **When** any tenant operation is attempted, **Then** the system rejects the request with a clear error indicating the company is required
7. **Given** a manager from Company A, **When** they attempt to access a tenant from Company B, **Then** the system denies access

---

### User Story 2 - Lease Lifecycle Management (Priority: P1) 🎯 MVP

A property manager needs to create and manage rental lease contracts that link a property to a tenant with defined dates and rent amounts. Beyond standard CRUD, the manager must be able to renew expiring leases (extending or creating a new period) and terminate active leases early when circumstances require. Each lease tracks its status through draft, active, terminated, and expired states.

**Why this priority**: Leases are the core business object for rental operations, directly representing revenue contracts. The ability to create, renew, and terminate leases is essential for day-to-day property management operations.

**Independent Test**: Can be fully tested by creating a lease between an existing property-tenant pair, viewing it, renewing it, and terminating it — delivers complete lease lifecycle management.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a valid company, **When** they request the list of leases, **Then** the system returns a paginated list of leases filtered by their company
2. **Given** valid property and tenant references, **When** a manager creates a lease with start date, end date, and rent amount, **Then** the system creates the lease linking property to tenant and returns the created record
3. **Given** a lease where end date is before start date, **When** a manager attempts to create the lease, **Then** the system rejects the request with a validation error
4. **Given** a non-existent property ID, **When** a manager attempts to create a lease, **Then** the system returns a not-found error
5. **Given** an active lease nearing expiration, **When** a manager renews it with a new end date, optionally updated rent, and a reason, **Then** the system extends the lease in-place and records a renewal history entry with who renewed, why, when, and the previous contract terms
6. **Given** an active lease, **When** a manager terminates it early with a termination date, reason, and optional penalty amount, **Then** the system marks the lease as terminated and records all early exit details including the penalty for audit
7. **Given** a lease that belongs to Company A, **When** a user from Company B attempts to access it, **Then** the system denies access

---

### User Story 3 - Sale Registration & Management (Priority: P1) 🎯 MVP

A property manager or agent needs to register property sales, capturing buyer information, sale price, the responsible agent, and optionally the originating lead. Sales must support cancellation for deals that fall through. When a sale is completed, the system should emit an event to trigger downstream processes such as commission calculation.

**Why this priority**: Sales represent completed transactions and revenue realization. Tracking sales with agent attribution and lead source is critical for commission processing and pipeline analytics.

**Independent Test**: Can be fully tested by creating a sale against an existing property, viewing sale details, and cancelling a sale — delivers complete sale tracking independent of commissions processing.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a valid company, **When** they request the list of sales, **Then** the system returns a paginated list of sales for their company with optional filters by property, agent, status, and price range
2. **Given** valid property and buyer information, **When** a manager creates a sale with sale date, price, and agent, **Then** the system registers the sale and emits a completion event for downstream processing
3. **Given** a sale price of zero or negative amount, **When** a manager attempts to create the sale, **Then** the system rejects the request with a validation error
4. **Given** an agent that belongs to a different company than the sale, **When** a manager attempts to create the sale, **Then** the system rejects the request because the agent must belong to the same company
5. **Given** a completed sale, **When** a manager cancels it with a reason, **Then** the system marks the sale as cancelled and records the cancellation reason
6. **Given** a sale from Company A, **When** a user from Company B attempts to view it, **Then** the system denies access

---

### User Story 4 - Tenant Lease History (Priority: P2)

A manager or agent viewing a tenant's profile needs to see all lease contracts associated with that tenant — both current and historical. This provides a consolidated view of the tenant's rental history without navigating away from the tenant record.

**Why this priority**: Enhances the tenant management experience by providing contextual lease information directly from the tenant, but not strictly required for core operations.

**Independent Test**: Can be tested by viewing a tenant's lease list endpoint — delivers consolidated lease history per tenant.

**Acceptance Scenarios**:

1. **Given** a tenant with multiple leases, **When** a user requests the tenant's lease list, **Then** the system returns all leases associated with that tenant
2. **Given** a tenant with no leases, **When** a user requests the tenant's lease list, **Then** the system returns an empty list

---

### User Story 5 - Soft Delete & Record Recovery (Priority: P2)

A manager needs to archive (deactivate) tenants, leases, and sales without permanently losing data. Archived records are hidden from default listings but can be queried explicitly. Deactivated records can also be reactivated if needed.

**Why this priority**: Data preservation is important for audit trails and undoing mistakes, but is secondary to core CRUD and lifecycle operations.

**Independent Test**: Can be tested by archiving a record and verifying it no longer appears in default listings, then querying explicitly with active filter — delivers audit-safe deletion.

**Acceptance Scenarios**:

1. **Given** an active tenant/lease/sale, **When** a manager deactivates it, **Then** the record is marked inactive and hidden from default listings
2. **Given** an inactive record, **When** a user queries with an explicit "include inactive" filter, **Then** the inactive record appears in results
3. **Given** an inactive tenant/lease/sale, **When** a manager reactivates it, **Then** the record becomes visible in default listings again

---

### Edge Cases

- What happens when a tenant is archived but has active leases? → Active leases associated with the tenant remain active; a warning is returned indicating the tenant has ongoing lease obligations
- What happens when a property referenced by a lease is archived? → The lease remains accessible, but creating new leases against an inactive property is rejected
- What happens when a sale is created for a property that already has active leases? → The sale proceeds and the property is marked as "sold"; existing active leases remain valid until their end date but no new leases can be created
- What happens when a sale is cancelled — does the property revert from "sold"? → Yes, cancelling a sale reverts the property status so new leases can be created again
- What happens when a lease renewal is attempted on a terminated lease? → The system rejects the renewal and returns an error indicating only active leases can be renewed
- What happens when a sale references a lead that has been archived? → The sale is still created; the lead reference is preserved for historical tracking
- How does the system handle duplicate tenant email within the same company? → Email uniqueness is not enforced across tenants (multiple tenants may share an email), but invalid email format is rejected
- What happens when paginated list requests exceed available records? → The system returns an empty data array with pagination metadata showing total count
- What happens when a lease's rent amount is zero or negative? → The system rejects with a validation error; rent must be a positive value
- What happens when a user tries to create a lease for a property that already has an active lease? → The system rejects the creation with an error indicating the property already has an active lease; the existing lease must expire or be terminated first

## Requirements *(mandatory)*

### Functional Requirements

**Tenant Management**

- **FR-001**: System MUST allow authenticated users to create tenant records with name (required), phone, email, and company association
- **FR-002**: System MUST validate tenant email format when provided and reject malformed emails
- **FR-003**: System MUST return paginated tenant lists filtered by the user's company
- **FR-004**: System MUST allow retrieval of a single tenant by ID, including related lease references
- **FR-005**: System MUST allow updating tenant contact information (name, phone, email, occupation, birthdate)
- **FR-006**: System MUST support logical deletion (archiving) of tenants, preserving the record for audit
- **FR-007**: System MUST support reactivation of archived tenants, leases, and sales
- **FR-008**: System MUST return all leases for a specific tenant via a dedicated sub-resource endpoint

**Lease Management**

- **FR-009**: System MUST allow creating lease contracts linking an existing property to an existing tenant with start date, end date, and rent amount
- **FR-010**: System MUST validate that end date is after start date when creating or updating a lease
- **FR-011**: System MUST validate that rent amount is a positive value
- **FR-012**: System MUST validate that the referenced property and tenant exist and belong to the user's company
- **FR-013**: System MUST reject lease creation if the property already has an active lease with overlapping dates (one active lease per property at a time) or if the property status is "sold" (per FR-029)
- **FR-014**: System MUST return paginated lease lists filtered by the user's company, with optional filters for property, tenant, and status
- **FR-015**: System MUST allow retrieval of a single lease by ID with property and tenant details
- **FR-016**: System MUST allow updating lease fields (dates, rent amount) for non-terminated leases
- **FR-017**: System MUST support lease renewal by extending the existing lease's end_date (and optionally rent_amount) in-place, while recording a renewal audit entry capturing: who renewed, reason, timestamp, and the previous terms (old end_date, old rent_amount)
- **FR-018**: System MUST support early termination of active leases, recording the termination date, reason, and an optional penalty amount for audit purposes (no automated billing)
- **FR-019**: System MUST support logical deletion (archiving) of leases
- **FR-020**: System MUST auto-generate a human-readable lease reference name from property, tenant, and start date

**Sale Management**

- **FR-021**: System MUST allow creating sale records linking a property with buyer information, sale date, price, and optionally an agent and originating lead
- **FR-022**: System MUST validate that sale price is a positive value
- **FR-023**: System MUST validate that the referenced agent belongs to the same company as the sale
- **FR-024**: System MUST return paginated sale lists filtered by the user's company, with optional filters for property, agent, status, and price range
- **FR-025**: System MUST allow retrieval of a single sale by ID with full details (buyer, agent, lead, property)
- **FR-026**: System MUST allow updating sale information for non-cancelled sales
- **FR-027**: System MUST support sale cancellation with a recorded reason
- **FR-028**: System MUST emit a domain event when a sale is successfully created, enabling downstream processes (e.g., commission calculation)
- **FR-029**: System MUST automatically mark the property as "sold" when a sale is created, preventing new leases from being created against that property

**Cross-cutting**

- **FR-030**: All endpoints MUST enforce company-based data isolation — users can only access records belonging to their authorized company
- **FR-031**: All endpoints MUST require dual authentication (application authorization + user session)
- **FR-032**: All list endpoints MUST require a company identifier parameter
- **FR-033**: All list endpoints MUST support pagination with configurable page size (default and maximum limits)
- **FR-034**: All responses MUST include navigational links following hypermedia conventions (self, collection, related resources)
- **FR-035**: All delete operations MUST be logical (soft delete) — records are deactivated, not permanently removed
- **FR-036**: System MUST support querying both active and inactive records via an explicit filter parameter
- **FR-037**: System MUST enforce role-based access: Managers and Owners can access all company records; Agents can only access tenants and leases linked to properties they are assigned to, and sales where they are the responsible agent

### Key Entities

- **Tenant**: Represents an individual who rents a property. Key attributes: name, contact information (phone, email), occupation, birthdate, portal access link. A tenant is associated with one or more companies and may have multiple leases over time.
- **Lease**: Represents a rental contract binding a specific property to a specific tenant for a defined period. Key attributes: linked property, linked tenant, start date, end date, monthly rent amount, status (draft/active/terminated/expired), auto-generated reference name. Leases support in-place renewal (with audit history of previous terms) and early termination workflows.
- **Lease Renewal History**: Represents an audit record of a lease renewal event. Key attributes: linked lease, previous end date, previous rent amount, renewed by (user), renewal reason, renewal timestamp. One lease may have multiple renewal history entries over its lifetime.
- **Sale**: Represents a completed or pending property sale transaction. Key attributes: linked property, buyer information (name, phone, email), sale date, sale price, responsible agent, originating lead, status (completed/cancelled). Creating a sale triggers a domain event for commission processing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create, view, update, and archive tenants in under 3 interactions per operation
- **SC-002**: Users can create a lease linking property and tenant, including all validations, in under 2 minutes
- **SC-003**: Users can renew an expiring lease in a single action, without re-entering existing contract data
- **SC-004**: Users can terminate a lease early in a single action, capturing the reason for audit
- **SC-005**: Users can register a sale and have the commission event triggered automatically without manual intervention
- **SC-006**: All 18 endpoints respond within acceptable time for single-resource operations (< 2 seconds perceived by user)
- **SC-007**: Company data isolation is 100% enforced — no cross-company data leakage under any scenario
- **SC-008**: All validation rules (email format, date ordering, positive amounts, company matching) reject invalid input with clear, actionable error messages
- **SC-009**: Archived records are never shown in default listings but remain queryable through explicit filters
- **SC-010**: 100% of validation constraints are covered by automated tests

## Assumptions

- The data models for Tenant, Lease, and Sale already exist in the system with their core fields defined
- Models currently lack an "active" field for soft delete — this needs to be added as part of this feature
- Models currently lack a "status" field for Lease and Sale lifecycle tracking — this needs to be added
- The event bus mechanism for emitting `sale.created` events already exists and is functional
- The authentication and session management infrastructure is already in place and follows the established dual-auth pattern
- Company association uses a many-to-many relationship for multi-company scenarios
- Existing controller patterns (property, agent, lead, owner, company) serve as the reference implementation for consistency
- Default pagination limit is consistent with other endpoints in the system (assumed 20 items, max 100)
- Email uniqueness is NOT enforced across tenants — a shared email (e.g., a household) is acceptable

## Clarifications

### Session 2026-02-14

- Q: How should lease renewal work — create a new linked lease, mutate the existing lease, or create an independent lease? → A: Mutate the existing lease (extend end_date/rent in-place), but record renewal audit history capturing who renewed, why, when, and the previous contract terms
- Q: What is the Agent RBAC scope for tenants and leases? → A: Transitive via property assignment — Agents see tenants and leases linked to properties they are assigned to, and sales where they are the responsible agent
- Q: What happens to a property's status after a sale is registered? → A: The property is automatically marked as "sold", preventing new leases; cancelling a sale reverts the property status
- Q: Does early lease termination carry a financial penalty? → A: An optional penalty amount can be recorded for audit/informational purposes, but no automated billing is triggered
- Q: Can a property have multiple active leases simultaneously? → A: No — only one active lease per property at a time; new lease creation is rejected if the property already has an active lease with overlapping dates

## Dependencies

- Existing tenant, lease, and sale data models must be available in the system
- Authentication gateway and session management must be operational
- Event bus system must be functional for sale creation events
- RBAC (role-based access control) framework must be in place for profile-based permissions
- **Infrastructure**: PostgreSQL 14+ (data persistence via Odoo ORM), Redis 7 (HTTP session storage). See [plan.md](plan.md) § Technical Context for versions and configuration.

## Technical Decisions

*Recorded during implementation to close specification gaps identified by checklist triage.*

### TD-001 — Dual Error Response Envelope (CHK001)

Two error response shapes coexist across endpoints:

| Origin | Shape | Used By |
|--------|-------|---------|
| `error_response()` (response.py) | `{error, message, code}` | Legacy catch-all blocks, 500 errors, auth failures |
| `util_error()` (responses.py) | `{success: false, message, errors}` | Validation errors, business logic rejections |

**Decision**: Both shapes are **valid and intentional**. `error_response()` is the gateway-layer error format shared across all features. `util_error()` is the feature-specific format that supports structured `errors` payloads (e.g., field-level validation). Consumers MUST handle both envelopes. Unification is deferred to a cross-feature refactoring effort.

### TD-002 — Event Bus Fire-and-Forget Semantics (CHK005)

Domain events emitted via `event_bus.emit()` (e.g., `sale.created`) execute **synchronously within the same database transaction**:

- **Success**: Observer callbacks run and complete before the HTTP response.
- **Observer failure** (`after_` events): Exceptions are caught and logged; the parent operation (sale creation) **succeeds**. This is fire-and-forget by design.
- **`before_` events**: Observer exceptions propagate and **abort** the parent operation (transaction rollback).
- **Bus infrastructure failure**: If `event_bus.emit()` itself raises (e.g., invalid event name), the entire operation rolls back.

This behavior is acceptable for MVP. Async event delivery (via Celery/RabbitMQ) is a future enhancement — see `PLANO-CELERY-RABBITMQ.md`.

### TD-003 — Sale: Cancel-Only, No DELETE Endpoint (CHK019)

Sales intentionally use **cancel semantics** (`POST /api/v1/sales/<id>/cancel`) instead of soft-archive (`DELETE`). Rationale:

- A cancelled sale records `cancellation_date`, `cancellation_reason`, and reverts the property status — this is a **business action** with side effects, not a simple visibility toggle.
- Soft-deleting a sale (hiding it from listings) would lose auditability of completed-then-cancelled transactions.
- The `active` field exists on the Sale model for Odoo framework compatibility but is **not toggled** by any endpoint.

If archive semantics are needed in the future, a `DELETE /api/v1/sales/<id>` endpoint can be added separately from cancellation.

### TD-004 — Tenant Archive with Active Leases (CHK010)

When a tenant with active or draft leases is archived (`DELETE /api/v1/tenants/<id>`):

- The archive **proceeds** (tenant is deactivated).
- Active leases **remain active** — they are not terminated or cascaded.
- A `warning` field is included in the response indicating the number of ongoing leases.
- This matches the Edge Case specification: "Active leases associated with the tenant remain active; a warning is returned."

### TD-005 — Audit Trail Scope (CHK007)

Audit capabilities in this feature are **in-record** — no general-purpose audit log model is implemented:

| Entity | Audit Fields |
|--------|-------------|
| Tenant | `deactivation_date`, `deactivation_reason` on archive |
| Lease | `renewal_history` (One2many to `lease.renewal.history` model), `termination_date`, `termination_reason`, `termination_penalty` on terminate |
| Sale | `cancellation_date`, `cancellation_reason` on cancel |

The `lease.renewal.history` model provides full provenance: who renewed, why, when, and previous contract terms. A general audit log (e.g., `mail.tracking.value`) is deferred.

### TD-006 — Concurrent Lease Overlap: ORM-Level Check (CHK026)

The overlapping-lease constraint (`@api.constrains` on `property_id`, `start_date`, `end_date`, `status`) is enforced at the **ORM level** using a read-then-check pattern:

- Under normal load, this is sufficient — Odoo's transaction isolation (READ COMMITTED) ensures consistency for sequential requests.
- Under **concurrent load** (two simultaneous lease creation requests for the same property), a TOCTOU race is theoretically possible: both requests read "no overlap" before either commits.
- **Known limitation**: No `SELECT FOR UPDATE` or advisory lock is used. For MVP, this is acceptable given the low-concurrency nature of property management operations.
- **Mitigation**: A PostgreSQL-level `EXCLUDE` constraint or application-level `FOR UPDATE` lock can be added if concurrent write patterns emerge in production.

### TD-007 — Rate Limiting: Deferred (CHK035)

Rate limiting is **not implemented** on Feature 008 endpoints. A `rate_limit_exceeded()` helper exists in the error handler module (returns HTTP 429) but is not called from tenant, lease, or sale controllers.

**Rationale**: Feature 008 endpoints are internal APIs consumed by the SSR frontend, not public-facing. Odoo's WSGI worker pool (`limit_request`) provides a natural back-pressure mechanism. Rate limiting per-endpoint thresholds will be defined if public API exposure is planned.

### TD-008 — Performance SLAs: Global Threshold (CHK037)

SC-006 defines a **global** response time target: `< 2 seconds` for all 18 endpoints. No per-endpoint thresholds are specified.

**Rationale**: All endpoints perform simple CRUD operations against indexed PostgreSQL tables. List endpoints use `LIMIT/OFFSET` pagination capped at 100 items, which bounds query time. If specific endpoints (e.g., `GET /tenants/<id>/leases` with large histories) show degraded performance, per-endpoint SLAs will be introduced.

### TD-009 — API Error Messages: English Only (CHK039)

All API error messages are in **English**. The `_()` i18n function is used in `schema.py` validation labels but **not** in controller error strings.

**Decision**: Headless REST APIs conventionally use English for machine-consumable error messages. The SSR frontend is responsible for translating error codes/messages to the user's locale (Portuguese). Controller messages are stable, developer-facing strings (e.g., `"Tenant not found"`, `"Invalid email format"`).

### TD-010 — Sale Serialization: Full Field Exposure (CHK041)

`_serialize_sale()` returns `buyer_phone` and `buyer_email` to **all authenticated roles** (agent, manager, owner) without field-level filtering.

**Decision**: Acceptable for MVP. All users with access to a sale record have a legitimate business need for buyer contact information (e.g., agents coordinate with buyers). If GDPR/LGPD field-level masking is required, a role-based serialization filter will be added: agents see partial phone (`***-1234`), managers see full fields.

### TD-011 — Lease State Machine (CHK024, implemented)

Lease status transitions are enforced by a `write()` override with explicit transition rules:

```
draft → [active]
active → [terminated]  (via terminate endpoint)
active → [expired]     (via daily cron only)
terminated → []        (final state)
expired → []           (final state)
```

Context flags `cron_expire` and `lease_terminate` allow controlled bypass for the cron job and terminate endpoint respectively. Generic `PUT /leases/<id>` with `status` field is validated against this state machine.

### TD-012 — Sale Cancel Property Guard (CHK009/CHK031, implemented)

`action_cancel()` only reverts the property status to `'new'` if the property is currently `'sold'`. If the property state was changed after the sale was created (e.g., a new lease was started), the revert is skipped to avoid overwriting a valid state.
