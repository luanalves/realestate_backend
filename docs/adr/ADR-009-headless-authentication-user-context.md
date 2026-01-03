# ADR 009: Autenticação Headless com Contexto de Usuário

## Status
Proposto

## Contexto

O sistema atual usa **OAuth 2.0 Client Credentials Grant** (RFC 6749), onde:
- Frontend obtém token usando `client_id` + `client_secret`
- Token representa a **aplicação**, não o **usuário**
- `request.env.user` no backend retorna usuário genérico da aplicação
- **Problema:** Não há contexto de qual usuário está fazendo a requisição

**Arquitetura headless** significa:
- Frontend desacoplado (React, Vue, Angular, etc.)
- Backend expõe apenas API REST (sem sessões web do Odoo)
- Autenticação stateless via JWT
- Cada requisição deve carregar identidade do usuário

**Requisitos:**
1. Frontend precisa fazer login com credenciais do usuário (email/senha)
2. Backend deve identificar qual usuário está autenticado em cada request
3. Filtros de empresa (`estate_company_ids`) dependem do usuário
4. Não usar sessões do Odoo (stateless)
5. Token deve expirar e ser renovável

## Decisão

Implementar **OAuth 2.0 Password Grant** (Resource Owner Password Credentials) combinado com **JWT contendo user_id** para autenticação headless com contexto de usuário.

### Fluxo de Autenticação

```
1. Frontend: POST /api/v1/auth/login
   Body: { "username": "user@company.com", "password": "xxx" }

2. Backend valida credenciais contra res.users

3. Backend gera JWT com payload:
   {
     "user_id": 123,
     "username": "user@company.com",
     "company_ids": [5, 8],
     "default_company_id": 5,
     "exp": 1701234567,
     "iat": 1701230967
   }

4. Backend retorna:
   {
     "access_token": "eyJ...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "refresh_token": "xxx",
     "user": {
       "id": 123,
       "name": "João Silva",
       "email": "user@company.com",
       "companies": [{"id": 5, "name": "Imobiliária A"}],
       "default_company_id": 5
     }
   }

5. Frontend armazena token (localStorage/sessionStorage)

6. Frontend envia em TODAS as requisições:
   Authorization: Bearer eyJ...

7. Middleware decodifica JWT e injeta user em request.env:
   request.env = request.env(user=user_from_jwt)
```

### Componentes da Solução

#### 1. Novo Endpoint de Login

**Rota:** `POST /api/v1/auth/login`

**Responsabilidade:**
- Validar username/password contra `res.users`
- Verificar se usuário está ativo
- Gerar JWT com `user_id` e `company_ids`
- Criar registro em `thedevkitchen.oauth.token` vinculado ao usuário

#### 2. Modelo OAuth Token Estendido

**Adicionar campos:**
- `user_id` (Many2one para `res.users`)
- `jti` (Char, unique, indexed) - JWT ID para revogação
- `session_metadata` (JSON) - IP, User-Agent, device info

**Comportamento:**
- Tokens de Client Credentials: `user_id = NULL`, `jti = NULL`
- Tokens de Password Grant: `user_id = <user>`, `jti = UUID único`

**Exemplo:**
```python
class OAuthToken(models.Model):
    _name = 'thedevkitchen.oauth.token'
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        index=True,
        ondelete='cascade',
        help='User authenticated via Password Grant'
    )
    jti = fields.Char(
        string='JWT ID',
        index=True,
        help='Unique token identifier for revocation (UUID)'
    )
    session_metadata = fields.Json(
        string='Session Metadata',
        help='IP, User-Agent, device info for audit'
    )
    
    _sql_constraints = [
        ('jti_unique', 'unique(jti)', 'JWT ID must be unique!'),
    ]
```

#### 3. Middleware JWT Atualizado

**Modificação em `require_jwt` (validação em 3 camadas):**

```python
@functools.wraps(func)
def wrapper(*args, **kwargs):
    # Extrair token do header
    auth_header = request.httprequest.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return error_response(401, 'Missing or invalid Authorization header')
    
    token = auth_header[7:]  # Remove 'Bearer '
    
    # CAMADA 1: Validar assinatura e estrutura do JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return error_response(401, 'Token expired')
    except jwt.InvalidTokenError:
        return error_response(401, 'Invalid token')
    
    # CAMADA 2: Validar token no banco (revogação)
    Token = request.env['thedevkitchen.oauth.token']
    token_record = Token.search([
        ('jti', '=', payload.get('jti')),
        ('revoked', '=', False),
        ('expires_at', '>', fields.Datetime.now()),
    ], limit=1)
    
    if not token_record:
        return error_response(401, 'Token revoked or not found')
    
    # CAMADA 3: Validar usuário ainda existe e está ativo
    if token_record.user_id:
        if not token_record.user_id.active:
            return error_response(401, 'User account is disabled')
        
        # ✅ CRÍTICO: Trocar contexto para usuário autenticado
        request.env = request.env(user=token_record.user_id)
    
    # Attach token info to request
    request.jwt_token = token_record
    request.jwt_payload = payload
    
    return func(*args, **kwargs)
```

#### 4. Refresh Token com Contexto de Usuário

**Rota:** `POST /api/v1/auth/refresh`

**Comportamento:**
- Validar `refresh_token`
- Gerar novo `access_token` com mesmo `user_id`
- Manter contexto de empresa

### Estrutura do JWT

```json
{
  "jti": "550e8400-e29b-41d4-a716-446655440000",  // JWT ID (session identifier) - CRÍTICO
  "sub": "123",                                    // user_id (subject)
  "username": "user@company.com",
  "email": "user@company.com",
  "company_ids": [5, 8],                          // empresas do usuário
  "default_company_id": 5,                        // empresa padrão
  "groups": [                                     // grupos de segurança (opcional)
    "quicksol_estate.group_real_estate_manager"
  ],
  "iss": "odoo-api-gateway",                      // issuer
  "aud": "real-estate-frontend",                  // audience
  "exp": 1701234567,                              // expiration (Unix timestamp)
  "iat": 1701230967,                              // issued at (Unix timestamp)
  "sid": "abc123def456"                           // session_id (referência ao registro oauth.token)
}
```

**Campos críticos de segurança:**
- **`jti`** (JWT ID): Identificador único do token - usado para revogação
- **`sub`** (Subject): ID do usuário - NUNCA deve ser aceito do request body
- **`sid`** (Session ID): Referência ao registro `thedevkitchen.oauth.token` no banco
- **`exp`** (Expiration): Token expira automaticamente (defesa em profundidade)

### Segurança

#### 1. Revogação de Tokens (CRÍTICO)

**Problema:** JWT stateless não pode ser revogado após emissão.

**Solução: Dual-layer validation**
```python
# Middleware valida em DUAS camadas:

# Camada 1: Validar assinatura e expiração do JWT
payload = jwt.decode(token, secret_key, algorithms=['HS256'])

# Camada 2: Validar se token não foi revogado
token_record = Token.search([
    ('id', '=', payload['sid']),        # Session ID
    ('jti', '=', payload['jti']),       # JWT ID
    ('revoked', '=', False),            # Não revogado
    ('expires_at', '>', now()),         # Não expirado no banco
])

if not token_record:
    return error_response(401, 'Token revoked or expired')

# Camada 3: Validar user ainda existe e está ativo
if not token_record.user_id or not token_record.user_id.active:
    return error_response(401, 'User inactive or deleted')
```

**Revogação em cenários:**
- **Logout:** `token_record.write({'revoked': True, 'revoked_at': now()})`
- **Troca de senha:** Revogar TODOS os tokens do usuário
- **Admin desativa user:** Revogar TODOS os tokens automaticamente
- **Suspeita de comprometimento:** Revogar token específico por `jti`

#### 2. Session ID vs User ID

**❌ NUNCA aceitar user_id do request:**
```python
# VULNERÁVEL - atacante pode trocar user_id
user_id = data.get('user_id')  # ❌ PERIGOSO
```

**✅ SEMPRE extrair do JWT validado:**
```python
# SEGURO - user_id vem do token assinado
payload = jwt.decode(token, secret_key)
user_id = payload['sub']  # ✅ CORRETO
token_record = Token.search([('jti', '=', payload['jti'])])
user = token_record.user_id  # ✅ Usuário da sessão
```

#### 3. Password Grant apenas para frontends confiáveis
   - Client Credentials para integrações server-to-server
   - Password Grant para frontend próprio (SPA)
   - **NUNCA** expor Password Grant para aplicações de terceiros

#### 4. JWT assinado com chave secreta forte
   - Usar `HS256` (HMAC-SHA256) ou `RS256` (RSA)
   - Chave mínima de 256 bits (32 caracteres)
   - Chave rotacionável via configuração do Odoo
   - Armazenar chave em variável de ambiente, não hardcoded

#### 5. Token de curta duração
   - **Access token:** 15-60 minutos (recomendado: 30min)
   - **Refresh token:** 7-30 dias (recomendado: 14 dias)
   - Renovação automática antes de expirar (frontend)
   - Expiração no JWT (`exp`) E no banco (`expires_at`)

#### 6. Rate limiting em login
   - Máximo 5 tentativas por IP em 15 minutos
   - Máximo 10 tentativas por username em 1 hora
   - Prevenir brute force de senhas
   - Considerar CAPTCHA após 3 falhas

#### 7. Auditoria de Sessões
   - Logar TODAS as tentativas de login (sucesso e falha)
   - Registrar IP, User-Agent, timestamp
   - Permitir user ver sessões ativas e revogar remotamente
   - Alertar user sobre login de novo dispositivo/localização

## Regras de Implementação

### ✅ SEMPRE

- Incluir `jti` (UUID único) e `sid` (session ID) no JWT
- Incluir `user_id` (sub) e `company_ids` no payload do JWT
- Validar token em 3 camadas: assinatura → banco → usuário ativo
- Consultar banco para verificar se token foi revogado (via `jti`)
- Trocar contexto de `request.env` para usuário do token
- Logar tentativas de login (sucesso e falha) com IP e User-Agent
- Implementar rate limiting em `/auth/login` (5 tentativas/15min)
- Revogar TODOS os tokens ao trocar senha
- Revogar refresh_token e access_token ao fazer logout
- Gerar novo `jti` para cada token (nunca reutilizar)
- Armazenar metadata da sessão (IP, User-Agent, device) para auditoria

### ❌ NUNCA

- Aceitar `user_id` ou `company_ids` do request body (sempre extrair do JWT)
- Confiar apenas na assinatura do JWT (sempre validar no banco)
- Permitir troca de `user_id` sem re-autenticação
- Gerar token sem validar credenciais do usuário
- Armazenar senha (hash ou plain) no JWT
- Usar sessões do Odoo (stateful) para autenticação de API
- Retornar mensagem específica "usuário não existe" vs "senha incorreta" (info leakage)
- Permitir token continuar válido após logout (sempre revogar via `jti`)
- Confiar em `exp` do JWT sem validar `expires_at` no banco
- Ignorar validação de `user_id.active` (usuário pode ser desativado)

## Consequências

### Positivas

- **Contexto de usuário em todas as requisições** - `request.env.user` representa usuário real
- **Stateless** - Não depende de sessões do Odoo
- **Escalável** - Frontend pode ser hospedado separadamente
- **Multi-tenancy funcional** - Filtros por `estate_company_ids` funcionam corretamente
- **Renovação transparente** - Refresh token permite renovar sem novo login
- **Auditoria completa** - Todos os logs têm usuário real identificado

### Negativas

- **Complexidade aumentada** - Dois fluxos OAuth (Client Credentials + Password Grant)
- **Gestão de tokens** - Tabela de tokens cresce (mitigado com TTL e cleanup)
- **Segurança do frontend** - JWT exposto no browser (usar httpOnly cookies ou curta duração)
- **Invalidação imediata difícil** - JWT válido até expirar (mitigado com blacklist)

### Alternativas Consideradas

#### 1. Session-based Authentication (REJEITADA)
- **Problema:** Não é stateless, quebra arquitetura headless
- **Problema:** Dificulta deploy independente de frontend

#### 2. API Key por Usuário (REJEITADA)
- **Problema:** Sem expiração automática
- **Problema:** Difícil revogar sem afetar todas as sessões

#### 3. OAuth 2.0 Authorization Code Flow (REJEITADA para MVP)
- **Vantagem:** Mais seguro (senha nunca vai ao frontend)
- **Problema:** Requer servidor OAuth separado
- **Problema:** Complexidade muito alta para MVP
- **Decisão:** Considerar para v2.0

## Migração

### Fase 1: Adicionar Suporte a Password Grant
- Criar endpoint `/api/v1/auth/login`
- Adicionar `user_id` em `thedevkitchen.oauth.token`
- Estender middleware para trocar contexto de usuário

### Fase 2: Atualizar Frontend
- Implementar tela de login
- Armazenar token no localStorage/sessionStorage
- Adicionar interceptor HTTP para incluir Authorization header
- Implementar auto-refresh antes de expiração

### Fase 3: Deprecar Client Credentials para Usuários
- Manter Client Credentials apenas para integrações M2M
- Password Grant para autenticação de usuários humanos

## Referências

- RFC 6749 - OAuth 2.0 (Password Grant): https://tools.ietf.org/html/rfc6749#section-4.3
- RFC 7519 - JSON Web Token (JWT): https://tools.ietf.org/html/rfc7519
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- ADR-008: API Security Multi-Tenancy
