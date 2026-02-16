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
| **Rate Limit** | Handled by API Gateway (global) |

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

---

## Architectural Decisions Log

**Decision Date**: 2026-02-06  
**Stakeholder Review**: Pre-release checklist review (release-readiness.md)

### DEC-001: Inactive Owner API Access Behavior (CHK082)

**Question**: O que acontece quando um Owner com `active=False` tenta acessar a API?

**Decision**: **Autenticação OK, Autorização Negada (403)**
- Token JWT é validado normalmente (usuário existe)
- Todas as operações de API retornam HTTP 403 Forbidden
- Mensagem de erro: `"User account is deactivated"`

**Rationale**: Permite auditoria do acesso (quem tentou) enquanto bloqueia operações. Melhor UX que falha de autenticação pois informa claramente o motivo.

**Implementation**: Validar `user.active` no decorator `@require_session` antes de autorizar qualquer operação.

---

### DEC-002: Soft-Delete Company Restoration (CHK083)

**Question**: Quem pode reativar uma Company soft-deleted?

**Decision**: **Apenas SaaS Admin**
- Owners não têm permissão para restaurar companies deletadas via API
- Restauração disponível apenas via interface Odoo Web (menu Admin)
- Endpoint API para restore: **Não implementado na v1** (CHK046)

**Rationale**: Soft-delete é operação crítica com implicações legais/fiscais. Requer supervisão administrativa.

**Implementation**: Sem endpoint `/companies/{id}/restore`. Admin usa Odoo Web: Companies → Filters → Archived → Unarchive.

---

### DEC-003: Last Owner Protection (CHK084)

**Question**: Owner pode se remover da única company que possui?

**Decision**: **Bloquear com erro HTTP 400**
- Company DEVE ter pelo menos 1 Owner ativo
- API retorna: `{"error": "validation_error", "message": "Cannot remove last owner from company"}`
- Exceção: SaaS Admin pode forçar remoção via Odoo Web (bypass de regra)

**Rationale**: Previne orphan companies sem gestão. Owner deve transferir propriedade antes de sair.

**Implementation**: Validação em `DELETE /companies/{id}/owners/{owner_id}` e `PUT /companies/{id}/owners/{owner_id}` (se desativar).

---

### DEC-004: Email Uniqueness Scope (CHK085) - REVISADO

**Question**: Email de Owner deve ser único globalmente ou por company?

**Decision**: **Globalmente Único** (obrigatório por constraint do Odoo)
- Email/login DEVE ser único em toda a base de dados
- Constraint: `res_users_login_key UNIQUE CONSTRAINT, btree (login)` em `res.users`
- NÃO é possível ter mesmo email em companies diferentes

**Technical Verification** (2025-01-25):
```sql
-- Verificação da constraint em res.users
\d res_users | grep -i login
-- Resultado:
-- login | character varying | not null |
-- "res_users_login_key" UNIQUE CONSTRAINT, btree (login)
```

**Rationale**: Constraint nativa do Odoo impõe unicidade global. Não há como contornar sem modificar o core. Para casos de consultores multi-company, usar emails distintos (ex: `user+company1@domain.com`).

**Implementation**: Validar email único via Odoo nativo. Mensagem de erro customizada: `{"error": "validation_error", "message": "Email already registered in another company"}`.

---

### DEC-005: Soft-Delete Company Cascade Behavior (CHK060)

**Question**: O que acontece com Owners quando Company é soft-deleted?

**Decision**: **Owners permanecem ativos**
- Soft-delete de Company NÃO afeta status de Owners
- Owners mantêm `active=True` e credenciais de login
- Owners perdem acesso à Company deletada (não aparece em `estate_company_ids` ativas)
- Se Owner tinha apenas esta Company, API retorna lista vazia (graceful empty state)

**Rationale**: Owners são entidades independentes que podem estar em múltiplas companies. Deletar company não deve afetar perfis de usuário.

**Implementation**: Nenhuma cascata automática. Record rules filtram companies ativas.

---

### DEC-006: Password Requirements (CHK067) - REVISADO

**Question**: Requisitos de senha para criação de Owner?

**Decision**: **Padrão do Framework Odoo**
- Usar política de senha nativa do Odoo
- Configurável via Settings → General Settings → Password Policy
- Parâmetros controlados por `ir.config_parameter`:
  - `auth_password_policy.minlength` (default: 8)
  - `auth_password_policy.complexity` (opcional)
- NÃO implementar validação customizada

**Rationale**: Framework já possui mecanismo robusto e auditado. Customização adiciona complexidade sem benefício. Administrador pode ajustar políticas conforme necessidade do cliente.

**Implementation**: Nenhuma. Odoo valida automaticamente via `res.users._check_credentials()`.

---

### DEC-007: JWT Token Expiration (CHK068)

**Question**: Tempo de expiração do access token JWT?

**Decision**: **Configurável via Odoo** (parâmetro de sistema)
- Default do Odoo OAuth: verificar `ir.config_parameter` key `oauth.access_token_expiration`
- Não há valor hardcoded na Feature 007
- Documentar onde configurar: Settings → Technical → Parameters → System Parameters

**Rationale**: Flexibilidade para diferentes políticas de segurança por deployment.

**Implementation**: Usar configuração existente do módulo OAuth do Odoo. Não criar nova configuração.

---

### DEC-008: API Response Time SLA (CHK073)

**Question**: Qual o SLA de tempo de resposta da API?

**Decision**: **Sem SLA definido (best effort)**
- Feature 007 não define requisitos de performance específicos
- Performance depende de infraestrutura do deployment
- Monitoramento é responsabilidade do time de operações

**Rationale**: SLAs de performance requerem baseline e infraestrutura de monitoramento não disponíveis nesta fase.

**Implementation**: Nenhuma otimização específica. Seguir boas práticas de query (pagination, lazy loading).

---

### DEC-009: Webhooks for Company/Owner Events (CHK088)

**Question**: Feature 007 deve emitir webhooks quando Company/Owner são criados/deletados?

**Decision**: **Sem webhooks na v1**
- Nenhum webhook implementado nesta versão
- Eventos podem ser adicionados em versão futura se necessário
- Integrações externas devem usar polling ou consulta direta à API

**Rationale**: Simplificar escopo da v1. Webhooks adicionam complexidade de delivery, retry, e gestão de endpoints.

**Implementation**: Nenhuma. Documentar como "não suportado" nas limitações da API.

---

### DEC-010: Data Migration Requirements (CHK089)

**Question**: Existem companies/owners existentes que precisam migração?

**Decision**: **Sem migração necessária**
- Feature 007 trabalha com dados novos
- Companies/Owners existentes foram criados via seed data ou manualmente
- Não há sistema legado a migrar

**Rationale**: Deployment greenfield. Seeds já configuram dados iniciais necessários.

**Implementation**: Nenhuma. Seeds em `data/company_seed.xml` e `data/demo_users.xml`.

---

### DEC-011: Company Owner vs Property Owner Terminology (CHK086)

**Question**: Como distinguir "Company Owner" (dono da imobiliária) de "Property Owner" (dono do imóvel)?

**Decision**: **Entidades distintas - documentar claramente**

| Termo | Entidade | Descrição |
|-------|----------|-----------|
| **Owner** (ou Company Owner) | `res.users` + `group_real_estate_owner` | Proprietário/sócio da imobiliária. Gerencia a empresa. |
| **Property Owner** | `real.estate.property.owner` | Pessoa física/jurídica proprietária de um imóvel específico. Cliente da imobiliária. |

**Rationale**: São conceitos completamente diferentes com modelos e permissões distintas.

**Implementation**: 
- Documentação sempre usa "Company Owner" ou apenas "Owner" para o papel RBAC
- "Property Owner" usado explicitamente quando referindo ao dono do imóvel
- Variáveis de código: `owner` = Company Owner, `property_owner` = Property Owner

---

### DEC-012: Owner Reactivation Method (CHK047)

**Question**: Como reativar um Owner que foi soft-deleted?

**Decision**: **Via PUT com active=true**
- Endpoint: `PUT /api/v1/companies/{id}/owners/{owner_id}` com body `{"active": true}`
- NÃO criar endpoint separado de restore (simplicidade)
- Permissão: Requer Owner role (mesmo Owner pode se reativar? Não, precisa de outro Owner)

**Rationale**: Consistente com padrão Odoo de usar `active` field. PUT já existe para edição.

**Implementation**: Validar que usuário ativo na company pode reativar inativo. Log de auditoria obrigatório.

---

### DEC-013: Record Rules for Multi-tenancy Isolation (CHK066)

**Question**: Record rules (ir.rule) devem isolar dados entre companies?

**Decision**: **Sim, implementar ir.rule com domain**
- Domain: `[('id', 'in', user.estate_company_ids.ids)]`
- Aplicável a todos modelos com campo `company_id` ou `estate_company_id`
- Grupos afetados: `group_real_estate_owner`, `group_real_estate_manager`, etc.

**Rationale**: Padrão Odoo para multi-tenancy. Garante isolamento em nível de ORM.

**Implementation**: Criar `security/company_record_rules.xml` com regras por modelo.

---

### DEC-014: Password Hashing Algorithm (CHK069)

**Question**: Que algoritmo de hash usar para senhas?

**Decision**: **Default Odoo - PBKDF2-SHA512**
- Não customizar hashing
- Odoo 18 usa PBKDF2-SHA512 com salt automático
- Iterações configuráveis via `ir.config_parameter`

**Rationale**: Algoritmo robusto e auditado. Não reinventar segurança.

**Implementation**: Usar `res.users.password` field nativo. Nunca armazenar plaintext.

---

### DEC-015: Critical Database Indexes Documentation (CHK072)

**Question**: Índices de banco devem ser documentados?

**Decision**: **Sim, documentar índices críticos**

Índices obrigatórios:
- `ix_estate_company_cnpj` - Busca por CNPJ (unicidade)
- `ix_estate_company_active` - Filtro padrão por ativo
- `ix_res_users_login` - Busca por email (já existe: `res_users_login_key`)
- `ix_company_user_rel` - Relacionamento many2many company↔user

**Rationale**: Performance crítica para listagens e lookups frequentes.

**Implementation**: Criar índices via `_sql_constraints` ou migration script. Documentar em `docs/architecture/database-indexes.md`.

---

### DEC-016: Owner Accessing Removed Company (CHK048)

**Question**: Owner tenta acessar company da qual foi removido (estate_company_ids). Qual comportamento?

**Decision**: **HTTP 403 Forbidden**
- Autenticação OK (token válido)
- Autorização falha (sem acesso à company específica)
- Response: `{"error": "forbidden", "message": "You no longer have access to this company"}`

**Rationale**: Distingue entre "não autenticado" (401) e "sem permissão" (403). Transparência para o usuário.

**Implementation**: Verificar `company_id in user.estate_company_ids.ids` em cada endpoint protegido.

---

### DEC-017: Malformed Request Payloads (CHK058)

**Question**: Como tratar payloads mal formatados (JSON inválido)?

**Decision**: **Padrão Odoo**
- Usar tratamento nativo do Odoo para erros de parsing
- Response: JSON padrão do Odoo com estrutura `{"error": {...}}`
- HTTP Status: 400 Bad Request

**Rationale**: Consistência com demais endpoints Odoo. Evita customização desnecessária.

**Implementation**: Nenhuma customização necessária. Odoo/Werkzeug tratam automaticamente.

---

### DEC-018: Transaction Rollback on Failure (CHK059)

**Question**: Como documentar rollback em falha de criação de company?

**Decision**: **Transação atômica Odoo (cr.savepoint)**
- Odoo usa transações atômicas por padrão via `cr.savepoint()`
- Qualquer exceção causa rollback automático
- Documentar que operações são ALL-OR-NOTHING

**Rationale**: Comportamento padrão robusto. Não reinventar transaction management.

**Implementation**: Documentar em spec.md que "operações são transacionais - falha em qualquer etapa reverte todas alterações".

---

### DEC-019: Company Lifecycle States (CHK062)

**Question**: Company deve ter estados explícitos (draft, active, archived)?

**Decision**: **Campo state selection** com 4 estados

| Estado | Descrição | Transições Permitidas |
|--------|-----------|----------------------|
| `draft` | Recém-criada, pendente ativação | → active |
| `active` | Operando normalmente | → suspended, archived |
| `suspended` | Temporariamente desativada | → active, archived |
| `archived` | Soft-deleted (active=False) | → active (restore) |

**Rationale**: Mais controle que boolean simples. Permite fluxos como "suspensão temporária por inadimplência".

**Implementation**: Adicionar campo `state = fields.Selection([...])` em `estate.company`. Manter `active` para compatibilidade ORM.

---

### DEC-020: API Consumer Documentation (CHK087)

**Question**: Quais sistemas consumirão esta API?

**Decision**: **Interno + externos**

Consumidores documentados:
1. **Frontend SPA** - App web principal (React/Vue)
2. **Mobile App** - iOS/Android nativo ou React Native
3. **Portais de terceiros** - Sites de parceiros imobiliários
4. **Integrações CRM** - Pipedrive, HubSpot, etc. (futuro)

**Rationale**: Planejamento de versionamento e breaking changes. API deve ser estável para externos.

**Implementation**: Documentar consumidores em `docs/architecture/api-consumers.md`. Definir política de deprecation (mínimo 6 meses).

---

### DEC-021: External Auth Provider Integration (CHK090)

**Question**: Sync com providers de autenticação externos (Google, Azure AD)?

**Decision**: **Sem auth provider externo (v1)**
- Autenticação exclusivamente via Odoo nativo
- JWT emitido pelo próprio sistema
- SSO/OAuth social login NÃO suportado nesta versão

**Rationale**: Simplifica v1. Integração SSO pode ser adicionada futuramente sem breaking changes.

**Implementation**: Nenhuma. Documentar como "out of scope" em spec.md.

---

### DEC-022: Requirements ID Scheme for Traceability (CHK091)

**Question**: Esquema de IDs para rastreabilidade de requisitos?

**Decision**: **ID scheme: FR/NFR/AC**

| Prefixo | Tipo | Exemplo |
|---------|------|---------|
| `FR-XXX` | Functional Requirement | FR-001: Company CRUD |
| `NFR-XXX` | Non-Functional Requirement | NFR-001: Response time < 200ms |
| `AC-XXX` | Acceptance Criteria | AC-001: CNPJ válido aceito |
| `BR-XXX` | Business Rule | BR-001: Company deve ter 1+ Owner |

**Rationale**: Padrão amplamente usado. Facilita mapeamento req↔test.

**Implementation**: Adicionar IDs em spec.md. Referenciar IDs em testes (`test_FR001_company_creation`).

---

### DEC-023: Requirements to Test Mapping (CHK095)

**Question**: Criar matriz de mapeamento requisitos ↔ testes?

**Decision**: **Criar matriz req→test**
- Arquivo: `research.md` seção "Traceability Matrix" ou arquivo dedicado
- Formato: tabela FR/AC → Test File → Test Method
- Manter atualizado durante desenvolvimento

**Rationale**: Garante cobertura de requisitos. Identifica gaps de teste.

**Implementation**: Criar seção em research.md após implementação. Template:
```markdown
| Req ID | Descrição | Test File | Status |
|--------|-----------|-----------|--------|
| FR-001 | ... | test_company.py::test_create | ✅ |
```

---

## Open Questions (To Be Resolved)

*(Todas as questões originais foram resolvidas nas decisões acima)*
