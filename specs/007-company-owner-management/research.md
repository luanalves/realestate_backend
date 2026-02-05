# Research: Company & Owner Management - Technical Details

**Feature**: 007-company-owner-management  
**Created**: 2026-02-05  
**Purpose**: Technical research and implementation details for the planning phase

---

## Executive Summary

Este sistema implementa o gerenciamento completo de **Imobiliárias (Company)** e **Proprietários (Owner)** através de APIs REST e interface Odoo Web. Permite que Owners existentes criem novas imobiliárias, gerenciem outros Owners de suas empresas, e que o SaaS Admin tenha controle total via interface administrativa. O sistema respeita rigorosamente o isolamento multi-tenancy (ADR-008) e as regras RBAC definidas na ADR-019.

---

## Data Model

### Entity: thedevkitchen.estate.company (Existing - extend)

**Model Name**: `thedevkitchen.estate.company` (já existe)  
**Table Name**: `thedevkitchen_estate_company` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(255) | required | Nome da imobiliária |
| `cnpj` | Char(18) | unique | CNPJ formatado |
| `creci` | Char(20) | - | Registro no CRECI |
| `legal_name` | Char(255) | - | Razão social |
| `email` | Char(100) | - | Email de contato |
| `phone` | Char(20) | - | Telefone |
| `mobile` | Char(20) | - | Celular |
| `website` | Char(200) | - | Website |
| `street` | Char(200) | - | Endereço |
| `city` | Char(100) | - | Cidade |
| `state_id` | Many2one | FK | Estado |
| `zip_code` | Char(10) | - | CEP |
| `logo` | Binary | - | Logo da empresa |
| `active` | Boolean | default=True | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | Audit field |
| `write_date` | Datetime | auto | Audit field |
| `owner_ids` | Many2many | computed | Owners da company (via res.users) |

**SQL Constraints**:
```python
_sql_constraints = [
    ('cnpj_unique', 'unique(cnpj)', 'CNPJ must be unique'),
]
```

**Python Constraints**:
```python
@api.constrains('cnpj')
def _check_cnpj(self):
    # Validação completa de CNPJ brasileiro (já existe)
    pass

@api.constrains('email')
def _check_email(self):
    # Validação de formato de email
    pass
```

### Entity: res.users (Extension)

**Field Addition**: `owner_company_ids` (computed field para facilitar queries)

```python
owner_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    compute='_compute_owner_companies',
    string='Owned Companies',
    help='Companies where this user is an Owner'
)

@api.depends('groups_id', 'estate_company_ids')
def _compute_owner_companies(self):
    owner_group = self.env.ref('quicksol_estate.group_real_estate_owner')
    for user in self:
        if owner_group in user.groups_id:
            user.owner_company_ids = user.estate_company_ids
        else:
            user.owner_company_ids = False
```

### Database Architecture Diagram

```
                         ┌────────────────────┐
                         │    res_groups      │
                         ├────────────────────┤
                         │ group_real_estate_ │
                         │ owner              │
                         │ manager            │
                         │ agent              │
                         │ ...                │
                         └─────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │   res_groups_users_rel      │
                    │   (uid, gid)                │
                    └──────────────┬──────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                           res_users                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ User A (Owner)           │ User B (Manager)  │ User C (Agent)│   │
│  │ groups: [owner]          │ groups: [manager] │ groups: [agent]   │
│  │ estate_company_ids: [1,2]│ estate_company_ids: [1] │ [1]     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │ thedevkitchen_user_company_ │
                    │ rel (user_id, company_id)   │
                    └──────────────┬──────────────┘
                                   │
┌──────────────────────────────────┴──────────────────────────────────┐
│                 thedevkitchen_estate_company                         │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Company 1 (id=1)       │  │ Company 2 (id=2)       │             │
│  │ name: "Imob Premium"   │  │ name: "Imob Gold"      │             │
│  │ cnpj: 12.345.../0001   │  │ cnpj: 98.765.../0001   │             │
│  │ Owners: [User A]       │  │ Owners: [User A]       │             │
│  │ Managers: [User B]     │  │ Managers: []           │             │
│  │ Agents: [User C]       │  │ Agents: []             │             │
│  └────────────────────────┘  └────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### Architectural Decision: Owner is NOT a separate model

**Why?**

```
❌ Option Rejected: Create model thedevkitchen.estate.owner
   - Would duplicate res.users data
   - Synchronization complexity
   - Violates DRY (Don't Repeat Yourself)

✅ Option Chosen: Owner = res.users with specific group
   - Owner is a ROLE, not an entity
   - Identified by: user.has_group('quicksol_estate.group_real_estate_owner')
   - Linked via: user.estate_company_ids (Many2many)
```

### SQL Query to Find Owners

```sql
-- Query to find all Owners of a Company
SELECT u.id, u.name, u.login as email
FROM res_users u
JOIN res_groups_users_rel gur ON u.id = gur.uid
JOIN res_groups g ON gur.gid = g.id
JOIN thedevkitchen_user_company_rel ucr ON u.id = ucr.user_id
WHERE g.id = (SELECT id FROM res_groups WHERE name = 'Real Estate Owner')
  AND ucr.company_id = :company_id
  AND u.active = true;
```

### Record Rules (per ADR-019)

Already existing in `record_rules.xml`:
- `rule_owner_estate_companies`: Owner accesses their companies (CRUD except unlink)
- `rule_manager_estate_companies`: Manager accesses their companies (read/write)
- `rule_agent_estate_companies`: Agent accesses their companies (read only)

**New Record Rule for Owners of Company**:
```xml
<!-- Owner: Can manage users (Owners) within their companies -->
<record id="rule_owner_manage_owners" model="ir.rule">
    <field name="name">Owner: Manage Company Owners</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="domain_force">[
        ('groups_id', 'in', [ref('group_real_estate_owner')]),
        ('estate_company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

---

## API Endpoints (per ADR-007, ADR-009, ADR-011)

### POST /api/v1/companies

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/companies` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Authorization** | `group_real_estate_owner` OR `base.group_system` (ADR-019) |
| **Rate Limit** | 10 requests/minute |

**Request Body** (per ADR-018):
```json
{
  "name": "string (required, max 255)",
  "cnpj": "string (optional, format XX.XXX.XXX/XXXX-XX)",
  "creci": "string (optional)",
  "legal_name": "string (optional)",
  "email": "string (optional, valid email)",
  "phone": "string (optional)",
  "mobile": "string (optional)",
  "website": "string (optional, valid URL)",
  "street": "string (optional)",
  "city": "string (optional)",
  "state_id": "integer (optional, FK to real.estate.state)",
  "zip_code": "string (optional)"
}
```

**Response Success (201)** (per ADR-007 HATEOAS):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Imobiliária Premium",
    "cnpj": "12.345.678/0001-90",
    "email": "contato@premium.com.br",
    "created_at": "2026-02-05T10:00:00Z",
    "links": [
      {"href": "/api/v1/companies/1", "rel": "self", "type": "GET"},
      {"href": "/api/v1/companies/1", "rel": "update", "type": "PUT"},
      {"href": "/api/v1/companies/1", "rel": "delete", "type": "DELETE"},
      {"href": "/api/v1/companies/1/owners", "rel": "owners", "type": "GET"},
      {"href": "/api/v1/companies", "rel": "collection", "type": "GET"}
    ]
  }
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation error (ADR-018) | `{"success": false, "error": "validation_error", "details": [{"field": "cnpj", "message": "Invalid CNPJ format"}]}` |
| 401 | Missing/invalid JWT (ADR-011) | `{"success": false, "error": "unauthorized", "message": "Invalid or expired token"}` |
| 403 | Insufficient permissions (ADR-019) | `{"success": false, "error": "forbidden", "message": "Only Owners can create companies"}` |
| 409 | CNPJ already exists | `{"success": false, "error": "conflict", "field": "cnpj", "message": "CNPJ already registered"}` |

---

### GET /api/v1/companies/{id}

| Attribute | Value |
|-----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/companies/{id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Any authenticated user with access to company |

**Response Success (200)**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Imobiliária Premium",
    "cnpj": "12.345.678/0001-90",
    "creci": "CRECI-SP 12345",
    "legal_name": "Premium Imóveis LTDA",
    "email": "contato@premium.com.br",
    "phone": "(11) 3456-7890",
    "website": "https://premium.com.br",
    "address": {
      "street": "Av. Paulista, 1000",
      "city": "São Paulo",
      "state": "SP",
      "zip_code": "01310-100"
    },
    "statistics": {
      "property_count": 150,
      "agent_count": 12,
      "active_leases": 45
    },
    "links": [
      {"href": "/api/v1/companies/1", "rel": "self", "type": "GET"},
      {"href": "/api/v1/companies/1/owners", "rel": "owners", "type": "GET"},
      {"href": "/api/v1/companies/1/agents", "rel": "agents", "type": "GET"}
    ]
  }
}
```

---

### PUT /api/v1/companies/{id}

| Attribute | Value |
|-----------|-------|
| **Method** | PUT |
| **Path** | `/api/v1/companies/{id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (own company) OR `base.group_system` |

**Request Body**: Same as POST (all fields optional)

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation error | `{"success": false, "error": "validation_error", ...}` |
| 403 | Not owner of company | `{"success": false, "error": "forbidden"}` |
| 404 | Company not found or inaccessible | `{"success": false, "error": "not_found"}` |

---

### DELETE /api/v1/companies/{id}

| Attribute | Value |
|-----------|-------|
| **Method** | DELETE |
| **Path** | `/api/v1/companies/{id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (own company) OR `base.group_system` |

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Company archived successfully",
  "data": {
    "id": 1
  }
}
```

**Note**: Soft delete only (sets `active=False`)

---

### POST /api/v1/companies/{company_id}/owners

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/companies/{company_id}/owners` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (of company_id) OR `base.group_system` |

**Request Body**:
```json
{
  "name": "string (required)",
  "email": "string (required, unique, valid email)",
  "password": "string (required, min 8 chars)",
  "phone": "string (optional)",
  "mobile": "string (optional)"
}
```

**Response Success (201)**:
```json
{
  "success": true,
  "data": {
    "id": 5,
    "name": "João Silva",
    "email": "joao@premium.com.br",
    "phone": "(11) 99999-0000",
    "is_owner": true,
    "companies": [
      {"id": 1, "name": "Imobiliária Premium"}
    ],
    "links": [
      {"href": "/api/v1/companies/1/owners/5", "rel": "self", "type": "GET"},
      {"href": "/api/v1/companies/1/owners/5", "rel": "update", "type": "PUT"},
      {"href": "/api/v1/companies/1/owners", "rel": "collection", "type": "GET"}
    ]
  }
}
```

---

### GET /api/v1/companies/{company_id}/owners

| Attribute | Value |
|-----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/companies/{company_id}/owners` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (of company_id) OR `base.group_system` |

**Response Success (200)**:
```json
{
  "success": true,
  "data": {
    "count": 2,
    "items": [
      {
        "id": 2,
        "name": "Maria Santos",
        "email": "maria@premium.com.br",
        "active": true,
        "created_at": "2026-01-15T08:00:00Z"
      },
      {
        "id": 5,
        "name": "João Silva",
        "email": "joao@premium.com.br",
        "active": true,
        "created_at": "2026-02-05T10:00:00Z"
      }
    ],
    "links": [
      {"href": "/api/v1/companies/1/owners", "rel": "self", "type": "GET"},
      {"href": "/api/v1/companies/1", "rel": "company", "type": "GET"}
    ]
  }
}
```

---

### PUT /api/v1/companies/{company_id}/owners/{owner_id}

| Attribute | Value |
|-----------|-------|
| **Method** | PUT |
| **Path** | `/api/v1/companies/{company_id}/owners/{owner_id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (of company_id) OR `base.group_system` |

**Request Body**:
```json
{
  "name": "string (optional)",
  "email": "string (optional, unique)",
  "password": "string (optional, min 8 chars)",
  "phone": "string (optional)",
  "mobile": "string (optional)",
  "active": "boolean (optional)"
}
```

---

### DELETE /api/v1/companies/{company_id}/owners/{owner_id}

| Attribute | Value |
|-----------|-------|
| **Method** | DELETE |
| **Path** | `/api/v1/companies/{company_id}/owners/{owner_id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | `group_real_estate_owner` (of company_id) OR `base.group_system` |

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Last active owner | `{"success": false, "error": "validation_error", "message": "Cannot remove the last active owner of a company"}` |
| 403 | Not owner of company | `{"success": false, "error": "forbidden"}` |
| 404 | Owner not found | `{"success": false, "error": "not_found"}` |

---

## Technical Constraints

### Must Follow (from ADRs)

| ADR | Requirement | Applied To |
|-----|-------------|------------|
| ADR-004 | `thedevkitchen_` prefix | Model names, tables |
| ADR-007 | HATEOAS links in responses | All API endpoints |
| ADR-008 | Company isolation via `estate_company_ids` | Record rules, API filters |
| ADR-011 | Dual auth decorators (`@require_jwt` + `@require_session` + `@require_company`) | All controllers |
| ADR-015 | Soft delete pattern | Delete operations (active=False) |
| ADR-018 | Schema validation | Input validation |
| ADR-019 | RBAC enforcement | Authorization checks |
| ADR-022 | Linting standards | All code |

### Architecture Patterns

- **Controller Pattern**: Per `.github/instructions/controllers.instructions.md`
- **Testing Pattern**: Per `.github/instructions/test-strategy.instructions.md`
- **Validation Pattern**: Per ADR-018 (schema validation before processing)

---

## RBAC Permission Matrix

| Operation | SaaS Admin | Owner | Director | Manager | Agent |
|-----------|:----------:|:-----:|:--------:|:-------:|:-----:|
| Create Company | ✅ | ✅ (own) | ❌ | ❌ | ❌ |
| Read Company | ✅ (all) | ✅ (own) | ✅ (own) | ✅ (own) | ✅ (own) |
| Update Company | ✅ (all) | ✅ (own) | ❌ | ❌ | ❌ |
| Delete Company | ✅ (all) | ✅ (own) | ❌ | ❌ | ❌ |
| Create Owner | ✅ (any) | ✅ (own co.) | ❌ | ❌ | ❌ |
| Read Owners | ✅ (any) | ✅ (own co.) | ❌ | ❌ | ❌ |
| Update Owner | ✅ (any) | ✅ (own co.) | ❌ | ❌ | ❌ |
| Delete Owner | ✅ (any) | ✅ (own co.) | ❌ | ❌ | ❌ |

---

## Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `controllers/company_api.py` | Company CRUD API endpoints |
| `controllers/owner_api.py` | Owner CRUD API endpoints (nested under company) |
| `views/company_views.xml` | Form, List, Search views for Company |
| `tests/api/test_company_api.py` | Integration tests for Company endpoints |
| `tests/api/test_owner_api.py` | Integration tests for Owner endpoints |
| `tests/unit/test_company_validations.py` | Unit tests for CNPJ, email validations |
| `tests/unit/test_owner_validations.py` | Unit tests for last-owner protection |

### Modified Files

| File | Changes |
|------|---------|
| `__manifest__.py` | Add new view files to data list |
| `controllers/__init__.py` | Import new controllers |
| `views/real_estate_menus.xml` | Fix `action_company` reference |
| `security/record_rules.xml` | Add Owner management rule |
| `models/res_users.py` | Add computed field `owner_company_ids` |

---

## Implementation Phases

### Phase 1: Company API & Views (3 days)
- Create `company_api.py` controller with CRUD endpoints
- Create `company_views.xml` with form/list/search views
- Fix menu action reference (`action_company`)
- Unit tests for CNPJ/email validations
- E2E test for company creation flow

### Phase 2: Owner API (3 days)
- Create `owner_api.py` controller with nested CRUD
- Add last-owner protection logic in model
- Add record rule for Owner management
- Unit tests for RBAC and last-owner protection
- E2E test for owner creation flow

### Phase 3: Testing & Integration (2 days)
- E2E tests for multi-tenancy isolation
- E2E tests for RBAC enforcement (all roles)
- Cypress tests for Admin UI (Company/Owner management)
- Integration test for full owner registration flow

### Phase 4: Documentation & Artifacts (1 day)
- OpenAPI/Swagger specification update
- Postman collection with all endpoints
- Update README with new endpoints
- Code review and linting fixes

---

## Assumptions & Dependencies

### Assumptions
- Owner group (`group_real_estate_owner`) already exists ✅ (confirmed in groups.xml)
- `estate_company_ids` field on res.users already exists ✅ (confirmed in res_users.py)
- Company model (`thedevkitchen.estate.company`) exists with CNPJ validation ✅ (confirmed in company.py)
- Authentication decorators available ✅ (confirmed in thedevkitchen_apigateway)

### Dependencies
- **Existing modules**: `thedevkitchen_apigateway`, `quicksol_estate`
- **External services**: PostgreSQL 14+, Redis 7+
- **Authentication**: OAuth2 via `thedevkitchen_apigateway`
- **Base Odoo**: `base`, `mail`

---

## Test Strategy Overview

### Unit Tests (Python unittest + mock)

| Test File | Coverage |
|-----------|----------|
| `test_company_validations.py` | CNPJ format, CNPJ check digits, email format, name required |
| `test_owner_validations.py` | Last owner protection, email unique, password min length |

### E2E Tests (curl/shell)

| Test File | Coverage |
|-----------|----------|
| `test_owner_creates_company.sh` | US1 - Full company creation flow |
| `test_owner_creates_owner.sh` | US2 - Owner creates another owner |
| `test_company_rbac.sh` | US4 - RBAC enforcement for all roles |
| `test_company_multitenancy.sh` | Multi-tenancy isolation |

### E2E Tests (Cypress)

| Test File | Coverage |
|-----------|----------|
| `admin-company-management.cy.js` | US3 - SaaS Admin manages companies via UI |
| `admin-owner-management.cy.js` | US3 - SaaS Admin manages owners via UI |

---

## Artifacts to Generate After Planning

1. **OpenAPI/Swagger** (per ADR-005)
   - Location: `docs/openapi/007-company-owner.yaml`
   
2. **Postman Collection** (per ADR-016)
   - Location: `docs/postman/007-company-owner.postman_collection.json`

3. **Test Files** (per ADR-003)
   - Unit: `tests/unit/test_company_*.py`, `tests/unit/test_owner_*.py`
   - E2E API: `integration_tests/test_company_*.sh`
   - E2E UI: `cypress/e2e/company-*.cy.js`
