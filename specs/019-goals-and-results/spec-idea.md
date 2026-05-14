# Feature Specification: Goals and Results (Metas e Resultados)

**Feature Branch**: `019-goals-and-results`
**Created**: 2026-05-11
**Status**: Draft
**ADR References**: ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-011, ADR-015, ADR-016, ADR-018, ADR-019, ADR-022

---

## Executive Summary

### Problema de Negócio

Imobiliárias que trabalham com equipes comerciais sofrem com a falta de visibilidade em tempo real sobre o desempenho individual dos corretores e gestores. Sem um sistema de metas estruturado, o acompanhamento é feito manualmente (planilhas, reuniões) e chega sempre tarde — quando o mês já acabou e não há mais como agir. Gestores não sabem quais corretores estão no ritmo certo para bater os resultados esperados, e os próprios corretores não têm clareza sobre onde estão em relação às suas metas.

### Solução Implementada

O módulo **Metas e Resultados** permite que Proprietários, Diretores e Gestores definam metas mensais individuais para cada membro da equipe em 5 métricas-chave do funil imobiliário:

| Métrica | O que mede |
|---------|------------|
| **Captações** | Imóveis captados (novos para a carteira), com VGV |
| **Novos Clientes** | Atendimentos abertos no período |
| **Visitas** | Atendimentos que evoluíram para visita |
| **Propostas** | Propostas geradas, com VGV |
| **Fechamento** | Negócios fechados (won), com VGV |

As conquistas (realizações) são calculadas automaticamente cruzando os dados já existentes no sistema — `real.estate.property`, `real.estate.service` e `real.estate.proposal` — sem entrada manual de resultados.

### Valor Entregue

- **Gestor**: acessa um painel comparativo (meta vs. conquista) de toda a equipe, filtrado por mês, período acumulado, perfil, tipo de operação (Venda/Locação) e status de atingimento. Pode agir preventivamente durante o mês.
- **Corretor**: visualiza seus próprios resultados em tempo real no app, sem depender de relatórios do gestor.
- **Admin Odoo**: gerencia as metas diretamente na interface administrativa, sem precisar de acesso ao frontend headless.
- **Consequência direta**: reuniões de resultado têm base de dados confiável, decisões de redistribuição de carteira ou leads têm fundamento quantitativo.

---

## User Scenarios & Testing

### User Story 1: Manager Sets Monthly Goal

**As a** Manager (or Owner/Director)
**I want to** define a monthly sales goal for a team member per metric and operation type
**So that** I can track performance against targets

**Acceptance Criteria**:
- [ ] Given a Manager with valid JWT, when `POST /api/v1/goals`, then goal is created (201) with HATEOAS links
- [ ] Given a duplicate goal (same user/year/month/metric/operation), when creating again, then 409 Conflict
- [ ] Given an Agent, when `POST /api/v1/goals`, then 403 Forbidden
- [ ] Given invalid month (0 or 13), when `POST`, then 400 validation error (ADR-018)
- [ ] Given `metric_type=visitas` with `target_vgv`, when `POST`, then 400 (VGV invalid for visits)
- [ ] Given goals for company A, when company B manager queries, then company B isolation enforced (ADR-008)

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_goal_unique_constraint()` | unique(user,year,month,metric,operation) | ⚠️ Required |
| Unit | `test_goal_target_count_non_negative()` | target_count >= 0 | ⚠️ Required |
| Unit | `test_goal_month_range_valid()` | month 1-12 only | ⚠️ Required |
| Unit | `test_goal_year_min_2000()` | year >= 2000 | ⚠️ Required |
| Unit | `test_vgv_forbidden_for_visitas_novos_clientes()` | VGV only for captacao/propostas/fechamento | ⚠️ Required |
| E2E (API) | `test_manager_creates_goal()` | Full creation flow with JWT auth | ⚠️ Required |
| E2E (API) | `test_agent_cannot_create_goal()` | RBAC enforcement (403) | ⚠️ Required |
| E2E (API) | `test_duplicate_goal_returns_409()` | Conflict detection | ⚠️ Required |
| E2E (API) | `test_multitenancy_goal_isolation()` | Company data isolation | ⚠️ Required |
| E2E (UI) | `cypress: test_goals_menu_loads_without_errors()` | Admin UI loads without "Oops!" | ⚠️ Required |

---

### User Story 2: Agent Views Own Results Report

**As an** Agent (Corretor)
**I want to** view my goals vs actual results for a given month
**So that** I can monitor my own performance

**Acceptance Criteria**:
- [ ] Given an Agent, when `GET /api/v1/goals/report?user_id={self.id}&year=2026&month=5`, then returns own metrics only
- [ ] Given an Agent, when `user_id` refers to another user, then 403 Forbidden
- [ ] Given no goals set for the period, when `GET report`, then returns conquistas with `meta_count=null`
- [ ] Given accumulated period (e.g. Jan–May), when `GET` with `date_from=2026-01&date_to=2026-05`, then sums conquistas vs sum of monthly goals

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_agent_views_own_report()` | Agent can see own metrics | ⚠️ Required |
| E2E (API) | `test_agent_cannot_view_others_report()` | 403 when filtering another user | ⚠️ Required |
| E2E (API) | `test_accumulated_period_report()` | Jan–May accumulation correct | ⚠️ Required |
| E2E (API) | `test_no_goals_returns_null_meta()` | conquista present, meta=null when not set | ⚠️ Required |

---

### User Story 3: Manager Views Team Report

**As a** Manager (or Owner/Director)
**I want to** view goals and results for my entire team with filters
**So that** I can identify top performers and take corrective action

**Acceptance Criteria**:
- [ ] Given a Manager, when `GET /api/v1/goals/report?year=2026&month=5`, returns all users of company
- [ ] Can filter by: `user_id`, `profile`, `operation_type`, `goal_status`
- [ ] Response includes a `totals` object aggregating all returned users
- [ ] `goal_status=complete` returns only users where conquista >= meta on ALL metrics
- [ ] Filter `operation_type=sale` returns results separated for Venda only

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_manager_views_full_team_report()` | All users appear in response | ⚠️ Required |
| E2E (API) | `test_filter_by_profile()` | Filter by RBAC group | ⚠️ Required |
| E2E (API) | `test_filter_by_operation_type()` | Venda vs Locação separation | ⚠️ Required |
| E2E (API) | `test_totals_row_aggregation()` | totals math correct | ⚠️ Required |
| E2E (API) | `test_filter_goal_status_complete()` | Only complete goals returned | ⚠️ Required |

---

### User Story 4: Admin Manages Goals in Odoo UI

**As an** Odoo Admin
**I want to** manage team goals from the Odoo back-office
**So that** I have full operational control without needing the headless frontend

**Acceptance Criteria**:
- [ ] Menu "Imobiliária > Metas" loads without JavaScript errors
- [ ] List view shows goal records (user, period, metric, operation, target)
- [ ] Form view allows create/edit/archive goals
- [ ] Browser DevTools console shows zero JS errors
- [ ] No `groups` attribute on `<menuitem>` (admin-only menus)

**Frontend Acceptance Criteria**:
- [ ] Views use `<list>` (not `<tree>`)
- [ ] No `attrs` attribute used
- [ ] `optional="show"` for list column visibility
- [ ] Cypress E2E tests pass

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (UI) | `cypress: test_goals_list_view_loads()` | List renders without errors | ⚠️ Required |
| E2E (UI) | `cypress: test_goals_form_view_loads()` | Form renders without errors | ⚠️ Required |
| E2E (UI) | `cypress: test_goals_form_create()` | Create goal from admin UI | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Goal Management**
- FR1.1: Owner, Director, Manager can create/update/delete goals for any user in their company
- FR1.2: Each goal is identified by the tuple `(user_id, company_id, year, month, metric_type, operation_type)`
- FR1.3: Fields: `target_count` (integer ≥ 0) and `target_vgv` (monetary, optional)
- FR1.4: `target_vgv` is valid only for metrics: `captacao`, `propostas`, `fechamento`
- FR1.5: Soft-delete via `active=False` (ADR-015); goals remain in DB for historical audit
- FR1.6: `target_count=0` is valid and means "goal not yet quantified"

**FR2: Achievement Computation (Conquistas)**

| Metric | Source Entity | Attribution Field | Period Field | Filter |
|--------|--------------|-------------------|--------------|--------|
| Captações | `real.estate.property` | `agent_id.user_id` | `create_date` | `for_sale`/`for_rent` per operation_type |
| Captações VGV | same | same | same | sum `price` (sale) / `rent_price` (rent) |
| Novos Clientes | `real.estate.service` | `agent_id` (res.users) | `create_date` | `operation_type` |
| Visitas | `real.estate.service` | `agent_id` | stage→`visit` via `mail.tracking.value` | `operation_type` |
| Propostas | `real.estate.proposal` | `agent_id` | `create_date` | `proposal_type` (sale/lease) |
| Propostas VGV | same | same | same | sum `proposal_value` |
| Fechamento | `real.estate.service` | `agent_id` | stage→`won` via `mail.tracking.value` | `operation_type` |
| Fechamento VGV | `real.estate.proposal` (state=accepted, linked service=won) | via service | same period | sum `proposal_value` |

- FR2.1: Period filter — single month (`year`+`month`) or accumulated (`date_from` to `date_to` in YYYY-MM format)
- FR2.2: Stage tracking uses `mail.tracking.value` records where `field_id.name='stage'` and `new_value_char` = target stage within the date range
- FR2.3: When `operation_type=all`, conquistas combine both sale and rent
- FR2.4: `proposal_type: lease` aligns with `operation_type: rent`; `proposal_type: sale` aligns with `operation_type: sale`

**FR3: Report**
- FR3.1: Report endpoint returns per-user rows with all 5 metrics (conquista vs meta)
- FR3.2: A `totals` object at root aggregates all returned users
- FR3.3: `completion_pct` = `(conquista / meta) * 100`; null when `meta_count=null` or `meta_count=0`
- FR3.4: `goal_status=complete` = all metrics have `conquista >= meta` (excluding null metas)
- FR3.5: Report is computed in real-time (v1); Redis cache TTL 60s is a future enhancement

---

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

**Module**: `thedevkitchen_estate_goals`

**Entity: Goal**
- **Model Name**: `thedevkitchen.estate.goal`
- **Table Name**: `thedevkitchen_estate_goal` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `user_id` | Many2one(res.users) | required, ondelete=cascade | Target user |
| `company_id` | Many2one(res.company) | required | Multi-tenancy (ADR-008) |
| `year` | Integer | required, CHECK >= 2000 | Goal year |
| `month` | Integer | required, CHECK 1–12 | Goal month |
| `metric_type` | Selection | required | `captacao`, `novos_clientes`, `visitas`, `propostas`, `fechamento` |
| `operation_type` | Selection | required, default=`all` | `all`, `sale`, `rent` |
| `target_count` | Integer | required, default=0, CHECK >= 0 | Goal quantity |
| `target_vgv` | Monetary | optional, CHECK >= 0 | Goal VGV (captacao/propostas/fechamento only) |
| `currency_id` | Many2one(res.currency) | related=company_id.currency_id | Display currency |
| `active` | Boolean | default=True | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | Audit |
| `write_date` | Datetime | auto | Audit |

**SQL Constraints**:
```python
_sql_constraints = [
    (
        'user_period_metric_op_uniq',
        'unique(user_id, company_id, year, month, metric_type, operation_type)',
        'Goal must be unique per user/company/year/month/metric/operation_type.',
    ),
    ('target_count_non_negative', 'CHECK(target_count >= 0)', 'Target count must be >= 0.'),
    ('target_vgv_non_negative', 'CHECK(target_vgv IS NULL OR target_vgv >= 0)', 'Target VGV must be >= 0.'),
    ('year_valid', 'CHECK(year >= 2000)', 'Year must be >= 2000.'),
    ('month_valid', 'CHECK(month >= 1 AND month <= 12)', 'Month must be between 1 and 12.'),
]
```

**Python Constraints**:
```python
@api.constrains('metric_type', 'target_vgv')
def _check_vgv_only_for_vgv_metrics(self):
    vgv_metrics = {'captacao', 'propostas', 'fechamento'}
    for rec in self:
        if rec.target_vgv and rec.metric_type not in vgv_metrics:
            raise ValidationError(
                "VGV target is only applicable to captacao, propostas, and fechamento metrics."
            )
```

**Database Indexes**:
```python
# Covered by unique constraint (implicit index)
# Additional composite index for report queries:
_indexes = [
    ('company_id', 'year', 'month'),
    ('user_id', 'company_id', 'year', 'month'),
]
```

**Record Rules** (per ADR-019):
```xml
<!-- All users: company isolation -->
<record id="rule_goal_company_isolation" model="ir.rule">
    <field name="name">Goal: company isolation</field>
    <field name="model_id" ref="model_thedevkitchen_estate_goal"/>
    <field name="domain_force">[('company_id', '=', company_id)]</field>
</record>

<!-- Agents: can only see their own goals -->
<record id="rule_goal_agent_own_only" model="ir.rule">
    <field name="name">Goal: agent restricted to own</field>
    <field name="model_id" ref="model_thedevkitchen_estate_goal"/>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_real_estate_agent'))]"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
</record>
```

---

### API Endpoints (per ADR-007, ADR-009, ADR-011)

#### POST /api/v1/goals — Create Goal

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/goals` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner, Director, Manager |

**Request Body** (per ADR-018):
```json
{
  "user_id": 42,
  "year": 2026,
  "month": 5,
  "metric_type": "captacao",
  "operation_type": "sale",
  "target_count": 10,
  "target_vgv": 5000000.00
}
```

**Response 201** (HATEOAS per ADR-007):
```json
{
  "id": 1,
  "user_id": 42,
  "user_name": "João Silva",
  "company_id": 1,
  "year": 2026,
  "month": 5,
  "metric_type": "captacao",
  "operation_type": "sale",
  "target_count": 10,
  "target_vgv": 5000000.00,
  "currency": "BRL",
  "active": true,
  "created_at": "2026-05-11T18:00:00Z",
  "links": [
    {"href": "/api/v1/goals/1", "rel": "self", "type": "GET"},
    {"href": "/api/v1/goals/1", "rel": "update", "type": "PUT"},
    {"href": "/api/v1/goals/1", "rel": "delete", "type": "DELETE"},
    {"href": "/api/v1/goals", "rel": "collection", "type": "GET"}
  ]
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation error | `{"error": "validation_error", "detail": "..."}` |
| 401 | Invalid/missing JWT | `{"error": "unauthorized"}` |
| 403 | Role not authorized (Agent/Receptionist/Prospector) | `{"error": "forbidden"}` |
| 409 | Duplicate | `{"error": "conflict", "detail": "Goal already exists for this user/period/metric/operation"}` |

---

#### PUT /api/v1/goals/{id} — Update Goal

| Attribute | Value |
|-----------|-------|
| **Method** | PUT |
| **Path** | `/api/v1/goals/{id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner, Director, Manager |

Allows partial update of `target_count` and/or `target_vgv`. Returns 200 with updated record + HATEOAS links.

**Error Responses**:
| Code | Condition |
|------|-----------|
| 400 | Validation error |
| 403 | Role not authorized |
| 404 | Goal not found |

---

#### DELETE /api/v1/goals/{id} — Soft Delete Goal

| Attribute | Value |
|-----------|-------|
| **Method** | DELETE |
| **Path** | `/api/v1/goals/{id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner, Director, Manager |

Sets `active=False` (ADR-015). Never hard-deletes.

**Response 200**:
```json
{
  "success": true,
  "message": "Goal archived successfully",
  "links": [{"href": "/api/v1/goals", "rel": "collection", "type": "GET"}]
}
```

---

#### GET /api/v1/goals — List Goals

| Attribute | Value |
|-----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/goals` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner/Director/Manager (all in company); Agent (own only, record rule enforced) |

**Query Parameters**: `user_id`, `year`, `month`, `metric_type`, `operation_type`

**Response 200**:
```json
{
  "count": 6,
  "results": [
    {
      "id": 1,
      "user_id": 42,
      "user_name": "João Silva",
      "year": 2026,
      "month": 5,
      "metric_type": "captacao",
      "operation_type": "sale",
      "target_count": 10,
      "target_vgv": 5000000.00,
      "currency": "BRL",
      "active": true,
      "links": [
        {"href": "/api/v1/goals/1", "rel": "self", "type": "GET"}
      ]
    }
  ],
  "links": [
    {"href": "/api/v1/goals", "rel": "self", "type": "GET"},
    {"href": "/api/v1/goals/report", "rel": "report", "type": "GET"}
  ]
}
```

---

#### GET /api/v1/goals/report — Goals vs Results Report

| Attribute | Value |
|-----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/goals/report` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner/Director/Manager (all users in company); Agent (own only) |

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `year` | integer | yes | Report year |
| `month` | integer | no | Single month (1–12); mutually exclusive with `date_from`/`date_to` |
| `date_from` | YYYY-MM | no | Accumulated period start |
| `date_to` | YYYY-MM | no | Accumulated period end (defaults to current month) |
| `user_id` | integer | no | Filter by user (agents: forced to own user_id) |
| `profile` | string | no | Filter by group XML ID (e.g. `group_real_estate_agent`) |
| `operation_type` | all/sale/rent | no | Filter by operation type (default: all) |
| `goal_status` | complete/incomplete | no | Filter by completion status |

**Response 200**:
```json
{
  "period": {
    "date_from": "2026-01-01",
    "date_to": "2026-05-31",
    "label": "Janeiro até Maio 2026"
  },
  "filters": {
    "operation_type": "all",
    "profile": null,
    "goal_status": null,
    "user_id": null
  },
  "users": [
    {
      "user_id": 42,
      "user_name": "Bárbara",
      "profile": "Director",
      "team": null,
      "metrics": {
        "captacoes": {
          "conquista": 1,
          "meta_count": 0,
          "conquista_vgv": 3500000.00,
          "meta_vgv": 0.00,
          "completion_pct": null
        },
        "novos_clientes": {
          "conquista": 0,
          "meta_count": 0,
          "completion_pct": null
        },
        "visitas": {
          "conquista": 0,
          "meta_count": 0,
          "completion_pct": null
        },
        "propostas": {
          "conquista": 0,
          "meta_count": 0,
          "conquista_vgv": 0.00,
          "meta_vgv": 0.00,
          "completion_pct": null
        },
        "fechamento": {
          "conquista": 0,
          "meta_count": 0,
          "conquista_vgv": 0.00,
          "meta_vgv": 0.00,
          "completion_pct": null
        }
      }
    }
  ],
  "totals": {
    "captacoes":      {"conquista": 3, "meta_count": 0, "conquista_vgv": 4958000.00, "meta_vgv": 0.00},
    "novos_clientes": {"conquista": 1, "meta_count": 0},
    "visitas":        {"conquista": 0, "meta_count": 0},
    "propostas":      {"conquista": 0, "meta_count": 0, "conquista_vgv": 0.00, "meta_vgv": 0.00},
    "fechamento":     {"conquista": 0, "meta_count": 0, "conquista_vgv": 0.00, "meta_vgv": 0.00}
  },
  "links": [
    {"href": "/api/v1/goals/report", "rel": "self", "type": "GET"},
    {"href": "/api/v1/goals", "rel": "goals", "type": "GET"}
  ]
}
```

> **Note on `meta_count`**: `null` means no goal record exists for this user/period/metric; `0` means a goal was explicitly set with target=0. `completion_pct` is `null` when meta is null or 0.

**Error Responses**:
| Code | Condition |
|------|-----------|
| 400 | `month` and `date_from`/`date_to` both provided |
| 400 | `year` missing |
| 403 | Agent filtering another user's data |

---

### Seed Data (MANDATORY — all solution types)

```python
# ============================================================
# SEED: Feature 019 — Goals and Results
# All logins prefixed with 'seed_' to avoid production conflicts
# Idempotent: check-before-create pattern
# ============================================================

# Seed: 2 companies for multi-tenancy isolation tests
company_a = env['res.company'].create({'name': 'Imobiliária Seed A (019)'})
company_b = env['res.company'].create({'name': 'Imobiliária Seed B (019)'})

# Seed: Users per role (company A)
seed_users = {
    'owner_a':    {'login': 'seed_019_owner@seed-goals.com',    'group': 'group_real_estate_owner'},
    'director_a': {'login': 'seed_019_director@seed-goals.com', 'group': 'group_real_estate_director'},
    'manager_a':  {'login': 'seed_019_manager@seed-goals.com',  'group': 'group_real_estate_manager'},
    'agent_a':    {'login': 'seed_019_agent@seed-goals.com',    'group': 'group_real_estate_agent'},
    'owner_b':    {'login': 'seed_019_owner_b@seed-goals.com',  'group': 'group_real_estate_owner'},  # isolation
}

# Seed: Properties (for captações metric)
# - 2 for_sale properties attributed to agent_a (May 2026), price=R$1.5M each
# - 1 for_rent property attributed to agent_a (May 2026), rent_price=R$5000/mo

# Seed: Services (for novos_clientes, visitas, fechamento)
# - 3 services created by agent_a in May 2026 (operation_type=sale)
# - 1 service that reached 'visit' stage in May 2026 (mail.tracking.value record)
# - 1 service that reached 'won' stage in May 2026 (mail.tracking.value record)

# Seed: Proposals (for propostas, fechamento VGV)
# - 2 proposals by agent_a in May 2026 (proposal_type=sale, value=R$480,000 each)
# - 1 accepted proposal linked to the won service above

# Seed: Goals for agent_a (May 2026) — for report vs reality tests
seed_goals = [
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'captacao',       'operation_type': 'sale', 'target_count': 5,  'target_vgv': 2000000.00},
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'captacao',       'operation_type': 'rent', 'target_count': 2,  'target_vgv': 100000.00},
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'novos_clientes', 'operation_type': 'all',  'target_count': 10},
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'visitas',        'operation_type': 'all',  'target_count': 8},
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'propostas',      'operation_type': 'sale', 'target_count': 3,  'target_vgv': 1500000.00},
    {'user': 'agent_a', 'year': 2026, 'month': 5, 'metric_type': 'fechamento',     'operation_type': 'sale', 'target_count': 2,  'target_vgv': 900000.00},
]
```

> **Seed rules**:
> - All logins use `seed_019_` prefix to avoid conflicts
> - Idempotent: check-before-create using `search([('login', '=', ...)])`
> - Covers all 5 metrics, all 3 operation types, and both companies
> - For API tests: seeds provide the initial state before each test request
> - For Cypress tests: seed records visible in Odoo admin list/form views

---

### Non-Functional Requirements

**NFR1: Security** (ADR-008, ADR-011, ADR-017, ADR-019)
- Triple decorators on all 5 endpoints
- Agents restricted to own data at both record-rule and application layer
- Company isolation enforced at DB level via record rules

**NFR2: Performance**
- Single-month report (≤50 users): < 500ms
- Accumulated 12-month report (≤50 users): < 2s
- DB indexes on `(user_id, company_id, year, month, metric_type)` (from unique constraint)
- Additional composite index on `(company_id, year, month)` for team report queries
- `mail.tracking.value` queries scoped with date range filter

**NFR3: Quality** (ADR-022)
- Pylint ≥ 8.0/10; black, isort, flake8 passing
- 100% unit test coverage on all SQL + Python constraints

**NFR4: Data Integrity**
- `user_id` → `ondelete=cascade` (goals auto-removed when user deleted)
- Soft delete only (ADR-015); never hard-delete goals

**NFR5: Frontend Standards** (knowledge_base/10-frontend-views-odoo18.md, ADR-001)
- `<list>` instead of `<tree>`
- `optional="show"` for column visibility in list views
- No `attrs` attribute
- No `column_invisible` with Python expressions

---

## Technical Constraints

### Must Follow (from ADRs & Knowledge Base)

| Source | Requirement | Applied To |
|--------|-------------|------------|
| ADR-001 | Odoo 18.0 view standards (no `attrs`, use `<list>`) | All views |
| ADR-001 | **No `groups` attribute on any `<menuitem>`** | All menus |
| Arch | Only system `admin` user accesses Odoo UI | Views scoped to admin |
| ADR-003 | 100% test coverage on validations | All constraints |
| ADR-004 | `thedevkitchen_` prefix | Module: `thedevkitchen_estate_goals` |
| ADR-007 | HATEOAS links in all responses | All 5 endpoints |
| ADR-008 | Company isolation | Record rules |
| ADR-011 | Triple auth decorators | All controllers |
| ADR-015 | Soft delete via `active` | Goal CRUD |
| ADR-018 | Schema validation | Input validation |
| ADR-019 | RBAC enforcement | Authorization matrix |
| ADR-022 | Linting standards | All Python + XML |
| KB-10 | `optional` for column visibility | List views |

### Architecture Patterns

- **Achievement Computation**: Extract all computation to `goals_report_service.py` (for testability)
- **Stage Tracking**: Use `mail.tracking.value` to detect when `stage` field changed to `'visit'` or `'won'` within the period (`field_id.name='stage'`, `new_value_char='visit'/'won'`)
- **Controller Pattern**: Per `.github/instructions/controllers.instructions.md`
- **Testing Pattern**: Per `.github/instructions/test-strategy.instructions.md`

---

## Success Criteria

### Backend
- [ ] Goal CRUD (POST/PUT/DELETE/GET) implemented and tested
- [ ] Achievement computation correct for all 5 metrics and 3 operation types
- [ ] VGV computation correct for captacao/propostas/fechamento
- [ ] Report with all 5 filters working
- [ ] Totals row correct in report
- [ ] Accumulated period (date_from/date_to) report tested
- [ ] Multi-company isolation verified
- [ ] RBAC: agents see own only; managers/owners see full team
- [ ] Code quality: Pylint ≥ 8.0, all linters passing (ADR-022)

### Frontend (Odoo Admin UI)
- [ ] Views follow Odoo 18.0 standards (KB-10, ADR-001)
- [ ] No `groups` attribute on any `<menuitem>`
- [ ] Cypress E2E tests for list + form views
- [ ] Manual browser test: zero JS console errors
- [ ] `optional` attribute used for column visibility

### Seeds
- [ ] Seed data file created with `seed_019_` prefix on all logins
- [ ] Covers Owner, Director, Manager, Agent + isolation company B
- [ ] Covers all 5 metric types and all 3 operation types
- [ ] Seed is idempotent (safe to run multiple times)
- [ ] API tests use seed records as initial state

### Documentation (Post-Development)
- [ ] Swagger/OpenAPI generated via `thedevkitchen.swagger` (ADR-005)
- [ ] Postman collection generated via `thedevkitchen.postman` (ADR-016)
- [ ] Constitution updated with new Report Endpoint Pattern (v1.8.0)

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| Report/Analytics Endpoint | Computed report from multiple source entities; totals row; period filter (single-month + accumulated) | Architectural Patterns | High |
| Achievement via mail.tracking.value | Using Odoo's tracking history to compute when a stage change occurred in a date range | Development Patterns | High |
| Dual-Period Report | Same endpoint supports `month` (single) and `date_from/date_to` (accumulated) — mutually exclusive | API Patterns | Medium |
| Goal-as-Target Model | Explicit goal records decoupled from achievement data; achievements computed at query time | Domain Patterns | Medium |

### New Entities/Relationships

| Entity | Related To | Relationship Type | Notes |
|--------|-----------|-------------------|-------|
| `thedevkitchen.estate.goal` | `res.users`, `res.company` | N:1 each | One goal per user/company/period/metric/operation tuple |
| Goal Report (virtual) | `real.estate.property`, `real.estate.service`, `real.estate.proposal` | Computed at query time | Conquistas derived from existing entities |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: v1.8.0 (MINOR)
- **Sections to Update**:
  - [ ] Architectural Patterns — add Report Endpoint Pattern
  - [ ] Development Patterns — add Achievement via mail.tracking.value
  - [ ] Reference Implementations — add Feature 019

---

## Assumptions & Dependencies

**Assumptions**:
- `mail.tracking.value` records exist for stage changes on `real.estate.service` (confirmed: `_inherit = ['mail.thread']`)
- Properties use `agent_id → real.estate.agent → user_id` (two-hop join) for captações attribution
- No team/equipe model exists yet in v1; `team` field in report response returns `null`
- `proposal_type: lease` aligns with `operation_type: rent`; `proposal_type: sale` aligns with `operation_type: sale`
- VGV for fechamento is computed from `real.estate.proposal` (state=accepted) linked to a `won` service

**Dependencies**:
- `quicksol_estate` — provides `real.estate.property`, `real.estate.service`, `real.estate.proposal`, `real.estate.agent`
- `thedevkitchen_apigateway` — provides `@require_jwt`, `@require_session`, `@require_company`
- PostgreSQL 14+ — for efficient tracking value queries
- Odoo `mail.thread` mixin — must be present on `real.estate.service` (confirmed)

---

## Implementation Phases

### Phase 1: Foundation
- New module `thedevkitchen_estate_goals` with manifest and `__init__.py`
- `thedevkitchen.estate.goal` model with all fields, constraints, and record rules
- ACL security definitions
- Unit tests for all constraints (SQL + Python)

### Phase 2: Achievement Computation
- `goals_report_service.py` with query logic for all 5 metrics
- Period filter (monthly + accumulated)
- `mail.tracking.value` stage tracking for Visitas and Fechamento

### Phase 3: API Layer
- Goal CRUD controllers: POST, PUT, DELETE, GET list (with triple auth)
- Report controller with all 5 filters
- Error envelope per FR6.9 pattern (`{"error": "...", "detail": "..."}`)

### Phase 4: Odoo Admin UI
- Goals list view (`<list>`, `optional` columns)
- Goal form view (no `attrs`, no `column_invisible`)
- Menu item under "Imobiliária" (no `groups` attribute)

### Phase 5: Testing & Quality
- E2E API integration tests (shell scripts in `integration_tests/`)
- Cypress E2E for Odoo admin UI
- Linting validation: `./lint.sh thedevkitchen_estate_goals && ./lint_xml.sh`

### Phase 6: Post-Development Documentation
- Swagger/OpenAPI via `thedevkitchen.swagger` (ADR-005)
- Postman collection via `thedevkitchen.postman` (ADR-016)
- Constitution update v1.8.0

---

## Validation Checklist

### Backend Validation
- [ ] All ADR requirements referenced and followed
- [ ] Multi-tenancy correctly specified (ADR-008)
- [ ] Security properly defined (ADR-011, ADR-017, ADR-019)
- [ ] Test strategy complete — unit + E2E API (ADR-003)
- [ ] API follows REST + HATEOAS standards (ADR-007)
- [ ] Database design normalized — 3NF minimum
- [ ] Error handling specified (ADR-018)
- [ ] Code quality requirements defined (ADR-022)

### Frontend Validation
- [ ] Views follow Odoo 18.0 standards (KB-10, ADR-001)
- [ ] No `attrs` attribute used
- [ ] Used `<list>` instead of `<tree>`
- [ ] Column visibility uses `optional="show|hide"` only
- [ ] No `column_invisible` with Python expressions
- [ ] Cypress E2E tests specified for all views
- [ ] Manual browser testing procedure defined
- [ ] Console error checks included in acceptance criteria
