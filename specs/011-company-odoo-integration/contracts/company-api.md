# API Contracts: Feature 011 — Company–Odoo Integration

**Phase 1 output** | **Date**: 2026-03-02

## Contract Philosophy

Feature 011 is a **backend refactoring** — no new endpoints are added and no request/response contracts change. The OpenAPI contracts below document the **existing** endpoints with annotations showing what changes internally (model source, field source) while the external contract remains identical.

---

## Affected Endpoints

### 1. Company CRUD — `/api/v1/companies`

**Contract**: UNCHANGED (FR-014)

#### POST `/api/v1/companies` — Create Company

**Auth**: `@require_jwt` + `@require_session` (no `@require_company` — creating first company)
**RBAC**: Owner or Admin only

**Request Body**:
```json
{
  "name": "Imobiliária Exemplo",         // required
  "cnpj": "12.345.678/0001-00",          // optional, validated
  "creci": "CRECI-SP 12345",             // optional, validated
  "legal_name": "Exemplo Imobiliária LTDA", // optional
  "email": "contato@exemplo.com",        // optional, validated
  "phone": "(11) 3456-7890",             // optional
  "mobile": "(11) 98765-4321",           // optional
  "website": "https://exemplo.com",      // optional
  "street": "Rua das Flores, 123",       // optional
  "street2": "Sala 45",                  // optional
  "city": "São Paulo",                   // optional
  "state_id": 25,                        // optional, int (res.country.state ID)
  "zip_code": "01234-567",              // optional → mapped to `zip` on res.company
  "country_id": 31,                      // optional, int (res.country ID)
  "foundation_date": "2020-01-15",       // optional, ISO date
  "description": "Descrição opcional"    // optional
}
```

**Internal Change**: `env['thedevkitchen.estate.company'].create(...)` → `env['res.company'].create(...)` with `is_real_estate=True` auto-set. `zip_code` mapped to `zip`. Auto-linkage changes from `estate_company_ids += (4, id)` to `company_ids += (4, id)`.

**Response 201** (unchanged):
```json
{
  "success": true,
  "data": {
    "id": 5,
    "name": "Imobiliária Exemplo",
    "cnpj": "12.345.678/0001-00",
    "creci": "CRECI-SP 12345",
    "legal_name": "Exemplo Imobiliária LTDA",
    "email": "contato@exemplo.com",
    "phone": "(11) 3456-7890",
    "mobile": "(11) 98765-4321",
    "website": "https://exemplo.com",
    "city": "São Paulo",
    "state": "São Paulo",
    "property_count": 0,
    "agent_count": 0
  },
  "links": { "self": "/api/v1/companies/5", "properties": "/api/v1/companies/5/properties" }
}
```

#### GET `/api/v1/companies` — List Companies

**Auth**: `@require_jwt` + `@require_session` + `@require_company`

**Internal Change**: Domain changes from `[('id', 'in', user.estate_company_ids.ids)]` to `[('is_real_estate', '=', True), ('id', 'in', user.company_ids.ids)]`.

**Response 200** (unchanged):
```json
{
  "success": true,
  "data": [
    { "id": 5, "name": "...", "cnpj": "...", "email": "...", "phone": "...", "city": "...", "state": "...", "property_count": 0, "agent_count": 0 }
  ],
  "pagination": { "total": 1, "page": 1, "page_size": 20, "total_pages": 1 }
}
```

#### GET `/api/v1/companies/<id>` — Get Company Detail

**Auth**: `@require_jwt` + `@require_session` + `@require_company`

**Internal Change**: `env['thedevkitchen.estate.company'].browse(id)` → `env['res.company'].browse(id)`. Multi-tenancy check: `id not in user.estate_company_ids.ids` → `id not in user.company_ids.ids`.

**Response 200** (unchanged): Full company detail with all fields + HATEOAS links.

#### PUT `/api/v1/companies/<id>` — Update Company

**Auth**: `@require_jwt` + `@require_session` + `@require_company`

**Request/Response**: Same contract, internal model reference changes.

#### DELETE `/api/v1/companies/<id>` — Soft-Delete Company

**Auth**: `@require_jwt` + `@require_session` + `@require_company`

**Internal Change**: `company.write({'active': False})` — identical behavior on `res.company`.

---

### 2. Master Data — `/api/v1/states`

**Contract**: PRESERVED (same JSON shape)

#### GET `/api/v1/states` — List States

**Auth**: `@require_jwt` + `@require_session`

**Internal Change**: `env['real.estate.state']` → `env['res.country.state']`

**Response 200** (unchanged shape):
```json
{
  "success": true,
  "data": [
    {
      "id": 25,
      "name": "São Paulo",
      "code": "SP",
      "country": { "id": 31, "name": "Brazil", "code": "BR" }
    }
  ]
}
```

**Note**: `res.country.state` has `name`, `code`, `country_id` — same fields as the custom model. Response shape identical.

---

### 3. Authentication — `/api/v1/auth/token`

**Contract**: PRESERVED

**Internal Change (login response)**:
```
companies[] iteration: user.estate_company_ids → user.company_ids.filtered(lambda c: c.is_real_estate)
default_company_id: user.main_estate_company_id.id → user.company_id.id
cnpj field: getattr(c, 'vat', None) → c.cnpj  (fixes latent bug)
```

---

### 4. User Profile — `/api/v1/me`

**Contract**: PRESERVED

**Internal Change**:
```
companies[] iteration: user.estate_company_ids → user.company_ids.filtered(lambda c: c.is_real_estate)
default_company_id: user.main_estate_company_id.id → user.company_id.id
```

---

### 5. Middleware — `X-Company-ID` Header

**Contract**: PRESERVED

**Internal Change**:
- Validates `X-Company-ID` against `user.company_ids` (native) instead of `user.estate_company_ids`
- Additionally validates `company.is_real_estate == True`
- Calls `request.update_env(company=company_id)` instead of setting `request.company_domain`
- `request.user_company_ids` preserved for backward compatibility

---

### 6. Invite — `/api/v1/users/invite`

**Contract**: PRESERVED

**Internal Change**:
- Company association: `estate_company_ids += (4, id)` → `company_ids += (4, id)`
- Company browse: `env['thedevkitchen.estate.company']` → `env['res.company']`
- User search: filter `estate_company_ids in [company_id]` → `company_ids in [company_id]`

---

## Field Mapping Reference

For controllers serializing company data, this mapping ensures backward compatibility:

| JSON Field | Old Source (`thedevkitchen.estate.company`) | New Source (`res.company`) |
|-----------|---------------------------------------------|---------------------------|
| `id` | `c.id` | `c.id` |
| `name` | `c.name` | `c.name` (native) |
| `cnpj` | `c.cnpj` | `c.cnpj` (added via `_inherit`) |
| `creci` | `c.creci` | `c.creci` (added via `_inherit`) |
| `legal_name` | `c.legal_name` | `c.legal_name` (added via `_inherit`) |
| `email` | `c.email` | `c.email` (native) |
| `phone` | `c.phone` | `c.phone` (native) |
| `mobile` | `c.mobile` | `c.partner_id.mobile` or add field |
| `website` | `c.website` | `c.website` (native) |
| `street` | `c.street` | `c.street` (native) |
| `street2` | `c.street2` | `c.street2` (native) |
| `city` | `c.city` | `c.city` (native) |
| `state_id` | `c.state_id.id` (real.estate.state) | `c.state_id.id` (res.country.state) |
| `state` | `c.state_id.name` | `c.state_id.name` |
| `zip_code` | `c.zip_code` | `c.zip` (native field name is `zip`) |
| `country_id` | `c.country_id.id` | `c.country_id.id` (native) |
| `foundation_date` | `c.foundation_date` | `c.foundation_date` (added via `_inherit`) |
| `description` | `c.description` | `c.description` (added via `_inherit`) |
| `property_count` | `c.property_count` (computed) | `c.property_count` (computed, same) |
| `agent_count` | `c.agent_count` (computed) | `c.agent_count` (computed, same) |

**Key Mapping Issue**: `zip_code` → `zip`. The request body accepts `zip_code` from API consumers. The controller must map `zip_code` → `zip` when writing to `res.company`. The response serialization must read from `c.zip` but output as `zip_code` for backward compatibility.
