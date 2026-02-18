# Quickstart: Unificação de Perfis (Profile Unification)

**Feature**: 010-profile-unification | **Date**: 2026-02-18
**Spec**: [spec.md](spec.md) | **Data Model**: [data-model.md](data-model.md) | **Research**: [research.md](research.md)

---

## 1. Environment Setup

```bash
# Navigate to project directory
cd 18.0

# Start services (Odoo + PostgreSQL + Redis)
docker compose up -d

# Verify services are running
docker compose ps

# Tail Odoo logs
docker compose logs -f odoo
```

**Ports**: Odoo `8069`, PostgreSQL `5432`, Redis `6379`
**Database**: `realestate` | **User**: `admin` / `admin`

---

## 2. Implementation Order

Execute phases sequentially — each step depends on the previous one.

### Phase 1: Schema Creation (6 steps)

| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 1.1 | Add `validate_document()`, `normalize_document()`, `is_cpf()`, `is_cnpj()` | `utils/validators.py` | — |
| 1.2 | Create `thedevkitchen.profile.type` model | `models/profile_type.py` | — |
| 1.3 | Create profile type seed data | `data/profile_type_data.xml` | 1.2 |
| 1.4 | Create `thedevkitchen.estate.profile` model | `models/profile.py` | 1.1, 1.2 |
| 1.5 | Add ACLs + record rules | `security/ir.model.access.csv`, `security/record_rules.xml` | 1.2, 1.4 |
| 1.6 | Add `PROFILE_CREATE_SCHEMA`, `PROFILE_UPDATE_SCHEMA` | `controllers/utils/schema.py` | 1.1 |

### Phase 2: Controller Creation (3 steps)

| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 2.1 | Create `profile_api.py` (6 endpoints) | `controllers/profile_api.py` | Phase 1 |
| 2.2 | Modify agent creation to auto-create profile | `controllers/agent_api.py` | 1.4 |
| 2.3 | Modify invite flow to accept `profile_id` | `thedevkitchen_user_onboarding/controllers/invite_controller.py`, `services/invite_service.py` | 1.4 |

### Phase 3: Cleanup (6 steps)

| # | Task | File(s) | Depends On |
|---|------|---------|------------|
| 3.1 | Migrate `lease.tenant_id` → `profile_id` | `models/lease.py`, `controllers/lease_api.py`, `controllers/utils/schema.py` | Phase 2 |
| 3.2 | Migrate `property.tenant_id` → `profile_id` | `models/property.py` | Phase 2 |
| 3.3 | Migrate `company.tenant_ids` → `profile_ids` | `models/company.py` | Phase 2 |
| 3.4 | Add `profile_id` FK to agent + sync in `create()` | `models/agent.py` | 1.4 |
| 3.5 | Remove tenant model + controller + views | `models/tenant.py`, `controllers/tenant_api.py`, `views/tenant_views.xml` | 3.1, 3.2, 3.3 |
| 3.6 | Update `__manifest__.py` + `__init__.py` files | `__manifest__.py`, `models/__init__.py`, `controllers/__init__.py` | 3.5 |

---

## 3. File Scaffolding

### 3.1 New Files to Create

```
18.0/extra-addons/quicksol_estate/
├── models/
│   ├── profile_type.py          # NEW (~60 LOC)
│   └── profile.py               # NEW (~150 LOC)
├── controllers/
│   └── profile_api.py           # NEW (~400 LOC)
├── data/
│   └── profile_type_data.xml    # NEW (~80 LOC)
└── tests/unit/
    ├── test_profile_validations_unit.py    # NEW (~150 LOC)
    ├── test_profile_authorization_unit.py  # NEW (~100 LOC)
    └── test_profile_sync_unit.py          # NEW (~80 LOC)
```

### 3.2 Files to Modify

```
models/__init__.py               # Add: from . import profile_type, profile
controllers/__init__.py          # Add: from . import profile_api
controllers/utils/schema.py      # Add: PROFILE_CREATE/UPDATE_SCHEMA
utils/validators.py              # Add: 4 functions
models/agent.py                  # Add: profile_id FK
models/lease.py                  # Change: tenant_id → profile_id
models/property.py               # Change: tenant_id → profile_id
models/company.py                # Change: tenant_ids → profile_ids
controllers/agent_api.py         # Extend: auto-create profile
controllers/lease_api.py         # Change: tenant refs → profile
security/ir.model.access.csv     # Add profile + profile_type ACLs
security/record_rules.xml        # Add profile rules, update portal lease rule
__manifest__.py                  # Add data/profile_type_data.xml
```

### 3.3 Files to Delete

```
models/tenant.py                 # Replaced by profile.py
controllers/tenant_api.py        # Replaced by profile_api.py
views/tenant_views.xml           # Headless — no dedicated UI
```

---

## 4. Key Patterns to Follow

### 4.1 Controller — Triple Auth Decorators (ADR-011)

```python
from odoo import http
from odoo.http import request, Response
from odoo.addons.thedevkitchen_apigateway.decorators import (
    require_jwt, require_session, require_company
)
import json

class ProfileApiController(http.Controller):

    @http.route('/api/v1/profiles', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_profiles(self, **kwargs):
        ...
```

### 4.2 `company_ids` Query Param Validation (from `property_api.py`)

```python
company_ids_param = kwargs.get('company_ids')
if not company_ids_param:
    return error_response(400, 'company_ids parameter is required')

try:
    requested_company_ids = [int(cid.strip()) for cid in company_ids_param.split(',')]
except ValueError:
    return error_response(400, 'Invalid company_ids format')

if request.user_company_ids:
    unauthorized = [cid for cid in requested_company_ids
                    if cid not in request.user_company_ids]
    if unauthorized:
        return error_response(403, f'Access denied to company IDs: {unauthorized}')
```

### 4.3 `company_id` in POST Body Validation (from `tenant_api.py`)

```python
if 'company_id' not in data or data['company_id'] is None:
    return error_response(400, 'Missing or invalid company_id')
company_id = int(data['company_id'])

user = request.env.user
if not user.has_group('base.group_system'):
    allowed_ids = set(user.estate_company_ids.ids)
    if company_id not in allowed_ids:
        return error_response(403, 'Access denied to company_id')
```

### 4.4 Schema Validation (from `schema.py`)

```python
PROFILE_CREATE_SCHEMA = {
    'required': ['name', 'company_id', 'document', 'email', 'birthdate', 'profile_type'],
    'optional': ['phone', 'mobile', 'occupation', 'hire_date'],
    'types': {
        'name': str, 'company_id': int, 'document': str,
        'email': str, 'birthdate': str, 'profile_type': str,
        'phone': str, 'mobile': str, 'occupation': str, 'hire_date': str,
    },
    'constraints': {
        'document': lambda v: validators.validate_document(
            validators.normalize_document(v)) if v else False,
        'email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else False,
    }
}
```

### 4.5 HATEOAS Response (from `utils/responses.py`)

```python
from ..utils.responses import success_response, error_response, build_hateoas_links

links = build_hateoas_links(
    base_url='/api/v1/profiles',
    resource_id=profile.id,
    relations={
        'invite': '/api/v1/users/invite',
        'company': f'/api/v1/companies/{profile.company_id.id}',
    }
)
# For agent-type profiles, add:
# 'agent': f'/api/v1/agents/{agent.id}'
```

### 4.6 RBAC Authorization Matrix

```python
PROFILE_AUTHORIZATION = {
    'owner':    ['owner', 'director', 'manager', 'agent', 'prospector',
                 'receptionist', 'financial', 'legal', 'portal'],
    'director': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
    'manager':  ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
    'agent':    ['owner', 'portal'],
}
```

### 4.7 Soft Delete Pattern (ADR-015)

```python
# Controller (DELETE endpoint → soft delete)
profile.write({
    'active': False,
    'deactivation_date': fields.Datetime.now(),
    'deactivation_reason': data.get('reason', ''),
    'updated_at': fields.Datetime.now(),
})

# Cascade to agent extension
if profile.profile_type_id.code == 'agent':
    agent = request.env['real.estate.agent'].sudo().search(
        [('profile_id', '=', profile.id)], limit=1)
    if agent:
        agent.write({'active': False, ...})
```

---

## 5. Validation Quick Reference

### 5.1 Validators to Implement (`utils/validators.py`)

```python
import re

def normalize_document(document: str) -> str:
    """'123.456.789-01' → '12345678901'"""
    return re.sub(r'[^0-9]', '', document) if document else ''

def is_cpf(document: str) -> bool:
    """Validate CPF checksum (11 digits, no formatting)."""
    if len(document) != 11 or document == document[0] * 11:
        return False
    # Checksum algorithm (two verification digits)
    ...

def is_cnpj(document: str) -> bool:
    """Validate CNPJ checksum (14 digits). Delegates to existing validate_cnpj()."""
    if len(document) != 14:
        return False
    return validate_cnpj(document)

def validate_document(document: str) -> bool:
    """Dispatch: 11 digits → is_cpf(), 14 digits → is_cnpj(), else False."""
    if len(document) == 11:
        return is_cpf(document)
    elif len(document) == 14:
        return is_cnpj(document)
    return False
```

---

## 6. Registration Checklist

After creating new files, register them:

### `models/__init__.py` — add imports

```python
from . import profile_type          # Feature 010
from . import profile               # Feature 010
# ... (keep existing imports)
# from . import tenant              # REMOVE (Feature 010)
```

### `controllers/__init__.py` — add import

```python
from . import profile_api           # Feature 010
# from . import tenant_api          # REMOVE (Feature 010)
```

### `__manifest__.py` — add to `data` list

```python
'data': [
    # Security (first)
    'security/groups.xml',
    ...
    # Data — add AFTER groups.xml
    'data/profile_type_data.xml',    # Feature 010: Profile type seed data
    ...
    # Views — REMOVE tenant_views.xml
    # 'views/tenant_views.xml',      # REMOVED (Feature 010)
]
```

---

## 7. Testing Quick Commands

```bash
# Run unit tests for profile module
docker compose exec odoo odoo -d realestate \
  --test-enable --stop-after-init \
  -i quicksol_estate \
  --test-tags /quicksol_estate:test_profile

# Run E2E API tests (from project root)
cd integration_tests
bash test_us10_s1_create_profile.sh

# Access PostgreSQL directly
docker compose exec db psql -U odoo -d realestate

# Verify profile type seed data
docker compose exec db psql -U odoo -d realestate \
  -c "SELECT * FROM thedevkitchen_profile_type;"

# Verify profile table structure
docker compose exec db psql -U odoo -d realestate \
  -c "\d thedevkitchen_estate_profile"

# Check record rules
docker compose exec db psql -U odoo -d realestate \
  -c "SELECT name, domain_force FROM ir_rule WHERE name LIKE '%Profile%';"

# Monitor Redis sessions
docker compose exec redis redis-cli MONITOR
```

---

## 8. Common Pitfalls

| # | Pitfall | Prevention |
|---|---------|------------|
| 1 | Forgetting `@require_company` decorator | Use all 3 decorators on every private endpoint (ADR-011) |
| 2 | Using `validate_docbr` directly in controllers | Always use `utils/validators.py` functions (constitution) |
| 3 | Creating profile without agent extension for `profile_type='agent'` | Wrap both creates in atomic transaction |
| 4 | Missing `noupdate="1"` on seed data XML | Profile types are immutable seed data — always `noupdate="1"` |
| 5 | Using `company_id` from header instead of body on POST | Profile uses body `company_id` (spec D5.1) |
| 6 | Forgetting to update `updated_at` in `write()` | Override `write()` to set `updated_at = fields.Datetime.now()` |
| 7 | Not normalizing document before uniqueness check | Always `normalize_document()` before `validate_document()` |
| 8 | Removing tenant before migrating all FKs | Phase 3 order: migrate lease/property/company FKs → then remove tenant |
| 9 | Using `create_date`/`write_date` instead of `created_at`/`updated_at` | Spec D10 mandates explicit audit field names |
| 10 | Lease `tenant_id` → `profile_id` without updating `_compute_name` | Both model + computed field depend on the FK name |
