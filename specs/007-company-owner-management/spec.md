# Feature Specification: Company & Owner Management System

**Feature Branch**: `007-company-owner-management`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Implementar sistema de gerenciamento de Imobiliárias (Company) e Proprietários (Owner) com CRUD completo via API REST e interface Odoo Web, seguindo regras RBAC definidas na ADR-019. Owners podem criar novas imobiliárias e gerenciar outros Owners de suas empresas. SaaS Admin tem controle total via interface administrativa."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner CRUD via Independent API (Priority: P1) 🎯 MVP

An existing Owner or SaaS Admin needs to create, manage, and link Owners to companies. Owners are created independently (without company) and then linked to one or more companies via a separate endpoint. This enables flexible owner management where the same Owner can be associated with multiple companies.

**Why this priority**: Owner management is the foundation for all business operations. Without Owners, no one can manage companies, properties, or agents. This is the entry point for the entire platform.

**Independent Test**: Can be fully tested by: (1) Creating Owner via POST /api/v1/owners, (2) Linking to company via POST /api/v1/owners/{id}/companies, (3) Verifying Owner can access the linked company.

**Acceptance Scenarios**:

1. **Given** authenticated Owner/Admin, **When** they send POST /api/v1/owners with valid name, email, password, **Then** new user is created with group_real_estate_owner and NO company links (estate_company_ids = [])
2. **Given** authenticated Owner/Admin, **When** they send POST /api/v1/owners without required fields, **Then** they receive 400 error with validation details
3. **Given** authenticated Owner/Admin, **When** they send POST /api/v1/owners with email already in use, **Then** they receive 409 conflict error
4. **Given** Owner exists without company, **When** they send POST /api/v1/owners/{id}/companies with valid company_id, **Then** Owner's estate_company_ids is updated to include the company
5. **Given** Owner linked to Company A, **When** user tries to remove last Owner link from Company A, **Then** system blocks with error "Cannot remove last active owner from company"
6. **Given** Owner linked to multiple companies, **When** they call GET /api/v1/owners, **Then** they see all Owners from all their companies

---

### User Story 2 - Owner Creates New Real Estate Company (Priority: P1) 🎯 MVP

An existing Owner wants to create a new real estate company to expand their business. They access the API to register a new company with valid CNPJ and business information. Upon creation, they are automatically linked to the new company.

**Why this priority**: After Owner exists, they need to create/manage companies. This enables platform growth and multi-company scenarios.

**Independent Test**: Can be fully tested by authenticating as an Owner, sending POST /api/v1/companies with valid data, and verifying the company is created with the Owner automatically linked via estate_company_ids.

**Acceptance Scenarios**:

1. **Given** Owner is authenticated via JWT+Session, **When** they send POST /api/v1/companies with valid name and CNPJ, **Then** new company is created and Owner's estate_company_ids is updated to include the new company
2. **Given** Owner is authenticated, **When** they send POST /api/v1/companies without required name field, **Then** they receive 400 error with clear validation message
3. **Given** Owner is authenticated, **When** they send POST /api/v1/companies with invalid CNPJ format, **Then** they receive 400 error with CNPJ validation message
4. **Given** Owner is authenticated, **When** they send POST /api/v1/companies with CNPJ already in use, **Then** they receive 409 conflict error
5. **Given** Owner from Company A, **When** they create new Company B, **Then** no data from Company A is affected (multi-tenancy isolation)

---

---

### User Story 3 - SaaS Admin Manages Any Company and Owner (Priority: P1) 🎯 MVP

The SaaS Admin (platform operator) needs full administrative control over all companies and owners via the Odoo Web interface. They can create companies without being an Owner, manage any Owner, and provide support to all tenants.

**Why this priority**: Critical for platform operations, customer support, and administrative oversight. Without this, the platform cannot be managed effectively.

**Independent Test**: Can be fully tested by logging into Odoo Web as admin, accessing Real Estate > Companies menu, creating a new company, and creating an Owner for any company.

**Acceptance Scenarios**:

1. **Given** SaaS Admin logged into Odoo Web, **When** they access menu "Real Estate > Companies", **Then** they see all companies in the system
2. **Given** SaaS Admin, **When** they create a new Company via Odoo form, **Then** company is created even without an existing Owner
3. **Given** SaaS Admin, **When** they create an Owner for any Company, **Then** Owner receives correct group and company linkage
4. **Given** SaaS Admin, **When** they edit any Owner, **Then** changes are saved without restriction
5. **Given** SaaS Admin, **When** they view Users list, **Then** they can filter by "Estate Owners" group

---

### User Story 4 - Director/Manager Views Company Information (Priority: P2)

Directors and Managers need to view their company's information for reference, but cannot modify company settings or manage Owners. They have read-only access to company data.

**Why this priority**: Important for operational visibility but not blocking for core functionality. System works without this initially.

**Independent Test**: Can be fully tested by authenticating as Manager, calling GET /api/v1/companies, verifying they see only their companies, and verifying POST/PUT/DELETE return 403.

**Acceptance Scenarios**:

1. **Given** Director/Manager is authenticated, **When** they call GET /api/v1/companies, **Then** they see only companies in their estate_company_ids
2. **Given** Director/Manager, **When** they call POST /api/v1/companies, **Then** they receive 403 Forbidden
3. **Given** Director/Manager, **When** they call PUT /api/v1/companies/{id}, **Then** they receive 403 Forbidden
4. **Given** Director/Manager, **When** they call GET /api/v1/companies/{id}/owners, **Then** they receive 403 Forbidden

---

### User Story 5 - New User Self-Registers as Owner (Priority: P2)

A new user signs up for the platform via API and becomes an Owner. They must then create their first company to start using the system. This enables self-service onboarding.

**Why this priority**: Enables growth through self-service but requires User Story 1 to be complete first.

**Independent Test**: Can be fully tested by calling registration endpoint, logging in as the new Owner, and creating the first company.

**Acceptance Scenarios**:

1. **Given** new user without account, **When** they call POST /api/v1/auth/register with valid data, **Then** user is created with group_real_estate_owner
2. **Given** new Owner without company, **When** they log in, **Then** they are prompted to create their first company
3. **Given** new Owner, **When** they create first company, **Then** they are automatically linked to it
4. **Given** new Owner without company, **When** they try to access other resources, **Then** they receive guidance to create company first

---

### Edge Cases

- **Company without Owner**: What happens if SaaS Admin creates company without owner? → Allowed, company remains "orphan" until admin creates owner
- **Owner with multiple companies**: Can Owner manage multiple companies? → Yes, via estate_company_ids (Many2many relationship)
- **Last Owner deletion**: What happens when trying to delete last active Owner? → System blocks with clear error message
- **Duplicate CNPJ**: Same CNPJ in two companies? → Blocked, CNPJ is unique in system (includes soft-deleted)
- **Owner self-removal**: Can Owner remove themselves? → No if last active; Yes if other Owners exist
- **Company without CNPJ**: Is CNPJ required? → Not required for creation, but recommended (system shows warning)
- **Duplicate email in Owners**: Two Owners with same email? → Blocked via unique constraint on res.users.login
- **Company transfer**: Can Owner transfer company to another Owner? → Not via API, only via SaaS Admin interface
- **Inactive Owner login**: What happens when deactivated Owner tries to log in? → Standard Odoo inactive user handling (login blocked)
- **CRECI validation**: Is CRECI validated? → Format validation per state if provided, but not required

## Requirements *(mandatory)*

### Functional Requirements

#### Owner CRUD API (Independent - Priority P1)

- **FR-001**: System MUST expose endpoint `POST /api/v1/owners` for creating Owners (without company)
- **FR-002**: System MUST expose endpoint `GET /api/v1/owners` for listing Owners (from all user's companies)
- **FR-003**: System MUST expose endpoint `GET /api/v1/owners/{id}` for Owner details
- **FR-004**: System MUST expose endpoint `PUT /api/v1/owners/{id}` for updating Owner
- **FR-005**: System MUST expose endpoint `DELETE /api/v1/owners/{id}` for soft delete (sets active=False)
- **FR-006**: System MUST expose endpoint `POST /api/v1/owners/{id}/companies` for linking Owner to company
- **FR-007**: System MUST expose endpoint `DELETE /api/v1/owners/{id}/companies/{company_id}` for unlinking Owner from company
- **FR-008**: When creating Owner, system MUST automatically assign group_real_estate_owner
- **FR-009**: Owner created via API starts with empty estate_company_ids (no company links)
- **FR-010**: All Owner endpoints MUST use @require_jwt, @require_session decorators. Exception: `POST /api/v1/owners` and `GET /api/v1/owners` may omit @require_company when Owner has no company links (document with `# no company context required`)

#### Company CRUD API (Priority P1)

- **FR-011**: System MUST expose endpoint `POST /api/v1/companies` for creating real estate companies
- **FR-012**: System MUST expose endpoint `GET /api/v1/companies` for listing companies (filtered by user access)
- **FR-013**: System MUST expose endpoint `GET /api/v1/companies/{id}` for company details
- **FR-014**: System MUST expose endpoint `PUT /api/v1/companies/{id}` for updating company
- **FR-015**: System MUST expose endpoint `DELETE /api/v1/companies/{id}` for soft delete (sets active=False)
- **FR-016**: When creating Company via API, system MUST auto-add to creator's estate_company_ids
- **FR-017**: All Company endpoints MUST use @require_jwt, @require_session, @require_company decorators

#### RBAC Enforcement

- **FR-018**: Only group_real_estate_owner and base.group_system can create Owners
- **FR-019**: Only group_real_estate_owner and base.group_system can create Companies
- **FR-020**: Owner can only link/unlink Owners to/from their own companies
- **FR-021**: Director and Manager MUST have read-only access to Companies
- **FR-022**: Agent, Prospector, Receptionist MUST NOT have access to Owner endpoints

#### Company Validations

- **FR-023**: Field `name` MUST be required (max 255 characters)
- **FR-024**: Field `cnpj` MUST validate Brazilian format (XX.XXX.XXX/XXXX-XX) and check digits
- **FR-025**: Field `cnpj` MUST be unique in system (including soft-deleted records)
- **FR-026**: Field `email` MUST validate email format when provided
- **FR-027**: Field `creci` MUST validate format per Brazilian state when provided

#### Owner Validations

- **FR-028**: Field `name` MUST be required for Owner creation
- **FR-029**: Field `email` (login) MUST be required and unique
- **FR-030**: Field `password` MUST be required on creation (minimum 8 characters)
- **FR-031**: System MUST prevent removal of last active Owner link from a company

#### Odoo Web Views

- **FR-032**: System MUST provide form view for Company (create/edit)
- **FR-033**: System MUST provide list view for Company with columns: name, cnpj, email, phone, agent_count, property_count
- **FR-034**: System MUST create action `action_company` referenced in menu
- **FR-035**: System MUST provide view to list/create Owners of a Company (action button on form)
- **FR-036**: Views MUST respect security groups (Owner and Admin see CRUD, others read-only)

#### Multi-Tenancy

- **FR-037**: Owner MUST only access companies in their estate_company_ids
- **FR-038**: Owner can only link/unlink Owners to/from companies in their estate_company_ids
- **FR-039**: Endpoints MUST return 404 (not 403) for inaccessible resources
- **FR-040**: GET /api/v1/owners returns Owners from all companies the user has access to

### Key Entities

- **Company (thedevkitchen.estate.company)**: Represents a real estate agency. Contains business information (name, CNPJ, CRECI, address), contact details, and computed statistics (property_count, agent_count). Linked to Users via estate_company_ids Many2many relationship.

- **Owner**: Not a separate model - Owner is a role assigned to res.users via group_real_estate_owner group. Identified by user having the Owner group membership. One User can be Owner of multiple companies (via estate_company_ids). An Owner can exist without any company links initially.

## Clarifications

### Session 2026-02-05

- Q: Rate limiting specification - should these endpoints have specific rate limits? → A: Rate limiting is responsibility of the global API Gateway - not included in this feature scope
- Q: Owner-Company architecture - nested or independent? → A: Independent. Owner created via `/api/v1/owners` (no company required), then linked via `/api/v1/owners/{id}/companies`
- Q: Who can create Owners? → A: Both Owner (for their companies) and SaaS Admin (any company)
- Q: GET /api/v1/owners returns what? → A: All Owners from all companies the user has access to

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Owner can be created without company in under 30 seconds
- **SC-002**: Owner can be linked to company in under 30 seconds
- **SC-003**: Owner can create a new company with complete information in under 2 minutes
- **SC-004**: Zero data leakage between companies - Owners from Company A cannot view, edit, or access any data from Company B under any circumstances
- **SC-005**: SaaS Admin can view and manage any company/owner via Odoo Web interface within 3 clicks from main menu
- **SC-006**: All RBAC rules enforced correctly - unauthorized operations return appropriate error codes (403 for forbidden, 404 for not found/inaccessible)
- **SC-007**: Last Owner protection works 100% of the time - system never allows removal of the last active Owner
- **SC-008**: CNPJ validation catches 100% of invalid CNPJs (format and check digit validation)
