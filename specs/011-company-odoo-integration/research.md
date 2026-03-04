# Research: Feature 011 — Company–Odoo Integration

**Phase 0 output** | **Date**: 2026-03-02 | **Branch**: `011-company-odoo-integration`

## Research Tasks & Findings

### R1 — Odoo `_inherit` on `res.company`: Best Practices

**Decision**: Use `_inherit = 'res.company'` with no new `_name` to extend the company model in-place.

**Rationale**:
- Odoo's localization modules (`l10n_br`, `l10n_mx`, `l10n_es`) all use `_inherit = 'res.company'` to add country-specific fields (CNPJ, RFC, CIF) directly in `res_company` table.
- `_inherits` (delegation inheritance) would create a second table linked by FK — adds JOINs, complexity, and is not how the ecosystem extends `res.company`.
- Fields added via `_inherit` are first-class columns in `res_company` — no performance penalty, no JOIN overhead.
- Existing Odoo infrastructure (`allowed_company_ids`, `company_id`, `company_ids`) automatically recognizes these companies.

**Alternatives Considered**:
1. `_inherits = {'res.company': 'company_id'}` — Rejected: unnecessary second table, extra JOINs, not ecosystem standard.
2. Keep standalone `thedevkitchen.estate.company` + add FK to `res.company` — Rejected: still duplicates data and doesn't enable native record rules.

---

### R2 — Native Multi-Company Record Rules Pattern

**Decision**: Use Odoo's standard domain `[('company_id', 'in', company_ids)]` for all record rules.

**Rationale**:
- `company_ids` is a special field in Odoo's security context — it resolves to `allowed_company_ids` from the user's active companies.
- The ORM automatically optimizes this domain pattern for performance.
- All 9 business models will have `company_id = fields.Many2one('res.company')` (M2O), making this pattern directly applicable.
- The special syntax `company_ids` (without `user.`) is Odoo's native way to reference the current user's allowed companies in record rule domains.

**Alternatives Considered**:
1. Keep `user.estate_company_ids.ids` — Rejected: custom field bypasses Odoo's optimized company-switching mechanism.
2. Use `user.company_ids.ids` (explicit) — Works but `company_ids` alone is the canonical form in Odoo record rules.

**Key Finding**: Odoo's `company_ids` in record rule domains automatically resolves to the current user's allowed company IDs. This is different from `user.company_ids` field access. The short form `company_ids` is what Odoo's own modules use.

---

### R3 — `request.update_env(company=...)` Pattern

**Decision**: Middleware `@require_company` should call `request.update_env(company=company_id)` after validation.

**Rationale**:
- `request.update_env(company=company_id)` sets `self.env.company` for all subsequent ORM calls in the request.
- This is Odoo's standard way to set the "active company" context, used by the web client when switching companies.
- After calling this, `self.env.company` returns the correct company, and `_get_company_domain()` style helpers can use it.
- Current middleware only sets `request.company_domain` (a plain list) — controllers must manually apply this domain. With `update_env`, ORM record rules handle isolation automatically.

**Current Implementation** (middleware.py L303-322):
```python
request.company_domain = [('company_ids', 'in', user.estate_company_ids.ids)]
request.user_company_ids = user.estate_company_ids.ids
```

**New Implementation**:
```python
company_id = int(request.httprequest.headers.get('X-Company-ID'))
company = request.env['res.company'].sudo().browse(company_id)
if not company.exists() or not company.is_real_estate:
    return _error_response(404, 'company_not_found', '...')
if company_id not in user.company_ids.ids:
    return _error_response(403, 'company_forbidden', '...')
request.update_env(company=company_id)
request.user_company_ids = user.company_ids.ids  # backward compat
```

**Alternatives Considered**:
1. Keep `request.company_domain` pattern — Rejected: manual domain injection is fragile and doesn't leverage native record rules.
2. Use `with_company()` in each controller — Rejected: repetitive and error-prone.

---

### R4 — `res.country.state` vs `real.estate.state`

**Decision**: Eliminate `real.estate.state` model. Use Odoo's native `res.country.state`.

**Rationale**:
- `res.country.state` is Odoo's built-in model for country subdivisions. It already contains all 27 Brazilian states (loaded by `base` module with country data).
- `real.estate.state` has only 3 fields: `name`, `code`, `country_id` — a subset of `res.country.state` which has `name`, `code`, `country_id` (identical schema).
- The custom model adds 16 lines of code + 27 XML seed records + 5 ACL lines — all unnecessary.
- `res.company` already has `state_id` pointing to `res.country.state` — using the same field on property/owner avoids joining different state tables.

**Migration Pattern**:
- Delete `models/state.py` and `data/states.xml`
- All `state_id = Many2one('real.estate.state')` → `state_id = Many2one('res.country.state')`
- `/api/v1/states` endpoint: `request.env['real.estate.state']` → `request.env['res.country.state']`
- `res.country.state` has same fields: `name`, `code`, `country_id`
- Response JSON format can remain identical: `{id, name, code, country: {id, name, code}}`

**Alternatives Considered**:
1. Keep `real.estate.state` alongside `res.country.state` — Rejected: unnecessary duplication, extra ACLs, extra table.
2. Rename to `estate_state_id` — Rejected: adds complexity; native `state_id` on `res.company` already points to `res.country.state`.

---

### R5 — M2M to M2O Migration Pattern for Business Models

**Decision**: Replace all M2M `company_ids` with M2O `company_id = Many2one('res.company')` on business models.

**Rationale**:
- Investigation of the codebase revealed that **no actual business record** is ever associated with multiple companies simultaneously. The M2M pattern was over-engineering.
- All record creation paths set a single company via `[(6, 0, [single_id])]` or `[(4, single_id)]`.
- Assignment validation (`assignment.py`) already assumed single-company: `agent.company_id not in property.company_ids`.
- M2O enables Odoo's standard record rule domain `[('company_id', 'in', company_ids)]` without customization.
- Eliminates 5 M2M relation tables: `thedevkitchen_company_property_rel`, `_agent_rel`, `_lease_rel`, `_sale_rel`, `real_estate_lead_company_rel`.

**Affected Models**:
| Model | Old Field | New Field |
|-------|-----------|-----------|
| `real.estate.property` | `company_ids` (M2M) | `company_id` M2O → `res.company` |
| `real.estate.agent` | `company_ids` (M2M) + `company_id` (M2O→custom) | `company_id` M2O → `res.company` (keep one) |
| `real.estate.lead` | `company_ids` (M2M) | `company_id` M2O → `res.company` |
| `real.estate.lease` | `company_ids` (M2M) | `company_id` M2O → `res.company` |
| `real.estate.sale` | `company_ids` (M2M) + `company_id` (M2O→custom) | `company_id` M2O → `res.company` (keep one) |

**Alternatives Considered**:
1. Keep M2M but point to `res.company` — Rejected: still doesn't enable native record rules (which require M2O `company_id`).
2. Gradual migration (soft-delete M2M, add M2O) — Rejected: dev environment, clean cut is simpler.

---

### R6 — `is_real_estate` Boolean Discriminator

**Decision**: Add `is_real_estate = fields.Boolean(default=False)` to `res.company` to distinguish real estate agencies from generic companies.

**Rationale**:
- Odoo creates a default company (ID=1) during installation. This company is NOT a real estate agency.
- The `is_real_estate` flag filters the company list in APIs: `[('is_real_estate', '=', True)]`.
- Set automatically when creating companies via the real estate API.
- Prevents real estate business data from leaking to/from the system company.

**Implementation**:
```python
class ResCompany(models.Model):
    _inherit = 'res.company'
    
    is_real_estate = fields.Boolean(
        string='Is Real Estate Company',
        default=False,
        help='Indicates this company is a real estate agency'
    )
```

**Alternatives Considered**:
1. Separate company type enum (`selection` field) — Rejected: Boolean is simpler and sufficient; no other company types expected.
2. Check for CNPJ presence as discriminator — Rejected: some companies might have CNPJ but not be real estate agencies.

---

### R7 — Field Naming Convention for Inherited Models

**Decision**: Custom fields on `res.company` use plain names without prefix: `cnpj`, `creci`, `legal_name`, `foundation_date`, `is_real_estate`.

**Rationale**:
- Odoo's localization modules (e.g., `l10n_br` uses `cnpj_cpf` on `res.partner`) don't use `x_` prefix for code-installed fields.
- `x_` prefix is Odoo's convention for **UI-created fields** (Studio), not code-installed fields.
- ADR-004 scope clarification: `thedevkitchen` prefix applies to **table names** and **module names**, not to fields on inherited core models.

**Field Mapping from Custom to Inherited**:
| Custom Model Field | `res.company` Equivalent | Notes |
|----|----|----|
| `name` | `name` (native) | Already exists |
| `email` | `email` (native) | Already exists |
| `phone` | `phone` (native) | Already exists |
| `mobile` | Mobile not on `res.company` | Use `partner_id.mobile` |
| `website` | `website` (native) | Already exists |
| `street`/`street2`/`city` | Native | Already exist |
| `state_id` → `real.estate.state` | `state_id` → `res.country.state` (native) | Already exists |
| `zip_code` | `zip` (native) | Field name difference |
| `country_id` | `country_id` (native) | Already exists |
| `cnpj` | `cnpj` (**new**) | Added via `_inherit` |
| `creci` | `creci` (**new**) | Added via `_inherit` |
| `legal_name` | `legal_name` (**new**) | Added via `_inherit` |
| `foundation_date` | `foundation_date` (**new**) | Added via `_inherit` |
| `logo` | `logo` (native) | Already exists |
| `description` | *(drop or add)* | `res.company` has no description field; may add |
| `active` | `active` (native) | Already exists |

**Latent Bug Found**: Login payload (`user_auth_controller.py`) reads `getattr(c, 'vat', None)` for CNPJ — but `thedevkitchen.estate.company` has `cnpj`, not `vat`. This returns `None`. Migration to `res.company` with explicit `cnpj` field fixes this.

---

### R8 — Login/Me Payload Backward Compatibility

**Decision**: Maintain the same JSON response structure but source data from native fields.

**Current `/me` Response** (companies array):
```json
{
  "companies": [
    {"id": 1, "name": "Imob A", "cnpj": "12.345.678/0001-00", "email": "...", "phone": "...", "website": "..."}
  ],
  "default_company_id": 1
}
```

**New Source Mapping**:
| JSON Field | Old Source | New Source |
|---|---|---|
| `companies[].id` | `c.id` (estate company) | `c.id` (res.company) |
| `companies[].name` | `c.name` (estate company) | `c.name` (res.company native) |
| `companies[].cnpj` | `c.cnpj` (estate company) | `c.cnpj` (added via _inherit) |
| `companies[].email` | `c.email` (estate company) | `c.email` (res.company native) |
| `default_company_id` | `user.main_estate_company_id.id` | `user.company_id.id` (native) |
| companies iteration | `user.estate_company_ids` | `user.company_ids.filtered(lambda c: c.is_real_estate)` |

**Key Note**: Filter by `is_real_estate` when iterating `user.company_ids` to exclude the system company (ID=1).

---

### R9 — Observer Migration Pattern

**Decision**: Adapt `UserCompanyValidatorObserver` to validate writes on `company_ids` (native) instead of `estate_company_ids`.

**Current Logic**:
```python
allowed = current_user.estate_company_ids.ids
new_companies = extract_from_vals('estate_company_ids')
unauthorized = new_companies - allowed
```

**New Logic**:
```python
allowed = current_user.company_ids.ids
new_companies = extract_from_vals('company_ids')
unauthorized = new_companies - allowed
# Browse res.company instead of thedevkitchen.estate.company for error messages
```

**Note**: The observer uses `quicksol.abstract.observer` model name (not `thedevkitchen.`) — naming inconsistency (ADR-004). This can be noted for future migration but is OUT OF SCOPE for Feature 011.

---

### R10 — CNPJ Validation Preservation

**Decision**: Port the CNPJ checksum validation from `company.py` to the new `_inherit` model.

**Current validation** (`company.py` L120-160): Full CNPJ checksum algorithm validating format `XX.XXX.XXX/XXXX-XX` and computing verification digits.

**Reuse**: The `utils/validators.py` module already has `is_cnpj()` and `normalize_document()` functions (per constitution). The `_inherit` model should use these utilities via `@api.constrains('cnpj')`.

**SQL Constraint**: `_sql_constraints = [('cnpj_unique', 'UNIQUE(cnpj)', 'CNPJ must be unique')]` — applied directly to `res_company` table.

---

### R11 — Computed Count Fields on `res.company`

**Decision**: Preserve computed count fields (`property_count`, `agent_count`, etc.) as computed fields on the extended `res.company`.

**Implementation Change**: Counts previously used reverse M2M (`property_ids`, `agent_ids`). With M2O migration, they become simpler `search_count` calls:

```python
property_count = fields.Integer(compute='_compute_property_count')

def _compute_property_count(self):
    for company in self:
        company.property_count = self.env['real.estate.property'].search_count(
            [('company_id', '=', company.id)]
        )
```

This is more performant than M2M reverse traversal and aligns with how Odoo calculates related counts.

---

## Unresolved Items

None. All NEEDS CLARIFICATION items from the spec were resolved during the `/speckit.clarify` session:
- Q1: M2O only (not M2M) ✅
- Q2: `is_real_estate` boolean flag ✅
- Q3: No `x_` prefix on fields ✅
- Q4: Use native `state_id` / `res.country.state` ✅
