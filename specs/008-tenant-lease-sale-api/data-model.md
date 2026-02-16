# Data Model: Tenant, Lease & Sale API Endpoints

**Feature**: 008-tenant-lease-sale-api
**Date**: 2026-02-14

## Entity Relationship Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    res.partner    │     │  real.estate.     │     │  real.estate.    │
│   (Portal User)  │     │    property       │     │     agent        │
└────────┬─────────┘     └────────┬──────────┘     └────────┬─────────┘
         │ partner_id             │ property_id              │ agent_id
         ▼                        ▼                          ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  real.estate.    │◄────│  real.estate.     │     │  real.estate.    │
│    tenant        │     │     lease         │     │     sale         │
│                  │     │                   │     │                  │
│ name*            │     │ name (computed)   │     │ property_id* ────┤──► property
│ phone            │     │ property_id* ─────┤──►  │ buyer_name*      │
│ email            │     │ tenant_id*  ──────┤──►  │ buyer_phone      │
│ occupation       │     │ start_date*       │     │ buyer_email      │
│ birthdate        │     │ end_date*         │     │ sale_date*       │
│ partner_id       │     │ rent_amount*      │     │ sale_price*      │
│ profile_picture  │     │ status            │     │ agent_id ────────┤──► agent
│ company_ids (M2M)│     │ company_ids (M2M) │     │ lead_id          │
│ active           │     │ active            │     │ company_id (M2O) │
│ deactivation_date│     │ termination_date  │     │ company_ids (M2M)│
│ deactivation_    │     │ termination_reason│     │ status           │
│   reason         │     │ termination_      │     │ active           │
│                  │     │   penalty         │     │ cancellation_date│
│ leases (O2M) ───┤──►  │ renewal_history   │     │ cancellation_    │
│                  │     │   (O2M) ──────────┤──►  │   reason         │
└──────────────────┘     └────────┬──────────┘     └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ real.estate.lease │
                         │ .renewal.history  │
                         │                   │
                         │ lease_id*         │
                         │ previous_end_date │
                         │ previous_rent_amt │
                         │ new_end_date      │
                         │ new_rent_amount   │
                         │ renewed_by_id     │
                         │ reason            │
                         │ renewal_date      │
                         └──────────────────┘
```

`*` = required field, `M2M` = Many2many, `M2O` = Many2one, `O2M` = One2many

## Entity: Tenant (`real.estate.tenant`)

**Status**: EXISTS — needs field additions
**Table**: `real_estate_tenant`

### Current Fields (no changes)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char | required | Tenant name |
| `phone` | Char | | Phone number |
| `email` | Char | email format (regex validated) | Email address |
| `birthdate` | Date | | Date of birth |
| `occupation` | Char | | Occupation |
| `partner_id` | Many2one → `res.partner` | | Portal access link |
| `profile_picture` | Binary | | Profile photo |
| `company_ids` | Many2many → `thedevkitchen.estate.company` | | Multi-tenancy (relation: `thedevkitchen_company_tenant_rel`) |
| `leases` | One2many → `real.estate.lease` | | Back-reference to leases |

### New Fields (to add)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `active` | Boolean | default=True | Soft delete flag (ADR-015) |
| `deactivation_date` | Datetime | | When deactivated |
| `deactivation_reason` | Text | | Why deactivated |

### Validations

| Rule | Implementation | FR |
|------|---------------|-----|
| Email format | `@api.constrains('email')` — existing regex | FR-002 |

### State Transitions

None — Tenant is a simple CRUD entity with active/inactive toggle.

---

## Entity: Lease (`real.estate.lease`)

**Status**: EXISTS — needs field additions
**Table**: `real_estate_lease`

### Current Fields (no changes)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char | computed (stored) | Reference: `{property} - {tenant} ({start_date})` |
| `property_id` | Many2one → `real.estate.property` | required | Leased property |
| `tenant_id` | Many2one → `real.estate.tenant` | required | Tenant |
| `start_date` | Date | required | Start date |
| `end_date` | Date | required, > start_date | End date |
| `rent_amount` | Float | required | Monthly rent |
| `company_ids` | Many2many → `thedevkitchen.estate.company` | | Multi-tenancy (relation: `thedevkitchen_company_lease_rel`) |

### New Fields (to add)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `active` | Boolean | default=True | Soft delete flag (ADR-015) |
| `status` | Selection | default='draft' | Lifecycle state |
| `termination_date` | Date | | Early termination date |
| `termination_reason` | Text | | Why terminated |
| `termination_penalty` | Float | >= 0 | Optional penalty amount (informational) |
| `renewal_history_ids` | One2many → `real.estate.lease.renewal.history` | | Renewal audit trail |

### Status Selection Values

| Value | Label | Description |
|-------|-------|-------------|
| `draft` | Draft | Newly created, not yet active |
| `active` | Active | Currently in effect |
| `terminated` | Terminated | Ended early via termination action |
| `expired` | Expired | Past end_date naturally |

### Validations

| Rule | Implementation | FR |
|------|---------------|-----|
| end_date > start_date | `@api.constrains('start_date', 'end_date')` — existing | FR-010 |
| rent_amount > 0 | `@api.constrains('rent_amount')` — new | FR-011 |
| One active lease per property | `@api.constrains('property_id', 'status')` — new | FR-013 |
| Property/tenant exist and belong to company | Controller-level validation | FR-012 |

### State Transitions

```
draft ──► active ──► terminated
  │                      │
  │                      ▼
  │                   (end state)
  │
  └──► active ──► expired
                     │
                     ▼
                  (end state)

Renewal: active ──► active (in-place, audit history created)
```

- `draft → active`: Manual activation or automatic on start_date
- `active → terminated`: Via POST /leases/{id}/terminate
- `active → expired`: Automatic when current_date > end_date (or manual)
- `active → active (renewed)`: Via POST /leases/{id}/renew (extends end_date)

---

## Entity: Lease Renewal History (`real.estate.lease.renewal.history`)

**Status**: NEW — must be created
**Table**: `real_estate_lease_renewal_history`

### Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `lease_id` | Many2one → `real.estate.lease` | required, ondelete='cascade' | Parent lease |
| `previous_end_date` | Date | required | End date before renewal |
| `previous_rent_amount` | Float | required | Rent before renewal |
| `new_end_date` | Date | required | End date after renewal |
| `new_rent_amount` | Float | required | Rent after renewal |
| `renewed_by_id` | Many2one → `res.users` | required | User who performed renewal |
| `reason` | Text | | Renewal justification |
| `renewal_date` | Datetime | default=now, required | When renewal occurred |

### Security (ir.model.access.csv)

| Group | Read | Write | Create | Unlink |
|-------|------|-------|--------|--------|
| base.group_user | 1 | 0 | 0 | 0 |
| base.group_system | 1 | 1 | 1 | 1 |

---

## Entity: Sale (`real.estate.sale`)

**Status**: EXISTS — needs field additions
**Table**: `real_estate_sale`

### Current Fields (no changes)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `property_id` | Many2one → `real.estate.property` | required | Property sold |
| `buyer_name` | Char | required | Buyer name |
| `buyer_partner_id` | Many2one → `res.partner` | | Buyer portal access |
| `buyer_phone` | Char(20) | | Buyer phone |
| `buyer_email` | Char(120) | | Buyer email |
| `company_id` | Many2one → `thedevkitchen.estate.company` | | Primary company |
| `company_ids` | Many2many → `thedevkitchen.estate.company` | | Multi-tenancy (relation: `thedevkitchen_company_sale_rel`) |
| `agent_id` | Many2one → `real.estate.agent` | | Responsible agent |
| `lead_id` | Many2one → `real.estate.lead` | | Source lead |
| `sale_date` | Date | required | Date of sale |
| `sale_price` | Float | required | Price |

### New Fields (to add)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `active` | Boolean | default=True | Soft delete flag (ADR-015) |
| `status` | Selection | default='completed' | Lifecycle state |
| `cancellation_date` | Date | | When cancelled |
| `cancellation_reason` | Text | | Why cancelled |

### Status Selection Values

| Value | Label | Description |
|-------|-------|-------------|
| `completed` | Completed | Sale successfully registered |
| `cancelled` | Cancelled | Sale reverted/cancelled |

### Validations

| Rule | Implementation | FR |
|------|---------------|-----|
| sale_price > 0 | `@api.constrains('sale_price')` — new | FR-022 |
| agent belongs to same company | Controller-level validation | FR-023 |

### Event Emission

Existing `create()` override already emits `sale.created` event via `quicksol.event.bus`. No changes needed for FR-027.

### Side Effects

| Trigger | Action | FR |
|---------|--------|-----|
| Sale created | Set `property_id.state = 'sold'` | FR-029 |
| Sale cancelled | Revert `property_id.state` to previous value | FR-029 |

---

## Relationship Summary

| From | To | Type | FK Field | Constraint |
|------|----|------|----------|------------|
| Lease | Property | Many2one | `property_id` | required |
| Lease | Tenant | Many2one | `tenant_id` | required |
| Tenant | Lease | One2many | `leases` | inverse of tenant_id |
| Lease Renewal History | Lease | Many2one | `lease_id` | required, cascade |
| Lease Renewal History | User | Many2one | `renewed_by_id` | required |
| Sale | Property | Many2one | `property_id` | required |
| Sale | Agent | Many2one | `agent_id` | optional |
| Sale | Lead | Many2one | `lead_id` | optional |
| Tenant | Company | Many2many | `company_ids` | multi-tenancy |
| Lease | Company | Many2many | `company_ids` | multi-tenancy |
| Sale | Company | Many2many | `company_ids` | multi-tenancy |
| Sale | Company | Many2one | `company_id` | primary company |

## Migration Notes

- Adding `active = fields.Boolean(default=True)` is safe — Odoo defaults existing records to True
- Adding `status` selection fields requires setting a default for existing records
- New `lease_renewal_history` table created automatically by Odoo ORM on module upgrade
- No data migration scripts needed — all additions are backwards-compatible
