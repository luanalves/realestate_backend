# Phase 1 Data Model: Property Proposals Management

**Feature**: 013-property-proposals
**Date**: 2026-04-27
**Source**: derived from [spec.md](spec.md) FR-001 — FR-048 and [research.md](research.md).

---

## Entities Overview

| Entity | Status | Module | Purpose |
|---|---|---|---|
| `real.estate.proposal` | NEW | `quicksol_estate` | Core entity. Captures the full proposal lifecycle. |
| `real.estate.lead` | EXTEND | `quicksol_estate` | Add `source` Selection field + `proposal_ids` reverse One2many. |
| `real.estate.property` | EXTEND | `quicksol_estate` | Add `proposal_ids` reverse One2many + override `write` for archive cascade. |
| `res.partner` | REUSED | base | Resolved by document (CPF/CNPJ); never modified by this feature. |
| `real.estate.agent` | REUSED | `quicksol_estate` | Read-only reference for assignment validation. |
| `ir.attachment` | REUSED | base | Standard Odoo attachment store; `res_model='real.estate.proposal'`. |
| `mail.template` | REUSED | mail | 7 new template records (data XML); not a model extension. |

---

## 1. `real.estate.proposal` (NEW)

**Inherits**: `mail.thread`, `mail.activity.mixin`
**Description**: A property proposal — an offer from a client on a property, tracked through the 8-state FSM with FIFO queueing.

### 1.1 Fields

| Field | Type | Required | Default | Stored | Description |
|---|---|:---:|---|:---:|---|
| `id` | Integer (PK) | auto | auto | yes | Primary key. |
| `proposal_code` | Char(20) | yes | sequence `PRP###` | yes | Unique per company; readonly. |
| `name` | Char | computed | — | yes | Display name = `proposal_code + property.name`. |
| `property_id` | Many2one(`real.estate.property`) | yes | — | yes | Target property. `ondelete='restrict'`. Indexed. |
| `partner_id` | Many2one(`res.partner`) | yes | — | yes | Client. Resolved by document at creation. `ondelete='restrict'`. Indexed. |
| `lead_id` | Many2one(`real.estate.lead`) | no | — | yes | Origin or auto-created lead. `ondelete='set null'`. |
| `agent_id` | Many2one(`real.estate.agent`) | yes | — | yes | Responsible agent. `ondelete='restrict'`. Indexed. Must be in `property_id.assigned_agent_ids` at creation. |
| `proposal_type` | Selection | yes | — | yes | `sale` \| `lease`. |
| `proposal_value` | Monetary | yes | — | yes | Offer amount. CHECK > 0. |
| `currency_id` | Many2one(`res.currency`) | yes | BRL | yes | Currency. |
| `state` | Selection | yes | `draft` | yes | One of 8 states (see §1.3). Indexed. |
| `description` | Text | no | — | yes | Notes / context. |
| `rejection_reason` | Text | conditional | — | yes | Required when `state='rejected'`. |
| `cancellation_reason` | Text | conditional | — | yes | Required when `state='cancelled'`. |
| `valid_until` | Date | no | — | yes | Validity. Bounds: `> today` AND `<= create_date + 90 days`. Auto-set to `sent_date + 7d` on `/send` if blank. |
| `sent_date` | Datetime | computed | — | yes | Set by `action_send`; readonly. |
| `accepted_date` | Datetime | computed | — | yes | Set by `action_accept`; readonly. |
| `rejected_date` | Datetime | computed | — | yes | Set by `action_reject`; readonly. |
| `parent_proposal_id` | Many2one(self) | no | — | yes | Parent in counter-proposal chain. `ondelete='set null'`. |
| `child_proposal_ids` | One2many(self, `parent_proposal_id`) | computed | — | no | Direct children. |
| `proposal_chain_ids` | Many2many(self) | computed | — | no | Full ancestor + descendant chain (chronological). |
| `superseded_by_id` | Many2one(self) | no | — | yes | The accepted proposal that auto-cancelled this one. `ondelete='set null'`. |
| `queue_position` | Integer | computed | — | yes | 0 = active; ≥1 = position in queue (FIFO); NULL = terminal. |
| `is_active_proposal` | Boolean | computed | — | yes | True iff this is the property's currently active proposal. |
| `attachment_ids` | One2many(`ir.attachment`, via `res_id`+`res_model`) | computed | — | no | Linked documents. |
| `documents_count` | Integer | computed | 0 | yes | Number of attachments. |
| `has_competing_proposals` | Boolean | computed | False | no | True iff other non-terminal proposals exist on same property. |
| `company_id` | Many2one(`res.company`) | yes | `env.company` | yes | Multi-tenant scope. Indexed. |
| `active` | Boolean | yes | True | yes | Soft-delete flag (per ADR-015). |
| `create_uid`, `create_date`, `write_uid`, `write_date` | — | auto | auto | yes | Audit columns (Odoo built-in). |

### 1.2 Computed Field Logic

- **`name`**: `f"{self.proposal_code} - {self.property_id.name}"`. Trigger: `proposal_code`, `property_id`.
- **`queue_position`**: per [research.md §R9](research.md#r9-queue-position-computation). Trigger: `(property_id, state, create_date, active)`.
- **`is_active_proposal`**: `state in ('draft','sent','negotiation','accepted') AND active=True AND parent_proposal_id is NULL OR (counter rule per R4)`. Trigger: same as above.
- **`documents_count`**: `len(env['ir.attachment'].search([('res_model','=','real.estate.proposal'),('res_id','=',rec.id)]))`. Trigger: `attachment_ids`.
- **`has_competing_proposals`**: `bool(self.search_count([('property_id','=',rec.property_id.id), ('id','!=',rec.id), ('state','in',['queued','draft','sent','negotiation']), ('active','=',True)]))`.
- **`proposal_chain_ids`**: recursive walk via `parent_proposal_id` and `child_proposal_ids`, ordered by `create_date ASC`.

### 1.3 State Machine

```
                        ┌─[counter]──┐
                        ▼            │
draft ──/send─────► sent ──/negotiation transition (parent ↔ child counters)
  │                  │
  │                  ├──/accept──► accepted ── (terminal; auto-cancel siblings)
  │                  ├──/reject──► rejected ── (terminal; promote next queued)
  │                  ├──[cron expire]──► expired ── (terminal; promote next queued)
  │                  └──/cancel──► cancelled ── (terminal; promote next queued)
  └──/cancel──► cancelled (terminal)

queued ──[auto-promote on slot release]──► draft
queued ──[auto-supersede on parent accept]──► cancelled (with superseded_by_id)
queued ──/cancel (manual)──► cancelled
```

**Allowed transitions** (others raise `ValidationError`) — per spec FR-022, FR-023, FR-024:

| From | Allowed To | Trigger |
|---|---|---|
| `draft` | `sent`, `cancelled` | manual |
| `queued` | `draft`, `cancelled` | auto-promote OR manual cancel OR auto-supersede |
| `sent` | `negotiation`, `accepted`, `rejected`, `expired`, `cancelled` | manual (counter / accept / reject / cancel) or cron (expired) |
| `negotiation` | `accepted`, `rejected`, `expired`, `cancelled` | manual or cron |
| `accepted`, `rejected`, `expired`, `cancelled` | (terminal) | none |

> **Note (reconciled with spec FR-023)**: `negotiation → sent` is **not** an allowed transition. Once a parent proposal enters `negotiation` due to a counter-proposal, it remains there until reaching a terminal state (when its child counter is resolved, the parent is set to `accepted`/`rejected`/`cancelled` accordingly — see acceptance auto-supersede rule FR-014).

### 1.4 Constraints

**SQL constraints** (`_sql_constraints`):

```python
('proposal_code_company_uniq', 'unique(proposal_code, company_id)',
 'Proposal code must be unique per company.'),
('proposal_value_positive', 'CHECK(proposal_value > 0)',
 'Proposal value must be greater than zero.'),
```

**Partial unique index** (created in `migrations/18.0.1.x.0/post-migrate.py`):

```sql
CREATE UNIQUE INDEX real_estate_proposal_one_active_per_property
ON real_estate_proposal (property_id)
WHERE state IN ('draft','sent','accepted') AND active = true
  AND parent_proposal_id IS NULL;
```

> Note the inclusion of `parent_proposal_id IS NULL` so that counter-proposals (which have a parent) do not collide with their parent's slot. The parent moves to `negotiation` (excluded from the index) at the same time, so the invariant remains correct.

**Python constraints** (`@api.constrains`):

| Method | Validation |
|---|---|
| `_check_property_same_company` | `property_id.company_id == company_id` |
| `_check_agent_assigned_to_property` | `agent_id in property_id.assigned_agent_ids` (only on create) |
| `_check_rejection_reason` | `state='rejected'` ⇒ `rejection_reason` non-empty |
| `_check_cancellation_reason` | `state='cancelled'` ⇒ `cancellation_reason` non-empty |
| `_check_valid_until_bounds` | `valid_until` is None OR (`valid_until > today` AND `valid_until <= create_date + 90 days`) |
| `_check_one_active_per_property` | Application-level mirror of partial unique index (defense-in-depth) |
| `_check_counter_consistency` | `parent_proposal_id` exists ⇒ same `property_id`, same `partner_id`, same `company_id` |
| `_check_proposal_type` | `proposal_type in ('sale','lease')` |
| `_check_document_format` | `partner_id.vat` is valid CPF or CNPJ (delegate to `utils/validators.py`) |

### 1.5 Indexes

| Index | Columns | Purpose |
|---|---|---|
| `real_estate_proposal_state_idx` | `(state)` | Filter by state in lists. |
| `real_estate_proposal_company_idx` | `(company_id)` | Multi-tenant scoping. |
| `real_estate_proposal_agent_idx` | `(agent_id)` | Agent's own proposals listing. |
| `real_estate_proposal_property_idx` | `(property_id)` | Property's queue lookup. |
| `real_estate_proposal_partner_idx` | `(partner_id)` | Lookup by client. |
| `real_estate_proposal_state_company_idx` | `(state, company_id)` | Composite for stats/list. |
| `real_estate_proposal_property_state_created_idx` | `(property_id, state, create_date)` | FIFO queue computation (R9). |
| `real_estate_proposal_one_active_per_property` | partial unique on `(property_id)` | Invariant guard. |

### 1.6 Record Rules (`security/proposal_record_rules.xml`)

| Rule | Domain | Groups |
|---|---|---|
| Company isolation | `[('company_id', 'in', company_ids)]` | `base.group_user` |
| Agent: own only | `[('agent_id.user_id', '=', user.id)]` | `quicksol_estate.group_estate_agent` |
| Manager / Owner: all in org | `[('company_id', 'in', company_ids)]` | `quicksol_estate.group_estate_manager`, `group_estate_owner` |
| Receptionist: read-only | `[('company_id', 'in', company_ids)]` | `quicksol_estate.group_estate_receptionist` (perm_read=1, perm_write=0) |
| Prospector: deny | (no rule; access removed in `ir.model.access.csv`) | `quicksol_estate.group_estate_prospector` |

### 1.7 Sequence

```xml
<record id="seq_real_estate_proposal" model="ir.sequence">
    <field name="name">Real Estate Proposal</field>
    <field name="code">real.estate.proposal</field>
    <field name="prefix">PRP</field>
    <field name="padding">3</field>
    <field name="company_id" eval="False"/>  <!-- per-company auto-creates copies -->
</record>
```

---

## 2. `real.estate.lead` (EXTEND)

**Changes**:

| Field | Action | Description |
|---|---|---|
| `source` | ADD | `Selection`. Initial values: `[('proposal', 'Proposal'), ('website', 'Website'), ('referral', 'Referral'), ('manual', 'Manual'), ('other', 'Other')]`. Default: `'manual'`. |
| `proposal_ids` | ADD | `One2many('real.estate.proposal', 'lead_id', string='Proposals')`. |
| `proposal_count` | ADD | `Integer` (computed, stored). Quick reference for UI. |

**Migration** (`migrations/18.0.1.x.0/pre-migrate.py`):

- Sets `source='manual'` for all existing leads (data migration).
- No data loss; backfill is non-destructive.

**Active state set for de-duplication** (per FR-030):

```python
ACTIVE_LEAD_STATES = ('new', 'contacted', 'qualified', 'won')
```

---

## 3. `real.estate.property` (EXTEND)

**Changes**:

| Field | Action | Description |
|---|---|---|
| `proposal_ids` | ADD | `One2many('real.estate.proposal', 'property_id')`. |
| `active_proposal_id` | ADD | `Many2one('real.estate.proposal')`, computed, stored. The single active proposal (or False). |
| `proposal_count` | ADD | `Integer` (computed, stored). |
| `queued_proposal_count` | ADD | `Integer` (computed, stored). |

**Method override**:

```python
def write(self, vals):
    res = super().write(vals)
    if 'active' in vals and vals['active'] is False:
        # Cascade per FR-046a
        for prop in self:
            non_terminal = prop.proposal_ids.filtered(
                lambda p: p.state in ('draft','queued','sent','negotiation')
            )
            for proposal in non_terminal:
                proposal.action_cancel(
                    reason='Property withdrawn from market',
                    auto=True,
                )
    return res
```

---

## 4. State Transitions Side-Effect Map

| Action | Direct State Change | Side Effects |
|---|---|---|
| `create()` | → `draft` (slot empty) OR `queued` | Acquire `SELECT FOR UPDATE` on property; resolve/create partner; resolve/create lead; assign queue position. |
| `action_send()` | `draft` → `sent` | Set `sent_date`; default `valid_until`; emit `proposal.notification` event (`proposal_sent` template). |
| `action_accept()` | `sent`/`negotiation` → `accepted` | Set `accepted_date`; auto-cancel all sibling non-terminal proposals (set `superseded_by_id`); emit `proposal.accepted` event (Observer per ADR-020); enqueue notifications for winner + each cancelled. |
| `action_reject(reason)` | `sent`/`negotiation` → `rejected` | Set `rejected_date`, `rejection_reason`; emit notification; trigger queue promotion. |
| `action_counter(value, ...)` | parent → `negotiation`; create new child `sent` | Inherit fields; child uses parent's slot. |
| `action_cancel(reason)` | (any non-terminal) → `cancelled` | Set `cancellation_reason`; soft-delete (`active=False`); trigger queue promotion if was active. |
| Cron `cron_expire_proposals` | `sent`/`negotiation` → `expired` (where `valid_until < today`) | Trigger queue promotion per affected property. |
| Promotion (internal) | `queued` → `draft` (oldest) | Recompute `queue_position` for siblings; emit `proposal_promoted` notification. |

---

## 5. ER Diagram (textual)

```
res.company ──┐
              ├─< real.estate.proposal >── res.currency
              │   ▲ ▲ ▲ ▲ ▲ ▲
              │   │ │ │ │ │ │
              │   │ │ │ │ │ └── ir.attachment (1:N via res_model+res_id)
              │   │ │ │ │ └── real.estate.proposal (parent_proposal_id self-ref, N:1)
              │   │ │ │ └── real.estate.proposal (superseded_by_id self-ref, N:1)
              │   │ │ └── real.estate.lead (lead_id, N:1, optional)
              │   │ └── real.estate.agent (agent_id, N:1)
              │   └── real.estate.property (property_id, N:1)
              │
              └─ res.partner (partner_id, N:1, resolved by document)
```

---

## 6. Validation Summary (cross-reference to FRs)

| FR | Enforced by |
|---|---|
| FR-002 unique code per org | `_sql_constraints.proposal_code_company_uniq` + sequence |
| FR-003 value > 0 | SQL CHECK + ADR-018 schema validator |
| FR-004 type sale/lease | Selection + Python constraint |
| FR-006 8 states + valid transitions | FSM table in `_set_state()` |
| FR-008 single active per property | partial unique index + Python constraint + pessimistic lock |
| FR-014 supersede on accept | `action_accept` cascade |
| FR-016 race-free creation | `SELECT FOR UPDATE` on property |
| FR-018 counter logic | `action_counter` + `parent_proposal_id` excluded from unique index |
| FR-020 rejection reason required | Python constraint |
| FR-021 cancellation reason required | Python constraint |
| FR-025 default validity 7d | `action_send` |
| FR-025a validity bounds | Python constraint |
| FR-026 daily expiration | `cron_expire_proposals` |
| FR-029 lead source 'proposal' | Selection extension |
| FR-030/031 active lead de-dup | Service-layer logic in `_resolve_or_create_lead()` |
| FR-033 CPF/CNPJ valid | `utils/validators.py` |
| FR-039 attachment whitelist + size | controller validation |
| FR-041a Outbox async | Celery dispatch |
| FR-043 multi-tenant isolation | record rules + `@require_company` |
| FR-046 soft-delete | `active=False`, never DELETE |
| FR-046a property archive cascade | `real.estate.property.write()` override |
| FR-048 no cross-org leakage | record rules + 404 fallback in controller |
