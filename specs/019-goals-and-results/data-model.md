# Data Model: Goals and Results (019)

**Module**: `thedevkitchen_estate_goals`  
**Status**: Phase 1 design  
**Date**: 2026-05-11

---

## Entity Overview

```
res.users ──────────────────────────────────────────────────────────┐
                                                                    │
res.company ─────────────────────────────────────────────────────── ├── thedevkitchen.estate.goal
                                                                    │
(referenced for achievement computation only — not FK on goal):     │
  real.estate.service        (agent_id → res.users direct)         │
  real.estate.property       (agent_id → real.estate.agent → user) │
  real.estate.proposal       (agent_id → real.estate.agent → user) │
  real.estate.agent          (user_id  → res.users)                │
```

---

## `thedevkitchen.estate.goal`

**DB table**: `thedevkitchen_estate_goal`  
**File**: `18.0/extra-addons/thedevkitchen_estate_goals/models/estate_goal.py`  
**Mixins**: none (no `mail.thread` — goals do not need chatter)

### Field Definitions

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | Integer (auto) | — | — | PK |
| `active` | Boolean | — | `True` | Soft delete (ADR-015) |
| `company_id` | Many2one(`res.company`) | ✅ | `env.company` | Multitenancy anchor |
| `user_id` | Many2one(`res.users`) | ✅ | — | The agent whose goal this is |
| `year` | Integer | ✅ | — | e.g. `2025`; validated ≥ 2020 |
| `month` | Integer | ✅ | — | 1-12 |
| `metric_type` | Selection | ✅ | — | `captacao`, `novos_clientes`, `visitas`, `propostas`, `fechamento` |
| `operation_type` | Selection | ✅ | — | `all`, `sale`, `rent` |
| `target` | Float | ✅ | — | Goal value; must be > 0 |
| `target_vgv` | Monetary | — | `None` | Optional VGV target (for captacao, propostas, fechamento) |
| `currency_id` | Many2one(`res.currency`) | — | `env.company.currency_id` | Linked to `target_vgv` |
| `notes` | Text | — | — | Free-text annotations |
| `create_date` | Datetime (auto) | — | — | Standard Odoo field |
| `write_date` | Datetime (auto) | — | — | Standard Odoo field |
| `create_uid` | Many2one (auto) | — | — | Standard Odoo field |

### Selection Field Values

**`metric_type`**:
```python
[
    ('captacao',      'Captação'),
    ('novos_clientes','Novos Clientes'),
    ('visitas',       'Visitas'),
    ('propostas',     'Propostas'),
    ('fechamento',    'Fechamento'),
]
```

**`operation_type`**:
```python
[
    ('all',  'Todos'),
    ('sale', 'Venda'),
    ('rent', 'Locação'),
]
```

### Constraints

**Unique constraint** (composite):
```python
_sql_constraints = [
    (
        'unique_user_company_period_metric_optype',
        'UNIQUE (user_id, company_id, year, month, metric_type, operation_type)',
        'A goal for this user/company/period/metric/operation already exists.',
    ),
]
```

**Python validation**:
```python
@api.constrains('year', 'month', 'target')
def _check_values(self):
    for rec in self:
        if rec.year < 2020:
            raise ValidationError('Year must be >= 2020.')
        if not (1 <= rec.month <= 12):
            raise ValidationError('Month must be between 1 and 12.')
        if rec.target <= 0:
            raise ValidationError('Target must be greater than zero.')
        if rec.target_vgv is not None and rec.target_vgv < 0:
            raise ValidationError('Target VGV cannot be negative.')
```

**VGV applicability check** (soft warning in UI; hard error in API):
```python
VGV_METRICS = {'captacao', 'propostas', 'fechamento'}
if rec.target_vgv and rec.metric_type not in VGV_METRICS:
    raise ValidationError('target_vgv only applies to captacao, propostas, fechamento.')
```

### Database Indexes

```sql
-- Unique constraint (auto-creates index)
UNIQUE (user_id, company_id, year, month, metric_type, operation_type)

-- Composite lookup index for report queries
CREATE INDEX idx_estate_goal_report
  ON thedevkitchen_estate_goal (company_id, year, month, operation_type)
  WHERE active = true;

-- User-scoped lookup
CREATE INDEX idx_estate_goal_user
  ON thedevkitchen_estate_goal (user_id, company_id)
  WHERE active = true;
```

### Record Rules (Multitenancy)

```xml
<!-- security/record_rules.xml -->
<record id="rule_estate_goal_company" model="ir.rule">
  <field name="name">Estate Goal: Company isolation</field>
  <field name="model_id" ref="model_thedevkitchen_estate_goal"/>
  <field name="domain_force">[('company_id', '=', user.company_id.id)]</field>
  <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

### Access Control (ACL)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_estate_goal_user,Estate Goal User,model_thedevkitchen_estate_goal,base.group_user,1,0,0,0
access_estate_goal_manager,Estate Goal Manager,model_thedevkitchen_estate_goal,base.group_system,1,1,1,1
```

---

## Achievement Computation (No Stored Fields)

Achievement values are **not stored** in `thedevkitchen.estate.goal`. They are computed at query time in `goals_report_service.py` using raw SQL. This table documents the computation logic per metric.

### Metric → Source Mapping

| Metric | Source model | Attribution field | Date anchor | VGV field |
|--------|-------------|------------------|------------|-----------|
| `captacao` | `real.estate.property` | `agent_id.user_id` (two-hop) | `create_date` | `price` (sale) / `rent_price` (rent) |
| `novos_clientes` | `real.estate.service` | `agent_id` (direct) | `create_date` | — |
| `visitas` | `real.estate.service` via `mail.tracking.value` | `agent_id` (direct) | `mtv.create_date` (stage→`visit`) | — |
| `propostas` | `real.estate.proposal` | `agent_id.user_id` (two-hop) | `create_date` | `proposal_value` |
| `fechamento` | `real.estate.service` via `mail.tracking.value` | `agent_id` (direct) | `mtv.create_date` (stage→`won`) | `proposal.proposal_value` (state=accepted) |

### `operation_type` Filtering per Source

| Goal `operation_type` | `real.estate.service` filter | `real.estate.property` filter | `real.estate.proposal` filter |
|----------------------|-----------------------------|-----------------------------|------------------------------|
| `sale` | `operation_type = 'sale'` | `for_sale = true` | `proposal_type = 'sale'` |
| `rent` | `operation_type = 'rent'` | `for_rent = true` | `proposal_type = 'lease'` |
| `all` | No filter (all) | `for_sale OR for_rent` | No filter (all) |

---

## Report Output Shape

The report endpoint returns aggregated per-user data. No new model is needed — computed in memory.

```json
{
  "users": [
    {
      "user_id": 5,
      "user_name": "Ana Costa",
      "goal_status": "complete",
      "metrics": {
        "captacao":       { "target": 10, "achievement": 12, "target_vgv": 500000, "achievement_vgv": 620000, "completion_pct": 120.0 },
        "novos_clientes": { "target": 15, "achievement": 15, "completion_pct": 100.0 },
        "visitas":        { "target": 8,  "achievement": 7,  "completion_pct": 87.5 },
        "propostas":      { "target": 5,  "achievement": 6,  "target_vgv": 200000, "achievement_vgv": 250000, "completion_pct": 120.0 },
        "fechamento":     { "target": 3,  "achievement": 2,  "target_vgv": 150000, "achievement_vgv": 100000, "completion_pct": 66.7 }
      }
    }
  ],
  "totals": {
    "users_with_goals": 8,
    "users_complete": 2,
    "users_in_progress": 5,
    "users_no_goals": 1,
    "team_completion_pct": 25.0
  },
  "period": {
    "year": 2025,
    "month": 3,
    "date_from": "2025-03-01",
    "date_to": "2025-03-31"
  }
}
```

### `goal_status` Enum

| Value | Condition |
|-------|-----------|
| `complete` | Has ≥1 goal set AND all set goals have `achievement >= target` |
| `in_progress` | Has ≥1 goal set AND at least one set goal has `achievement < target` |
| `no_goals` | Has zero active goals for the queried period/operation_type |
