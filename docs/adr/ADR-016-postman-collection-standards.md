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
  "refresh_token": "auto_populated_by_test_script",
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

Session ID vai no **body JSON** (formato direto, sem wrapper JSONRPC):


### 4. OAuth Token Endpoint

**Endpoint**: `POST {{base_url}}/api/v1/auth/token`

**⚠️ IMPORTANTE**: Endpoints OAuth **NÃO** usam formato JSON-RPC. Enviar JSON direto no body:

```json
// ✅ CORRETO - JSON direto
{"client_id": "xxx", "client_secret": "yyy", "grant_type": "client_credentials"}

// ❌ ERRADO - wrapper JSON-RPC (NÃO usar)
{"jsonrpc": "2.0", "method": "call", "params": {...}}
```

**Body**:
```json
{
  "client_id": "{{client_id}}",
  "client_secret": "{{client_secret}}",
  "grant_type": "client_credentials"
}
```

**Resposta esperada** (OAuth Token Response):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "dGhpc19pc19hX3JlZnJlc2hfdG9rZW4..."
}
```

**Test Script Obrigatório** (auto-popula access_token **E** refresh_token):
```javascript
const jsonData = pm.response.json();
if (jsonData && jsonData.access_token) {
    pm.environment.set('access_token', jsonData.access_token);
    console.log('✅ Access token saved to environment');
    
    // Salvar refresh_token para uso em endpoints de refresh
    if (jsonData.refresh_token) {
        pm.environment.set('refresh_token', jsonData.refresh_token);
        console.log('✅ Refresh token saved to environment');
    }
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

### 8. Padrões de Request Body: company_ids

#### 8.1 Contexto

Endpoints que criam/atualizam recursos vinculados a empresas (properties, leads, etc.) precisam saber a qual(is) imobiliária(s) o recurso pertence. O sistema suporta **multi-tenancy** com usuários podendo estar associados a múltiplas companies.

#### 8.2 Comportamento do Campo `company_ids`

**Opção 1: Explícito (Recomendado)**

Passar `company_ids` no body do request:

```json
{
  "name": "Apartamento 101",
  "property_type_id": 1,
  "area": 85.5,
  "company_ids": [63]
}
```

Para múltiplas empresas:
```json
{
  "name": "Apartamento 101",
  "company_ids": [63, 64, 65]
}
```

**Opção 2: Automático (Fallback)**

Se `company_ids` **NÃO** for enviado, o sistema aplica o seguinte fallback:

1. **Primeira tentativa**: Usa `estate_default_company_id` do usuário (empresa padrão configurada)
2. **Segunda tentativa**: Usa a primeira empresa em `estate_company_ids` do usuário
3. **Nenhuma empresa**: Retorna erro 400

**Implementação**: `CompanyValidator.ensure_company_ids()` em `services/company_validator.py`

#### 8.3 Validação de Acesso

O sistema **SEMPRE** valida que o usuário tem permissão para associar recursos às companies especificadas:

- **Admin** (`base.group_system`): Pode usar qualquer company (bypass)
- **Owner/Manager/Agent**: Só as companies em `estate_company_ids`
- **Violation**: Retorna 403 com `"Access denied to companies: [ids]"`

**Implementação**: `CompanyValidator.validate_company_ids()` em `services/company_validator.py`

#### 8.4 Recomendação para Collections

Em **Postman Collections**, para cenários com **múltiplas imobiliárias**:

✅ **SEMPRE** passar `company_ids` explicitamente no body para evitar ambiguidade

❌ **EVITAR** depender do fallback automático em testes (comportamento imprevisível se usuário mudar empresa padrão)

**Exemplo de request completo**:

```json
POST {{base_url}}/api/v1/properties
Headers:
  Authorization: Bearer {{access_token}}
  X-Openerp-Session-Id: {{session_id}}
  User-Agent: {{user_agent}}
  Content-Type: application/json

Body:
{
  "name": "Apartamento Jardins",
  "property_type_id": 1,
  "area": 120.5,
  "company_ids": [63],
  "zip_code": "01310-100",
  "state_id": 1,
  "city": "São Paulo",
  "street": "Av. Paulista",
  "street_number": "1000",
  "location_type_id": 2
}
```

**Pre-request Script** (opcional - para obter company_id automaticamente):

```javascript
// Se você quer usar a primeira company do usuário automaticamente
const meEndpoint = pm.environment.get('base_url') + '/api/v1/me';
pm.sendRequest({
    url: meEndpoint,
    method: 'GET',
    header: {
        'Authorization': 'Bearer ' + pm.environment.get('access_token'),
        'X-Openerp-Session-Id': pm.environment.get('session_id'),
        'User-Agent': pm.environment.get('user_agent')
    }
}, function (err, response) {
    if (!err && response.json().companies && response.json().companies.length > 0) {
        pm.environment.set('default_company_id', response.json().companies[0].id);
        console.log('✅ Default company ID set: ' + response.json().companies[0].id);
    }
});
```

**Nota**: Este pre-request adiciona latência (~100-200ms). Preferir hardcoding de `company_ids` quando possível.

### 9. Regras de Ouro

1. **🚫 NUNCA** usar wrapper JSON-RPC (`{"jsonrpc": "2.0", "method": "call", "params": {...}}`) - enviar JSON direto no body
2. **NUNCA** enviar `session_id` no body de requisições GET - será ignorado
3. **SEMPRE** usar variáveis `{{...}}` ao invés de valores hardcoded
4. **SEMPRE** incluir User-Agent para evitar falha de fingerprint
5. **SEMPRE** manter User-Agent consistente durante toda a sessão
6. **SEMPRE** versionar collections ao fazer mudanças estruturais
7. **SEMPRE** adicionar test scripts para auto-popular tokens/sessions (incluindo `refresh_token`)
8. **SEMPRE** documentar tipo de autenticação necessária na descrição
9. **SEMPRE** salvar `refresh_token` em variável de ambiente (usado por endpoints de refresh)
10. **SEMPRE** passar `company_ids` explicitamente em endpoints multi-tenant para evitar ambiguidade

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


---

**Data de Criação**: 2026-01-17  
**Última Atualização**: 2026-01-17  
**Autor**: Equipe de Desenvolvimento  
**Status**: Aceito
