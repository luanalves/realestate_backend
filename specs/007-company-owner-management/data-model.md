# Data Model: Company & Owner Management

**Feature**: 007-company-owner-management  
**Created**: 2026-02-05  
**Status**: Phase 1 Design

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              RBAC LAYER                                  │
│  ┌────────────────────┐                                                 │
│  │    res_groups      │                                                 │
│  ├────────────────────┤                                                 │
│  │ • group_real_estate_owner     (can create companies & owners)        │
│  │ • group_real_estate_director  (read-only company access)             │
│  │ • group_real_estate_manager   (read-only company access)             │
│  │ • group_real_estate_agent     (read-only company access)             │
│  └─────────┬──────────┘                                                 │
│            │ res_groups_users_rel (uid, gid)                            │
└────────────┼────────────────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────────────────────┐
│                              USER LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                          res_users                                │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │ id            │ INTEGER      │ PK                                 │   │
│  │ name          │ VARCHAR(255) │ required                           │   │
│  │ login         │ VARCHAR(255) │ required, unique (email)           │   │
│  │ password      │ VARCHAR      │ hashed                             │   │
│  │ phone         │ VARCHAR(20)  │ optional                           │   │
│  │ mobile        │ VARCHAR(20)  │ optional                           │   │
│  │ active        │ BOOLEAN      │ default=True (soft delete)         │   │
│  │ groups_id     │ M2M          │ → res_groups                       │   │
│  │ estate_company_ids │ M2M     │ → thedevkitchen_estate_company     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│            │ thedevkitchen_user_company_rel (user_id, company_id)       │
└────────────┼────────────────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────────────────────┐
│                            COMPANY LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │               thedevkitchen_estate_company                        │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │ id            │ INTEGER      │ PK, auto                           │   │
│  │ name          │ VARCHAR(255) │ required                           │   │
│  │ cnpj          │ VARCHAR(18)  │ unique (including soft-deleted)    │   │
│  │ creci         │ VARCHAR(20)  │ optional                           │   │
│  │ legal_name    │ VARCHAR(255) │ optional                           │   │
│  │ email         │ VARCHAR(100) │ optional, validated format         │   │
│  │ phone         │ VARCHAR(20)  │ optional                           │   │
│  │ mobile        │ VARCHAR(20)  │ optional                           │   │
│  │ website       │ VARCHAR(200) │ optional                           │   │
│  │ street        │ VARCHAR(200) │ optional                           │   │
│  │ city          │ VARCHAR(100) │ optional                           │   │
│  │ state_id      │ INTEGER      │ FK → res.country.state             │   │
│  │ zip_code      │ VARCHAR(10)  │ optional                           │   │
│  │ logo          │ BINARY       │ optional                           │   │
│  │ active        │ BOOLEAN      │ default=True (soft delete)         │   │
│  │ create_date   │ DATETIME     │ auto                               │   │
│  │ write_date    │ DATETIME     │ auto                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Entity: thedevkitchen.estate.company

**Status**: EXISTS (extend validation)

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(255) | required | Nome fantasia da imobiliária |
| `cnpj` | Char(18) | unique | CNPJ formatado (XX.XXX.XXX/XXXX-XX) |
| `creci` | Char(20) | - | Registro no CRECI estadual |
| `legal_name` | Char(255) | - | Razão social |
| `email` | Char(100) | format validation | Email de contato principal |
| `phone` | Char(20) | - | Telefone fixo |
| `mobile` | Char(20) | - | Celular/WhatsApp |
| `website` | Char(200) | - | URL do website |
| `street` | Char(200) | - | Endereço (logradouro + número) |
| `city` | Char(100) | - | Cidade |
| `state_id` | Many2one | FK → res.country.state | Estado (UF) |
| `zip_code` | Char(10) | - | CEP |
| `logo` | Binary | - | Logo da empresa |
| `active` | Boolean | default=True | Soft delete flag (ADR-015) |
| `create_date` | Datetime | auto | Data de criação |
| `write_date` | Datetime | auto | Última modificação |

### Computed Fields (read-only)

| Field | Type | Description |
|-------|------|-------------|
| `property_count` | Integer | Total de imóveis cadastrados |
| `agent_count` | Integer | Total de corretores ativos |
| `lease_count` | Integer | Total de contratos ativos |
| `owner_ids` | Many2many | Usuários com role Owner desta company |

### Constraints

```python
_sql_constraints = [
    ('cnpj_unique', 'unique(cnpj)', 'CNPJ must be unique across all companies'),
]

@api.constrains('cnpj')
def _check_cnpj(self):
    """Validates CNPJ format and check digits (Brazilian tax ID)"""
    # Already implemented in company.py

@api.constrains('email')
def _check_email(self):
    """Validates email format when provided"""
    import re
    for record in self:
        if record.email:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', record.email):
                raise ValidationError(_('Invalid email format'))
```

### Business Rules

1. **CNPJ Uniqueness**: Includes soft-deleted records (prevents reuse of deactivated company CNPJs)
2. **Soft Delete**: DELETE operation sets `active=False`, data preserved for audit
3. **Owner Auto-Link**: When created via API by Owner, creator's `estate_company_ids` updated automatically

---

## Entity: res.users (Extension)

**Status**: EXISTS (extend with computed field)

### New Computed Field

```python
# In models/res_users.py

owner_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    compute='_compute_owner_companies',
    string='Owned Companies',
    help='Companies where this user has Owner role'
)

@api.depends('groups_id', 'estate_company_ids')
def _compute_owner_companies(self):
    """Returns companies where user is an Owner"""
    owner_group = self.env.ref('quicksol_estate.group_real_estate_owner')
    for user in self:
        if owner_group in user.groups_id:
            user.owner_company_ids = user.estate_company_ids
        else:
            user.owner_company_ids = self.env['thedevkitchen.estate.company']
```

### Owner Identification

**Owner is NOT a separate model.** Owner is a role identified by:

```python
# Check if user is Owner
user.has_group('quicksol_estate.group_real_estate_owner')

# Get all Owners of a specific company
owner_group = env.ref('quicksol_estate.group_real_estate_owner')
owners = env['res.users'].search([
    ('groups_id', 'in', [owner_group.id]),
    ('estate_company_ids', 'in', [company_id]),
    ('active', '=', True)
])
```

---

## Relationship Tables

### thedevkitchen_user_company_rel (EXISTS)

Links users to companies (many-to-many).

```sql
CREATE TABLE thedevkitchen_user_company_rel (
    user_id INTEGER REFERENCES res_users(id),
    company_id INTEGER REFERENCES thedevkitchen_estate_company(id),
    PRIMARY KEY (user_id, company_id)
);
```

### res_groups_users_rel (EXISTS - Odoo core)

Links users to groups (RBAC).

```sql
-- Standard Odoo table
CREATE TABLE res_groups_users_rel (
    uid INTEGER REFERENCES res_users(id),
    gid INTEGER REFERENCES res_groups(id),
    PRIMARY KEY (uid, gid)
);
```

---

## Record Rules (Security)

### Existing Rules (in record_rules.xml)

| Rule ID | Model | Domain | Permissions |
|---------|-------|--------|-------------|
| `rule_owner_estate_companies` | company | `estate_company_ids in user.estate_company_ids.ids` | CRUD (no unlink) |
| `rule_manager_estate_companies` | company | `estate_company_ids in user.estate_company_ids.ids` | Read/Write |
| `rule_agent_estate_companies` | company | `estate_company_ids in user.estate_company_ids.ids` | Read only |

### New Rule (to add)

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

## Validation Rules

### CNPJ Validation

```python
def validate_cnpj(cnpj: str) -> bool:
    """
    Validates Brazilian CNPJ (tax ID for companies).
    Format: XX.XXX.XXX/XXXX-XX
    """
    # Remove formatting
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
    
    # Check for all same digits
    if cnpj == cnpj[0] * 14:
        return False
    
    # Validate check digits
    # ... (algorithm for mod-11 verification)
    return True
```

### Email Validation

```python
def validate_email(email: str) -> bool:
    """Validates email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

### Password Requirements

```python
def validate_password(password: str) -> bool:
    """Validates password meets minimum requirements."""
    return len(password) >= 8
```

### Last Owner Protection

```python
def can_remove_owner(company_id: int, owner_id: int) -> bool:
    """
    Prevents removal of last active Owner of a company.
    Returns True if owner can be removed, False otherwise.
    """
    owner_group = env.ref('quicksol_estate.group_real_estate_owner')
    active_owners = env['res.users'].search_count([
        ('groups_id', 'in', [owner_group.id]),
        ('estate_company_ids', 'in', [company_id]),
        ('active', '=', True),
        ('id', '!=', owner_id)
    ])
    return active_owners > 0
```

---

## Migration Notes

**No database migrations required.** All tables exist. Changes are:

1. **Code only**: Add computed field `owner_company_ids` to res.users
2. **XML only**: Add record rule `rule_owner_manage_owners`
3. **Views**: Create `company_views.xml` with form/list/search views
4. **Controllers**: Create `company_api.py` and `owner_api.py`
