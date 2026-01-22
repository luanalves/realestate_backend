# Feature Specification: RBAC User Profiles System

**Feature Branch**: `005-rbac-user-profiles`  
**Created**: 2026-01-19  
**Status**: Draft  
**Input**: User description: "Implement RBAC system with 9 predefined user profiles (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal User) in multi-tenancy environment with proper access controls and record rules"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner Onboards New Real Estate Company (Priority: P1)

A real estate company owner is onboarded to the system and needs to set up their company and start managing their team.

**Why this priority**: This is the foundation - without company setup and owner access, no other functionality can work. The owner is the first user who enables all other user stories.

**Independent Test**: Can be fully tested by creating a company record, assigning an owner user, and verifying the owner can log in and access all company data with full CRUD permissions.

**Acceptance Scenarios**:

1. **Given** a SaaS admin creates a new real estate company, **When** they create an owner user and link them via estate_company_ids, **Then** the owner can log in and sees full access to all company data
2. **Given** an owner is logged in, **When** they attempt to view properties, agents, contracts, and leads, **Then** they can view and modify all records belonging to their company
3. **Given** an owner from Company A, **When** they log in, **Then** they cannot see any data from Company B (multi-tenancy isolation)

---

### User Story 2 - Owner Creates Team Members with Different Roles (Priority: P1)

An owner needs to build their team by creating user accounts with appropriate access levels for different job functions.

**Why this priority**: Critical for the system to be usable - owners must delegate work to specialized team members. Without this, only owners could use the system.

**Independent Test**: Can be fully tested by having an owner create users with different profiles (Agent, Manager, Receptionist), and verifying each user sees only what their role permits.

**Acceptance Scenarios**:

1. **Given** an owner is logged in, **When** they create a new user and assign the "Real Estate Agent" profile, **Then** the user account is created with agent-level permissions
2. **Given** an owner creates multiple users with different profiles, **When** each user logs in, **Then** each sees different menus and data according to their assigned profile
3. **Given** an owner attempts to assign a user to their company, **When** saving the user record, **Then** the user's estate_company_ids includes the owner's company
4. **Given** an owner from Company A, **When** they try to create a user, **Then** they can only assign that user to Company A, not to other companies

---

### User Story 3 - Agent Manages Their Own Properties and Leads (Priority: P1)

A real estate agent needs to create, view, and manage properties they're assigned to, plus track their own leads.

**Why this priority**: Agents are the primary users who generate revenue. This is the core workflow for daily operations.

**Independent Test**: Can be fully tested by creating an agent user, having them create properties and leads, and verifying they can only access their own records.

**Acceptance Scenarios**:

1. **Given** an agent is logged in, **When** they create a new property, **Then** the property is automatically assigned to them as agent_id
2. **Given** an agent has 5 properties assigned to them, **When** they view the properties list, **Then** they see only their 5 properties, not properties of other agents
3. **Given** an agent is assigned to a lead, **When** they access the leads module, **Then** they can view and update that lead
4. **Given** an agent tries to modify a property assigned to another agent, **When** they search for that property, **Then** the property doesn't appear in their search results
5. **Given** an agent belongs to Company A, **When** they view properties, **Then** they only see properties from Company A, even if other properties exist in Company B

---

### User Story 4 - Manager Oversees All Company Operations (Priority: P2)

A manager needs visibility into all properties, agents, leads, and contracts across the company to manage operations.

**Why this priority**: Managers coordinate the team and handle operational decisions. Essential for scaling beyond a single agent, but the system can function with just owner and agents initially.

**Independent Test**: Can be fully tested by creating a manager user, creating properties/leads assigned to various agents, and verifying the manager sees all company data.

**Acceptance Scenarios**:

1. **Given** a manager is logged in, **When** they view the properties list, **Then** they see all properties from all agents in their company
2. **Given** a manager views leads, **When** they select a lead assigned to an agent, **Then** they can reassign it to a different agent
3. **Given** a manager tries to create a new user, **When** they access user management, **Then** they cannot create users (only owners can)
4. **Given** a manager generates a performance report, **When** the report runs, **Then** it includes data from all agents in their company
5. **Given** a manager from Company A, **When** they view dashboards, **Then** the data includes only Company A records, not other companies

---

### User Story 5 - Prospector Creates Properties with Commission Split (Priority: P2)

A prospector (property hunter) finds new properties and registers them, earning a commission that's split with the selling agent.

**Why this priority**: Important for specialized sales teams, but not all companies use prospectors. Can be added after core agent functionality works.

**Independent Test**: Can be fully tested by creating a prospector user, having them register a property, assigning a selling agent, and verifying commission split rules apply.

**Acceptance Scenarios**:

1. **Given** a prospector is logged in, **When** they create a new property, **Then** the property is saved with prospector_id set to their agent record
2. **Given** a prospector creates a property, **When** a manager assigns a selling agent to it, **Then** both prospector and agent are linked to the property
3. **Given** a property has both prospector and selling agent, **When** commission is calculated, **Then** the commission is split according to the configured rule (default 30% prospector, 70% agent)
4. **Given** a prospector views properties, **When** they access the properties list, **Then** they only see properties they prospected
5. **Given** a prospector tries to manage leads or sales, **When** they access those modules, **Then** they don't have access

---

### User Story 6 - Receptionist Manages Contracts and Keys (Priority: P3)

A receptionist handles administrative tasks like creating contracts, managing keys, and processing renewals.

**Why this priority**: Valuable for larger operations with administrative staff, but smaller teams can have agents/managers handle these tasks.

**Independent Test**: Can be fully tested by creating a receptionist user, creating contract and key records, and verifying they can view all properties but only edit contracts/keys.

**Acceptance Scenarios**:

1. **Given** a receptionist is logged in, **When** they create a new lease contract, **Then** the contract is saved with full access to edit
2. **Given** a receptionist views properties, **When** they open a property record, **Then** they can view all details but cannot edit property information
3. **Given** a receptionist manages keys, **When** they check out a key to a client, **Then** the key status is updated
4. **Given** a receptionist tries to edit agent commissions, **When** they access commission records, **Then** they cannot modify commission amounts
5. **Given** a receptionist views contracts, **When** filtering, **Then** they see all contracts from their company regardless of which agent created them

---

### User Story 7 - Financial Staff Processes Commissions (Priority: P3)

Financial staff need to calculate, review, and process commission payments to agents.

**Why this priority**: Important for payment processing, but can be manual initially. Agents can operate without automated commission processing.

**Independent Test**: Can be fully tested by creating a financial user, creating sale/lease records with commissions, and verifying they can view and process commission records.

**Acceptance Scenarios**:

1. **Given** financial staff is logged in, **When** they view commissions, **Then** they see all pending and paid commissions for their company
2. **Given** a commission record exists, **When** financial staff mark it as paid, **Then** the commission status updates
3. **Given** financial staff generates a commission report, **When** the report runs, **Then** it shows totals by agent with split commissions properly calculated
4. **Given** financial staff tries to edit a property, **When** they access properties, **Then** they can only view, not edit
5. **Given** financial staff views sales data, **When** filtering by date range, **Then** they see all sales from their company in that period

---

### User Story 8 - Legal Reviews Contracts (Priority: P3)

Legal staff need to review contracts for compliance and add legal opinions without modifying financial terms.

**Why this priority**: Useful for companies with in-house legal, but most can operate with external legal review. Nice-to-have for specialized teams.

**Independent Test**: Can be fully tested by creating a legal user, creating contract records, and verifying they can view all contracts and add notes but not edit terms.

**Acceptance Scenarios**:

1. **Given** legal staff is logged in, **When** they view contracts, **Then** they see all contracts from their company
2. **Given** legal staff reviews a contract, **When** they add a legal opinion/note, **Then** the note is saved on the contract record
3. **Given** legal staff tries to modify contract value, **When** they edit the contract, **Then** financial fields are read-only
4. **Given** legal staff reviews a property listing, **When** they access the property, **Then** they can view all details but cannot modify
5. **Given** legal staff searches contracts, **When** filtering by status, **Then** they can find all contracts needing legal review

---

### User Story 9 - Director Views Executive Dashboards (Priority: P3)

A director (executive) needs high-level business intelligence and executive reports without getting involved in daily operations.

**Why this priority**: Valuable for reporting to leadership, but operational users (agents, managers) are more critical for daily work.

**Independent Test**: Can be fully tested by creating a director user and verifying they have access to all data plus executive-level reports and dashboards.

**Acceptance Scenarios**:

1. **Given** a director is logged in, **When** they access the dashboard, **Then** they see executive metrics including sales volume, revenue, and team performance
2. **Given** a director generates a BI report, **When** the report runs, **Then** it includes consolidated data across all agents and properties
3. **Given** a director views all data, **When** browsing properties or contracts, **Then** they have the same visibility as managers plus additional financial insights
4. **Given** a director from Company A, **When** viewing metrics, **Then** all data is scoped to Company A only

---

### User Story 10 - Portal User Views Their Own Contracts (Priority: P3)

A client (buyer/renter) accesses a portal to view their contracts, upload documents, and track their transactions.

**Why this priority**: Enhances client experience but not critical for internal operations. The company can function by emailing documents to clients initially.

**Independent Test**: Can be fully tested by creating a portal user linked to a partner/client, creating contracts for that partner, and verifying they only see their own records.

**Acceptance Scenarios**:

1. **Given** a portal user is logged in, **When** they view contracts, **Then** they see only contracts where they are the client (partner_id matches)
2. **Given** a portal user uploads a document, **When** saving, **Then** the document is attached to their contract
3. **Given** a portal user tries to view other clients' contracts, **When** they search, **Then** they find no results
4. **Given** a portal user views a property listing, **When** accessing public listings, **Then** they can view property details but cannot see agent commission data
5. **Given** a portal user belongs to multiple contracts, **When** filtering, **Then** they can see all their contracts across different properties

---

### Edge Cases

- What happens when a user is assigned to multiple companies? They should see combined data from all companies they're linked to via estate_company_ids
- What happens when an owner tries to delete their own account? System should prevent deletion if they're the last owner for a company
- What happens when a manager tries to assign a lead to an agent from a different company? System should prevent cross-company assignments
- What happens when a property has both a prospector and selling agent, but the prospector leaves the company? Commission rules should still calculate correctly with archived prospector record
- What happens when a portal user is linked to a partner that doesn't have any contracts? They see an empty list with appropriate messaging
- What happens when an agent creates a property but is later reassigned to a different company? The property should remain with the original company, not move with the agent
- What happens when a financial user tries to modify a commission that's already been paid? System should prevent editing of paid commissions
- What happens when multiple roles are needed (e.g., someone who's both manager and agent)? User can have multiple group memberships via Odoo's native group system
- What happens when a user's profile is changed from Agent to Receptionist? Their permissions update immediately and they lose access to records they previously could edit
- What happens when commission split percentages aren't configured for prospector/agent split? System should use default values (30% prospector, 70% agent)

## Requirements *(mandatory)*

### Functional Requirements

**Profile Management**

- **FR-001**: System MUST provide exactly 9 predefined user profiles: Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, and Portal User
- **FR-002**: System MUST implement each profile using Odoo's native res.groups mechanism
- **FR-003**: System MUST follow naming convention group_real_estate_<role> for XML IDs to avoid module conflicts
- **FR-004**: System MUST allow users to be assigned to multiple profiles simultaneously
- **FR-005**: System MUST implement profile hierarchy where Director inherits Manager permissions, and Manager inherits base user permissions

**Multi-Tenancy & Data Isolation**

- **FR-006**: System MUST enforce data isolation between companies using estate_company_ids field on users
- **FR-007**: System MUST implement record rules that filter all data by user's estate_company_ids
- **FR-008**: Users MUST be able to belong to multiple companies and see combined data from all assigned companies
- **FR-009**: System MUST prevent users from accessing any data from companies they're not assigned to
- **FR-010**: System MUST scope all queries, reports, and dashboards to the user's assigned companies

**Owner Profile**

- **FR-011**: Owners MUST have full CRUD access to all records belonging to their assigned companies
- **FR-012**: Owners MUST be able to create and manage user accounts for their companies
- **FR-013**: Owners MUST be able to assign users to their companies via estate_company_ids
- **FR-014**: Owners MUST NOT be able to assign users to companies they don't own
- **FR-015**: System MUST allow multiple owners per company

**Director Profile**

- **FR-016**: Directors MUST have all Manager permissions plus access to executive dashboards
- **FR-017**: Directors MUST be able to view all financial reports including detailed commission breakdowns
- **FR-018**: Directors MUST have read-only access to business intelligence reports

**Manager Profile**

- **FR-019**: Managers MUST have CRUD access to properties, agents, contracts, and leads for their companies
- **FR-020**: Managers MUST be able to assign and reassign leads to agents within their companies
- **FR-021**: Managers MUST be able to generate performance reports for all agents in their companies
- **FR-022**: Managers MUST NOT be able to create or delete user accounts
- **FR-023**: Managers MUST be able to view all properties and leads across all agents in their companies

**Agent Profile**

- **FR-024**: Agents MUST be able to create properties that are automatically assigned to them
- **FR-025**: Agents MUST only see properties where they are listed as agent_id or in assignment_ids
- **FR-026**: Agents MUST be able to create and manage their own leads
- **FR-027**: Agents MUST be able to view leads assigned to them
- **FR-028**: Agents MUST NOT be able to modify commission amounts
- **FR-029**: Agents MUST be able to create proposals for properties they manage
- **FR-030**: Agents MUST NOT be able to change the client (partner) on proposals
- **FR-031**: Agents MUST be able to view property sale prices

**Prospector Profile**

- **FR-032**: Prospectors MUST be able to create new property records
- **FR-033**: System MUST automatically set prospector_id field when a prospector creates a property
- **FR-034**: Prospectors MUST only see properties they prospected
- **FR-035**: Prospectors MUST NOT have access to leads or sales modules
- **FR-036**: System MUST calculate commission split between prospector and selling agent when both are assigned
- **FR-037**: Commission split MUST default to 30% prospector and 70% selling agent if not configured otherwise
- **FR-038**: Prospectors MUST NOT be able to edit properties after creation (only view their prospected properties)

**Receptionist Profile**

- **FR-039**: Receptionists MUST have CRUD access to lease contracts
- **FR-040**: Receptionists MUST have CRUD access to key management records
- **FR-041**: Receptionists MUST be able to view all properties in their company (read-only)
- **FR-042**: Receptionists MUST NOT be able to edit property details, agent assignments, or prices
- **FR-043**: Receptionists MUST NOT be able to modify commissions
- **FR-044**: Receptionists MUST be able to process lease renewals
- **FR-045**: Receptionists MUST see all contracts regardless of which agent created them

**Financial Profile**

- **FR-046**: Financial users MUST be able to view all sales and leases in their company (read-only)
- **FR-047**: Financial users MUST have CRUD access to commission transaction records (real.estate.commission.transaction)
- **FR-048**: Financial users MUST be able to generate commission reports by agent, date range, and status
- **FR-049**: Financial users MUST be able to mark commissions as paid
- **FR-050**: Financial users MUST NOT be able to edit properties or leads
- **FR-051**: System MUST calculate split commissions correctly when generating commission records

**Legal Profile**

- **FR-052**: Legal users MUST be able to view all contracts in their company (read-only)
- **FR-053**: Legal users MUST be able to add notes and legal opinions to contracts
- **FR-054**: Legal users MUST NOT be able to modify contract financial terms (values, commissions, prices)
- **FR-055**: Legal users MUST NOT be able to edit properties beyond viewing
- **FR-056**: Legal users MUST be able to filter contracts by status for legal review workflows

**Portal User Profile**

- **FR-057**: Portal users MUST only see records where partner_id matches their linked partner
- **FR-058**: Portal users MUST be able to view their own contracts
- **FR-059**: Portal users MUST be able to upload documents to their contracts
- **FR-060**: Portal users MUST NOT see other clients' contracts or data
- **FR-061**: Portal users MUST be able to view property listings that are publicly available
- **FR-062**: Portal users MUST NOT see agent commission information on properties

**Security & Access Control**

- **FR-063**: System MUST implement all permissions using Odoo's record rules (ir.rule)
- **FR-064**: System MUST implement CRUD permissions using access control lists (ir.model.access.csv)
- **FR-065**: System MUST implement field-level security where needed (e.g., commission fields, prospector_id)
- **FR-066**: Record rules MUST always include company filtering via estate_company_ids
- **FR-067**: System MUST prevent privilege escalation by enforcing group hierarchies
- **FR-068**: Permissions MUST be enforced at the database/ORM level, not just UI level

**Data Model Extensions**

- **FR-069**: System MUST add prospector_id field to property model as Many2one to real.estate.agent
- **FR-070**: System MUST add commission_rule configuration for split percentage between prospector and agent
- **FR-071**: System MUST track prospector_id changes in property audit log
- **FR-072**: System MUST prevent direct editing of prospector_id field by non-managers

**Group Definitions**

- **FR-073**: Each profile MUST have a corresponding res.groups record with unique XML ID
- **FR-074**: Display names MUST follow format "Real Estate <Role>"
- **FR-075**: System MUST define group hierarchy using implied_ids (group inheritance)
- **FR-076**: Base group (group_real_estate_user) MUST inherit from base.group_user
- **FR-077**: Portal group (group_real_estate_portal_user) MUST inherit from base.group_portal

### Key Entities

- **User Profile (res.groups)**: Represents one of the 9 predefined roles (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal User). Contains permissions configuration and group hierarchy.

- **User (res.users)**: Represents a system user. Linked to one or more real estate companies via estate_company_ids. Can have multiple profile groups assigned. Determines what data the user can access.

- **Real Estate Company (thedevkitchen.estate.company)**: Represents a single real estate agency in the multi-tenancy system. Users are linked to companies via estate_company_ids. All data is scoped to companies.

- **Property (real.estate.property)**: Represents a real estate property listing. Has agent_id for the selling agent, prospector_id for the prospector (if applicable), and company_ids for multi-tenancy. Access is controlled by record rules based on user profile.

- **Agent (real.estate.agent)**: Represents a real estate agent. Linked to a user via user_id field. Used in agent_id and prospector_id references on properties.

- **Lead (crm.lead or custom)**: Represents a potential customer/sale. Assigned to specific agents. Agents can only see their own leads; managers can see all.

- **Lease Contract (real.estate.lease)**: Represents a rental agreement. Managed by receptionists and viewable by financial/legal staff. Linked to partner (client) for portal access.

- **Commission Transaction (real.estate.commission.transaction)**: Represents payment due to agents/prospectors. Managed by financial staff. Supports split commissions when both prospector and agent are involved.

- **Commission Rule (real.estate.commission.rule)**: Configuration for commission calculations including split percentages for prospector/agent scenarios. Default is 30% prospector, 70% agent.

- **Partner (res.partner)**: Represents clients (buyers/renters). Portal users are linked to partners and can only see data where partner_id matches their linked partner.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**User Management & Access Control**

- **SC-001**: Owners can create new users with any of the 9 profiles and assign them to their company in under 2 minutes
- **SC-002**: 100% of users can only access data from their assigned companies (zero cross-company data leaks)
- **SC-003**: Each of the 9 profiles correctly enforces permissions with zero unauthorized access incidents in testing

**Multi-Tenancy Isolation**

- **SC-004**: Users from Company A cannot see any records from Company B when browsing properties, leads, contracts, or any other data
- **SC-005**: System correctly shows combined data when a user is assigned to multiple companies
- **SC-006**: All reports, dashboards, and searches are automatically scoped to user's assigned companies

**Agent Operations**

- **SC-007**: Agents can create and view their own properties and leads without seeing other agents' data
- **SC-008**: Agents complete property creation in under 3 minutes
- **SC-009**: Agents attempting to access another agent's property see zero results

**Manager Operations**

- **SC-010**: Managers can view all properties and leads across all agents in their company
- **SC-011**: Managers can reassign leads between agents in under 1 minute
- **SC-012**: Manager dashboards load in under 3 seconds showing company-wide metrics

**Commission Processing**

- **SC-013**: System correctly calculates split commissions (30% prospector, 70% agent) when both are assigned to a property
- **SC-014**: Financial staff can process commission payments in under 2 minutes per commission
- **SC-015**: Commission reports accurately reflect all sales with proper splits for the selected period

**Role-Specific Access**

- **SC-016**: Receptionists can create/edit contracts but cannot modify property details or commissions
- **SC-017**: Legal staff can view all contracts and add notes but cannot modify financial terms
- **SC-018**: Prospectors can only see properties they prospected, not sales data or leads
- **SC-019**: Directors have access to all manager functionality plus executive reports

**Portal Access**

- **SC-020**: Portal users can only view their own contracts where they are the client
- **SC-021**: Portal users can upload documents to their contracts in under 2 minutes
- **SC-022**: Portal users attempting to view other clients' data see zero results

**System Performance & Reliability**

- **SC-023**: Permission checks complete in under 100ms per database query
- **SC-024**: System supports at least 50 concurrent users across 10 different companies without performance degradation
- **SC-025**: Role changes take effect immediately without requiring user logout/login

**Security & Compliance**

- **SC-026**: Zero privilege escalation vulnerabilities discovered during security testing
- **SC-027**: 100% of data access is enforced at ORM level (not just UI hiding)
- **SC-028**: All record rules correctly combine profile permissions with company filtering

**User Experience**

- **SC-029**: New users understand their access level and available actions within first 10 minutes of use
- **SC-030**: Users can complete their primary task (agents: add property, managers: reassign lead, financial: process commission) on first attempt with 90% success rate

## Assumptions *(mandatory)*

**System Context**

- **A-001**: This feature is being built for an Odoo 18.0 environment
- **A-002**: The base multi-tenancy system (estate_company_ids on users) is already implemented per ADR-008
- **A-003**: Existing models (property, agent, lead, contract) already have company_ids fields for multi-tenancy
- **A-004**: The thedevkitchen.estate.company model exists and is functional

**User Onboarding**

- **A-005**: SaaS administrators will manually create the first owner user for each new company
- **A-006**: Owners will be trained on how to create team members with appropriate profiles
- **A-007**: Users will receive credentials via email and complete first login without technical support

**Business Rules**

- **A-008**: Commission split default of 30% prospector / 70% agent is acceptable for all companies initially
- **A-009**: Companies will use predefined profiles without requesting customization during MVP phase
- **A-010**: Most users will have a single profile; multi-profile users are the exception
- **A-011**: Property ownership transfers between agents are rare edge cases that will be handled manually

**Security Model**

- **A-012**: Odoo's standard authentication mechanisms (session-based) are sufficient
- **A-013**: Field-level security via groups attribute in field definitions is acceptable
- **A-014**: Record rules will be evaluated on every database query per Odoo's standard behavior

**Data Model**

- **A-015**: The real.estate.agent model already exists and has a user_id field
- **A-016**: Properties can have either agent_id only, or both agent_id and prospector_id
- **A-017**: Commission records are created after a sale is finalized, not at property creation
- **A-018**: Partners (clients) are already created in res.partner before contract creation

**Performance**

- **A-019**: Initial deployment will support up to 10 companies with 50 total users
- **A-020**: Most companies will have 3-10 agents, 1-2 managers, and 1 owner
- **A-021**: Database queries with proper indexing on estate_company_ids and agent_id fields will perform adequately

**Future Flexibility**

- **A-022**: Phase 2 customization features (if implemented) will not require migration of existing permission structure
- **A-023**: Adding new profiles beyond the initial 9 is out of scope for Phase 1
- **A-024**: Profile permissions can be adjusted in code updates without requiring data migration

**External Dependencies**

- **A-025**: No external identity providers (LDAP, OAuth) are required; Odoo's built-in authentication is sufficient
- **A-026**: No third-party role management modules are needed for Phase 1
- **A-027**: Audit logging of permission changes will use Odoo's standard audit mechanisms

## Out of Scope *(mandatory)*

**Phase 2 Features**

- **OS-001**: Custom permission configuration per company (all companies use the same 9 profiles in Phase 1)
- **OS-002**: UI for owners to enable/disable specific menus or fields for profiles
- **OS-003**: Temporal permissions (roles with expiration dates)
- **OS-004**: Integration with OCA's base_user_role module
- **OS-005**: Dynamic role creation by end users

**Advanced RBAC Features**

- **OS-006**: Row-level security beyond company and agent assignment
- **OS-007**: Time-based access restrictions (e.g., access only during business hours)
- **OS-008**: Context-based permissions (e.g., different permissions for mobile vs web)
- **OS-009**: Delegation workflows (temporary permission grants)
- **OS-010**: Approval workflows for permission changes

**Additional User Types**

- **OS-011**: External partner/vendor access beyond portal users
- **OS-012**: Read-only auditor profile
- **OS-013**: System administrator profile (separate from owner)
- **OS-014**: Marketing specialist profile
- **OS-015**: Property photographer profile

**Commission Features**

- **OS-016**: Complex commission formulas beyond simple percentage splits
- **OS-017**: Multi-tier commission splits (more than 2 agents)
- **OS-018**: Commission overrides or manual adjustments
- **OS-019**: Commission approvals workflow
- **OS-020**: Historical commission rule changes and versioning

**Advanced Multi-Tenancy**

- **OS-021**: Cross-company data sharing or partnerships
- **OS-022**: Company hierarchies (parent/child company relationships)
- **OS-023**: Franchise or white-label company types
- **OS-024**: Company-specific branding or configuration

**Integration Features**

- **OS-025**: SSO integration (SAML, OAuth2, LDAP)
- **OS-026**: Active Directory synchronization
- **OS-027**: External RBAC system integration
- **OS-028**: API-based permission management

**Reporting & Analytics**

- **OS-029**: Advanced BI dashboards beyond what's needed for Director profile
- **OS-030**: Custom report builder for end users
- **OS-031**: Permission audit reports
- **OS-032**: User activity tracking and analytics

**UI Customization**

- **OS-033**: Per-user UI customization (custom dashboards, layouts)
- **OS-034**: Profile-specific themes or branding
- **OS-035**: Configurable menu structures per profile

## Dependencies *(mandatory)*

**Existing System Components**

- **D-001**: Multi-tenancy infrastructure with estate_company_ids field on res.users (ADR-008)
- **D-002**: thedevkitchen.estate.company model is implemented and functional
- **D-003**: real.estate.property model with company_ids field for multi-tenancy
- **D-004**: real.estate.agent model with user_id field linking agents to users
- **D-005**: CRM leads module or equivalent for lead management

**Odoo Framework**

- **D-006**: Odoo 18.0 platform with standard security framework (res.groups, ir.rule, ir.model.access)
- **D-007**: Odoo base module with base.group_user and base.group_portal
- **D-008**: Odoo ORM with record rule evaluation on all database queries

**Data Model Changes Required**

- **D-009**: Addition of prospector_id field to real.estate.property model (Many2one to real.estate.agent)
- **D-010**: Commission rule configuration model for split percentages
- **D-011**: Commission tracking model (if not already exists) for financial processing

**Security Infrastructure**

- **D-012**: XML data files for group definitions (security/groups.xml)
- **D-013**: CSV file for access control lists (security/ir.model.access.csv)
- **D-014**: XML file for record rules (security/record_rules.xml)

**Testing Infrastructure**

- **D-015**: Test data sets for multiple companies
- **D-016**: Test users with each of the 9 profiles
- **D-017**: Test framework for security/permission verification

**Documentation**

- **D-018**: ADR-008 (API Security Multi-Tenancy) for multi-tenancy patterns
- **D-019**: ADR-003 (Mandatory Test Coverage) for testing standards

**Deployment Requirements**

- **D-020**: Ability to load security XML files before any data migrations
- **D-021**: Database migration scripts for adding prospector_id field
- **D-022**: Seed data for creating default groups on fresh installations

## Notes *(optional)*

**Design Decisions Rationale**

This feature implements the decisions documented in ADR-019 (RBAC User Profiles in Multi-Tenancy). The two-phase approach balances time-to-market with future flexibility:

- **Phase 1 (This Spec)**: Predefined profiles using Odoo's native group system. Fast to implement, well-tested, and secure.
- **Phase 2 (Future)**: Conditional customization layer if market demand validates the need. Will not require rewriting Phase 1 code.

**Why 9 Specific Profiles?**

These profiles were identified through analysis of real estate company organizational structures:
- **Administrative tier** (Owner, Director, Manager): Strategic and operational leadership
- **Operational tier** (Agent, Prospector, Receptionist, Financial, Legal): Specialized daily operations
- **External tier** (Portal User): Client self-service

This covers the spectrum from C-level executives to frontline staff to external clients.

**Multi-Tenancy Strategy**

Every record rule includes company filtering via `estate_company_ids`. This ensures:
- Complete data isolation between companies
- Support for users belonging to multiple companies (consolidated view)
- Compliance with ADR-008 security requirements

**Commission Split Innovation**

The prospector/agent split commission model addresses a common real estate business practice where one person finds the property (prospector) and another sells it (agent). The 30/70 split is industry-standard but configurable.

**Group Naming Convention**

Using `group_real_estate_<role>` instead of `group_<role>` prevents namespace collisions. For example, `group_manager` could conflict with Odoo's built-in groups or other modules. The `real_estate_` prefix makes it explicit these groups belong to the real estate module.

**Security at ORM Level**

All permissions are enforced by Odoo's ORM (record rules and ACLs), not by hiding UI elements. This prevents:
- API bypass attacks
- Direct database manipulation
- RPC call exploits
Even if a user crafts a direct API request, the ORM will block unauthorized access.

**Portal User Isolation**

Portal users use `partner_id` filtering instead of `estate_company_ids` because they're external to the company. A client may do business with multiple companies and should only see their own contracts regardless of which company created them.

**No Custom Permission UI in Phase 1**

Providing a UI for customizing permissions is tempting but risky without market validation:
- Increases complexity and testing scope
- Delays launch
- May build functionality that users don't actually need
- Could create security vulnerabilities if not properly constrained

Phase 1 validates whether the predefined profiles meet market needs. Phase 2 can add customization only if demonstrated necessary.

**Performance Considerations**

Record rules are evaluated on every query, which could impact performance at scale. Mitigation strategies:
- Proper database indexing on `estate_company_ids`, `agent_id`, `prospector_id`, and `partner_id`
- Caching of group memberships
- Query optimization to combine multiple rules efficiently
- Monitoring query performance in production

Expected load (10 companies, 50 users) is well within Odoo's performance capabilities with proper indexing.

**Migration Path**

If companies are already using the system without these profiles:
1. Create all 9 groups via XML data load
2. Assign existing users to appropriate groups based on their current access patterns
3. Apply record rules (this may restrict some users' access - requires communication)
4. Audit to ensure no users lost critical access

For greenfield deployments, groups are created during module installation.

**Testing Strategy**

Per ADR-003 (Mandatory Test Coverage), comprehensive tests must cover:
- Each profile's positive permissions (can access what they should)
- Each profile's negative permissions (cannot access what they shouldn't)
- Multi-tenancy isolation (Company A users can't see Company B data)
- Edge cases (multi-company users, multi-profile users)
- Commission split calculations
- Group hierarchy inheritance

**Alignment with ADR-019**

This specification directly implements the decisions in ADR-019:
- Uses Odoo's native `res.groups` (not `base_user_role`)
- Defines exactly 9 profiles as documented
- Implements company-based record rules
- Defers UI customization to Phase 2
- Uses the specified naming conventions
- Follows the group hierarchy structure

**Future Extensibility**

While Phase 1 uses fixed profiles, the architecture supports future expansion:
- Group hierarchy allows adding new profiles that inherit from existing ones
- Record rules can be refined without breaking existing logic
- Field-level security can be added incrementally
- Commission calculation is abstracted to support future formula complexity

The key design principle: Build the simplest thing that works, with clean extension points for future needs.
