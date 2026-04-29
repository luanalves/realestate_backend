# Data Model: Rental Credit Check (spec 014)

**Date**: 2026-04-29
**Branch**: `014-rental-credit-check`
**Module**: `thedevkitchen_estate_credit_check`
**Status**: Phase 1 design — final

---

## Overview

Spec 014 introduces one new entity (`thedevkitchen.estate.credit.check`) and extends two existing entities via `_inherit` (`thedevkitchen.estate.proposal` and `res.partner`).

---

## Entity 1 — `thedevkitchen.estate.credit.check`

**Table**: `thedevkitchen_estate_credit_check`
**Module**: `thedevkitchen_estate_credit_check`
**Mixins**: `mail.thread`, `mail.activity.mixin`

### Fields

| Field | Odoo type | Nullable | Index | Description |
|-------|-----------|----------|-------|-------------|
| `proposal_id` | `Many2one('thedevkitchen.estate.proposal')` | NO | YES | Parent proposal. `ondelete='cascade'`. |
| `company_id` | `Many2one('res.company')` | NO | YES | Denormalized from proposal. Auto-populated on create. Enables company-scoped record rules without join. |
| `partner_id` | `Many2one('res.partner')` | NO | YES | Tenant being analysed. Denormalized from `proposal.partner_id`. |
| `insurer_name` | `Char(size=255)` | NO | NO | Name of the insurer performing the analysis (free text, FR-008, FR-022). Required on create. |
| `result` | `Selection` | NO | YES | `[('pending','Pending'),('approved','Approved'),('rejected','Rejected'),('cancelled','Cancelled')]`. Default `'pending'`. |
| `requested_by` | `Many2one('res.users')` | NO | NO | User who requested the check. Set from `env.user` on create. `ondelete='restrict'`. |
| `requested_at` | `Datetime` | NO | NO | `default=fields.Datetime.now`. Set on create. |
| `result_registered_by` | `Many2one('res.users')` | YES | NO | Manager/Owner who registered the result. Set on `approve` / `reject` / `cancel`. `ondelete='set null'`. |
| `result_registered_at` | `Datetime` | YES | NO | When result was registered. Set when `result` changes from `pending`. |
| `rejection_reason` | `Text` | YES | NO | Required when `result = 'rejected'`. `@api.constrains` enforces. |
| `check_date` | `Date` | YES | NO | Date the analysis was performed by insurer. Optional informational field. |
| `active` | `Boolean` | NO | NO | Default `True`. Enables soft-delete (ADR-015). |

### Python Constraints

```python
@api.constrains('result', 'rejection_reason')
def _check_rejection_reason(self):
    for rec in self:
        if rec.result == 'rejected' and not rec.rejection_reason:
            raise ValidationError(_("Rejection reason is required when result is Rejected."))
```

### DB-Level Constraint (partial unique index)

```sql
-- Ensures at most one pending check per proposal (inserted in the module's _auto_init or data migration)
CREATE UNIQUE INDEX thedevkitchen_estate_credit_check_one_pending_per_proposal
ON thedevkitchen_estate_credit_check (proposal_id)
WHERE result = 'pending' AND active = true;
```

Implementation note: declared via `_sql_constraints` where possible; for partial indexes use `_auto_init()` override.

### State Machine

```
pending ──(approve)──► approved   [terminal]
pending ──(reject)───► rejected   [terminal]
pending ──(cancel)───► cancelled  [terminal — manual cancel]
pending ──(cron)─────► cancelled  [terminal — proposal expired]
```

All transitions: `result_registered_by` = `env.user`, `result_registered_at` = `Datetime.now()`.

### Record Rules

```xml
<!-- company isolation — applied to all CRUD -->
<record id="rule_credit_check_company" model="ir.rule">
  <field name="name">Credit Check: company isolation</field>
  <field name="model_id" ref="model_thedevkitchen_estate_credit_check"/>
  <field name="domain_force">[('company_id', 'in', user.company_ids.ids)]</field>
</record>
```

---

## Entity 2 — `thedevkitchen.estate.proposal` (extension)

**Module**: `thedevkitchen_estate_credit_check` via `_inherit`
**New fields added**:

| Field | Odoo type | Description |
|-------|-----------|-------------|
| `state` | `Selection` (extended) | Add `('credit_check_pending', 'Credit Check Pending')` between `sent` and `accepted`. |
| `credit_check_ids` | `One2many('thedevkitchen.estate.credit.check', 'proposal_id')` | Reverse relation to all credit checks for this proposal. |
| `credit_history_summary` | `Char` (computed, `store=False`) | `"N approved / M rejected"` for `partner_id` across all proposals in `company_id`. See `_compute_credit_history_summary()`. |

**State machine extension** (full updated sequence):

```
draft → sent → credit_check_pending → accepted  [terminal]
                                    → rejected  [terminal]
draft → sent → negotiation → credit_check_pending → accepted  [terminal]
                                                  → rejected  [terminal]
draft → sent → expired   [terminal — cron, no credit check]
draft → sent → credit_check_pending → expired   [terminal — cron, validity elapsed while pending]
draft → sent → credit_check_pending → cancelled [terminal — proposal manually cancelled, FR-007b]
draft → sent → credit_check_pending → sent      [CreditCheck cancelled via API PATCH, FR-007c]
draft → queued → (promoted) → draft → ...
```

**New transition guard** (counter-proposal block):

```python
# In proposal model extension
def _can_create_counter_proposal(self):
    self.ensure_one()
    if self.state == 'credit_check_pending':
        raise UserError(_("Counter-proposal not allowed while credit check is pending."))
    return super()._can_create_counter_proposal()
```

**New service method — initiate credit check**:

```python
def action_initiate_credit_check(self):
    """Transition proposal from 'sent' → 'credit_check_pending' and create CreditCheck record."""
    self.ensure_one()
    if self.state not in ('sent', 'negotiation'):
        raise UserError(_("Credit check can only be initiated on sent or negotiation proposals."))
    # guard: no other active pending check
    existing = self.env['thedevkitchen.estate.credit.check'].search([
        ('proposal_id', '=', self.id),
        ('result', '=', 'pending'),
        ('active', '=', True),
    ], limit=1)
    if existing:
        raise UserError(_("A credit check is already pending for this proposal."))
    self.env['thedevkitchen.estate.credit.check'].create({
        'proposal_id': self.id,
        'company_id': self.company_id.id,
        'partner_id': self.partner_id.id,
        'insurer_name': insurer_name,
    })
    self.write({'state': 'credit_check_pending'})
```

---

## Entity 3 — `res.partner` (read-only extension)

**No new fields stored on `res.partner`** — credit history is derived from `thedevkitchen.estate.credit.check` records linked via `partner_id`.

**Computed method** (on `thedevkitchen.estate.proposal`):

```python
@api.depends()
def _compute_credit_history_summary(self):
    for rec in self:
        if not rec.partner_id:
            rec.credit_history_summary = ''
            continue
        checks = self.env['thedevkitchen.estate.credit.check'].search([
            ('partner_id', '=', rec.partner_id.id),
            ('company_id', '=', rec.company_id.id),
            ('active', '=', True),
        ])
        approved = len(checks.filtered(lambda c: c.result == 'approved'))
        rejected = len(checks.filtered(lambda c: c.result == 'rejected'))
        rec.credit_history_summary = f"{approved} aprovada(s) / {rejected} rejeitada(s)"
```

---

## Relationships Diagram

```
res.partner ◄──────────────────────────────────────────────────────┐
      ▲                                                             │
      │ partner_id                                                  │ partner_id
      │                                                             │
thedevkitchen.estate.proposal ──(1:N)──► thedevkitchen.estate.credit.check
      │                                         │
      │ company_id                              │ company_id
      ▼                                         ▼
  res.company ◄────────────────────────── res.company
```

---

## Access Control Matrix

| Profile | Create CreditCheck | Approve/Reject | Cancel | Read |
|---------|--------------------|----------------|--------|------|
| Owner | YES (via API + UI) | YES | YES | YES |
| Manager | YES (via API + UI) | YES | YES | YES |
| Agent | YES (via API only) | NO | NO | YES (own proposals) |
| Other profiles | NO | NO | NO | NO |

Record rules enforce company isolation for all operations.

---

## Indices Summary

| Table | Column(s) | Type | Purpose |
|-------|-----------|------|---------|
| `thedevkitchen_estate_credit_check` | `proposal_id` | B-tree | FK join |
| `thedevkitchen_estate_credit_check` | `company_id` | B-tree | Record rule filter |
| `thedevkitchen_estate_credit_check` | `partner_id` | B-tree | History query |
| `thedevkitchen_estate_credit_check` | `result` | B-tree | State filter |
| `thedevkitchen_estate_credit_check` | `(proposal_id) WHERE result='pending' AND active=true` | Partial UNIQUE | Invariant guard |

---

## Migration Notes

- No migration needed from spec 013 — the `credit_check_pending` state is additive.
- The partial unique index must be created in `_auto_init()` or via a `post_init_hook` in `__manifest__.py`, since Odoo's `_sql_constraints` does not support partial indexes.
- All existing proposals remain in their current states; the new state is only reachable via `action_initiate_credit_check()`.
