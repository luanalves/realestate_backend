# Phase 0 Research: Goals and Results (019)

**Status**: Complete  
**Source**: Codebase exploration of `18.0/extra-addons/quicksol_estate/models/`  
**Files examined**: `service.py`, `property.py`, `proposal.py`, `agent.py`  
**Date**: 2026-05-11

---

## D001 — Agent Attribution per Entity (CORRECTS Q1)

**Decision**: Attribution to `res.users` follows two different join patterns depending on the entity.

| Entity | `agent_id` field type | Path to `res.users.id` |
|--------|----------------------|----------------------|
| `real.estate.service` | `Many2one(res.users)` | **Direct** — `service.agent_id` |
| `real.estate.property` | `Many2one(real.estate.agent)` | Two-hop — `property.agent_id.user_id` |
| `real.estate.proposal` | `Many2one(real.estate.agent)` | Two-hop — `proposal.agent_id.user_id` |

**⚠️ Spec Correction**: Clarification Q1 accepted the assumption that `real.estate.service.agent_id` was `Many2one(real.estate.agent)` (two-hop). The actual field definition in `service.py` is `Many2one(res.users)` — direct FK. `spec.md` has been updated to reflect this.

**Rationale**: Service model was designed with direct user FK (simpler); property/proposal were designed with an agent profile intermediary (needed for CRECI, CPF registration).

**SQL implications**:
- Service metrics (novos_clientes, visitas, fechamento): filter `real_estate_service.agent_id = target_user_id`
- Captação (property): `JOIN real_estate_agent ON real_estate_agent.id = real_estate_property.agent_id WHERE real_estate_agent.user_id = target_user_id`
- Propostas (proposal): `JOIN real_estate_agent ON real_estate_agent.id = real_estate_proposal.agent_id WHERE real_estate_agent.user_id = target_user_id`

---

## D002 — `mail.tracking.value` Query Pattern for Stage Transitions

**Decision**: Use raw SQL (`env.cr.execute`) to efficiently count services that transitioned to a specific stage within a date range.

**Schema relationships**:
```
mail_tracking_value
  ├── id
  ├── mail_message_id  → mail_message.id
  ├── field_id         → ir_model_fields.id (WHERE name = 'stage')
  ├── new_value_char   (the new selection value, e.g. 'visit', 'won')
  └── create_date      (timestamp of the change — use for date range filtering)

mail_message
  ├── id
  ├── model            (= 'real.estate.service')
  ├── res_id           (= service record ID)
  └── date             (message date — NOT used; use mtv.create_date instead)
```

**Verified**: `real.estate.service` inherits `mail.thread` with `tracking=True` on `stage` field — every stage change creates a `mail.tracking.value` record.

**Reference SQL pattern** (visitas per user, single month):
```sql
SELECT rs.agent_id AS user_id, COUNT(DISTINCT rs.id) AS count
FROM real_estate_service rs
JOIN mail_message mm
  ON mm.res_id = rs.id
 AND mm.model = 'real.estate.service'
JOIN mail_tracking_value mtv
  ON mtv.mail_message_id = mm.id
JOIN ir_model_fields imf
  ON imf.id = mtv.field_id
 AND imf.name = 'stage'
WHERE mtv.new_value_char = 'visit'
  AND mtv.create_date >= %(date_from)s
  AND mtv.create_date <  %(date_to)s
  AND rs.company_id = %(company_id)s
  AND rs.agent_id IN %(user_ids)s
GROUP BY rs.agent_id
```

**Key detail**: A single service can transition to `visit` multiple times (e.g., reschedule). `COUNT(DISTINCT rs.id)` counts unique services, not transitions. This matches the spec's intent ("número de serviços com visita realizada").

**Alternatives considered**:
- Odoo ORM domain search — rejected because of N+1 risk when `mail_message_id.res_id` cannot be indexed via ORM
- `mail.message.tracking_value_ids` computed field — rejected (not stored, slow for large volumes)

---

## D003 — Property Price Fields (Captação VGV)

**Decision**: Use `price` for sale captação VGV and `rent_price` for rent captação VGV.

| Property flag | Price field | Filter condition |
|---------------|------------|-----------------|
| `for_sale = True` | `price` (Monetary) | Goal `metric_type='captacao'`, `operation_type='sale'` |
| `for_rent = True` | `rent_price` (Monetary) | Goal `metric_type='captacao'`, `operation_type='rent'` |
| Both | Sum both | Goal `metric_type='captacao'`, `operation_type='all'` |

**Important**: Property does NOT have an `operation_type` field. The sale/rent split is via boolean flags `for_sale` and `for_rent`. A single property can be both `for_sale=True` AND `for_rent=True`.

**SQL pattern** (captação count, sale only):
```sql
SELECT rea.user_id, COUNT(rp.id) AS count, SUM(rp.price) AS vgv
FROM real_estate_property rp
JOIN real_estate_agent rea ON rea.id = rp.agent_id
WHERE rp.for_sale = true
  AND rp.create_date >= %(date_from)s
  AND rp.create_date <  %(date_to)s
  AND rp.company_id = %(company_id)s
  AND rea.user_id IN %(user_ids)s
GROUP BY rea.user_id
```

---

## D004 — Proposal Fields (Propostas Count + VGV, Fechamento VGV)

**Decision**: Use `proposal_value` (Monetary) for VGV; `proposal_type` for sale/rent filter; `state='accepted'` for fechamento VGV.

| Field | Value | Use |
|-------|-------|-----|
| `proposal_type` | `'sale'` or `'lease'` | Filter for sale vs rent (note: `'lease'` not `'rent'`) |
| `proposal_value` | Monetary | VGV accumulation |
| `state` | `'accepted'` | Fechamento VGV: only accepted proposals count |
| `service_id` | FK to `real.estate.service` (nullable) | Link to winning service for fechamento |
| `agent_id` | FK to `real.estate.agent` | Two-hop attribution via `.user_id` |

**⚠️ Mapping note**: Goal `operation_type='rent'` maps to `proposal_type='lease'` (not `'rent'`). This translation must be handled in the service layer:
```python
OP_TYPE_TO_PROPOSAL_TYPE = {'sale': 'sale', 'rent': 'lease', 'all': None}
```

**Propostas SQL pattern** (count + VGV per user):
```sql
SELECT rea.user_id, COUNT(rpr.id) AS count, SUM(rpr.proposal_value) AS vgv
FROM real_estate_proposal rpr
JOIN real_estate_agent rea ON rea.id = rpr.agent_id
WHERE rpr.proposal_type = %(proposal_type)s   -- 'sale' or 'lease'
  AND rpr.create_date >= %(date_from)s
  AND rpr.create_date <  %(date_to)s
  AND rpr.company_id = %(company_id)s
  AND rea.user_id IN %(user_ids)s
GROUP BY rea.user_id
```

**Fechamento VGV** links service won-transition to accepted proposal:
```sql
SELECT rs.agent_id AS user_id,
       COUNT(DISTINCT rs.id) AS count,
       SUM(rpr.proposal_value) AS vgv
FROM real_estate_service rs
JOIN mail_message mm ON mm.res_id = rs.id AND mm.model = 'real.estate.service'
JOIN mail_tracking_value mtv ON mtv.mail_message_id = mm.id
JOIN ir_model_fields imf ON imf.id = mtv.field_id AND imf.name = 'stage'
LEFT JOIN real_estate_proposal rpr
       ON rpr.service_id = rs.id AND rpr.state = 'accepted'
WHERE mtv.new_value_char = 'won'
  AND mtv.create_date >= %(date_from)s
  AND mtv.create_date <  %(date_to)s
  AND rs.company_id = %(company_id)s
  AND rs.agent_id IN %(user_ids)s
GROUP BY rs.agent_id
```

---

## D005 — Service Fields (Novos Clientes, Visitas, Fechamento)

**Decision**: `operation_type` field on `real.estate.service` uses values `['sale', 'rent']`; `stage` field has `tracking=True` with values including `'visit'` and `'won'`.

| Metric | Source field | Filter | Date anchor |
|--------|-------------|--------|-------------|
| Novos Clientes | `real_estate_service` | `operation_type` | `create_date` |
| Visitas | `mail_tracking_value` | `new_value_char = 'visit'` | `mtv.create_date` |
| Fechamento | `mail_tracking_value` | `new_value_char = 'won'` | `mtv.create_date` |

**Novos Clientes SQL** (count per user):
```sql
SELECT rs.agent_id AS user_id, COUNT(rs.id) AS count
FROM real_estate_service rs
WHERE rs.operation_type = %(operation_type)s  -- 'sale' or 'rent'
  AND rs.create_date >= %(date_from)s
  AND rs.create_date <  %(date_to)s
  AND rs.company_id = %(company_id)s
  AND rs.agent_id IN %(user_ids)s
GROUP BY rs.agent_id
```

---

## D006 — User Cap Implementation (200-user hard limit)

**Decision**: Count users matching the report query before executing metric aggregations. Return HTTP 422 with descriptive error if count exceeds 200.

```python
# In service layer, before running report queries:
user_count = len(user_ids)
if user_count > 200:
    raise ValidationError(
        f"Report exceeds maximum of 200 users. "
        f"Found {user_count} users. Apply stricter filters."
    )
```

**Alternatives considered**:
- Pagination — rejected for v1 (spec decision; real teams ≤ 50 users)
- Silent truncation — rejected (produces misleading reports)
- `totals` aggregation across pages — rejected (non-trivial, deferred to v2)

---

## D007 — `operation_type=all` Goals in Filtered Reports

**Decision**: Goals with `operation_type='all'` are **excluded** from `sale`-only or `rent`-only filtered reports. They appear only in unfiltered (all-operation) reports.

**Rationale** (from Clarification Q4): Including `all`-goals against filtered achievement data (e.g., sale-only visitas) would produce misleading `completion_pct`. A `captacao/all` target=10 compared against only sale captações is meaningless without recalculating the denominator.

**Implementation**: In the service layer, when `operation_type` param is `'sale'` or `'rent'`, add `goal.operation_type = param` to the goal lookup query (excludes `all`-goals).

---

## D008 — Date Range Anchor for `year`/`month` vs `date_from`/`date_to`

**Decision** (from Clarification Q3):
- Single-month mode: `year` required + `month` (1-12) required → `date_from = first day of month`, `date_to = first day of next month`
- Accumulated mode: `date_from` + `date_to` provided → `year` param ignored
- `date_from` and `date_to` are ISO 8601 date strings; converted to `datetime` with UTC midnight in service layer

**Note**: `year` is only validated/required when `date_from`/`date_to` are absent.

---

## D009 — `goal_status` Computation Rules

**Decision** (from Clarification Q2):
- `complete` = all metrics that have a goal set (target > 0) meet or exceed their achievement value
- Metrics with `target = null` (no goal set) are **neutral** — ignored in completeness evaluation
- A user with **zero goals set** is **NOT complete** (no goals = not evaluable)
- `in_progress` = has at least one goal set but some are not yet met
- `no_goals` = user exists in report scope (in company, with requested `operation_type`) but has zero active goals for the period

---

## Summary of Technical Decisions

| ID | Decision | Confidence |
|----|----------|------------|
| D001 | Service uses direct FK; property/proposal use two-hop via `real.estate.agent` | HIGH — verified in source |
| D002 | Raw SQL via `env.cr.execute` for `mail.tracking.value` stage queries | HIGH — ORM risk of N+1 |
| D003 | `for_sale`/`for_rent` booleans on property; `price`/`rent_price` for VGV | HIGH — verified in source |
| D004 | `proposal_value`; `proposal_type='lease'` maps from `operation_type='rent'` | HIGH — verified in source |
| D005 | `operation_type` on service; `stage` tracking values `'visit'`, `'won'` | HIGH — verified in source |
| D006 | 200-user cap: count before query, 422 if exceeded | HIGH — spec confirmed |
| D007 | `all`-goals excluded from filtered reports | HIGH — spec Q4 confirmed |
| D008 | `year`/`month` single-month; `date_from`/`date_to` accumulated | HIGH — spec Q3 confirmed |
| D009 | `complete` = all set goals met; zero goals → `no_goals` status | HIGH — spec Q2 confirmed |
