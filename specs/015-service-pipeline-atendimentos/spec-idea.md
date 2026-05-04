# Feature Specification: Service Pipeline Management (Atendimentos)

**Feature Branch**: `015-service-pipeline-atendimentos`
**Created**: 2026-04-30
**Status**: Draft
**ADR References**: ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-011, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-022
**Related Specs**: 004-agent-management, 005-rbac-user-profiles, 006-lead-management, 013-property-proposals

## Executive Summary

Sistema de gestão de **Atendimentos** (service pipeline) — entidade que representa uma jornada de relacionamento entre um corretor e um cliente potencial sobre uma operação imobiliária específica (Venda ou Locação), movendo-se através de um pipeline estilo CRM: **Sem atendimento → Em atendimento → Visita → Proposta → Formalização**. Inspirado em CRMs imobiliários brasileiros (Kenlo IMOB, Vista, Imobzi), o atendimento é distinto do `real.estate.lead` (que representa o cliente potencial) — um mesmo lead/cliente pode originar múltiplos atendimentos (ex.: um de venda e outro de locação, ou um por corretor distinto). Permite filtragem por etapa, corretor, etiquetas, pendências e busca textual; suporta etiquetas (tags) configuráveis e origens de atendimento; e respeita multi-tenancy e RBAC.

---

## User Scenarios & Testing

### User Story 1 — Corretor cria e movimenta atendimento no pipeline (Priority: P1) 🎯 MVP

**As a** Agent (corretor)
**I want to** criar um atendimento ao receber um contato de cliente e movê-lo pelas etapas do pipeline
**So that** acompanho cada oportunidade de venda/locação até a formalização

**Acceptance Criteria**:
- [ ] Given Agent autenticado, when POST `/api/v1/services` com cliente novo (nome, telefone, e-mail) + tipo `rent` + origem + observações, then atendimento é criado com `stage='no_service'`, `agent_id=current_user`, `company_id=current_company` (ADR-008)
- [ ] Given atendimento em `no_service`, when PATCH `/api/v1/services/{id}/stage` com `{"stage":"in_service"}`, then transição é registrada em `mail.thread` com timestamp e usuário
- [ ] Given atendimento em `in_service` sem propriedade vinculada, when PATCH `/stage` com `{"stage":"proposal"}`, then retorna 422 com `{"error":"validation_error","details":["proposal stage requires at least one property linked"]}`
- [ ] Given atendimento em `proposal` sem proposta aprovada (013), when PATCH `/stage` com `{"stage":"formalization"}`, then retorna 422
- [ ] Given Agent A cria atendimento, when Agent B autentica e faz GET `/api/v1/services/{id}`, then retorna 404 (isolamento por agent_id em ADR-019)
- [ ] Given mesma combinação (cliente, tipo `sale`, agent) já tem atendimento ativo, when POST cria duplicado, then retorna 409 `{"error":"conflict","field":"client_id+operation_type+agent_id"}`
- [ ] Given atendimento com tag `closed`, when PATCH `/stage`, then retorna 423 `{"error":"locked","reason":"service is marked as closed"}`
- [ ] Given input inválido (tipo telefone fora de enum), when POST, then retorna 400 com lista de erros (ADR-018)

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_stage_transition_linear()` | Valida transições de etapa (forward + backward auditado) | ⚠️ Required |
| Unit | `test_stage_proposal_requires_property()` | Bloqueia avanço para proposal sem property_ids | ⚠️ Required |
| Unit | `test_stage_formalization_requires_approved_proposal()` | Integração com 013 | ⚠️ Required |
| Unit | `test_unique_active_service_per_client_type_agent()` | SQL constraint anti-duplicação | ⚠️ Required |
| Unit | `test_closed_tag_blocks_stage_change()` | Tag `closed` torna readonly no pipeline | ⚠️ Required |
| Unit | `test_lost_requires_lost_reason()` | Marcar como perdido exige motivo | ⚠️ Required |
| Unit | `test_pendency_computed_after_n_days()` | Campo computado `is_pending` | ⚠️ Required |
| E2E (API) | `test_agent_creates_service_full_lifecycle.sh` | POST → PATCH stages → close | ⚠️ Required |
| E2E (API) | `test_multitenancy_isolation_services.sh` | Agent A ↔ Agent B | ⚠️ Required |
| E2E (API) | `test_rbac_matrix_services.sh` | Owner/Manager/Agent/Reception/Prospector | ⚠️ Required |
| E2E (UI) | `cypress: services_admin_view.cy.js` | Admin visualiza lista no Odoo UI sem erros | ⚠️ Required |

---

### User Story 2 — Manager visualiza e reatribui atendimentos da company (Priority: P2)

**As a** Manager
**I want to** ver todos os atendimentos da minha imobiliária, filtrar e reatribuir corretor quando necessário
**So that** balanceio carga de trabalho e identifico gargalos no pipeline

**Acceptance Criteria**:
- [ ] Given Manager da Company A, when GET `/api/v1/services?stage=in_service&agent_id=5`, then retorna apenas atendimentos da Company A no estágio em atendimento do agent 5
- [ ] Given Manager, when PATCH `/api/v1/services/{id}/reassign` com `{"new_agent_id": 7}`, then `agent_id` é atualizado, evento registrado em `mail.thread`, e ambos corretores recebem notificação interna
- [ ] Given Agent autenticado, when PATCH `/reassign`, then retorna 403 (apenas Manager/Owner)
- [ ] Given Manager, when GET `/api/v1/services/summary`, then retorna `{"no_service": 55, "in_service": 84, "visit": 0, "proposal": 0, "formalization": 0}` com counts por etapa filtrados pela company
- [ ] Given filtro `?ordering=pendency`, when GET list, then retorna ordenado por `last_activity_date` ASC (mais antigos primeiro), respeitando regra de pendência (>N dias sem interação)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_reassign_updates_audit_log()` | Auditoria via mail.thread | ⚠️ Required |
| Unit | `test_summary_counts_per_company()` | Multi-tenancy nos contadores | ⚠️ Required |
| E2E (API) | `test_manager_reassigns_service.sh` | Fluxo de reatribuição | ⚠️ Required |
| E2E (API) | `test_kanban_summary_endpoint.sh` | GET /summary | ⚠️ Required |
| E2E (API) | `test_filters_and_ordering.sh` | tipo, corretor, etiquetas, pendências, busca | ⚠️ Required |

---

### User Story 3 — Etiquetas (Tags) e Origens configuráveis (Priority: P2)

**As a** Owner ou Manager
**I want to** gerenciar etiquetas (Follow Up, Qualificado, Lançamento, Parceria, Encerrado, etc.) e origens de atendimento (Site, Indicação, Portal, etc.)
**So that** corretores categorizam atendimentos de forma padronizada por toda a imobiliária

**Acceptance Criteria**:
- [ ] Given Owner, when POST `/api/v1/service-tags` com `{"name":"VIP","color":"#FF0000"}`, then tag é criada, escopo da company
- [ ] Given Agent, when POST `/api/v1/service-tags`, then retorna 403
- [ ] Given atendimento, when PUT `/api/v1/services/{id}` com `{"tag_ids":[1,3,5]}`, then associação many2many é atualizada
- [ ] Given tag em uso por atendimentos, when DELETE `/api/v1/service-tags/{id}`, then aplica soft delete (active=False) preservando histórico (ADR-015)
- [ ] Given Manager, when GET `/api/v1/service-sources`, then retorna lista de origens configuradas (Site, Indicação, Portal Imobiliário, WhatsApp, etc.)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_tag_company_isolation()` | Tag da Company A invisível para B | ⚠️ Required |
| Unit | `test_tag_soft_delete_preserves_history()` | ADR-015 | ⚠️ Required |
| E2E (API) | `test_tags_crud.sh` | CRUD completo + RBAC | ⚠️ Required |
| E2E (API) | `test_sources_crud.sh` | CRUD origens | ⚠️ Required |

---

### User Story 4 — Múltiplos telefones e dados do cliente (Priority: P3)

**As a** Agent ou Recepcionista
**I want to** cadastrar múltiplos telefones do cliente (celular, residencial, comercial, WhatsApp) ao criar atendimento
**So that** tenho múltiplos canais de contato

**Acceptance Criteria**:
- [ ] Given POST `/api/v1/services` com `phones:[{"type":"mobile","number":"(11) 98133-0379"},{"type":"whatsapp","number":"(11) 91111-2222"}]`, then phones são criados/vinculados ao `res.partner` do cliente
- [ ] Given mesmo cliente já existe (match por telefone OR email), when POST cria atendimento, then reusa partner existente em vez de duplicar
- [ ] Given tipo de telefone fora do enum (`mobile|home|work|whatsapp|fax`), when POST, then retorna 400

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_partner_deduplication_by_phone_or_email()` | Reuso de partner | ⚠️ Required |
| Unit | `test_phone_type_enum_validation()` | ADR-018 | ⚠️ Required |
| E2E (API) | `test_service_with_multiple_phones.sh` | Fluxo completo | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Pipeline de Atendimento**
- FR1.1: Etapas suportadas (enum): `no_service`, `in_service`, `visit`, `proposal`, `formalization`, `won`, `lost`
- FR1.2: Transições lineares no fluxo principal (`no_service → in_service → visit → proposal → formalization → won`); retroceder é permitido com auditoria; transição para `lost` pode ocorrer de qualquer etapa exigindo `lost_reason`
- FR1.3: Etapa `proposal` exige `property_ids` não-vazio
- FR1.4: Etapa `formalization` exige proposta aprovada vinculada (integração com `real.estate.proposal` da spec 013)
- FR1.5: Tag `closed` (system tag não-editável) bloqueia movimentação no pipeline
- FR1.6: Cada transição é registrada em `mail.thread` (ADR via Odoo `mail.thread` mixin)

**FR2: Filtros e Listagem**
- FR2.1: Filtros suportados via query params: `operation_type` (sale|rent), `stage`, `agent_id`, `tag_ids` (CSV), `source_id`, `is_pending` (bool), `q` (busca em cliente/telefone/imóvel), `archived` (bool)
- FR2.2: Ordenação via `?ordering=`: `pendency` (mais antigos sem interação), `recent` (most recently updated), `oldest`, `best_potential` (orçamento desc)
- FR2.3: Paginação `?page=&per_page=` (default 20, max 100)
- FR2.4: Endpoint `GET /api/v1/services/summary` retorna contadores por etapa para a company

**FR3: Etiquetas e Origens**
- FR3.1: Tags (`real.estate.service.tag`) com `name`, `color`, `company_id`, escopo da company
- FR3.2: Origens (`real.estate.service.source`) com `name`, `code`, `active`, `company_id`
- FR3.3: CRUD de tags e origens restrito a Owner/Manager

**FR4: Cliente e Contatos**
- FR4.1: Cliente representado por `res.partner` (Odoo nativo) com extensão para múltiplos telefones via `real.estate.partner.phone` (one2many)
- FR4.2: Deduplicação de partner por `(phone OR email)` na criação do atendimento
- FR4.3: Tipos de telefone (enum): `mobile`, `home`, `work`, `whatsapp`, `fax`

**FR5: Reatribuição e Pendências**
- FR5.1: PATCH `/services/{id}/reassign` exclusivo para Manager/Owner; auditado
- FR5.2: Campo computado `is_pending`: True se `last_activity_date` > N dias (configurável em `thedevkitchen.service.settings`, default 3 dias)
- FR5.3: Settings singleton: `pendency_threshold_days` (1-30), `auto_close_after_days` (opcional)

### Data Model

> Naming segue convenção existente do projeto (`real.estate.*` — vide modelos atuais `real.estate.lead`, `real.estate.proposal`); módulo será adicionado a `quicksol_estate` ou criado como `quicksol_service_pipeline` (a decidir no plan).

**Entity: `real.estate.service`** (Atendimento)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | — |
| `name` | Char(50) | required, computed | Identificador (ex.: `ATD/2026/00001`) gerado por sequence |
| `client_partner_id` | Many2one(res.partner) | required, ondelete='restrict' | Cliente |
| `lead_id` | Many2one(real.estate.lead) | optional | Vínculo com lead da spec 006 (se originado de lead) |
| `agent_id` | Many2one(res.users) | required, index | Corretor responsável |
| `operation_type` | Selection | required | `sale`, `rent` |
| `source_id` | Many2one(real.estate.service.source) | required | Origem |
| `stage` | Selection | required, default `no_service`, index | `no_service`, `in_service`, `visit`, `proposal`, `formalization`, `won`, `lost` |
| `tag_ids` | Many2many(real.estate.service.tag) | — | Etiquetas |
| `property_ids` | Many2many(real.estate.property) | — | Imóveis de interesse |
| `proposal_ids` | One2many(real.estate.proposal) | — | Propostas vinculadas (013) |
| `notes` | Text | — | Observações |
| `last_activity_date` | Datetime | computed, stored | Última interação (max de write_date e mail messages) |
| `is_pending` | Boolean | computed, stored | True se `last_activity_date` > threshold |
| `lost_reason` | Char(255) | conditional | Obrigatório se `stage='lost'` |
| `won_date` | Datetime | conditional | Preenchido ao mover para `won` |
| `company_id` | Many2one(res.company) | required, index | Multi-tenancy (ADR-008) |
| `active` | Boolean | default True | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | Auditoria |
| `write_date` | Datetime | auto | Auditoria |
| `create_uid` | Many2one(res.users) | auto | Auditoria |

Inherits: `mail.thread`, `mail.activity.mixin`

**SQL Constraints**:
```python
_sql_constraints = [
    ('unique_active_service_per_client_type_agent',
     'EXCLUDE (client_partner_id WITH =, operation_type WITH =, agent_id WITH =) WHERE (active AND stage NOT IN (\'won\',\'lost\'))',
     'Já existe um atendimento ativo para este cliente, tipo de operação e corretor'),
]
```

**Python Constraints**:
```python
@api.constrains('stage', 'property_ids')
def _check_proposal_stage_requires_property(self):
    for r in self:
        if r.stage == 'proposal' and not r.property_ids:
            raise ValidationError(_('Etapa Proposta exige ao menos um imóvel vinculado.'))

@api.constrains('stage', 'proposal_ids')
def _check_formalization_requires_approved_proposal(self):
    for r in self:
        if r.stage == 'formalization' and not r.proposal_ids.filtered(lambda p: p.state == 'approved'):
            raise ValidationError(_('Etapa Formalização exige proposta aprovada vinculada.'))

@api.constrains('stage', 'lost_reason')
def _check_lost_reason(self):
    for r in self:
        if r.stage == 'lost' and not r.lost_reason:
            raise ValidationError(_('Informe o motivo da perda.'))
```

**Entity: `real.estate.service.tag`**

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | PK |
| `name` | Char(50) | required |
| `color` | Char(7) | hex `#RRGGBB`, default `#808080` |
| `is_system` | Boolean | default False (tag `closed` é system) |
| `company_id` | Many2one | required |
| `active` | Boolean | default True |

`_sql_constraints`: `unique(name, company_id)`

**Entity: `real.estate.service.source`**

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | PK |
| `name` | Char(80) | required |
| `code` | Char(30) | required |
| `company_id` | Many2one | required |
| `active` | Boolean | default True |

`_sql_constraints`: `unique(code, company_id)`

**Entity: `real.estate.partner.phone`**

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | Integer | PK |
| `partner_id` | Many2one(res.partner) | required, ondelete='cascade' |
| `phone_type` | Selection | required: `mobile`, `home`, `work`, `whatsapp`, `fax` |
| `number` | Char(30) | required, normalized E.164 quando possível |
| `is_primary` | Boolean | default False |

**Entity: `thedevkitchen.service.settings`** (singleton per company)

| Field | Type | Constraints |
|-------|------|-------------|
| `pendency_threshold_days` | Integer | required, 1..30, default 3 |
| `auto_close_after_days` | Integer | optional, 0..365 |
| `company_id` | Many2one | required, unique |

**Record Rules** (per ADR-019):

```xml
<record id="rule_service_company" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>

<record id="rule_service_agent_own" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="groups" eval="[(4, ref('thedevkitchen_user_onboarding.group_profile_agent'))]"/>
  <field name="domain_force">[('agent_id', '=', user.id)]</field>
</record>

<record id="rule_service_prospector_own" model="ir.rule">
  <field name="model_id" ref="model_real_estate_service"/>
  <field name="groups" eval="[(4, ref('thedevkitchen_user_onboarding.group_profile_prospector'))]"/>
  <field name="domain_force">[('agent_id', '=', user.id)]</field>
</record>
```

### API Endpoints (per ADR-007, ADR-009, ADR-011)

> Todos os endpoints autenticados aplicam **triple decorator**: `@require_jwt + @require_session + @require_company`.

| Method | Path | Auth | Roles | Descrição |
|--------|------|------|-------|-----------|
| POST | `/api/v1/services` | triple | Owner, Manager, Agent, Reception, Prospector | Cria atendimento |
| GET | `/api/v1/services` | triple | All | Lista com filtros |
| GET | `/api/v1/services/summary` | triple | Owner, Manager, Agent (own), Reception, Prospector (own) | Contadores por etapa |
| GET | `/api/v1/services/{id}` | triple | All (com isolamento) | Detalhe |
| PUT | `/api/v1/services/{id}` | triple | Owner, Manager, Agent (own) | Atualiza |
| DELETE | `/api/v1/services/{id}` | triple | Owner, Manager | Soft delete |
| PATCH | `/api/v1/services/{id}/stage` | triple | Owner, Manager, Agent (own) | Move etapa |
| PATCH | `/api/v1/services/{id}/reassign` | triple | Owner, Manager | Reatribui corretor |
| GET/POST/PUT/DELETE | `/api/v1/service-tags[/id]` | triple | Read: All; Write: Owner, Manager | CRUD tags |
| GET/POST/PUT/DELETE | `/api/v1/service-sources[/id]` | triple | Read: All; Write: Owner, Manager | CRUD origens |

**Exemplo: POST `/api/v1/services`**

Request:
```json
{
  "client": {
    "name": "Danilo Silva",
    "email": "danilo@example.com",
    "phones": [
      {"type": "mobile", "number": "(98) 98882-5176", "is_primary": true}
    ]
  },
  "operation_type": "rent",
  "source_id": 3,
  "agent_id": 12,
  "property_ids": [45],
  "tag_ids": [1, 4],
  "notes": "Cliente interessada em apto 2 quartos no Centro"
}
```

Response 201:
```json
{
  "id": 101,
  "name": "ATD/2026/00101",
  "client": {"id": 88, "name": "Danilo Silva"},
  "agent_id": 12,
  "operation_type": "rent",
  "stage": "no_service",
  "is_pending": false,
  "tag_ids": [1, 4],
  "property_ids": [45],
  "source_id": 3,
  "company_id": 1,
  "created_at": "2026-04-30T10:00:00Z",
  "links": [
    {"href":"/api/v1/services/101", "rel":"self", "type":"GET"},
    {"href":"/api/v1/services/101", "rel":"update", "type":"PUT"},
    {"href":"/api/v1/services/101/stage", "rel":"move-stage", "type":"PATCH"},
    {"href":"/api/v1/services/101/reassign", "rel":"reassign", "type":"PATCH"},
    {"href":"/api/v1/services", "rel":"collection", "type":"GET"}
  ]
}
```

**Exemplo: PATCH `/api/v1/services/{id}/stage`**

Request:
```json
{"stage": "proposal", "comment": "Cliente fechou visita, aguardando proposta"}
```

Erros:
| Code | Condição | Response |
|------|----------|----------|
| 400 | Validation (ADR-018) | `{"error":"validation_error","details":[...]}` |
| 401 | JWT inválido | `{"error":"unauthorized"}` |
| 403 | RBAC (ADR-019) | `{"error":"forbidden"}` |
| 404 | Não encontrado / fora do escopo | `{"error":"not_found"}` |
| 409 | Duplicado | `{"error":"conflict","field":"client_partner_id+operation_type+agent_id"}` |
| 422 | Regra de pipeline | `{"error":"unprocessable","reason":"proposal stage requires at least one property linked"}` |
| 423 | Tag closed bloqueia | `{"error":"locked","reason":"service is marked as closed"}` |

### Authorization Matrix (ADR-019)

| Operação | Owner | Manager | Agent | Reception | Prospector |
|----------|-------|---------|-------|-----------|------------|
| Create service | ✅ | ✅ | ✅ | ✅ | ✅ |
| Read all (company) | ✅ | ✅ | ❌ (own) | ✅ | ❌ (own) |
| Update | ✅ | ✅ | ✅ (own) | ❌ | ❌ |
| Delete (soft) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Move stage | ✅ | ✅ | ✅ (own) | ❌ | ❌ |
| Reassign | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage tags/sources | ✅ | ✅ | ❌ | ❌ | ❌ |

### Seed Data (MANDATORY)

```python
# Companies
company_a = env['res.company'].create({'name': 'Imobiliária Seed A'})
company_b = env['res.company'].create({'name': 'Imobiliária Seed B'})

# Users (one per role; logins prefixed with seed_)
seed_users = {
    'owner_a':       'seed_owner_a@test.com',
    'manager_a':     'seed_manager_a@test.com',
    'agent_a1':      'seed_agent_a1@test.com',
    'agent_a2':      'seed_agent_a2@test.com',
    'reception_a':   'seed_reception_a@test.com',
    'prospector_a':  'seed_prospector_a@test.com',
    'owner_b':       'seed_owner_b@test.com',  # for isolation tests
    'agent_b1':      'seed_agent_b1@test.com',
}

# Sources
sources = ['Site', 'Indicação', 'Portal Imobiliário', 'WhatsApp', 'Plantão']

# Tags (system + custom)
tags = [
    {'name': 'closed', 'is_system': True, 'color': '#9E9E9E'},
    {'name': 'Follow Up', 'color': '#2196F3'},
    {'name': 'Qualificado', 'color': '#4CAF50'},
    {'name': 'Lançamento', 'color': '#F44336'},
    {'name': 'Parceria', 'color': '#FF9800'},
]

# Sample partners (clients) + phones
# Sample properties (3 in company_a, 1 in company_b)
# Sample services covering all stages: no_service, in_service, visit, proposal, formalization, won, lost
# At least one service in company_b for isolation tests
```

> Idempotente — usa `xml_id` `seed_service_*` para upsert.

---

### Non-Functional Requirements

**NFR1: Security** (ADR-008/011/017/019)
- Triple decorator em todos os endpoints autenticados
- Multi-tenant via `company_id` + record rules
- RBAC matrix enforced
- JWT fingerprint validation (ADR-017)

**NFR2: Performance**
- GET `/api/v1/services?...` < 300ms para até 10k registros (com índices em `stage`, `agent_id`, `company_id`, `last_activity_date`)
- GET `/summary` < 100ms (query agregada com cache Redis opcional, TTL 30s)
- Paginação default 20, max 100

**NFR3: Quality** (ADR-022)
- black, isort, flake8 passing
- pylint ≥ 8.0
- 100% cobertura nas validações
- Cypress: zero erros de console no admin view

**NFR4: Data Integrity** (KB-09)
- 3NF; tags como entidade separada; phones como tabela 1:N
- FK com `ondelete` adequado: client `restrict`, agent `restrict`, source `restrict`, tags via M2M, property M2M
- Soft delete (ADR-015)

**NFR5: Frontend (Admin Odoo UI)** (KB-10)
- Use `<list>` (não `<tree>`)
- `optional="show|hide"` para colunas
- Sem `column_invisible` com expressão Python
- Sem `attrs`
- **Menus admin sem `groups`** (admin user only)

---

## Technical Constraints

| Source | Requirement |
|--------|-------------|
| ADR-001 | Estrutura plana; views Odoo 18.0 |
| ADR-001 | `<menuitem>` sem `groups` |
| ADR-003 | 100% cobertura validações; Cypress E2E para Odoo UI admin |
| ADR-004 | Prefixo padrão do projeto (`real.estate.*` para domínio, `thedevkitchen.*` para infra) |
| ADR-005 | OpenAPI 3.0 dinâmico via `thedevkitchen_api_endpoint` (skill swagger-updater) |
| ADR-007 | HATEOAS em todas respostas |
| ADR-008 | `company_id` em todas entidades + record rules |
| ADR-011 | Triple decorator `@require_jwt + @require_session + @require_company` |
| ADR-015 | Soft delete via `active` |
| ADR-016 | Coleção Postman padrão |
| ADR-018 | Schema validation em todos POST/PUT/PATCH |
| ADR-019 | RBAC matrix |
| ADR-022 | Lint Python + XML |
| KB-09 | 3NF, índices, FKs |
| KB-10 | Padrões frontend Odoo 18.0 |

---

## Success Criteria

### Backend
- [ ] Todas user stories implementadas e testadas
- [ ] 100% cobertura unit tests nas validações (ADR-003)
- [ ] E2E API tests para todos fluxos críticos (criar, mover etapa, reatribuir, summary, RBAC, isolamento)
- [ ] Multi-company isolation verificado
- [ ] Pylint ≥ 8.0; black/isort/flake8 OK
- [ ] Pipeline transitions auditadas via mail.thread

### Frontend (Odoo UI Admin)
- [ ] Lista e form views seguem Odoo 18.0 (KB-10)
- [ ] Menus sem `groups`
- [ ] Cypress E2E: admin abre lista de services sem erros
- [ ] Zero erros JS no console

### Seeds
- [ ] Seed file criado, idempotente, prefixo `seed_`
- [ ] Cobre todos os 5 perfis em duas companies
- [ ] Cobre todos os 7 estágios do pipeline

### Documentação (post-dev)
- [ ] Swagger atualizado via DB (skill swagger-updater)
- [ ] Coleção Postman criada (skill postman-collection-manager)

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| Pipeline state machine com auditoria via mail.thread | Padrão para futuras features de pipeline (proposta, contratos) | Architectural Patterns → Pipeline | High |
| Computed pendency flag (time-based) | Campo `is_pending` baseado em threshold configurável | Architectural Patterns → Computed Stored Fields | Medium |
| Singleton de configurações por company | `thedevkitchen.service.settings` (similar a `thedevkitchen.email.link.settings` da 009) | Configuration Patterns | Low (já existe pattern) |
| `EXCLUDE` SQL constraint para unicidade condicional | Anti-duplicação de atendimento ativo via PostgreSQL EXCLUDE | Database Patterns | Medium |
| Tag system flag (`is_system`) | Tags imutáveis pelo usuário (ex.: `closed` controla regra de negócio) | Data Modeling | Medium |
| Endpoint summary/aggregação para kanban | Padrão `GET /resource/summary` com counts por estado | API Patterns → Aggregation Endpoints | High |

### New Entities/Relationships

| Entity | Related To | Relationship | Notes |
|--------|-----------|--------------|-------|
| `real.estate.service` | `res.partner`, `real.estate.lead`, `res.users`, `real.estate.property`, `real.estate.proposal` | M2O / M2M / O2M | Pipeline central |
| `real.estate.service.tag` | `real.estate.service` | M2M | Tags por company |
| `real.estate.service.source` | `real.estate.service` | M2O | Origens por company |
| `real.estate.partner.phone` | `res.partner` | O2M | Múltiplos telefones |
| `thedevkitchen.service.settings` | `res.company` | M2O (singleton) | Config por company |

### Architectural Decisions

| Decision | Rationale | ADR Required? |
|----------|-----------|---------------|
| Atendimento como entidade distinta de Lead | Um lead pode originar múltiplas oportunidades (sale + rent, ou múltiplos corretores); entidades separadas mantêm responsabilidade única | Sim — sugerir **ADR-025: Service Pipeline vs Lead Domain Boundaries** |
| Uso de `EXCLUDE` constraint condicional | Permite unicidade apenas para registros ativos sem afetar `won/lost` históricos | Não (decisão técnica, documentar em data-model.md) |
| Pipeline state machine na própria entidade (não em workflow externo) | Simplicidade; pipelines são estáveis | Não |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: MINOR (1.3.0 → 1.4.0)
- **Sections to Update**:
  - [x] Architectural Patterns (Pipeline state machine, Aggregation endpoints, EXCLUDE constraint)
  - [x] Data Modeling Patterns (system tags, computed pendency)
  - [ ] Core Principles — sem mudança
  - [ ] Security Requirements — sem mudança

---

## Assumptions & Dependencies

**Assumptions**:
- Spec 006 (`real.estate.lead`) está implementada — atendimento referencia opcionalmente lead
- Spec 013 (`real.estate.proposal`) está implementada — etapa `formalization` exige proposta aprovada
- Spec 005 (RBAC) está implementada — grupos `group_profile_*` existem
- `mail.thread`/`mail.activity.mixin` disponíveis (Odoo nativo)

**Dependencies**:
- Módulos: `quicksol_estate`, `thedevkitchen_apigateway`, `thedevkitchen_user_onboarding`
- Externos: PostgreSQL 14+ (necessário para `EXCLUDE` constraint), Redis 7+ (cache opcional do summary)
- Auth: OAuth2 via `thedevkitchen_apigateway`

---

## Implementation Phases

### Phase 1: Foundation
- Modelos: `service`, `service.tag`, `service.source`, `partner.phone`, `service.settings`
- Sequence `ATD/YYYY/NNNNN`
- SQL constraints (incluindo EXCLUDE)
- Record rules (ADR-019)
- Unit tests para todas validações

### Phase 2: API Layer
- Controllers com triple decorator (ADR-011)
- Schemas de validação (ADR-018)
- HATEOAS (ADR-007)
- Endpoint `/summary` agregado

### Phase 3: Admin UI (Odoo)
- List/form views (Odoo 18.0 compliant)
- Menus (sem `groups`)
- Cypress E2E para admin

### Phase 4: Testing & Quality
- Integration tests (`integration_tests/test_us15_*.sh`)
- Multi-tenancy isolation
- RBAC matrix tests
- Linters (Python + XML)

### Phase 5: Documentation (post-dev)
- Swagger via DB (skill swagger-updater)
- Coleção Postman (skill postman-collection-manager)
- Constitution amendment (MINOR bump)

---

## Artifacts to Generate

1. **Constitution Update** (MANDATORY) — novos patterns identificados acima → handoff `thedevkitchen.constitution`
2. **Implementation Plan** → handoff `speckit.plan` (gera `plan-idea.md` neste diretório)
3. **Test Strategy** → handoff `speckit.test-strategy`
4. **Post-dev**: Swagger (`thedevkitchen.swagger`), Postman (`thedevkitchen.postman`)

---

## Validation Checklist

### Backend
- [x] ADRs referenciadas (001, 003, 004, 005, 007, 008, 009, 011, 015, 016, 017, 018, 019, 022)
- [x] KB patterns aplicados (09 DB, 10 frontend)
- [x] Multi-tenancy especificada (ADR-008)
- [x] Triple decorator security (ADR-011)
- [x] Test strategy completa (unit + E2E API + Cypress admin)
- [x] HATEOAS em todas responses
- [x] 3NF + índices + FK actions
- [x] Error handling com códigos específicos (incluindo 422/423)
- [x] Lint requirements

### Frontend (Admin)
- [x] Sem `attrs`, sem `<tree>`, sem `column_invisible` com expressão
- [x] `optional` para colunas
- [x] Menus sem `groups`
- [x] Cypress E2E especificado
- [x] Zero console errors

### Seeds
- [x] Seed plan com prefixo `seed_`
- [x] Cobre 5 perfis em 2 companies
- [x] Cobre todos os 7 stages
- [x] Idempotente (xml_id)
