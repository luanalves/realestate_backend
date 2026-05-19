# Data Model: RBAC Capabilities API

**Phase**: 1 — Design  
**Feature**: `020-rbac-capabilities-api`  
**Branch**: `020-rbac-capabilities-api`  
**Date**: 2026-05-18

---

## Overview

This feature introduces **no new database tables or Odoo models**. All capability data is a
virtual, read-only projection derived from the authenticated request context at runtime.
No migrations are required.

The capability contract is composed from three existing sources:
1. **`res.users`** — Authenticated user identity and group membership
2. **`res.company`** — Active company context enforced by `@require_company`
3. **`ROLE_RULES`** — Module-level Python constant declared in `capability_service.py`

---

## Virtual Entities

These entities describe the response contract — they are not persisted.

### CapabilityResponse (Response Root)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `user` | `CapabilityUser` | required | Minimal identity context for the active session |
| `rules` | `list[CapabilityRule]` | required, never null | Ordered list of allowed CASL-safe rules |

**Contract invariants**:
- Exactly these two top-level keys — no additional fields (FR-004)
- `rules` is always an array; `[]` for no-role users, never `null` (FR-007)

---

### CapabilityUser (Nested Object)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `integer` | required | `res.users.id` of the authenticated user |
| `role` | `string \| null` | required | Resolved estate role string or `null` if none |
| `company_id` | `integer` | required | `res.company.id` of the active authenticated company |

**Contract invariants**:
- Exactly these three fields — no `name`, `email`, `companies` or other `/api/v1/me` fields (FR-005)
- `role` is one of: `"owner"`, `"director"`, `"manager"`, `"agent"`, `"prospector"`, `"receptionist"`, `"financial"`, `"legal"`, `"property_owner"`, `"tenant"`, or `null`

---

### CapabilityRule (List Item)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `action` | `string` | required, enum | One of the allowed MVP actions |
| `subject` | `string` | required, enum | One of the allowed MVP subjects |

**Contract invariants**:
- Only fields `action` and `subject` — no `inverted`, `conditions`, `fields` (CASL extended) (FR-012)
- Pairs are unique within a response — no duplicates (FR-015)
- Ordering is the canonical backend declarative contract order (FR-016)

---

## Allowed Actions (MVP Whitelist)

Declared in `ALLOWED_ACTIONS` constant in `capability_service.py`:

| Action | Semantic meaning |
|--------|-----------------|
| `view` | Read-only access to an entity or menu surface |
| `create` | Create a new record |
| `update` | Modify an existing record |
| `delete` | Remove a record |
| `reassign` | Transfer ownership/assignment of a record |
| `approve` | Grant approval to a record in a pending state |
| `cancel` | Cancel/abort a record |
| `export` | Export data (reporting surfaces) |

> `manage` is **intentionally excluded** from MVP. Explicit granular actions allow the frontend
> to distinguish individual buttons and routes without role-branching.

---

## Allowed Subjects (MVP Whitelist)

Declared in `ALLOWED_SUBJECTS` constant in `capability_service.py`:

| Subject | Category | Description |
|---------|----------|-------------|
| `MenuCRM` | Navigation | CRM / main operational menu surface |
| `MenuAdmin` | Navigation | Admin menu surface (owner-only) |
| `MenuCMS` | Navigation | CMS headless menu (not granted in MVP) |
| `Dashboard` | Product | Operational dashboard |
| `Property` | Product | Property listings and details |
| `Lead` | Product | Lead / prospect management |
| `Service` | Product | Service pipeline (atendimentos) |
| `Proposal` | Product | Property proposals |
| `Agent` | Product | Agent management |
| `Company` | Product | Company configuration |
| `Settings` | Product | Platform settings |
| `Appointment` | Product | Appointment scheduling (not granted in MVP) |
| `Report` | Product | Reporting and analytics |
| `Goal` | Product | Agent performance goals |
| `CMSPage` | CMS | CMS page management (not granted in MVP) |
| `CMSMedia` | CMS | CMS media library (not granted in MVP) |

**Deliberate MVP omissions** (no role receives these in v1):
- `MenuCMS`, `CMSPage`, `CMSMedia` — CMS headless surface not productized yet
- `Appointment` — No dedicated appointment capability contract in first delivery

---

## ROLE_RULES Matrix (Canonical Declaration)

Below is the complete grant matrix. Each role's rules are declared in **business/navigation
subject order** with **semantic action progression** per subject. This declaration order is
the canonical response contract order.

### Subject Order (canonical)
```
MenuCRM → MenuAdmin → MenuCMS → Dashboard →
Property → Lead → Service → Proposal →
Agent → Company → Settings → Appointment →
Report → Goal → CMSPage → CMSMedia
```

### Action Order within subject (canonical)
```
view → create → update → delete → reassign → approve → cancel → export
```

### Per-Role Grant Matrix

| Role | Subject | Granted Actions |
|------|---------|----------------|
| **owner** | MenuCRM | view |
| | MenuAdmin | view |
| | Dashboard | view |
| | Property | view, create, update, delete |
| | Lead | view, create, update, delete, reassign |
| | Service | view, create, update, delete, reassign, cancel |
| | Proposal | view, create, update, delete, approve, cancel |
| | Agent | view, create, update, delete |
| | Company | view, update |
| | Settings | view, update |
| | Report | view, export |
| | Goal | view |
| **director** | MenuCRM | view |
| | Dashboard | view |
| | Property | view, create, update |
| | Lead | view, create, update, reassign |
| | Service | view, create, update, reassign, cancel |
| | Proposal | view, create, update, approve, cancel |
| | Agent | view, update |
| | Company | view |
| | Report | view, export |
| | Goal | view |
| **manager** | MenuCRM | view |
| | Dashboard | view |
| | Property | view, create, update |
| | Lead | view, create, update, reassign |
| | Service | view, create, update, reassign, cancel |
| | Proposal | view, create, update, approve, cancel |
| | Agent | view, update |
| | Company | view |
| | Report | view, export |
| | Goal | view |

> **Note**: `director` and `manager` share an identical capability set by design.
> They differ in organizational hierarchy (director is above manager) but not in system access.
> This mirrors the existing codebase pattern where both roles receive the same inviteable profiles
> and resource permissions (see `invite_service.py`, `profile_api.py`).

| **agent** | MenuCRM | view |
| | Dashboard | view |
| | Property | view, create, update |
| | Lead | view, create, update |
| | Service | view, create, update, cancel |
| | Proposal | view, create, update, cancel |
| | Goal | view |
| **prospector** | MenuCRM | view |
| | Dashboard | view |
| | Property | view, create, update |
| **receptionist** | MenuCRM | view |
| | Property | view |
| | Service | view, create |
| | Proposal | view |
| **financial** | MenuCRM | view |
| | Property | view |
| | Service | view |
| | Proposal | view |
| | Company | view |
| | Report | view, export |
| **legal** | MenuCRM | view |
| | Property | view |
| | Service | view |
| | Proposal | view |
| | Company | view |
| **property_owner** | Property | view |
| | Proposal | view |
| **tenant** | Property | view |
| | Proposal | view |

---

## Existing Sources Reused

| Odoo Source | Field/Method Used | Purpose |
|-------------|-------------------|---------|
| `res.users` (request.env.user) | `.id`, `.company_id.id`, `.has_group(xml_id)` | User identity and role resolution |
| `res.company` (user.company_id) | `.id` | Active company context (set by `@require_company`) |
| `quicksol_estate.group_real_estate_*` | XML IDs in `role_map` dict | RBAC group lookup for role resolution |

---

## Data Flow

```
HTTP GET /api/v1/me/capabilities
         │
         ▼
@require_jwt         ← validates Bearer token (thedevkitchen_apigateway)
         │
         ▼
@require_session     ← validates session, sets request.env user, fingerprint check
         │
         ▼
@require_company     ← validates company context, sets request.user_company_ids
         │
         ▼
CapabilitiesController.get_capabilities()
         │
         ├── resolve role: iterate role_map, first has_group() match → role string or None
         │
         ├── call CapabilityService.get_rules(role)
         │     ├── if role is None → return []
         │     └── rules = ROLE_RULES.get(role, [])
         │           filter: seen set (dedup)
         │           filter: assert action in ALLOWED_ACTIONS, subject in ALLOWED_SUBJECTS
         │           → list[dict]  (declaration order preserved)
         │
         └── return make_json_response({
               "user": {"id": ..., "role": ..., "company_id": ...},
               "rules": [{"action": ..., "subject": ...}, ...]
             })
```

---

## Migration Plan

**No database migration required.** This feature is read-only and introduces no new:
- Odoo models
- PostgreSQL tables
- SQL constraints
- `ir.rule` records
- `ir.model.access` rows
- `res.groups` records

The only installation artefact is the new Python files (controller + service), which are
auto-discovered by Odoo's module loader when `quicksol_estate` is updated.

Module version bump: `quicksol_estate` `18.0.4.0.0` → `18.0.5.0.0`.
