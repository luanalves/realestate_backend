# Data Model: Unificação de Perfis (Profile Unification)

**Feature**: 010-profile-unification | **Date**: 2026-02-18
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

---

## 1. Entity-Relationship Diagram

```
                                     ┌─────────────────────────────┐
                                     │      res.partner            │
                                     │  (Odoo core — auto-created) │
                                     ├─────────────────────────────┤
                                     │ id: Integer (PK)            │
                                     │ name: Char                  │
                                     │ email: Char                 │
                                     └────────────▲────────────────┘
                                                  │ partner_id
                                                  │ (optional, auto-created)
                                                  │
┌──────────────────────────────┐     ┌────────────┴────────────────┐     ┌──────────────────────────────┐
│  thedevkitchen.profile.type  │     │ thedevkitchen.estate.profile│     │ thedevkitchen.estate.company │
│  (Lookup Table — 9 records)  │     │ (Unified Profile)           │     │ (Existing)                   │
├──────────────────────────────┤  1  ├─────────────────────────────┤  N  ├──────────────────────────────┤
│ id: Integer (PK)             │◄────│ profile_type_id: FK (req)   │────►│ id: Integer (PK)             │
│ code: Char(30) UNIQUE        │  N  │ company_id: FK (req)        │  1  │ name: Char                   │
│ name: Char(100)              │     │ partner_id: FK (opt)        │     │ cnpj: Char                   │
│ group_xml_id: Char(100)      │     │ name: Char(200) NOT NULL    │     │ ...                          │
│ level: Selection             │     │ document: Char(20) NOT NULL │     └──────────────────────────────┘
│ is_active: Boolean           │     │ document_normalized: Char   │
│ created_at: Datetime         │     │ email: Char(100) NOT NULL   │     ┌──────────────────────────────┐
│ updated_at: Datetime         │     │ phone: Char(20)             │     │   real.estate.agent          │
└──────────────────────────────┘     │ mobile: Char(20)            │     │   (Business Extension)       │
                                     │ occupation: Char(100)       │     ├──────────────────────────────┤
                                     │ birthdate: Date NOT NULL    │  1  │ profile_id: FK → profile     │
                                     │ hire_date: Date             │◄────│ creci: Char(50)              │
                                     │ profile_picture: Binary     │  1  │ bank_name, bank_branch, ...  │
                                     │ active: Boolean             │     │ commission_rule_ids: O2M     │
                                     │ deactivation_date: Datetime │     │ commission_transaction_ids   │
                                     │ deactivation_reason: Text   │     │ assignment_ids: O2M          │
                                     │ created_at: Datetime        │     │ (600+ LOC domain logic)      │
                                     │ updated_at: Datetime        │     └──────────────────────────────┘
                                     │                             │
                                     │ UNIQUE(document,            │     ┌──────────────────────────────┐
                                     │   company_id,               │     │   real.estate.lease          │
                                     │   profile_type_id)          │  1  │   (Existing — FK change)     │
                                     │                             │◄────├──────────────────────────────┤
                                     └─────────────────────────────┘  N  │ profile_id: FK → profile     │
                                                                         │ (was: tenant_id)             │
                                                                         └──────────────────────────────┘
```

---

## 2. Model Definitions

### 2.1 `thedevkitchen.profile.type` — Lookup Table

**Odoo `_name`**: `thedevkitchen.profile.type`
**PostgreSQL table**: `thedevkitchen_profile_type` (auto-generated)
**Purpose**: Normalized catalog of the 9 RBAC profile types (KB-09 §2.1: lookup tables for enums > 5 values)
**Records**: 9 (seed data, `noupdate="1"`)

#### Field Definitions

| # | Field | Odoo Type | PG Type | Required | Default | Index | Constraints | Description |
|---|-------|-----------|---------|----------|---------|-------|-------------|-------------|
| 1 | `id` | Integer | `SERIAL` | auto | auto | PK | — | Surrogate key (KB-09 §3) |
| 2 | `code` | Char(30) | `VARCHAR(30)` | ✅ | — | ✅ UNIQUE | `NOT NULL`, `UNIQUE(code)` | Machine identifier: `owner`, `agent`, `portal`, etc. |
| 3 | `name` | Char(100) | `VARCHAR(100)` | ✅ | — | ❌ | `NOT NULL` | Display name: "Proprietário", "Corretor", etc. |
| 4 | `group_xml_id` | Char(100) | `VARCHAR(100)` | ✅ | — | ❌ | `NOT NULL` | Odoo security group XML ID |
| 5 | `level` | Selection | `VARCHAR` | ✅ | — | ❌ | `NOT NULL` | ADR-019 classification: `admin`, `operational`, `external` |
| 6 | `is_active` | Boolean | `BOOLEAN` | ✅ | `True` | ❌ | — | Soft delete for lookup entries (KB-09 §9) |
| 7 | `created_at` | Datetime | `TIMESTAMP` | auto | `now()` | ❌ | — | Audit: creation timestamp |
| 8 | `updated_at` | Datetime | `TIMESTAMP` | auto | `now()` | ❌ | — | Audit: last modification |

#### SQL Constraints

```python
_sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'O código do tipo de perfil deve ser único.'),
]
```

**PostgreSQL constraint name**: `thedevkitchen_profile_type_code_unique`

#### Odoo Model Declaration

```python
class ProfileType(models.Model):
    _name = 'thedevkitchen.profile.type'
    _description = 'Profile Type (Lookup)'
    _order = 'name asc'
    _rec_name = 'name'

    code = fields.Char('Code', size=30, required=True, index=True, copy=False)
    name = fields.Char('Name', size=100, required=True, translate=True)
    group_xml_id = fields.Char(
        'Security Group XML ID', size=100, required=True,
        help='Full XML ID of the Odoo security group (e.g., quicksol_estate.group_real_estate_owner)'
    )
    level = fields.Selection([
        ('admin', 'Admin'),
        ('operational', 'Operational'),
        ('external', 'External'),
    ], string='Level', required=True, help='ADR-019 hierarchy level')
    is_active = fields.Boolean('Active', default=True)

    # Audit fields (spec D10)
    created_at = fields.Datetime('Created At', default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime('Updated At', default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'O código do tipo de perfil deve ser único.'),
    ]
```

> **⚠️ ADR-004 Conflict Note**: ADR-004 states "use Odoo native audit fields (`create_date`, `write_date`)". Spec D10 overrides this with explicit `created_at`/`updated_at`. The codebase is mixed — `commission_rule.py` and `lead.py` use `create_date`/`write_date`. This data model follows spec D10 as the explicit decision for Feature 010. The `write()` override must update `updated_at` on each save.

---

### 2.2 `thedevkitchen.estate.profile` — Unified Profile

**Odoo `_name`**: `thedevkitchen.estate.profile`
**PostgreSQL table**: `thedevkitchen_estate_profile` (auto-generated)
**Purpose**: Single normalized table for all 9 profile types with compound unique constraint
**Inheritance**: `mail.thread`, `mail.activity.mixin` (tracking enabled, consistent with `real.estate.agent`)

#### Field Definitions

| # | Field | Odoo Type | PG Type | Required | Default | Index | Constraints | Description |
|---|-------|-----------|---------|----------|---------|-------|-------------|-------------|
| 1 | `id` | Integer | `SERIAL` | auto | auto | PK | — | Surrogate key |
| 2 | `profile_type_id` | Many2one → `thedevkitchen.profile.type` | `INTEGER` | ✅ | — | ✅ FK | `NOT NULL`, `ondelete='restrict'` | Profile type reference |
| 3 | `company_id` | Many2one → `thedevkitchen.estate.company` | `INTEGER` | ✅ | — | ✅ FK | `NOT NULL`, `ondelete='restrict'` | Company this profile belongs to |
| 4 | `partner_id` | Many2one → `res.partner` | `INTEGER` | ❌ | auto-created | ✅ FK | `ondelete='restrict'` | Odoo partner bridge (portal/user access) |
| 5 | `name` | Char(200) | `VARCHAR(200)` | ✅ | — | ❌ | `NOT NULL`, tracking | Full legal name |
| 6 | `document` | Char(20) | `VARCHAR(20)` | ✅ | — | ✅ | `NOT NULL`, tracking | CPF or CNPJ (formatted: `123.456.789-01`) |
| 7 | `document_normalized` | Char(14) | `VARCHAR(14)` | computed | — | ✅ stored | `@api.depends('document')` | Digits only (`12345678901`) |
| 8 | `email` | Char(100) | `VARCHAR(100)` | ✅ | — | ❌ | `NOT NULL`, tracking | Contact email |
| 9 | `phone` | Char(20) | `VARCHAR(20)` | ❌ | — | ❌ | — | Phone number |
| 10 | `mobile` | Char(20) | `VARCHAR(20)` | ❌ | — | ❌ | — | Mobile phone |
| 11 | `occupation` | Char(100) | `VARCHAR(100)` | ❌ | — | ❌ | — | Occupation (relevant for portal type) |
| 12 | `birthdate` | Date | `DATE` | ✅ | — | ❌ | `NOT NULL` | Date of birth (required all 9 types — D9) |
| 13 | `hire_date` | Date | `DATE` | ❌ | — | ❌ | — | Hire date (internal profiles) |
| 14 | `profile_picture` | Binary | `BYTEA` | ❌ | — | ❌ | — | Profile photo |
| 15 | `active` | Boolean | `BOOLEAN` | ✅ | `True` | auto | — | Soft delete (ADR-015) |
| 16 | `deactivation_date` | Datetime | `TIMESTAMP` | ❌ | — | ❌ | — | When deactivated |
| 17 | `deactivation_reason` | Text | `TEXT` | ❌ | — | ❌ | — | Why deactivated |
| 18 | `created_at` | Datetime | `TIMESTAMP` | auto | `now()` | ❌ | — | Audit: creation timestamp |
| 19 | `updated_at` | Datetime | `TIMESTAMP` | auto | `now()` | ❌ | — | Audit: last modification |

**Total fields**: 19 (17 stored + 1 computed stored + 1 PK)

#### SQL Constraints

```python
_sql_constraints = [
    ('document_company_type_unique',
     'UNIQUE(document, company_id, profile_type_id)',
     'Este documento já está cadastrado para este tipo de perfil nesta empresa.'),
]
```

**PostgreSQL constraint name**: `thedevkitchen_estate_profile_document_company_type_unique`

This compound unique constraint enables:
- ✅ Same person (document) in **different companies** → 2 separate profiles
- ✅ Same person (document) with **different types** in the same company (e.g., agent + owner)
- ❌ Same person + same company + same type → 409 Conflict

#### Indexes

| Index | Columns | Type | Auto/Manual | Rationale |
|-------|---------|------|-------------|-----------|
| PK | `id` | B-tree UNIQUE | Auto (PK) | — |
| FK | `profile_type_id` | B-tree | Auto (FK) | JOIN performance |
| FK | `company_id` | B-tree | Auto (FK) | JOIN + WHERE filtering |
| FK | `partner_id` | B-tree | Auto (FK) | Partner lookup |
| Explicit | `document` | B-tree | `index=True` | Search by document |
| Computed | `document_normalized` | B-tree | `index=True, store=True` | Search by normalized document |
| Compound UNIQUE | `(document, company_id, profile_type_id)` | B-tree UNIQUE | Auto (constraint) | Uniqueness enforcement |
| Partial (recommended) | `(company_id, profile_type_id) WHERE active = true` | B-tree | Manual SQL | Active profiles listing optimization |

#### Python Constraints

```python
from ..utils import validators

@api.constrains('document')
def _check_document(self):
    """Validate CPF/CNPJ using centralized validators (constitution, D11)."""
    for record in self:
        if record.document:
            normalized = validators.normalize_document(record.document)
            if not validators.validate_document(normalized):
                raise ValidationError(
                    _('Documento inválido (CPF ou CNPJ): %s') % record.document
                )

@api.depends('document')
def _compute_document_normalized(self):
    """Strip formatting to digits only via centralized normalize_document()."""
    for record in self:
        if record.document:
            record.document_normalized = validators.normalize_document(record.document)
        else:
            record.document_normalized = False

@api.constrains('email')
def _check_email(self):
    """Validate email format via centralized validator."""
    for record in self:
        if record.email and not validators.validate_email_format(record.email):
            raise ValidationError(_('Email inválido: %s') % record.email)

@api.constrains('birthdate')
def _check_birthdate(self):
    """Birthdate must be in the past."""
    for record in self:
        if record.birthdate and record.birthdate >= fields.Date.today():
            raise ValidationError(_('Data de nascimento deve ser anterior à data atual.'))
```

#### Odoo Model Declaration

```python
class Profile(models.Model):
    _name = 'thedevkitchen.estate.profile'
    _description = 'Unified Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    # === Relationships ===
    profile_type_id = fields.Many2one(
        'thedevkitchen.profile.type', string='Profile Type',
        required=True, ondelete='restrict', index=True, tracking=True,
    )
    company_id = fields.Many2one(
        'thedevkitchen.estate.company', string='Company',
        required=True, ondelete='restrict', index=True, tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner',
        ondelete='restrict',
        help='Auto-created Odoo partner. Bridges to res.users for system access.',
    )

    # === Cadastral Fields ===
    name = fields.Char('Full Name', size=200, required=True, tracking=True)
    document = fields.Char('CPF/CNPJ', size=20, required=True, index=True, copy=False, tracking=True)
    document_normalized = fields.Char(
        'Document (normalized)', size=14,
        compute='_compute_document_normalized', store=True, index=True,
    )
    email = fields.Char('Email', size=100, required=True, tracking=True)
    phone = fields.Char('Phone', size=20)
    mobile = fields.Char('Mobile', size=20)
    occupation = fields.Char('Occupation', size=100)
    birthdate = fields.Date('Date of Birth', required=True)
    hire_date = fields.Date('Hire Date')
    profile_picture = fields.Binary('Profile Picture')

    # === Soft Delete (ADR-015) ===
    active = fields.Boolean('Active', default=True)
    deactivation_date = fields.Datetime('Deactivation Date')
    deactivation_reason = fields.Text('Deactivation Reason')

    # === Audit (spec D10) ===
    created_at = fields.Datetime('Created At', default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime('Updated At', default=fields.Datetime.now, readonly=True)

    # === Computed / Convenience ===
    # has_system_access: computed from partner_id → res.users existence
    # agent_extension_id: reverse O2M from real.estate.agent (profile_id)

    _sql_constraints = [
        ('document_company_type_unique',
         'UNIQUE(document, company_id, profile_type_id)',
         'Este documento já está cadastrado para este tipo de perfil nesta empresa.'),
    ]
```

---

### 2.3 `real.estate.agent` — Business Extension (Modified)

**Odoo `_name`**: `real.estate.agent` (existing, unchanged)
**PostgreSQL table**: `real_estate_agent` (existing)
**Change**: Add `profile_id` FK; sync common fields Phase 1 → `related` fields Phase 2

#### New/Changed Fields

| # | Field | Change | Odoo Definition | Notes |
|---|-------|--------|-----------------|-------|
| 1 | `profile_id` | **NEW** | `Many2one('thedevkitchen.estate.profile', ondelete='restrict', index=True)` | Links agent to unified profile |
| 2 | `name` | Phase 1: keep + sync | `Char('Full Name', required=True)` | Synced from `profile_id.name` on create |
| 3 | `cpf` | Phase 1: keep + sync | `Char('CPF', size=14, required=True)` | Synced from `profile_id.document` on create |
| 4 | `email` | Phase 1: keep + sync | `Char('Email')` | Synced from `profile_id.email` on create |
| 5 | `phone` | Phase 1: keep + sync | `Char('Phone', size=20)` | Synced from `profile_id.phone` on create |
| 6 | `company_id` | Phase 1: keep + sync | `Many2one(..., required=True)` | Synced from `profile_id.company_id` on create |

**Phase 1 strategy** (Feature 010): Agent `create()` override receives `profile_id`, copies cadastral data from profile to agent fields. This avoids breaking 18 existing agent_api endpoints that rely on agent-level fields.

**Phase 2 strategy** (future): Convert above fields to `related` fields pointing to `profile_id.*`. This eliminates data duplication but requires updating all agent_api serializers.

#### Create Override Extension

```python
@api.model
def create(self, vals):
    """Extended to sync data from profile when profile_id is provided."""
    if vals.get('profile_id'):
        profile = self.env['thedevkitchen.estate.profile'].browse(vals['profile_id'])
        if profile.exists():
            vals.setdefault('name', profile.name)
            vals.setdefault('cpf', profile.document)
            vals.setdefault('email', profile.email)
            vals.setdefault('phone', profile.phone)
            vals.setdefault('company_id', profile.company_id.id)
    return super().create(vals)
```

#### Existing Constraints (unchanged)

```python
_sql_constraints = [
    ('cpf_company_unique', 'UNIQUE(cpf, company_id)',
     'Já existe um corretor com este CPF nesta empresa.'),
    ('user_company_unique', 'UNIQUE(user_id, company_id)',
     'Este usuário já está vinculado como corretor nesta empresa.'),
]
```

These constraints coexist with profile's `UNIQUE(document, company_id, profile_type_id)` — agent always has `profile_type='agent'`, so the compound unique covers agent CPF uniqueness at the profile level, and `cpf_company_unique` provides a double-check at the agent level.

---

### 2.4 `real.estate.lease` — FK Migration

**Change**: `tenant_id` → `profile_id`

| Field | Before | After |
|-------|--------|-------|
| FK field name | `tenant_id` | `profile_id` |
| FK target | `real.estate.tenant` | `thedevkitchen.estate.profile` |
| Required | ✅ | ✅ |
| ondelete | `set null` (Odoo default) | `restrict` (preserve lease history) |

```python
# Before
tenant_id = fields.Many2one('real.estate.tenant', string='Tenant', required=True)

# After
profile_id = fields.Many2one(
    'thedevkitchen.estate.profile', string='Profile (Tenant)',
    required=True, ondelete='restrict', index=True,
    help='Profile associated with this lease (typically portal/tenant type)',
)
```

**Impact on `_compute_name`**:
```python
# Before
@api.depends('property_id', 'tenant_id', 'start_date')
def _compute_name(self):
    for record in self:
        if record.property_id and record.tenant_id and record.start_date:
            record.name = f"{record.property_id.name} - {record.tenant_id.name} ({record.start_date})"

# After
@api.depends('property_id', 'profile_id', 'start_date')
def _compute_name(self):
    for record in self:
        if record.property_id and record.profile_id and record.start_date:
            record.name = f"{record.property_id.name} - {record.profile_id.name} ({record.start_date})"
```

### 2.5 `real.estate.property` — FK Migration

**Change**: `tenant_id` → `profile_id`

```python
# Before (line 217)
tenant_id = fields.Many2one('real.estate.tenant', string='Tenant')

# After
profile_id = fields.Many2one(
    'thedevkitchen.estate.profile', string='Profile (Tenant)',
    ondelete='set null', index=True,
)
```

### 2.6 `thedevkitchen.estate.company` — Relationship Change

**Changes**:
- Remove `tenant_ids` M2M + `tenant_count` computed
- Add `profile_ids` reverse O2M + `profile_count` computed

```python
# Before
tenant_ids = fields.Many2many('real.estate.tenant', 'thedevkitchen_company_tenant_rel',
                               'company_id', 'tenant_id', string='Tenants')
tenant_count = fields.Integer(compute='_compute_counts')

# After
profile_ids = fields.One2many('thedevkitchen.estate.profile', 'company_id', string='Profiles')
profile_count = fields.Integer(string='Profiles Count', compute='_compute_counts')
```

> **Note**: M2M → O2M change is intentional. Profile has `company_id` (M2O), so the reverse is O2M, not M2M. The join table `thedevkitchen_company_tenant_rel` is dropped.

---

## 3. Record Rules (Security)

### 3.1 Profile Record Rules

Following the pattern from [record_rules.xml](../../18.0/extra-addons/quicksol_estate/security/record_rules.xml) with comprehensive coverage matching other models (property=8 rules, lease=7, agent=4).

| Rule ID | Group | Domain | Permissions | Description |
|---------|-------|--------|-------------|-------------|
| `rule_owner_profiles` | `group_real_estate_owner` | `[('company_id', 'in', user.estate_company_ids.ids)]` | CRUD | Owner: full access to company profiles |
| `rule_manager_all_company_profiles` | `group_real_estate_manager` | `[('company_id', 'in', user.estate_company_ids.ids)]` | Read, Write, Create | Manager: manage company profiles |
| `rule_agent_company_profiles` | `group_real_estate_agent` | `[('company_id', 'in', user.estate_company_ids.ids)]` | Read only | Agent: view company profiles |
| `rule_receptionist_company_profiles` | `group_real_estate_receptionist` | `[('company_id', 'in', user.estate_company_ids.ids)]` | Read, Write, Create | Receptionist: manage profiles (no delete) |
| `rule_portal_own_profile` | `group_real_estate_portal_user` | `[('partner_id', '=', user.partner_id.id)]` | Read only | Portal: view own profile only |
| `rule_profile_multi_company` | `group_real_estate_user`, `group_real_estate_manager` | `[('company_id', 'in', user.estate_company_ids.ids)]` | Full (default) | Multi-company isolation base |

### 3.2 Profile Type Record Rules

| Rule ID | Group | Domain | Permissions | Description |
|---------|-------|--------|-------------|-------------|
| `rule_profile_type_global_read` | (global) | `[(1, '=', 1)]` | Read only | All authenticated users can list profile types |

Profile types are read-only seed data — no write rules needed beyond system admin (base.group_system).

### 3.3 Existing Rules Impacted

| Rule ID | Current Domain | New Domain | Change |
|---------|---------------|------------|--------|
| `rule_portal_own_leases` | `[('tenant_id.partner_id', '=', user.partner_id.id)]` | `[('profile_id.partner_id', '=', user.partner_id.id)]` | FK rename |
| `rule_tenant_multi_company` | `model_real_estate_tenant` ref | **REMOVE** — replaced by `rule_profile_multi_company` | Model removed |

---

## 4. ACL Matrix (`ir.model.access.csv`)

### 4.1 New ACLs for `thedevkitchen.estate.profile`

| External ID | Model | Group | Read | Write | Create | Unlink |
|-------------|-------|-------|------|-------|--------|--------|
| `access_profile_owner` | `model_thedevkitchen_estate_profile` | `group_real_estate_owner` | 1 | 1 | 1 | 1 |
| `access_profile_manager` | `model_thedevkitchen_estate_profile` | `group_real_estate_manager` | 1 | 1 | 1 | 0 |
| `access_profile_receptionist` | `model_thedevkitchen_estate_profile` | `group_real_estate_receptionist` | 1 | 1 | 1 | 0 |
| `access_profile_agent` | `model_thedevkitchen_estate_profile` | `group_real_estate_agent` | 1 | 0 | 0 | 0 |
| `access_profile_system_admin` | `model_thedevkitchen_estate_profile` | `base.group_system` | 1 | 1 | 1 | 1 |
| `access_profile_company_manager` | `model_thedevkitchen_estate_profile` | `group_real_estate_director` | 1 | 1 | 1 | 1 |
| `access_profile_user` | `model_thedevkitchen_estate_profile` | `group_real_estate_user` | 1 | 1 | 1 | 0 |
| `access_profile_portal` | `model_thedevkitchen_estate_profile` | `group_real_estate_portal_user` | 1 | 0 | 0 | 0 |

### 4.2 New ACLs for `thedevkitchen.profile.type`

| External ID | Model | Group | Read | Write | Create | Unlink |
|-------------|-------|-------|------|-------|--------|--------|
| `access_profile_type_user` | `model_thedevkitchen_profile_type` | `group_real_estate_user` | 1 | 0 | 0 | 0 |
| `access_profile_type_owner` | `model_thedevkitchen_profile_type` | `group_real_estate_owner` | 1 | 0 | 0 | 0 |
| `access_profile_type_system_admin` | `model_thedevkitchen_profile_type` | `base.group_system` | 1 | 1 | 1 | 1 |
| `access_profile_type_portal` | `model_thedevkitchen_profile_type` | `group_real_estate_portal_user` | 1 | 0 | 0 | 0 |

### 4.3 ACLs to Remove

All 7 rows referencing `model_real_estate_tenant`:
- `access_tenant_owner`, `access_tenant_receptionist`, `access_tenant_manager`, `access_tenant_system_admin`, `access_tenant_company_manager`, `access_tenant_user`, `access_tenant_agent`

---

## 5. Seed Data — Profile Types

**File**: `data/profile_type_data.xml`
**Load order**: After `security/groups.xml` (references group XML IDs)
**noupdate**: `"1"` (seed data — never overwritten on module update)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- Admin Level -->
        <record id="profile_type_owner" model="thedevkitchen.profile.type">
            <field name="code">owner</field>
            <field name="name">Proprietário</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_owner</field>
            <field name="level">admin</field>
        </record>
        <record id="profile_type_director" model="thedevkitchen.profile.type">
            <field name="code">director</field>
            <field name="name">Diretor</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_director</field>
            <field name="level">admin</field>
        </record>
        <record id="profile_type_manager" model="thedevkitchen.profile.type">
            <field name="code">manager</field>
            <field name="name">Gerente</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_manager</field>
            <field name="level">admin</field>
        </record>

        <!-- Operational Level -->
        <record id="profile_type_agent" model="thedevkitchen.profile.type">
            <field name="code">agent</field>
            <field name="name">Corretor</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_agent</field>
            <field name="level">operational</field>
        </record>
        <record id="profile_type_prospector" model="thedevkitchen.profile.type">
            <field name="code">prospector</field>
            <field name="name">Captador</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_prospector</field>
            <field name="level">operational</field>
        </record>
        <record id="profile_type_receptionist" model="thedevkitchen.profile.type">
            <field name="code">receptionist</field>
            <field name="name">Atendente</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_receptionist</field>
            <field name="level">operational</field>
        </record>
        <record id="profile_type_financial" model="thedevkitchen.profile.type">
            <field name="code">financial</field>
            <field name="name">Financeiro</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_financial</field>
            <field name="level">operational</field>
        </record>
        <record id="profile_type_legal" model="thedevkitchen.profile.type">
            <field name="code">legal</field>
            <field name="name">Jurídico</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_legal</field>
            <field name="level">operational</field>
        </record>

        <!-- External Level -->
        <record id="profile_type_portal" model="thedevkitchen.profile.type">
            <field name="code">portal</field>
            <field name="name">Portal (Inquilino/Comprador)</field>
            <field name="group_xml_id">quicksol_estate.group_real_estate_portal_user</field>
            <field name="level">external</field>
        </record>
    </data>
</odoo>
```

---

## 6. Validators — Required Functions

**File**: `utils/validators.py` (existing, 239 LOC)
**Prerequisite**: Must be implemented before profile model (Phase 1, Step 1)

### 6.1 Functions to Add

```python
def is_cpf(document: str) -> bool:
    """Check if a digits-only string is a valid CPF (11 digits + checksum).
    
    Args:
        document: Digits-only string (no formatting).
    
    Returns:
        True if valid CPF, False otherwise.
    """

def is_cnpj(document: str) -> bool:
    """Check if a digits-only string is a valid CNPJ (14 digits + checksum).
    
    Delegates to existing validate_cnpj() after formatting.
    
    Args:
        document: Digits-only string (no formatting).
    
    Returns:
        True if valid CNPJ, False otherwise.
    """

def normalize_document(document: str) -> str:
    """Strip all non-digit characters from a document string.
    
    Args:
        document: CPF/CNPJ with or without formatting.
    
    Returns:
        Digits-only string. Example: '123.456.789-01' → '12345678901'
    """

def validate_document(document: str) -> bool:
    """Validate a document as CPF (11 digits) or CNPJ (14 digits).
    
    Dispatches to is_cpf() or is_cnpj() based on length.
    
    Args:
        document: Digits-only string (call normalize_document first).
    
    Returns:
        True if valid CPF or CNPJ, False otherwise.
    """
```

### 6.2 Validation Flow

```
User input: "123.456.789-01"
    │
    ▼
normalize_document("123.456.789-01")  →  "12345678901"
    │
    ▼
validate_document("12345678901")
    │
    ├─ len == 11 → is_cpf("12345678901")  →  True/False
    ├─ len == 14 → is_cnpj("12345678901")  →  True/False
    └─ else      → False
```

---

## 7. Dropped Entities (Dev Environment — Direct Removal)

### 7.1 `real.estate.tenant`

| Artifact | Action |
|----------|--------|
| `models/tenant.py` | Delete file |
| `models/__init__.py` | Remove `from . import tenant` |
| Table `real_estate_tenant` | `DROP TABLE IF EXISTS real_estate_tenant CASCADE;` |
| Join table `thedevkitchen_company_tenant_rel` | `DROP TABLE IF EXISTS thedevkitchen_company_tenant_rel CASCADE;` |
| ACLs in `ir.model.access.csv` | Remove 7 rows matching `model_real_estate_tenant` |
| Record rule `rule_tenant_multi_company` | Remove from `record_rules.xml` |
| Views `views/tenant_views.xml` | Delete file |
| `__manifest__.py` | Remove `'views/tenant_views.xml'` from data list |
| `controllers/tenant_api.py` | Delete file |
| `controllers/__init__.py` | Remove `from . import tenant_api` |
| Schema `TENANT_CREATE_SCHEMA`, `TENANT_UPDATE_SCHEMA` | Remove from `controllers/utils/schema.py` |

### 7.2 ORM Metadata Cleanup (after module update)

```sql
-- Clean up Odoo's internal model registry
DELETE FROM ir_model WHERE model = 'real.estate.tenant';
DELETE FROM ir_model_fields WHERE model_id IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);
DELETE FROM ir_model_access WHERE model_id IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);
DELETE FROM ir_rule WHERE model_id IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);
```

---

## 8. Compliance Checklist

| # | KB-09 / ADR Rule | Compliance | Notes |
|---|------------------|------------|-------|
| 1 | **KB-09 §1**: 3NF normalization | ✅ | Profile type in lookup table (eliminates redundancy) |
| 2 | **KB-09 §2**: snake_case, singular table names | ✅ | `thedevkitchen_profile_type`, `thedevkitchen_estate_profile` |
| 3 | **KB-09 §2.1**: Lookup tables for enums > 5 | ✅ | 9 profile types → lookup table |
| 4 | **KB-09 §3**: Surrogate PKs | ✅ | Auto-increment `id` on all tables |
| 5 | **KB-09 §4**: Explicit FKs with `ondelete` | ✅ | `restrict` on profile_type_id, company_id, partner_id |
| 6 | **KB-09 §5**: Indexes on FK, WHERE, ORDER BY | ✅ | FK auto-indexed + explicit on document, document_normalized |
| 7 | **KB-09 §5.3**: Partial indexes for soft delete | ✅ | Recommended: `WHERE active = true` |
| 8 | **KB-09 §6**: Correct data types | ✅ | VARCHAR for text, BOOLEAN for flags, DATE/TIMESTAMP for dates |
| 9 | **KB-09 §7**: Named constraints | ✅ | `document_company_type_unique`, `code_unique` |
| 10 | **KB-09 §9**: Soft delete | ✅ | `active` Boolean (ADR-015) + `deactivation_date/reason` |
| 11 | **KB-09 §10**: Audit fields | ⚠️ | `created_at`/`updated_at` per spec D10 (conflicts with ADR-004 `create_date`/`write_date`) |
| 12 | **ADR-004**: `thedevkitchen.` model prefix | ✅ | Both new models use `thedevkitchen.` prefix |
| 13 | **ADR-008**: Multi-tenancy company isolation | ✅ | `company_id` M2O + record rules with `user.estate_company_ids` |
| 14 | **ADR-015**: Soft delete pattern | ✅ | `active` + `deactivation_date` + `deactivation_reason` |
| 15 | **ADR-019**: 9 RBAC profiles | ✅ | All 9 types in seed data with correct `group_xml_id` |

---

## 9. PostgreSQL DDL Summary (Reference Only)

> Odoo generates these tables automatically from model definitions. This DDL is for reference and review only.

```sql
-- 1. Profile Type (Lookup)
CREATE TABLE thedevkitchen_profile_type (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(30) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    group_xml_id    VARCHAR(100) NOT NULL,
    level           VARCHAR NOT NULL,  -- 'admin', 'operational', 'external'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Odoo internal fields (auto)
    create_uid      INTEGER REFERENCES res_users(id),
    write_uid       INTEGER REFERENCES res_users(id),
    create_date     TIMESTAMP,
    write_date      TIMESTAMP,

    CONSTRAINT thedevkitchen_profile_type_code_unique
        UNIQUE (code)
);

CREATE INDEX thedevkitchen_profile_type_code_idx
    ON thedevkitchen_profile_type (code);


-- 2. Unified Profile
CREATE TABLE thedevkitchen_estate_profile (
    id                      SERIAL PRIMARY KEY,
    profile_type_id         INTEGER NOT NULL REFERENCES thedevkitchen_profile_type(id)
                            ON DELETE RESTRICT,
    company_id              INTEGER NOT NULL REFERENCES thedevkitchen_estate_company(id)
                            ON DELETE RESTRICT,
    partner_id              INTEGER REFERENCES res_partner(id)
                            ON DELETE RESTRICT,
    name                    VARCHAR(200) NOT NULL,
    document                VARCHAR(20) NOT NULL,
    document_normalized     VARCHAR(14),
    email                   VARCHAR(100) NOT NULL,
    phone                   VARCHAR(20),
    mobile                  VARCHAR(20),
    occupation              VARCHAR(100),
    birthdate               DATE NOT NULL,
    hire_date               DATE,
    profile_picture         BYTEA,
    active                  BOOLEAN NOT NULL DEFAULT TRUE,
    deactivation_date       TIMESTAMP,
    deactivation_reason     TEXT,
    created_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Odoo internal fields (auto)
    create_uid              INTEGER REFERENCES res_users(id),
    write_uid               INTEGER REFERENCES res_users(id),
    create_date             TIMESTAMP,
    write_date              TIMESTAMP,

    CONSTRAINT thedevkitchen_estate_profile_document_company_type_unique
        UNIQUE (document, company_id, profile_type_id)
);

-- FK indexes (auto-created by Odoo)
CREATE INDEX thedevkitchen_estate_profile_profile_type_id_idx
    ON thedevkitchen_estate_profile (profile_type_id);
CREATE INDEX thedevkitchen_estate_profile_company_id_idx
    ON thedevkitchen_estate_profile (company_id);
CREATE INDEX thedevkitchen_estate_profile_partner_id_idx
    ON thedevkitchen_estate_profile (partner_id);

-- Explicit indexes
CREATE INDEX thedevkitchen_estate_profile_document_idx
    ON thedevkitchen_estate_profile (document);
CREATE INDEX thedevkitchen_estate_profile_document_normalized_idx
    ON thedevkitchen_estate_profile (document_normalized);

-- Recommended partial index for active profiles
CREATE INDEX thedevkitchen_estate_profile_active_company_type_idx
    ON thedevkitchen_estate_profile (company_id, profile_type_id)
    WHERE active = TRUE;


-- 3. Agent FK addition
ALTER TABLE real_estate_agent
    ADD COLUMN profile_id INTEGER REFERENCES thedevkitchen_estate_profile(id)
    ON DELETE RESTRICT;

CREATE INDEX real_estate_agent_profile_id_idx
    ON real_estate_agent (profile_id);


-- 4. Lease FK migration
ALTER TABLE real_estate_lease
    DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE real_estate_lease
    ADD COLUMN profile_id INTEGER NOT NULL
    REFERENCES thedevkitchen_estate_profile(id)
    ON DELETE RESTRICT;

CREATE INDEX real_estate_lease_profile_id_idx
    ON real_estate_lease (profile_id);


-- 5. Cleanup (dev environment)
DROP TABLE IF EXISTS real_estate_tenant CASCADE;
DROP TABLE IF EXISTS thedevkitchen_company_tenant_rel CASCADE;
```

---

## 10. Data Flow Diagrams

### 10.1 Profile Creation Flow

```
POST /api/v1/profiles
    │
    ▼
┌───────────────────────────────┐
│ Controller: validate payload  │
│  - SchemaValidator            │
│  - company_id in body         │
│  - RBAC authorization matrix  │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Validators                    │
│  - normalize_document()       │
│  - validate_document()        │
│  - validate_email_format()    │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐     ┌────────────────────────┐
│ Profile.create(vals)          │────▶│ IF profile_type='agent'│
│  - partner_id auto-created?   │     │   Agent.create(        │
│  - compound unique check      │     │     profile_id=new_id  │
│  - SQL constraint enforced    │     │   )                    │
└──────────┬────────────────────┘     └────────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Response (201 Created)        │
│  - Profile data               │
│  - agent_extension_id (if)    │
│  - HATEOAS _links             │
└───────────────────────────────┘
```

### 10.2 Two-Step Invite Flow

```
Step 1: POST /api/v1/profiles          Step 2: POST /api/v1/users/invite
    │                                       │
    ▼                                       ▼
┌──────────────────┐                 ┌──────────────────┐
│ Create profile   │                 │ Read profile     │
│ (no system       │                 │ by profile_id    │
│  access yet)     │                 │ → get name,      │
│                  │                 │   email, document│
│ active=True      │                 │   company_id,    │
│ partner_id=null  │                 │   profile_type   │
│ or auto-created  │                 │   .group_xml_id  │
└──────────────────┘                 └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │ Create res.users │
                                     │ with correct     │
                                     │ security group   │
                                     │ Send invite email│
                                     │ Link partner_id  │
                                     └──────────────────┘
```
