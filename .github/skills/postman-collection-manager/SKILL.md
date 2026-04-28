---
name: postman-collection-manager
description: Create, update, and validate Postman collections following ADR-016 standards. Handles naming conventions, versioning, required variables (base_url, tokens, session_id), headers by endpoint type (GET vs POST), OAuth token endpoints with auto-save scripts, and JSON-RPC structure. Use when creating new collections, adding endpoints, updating versions, or validating ADR-016 compliance.
---

# Postman Collection Manager

Skill to create, update, and validate Postman collections following strict ADR-016 rules (Postman Collection Standards). This skill ensures total compliance with project standards for API documentation and testing.

## When to Use

Use esta skill quando:
- Precisar criar uma nova coleção Postman do zero
- Adicionar novos endpoints a uma coleção existente
- Atualizar a versão de uma coleção
- Validar se uma coleção está conforme ADR-016
- Sincronizar endpoints da especificação OpenAPI para Postman
- Onboarding de novos desenvolvedores que precisam testar a API

## Prerequisites

1. Ler completamente a [ADR-016: Postman Collection Standards](../../docs/adr/ADR-016-postman-collection-standards.md)
2. Conhecer a estrutura da API e endpoints disponíveis
3. Ter acesso à especificação OpenAPI (se estiver sincronizando)

## Instructions

### Regras Obrigatórias da ADR-016

Antes de criar ou modificar qualquer coleção, **SEMPRE** siga estas regras:

#### 1. Nomenclatura e Versionamento (ADR-016 §1)

**Arquivo:**
- Formato: `{nome_da_api}_v{versao}_postman_collection.json`
- Exemplo: `quicksol_api_v1.2_postman_collection.json`
- Localização: `docs/postman/`

**Dentro do JSON:**
```json
{
  "info": {
    "name": "Quicksol Real Estate API",  // SEM versão
    "version": "1.2",                     // Versão AQUI
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  }
}
```

**❌ NUNCA fazer:**
- `"name": "Quicksol Real Estate API v1.2"` (versão no nome)
- Nome de arquivo sem versão: `quicksol_api_postman_collection.json`
- Usar patch version: `v1.2.3` (apenas major.minor)

#### 2. Variáveis Obrigatórias (ADR-016 §2)

Toda coleção **DEVE** incluir estas variáveis:

```json
"variable": [
  {"key": "base_url", "value": "http://localhost:8069"},
  {"key": "client_id", "value": "client_xxx"},
  {"key": "client_secret", "value": "secret_yyy"},
  {"key": "access_token", "value": ""},
  {"key": "refresh_token", "value": ""},
  {"key": "session_id", "value": ""},
  {"key": "user_agent", "value": "PostmanRuntime/7.26.8"},
  {"key": "user_email", "value": "admin@example.com"},
  {"key": "user_password", "value": "admin"}
]
```

**🚫 Proibido:** Hardcoding de valores sensíveis (tokens, passwords, secrets)

#### 3. Headers por Tipo de Endpoint (ADR-016 §3)

**Headers comuns (todos os endpoints exceto OAuth):**
```json
[
  {"key": "Content-Type", "value": "application/json"},
  {"key": "User-Agent", "value": "{{user_agent}}", "description": "Required for session fingerprint validation"},
  {"key": "Authorization", "value": "Bearer {{access_token}}", "description": "OAuth 2.0 Bearer token"}
]
```

**Para endpoints GET (type='http'):**
Adicionar também:
```json
{
  "key": "X-Openerp-Session-Id",
  "value": "{{session_id}}",
  "description": "Session ID for fingerprint validation (REQUIRED for GET)"
}
```

**Para endpoints POST/PUT/PATCH (type='json'):**
Session ID vai no **body JSON** (não no header):
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "session_id": "{{session_id}}"
}
```

#### 4. OAuth Token Endpoint (ADR-016 §4)

```json
{
  "name": "Get OAuth Token",
  "request": {
    "method": "POST",
    "header": [{"key": "Content-Type", "value": "application/json"}],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"client_id\": \"{{client_id}}\",\n  \"client_secret\": \"{{client_secret}}\",\n  \"grant_type\": \"client_credentials\"\n}"
    },
    "url": "{{base_url}}/api/v1/auth/token"
  },
  "event": [{
    "listen": "test",
    "script": {
      "exec": [
        "const jsonData = pm.response.json();",
        "if (jsonData && jsonData.access_token) {",
        "    pm.environment.set('access_token', jsonData.access_token);",
        "    console.log('✅ Access token saved to environment');",
        "    if (jsonData.refresh_token) {",
        "        pm.environment.set('refresh_token', jsonData.refresh_token);",
        "        console.log('✅ Refresh token saved to environment');",
        "    }",
        "}"
      ]
    }
  }]
}
```

**⚠️ IMPORTANTE:** OAuth endpoints **NÃO** usam JSON-RPC. Enviar JSON direto.

#### 5. User Login Endpoint (ADR-016 §5)

```json
{
  "name": "User Login",
  "request": {
    "method": "POST",
    "header": [/* headers comuns */],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"email\": \"{{user_email}}\",\n  \"password\": \"{{user_password}}\"\n}"
    },
    "url": "{{base_url}}/api/v1/users/login"
  },
  "event": [{
    "listen": "test",
    "script": {
      "exec": [
        "const jsonData = pm.response.json();",
        "if (jsonData && jsonData.result && jsonData.result.session_id) {",
        "    pm.environment.set('session_id', jsonData.result.session_id);",
        "    console.log('✅ Session ID saved to environment');",
        "}"
      ]
    }
  }]
}
```

#### 6. Estrutura de Pastas (ADR-016 §6)

```
Collection Root
├── 1. Authentication (OAuth Token, Refresh Token)
├── 2. User Management (Login, Logout, Get Me)
├── 3. Agents (CRUD endpoints)
├── 4. Properties (CRUD endpoints)
├── 5. Assignments (Assignment endpoints)
├── 6. Leads (Lead management)
└── [outras pastas de domínio]
```

#### 7. Descrições de Endpoints (ADR-016 §7)

Toda descrição de endpoint **DEVE** incluir:

```markdown
**Authentication:** Bearer Token + Session ID required
**Multi-tenancy:** Company isolation active (@require_company)
**Fingerprint validation:** Active (IP + User-Agent + Accept-Language)

**IMPORTANT:** For GET requests (type='http'), session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in request body.

[Descrição funcional específica do endpoint]
```

#### 8. Regras de Ouro (ADR-016 §8)

1. **🚫 NUNCA** usar wrapper JSON-RPC - enviar JSON direto no body
2. **🚫 NUNCA** enviar `session_id` no body de GET - será ignorado
3. **✅ SEMPRE** usar variáveis `{{...}}` ao invés de valores hardcoded
4. **✅ SEMPRE** incluir User-Agent consistente (fingerprint validation)
5. **✅ SEMPRE** versionar collections ao fazer mudanças estruturais
6. **✅ SEMPRE** adicionar test scripts para auto-popular tokens
7. **✅ SEMPRE** salvar `refresh_token` em variável (usado por endpoints de refresh)
8. **✅ SEMPRE** documentar tipo de autenticação na descrição

### ⚠️ Regra Crítica: Feature Nova → Atualizar Coleção Principal

**NUNCA crie um arquivo de coleção separado por feature** (ex: `feature013_proposals_v1.0_postman_collection.json`).

Ao implementar endpoints de uma nova feature:
1. **Localize a última versão** da coleção principal em `docs/postman/` (ex: `quicksol_api_v1.23_postman_collection.json`)
2. **Adicione os novos endpoints** como uma nova pasta numerada (ex: `21. Property Proposals`)
3. **Incremente a versão minor** (`1.23` → `1.24`)
4. **Adicione entrada no Changelog** no campo `info.description`
5. **Adicione novas variáveis** necessárias (ex: `proposal_id`)
6. **Salve como novo arquivo** com a versão atualizada
7. **Delete o arquivo antigo** (apenas guarde a última versão)

**Como encontrar a última versão:**
```bash
ls docs/postman/quicksol_api_v*.json | sort -V | tail -1
```

**Script Python para fundir:**
```python
import json

# 1. Carregar última versão
with open('quicksol_api_v1.23_postman_collection.json', encoding='utf-8') as f:
    collection = json.loads(f.read(), strict=False)  # strict=False para control chars

# 2. Criar pasta da nova feature
new_folder = {
    "name": "21. Property Proposals",
    "description": "...",
    "item": [/* endpoints */]
}

# 3. Adicionar pasta, incrementar versão, adicionar changelog
collection['item'].append(new_folder)
collection['info']['version'] = '1.24'
collection['info']['description'] += '\n\n## Changelog v1.24\n- **NEW**: ...' 

# 4. Adicionar variáveis novas
collection['variable'].append({'key': 'proposal_id', 'value': '', 'type': 'string'})

# 5. Salvar com nova versão
with open('quicksol_api_v1.24_postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
```

> **Nota:** `json.loads(..., strict=False)` é necessário pois alguns arquivos podem conter control characters nos campos de descrição. Sempre use esta opção ao ler coleções existentes.

---

### Processo: Criar Nova Coleção

1. **Leia a ADR-016 completa**
   - Arquivo: `docs/adr/ADR-016-postman-collection-standards.md`
   - Entenda todas as regras antes de criar

2. **Determine a versão**
   - Major (v2.0): Breaking changes na API
   - Minor (v1.1): Novos endpoints, correções
   - Primeira coleção: v1.0

3. **Crie a estrutura básica:**

```json
{
  "info": {
    "_postman_id": "[gerar UUID único]",
    "name": "Quicksol Real Estate API",
    "description": "API REST para sistema imobiliário multi-tenant com OAuth 2.0 e autenticação dual",
    "version": "1.0",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [],
  "variable": []
}
```

4. **Adicione as variáveis obrigatórias** (conforme §2)

5. **Crie as pastas padrão** (conforme §6):
   - 1. Authentication
   - 2. User Management
   - 3-6. Pastas de domínio

6. **Adicione endpoints essenciais:**
   - OAuth Token (com test script)
   - Refresh Token
   - User Login (com test script)
   - User Logout
   - Get Current User (/api/v1/me)

7. **Salve o arquivo:**
   - Nome: `quicksol_api_v1.0_postman_collection.json`
   - Localização: `docs/postman/`

8. **Valide a coleção:**
   - ✅ Campo `info.version` presente?
   - ✅ Nome sem versão?
   - ✅ Todas as variáveis obrigatórias?
   - ✅ Headers padronizados?
   - ✅ Test scripts nos endpoints corretos?

9. **Commit no Git:**
   ```bash
   git add docs/postman/quicksol_api_v1.0_postman_collection.json
   git commit -m "feat: create Postman collection v1.0 (ADR-016 compliant)"
   ```

### Processo: Adicionar Endpoint GET

1. **Identifique a pasta correta** (ex: "3. Agents")

2. **Crie o request:**

```json
{
  "name": "List Agents",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "{{user_agent}}"},
      {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}
    ],
    "url": {
      "raw": "{{base_url}}/api/v1/agents?limit=10&offset=0",
      "host": ["{{base_url}}"],
      "path": ["api", "v1", "agents"],
      "query": [
        {"key": "limit", "value": "10"},
        {"key": "offset", "value": "0"}
      ]
    },
    "description": "**Authentication:** Bearer Token + Session ID required\n**Multi-tenancy:** Company isolation active\n\n**IMPORTANT:** For GET requests, session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in body.\n\nReturns paginated list of agents in the current company."
  }
}
```

3. **Adicione à pasta correta** no array `item`

4. **⚠️ Verificação crítica para GET:**
   - ✅ Header `X-Openerp-Session-Id` presente?
   - ✅ `session_id` NÃO está no body?
   - ✅ Descrição alerta sobre envio via header?

### Processo: Adicionar Endpoint POST

1. **Identifique a pasta correta**

2. **Crie o request:**

```json
{
  "name": "Create Agent",
  "request": {
    "method": "POST",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "{{user_agent}}"}
    ],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"name\": \"João Silva\",\n  \"email\": \"joao@example.com\",\n  \"creci\": \"F123456\",\n  \"session_id\": \"{{session_id}}\"\n}"
    },
    "url": {
      "raw": "{{base_url}}/api/v1/agents",
      "host": ["{{base_url}}"],
      "path": ["api", "v1", "agents"]
    },
    "description": "**Authentication:** Bearer Token + Session ID required\n**Multi-tenancy:** Company isolation active\n\n**IMPORTANT:** Business endpoints do NOT use JSON-RPC format. Send JSON directly in body.\n\nCreates a new agent in the current company."
  }
}
```

3. **⚠️ Verificação crítica para POST:**
   - ✅ `session_id` está no **body JSON**?
   - ✅ Header `X-Openerp-Session-Id` NÃO presente?
   - ✅ Body é JSON direto (sem wrapper JSON-RPC)?
   - ✅ Descrição alerta sobre NÃO usar JSON-RPC?

### Processo: Atualizar Versão

1. **Determine o tipo de mudança:**
   - Breaking change → Major (1.0 → 2.0)
   - Novos endpoints → Minor (1.0 → 1.1)

2. **Carregue a coleção atual**

3. **Atualize o campo `info.version`:**
   ```json
   "version": "1.1"  // Era 1.0
   ```

4. **Gere novo nome de arquivo:**
   - Antigo: `quicksol_api_v1.0_postman_collection.json`
   - Novo: `quicksol_api_v1.1_postman_collection.json`

5. **Salve com novo nome**

6. **Commit e remova arquivo antigo:**
   ```bash
   git rm docs/postman/quicksol_api_v1.0_postman_collection.json
   git add docs/postman/quicksol_api_v1.1_postman_collection.json
   git commit -m "chore: update Postman collection to v1.1"
   ```

### Processo: Validar Coleção

Verifique cada item:

**✅ Checklist de Validação:**

1. **Arquivo e Metadata**
   - [ ] Nome do arquivo: `{nome}_v{versao}_postman_collection.json`
   - [ ] Campo `info.version` presente
   - [ ] Campo `info.name` sem versão
   - [ ] Schema: `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`

2. **Variáveis (ADR-016 §2)**
   - [ ] base_url
   - [ ] client_id, client_secret
   - [ ] access_token, refresh_token
   - [ ] session_id
   - [ ] user_agent
   - [ ] user_email, user_password

3. **Endpoints OAuth**
   - [ ] Get OAuth Token com test script (salva access_token + refresh_token)
   - [ ] Refresh Token endpoint presente

4. **Endpoints User**
   - [ ] User Login com test script (salva session_id)
   - [ ] Headers corretos (Authorization + User-Agent)

5. **Endpoints GET**
   - [ ] Header `X-Openerp-Session-Id` presente
   - [ ] `session_id` NÃO no body
   - [ ] Descrição alerta sobre envio via header

6. **Endpoints POST/PUT/PATCH**
   - [ ] `session_id` no body JSON
   - [ ] Header `X-Openerp-Session-Id` NÃO presente
   - [ ] JSON direto (sem wrapper JSON-RPC)

7. **Descrições**
   - [ ] Tipo de autenticação documentado
   - [ ] Multi-tenancy documentado
   - [ ] Avisos importantes presentes

Se algum item falhar, corrija antes de commitar.

## Examples

### Exemplo 1: Criar Collection v1.0 do Zero

**Objetivo:** Criar primeira versão da coleção Postman

**Passo 1:** Crie arquivo base
```json
{
  "info": {
    "_postman_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Quicksol Real Estate API",
    "version": "1.0",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [],
  "variable": [
    {"key": "base_url", "value": "http://localhost:8069"},
    {"key": "client_id", "value": "client_xxx"},
    {"key": "client_secret", "value": "secret_yyy"},
    {"key": "access_token", "value": ""},
    {"key": "refresh_token", "value": ""},
    {"key": "session_id", "value": ""},
    {"key": "user_agent", "value": "PostmanRuntime/7.26.8"},
    {"key": "user_email", "value": "admin@example.com"},
    {"key": "user_password", "value": "admin"}
  ]
}
```

**Passo 2:** Adicione pastas (Authentication, User Management, etc.)

**Passo 3:** Adicione endpoints essenciais (OAuth Token, User Login)

**Passo 4:** Salve como `docs/postman/quicksol_api_v1.0_postman_collection.json`

### Exemplo 2: Adicionar Endpoint "List Agents"

**Contexto:** Novo endpoint GET foi criado em `quicksol_estate/controllers/agents.py`

**Ação:** Adicionar na pasta "3. Agents"

```json
{
  "name": "List Agents",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "{{user_agent}}"},
      {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}
    ],
    "url": {
      "raw": "{{base_url}}/api/v1/agents?limit=10&offset=0",
      "query": [
        {"key": "limit", "value": "10"},
        {"key": "offset", "value": "0"}
      ]
    },
    "description": "**Authentication:** Bearer Token + Session ID required\n**IMPORTANT:** session_id via header X-Openerp-Session-Id"
  }
}
```

### Exemplo 3: Corrigir Collection Não-Conforme

**Problema encontrado:** Collection antiga sem campo `version` e com session_id errado em GET

**Correções:**

1. Adicionar campo version:
```json
"info": {
  "name": "Quicksol Real Estate API",  // OK
  "version": "1.1"  // ADICIONAR
}
```

2. Corrigir endpoint GET:
```json
// ❌ ANTES (errado)
{
  "method": "GET",
  "body": {
    "raw": "{\"session_id\": \"{{session_id}}\"}"  // ERRADO!
  }
}

// ✅ DEPOIS (correto)
{
  "method": "GET",
  "header": [
    ...,
    {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}  // CORRETO!
  ]
}
```

3. Salvar como nova versão: `quicksol_api_v1.1_postman_collection.json`

## Common Pitfalls

### ❌ Erro 1: Versão no Nome da Collection
```json
// ERRADO
"name": "Quicksol Real Estate API v1.1"

// CORRETO
"name": "Quicksol Real Estate API",
"version": "1.1"
```

### ❌ Erro 2: Session ID em Body de GET
```json
// ERRADO - GET não processa body
{
  "method": "GET",
  "body": {"raw": "{\"session_id\": \"...\"}"}
}

// CORRETO - Session ID via header
{
  "method": "GET",
  "header": [
    {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}
  ]
}
```

### ❌ Erro 3: Usar JSON-RPC
```json
// ERRADO - wrapper JSON-RPC
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {"name": "John"}
}

// CORRETO - JSON direto
{
  "name": "John",
  "session_id": "{{session_id}}"
}
```

### ❌ Erro 4: Não Salvar Refresh Token
```javascript
// ERRADO - só salva access_token
pm.environment.set('access_token', jsonData.access_token);

// CORRETO - salva ambos
pm.environment.set('access_token', jsonData.access_token);
if (jsonData.refresh_token) {
    pm.environment.set('refresh_token', jsonData.refresh_token);
}
```

### ❌ Erro 6: Criar Arquivo Separado por Feature
```
// ERRADO - arquivo isolado por feature
docs/postman/feature013_property_proposals_v1.0_postman_collection.json

// CORRETO - adicionar à coleção principal com versão incrementada
docs/postman/quicksol_api_v1.24_postman_collection.json  // era v1.23
```

Uma feature nova = uma nova pasta na coleção principal + versão minor incrementada.

### ❌ Erro 5: Headers Hardcoded
```json
// ERRADO
{"key": "User-Agent", "value": "PostmanRuntime/7.26.8"}

// CORRETO
{"key": "User-Agent", "value": "{{user_agent}}"}
```

## Related Documentation

- **ADR-016:** [Postman Collection Standards](../../docs/adr/ADR-016-postman-collection-standards.md) - Regras completas e rationale
- **ADR-005:** [OpenAPI 3.0 / Swagger](../../docs/adr/ADR-005-openapi-30-swagger-documentation.md) - Documentação complementar
- **ADR-009:** [Headless Authentication](../../docs/adr/ADR-009-headless-authentication-user-context.md) - Contexto sobre autenticação dual
- **ADR-011:** [Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md) - Decoradores @require_jwt e @require_session
- [Postman Collection Format v2.1.0](https://schema.getpostman.com/json/collection/v2.1.0/collection.json) - Schema oficial

## Maintenance

- **Atualizar sempre que:** Novos endpoints forem criados, autenticação mudar, ou breaking changes na API
- **Validar em PRs:** Verificar se collection foi atualizada junto com mudanças de endpoint
- **Versionamento:** Seguir Git Flow (ADR-006) para branches e commits
- **Sincronização:** Manter OpenAPI e Postman sincronizados (collections refletem OpenAPI spec)

---

**Skill Version:** 1.1  
**Last Updated:** 2026-04-28  
**Maintained by:** Development Team
