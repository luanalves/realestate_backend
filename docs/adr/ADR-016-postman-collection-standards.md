# ADR-016: Padrões para Postman Collections

## Status
Aceito

## Contexto

As Postman Collections são ferramentas essenciais para:
- **Documentação viva** da API REST
- **Testes manuais** durante desenvolvimento
- **Onboarding** de novos desenvolvedores
- **Validação** de contratos de API
- **Debugging** de problemas de autenticação

Sem padrões consistentes, as collections podem:
- Ter variáveis hardcoded (inseguro)
- Usar nomes de variáveis inconsistentes entre collections
- Perder versionamento (impossível rastrear mudanças)
- Ter configurações de headers inconsistentes (quebra autenticação dual)
- Dificultar automação e CI/CD

**Problema específico identificado**: Durante implementação da spec 002, descobrimos que endpoints GET (`type='http'`) não processam JSON body. Isso causou 100% de falha nos testes até identificarmos que `session_id` deve ir no **header** para GET e no **body** para POST. Essa descoberta precisa estar documentada e padronizada.

## Decisão

### 1. Localização e Versionamento

**Diretório padrão**: `/docs/postman/`

**Nomenclatura do arquivo**: O arquivo **DEVE** ter sufixo versionado `_v{versao}` antes de `postman_collection.json`

**Formato**: `{nome_da_api}_v{versao}_postman_collection.json`

**Exemplos**:
- `quicksol_api_v1.0_postman_collection.json`
- `quicksol_api_v1.1_postman_collection.json`
- `quicksol_api_v2.0_postman_collection.json`

**Título da collection**: O campo `info.name` dentro do JSON **NÃO DEVE** incluir versão (nome limpo):
- ✅ Correto: `"name": "Quicksol Real Estate API"`
- ❌ Errado: `"name": "Quicksol Real Estate API v1.1"`

**Campo version**: O campo `info.version` **DEVE** estar presente e conter a versão:
```json
{
  "info": {
    "name": "Quicksol Real Estate API",
    "version": "1.1.0"
  }
}
```

**Regra**: A versão aparece **UMA VEZ** no nome do arquivo e **UMA VEZ** no campo `info.version`, mas **NÃO** no `info.name`.

**Versionamento**:
- **Major** (v2.0): Breaking changes na API ou mudanças estruturais na collection
- **Minor** (v1.1): Novos endpoints, correções de bugs, melhorias na documentação
- **Não usar** patch version (complexidade desnecessária)

**Git**:
- Collections devem estar no controle de versão
- Commit sempre que houver mudança nos endpoints
- Branch seguindo Git Flow (ADR-006)

### 2. Variáveis Padrão Obrigatórias

Todas as collections **DEVEM** usar as seguintes variáveis de ambiente:

```json
{
  "base_url": "http://localhost:8069",
  "client_id": "client_xxx",
  "client_secret": "secret_yyy",
  "access_token": "auto_populated_by_test_script",
  "session_id": "auto_populated_by_test_script",
  "user_agent": "PostmanRuntime/7.26.8",
  "user_email": "admin@example.com",
  "user_password": "admin"
}
```

**Proibido**: Hardcoding de valores sensíveis (client_secret, tokens, session_id, passwords, user-agent)

**Recomendado**: Criar environment separado para cada ambiente (dev, staging, prod)

**Nota**: `user_agent` deve permanecer consistente durante toda a sessão (fingerprint validation)

### 3. Headers Obrigatórios

Todos os endpoints (exceto OAuth token) **DEVEM** incluir os seguintes headers:

#### 3.1 Headers Comuns

```json
{
  "key": "Content-Type",
  "value": "application/json",
  "type": "text"
}
```

```json
{
  "key": "User-Agent",
  "value": "{{user_agent}}",
  "type": "text",
  "description": "Required for session fingerprint validation"
}
```

```json
{
  "key": "Authorization",
  "value": "Bearer {{access_token}}",
  "type": "text",
  "description": "OAuth 2.0 Bearer token"
}
```

#### 3.2 Headers Específicos por Tipo de Endpoint

**Para endpoints GET (`type='http'`)**:

```json
{
  "key": "X-Openerp-Session-Id",
  "value": "{{session_id}}",
  "type": "text",
  "description": "Session ID for fingerprint validation (REQUIRED for GET)"
}
```

**Para endpoints POST/PUT/PATCH (`type='json'`)**:

Session ID vai no **body JSON**, não no header:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "{{session_id}}",
    ...outros parâmetros
  }
}
```

### 4. OAuth Token Endpoint

**Endpoint**: `POST {{base_url}}/api/v1/auth/token`

**Importante**: Endpoints OAuth **NÃO** usam formato JSONRPC. Enviar JSON direto no body.

**Body**:
```json
{
  "client_id": "{{client_id}}",
  "client_secret": "{{client_secret}}",
  "grant_type": "client_credentials"
}
```

**Test Script Obrigatório** (auto-popula access_token):
```javascript
const jsonData = pm.response.json();
if (jsonData && jsonData.access_token) {
    pm.environment.set('access_token', jsonData.access_token);
    console.log('✅ Access token saved to environment');
} else {
    console.error('❌ Failed to extract access_token from response');
}
```

### 5. User Login Endpoint

**Endpoint**: `POST {{base_url}}/api/v1/users/login`

**Headers**: Authorization + User-Agent (conforme §3)

**Importante**: Endpoints de negócio (type='json') **NÃO** usam formato JSONRPC. Enviar JSON direto no body.

**Body** (usar variáveis para credenciais):
```json
{
  "email": "{{user_email}}",
  "password": "{{user_password}}"
}
```

**Test Script Obrigatório** (auto-popula session_id):
```javascript
const jsonData = pm.response.json();
if (jsonData && jsonData.result && jsonData.result.session_id) {
    pm.environment.set('session_id', jsonData.result.session_id);
    console.log('✅ Session ID saved to environment');
} else {
    console.error('❌ Failed to extract session_id from response');
}
```

### 6. Estrutura de Pastas (Folders)

Collections devem ser organizadas em pastas lógicas:

```
Quicksol Real Estate API
├── 1. Authentication
│   ├── Get OAuth Token
│   ├── Refresh Token
│   └── Revoke Token
├── 2. User Management
│   ├── User Login
│   ├── User Logout
│   └── Get Current User (/api/v1/me)
├── 3. Agents (Business Domain)
│   ├── List Agents (GET)
│   ├── Create Agent (POST)
│   ├── Get Agent (GET)
│   ├── Update Agent (PUT)
│   └── Delete Agent (DELETE)
├── 4. Properties (Business Domain)
├── 5. Assignments (Business Domain)
├── 6. Commissions (Business Domain)
├── 7. Performance (Business Domain)
└── 8. Master Data (Read-only, no session)
```

### 7. Descrições de Endpoints

Cada endpoint **DEVE** ter descrição documentando:

```markdown
**Authentication:** Bearer Token + Session ID required
**Multi-tenancy:** Company isolation active (@require_company)
**Fingerprint validation:** Active (IP + User-Agent + Accept-Language)

**IMPORTANT:** For GET requests (type='http'), session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in request body.

**User-Agent consistency:** Required for session validation
**Session expiry:** 2 hours inactivity

[Descrição funcional do endpoint]
```

### 8. Regras de Ouro

1. **NUNCA** usar wrapper JSONRPC (`{"jsonrpc": "2.0", "method": "call", "params": {...}}`) - enviar JSON direto
2. **NUNCA** enviar `session_id` no body de requisições GET - será ignorado
3. **SEMPRE** usar variáveis `{{...}}` ao invés de valores hardcoded
4. **SEMPRE** incluir User-Agent para evitar falha de fingerprint
5. **SEMPRE** manter User-Agent consistente durante toda a sessão
6. **SEMPRE** versionar collections ao fazer mudanças estruturais
7. **SEMPRE** adicionar test scripts para auto-popular tokens/sessions
8. **SEMPRE** documentar tipo de autenticação necessária na descrição

## Consequências

### Positivas

✅ **Consistência**: Todas as collections seguem mesmo padrão
✅ **Rastreabilidade**: Versionamento permite rollback e histórico de mudanças
✅ **Segurança**: Variáveis evitam exposição de credenciais no Git
✅ **Automação**: Test scripts eliminam copy-paste manual de tokens
✅ **Documentação**: Collections servem como documentação viva da API
✅ **Onboarding**: Novos desenvolvedores entendem API rapidamente
✅ **Debug**: Headers padronizados reduzem erros de configuração
✅ **CI/CD**: Collections podem ser usadas em Newman (Postman CLI)

### Negativas

⚠️ **Overhead inicial**: Criar collection completa leva tempo (~2-3h)
⚠️ **Manutenção**: Mudanças na API exigem atualização da collection
⚠️ **Duplicação**: Informação duplicada entre Swagger/OpenAPI e Postman
⚠️ **Disciplina**: Requer que todos desenvolvedores sigam padrões

### Mitigações

- **Template**: Criar template de collection para acelerar criação
- **Automação**: Scripts para gerar collection a partir de OpenAPI spec
- **CI/CD**: Validar que PRs atualizam collection quando mudam endpoints
- **Documentação**: Este ADR serve como guia de referência

## Referências

- [ADR-005: OpenAPI 3.0 / Swagger Documentation](ADR-005-openapi-30-swagger-documentation.md)
- [ADR-006: Git Flow Workflow](ADR-006-git-flow-workflow.md)
- [ADR-009: Headless Authentication](ADR-009-headless-authentication-user-context.md)
- [ADR-011: Controller Security](ADR-011-controller-security-authentication-storage.md)
- [Postman Collection Format v2.1.0](https://schema.getpostman.com/json/collection/v2.1.0/collection.json)
- [docs/api-authentication.md](../api-authentication.md) - Session ID transmission guide

## Exemplos

### Collection Metadata

```json
{
  "info": {
    "_postman_id": "quicksol-api-v1.1",
    "name": "Quicksol Real Estate API v1.1",
    "description": "Complete API documentation...",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    "version": "1.1.0"
  }
}
```

### Endpoint GET Correto

```json
{
  "name": "List Agents",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "PostmanRuntime/7.26.8"},
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
    }
  }
}
```

### Endpoint POST Correto

```json
{
  "name": "Create Agent",
  "request": {
    "method": "POST",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "PostmanRuntime/7.26.8"}
    ],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"jsonrpc\": \"2.0\",\n  \"method\": \"call\",\n  \"params\": {\n    \"session_id\": \"{{session_id}}\",\n    \"name\": \"João Silva\",\n    \"creci\": \"F12345\"\n  }\n}"
    },
    "url": {
      "raw": "{{base_url}}/api/v1/agents",
      "host": ["{{base_url}}"],
      "path": ["api", "v1", "agents"]
    }
  }
}
```

---

**Data de Criação**: 2026-01-17  
**Última Atualização**: 2026-01-17  
**Autor**: Equipe de Desenvolvimento  
**Status**: Aceito
