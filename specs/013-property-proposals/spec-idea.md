# Feature Specification: Property Proposals Management

**Feature Branch**: `012-property-proposals`
**Created**: 2026-04-27
**Status**: Draft
**ADR References**: ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-011, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020, ADR-022, ADR-025, **ADR-027 (proposed: Pessimistic Locking for Resource Queues)**

---

## Executive Summary

Gerenciamento completo de **propostas de venda/locação** sobre propriedades. Permite que agentes/managers/owners criem, enviem, negociem, aceitem ou rejeitem propostas vinculadas a uma propriedade e a um cliente (`res.partner`). Suporta workflow de **8 estados** (Draft → Queued → Sent → Negotiation → Accepted/Rejected/Expired/Cancelled), regra de **1 proposta ativa por propriedade com fila FIFO automática**, contraproposta versionada via `parent_proposal_id`, anexos via `ir.attachment`, timeline via `mail.thread`, geração opcional de lead a partir do contato com `source = 'proposal'`, e auto-cancelamento de concorrentes ao aceitar (com rastreabilidade via `superseded_by_id`).

---

## User Scenarios & Testing

### User Story 1: Agent cria e envia proposta (Priority: P1) MVP

**As an** Agent
**I want to** registrar uma nova proposta para uma propriedade que tenho atribuída
**So that** o cliente receba a oferta formal e eu possa acompanhar a negociação

**Acceptance Criteria**:
- [ ] Given uma propriedade ativa atribuída ao agent SEM proposta ativa, when ele faz `POST /api/v1/proposals` com `client_name`, `client_document`, `property_id`, `proposal_value`, `agent_id`, then a proposta é criada em status `draft` (HTTP 201) com `proposal_code` (PRP001…) gerado por sequência.
- [ ] Given um `client_document` que já existe como `res.partner`, when a proposta é criada, then o partner existente é reutilizado (não duplicado).
- [ ] Given um `client_document` que já é `lead_id` ativo, when a proposta é criada sem `lead_id`, then o sistema vincula automaticamente o lead existente.
- [ ] Given proposta em `draft`, when agent chama `POST /api/v1/proposals/{id}/send`, then status muda para `sent`, `sent_date` é registrado, email disparado (mail.template), timeline registra evento.
- [ ] Given `proposal_value <= 0`, when criação é tentada, then HTTP 400 (ADR-018).
- [ ] Given agent tentando criar para propriedade NÃO atribuída, when `POST /api/v1/proposals`, then HTTP 403.
- [ ] Given proposta da Empresa A, when agent da Empresa B faz `GET /api/v1/proposals/{id}`, then HTTP 404 (ADR-008).

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_proposal_value_must_be_positive` | Constraint valor > 0 | Required |
| Unit | `test_proposal_code_sequence_unique` | Sequência por empresa | Required |
| Unit | `test_partner_reuse_by_document` | Reutiliza partner por CPF/CNPJ | Required |
| Unit | `test_auto_link_existing_lead` | Vincula lead existente | Required |
| Unit | `test_state_transition_draft_to_sent` | FSM válido | Required |
| Unit | `test_invalid_state_transition_blocked` | sent→draft bloqueado | Required |
| E2E (API) | `test_us1_s1_agent_creates_proposal.sh` | Criação completa | Required |
| E2E (API) | `test_us1_s2_agent_sends_proposal.sh` | draft→sent + email | Required |
| E2E (API) | `test_us1_s3_multitenancy_isolation.sh` | Isolamento por company | Required |
| E2E (UI) | `cypress/e2e/views/proposals.cy.js` | List/form sem console errors | Required |

---

### User Story 2: Negociação e contraproposta (Priority: P1)

**As a** Manager or Agent
**I want to** registrar uma contraproposta quando o cliente solicita mudanças
**So that** o histórico de negociação fique rastreado

**Acceptance Criteria**:
- [ ] Given proposta em `sent`, when `POST /api/v1/proposals/{id}/counter` com novo `proposal_value` e `notes`, then a original muda para `negotiation`, é criada nova proposta vinculada via `parent_proposal_id`, herdando `client_id`, `property_id`, `agent_id`.
- [ ] Given proposta com `parent_proposal_id`, when consultada via `GET /api/v1/proposals/{id}`, then resposta inclui `proposal_chain` (cadeia em ordem cronológica).
- [ ] Given múltiplas contrapropostas encadeadas, when consultada a chain, then todas as versões são retornadas.
- [ ] **Importante**: contraproposta NÃO entra na fila — ela substitui logicamente a anterior na mesma propriedade (mesma sequência ativa).

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_counter_creates_linked_proposal` | parent_proposal_id setado | Required |
| Unit | `test_counter_changes_original_to_negotiation` | Estado anterior muda | Required |
| Unit | `test_counter_inherits_fields` | Herança de cliente/property/agent | Required |
| Unit | `test_counter_does_not_enqueue` | Counter mantém slot ativo | Required |
| E2E (API) | `test_us2_s1_counter_proposal.sh` | Fluxo contraproposta | Required |

---

### User Story 3: Aceite/Rejeição com efeitos colaterais (Priority: P1)

**As a** Manager or Agent (proprietário)
**I want to** marcar a proposta como aceita ou rejeitada
**So that** o status reflita a decisão e habilite próximos passos

**Acceptance Criteria**:
- [ ] Given proposta em `sent` ou `negotiation`, when `POST /api/v1/proposals/{id}/accept`, then status muda para `accepted`, `accepted_date` registrado, evento `proposal.accepted` emitido (Observer ADR-020), email disparado.
- [ ] Given proposta aceita, when consultada, then HATEOAS inclui `rel: "create-contract"` (feature 008) — **NÃO cria contrato automaticamente**.
- [ ] Given `POST /api/v1/proposals/{id}/reject`, then `rejection_reason` é obrigatório; status → `rejected`, `rejected_date` registrado.
- [ ] Given proposta `accepted`/`rejected`/`expired`/`cancelled`, when `PUT /api/v1/proposals/{id}`, then HTTP 409 (estado terminal).
- [ ] Given rejeição, when processada, then o sistema **promove automaticamente** a próxima `queued` da propriedade para `draft` (FIFO) — ver US8.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_reject_requires_reason` | rejection_reason obrigatório | Required |
| Unit | `test_terminal_state_blocks_update` | accepted/rejected immutable | Required |
| Unit | `test_accept_emits_observer_event` | proposal.accepted disparado | Required |
| E2E (API) | `test_us3_s1_accept_proposal.sh` | Aceite + HATEOAS contract link | Required |
| E2E (API) | `test_us3_s2_reject_proposal.sh` | Rejeição com motivo | Required |

---

### User Story 4: Listagem com filtros e métricas (Priority: P1)

**As a** Manager
**I want to** ver todas as propostas da minha empresa com totalizadores por status
**So that** acompanhe o pipeline de negociações

**Acceptance Criteria**:
- [ ] `GET /api/v1/proposals?status=negotiation&agent_id=X&property_id=Y&search=PRP001&date_from=...&date_to=...` retorna paginação (max 100/pg) isolado por `company_id`.
- [ ] `GET /api/v1/proposals/stats` retorna `{total, by_state: {draft, queued, sent, negotiation, accepted, rejected, expired, cancelled}}` para a empresa.
- [ ] Agent autenticado, `GET /api/v1/proposals` (sem filtro) → apenas onde `agent_id == user`.
- [ ] Manager/Owner → todas da empresa.
- [ ] Receptionist → read-only (sem links de mutação no HATEOAS).

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_stats_aggregation_by_company` | Contadores por estado | Required |
| E2E (API) | `test_us4_s1_list_filters.sh` | Filtros combinados + paginação | Required |
| E2E (API) | `test_us4_s2_agent_sees_only_own.sh` | Agent restrito | Required |
| E2E (API) | `test_us4_s3_stats_endpoint.sh` | Agregados corretos | Required |

---

### User Story 5: Lead origem `proposal` quando contato é novo (Priority: P2)

**As the** system
**I want to** criar automaticamente um lead com `source='proposal'` quando o contato não existe ainda como lead
**So that** o pipeline de leads inclua oportunidades vindas de propostas diretas

**Acceptance Criteria**:
- [ ] Given contato cujo `document` NÃO existe em `real.estate.lead` ativo, when proposta é criada, then sistema cria lead com `source='proposal'`, `proposal_id` setado, `partner_id` linkado.
- [ ] Given contato JÁ existe como lead ativo, when criada, then sistema apenas vincula `lead_id` (NÃO duplica).
- [ ] Selection `source` em `real.estate.lead` inclui `'proposal'` após migration.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_new_contact_creates_lead_with_proposal_source` | Auto-criação | Required |
| Unit | `test_existing_lead_is_linked_not_duplicated` | Reutilização | Required |
| E2E (API) | `test_us5_s1_proposal_generates_lead.sh` | Fluxo completo | Required |

---

### User Story 6: Anexos (documentos) (Priority: P2)

**As an** Agent
**I want to** anexar documentos à proposta
**So that** ela seja completa e auditável

**Acceptance Criteria**:
- [ ] `POST /api/v1/proposals/{id}/attachments` (multipart) → grava em `ir.attachment`, retorna `attachment_id` e `download_url`.
- [ ] `documents_count` reflete número de anexos.
- [ ] `GET /api/v1/proposals/{id}` inclui `attachments[]` com `id`, `name`, `mimetype`, `size`, `download_url`.
- [ ] Tipo não permitido → HTTP 400. Arquivo > 10MB → HTTP 413.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_attachment_size_limit` | Limite 10MB | Required |
| Unit | `test_attachment_mimetype_whitelist` | PDF/DOC/IMG only | Required |
| E2E (API) | `test_us6_s1_upload_attachment.sh` | Upload + listagem | Required |

---

### User Story 7: Expiração automática (Priority: P3)

**As the** system
**I want to** marcar propostas como `expired` automaticamente após `valid_until`
**So that** o pipeline reflita a realidade

**Acceptance Criteria**:
- [ ] Cron `cron_expire_proposals` (diário 02:00) move `sent`/`negotiation` com `valid_until < today` para `expired`.
- [ ] Default de `valid_until` = `sent_date + 7 dias` no `/send`.
- [ ] Proposta `expired` libera o slot ativo da propriedade → próxima `queued` é promovida (FIFO).
- [ ] Proposta `expired` oferece HATEOAS `rel: "renew"` (clona em `draft` se slot disponível).

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_cron_expires_overdue_proposals` | Cron move estados | Required |
| Unit | `test_default_validity_7_days` | Default no send | Required |
| Unit | `test_expiration_promotes_next_queued` | Auto-promoção | Required |
| Integration | `test_us7_s1_expiration_cron.sh` | Cron integração | Required |

---

### User Story 8: Enfileiramento automático em propriedade ocupada (Priority: P1)

**As an** Agent
**I want to** criar uma proposta para uma propriedade que já tem outra ativa
**So that** ela entre na fila e seja automaticamente promovida quando a ativa terminar

**Acceptance Criteria**:
- [ ] Given propriedade com proposta ativa (`draft`/`sent`/`negotiation`/`accepted`) de outro agent, when crio nova proposta, then ela é criada com `state='queued'` e `queue_position=N` (N = posição na fila, FIFO por `created_date ASC`).
- [ ] Given proposta ativa vai para estado terminal **não-aceito** (`rejected`/`expired`/`cancelled`), when sistema processa transição, then a próxima `queued` é promovida para `draft`, `queue_position` é recalculado para as restantes, agente da promovida é notificado via email + chatter.
- [ ] Given múltiplas em `queued`, when listo via `GET /api/v1/proposals?property_id=X&state=queued`, then resposta vem ordenada por `created_date ASC` com `queue_position` correto.
- [ ] Given proposta em `queued`, when tento `POST /api/v1/proposals/{id}/send`, then HTTP 422 com mensagem "Proposal is queued; cannot send until promoted".
- [ ] Given `queued`, when `PUT /api/v1/proposals/{id}` para editar `proposal_value`/`description`/`valid_until`, then permitido.
- [ ] Given criação concorrente (2 agentes simultâneos para propriedade vazia), when ambas tentam virar `draft`, then sistema usa `SELECT FOR UPDATE` em `real.estate.property` → uma vira `draft`, outra vira `queued` (sem violação de constraint).
- [ ] Given `GET /api/v1/proposals/{id}/queue`, then retorna `{property_id, active_proposal, queue: [...]}`.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_second_proposal_goes_to_queued` | FIFO automático | Required |
| Unit | `test_queue_position_computed` | Posição correta e recalculada | Required |
| Unit | `test_queued_cannot_send` | Bloqueio de transição | Required |
| Unit | `test_auto_promote_on_rejection` | Próxima vira draft | Required |
| Unit | `test_auto_promote_on_expiration` | Cron + promoção | Required |
| Unit | `test_auto_promote_on_cancellation` | Cancel manual + promoção | Required |
| Unit | `test_concurrent_creation_lock` | Race condition (FOR UPDATE) | Required |
| E2E (API) | `test_us8_s1_queued_flow.sh` | Fluxo completo de fila | Required |
| E2E (API) | `test_us8_s2_queue_endpoint.sh` | GET /queue | Required |

---

### User Story 9: Auto-cancelamento de concorrentes ao aceitar (Priority: P1)

**As the** system
**I want to** cancelar automaticamente propostas concorrentes quando uma é aceita
**So that** a propriedade fique exclusiva para a proposta vencedora

**Acceptance Criteria**:
- [ ] Given propriedade com 1 ativa em `negotiation` + 3 em `queued`, when ativa é aceita, then todas as 3 viram `cancelled` com `cancellation_reason="Superseded by accepted proposal PRPxxx"` e `superseded_by_id` apontando para a vencedora.
- [ ] Cada cancelamento gera entrada em `mail.thread` e dispara email para o agente respectivo (mail.template `proposal_superseded`).
- [ ] Caso edge (estado inconsistente com 2 ativas), when uma é aceita, then a outra também é cancelada com mesma regra.
- [ ] Aceite NÃO promove fila — propriedade fica "ocupada" até o aceite ser revogado (fora de escopo desta feature) ou contrato gerado.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_accept_supersedes_queued` | Cancela queued | Required |
| Unit | `test_supersede_sets_reason_and_link` | Campos preenchidos | Required |
| Unit | `test_supersede_notifies_agents` | Email/chatter | Required |
| Unit | `test_accept_does_not_promote_queue` | Slot permanece ocupado | Required |
| E2E (API) | `test_us9_s1_accept_cancels_queue.sh` | Fluxo completo | Required |

---

## Requirements

### Functional Requirements

**FR1: Modelo de Proposta**
- FR1.1: Vinculada a exatamente uma `real.estate.property` (FK obrigatória).
- FR1.2: Vinculada a um `res.partner` (criado/reutilizado por documento).
- FR1.3: Pode estar vinculada a um `real.estate.lead` (opcional).
- FR1.4: Vinculada a um `real.estate.agent` responsável.
- FR1.5: `proposal_code` único por empresa via `ir.sequence` (formato `PRP###`).
- FR1.6: `company_id` obrigatório (multi-tenancy).

**FR2: Workflow FSM (8 estados)**
- FR2.1: Estados: `draft`, `queued`, `sent`, `negotiation`, `accepted`, `rejected`, `expired`, `cancelled`.
- FR2.2: Status weight (precedência): `accepted` > `negotiation` > `sent` > `draft` > `queued` > `expired` > `rejected` > `cancelled`.
- FR2.3: Transições válidas:
  - **[criação]**: se property tem ativa → `queued`; senão → `draft`
  - `queued` → `draft` (auto-promoção FIFO) | `cancelled` (manual ou auto-supersede)
  - `draft` → `sent` | `cancelled`
  - `sent` → `negotiation` | `accepted` | `rejected` | `expired` | `cancelled`
  - `negotiation` → `sent` | `accepted` | `rejected` | `expired` | `cancelled`
  - **[terminais]**: `accepted`, `rejected`, `expired`, `cancelled`
- FR2.4: Toda transição registra evento em `mail.thread`.

**FR3: Regra de Slot Ativo (FIFO)**
- FR3.1: Por `property_id`, no máximo 1 proposta em `{draft, sent, negotiation, accepted}` simultaneamente.
- FR3.2: Propostas adicionais entram em `queued` ordenadas por `created_date ASC`.
- FR3.3: Quando ativa termina em `rejected`/`expired`/`cancelled` (não `accepted`), próxima `queued` (menor `created_date`) é promovida para `draft` automaticamente.
- FR3.4: Quando ativa vai para `accepted`, todas em `queued`/`draft`/`sent`/`negotiation` da mesma property são `cancelled` com `superseded_by_id` e `cancellation_reason`.
- FR3.5: Concorrência tratada com `SELECT FOR UPDATE` em `real.estate.property` durante criação.

**FR4: Contraproposta**
- FR4.1: `/counter` cria nova com `parent_proposal_id` apontando para a anterior.
- FR4.2: Original muda para `negotiation`, nova substitui logicamente como ativa (NÃO entra na fila).
- FR4.3: Computed `proposal_chain_ids` retorna cadeia recursiva.

**FR5: Integração com Lead**
- FR5.1: Adicionar `'proposal'` ao selection `source` em `real.estate.lead` (data migration).
- FR5.2: Auto-criar lead com `source='proposal'` se contato é novo; vincular existente caso contrário.
- FR5.3: Campo `proposal_ids` em `real.estate.lead` (One2many reverso).

**FR6: Anexos**
- FR6.1: `ir.attachment` com `res_model='real.estate.proposal'`.
- FR6.2: Whitelist mimetypes: PDF, JPEG, PNG, DOC/DOCX, XLS/XLSX.
- FR6.3: Limite por arquivo: 10MB.

**FR7: Expiração**
- FR7.1: Cron `cron_expire_proposals` diário às 02:00.
- FR7.2: Default `valid_until` = `sent_date + 7 dias` na ação `/send`.
- FR7.3: Expiração libera slot e promove próxima `queued`.

**FR8: Notificações (mail.template em pt_BR)**
- `proposal_sent` — proposta enviada ao cliente
- `proposal_counter` — contraproposta gerada
- `proposal_accepted` — aceite confirmado
- `proposal_rejected` — rejeição (com motivo)
- `proposal_expired` — expiração automática
- `proposal_superseded` — cancelamento por aceite de concorrente
- `proposal_promoted` — proposta promovida da fila

**FR9: Métricas**
- FR9.1: `/stats` retorna contagens por estado (8 buckets), isolado por `company_id`.
- FR9.2: Cache Redis TTL 60s.

---

### Data Model (per ADR-004, KB-09)

**Entity: `real.estate.proposal`**

- **Model Name**: `real.estate.proposal` (alinhado com `real.estate.lead/property/agent/lease/sale` em `quicksol_estate`)
- **Table Name**: `real_estate_proposal`
- **Inherits**: `mail.thread`, `mail.activity.mixin`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | PK |
| `proposal_code` | Char(20) | required, readonly, unique(company_id) | Código tipo `PRP001` |
| `name` | Char | computed | Display name |
| `property_id` | Many2one(`real.estate.property`) | required, ondelete=restrict, indexed | Propriedade |
| `partner_id` | Many2one(`res.partner`) | required, ondelete=restrict, indexed | Cliente |
| `lead_id` | Many2one(`real.estate.lead`) | optional, ondelete=set null | Lead origem |
| `agent_id` | Many2one(`real.estate.agent`) | required, ondelete=restrict, indexed | Agente responsável |
| `proposal_type` | Selection | required | `sale` \| `lease` |
| `proposal_value` | Monetary | required, > 0 | Valor |
| `currency_id` | Many2one(`res.currency`) | required, default BRL | Moeda |
| `state` | Selection (8 valores) | required, default `draft`, indexed | FSM |
| `description` | Text | optional | Notas |
| `rejection_reason` | Text | required if state=rejected | Motivo de rejeição |
| `cancellation_reason` | Text | required if state=cancelled | Motivo de cancelamento |
| `valid_until` | Date | optional | Validade |
| `sent_date` | Datetime | readonly | Set on /send |
| `accepted_date` | Datetime | readonly | Set on /accept |
| `rejected_date` | Datetime | readonly | Set on /reject |
| `parent_proposal_id` | Many2one(self) | optional, ondelete=set null | Pai (contraproposta) |
| `child_proposal_ids` | One2many(self, parent) | computed | Filhas |
| `proposal_chain_ids` | Many2many(self) | computed | Cadeia recursiva |
| `superseded_by_id` | Many2one(self) | optional | Aceita que cancelou esta |
| `queue_position` | Integer | computed, stored | 0=ativa, ≥1=posição na fila, NULL=terminal |
| `is_active_proposal` | Boolean | computed, stored | True se é a ativa da property |
| `attachment_ids` | One2many(`ir.attachment`) | computed | Anexos |
| `documents_count` | Integer | computed, stored | # anexos |
| `has_competing_proposals` | Boolean | computed | Outras na mesma property |
| `company_id` | Many2one(`res.company`) | required, default env.company, indexed | Multi-tenancy |
| `active` | Boolean | default True | Soft delete (ADR-015) |
| `create_date`/`write_date`/`create_uid`/`write_uid` | — | auto | Auditoria |

**SQL Constraints**:
```python
_sql_constraints = [
    ('proposal_code_company_uniq',
     'unique(proposal_code, company_id)',
     'Proposal code must be unique per company.'),
    ('proposal_value_positive',
     'CHECK(proposal_value > 0)',
     'Proposal value must be greater than zero.'),
]
```

**Partial Unique Index** (via migration SQL — `_sql_constraints` não suporta WHERE):
```sql
CREATE UNIQUE INDEX real_estate_proposal_one_active_per_property
ON real_estate_proposal (property_id)
WHERE state IN ('draft','sent','negotiation','accepted') AND active = true;
```

**Python Constraints**:
```python
@api.constrains('property_id', 'company_id')
def _check_property_same_company(self): ...

@api.constrains('agent_id', 'property_id')
def _check_agent_assigned_to_property(self): ...  # ADR-014

@api.constrains('state', 'rejection_reason')
def _check_rejection_reason(self): ...

@api.constrains('state', 'cancellation_reason')
def _check_cancellation_reason(self): ...

@api.constrains('property_id', 'state', 'active')
def _check_one_active_per_property(self):
    # Defesa em profundidade (além do unique index)
    ...

@api.constrains('parent_proposal_id', 'property_id', 'partner_id')
def _check_counter_consistency(self): ...
```

**Indexes**: `state`, `company_id`, `agent_id`, `property_id`, `partner_id`, `(state, company_id)` composto, `(property_id, state, created_date)` para fila FIFO.

**Record Rules** (ADR-008, ADR-019):
```xml
<record id="rule_proposal_company" model="ir.rule">
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>

<record id="rule_proposal_agent_own" model="ir.rule">
    <field name="domain_force">[('agent_id.user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_estate_agent'))]"/>
</record>

<record id="rule_proposal_manager_all" model="ir.rule">
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_estate_manager'))]"/>
</record>
```

**Lead Schema Update** (`real.estate.lead`):
- Adicionar `'proposal'` ao selection `source` (data migration).
- Campo novo `proposal_ids = One2many('real.estate.proposal', 'lead_id')`.

---

### API Endpoints (per ADR-007, ADR-009, ADR-011)

Todos endpoints autenticados usam **triple decorators**: `@require_jwt` + `@require_session` + `@require_company`.

#### POST /api/v1/proposals (Create)

| Attribute | Value |
|-----------|-------|
| Method | POST |
| Auth | triple decorators |
| Authorization | Owner, Manager, Agent (próprias) |

**Request Body** (validado per ADR-018):
```json
{
  "property_id": 12,
  "client_name": "Ana Silva",
  "client_document": "12345678901",
  "client_email": "ana@example.com",
  "client_phone": "+5511999998888",
  "agent_id": 3,
  "proposal_type": "sale",
  "proposal_value": 550000.00,
  "valid_until": "2026-05-15",
  "description": "Cliente quer negociar prazo",
  "lead_id": null
}
```

**Response 201**:
```json
{
  "id": 1,
  "proposal_code": "PRP001",
  "state": "draft",
  "queue_position": 0,
  "is_active_proposal": true,
  "property": {"id": 12, "name": "Apt. Downtown"},
  "client": {"id": 45, "name": "Ana Silva", "document": "12345678901"},
  "agent": {"id": 3, "name": "João P."},
  "lead_id": 78,
  "proposal_type": "sale",
  "proposal_value": 550000.00,
  "currency": "BRL",
  "valid_until": "2026-05-15",
  "documents_count": 0,
  "has_competing_proposals": false,
  "created_at": "2026-04-27T10:00:00Z",
  "links": [
    {"rel": "self", "href": "/api/v1/proposals/1", "method": "GET"},
    {"rel": "update", "href": "/api/v1/proposals/1", "method": "PUT"},
    {"rel": "send", "href": "/api/v1/proposals/1/send", "method": "POST"},
    {"rel": "cancel", "href": "/api/v1/proposals/1", "method": "DELETE"},
    {"rel": "attachments", "href": "/api/v1/proposals/1/attachments", "method": "POST"},
    {"rel": "queue", "href": "/api/v1/proposals/1/queue", "method": "GET"},
    {"rel": "collection", "href": "/api/v1/proposals", "method": "GET"}
  ]
}
```

**Quando `state='queued'`**: links HATEOAS NÃO incluem `rel: "send"`.

#### GET /api/v1/proposals (List)
- Query params: `state`, `agent_id`, `property_id`, `partner_id`, `search`, `date_from`, `date_to`, `page`, `page_size` (max 100).
- Resposta inclui `_meta: {total, page, page_size, pages}` + `_links: {next, prev, first, last}`.

#### GET /api/v1/proposals/{id} (Detail)
- Inclui `proposal_chain`, `attachments[]`, `queue_position`, `is_active_proposal`.

#### PUT /api/v1/proposals/{id} (Update)
- Permitido em `draft`, `queued`, `sent`, `negotiation`. HTTP 409 caso contrário.
- Campos editáveis: `proposal_value`, `description`, `valid_until`, `agent_id` (manager/owner).

#### DELETE /api/v1/proposals/{id} (Soft Delete / Cancel)
- Per ADR-015: marca `active=False` + `state=cancelled` + `cancellation_reason`. Apenas Owner/Manager.
- Se era ativa, dispara promoção da próxima `queued`.

#### POST /api/v1/proposals/{id}/send
- `draft` → `sent`. Seta `sent_date`, default `valid_until = sent_date + 7d` se nulo. Email disparado.
- HTTP 422 se `state='queued'`.

#### POST /api/v1/proposals/{id}/accept
- `sent`/`negotiation` → `accepted`. Emite `proposal.accepted` (ADR-020). HATEOAS inclui `rel: "create-contract"`.
- Auto-cancela todas as outras (`queued`/`draft`/`sent`/`negotiation`) da mesma property com `superseded_by_id`.

#### POST /api/v1/proposals/{id}/reject
- Body: `{"rejection_reason": "..."}` (obrigatório). → `rejected`.
- Promove próxima `queued` da property.

#### POST /api/v1/proposals/{id}/counter
- Body: `{"proposal_value": ..., "description": "...", "valid_until": "..."}`.
- Cria nova com `parent_proposal_id`, original → `negotiation`. Não entra na fila.

#### GET /api/v1/proposals/{id}/queue
```json
{
  "property_id": 12,
  "active_proposal": {"id": 5, "proposal_code": "PRP005", "state": "negotiation", "agent": {...}},
  "queue": [
    {"id": 8, "proposal_code": "PRP008", "queue_position": 1, "agent": {...}, "proposal_value": 540000},
    {"id": 11, "proposal_code": "PRP011", "queue_position": 2, "agent": {...}, "proposal_value": 555000}
  ]
}
```

#### GET /api/v1/proposals/stats
```json
{
  "total": 9,
  "by_state": {
    "draft": 1, "queued": 3, "sent": 2, "negotiation": 1,
    "accepted": 1, "rejected": 1, "expired": 0, "cancelled": 0
  }
}
```

#### POST /api/v1/proposals/{id}/attachments
- Multipart: `file`, `description`. Retorna metadata + `download_url`.

**Error Responses**:
| Code | Condition |
|------|-----------|
| 400 | Schema validation (ADR-018) |
| 401 | JWT inválido (ADR-011) |
| 403 | RBAC (ADR-019) ou agent não atribuído |
| 404 | Recurso não encontrado / outra empresa (ADR-008) |
| 409 | Estado terminal não permite mutação |
| 413 | Anexo > 10MB |
| 422 | Transição de estado inválida (ex: send em queued) |

---

### Non-Functional Requirements

**NFR1: Security** (ADR-008, ADR-011, ADR-017, ADR-019)
- Triple auth em todos endpoints
- Multi-tenant via `company_id` + record rules
- Session fingerprint (ADR-017)

**NFR2: Performance**
- API < 200ms para detalhes
- Lista paginada (max 100/pg)
- Indexes compostos (especialmente `(property_id, state, created_date)` para fila)
- Cache Redis para `/stats` (TTL 60s)

**NFR3: Quality** (ADR-022)
- black, isort, flake8, pylint ≥ 8.0
- 100% cobertura em validações
- Zero erros JS no console

**NFR4: Data Integrity** (KB-09)
- 3NF, FKs com `ondelete` apropriado
- Soft delete (ADR-015)
- Partial unique index para slot ativo

**NFR5: Frontend** (KB-10)
- Views Odoo 18.0: `<list>`, `optional`, sem `attrs`/`column_invisible` com expressão
- Cypress E2E para list/form/kanban

**NFR6: Concorrência** (proposed ADR-027)
- `SELECT FOR UPDATE` em `real.estate.property` durante criação para evitar race condition na decisão `draft` vs `queued`.
- Re-verificação do estado da fila dentro do lock.
- Documentar como pattern reutilizável.

**NFR7: Auditoria/Observabilidade**
- `mail.thread` em todas transições
- OpenTelemetry traces nos endpoints (ADR-025)

---

## Technical Constraints

| Source | Requirement |
|--------|-------------|
| ADR-001 | Estrutura flat, views Odoo 18.0 |
| ADR-003 | 100% cobertura validações + E2E |
| ADR-004 | Naming `real.estate.proposal` (consistência módulo) |
| ADR-007 | HATEOAS em todas respostas |
| ADR-008 | Isolamento `company_id` |
| ADR-011 | Triple decorators |
| ADR-014 | Agent atribuído à propriedade (M2M) |
| ADR-015 | Soft delete |
| ADR-016 | Postman collection |
| ADR-017 | Fingerprint validation |
| ADR-018 | Schema validation request body |
| ADR-019 | RBAC matrix |
| ADR-020 | Observer event `proposal.accepted` |
| ADR-022 | Linters obrigatórios |
| ADR-025 | OpenTelemetry traces |
| **ADR-027 (proposed)** | **Pessimistic Locking for Resource Queues** |
| KB-10 | Views frontend Odoo 18.0 |

---

## Authorization Matrix (ADR-019)

| Operação | Owner | Manager | Agent | Receptionist | Prospector |
|----------|:-----:|:-------:|:-----:|:------------:|:----------:|
| Criar proposta | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Listar todas (empresa) | ✅ | ✅ | ❌ | ✅ (read-only) | ❌ |
| Listar próprias | — | — | ✅ | — | — |
| Atualizar (draft/queued/sent/negotiation) | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Enviar (`/send`) | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Aceitar (`/accept`) | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Rejeitar (`/reject`) | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Contraproposta (`/counter`) | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Cancelar/Excluir (soft) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Anexar documentos | ✅ | ✅ | ✅ (próprias) | ❌ | ❌ |
| Ver fila (`/queue`) | ✅ | ✅ | ✅ | ✅ (read-only) | ❌ |

---

## Success Criteria

### Backend
- [ ] 12 endpoints REST implementados com triple auth
- [ ] FSM 8 estados com transições validadas
- [ ] Slot ativo único por property (partial unique index + constraint Python)
- [ ] FIFO queue com auto-promoção em rejected/expired/cancelled
- [ ] Auto-supersede em accepted (com `superseded_by_id`)
- [ ] Pessimistic locking para race condition
- [ ] Cron de expiração funcionando
- [ ] Auto-criação/vínculo de lead com `source='proposal'`
- [ ] 100% cobertura unit em validações
- [ ] E2E API tests para US1-US9
- [ ] Multi-company isolation testado
- [ ] Pylint ≥ 8.0, linters OK

### Frontend (Odoo Portal Interno)
- [ ] List view com filtros por estado, busca, indicador de slot ativo
- [ ] Form view com chatter (mail.thread) e proposal_chain visual
- [ ] Kanban view (colunas por estado)
- [ ] Search view com filtros pré-definidos
- [ ] Cypress E2E para todas views
- [ ] Zero JS console errors

### Documentation
- [ ] OpenAPI/Swagger (ADR-005) — pós-dev
- [ ] Postman collection (ADR-016) — pós-dev
- [ ] Constitution update (v1.4.0)
- [ ] **ADR-027 (proposed) Pessimistic Locking for Resource Queues** — criar antes da implementação

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| **FIFO Queue Pattern** | Recurso compartilhado com 1 ativo + fila FIFO ordenada por `created_date` | **Concurrency Patterns (nova seção)** | **High** |
| **Auto-supersede on terminal state** | Aceite cancela concorrentes com rastreabilidade (`superseded_by_id`) | Domain Patterns | High |
| **Pessimistic Locking** | `SELECT FOR UPDATE` para evitar race em fila | **Concurrency Patterns** | **High** — sugere ADR-027 |
| FSM com 8 estados | Workflow com `queued` adicional + 4 terminais | Domain Patterns | High |
| Auto-criação de Lead com origem secundária | Entidade gera entidade upstream com `source` tracking | Integration Patterns | High |
| Cron de expiração com promoção de fila | Job para transição automática + side-effect na fila | Async Patterns | Medium |
| HATEOAS condicional por estado/role | Links variam conforme FSM e perfil | API Design | Medium |
| Partial Unique Index | Constraint condicional via PostgreSQL `WHERE` | Database Patterns | Medium |

### New Entities/Relationships

| Entity | Related To | Relationship |
|--------|-----------|--------------|
| `real.estate.proposal` | `real.estate.property` | N:1 (required, com slot ativo único) |
| `real.estate.proposal` | `res.partner` | N:1 (required) |
| `real.estate.proposal` | `real.estate.lead` | N:1 (optional, bidirecional) |
| `real.estate.proposal` | `real.estate.agent` | N:1 (required, validated via M2M ADR-014) |
| `real.estate.proposal` | `real.estate.proposal` | N:1 self-ref (`parent_proposal_id`) |
| `real.estate.proposal` | `real.estate.proposal` | N:1 self-ref (`superseded_by_id`) |
| `real.estate.proposal` | `ir.attachment` | 1:N |

### Constitution Update Recommendation

- **Update Required**: **Yes**
- **Suggested Version Bump**: **MINOR** (1.3.0 → 1.4.0)
- **Sections to Update**:
  - [x] Domain Patterns (FSM 8 estados + auto-supersede)
  - [x] **Concurrency Patterns (NOVA seção)** — FIFO queue + pessimistic locking
  - [x] Integration Patterns (auto-link entidades por documento)
  - [x] Reference Implementations (Feature 012)
  - [x] Referência ao novo ADR-027 (a criar)

---

## Assumptions & Dependencies

**Assumptions**:
- `real.estate.lead` aceita extensão do campo `source` via inheritance.
- Sequência `ir.sequence` por empresa (multi-company sequence).
- Frontend headless cuida de UI externa; portal Odoo é para uso interno.
- Aceite de proposta é decisão final — não há fluxo de "desfazer aceite" nesta feature (escopo futuro).

**Dependencies**:
- Módulos: `quicksol_estate` (property, lead, agent), `thedevkitchen_apigateway` (auth), `mail` (thread/template).
- DB: PostgreSQL 14+ (partial unique index, `SELECT FOR UPDATE`), Redis 7+ (cache `/stats`).
- ADR-027 (proposed) deve ser criado antes da implementação do lock pessimista.

---

## Implementation Phases

### Phase 1: Foundation
- Criar ADR-027 Pessimistic Locking for Resource Queues
- Modelo `real.estate.proposal` + constraints + sequence
- Partial unique index via migration
- Extensão de `real.estate.lead.source` (selection + migration)
- Record rules + grupos de segurança
- Unit tests de validações e FSM

### Phase 2: Queue & Concurrency
- Lógica de criação com `SELECT FOR UPDATE`
- Auto-promoção FIFO (override de `write` e cron)
- Auto-supersede em `/accept`
- Computed `queue_position`, `is_active_proposal`
- Unit tests de concorrência

### Phase 3: API Layer
- Controllers REST (12 endpoints) com triple auth
- Schemas de validação (ADR-018)
- HATEOAS responses condicionais por estado
- Observer event `proposal.accepted` (ADR-020)

### Phase 4: Notifications & Cron
- 7 mail.template (pt_BR)
- Cron `cron_expire_proposals`
- Integração `mail.thread`

### Phase 5: Frontend (Views Odoo)
- List, form, kanban, search views (KB-10 compliant)
- Menus e ações
- Cypress E2E

### Phase 6: Testing & Quality
- Integration tests (US1–US9)
- Multi-tenancy isolation
- Race condition tests (concurrent creation)
- Linters (Python + XML)

### Phase 7: Post-Development Artifacts
- OpenAPI 3.0 (ADR-005) → `docs/openapi/proposals.yaml`
- Postman collection (ADR-016) → `docs/postman/proposals.postman_collection.json`
- Constitution update (v1.4.0)

---

## Validation Checklist

### Backend
- [x] ADRs referenciados (001, 003, 004, 007, 008, 011, 014, 015, 017, 018, 019, 020, 022, 025, 027-proposed)
- [x] Multi-tenancy especificada
- [x] Triple decorators em todos endpoints autenticados
- [x] Test pyramid completo (unit + integration + E2E + Cypress)
- [x] HATEOAS responses condicionais
- [x] Schema validation
- [x] Soft delete
- [x] Observer pattern para evento de aceite
- [x] Pessimistic locking documentado

### Frontend
- [x] Views Odoo 18.0 (KB-10)
- [x] Sem `attrs`, `<list>` em vez de `<tree>`, `optional` para column visibility
- [x] Cypress E2E
- [x] Acceptance criteria com console error check
