# Data Model: Company Isolation Phase 1

**Feature**: Company Isolation Phase 1  
**Phase**: 1 (Design)  
**Date**: January 8, 2026

## Overview

This document defines the data model for multi-tenant company isolation, focusing on the Many2many relationships between estate entities and companies. The model enables users to be assigned to multiple companies and view aggregated data from all their assigned companies.

## Core Entities

### 1. Estate Company (`thedevkitchen.estate.company`)

**Purpose**: Represents a real estate agency/company in the multi-tenant system.

**Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer | Yes | Primary key |
| `name` | Char | Yes | Company name (e.g., "ABC Imóveis") |
| `registration` | Char | No | CNPJ registration number |
| `email` | Char | No | Company contact email |
| `phone` | Char | No | Company contact phone |
| `active` | Boolean | Yes | Soft delete flag (default: True) |

**Relationships**:
- One-to-Many with `res.users` via `estate_company_ids` (inverse Many2many)
- Many-to-Many with all estate entities (properties, agents, tenants, etc.)

**Indexes**:
- Primary key: `id`
- Unique constraint: `name` (per Odoo convention)

---

### 2. User (`res.users`)

**Purpose**: Odoo core user model extended with estate company assignments.

**Extended Fields** (added by `quicksol_estate`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | No | Companies user has access to |
| `estate_default_company_id` | Many2one | No | Default company for new records |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_user_rel',           # Junction table
    'user_id',                     # Column for res.users FK
    'company_id',                  # Column for company FK
    string='Real Estate Companies'
)
```

**Business Rules**:
- Users with 0 companies get 403 error on API calls (unless system admin)
- Users with 1 company: `estate_default_company_id` auto-set to that company
- Users with 2+ companies: `estate_default_company_id` must be manually selected
- System admins (`base.group_system`) bypass company filtering (see all data)

**Validation**:
- `estate_default_company_id` must be in `estate_company_ids` (if set)
- Cannot remove last company if user has assigned records

---

### 3. Property (`thedevkitchen.estate.property`)

**Purpose**: Real estate property listings with company ownership.

**Company-Related Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes | Companies that own/manage this property |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_property_rel',        # Junction table
    'property_id',                 # Column for property FK
    'company_id',                  # Column for company FK
    string='Companies',
    required=True
)
```

**Default Value**:
- On create: Auto-assign user's `estate_default_company_id` if `estate_company_ids` not provided

**Access Rules**:
- Users see only properties where `estate_company_ids` overlaps with their `estate_company_ids`
- Record Rule: `[('estate_company_ids', 'in', user.estate_company_ids.ids)]`
- API: Filtered via `request.company_domain`

---

### 4. Agent (`thedevkitchen.estate.agent`)

**Purpose**: Real estate agents (brokers, salespeople).

**Company-Related Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes | Companies agent works for |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_agent_rel',
    'agent_id',
    'company_id',
    string='Companies',
    required=True
)
```

**Business Rules**:
- Agents can work for multiple companies (common in Brazilian market)
- Commission tracking is per-property, not per-company
- Access follows same rules as properties

---

### 5. Tenant (`thedevkitchen.estate.tenant`)

**Purpose**: Individuals or businesses renting properties.

**Company-Related Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes | Companies managing this tenant |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_tenant_rel',
    'tenant_id',
    'company_id',
    string='Companies',
    required=True
)
```

---

### 6. Owner (`thedevkitchen.estate.owner`)

**Purpose**: Property owners (landlords, investors).

**Company-Related Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes | Companies managing owner's properties |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_owner_rel',
    'owner_id',
    'company_id',
    string='Companies',
    required=True
)
```

---

### 7. Building (`thedevkitchen.estate.building`)

**Purpose**: Buildings/condominiums containing multiple units.

**Company-Related Fields** (existing):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes | Companies managing this building |

**Many2many Configuration**:
```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    'company_building_rel',
    'building_id',
    'company_id',
    string='Companies',
    required=True
)
```

---

### 8. Lease (`thedevkitchen.estate.lease`) - TO VERIFY

**Purpose**: Rental contracts between owners and tenants.

**Company-Related Fields** (needs verification):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes? | Companies managing this lease |

**Note**: Implementation may need to be added during Phase 1. Verify if field exists.

---

### 9. Sale (`thedevkitchen.estate.sale`) - TO VERIFY

**Purpose**: Sales contracts/transactions.

**Company-Related Fields** (needs verification):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estate_company_ids` | Many2many | Yes? | Companies involved in this sale |

**Note**: Implementation may need to be added during Phase 1. Verify if field exists.

---

## Junction Tables

All Many2many relationships use dedicated junction tables in PostgreSQL.

### Schema Pattern

```sql
CREATE TABLE company_<entity>_rel (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    <entity>_id INTEGER NOT NULL REFERENCES thedevkitchen_estate_<entity>(id) ON DELETE CASCADE,
    UNIQUE(company_id, <entity>_id)
);

CREATE INDEX idx_company_<entity>_company ON company_<entity>_rel(company_id);
CREATE INDEX idx_company_<entity>_entity ON company_<entity>_rel(<entity>_id);
```

### Junction Tables List

1. `company_user_rel` - Users ↔ Companies
2. `company_property_rel` - Properties ↔ Companies
3. `company_agent_rel` - Agents ↔ Companies
4. `company_tenant_rel` - Tenants ↔ Companies
5. `company_owner_rel` - Owners ↔ Companies
6. `company_building_rel` - Buildings ↔ Companies
7. `company_lease_rel` - Leases ↔ Companies (if applicable)
8. `company_sale_rel` - Sales ↔ Companies (if applicable)

**Indexes** (required for performance):
- All junction tables have indexes on both `company_id` and `<entity>_id`
- Unique constraint on `(company_id, <entity>_id)` pair prevents duplicates

---

## Filtering Logic

### ORM Domain Pattern

All search operations include company filter:

```python
# In controller (after @require_company decorator):
domain = [('estate_company_ids', 'in', request.user_company_ids)]
properties = request.env['thedevkitchen.estate.property'].search(domain)
```

### SQL Query (Generated by Odoo ORM)

```sql
SELECT property.* 
FROM thedevkitchen_estate_property AS property
INNER JOIN company_property_rel AS rel 
    ON property.id = rel.property_id
WHERE rel.company_id IN (1, 2, 3)  -- user's estate_company_ids
```

### Record Rule Domain

```python
# In security.xml:
domain_force = [('estate_company_ids', 'in', user.estate_company_ids.ids)]
```

---

## State Transitions

### Property Lifecycle with Companies

```
┌─────────────────────────────────────────────────┐
│ 1. Property Created                             │
│    estate_company_ids = [user.default_company]  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ 2. Company Assignment Validated                 │
│    CompanyValidator.validate_company_ids()      │
│    → Ensures all IDs in user's estate_company_ids│
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ 3. Property Saved to Database                   │
│    junction table: company_property_rel         │
│    rows created: (company_id=1, property_id=42) │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ 4. Property Queryable by Authorized Users       │
│    Users with company_id=1 can see property 42  │
│    Users with other companies cannot see it     │
└─────────────────────────────────────────────────┘
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| User creates property without `estate_company_ids` | Auto-assign `estate_default_company_id` |
| User creates property with `estate_company_ids=[X]` where X is unauthorized | 403 Forbidden error from `CompanyValidator` |
| User updates property to remove all companies | Error: `estate_company_ids` is required |
| User updates property to add unauthorized company | 403 Forbidden error |
| User's company assignment removed while viewing property | Next API call returns 404 (property no longer visible) |
| Admin user views properties | Sees all properties (bypasses filtering) |

---

## Migration Considerations

### Existing Data

If the database already has properties without `estate_company_ids`:

1. Create a default "Legacy" company
2. Assign all orphaned records to "Legacy" company
3. Assign all existing users to "Legacy" company
4. Administrators manually reassign records to correct companies via Odoo Web UI

### Migration Script (if needed)

```python
# In Odoo migration script (post-migration.py):
def migrate(cr, version):
    # Create default company
    cr.execute("""
        INSERT INTO thedevkitchen_estate_company (name, active, create_date, write_date)
        VALUES ('Legacy Company', TRUE, NOW(), NOW())
        RETURNING id
    """)
    legacy_company_id = cr.fetchone()[0]
    
    # Assign orphaned properties
    cr.execute("""
        INSERT INTO company_property_rel (company_id, property_id)
        SELECT %s, p.id
        FROM thedevkitchen_estate_property p
        LEFT JOIN company_property_rel cpr ON p.id = cpr.property_id
        WHERE cpr.property_id IS NULL
    """, (legacy_company_id,))
    
    # Similar for other entities...
```

---

## Summary

- **9 entities** with company relationships (8 confirmed + 2 to verify)
- **8 junction tables** for Many2many relationships
- **Filtering at ORM level** via `('estate_company_ids', 'in', user_ids)`
- **Validation at service layer** via `CompanyValidator`
- **Record Rules** enforce isolation in Odoo Web UI
- **Migration strategy** for existing data (if needed)

**Status**: ✅ Data model complete and aligned with existing codebase structure.
