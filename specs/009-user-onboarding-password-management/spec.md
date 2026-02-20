# Feature Specification: User Onboarding & Password Management

**Feature Branch**: `009-user-onboarding-password-management`
**Created**: 2026-02-16
**Status**: Draft
**ADR References**: ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-011, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-022

## Executive Summary

Implementar o fluxo completo de onboarding de usuários e gestão de senhas para todos os 10 perfis do sistema (ADR-019, ADR-024). Quando um usuário autorizado (Owner, Manager ou Agent) cria um novo usuário via API, o sistema envia automaticamente um email de convite com um link seguro e temporário para criação de senha. Adicionalmente, todos os perfis terão acesso ao fluxo de "Esqueci minha senha" para recuperação de acesso. O tempo de validade do link enviado por email será configurável dinamicamente via menu Technical do Odoo, com padrão de 24 horas. Todos os perfis utilizam o mesmo endpoint de login existente (`POST /api/v1/users/login`) e seguem o padrão de cadastro de `res.users` do Odoo, conforme já implementado para o perfil Owner.

---

## Clarifications

### Session 2026-02-16

**Q1: Agent invitando "property_owner" — risco de escalação de privilégio?**
- **R**: Sem risco. Agent pode convidar perfil `property_owner` (`group_real_estate_property_owner`) — Property Owner (dono de imóvel, cliente) é perfil externo (portal) sem privilégios administrativos. Distinto de `owner` (Company Owner). É regra de negócio intencional.

**Q2: Agent invitando "portal" (tenant) — tenant não é `res.users` hoje**
- **R**: Dual record obrigatório. Quando `profile=portal`, o endpoint `/api/v1/users/invite` deve criar simultaneamente:
  1. `res.users` com grupo portal (para acesso ao sistema)
  2. `real.estate.tenant` (entidade de negócio) vinculado via `partner_id`
- Campos obrigatórios do `real.estate.tenant` que não existem no invite genérico devem ser **adicionados como campos obrigatórios condicionais** no endpoint quando `profile=portal`.

**Q3: Login funciona para todos os perfis sem alteração?**
- **R**: Sim. Análise do `auth_controller.py` confirma:
  - `request.session.authenticate()` aceita qualquer `res.users` — sem filtro por grupo
  - JWT payload é genérico (`uid`, `email`, `company_id`, `db`)
  - Sessão Redis não contém dados owner-specific
  - **Nenhuma alteração no endpoint de login é necessária**

**Q4: Endpoint genérico para todos**
- **R**: Todos os perfis usam `POST /api/v1/users/invite`. Campos faltantes nos controllers existentes devem ser obrigatórios no endpoint. Perfis que não estão adequados devem ser adaptados (Owner, Tenant).

**Q5: Document duplicado — tenant existente sem `res.users`**
- **R**: A regra de conflito de `document` para `profile=portal` é **por empresa ativa** (`X-Company-ID`):
  - Se já existe `real.estate.tenant` com mesmo `document` na **mesma empresa ativa** (com ou sem `res.users` vinculado), retornar **409 Conflict** com `{"error": "conflict", "field": "document", "message": "Document already registered in this company"}`.
  - Se o mesmo `document` existir apenas em **outra empresa**, o invite **é permitido** na empresa ativa (não há unicidade global entre empresas).
  - Quando o conflito ocorrer por tenant sem `res.users` na mesma empresa, a resolução é operacional: o administrador deve vincular/corrigir manualmente (menu Odoo ou endpoint de edição de tenant).

**Q6: Declaração explícita de out-of-scope**
- **R**: Declarar explicitamente fora do escopo: self-registration (usuário cria própria conta), social login (Google/Facebook), 2FA/MFA, política de expiração de senha, histórico de senhas (impedir reutilização).

### Session 2026-02-17 (Release Gate Decisions)

- **Escopo multiempresa**: endpoints autenticados operam somente no contexto da empresa ativa enviada em `X-Company-ID`; usuários multiempresa não operam em escopo agregado nesta feature.
- **Isolamento cross-company**: acesso a recurso de outra empresa responde **404 genérico** (sem identificar recurso/empresa).
- **Precedência de erro**: `AuthZ (403)` → `Isolamento (404)` → `Validação (400)`.
- **Anti-enumeration (forgot-password)**: manter paridade entre emails existentes e não existentes com **mesmo status**, **mesmo shape JSON** e **tempo de resposta aproximado**.
- **Race condition de tokens**: em emissões concorrentes para mesmo usuário/tipo, **último token vence**; anteriores devem ser invalidados.
- **Observabilidade**: registrar somente eventos de erro/negação com contexto técnico mínimo, sem dados sensíveis.
- **Performance**: sem meta numérica fixa de latência neste ciclo; requisito é monitorar e evitar regressões relevantes no mesmo ambiente.
- **Rastreabilidade**: manter vínculo explícito `FR` ↔ `AC` ↔ `TEST` para release gate.

---

## Out of Scope

Os seguintes itens estão **explicitamente fora do escopo** desta feature e NÃO devem ser implementados:

| Item | Motivo |
|------|--------|
| **Self-registration** (usuário cria própria conta) | Todos os usuários são convidados por um perfil autorizado |
| **Social login** (Google, Facebook, etc.) | Autenticação via OAuth2/JWT próprio já implementada |
| **2FA / MFA** (autenticação multifator) | Pode ser adicionado em feature futura |
| **Política de expiração de senha** | Senhas não expiram automaticamente nesta versão |
| **Histórico de senhas** (impedir reutilização) | Sem restrição de reutilização de senhas anteriores |
| **Alteração de perfil/grupo** via invite | Invite cria usuário novo; alterar grupo de usuário existente é outra funcionalidade |

---

## User Scenarios & Testing

### User Story 1: Usuário Autorizado Convida Novo Usuário (Priority: P1) 🎯 MVP

**As a** Owner (group_real_estate_owner), Manager (group_real_estate_manager) ou Agent (group_real_estate_agent)
**I want to** criar um novo usuário (conforme minha autorização de perfil) sem definir senha
**So that** o usuário receba um email de convite com link seguro para criar sua própria senha

**Nota Importante**: O cadastro do novo usuário segue o mesmo padrão do Odoo `res.users` já implementado para o perfil Owner (ver `owner_api.py`). Todos os perfis criados são usuários Odoo padrão com grupo de segurança atribuído.

**Acceptance Criteria**:
- [ ] Given Owner/Manager/Agent autenticado, when cria usuário via `POST /api/v1/users/invite` com campos obrigatórios, then usuário é criado como `res.users` SEM senha (bloqueado para login) e email de convite é enviado
- [ ] Given usuário com múltiplas empresas vinculadas, when envia invite com `X-Company-ID`, then operação usa somente a empresa ativa do header (sem escopo agregado)
- [ ] Given `X-Company-ID` ausente, inválido ou não vinculado ao usuário autenticado, when tenta invite, then resposta é 404 genérico (sem exposição de contexto)
- [ ] Given `profile=portal`, when Agent convida tenant, then cria simultaneamente `res.users` (grupo portal) + `real.estate.tenant` vinculado via `partner_id`
- [ ] Given `profile=portal`, when campos obrigatórios de tenant (`document`, `phone`, `birthdate`, `company_id`) faltando, then retorna erro 400 com campos faltantes
- [ ] Given `profile=portal`, when `document` já existe na mesma empresa ativa, then retorna 409 Conflict; when existe apenas em outra empresa, then criação é permitida
- [ ] Given `profile=property_owner`, when Agent convida property owner (dono de imóvel), then cria `res.users` com grupo `group_real_estate_property_owner`
- [ ] Given email de convite enviado, when usuário clica no link, then é redirecionado para página/endpoint de criação de senha
- [ ] Given link de convite válido, when usuário define senha (min 8 chars), then senha é salva e usuário pode fazer login
- [ ] Given link de convite expirado (TTL configurável, padrão 24h), when usuário tenta usá-lo, then recebe erro 410 Gone informando que o link expirou
- [ ] Given link de convite já utilizado, when usuário tenta reutilizá-lo, then recebe erro 410 Gone
- [ ] Given email já existente no sistema, when Owner tenta convidar, then recebe erro 409 Conflict
- [ ] Given empresa diferente do Owner, when acessa dados, then isolamento multi-tenancy é mantido (ADR-008)
- [ ] Given usuário de perfil Agent, when recebe convite, then é atribuído ao grupo `group_real_estate_agent`

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_invite_token_generation()` | Token gerado é único e contém dados corretos | ⚠️ Required |
| Unit | `test_invite_token_expiration()` | Token expira após TTL configurado | ⚠️ Required |
| Unit | `test_password_strength_validation()` | Senha com < 8 chars é rejeitada | ⚠️ Required |
| Unit | `test_email_template_rendering()` | Template renderiza com variáveis corretas | ⚠️ Required |
| E2E (API) | `test_owner_invites_manager()` | Owner cria Manager e email é enviado | ⚠️ Required |
| E2E (API) | `test_manager_invites_agent()` | Manager cria Agent e email é enviado | ⚠️ Required |
| E2E (API) | `test_agent_invites_tenant_dual_record()` | Agent convida tenant: cria `real.estate.tenant` + `res.users` (portal) vinculados via `partner_id` | ⚠️ Required |
| E2E (API) | `test_agent_invites_tenant_missing_fields()` | Convite portal sem campos obrigatórios de tenant retorna 400 | ⚠️ Required |
| E2E (API) | `test_agent_invites_property_owner()` | Agent cria property owner (group_real_estate_property_owner) e email é enviado | ⚠️ Required |
| E2E (API) | `test_set_password_valid_token()` | Criação de senha com token válido | ⚠️ Required |
| E2E (API) | `test_set_password_expired_token()` | Token expirado retorna 410 | ⚠️ Required |
| E2E (API) | `test_set_password_used_token()` | Token já usado retorna 410 | ⚠️ Required |
| E2E (API) | `test_multitenancy_isolation()` | Convite respeita isolamento de empresa | ⚠️ Required |

---

### User Story 2: Usuário Define Senha via Link de Convite (Priority: P1) 🎯 MVP

**As a** novo usuário convidado (qualquer perfil)
**I want to** clicar no link do email e definir minha senha
**So that** eu possa acessar o sistema com minhas credenciais

**Acceptance Criteria**:
- [ ] Given token válido na URL, when `POST /api/v1/auth/set-password` com `token`, `password` e `confirm_password`, then senha é definida
- [ ] Given senha definida com sucesso, when token é marcado como usado, then não pode ser reutilizado
- [ ] Given `password` !== `confirm_password`, when tenta definir senha, then recebe erro 400
- [ ] Given senha com menos de 8 caracteres, when tenta definir, then recebe erro 400 com mensagem clara
- [ ] Given token válido, when senha definida, then resposta inclui confirmação + HATEOAS link para login
- [ ] Given token inválido/inexistente, when tenta definir senha, then recebe erro 404

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_password_confirmation_mismatch()` | Senhas diferentes são rejeitadas | ⚠️ Required |
| Unit | `test_password_minimum_length()` | Senha < 8 chars rejeitada | ⚠️ Required |
| E2E (API) | `test_full_invite_to_login_flow()` | Convite → set password → login com sucesso | ⚠️ Required |
| E2E (API) | `test_set_password_invalid_token()` | Token inexistente retorna 404 | ⚠️ Required |

---

### User Story 3: Usuário Esqueceu a Senha (Priority: P1) 🎯 MVP

**As a** usuário autenticado anteriormente (qualquer perfil)
**I want to** solicitar redefinição de senha quando esqueci
**So that** eu possa recuperar acesso ao sistema sem precisar contatar o administrador

**Acceptance Criteria**:
- [ ] Given email cadastrado no sistema, when `POST /api/v1/auth/forgot-password` com `email`, then email de redefinição é enviado e resposta é 200 (sempre, para não revelar existência do email)
- [ ] Given email NÃO cadastrado, when solicita forgot password, then resposta é 200 (mesma resposta por segurança — anti-enumeration)
- [ ] Given link de redefinição válido, when `POST /api/v1/auth/reset-password` com `token`, `password`, `confirm_password`, then senha é atualizada
- [ ] Given link de redefinição expirado (TTL configurável), when tenta usar, then recebe erro 410 Gone
- [ ] Given link de redefinição já utilizado, when tenta reutilizar, then recebe erro 410 Gone
- [ ] Given múltiplas solicitações de forgot password, when gera novo token, then tokens anteriores do mesmo usuário são invalidados
- [ ] Given usuário inativo (`active=False`), when solicita forgot password, then resposta é 200 (não revela status) mas email NÃO é enviado

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_forgot_password_always_200()` | Resposta é 200 independente do email | ⚠️ Required |
| Unit | `test_reset_token_invalidates_previous()` | Novo token invalida anteriores | ⚠️ Required |
| E2E (API) | `test_forgot_password_valid_email()` | Email cadastrado: token gerado + email enviado | ⚠️ Required |
| E2E (API) | `test_forgot_password_invalid_email()` | Email não cadastrado: 200 mas sem email enviado | ⚠️ Required |
| E2E (API) | `test_reset_password_valid_token()` | Reset com token válido funciona | ⚠️ Required |
| E2E (API) | `test_reset_password_expired_token()` | Token expirado retorna 410 | ⚠️ Required |
| E2E (API) | `test_full_forgot_to_login_flow()` | Forgot → reset → login com nova senha | ⚠️ Required |

---

### User Story 4: Owner/Manager/Agent Reenvia Convite (Priority: P2)

**As a** Owner, Manager ou Agent (conforme matriz de autorização do Endpoint 5)
**I want to** reenviar o email de convite para um usuário que ainda não definiu a senha
**So that** o usuário tenha uma nova chance de ativar sua conta

**Acceptance Criteria**:
- [ ] Given usuário sem senha definida, when `POST /api/v1/users/{id}/resend-invite`, then novo token é gerado, anteriores são invalidados e novo email é enviado
- [ ] Given usuário já com senha definida, when tenta reenviar convite, then recebe erro 400 (usuário já ativo, usar forgot password)
- [ ] Given usuário de outra empresa, when tenta reenviar convite, then recebe erro 404 (isolamento multi-tenancy)
- [ ] Given requisição com múltiplas violações (ex.: perfil sem permissão + empresa incorreta + payload inválido), then a resposta segue precedência AuthZ(403) → Isolamento(404) → Validação(400)

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_resend_invite_pending_user()` | Reenvio gera novo token e invalida anterior | ⚠️ Required |
| E2E (API) | `test_resend_invite_active_user()` | Usuário ativo retorna 400 | ⚠️ Required |
| E2E (API) | `test_resend_invite_multitenancy()` | Isolamento entre empresas | ⚠️ Required |

---

### User Story 5: Configuração Dinâmica de Validade do Link por Email (Priority: P2)

**As a** administrador do sistema (via menu Technical do Odoo)
**I want to** configurar o tempo de validade dos links enviados por email (convite e redefinição de senha)
**So that** eu possa ajustar a segurança conforme a política da organização

**Acceptance Criteria**:
- [ ] Given menu Technical > Configuration > Email Link Settings, when altera tempo de validade do link de convite, then novos emails de convite usam o novo valor de expiração
- [ ] Given menu Technical > Configuration > Email Link Settings, when altera tempo de validade do link de redefinição, then novos emails de redefinição usam o novo valor
- [ ] Given validade padrão de 24 horas, when sistema é instalado, then configuração existe com valor 24h para ambos os tipos de link
- [ ] Given validade configurada em horas, when email é enviado, then link expira no tempo correto
- [ ] Given valores inválidos (0, negativos), when tenta salvar, then validação impede

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_link_ttl_default_24h()` | Validade padrão do link é 24 horas | ⚠️ Required |
| Unit | `test_link_ttl_positive_validation()` | Validade deve ser > 0 | ⚠️ Required |
| E2E (UI) | `cypress: test_settings_menu_loads()` | Menu de configuração carrega sem erros | ⚠️ If has views |

---

### User Story 6: Login Universal para Todos os Perfis (Priority: P1) 🎯 MVP

**As a** usuário de qualquer perfil (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal)
**I want to** fazer login com meu email e senha
**So that** eu possa acessar as funcionalidades do meu perfil

**IMPORTANTE**: O endpoint de login existente (`POST /api/v1/users/login`) em `auth_controller.py` **NÃO deve ser modificado**. Análise do código confirma:
- `request.session.authenticate()` aceita qualquer `res.users` — sem filtro por grupo
- JWT payload genérico: `uid`, `email`, `company_id`, `db`
- Sessão Redis não contém dados owner-specific
- Login funciona nativamente para qualquer `res.users` com senha definida

**Acceptance Criteria**:
- [ ] Given usuário com senha definida de qualquer perfil, when `POST /api/v1/users/login` com email e senha, then login é bem-sucedido (endpoint existente, sem alterações)
- [ ] Given usuário convidado que ainda NÃO definiu a senha, when tenta login, then recebe erro 401 (comportamento natural do Odoo — sem senha = credenciais inválidas)
- [ ] Given usuário inativo (`active=False`), when tenta login, then recebe erro 403 (já implementado)
- [ ] Given qualquer perfil com senha definida, when faz login, then resposta inclui `session_id`, dados do usuário e empresas vinculadas (mesmo formato do Owner)

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_login_all_profiles()` | Login funciona para cada um dos 9 perfis | ⚠️ Required |
| E2E (API) | `test_login_pending_user()` | Usuário sem senha recebe 401 | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Convite de Usuário (Invite)**
- FR1.1: `POST /api/v1/users/invite` é o endpoint genérico para todos os perfis. Cria `res.users` do Odoo (mesmo padrão do Owner) sem senha e dispara email de convite
- FR1.2: Owner, Manager e Agent podem convidar usuários (conforme matriz de autorização abaixo)
- FR1.3: Owner pode convidar qualquer perfil; Manager pode convidar perfis operacionais; Agent pode convidar inquilinos (portal) e donos de imóveis (property_owner)
- FR1.4: Email de convite contém link com token seguro (UUID v4 + hash SHA-256)
- FR1.5: Token de convite é armazenado no banco com status, data de criação e data de expiração
- FR1.6: Validade do link é lida da configuração dinâmica `thedevkitchen.email.link.settings` (padrão 24h)
- FR1.7: Email duplicado retorna 409 Conflict
- FR1.8: CPF/Document duplicado retorna 409 Conflict
- FR1.9: Usuário é criado como `res.users` seguindo o padrão implementado no Owner (`owner_api.py`), com `password=False` e campo `signup_pending=True`, e grupo de segurança atribuído conforme o perfil
- FR1.10: Email utiliza `mail.template` do Odoo para internacionalização futura
- FR1.11: **Caso especial — Perfil `portal` (tenant)**: Quando o invite é para `profile=portal`, o endpoint deve criar simultaneamente: (a) `res.users` com grupo portal; (b) `real.estate.tenant` com `name`, `document`, `email`, `phone`, `birthdate`, `company_ids`. O campo `partner_id` do `real.estate.tenant` deve ser vinculado ao `res.partner` do `res.users` criado, garantindo a ligação entre entidade de negócio e acesso ao sistema. Para este perfil, os campos `document` (CPF/CNPJ), `phone`, `birthdate` e `company_id` são **obrigatórios** no request body.
- FR1.12: **Caso especial — Perfil `property_owner`**: Property Owner (dono de imóvel, cliente) é perfil externo (level=external) distinto de `owner` (Company Owner). O endpoint de invite cria `res.users` com grupo `group_real_estate_property_owner` com `password=False` e envio de email para criação de senha.
- FR1.13: Para perfis que NÃO são `portal`, o campo `document` no request body corresponde ao CPF (validação via `validate_docbr`). Para perfil `portal`, o campo `document` aceita CPF ou CNPJ (validação via `validators.validate_document()`).
- FR1.14: O endpoint opera exclusivamente na empresa ativa recebida em `X-Company-ID`; ausência, invalidez ou falta de vínculo do header resulta em 404 genérico.
- FR1.15: Para `profile=portal`, os campos `document`, `phone`, `birthdate` e `company_id` são obrigatórios **somente** no `POST /api/v1/users/invite` (não aplicável a endpoints de senha/reenvio).
- FR1.16: Conflito de `document` para `portal` é avaliado por empresa ativa: duplicado na mesma empresa retorna 409; duplicado em outra empresa não bloqueia criação.
- FR1.17: Se existir tenant na mesma empresa com mesmo `document` e sem `res.users`, retornar 409 com mensagem explícita de conflito e exigir resolução manual de vínculo.
- FR1.18: A matriz RBAC é avaliada antes das validações de payload; perfis não autorizados retornam 403 independentemente de outros problemas na requisição.

**FR2: Criação de Senha (Set Password)**
- FR2.1: `POST /api/v1/auth/set-password` define senha para token de convite válido
- FR2.2: Senha mínima de 8 caracteres
- FR2.3: `password` e `confirm_password` devem coincidir
- FR2.4: Token é marcado como `used` após uso bem-sucedido
- FR2.5: Token expirado retorna 410 Gone com mensagem clara
- FR2.6: Token já utilizado retorna 410 Gone
- FR2.7: Token inexistente retorna 404
- FR2.8: Após definir senha, campo `signup_pending` é setado como `False`
- FR2.9: Endpoint é público (`# public endpoint`) — não requer `@require_jwt` nem `@require_session`
- FR2.10: Cenários de token devem cobrir, sem ambiguidade: inexistente (404), expirado (410), já usado (410), inválido/malformado (400).

**FR3: Esqueci Minha Senha (Forgot Password)**
- FR3.1: `POST /api/v1/auth/forgot-password` aceita `email` e SEMPRE retorna 200 (anti-enumeration, ADR-008)
- FR3.2: Se email existe e usuário está ativo, gera token e envia email de redefinição
- FR3.3: Se email não existe ou usuário inativo, retorna 200 SEM enviar email
- FR3.4: Tokens anteriores do mesmo usuário são invalidados ao gerar novo
- FR3.5: Endpoint é público (`# public endpoint`)
- FR3.6: Rate limit de 3 solicitações por email por hora (proteção contra abuso)
- FR3.7: A resposta anti-enumeration deve manter paridade entre casos (email existente, inexistente, usuário inativo): mesmo status HTTP, mesmo shape JSON e sem identificação do motivo no payload.
- FR3.8: Para emissões concorrentes de token de reset para o mesmo usuário, somente o token mais recente permanece válido.

**FR4: Redefinição de Senha (Reset Password)**
- FR4.1: `POST /api/v1/auth/reset-password` redefine senha com token válido
- FR4.2: Mesmas validações de senha do FR2 (min 8 chars, confirmação coincidir)
- FR4.3: Token é marcado como `used` após uso
- FR4.4: Token expirado retorna 410 Gone
- FR4.5: Token já utilizado retorna 410 Gone
- FR4.6: Endpoint é público (`# public endpoint`)
- FR4.7: Todas as sessões ativas do usuário são invalidadas após reset (segurança)
- FR4.8: Em reset concorrente, apenas o primeiro consumo válido do token mais recente é aceito; demais tentativas devem falhar como token usado/inválido conforme estado.

**FR5: Reenvio de Convite**
- FR5.1: `POST /api/v1/users/{id}/resend-invite` reenvia email com novo token
- FR5.2: Apenas funciona para usuários com `signup_pending=True`
- FR5.3: Tokens anteriores são invalidados
- FR5.4: Requer `@require_jwt` + `@require_session` + `@require_company`
- FR5.5: Isolamento multi-tenancy — só pode reenviar para usuários da própria empresa
- FR5.6: Usuários multiempresa só podem reenviar no contexto da empresa ativa (`X-Company-ID`), sem escopo agregado.
- FR5.7: Se o alvo estiver fora da empresa ativa, retornar 404 genérico (sem exposição de existência).

**FR6: Configuração Dinâmica de Validade dos Links por Email**
- FR6.1: Modelo `thedevkitchen.email.link.settings` com campos configuráveis
- FR6.2: `invite_link_ttl_hours` — Tempo de validade do link de convite enviado por email (padrão: 24h)
- FR6.3: `reset_link_ttl_hours` — Tempo de validade do link de redefinição de senha enviado por email (padrão: 24h)
- FR6.4: Padrão Singleton (apenas um registro de configuração)
- FR6.5: Acessível via menu Technical > Configuration > Email Link Settings
- FR6.6: Validação: Validade deve ser > 0 e <= 720 horas (30 dias)

**FR7: Templates de Email**
- FR7.1: Template de convite (`mail.template`) com nome, link, expiração
- FR7.2: Template de redefinição de senha com nome, link, expiração
- FR7.3: Templates utilizam `ir.mail_server` para envio (SMTP configurável)
- FR7.4: Idioma padrão: Português (pt_BR)
- FR7.5: Link no email aponta para o frontend headless (URL base configurável)

**FR8: Regras Transversais de Erro, Isolamento e Rastreabilidade**
- FR8.1: Precedência obrigatória de erro para endpoints autenticados: autorização (403) antes de isolamento (404), e isolamento antes de validação de payload (400).
- FR8.2: Respostas de isolamento cross-company devem ser genéricas (`{"error":"not_found"}`), sem revelar ID, empresa, ou existência de recurso.
- FR8.3: Cada requisito funcional deve possuir vínculo de rastreabilidade com ao menos um critério de aceitação e um caso de teste nomeado (`FRx.y` ↔ `AC` ↔ `test_*`).

---

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

**Entity: Password Token**
- **Model Name**: `thedevkitchen.password.token`
- **Table Name**: `thedevkitchen_password_token` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `user_id` | Many2one(res.users) | required, FK, ondelete='cascade' | Usuário associado ao token |
| `token` | Char(64) | required, unique, index | SHA-256 hash do token (nunca armazena o token bruto) |
| `token_type` | Selection | required | `invite` (convite) ou `reset` (redefinição) |
| `status` | Selection | required, default='pending' | `pending`, `used`, `expired`, `invalidated` |
| `expires_at` | Datetime | required | Data/hora de expiração |
| `used_at` | Datetime | | Data/hora em que foi utilizado |
| `ip_address` | Char(45) | | IP de onde foi utilizado (audit) |
| `user_agent` | Char(255) | | User-Agent de onde foi utilizado (audit) |
| `company_id` | Many2one(thedevkitchen.estate.company) | FK | Empresa associada (multi-tenancy) |
| `created_by` | Many2one(res.users) | FK | Quem criou o convite (audit) |
| `active` | Boolean | default=True | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | Data de criação |
| `write_date` | Datetime | auto | Data de atualização |

**SQL Constraints**:
```python
_sql_constraints = [
    ('token_unique', 'unique(token)', 'Token must be unique'),
]
```

**Python Constraints**:
```python
@api.constrains('expires_at')
def _check_expires_at(self):
    for record in self:
        if record.expires_at and record.expires_at <= fields.Datetime.now():
            raise ValidationError('Expiration date must be in the future')

@api.constrains('token_type')
def _check_token_type(self):
    for record in self:
        if record.token_type not in ('invite', 'reset'):
            raise ValidationError('Token type must be invite or reset')
```

**Indexes**:
```python
# Performance indexes for frequent lookups
_sql_constraints = [
    ('token_unique', 'unique(token)', 'Token must be unique'),
]
# Additional index on (user_id, token_type, status) for invalidation queries
# Additional index on (expires_at) for cleanup cron
```

---

**Entity: Email Link Settings (Singleton)**
- **Model Name**: `thedevkitchen.email.link.settings`
- **Table Name**: `thedevkitchen_email_link_settings` (auto-generated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(100) | required, default='Email Link Configuration' | Nome da configuração |
| `invite_link_ttl_hours` | Integer | required, default=24 | Tempo de validade (em horas) do link de convite enviado por email |
| `reset_link_ttl_hours` | Integer | required, default=24 | Tempo de validade (em horas) do link de redefinição de senha enviado por email |
| `frontend_base_url` | Char(255) | required, default='http://localhost:3000' | URL base do frontend headless |
| `max_resend_attempts` | Integer | default=5 | Máximo de reenvios de convite por usuário |
| `rate_limit_forgot_per_hour` | Integer | default=3 | Máximo de solicitações forgot-password por email/hora |

**Python Constraints**:
```python
@api.constrains('invite_link_ttl_hours', 'reset_link_ttl_hours')
def _check_link_ttl_positive(self):
    for record in self:
        if record.invite_link_ttl_hours <= 0 or record.invite_link_ttl_hours > 720:
            raise ValidationError('Invite link validity must be between 1 and 720 hours')
        if record.reset_link_ttl_hours <= 0 or record.reset_link_ttl_hours > 720:
            raise ValidationError('Reset link validity must be between 1 and 720 hours')

@api.model
def get_settings(self):
    """Singleton pattern — returns the single settings record, creating if needed."""
    settings = self.search([], limit=1)
    if not settings:
        settings = self.create({'name': 'Email Link Configuration'})
    return settings
```

---

**Extension: res.users (campo adicional)**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `signup_pending` | Boolean | default=False | Indica se usuário está aguardando criação de senha |

---

**Record Rules** (per ADR-019):
```xml
<!-- Company isolation for password tokens -->
<record id="rule_password_token_company" model="ir.rule">
    <field name="name">Password Token: Company Isolation</field>
    <field name="model_id" ref="model_thedevkitchen_password_token"/>
    <field name="domain_force">[('company_id', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_real_estate_user'))]"/>
</record>
```

---

### API Endpoints (per ADR-007, ADR-009, ADR-011)

#### Endpoint 1: POST /api/v1/users/invite

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/users/invite` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Authorization** | Owner, Manager, Agent (ADR-019) — conforme matriz de autorização |
| **Rate Limit** | N/A (authenticated endpoint) |

**Request Body — Campos Base** (todos os perfis) (per ADR-018):
```json
{
  "name": "string (required, max 255)",
  "email": "string (required, valid email format)",
  "document": "string (required — CPF para perfis internos, CPF ou CNPJ para portal)",
  "profile": "string (required, enum: owner|director|manager|agent|prospector|receptionist|financial|legal|portal|property_owner)",
  "phone": "string (optional para perfis internos, OBRIGATÓRIO para portal)",
  "mobile": "string (optional)"
}
```

**Request Body — Campos Condicionais quando `profile=portal`** (obrigatórios):
```json
{
  "...campos base acima...",
  "phone": "string (REQUIRED — telefone do tenant)",
  "birthdate": "string (REQUIRED — formato YYYY-MM-DD)",
  "company_id": "integer (REQUIRED — ID da empresa imobiliária vinculada ao tenant)",
  "occupation": "string (optional)"
}
```

**Lógica Condicional do Endpoint**:

| Profile | `res.users` | `real.estate.tenant` | Campos extras obrigatórios | Document validation |
|---------|-------------|----------------------|---------------------------|---------------------|
| `portal` | ✅ grupo portal | ✅ criado + vinculado via `partner_id` | `phone`, `birthdate`, `company_id` | CPF ou CNPJ (`validators.validate_document()`) |
| `owner` | ✅ grupo owner | ❌ | nenhum | CPF (`validate_docbr.CPF`) |
| Outros 7 | ✅ grupo respectivo | ❌ | nenhum | CPF (`validate_docbr.CPF`) |

**Response Success (201)** (per ADR-007 HATEOAS):
```json
{
  "success": true,
  "data": {
    "id": 42,
    "name": "João Silva",
    "email": "joao@empresa.com",
    "document": "12345678901",
    "profile": "agent",
    "signup_pending": true,
    "invite_sent_at": "2026-02-16T10:00:00Z",
    "invite_expires_at": "2026-02-17T10:00:00Z"
  },
  "message": "User invited successfully. Email sent to joao@empresa.com",
  "links": [
    {"href": "/api/v1/users/42", "rel": "self", "type": "GET"},
    {"href": "/api/v1/users/42/resend-invite", "rel": "resend_invite", "type": "POST"},
    {"href": "/api/v1/users", "rel": "collection", "type": "GET"}
  ]
}
```

**Response Success para `profile=portal` (201)** — inclui tenant data:
```json
{
  "success": true,
  "data": {
    "id": 42,
    "name": "Maria Souza",
    "email": "maria@email.com",
    "document": "12345678901",
    "profile": "portal",
    "signup_pending": true,
    "invite_sent_at": "2026-02-16T10:00:00Z",
    "invite_expires_at": "2026-02-17T10:00:00Z",
    "tenant_id": 15,
    "tenant": {
      "id": 15,
      "name": "Maria Souza",
      "document": "12345678901",
      "phone": "11999998888",
      "birthdate": "1990-05-15",
      "company_id": 3
    }
  },
  "message": "User invited successfully. Email sent to maria@email.com",
  "links": [
    {"href": "/api/v1/users/42", "rel": "self", "type": "GET"},
    {"href": "/api/v1/tenants/15", "rel": "tenant", "type": "GET"},
    {"href": "/api/v1/users/42/resend-invite", "rel": "resend_invite", "type": "POST"}
  ]
}
```

**Authorization Matrix**:

| Requester Profile | Can Invite Profiles |
|-------------------|---------------------|
| Owner | owner, director, manager, agent, prospector, receptionist, financial, legal, portal |
| Director | Herda Manager (agent, prospector, receptionist, financial, legal) |
| Manager | agent, prospector, receptionist, financial, legal |
| Agent | property_owner (dono de imóvel), portal (inquilino) |
| Others | Nenhum (403 Forbidden) |

**Regras Operacionais de Isolamento**:
- O escopo de execução é sempre a empresa ativa em `X-Company-ID`.
- Usuário com múltiplas empresas vinculadas não obtém escopo global; cada requisição é isolada por empresa ativa.
- Se `X-Company-ID` estiver ausente, inválido ou não vinculado ao usuário, retornar `404 {"error":"not_found"}`.
- Acesso a recursos de outra empresa retorna `404 {"error":"not_found"}` (LGPD/anti-enumeration operacional).
- Ordem de avaliação de erro no endpoint: `403 (AuthZ)` → `404 (Isolamento)` → `400 (Validação)`.

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation error (ADR-018) | `{"error": "validation_error", "details": [...]}` |
| 400 | Invalid profile value | `{"error": "validation_error", "message": "Invalid profile: xyz"}` |
| 400 | Missing portal-required fields | `{"error": "validation_error", "message": "Fields phone, birthdate, company_id are required for portal profile"}` |
| 401 | Missing/invalid JWT (ADR-011) | `{"error": "unauthorized"}` |
| 403 | Insufficient permissions (ADR-019) | `{"error": "forbidden", "message": "Managers cannot invite owners"}` |
| 404 | Company context inválido/incompatível | `{"error": "not_found"}` |
| 409 | Email already exists | `{"error": "conflict", "field": "email"}` |
| 409 | Document already exists in active company | `{"error": "conflict", "field": "document", "message": "Document already registered in this company"}` |

> **Nota sobre falha de email (NFR5)**: Se o envio do email falhar após a criação bem-sucedida do usuário, a API retorna **201** (usuário criado) com campo adicional `"email_status": "failed"` no response. O erro de email é logado mas **não bloqueia** a criação do usuário. O administrador pode usar resend-invite para reenviar.

---

#### Endpoint 2: POST /api/v1/auth/set-password

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/auth/set-password` |
| **Authentication** | None — `# public endpoint` |
| **Authorization** | Anyone with valid token |

**Request Body**:
```json
{
  "token": "string (required, the raw token from email link)",
  "password": "string (required, min 8 chars)",
  "confirm_password": "string (required, must match password)"
}
```

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Password set successfully. You can now log in.",
  "links": [
    {"href": "/api/v1/users/login", "rel": "login", "type": "POST"}
  ]
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Missing fields | `{"error": "validation_error", "details": ["token is required"]}` |
| 400 | Password too short | `{"error": "validation_error", "message": "Password must be at least 8 characters"}` |
| 400 | Passwords don't match | `{"error": "validation_error", "message": "Password and confirmation do not match"}` |
| 404 | Token not found | `{"error": "not_found", "message": "Token not found"}` |
| 410 | Token expired | `{"error": "token_expired", "message": "This link has expired. Please request a new invite."}` |
| 410 | Token already used | `{"error": "token_used", "message": "This link has already been used."}` |

---

#### Endpoint 3: POST /api/v1/auth/forgot-password

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/auth/forgot-password` |
| **Authentication** | None — `# public endpoint` |
| **Rate Limit** | 3 requests per email per hour |

**Request Body**:
```json
{
  "email": "string (required, valid email format)"
}
```

**Response (ALWAYS 200 — anti-enumeration per ADR-008)**:
```json
{
  "success": true,
  "message": "If this email is registered, a password reset link has been sent."
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Missing email | `{"error": "validation_error", "message": "Email is required"}` |
| 400 | Invalid email format | `{"error": "validation_error", "message": "Invalid email format"}` |
| 429 | Rate limit exceeded | `{"error": "rate_limited", "message": "Too many requests. Please try again later."}` |

---

#### Endpoint 4: POST /api/v1/auth/reset-password

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/auth/reset-password` |
| **Authentication** | None — `# public endpoint` |

**Request Body**:
```json
{
  "token": "string (required)",
  "password": "string (required, min 8 chars)",
  "confirm_password": "string (required, must match password)"
}
```

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Password reset successfully. You can now log in with your new password.",
  "links": [
    {"href": "/api/v1/users/login", "rel": "login", "type": "POST"}
  ]
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Validation errors | `{"error": "validation_error", "details": [...]}` |
| 404 | Token not found | `{"error": "not_found", "message": "Token not found"}` |
| 410 | Token expired | `{"error": "token_expired", "message": "This link has expired. Please request a new password reset."}` |
| 410 | Token already used | `{"error": "token_used", "message": "This link has already been used."}` |

---

#### Endpoint 5: POST /api/v1/users/{id}/resend-invite

| Attribute | Value |
|-----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/users/{id}/resend-invite` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) |
| **Authorization** | Owner, Manager, Agent (ADR-019) — conforme matriz de autorização |

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Invite resent successfully to joao@empresa.com",
  "data": {
    "invite_expires_at": "2026-02-17T10:00:00Z"
  }
}
```

**Error Responses**:
| Code | Condition | Response |
|------|-----------|----------|
| 400 | User already has password | `{"error": "bad_request", "message": "User already activated. Use forgot-password instead."}` |
| 401 | Missing/invalid auth | `{"error": "unauthorized"}` |
| 403 | Insufficient permissions | `{"error": "forbidden"}` |
| 404 | User not found, company context inválido ou other company | `{"error": "not_found"}` |

---

### Non-Functional Requirements

**NFR1: Security** (per ADR-008, ADR-011, ADR-017, ADR-019)
- Tokens armazenados como **SHA-256 hash** no banco (nunca plain-text)
- Token bruto enviado apenas no email (HTTPS obrigatório)
- Endpoints autenticados usam decoradores triplos (`@require_jwt` + `@require_session` + `@require_company`)
- Endpoints públicos marcados explicitamente com `# public endpoint`
- Rate limiting em forgot-password (anti-brute-force)
- Resposta genérica em forgot-password (anti-enumeration)
- Invalidação de sessões ativas após reset de senha
- Multi-tenant isolation at database level (company_id)
- RBAC enforcement per user profile
- Audit logging de todas as operações de token (criação, uso, expiração)
- Logging de isolamento/autorização somente em nível de erro, com `correlation_id`, `requester_id`, `active_company_id`, `endpoint` e `reason_code` (sem payload sensível)
- Respostas de erro cross-company não devem revelar existência de recurso, nome de empresa ou identificadores internos

**NFR2: Performance**
- Sem meta numérica fixa de latência neste ciclo; operações de token devem ser monitoradas e não podem apresentar regressão relevante no mesmo ambiente de execução
- Envio de email: assíncrono (não bloqueia resposta da API)
- Database indexes nos campos `token`, `user_id`, `expires_at`
- Cron job para limpeza de tokens expirados (diário)

**NFR7: Traceability**
- Requisitos, critérios de aceitação e testes devem manter mapeamento explícito no padrão `FRx.y` ↔ `AC` ↔ `test_*`
- Mudanças de comportamento de erro/isolamento exigem atualização conjunta de `spec.md`, testes E2E e coleção Postman

**NFR3: Quality** (per ADR-022, Constitution v1.2.0)
- Code must pass: `ruff check` + `black` (per constitution linting standards)
- Pylint score ≥ 8.0/10
- 100% test coverage on validations (ADR-003)
- Zero JavaScript console errors in browser (se houver views)

**NFR4: Data Integrity** (per knowledge_base/09-database-best-practices.md)
- Database normalized to 3NF minimum
- Foreign keys with `ondelete='cascade'` para tokens (se usuário deletado, tokens também)
- Soft delete with `active` field (ADR-015)
- Token status machine: `pending` → `used` | `expired` | `invalidated`

**NFR5: Email Delivery**
- Utilizar `mail.template` + `ir.mail_server` do Odoo
- Fallback: se email falhar, logar erro mas não bloquear criação do usuário
- Template deve renderizar corretamente com variáveis dinâmicas (nome, link, prazo)
- Link base configurável via `frontend_base_url` nas settings

**NFR6: Frontend Compatibility** (per knowledge_base/10-frontend-views-odoo18.md)
- View de configuração segue Odoo 18.0 standards (form view no menu Technical)
- Não usar `attrs` (deprecated em 18.0)
- Usar `<list>` ao invés de `<tree>`

---

## Technical Constraints

### Must Follow (from ADRs & Knowledge Base)

| Source | Requirement | Applied To |
|--------|-------------|------------|
| ADR-003 | 100% test coverage on validations | All constraints |
| ADR-004 | `thedevkitchen_` prefix | Model names, tables |
| ADR-007 | HATEOAS links in responses | Non-public API endpoints |
| ADR-008 | Company isolation | Record rules, invite endpoint |
| ADR-011 | Dual auth decorators | Authenticated endpoints |
| ADR-015 | Soft delete pattern | Token model |
| ADR-018 | Schema validation | Input validation |
| ADR-019 | RBAC enforcement | Authorization matrix |
| ADR-022 | Linting standards | All code |
| KB-09 | 3NF database normalization | Token model |
| KB-10 | Odoo 18.0 view standards | Settings view |

### Architecture Patterns

- **Controller Pattern**: Per `.github/instructions/controllers.instructions.md`
- **Testing Pattern**: Per `.github/instructions/test-strategy.instructions.md`
- **Token Security**: SHA-256 hash em banco, token bruto apenas em email/URL
- **Singleton Pattern**: Settings model com `get_settings()`
- **Dual Record Creation**: Para `profile=portal`, criação atômica de `res.users` + `real.estate.tenant` em uma mesma transação

### Token Security Architecture

```
[Invite Flow]
1. API gera UUID v4 (raw_token)
2. Calcula SHA-256(raw_token) → stored_hash
3. Salva stored_hash no banco (thedevkitchen.password.token)
4. Envia raw_token na URL do email: {frontend_base_url}/set-password?token={raw_token}
5. Usuário clica no link → frontend envia raw_token para API
6. API calcula SHA-256(raw_token) → compara com stored_hash
7. Se match: define senha, marca token como used

[Invite Flow — Portal (Dual Record)]
1-7. Mesmo fluxo acima
Extra: Antes do step 3, cria real.estate.tenant vinculado ao res.users via partner_id
       Se qualquer step falhar, rollback da transação inteira (atômico)

[Forgot Password Flow]
1. API gera UUID v4 (raw_token)
2. Invalida todos tokens anteriores do usuário (type=reset, status=pending)
3. Calcula SHA-256(raw_token) → stored_hash
4. Salva stored_hash no banco
5. Envia raw_token na URL do email: {frontend_base_url}/reset-password?token={raw_token}
6. Mesma validação do invite flow
7. Após reset: invalida todas as sessões ativas do usuário
```

### Profile Mapping (para campo `profile` do endpoint invite)

| Profile Value | Odoo Group XML ID | Dual Record | Document Validation |
|---------------|-------------------|-------------|---------------------|
| `owner` | `quicksol_estate.group_real_estate_owner` | ❌ `res.users` only | CPF only |
| `director` | `quicksol_estate.group_real_estate_director` | ❌ `res.users` only | CPF only |
| `manager` | `quicksol_estate.group_real_estate_manager` | ❌ `res.users` only | CPF only |
| `agent` | `quicksol_estate.group_real_estate_agent` | ❌ `res.users` only | CPF only |
| `prospector` | `quicksol_estate.group_real_estate_prospector` | ❌ `res.users` only | CPF only |
| `receptionist` | `quicksol_estate.group_real_estate_receptionist` | ❌ `res.users` only | CPF only |
| `financial` | `quicksol_estate.group_real_estate_financial` | ❌ `res.users` only | CPF only |
| `legal` | `quicksol_estate.group_real_estate_legal` | ❌ `res.users` only | CPF only |
| `portal` | `quicksol_estate.group_real_estate_portal_user` | ✅ `res.users` + `real.estate.tenant` | CPF or CNPJ |

---

## Success Criteria

### Backend
- [ ] All user stories implemented and tested
- [ ] 100% unit test coverage on validations (ADR-003)
- [ ] E2E API tests for all critical flows (invite, set-password, forgot, reset, resend)
- [ ] Portal invite creates dual record (`res.users` + `real.estate.tenant`) correctly linked
- [ ] Owner invite creates `res.users` with `group_real_estate_owner` without password
- [ ] Multi-company isolation verified
- [ ] API documented in OpenAPI/Swagger (ADR-005)
- [ ] Postman collection updated (ADR-016)
- [ ] Code quality: Pylint ≥ 8.0, all linters passing (ADR-022)
- [ ] Security requirements validated (token hashing, rate limiting, anti-enumeration)
- [ ] Email templates functional with SMTP server configured
- [ ] Validade do link por email configurável via menu Technical > Email Link Settings

### Frontend (Settings View Only)
- [ ] Settings view follows Odoo 18.0 standards (KB-10)
- [ ] Cypress E2E tests for settings menu
- [ ] Manual browser test passed (no "Oops!" errors)
- [ ] Zero JavaScript console errors

### Documentation
- [ ] Constitution feedback analyzed and documented

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| Token-based onboarding | UUID + SHA-256 hash para convites seguros | Security Requirements | High |
| Public endpoint pattern | Endpoints sem autenticação com `# public endpoint` | Security Requirements | Medium |
| Anti-enumeration response | Forgot-password sempre retorna 200 | Security Requirements | High |
| Singleton configuration model | Email Link Settings acessível via Technical menu | Development Workflow | Medium |
| Email template integration | `mail.template` para notificações transacionais | New Section: Email & Notifications | Medium |
| Rate limiting pattern | Controle de taxa em endpoints públicos | Security Requirements | High |
| Dual record creation | Criação atômica de `res.users` + entidade de negócio para perfis portal | Architecture Patterns | High |

### New Entities/Relationships

| Entity | Related To | Relationship Type | Notes |
|--------|-----------|-------------------|-------|
| `thedevkitchen.password.token` | `res.users` | N:1 (muitos tokens para 1 usuário) | Tokens de convite e redefinição |
| `thedevkitchen.email.link.settings` | N/A | Singleton | Configuração global de validade dos links por email |
| `res.users` (extended) | `thedevkitchen.password.token` | 1:N | Campo `signup_pending` adicionado |
| `real.estate.tenant` | `res.users` (via `partner_id`) | 1:1 | Vínculo tenant ↔ usuário portal |

### Architectural Decisions

| Decision | Rationale | ADR Required? |
|----------|-----------|---------------|
| SHA-256 hash do token no banco | Prevenção contra vazamento de tokens se banco for comprometido | No — segue práticas padrão de segurança |
| Rate limiting em endpoints públicos | Proteção contra brute-force e abuso | Yes — ADR-023: Rate Limiting Strategy |
| Anti-enumeration via resposta genérica | Prevenir descoberta de emails cadastrados (OWASP) | No — segue ADR-008 princípio 5 (respostas genéricas) |
| Envio de email assíncrono | Não bloquear resposta da API aguardando SMTP | No — padrão do Odoo `mail.template.send_mail()` |
| Configuração via menu Technical | Flexibilidade sem redeploy, acessível para SysAdmin | No — padrão Odoo para configurações |
| Dual record para portal | Tenant precisa existir como entidade de negócio (`real.estate.tenant`) E ter acesso ao sistema (`res.users`) | No — requisito funcional, não decisão arquitetural |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: MINOR (1.3.0)
- **Sections to Update**:
  - [ ] Security Requirements — Adicionar padrão de token hashing e anti-enumeration
  - [ ] New Section: Email & Notifications — Documentar padrão de templates transacionais
  - [ ] Quality & Testing Standards — Adicionar testes de endpoints públicos
  - [ ] Development Workflow — Documentar padrão de Singleton settings
  - [ ] Architecture Patterns — Documentar padrão dual record para entidades com acesso portal

---

## Assumptions & Dependencies

**Assumptions**:
- SMTP server será configurado via `ir.mail_server` do Odoo (responsabilidade do SysAdmin)
- Frontend headless (Next.js/React) terá páginas `/set-password` e `/reset-password` para consumir os endpoints
- Todos os 9 grupos Odoo do ADR-019 já estão implementados em `security/groups.xml`
- Redis está disponível para sessões (conforme docker-compose.yml)
- `validate_docbr` está instalado para validação de CPF
- Modelo `real.estate.tenant` já existe com campo `partner_id` (Many2one para `res.partner`) que será usado para vincular tenant à conta de usuário portal
- Validadores existentes (`validators.validate_document()`, `validators.normalize_document()`) suportam CPF e CNPJ
- O endpoint de login (`POST /api/v1/users/login`) funciona para todos os perfis sem alteração (confirmado via análise de código)

**Dependencies**:
- Existing modules: `thedevkitchen_apigateway` (auth, middleware, sessions), `quicksol_estate` (groups, models, tenant)
- External services: PostgreSQL 14+, Redis 7+, SMTP server
- Authentication: OAuth2 via `thedevkitchen_apigateway`
- Odoo core: `mail` module (mail.template, ir.mail_server)
- Python packages: `uuid`, `hashlib` (stdlib — sem dependências extras)
- Existing models: `real.estate.tenant` (para dual record com portal)

---

## Implementation Phases

### Phase 1: Foundation (Models & Token Logic)
- Modelo `thedevkitchen.password.token` com constraints e indexes
- Modelo `thedevkitchen.email.link.settings` (Singleton)
- Extensão `res.users` com campo `signup_pending`
- Service `PasswordTokenService` (geração, validação, invalidação de tokens)
- Unit tests para validações e token lifecycle

### Phase 2: API Layer (Controllers)
- `POST /api/v1/users/invite` (com authorization matrix + lógica condicional para portal)
  - Fluxo padrão: cria `res.users` com grupo
  - Fluxo portal: cria `res.users` + `real.estate.tenant` (dual record, atômico)
  - Validação condicional de campos obrigatórios por perfil
- `POST /api/v1/auth/set-password` (public endpoint)
- `POST /api/v1/auth/forgot-password` (public endpoint + rate limiting)
- `POST /api/v1/auth/reset-password` (public endpoint)
- `POST /api/v1/users/{id}/resend-invite`
- Schema validation para todos os endpoints
- Audit logging

### Phase 3: Email Integration
- Email templates (`mail.template`) para convite e redefinição
- Integração com `ir.mail_server`
- Frontend URL configurável via settings

### Phase 4: Settings View (Odoo 18.0)
- Form view para `thedevkitchen.email.link.settings`
- Menu entry em Technical > Configuration > Email Link Settings
- Record rules e ACLs

### Phase 5: Testing & Quality
- E2E test scenarios (shell/curl)
- Unit tests para services e validações
- Dual record creation tests (portal invite)
- Multi-tenancy isolation tests
- Code quality validation (lint)
- Cypress E2E para settings view

### Phase 6: Documentation & Artifacts
- Swagger/OpenAPI update
- Postman collection update
- Constitution update

---

## Artifacts to Generate

After specification approval, generate:

1. **OpenAPI/Swagger** (per ADR-005)
   - Location: `docs/openapi/009-user-onboarding.yaml`
   - Include all 5 endpoints with examples
   - Document conditional request body for portal profile

2. **Postman Collection** (per ADR-016)
   - Location: `docs/postman/feature009_user_onboarding_v1.0_postman_collection.json`
   - Include invite flow (standard + portal dual record), set-password, forgot-password, reset-password
   - Test scripts for token extraction

3. **Constitution Update** (MANDATORY — new patterns introduced)
   - Location: `.specify/memory/constitution.md`
   - Add token hashing pattern, anti-enumeration, email templates, dual record
   - Version bump: 1.2.0 → 1.3.0

4. **Copilot Instructions Update** (if tactical rules change)
   - Add `# public endpoint` pattern for unauthenticated endpoints

---

## Validation Checklist

### Backend Validation
- [ ] All ADR requirements referenced and followed
- [ ] Knowledge base patterns applied
- [ ] Multi-tenancy correctly specified (ADR-008)
- [ ] Security properly defined (ADR-011, ADR-017, ADR-019)
- [ ] Test strategy complete — unit + E2E API (ADR-003)
- [ ] API follows REST + HATEOAS standards (ADR-007)
- [ ] Database design normalized — 3NF minimum
- [ ] Error handling specified (ADR-018)
- [ ] Code quality requirements defined (ADR-022)
- [ ] Token security architecture documented (SHA-256 hashing)
- [ ] Rate limiting specified for public endpoints
- [ ] Anti-enumeration pattern applied (forgot-password)
- [ ] Portal dual record creation specified (res.users + real.estate.tenant)
- [ ] Conditional field validation for portal profile documented
- [ ] Owner profile invite without password documented

### Frontend Validation (Settings View)
- [ ] Views follow Odoo 18.0 standards (KB-10, ADR-001)
- [ ] No `attrs` attribute used
- [ ] Used `<list>` instead of `<tree>` (if applicable)
- [ ] Cypress E2E tests specified for settings view
- [ ] Manual browser testing procedure defined
