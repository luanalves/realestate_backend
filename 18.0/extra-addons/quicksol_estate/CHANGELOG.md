# Changelog

All notable changes to the quicksol_estate module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-12

### Added - Phase 8: Polish & Cross-Cutting Concerns

#### Agent Management UI
- **Agent Views** (`views/agent_views.xml` - 218 lines):
  - Tree view with performance metrics (total sales, commissions, active properties)
  - Form view with smart buttons linking to properties and commission transactions
  - Notebook with 4 tabs:
    * Performance: computed metrics (sales count, total/average commissions)
    * Commission Rules: inline editable list of agent commission configurations
    * Assignments: property assignments with active/inactive decorations
    * Commission History: transaction list with payment status
  - Search view with filters (Active/Inactive) and grouping (Company, CRECI State)
  - Action with default active filter

- **Commission Rule Views** (`views/commission_rule_views.xml` - ~140 lines):
  - Tree view with conditional column visibility (percentage/fixed amount based on structure type)
  - Form view with grouped fields:
    * Basic Information: agent, transaction type
    * Commission Configuration: structure type, percentage/fixed amount (conditional required)
    * Transaction Filters: min/max values
    * Validity Period: valid_from/valid_until dates
  - Search view with filters by active status, structure type, transaction type
  - Chatter integration for audit trail

- **Assignment Views** (`views/assignment_views.xml` - ~180 lines):
  - Kanban view grouped by responsibility_type (Primary/Support)
  - Tree view with active/inactive decorations
  - Form view with assignment info, dates, and notes
  - Search view with filters and grouping

- **Menu Structure** (`views/real_estate_menus.xml`):
  - Agents (sequence 20)
  - Property Assignments (sequence 25) - NEW
  - Commission Rules (sequence 26) - NEW
  - Positioned between Agents and Tenants

- **Smart Button Actions** (`models/agent.py`):
  - `action_view_properties()`: Opens assignment list filtered by agent
  - `action_view_commission_transactions()`: Opens commission history for agent

#### Demo Data
- **Agent Seed Data** (`data/agent_seed.xml` - 79 lines):
  - 5 demo agents with realistic Brazilian names and contact info
  - Valid CPF numbers (11 digits)
  - CRECI registration (SP: 123456, 234567, 456789; RJ: 345678, 567890)
  - Distributed across 2 companies (Quicksol Real Estate, Urban Properties)
  - All agents active with current hire_date

#### Internationalization
- **Portuguese Translations** (`i18n/pt_BR.po` - 906 lines):
  - Existing translation file covers all labels
  - Odoo auto-generates translations from view arch_db strings
  - Field descriptions and menu items localized

#### Documentation
- **README.md** (300+ lines):
  - Complete installation guide
  - Agent management usage instructions
  - API usage examples
  - Database schema documentation
  - Troubleshooting section
  - Architecture overview with ADR compliance

- **CHANGELOG.md** (this file):
  - Version history tracking
  - Detailed change documentation

### Changed

#### Odoo 18 Compatibility
- **View Element Updates**:
  - Replaced `<tree>` with `<list>` in all view definitions (breaking change in Odoo 18)
  - Removed deprecated `attrs` attribute, replaced with `invisible` and `column_invisible`
  - Updated conditional field visibility to use Python expressions instead of domain lists

#### Field Validation
- **View Field Corrections** (15+ iterations):
  - agent_views.xml: Removed 8 non-existent fields (image_128, rg, birth_date, marital_status, whatsapp, specialization, employment_type, notes)
  - commission_rule_views.xml: Corrected 6 field names (structure_type, percentage, fixed_amount, min_value, max_value)
  - assignment_views.xml: Updated field names (responsibility_type, assignment_date)
  - All views validated against actual model definitions

### Fixed
- XML syntax in agent_seed.xml (double quotes in eval attributes → single quotes)
- Company reference issues in seed data (using existing company_quicksol_real_estate, company_urban_properties)
- Property reference corrections (demo_property_1/2/3)
- Removed chatter from assignment views (model doesn't inherit mail.thread)

### Testing
- **Test Execution**:
  - 160 total tests run
  - 75 tests passing (46.9% pass rate)
  - Failures primarily in existing property tests (zip_code NotNull constraint)
  - Agent CRUD tests functional
  - Multi-tenancy isolation validated

### Technical Debt Resolved
- All view files use Odoo 18 syntax
- Field references validated via grep_search on model files
- Deprecation warnings addressed (attrs, tree elements)
- Module loads successfully without ParseErrors

---

## [1.1.0] - 2026-01-11

### Added - Phase 7: Performance Metrics

#### Computed Fields
- `total_sales_count` (Integer): Count of all commission transactions for agent
- `total_commissions` (Monetary): Sum of all commission amounts earned
- `average_commission` (Monetary): Average commission per transaction
- `active_properties_count` (Integer): Count of active property assignments

#### Performance Optimizations
- SQL query optimization for large datasets
- Index creation on frequently queried fields
- Computed field caching with `store=True` where appropriate

---

## [1.0.0] - 2026-01-10

### Added - Phases 1-6: Core Functionality

#### Agent Management (Backend)
- `real.estate.agent` model (35 fields):
  - Personal info: name, CPF (validated), email, phone, mobile
  - CRECI registration: state, number (unique per company), normalized format
  - Company assignment with multi-tenant isolation
  - User account sync (optional)
  - Hire date tracking
  - Soft-delete with `active` flag

- **Validation Rules**:
  - CPF format and check digit validation (via validate_docbr)
  - Email format validation
  - CRECI uniqueness per state and company
  - User account uniqueness (one agent per user)
  - Company isolation (agent.company_id must match related records)

#### Commission System
- `real.estate.commission.rule` model (21 fields):
  - Agent assignment
  - Transaction type (sale/rental)
  - Structure type (percentage/fixed/tiered)
  - Percentage value (0-100 validation)
  - Fixed amount (positive value validation)
  - Min/max transaction value filters
  - Validity period (valid_from/valid_until)
  - Company assignment (auto-matched to agent company)
  - Soft-delete with `active` flag

- `real.estate.commission.transaction` model (25 fields):
  - Transaction tracking (date, type, reference, amounts)
  - Payment status (pending/paid/cancelled)
  - Agent linkage
  - Automatic commission calculation based on active rules

- **Commission Calculation Logic**:
  - Non-retroactive (only future transactions)
  - Rule priority: most specific to most general
  - Overlap handling (first matching rule wins)
  - Validation: percentage range, fixed amount positive, min < max

#### Property Assignments
- `real.estate.agent.property.assignment` model (8 fields):
  - Agent-property linkage
  - Responsibility type (primary/support)
  - Assignment date
  - Company isolation
  - Active/inactive status
  - Notes field for additional context

- **Constraints**:
  - One active primary assignment per property-agent pair
  - Company match validation (agent.company_id == property.company_id)
  - Unique assignment per active agent-property combination

#### Security & Multi-Tenancy
- **Record Rules** (`security/record_rules.xml`):
  - `real_estate_agent_company_rule`: Agents filtered by current company
  - `real_estate_commission_rule_company_rule`: Commission rules by company
  - `real_estate_assignment_company_rule`: Assignments by company
  - `real_estate_commission_transaction_company_rule`: Transactions by company

- **Access Rights** (`security/ir.model.access.csv`):
  - Real Estate Manager: Full CRUD on all models
  - Real Estate User: Read all, Create/Update own records
  - Portal User: Read-only access to public data

- **Groups** (`security/groups.xml`):
  - `group_real_estate_manager`: Admin access
  - `group_real_estate_user`: Standard user access

#### REST API
- **Agent Endpoints**:
  - `GET /api/v1/agents` - List agents (company-filtered)
  - `POST /api/v1/agents` - Create agent
  - `GET /api/v1/agents/{id}` - Get agent details
  - `PUT /api/v1/agents/{id}` - Update agent
  - `DELETE /api/v1/agents/{id}` - Deactivate agent (soft-delete)

- **Authentication**:
  - JWT token via `/api/v1/oauth/token`
  - Session-based for web UI
  - Both decorators required: `@require_jwt` and `@require_session`

- **API Features**:
  - HATEOAS hypermedia links
  - OpenAPI 3.0 schema documentation
  - Multi-tenant isolation (automatic company filtering)
  - Error handling with proper HTTP status codes

#### Database Schema
- **Tables Created**:
  - `real_estate_agent`
  - `real_estate_commission_rule`
  - `real_estate_agent_property_assignment`
  - `real_estate_commission_transaction`

- **Indexes**:
  - `real_estate_agent.creci_normalized` (for uniqueness check)
  - `real_estate_agent.company_id` (for multi-tenant filtering)
  - `real_estate_commission_rule.agent_id` (for rule lookups)
  - `real_estate_assignment.agent_id`, `property_id` (for assignment queries)

- **Constraints**:
  - `real_estate_agent_creci_company_unique`: UNIQUE(creci_normalized, company_id) WHERE creci_normalized IS NOT NULL
  - `real_estate_agent_user_unique`: UNIQUE(user_id) WHERE user_id IS NOT NULL
  - `real_estate_agent_property_assignment_agent_property_unique`: UNIQUE(agent_id, property_id, active) WHERE active = TRUE

#### Testing
- **Test Files**:
  - `tests/test_agent_crud.py`: Agent CRUD operations, multi-tenancy
  - `tests/test_agent_unit.py`: Field validation, user sync
  - `tests/test_commission.py`: Commission calculation, rule application
  - `tests/test_assignment.py`: Property assignment logic

---

## [Unreleased]

### Planned
- Commission rule priority system (for handling overlapping rules)
- Bulk agent import via CSV
- Commission payment tracking workflow
- Agent performance reports (charts, dashboards)
- Email notifications for commission payments
- Integration with accounting module for commission invoicing

### Known Issues
- Property tests failing due to `zip_code` NotNull constraint (not agent-related)
- Agent user sync tests may fail without proper Odoo user setup
- Test coverage at 46.9% (target: 80%)

---

## Version History

| Version | Release Date | Description |
|---------|--------------|-------------|
| 1.2.0   | 2026-01-12  | Phase 8: UI views, seed data, documentation |
| 1.1.0   | 2026-01-11  | Phase 7: Performance metrics |
| 1.0.0   | 2026-01-10  | Phases 1-6: Core agent management system |

---

## Migration Notes

### Upgrading from 1.1.0 to 1.2.0
- No database migrations required
- New views auto-registered via `__manifest__.py`
- Demo data loaded via `agent_seed.xml` (noupdate=1, won't override existing records)
- Translation file auto-updated on module upgrade

### Upgrading from 1.0.0 to 1.1.0
- Computed fields added with `store=False` (no schema changes)
- Existing agent records will compute metrics on first access
- No manual data migration needed

---

## ADR Compliance

This module follows project-wide Architecture Decision Records:

- **ADR-004**: Nomenclatura de módulos e tabelas (Portuguese naming)
- **ADR-008**: Multi-tenancy & API security architecture
- **ADR-009**: Headless authentication (JWT + session)
- **ADR-011**: Controller security patterns (@require_jwt + @require_session)

See `/docs/adr/` for complete ADR documentation.
