# Feature Specification: Unificação de Perfis (Profile Unification)

**Feature Branch**: `010-profile-unification`
**Created**: 2026-02-18
**Status**: Draft
**ADR References**: ADR-004, ADR-008, ADR-009, ADR-011, ADR-015, ADR-018, ADR-019, ADR-024 (new)
**KB References**: KB-09 (Database Best Practices)

---

## Executive Summary

Unificar todos os 9 perfis RBAC do sistema (ADR-019) em um modelo normalizado `thedevkitchen.estate.profile`, substituindo a abordagem atual em que apenas 2 perfis (Agent e Tenant) possuem tabelas dedicadas e os demais 7 existem apenas como grupos de segurança (`res.groups`). A unificação introduz:

1. **Tabela lookup `thedevkitchen.profile.type`** — catálogo normalizado dos 9 tipos de perfil (3NF, KB-09 §2.1)
2. **Tabela unificada `thedevkitchen.estate.profile`** — dados cadastrais comuns a todos os perfis com constraint composta `UNIQUE(document, company_id, profile_type_id)` permitindo a mesma pessoa em múltiplas empresas e/ou com múltiplos perfis
3. **Extensão de negócio `real.estate.agent`** — mantida como modelo separado referenciando `profile_id`, preservando domínio complexo (comissões, assignments, CRECI, dados bancários, métricas)
4. **Endpoint unificado `POST /api/v1/profiles`** — substituindo endpoints separados de tenant e eliminando dispersão
5. **Migração de dados** — `real.estate.tenant` → `thedevkitchen.estate.profile` com preservação de FKs (leases, sales)
6. **Fluxo two-step** — criar perfil (dados cadastrais) → convidar para acesso ao sistema (Feature 009)

**Motivação**: O modelo atual apresenta inconsistência estrutural (2 tabelas vs 7 grupos-only), constraint global no tenant que bloqueia multi-tenancy (`UNIQUE(document)` em vez de compound unique), e duplicação de dados no fluxo de convite (Feature 009).

---

## Clarifications & Decisions

### Session 2026-02-18

**D1: Quantos perfis possuem tabelas dedicadas hoje?**
- **R**: Apenas 2 — `real.estate.agent` (611 LOC, domínio complexo) e `real.estate.tenant` (35 LOC, simples). Os 7 restantes (Owner, Director, Manager, Prospector, Receptionist, Financial, Legal) são apenas `res.groups` em `groups.xml` sem tabela ou controller dedicado.

**D2: Agent deve ser absorvido na tabela unificada?**
- **R**: **Não (Opção A)**. `real.estate.agent` possui domínio de negócio rico (comissões, assignments, CRECI, dados bancários, métricas de performance — 611 LOC) que não pertence a um "perfil genérico". O modelo Agent é mantido como **extensão de negócio** com uma FK `profile_id → thedevkitchen.estate.profile`. Os campos cadastrais comuns (name, document, email, phone, company_id) migram para `thedevkitchen.estate.profile`; campos de domínio específico (creci, bank_*, commission_*, assignment_ids) permanecem em `real.estate.agent`.

**D3: Tenant será absorvido na tabela unificada?**
- **R**: **Sim**. `real.estate.tenant` é simples (35 LOC, campos: name, document, phone, email, occupation, birthdate, partner_id, company_ids, leases). Todos os campos migram para `thedevkitchen.estate.profile` com `profile_type = 'portal'`. O campo `leases` passa a usar FK reversa apontando para profile_id. A tabela `real_estate_tenant` será deprecated e removida após migração.

**D4: Endpoint único vs múltiplos?**
- **R**: **Endpoint único `POST /api/v1/profiles`** com `profile_type` no body. GET/PUT/DELETE seguem o padrão REST (`/api/v1/profiles/{id}`). Endpoints do tenant (`/api/v1/tenants/*`) serão deprecated com redirect 301 para `/api/v1/profiles/*`.

**D5: O `company_id` no perfil é Many2one ou Many2many?**
- **R**: **Many2one** para a constraint composta funcionar. Um perfil pertence a uma empresa. Para a mesma pessoa atuar em 2 empresas, são 2 registros de perfil distintos (um por empresa). Isso segue o modelo já correto do Agent (`company_id Many2one`). A M2M `company_ids` do Tenant é migrada: cada relação M2M vira um registro de perfil separado.

**D6: Profile type como Selection ou tabela lookup?**
- **R**: **Tabela lookup** (`thedevkitchen.profile.type`) conforme KB-09 §2.1 — "Use lookup/ref tables for enums > 5 values". São 9 tipos; a lookup permite extensão futura sem migração, referência ao `group_xml_id` do Odoo, e auditoria via soft delete.

**D7: Fluxo two-step — como integra com Feature 009?**
- **R**: Step 1: `POST /api/v1/profiles` cria o registro de perfil (dados cadastrais, sem acesso ao sistema). Step 2: `POST /api/v1/users/invite` envia convite para o email do perfil, criando `res.users` e vinculando via `partner_id`. O invite referencia o `profile_id`, não recebe dados cadastrais (já existem no perfil).

**D8: O que acontece com os controllers de Agent existentes?**
- **R**: Mantidos. Os 18 endpoints de `agent_api.py` (1,462 LOC) continuam operando sobre `real.estate.agent`. Na criação de Agent, o controller passa a criar automaticamente um `thedevkitchen.estate.profile` (profile_type='agent') e vincular via `profile_id`. Isso é transparente para os consumers atuais da API.

---

## Out of Scope

| Item | Motivo |
|------|--------|
| **Customização de perfis por empresa** | ADR-019 Fase 2 (pós-lançamento) |
| **Unificação do controller de Agent** | Agent tem domínio complexo; controller dedicado é justificado |
| **Remoção imediata de `real.estate.tenant`** | Deprecated nesta feature; remoção em release futura após validação |
| **UI/Views para perfis** | Headless architecture; views apenas para admin (Technical menu) |
| **Migração de campos de Agent para profile** | Agent mantém seus campos; profile possui apenas dados comuns |
| **Self-registration de perfis** | Todos os perfis são criados por usuários autorizados |

---

## User Scenarios & Testing

### User Story 1: Criar Perfil Genérico (Priority: P1) 🎯 MVP

**As a** Owner, Manager ou Agent autenticado
**I want to** criar um perfil (cadastro) para qualquer tipo autorizado
**So that** o registro exista no sistema antes de convidar para acesso

**Acceptance Criteria**:
- [ ] AC1.1: Given Owner autenticado, when `POST /api/v1/profiles` com `profile_type`, `name`, `document`, `email`, then perfil é criado em `thedevkitchen.estate.profile` vinculado à empresa ativa (`X-Company-ID`)
- [ ] AC1.2: Given `profile_type='agent'`, when perfil criado, then `real.estate.agent` é criado automaticamente com `profile_id` referenciando o perfil
- [ ] AC1.3: Given `profile_type='portal'`, when perfil criado, then campos `occupation` e `birthdate` são aceitos (opcionais)
- [ ] AC1.4: Given `document` + `company_id` + `profile_type_id` já existentes, when tentativa de criar duplicata, then 409 Conflict
- [ ] AC1.5: Given `document` existente em outra empresa, when cria perfil na empresa ativa, then perfil é criado normalmente (isolamento multi-tenancy)
- [ ] AC1.6: Given RBAC inválido (ex: Agent criando Director), when `POST /api/v1/profiles`, then 403 Forbidden
- [ ] AC1.7: Given `profile_type` inexistente, when `POST /api/v1/profiles`, then 400 Bad Request

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Endpoint `POST /api/v1/profiles` aceita `profile_type`, `name`, `document`, `email`, `phone` (obrigatórios) e campos opcionais por tipo | P1 |
| FR1.2 | `profile_type` deve existir na tabela `thedevkitchen.profile.type` com `is_active=True` | P1 |
| FR1.3 | Constraint composta `UNIQUE(document, company_id, profile_type_id)` previne duplicatas por empresa/tipo | P1 |
| FR1.4 | Quando `profile_type='agent'`, criar simultaneamente `thedevkitchen.estate.profile` + `real.estate.agent` (transação atômica) | P1 |
| FR1.5 | Quando `profile_type='portal'`, aceitar campos opcionais: `occupation`, `birthdate` | P1 |
| FR1.6 | O `company_id` é obtido de `X-Company-ID` header — nunca do body | P1 |
| FR1.7 | Validação de CPF/CNPJ via `validate_docbr` antes de persistir | P1 |
| FR1.8 | Normalização de documento (remover máscara) em `document_normalized` computed field | P2 |
| FR1.9 | HATEOAS links no response: `self`, `invite` (Feature 009), `company` | P1 |
| FR1.10 | Autorização segue matriz RBAC de ADR-019 (mesma de Feature 009) | P1 |
| FR1.11 | Perfil criado com `active=True` e timestamps de auditoria (`create_date`, `write_date`) | P1 |
| FR1.12 | Cross-company access retorna 404 genérico (anti-enumeration, FR precedence: AuthZ→Isolation→Validation) | P1 |

**Test Coverage** (per ADR-003):

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| Unit | T1.1 | Constraint composta rejeita duplicata (document+company+type) | FR1.3 |
| Unit | T1.2 | Constraint permite mesmo document em empresa diferente | FR1.3 |
| Unit | T1.3 | Constraint permite mesmo document com type diferente na mesma empresa | FR1.3 |
| Unit | T1.4 | Agent extension criada atomicamente com profile | FR1.4 |
| Unit | T1.5 | CPF inválido rejeitado com 400 | FR1.7 |
| Unit | T1.6 | Profile type inexistente rejeitado com 400 | FR1.2 |
| Unit | T1.7 | Profile type inativo rejeitado com 400 | FR1.2 |
| E2E | T1.8 | Owner cria perfil Manager com sucesso | FR1.1 |
| E2E | T1.9 | Owner cria perfil Agent → agent extension criada | FR1.4 |
| E2E | T1.10 | Owner cria perfil Portal com occupation/birthdate | FR1.5 |
| E2E | T1.11 | Duplicate document+company+type retorna 409 | FR1.3 |
| E2E | T1.12 | Same document, different company → 201 | FR1.3 |
| E2E | T1.13 | Cross-company access → 404 | FR1.12 |
| E2E | T1.14 | Agent tenta criar Director → 403 | FR1.10 |
| E2E | T1.15 | Response contém HATEOAS links | FR1.9 |

---

### User Story 2: Listar e Consultar Perfis (Priority: P1) 🎯 MVP

**As a** Owner, Manager ou Agent autenticado
**I want to** listar perfis da minha empresa com filtros por tipo
**So that** eu possa gerenciar os cadastros existentes

**Acceptance Criteria**:
- [ ] AC2.1: Given Owner autenticado, when `GET /api/v1/profiles`, then retorna todos os perfis da empresa ativa
- [ ] AC2.2: Given query param `?profile_type=agent`, when `GET /api/v1/profiles`, then retorna somente perfis do tipo agent
- [ ] AC2.3: Given `GET /api/v1/profiles/{id}`, when perfil existe na empresa ativa, then retorna detalhes completos
- [ ] AC2.4: Given `GET /api/v1/profiles/{id}`, when perfil pertence a outra empresa, then 404
- [ ] AC2.5: Given perfil com `profile_type='agent'`, when `GET /api/v1/profiles/{id}`, then response inclui link HATEOAS para agent extension (`/api/v1/agents/{agent_id}`)

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | `GET /api/v1/profiles` retorna lista paginada com filtros `profile_type`, `document`, `name`, `active` | P1 |
| FR2.2 | `GET /api/v1/profiles/{id}` retorna detalhes do perfil com HATEOAS links | P1 |
| FR2.3 | Filtro por `profile_type` aceita código da lookup table (ex: `agent`, `portal`, `manager`) | P1 |
| FR2.4 | Paginação via `offset` + `limit` (padrão: offset=0, limit=20, max=100) | P2 |
| FR2.5 | Ordenação via `order_by` (padrão: `name asc`) | P2 |
| FR2.6 | Escopo sempre limitado à empresa ativa (`X-Company-ID`) | P1 |
| FR2.7 | RBAC: Owner vê todos; Manager vê operacionais; Agent vê owner+portal + próprio | P1 |

**Test Coverage**:

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| E2E | T2.1 | List profiles retorna perfis da empresa ativa | FR2.1 |
| E2E | T2.2 | Filter por profile_type funciona | FR2.3 |
| E2E | T2.3 | Get profile detail com HATEOAS links | FR2.2 |
| E2E | T2.4 | Cross-company profile → 404 | FR2.6 |
| E2E | T2.5 | Agent-type profile includes agent extension link | FR2.2 |
| E2E | T2.6 | Pagination offset+limit | FR2.4 |

---

### User Story 3: Atualizar Perfil (Priority: P1)

**As a** Owner ou Manager autenticado
**I want to** atualizar dados cadastrais de um perfil existente
**So that** informações corretas estejam sempre disponíveis

**Acceptance Criteria**:
- [ ] AC3.1: Given Owner, when `PUT /api/v1/profiles/{id}` com campos atualizados, then perfil é atualizado
- [ ] AC3.2: Given atualização de `document` que causa duplicata, when `PUT`, then 409 Conflict
- [ ] AC3.3: Given perfil do tipo agent, when atualiza `name`, then `real.estate.agent.name` é sincronizado
- [ ] AC3.4: Given `profile_type` no body, when `PUT`, then 400 (profile_type é imutável)

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | `PUT /api/v1/profiles/{id}` atualiza campos permitidos | P1 |
| FR3.2 | `profile_type` e `company_id` são imutáveis após criação | P1 |
| FR3.3 | Atualização de `name`, `email`, `phone` sincroniza para `real.estate.agent` se `profile_type='agent'` | P1 |
| FR3.4 | Atualização de `document` revalida constraint composta | P1 |
| FR3.5 | RBAC: Owner→todos; Manager→operacionais | P1 |

**Test Coverage**:

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| E2E | T3.1 | Update profile name com sucesso | FR3.1 |
| E2E | T3.2 | Update document causing duplicate → 409 | FR3.4 |
| E2E | T3.3 | Update agent-type profile syncs to agent model | FR3.3 |
| E2E | T3.4 | Attempt to change profile_type → 400 | FR3.2 |
| E2E | T3.5 | Manager cannot update Director profile → 403 | FR3.5 |

---

### User Story 4: Desativar Perfil — Soft Delete (Priority: P2)

**As a** Owner autenticado
**I want to** desativar um perfil sem perder dados históricos
**So that** o cadastro fique inativo mas auditável

**Acceptance Criteria**:
- [ ] AC4.1: Given Owner, when `DELETE /api/v1/profiles/{id}`, then `active=False`, `deactivation_date` e `deactivation_reason` são preenchidos
- [ ] AC4.2: Given perfil com agent extension, when desativado, then `real.estate.agent.active=False` também
- [ ] AC4.3: Given perfil com `res.users` vinculado, when desativado, then `res.users.active=False` (bloqueia login)
- [ ] AC4.4: Given perfil já inativo, when tenta desativar novamente, then 400

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | `DELETE /api/v1/profiles/{id}` faz soft delete (ADR-015) | P2 |
| FR4.2 | Cascata de desativação: profile → agent extension → res.users | P2 |
| FR4.3 | `deactivation_reason` aceito como campo opcional no body | P2 |
| FR4.4 | Perfis inativos excluídos de listagens por padrão (filtro `?active=false` para ver) | P2 |

**Test Coverage**:

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| E2E | T4.1 | Soft delete profile with reason | FR4.1 |
| E2E | T4.2 | Agent extension deactivated in cascade | FR4.2 |
| E2E | T4.3 | Linked res.users deactivated | FR4.2 |
| E2E | T4.4 | Already inactive → 400 | FR4.1 |

---

### User Story 5: Migração e Compatibilidade (Priority: P1) 🎯 MVP

**As a** DevOps/Developer
**I want to** migrar dados de `real.estate.tenant` para `thedevkitchen.estate.profile`
**So that** a transição seja transparente e sem perda de dados

**Acceptance Criteria**:
- [ ] AC5.1: Given tenants existentes, when migration roda, then cada tenant vira um `thedevkitchen.estate.profile` com `profile_type='portal'`
- [ ] AC5.2: Given tenant com M2M `company_ids` (N empresas), when migração, then N registros de perfil são criados (1 por empresa)
- [ ] AC5.3: Given `real.estate.lease` com FK `tenant_id`, when migração, then FK atualizada para `profile_id`
- [ ] AC5.4: Given endpoints antigos (`/api/v1/tenants/*`), when requisição, then redirect 301 para `/api/v1/profiles/*`
- [ ] AC5.5: Given `real.estate.agent` existentes, when migration roda, then `thedevkitchen.estate.profile` criado para cada agent e `profile_id` FK preenchida

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | Migration script idempotente (pode rodar múltiplas vezes sem efeito colateral) — KB-09 §11 | P1 |
| FR5.2 | Tenant M2M → N registros de profile (1 per company) com dados clonados | P1 |
| FR5.3 | FKs em `real.estate.lease` e `real.estate.sale` redirecionadas para `profile_id` | P1 |
| FR5.4 | Agent existentes ganham `profile_id` FK para novo profile criado na migração | P1 |
| FR5.5 | Redirect 301 nos endpoints deprecated (`/api/v1/tenants/*`) | P2 |
| FR5.6 | Rollback plan: migration reversível com script dedicado | P1 |
| FR5.7 | Data validation pós-migração: contagem de registros, integridade de FKs, constraint check | P1 |

**Test Coverage**:

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| Integration | T5.1 | Migration creates profile for each tenant | FR5.2 |
| Integration | T5.2 | Tenant with 3 companies → 3 profiles | FR5.2 |
| Integration | T5.3 | Lease FK updated to profile_id | FR5.3 |
| Integration | T5.4 | Agent gets profile_id FK | FR5.4 |
| Integration | T5.5 | Migration is idempotent (run twice, same result) | FR5.1 |
| Integration | T5.6 | Data counts match pre/post migration | FR5.7 |
| E2E | T5.7 | GET /api/v1/tenants/{id} → 301 → /api/v1/profiles/{id} | FR5.5 |

---

### User Story 6: Integração com Feature 009 — Invite Flow (Priority: P1) 🎯 MVP

**As a** Owner autenticado
**I want to** convidar um perfil existente para ter acesso ao sistema
**So that** o fluxo dois-passos funcione (create profile → invite for access)

**Acceptance Criteria**:
- [ ] AC6.1: Given perfil criado sem `res.users`, when `POST /api/v1/users/invite` com `profile_id`, then `res.users` é criado e email de convite enviado
- [ ] AC6.2: Given perfil já com `res.users` vinculado, when tenta invite, then 409 Conflict ("Profile already has system access")
- [ ] AC6.3: Given invite com `profile_id`, when dados cadastrais (name, email) são obtidos do perfil, then invite não exige re-envio de dados
- [ ] AC6.4: Given `profile_type` do perfil, when `res.users` é criado, then grupo de segurança correto é atribuído automaticamente via `group_xml_id` da lookup

**Functional Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| FR6.1 | `POST /api/v1/users/invite` aceita `profile_id` como identificador — name, email, document lidos do perfil | P1 |
| FR6.2 | Se perfil já possui `user_id` (via partner_id), retornar 409 | P1 |
| FR6.3 | Grupo de segurança determinado por `profile_type.group_xml_id`, não por campo `profile` no body | P1 |
| FR6.4 | Após invite aceito (set-password), `profile.user_id` é preenchido | P1 |
| FR6.5 | `company_id` do perfil é herdado para o contexto do invite | P1 |

**Test Coverage**:

| Type | Test ID | Description | FR |
|------|---------|-------------|-----|
| E2E | T6.1 | Invite via profile_id → user created, email sent | FR6.1 |
| E2E | T6.2 | Profile already has user → 409 | FR6.2 |
| E2E | T6.3 | Correct security group assigned from profile_type | FR6.3 |
| E2E | T6.4 | After set-password, profile.user_id populated | FR6.4 |

---

## Data Model

### Entity Relationship Diagram

```
┌─────────────────────────────────────┐
│   thedevkitchen.profile.type        │
│   (Lookup / Reference Table)        │
├─────────────────────────────────────┤
│ id: Integer (PK, surrogate)         │
│ code: Char(30) UNIQUE NOT NULL      │
│ name: Char(100) NOT NULL            │
│ group_xml_id: Char(100) NOT NULL    │
│ level: Selection (admin/oper/ext)   │
│ is_active: Boolean DEFAULT TRUE     │
│ create_date: Datetime (audit)       │
│ write_date: Datetime (audit)        │
└──────────────┬──────────────────────┘
               │ 1
               │
               │ N
┌──────────────┴──────────────────────┐        ┌──────────────────────────────┐
│  thedevkitchen.estate.profile       │        │   thedevkitchen.estate.      │
│  (Unified Profile Table)            │        │   company                    │
├─────────────────────────────────────┤        ├──────────────────────────────┤
│ id: Integer (PK, surrogate)         │   N  1 │ id                           │
│ profile_type_id: FK → profile.type  │───────→│ name                         │
│ company_id: FK → estate.company     │        │ ...                          │
│ partner_id: FK → res.partner        │        └──────────────────────────────┘
│ name: Char(200) NOT NULL            │
│ document: Char(20) NOT NULL         │        ┌──────────────────────────────┐
│ document_normalized: Char(14)       │        │   res.partner                │
│ email: Char(100) NOT NULL           │        ├──────────────────────────────┤
│ phone: Char(20)                     │   N  1 │ id                           │
│ occupation: Char(100)               │───────→│ (auto-created by Odoo)       │
│ birthdate: Date                     │        └──────────────────────────────┘
│ hire_date: Date                     │
│ profile_picture: Binary             │
│ active: Boolean DEFAULT TRUE        │        ┌──────────────────────────────┐
│ deactivation_date: Datetime         │        │   real.estate.agent          │
│ deactivation_reason: Text           │        │   (Business Extension)       │
│ create_date: Datetime (audit)       │        ├──────────────────────────────┤
│ write_date: Datetime (audit)        │   1  1 │ profile_id: FK → profile     │
│                                     │◄───────│ creci, creci_normalized      │
│ UNIQUE(document, company_id,        │        │ bank_name, bank_branch, ...  │
│        profile_type_id)             │        │ commission_rule_ids          │
└─────────────────────────────────────┘        │ commission_transaction_ids   │
                                               │ assignment_ids               │
                                               │ ...                          │
                                               └──────────────────────────────┘
```

### Entity 1: `thedevkitchen.profile.type` (Lookup Table)

**Table**: `thedevkitchen_profile_type` (auto-generated)
**Module**: `quicksol_estate` (or new `thedevkitchen_profile`)
**Purpose**: Normalized catalog of the 9 RBAC profile types (KB-09 §2.1: lookup tables for enums > 5 values)

#### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | Integer | auto | auto | PK | Surrogate primary key (KB-09 §3) |
| `code` | Char(30) | ✅ | — | UNIQUE, NOT NULL, index | Machine identifier: `owner`, `director`, `manager`, `agent`, `prospector`, `receptionist`, `financial`, `legal`, `portal` |
| `name` | Char(100) | ✅ | — | NOT NULL | Display name: "Proprietário", "Diretor", etc. |
| `group_xml_id` | Char(100) | ✅ | — | NOT NULL | Odoo group XML ID: `quicksol_estate.group_real_estate_owner`, etc. |
| `level` | Selection | ✅ | — | `[('admin','Admin'),('operational','Operational'),('external','External')]` | ADR-019 level classification |
| `is_active` | Boolean | ✅ | `True` | — | Soft delete for lookup (KB-09 §9) |
| `create_date` | Datetime | auto | auto | — | Audit (ADR-004) |
| `write_date` | Datetime | auto | auto | — | Audit (ADR-004) |

#### SQL Constraints

```python
_sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Profile type code must be unique'),
]
```

#### Seed Data (XML `noupdate="1"`)

| code | name | group_xml_id | level |
|------|------|-------------|-------|
| `owner` | Proprietário | `quicksol_estate.group_real_estate_owner` | admin |
| `director` | Diretor | `quicksol_estate.group_real_estate_director` | admin |
| `manager` | Gerente | `quicksol_estate.group_real_estate_manager` | admin |
| `agent` | Corretor | `quicksol_estate.group_real_estate_agent` | operational |
| `prospector` | Captador | `quicksol_estate.group_real_estate_prospector` | operational |
| `receptionist` | Atendente | `quicksol_estate.group_real_estate_receptionist` | operational |
| `financial` | Financeiro | `quicksol_estate.group_real_estate_financial` | operational |
| `legal` | Jurídico | `quicksol_estate.group_real_estate_legal` | operational |
| `portal` | Portal (Inquilino/Comprador) | `quicksol_estate.group_real_estate_portal_user` | external |

---

### Entity 2: `thedevkitchen.estate.profile` (Unified Profile)

**Table**: `thedevkitchen_estate_profile` (auto-generated)
**Module**: `quicksol_estate` (or new module)
**Purpose**: Single table for all 9 profile types with compound unique constraint

#### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | Integer | auto | auto | PK | Surrogate primary key |
| `profile_type_id` | Many2one(`thedevkitchen.profile.type`) | ✅ | — | FK, `ondelete='restrict'`, index | Profile type reference |
| `company_id` | Many2one(`thedevkitchen.estate.company`) | ✅ | from `X-Company-ID` | FK, `ondelete='restrict'`, index | Company this profile belongs to |
| `partner_id` | Many2one(`res.partner`) | ❌ | auto-created | FK, `ondelete='restrict'` | Odoo partner (bridge to `res.users`) |
| `name` | Char(200) | ✅ | — | NOT NULL | Full legal name |
| `document` | Char(20) | ✅ | — | NOT NULL, index | CPF or CNPJ (with formatting) |
| `document_normalized` | Char(14) | computed | — | stored, index | Digits only (computed, stored) |
| `email` | Char(100) | ✅ | — | NOT NULL | Contact email |
| `phone` | Char(20) | ❌ | — | — | Phone number |
| `mobile` | Char(20) | ❌ | — | — | Mobile phone |
| `occupation` | Char(100) | ❌ | — | — | Occupation (relevant for portal/tenant) |
| `birthdate` | Date | ❌ | — | — | Date of birth |
| `hire_date` | Date | ❌ | — | — | Hire date (relevant for internal profiles) |
| `profile_picture` | Binary | ❌ | — | — | Profile picture |
| `active` | Boolean | ✅ | `True` | — | Soft delete (ADR-015) |
| `deactivation_date` | Datetime | ❌ | — | — | When deactivated |
| `deactivation_reason` | Text | ❌ | — | — | Why deactivated |
| `create_date` | Datetime | auto | auto | — | Audit timestamp |
| `write_date` | Datetime | auto | auto | — | Audit timestamp |

#### SQL Constraints

```python
_sql_constraints = [
    ('document_company_type_unique',
     'UNIQUE(document, company_id, profile_type_id)',
     'Este documento já está cadastrado para este tipo de perfil nesta empresa'),
]
```

#### Named Constraint (KB-09 §7.3)

PostgreSQL auto-generates name from `_sql_constraints` tuple in Odoo. The logical name follows:
`thedevkitchen_estate_profile_document_company_type_unique`

#### Indexes (KB-09 §5)

Automatically created by Odoo for:
- `profile_type_id` (FK index)
- `company_id` (FK index)
- `document` (explicit `index=True`)
- `document_normalized` (explicit `index=True`, stored computed)

Additional recommended partial index for soft delete (KB-09 §9.2):
```sql
CREATE INDEX idx_profile_active ON thedevkitchen_estate_profile (company_id, profile_type_id)
WHERE active = true;
```

#### Python Constraints

```python
@api.constrains('document')
def _check_document(self):
    """Validate CPF/CNPJ format and checksum"""
    from validate_docbr import CPF, CNPJ
    for record in self:
        doc_clean = ''.join(filter(str.isdigit, record.document))
        if len(doc_clean) == 11:
            if not CPF().validate(doc_clean):
                raise ValidationError('CPF inválido: %s' % record.document)
        elif len(doc_clean) == 14:
            if not CNPJ().validate(doc_clean):
                raise ValidationError('CNPJ inválido: %s' % record.document)
        else:
            raise ValidationError('Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos')

@api.depends('document')
def _compute_document_normalized(self):
    """Strip formatting, keep only digits"""
    for record in self:
        if record.document:
            record.document_normalized = ''.join(filter(str.isdigit, record.document))
        else:
            record.document_normalized = False

@api.constrains('email')
def _check_email(self):
    """Validate email format"""
    import re
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    for record in self:
        if record.email and not pattern.match(record.email):
            raise ValidationError('Email inválido: %s' % record.email)
```

#### Record Rules (Multi-Tenancy — ADR-008)

```xml
<record id="profile_company_rule" model="ir.rule">
    <field name="name">Profile: Company Isolation</field>
    <field name="model_id" ref="model_thedevkitchen_estate_profile"/>
    <field name="domain_force">[('company_id', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_real_estate_user'))]"/>
</record>
```

---

### Entity 3: `real.estate.agent` (Business Extension — Modified)

**Table**: `real_estate_agent` (existing)
**Module**: `quicksol_estate`
**Purpose**: Agent-specific business domain. Gains `profile_id` FK; common fields (`name`, `cpf`, `email`, `phone`, `company_id`) become **related fields** synced from profile.

#### Changes to Existing Model

| Change | Field | Before | After |
|--------|-------|--------|-------|
| **ADD** | `profile_id` | — | `Many2one('thedevkitchen.estate.profile', ondelete='restrict', index=True)` |
| **MODIFY** | `name` | `Char, required` | Related field `→ profile_id.name` (or keep + sync) |
| **MODIFY** | `cpf` | `Char, required` | Related field `→ profile_id.document` (or keep + sync) |
| **MODIFY** | `email` | `Char` | Related field `→ profile_id.email` (or keep + sync) |
| **MODIFY** | `phone` | `Char` | Related field `→ profile_id.phone` (or keep + sync) |
| **MODIFY** | `company_id` | `Many2one, required` | Related field `→ profile_id.company_id` (or keep + sync) |
| **KEEP** | `creci`, `creci_*` | as-is | Agent-specific domain |
| **KEEP** | `bank_*`, `pix_key` | as-is | Agent-specific financial |
| **KEEP** | `commission_*` | as-is | Agent-specific business |
| **KEEP** | `assignment_ids` | as-is | Agent-specific business |
| **KEEP** | `user_id` | `Many2one('res.users')` | Stays; eventually synced via profile.partner_id |
| **DEPRECATE** | `company_ids` (M2M) | deprecated field | Remove in future release |

**Strategy**: Phased approach. Phase 1 adds `profile_id` FK and sync logic. Phase 2 (future) converts common fields to Odoo `related` fields. This avoids breaking the 18 existing endpoints in `agent_api.py`.

#### SQL Constraint Update

Existing constraint `UNIQUE(cpf, company_id)` can coexist with profile's `UNIQUE(document, company_id, profile_type_id)` since agent always has `profile_type='agent'`. No change needed in Phase 1.

---

## API Design

### Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/profiles` | `@require_jwt` + `@require_session` + `@require_company` | Create profile |
| `GET` | `/api/v1/profiles` | `@require_jwt` + `@require_session` + `@require_company` | List profiles (paginated, filtered) |
| `GET` | `/api/v1/profiles/{id}` | `@require_jwt` + `@require_session` + `@require_company` | Get profile detail |
| `PUT` | `/api/v1/profiles/{id}` | `@require_jwt` + `@require_session` + `@require_company` | Update profile |
| `DELETE` | `/api/v1/profiles/{id}` | `@require_jwt` + `@require_session` + `@require_company` | Soft delete profile |
| `GET` | `/api/v1/profile-types` | `@require_jwt` + `@require_session` | List available profile types |

### Request/Response Examples

#### POST /api/v1/profiles

**Request**:
```json
{
  "profile_type": "agent",
  "name": "João Silva",
  "document": "123.456.789-01",
  "email": "joao@example.com",
  "phone": "+55 (11) 99999-0001"
}
```

**Response (201)**:
```json
{
  "id": 42,
  "profile_type": {
    "code": "agent",
    "name": "Corretor"
  },
  "name": "João Silva",
  "document": "123.456.789-01",
  "email": "joao@example.com",
  "phone": "+55 (11) 99999-0001",
  "company_id": 1,
  "has_system_access": false,
  "agent_extension_id": 15,
  "created_at": "2026-02-18T10:30:00Z",
  "_links": {
    "self": {"href": "/api/v1/profiles/42"},
    "invite": {"href": "/api/v1/users/invite", "method": "POST"},
    "agent": {"href": "/api/v1/agents/15"},
    "company": {"href": "/api/v1/companies/1"}
  }
}
```

#### POST /api/v1/profiles (portal type)

**Request**:
```json
{
  "profile_type": "portal",
  "name": "Maria Oliveira",
  "document": "987.654.321-00",
  "email": "maria@example.com",
  "phone": "+55 (11) 98888-0002",
  "occupation": "Engenheira",
  "birthdate": "1990-05-15"
}
```

**Response (201)**:
```json
{
  "id": 43,
  "profile_type": {
    "code": "portal",
    "name": "Portal (Inquilino/Comprador)"
  },
  "name": "Maria Oliveira",
  "document": "987.654.321-00",
  "email": "maria@example.com",
  "phone": "+55 (11) 98888-0002",
  "occupation": "Engenheira",
  "birthdate": "1990-05-15",
  "company_id": 1,
  "has_system_access": false,
  "created_at": "2026-02-18T10:35:00Z",
  "_links": {
    "self": {"href": "/api/v1/profiles/43"},
    "invite": {"href": "/api/v1/users/invite", "method": "POST"},
    "company": {"href": "/api/v1/companies/1"}
  }
}
```

#### GET /api/v1/profiles?profile_type=agent&limit=20&offset=0

**Response (200)**:
```json
{
  "count": 45,
  "offset": 0,
  "limit": 20,
  "data": [
    {
      "id": 42,
      "profile_type": {"code": "agent", "name": "Corretor"},
      "name": "João Silva",
      "document": "123.456.789-01",
      "email": "joao@example.com",
      "has_system_access": true,
      "_links": {
        "self": {"href": "/api/v1/profiles/42"},
        "agent": {"href": "/api/v1/agents/15"}
      }
    }
  ],
  "_links": {
    "self": {"href": "/api/v1/profiles?profile_type=agent&limit=20&offset=0"},
    "next": {"href": "/api/v1/profiles?profile_type=agent&limit=20&offset=20"}
  }
}
```

#### Error Responses

| Status | Scenario | Body |
|--------|----------|------|
| 400 | Invalid CPF, missing required field, invalid profile_type | `{"error": "validation_error", "field": "document", "message": "CPF inválido"}` |
| 403 | RBAC violation (Agent creating Director) | `{"error": "forbidden", "message": "Insufficient permissions for this profile type"}` |
| 404 | Cross-company or nonexistent | `{"error": "not_found", "message": "Profile not found"}` |
| 409 | Duplicate document+company+type | `{"error": "conflict", "field": "document", "message": "Document already registered for this profile type in this company"}` |

---

## Authorization Matrix (RBAC)

Follows ADR-019 hierarchy. Same matrix as Feature 009 invite flow:

| Creator Role | Can Create Profile Types |
|-------------|--------------------------|
| **Owner** | All 9: owner, director, manager, agent, prospector, receptionist, financial, legal, portal |
| **Manager** | 5 operational: agent, prospector, receptionist, financial, legal |
| **Agent** | 2: owner (property owner), portal (tenant) |
| **Director** | Same as Manager (inherits) |
| **Others** | Cannot create profiles |

---

## Migration Plan

### Phase 1: Schema Creation (Non-breaking)

1. Create `thedevkitchen.profile.type` model + seed data (9 records)
2. Create `thedevkitchen.estate.profile` model with compound unique constraint
3. Add `profile_id` FK to `real.estate.agent` (nullable initially)

### Phase 2: Data Migration (Idempotent — KB-09 §11)

```python
def migrate(cr, version):
    """
    Idempotent migration: tenant → profile, agent → profile.
    Safe to run multiple times.
    """
    # Step 1: Get profile_type IDs
    cr.execute("SELECT id FROM thedevkitchen_profile_type WHERE code = 'portal'")
    portal_type_id = cr.fetchone()[0]
    
    cr.execute("SELECT id FROM thedevkitchen_profile_type WHERE code = 'agent'")
    agent_type_id = cr.fetchone()[0]
    
    # Step 2: Migrate tenants (M2M → N profiles)
    cr.execute("""
        INSERT INTO thedevkitchen_estate_profile 
            (profile_type_id, company_id, partner_id, name, document, email, phone,
             occupation, birthdate, active, create_date, write_date)
        SELECT 
            %(portal_type)s, rel.company_id, t.partner_id, t.name, t.document, 
            t.email, t.phone, t.occupation, t.birthdate, t.active, 
            t.create_date, t.write_date
        FROM real_estate_tenant t
        JOIN thedevkitchen_company_tenant_rel rel ON rel.tenant_id = t.id
        WHERE NOT EXISTS (
            SELECT 1 FROM thedevkitchen_estate_profile p
            WHERE p.document = t.document 
              AND p.company_id = rel.company_id
              AND p.profile_type_id = %(portal_type)s
        )
    """, {'portal_type': portal_type_id})
    
    # Step 3: Migrate agents → profiles
    cr.execute("""
        INSERT INTO thedevkitchen_estate_profile
            (profile_type_id, company_id, partner_id, name, document, email, phone,
             hire_date, active, create_date, write_date)
        SELECT
            %(agent_type)s, a.company_id, NULL, a.name, a.cpf, a.email, a.phone,
            a.hire_date, a.active, a.create_date, a.write_date
        FROM real_estate_agent a
        WHERE NOT EXISTS (
            SELECT 1 FROM thedevkitchen_estate_profile p
            WHERE p.document = a.cpf
              AND p.company_id = a.company_id
              AND p.profile_type_id = %(agent_type)s
        )
    """, {'agent_type': agent_type_id})
    
    # Step 4: Link agents to their new profiles
    cr.execute("""
        UPDATE real_estate_agent a
        SET profile_id = (
            SELECT p.id FROM thedevkitchen_estate_profile p
            WHERE p.document = a.cpf
              AND p.company_id = a.company_id
              AND p.profile_type_id = %(agent_type)s
            LIMIT 1
        )
        WHERE a.profile_id IS NULL
    """, {'agent_type': agent_type_id})
    
    # Step 5: Update lease FK (tenant_id → profile_id)
    # This requires adding profile_id column to real_estate_lease first
    cr.execute("""
        UPDATE real_estate_lease l
        SET profile_id = (
            SELECT p.id FROM thedevkitchen_estate_profile p
            JOIN real_estate_tenant t ON t.document = p.document
            WHERE t.id = l.tenant_id
              AND p.profile_type_id = %(portal_type)s
              AND p.company_id = l.company_id
            LIMIT 1
        )
        WHERE l.profile_id IS NULL AND l.tenant_id IS NOT NULL
    """, {'portal_type': portal_type_id})
```

### Phase 3: Controller Migration

1. Create `profile_api.py` in `quicksol_estate/controllers/` with 6 endpoints
2. Add 301 redirects from `/api/v1/tenants/*` to `/api/v1/profiles/*`
3. Modify `agent_api.py` creation endpoint to auto-create profile alongside agent
4. Modify Feature 009 `invite_controller.py` to accept `profile_id`

### Phase 4: Deprecation & Cleanup (Future Release)

1. Mark `real.estate.tenant` model as `_deprecated = True`
2. Remove deprecated `company_ids` M2M from agent
3. Convert agent common fields to `related` fields pointing to profile
4. Remove `/api/v1/tenants/*` redirect endpoints
5. Drop `real_estate_tenant` table

---

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1 | Profile CRUD response time | < 200ms p95 |
| NFR2 | Migration script handles 10k+ records | < 30s |
| NFR3 | Compound unique constraint enforced at DB level | PostgreSQL constraint |
| NFR4 | Profile lookup by document+company | < 50ms (indexed) |
| NFR5 | Migration is idempotent (KB-09 §11) | Run N times, same result |
| NFR6 | Backward compatibility for agent API consumers | 0 breaking changes |
| NFR7 | Tenant API deprecated with 301 redirects | Minimum 1 release cycle |

---

## ADR-024: Unificação de Perfis em Modelo Normalizado

### Status
Proposto

### Contexto

O sistema possui 9 perfis RBAC (ADR-019) com implementação inconsistente:
- 2 perfis com tabelas dedicadas (`real.estate.agent` com 611 LOC, `real.estate.tenant` com 35 LOC)
- 7 perfis apenas como `res.groups` sem tabela ou cadastro dedicado
- Tenant tem `UNIQUE(document)` global bloqueando multi-tenancy
- Agent tem `UNIQUE(cpf, company_id)` (correto, mas isolado)
- Feature 009 (invite flow) forçava re-envio de dados cadastrais no convite

### Decisão

1. **Tabela lookup `thedevkitchen.profile.type`** com 9 registros fixos (KB-09 §2.1: enums > 5 → lookup table)
2. **Tabela unificada `thedevkitchen.estate.profile`** com constraint `UNIQUE(document, company_id, profile_type_id)`
3. **Agent como extensão de negócio** — `real.estate.agent` mantido com FK `profile_id`, preservando 611 LOC de domínio
4. **Tenant absorvido** na tabela unificada (`profile_type='portal'`)
5. **Endpoint unificado** `POST /api/v1/profiles` com `profile_type` no body
6. **Fluxo two-step**: criar perfil (step 1) → convidar para acesso (step 2, Feature 009)

### Consequências

**Positivas:**
- Consistência: todos os 9 perfis possuem cadastro normalizado
- Multi-tenancy: compound unique permite mesma pessoa em múltiplas empresas
- Feature 009 simplificado: invite referencia `profile_id`, sem re-envio de dados
- Extensibilidade: novos tipos de perfil = novo registro na lookup table (sem migração)
- 3NF compliance (KB-09): eliminação de redundância e anomalias de atualização

**Negativas:**
- Migração de dados complexa (tenant M2M → N profiles, agent FK backfill)
- FKs em lease/sale precisam ser redirecionadas
- Período de deprecação do tenant API (301 redirects)
- Agent mantém campos duplicados temporariamente (Phase 1 → Phase 2 sync)

### Riscos Aceitos

| Risco | Mitigação |
|-------|-----------|
| Migração pode falhar em produção | Script idempotente + rollback script + validation queries |
| FKs orphanadas durante migração | Transação atômica; validação pós-migração |
| Agent sync desincronizar | Constraint + trigger no Phase 2; testes de sync |
| Performance com tabela maior | Partial index em `active=true`; compound index já coberto pela constraint |

---

## Test Strategy Overview

| Category | Count | Focus |
|----------|-------|-------|
| Unit (Python) | ~15 | Constraints, validations, authorization matrix, sync logic |
| Integration (Migration) | ~7 | Data migration correctness, idempotency, FK integrity |
| E2E (Shell/Curl) | ~25 | All API endpoints, RBAC, multi-tenancy, pagination, HATEOAS |
| E2E (Cypress) | ~3 | Profile type admin view (if applicable) |

### Traceability Matrix (FR ↔ AC ↔ TEST)

| FR | AC | Tests |
|----|-----|-------|
| FR1.1 | AC1.1 | T1.8, T1.9, T1.10 |
| FR1.3 | AC1.4, AC1.5 | T1.1, T1.2, T1.3, T1.11, T1.12 |
| FR1.4 | AC1.2 | T1.4, T1.9 |
| FR1.10 | AC1.6 | T1.14 |
| FR1.12 | AC1.5 | T1.13 |
| FR2.1-2.7 | AC2.1-2.5 | T2.1-T2.6 |
| FR3.1-3.5 | AC3.1-3.4 | T3.1-T3.5 |
| FR4.1-4.4 | AC4.1-4.4 | T4.1-T4.4 |
| FR5.1-5.7 | AC5.1-5.5 | T5.1-T5.7 |
| FR6.1-6.5 | AC6.1-6.4 | T6.1-T6.4 |

---

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Feature 009 (User Onboarding) | Modifies invite flow to accept `profile_id` | Draft (spec complete) |
| `quicksol_estate` module | Hosts profile model, agent model, groups | Existing |
| `thedevkitchen_apigateway` | Auth decorators (`@require_jwt`, `@require_session`, `@require_company`) | Existing |
| ADR-019 | RBAC profile definitions (9 profiles, 3 levels) | Accepted |
| KB-09 | Database best practices (3NF, naming, constraints, indexes, migration) | Reviewed |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Profile** | Cadastro unificado de uma pessoa em uma empresa com um tipo de perfil |
| **Profile Type** | Um dos 9 tipos RBAC: owner, director, manager, agent, prospector, receptionist, financial, legal, portal |
| **Agent Extension** | Modelo `real.estate.agent` com dados de negócio específicos do corretor (comissões, CRECI, etc.) |
| **Compound Unique** | Constraint `UNIQUE(document, company_id, profile_type_id)` — mesma pessoa pode existir em empresas diferentes |
| **Two-step Flow** | Criar perfil (dados cadastrais) → convidar para acesso ao sistema (Feature 009) |
| **Lookup Table** | Tabela normalizada de referência para tipos enumerados (KB-09 §2.1) |
