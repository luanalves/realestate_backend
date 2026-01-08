# Feature Specification: Company Isolation Phase 1

**Feature Branch**: `001-company-isolation`  
**Created**: January 7, 2026  
**Status**: Draft  
**Input**: User description: "Complete Phase 1 multi-tenant company isolation with @require_company decorator and data filtering"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Company Data Filtering in API Endpoints (Priority: P1)

Real estate agency users can only access properties, agents, and other data that belong to their assigned company. When a user from "ABC Imóveis" logs in and requests property listings, the system automatically filters results to show only properties associated with their company, preventing data leakage from competing agencies.

**Why this priority**: This is the core security requirement for multi-tenancy. Without this, the entire multi-tenant architecture fails, exposing confidential business data across competitors.

**Independent Test**: Can be fully tested by creating two companies with distinct properties, then verifying that API calls from users of Company A return zero properties from Company B, and vice versa.

**Acceptance Scenarios**:

1. **Given** a user assigned to Company A with 10 properties, **When** they call `GET /api/v1/properties`, **Then** the response contains only the 10 properties from Company A (zero from other companies)
2. **Given** a user assigned to both Company A and Company B, **When** they call `GET /api/v1/properties`, **Then** the response contains properties from both companies
3. **Given** a user with no company assignment, **When** they call `GET /api/v1/properties`, **Then** the response returns an empty list (or 403 Forbidden with clear error message)
4. **Given** a user assigned to Company A, **When** they attempt to access a property from Company B via `GET /api/v1/properties/{id}`, **Then** the system returns 404 Not Found (not 403, to avoid information disclosure)

---

### User Story 2 - Company Validation on Create/Update Operations (Priority: P1)

When a user creates or updates a property, agent, tenant, or other entity, the system validates that the assigned company is one of the user's authorized companies. This prevents users from maliciously or accidentally assigning data to unauthorized companies.

**Why this priority**: Write operations are equally critical as read operations. Without validation, users could "inject" data into competitor companies or create orphaned records.

**Independent Test**: Can be fully tested by attempting to create a property with `company_id` set to an unauthorized company, verifying the request is rejected with a clear validation error.

**Acceptance Scenarios**:

1. **Given** a user assigned to Company A, **When** they create a property with `company_ids` set to [Company A], **Then** the property is created successfully
2. **Given** a user assigned to Company A, **When** they attempt to create a property with `company_ids` set to [Company B], **Then** the request is rejected with 403 Forbidden and error message "You are not authorized to assign data to this company"
3. **Given** a user assigned to both Company A and B, **When** they create a property with `company_ids` set to [Company A, Company B], **Then** the property is created and visible to users of both companies
4. **Given** a user updates an existing property from Company A, **When** they attempt to change `company_ids` to [Company B], **Then** the request is rejected with 403 Forbidden

---

### User Story 3 - @require_company Decorator Implementation (Priority: P1)

Developers can protect API endpoints by adding the `@require_company` decorator, which automatically filters database queries by the user's authorized companies. This decorator integrates seamlessly with existing `@require_jwt` and `@require_session` decorators.

**Why this priority**: This is the technical foundation that makes stories 1 and 2 possible. Without the decorator, every endpoint would need manual filtering logic, creating inconsistency and security gaps.

**Independent Test**: Can be fully tested by creating a test endpoint with `@require_company`, then verifying it filters results correctly and integrates with existing authentication decorators.

**Acceptance Scenarios**:

1. **Given** an endpoint decorated with `@require_company`, **When** a user without a session calls it, **Then** the `@require_session` decorator rejects the request before company filtering occurs
2. **Given** an endpoint decorated with `@require_company`, **When** an authenticated user with company assignment calls it, **Then** the decorator injects company filters into the database context
3. **Given** an endpoint using `env['thedevkitchen.estate.property'].search([])`, **When** the `@require_company` decorator is active, **Then** the search automatically includes `('estate_company_ids', 'in', user.estate_company_ids.ids)`
4. **Given** an endpoint decorated with `@require_company`, **When** a user with no company assignment calls it, **Then** the decorator returns 403 Forbidden with message "No company assignment found for user"

---

### User Story 4 - Record Rules Activation for Odoo Web UI (Priority: P2)

When users access the Odoo Web interface (not just REST APIs), they see only records from their assigned companies. This is achieved by activating Odoo Record Rules that mirror the API-level filtering.

**Why this priority**: While the project is API-first, developers and administrators still use the Odoo Web UI for configuration and debugging. Consistency between API and Web UI prevents confusion and security gaps.

**Independent Test**: Can be fully tested by logging into Odoo Web as a user assigned to Company A, then verifying the Properties menu shows only Company A properties.

**Acceptance Scenarios**:

1. **Given** Record Rules are activated for `thedevkitchen.estate.property`, **When** a user assigned to Company A views the Properties menu in Odoo Web, **Then** only Company A properties are visible
2. **Given** a user creates a property via Odoo Web, **When** they save the record without selecting a company, **Then** the system automatically assigns the user's default company (`estate_default_company_id`)
3. **Given** Record Rules are activated, **When** a user attempts to directly access a property ID from another company (via URL manipulation), **Then** Odoo displays "Access Denied" error

---

### User Story 5 - Multi-Tenant Isolation Test Suite (Priority: P2)

The system includes comprehensive automated tests verifying that company isolation works correctly across all API endpoints and entity types. These tests prevent regressions when new features are added.

**Why this priority**: Without automated testing, company isolation could silently break during refactoring or new feature development, creating security vulnerabilities.

**Independent Test**: Can be fully tested by running the isolation test suite and verifying all tests pass, then intentionally breaking isolation logic to confirm tests catch the failure.

**Acceptance Scenarios**:

1. **Given** the isolation test suite is run, **When** all tests execute, **Then** 100% pass with no failures or warnings
2. **Given** isolation logic is intentionally disabled in an endpoint, **When** the test suite runs, **Then** at least one test fails with a clear error message about data leakage
3. **Given** a new endpoint is added without `@require_company`, **When** the test suite runs, **Then** a test failure indicates the missing decorator
4. **Given** the test suite covers all entity types (properties, agents, tenants, owners, buildings, leases, sales), **When** run, **Then** each entity type has passing isolation tests

---

### Edge Cases

- What happens when a user's company assignment is removed while they have an active session?
- How does the system handle users assigned to a company that is archived or deleted?
- What occurs when a property is shared across 3 companies, but the user creating it only belongs to 2 of them?
- How does bulk import (via CSV or API) handle company assignments for hundreds of properties at once?
- What happens when Record Rules and API decorators are misaligned (e.g., Rule allows access but decorator denies)?
- How does the system behave when `estate_company_ids` field is empty (null vs empty list)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST filter all API query results by the authenticated user's `estate_company_ids` field
- **FR-002**: System MUST reject create/update operations that attempt to assign entities to companies not in the user's `estate_company_ids`
- **FR-003**: The `@require_company` decorator MUST integrate with existing `@require_jwt` and `@require_session` decorators without conflicts
- **FR-004**: All REST API endpoints for properties, agents, tenants, owners, buildings, leases, and sales MUST apply `@require_company` decorator
- **FR-005**: Record Rules MUST be activated for all estate models (`thedevkitchen.estate.*`) to enforce company isolation in Odoo Web UI
- **FR-006**: System MUST log company isolation violations (attempts to access unauthorized data) in audit logs
- **FR-007**: Error messages for unauthorized access MUST NOT reveal the existence of data in other companies (use 404, not 403, for record-level access)
- **FR-008**: When a user has multiple company assignments, system MUST aggregate data from ALL assigned companies, not just the default company
- **FR-009**: System MUST handle users with zero company assignments gracefully (return empty results or clear error, not crash)
- **FR-010**: The `@require_company` decorator MUST inject company filters at the ORM level, not application level, to prevent SQL injection bypasses

### Key Entities *(include if feature involves data)*

- **User (res.users)**: Extended with `estate_company_ids` (Many2many to `thedevkitchen.estate.company`) and `estate_default_company_id` (Many2one)
- **Company (thedevkitchen.estate.company)**: Real estate company entity with name, registration, contact info
- **Property (thedevkitchen.estate.property)**: Extended with `estate_company_ids` (Many2many) for multi-company ownership
- **Agent (thedevkitchen.estate.agent)**: Extended with `estate_company_ids` for company association
- **Tenant (thedevkitchen.estate.tenant)**: Extended with `estate_company_ids` for company association
- **Owner (thedevkitchen.estate.owner)**: Extended with `estate_company_ids` for company association
- **Building (thedevkitchen.estate.building)**: Extended with `estate_company_ids` for company association
- **Lease (thedevkitchen.estate.lease)**: Extended with `estate_company_ids` for company association
- **Sale (thedevkitchen.estate.sale)**: Extended with `estate_company_ids` for company association
- **Company Relationship Tables**: Junction tables like `company_property_rel`, `company_agent_rel`, etc., for Many2many relationships

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users from Company A see zero records from Company B when querying any API endpoint (100% isolation verified via automated tests)
- **SC-002**: All 12 existing API endpoints (4 CRUD + 8 master data) successfully apply company filtering without breaking existing functionality
- **SC-003**: Multi-tenant isolation test suite achieves 100% pass rate with at least 30 test scenarios covering all entity types
- **SC-004**: Record Rules in Odoo Web UI match API-level filtering (verified by manual testing of all entity menus)
- **SC-005**: System handles users with 0, 1, or multiple company assignments correctly (edge case coverage ≥ 90%)
- **SC-006**: Unauthorized access attempts (user from Company A trying to access Company B data) are logged in audit logs with 100% capture rate
- **SC-007**: API endpoint performance degradation is less than 10% after adding company filtering (measured via benchmark tests)
- **SC-008**: Documentation for `@require_company` decorator is complete with code examples and integration guide

## Assumptions

- User-to-company assignments are managed via Odoo Web UI by administrators (not exposed via REST API initially)
- All existing properties in the database will be migrated to have at least one company assignment (migration script required)
- The `thedevkitchen.estate.company` model already exists with basic fields (name, registration, contact)
- Redis session storage is already configured and working (Phase 0 complete)
- JWT and session authentication decorators are stable and tested (Phase 0 complete)
- Odoo Record Rules syntax and behavior are well-understood by the development team

## Out of Scope

- Role-Based Access Control (RBAC) within a company (e.g., Manager vs Agent permissions) - deferred to Phase 2
- Dynamic company switching within a single session (users see aggregated data from all assigned companies)
- Cross-company data sharing workflows (e.g., property referrals between agencies) - future feature
- Company hierarchy or parent-child company relationships
- REST API endpoints for managing company assignments (admin-only via Odoo Web UI)
- Performance optimization via database indexes (addressed in future performance sprint)
- Multi-company support for Odoo core modules (`res.company` integration) - deferred per technical debt item #5

## Dependencies

- **Phase 0 Complete**: JWT authentication, session management, and user login endpoints must be functional
- **Database Schema**: `estate_company_ids` fields must exist on all estate models (may require migration)
- **Audit Logging Module**: `auditlog` module must be installed and configured to capture security events
- **Test Infrastructure**: Odoo test framework and Cypress E2E setup must be working

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation from Many2many joins | High | Medium | Add database indexes on junction tables; monitor query performance |
| Existing data lacks company assignments | High | High | Create migration script to assign all orphaned records to a default company |
| Record Rules conflict with API decorators | Medium | Low | Comprehensive integration tests; alignment checklist in code review |
| Users accidentally locked out (zero companies) | Medium | Medium | Default new users to a "demo" company; clear error messages |
| Incomplete endpoint coverage (missed decorators) | High | Medium | Automated test to scan all API endpoints for `@require_company` presence |
