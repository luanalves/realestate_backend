# API Gateway - OAuth 2.0 para Odoo 18.0

Módulo de autenticação e autorização OAuth 2.0 para expor APIs REST seguras no Odoo.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Autenticação OAuth 2.0](#autenticação-oauth-20)
- [Endpoints Disponíveis](#endpoints-disponíveis)
- [Exemplos de Uso](#exemplos-de-uso)
- [Segurança](#segurança)
- [Documentação Interativa](#documentação-interativa)
- [Testes](#testes)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O **API Gateway** é um módulo completo de autenticação OAuth 2.0 desenvolvido para o Odoo 18.0, permitindo que aplicações externas consumam APIs REST de forma segura e padronizada.

### Principais Funcionalidades

- ✅ **OAuth 2.0 Client Credentials Grant** - Autenticação máquina-a-máquina
- ✅ **JWT (JSON Web Tokens)** - Tokens stateless e seguros
- ✅ **Refresh Tokens** - Renovação de tokens sem re-autenticação
- ✅ **Token Revocation** - Invalidação de tokens (RFC 7009)
- ✅ **API Endpoint Registry** - Registro centralizado de endpoints
- ✅ **Access Logs** - Auditoria completa de acessos
- ✅ **Swagger UI** - Documentação interativa automática
- ✅ **Rate Limiting** - Proteção contra abuso
- ✅ **CORS Support** - Integração com SPAs e apps mobile

---

## 🚀 Características

### Segurança

| Recurso | Implementação | Padrão |
|---------|---------------|--------|
| **Criptografia de Tokens** | JWT com HS256 | RFC 7519 |
| **Hashing de Secrets** | SHA-256 | FIPS 180-4 |
| **Geração de Chaves** | `secrets.token_urlsafe(32)` | CSPRNG |
| **Expiração de Tokens** | 1 hora (configurável) | OAuth 2.0 |
| **Refresh Tokens** | 30 dias (configurável) | OAuth 2.0 |
| **Revogação** | Blacklist em banco | RFC 7009 |

### Algoritmos de Criptografia

```python
# JWT - JSON Web Token
{
  "alg": "HS256",        # HMAC com SHA-256
  "typ": "JWT"
}

# Payload
{
  "iss": "data variable environment",  # Issuer (configurável via env)
  "sub": "client_id",                   # Subject (ID da aplicação)
  "exp": 1234567890,                    # Expiration (Unix timestamp)
  "iat": 1234564290,                    # Issued At (Unix timestamp)
  "jti": "unique-token-id",             # JWT ID (UUID)
  "application_id": 123                 # ID da aplicação no Odoo
}

# Assinatura
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  client_secret  # Chave secreta da aplicação
)
```

---

## ⚙️ Configuração

### 1. Configurar Variáveis de Ambiente (Opcional)

```bash
# docker-compose.yml
services:
  odoo:
    environment:
      - JWT_ISSUER=thedevkitchen-api-gateway  # Nome do emissor JWT
      - JWT_EXPIRATION=3600                    # Expiração em segundos (1h)
      - REFRESH_TOKEN_EXPIRATION=2592000      # Expiração em segundos (30d)
```

### 2. Criar Aplicação OAuth

**Via Interface Web:**

1. Acesse `Settings → Technical → API Gateway → OAuth Applications`
2. Clique em `Create`
3. Preencha:
   - **Name**: Nome da aplicação
   - **Description**: Descrição (opcional)
   - **Active**: Marque como ativo
4. Salve

**Credenciais geradas automaticamente:**
- `client_id`: Identificador público (43 caracteres)
- `client_secret`: Chave secreta (64 caracteres) - **Guarde com segurança!**

**Via API (Python):**

```python
import requests

# Login no Odoo
session = requests.Session()
session.post('http://localhost:8069/web/login', data={
    'login': 'admin',
    'password': 'admin',
    'db': 'realestate'
})

# Criar aplicação
response = session.post(
    'http://localhost:8069/web/dataset/call_kw/oauth.application/create',
    json={
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': 'oauth.application',
            'method': 'create',
            'args': [{
                'name': 'My External App',
                'description': 'Application for mobile app',
                'active': True
            }],
            'kwargs': {}
        },
        'id': 1
    }
)

app_id = response.json()['result']
print(f"Application ID: {app_id}")
```

---

## 🔐 Autenticação OAuth 2.0

### Client Credentials Grant Flow

```
┌─────────────┐                                  ┌─────────────┐
│   Client    │                                  │   Odoo API  │
│ Application │                                  │   Gateway   │
└──────┬──────┘                                  └──────┬──────┘
       │                                                │
       │  POST /api/v1/auth/token                      │
       │  {                                             │
       │    "grant_type": "client_credentials",         │
       │    "client_id": "client_xxx",                  │
       │    "client_secret": "secret_yyy"               │
       │  }                                             │
       │───────────────────────────────────────────────>│
       │                                                │
       │                                        ┌───────┴───────┐
       │                                        │ Validate      │
       │                                        │ Credentials   │
       │                                        └───────┬───────┘
       │                                                │
       │  200 OK                                        │
       │  {                                             │
       │    "access_token": "eyJhbGc...",               │
       │    "token_type": "Bearer",                     │
       │    "expires_in": 3600,                         │
       │    "refresh_token": "refresh_xxx"              │
       │  }                                             │
       │<───────────────────────────────────────────────│
       │                                                │
       │  GET /api/v1/properties                        │
       │  Authorization: Bearer eyJhbGc...              │
       │───────────────────────────────────────────────>│
       │                                                │
       │                                        ┌───────┴───────┐
       │                                        │ Validate JWT  │
       │                                        │ Check Claims  │
       │                                        └───────┬───────┘
       │                                                │
       │  200 OK                                        │
       │  { "data": [...] }                             │
       │<───────────────────────────────────────────────│
       │                                                │
```

---

## 📡 Endpoints Disponíveis

### Autenticação

#### 1. **Obter Token de Acesso**

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "client_id": "client_fmNevWbfaoqiD0uECObPvQ",
  "client_secret": "0zMAjjqDevxhDe5OBo2zx8HRBf87cgYej3mcSbPanp8TVMhfynLD3nyY3yjAXpZn"
}
```

**Resposta (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0aGVkZXZraXRjaGVuLWFwaS1nYXRld2F5Iiwic3ViIjoiY2xpZW50X2ZtTmV2V2JmYW9xaUQwdUVDT2JQdlEiLCJleHAiOjE3MzE4NzYxMjMsImlhdCI6MTczMTg3MjUyMywianRpIjoiYWJjMTIzIiwiYXBwbGljYXRpb25faWQiOjF9.signature",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_abc123xyz789"
}
```

**Erros:**

| Código | Erro | Descrição |
|--------|------|-----------|
| 400 | `invalid_request` | Parâmetros ausentes ou inválidos |
| 401 | `invalid_client` | Credenciais inválidas |
| 400 | `unsupported_grant_type` | Grant type não suportado |

---

#### 2. **Renovar Token (Refresh)**

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "grant_type": "refresh_token",
  "refresh_token": "refresh_abc123xyz789"
}
```

**Resposta (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_abc123xyz789"
}
```

> **Nota:** O `refresh_token` permanece o mesmo. Apenas o `access_token` é renovado.

---

#### 3. **Revogar Token**

**Opção A: Via Authorization Header**

```http
POST /api/v1/auth/revoke
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{}
```

**Opção B: Via Request Body**

```http
POST /api/v1/auth/revoke
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Resposta (200 OK):**

```json
{
  "message": "Token revoked successfully"
}
```

> **RFC 7009:** Revogar um token inexistente também retorna 200 OK (por segurança).

---

### Endpoints de Teste

#### 4. **Testar Token Válido**

```http
GET /api/v1/test/protected
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Resposta (200 OK):**

```json
{
  "message": "Access granted to protected resource",
  "authenticated": true,
  "application_id": 1,
  "application_name": "My External App",
  "token_expires_at": "2024-11-17T15:30:00Z"
}
```

---

### Documentação e Monitoramento

#### 5. **Swagger UI (Documentação Interativa)**

```
GET /api/docs
```

Interface web para testar todos os endpoints disponíveis.

**Link:** [http://localhost:8069/api/docs](http://localhost:8069/api/docs)

#### 6. **OpenAPI Spec (JSON)**

```
GET /api/v1/openapi.json
```

Especificação OpenAPI 3.0 para integração com ferramentas.

---

## 💻 Exemplos de Uso

### cURL

```bash
# 1. Obter token
TOKEN_RESPONSE=$(curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "client_fmNevWbfaoqiD0uECObPvQ",
    "client_secret": "0zMAjjqDevxhDe5OBo2zx8HRBf87cgYej3mcSbPanp8TVMhfynLD3nyY3yjAXpZn"
  }')

# 2. Extrair access_token
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# 3. Usar token em requisição protegida
curl -X GET http://localhost:8069/api/v1/test/protected \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 4. Renovar token
REFRESH_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.refresh_token')

curl -X POST http://localhost:8069/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\": \"refresh_token\", \"refresh_token\": \"$REFRESH_TOKEN\"}"

# 5. Revogar token
curl -X POST http://localhost:8069/api/v1/auth/revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{}'
```

---

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8069"

# Credenciais
CLIENT_ID = "client_fmNevWbfaoqiD0uECObPvQ"
CLIENT_SECRET = "0zMAjjqDevxhDe5OBo2zx8HRBf87cgYej3mcSbPanp8TVMhfynLD3nyY3yjAXpZn"

# 1. Obter token
token_response = requests.post(
    f"{BASE_URL}/api/v1/auth/token",
    json={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
)

token_data = token_response.json()
access_token = token_data["access_token"]
refresh_token = token_data["refresh_token"]

print(f"Access Token: {access_token[:50]}...")
print(f"Expires in: {token_data['expires_in']} seconds")

# 2. Usar token em requisição protegida
protected_response = requests.get(
    f"{BASE_URL}/api/v1/test/protected",
    headers={"Authorization": f"Bearer {access_token}"}
)

print(f"Protected Resource: {protected_response.json()}")

# 3. Renovar token
refresh_response = requests.post(
    f"{BASE_URL}/api/v1/auth/refresh",
    json={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
)

new_access_token = refresh_response.json()["access_token"]
print(f"New Access Token: {new_access_token[:50]}...")

# 4. Revogar token
revoke_response = requests.post(
    f"{BASE_URL}/api/v1/auth/revoke",
    headers={"Authorization": f"Bearer {access_token}"},
    json={}
)

print(f"Revocation: {revoke_response.json()}")
```

---

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8069';
const CLIENT_ID = 'client_fmNevWbfaoqiD0uECObPvQ';
const CLIENT_SECRET = '0zMAjjqDevxhDe5OBo2zx8HRBf87cgYej3mcSbPanp8TVMhfynLD3nyY3yjAXpZn';

async function main() {
  try {
    // 1. Obter token
    const tokenResponse = await axios.post(`${BASE_URL}/api/v1/auth/token`, {
      grant_type: 'client_credentials',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET
    });

    const { access_token, refresh_token, expires_in } = tokenResponse.data;
    console.log(`Access Token: ${access_token.substring(0, 50)}...`);
    console.log(`Expires in: ${expires_in} seconds`);

    // 2. Usar token em requisição protegida
    const protectedResponse = await axios.get(`${BASE_URL}/api/v1/test/protected`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    console.log('Protected Resource:', protectedResponse.data);

    // 3. Renovar token
    const refreshResponse = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
      grant_type: 'refresh_token',
      refresh_token: refresh_token
    });

    const new_access_token = refreshResponse.data.access_token;
    console.log(`New Access Token: ${new_access_token.substring(0, 50)}...`);

    // 4. Revogar token
    const revokeResponse = await axios.post(
      `${BASE_URL}/api/v1/auth/revoke`,
      {},
      { headers: { Authorization: `Bearer ${access_token}` } }
    );

    console.log('Revocation:', revokeResponse.data);

  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

main();
```

---

### Postman Collection

Importe a collection do Postman para testar rapidamente:

```json
{
  "info": {
    "name": "Odoo API Gateway - OAuth 2.0",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "1. Get Access Token",
      "request": {
        "method": "POST",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"grant_type\": \"client_credentials\",\n  \"client_id\": \"{{client_id}}\",\n  \"client_secret\": \"{{client_secret}}\"\n}"
        },
        "url": "{{base_url}}/api/v1/auth/token"
      }
    },
    {
      "name": "2. Test Protected Endpoint",
      "request": {
        "method": "GET",
        "header": [{"key": "Authorization", "value": "Bearer {{access_token}}"}],
        "url": "{{base_url}}/api/v1/test/protected"
      }
    }
  ],
  "variable": [
    {"key": "base_url", "value": "http://localhost:8069"},
    {"key": "client_id", "value": ""},
    {"key": "client_secret", "value": ""},
    {"key": "access_token", "value": ""}
  ]
}
```

---

## 🔒 Segurança

### Boas Práticas

#### ✅ DO (Faça)

- ✅ Armazene `client_secret` em variáveis de ambiente
- ✅ Use HTTPS em produção
- ✅ Implemente rate limiting no proxy reverso (nginx)
- ✅ Monitore logs de acesso regularmente
- ✅ Revogue tokens comprometidos imediatamente
- ✅ Use refresh tokens para renovação automática
- ✅ Configure expiração adequada (1h para access, 30d para refresh)

#### ❌ DON'T (Não faça)

- ❌ Nunca exponha `client_secret` em frontend/mobile apps
- ❌ Não commite credenciais no Git
- ❌ Não reutilize tokens entre ambientes (dev/staging/prod)
- ❌ Não use HTTP em produção
- ❌ Não armazene tokens em localStorage (XSS vulnerability)

### Configuração de Produção

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location /api/ {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📚 Documentação Interativa

### Swagger UI

Acesse a documentação interativa em:

```
http://localhost:8069/api/docs
```

**Recursos:**
- 🔍 Explorar todos os endpoints disponíveis
- 🧪 Testar requisições diretamente no browser
- 📖 Ver schemas de request/response
- 🔐 Autenticar com OAuth 2.0

**Screenshot:**

```
┌─────────────────────────────────────────────────────────────┐
│ 🚀 Odoo API Gateway - Swagger UI                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ OAuth 2.0 Authentication                                     │
│ ├─ POST /api/v1/auth/token       Generate access token      │
│ ├─ POST /api/v1/auth/refresh     Refresh access token       │
│ └─ POST /api/v1/auth/revoke      Revoke token               │
│                                                              │
│ Protected Resources                                          │
│ └─ GET  /api/v1/test/protected   Test authentication        │
│                                                              │
│ [Authorize] 🔒                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### OpenAPI Specification

Baixe a especificação OpenAPI 3.0:

```bash
curl http://localhost:8069/api/v1/openapi.json > openapi.json
```

Use com ferramentas:
- **Postman**: Import → OpenAPI
- **Insomnia**: Import → OpenAPI
- **Swagger Codegen**: Gerar SDKs automaticamente

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── unit/                           # 76 testes (sem banco)
│   ├── test_oauth_application.py   # 8 tests
│   ├── test_oauth_token.py         # 10 tests
│   ├── test_api_endpoint.py        # 11 tests
│   ├── test_api_access_log.py      # 11 tests
│   ├── test_auth_controller.py     # 10 tests
│   ├── test_jwt_service.py         # 16 tests
│   └── test_middleware.py          # 10 tests
│
├── integration/                    # 17 testes (com banco)
│   └── test_oauth_endpoints.py     # 17 tests - API completa
│
└── e2e/ (Cypress)                  # 47 testes (browser)
    ├── api-gateway.cy.js           # 27 tests - UI/UX
    └── tokens-lifecycle.cy.js      # 20 tests - Lifecycle
```

### Executar Testes

#### Unit Tests (Rápido - ~2s)

```bash
cd 18.0/extra-addons/api_gateway

# Todos os unit tests
python -m pytest tests/ -k "not integration" -v

# Apenas JWT service
python -m pytest tests/test_jwt_service.py -v

# Com cobertura
python -m pytest tests/ -k "not integration" --cov=. --cov-report=html
```

#### Integration Tests (Médio - ~15s)

```bash
# Via Docker
cd 18.0
docker compose exec odoo python3 -m pytest \
  /mnt/extra-addons/api_gateway/tests/integration/ -v

# OU via Odoo test runner
docker compose exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d test_realestate \
  -i api_gateway \
  --test-enable \
  --stop-after-init
```

#### E2E Tests (Lento - ~3min)

```bash
# Certifique-se de que Odoo está rodando
cd 18.0
docker compose up -d

# Execute Cypress
cd ..
npm run cypress:run

# OU modo interativo
npm run cypress:open
```

### Comparação de Performance

| Tipo | Ferramenta | Testes | Tempo | Browser? | Banco? |
|------|-----------|--------|-------|----------|--------|
| **Unit** | Pytest | 76 | ~2s | ❌ | ❌ |
| **Integration** | Pytest | 17 | ~15s | ❌ | ✅ |
| **E2E** | Cypress | 47 | ~3min | ✅ | ✅ |

**Exemplo de Output:**

```bash
$ python -m pytest tests/ -k "not integration" -v

tests/test_jwt_service.py::test_generate_token PASSED
tests/test_jwt_service.py::test_validate_token PASSED
tests/test_jwt_service.py::test_expired_token PASSED
tests/test_oauth_application.py::test_create_application PASSED
...

========== 76 passed in 2.14s ==========
```

---

## 🐛 Troubleshooting

### Problema: "Invalid client credentials"

**Causa:** `client_id` ou `client_secret` incorretos.

**Solução:**
1. Verifique as credenciais em `Settings → Technical → API Gateway → OAuth Applications`
2. Certifique-se de copiar corretamente (sem espaços)
3. Valide que a aplicação está **Active = True**

---

### Problema: "Token has expired"

**Causa:** Access token expirou (padrão: 1 hora).

**Solução:** Use refresh token para obter novo access token:

```bash
curl -X POST http://localhost:8069/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "refresh_token", "refresh_token": "YOUR_REFRESH_TOKEN"}'
```

---

### Problema: "Invalid token signature"

**Causa:** Token foi alterado ou gerado com secret diferente.

**Solução:**
1. Não modifique manualmente o token JWT
2. Gere um novo token se necessário
3. Verifique que não há proxy modificando headers

---

### Problema: Swagger UI não carrega

**Causa:** Módulo `swagger-ui-dist` não instalado.

**Solução:**

```bash
# Instalar no container Odoo
docker compose exec odoo pip3 install swagger-ui-dist
docker compose restart odoo
```

---

### Problema: CORS errors no browser

**Causa:** Requisição de origem diferente bloqueada.

**Solução:** Configure CORS no nginx ou Odoo:

```python
# Em seu controller
from odoo.http import route, request

@route('/api/v1/test/protected', type='json', auth='none', methods=['GET', 'OPTIONS'], cors='*')
def protected_endpoint(self, **kwargs):
    if request.httprequest.method == 'OPTIONS':
        return request.make_response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type'
        })
    # ... resto do código
```

---

## 📝 Logs e Monitoramento

### Access Logs

Todos os acessos são registrados em:

```
Settings → Technical → API Gateway → Access Logs
```

**Campos registrados:**
- Endpoint acessado
- Método HTTP
- IP do cliente
- User Agent
- Application ID
- Tempo de resposta (ms)
- Status HTTP
- Erro (se houver)
- Timestamp

### Visualização de Métricas

```sql
-- Top 10 endpoints mais acessados
SELECT 
    endpoint, 
    COUNT(*) as total_requests,
    AVG(response_time) as avg_response_time
FROM api_access_log
WHERE create_date >= NOW() - INTERVAL '7 days'
GROUP BY endpoint
ORDER BY total_requests DESC
LIMIT 10;

-- Erros nas últimas 24h
SELECT 
    endpoint,
    status_code,
    error_message,
    COUNT(*) as error_count
FROM api_access_log
WHERE 
    create_date >= NOW() - INTERVAL '1 day'
    AND status_code >= 400
GROUP BY endpoint, status_code, error_message
ORDER BY error_count DESC;
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Checklist para PR

- [ ] Testes passando (`pytest tests/ -v`)
- [ ] Cobertura de testes > 80%
- [ ] Documentação atualizada
- [ ] CHANGELOG.md atualizado
- [ ] Seguir convenções de código (PEP 8)

---

## 📄 Licença

Este módulo é distribuído sob a licença **LGPL-3.0**.

---

## 📞 Suporte

- **Documentação**: [Swagger UI](http://localhost:8069/api/docs)
- **Issues**: [GitHub Issues](https://github.com/luanalves/odoo-docker/issues)
- **Odoo Community**: [discuss.odoo.com](https://discuss.odoo.com)

---

## 🙏 Agradecimentos

- [Odoo SA](https://www.odoo.com) - Framework base
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT implementation
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749) - OAuth 2.0 specification
- [RFC 7009](https://tools.ietf.org/html/rfc7009) - Token Revocation
- [RFC 7519](https://tools.ietf.org/html/rfc7519) - JSON Web Token

---

**Desenvolvido com ❤️ para a comunidade Odoo**

**Versão:** 18.0.1.0  
**Data:** Novembro 2025
