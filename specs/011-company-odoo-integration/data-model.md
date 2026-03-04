# Data Model: Feature 011 — Company–Odoo Integration

**Phase 1 output** | **Date**: 2026-03-02 | **Branch**: `011-company-odoo-integration`

## Entity Overview

This feature does **NOT create new models**. It **eliminates 2 custom models** and **extends 1 core model**. All business models change their FK target from `thedevkitchen.estate.company` → `res.company`.

## Models Eliminated

### 1. `thedevkitchen.estate.company` (DROP)

**Table**: `thedevkitchen_estate_company`
**Reason**: All fields migrated to `res.company` via `_inherit`. Model fully replaced.

### 2. `real.estate.state` (DROP)

**Table**: `real_estate_state`
**Reason**: Redundant with Odoo's native `res.country.state`. All 27 Brazilian states already in base data.

## Model Extended: `res.company` (via `_inherit`)

### New Fields Added to `res_company` Table

| Field | Python Type | DB Type | Required | Default | Constraint | Notes |
|-------|------------|---------|----------|---------|------------|-------|
| `is_real_estate` | `Boolean` | `boolean` | No | `False` | — | Discriminator: True = real estate agency |
| `cnpj` | `Char(18)` | `varchar(18)` | No | — | `UNIQUE(cnpj)` SQL | Format: `XX.XXX.XXX/XXXX-XX`, checksum validated |
| `creci` | `Char` | `varchar` | No | — | — | Regional council registration |
| `legal_name` | `Char` | `varchar` | No | — | — | Razão social |
| `foundation_date` | `Date` | `date` | No | — | — | Company founding date |
| `description` | `Text` | `text` | No | — | — | Optional description/notes |

### Native Fields Reused (already in `res_company`)

| Field | Type | Notes |
|-------|------|-------|
| `name` | `Char` | Company display name |
| `email` | `Char` | Contact email |
| `phone` | `Char` | Contact phone |
| `website` | `Char` | Company website |
| `street` / `street2` / `city` | `Char` | Address fields |
| `state_id` | `Many2one('res.country.state')` | UF / State (native, replaces custom `real.estate.state`) |
| `zip` | `Char` | CEP (note: custom model used `zip_code`) |
| `country_id` | `Many2one('res.country')` | Country |
| `logo` | `Binary` | Company logo |
| `active` | `Boolean` | Soft delete support |
| `currency_id` | `Many2one('res.currency')` | Default BRL |
| `partner_id` | `Many2one('res.partner')` | Auto-created by Odoo |

### Computed Fields (preserved from custom model)

| Field | Type | Compute Method | Notes |
|-------|------|---------------|-------|
| `property_count` | `Integer` | `_compute_property_count` | `search_count([('company_id', '=', self.id)])` |
| `agent_count` | `Integer` | `_compute_agent_count` | Same pattern |
| `profile_count` | `Integer` | `_compute_profile_count` | Same pattern |
| `lease_count` | `Integer` | `_compute_lease_count` | Same pattern |
| `sale_count` | `Integer` | `_compute_sale_count` | Same pattern |

### SQL Constraints

```sql
-- On res_company table (added by _inherit)
UNIQUE(cnpj)  -- "CNPJ must be unique"
```

### Python Constraints

```python
@api.constrains('cnpj')
def _check_cnpj(self):
    """CNPJ format and checksum validation using utils/validators.py"""
```

### Implementation Skeleton

```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.quicksol_estate.utils.validators import is_cnpj, normalize_document

class ResCompany(models.Model):
    _inherit = 'res.company'

    is_real_estate = fields.Boolean(
        string='Is Real Estate Company',
        default=False,
    )
    cnpj = fields.Char(
        string='CNPJ',
        size=18,
        copy=False,
        help='XX.XXX.XXX/XXXX-XX',
    )
    creci = fields.Char(string='CRECI')
    legal_name = fields.Char(string='Legal Name')
    foundation_date = fields.Date(string='Foundation Date')
    description = fields.Text(string='Description')

    # Computed counts
    property_count = fields.Integer(compute='_compute_property_count')
    agent_count = fields.Integer(compute='_compute_agent_count')
    profile_count = fields.Integer(compute='_compute_profile_count')
    lease_count = fields.Integer(compute='_compute_lease_count')
    sale_count = fields.Integer(compute='_compute_sale_count')

    _sql_constraints = [
        ('cnpj_unique', 'UNIQUE(cnpj)', 'CNPJ must be unique'),
    ]

    @api.constrains('cnpj')
    def _check_cnpj(self):
        for record in self:
            if record.cnpj:
                normalized = normalize_document(record.cnpj)
                if not is_cnpj(normalized):
                    raise ValidationError('Invalid CNPJ')

    def _compute_property_count(self):
        for company in self:
            company.property_count = self.env['real.estate.property'].search_count(
                [('company_id', '=', company.id)]
            )
    # ... same pattern for other counts
```

---

## Relations Changed on Business Models

### M2M → M2O Migrations

| Model | Old Relation | New Relation | Old Table Dropped |
|-------|-------------|-------------|-------------------|
| `real.estate.property` | `company_ids = M2M('thedevkitchen.estate.company')` | `company_id = M2O('res.company', required=True)` | `thedevkitchen_company_property_rel` |
| `real.estate.agent` | `company_ids = M2M('thedevkitchen.estate.company')` + `company_id = M2O(same)` | `company_id = M2O('res.company', required=True)` | `thedevkitchen_company_agent_rel` |
| `real.estate.lead` | `company_ids = M2M('thedevkitchen.estate.company')` | `company_id = M2O('res.company', required=True)` | `real_estate_lead_company_rel` |
| `real.estate.lease` | `company_ids = M2M('thedevkitchen.estate.company')` | `company_id = M2O('res.company', required=True)` | `thedevkitchen_company_lease_rel` |
| `real.estate.sale` | `company_ids = M2M(same)` + `company_id = M2O(same)` | `company_id = M2O('res.company', required=True)` | `thedevkitchen_company_sale_rel` |

### M2O Comodel Changes (no structural change, just target model)

| Model | Old Comodel | New Comodel |
|-------|------------|------------|
| `real.estate.commission.rule` | `thedevkitchen.estate.company` | `res.company` |
| `real.estate.commission.transaction` | `thedevkitchen.estate.company` | `res.company` |
| `thedevkitchen.estate.profile` | `thedevkitchen.estate.company` | `res.company` |
| `real.estate.property.assignment` | `thedevkitchen.estate.company` | `res.company` |

### `state_id` Comodel Changes

| Model | Old Comodel | New Comodel |
|-------|------------|------------|
| `real.estate.property` | `real.estate.state` | `res.country.state` |
| `real.estate.property.owner` | `real.estate.state` | `res.country.state` |
| `real.estate.property.building` | `real.estate.state` | `res.country.state` |

---

## `res.users` Changes

### Fields Removed

| Field | Type | Relation Table |
|-------|------|---------------|
| `estate_company_ids` | `Many2many('thedevkitchen.estate.company')` | `thedevkitchen_user_company_rel` |
| `main_estate_company_id` | `Many2one('thedevkitchen.estate.company')` | — |

### Fields Preserved (adapted)

| Field | Old | New |
|-------|-----|-----|
| `owner_company_ids` | Computed from `estate_company_ids` | Computed from `company_ids` filtered by `is_real_estate` |

### Methods Changed

| Method | Change |
|--------|--------|
| `write()` | Remove agent sync via `estate_company_ids`; adapt if needed for `company_ids` |
| `get_user_companies()` | Return `user.company_ids.filtered(lambda c: c.is_real_estate)` |
| `has_estate_company_access()` | Rename/adapt to check `company_id in user.company_ids.ids` |

---

## Tables Summary

### Tables DROPPED (8)

| Table | Type |
|-------|------|
| `thedevkitchen_estate_company` | Model table |
| `real_estate_state` | Model table |
| `thedevkitchen_user_company_rel` | M2M: users ↔ companies |
| `thedevkitchen_company_property_rel` | M2M: companies ↔ properties |
| `thedevkitchen_company_agent_rel` | M2M: companies ↔ agents |
| `thedevkitchen_company_lease_rel` | M2M: companies ↔ leases |
| `thedevkitchen_company_sale_rel` | M2M: companies ↔ sales |
| `real_estate_lead_company_rel` | M2M: leads ↔ companies |

### Tables MODIFIED (1)

| Table | Change |
|-------|--------|
| `res_company` | +6 columns: `is_real_estate`, `cnpj`, `creci`, `legal_name`, `foundation_date`, `description` |

### Tables UNCHANGED (used natively)

| Table | Purpose |
|-------|---------|
| `res_company_users_rel` | Native M2M: users ↔ companies (replaces `thedevkitchen_user_company_rel`) |
| `res_country_state` | Native states (replaces `real_estate_state`) |

---

## Record Rules — Domain Migration

All record rules change from custom to native pattern:

| Old Domain | New Domain |
|-----------|-----------|
| `[('id', 'in', user.estate_company_ids.ids)]` | `[('id', 'in', company_ids)]` |
| `[('company_ids', 'in', user.estate_company_ids.ids)]` | `[('company_id', 'in', company_ids)]` |
| `[('company_id', 'in', user.estate_company_ids.ids)]` | `[('company_id', 'in', company_ids)]` |

**Note**: `company_ids` (unqualified) in Odoo record rule domains resolves to the current user's allowed companies. This is Odoo's canonical form.

---

## ER Diagram (After Migration)

```
res.company (extended)
├── is_real_estate: Boolean
├── cnpj: Char (UNIQUE)
├── creci: Char
├── legal_name: Char
├── foundation_date: Date
├── (native: name, email, phone, state_id→res.country.state, ...)
│
├──< real.estate.property (company_id M2O)
│     └── state_id → res.country.state
├──< real.estate.agent (company_id M2O)
├──< real.estate.lead (company_id M2O)
├──< real.estate.lease (company_id M2O)
├──< real.estate.sale (company_id M2O)
├──< real.estate.commission.rule (company_id M2O)
├──< real.estate.commission.transaction (company_id M2O)
├──< thedevkitchen.estate.profile (company_id M2O)
├──< real.estate.property.assignment (company_id M2O)
│
└──>< res.users (via native company_ids M2M through res_company_users_rel)
```
