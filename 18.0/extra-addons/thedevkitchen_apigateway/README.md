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

**Versão:** 18.0.1.0  
**Data:** Novembro 2025
