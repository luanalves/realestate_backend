# Feature Specification: Rental Credit Check (Análise de Ficha)

**Feature Branch**: `014-rental-credit-check`
**Created**: 2026-04-28
**Status**: Draft
**ADR References**: ADR-001, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-011, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-022

---

## Executive Summary

Para propostas de **locação**, após o envio e possível negociação de valor, é necessário realizar uma **análise de crédito (ficha)** do locatário por uma seguradora (ex.: Porto Seguro, Tokio Marine). Esta feature adiciona o estado `credit_check_pending` ao fluxo de propostas de locação, introduz a entidade `CreditCheck` que registra o resultado (aprovado/reprovado + seguradora + motivo), e expõe o **histórico de fichas do cliente** para que agentes possam consultar análises anteriores quando o mesmo cliente retorna meses depois. Integra-se ao ciclo de vida da spec 013 sem alterá-lo para propostas de venda.

---

## Clarifications

### Session 2026-04-28 (áudios WhatsApp 13:32 e 13:34)

- Q: Qual é o tipo de solução desta feature? → A: Ambos — API + Odoo UI.
- Q: Esta feature cobre quais fluxos dos áudios? → A: Análise de ficha / crédito do locatário (locação) + Histórico de ficha do cliente. O fluxo de decisão do proprietário entre propostas concorrentes ficou **fora do escopo** desta spec (pode virar spec própria).
- Q: Como esta spec se relaciona com a spec 013? → A: Extensão da 013 — adiciona regras sobre ela, depende do modelo de propostas.
- Q: Quem são os atores da análise de ficha e como o resultado entra no sistema? → A: Agente registra o resultado manualmente (aprovado/reprovado + motivo). Sem integração automática com API de seguradora nesta versão.
- Q: A análise de ficha adiciona um novo estado? → A: Sim — novo estado explícito `credit_check_pending`; proposta fica nele até o resultado ser registrado.
- Q: Como modelar a análise de ficha? → A: Entidade `CreditCheck` separada (ligada à proposta e ao cliente), para suportar histórico completo.
- Q: Uma proposta pode ter mais de uma análise? → A: Uma por vez; nova análise só pode ser aberta se a anterior foi reprovada ou cancelada.
- Q: Quais perfis podem registrar e visualizar as análises? → A: Owner + Manager registram e veem tudo; Agent registra e vê apenas as suas.

---

## User Scenarios & Testing

### User Story 1 — Agente inicia análise de ficha (P1) 🎯 MVP

**As an** Agent (ou Manager/Owner)
**I want to** iniciar a análise de ficha do locatário em uma proposta de locação
**So that** a seguradora possa avaliar o crédito antes do aceite formal

**Acceptance Criteria**:
- [ ] Given uma proposta de locação em estado `sent` ou `negotiation`, when o agente chama `POST /api/v1/proposals/{id}/credit-checks` com `insurer_name`, then a proposta muda para `credit_check_pending`, um registro `CreditCheck` com `result=pending` é criado, e o timeline da proposta registra o evento.
- [ ] Given uma proposta de **venda**, when a mesma chamada é tentada, then HTTP 422 — análise de ficha não se aplica a propostas de venda.
- [ ] Given uma proposta de locação em estado `credit_check_pending` (análise já ativa), when tentativa de abrir outra análise, then HTTP 409 — uma análise por vez.
- [ ] Given uma proposta em estado terminal, when qualquer operação de ficha é tentada, then HTTP 409.
- [ ] Given agente tentando iniciar ficha em proposta de outro agente, when `POST`, then HTTP 403.
- [ ] Given proposta da Empresa A, when agente da Empresa B tenta acessar, then HTTP 404 (ADR-008).

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_credit_check_only_for_lease` | Rejeita para tipo `sale` | ⚠️ Required |
| Unit | `test_one_active_check_at_a_time` | Bloqueia segunda análise simultânea | ⚠️ Required |
| Unit | `test_state_transitions_to_credit_check_pending` | FSM válido | ⚠️ Required |
| Unit | `test_terminal_state_blocks_credit_check` | Estado terminal bloqueado | ⚠️ Required |
| E2E (API) | `test_us1_s1_agent_initiates_credit_check.sh` | Fluxo completo de abertura | ⚠️ Required |
| E2E (API) | `test_us1_s2_sale_proposal_blocked.sh` | Tipo errado bloqueado | ⚠️ Required |
| E2E (API) | `test_us1_s3_multitenancy_isolation.sh` | Isolamento por empresa | ⚠️ Required |
| E2E (UI) | `cypress: credit_check_tab_loads.cy.js` | Aba de ficha carrega sem erros | ⚠️ Required |

---

### User Story 2 — Agente registra resultado (aprovado ou reprovado) (P1) 🎯 MVP

**As an** Agent (ou Manager/Owner)
**I want to** registrar o resultado da análise de ficha (aprovado ou reprovado)
**So that** a proposta avance para aceite ou libere a propriedade para o próximo da fila

**Acceptance Criteria**:
- [ ] Given um `CreditCheck` em estado `pending`, when o agente chama `PATCH /api/v1/proposals/{id}/credit-checks/{check_id}` com `result=approved`, then o check muda para `approved`, a proposta muda para `accepted`, `accepted_date` é registrado, o evento `proposal.accepted` é emitido, e o timeline registra o evento.
- [ ] Given `result=rejected`, when o agente envia a chamada **sem** `rejection_reason`, then HTTP 400.
- [ ] Given `result=rejected` com `rejection_reason`, when registrado, then o check muda para `rejected`, a proposta muda para `rejected`, e a próxima proposta na fila da propriedade é promovida automaticamente (mesmo comportamento da rejeição regular da spec 013).
- [ ] Given proposta rejeitada por ficha, when a proposta promovida é de locação, then ela **não** inicia análise de ficha automaticamente — o agente responsável inicia quando estiver pronto.
- [ ] Given check aprovado/rejeitado, when tentativa de alterar resultado, then HTTP 409 — resultado é imutável.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_approval_transitions_proposal_to_accepted` | FSM: credit_check_pending→accepted | ⚠️ Required |
| Unit | `test_rejection_requires_reason` | reason obrigatório | ⚠️ Required |
| Unit | `test_rejection_promotes_next_queued` | Fila promovida após reprovação | ⚠️ Required |
| Unit | `test_check_result_is_immutable` | Resultado não pode ser alterado | ⚠️ Required |
| E2E (API) | `test_us2_s1_approve_credit_check.sh` | Aprovação → accepted | ⚠️ Required |
| E2E (API) | `test_us2_s2_reject_credit_check.sh` | Reprovação + promoção de fila | ⚠️ Required |
| E2E (UI) | `cypress: register_credit_check_result.cy.js` | Formulário resultado sem erros | ⚠️ Required |

---

### User Story 3 — Segunda tentativa com outra seguradora após reprovação (P2)

**As an** Agent
**I want to** abrir uma nova análise de ficha com uma seguradora diferente, após a anterior ter sido reprovada
**So that** o cliente ainda tenha chance de fechar o contrato sem perder sua posição no pipeline

**Acceptance Criteria**:
- [ ] Given proposta de locação cujo último `CreditCheck` tem `result=rejected`, when agente chama `POST /api/v1/proposals/{id}/credit-checks` com nova `insurer_name`, then a proposta volta para `credit_check_pending`, um novo registro `CreditCheck` é criado, e o histórico preserva os checks anteriores.
- [ ] Given agente abrindo segunda análise em proposta ainda com check `pending`, then HTTP 409 — aguarda resultado da análise em andamento.
- [ ] Given listagem de checks da proposta, then todos os checks (pending, approved, rejected) aparecem em ordem cronológica.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_new_check_allowed_after_rejection` | Re-abertura após rejeição | ⚠️ Required |
| Unit | `test_history_preserved_across_checks` | Histórico completo mantido | ⚠️ Required |
| E2E (API) | `test_us3_s1_retry_with_different_insurer.sh` | Segunda tentativa + histórico | ⚠️ Required |

---

### User Story 4 — Histórico de fichas do cliente (P2)

**As a** Manager ou Agent
**I want to** consultar o histórico de análises de ficha de um cliente específico
**So that** eu saiba de antemão se esse cliente já teve fichas reprovadas no passado

**Acceptance Criteria**:
- [ ] Given um cliente com fichas em múltiplas propostas, when consultado `GET /api/v1/clients/{partner_id}/credit-history`, then retorna todos os checks do cliente, paginados (max 100), incluindo: proposta, seguradora, resultado, data, motivo de reprovação (se houver).
- [ ] Given cliente da Empresa B consultado por usuário da Empresa A, then HTTP 404.
- [ ] Given histórico vazio, then retorna array vazio com HTTP 200.
- [ ] Given a criação de uma nova proposta para o cliente, when a proposta é consultada, then o campo `credit_history_summary` mostra contagem de aprovações e reprovações anteriores desse cliente.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_credit_history_scoped_by_company` | Isolamento multi-tenant | ⚠️ Required |
| Unit | `test_history_summary_counts` | Contadores corretos | ⚠️ Required |
| E2E (API) | `test_us4_s1_client_credit_history.sh` | Histórico paginado | ⚠️ Required |
| E2E (UI) | `cypress: client_credit_history_tab.cy.js` | Aba histórico sem erros | ⚠️ Required |

---

### User Story 5 — Visualização no Odoo UI (P1)

**As a** Manager ou Agent (Odoo)
**I want to** ver e registrar análises de ficha diretamente no formulário da proposta
**So that** não precise usar a API diretamente para o fluxo operacional diário

**Acceptance Criteria**:
- [ ] Given uma proposta de locação aberta no Odoo, when o usuário clica na aba "Análise de Ficha", then a aba carrega sem erros e exibe o histórico de checks.
- [ ] Given proposta em `sent` ou `negotiation`, when aba de ficha está aberta, then o botão "Iniciar Análise" está visível e habilitado.
- [ ] Given proposta em `credit_check_pending`, when aba de ficha aberta, then formulário de registro de resultado (aprovado/reprovado + seguradora + motivo) está disponível.
- [ ] Given proposta de venda, when aba de ficha aberta, then uma mensagem informativa indica que análise de ficha é exclusiva para locação.
- [ ] Browser DevTools console: ZERO erros JavaScript em qualquer interação.

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (UI) | `cypress: credit_check_tab_lease_proposal.cy.js` | Fluxo completo na UI | ⚠️ Required |
| E2E (UI) | `cypress: credit_check_disabled_for_sale.cy.js` | Desabilitado para venda | ⚠️ Required |

---

### Edge Cases

- **Análise em proposta expirada**: se uma proposta expira enquanto o check está `pending`, o check deve ser marcado como `cancelled` automaticamente com razão "Proposta expirada".
- **Análise em proposta cancelada**: se a proposta for cancelada manualmente enquanto check `pending`, o check é marcado `cancelled`.
- **Aprovação não promove fila**: a aprovação finaliza a proposta como `accepted` — os concorrentes são cancelados (comportamento da spec 013, FR-014).
- **Re-abertura após aprovação**: não é permitida — proposta já está em estado terminal `accepted`.
- **Agente sem ficha na sua proposta**: agente pode visualizar checks criados por managers na sua proposta.
- **Seguradora com nome livre**: o campo `insurer_name` é texto livre (não uma lista fixa) para suportar qualquer seguradora.
- **Reprovação + fila vazia**: se a ficha é reprovada e não há propostas na fila, a propriedade fica livre normalmente, sem promoção.
- **Proposta rejeitada por ficha reentra na fila?**: não — a proposta em si vai para `rejected` (terminal). Se o agente quiser tentar novamente, deve criar uma nova proposta (nova entrada na fila).

---

## Requirements

### Functional Requirements

#### Estado e Transições

- **FR-001**: O sistema DEVE adicionar o estado `credit_check_pending` ao conjunto de estados válidos de uma proposta, aplicável **exclusivamente** a propostas de tipo `lease`.
- **FR-002**: O sistema DEVE permitir a transição `sent → credit_check_pending` e `negotiation → credit_check_pending` somente para propostas de locação.
- **FR-003**: O sistema DEVE permitir a transição `credit_check_pending → accepted` quando o resultado da análise for aprovado.
- **FR-004**: O sistema DEVE permitir a transição `credit_check_pending → rejected` quando o resultado for reprovado, com `rejection_reason` obrigatório.
- **FR-005**: O sistema DEVE bloquear transições diretas de `credit_check_pending` para qualquer outro estado que não seja `accepted`, `rejected`, ou `cancelled`.
- **FR-006**: O sistema DEVE rejeitar com HTTP 422 a tentativa de iniciar análise de ficha em proposta de tipo `sale`.
- **FR-007**: O sistema DEVE, quando uma proposta em `credit_check_pending` for expirada pelo cron diário ou cancelada manualmente, marcar o `CreditCheck` ativo como `cancelled` automaticamente.

#### Entidade CreditCheck

- **FR-008**: O sistema DEVE criar um registro `CreditCheck` a cada solicitação de análise, contendo: `proposal_id`, `partner_id` (cliente), `company_id`, `insurer_name`, `result` (pending/approved/rejected/cancelled), `requested_date`, `check_date` (data do resultado), `rejection_reason`, e campos de auditoria.
- **FR-009**: O sistema DEVE tratar o resultado de um `CreditCheck` como imutável após ser definido como `approved`, `rejected`, ou `cancelled`.
- **FR-010**: O sistema DEVE permitir no máximo **uma análise ativa** (`result=pending`) por proposta ao mesmo tempo.
- **FR-011**: O sistema DEVE permitir a abertura de nova análise somente quando o `CreditCheck` mais recente da proposta tiver `result=rejected` ou `cancelled`.
- **FR-012**: O sistema DEVE preservar todo o histórico de checks da proposta mesmo após a abertura de novas análises.

#### Histórico do Cliente

- **FR-013**: O sistema DEVE expor um endpoint de histórico de fichas por cliente retornando todos os `CreditCheck` associados a esse `partner_id` dentro da empresa, paginados (máx. 100).
- **FR-014**: O sistema DEVE incluir, na resposta de detalhe de uma proposta, um campo `credit_history_summary` com contadores de aprovações e reprovações históricas do cliente.
- **FR-015**: O sistema DEVE isolar o histórico de fichas por `company_id` — nenhum cross-company leakage.

#### Integração com Fila (spec 013)

- **FR-016**: O sistema DEVE, quando o resultado de um `CreditCheck` for `rejected`, executar o mesmo mecanismo de promoção de fila da spec 013 (FR-011): a próxima proposta `queued` mais antiga é promovida para `draft`, e o agente responsável notificado.
- **FR-017**: O sistema DEVE, quando o resultado for `approved` e a proposta transitar para `accepted`, executar o mesmo mecanismo de cancelamento de concorrentes da spec 013 (FR-014): todas as propostas não-terminais na mesma propriedade são canceladas com razão "Superseded by accepted proposal *PRPxxx*".

#### Notificações

- **FR-018**: O sistema DEVE enviar notificação (email + timeline) ao agente responsável quando uma análise de ficha é aprovada ou reprovada.
- **FR-019**: O sistema DEVE desacoplar o envio de email da transição de estado (padrão Outbox assíncrono, conforme spec 013 FR-041a).

#### Autorização

- **FR-020**: O sistema DEVE aplicar a seguinte matriz de autorização para operações de crédito:

  | Ação | Owner | Manager | Agent | Receptionist | Prospector |
  |---|---|---|---|---|---|
  | Iniciar análise | Sim | Sim | Sim (proposta própria) | Não | Não |
  | Registrar resultado | Sim | Sim | Sim (proposta própria) | Não | Não |
  | Ver checks da proposta | Sim | Sim | Sim (proposta própria) | Leitura | Não |
  | Ver histórico do cliente | Sim | Sim | Sim (clientes das suas propostas) | Leitura | Não |

- **FR-021**: O sistema DEVE isolar todos os dados por `company_id`, retornando HTTP 404 para recursos de outra empresa (sem informação de existência).

#### Validação

- **FR-022**: O sistema DEVE validar `insurer_name` como campo obrigatório ao iniciar análise.
- **FR-023**: O sistema DEVE validar `rejection_reason` como obrigatório ao registrar resultado `rejected`.
- **FR-024**: O sistema DEVE validar que `check_date` não é uma data futura.
- **FR-025**: O sistema DEVE retornar erros de validação estruturados (ADR-018).

#### Odoo UI

- **FR-026**: O sistema DEVE exibir uma aba "Análise de Ficha" no formulário de proposta, visível para todos os perfis autorizados.
- **FR-027**: O sistema DEVE ocultar ou desabilitar controles de criação/edição de ficha para propostas de venda, exibindo mensagem informativa.
- **FR-028**: O sistema DEVE exibir o histórico de checks do cliente na aba de análise do formulário de proposta.
- **FR-029**: O sistema DEVE usar `<list>` (não `<tree>`), sem `attrs`, sem `column_invisible` com expressões Python (ADR-001, KB-10).

---

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

**Entity: `thedevkitchen.estate.credit.check`**
- **Model Name**: `thedevkitchen.estate.credit.check`
- **Table Name**: `thedevkitchen_estate_credit_check` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Chave primária |
| `name` | Char | computed | Ex: `CHK/2026/001` |
| `proposal_id` | Many2one | required, FK→proposal | Proposta associada |
| `partner_id` | Many2one | required, FK→res.partner | Cliente analisado |
| `company_id` | Many2one | required, FK→res.company | Multi-tenancy (ADR-008) |
| `insurer_name` | Char(100) | required | Nome da seguradora (texto livre) |
| `result` | Selection | required | `pending`, `approved`, `rejected`, `cancelled` |
| `requested_date` | Date | required | Data de solicitação |
| `check_date` | Date | optional | Data do resultado |
| `rejection_reason` | Text | required if result=rejected | Motivo da reprovação |
| `notes` | Text | optional | Observações livres |
| `active` | Boolean | default=True | Soft delete (ADR-015) |
| `create_uid`, `write_uid` | Many2one | auto | Auditoria |
| `create_date`, `write_date` | Datetime | auto | Auditoria |

**SQL Constraints**:
```python
_sql_constraints = [
    ('one_pending_per_proposal',
     "EXCLUDE USING gist (proposal_id WITH =) WHERE (result = 'pending')",
     'Only one pending credit check is allowed per proposal at a time.'),
]
```

**Python Constraints**:
```python
@api.constrains('result', 'rejection_reason')
def _check_rejection_reason_required(self):
    for rec in self:
        if rec.result == 'rejected' and not rec.rejection_reason:
            raise ValidationError("Rejection reason is required when result is 'rejected'.")

@api.constrains('check_date')
def _check_date_not_future(self):
    for rec in self:
        if rec.check_date and rec.check_date > fields.Date.today():
            raise ValidationError("Check date cannot be in the future.")
```

**Record Rules** (ADR-019):
```xml
<record id="rule_credit_check_company" model="ir.rule">
    <field name="name">Credit Check: company isolation</field>
    <field name="model_id" ref="model_thedevkitchen_estate_credit_check"/>
    <field name="domain_force">[('company_id', '=', company_id)]</field>
</record>
```

**Extensão ao modelo de proposta** (`thedevkitchen.estate.proposal`):
```python
credit_check_ids = fields.One2many(
    'thedevkitchen.estate.credit.check', 'proposal_id',
    string='Credit Checks')
credit_history_summary = fields.Char(
    compute='_compute_credit_history_summary', store=False)
```

---

### API Endpoints (per ADR-007, ADR-009, ADR-011)

#### POST /api/v1/proposals/{id}/credit-checks

| Atributo | Valor |
|----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/proposals/{id}/credit-checks` |
| **Auth** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Roles** | Owner, Manager, Agent (proposta própria) |

**Request Body**:
```json
{ "insurer_name": "Porto Seguro" }
```

**Response 201** (ADR-007 HATEOAS):
```json
{
  "id": 1,
  "proposal_id": 42,
  "insurer_name": "Porto Seguro",
  "result": "pending",
  "requested_date": "2026-04-28",
  "links": [
    {"href": "/api/v1/proposals/42/credit-checks/1", "rel": "self", "type": "GET"},
    {"href": "/api/v1/proposals/42/credit-checks/1", "rel": "register-result", "type": "PATCH"},
    {"href": "/api/v1/proposals/42", "rel": "proposal", "type": "GET"}
  ]
}
```

**Error Responses**:

| Code | Condition |
|------|-----------|
| 400 | Validação de schema (ADR-018) |
| 403 | Permissão insuficiente (ADR-019) |
| 404 | Proposta não encontrada ou de outra empresa |
| 409 | Análise ativa já existe para esta proposta |
| 422 | Proposta de venda (análise de ficha não aplicável) |

---

#### PATCH /api/v1/proposals/{id}/credit-checks/{check_id}

| Atributo | Valor |
|----------|-------|
| **Method** | PATCH |
| **Path** | `/api/v1/proposals/{id}/credit-checks/{check_id}` |
| **Auth** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Roles** | Owner, Manager, Agent (proposta própria) |

**Request Body**:
```json
{
  "result": "rejected",
  "rejection_reason": "CPF com restrição na Serasa",
  "check_date": "2026-04-28",
  "notes": "Cliente informado"
}
```

**Response 200** (ADR-007 HATEOAS):
```json
{
  "id": 1,
  "result": "rejected",
  "rejection_reason": "CPF com restrição na Serasa",
  "check_date": "2026-04-28",
  "proposal": { "id": 42, "state": "rejected" },
  "links": [
    {"href": "/api/v1/proposals/42/credit-checks/1", "rel": "self", "type": "GET"},
    {"href": "/api/v1/proposals/42", "rel": "proposal", "type": "GET"}
  ]
}
```

**Error Responses**:

| Code | Condition |
|------|-----------|
| 400 | `rejection_reason` ausente quando `result=rejected` |
| 404 | Check não encontrado |
| 409 | Resultado já registrado (imutável) |

---

#### GET /api/v1/proposals/{id}/credit-checks

Retorna lista paginada de todos os checks da proposta em ordem cronológica.

**Auth**: `@require_jwt` + `@require_session` + `@require_company`

---

#### GET /api/v1/clients/{partner_id}/credit-history

| Atributo | Valor |
|----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/clients/{partner_id}/credit-history` |
| **Auth** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Roles** | Owner, Manager; Agent (somente clientes de suas propostas) |

**Response 200** (paginado, ADR-007 HATEOAS):
```json
{
  "partner_id": 10,
  "summary": { "total": 5, "approved": 2, "rejected": 3 },
  "items": [
    {
      "id": 1,
      "proposal_code": "PRP001",
      "property_name": "Ap. Jd. América 201",
      "insurer_name": "Porto Seguro",
      "result": "rejected",
      "check_date": "2025-10-12",
      "rejection_reason": "Renda insuficiente"
    }
  ],
  "links": [
    {"href": "/api/v1/clients/10/credit-history?page=2", "rel": "next", "type": "GET"}
  ]
}
```

---

### Seed Data (MANDATORY)

**Seed: Companies**
```python
company_a = env['res.company'].create({'name': 'Imobiliária Seed A'})
company_b = env['res.company'].create({'name': 'Imobiliária Seed B'})
```

**Seed: Users por papel**
```python
users = {
    'owner':   {'login': 'seed_owner@test.com',   'company': company_a},
    'manager': {'login': 'seed_manager@test.com', 'company': company_a},
    'agent_a': {'login': 'seed_agent_a@test.com', 'company': company_a},
    'agent_b': {'login': 'seed_agent_b@test.com', 'company': company_a},
    'owner_b': {'login': 'seed_owner_b@test.com', 'company': company_b},
}
```

**Seed: Clientes e Propostas**
```python
# Cliente com histórico de fichas anteriores
seed_client_with_history = env['res.partner'].create({
    'name': 'Seed Cliente Histórico', 'vat': '123.456.789-09'
})

# Proposta de locação em sent (pronta para iniciar ficha)
seed_lease_proposal_sent = env['thedevkitchen.estate.proposal'].create({
    'proposal_type': 'lease', 'state': 'sent',
    'partner_id': seed_client_with_history.id, ...
})

# Proposta de locação com ficha pendente (para testar registro de resultado)
seed_lease_proposal_pending_check = ...

# Proposta de venda (para testar bloqueio de ficha)
seed_sale_proposal = env['thedevkitchen.estate.proposal'].create({
    'proposal_type': 'sale', 'state': 'sent', ...
})

# CreditChecks históricos do cliente (2 reprovações, 1 aprovação em propostas anteriores)
seed_check_rejected_1 = env['thedevkitchen.estate.credit.check'].create({
    'proposal_id': ..., 'insurer_name': 'Porto Seguro',
    'result': 'rejected', 'rejection_reason': 'Seed: CPF com restrição',
    'requested_date': '2025-09-01', 'check_date': '2025-09-10'
})
seed_check_approved = env['thedevkitchen.estate.credit.check'].create({
    'proposal_id': ..., 'insurer_name': 'Tokio Marine',
    'result': 'approved', 'requested_date': '2025-10-15', 'check_date': '2025-11-01'
})
```

> ⚠️ **Regras**: prefixo `seed_` em todos os registros; seed idempotente; cobre ao menos uma proposta de locação por estado relevante (`sent`, `credit_check_pending`) e uma de venda.

---

### Non-Functional Requirements

**NFR-001 (Security)**: Todos os endpoints exigem `@require_jwt` + `@require_session` + `@require_company`. Isolamento multi-tenant por `company_id` (ADR-008). RBAC conforme FR-020 (ADR-019).

**NFR-002 (Performance)**: Resposta do histórico do cliente < 300ms para clientes com até 500 fichas. Listagem de checks por proposta < 200ms.

**NFR-003 (Quality)**: Pylint ≥ 8.0; black + isort + flake8 passando (ADR-022). 100% de cobertura nos constraints Python (ADR-003).

**NFR-004 (Data Integrity)**: FK de `CreditCheck` para proposta com `ON DELETE RESTRICT` — proposta com checks só pode ser excluída via soft delete (`active=False`, ADR-015).

**NFR-005 (Frontend)**: Views seguem padrão Odoo 18.0 — `<list>` em vez de `<tree>`, sem `attrs`, sem `column_invisible` com expressões Python, sem `groups` em `<menuitem>` (ADR-001, KB-10).

---

## Technical Constraints

| Fonte | Requisito | Aplicado em |
|-------|-----------|-------------|
| ADR-001 | Sem `attrs`, usar `<list>`, sem `groups` em menus | Todas as views |
| ADR-003 | 100% cobertura em constraints | CreditCheck model |
| ADR-004 | Prefixo `thedevkitchen_` | Nome do modelo e tabela |
| ADR-007 | HATEOAS links nas respostas | Todos os endpoints |
| ADR-008 | Isolamento por company_id | Record rules |
| ADR-011 | Duplo decorador (`@require_jwt` + `@require_session`) | Todos os controllers |
| ADR-015 | Soft delete com campo `active` | CreditCheck |
| ADR-018 | Validação de schema | Inputs de todos os endpoints |
| ADR-019 | RBAC por perfil | Authorization matrix FR-020 |
| ADR-022 | Linting: black, isort, flake8 | Todo o código Python |
| KB-10 | `optional` para visibilidade de colunas | List views Odoo |

---

## Success Criteria

- [ ] **SC-001**: Agente consegue iniciar e registrar resultado de análise de ficha em menos de 2 minutos via UI.
- [ ] **SC-002**: Reprovação de ficha promove próximo da fila em ≤ 5 segundos.
- [ ] **SC-003**: Aprovação de ficha cancela todos os concorrentes atomicamente — 0 falhas em 100 execuções concorrentes.
- [ ] **SC-004**: Histórico do cliente retorna corretamente fichas de múltiplas propostas, isolado por empresa.
- [ ] **SC-005**: 0 erros JavaScript no console em qualquer interação na UI.
- [ ] **SC-006**: 100% das transições de estado registradas no timeline da proposta.
- [ ] **SC-007**: Tentativa de análise em proposta de venda retorna HTTP 422 em 100% dos testes.
- [ ] **SC-008**: Re-abertura de análise após check `approved` retorna HTTP 409 em 100% dos testes.

---

## Assumptions

- A spec 013 (Property Proposals) está implementada e o modelo `thedevkitchen.estate.proposal` existe com os estados e mecanismos de fila documentados.
- O campo `proposal_type` (`sale`/`lease`) já existe na proposta (spec 013).
- O `insurer_name` é texto livre — sem integração com APIs de seguradoras nesta versão.
- A transição de `credit_check_pending → accepted/rejected` executa os mesmos efeitos colaterais de aceitação/rejeição da spec 013 (cancelamento de concorrentes e promoção de fila, respectivamente).
- Uma análise de ficha reprovada move a proposta para `rejected` (terminal). O cliente pode tentar novamente criando uma nova proposta.
- Única exceção ao terminal: se o check mais recente é `rejected` ou `cancelled`, o agente pode abrir um novo check antes de a proposta atingir o estado `rejected` — a proposta volta para `credit_check_pending`.

## Dependencies

- **Spec 013**: `thedevkitchen.estate.proposal`, mecanismo de fila FIFO, notificações assíncronas, FSM de estados.
- **Partner module**: `res.partner` como entidade de cliente.
- **Notification subsystem**: Outbox assíncrono para emails (spec 013 FR-041a).
- **Activity timeline**: `mail.thread` / `mail.activity.mixin` na proposta.
- **Background job scheduler**: cron diário de expiração da spec 013 precisa marcar checks `pending` como `cancelled` ao expirar propostas.

## Out of Scope

- Integração automática via API/webhook com seguradoras (Porto Seguro, Tokio Marine etc.) — MVP é registro manual.
- Análise de ficha para propostas de **venda**.
- Score de crédito calculado pelo sistema — apenas registro do resultado externo da seguradora.
- Múltiplas análises simultâneas em paralelo por proposta.
- Re-abertura de análise após aprovação (proposta já em estado terminal `accepted`).
- Notificações ao **cliente/locatário** sobre o resultado da análise — notificação é apenas ao agente, nesta versão.
- Fluxo de decisão do proprietário entre propostas concorrentes de diferente valor (mencionado nos áudios — pode ser spec 015).

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| Credit Check sub-resource | Recurso filho (`/proposals/{id}/credit-checks`) com ciclo de vida próprio ligado ao pai | API Patterns | Medium |
| Imutable result pattern | Após definição, resultado de entidade de análise não pode ser alterado | Data Integrity Patterns | Medium |
| State extension for sub-type | Estado `credit_check_pending` exclusivo para subtype `lease` — FSM condicional por tipo | Domain Patterns | High |

### New Entities/Relationships

| Entity | Related To | Relationship Type | Notes |
|--------|-----------|-------------------|-------|
| `CreditCheck` | `Proposal` | N:1 (múltiplos checks por proposta) | Histórico preservado |
| `CreditCheck` | `res.partner` | N:1 | Base do histórico por cliente |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: MINOR (1.3.0 → 1.4.0)
- **Sections to Update**:
  - [ ] Domain Patterns: FSM condicional por tipo de proposta
  - [ ] API Patterns: sub-resources com ciclo de vida próprio
  - [ ] Data Integrity: resultado imutável após definição

---

## Validation Checklist

### Backend
- [ ] ADR-004: modelo nomeado `thedevkitchen.estate.credit.check`
- [ ] ADR-008: record rule de `company_id` presente
- [ ] ADR-011: todos os controllers com `@require_jwt` + `@require_session` + `@require_company`
- [ ] ADR-015: campo `active` presente
- [ ] ADR-018: validação de schema em todos os inputs
- [ ] ADR-019: matriz FR-020 implementada
- [ ] ADR-003: 100% cobertura nos constraints Python

### Frontend
- [ ] Views com `<list>` (não `<tree>`)
- [ ] Sem `attrs`; sem `column_invisible` com expressões Python
- [ ] Sem `groups` em `<menuitem>`
- [ ] Cypress E2E para aba de ficha (lease e sale)
- [ ] Zero erros JavaScript no console

### Seeds
- [ ] Prefixo `seed_` em todos os registros
- [ ] Seed idempotente
- [ ] Cobre: proposta `lease/sent`, `lease/credit_check_pending`, `sale/sent`, cliente com histórico (2 reprovações + 1 aprovação)
