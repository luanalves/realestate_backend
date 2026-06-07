# Feature Specification: Admin UI — Cross-Company Access for System Admin

**Feature Branch**: `022-admin-ui-cross-company`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "Admin UI cross-company access and API login block for system admin (base.group_system)"

## Clarifications

### Session 2026-06-03

- Q: When the REST API login endpoint rejects a System Admin (valid credentials, wrong channel), what HTTP status code must it return? → A: 401 Unauthorized — for security, the response must not reveal that the credentials were valid (anti-enumeration / information hiding extends ADR-008 principle to channel rejection).
- Q: FR-008 says the System Admin cross-company override must be a "developer convention verified via checklist" — where should that checklist live? → A: Both `knowledge_base/` (day-to-day developer reference when creating new modules) and `docs/adr/` (new ADR formalising the convention architecturally for design reviews and AI agents).
- Q: Is FR-007 (System Admin cannot be invited via API) enforced by Feature 009's existing authorization matrix or does it require new guard code? → A: Already satisfied by Feature 009 — `base.group_system` is not in any invitable profile; no new guard code needed for this feature. Add a verification test and document the constraint in ADR-029.
- Q: Should System Admin write access to sensitive models (e.g. `thedevkitchen.password.token`) be unrestricted or read-only? → A: Unrestricted — the System Admin already has native Odoo access to password tokens via another area of the platform; no special carve-outs needed. FR-002 applies uniformly to all entities.
- Q: Does rate limiting apply to blocked System Admin REST API login attempts, or is it delegated elsewhere? → A: Delegated to Kong API Gateway — existing gateway-level rate limiting covers all login endpoint traffic; this feature adds no application-level throttle.

---

## Context

The SaaS platform hosts multiple tenant companies under a single Odoo instance. Nine business role profiles (Owner, Manager, Agent, Receptionist, Tenant, etc.) exist for day-to-day operations, each scoped to their company's data. The System Admin is a platform-level role above all business roles — an infrastructure/SaaS administrator who must be able to oversee and manage data from every tenant company.

Currently, multi-tenancy access controls that correctly isolate business users also inadvertently block the System Admin from seeing data across companies. Additionally, there is no guard preventing a System Admin from authenticating through the application's REST API, which is intended exclusively for business users and headless integrations.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Views All Company Data (Priority: P1)

A System Admin logs in to the Odoo web interface and navigates to the Real Estate module. They expect to see records (properties, agents, leases, sales, proposals, services, CMS pages, goals, credit checks, commission data, etc.) belonging to **all tenant companies**, not just the company they are directly associated with.

**Why this priority**: Without cross-company visibility, the System Admin cannot fulfill their SaaS oversight role. This is the core value of the feature and every other story builds on it.

**Independent Test**: Can be fully tested by logging in as a System Admin and opening the Properties list — records from all companies must appear. If they do, the fundamental access fix is working and delivers the "oversight" value independently.

**Acceptance Scenarios**:

1. **Given** a System Admin is logged in to the Odoo web interface, **When** they navigate to the Real Estate Properties list, **Then** they see properties from all tenant companies, not filtered to a single company.
2. **Given** a System Admin is logged in to the Odoo web interface, **When** they navigate to Leases, Sales, Agents, Proposals, Services, Goals, CMS Pages, or Commission data, **Then** all records from all companies are visible.
3. **Given** a System Admin is logged in, **When** they open a record belonging to a tenant company that is not their own, **Then** the record opens fully readable without any access error.

---

### User Story 2 - Admin Manages Data Across All Companies (Priority: P2)

A System Admin can not only view but also create, edit, and delete records belonging to any tenant company through the Odoo web interface.

**Why this priority**: Read-only cross-company access delivers visibility but not governance. The ability to correct data, onboard companies, or resolve issues for any tenant is a key SaaS admin responsibility.

**Independent Test**: Can be fully tested by editing a property record that belongs to a different company and saving it successfully — this confirms write access is also unrestricted.

**Acceptance Scenarios**:

1. **Given** a System Admin is viewing a record from any tenant company, **When** they edit a field and save, **Then** the change is saved successfully without access errors.
2. **Given** a System Admin opens the creation form for any real estate entity, **When** they fill in required fields selecting any company, **Then** the record is created and persisted correctly.
3. **Given** a System Admin selects a record from any tenant company, **When** they delete it, **Then** the record is removed successfully.

---

### User Story 3 - Admin Sees All Navigation Menus (Priority: P3)

A System Admin navigating the Real Estate module can see and access all menu items, including menus that are normally restricted to specific business roles such as Agents and Managers.

**Why this priority**: If certain menus are hidden from the System Admin, cross-company data access is incomplete — they cannot reach all the data they need to manage. Visible menus are a prerequisite for full oversight.

**Independent Test**: Can be fully tested by confirming the Leads menu (and any other role-restricted menu) is visible and accessible to the System Admin in the web interface.

**Acceptance Scenarios**:

1. **Given** a System Admin is logged in to the Odoo web interface, **When** they open the Real Estate module's navigation, **Then** all sub-menus are visible, including Leads and any other menu previously restricted to business role groups.
2. **Given** a System Admin clicks any previously restricted menu item, **When** the page loads, **Then** it displays the full list of records from all companies without errors.

---

### User Story 4 - API Login Blocked for System Admin (Priority: P2)

A System Admin attempting to authenticate via the application's REST API login endpoint receives an error and cannot proceed. System Admins may only access the platform through the Odoo web interface.

**Why this priority**: Without this guard, a misconfigured or deliberately misused System Admin account could bypass multi-tenancy controls at the API level. This is a security requirement aligned with the platform's channel separation policy (admin = web only, business users = API/headless).

**Independent Test**: Can be fully tested independently by sending a login request with valid System Admin credentials to the REST API login endpoint — it must return a rejection response, not a session token.

**Acceptance Scenarios**:

1. **Given** valid System Admin credentials, **When** submitted to the REST API login endpoint, **Then** the endpoint returns HTTP 401 Unauthorized with a generic error message that does not reveal the user exists or that the channel is the reason for rejection (anti-enumeration: same response as for invalid credentials).
2. **Given** a valid System Admin login attempt via REST API is rejected, **Then** the event is recorded as a security audit log entry.
3. **Given** a regular business user with valid credentials, **When** they submit to the REST API login endpoint, **Then** authentication proceeds normally (System Admin block does not affect other users).

---

### Edge Cases

- What happens when a System Admin belongs to a company with no tenant data — does the cross-company fix still expose all other companies' data? (Expected: yes, access is unrestricted regardless of own company.)
- How does the system handle records that have no `company_id` set — does the System Admin see them? (Expected: yes, rules permitting all records implicitly include records with null company.)
- What if a System Admin's account is also added to a business role group? (Expected: the cross-company rules still apply and business-role rules do not restrict them, per Odoo's OR-union of rules.)
- What happens if a newly created module in the future introduces new data isolation rules without including System Admin access? (Expected: the platform should catch this — addressed via developer checklist, not runtime behaviour.)
- Can a System Admin accidentally create records without assigning a company, causing orphan data? (Expected: the Odoo web interface enforces company selection on the form; this is an existing Odoo safeguard.)

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow System Admin users to view all real estate records (properties, agents, leases, sales, proposals, services, CMS pages, goals, credit checks, commission rules, commission transactions, lease renewal history, user profiles, and password tokens) from all tenant companies via the Odoo web interface.
- **FR-002**: The system MUST allow System Admin users to create, edit, and delete records belonging to any tenant company via the Odoo web interface. *(Write access is unrestricted across all entities including `thedevkitchen.password.token` — the System Admin already has native Odoo-level access to password tokens via another platform area; no read-only carve-outs apply.)* 
- **FR-003**: The system MUST make all navigation menus in the Real Estate module visible and accessible to System Admin users, including menus currently restricted to specific business role groups.
- **FR-004**: The system MUST reject REST API authentication requests submitted with System Admin credentials, returning HTTP 401 Unauthorized with a generic error message that does not reveal whether the account exists or the reason for rejection (anti-enumeration — the response must be indistinguishable from a failed login with invalid credentials).
- **FR-005**: The system MUST record a security audit log entry each time a System Admin user attempts to authenticate via the REST API.
- **FR-006**: The system MUST preserve existing data isolation for all business role profiles (Owner, Manager, Agent, Receptionist, Tenant, etc.) — these users MUST continue to see only their own company's records after this feature is implemented.
- **FR-007**: System Admin users MUST only be created and managed through the Odoo web interface; it MUST NOT be possible to create or invite a System Admin via the REST API invitation flow. *(Satisfied by Feature 009's existing invitation authorization matrix — `base.group_system` is not an invitable profile; no new guard code required. This feature adds a verification test and documents the constraint in ADR-029.)*
- **FR-008**: The system MUST ensure that new data isolation rules added for future modules also include the System Admin cross-company override. This convention MUST be documented in two places: (1) a new ADR in `docs/adr/` formalising the rule architecturally, and (2) a developer checklist in `knowledge_base/` for day-to-day reference when creating new Odoo modules.

### Key Entities

- **System Admin**: A platform-level administrative user, above all business role profiles. Created exclusively through the Odoo web interface. Has unrestricted access to all company data via the web interface only.
- **Tenant Company**: An individual real estate business operating within the SaaS platform. Business role users are scoped to their company's data.
- **Business Role User**: Any user with one of the 9 real estate business profiles (Owner, Manager, Agent, Receptionist, Tenant, Investor, Accountant, Buyer, Porter). Remains isolated to their own company after this feature.
- **Security Audit Log**: A persistent record of security events, including blocked API login attempts.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of real estate record types (exactly 20 entity types as listed in `data-model.md`, across 5 modules) are visible to the System Admin across all tenant companies without any access error or empty list caused by company filtering. Note: entities from modules not yet installed on a given environment are exempt until those modules are installed.
- **SC-002**: System Admin can successfully create, edit, and delete records belonging to companies other than their own in the Odoo web interface in a single operation (no extra steps).
- **SC-003**: All navigation menus within the Real Estate module are visible and functional for the System Admin — zero menus hidden due to business role group restrictions.
- **SC-004**: 100% of REST API login attempts by System Admin users are rejected with HTTP 401 and a generic error message — no System Admin session tokens are issued via the API under any circumstances, and the response is indistinguishable from an invalid-credential failure.
- **SC-005**: Every blocked System Admin API login attempt produces a corresponding security log entry — zero silent failures.
- **SC-006**: Business role users' data isolation is unaffected — a tenant company user sees exactly the same set of records before and after this feature is deployed (zero cross-company data leakage).
- **SC-007**: The feature can be deployed to existing production databases without manual database intervention for any newly added isolation overrides.

---

## Assumptions

- The System Admin role corresponds to `base.group_system` in Odoo — a pre-existing system group, not a custom group to be created.
- The Odoo native behaviour for record rule resolution (multiple rules for the same model are combined with OR) is the mechanism relied upon to grant System Admin unrestricted access alongside existing business-role restrictions.
- The `SUPERUSER_ID` (uid=1, the `__system__` user) is never used for login; the System Admin in scope is uid=2 (`admin`) or any user added to `base.group_system`.
- Records with `noupdate="1"` in existing security files will be handled by placing the new System Admin rules in `noupdate="0"` blocks, ensuring they are applied on module upgrade without disrupting existing rules.
- This feature does not change authentication for the Odoo web interface itself — System Admins continue to log in via the standard Odoo login page.
- The REST API login block applies only to the application's custom login endpoint, not to Odoo's built-in web session mechanism.
- Rate limiting for repeated blocked System Admin API login attempts is delegated to Kong API Gateway (existing gateway-level policy); no application-level throttle is added by this feature.

---

## Dependencies

- Feature 019 (Goals and Results) — System Admin must see goals from all companies.
- Feature 021 (CMS Domain) — System Admin must see CMS pages and media from all companies.
- Feature 009 (User Onboarding) — System Admin must not appear in invitation authorization matrix.
- Feature 010 (Profile Unification) — System Admin must see profiles from all companies.
- ADR-008 (API Multi-Tenancy Security) — company isolation is mandatory for API; admin bypass is explicitly scoped to Odoo UI only.
- ADR-009 (Headless Authentication) — REST API login is for headless/business users only; System Admin is excluded.
- ADR-019 (RBAC Profiles) — defines the 9 business profiles; System Admin is above this hierarchy.
