# Phase 1 — Data Model: Service Pipeline (Atendimentos)

**Feature**: 015-service-pipeline-atendimentos
**Date**: 2026-05-03

## Entity Inventory

| Entity | Odoo `_name` | Purpose |
|--------|-------------|---------|
| Service (Atendimento) | `real.estate.service` | Pipeline entity tracking an agent–client engagement |
| Service Tag | `real.estate.service.tag` | Categorization labels (per company, with system flag) |
| Service Source | `real.estate.service.source` | Captation origin (Site, WhatsApp, Indicação…) per company |
| Partner Phone | `real.estate.partner.phone` | Multi-phone for clients linked to `res.partner` |
| Service Settings | `thedevkitchen.service.settings` | Singleton config per company (pendency threshold, etc.) |

Existing entities **referenced** (not modified beyond additive fields):
- `res.partner` (client) — extended with O2M `phone_ids`
- `res.users` (agent) — referenced
- `res.company` — referenced for multi-tenancy
- `real.estate.lead` (006) — optional M2O reference
- `real.estate.property` (existing) — M2M relation
- `real.estate.proposal` (013) — additive field `service_id` (M2O) for inverse lookup

---

## E1 · `real.estate.service`

**Inherits**: `mail.thread`, `mail.activity.mixin`
**Mode**: `_order = 'last_activity_date desc, id desc'`
**Sequence**: `ATD/YYYY/NNNNN` (defined in `service_sequence_data.xml`)

| Field | Type | Required | Default | Description |
|-------|------|---------|---------|-------------|
| `id` | Integer (PK) | auto | — | — |
| `name` | Char(50) | yes | computed via `ir.sequence` | Public ID (e.g., `ATD/2026/00101`) |
| `client_partner_id` | Many2one('res.partner') | yes | — | Client; `ondelete='restrict'` |
| `lead_id` | Many2one('real.estate.lead') | no | — | Optional origin lead; `ondelete='set null'`; no inverse on lead |
| `agent_id` | Many2one('res.users') | yes | `current_user` (creation) | Responsible agent; `ondelete='restrict'`; **indexed** |
| `operation_type` | Selection | yes | — | `sale`, `rent` |
| `source_id` | Many2one('real.estate.service.source') | yes | — | Captation source |
| `stage` | Selection | yes | `no_service` | `no_service`, `in_service`, `visit`, `proposal`, `formalization`, `won`, `lost`; **indexed** |
| `tag_ids` | Many2many('real.estate.service.tag') | no | — | Labels |
| `property_ids` | Many2many('real.estate.property') | no | — | Properties of interest |
| `proposal_ids` | One2many('real.estate.proposal','service_id') | no | — | Linked proposals (013) |
| `notes` | Text | no | — | Free-text observations |
| `last_activity_date` | Datetime | computed, stored | — | `max(write_date, latest user mail.message create_date)` — see R2 |
| `is_pending` | Boolean | computed, stored | False | True if `last_activity_date` older than `settings.pendency_threshold_days` |
| `is_orphan_agent` | Boolean | computed, stored | False | True if `agent_id.active == False` (FR-024a) |
| `lost_reason` | Char(255) | conditional (required iff stage='lost') | — | — |
| `won_date` | Datetime | conditional (set on stage='won') | — | Auto-filled by service layer |
| `company_id` | Many2one('res.company') | yes | `current_company` | Multi-tenancy; **indexed** |
| `active` | Boolean | yes | True | Soft delete (ADR-015) |
| `create_date`, `write_date`, `create_uid`, `write_uid` | auto (Odoo) | — | — | Audit |

### SQL Constraints

```sql
-- Created via migration (research R1) — NOT in _sql_constraints
ALTER TABLE real_estate_service
  ADD CONSTRAINT real_estate_service_unique_active_per_client_type_agent
  EXCLUDE (
    client_partner_id WITH =,
    operation_type WITH =,
    agent_id WITH =
  ) WHERE (active AND stage NOT IN ('won','lost'));
```

### Python Constraints (`@api.constrains`)

| Constraint | Triggers | Rule |
|-----------|---------|------|
| `_check_proposal_stage_requires_property` | `stage`, `property_ids` | If `stage='proposal'` then `property_ids` must be non-empty. |
| `_check_formalization_requires_approved_proposal` | `stage`, `proposal_ids.state` | If `stage='formalization'` then any of `proposal_ids` must have `state='accepted'`. |
| `_check_lost_requires_reason` | `stage`, `lost_reason` | If `stage='lost'` then `lost_reason` must be non-empty. |
| `_check_closed_tag_locks_stage` | `tag_ids`, `stage` | If `tag_ids` includes the system tag `closed` and `stage` is being changed (compared via `_origin`), raise. |
| `_check_orphan_agent_blocks_stage_change` | `stage`, `agent_id.active` | If `agent_id.active == False` and `stage` is being changed, raise (FR-024a). |
| `_check_terminal_stages_require_explicit_reopen` | `stage` | If transitioning from `won`/`lost` to a non-terminal stage without context flag `service.allow_reopen`, raise. |

### Indexes

| Name | Columns | Purpose |
|------|---------|---------|
| `idx_service_company_stage` | `(company_id, stage)` | Listing & summary aggregation |
| `idx_service_company_agent` | `(company_id, agent_id)` | Per-agent dashboards |
| `idx_service_company_lastactivity` | `(company_id, last_activity_date)` | Pendency ordering |
| `idx_service_active` | `(active) WHERE active = TRUE` | Default filter |

### State Diagram

```text
                     ┌────────────┐
                     │ no_service │ ───────────────┐
                     └──────┬─────┘                │
                            │                      │
                            ▼                      │
                     ┌────────────┐                │
                     │ in_service │ ───────────┐   │
                     └──────┬─────┘            │   │
                            │                  │   │
                            ▼                  │   │
                     ┌────────────┐            │   │
            ┌─────── │   visit    │ ────────┐  │   │
            │        └──────┬─────┘         │  │   │
            │               │               │  │   │
            │               ▼               │  │   │
            │        ┌────────────┐         │  │   │
            │        │  proposal  │ (gate: property_ids non-empty)
            │        └──────┬─────┘         │  │   │
            │               │               │  │   │
            │               ▼               │  │   │
            │        ┌──────────────┐       │  │   │
            │        │ formalization│ (gate: ∃ proposal with state=accepted)
            │        └──────┬───────┘       │  │   │
            │               │               │  │   │
            │               ▼               │  │   │
            │        ┌──────────┐           │  │   │
            │        │   won    │  (terminal — won_date set)
            │        └──────────┘           │  │   │
            │                               │  │   │
            └────────► ┌──────────┐ ◄───────┴──┴───┘
                       │   lost   │  (gate: lost_reason non-empty; from any non-terminal stage)
                       └──────────┘
```

Forward jumps allowed (e.g., `no_service → proposal`) provided gates pass (clarification Q1).
Backward (rollback) allowed except from terminal states (`won`/`lost`).

---

## E2 · `real.estate.service.tag`

| Field | Type | Required | Default | Description |
|-------|------|---------|---------|-------------|
| `id` | Integer (PK) | auto | — | — |
| `name` | Char(50) | yes | — | Label |
| `color` | Char(7) | yes | `#808080` | Hex color (`#RRGGBB`) |
| `is_system` | Boolean | yes | False | Immutable system tags drive business rules |
| `company_id` | Many2one('res.company') | yes | `current_company` | Multi-tenancy |
| `active` | Boolean | yes | True | Soft delete |

`_sql_constraints`:
- `unique_tag_name_per_company` — UNIQUE(`name`, `company_id`)
- `valid_color_format` — CHECK `color ~ '^#[0-9A-Fa-f]{6}$'`

`@api.constrains('name','active','is_system')`:
- If a tag has `is_system=True`, no user-initiated write to `name`/`active`/`is_system` is allowed except by admin via context flag `service.tag_admin`.

System tags (created in data XML on module install / post-init):
- `closed` — locks pipeline movement (FR-007)

Suggested non-system tags (created on post-init per company): `Follow Up`, `Qualificado`, `Lançamento`, `Parceria`.

---

## E3 · `real.estate.service.source`

| Field | Type | Required | Default | Description |
|-------|------|---------|---------|-------------|
| `id` | Integer (PK) | auto | — | — |
| `name` | Char(80) | yes | — | Display name |
| `code` | Char(30) | yes | — | Stable code (e.g., `site`, `whatsapp`) |
| `company_id` | Many2one('res.company') | yes | `current_company` | Multi-tenancy |
| `active` | Boolean | yes | True | Soft delete |

`_sql_constraints`:
- `unique_source_code_per_company` — UNIQUE(`code`, `company_id`)

Default sources (post-init hook per company): `Site`, `Indicação`, `Portal Imobiliário`, `WhatsApp`, `Plantão`.

---

## E4 · `real.estate.partner.phone`

| Field | Type | Required | Default | Description |
|-------|------|---------|---------|-------------|
| `id` | Integer (PK) | auto | — | — |
| `partner_id` | Many2one('res.partner') | yes | — | `ondelete='cascade'` |
| `phone_type` | Selection | yes | — | `mobile`, `home`, `work`, `whatsapp`, `fax` |
| `number` | Char(30) | yes | — | Free-form normalized to digits + DDI |
| `is_primary` | Boolean | no | False | At most one primary per partner (Python constraint) |

`@api.constrains('partner_id','is_primary')`:
- At most one phone with `is_primary=True` per `partner_id`.

Extension on `res.partner`:
- `phone_ids = One2many('real.estate.partner.phone','partner_id')`

---

## E5 · `thedevkitchen.service.settings`

Singleton per company (similar to `thedevkitchen.email.link.settings` from Feature 009).

| Field | Type | Required | Default | Range | Description |
|-------|------|---------|---------|-------|-------------|
| `id` | Integer (PK) | auto | — | — | — |
| `pendency_threshold_days` | Integer | yes | 3 | 1..30 | Days without interaction → `is_pending=True` |
| `auto_close_after_days` | Integer | no | 0 | 0..365 | 0 disables auto-close (future use) |
| `company_id` | Many2one('res.company') | yes | `current_company` | — | UNIQUE per company |

`_sql_constraints`:
- `unique_settings_per_company` — UNIQUE(`company_id`)

`@api.constrains`:
- `pendency_threshold_days` ∈ [1, 30]
- `auto_close_after_days` ∈ [0, 365]

Class method:
```python
@classmethod
def get_settings(cls, env, company_id=None):
    cid = company_id or env.company.id
    rec = env['thedevkitchen.service.settings'].search([('company_id','=',cid)], limit=1)
    if not rec:
        rec = env['thedevkitchen.service.settings'].create({'company_id': cid})
    return rec
```

---

## E6 · Additive field on `real.estate.proposal` (013)

To support `proposal_ids` One2many on Service:

| Field | Type | Required | Default | Description |
|-------|------|---------|---------|-------------|
| `service_id` | Many2one('real.estate.service') | no | — | `ondelete='set null'`; **indexed** |

This is an **additive, nullable** field — backward compatible.

---

## Record Rules (security/service_record_rules.xml)

```xml
<!-- Multi-tenancy by company -->
<record id="rule_service_company" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>

<!-- Agent: own services only -->
<record id="rule_service_agent_own" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="groups" eval="[(4, ref('thedevkitchen_user_onboarding.group_profile_agent'))]"/>
  <field name="domain_force">[('agent_id', '=', user.id)]</field>
</record>

<!-- Prospector: own services only -->
<record id="rule_service_prospector_own" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="groups" eval="[(4, ref('thedevkitchen_user_onboarding.group_profile_prospector'))]"/>
  <field name="domain_force">[('agent_id', '=', user.id)]</field>
</record>

<!-- Reception: read all in company; write none on services (handled by ir.model.access.csv) -->
<!-- Owner / Manager: full per company (handled by ir.model.access.csv) -->
```

`ir.model.access.csv` matrix per profile group (Owner, Manager, Agent, Reception, Prospector) for: `real.estate.service`, `real.estate.service.tag`, `real.estate.service.source`, `real.estate.partner.phone`, `thedevkitchen.service.settings`.

---

## Authorization Matrix (FR-010 implementation)

| Operation | Owner | Manager | Agent | Reception | Prospector |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Create service | ✓ | ✓ | ✓ | ✓ | ✓ |
| Read services | ✓ company | ✓ company | own only | ✓ company | own only |
| Update service | ✓ | ✓ | ✓ own | — | — |
| Delete (soft) | ✓ | ✓ | — | — | — |
| Stage transition | ✓ | ✓ | ✓ own | — | — |
| Reassign agent | ✓ | ✓ | — | — | — |
| Manage tags/sources | ✓ | ✓ | read | read | read |
| Manage settings | ✓ | ✓ | — | — | — |

---

## Validation Cross-Reference (Spec ↔ Model)

| Spec FR | Implementation |
|---------|----------------|
| FR-001 / FR-001a | `lead_id` M2O optional; no inverse on lead; no automatic propagation |
| FR-002 | `stage` Selection with 7 codes |
| FR-003 / FR-003a | `_track_visibility='onchange'` on stage; mail.thread auto-audit; terminal stages reject transitions without `service.allow_reopen` context |
| FR-004 | `_check_proposal_stage_requires_property` |
| FR-005 | `_check_formalization_requires_approved_proposal` |
| FR-006 | `_check_lost_requires_reason` |
| FR-007 | `_check_closed_tag_locks_stage` |
| FR-008 / FR-008a | EXCLUDE constraint on (client, type, agent) WHERE active AND stage∉(won,lost); no constraint on properties |
| FR-009 | `company_id` + record rules |
| FR-010 | ir.model.access.csv + record rules + controller-level RBAC |
| FR-011 | Controller filters via Odoo domain |
| FR-012 | Stored `last_activity_date` + `is_pending` |
| FR-013 | Pagination via controller `limit`/`offset` |
| FR-014 | `/summary` endpoint via `read_group` |
| FR-015 | `is_pending` computed; cron `service_recompute_pendency` daily |
| FR-016 / FR-017 | tag/source models + RBAC |
| FR-018 | `is_system` flag immutability |
| FR-019 | Soft delete on tags/sources via `active` |
| FR-020 | `service.settings.pendency_threshold_days` |
| FR-021 / FR-022 / FR-023 | `partner.phone` + `partner_dedup_service.py` |
| FR-024 / FR-024a | `reassign` controller action; `is_orphan_agent` computed; orphan blocks stage transitions |
| FR-025 | mail.thread audit + soft delete preserves history |
| FR-026 | `active` field; archived view filter |
