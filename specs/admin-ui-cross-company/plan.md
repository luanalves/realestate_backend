# Plano: Admin UI — Acesso Cross-Company via Interface Odoo

## Status
Proposto

## Data
2026-06-03

## Resumo

Permitir que usuários do grupo `base.group_system` (superusuários/admins) acessem e modifiquem **todos os dados de todas as empresas** pela interface web do Odoo, sem restrições de multi-tenancy. Este tipo de usuário **só pode ser criado via interface Odoo** (nunca via API).

---

## 1. Referências de ADR (Validação Cruzada)

| ADR | Tema | Impacto neste plano |
|-----|------|---------------------|
| **ADR-008** | Segurança API Multi-Tenancy | Isolamento `company_ids` é **obrigatório na API**, mas admin acessa **via Odoo UI** — API fica bloqueada para ele |
| **ADR-009** | Autenticação Headless | Login via API (`/api/v1/users/login`) é para aplicações headless. Admin **não deve usar** este canal |
| **ADR-011** | Decoradores `@require_jwt` + `@require_session` + `@require_company` | Admin não precisa de `@require_company` pois acessa todas. Mas admin **não usa a API** — logo os decoradores não são impactados |
| **ADR-019** | RBAC Perfis Multi-Tenancy | Define 9 perfis de negócio. Admin (`base.group_system`) é **nível SaaS/infraestrutura**, acima da hierarquia de negócio |
| **ADR-024** | Unificação de Perfis | `InviteService.INVITE_AUTHORIZATION` **não inclui** `base.group_system` como inviter — correto: admin não convida via API |

### Princípios validados

1. **ADR-008 §3**: "Transferências entre empresas devem ser feitas apenas via **interface administrativa**" — exatamente o caso do admin
2. **ADR-019 §Fase 1**: "Perfis pré-definidos via `res.groups`" — `base.group_system` já existe no Odoo core
3. **ADR-019 §Hierarquia**: Admin está acima de `group_real_estate_owner` — é o "SaaS Admin" citado na jornada de onboarding
4. **ADR-008 §5**: Respostas genéricas se aplicam à **API** — na Odoo UI, admin pode ver tudo
5. **ADR-011 §3**: Decoradores obrigatórios se aplicam à **API REST** — Odoo UI usa autenticação web nativa
6. **ADR-024**: `PROFILE_TO_GROUP` não mapeia `admin` → não é possível criar admin via convite (correto)

---

## 2. Diagnóstico do Estado Atual

### 2.1 O que funciona

| Componente | Status | Detalhe |
|------------|--------|---------|
| `ir.model.access.csv` | ✅ OK | `base.group_system` tem CRUD em todos os modelos (`access_system_admin_*`) |
| Menu principal `menu_real_estate_root` | ✅ OK | Sem restrição de grupo — admin vê |
| Invite API | ✅ OK | `INVITE_AUTHORIZATION` não inclui `base.group_system` — admin não cria users via API |

### 2.2 O que está quebrado

#### Problema A: Record Rules bloqueiam o admin

**Causa raiz:** Todas as record rules usam `company_ids` (empresas do usuário) como filtro. O admin (`uid=2`) geralmente está vinculado apenas à `My Company` (`company_id=1`), enquanto dados reais estão em `QuickSol Real Estate` (`company_id=2`+).

**Comportamento do Odoo com record rules:**
- Regras **com grupo específico** (`groups="[(4, ref('group_x'))]"`) — se o admin **não está** no grupo, a regra **não se aplica** a ele. Mas se há uma regra **global** (sem grupo) ou com `[(5,0,0)]`, ela se aplica a todos.
- O superusuário (`SUPERUSER_ID=1`, o usuário `__system__`) bypassa record rules automaticamente. Porém, o `admin` (`uid=2`) **não é** o SUPERUSER_ID — ele é apenas um membro do grupo `base.group_system`.

**Inventário completo de regras que bloqueiam o admin:**

##### Regras GLOBAIS (sem grupo ou `[(5,0,0)]`) — BLOQUEIAM O ADMIN

| # | Arquivo | ID da Regra | Modelo | `noupdate` |
|---|---------|-------------|--------|------------|
| 1 | `proposal_record_rules.xml` | `rule_proposal_company_isolation` | `real.estate.proposal` | `0` |
| 2 | `service_record_rules.xml` | `rule_service_company_isolation` | `real.estate.service` | `0` |
| 3 | `service_record_rules.xml` | `rule_service_tag_company` | `real.estate.service.tag` | `0` |
| 4 | `service_record_rules.xml` | `rule_service_source_company` | `real.estate.service.source` | `0` |
| 5 | `service_record_rules.xml` | `rule_service_settings_company` | `thedevkitchen.service.settings` | `0` |
| 6 | `cms_record_rules.xml` | `rule_cms_page_company` | `thedevkitchen.cms.page` | `1` |
| 7 | `cms_record_rules.xml` | `rule_cms_media_company` | `thedevkitchen.cms.media` | `1` |
| 8 | `cms_record_rules.xml` | `rule_cms_settings_company` | `thedevkitchen.cms.settings` | `1` |

> **Estas são as mais críticas:** regras globais/`[(5,0,0)]` se aplicam a TODOS os usuários, inclusive admin.

##### Regras com grupo `base.group_user` — BLOQUEIAM O ADMIN (admin herda `base.group_user`)

| # | Arquivo | ID da Regra | Modelo | `noupdate` |
|---|---------|-------------|--------|------------|
| 9 | `record_rules.xml` | `rule_property_multi_company` | `real.estate.property` | `1` |
| 10 | `record_rules.xml` | `rule_agent_multi_company` | `real.estate.agent` | `1` |
| 11 | `record_rules.xml` | `rule_lease_multi_company` | `real.estate.lease` | `1` |
| 12 | `record_rules.xml` | `rule_sale_multi_company` | `real.estate.sale` | `1` |
| 13 | `record_rules.xml` | `rule_assignment_multi_company` | `real.estate.agent.property.assignment` | `1` |
| 14 | `record_rules.xml` | `rule_commission_rule_multi_company` | `real.estate.commission.rule` | `1` |
| 15 | `record_rules.xml` | `rule_commission_transaction_multi_company` | `real.estate.commission.transaction` | `1` |
| 16 | `record_rules.xml` | `rule_lease_renewal_history_multi_company` | `real.estate.lease.renewal.history` | `1` |
| 17 | `record_rules.xml` | `rule_profile_multi_company` | `thedevkitchen.estate.profile` | `1` |
| 18 | `goals/record_rules.xml` | `rule_estate_goal_company` | `thedevkitchen.estate.goal` | `0` |

##### Regras com grupos específicos — NÃO bloqueiam admin (admin não está nesses grupos)

| # | Arquivo | ID da Regra | Modelo | Grupos |
|---|---------|-------------|--------|--------|
| - | `credit_check/record_rules.xml` | `rule_credit_check_company` | `thedevkitchen.estate.credit.check` | Owner+Manager+Agent+Receptionist |
| - | `record_rules.xml` | `rule_owner_*`, `rule_agent_*`, etc. | Vários | Grupos específicos de negócio |

> **Nota:** Para `credit_check`, o admin **não está** nos grupos listados, mas como não há regra global nem `base.group_user` para esse modelo, o admin não é bloqueado — ele simplesmente não tem regra aplicada. No Odoo, se NENHUMA record rule se aplica ao usuário (ele não está em nenhum grupo das regras), ele vê **todos os registros** (comportamento padrão). Porém, se houver regra global `[(5,0,0)]` ou com grupo que o admin herda, aí sim é bloqueado.

#### Problema B: Menus restritos invisíveis para admin

| Menu | Groups atuais | Admin vê? |
|------|---------------|-----------|
| `menu_real_estate_lead` | `group_real_estate_agent`, `group_real_estate_manager` | ❌ Não |

#### Problema C: Admin pode fazer login via API

O `user_auth_controller.py` **não bloqueia** `base.group_system` no login. Isso viola o princípio ADR-009 de que a API é para **aplicações headless** e o admin deve operar **apenas via Odoo UI**.

---

## 3. Solução Proposta

### 3.1 Estratégia: Record Rules `[(1,'=',1)]` para `base.group_system`

Para cada modelo que tem record rules bloqueando o admin, criar uma regra **complementar** atribuída ao grupo `base.group_system` com domain `[(1,'=',1)]` (acesso a todos os registros, sem filtro de empresa).

**Justificativa (padrão Odoo nativo):**
- Módulos oficiais como `sale`, `purchase`, `stock` usam esta mesma abordagem
- No Odoo, quando um usuário pertence a múltiplos grupos que têm record rules para o mesmo modelo, as regras são combinadas com **OR** (união)
- Portanto, a regra `[(1,'=',1)]` para `base.group_system` **prevalece** sobre qualquer filtro `company_ids` de outros grupos que o admin herde

**Segurança mantida (ADR-008):**
- O isolamento multi-tenant para perfis de negócio (owner, manager, agent, etc.) **permanece intacto**
- Apenas `base.group_system` ganha acesso cross-company
- Admin **só existe via Odoo UI** — não acessa a API REST

### 3.2 Bloqueio do admin na API (ADR-009)

Adicionar validação no endpoint de login:

```python
# user_auth_controller.py — após verificar user.active
if user.has_group('base.group_system'):
    _logger.warning(f"Admin login attempt via API blocked: {email}")
    AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')
    return request.make_json_response(
        {'error': {'status': 403, 'message': 'Admin users must use Odoo web interface'}},
        status=403
    )
```

**Aderência a ADRs:**
- **ADR-009**: API é para aplicações headless → admin usa Odoo web nativa
- **ADR-008 §4**: Logar tentativas de acesso falhadas → registrar tentativa de login admin via API
- **ADR-008 §5**: Respostas genéricas → retorna 403 sem revelar detalhes internos

> **Nota:** Retornamos 403 (Forbidden) ao invés de 401 porque as credenciais são válidas — o problema é que o canal de acesso (API) não é autorizado para este tipo de usuário. Isso é uma exceção consciente à regra "usar 404 genérico" do ADR-008, que se aplica a recursos não encontrados/inacessíveis; aqui o recurso (endpoint de login) existe, mas o **perfil do usuário** não é compatível com o canal.

### 3.3 Visibilidade de menus

Adicionar `base.group_system` em menus que hoje são restritos a grupos de negócio.

---

## 4. Inventário de Alterações

### 4.1 Arquivos de Record Rules

#### `quicksol_estate/security/record_rules.xml`

Adicionar **ao final** do arquivo (antes de `</data></odoo>`):

```xml
<!-- ===== SYSTEM ADMIN: CROSS-COMPANY ACCESS (Odoo UI only) ===== -->
<!-- ADR-008 §3: Admin acessa via interface administrativa -->
<!-- ADR-019: SaaS Admin opera acima da hierarquia de negócio -->

<record id="rule_admin_all_properties" model="ir.rule">
    <field name="name">System Admin: All Properties (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_agents" model="ir.rule">
    <field name="name">System Admin: All Agents (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_agent"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_leases" model="ir.rule">
    <field name="name">System Admin: All Leases (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_sales" model="ir.rule">
    <field name="name">System Admin: All Sales (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_sale"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_leads" model="ir.rule">
    <field name="name">System Admin: All Leads (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_assignments" model="ir.rule">
    <field name="name">System Admin: All Assignments (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_agent_property_assignment"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_commission_rules" model="ir.rule">
    <field name="name">System Admin: All Commission Rules (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_commission_rule"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_commission_transactions" model="ir.rule">
    <field name="name">System Admin: All Commission Transactions (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_commission_transaction"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_lease_renewal_history" model="ir.rule">
    <field name="name">System Admin: All Lease Renewal History (Cross-Company)</field>
    <field name="model_id" ref="model_real_estate_lease_renewal_history"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_profiles" model="ir.rule">
    <field name="name">System Admin: All Profiles (Cross-Company)</field>
    <field name="model_id" ref="model_thedevkitchen_estate_profile"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_admin_all_companies" model="ir.rule">
    <field name="name">System Admin: All Companies</field>
    <field name="model_id" ref="base.model_res_company"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `quicksol_estate/security/proposal_record_rules.xml`

Adicionar após a regra `rule_proposal_receptionist_readonly`:

```xml
<!-- ============================================================ -->
<!-- 6. System Admin: all proposals, all companies                 -->
<!-- ADR-008 §3 + ADR-019: SaaS Admin cross-company               -->
<!-- ============================================================ -->
<record id="rule_proposal_admin_all" model="ir.rule">
    <field name="name">Proposal: system admin sees all (cross-company)</field>
    <field name="model_id" ref="model_real_estate_proposal"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `quicksol_estate/security/service_record_rules.xml`

Adicionar ao final:

```xml
<!-- ============================================================ -->
<!-- System Admin: all services, tags, sources, settings           -->
<!-- ADR-008 §3 + ADR-019: SaaS Admin cross-company               -->
<!-- ============================================================ -->
<record id="rule_service_admin_all" model="ir.rule">
    <field name="name">Service: system admin sees all (cross-company)</field>
    <field name="model_id" ref="model_real_estate_service"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_service_tag_admin_all" model="ir.rule">
    <field name="name">Service Tag: system admin (cross-company)</field>
    <field name="model_id" ref="model_real_estate_service_tag"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_service_source_admin_all" model="ir.rule">
    <field name="name">Service Source: system admin (cross-company)</field>
    <field name="model_id" ref="model_real_estate_service_source"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_service_settings_admin_all" model="ir.rule">
    <field name="name">Service Settings: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_service_settings"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `thedevkitchen_cms/security/cms_record_rules.xml`

Adicionar ao final:

```xml
<!-- System Admin: all CMS data cross-company -->
<record id="rule_cms_page_admin_all" model="ir.rule">
    <field name="name">CMS Page: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_cms_page"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_cms_media_admin_all" model="ir.rule">
    <field name="name">CMS Media: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_cms_media"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>

<record id="rule_cms_settings_admin_all" model="ir.rule">
    <field name="name">CMS Settings: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_cms_settings"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `thedevkitchen_estate_goals/security/record_rules.xml`

Adicionar ao final:

```xml
<!-- System Admin: all goals cross-company -->
<record id="rule_estate_goal_admin_all" model="ir.rule">
    <field name="name">Estate Goal: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_estate_goal"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `thedevkitchen_estate_credit_check/security/record_rules.xml`

Adicionar ao final:

```xml
<!-- System Admin: all credit checks cross-company -->
<record id="rule_credit_check_admin_all" model="ir.rule">
    <field name="name">Credit Check: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_estate_credit_check"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

#### `thedevkitchen_user_onboarding/security/record_rules.xml`

Adicionar ao final:

```xml
<!-- System Admin: all password tokens cross-company -->
<record id="rule_password_token_admin_all" model="ir.rule">
    <field name="name">Password Token: system admin (cross-company)</field>
    <field name="model_id" ref="model_thedevkitchen_password_token"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

### 4.2 Menus

#### `quicksol_estate/views/real_estate_menus.xml`

```xml
<!-- ANTES -->
<menuitem id="menu_real_estate_lead" ... groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager"/>

<!-- DEPOIS -->
<menuitem id="menu_real_estate_lead" ... groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager,base.group_system"/>
```

### 4.3 API Login Block

#### `thedevkitchen_apigateway/controllers/user_auth_controller.py`

Adicionar validação **após** o check `user.active` e **antes** de invalidar sessões antigas:

```python
# Block admin users from API login (ADR-009: API is for headless apps)
if user.has_group('base.group_system'):
    _logger.warning(f"Admin login attempt via API blocked: {email}")
    AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')
    return request.make_json_response(
        {'error': {'status': 403, 'message': 'Admin users must use Odoo web interface'}},
        status=403
    )
```

---

## 5. Consideração sobre `noupdate`

Algumas record rules estão em blocos `<data noupdate="1">`:

| Módulo | noupdate | Consequência |
|--------|----------|-------------|
| `quicksol_estate/record_rules.xml` | `1` | Regras **não são atualizadas** em `--update` em bases existentes |
| `quicksol_estate/proposal_record_rules.xml` | `0` | ✅ Atualiza normalmente |
| `quicksol_estate/service_record_rules.xml` | `0` | ✅ Atualiza normalmente |
| `thedevkitchen_cms/cms_record_rules.xml` | `1` | Regras **não são atualizadas** |
| `thedevkitchen_estate_goals/record_rules.xml` | `0` | ✅ Atualiza normalmente |
| `thedevkitchen_estate_credit_check/record_rules.xml` | `1` | Regras **não são atualizadas** |
| `thedevkitchen_user_onboarding/record_rules.xml` | `1` | Regras **não são atualizadas** |

### Solução para `noupdate="1"`

As **novas regras admin** serão adicionadas em blocos `<data noupdate="0">` separados dentro do mesmo arquivo XML. Isso garante que as novas regras são criadas no `--update`, sem afetar as regras existentes.

Alternativa: se o bloco `noupdate="0"` não for viável no mesmo arquivo, criar scripts de migração ou inserir via `odoo-init.sh`.

---

## 6. Testes de Validação

### 6.1 Teste Cypress (E2E via Odoo UI)

```
cenário: Admin visualiza dados de todas as empresas
  dado: admin logado na interface Odoo
  quando: acessa Real Estate > Properties
  então: vê propriedades de TODAS as empresas (não apenas My Company)

cenário: Admin acessa todos os menus
  dado: admin logado na interface Odoo  
  quando: abre o menu Real Estate
  então: vê submenus: Properties, Agents, Leads, Assignments, Commission Rules, Leases, Sales

cenário: Admin edita registro de outra empresa
  dado: admin logado na interface Odoo
  quando: abre propriedade da empresa "QuickSol Real Estate"
  então: pode editar e salvar com sucesso
```

### 6.2 Teste Integration (API block)

```bash
# test_admin_api_login_blocked.sh
# Cenário: admin tenta login via API → deve retornar 403
curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin_password"}' \
  | jq '.error.status' 
# Esperado: 403
```

### 6.3 Checklist Manual

- [ ] Admin vê propriedades de todas as empresas na Odoo UI
- [ ] Admin vê propostas de todas as empresas na Odoo UI
- [ ] Admin vê leads de todas as empresas na Odoo UI
- [ ] Admin vê serviços de todas as empresas na Odoo UI
- [ ] Admin vê páginas CMS de todas as empresas na Odoo UI
- [ ] Admin vê metas de todas as empresas na Odoo UI
- [ ] Admin pode editar/criar/deletar registros de qualquer empresa
- [ ] Admin **não consegue** fazer login via API REST (`/api/v1/users/login`)
- [ ] Usuários de negócio (owner, agent, manager) **continuam isolados** por empresa
- [ ] Menus restritos (Leads) visíveis para admin

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Regras `noupdate="1"` não aplicam em bases existentes | Alta | Médio | Usar bloco `noupdate="0"` para novas regras admin |
| Admin acessa API se bloqueio não implementado | Média | Alto | Implementar check em `user_auth_controller.py` + teste |
| Novos módulos futuros esquecem regra admin | Média | Baixo | Adicionar ao checklist de novo módulo (Knowledge Base) |
| Admin cria dados sem `company_id` correto | Baixa | Médio | Odoo UI força seleção de empresa no formulário |

---

## 8. Ordem de Implementação

| Fase | Tarefa | Arquivos | Prioridade |
|------|--------|----------|------------|
| 1 | Record rules `[(1,'=',1)]` para `base.group_system` | 7 arquivos XML | **Alta** |
| 2 | Bloqueio de admin na API de login | `user_auth_controller.py` | **Alta** |
| 3 | Visibilidade de menus para admin | `real_estate_menus.xml` | **Média** |
| 4 | Testes E2E (Cypress) | `cypress/e2e/views/admin_cross_company.cy.js` | **Média** |
| 5 | Teste integration (API block) | `integration_tests/test_admin_api_block.sh` | **Média** |
| 6 | Atualizar Knowledge Base com checklist | `knowledge_base/` | **Baixa** |

---

## 9. Resumo de Aderência às ADRs

| ADR | Regra | Este plano respeita? | Como |
|-----|-------|---------------------|------|
| **ADR-008** | Nunca usar `.sudo()` em queries transacionais | ✅ | Não altera queries — apenas record rules |
| **ADR-008** | Isolamento por `company_ids` obrigatório | ✅ | Isolamento mantido para perfis de negócio; admin é exceção documentada |
| **ADR-008** | Logar tentativas de acesso | ✅ | Login admin via API é logado como falha |
| **ADR-008** | Respostas genéricas | ✅ | 403 sem detalhes internos |
| **ADR-009** | API para aplicações headless | ✅ | Admin bloqueado da API |
| **ADR-011** | Decoradores obrigatórios | ✅ | Não alterados — admin não usa API |
| **ADR-019** | 9 perfis pré-definidos | ✅ | Admin é nível SaaS, acima dos perfis de negócio |
| **ADR-019** | Record rules baseadas em `company_ids` | ✅ | Perfis de negócio mantém isolamento; admin tem regra `[(1,'=',1)]` |
| **ADR-024** | Admin não é criado via invite flow | ✅ | `INVITE_AUTHORIZATION` e `PROFILE_TO_GROUP` não incluem admin |
