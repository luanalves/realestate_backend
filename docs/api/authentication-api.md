# API de Autenticação e Usuários

> **Base URL:** `https://{domain}`  
> **Versão:** v1  
> **Formato:** JSON  
> **CORS:** habilitado em todos os endpoints

---

## Sumário

- [Pré-requisito: Criar Aplicação OAuth2 no Odoo](#0-pré-requisito-criar-aplicação-oauth2-no-odoo)
- [Autenticação OAuth2](#1-autenticação-oauth2)
- [Login e Sessão](#2-login-e-sessão)
- [Gerenciamento de Senha (autenticado)](#3-gerenciamento-de-senha-autenticado)
- [Gerenciamento de Senha (público)](#4-gerenciamento-de-senha-público)
- [Convite de Usuários](#5-convite-de-usuários)
- [Perfis (Profiles)](#6-perfis-profiles)
- [Usuário Autenticado](#7-usuário-autenticado)
- [Headers Padrão](#headers-padrão)
- [Códigos de Erro](#códigos-de-erro)

---

## 0. Pré-requisito: Criar Aplicação OAuth2 no Odoo

Antes de usar qualquer endpoint autenticado, é necessário criar uma **Aplicação OAuth2** no painel administrativo do Odoo para obter o `client_id` e o `client_secret`.

---

### Passo 1 — Acessar o Odoo em modo debug com usuário admin

Acesse a aplicação pelo navegador adicionando o parâmetro `?debug=1` na URL:

```
https://{domain}/odoo?debug=1
```

Faça login com o usuário **admin**.

<!-- SCREENSHOT: tela de login do Odoo com URL contendo ?debug=1 -->
> 📸 _[inserir print aqui]_

---

### Passo 2 — Navegar até Api Gateway → Oauth Applications

Com o modo debug ativo, o menu **Technical** ficará disponível na barra de navegação superior.

Acesse:

```
Technical → Api Gateway → Oauth Applications
```

<!-- SCREENSHOT: menu Technical expandido mostrando "Api Gateway > Oauth Applications" -->
> 📸 _[inserir print aqui]_

---

### Passo 3 — Criar nova aplicação (New)

Na listagem de aplicações, clique em **New** para criar uma nova aplicação OAuth2.

Preencha os campos:

| Campo | Valor sugerido |
|---|---|
| **Name** | Nome da sua aplicação (ex: `Postman - Dev`) |
| **Active** | ✅ marcado |

Após preencher, clique em **Save**.

<!-- SCREENSHOT: formulário de criação da aplicação OAuth2 com os campos preenchidos -->
> 📸 _[inserir print aqui]_

---

### Passo 4 — Capturar Client ID e Client Secret

Após salvar, o Odoo exibirá o `client_id` e o `client_secret` gerados para a aplicação.

> ⚠️ **Atenção:** o `client_secret` é exibido **apenas uma vez**. Copie e armazene em local seguro antes de sair da página.

<!-- SCREENSHOT: registro salvo exibindo client_id e client_secret -->
> 📸 _[inserir print aqui]_

Use esses valores no endpoint de geração de token:

```json
{
  "grant_type": "client_credentials",
  "client_id": "COLE_AQUI_O_CLIENT_ID",
  "client_secret": "COLE_AQUI_O_CLIENT_SECRET"
}
```

---

---

## Headers Padrão

| Header | Quando usar |
|---|---|
| `Authorization: Bearer {access_token}` | Todos os endpoints autenticados |
| `X-Session-ID: {session_id}` | Obtido após login, obrigatório nos endpoints com `@require_session` |
| `X-Company-ID: {company_id}` | Obrigatório nos endpoints com `@require_company` |
| `Content-Type: application/json` | Em todas as requisições com body |

---

## 1. Autenticação OAuth2

### 1.1 Obter Token de Acesso (Client Credentials)

Gera um Bearer token JWT para autenticar as chamadas à API.

```
POST /api/v1/auth/token
```

**Autenticação:** Nenhuma (public endpoint)

**Request Body:**
```json
{
  "grant_type": "client_credentials",
  "client_id": "string",
  "client_secret": "string"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "string"
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `unsupported_grant_type` | Apenas `client_credentials` suportado |
| 400 | `invalid_request` | `client_id` ou `client_secret` ausente |
| 401 | `invalid_client` | Credenciais inválidas |
| 500 | `server_error` | Erro interno |

---

### 1.2 Renovar Token (Refresh)

```
POST /api/v1/auth/refresh
```

**Autenticação:** Nenhuma (public endpoint)

**Request Body:**
```json
{
  "grant_type": "refresh_token",
  "refresh_token": "string",
  "client_id": "string",
  "client_secret": "string"
}
```

> `grant_type`, `client_id` e `client_secret` são opcionais, mas recomendados.

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "string"
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `invalid_request` | `refresh_token` ausente |
| 401 | `invalid_grant` | Token inválido ou revogado |
| 401 | `invalid_client` | Credenciais do cliente inválidas |

---

### 1.3 Revogar Token

```
POST /api/v1/auth/revoke
```

**Autenticação:** Nenhuma (public endpoint)

> Conforme RFC 7009: sempre retorna `200` mesmo que o token não seja encontrado.

**Request Body** (ou via header `Authorization: Bearer {token}`):
```json
{
  "token": "string"
}
```

**Response 200:**
```json
{
  "success": true
}
```

---

## 2. Login e Sessão

### 2.1 Login

Autentica o usuário com email e senha. Invalida sessões anteriores e cria uma nova sessão de API.

```
POST /api/v1/users/login
```

**Autenticação:** `@require_jwt` — requer `Authorization: Bearer {access_token}`

**Request Body:**
```json
{
  "email": "usuario@empresa.com",
  "password": "string"
}
```

> `login` é aceito como alias de `email`.

**Response 200:**
```json
{
  "session_id": "abc123def456...",
  "user": {
    "id": 42,
    "name": "João Silva",
    "email": "usuario@empresa.com",
    "login": "usuario@empresa.com",
    "phone": "+55 11 99999-9999",
    "mobile": "",
    "companies": [
      {
        "id": 2,
        "name": "QuickSol Real Estate",
        "cnpj": "12.345.678/0001-90",
        "email": "contato@empresa.com",
        "phone": "+55 11 3333-4444",
        "website": "https://empresa.com"
      }
    ],
    "default_company_id": 2
  }
}
```

**Erros:**

| Status | Mensagem | Descrição |
|---|---|---|
| 400 | `Invalid JSON body` | Body malformado |
| 401 | `Invalid credentials` | Email ou senha incorretos |
| 403 | `User inactive` | Usuário desativado |
| 500 | `Internal server error` | Erro interno |

---

### 2.2 Logout

Invalida a sessão de API ativa do usuário.

```
POST /api/v1/users/logout
```

**Autenticação:** `@require_jwt` + `@require_session`

**Headers obrigatórios:**
```
Authorization: Bearer {access_token}
X-Session-ID: {session_id}
```

**Request Body:** Nenhum

**Response 200:**
```json
{
  "message": "Logged out successfully"
}
```

---

## 3. Gerenciamento de Senha (autenticado)

### 3.1 Atualizar Perfil do Usuário

Atualiza dados do usuário autenticado (nome, email, telefone).

```
PATCH /api/v1/users/profile
```

**Autenticação:** `@require_jwt` + `@require_session`

**Request Body** (todos os campos são opcionais):
```json
{
  "name": "string",
  "email": "novo@email.com",
  "phone": "+55 11 99999-9999",
  "mobile": "+55 11 88888-8888"
}
```

**Response 200:**
```json
{
  "user": { ... },
  "message": "Profile updated successfully"
}
```

**Erros:**

| Status | Mensagem | Descrição |
|---|---|---|
| 400 | `No fields to update` | Nenhum campo válido enviado |
| 400 | `Name cannot be empty` | Nome vazio |
| 400 | `Invalid email format` | Formato de email inválido |
| 409 | `Email already in use` | Email pertence a outro usuário |

---

### 3.2 Alterar Senha (usuário autenticado)

Altera a senha do usuário autenticado, exigindo a senha atual.

```
POST /api/v1/users/change-password
```

**Autenticação:** `@require_jwt` + `@require_session`

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```

> `old_password` é aceito como alias de `current_password`. `confirm_password` é opcional mas recomendado.

**Response 200:**
```json
{
  "message": "Password changed successfully"
}
```

**Erros:**

| Status | Mensagem | Descrição |
|---|---|---|
| 400 | `Current password is required` | Campo obrigatório ausente |
| 400 | `New password is required` | Campo obrigatório ausente |
| 400 | `Password must be at least 8 characters long` | Senha muito curta |
| 400 | `New password and confirmation do not match` | Confirmação divergente |
| 401 | `Current password is incorrect` | Senha atual errada |

---

## 4. Gerenciamento de Senha (público)

> Endpoints públicos — **não** requerem autenticação.

### 4.1 Definir Senha (via link de convite)

Utilizado quando o usuário acessa o link de convite recebido por email para definir sua senha pela primeira vez.

```
POST /api/v1/auth/set-password
```

**Autenticação:** Nenhuma (public endpoint)

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
  "password": "MinhasSenha123",
  "confirm_password": "MinhasSenha123"
}
```

> `token` deve ser exatamente 32 caracteres hexadecimais minúsculos (UUID v4 hex).  
> `password` deve ter no mínimo 8 caracteres.

**Response 200:**
```json
{
  "success": true,
  "data": null,
  "message": "Password set successfully. You can now log in.",
  "links": [
    { "href": "/api/v1/users/login", "rel": "login", "type": "POST" }
  ]
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `validation_error` | Campo ausente, senha curta, confirmação divergente ou formato de token inválido |
| 404 | `not_found` | Token não encontrado |
| 410 | `token_expired` | Link expirado |
| 410 | `token_used` | Link já utilizado |

---

### 4.2 Solicitar Redefinição de Senha (Forgot Password)

Envia email com link de redefinição de senha. Implementa **anti-enumeração**: sempre retorna `200`, independentemente de o email existir ou não.

```
POST /api/v1/auth/forgot-password
```

**Autenticação:** Nenhuma (public endpoint)

**Rate limit:** 3 requisições por email por hora.

**Request Body:**
```json
{
  "email": "usuario@empresa.com"
}
```

**Response 200** (sempre retorna 200):
```json
{
  "success": true,
  "data": null,
  "message": "If this email is registered, a password reset link has been sent."
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `validation_error` | Email ausente ou formato inválido |
| 429 | `rate_limited` | Limite de requisições excedido |

---

### 4.3 Redefinir Senha (Reset Password)

Redefine a senha com um token de redefinição válido. **Invalida todas as sessões ativas** após a redefinição.

```
POST /api/v1/auth/reset-password
```

**Autenticação:** Nenhuma (public endpoint)

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
  "password": "NovaSenha123",
  "confirm_password": "NovaSenha123"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": null,
  "message": "Password reset successfully. You can now log in with your new password.",
  "links": [
    { "href": "/api/v1/users/login", "rel": "login", "type": "POST" }
  ]
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `validation_error` | Campo ausente, token inválido ou senha fraca |
| 404 | `not_found` | Token não encontrado |
| 410 | `token_expired` | Link expirado |
| 410 | `token_used` | Link já utilizado |

---

## 5. Convite de Usuários

### 5.1 Convidar Usuário

Cria um usuário Odoo a partir de um perfil existente e envia o link de convite por email.

```
POST /api/v1/users/invite
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

**Matriz de Autorização (RBAC):**

| Papel do requisitante | Perfis que pode convidar |
|---|---|
| Owner | Todos (owner, director, manager, agent, prospector, receptionist, financial, legal, tenant, property_owner) |
| Director | agent, prospector, receptionist, financial, legal |
| Manager | agent, prospector, receptionist, financial, legal |
| Agent | tenant, property_owner |

**Request Body:**
```json
{
  "profile_id": 15
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": 42,
    "name": "João Silva",
    "email": "joao@empresa.com",
    "document": "123.456.789-00",
    "profile": "agent",
    "profile_id": 15,
    "signup_pending": true,
    "invite_sent_at": "2026-03-06T23:00:00",
    "invite_expires_at": "2026-03-07T23:00:00"
  },
  "message": "User invited successfully. Email sent to joao@empresa.com",
  "links": {
    "self": "/api/v1/users/42",
    "resend_invite": "/api/v1/users/42/resend-invite",
    "collection": "/api/v1/users",
    "profile": "/api/v1/profiles/15"
  }
}
```

> Se o email falhar, o campo `"email_status": "failed"` é adicionado ao `data`.

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `validation_error` | `profile_id` ausente |
| 403 | `forbidden` | Papel do requisitante não pode convidar este tipo de perfil |
| 404 | `not_found` | Perfil não encontrado |
| 409 | `conflict` | Perfil já possui usuário vinculado ou CPF/email duplicado |

---

### 5.2 Reenviar Convite

Reenvia o email de convite para um usuário que ainda não definiu a senha.

```
POST /api/v1/users/resend-invite
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

**Request Body:**
```json
{
  "user_id": 42
}
```

**Response 200:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Invite resent successfully to joao@empresa.com"
}
```

**Erros:**

| Status | Código | Descrição |
|---|---|---|
| 400 | `ERR_USER_ALREADY_ACTIVE` | Usuário já definiu a senha — usar `forgot-password` |
| 400 | `validation_error` | `user_id` ausente ou inválido |
| 401 | `ERR_UNAUTHORIZED` | Contexto de sessão ausente |
| 403 | `ERR_FORBIDDEN` | Sem permissão para este tipo de perfil |
| 404 | `ERR_NOT_FOUND` | Usuário não encontrado na sua empresa |

---

## 6. Perfis (Profiles)

Gerenciamento unificado de perfis RBAC (Feature 010). Perfis são a entidade central para criação de usuários.

**9 tipos de perfil disponíveis:** `owner`, `director`, `manager`, `agent`, `prospector`, `receptionist`, `financial`, `legal`, `tenant`, `property_owner`

---

### 6.1 Listar Tipos de Perfil

```
GET /api/v1/profile-types
```

**Autenticação:** `@require_jwt` + `@require_session`

**Response 200:**
```json
{
  "success": true,
  "data": [
    { "id": 1, "code": "owner", "name": "Owner", "level": 1, "group_xml_id": "quicksol_estate.group_real_estate_owner" },
    { "id": 2, "code": "director", "name": "Director", "level": 2, "group_xml_id": "quicksol_estate.group_real_estate_director" },
    { "id": 3, "code": "manager", "name": "Manager", "level": 3, "group_xml_id": "quicksol_estate.group_real_estate_manager" }
  ],
  "count": 10
}
```

---

### 6.2 Criar Perfil

```
POST /api/v1/profiles
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

**Request Body:**
```json
{
  "name": "João Silva",
  "company_id": 2,
  "profile_type_id": 3,
  "document": "123.456.789-00",
  "email": "joao@empresa.com",
  "birthdate": "1990-05-15",
  "phone": "+55 11 99999-9999",
  "mobile": "+55 11 88888-8888",
  "occupation": "Corretor",
  "hire_date": "2026-01-01"
}
```

> Campos obrigatórios: `name`, `company_id`, `profile_type_id`, `document`, `email`, `birthdate`.  
> `document` aceita CPF (`000.000.000-00`) ou CNPJ (`00.000.000/0000-00`) — normalizado automaticamente.

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "name": "João Silva",
    "profile_type": "manager",
    "profile_type_id": 3,
    "company_id": 2,
    "document": "123.456.789-00",
    "email": "joao@empresa.com",
    "phone": "+55 11 99999-9999",
    "active": true,
    "_links": {
      "self": "/api/v1/profiles/15",
      "invite": "/api/v1/users/invite"
    }
  }
}
```

**Erros:**

| Status | Descrição |
|---|---|
| 400 | Campos obrigatórios ausentes, documento inválido ou `profile_type_id` inativo |
| 403 | Seu papel não pode criar este tipo de perfil |
| 409 | Perfil já existe com este documento + empresa + tipo |

---

### 6.3 Listar Perfis

```
GET /api/v1/profiles?company_ids={id}&profile_type={code}&limit={n}&offset={n}
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `company_ids` | `string` | ✅ | IDs das empresas separados por vírgula (ex: `2,3`) |
| `profile_type` | `string` | ❌ | Filtro por código de tipo (ex: `agent`) |
| `document` | `string` | ❌ | Filtro por CPF/CNPJ |
| `name` | `string` | ❌ | Filtro por nome (busca parcial) |
| `active` | `boolean` | ❌ | Filtro por status ativo (`true` / `false`) |
| `limit` | `integer` | ❌ | Máximo de resultados (padrão: 20, máx: 100) |
| `offset` | `integer` | ❌ | Paginação (padrão: 0) |

**Response 200:**
```json
{
  "success": true,
  "data": [ { ... }, { ... } ],
  "count": 2,
  "total": 50,
  "limit": 20,
  "offset": 0,
  "_links": {
    "self": "/api/v1/profiles?company_ids=2&limit=20&offset=0",
    "next": "/api/v1/profiles?company_ids=2&limit=20&offset=20"
  }
}
```

---

### 6.4 Buscar Perfil por ID

```
GET /api/v1/profiles/{profile_id}
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "name": "João Silva",
    "profile_type": "manager",
    ...
  }
}
```

**Erros:**

| Status | Descrição |
|---|---|
| 404 | Perfil não encontrado (ou fora do acesso da empresa) |

---

### 6.5 Atualizar Perfil

```
PUT /api/v1/profiles/{profile_id}
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

> Campos **imutáveis**: `profile_type`, `company_id`, `document`.

**Request Body** (todos opcionais):
```json
{
  "name": "João Silva Atualizado",
  "email": "novo@email.com",
  "phone": "+55 11 99999-9999",
  "mobile": "+55 11 88888-8888",
  "occupation": "Gerente",
  "birthdate": "1990-05-15",
  "hire_date": "2026-01-01"
}
```

> Se o perfil for do tipo `agent`, as atualizações são sincronizadas automaticamente com o registro `real.estate.agent`.

**Response 200:**
```json
{
  "success": true,
  "data": { ... }
}
```

---

### 6.6 Desativar Perfil (Soft Delete)

```
DELETE /api/v1/profiles/{profile_id}
```

**Autenticação:** `@require_jwt` + `@require_session` + `@require_company`

> Desativação em cascata: o usuário Odoo vinculado e o agente (`real.estate.agent`) também são desativados.

**Request Body** (opcional):
```json
{
  "reason": "Colaborador desligado"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Profile 15 deactivated successfully"
}
```

**Erros:**

| Status | Descrição |
|---|---|
| 400 | Perfil já está inativo |
| 404 | Perfil não encontrado |

---

## 7. Usuário Autenticado

### 7.1 Dados do Usuário Logado

Retorna os dados do usuário da sessão ativa.

```
GET /api/v1/me
```

**Autenticação:** `@require_jwt` + `@require_session`

**Response 200:**
```json
{
  "id": 42,
  "name": "João Silva",
  "email": "joao@empresa.com",
  "login": "joao@empresa.com",
  "phone": "+55 11 99999-9999",
  "mobile": "",
  "companies": [
    {
      "id": 2,
      "name": "QuickSol Real Estate",
      "cnpj": "12.345.678/0001-90",
      "email": "contato@empresa.com",
      "phone": "+55 11 3333-4444",
      "website": "https://empresa.com"
    }
  ],
  "default_company_id": 2
}
```

**Erros:**

| Status | Descrição |
|---|---|
| 401 | Sessão inválida ou usuário do sistema |

---

## Códigos de Erro

### Formato Padrão de Erro

```json
{
  "error": {
    "status": 401,
    "message": "Invalid credentials"
  }
}
```

Ou no formato de endpoints de onboarding:

```json
{
  "success": false,
  "error": "validation_error",
  "message": "Missing required fields: token",
  "details": { "missing_fields": ["token"] }
}
```

### Tabela Geral de Status HTTP

| Status | Significado |
|---|---|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 400 | Requisição inválida (validação) |
| 401 | Não autenticado |
| 403 | Autorização negada (sem permissão) |
| 404 | Recurso não encontrado |
| 409 | Conflito (duplicidade) |
| 410 | Recurso expirado ou já utilizado |
| 429 | Rate limit excedido |
| 500 | Erro interno do servidor |

---

## Fluxo de Autenticação Completo

```
1. POST /api/v1/auth/token
   → access_token, refresh_token

2. POST /api/v1/users/login  (Authorization: Bearer {access_token})
   → session_id, user data

3. GET|POST /api/v1/...  (Authorization: Bearer {access_token} + X-Session-ID: {session_id})
   → dados protegidos

4. POST /api/v1/auth/refresh  (quando access_token expirar)
   → novo access_token

5. POST /api/v1/users/logout  (Authorization + X-Session-ID)
   → sessão invalidada
```

## Fluxo de Convite de Usuário

```
1. POST /api/v1/profiles  → cria perfil com dados do usuário
2. POST /api/v1/users/invite  { profile_id }  → cria conta + envia email
3. [usuário recebe email com link contendo token]
4. POST /api/v1/auth/set-password  { token, password, confirm_password }
5. POST /api/v1/users/login  → acesso completo
```
