# Phase 0 Research: Unificação de Perfis (Profile Unification)

**Feature**: 010-profile-unification | **Date**: 2026-02-18
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## 1. Codebase Audit — Current State of Tenant & Agent

### 1.1 `real.estate.tenant` (tenant.py — 35 LOC)

**Location**: `18.0/extra-addons/quicksol_estate/models/tenant.py`

| Field | Type | Required | Constraint | Notes |
|-------|------|----------|------------|-------|
| `name` | Char | ✅ | — | Tenant name |
| `document` | Char | ✅ | `UNIQUE(document)` ⚠️ | **GLOBAL unique — blocks multi-tenancy** |
| `partner_id` | Many2one(`res.partner`) | ❌ | — | Portal access bridge |
| `phone` | Char | ❌ | — | — |
| `email` | Char | ❌ | email regex | Inline validation (not via centralized validators) |
| `company_ids` | Many2many(`thedevkitchen.estate.company`) | ❌ | — | Via `thedevkitchen_company_tenant_rel` join table |
| `leases` | One2many(`real.estate.lease`) | — | — | Reverse FK |
| `profile_picture` | Binary | ❌ | — | — |
| `occupation` | Char | ❌ | — | — |
| `birthdate` | Date | ❌ | — | ⚠️ Not required in current model |
| `active` | Boolean | ✅ | default=True | Soft delete (ADR-015) |
| `deactivation_date` | Datetime | ❌ | — | — |
| `deactivation_reason` | Text | ❌ | — | — |

**Critical Issue**: `_sql_constraints = [('document_unique', 'unique(document)', ...)]` — **global unique on document**, not scoped to company. This blocks the same person from being a tenant in 2 different companies.

**Inheritance**: None (no `_inherit`, no `mail.thread`).

---

### 1.2 `real.estate.agent` (agent.py — 611 LOC)

**Location**: `18.0/extra-addons/quicksol_estate/models/agent.py`

#### Core Fields (overlap with future profile)

| Field | Type | Required | Constraint | Profile Equivalent |
|-------|------|----------|------------|-------------------|
| `name` | Char | ✅ | — | `name` |
| `cpf` | Char(14) | ✅ | `UNIQUE(cpf, company_id)` ✅ | `document` |
| `email` | Char | ❌ | regex in `_check_email_format` | `email` |
| `phone` | Char(20) | ❌ | phonenumbers lib | `phone` |
| `mobile` | Char(20) | ❌ | phonenumbers lib | `mobile` |
| `company_id` | Many2one | ✅ | `ondelete='restrict'` | `company_id` |
| `company_ids` | Many2many | — | **deprecated** | — (remove) |
| `user_id` | Many2one(`res.users`) | ❌ | `UNIQUE(user_id, company_id)` | via `partner_id` |
| `active` | Boolean | ✅ | default=True | `active` |
| `hire_date` | Date | ✅ | default=today | `hire_date` |
| `deactivation_date` | Date | ❌ | — | `deactivation_date` |
| `deactivation_reason` | Text | ❌ | — | `deactivation_reason` |
| `profile_picture` | Binary | ❌ | — | `profile_picture` |

#### Agent-Specific Fields (stay in agent)

| Field | Type | Notes |
|-------|------|-------|
| `creci` | Char(50) | CRECI license |
| `creci_normalized` | Char(20) | Computed, stored |
| `creci_state` | Char(2) | Computed |
| `creci_number` | Char(8) | Computed |
| `bank_name` | Char | Financial |
| `bank_branch` | Char(10) | Financial |
| `bank_account` | Char(20) | Financial |
| `bank_account_type` | Selection | Financial |
| `pix_key` | Char | Financial |
| `properties` | One2many | Legacy |
| `agency_name` | Char | Legacy |
| `years_experience` | Integer | Legacy |
| `agent_property_ids` | Computed M2M | Assignments |
| `assigned_property_count` | Computed Int | Assignments |
| `assignment_ids` | One2many | Assignments |
| `commission_rule_ids` | One2many | Commissions |
| `commission_transaction_ids` | One2many | Commissions |
| `total_sales_count` | Computed | Performance |
| `total_commissions` | Computed | Performance |
| `average_commission` | Computed | Performance |
| `active_properties_count` | Computed | Performance |

**Constraint**: `UNIQUE(cpf, company_id)` — correct compound unique, scoped to company. ✅

**Validation Pattern**: Uses `validate_docbr.CPF` directly in `_check_cpf_format()` (line ~310). Does NOT use centralized `utils/validators.py`. Constitution mandates centralized validators.

**Create Override**: Lines 465-490 — handles `user_id` sync, `company_ids` migration to `company_id`. Will need to be extended to auto-create profile.

**Write Override**: Lines 492-520 — handles `company_ids` sync from `company_id`. May need sync to profile.

**Inheritance**: `mail.thread`, `mail.activity.mixin` — tracking enabled.

---

## 2. Dependency Map — What References Tenant

### 2.1 Models

| Model | File | Field | FK Type | Impact |
|-------|------|-------|---------|--------|
| `real.estate.lease` | `models/lease.py:15` | `tenant_id` | Many2one, required | **Must change** → `profile_id` |
| `real.estate.property` | `models/property.py:217` | `tenant_id` | Many2one, optional | **Must change** → `profile_id` |
| `thedevkitchen.estate.company` | `models/company.py:59` | `tenant_ids` | Many2many via `thedevkitchen_company_tenant_rel` | **Must remove** + add `profile_ids` |
| `thedevkitchen.estate.company` | `models/company.py:73` | `tenant_count` | Computed | **Must change** → `profile_count` (or separate counts) |

### 2.2 Controllers

| Controller | File | LOC | Endpoints | Impact |
|------------|------|-----|-----------|--------|
| `TenantApiController` | `controllers/tenant_api.py` | 550 | 5 endpoints (CRUD + leases) | **DELETE entirely** |
| `LeaseApiController` | `controllers/lease_api.py` | 620 | CRUD + lifecycle | **Modify**: `tenant_id` refs → `profile_id` |
| — | `controllers/lease_api.py:237` | — | create_lease | `browse('real.estate.tenant')` → profile |
| — | `controllers/lease_api.py:75,91,98-99` | — | serialize | `tenant_id` links/fields |
| — | `controllers/lease_api.py:155-157` | — | list_leases | `tenant_id` filter param |

### 2.3 Security

| File | Line(s) | Records | Impact |
|------|---------|---------|--------|
| `ir.model.access.csv` | 7,20,39,52,72,92,108 | 7 ACL rows for `model_real_estate_tenant` | **Remove** + add `model_thedevkitchen_estate_profile` |
| `record_rules.xml` | ~488 | 1 rule (`rule_tenant_multi_company`) — user+manager only | **Insufficient** — profile needs 6+ rules like other models |

### 2.4 Views

| File | Purpose | Impact |
|------|---------|--------|
| `views/tenant_views.xml` | List, form, search views | **Remove** (headless architecture) |

### 2.5 Schema Validation

| File | Schema | Impact |
|------|--------|--------|
| `controllers/utils/schema.py:112-140` | `TENANT_CREATE_SCHEMA` | **Replace** with `PROFILE_CREATE_SCHEMA` |
| `controllers/utils/schema.py:143-155` | `TENANT_UPDATE_SCHEMA` | **Replace** with `PROFILE_UPDATE_SCHEMA` |
| `controllers/utils/schema.py:158-175` | `LEASE_CREATE_SCHEMA` | **Modify**: `tenant_id` → `profile_id` |

### 2.6 __manifest__.py

| Line | Entry | Impact |
|------|-------|--------|
| `data/` | — | **Add**: `data/profile_type_data.xml` |
| `views/` | `'views/tenant_views.xml'` | **Remove** |
| `views/` | — | **Add**: `'views/profile_type_views.xml'` (optional admin view) |

### 2.7 Feature 009 (thedevkitchen_user_onboarding)

| File | LOC | Integration Point | Impact |
|------|-----|--------------------|--------|
| `controllers/invite_controller.py` | 432 | Lines 42-48: requires `name`, `email`, `document`, `profile` | **Modify**: accept optional `profile_id`; if provided, skip cadastral fields |
| `controllers/invite_controller.py` | — | Line 84: gets `company_id` from `X-Company-ID` header | Note: invite still uses header (profile uses body) |
| `services/invite_service.py` | 297 | Lines 87-101: `create_invited_user()` creates `res.users` | **Modify**: link to existing profile via `partner_id` |
| `services/invite_service.py` | — | Lines 143-224: `create_portal_user()` creates `res.users` + `real.estate.tenant` | **Modify**: create `res.users` + link to existing profile (no tenant creation) |
| `services/invite_service.py` | — | Line 177: `self.env['real.estate.tenant'].sudo().search(...)` | **Remove**: tenant existence check → profile existence check |

---

## 3. Validators Gap Analysis

### 3.1 Current State (`utils/validators.py` — 239 LOC)

| Function | Exists | Used By |
|----------|--------|---------|
| `validate_cnpj(cnpj)` | ✅ | `company.py` (indirectly), `schema.py` |
| `format_cnpj(cnpj)` | ✅ | — |
| `validate_email_format(email)` | ✅ | `tenant_api.py`, `owner_api.py` |
| `validate_creci(creci, state_code)` | ✅ | — (agent uses `CreciValidator` service instead) |
| `validate_phone(phone)` | ✅ | — |
| `format_phone(phone)` | ✅ | — |
| `validate_document(document)` | ❌ MISSING | Referenced by `schema.py:125` (`TENANT_CREATE_SCHEMA`), `tenant_api.py:223` |
| `normalize_document(document)` | ❌ MISSING | Referenced by `tenant_api.py:222` |
| `is_cpf(document)` | ❌ MISSING | Constitution mandates it |
| `is_cnpj(document)` | ❌ MISSING | Constitution mandates it |

### 3.2 Validation Approaches by Model

| Model | Document Validation | Email Validation | Phone Validation |
|-------|-------------------|------------------|------------------|
| `tenant.py` | Inline regex (email only) | Inline regex | — |
| `agent.py` | `validate_docbr.CPF` (direct import) | Inline regex | `phonenumbers` lib |
| `schema.py` | `validators.validate_document(v)` | Inline `'@' in v` | — |
| `invite_service.py` | `validate_docbr.CPF` (direct), `validators.validate_cnpj` (fallback) | — | — |

**Finding**: There are 3 different validation approaches for documents. Constitution mandates centralized `utils/validators.py`. Feature 010 Phase 1 must implement:
- `validate_document(doc)` → dispatches to `is_cpf`/`is_cnpj` based on digit count
- `normalize_document(doc)` → strips formatting to digits only
- `is_cpf(doc)` → validates CPF checksum (replace `validate_docbr` usage)
- `is_cnpj(doc)` → delegates to existing `validate_cnpj()`

---

## 4. API Pattern Analysis

### 4.1 `company_ids` Query Parameter Pattern

**Reference implementation**: `property_api.py` lines 28-50

```python
# 1. Required parameter
company_ids_param = kwargs.get('company_ids')
if not company_ids_param:
    return error_response(400, 'company_ids parameter is required')

# 2. Parse comma-separated integers
try:
    requested_company_ids = [int(cid.strip()) for cid in company_ids_param.split(',')]
except ValueError:
    return error_response(400, 'Invalid company_ids format...')

# 3. Validate against user's allowed companies
if request.user_company_ids:  # Not admin
    unauthorized = [cid for cid in requested_company_ids if cid not in request.user_company_ids]
    if unauthorized:
        return error_response(403, f'Access denied to company IDs: {unauthorized}...')
```

**Same pattern in**: `tenant_api.py` lines 101-122 (same logic, slightly different error responses via `util_error`).

**Profile API must follow this exact pattern** for `GET /api/v1/profiles?company_ids=63,64`.

### 4.2 `company_id` in POST Body Pattern

**Reference implementation**: `tenant_api.py` lines 210-220

```python
# 1. Required in body
if 'company_id' not in data or data['company_id'] is None:
    return error_response(400, 'Missing or invalid tenant company_id')
company_id = int(data['company_id'])

# 2. RBAC validation
if not user.has_group('base.group_system'):
    allowed_ids = set(user.estate_company_ids.ids)
    if company_id not in allowed_ids:
        return error_response(403, 'Access denied to company_id')
```

**Profile API `POST` must follow this pattern** for `company_id` in request body.

### 4.3 HATEOAS Links Pattern

**Reference**: `utils/responses.py` + `tenant_api.py` serializer

```python
# Per-resource links
links = build_hateoas_links(
    base_url='/api/v1/tenants',
    resource_id=tenant.id,
    relations={'leases': '/leases'}
)

# Pagination links
links = build_pagination_links(
    base_url='/api/v1/tenants',
    page=page,
    total_pages=total_pages,
)
```

### 4.4 Schema Validation Pattern

**Reference**: `schema.py` `SchemaValidator` class

```python
TENANT_CREATE_SCHEMA = {
    'required': ['name', 'company_id', 'document', 'phone', 'email', 'birthdate'],
    'optional': ['occupation'],
    'types': { 'name': str, 'company_id': int, ... },
    'constraints': {
        'document': lambda v: validators.validate_document(v) if v else False,
        'email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else False,
    }
}
```

Profile schemas must follow this exact structure.

### 4.5 Agent Create Pattern (modify for auto-profile creation)

**Reference**: `agent_api.py` lines 146-230

```python
# 1. RBAC check (managers + admins only)
# 2. Parse JSON body
# 3. Schema validation (validate_agent_create)
# 4. Prepare agent_vals dict
# 5. Validate company access (CompanyValidator)
# 6. Agent.sudo().create(agent_vals)
# 7. Serialize response with HATEOAS links
```

After Feature 010: Step 6 must also create profile + link via `profile_id`.

---

## 5. Security Audit

### 5.1 ACLs for Tenant (to be replaced with Profile)

| Group | Read | Write | Create | Unlink |
|-------|------|-------|--------|--------|
| Owner | ✅ | ✅ | ✅ | ✅ |
| Receptionist | ✅ | ✅ | ✅ | ❌ |
| Manager | ✅ | ✅ | ✅ | ✅ |
| System Admin | ✅ | ✅ | ✅ | ✅ |
| Company Manager | ✅ | ✅ | ✅ | ✅ |
| Company User | ✅ | ✅ | ✅ | ❌ |
| Agent | ✅ | ❌ | ❌ | ❌ |

Profile ACLs should mirror these with additional rows for `model_thedevkitchen_profile_type` (read-only for all, full CRUD for system admin).

### 5.2 Record Rules

**Current tenant isolation**: Has only 1 record rule (`rule_tenant_multi_company`) covering `group_real_estate_user` + `group_real_estate_manager`. Missing rules for: owner, agent, receptionist, portal, financial, legal. By comparison, property has 8 rules, lease has 7, sale has 6, agent has 4.

**Profile must have comprehensive record rules** matching the coverage of other models:
- Owner: `[('company_id', 'in', user.estate_company_ids.ids)]` — full CRUD
- Manager: `[('company_id', 'in', user.estate_company_ids.ids)]` — full CRUD
- Agent: `[('company_id', 'in', user.estate_company_ids.ids)]` — read only
- Receptionist: `[('company_id', 'in', user.estate_company_ids.ids)]` — read/write/create
- Portal: `[('partner_id', '=', user.partner_id.id)]` — read own record only
- Multi-company: `[('company_id', 'in', user.estate_company_ids.ids)]` — user+manager groups

**Also impacted**: `rule_portal_own_leases` (line ~455) uses `('tenant_id.partner_id', '=', user.partner_id.id)` — must change to `('profile_id.partner_id', '=', user.partner_id.id)`.

### 5.3 Auth Decorators

All profile endpoints must use triple decorators per ADR-011:
```python
@http.route('/api/v1/profiles', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
```

---

## 6. Groups XML Analysis

**File**: `security/groups.xml` — 95 lines

| XML ID | Group Name | Implied IDs | Level |
|--------|------------|-------------|-------|
| `group_real_estate_user` | Company User | `base.group_user` | base |
| `group_real_estate_manager` | Company Manager | `group_real_estate_user` | admin |
| `group_real_estate_director` | Director | `group_real_estate_manager` | admin |
| `group_real_estate_owner` | Owner | `base.group_user` | admin |
| `group_real_estate_receptionist` | Receptionist | `base.group_user` | operational |
| `group_real_estate_financial` | Financial | `group_real_estate_user` | operational |
| `group_real_estate_legal` | Legal | `group_real_estate_user` | operational |
| `group_real_estate_agent` | Agent | `group_real_estate_user` | operational |
| `group_real_estate_prospector` | Prospector | `group_real_estate_user` | operational |
| `group_real_estate_portal_user` | Portal User | `base.group_portal` | external |

These 9 groups + their XML IDs map directly to the seed data for `thedevkitchen.profile.type.group_xml_id`.

---

## 7. Data Files Audit

### 7.1 Existing data/ directory

```
data/
├── agent_seed.xml           ← Agent demo data
├── amenity_data.xml
├── api_endpoints.xml
├── company_seed.xml         ← Company demo data
├── demo_users.xml           ← User demo data
├── lease_cron.xml
├── location_types.xml
├── oauth2_seed.xml
├── property_data.xml
├── property_demo_data.xml
├── property_type_data.xml   ← ⚠️ Name taken! Profile type must use different name
├── states.xml
├── system_parameters.xml
├── user_auth_endpoints_data.xml
```

**Name collision**: `property_type_data.xml` already exists. New file must be named `profile_type_data.xml` (as specified in plan.md). ✅

### 7.2 __manifest__.py data loading order

Security files load first → data files → views. Profile type seed data must load **after** `groups.xml` (references group XML IDs) but **before** any views that reference profile types.

Recommended insertion point in `__manifest__.py`:
```python
'data': [
    # Security files (first)
    'security/groups.xml',
    ...
    # Data files
    'data/profile_type_data.xml',   # ← NEW: After groups.xml, before views
    ...
]
```

---

## 8. Impact Summary — Files That Must Change

### 8.1 New Files

| File | Purpose | Est. LOC |
|------|---------|----------|
| `models/profile_type.py` | `thedevkitchen.profile.type` lookup model | ~60 |
| `models/profile.py` | `thedevkitchen.estate.profile` unified model | ~150 |
| `controllers/profile_api.py` | 6 REST endpoints | ~400 |
| `data/profile_type_data.xml` | 9 profile type seed records | ~80 |
| `views/profile_type_views.xml` | Admin tree/form (optional) | ~50 |
| `tests/unit/test_profile_validations_unit.py` | Constraints, validators | ~150 |
| `tests/unit/test_profile_authorization_unit.py` | RBAC matrix | ~100 |
| `tests/unit/test_profile_sync_unit.py` | Agent ↔ profile sync | ~80 |

### 8.2 Modified Files

| File | Changes | Risk |
|------|---------|------|
| `models/__init__.py` | Add imports for `profile_type`, `profile` | Low |
| `models/agent.py` | Add `profile_id` FK, extend `create()` override | **Medium** — 611 LOC, complex create/write |
| `models/lease.py` | `tenant_id` → `profile_id` | **Medium** — affects `_compute_name`, constraints |
| `models/property.py` | `tenant_id` → `profile_id` | Low — optional field |
| `models/company.py` | `tenant_ids` → `profile_ids`, counts | Medium |
| `controllers/__init__.py` | Remove `tenant_api`, add `profile_api` | Low |
| `controllers/agent_api.py` | Auto-create profile in `create_agent()` | **Medium** — 1,463 LOC |
| `controllers/lease_api.py` | `tenant_id` refs → `profile_id` | Medium — 620 LOC |
| `controllers/utils/schema.py` | Add `PROFILE_*_SCHEMA`, modify `LEASE_*_SCHEMA` | Medium |
| `utils/validators.py` | Add `validate_document()`, `normalize_document()`, `is_cpf()`, `is_cnpj()` | Low — additive |
| `utils/__init__.py` | No change (already exports validators) | None |
| `security/ir.model.access.csv` | Remove tenant ACLs + add profile/profile_type ACLs | Medium |
| `security/record_rules.xml` | Remove `rule_tenant_multi_company`, add 6+ profile rules (owner/manager/agent/receptionist/portal/multi-company) + update `rule_portal_own_leases` (`tenant_id` → `profile_id`) | Medium |
| `__manifest__.py` | Add `profile_type_data.xml`, remove `tenant_views.xml`, add `profile_type_views.xml` | Low |

### 8.3 Removed Files

| File | Reason |
|------|--------|
| `models/tenant.py` | Replaced by `profile.py` (portal type) |
| `controllers/tenant_api.py` | Replaced by `profile_api.py` |
| `views/tenant_views.xml` | Headless architecture — no dedicated UI |

### 8.4 Feature 009 Modified Files

| File | Changes | Risk |
|------|---------|------|
| `thedevkitchen_user_onboarding/controllers/invite_controller.py` | Accept optional `profile_id`; if present, use profile data instead of body fields | Medium |
| `thedevkitchen_user_onboarding/services/invite_service.py` | `create_portal_user()`: stop creating `real.estate.tenant`, link to existing profile | **High** — 297 LOC, dual record creation logic |

---

## 9. Integration Tests Impact

### 9.1 Existing Tests That Reference Tenant

```bash
# Shell scripts that create/use tenants
integration_tests/test_us8_s1_tenant_crud.sh        # ← Must be adapted or replaced
integration_tests/test_us8_s2_lease_lifecycle.sh     # ← Uses tenant_id in lease creation
integration_tests/test_us8_s3_sale_management.sh     # ← May reference tenant
integration_tests/test_us8_s4_tenant_lease_history.sh # ← Direct tenant API calls
```

Since this is a dev environment:
- Existing tenant E2E tests in `test_us8_*` will **break** after cleanup. They must be updated to use `/api/v1/profiles` instead of `/api/v1/tenants`.
- New E2E tests (`test_us10_*`) should be created first, then `test_us8_*` migrated or marked as superseded.

### 9.2 Existing Unit Tests

No unit tests currently exist for `tenant.py` (35 LOC, no complex logic). Agent unit tests exist in `tests/unit/test_agent_unit.py`.

---

## 10. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Agent `create()` override is complex (590-520 LOC) — adding profile creation may break | High | Add profile creation as first step in overridden `create()`, wrapped in try/except. If profile creation fails, don't create agent. |
| Lease FK change (`tenant_id` → `profile_id`) affects 5+ locations in `lease_api.py` | Medium | Mechanical replacement — search and replace with verification. |
| Feature 009 `create_portal_user()` tightly coupled to `real.estate.tenant` | High | Refactor to accept `profile_id`: if profile exists, skip tenant creation. If no profile exists, create profile first, then link. |
| `validate_document`/`normalize_document` are referenced but don't exist | Medium | Implement in Phase 1 before any model that uses them. |
| Schema `LEASE_CREATE_SCHEMA` references `tenant_id` — must be updated atomically with lease model | Medium | Update schema + model + controller in same commit. |
| Agent uses `validate_docbr.CPF` directly — inconsistent with centralized validators | Low | Not an immediate blocker, but should be refactored to use `utils/validators.is_cpf()` in Phase 1. |
| Company model has `tenant_ids` (M2M) and `tenant_count` — computed field will break | Medium | Replace with `profile_ids` M2M and `profile_count` computed, or remove if not needed in API. |

---

## 11. Technical Decisions Confirmed by Research

| Decision | Research Finding | Confidence |
|----------|-----------------|------------|
| D3: Tenant fully absorbed | tenant.py is 35 LOC, no complex logic, no inheritance | ✅ High |
| D5.1: company_id in body | `TENANT_CREATE_SCHEMA` already uses this pattern | ✅ High |
| D5.2: company_ids query param | `property_api.py` and `tenant_api.py` both implement this | ✅ High |
| D9: birthdate required all profiles | Currently NOT required in tenant.py — this is a new enforcement | ⚠️ Confirmed new requirement |
| D11: Reuse validators.py | Functions referenced but NOT implemented — must create | ⚠️ Must implement first |
| D12: No migration | Dev environment confirmed — no production data | ✅ High |

---

## 12. Implementation Order (Validated)

Based on dependency analysis, the correct implementation order is:

1. **`utils/validators.py`** — Add missing functions first (depended on by everything)
2. **`models/profile_type.py`** + `data/profile_type_data.xml` — No dependencies
3. **`models/profile.py`** — Depends on profile_type + validators
4. **`security/`** — ACLs + record rules for new models
5. **`controllers/utils/schema.py`** — Add `PROFILE_*_SCHEMA`
6. **`controllers/profile_api.py`** — New endpoints
7. **`models/agent.py`** — Add `profile_id` FK + extend `create()` override
8. **`controllers/agent_api.py`** — Auto-create profile on agent creation
9. **`models/lease.py`** + `controllers/lease_api.py` + `schema.py` — Atomic `tenant_id` → `profile_id`
10. **`models/property.py`** + `models/company.py`** — Update `tenant_id` refs
11. **Remove**: `tenant.py`, `tenant_api.py`, `tenant_views.xml`, tenant ACLs
12. **Feature 009**: Update `invite_controller.py` + `invite_service.py`
13. **`__manifest__.py`** — Update data/views lists (last, after all files exist)

---

## 13. Open Questions for Implementation

| # | Question | Default Answer |
|---|----------|---------------|
| Q1 | Should `profile_type_views.xml` include form + tree + search, or just tree + form? | Tree + form (admin only, Technical menu) |
| Q2 | Should agent's `_check_cpf_format()` be refactored to use `validators.is_cpf()` now or later? | Now (Phase 1) — while touching agent.py |
| Q3 | Should `real.estate.lease.tenant_id` be renamed to `profile_id` or kept as `tenant_id` with changed FK target? | Rename to `profile_id` — cleaner, avoids confusion |
| Q4 | Should existing `test_us8_*` shell tests be adapted or left as-is (broken) until Feature 010 E2E tests replace them? | Leave as-is, create `test_us10_*` tests, mark `test_us8_*` as superseded |
