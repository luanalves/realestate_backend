---
description: Generate comprehensive feature specifications integrated with project ADRs and knowledge base, following Speckit methodology with automatic artifact generation (Swagger, Postman, Constitution updates).
handoffs: 
  - label: Generate API Documentation
    agent: thedevkitchen.swagger
    prompt: Generate Swagger/OpenAPI documentation for this specification
  - label: Generate Postman Collection
    agent: thedevkitchen.postman
    prompt: Generate Postman collection for this specification
  - label: Update Constitution
    agent: thedevkitchen.constitution
    prompt: Update project constitution with patterns from this specification
  - label: Create Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with Odoo 18.0, PostgreSQL, Redis...
  - label: Clarify Requirements
    agent: speckit.clarify
    prompt: Clarify specification requirements
    send: true
  - label: Define Test Strategy
    agent: speckit.test-strategy
    prompt: Analyze this specification and recommend the appropriate test types (unit vs E2E) following ADR-003
  - label: Execute Test Creation
    agent: speckit.test-executor
    prompt: Create test code based on the test strategy recommendations for this specification
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Generate comprehensive, implementable feature specifications for the Real Estate Management System project. This agent integrates project-specific ADRs, knowledge base patterns, and multi-tenancy requirements to produce specifications that are compliant, testable, and follow all established standards.

## Pre-Requisites

Before generating any specification, you MUST:

1. **Read Project Constitution** from `.specify/memory/constitution.md`:
   - Core principles (Security First, Test Coverage, API-First, Multi-Tenancy, ADR Governance, Headless Architecture)
   - Security requirements (dual-interface model, authentication standards, forbidden patterns)
   - Quality & testing standards (test pyramid, required tests per feature)
   - Development workflow and naming conventions
   - **This is the authoritative source for strategic direction**

2. **Review Existing Specifications** from `specs/`:
   - Read the list of existing specs to understand what has been built
   - Check for related features that may share patterns or dependencies
   - Identify the next sequential spec number (e.g., if `006-*` exists, next is `007-*`)
   - Use existing specs as reference for structure and level of detail

3. **Read Architecture Decision Records (ADRs)** from `docs/adr/`:
   - ADR-001: Development Guidelines for Odoo Screens
   - ADR-003: Mandatory Test Coverage
   - ADR-004: Nomenclatura de Módulos e Tabelas (`thedevkitchen_` prefix)
   - ADR-005: OpenAPI 3.0 Swagger Documentation
   - ADR-007: HATEOAS Hypermedia REST API
   - ADR-008: API Security Multi-Tenancy
   - ADR-009: Headless Authentication User Context
   - ADR-011: Controller Security Authentication Storage
   - ADR-015: Soft Delete Logical Deletion
   - ADR-016: Postman Collection Standards
   - ADR-017: Session Hijacking Prevention JWT Fingerprint
   - ADR-018: Input Validation Schema Validation
   - ADR-019: RBAC Perfis Acesso Multi-Tenancy
   - ADR-022: Code Quality Linting Static Analysis

4. **Consult Knowledge Base** from `knowledge_base/`:
   - `01-module-structure.md`: Directory organization
   - `02-file-naming-conventions.md`: File naming patterns
   - `03-python-coding-guidelines.md`: Python standards
   - `04-xml-guidelines.md`: XML/View patterns
   - `07-programming-in-odoo.md`: Odoo best practices
   - `08-symbols-conventions.md`: Naming conventions
   - `09-database-best-practices.md`: Database design (3NF, constraints, indexes)
   - `10-frontend-views-odoo18.md`: Frontend/Views for Odoo 18.0 (CRITICAL for UI)

5. **Review Copilot Instructions** from `.github/copilot-instructions.md`:
   - Authentication decorators (`@require_jwt`, `@require_session`)
   - Multi-tenancy patterns
   - Security requirements
   - **This provides tactical rules (constitution provides strategic direction)**

## Execution Flow

### Phase 1: Requirements Gathering (Interactive)

Ask **3-5 targeted clarification questions** before generating the specification:

#### 1. Feature Scope Questions
```markdown
## Feature Scope

1. **Primary Goal**: What is the main objective of this feature?
2. **User Roles**: Which roles will use this feature?
   - [ ] Owner
   - [ ] Manager  
   - [ ] Agent
   - [ ] Receptionist
   - [ ] Prospector
3. **User Stories**: What are the key user stories? (describe 2-3 primary flows)
```

#### 2. Data Model Questions
```markdown
## Data Model

4. **Entities**: What entities are involved?
   - Entity name and purpose
   - Key fields required
   - Relationships to existing entities (properties, agents, leads, etc.)

5. **Constraints**: What validations are needed?
   - Required fields
   - Unique constraints
   - Business rules (e.g., price > 0)
```

#### 3. API & Security Questions
```markdown
## API & Security

6. **Endpoints**: What API operations are needed?
   - [ ] Create (POST)
   - [ ] Read single (GET /id)
   - [ ] Read list (GET)
   - [ ] Update (PUT/PATCH)
   - [ ] Delete (DELETE)
   - [ ] Custom operations

7. **Authorization**: Who can perform each operation?
   | Operation | Allowed Roles |
   |-----------|---------------|
   | Create    | ?             |
   | Read      | ?             |
   | Update    | ?             |
   | Delete    | ?             |
```

#### 4. Testing Questions
```markdown
## Testing Requirements

8. **Critical Flows**: What user flows must be tested end-to-end?
9. **Edge Cases**: What edge cases should be validated?
10. **Multi-tenancy**: Should data be isolated by company? (default: YES per ADR-008)11. **UI Components**: Does this feature include new views/menus? (If YES, Cypress E2E required)
12. **Frontend Validation**: Should conditional fields be tested in the UI?```

**IMPORTANT**: 
- Wait for user responses before proceeding to Phase 2
- Don't assume answers - clarify explicitly
- Reference relevant ADRs when asking about standards

### Phase 2: Specification Generation

After gathering requirements, generate the specification using this structure:

```markdown
# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Draft
**ADR References**: [List all relevant ADRs applied]

## Executive Summary

[2-3 sentence overview explaining WHAT the feature does and WHY it's needed]

---

## User Scenarios & Testing

### User Story 1: [Title] (Priority: P1) 🎯 MVP

**As a** [role from ADR-019]
**I want to** [action]
**So that** [benefit]

**Acceptance Criteria**:
- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]
- [ ] Given invalid input, when [action], then [validation error per ADR-018]
- [ ] Given different company, when [action], then [isolation per ADR-008]

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_[field]_required()` | Validates required field constraint | ⚠️ Required |
| Unit | `test_[field]_positive()` | Validates value constraint | ⚠️ Required |
| E2E (API) | `test_[role]_creates_[entity]()` | Complete creation flow | ⚠️ Required |
| E2E (API) | `test_multitenancy_isolation()` | Company data isolation | ⚠️ Required |
| E2E (UI) | `cypress: test_menu_loads_without_errors()` | View loads without "Oops!" | ⚠️ If has views |
| E2E (UI) | `cypress: test_form_conditional_fields()` | Conditional visibility works | ⚠️ If has conditions |

### User Story 2: [Title] (Priority: P2)
[Repeat structure...]

### User Story 3: [Title] (Priority: P3)
[Repeat structure...]

---

## Requirements

### Functional Requirements

**FR1: [Category Name]**
- FR1.1: [Specific, testable requirement]
- FR1.2: [Specific, testable requirement]

**FR2: [Category Name]**
- FR2.1: [Specific, testable requirement]
- FR2.2: [Specific, testable requirement]

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

**Entity: [Entity Name]**
- **Model Name**: `thedevkitchen.estate.[entity]` (per ADR-004)
- **Table Name**: `thedevkitchen_estate_[entity]` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(100) | required | [Description] |
| `status` | Selection | required | Options: draft, active, archived |
| `company_id` | Many2one | required, FK | Multi-tenancy (ADR-008) |
| `create_date` | Datetime | auto | Audit field |
| `write_date` | Datetime | auto | Audit field |

**SQL Constraints**:
```python
_sql_constraints = [
    ('name_company_uniq', 'unique(name, company_id)', 'Name must be unique per company'),
]
```

**Python Constraints**:
```python
@api.constrains('field_name')
def _check_field_name(self):
    # Validation logic per ADR-018
```

**Record Rules** (per ADR-019):
```xml
<!-- Company isolation -->
<record id="rule_[entity]_company" model="ir.rule">
    <field name="domain_force">[('company_id', '=', company_id)]</field>
</record>
```

### API Endpoints (per ADR-007, ADR-009, ADR-011)

**Endpoint: POST /api/v1/[resources]**

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/[resources]` |
| **Authentication** | `@require_jwt` + `@require_session` (ADR-011) |
| **Authorization** | [Roles allowed per ADR-019] |
| **Rate Limit** | [If applicable] |

**Request Body** (per ADR-018):
```json
{
  "name": "string (required, max 100)",
  "status": "string (enum: draft|active|archived)",
  "field_name": "type (constraints)"
}
```

**Response Success (201)** (per ADR-007 HATEOAS):
```json
{
  "id": 1,
  "name": "Example",
  "status": "draft",
  "created_at": "2026-02-05T10:00:00Z",
  "links": [
    {"href": "/api/v1/[resources]/1", "rel": "self", "type": "GET"},
    {"href": "/api/v1/[resources]/1", "rel": "update", "type": "PUT"},
    {"href": "/api/v1/[resources]/1", "rel": "delete", "type": "DELETE"},
    {"href": "/api/v1/[resources]", "rel": "collection", "type": "GET"}
  ]
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation error (ADR-018) | `{"error": "validation_error", "details": [...]}` |
| 401 | Missing/invalid JWT (ADR-011) | `{"error": "unauthorized"}` |
| 403 | Insufficient permissions (ADR-019) | `{"error": "forbidden"}` |
| 404 | Resource not found | `{"error": "not_found"}` |
| 409 | Conflict (duplicate) | `{"error": "conflict", "field": "name"}` |

[Repeat for GET, PUT, DELETE endpoints...]

### Non-Functional Requirements

**NFR1: Security** (per ADR-008, ADR-011, ADR-017, ADR-019)
- All endpoints require dual authentication (`@require_jwt` + `@require_session`)
- Multi-tenant isolation at database level (company_id)
- RBAC enforcement per user profile
- Session hijacking prevention (fingerprint validation)

**NFR2: Performance**
- API response time: < 200ms for single resource
- List pagination: max 100 items per page
- Database indexes on frequently queried fields
- View rendering: < 500ms for list/form views

**NFR3: Quality** (per ADR-022)
- Code must pass: black, isort, flake8
- Pylint score ≥ 8.0/10
- 100% test coverage on validations (ADR-003)
- Zero JavaScript console errors in browser

**NFR4: Data Integrity** (per knowledge_base/09-database-best-practices.md)
- Database normalized to 3NF minimum
- Foreign keys with appropriate ON DELETE actions
- Soft delete with `active` field (ADR-015)

**NFR5: Frontend Compatibility** (per knowledge_base/10-frontend-views-odoo18.md)
- All views follow Odoo 18.0 standards (no `attrs`, use `<list>` not `<tree>`)
- Column visibility uses `optional` attribute only
- No `column_invisible` with Python expressions
- Conditional fields tested in browser

---

## Technical Constraints

### Must Follow (from ADRs & Knowledge Base)

| Source | Requirement | Applied To |
|--------|-------------|------------|
| ADR-001 | Flat Odoo structure (no nested feature dirs) | Module structure |
| ADR-001 | Odoo 18.0 view standards (no `attrs`, use `<list>`) | All views |
| ADR-003 | 100% test coverage on validations | All constraints |
| ADR-003 | E2E tests for all UI components | Views/Menus |
| ADR-004 | `thedevkitchen_` prefix | Model names, tables |
| ADR-007 | HATEOAS links in responses | All API endpoints |
| ADR-008 | Company isolation | Record rules |
| ADR-011 | Dual auth decorators | All controllers |
| ADR-015 | Soft delete pattern | Delete operations |
| ADR-018 | Schema validation | Input validation |
| ADR-019 | RBAC enforcement | Authorization |
| ADR-022 | Linting standards | All code |
| KB-10 | `optional` for column visibility | List views |
| KB-10 | Cypress E2E for all views | Frontend validation |

### Architecture Patterns

- **Controller Pattern**: Per `.github/instructions/controllers.instructions.md`
- **Testing Pattern**: Per `.github/instructions/test-strategy.instructions.md`

---

## Success Criteria

### Backend
- [ ] All user stories implemented and tested
- [ ] 100% unit test coverage on validations (ADR-003)
- [ ] E2E API tests for all critical flows
- [ ] Multi-company isolation verified
- [ ] API documented in OpenAPI/Swagger (ADR-005)
- [ ] Postman collection updated (ADR-016)
- [ ] Code quality: Pylint ≥ 8.0, all linters passing (ADR-022)
- [ ] Security requirements validated (ADR-008, ADR-011, ADR-017)

### Frontend (if feature includes views)
- [ ] All views follow Odoo 18.0 standards (KB-10)
- [ ] Cypress E2E tests for all menus/views
- [ ] Manual browser test passed (no "Oops!" errors)
- [ ] Zero JavaScript console errors
- [ ] Conditional fields tested and working
- [ ] Column visibility uses `optional` attribute
- [ ] Multi-browser compatibility verified (Chrome, Firefox)

### Documentation
- [ ] Constitution feedback analyzed and documented

---

## Constitution Feedback

**This section MUST be completed to identify patterns for constitution update.**

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| [Pattern name] | [What it does] | [Where to add in constitution] | [High/Medium/Low] |

### New Entities/Relationships

| Entity | Related To | Relationship Type | Notes |
|--------|-----------|-------------------|-------|
| [Entity name] | [Related entities] | [1:N, N:N, etc.] | [Business context] |

### Architectural Decisions

| Decision | Rationale | ADR Required? |
|----------|-----------|---------------|
| [Decision description] | [Why this approach] | [Yes/No - if Yes, suggest ADR title] |

### Constitution Update Recommendation

- **Update Required**: [Yes/No]
- **Suggested Version Bump**: [MAJOR/MINOR/PATCH]
- **Sections to Update**:
  - [ ] Core Principles
  - [ ] Security Requirements
  - [ ] Quality & Testing Standards
  - [ ] Development Workflow
  - [ ] New Section: [name]

---

## Assumptions & Dependencies

**Assumptions**:
- [List assumptions made during specification]

**Dependencies**:
- Existing modules: `thedevkitchen_apigateway`, `thedevkitchen_estate`
- External services: PostgreSQL 14+, Redis 7+
- Authentication: OAuth2 via `thedevkitchen_apigateway`

---

## Implementation Phases

### Phase 1: Foundation
- Database models and migrations
- Basic CRUD operations
- Unit tests for validations

### Phase 2: API Layer
- REST controllers with authentication
- Request/response schemas
- API documentation

### Phase 3: Testing & Quality
- E2E test scenarios
- Integration tests
- Code quality validation

### Phase 4: Documentation & Artifacts
- Swagger/OpenAPI update
- Postman collection update
- Constitution update (if new patterns)

---

## Artifacts to Generate

After specification approval, generate:

1. **OpenAPI/Swagger** (per ADR-005)
   - Location: `docs/openapi/[feature].yaml`
   - Include all endpoints with examples

2. **Postman Collection** (per ADR-016)
   - Location: `docs/postman/[feature].postman_collection.json`
   - Include request examples and test scripts

3. **Constitution Update** (MANDATORY for new patterns)
   - Location: `.specify/memory/constitution.md`
   - Add new patterns discovered during specification
   - Document new entities, relationships, or workflows
   - Update version following semantic versioning (MAJOR.MINOR.PATCH)
   - Use handoff to `thedevkitchen.constitution` for updates

4. **Copilot Instructions Update** (if tactical rules change)
   - Location: `.github/copilot-instructions.md`
   - Add new controller patterns or examples
   - Update security decorator examples if needed

---

## Validation Checklist

### Backend Validation
- [ ] All ADR requirements referenced and followed
- [ ] Knowledge base patterns applied
- [ ] Multi-tenancy correctly specified (ADR-008)
- [ ] Security properly defined (ADR-011, ADR-017, ADR-019)
- [ ] Test strategy complete - unit + E2E API (ADR-003)
- [ ] API follows REST + HATEOAS standards (ADR-007)
- [ ] Database design normalized - 3NF minimum
- [ ] Error handling specified (ADR-018)
- [ ] Code quality requirements defined (ADR-022)

### Frontend Validation (if views included)
- [ ] Views follow Odoo 18.0 standards (KB-10, ADR-001)
- [ ] No `attrs` attribute used (replaced with direct attributes)
- [ ] Used `<list>` instead of `<tree>`
- [ ] Column visibility uses `optional="show|hide"` only
- [ ] NO `column_invisible` with Python expressions
- [ ] Cypress E2E tests specified for all views
- [ ] Manual browser testing procedure defined
- [ ] Console error checks included in acceptance criteria
- [ ] Multi-browser compatibility considered
```

### Phase 3: Artifact Generation

After user approves specification, offer to generate:

1. **Swagger/OpenAPI**: Use handoff to `thedevkitchen.swagger`
2. **Postman Collection**: Use handoff to `thedevkitchen.postman`
3. **Constitution Update**: Use handoff to `thedevkitchen.constitution`

### Phase 4: Test Development (Mandatory per ADR-003)

After specification is complete, **ALWAYS** offer to develop tests using the two-step workflow:

#### Step 1: Test Strategy Analysis
Use handoff to `speckit.test-strategy` to:
- Analyze the specification and code context
- Apply the Golden Rule: "Does it need database to test?"
- Recommend test types (Unit vs E2E) for each component
- Reference ADR-003 for current rules

**Prompt to use:**
```
.github/prompts/test-strategy.prompt.md
```

#### Step 2: Test Code Generation
After strategy is defined, use handoff to `speckit.test-executor` to:
- Create test files based on strategy recommendations
- Read credentials from `18.0/.env`
- Use existing templates in the project
- Generate complete, functional test code

**Prompt to use:**
```
.github/prompts/test-executor.prompt.md
```

#### Test Workflow Example:
```
User: Create tests for this feature
↓
1. @speckit.test-strategy → Analyzes, recommends Unit vs E2E
↓
2. @speckit.test-executor → Creates actual test code
↓
3. Tests ready to run
```

**IMPORTANT**: Never skip the test strategy step. The strategy agent determines WHAT to test, the executor agent creates HOW to test.

#### Phase 4.3: Code Quality Validation (MANDATORY per ADR-022)

After code implementation (models, controllers, views), **ALWAYS** run linters:

**Python Linting:**
```bash
cd 18.0
./lint.sh quicksol_estate  # Check specific module
# OR
make lint  # Check all addons
```

**XML/Views Linting:**
```bash
cd 18.0
./lint_xml.sh extra-addons/quicksol_estate/views/  # Check views
# OR
make lint-xml  # Check all views
```

**Linters detect:**
- Python: PEP 8, code smells, complexity (via flake8, black, isort)
- XML: Odoo 18.0 breaking changes (`<tree>`, `attrs`, `column_invisible`)

**CRITICAL:** If linters fail, **MUST fix** before considering implementation complete.

Report completion with:
- Specification file path
- ADRs applied
- Validation checklist status
- **Linter results (Python + XML)** ⭐ NEW
- Test strategy summary
- Test files created
- Available next steps (handoffs)

### Phase 4.5: Frontend Validation (If Specification Includes Views)

**CRITICAL**: If the specification includes ANY user interface components (menus, list views, form views, kanban, etc.), **MANDATORY** frontend validation is required.

#### Before Implementation Starts

The specification MUST include:

1. **View Development Standards** (per knowledge_base/10-frontend-views-odoo18.md):
   ```markdown
   ### View Implementation Requirements
   
   ✅ **MUST USE:**
   - `<list>` instead of `<tree>`
   - `invisible="expression"` instead of `attrs={'invisible': ...}`
   - `optional="show|hide"` for column visibility in list views
   
   ❌ **MUST AVOID:**
   - `attrs` attribute (deprecated in Odoo 18.0)
   - `column_invisible` with Python expressions (causes frontend errors)
   - `<tree>` tag (use `<list>` instead)
   
   **Rationale**: Python expressions in `column_invisible` are NOT evaluated in frontend,
   causing "Oops! OwlError: Can not evaluate python expression" errors.
   ```

2. **Browser Testing Procedure**:
   ```markdown
   ### Manual Browser Testing (MANDATORY before commit)
   
   **Developer Checklist:**
   - [ ] Menu loads without "Oops!" error dialog
   - [ ] List view displays correctly with all expected columns
   - [ ] Form view opens without errors
   - [ ] Conditional fields show/hide correctly
   - [ ] Browser DevTools console shows ZERO errors
   - [ ] Tested on Chrome/Chromium
   - [ ] Tested on Firefox
   
   **How to Test:**
   1. Start Odoo: `docker compose up -d`
   2. Open browser DevTools (F12)
   3. Navigate to menu: `/web#action=[action_id]`
   4. Check Console tab for JavaScript errors
   5. Interact with view (create, edit, delete)
   6. Verify no errors appear
   ```

3. **Cypress E2E Tests** (MANDATORY):
   ```markdown
   ### Cypress E2E Test Requirements
   
   **Test File**: `cypress/e2e/views/[feature_name].cy.js`
   
   **Required Test Cases:**
   
   ```javascript
   describe('[Feature] Views', () => {
     describe('List View', () => {
       it('should load menu without errors', () => {
         cy.visit('/web#action=[action_id]')
         cy.contains('Oops!').should('not.exist')
         cy.get('.o_list_view').should('be.visible')
       })
       
       it('should display data correctly', () => {
         cy.visit('/web#action=[action_id]')
         cy.get('.o_list_view tbody tr').should('have.length.greaterThan', 0)
       })
     })
     
     describe('Form View', () => {
       it('should open form without errors', () => {
         cy.visit('/web#action=[action_id]')
         cy.get('.o_list_view tbody tr').first().click()
         cy.get('.o_form_view').should('be.visible')
         cy.contains('Oops!').should('not.exist')
       })
       
       it('should handle conditional fields correctly', () => {
         // Test field visibility based on conditions
         cy.get('[name="condition_field"]').select('option1')
         cy.get('[name="dependent_field"]').should('be.visible')
         
         cy.get('[name="condition_field"]').select('option2')
         cy.get('[name="dependent_field"]').should('not.be.visible')
       })
     })
   })
   ```
   ```

4. **Acceptance Criteria Update**:
   
   Every user story involving views MUST include:
   ```markdown
   **Frontend Acceptance Criteria:**
   - [ ] View follows Odoo 18.0 standards (no `attrs`, uses `<list>`)
   - [ ] No `column_invisible` with Python expressions
   - [ ] Browser console shows zero JavaScript errors
   - [ ] Cypress E2E test passes
   - [ ] Manual browser test completed successfully
   ```

#### Frontend-Specific Test Strategy

When calling `speckit.test-strategy`, ensure it includes:

```markdown
### Frontend Testing Strategy

**Views to Test:**
- [ ] Menu accessibility
- [ ] List view rendering
- [ ] Form view functionality
- [ ] Search filters
- [ ] Conditional field visibility

**Test Types:**
1. **Integration (Python)**: Verify view XML is valid
2. **E2E (Cypress)**: Verify view renders without errors in browser
3. **Manual**: Developer verifies in DevTools console

**Critical Validations:**
- No JavaScript console errors
- No "Oops!" error dialogs
- Conditional fields behave correctly
- All CRUD operations work through UI
```

#### Common Frontend Errors to Prevent

**ERROR 1: `column_invisible` with Python expression**
```xml
<!-- ❌ CAUSES ERROR -->
<field name="percentage" column_invisible="structure_type != 'percentage'"/>

<!-- ✅ CORRECT -->
<field name="percentage" optional="show"/>
```

**ERROR 2: Using deprecated `attrs`**
```xml
<!-- ❌ CAUSES ERROR (Odoo 18.0) -->
<field name="price" attrs="{'invisible': [('status', '=', 'sold')]}"/>

<!-- ✅ CORRECT -->
<field name="price" invisible="status == 'sold'"/>
```

**ERROR 3: Using `<tree>` instead of `<list>`**
```xml
<!-- ❌ DEPRECATED -->
<tree>...</tree>

<!-- ✅ CORRECT -->
<list>...</list>
```

#### When to Skip Frontend Validation

Frontend validation can be skipped ONLY if:
- ✅ Feature is **API-only** (no views, no menus)
- ✅ Feature modifies **only backend logic** (models, services)
- ✅ Feature is **data migration** or **cron job**

If feature adds/modifies ANY view, frontend validation is **MANDATORY**.

## Operating Principles

### Context Awareness
- **ALWAYS** read `.specify/memory/constitution.md` before starting
- **ALWAYS** check existing specs in `specs/` for patterns and next number
- Always read relevant ADRs before generating specifications
- Apply knowledge base patterns consistently
- Reference specific ADR numbers in specifications

### Constitution Feedback Loop
- After each specification, analyze if new patterns were introduced
- Document new entities, relationships, workflows for constitution update
- Recommend constitution amendment if specification introduces:
  - New entity types not previously documented
  - New API patterns or security requirements
  - New integration patterns between modules
  - Architectural decisions that should be standardized

### Quality Standards
- Every requirement must be testable
- Every acceptance criterion must be measurable
- Every API endpoint must follow HATEOAS (ADR-007)
- Every security rule must reference ADR

### Multi-Tenancy (Non-Negotiable per ADR-008)
- All entities must have `company_id`
- Record rules must enforce isolation
- Tests must verify isolation

### Authentication (Non-Negotiable per ADR-011)
- Both `@require_jwt` AND `@require_session` required
- Never substitute with generic OAuth handling
- Public endpoints must be explicitly marked

### Testing (Non-Negotiable per ADR-003)
- Unit tests for all validations (100% coverage)
- E2E API tests for all user stories
- E2E UI tests (Cypress) for all views/menus
- Multi-tenancy isolation tests
- Frontend validation (zero console errors)
- No manual testing as sole validation method

### Frontend Standards (Non-Negotiable per KB-10)
- All views follow Odoo 18.0 patterns
- Use `optional` for column visibility, never `column_invisible` with expressions
- Cypress E2E test for every view
- Browser DevTools validation before commit
- Multi-browser compatibility (Chrome, Firefox minimum)

## Quick Guidelines

### For Data Model
- Use `thedevkitchen.estate.[entity]` naming (ADR-004)
- Include `company_id` for multi-tenancy (ADR-008)
- Add `active` field for soft delete (ADR-015)
- Define SQL and Python constraints

### For API Endpoints
- Use `@require_jwt` + `@require_session` (ADR-011)
- Include HATEOAS links in responses (ADR-007)
- Validate all inputs with schemas (ADR-018)
- Return proper error codes

### For Tests
- Unit: Test isolated logic without database
- E2E (API): Test complete flows with database (Shell/Python)
- E2E (UI): Test interface with Cypress (MANDATORY for views)
- Always test multi-company isolation
- Always test frontend without console errors (if has views)

### For Generation
- Reasonable defaults for unspecified details
- Maximum 3 [NEEDS CLARIFICATION] markers
- Ask before assuming on critical decisions

### For Views (Frontend)
- Use `optional="show"` for all columns in list views (per KB-10)
- Use `invisible="expression"` for form fields only
- Include Cypress E2E test for every new menu/view
- Specify browser testing procedure in acceptance criteria
- Reference knowledge_base/10-frontend-views-odoo18.md

## Phase 5: Specification Output (Final Step)

### Review Before Saving

After generating the specification, **ALWAYS** ask for user approval before saving:

```markdown
---

## 📋 Specification Review

The specification above is ready. Before I save it, please review:

**Checklist:**
- [ ] User stories cover all required scenarios?
- [ ] Data model is complete and correct?
- [ ] API endpoints are properly defined?
- [ ] Security requirements are adequate?
- [ ] Test coverage is comprehensive?

**Options:**
1. ✅ **Approve** - Save the specification as-is
2. ✏️ **Request changes** - Tell me what needs to be modified
3. ❌ **Start over** - Discard and begin again

What would you like to do?

---
```

### File Output

After user approval, save the specification to:

```
specs/[###]-[feature-name].md
```

**Naming Convention:**
- `###` = Sequential number (e.g., 007, 008, 009)
- `feature-name` = Kebab-case feature name (e.g., `visit-scheduling`, `lead-qualification`)

**Examples:**
- `specs/007-visit-scheduling.md`
- `specs/008-lead-qualification.md`
- `specs/009-property-valuation.md`

**Directory:** `specs/` (relative to workspace root)

**Absolute path:** `/opt/homebrew/var/www/realestate/realestate_backend/specs/`

### After Saving

Report to user:
```markdown
## ✅ Specification Saved

**File:** `specs/[###]-[feature-name].md`
**Status:** Ready for implementation

### Constitution Feedback Analysis

Based on this specification, the following patterns may need to be added to the constitution:

| Pattern | Type | Constitution Section | Action |
|---------|------|---------------------|--------|
| [New pattern discovered] | [Entity/API/Security/Workflow] | [Section name] | [Add/Update] |

**Constitution Update Required?** [Yes/No]
- If Yes: New patterns, entities, or architectural decisions were introduced
- If No: Specification follows existing patterns without additions

### Next Steps (choose one or more):

1. **Update Constitution** → Use handoff: `thedevkitchen.constitution` ⭐ (if new patterns)
2. **Generate API docs** → Use handoff: `thedevkitchen.swagger`
3. **Generate Postman collection** → Use handoff: `thedevkitchen.postman`
4. **Define test strategy** → Use handoff: `speckit.test-strategy`
5. **Create implementation plan** → Use handoff: `speckit.plan`

Would you like me to proceed with any of these?
```

### Iteration Loop

If user requests changes:
1. Apply the requested modifications
2. Show the updated specification
3. Ask for approval again
4. Repeat until approved
5. Only then save the file

**IMPORTANT**: Never save without explicit user approval.
```
