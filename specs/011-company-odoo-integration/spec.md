# Feature Specification: Integração do Módulo de Imobiliária com Company do Odoo

**Feature Branch**: `011-company-odoo-integration`  
**Created**: 2025-03-02  
**Status**: Approved  
**Input**: "Integrar modulo de imobiliaria com company do framework Odoo, para que cada imobiliaria seja uma company diferente, e os usuários sejam associados a essas companies (atualmente não tem associação entre usuários e imobiliarias)"

## Problema Atual (Análise do Codebase)

O sistema atual opera com uma **arquitetura paralela** ao mecanismo nativo de multi-company do Odoo:

### Modelo de Imobiliária Isolado

O modelo `thedevkitchen.estate.company` (tabela `thedevkitchen_estate_company`) existe como entidade completamente separada de `res.company`. Ele declara campos próprios para `name`, `email`, `phone`, `mobile`, `website`, `street`, `city`, `state_id`, `zip_code`, `country_id`, `logo` — todos campos que já existem nativamente em `res.company`. Isso causa **duplicação de dados** e impede o uso de funcionalidades nativas do framework.

### Associação Custom de Usuários

A relação entre usuários e imobiliárias é feita por meio de:

- Tabela M2M custom **`thedevkitchen_user_company_rel`** (colunas `user_id`, `company_id`)
- Campo **`estate_company_ids`** em `res.users` — um `Many2many` apontando para `thedevkitchen.estate.company` via essa tabela
- Campo **`main_estate_company_id`** — `Many2one` para a imobiliária principal
- Campo computado **`owner_company_ids`** — filtra `estate_company_ids` apenas para usuários com perfil Owner

O campo nativo `company_ids` do Odoo (`res.users` → `res.company`) **não é usado** para controle de acesso às imobiliárias.

### Record Rules Baseadas em Campo Custom

Todas as regras de isolamento em `record_rules.xml` usam `user.estate_company_ids.ids` no domínio:

- `rule_owner_estate_companies`: `[('id', 'in', user.estate_company_ids.ids)]`
- `rule_owner_properties`: `[('company_ids', 'in', user.estate_company_ids.ids)]`
- `rule_owner_agents`: `[('company_ids', 'in', user.estate_company_ids.ids)]`
- `rule_owner_commission_rules`: `[('company_id', 'in', user.estate_company_ids.ids)]`
- Regras equivalentes para Agent, Manager e demais perfis

Isso **não se beneficia** do mecanismo nativo `[('company_id', 'in', company_ids)]` do Odoo que é otimizado e reconhecido automaticamente pelo framework.

### Middleware Custom

O decorator `@require_company` em `middleware.py` consulta `user.estate_company_ids` diretamente:

```
if not user.estate_company_ids:
    return _error_response(403, 'no_company', ...)
request.company_domain = [('company_ids', 'in', user.estate_company_ids.ids)]
request.user_company_ids = user.estate_company_ids.ids
```

Não utiliza `request.update_env(company=...)` que é o padrão do Odoo para setar o contexto de empresa ativa.

### Modelos Dependentes com Tabelas M2M Custom

Todos os modelos de negócio referenciam `thedevkitchen.estate.company` via tabelas M2M próprias:

| Modelo | Campo | Tabela M2M |
|--------|-------|------------|
| `real.estate.property` | `company_ids` (M2M) | `thedevkitchen_company_property_rel` |
| `real.estate.lease` | `company_ids` (M2M) | `thedevkitchen_company_lease_rel` |
| `real.estate.sale` | `company_ids` (M2M) + `company_id` (M2O) | `thedevkitchen_company_sale_rel` |
| `real.estate.lead` | `company_ids` (M2M) | M2M inline |
| `real.estate.agent` | `company_ids` (M2M) + `main_company_id` (M2O) | M2M inline |
| `real.estate.commission.rule` | `company_id` (M2O) | Many2one direto |
| `real.estate.commission.transaction` | `company_id` (M2O) | Many2one direto |
| `thedevkitchen.estate.profile` | `company_id` (M2O) | Many2one direto |
| `real.estate.property.assignment` | `company_id` (M2O) | Many2one direto |

Nenhum desses modelos expõe um campo `company_id` apontando para `res.company`, impossibilitando record rules nativas.

**Decisão**: Todos os M2M `company_ids` nos modelos de negócio serão migrados para M2O `company_id` apontando para `res.company`. Cada registro pertence a exatamente uma company. Isso elimina as 5 tabelas M2M de relação (property, lease, sale, agent, lead) e habilita record rules nativas `[('company_id', 'in', company_ids)]` sem customização.

### Controllers Afetados

Os seguintes controllers referenciam `estate_company_ids` ou usam `@require_company`:

- **`user_auth_controller.py`** — retorna `estate_company_ids` e `main_estate_company_id` no payload de login
- **`me_controller.py`** — retorna companies do usuário via `estate_company_ids`
- **`property_api.py`** — usa `@require_company` em 5 endpoints
- **`sale_api.py`** — usa `@require_company` em 5 endpoints + consulta `estate_company_ids`
- **`profile_api.py`** — usa `@require_company`
- **`invite_controller.py`** (Feature 009) — usa `@require_company` + filtra por `estate_company_ids`

### Observer Pattern Afetado

O `user_company_validator_observer.py` valida associações usando `estate_company_ids`:
- Verifica se o usuário atual tem permissão para associar usuários às companies via `current_user.estate_company_ids.ids`
- Intercepta writes no campo `estate_company_ids` para validar autorização

---

## Clarifications

### Session 2025-03-02

- Q: Business models (property, lease, sale, agent, lead) currently use M2M `company_ids` to associate records with multiple companies. Should they keep M2M or migrate to M2O `company_id` (one company per record) to enable native Odoo record rules? → A: **M2O only**. Each business record belongs to exactly one company via `company_id = Many2one('res.company')`. All M2M `company_ids` fields on business models are eliminated. Native Odoo record rules `[('company_id', 'in', company_ids)]` apply directly.
- Q: Como distinguir imobiliárias de companies genéricas (ex: company padrão ID=1)? → A: **Boolean flag** `is_real_estate = Boolean(default=False)` em `res.company`. Companies criadas via API imobiliária recebem `True` automaticamente. Endpoints/domínios filtram por `[('is_real_estate', '=', True)]`.
- Q: Campos em `res.company` devem usar prefixo `x_thedevkitchen_`? → A: **Sem prefixo `x_`**. Campos diretos: `cnpj`, `creci`, `legal_name`, `foundation_date`, `is_real_estate`. Padrão idiomático para módulos Odoo custom instalados via código. ADR-004 esclarece que prefixo `thedevkitchen` aplica-se apenas a **nomes de tabelas** e **nomes de módulos**, não a campos em modelos herdados do core.
- Q: Campo `state_id` no modelo custom apontava para `real.estate.state` (custom). `res.company` já possui `state_id` nativo apontando para `res.country.state`. Usar o nativo ou renomear? → A: **Usar `state_id` nativo** (`res.country.state`). O modelo custom `real.estate.state` é eliminado. `res.country.state` já contém os estados brasileiros. Qualquer referência a `real.estate.state` deve ser migrada para `res.country.state`.

---

## Estratégia Escolhida: Herança Direta (`_inherit = 'res.company'`)

Após análise, a estratégia escolhida é **herança direta** — estender `res.company` com os campos imobiliários, **eliminando completamente** o modelo standalone `thedevkitchen.estate.company` e sua tabela `thedevkitchen_estate_company`.

Essa abordagem:

- **Elimina** o modelo `thedevkitchen.estate.company` — não existe mais como `_name` separado
- **Adiciona** campos imobiliários (`is_real_estate`, `cnpj`, `creci`, `legal_name`, `foundation_date`) diretamente em `res.company`
- **Elimina** a tabela `thedevkitchen_estate_company` e todas as 6 tabelas M2M associadas
- **Elimina** a tabela custom `thedevkitchen_user_company_rel` — usa-se `company_ids` nativo
- **Elimina** o campo `estate_company_ids` em `res.users` — substituído por `company_ids` nativo
- **Simplifica** todos os FKs: modelos que apontavam para `thedevkitchen.estate.company` passam a apontar diretamente para `res.company`
- **Migra** todos os M2M `company_ids` nos modelos de negócio para M2O `company_id` — cada registro pertence a uma única company, habilitando record rules nativas
- **Remove** arquivos, views, seeds e testes que referenciam o modelo obsoleto

### Por que `_inherit` e não `_inherits`?

- `_inherits` manteria duas tabelas (uma custom + `res_company`), adicionando complexidade sem ganho — no nosso caso, não há razão para manter a tabela separada
- Estamos em **ambiente de desenvolvimento** — destruição de dados é aceitável, a abordagem mais limpa e nativa é preferível
- `_inherit` adiciona os campos diretamente na tabela `res_company`, que é o **padrão do ecossistema Odoo** para módulos que estendem companies com campos de domínio (ex: `l10n_br` adiciona CNPJ em `res_company`)
- Menos JOINs, menos complexidade, menos manutenção — e compatibilidade total com o mecanismo multi-company nativo

### Nomenclatura de Campos em Modelos Herdados

Campos custom adicionados em `res.company` via `_inherit` usam nomes diretos e legíveis (`cnpj`, `creci`, `legal_name`, `foundation_date`, `is_real_estate`) — sem prefixo `x_` ou `x_thedevkitchen_`. Isso segue o padrão idiomático de módulos Odoo instalados via código (ex: `l10n_br` usa `cnpj_cpf` diretamente em `res.partner`). A ADR-004 será atualizada para esclarecer que o prefixo `thedevkitchen` aplica-se a **tabelas** e **nomes de módulos**, não a campos em modelos herdados do core.

### Comparativo Antes/Depois

| Aspecto | Antes (atual) | Depois (`_inherit`) |
|---------|--------------|---------------------|
| Modelo de imobiliária | `thedevkitchen.estate.company` (standalone) | `res.company` (estendido com campos imobiliários) |
| Tabela | `thedevkitchen_estate_company` | `res_company` (colunas adicionadas) |
| `_name` | `thedevkitchen.estate.company` | `res.company` (original preservado) |
| Campos genéricos | Duplicados (`name`, `email`, `phone`) | Nativos (sem duplicação) |
| Campos imobiliários | Na tabela custom | Na tabela `res_company` — campos diretos (`cnpj`, `creci`, etc.) |
| FK nos modelos de negócio | `Many2one('thedevkitchen.estate.company')` ou `Many2many` | `Many2one('res.company')` (M2O único para todos) |
| M2M nos modelos de negócio | 5 tabelas custom (`thedevkitchen_company_*_rel`) | **Eliminadas** — migradas para M2O `company_id` |
| Associação de usuários | `thedevkitchen_user_company_rel` (custom M2M) | `res_company_users_rel` (nativo Odoo) |
| Campo em `res.users` | `estate_company_ids` (stored M2M) | `company_ids` (nativo) |
| Record rules | `user.estate_company_ids.ids` | `company_ids` (nativo) |
| Middleware | Consulta `estate_company_ids` | Consulta `company_ids` nativo |
| env[] no Python | `env['thedevkitchen.estate.company']` | `env['res.company']` |

---

## Inventário de Limpeza (Remoções Obrigatórias)

### Tabelas a Remover (DROP) — 8 tabelas

| Tabela | Tipo | Motivo |
|--------|------|--------|
| `thedevkitchen_estate_company` | Tabela principal | Modelo eliminado; campos migram para `res_company` |
| `real_estate_state` | Tabela principal | Modelo `real.estate.state` eliminado; usar `res.country.state` nativo |
| `thedevkitchen_user_company_rel` | M2M usuários ↔ companies | Substituída por `res_company_users_rel` (nativo) |
| `thedevkitchen_company_property_rel` | M2M companies ↔ propriedades | Eliminada — substituída por M2O `company_id` no modelo de negócio |
| `thedevkitchen_company_agent_rel` | M2M companies ↔ agentes | Eliminada — substituída por M2O `company_id` no modelo de negócio |
| `thedevkitchen_company_lease_rel` | M2M companies ↔ contratos | Eliminada — substituída por M2O `company_id` no modelo de negócio |
| `thedevkitchen_company_sale_rel` | M2M companies ↔ vendas | Eliminada — substituída por M2O `company_id` no modelo de negócio |
| `real_estate_lead_company_rel` | M2M leads ↔ companies | Eliminada — substituída por M2O `company_id` no modelo de negócio |

### Arquivos a Remover (DELETE) — 8 arquivos

| Arquivo | Conteúdo | Motivo |
|---------|----------|--------|
| `models/company.py` | Modelo standalone `RealEstateCompany` (224 linhas) | Substituído por novo arquivo com `_inherit = 'res.company'` |
| `models/state.py` | Modelo standalone `real.estate.state` | Eliminado; usar `res.country.state` nativo |
| `data/states.xml` | Seed com 27 estados brasileiros para modelo custom | Eliminado; `res.country.state` já contém os estados |
| `views/company_views.xml` | Form, tree, search views para modelo custom | Substituído por views herdadas de `res.company` |
| `data/company_seed.xml` | 3 seed records para modelo custom | Substituído por seeds de `res.company` |
| `tests/unit/test_company_unit.py` | Testes unitários do modelo custom | Reescrever para `res.company` estendido |
| `tests/unit/test_company_validations.py` | Testes de validação CNPJ/email | Reescrever para `res.company` estendido |
| `CLEANUP_TENANT_MIGRATION.md` | Documentação de migração obsoleta | Superseded por esta feature |

### Campos a Remover de `res.users`

| Campo | Tipo | Motivo |
|-------|------|--------|
| `estate_company_ids` | Many2many stored → custom table | Substituído por `company_ids` nativo |
| `main_estate_company_id` | Many2one stored | Substituído por `company_id` nativo |
| `owner_company_ids` | Computed Many2many | Pode ser mantido mas adaptar para filtrar `company_ids` nativo |

### ACLs a Remover (`ir.model.access.csv`)

Todas as 7 linhas referenciando `model_thedevkitchen_estate_company` devem ser removidas — `res.company` já tem ACLs gerenciadas pelo core do Odoo.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Imobiliária É uma `res.company` Nativa (Priority: P1)

Como **Owner** de uma imobiliária, quero que minha imobiliária **seja** uma `res.company` nativa do Odoo com campos imobiliários adicionais, para que a infraestrutura de multi-tenancy, isolamento de dados e gestão de usuários funcione com o mecanismo padrão do framework.

O modelo `thedevkitchen.estate.company` deixa de existir. Em seu lugar, `res.company` é estendido via `_inherit` com campos imobiliários prefixados (`cnpj`, `creci`, `legal_name`, `foundation_date`). Na prática, toda `res.company` pode ser uma imobiliária se os campos imobiliários forem preenchidos.

**Why this priority**: Fundação da qual tudo depende. Sem que a imobiliária seja uma `res.company`, nada funciona: nem associação nativa de usuários, nem record rules nativas, nem contexto de empresa ativa.

**Independent Test**: Criar uma company via `env['res.company'].create(...)` com os campos imobiliários, verificar que os campos estão na tabela `res_company`, e que `company.cnpj` retorna o valor correto.

**Acceptance Scenarios**:

1. **Given** o módulo instalado, **When** um Owner cria uma nova company com nome "Imobiliária Teste", CNPJ "12.345.678/0001-00" e CRECI "CRECI-SP 99999", **Then** um registro em `res_company` é criado com todas essas informações na mesma linha (sem tabela secundária).
2. **Given** uma company existente com CNPJ preenchido, **When** o sistema consulta `company.cnpj`, **Then** o valor é lido diretamente da tabela `res_company`.
3. **Given** uma company sendo criada, **When** nenhuma moeda ou país é especificado, **Then** defaults são aplicados: `currency_id` = BRL, `country_id` = Brasil.
4. **Given** duas companies com CNPJs diferentes, **When** uma tenta usar um CNPJ já existente, **Then** constraint de unicidade impede a operação.
5. **Given** o código anterior usava `env['thedevkitchen.estate.company']`, **When** o código atualizado usa `env['res.company']`, **Then** os mesmos dados e funcionalidades estão disponíveis (sem modelo intermediário).
6. **Given** a tabela `thedevkitchen_estate_company` existia no banco, **When** o reset é executado, **Then** a tabela não é mais criada — os dados estão em `res_company`.
7. **Given** GET /api/v1/states, **When** resposta retornada, **Then** contém 27 estados brasileiros provenientes de `res.country.state`, com shape idêntico ao endpoint pré-migração.
8. **Given** POST /api/v1/companies com `zip_code='01234-567'`, **When** GET /api/v1/companies/:id, **Then** resposta contém `zip_code='01234-567'` (round-trip validado — mapeamento `zip_code`↔`zip` transparente).

---

### User Story 2 — Associação de Usuários via `company_ids` Nativo (Priority: P1)

Como **Owner**, quero que os usuários da minha imobiliária sejam associados via campo nativo `company_ids` do Odoo, para que o framework gerencie automaticamente quais empresas cada usuário pode acessar.

A tabela custom `thedevkitchen_user_company_rel` e o campo `estate_company_ids` são **eliminados**. A associação é feita exclusivamente pelo campo nativo `company_ids` do Odoo (`res_company_users_rel`). O campo `main_estate_company_id` é substituído por `company_id` nativo (empresa ativa do usuário).

**Why this priority**: Igualmente crítica à US1. Sem associar usuários às `res.company`, record rules nativas não funcionam e o isolamento de dados continua dependendo do mecanismo custom.

**Independent Test**: Associar um usuário à company X, verificar que `user.company_ids` inclui X.

**Acceptance Scenarios**:

1. **Given** um usuário sem empresas, **When** ele é associado a uma imobiliária via `company_ids`, **Then** o `company_ids` nativo contém a `res.company` correspondente.
2. **Given** um usuário associado a duas imobiliárias (A e B), **When** o sistema consulta `user.company_ids`, **Then** retorna ambas as companies.
3. **Given** um usuário que perde acesso à imobiliária A, **When** a company A é removida de `company_ids`, **Then** o usuário não tem mais acesso a dados de A.
4. **Given** um novo usuário convidado via Feature 009, **When** o convite é aceito e o set-password completa, **Then** o `company_ids` do novo usuário contém a company da imobiliária que o convidou.
5. **Given** a empresa ativa do usuário (`company_id`), **When** o sistema identifica a imobiliária principal, **Then** é a company ativa — sem campo custom `main_estate_company_id`.
6. **Given** o campo `estate_company_ids` existia em `res.users`, **When** o módulo é atualizado, **Then** esse campo não existe mais.

---

### User Story 3 — Record Rules com Multi-Company Nativo (Priority: P2)

Como **sistema**, quero que todas as regras de isolamento de dados usem o mecanismo nativo `[('company_id', 'in', company_ids)]` do Odoo, para que o isolamento se beneficie das otimizações do framework.

As 15+ record rules em `record_rules.xml` que usam `user.estate_company_ids.ids` são migradas para `company_ids` nativo. Cada modelo de negócio já aponta diretamente para `res.company`, então o campo `company_id` em cada modelo é automaticamente compatível.

**Why this priority**: Impacto direto na segurança multi-tenant. Depende de US1 e US2.

**Independent Test**: Duas imobiliárias com propriedades distintas → user de cada uma só vê suas propriedades.

**Acceptance Scenarios**:

1. **Given** propriedade P1 da imobiliária A e P2 da imobiliária B, **When** usuário de A lista propriedades, **Then** apenas P1 é retornada.
2. **Given** agente AG1 da imobiliária A, **When** ele tenta acessar lead L1 da imobiliária B, **Then** acesso negado pela record rule.
3. **Given** Owner com acesso a A e B, **When** contexto ativo = A, **Then** apenas dados de A exibidos por padrão.
4. **Given** os 9 modelos de negócio, **When** o sistema avalia regras de acesso, **Then** cada um possui campo `company_id` apontando para `res.company` e as record rules usam `[('company_id', 'in', company_ids)]`.
5. **Given** a `res.company` padrão do Odoo (ID=1), **When** não é uma imobiliária (sem CNPJ/CRECI), **Then** nenhum dado de negócio do módulo imobiliário é visível para ela.

---

### User Story 4 — Middleware `@require_company` Adaptado (Priority: P2)

Como **API**, quero que o middleware `@require_company` valide acesso contra `company_ids` nativo e use `request.update_env(company=...)` para setar o contexto de empresa ativa.

O middleware atual consulta `user.estate_company_ids` e seta `request.company_domain` e `request.user_company_ids`. Isso é substituído por validação contra `user.company_ids` nativo + `request.update_env(company=company_id)`.

**Why this priority**: 16+ endpoints usam `@require_company`.

**Independent Test**: Requisições com `X-Company-ID` válido/inválido.

**Acceptance Scenarios**:

1. **Given** usuário com acesso à company X, **When** `X-Company-ID` = ID de X, **Then** requisição autorizada e `self.env.company` = X.
2. **Given** usuário sem acesso à company Y, **When** `X-Company-ID` = ID de Y, **Then** retorna 403.
3. **Given** admin (`base.group_system`), **When** qualquer `X-Company-ID`, **Then** bypass mantido.
4. **Given** `X-Company-ID` inexistente, **When** requisição recebida, **Then** retorna 404.
5. **Given** middleware seta contexto, **When** controllers fazem ORM calls, **Then** `self.env.company` reflete a empresa do header.
6. **Given** `X-Company-ID` = ID de `res.company` válida com `is_real_estate=False`, **When** requisição recebida, **Then** middleware retorna 403 (company existe mas não é imobiliária).

---

### User Story 5 — Controllers Atualizados (Priority: P2)

Como **API**, quero que todos os controllers que referenciam `estate_company_ids` ou `thedevkitchen.estate.company` sejam atualizados para usar `res.company` e `company_ids` nativo.

~144 ocorrências de `thedevkitchen.estate.company` em Python/XML e ~20 em shell scripts devem ser substituídas.

**Why this priority**: Depende de US1 e US2. É trabalho de refatoração extenso mas mecânico.

**Independent Test**: Login → payload com companies correto. Invite → associação via `company_ids` nativo.

**Acceptance Scenarios**:

1. **Given** login com credenciais válidas, **When** resposta retornada, **Then** payload contém companies no mesmo formato (mas obtidas via `company_ids` nativo).
2. **Given** `GET /api/v1/me`, **When** consulta dados, **Then** companies retornadas via `company_ids`.
3. **Given** `POST /api/v1/users/invite`, **When** convite cria usuário, **Then** `company_ids` nativo populado.
4. **Given** `env['thedevkitchen.estate.company']` não existe mais, **When** qualquer controller tenta acessar, **Then** usa `env['res.company']` ao invés.
5. **Given** o observer `user_company_validator`, **When** validação de associação de company, **Then** valida contra `company_ids` nativo (não `estate_company_ids`).

---

### User Story 6 — Atualização de ADRs e Knowledge Base (Priority: P2)

Como **equipe de desenvolvimento**, queremos que a documentação arquitetural reflita a nova arquitetura, para que decisões futuras sejam tomadas com base na realidade do sistema.

6 ADRs e 1 Knowledge Base precisam de atualização para refletir a migração de `thedevkitchen.estate.company` para `_inherit = 'res.company'`.

**Why this priority**: Documentação desatualizada causa decisões incorretas e confusão entre desenvolvedores.

**Independent Test**: Revisão de cada documento para confirmar ausência de referências obsoletas.

**Acceptance Scenarios**:

1. **Given** ADR-004 (Nomenclatura de Módulos e Tabelas), **When** revisado, **Then** esclarece que prefixo `thedevkitchen` aplica-se a **nomes de tabelas** e **nomes de módulos**. Campos em modelos herdados do core usam nomes diretos sem prefixo.
2. **Given** ADR-008 (Multi-Tenancy API), **When** revisado, **Then** referências a `estate_company_ids` substituídas por `company_ids` nativo.
3. **Given** ADR-009 (Auth/JWT), **When** revisado, **Then** referência a `estate_company_ids` na seção "Positivas" atualizada.
4. **Given** ADR-019 (RBAC Multi-Tenancy), **When** revisado, **Then** todas as record rules usam `company_ids` nativo, jornada de onboarding atualizada, `Many2one('thedevkitchen.estate.company')` substituído.
5. **Given** ADR-020 (Observer Pattern), **When** revisado, **Then** exemplos de código do `UserCompanyValidatorObserver` atualizados.
6. **Given** ADR-024 (Profile Unification), **When** revisado, **Then** FK do profile model aponta para `res.company`, Phase 2 atualizada.
7. **Given** KB-07 (Programming in Odoo), **When** revisado, **Then** contém seção sobre padrões de herança (`_inherit` vs `_inherits` vs `_name` + `_inherit`).

---

### User Story 7 — Reset e Seed do Ambiente de Desenvolvimento (Priority: P3)

Como **equipe de desenvolvimento**, queremos um processo automatizado para recriar o banco com a nova estrutura, já que estamos em ambiente dev e destruição de dados é aceitável.

**Why this priority**: Sem dados para migrar. `./reset_db.sh` é o caminho mais limpo.

**Independent Test**: Reset → sistema sobe sem erros → seed companies com campos imobiliários → login funciona.

**Acceptance Scenarios**:

1. **Given** banco com estrutura antiga, **When** `./reset_db.sh` + module update, **Then** banco recriado sem tabela `thedevkitchen_estate_company`.
2. **Given** seed data atualizado, **When** sistema inicializado, **Then** companies seed têm campos `cnpj` e `creci` preenchidos.
3. **Given** módulo atualizado, **When** ORM cria as tabelas, **Then** 7 tabelas obsoletas não são mais criadas.
4. **Given** seeds de usuários, **When** sistema inicializado, **Then** usuários têm `company_ids` nativo populado (sem `estate_company_ids`).

---

### Edge Cases

- **`res.company` padrão (ID=1)**: A company padrão terá `is_real_estate = False`. Endpoints e domínios filtram por `[('is_real_estate', '=', True)]` para excluí-la automaticamente. Não aparece nas listagens de imobiliárias.
- **Exclusão de company com usuários**: O Odoo impede exclusão de `res.company` se houver usuários com ela como `company_id` principal — desassociar primeiro.
- **Usuário sem `company_ids`**: Middleware retorna 403.
- **Módulos de terceiros**: Imobiliárias aparecem como companies normais — intencional e desejável.
- **Agent sync**: `real.estate.agent` tem `_auto_assign_company` e `_sync_company_from_user` que usavam `estate_company_ids` — adaptar para `company_ids` nativo e `company_id` M2O.
- **Observer**: `user_company_validator_observer.py` interceptava writes em `estate_company_ids` — adaptar para `company_ids` nativo.
- **`state_id` resolvido**: Campo `state_id` do modelo custom (apontava para `real.estate.state`) é eliminado. Usa-se o `state_id` nativo de `res.company` (`res.country.state`). O modelo custom `real.estate.state` é eliminado — `res.country.state` já contém os estados brasileiros.
- **Assignment validation**: `assignment.py` atualmente valida `agent.company_id not in property.company_ids` (M2M). Com M2O, a validação simplifica para `agent.company_id != property.company_id`.
- **Record rules simplificadas**: Com M2O `company_id` em todos os modelos, todas as record rules usam o padrão nativo `[('company_id', 'in', company_ids)]` — sem necessidade de customização.
- **Integration test scripts**: 14+ shell scripts enviam payloads JSON-RPC com `thedevkitchen.estate.company` em queries SQL — todos devem ser atualizados.

---

## Inventário de Arquivos a Modificar (82 arquivos)

### Modelos — `quicksol_estate` (15 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| `models/company.py` | **REMOVER** e recriar como `_inherit = 'res.company'` com campos prefixados |
| `models/state.py` | **REMOVER** — modelo `real.estate.state` eliminado, usar `res.country.state` nativo |
| `models/res_users.py` | Remover `estate_company_ids`, `main_estate_company_id`. Adaptar `owner_company_ids` |
| `models/property.py` | **Remover** M2M `company_ids` → adicionar M2O `company_id = Many2one('res.company')`. Migrar `state_id` de `real.estate.state` → `res.country.state` |
| `models/agent.py` | **Remover** M2M `company_ids` + `main_company_id` → M2O `company_id = Many2one('res.company')`. Adaptar sync methods |
| `models/lead.py` | **Remover** M2M `company_ids` → M2O `company_id = Many2one('res.company')` |
| `models/lease.py` | **Remover** M2M `company_ids` → M2O `company_id = Many2one('res.company')` |
| `models/sale.py` | **Remover** M2M `company_ids` → M2O `company_id = Many2one('res.company')` (já tem M2O, remover M2M) |
| `models/commission_rule.py` | `company_id` M2O → `Many2one('res.company')` |
| `models/commission_transaction.py` | `company_id` M2O → `Many2one('res.company')` |
| `models/profile.py` | `company_id` M2O → `Many2one('res.company')` |
| `models/assignment.py` | `company_id` M2O → `Many2one('res.company')` |
| `models/property_owner.py` | Migrar `state_id` de `real.estate.state` → `res.country.state` |
| `models/property_building.py` | Migrar `state_id` de `real.estate.state` → `res.country.state` |
| `models/observers/user_company_validator_observer.py` | Adaptar para validar `company_ids` nativo |

### Controllers — `quicksol_estate` (6 arquivos)

| Arquivo | # Refs | Alteração |
|---------|--------|-----------|
| `controllers/company_api.py` | 9 | `env['thedevkitchen.estate.company']` → `env['res.company']` |
| `controllers/owner_api.py` | 2 | Idem |
| `controllers/sale_api.py` | 1 + `estate_company_ids` | Idem + adaptar `_get_user_company_ids()` |
| `controllers/property_api.py` | 3 | Atualizar refs e strings de erro |
| `controllers/agent_api.py` | 3 | Idem |
| `controllers/master_data_api.py` | 1 | Idem. Endpoint `/states` migrar de `real.estate.state` → `res.country.state` |

### Services — `quicksol_estate` (2 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| `services/assignment_service.py` | 4 refs → `res.company` |
| `services/performance_service.py` | 1 ref → `res.company` |

### Security — `quicksol_estate` (2 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| `security/ir.model.access.csv` | Remover 7 linhas de ACL para `model_thedevkitchen_estate_company` + 5 linhas para `model_real_estate_state` |
| `security/record_rules.xml` | Migrar 15+ regras: `user.estate_company_ids.ids` → `company_ids` nativo |

### Módulos adjacentes (6 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| `thedevkitchen_apigateway/middleware.py` | Reescrever `require_company` para `company_ids` nativo |
| `thedevkitchen_apigateway/controllers/user_auth_controller.py` | Adaptar payload de login |
| `thedevkitchen_apigateway/controllers/me_controller.py` | Adaptar payload de `/me` |
| `thedevkitchen_user_onboarding/models/password_token.py` | `company_id` → `Many2one('res.company')` |
| `thedevkitchen_user_onboarding/controllers/invite_controller.py` | Associar via `company_ids` nativo |
| `thedevkitchen_user_onboarding/services/invite_service.py` | 2 refs → `res.company` |

### Testes (29 arquivos)

| Categoria | # Arquivos | Alteração |
|-----------|------------|-----------|
| API tests | 5 | `env['thedevkitchen.estate.company']` → `env['res.company']` |
| Base test fixtures | 2 | Idem |
| Integration tests (RBAC, CRUD, etc.) | 13 | Idem |
| Observer tests | 3 | Adaptar para `company_ids` nativo |
| Unit tests | 4 (2 removidos + 2 adaptados) | Idem |
| Tests em `thedevkitchen_apigateway` | 2 | Idem |

### Integration Test Scripts — Shell (14 arquivos)

Todos os scripts em `integration_tests/` que enviam payloads com `thedevkitchen.estate.company` ou queries SQL com `thedevkitchen_estate_company` devem ser atualizados.

### Seed Data, Manifest e Views (6 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| `data/company_seed.xml` | **REMOVER** e recriar seeds de `res.company` com campos prefixados |
| `data/states.xml` | **REMOVER** — modelo custom eliminado, `res.country.state` já contém estados brasileiros |
| `data/seed_test_company.xml` | Idem |
| `views/company_views.xml` | **REMOVER** e recriar como inherited views de `res.company` |
| `views/real_estate_menus.xml` | Action → `res.company` |
| `__manifest__.py` | Atualizar referências de data files e dependências |

### Documentação (9 arquivos)

| Arquivo | Alteração |
|---------|-----------|
| ADR-004 | Esclarecer: prefixo `thedevkitchen` para tabelas e módulos apenas (não campos) |
| ADR-008 | `estate_company_ids` → `company_ids` |
| ADR-009 | Atualizar referência na seção "Positivas" |
| ADR-019 | Reescrever record rules, onboarding journey, FK refs |
| ADR-020 | Atualizar exemplos do Observer |
| ADR-024 | Atualizar FK do profile model |
| KB-07 | Adicionar seção sobre padrões de herança Odoo |
| `constitution.md` | Atualizar Principle IV: `estate_company_ids` → `company_ids` nativo (amendment v1.4.1) |
| `docs/architecture/DATABASE_ARCHITECTURE_USERS.md` | 20+ refs ao modelo custom |

---

## ADRs e Knowledge Base — Detalhamento das Alterações

### ADR-004 (Nomenclatura de Módulos e Tabelas) — Impacto ALTO

**Seção afetada**: Regra #2 (`_name` must be `thedevkitchen.*`) e Regra #3 (tabela)

**Alteração**: Esclarecer escopo do prefixo:
> "O prefixo `thedevkitchen` aplica-se a **nomes de tabelas** (ex: `thedevkitchen_estate_company`) e **nomes de módulos** (ex: `thedevkitchen_apigateway`). Ao estender modelos core do Odoo via `_inherit` (sem novo `_name`), o `_name` permanece o original do core (ex: `res.company`, `res.users`). Campos custom adicionados nesses modelos usam nomes diretos e descritivos (ex: `cnpj`, `creci`, `is_real_estate`) — sem prefixo."

### ADR-019 (RBAC Multi-Tenancy) — Impacto ALTO

**Seções afetadas**: Todas as record rules, jornada de onboarding, referências ao modelo

**Alterações**:
- Substituir `user.estate_company_ids.ids` → `company_ids` em todos os exemplos de record rules
- Atualizar jornada de onboarding para usar `company_ids` nativo
- Substituir `Many2one('thedevkitchen.estate.company')` → `Many2one('res.company')` em todos os exemplos

### ADR-024 (Profile Unification) — Impacto ALTO

**Seção afetada**: FK do profile model, Phase 2

**Alteração**: `company_id = fields.Many2one('thedevkitchen.estate.company')` → `fields.Many2one('res.company')`

### ADR-008 (Multi-Tenancy API) — Impacto MÉDIO

**Seção afetada**: Referências a `estate_company_ids`

**Alteração**: Atualizar para `company_ids` nativo

### ADR-020 (Observer Pattern) — Impacto MÉDIO

**Seção afetada**: Exemplos de código do `UserCompanyValidatorObserver`

**Alteração**: Atualizar `estate_company_ids` → `company_ids` nos exemplos de código

### ADR-009 (Auth/JWT) — Impacto BAIXO

**Seção afetada**: Seção "Positivas" menciona `estate_company_ids`

**Alteração**: Atualizar referência

### KB-07 (Programming in Odoo) — Impacto MÉDIO

**Alteração**: Adicionar seção sobre padrões de herança no Odoo:
- `_inherit = 'model'` (extensão in-place, mesma tabela) — para estender modelos core
- `_inherits = {'model': 'field'}` (delegação, tabela separada) — para composição
- `_name = 'new.model'` + `_inherit = 'model'` (novo modelo baseado em outro) — para cópia com modificações

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `res.company` DEVE ser estendido via `_inherit` com campos imobiliários (`is_real_estate`, `cnpj`, `creci`, `legal_name`, `foundation_date`, `description`), adicionados diretamente na tabela `res_company`. O campo `is_real_estate` (Boolean, default=False) DEVE ser o discriminador para identificar companies que são imobiliárias. Companies criadas via API imobiliária DEVEM ter `is_real_estate=True` auto-setado pelo controller, independentemente do corpo da requisição.
- **FR-002**: O modelo standalone `thedevkitchen.estate.company` DEVE ser completamente eliminado — nenhum `_name = 'thedevkitchen.estate.company'` pode existir no código.
- **FR-003**: A tabela `thedevkitchen_estate_company` DEVE ser eliminada. As 6 tabelas M2M associadas DEVEM ser eliminadas.
- **FR-004**: Todos os campos genéricos redundantes (`name`, `email`, `phone`, etc.) DEVEM ser eliminados — `res.company` já os possui nativamente.
- **FR-005**: A tabela custom `thedevkitchen_user_company_rel` DEVE ser eliminada. A associação de usuários DEVE usar exclusivamente `company_ids` nativo.
- **FR-006**: Os campos `estate_company_ids` e `main_estate_company_id` em `res.users` DEVEM ser removidos. Código que referenciava esses campos DEVE usar `company_ids` e `company_id` nativos.
- **FR-007**: Cada modelo de negócio que referenciava `thedevkitchen.estate.company` DEVE usar `company_id = Many2one('res.company')` (M2O). Todos os campos M2M `company_ids` em modelos de negócio (property, lease, sale, lead, agent) DEVEM ser eliminados e substituídos por M2O `company_id`. Cada registro pertence a exatamente uma company. Modelos afetados: `real.estate.property`, `real.estate.lease`, `real.estate.sale`, `real.estate.lead`, `real.estate.agent`, `real.estate.commission.rule`, `real.estate.commission.transaction`, `thedevkitchen.estate.profile`, `real.estate.property.assignment`.
- **FR-008**: Todas as record rules em `record_rules.xml` DEVEM usar o domínio nativo `[('company_id', 'in', company_ids)]`. Nenhuma referência a `user.estate_company_ids` pode permanecer.
- **FR-009**: O middleware `@require_company` DEVE: (a) validar `X-Company-ID` contra `user.company_ids` nativo, (b) setar contexto via `request.update_env(company=...)`, (c) manter bypass para admin.
- **FR-010**: Os controllers que retornam companies no payload DEVEM manter o mesmo formato de resposta JSON, obtendo dados via `company_ids` nativo. O campo `zip_code` da API DEVE ser mapeado bidirecional para o campo `zip` nativo de `res.company` — consumidores da API nunca veem o campo `zip` interno.
- **FR-011**: O controller `invite_controller.py` DEVE associar novos usuários via `company_ids` nativo.
- **FR-012**: O observer `user_company_validator_observer.py` DEVE validar writes em `company_ids` nativo.
- **FR-013**: Constraints de unicidade DEVEM ser mantidas: `UNIQUE(cnpj)` na tabela `res_company`. Violações de unicidade do CNPJ DEVEM retornar HTTP 400 com `{'success': false, 'error': {'code': 'cnpj_duplicate', 'message': 'CNPJ já cadastrado'}}` — NOT 500. O controller DEVE capturar `ValidationError` e `IntegrityError` e converter para resposta estruturada.
- **FR-014**: Os endpoints existentes DEVEM manter os mesmos contratos de entrada/saída — zero breaking changes para consumidores da API. Ver `contracts/company-api.md` para a tabela de mapeamento de campos e documentação before/after por endpoint.
- **FR-015**: O reset/migração DEVE ser automatizado via `reset_db.sh` + module update.
- **FR-016**: 6 ADRs DEVEM ser atualizadas para refletir a nova arquitetura (ADR-004, 008, 009, 019, 020, 024).
- **FR-017**: KB-07 DEVE ser atualizada com documentação sobre padrões de herança do Odoo.
- **FR-018**: As 7 linhas de ACL referenciando `model_thedevkitchen_estate_company` e 5 linhas referenciando `model_real_estate_state` DEVEM ser removidas do `ir.model.access.csv`.
- **FR-019**: O modelo `real.estate.state` (tabela `real_estate_state`) DEVE ser eliminado. Todos os campos `state_id` que apontavam para `real.estate.state` DEVEM ser migrados para `res.country.state`. O arquivo `data/states.xml` DEVE ser removido — `res.country.state` já contém os estados brasileiros. O endpoint `/states` em `master_data_api.py` DEVE usar `res.country.state`.
- **FR-020**: A `constitution.md` Principle IV DEVE ser atualizada: referências a `estate_company_ids` substituídas por `company_ids` nativo. Descrição de Record Rules atualizada para padrão nativo `[('company_id', 'in', company_ids)]`. Amendment v1.4.1 PATCH.

### Key Entities

- **Imobiliária** (agora é `res.company` estendido):
  - **Campos nativos usados**: `name`, `email`, `phone`, `mobile`, `website`, `street`, `street2`, `city`, `state_id`, `zip`, `country_id`, `logo`, `currency_id`, `partner_id`
  - **Campos adicionados**: `is_real_estate` (Boolean, default=False — discriminador), `cnpj` (Char, unique), `creci` (Char), `legal_name` (Char), `foundation_date` (Date)
  - **Constraints**: `UNIQUE(cnpj)` — SQL constraint na tabela `res_company`
  - **Filtro de domínio**: `[('is_real_estate', '=', True)]` para listar apenas imobiliárias

- **Usuário** (`res.users`):
  - **Usa nativamente**: `company_ids` (M2M para `res.company`), `company_id` (empresa ativa)
  - **Remove**: `estate_company_ids`, `main_estate_company_id`
  - **Adapta**: `owner_company_ids` → computed via `company_ids` nativo

- **Modelos de negócio** (property, agent, lead, lease, sale, commission_rule, commission_transaction, profile, assignment):
  - **Todos usam M2O**: `company_id = Many2one('res.company')` — um registro, uma company
  - **M2M eliminados**: `company_ids` M2M removido de property, lease, sale, lead, agent
  - **Record rules**: Domínio nativo `[('company_id', 'in', company_ids)]`

### Assumptions

- Ambiente de desenvolvimento — destruição e recriação total de dados é aceitável. `./reset_db.sh` é o caminho preferido.
- Campos custom em `res.company` usam nomes diretos (`cnpj`, `creci`, `legal_name`, `foundation_date`, `is_real_estate`) — sem prefixo `x_`. Padrão idiomático para módulos Odoo custom instalados via código.
- Defaults para novas companies: `currency_id` = BRL, `country_id` = Brasil.
- Os 9 perfis RBAC existentes continuam com as mesmas permissões — apenas a base de isolamento muda para o mecanismo nativo.
- `state_id` do modelo custom (`real.estate.state`) é eliminado. Usa-se o nativo `state_id` de `res.company` (`res.country.state`). O modelo `real.estate.state` será removido — `res.country.state` já contém os estados brasileiros.
- `company_ids` nativo do Odoo usa a tabela `res_company_users_rel` (colunas `cid`, `user_id`) — não confundir com a tabela custom eliminada.
- A `res.company` default do Odoo (ID=1) não será usada como imobiliária.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `res.company` estendido contém colunas `is_real_estate`, `cnpj`, `creci`, `legal_name`, `foundation_date` na tabela `res_company`. A company padrão (ID=1) tem `is_real_estate = False`.
- **SC-002**: A tabela `thedevkitchen_estate_company` NÃO EXISTE no banco de dados.
- **SC-003**: As 6 tabelas M2M custom NÃO EXISTEM no banco de dados.
- **SC-004**: A tabela `thedevkitchen_user_company_rel` NÃO EXISTE no banco.
- **SC-005**: 100% dos usuários com acesso a imobiliárias possuem as `res.company` correspondentes em `company_ids` nativo. Verificação: `SELECT u.login FROM res_users u LEFT JOIN res_company_users_rel rel ON rel.user_id = u.id WHERE rel.cid IS NULL AND u.active = True` — deve retornar 0 linhas.
- **SC-006**: Todas as 15+ record rules usam `[('company_id', 'in', company_ids)]` — nenhuma referencia `user.estate_company_ids`.
- **SC-007**: Isolamento multi-tenant: 100% de eficácia em testes de isolamento entre imobiliárias. Validado pelos scripts `integration_tests/test_us3_s1.sh` ~ `test_us3_s5.sh`.
- **SC-008**: Todos os endpoints mantêm mesmo formato de resposta JSON — zero breaking changes.
- **SC-009**: Middleware usa `request.update_env(company=...)` e valida contra `company_ids` nativo.
- **SC-010**: 0 ocorrências de `thedevkitchen.estate.company` no código Python/XML como `_name` ou comodel.
- **SC-011**: 0 ocorrências de `estate_company_ids` como campo stored em `res.users`.
- **SC-012**: 6 ADRs atualizadas sem referências obsoletas. Verificação: `grep -r 'estate_company_ids\|thedevkitchen\.estate\.company' docs/ knowledge_base/` deve retornar 0 resultados.
- **SC-013**: KB-07 contém seção sobre padrões de herança Odoo.
- **SC-014**: Reset do banco + module update completa sem erros.
- **SC-015**: A `constitution.md` Principle IV contém referência a `company_ids` nativo, sem referências a `estate_company_ids`. Amendment v1.4.1 PATCH refletido.
