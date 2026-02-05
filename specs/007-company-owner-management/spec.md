# Feature Specification: Company & Owner Management System

**Feature Branch**: `007-company-owner-management`  
**Created**: 2026-02-05  
**Status**: Draft  
**Input**: User description: "Implementar sistema de gerenciamento de Imobiliárias (Company) e Proprietários (Owner) com CRUD completo via API REST e interface Odoo Web, seguindo regras RBAC definidas na ADR-019. Owners podem criar novas imobiliárias e gerenciar outros Owners de suas empresas. SaaS Admin tem controle total via interface administrativa."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner Creates New Real Estate Company (Priority: P1) 🎯 MVP

An existing Owner wants to create a new real estate company to expand their business. They access the API to register a new company with valid CNPJ and business information. Upon creation, they are automatically linked to the new company.

**Why this priority**: This is the foundational flow - without the ability to create companies, the entire platform cannot onboard new real estate agencies. Owners expanding their business need this capability to manage multiple companies.

**Independent Test**: Can be fully tested by authenticating as an Owner, sending POST /api/v1/companies with valid data, and verifying the company is created with the Owner automatically linked via estate_company_ids.

**Acceptance Scenarios**:

1. **Given** Owner is authenticated via JWT+Session, **When** they send POST /api/v1/companies with valid name and CNPJ, **Then** new company is created and Owner's estate_company_ids is updated to include the new company
2. **Given** Owner is authenticated, **When** they send POST /api/v1/companies without required name field, **Then** they receive 400 error with clear validation message
3. **Given** Owner is authenticated, **When** they send POST /api/v1/companies with invalid CNPJ format, **Then** they receive 400 error with CNPJ validation message
4. **Given** Owner is authenticated, **When** they send POST /api/v1/companies with CNPJ already in use, **Then** they receive 409 conflict error
5. **Given** Owner from Company A, **When** they create new Company B, **Then** no data from Company A is affected (multi-tenancy isolation)

---

### User Story 2 - Owner Manages Other Owners Within Same Company (Priority: P1) 🎯 MVP

An Owner needs to add business partners or delegates as additional Owners of their company. They can create, edit, and remove other Owners, but only within companies they own. The system prevents removal of the last active Owner.

**Why this priority**: Essential for business delegation and partnership scenarios. Real estate agencies often have multiple partners who need Owner-level access.

**Independent Test**: Can be fully tested by authenticating as Owner of Company A, creating a new Owner for Company A, verifying the new Owner can log in with full access, and verifying the original Owner cannot create Owners for Company B (which they don't own).

**Acceptance Scenarios**:

1. **Given** Owner of Company A, **When** they send POST /api/v1/companies/A/owners with valid user data, **Then** new user is created with group_real_estate_owner and estate_company_ids = [Company A]
2. **Given** Owner of Company A, **When** they try to create Owner for Company B (not theirs), **Then** they receive 403 Forbidden error
3. **Given** Owner, **When** they edit another Owner of the same company, **Then** they can update name, email, and password
4. **Given** Owner, **When** they remove another Owner (soft delete), **Then** Owner becomes inactive but data is preserved
5. **Given** Company has only one active Owner, **When** that Owner tries to delete themselves, **Then** system blocks with error "Cannot remove last active owner"
6. **Given** newly created Owner, **When** they log in, **Then** they have full access to the company

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

#### Company CRUD API

- **FR-001**: System MUST expose endpoint `POST /api/v1/companies` for creating real estate companies
- **FR-002**: System MUST expose endpoint `GET /api/v1/companies` for listing companies (filtered by user access)
- **FR-003**: System MUST expose endpoint `GET /api/v1/companies/{id}` for company details
- **FR-004**: System MUST expose endpoint `PUT /api/v1/companies/{id}` for updating company
- **FR-005**: System MUST expose endpoint `DELETE /api/v1/companies/{id}` for soft delete (sets active=False)
- **FR-006**: All Company endpoints MUST use @require_jwt, @require_session, @require_company decorators

#### Owner CRUD API

- **FR-007**: System MUST expose endpoint `POST /api/v1/companies/{company_id}/owners` for creating Owners
- **FR-008**: System MUST expose endpoint `GET /api/v1/companies/{company_id}/owners` for listing company Owners
- **FR-009**: System MUST expose endpoint `GET /api/v1/companies/{company_id}/owners/{owner_id}` for Owner details
- **FR-010**: System MUST expose endpoint `PUT /api/v1/companies/{company_id}/owners/{owner_id}` for updating Owner
- **FR-011**: System MUST expose endpoint `DELETE /api/v1/companies/{company_id}/owners/{owner_id}` for soft delete
- **FR-012**: When creating Owner, system MUST automatically assign group_real_estate_owner
- **FR-013**: When creating Owner, system MUST add company_id to user's estate_company_ids

#### RBAC Enforcement

- **FR-014**: Only group_real_estate_owner and base.group_system can create Companies
- **FR-015**: Only group_real_estate_owner (of target company) and base.group_system can create/manage Owners
- **FR-016**: Owner MUST only create/edit/remove Owners of their own companies
- **FR-017**: Director and Manager MUST have read-only access to Companies
- **FR-018**: Agent, Prospector, Receptionist MUST NOT have access to Owner endpoints

#### Company Validations

- **FR-019**: Field `name` MUST be required (max 255 characters)
- **FR-020**: Field `cnpj` MUST validate Brazilian format (XX.XXX.XXX/XXXX-XX) and check digits
- **FR-021**: Field `cnpj` MUST be unique in system (including soft-deleted records)
- **FR-022**: Field `email` MUST validate email format when provided
- **FR-023**: Field `creci` MUST validate format per Brazilian state when provided

#### Owner Validations

- **FR-024**: Field `name` MUST be required for Owner creation
- **FR-025**: Field `email` (login) MUST be required and unique
- **FR-026**: Field `password` MUST be required on creation (minimum 8 characters)
- **FR-027**: System MUST prevent removal of last active Owner of a company

#### Odoo Web Views

- **FR-028**: System MUST provide form view for Company (create/edit)
- **FR-029**: System MUST provide list view for Company with columns: name, cnpj, email, phone, agent_count, property_count
- **FR-030**: System MUST create action `action_company` referenced in menu
- **FR-031**: System MUST provide view to list/create Owners of a Company (action button on form)
- **FR-032**: Views MUST respect security groups (Owner and Admin see CRUD, others read-only)

#### Multi-Tenancy

- **FR-033**: Owner MUST only access companies in their estate_company_ids
- **FR-034**: Owner MUST only create Owners for companies in their estate_company_ids
- **FR-035**: Endpoints MUST return 404 (not 403) for inaccessible companies
- **FR-036**: When creating Company via API, system MUST auto-add to creator's estate_company_ids

### Key Entities

- **Company (thedevkitchen.estate.company)**: Represents a real estate agency. Contains business information (name, CNPJ, CRECI, address), contact details, and computed statistics (property_count, agent_count). Linked to Users via estate_company_ids Many2many relationship.

- **Owner**: Not a separate model - Owner is a role assigned to res.users via group_real_estate_owner group. Identified by user having both the Owner group membership AND estate_company_ids containing the target company. One User can be Owner of multiple companies.

## Clarifications

### Session 2026-02-05

- Q: Rate limiting specification - should these endpoints have specific rate limits? → A: Rate limiting is responsibility of the global API Gateway - not included in this feature scope

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Owner can create a new company with complete information in under 2 minutes from API call to confirmation
- **SC-002**: Owner can add a new Owner to their company in under 1 minute
- **SC-003**: Zero data leakage between companies - Owners from Company A cannot view, edit, or access any data from Company B under any circumstances
- **SC-004**: SaaS Admin can view and manage any company/owner via Odoo Web interface within 3 clicks from main menu
- **SC-005**: All RBAC rules enforced correctly - unauthorized operations return appropriate error codes (403 for forbidden, 404 for not found/inaccessible)
- **SC-006**: Last Owner protection works 100% of the time - system never allows removal of the last active Owner
- **SC-007**: CNPJ validation catches 100% of invalid CNPJs (format and check digit validation)
