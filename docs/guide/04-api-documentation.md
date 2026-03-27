# Capítulo 4: Documentação da API

Como usar e testar a API REST do sistema Realestate.

---

## 🎯 Overview

O sistema Realestate expõe uma API REST completa documentada com **OpenAPI 3.0** (Swagger).

### Características principais
- **OpenAPI 3.0** - Especificação padrão da indústria
- **Swagger UI** - Interface interativa para testes
- **Autenticação OAuth 2.0** - Token Bearer JWT
- **Versionamento** - API v1 (`/api/v1/`)
- **Rate Limiting** - Proteção contra abuso
- **CORS configurado** - Para integração cross-origin

---

## 🌐 Acessando a Documentação

### Swagger UI (Interface Interativa)

**Local:**
```
http://localhost:8069/api/docs
```

**Produção:**
```
https://torque-backoffice.thedevkitchen.com.br/api/docs
```

A interface Swagger permite:
- ✅ Visualizar todos os endpoints disponíveis
- ✅ Ver schemas de request/response
- ✅ Testar endpoints diretamente no navegador
- ✅ Copiar exemplos de código (curl, Python, JavaScript)
- ✅ Autenticar e fazer requisições reais

### OpenAPI Specification (JSON)

**Local:**
```
http://localhost:8069/api/v1/openapi.json
```

**Produção:**
```
https://torque-backoffice.thedevkitchen.com.br/api/v1/openapi.json
```

Use este endpoint para:
- Importar em Postman
- Importar em Insomnia
- Gerar clients automáticos (openapi-generator)
- Integração com ferramentas CI/CD

---

## 🔐 Autenticação

A API usa **OAuth 2.0** com **JWT Tokens**.

### 1. Obter Token de Acesso

**Endpoint:** `POST /api/v1/oauth/token`

**Request:**
```bash
curl -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "db": "realestate",
      "login": "admin",
      "password": "admin"
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "userinfo"
  }
}
```

### 2. Usar o Token

Adicione o token no header `Authorization` de todas as requisições:

```bash
curl -X GET http://localhost:8069/api/v1/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Refresh Token

Quando o `access_token` expirar (1 hora), use o `refresh_token`:

**Endpoint:** `POST /api/v1/oauth/refresh`

```bash
curl -X POST http://localhost:8069/api/v1/oauth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }'
```

---

## 🚀 Testando no Swagger UI

### Passo a passo

#### 1. Acessar o Swagger
Abra http://localhost:8069/api/docs no navegador.

#### 2. Obter token
1. Procure o endpoint **POST /api/v1/oauth/token**
2. Clique em **"Try it out"**
3. Preencha os campos:
   ```json
   {
     "db": "realestate",
     "login": "admin",
     "password": "admin"
   }
   ```
4. Clique em **"Execute"**
5. Copie o `access_token` da resposta

#### 3. Autorizar
1. Clique no botão **"Authorize"** (cadeado verde no topo)
2. Cole o token no campo:
   ```
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
3. Clique em **"Authorize"**
4. Feche o modal

#### 4. Testar endpoints
Agora todos os endpoints estão autorizados! Você pode testar qualquer endpoint:

1. Escolha um endpoint (ex: **GET /api/v1/users**)
2. Clique em **"Try it out"**
3. Preencha parâmetros (se necessário)
4. Clique em **"Execute"**
5. Veja a resposta

---

## 📋 Principais Endpoints

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/oauth/token` | Obter access token |
| POST | `/api/v1/oauth/refresh` | Renovar access token |
| POST | `/api/v1/oauth/revoke` | Revogar token |

### Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/users` | Listar usuários |
| POST | `/api/v1/users` | Criar usuário |
| GET | `/api/v1/users/{id}` | Obter usuário |
| PUT | `/api/v1/users/{id}` | Atualizar usuário |
| DELETE | `/api/v1/users/{id}` | Deletar usuário |
| POST | `/api/v1/users/invite` | Convidar usuário |

### Propriedades

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/properties` | Listar propriedades |
| POST | `/api/v1/properties` | Criar propriedade |
| GET | `/api/v1/properties/{id}` | Obter propriedade |
| PUT | `/api/v1/properties/{id}` | Atualizar propriedade |
| DELETE | `/api/v1/properties/{id}` | Deletar propriedade |

### Contratos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/contracts` | Listar contratos |
| POST | `/api/v1/contracts` | Criar contrato |
| GET | `/api/v1/contracts/{id}` | Obter contrato |
| PUT | `/api/v1/contracts/{id}` | Atualizar contrato |
| POST | `/api/v1/contracts/{id}/sign` | Assinar contrato |

Ver documentação completa no Swagger para todos os endpoints disponíveis.

---

## 🧪 Exemplos de Uso

### Python (requests)

```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8069/api/v1"

# 1. Autenticar
auth_response = requests.post(
    f"{BASE_URL}/oauth/token",
    json={
        "jsonrpc": "2.0",
        "params": {
            "db": "realestate",
            "login": "admin",
            "password": "admin"
        }
    }
)
token = auth_response.json()["result"]["access_token"]

# 2. Headers com token
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 3. Listar usuários
users_response = requests.get(
    f"{BASE_URL}/users",
    headers=headers
)
users = users_response.json()
print(f"Total de usuários: {len(users['result'])}")

# 4. Criar propriedade
property_data = {
    "jsonrpc": "2.0",
    "params": {
        "name": "Apartamento Vila Mariana",
        "property_type": "apartment",
        "bedrooms": 2,
        "price": 450000
    }
}
property_response = requests.post(
    f"{BASE_URL}/properties",
    headers=headers,
    json=property_data
)
print(f"Propriedade criada: ID {property_response.json()['result']['id']}")
```

### JavaScript (fetch)

```javascript
// Base URL
const BASE_URL = "http://localhost:8069/api/v1";

// 1. Autenticar
async function authenticate() {
  const response = await fetch(`${BASE_URL}/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      params: {
        db: "realestate",
        login: "admin",
        password: "admin"
      }
    })
  });
  const data = await response.json();
  return data.result.access_token;
}

// 2. Listar propriedades
async function listProperties(token) {
  const response = await fetch(`${BASE_URL}/properties`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });
  const data = await response.json();
  return data.result;
}

// Uso
(async () => {
  const token = await authenticate();
  const properties = await listProperties(token);
  console.log(`Total de propriedades: ${properties.length}`);
})();
```

### cURL

```bash
# 1. Autenticar
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "db": "realestate",
      "login": "admin",
      "password": "admin"
    }
  }' | jq -r '.result.access_token')

# 2. Listar propriedades
curl -X GET http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"

# 3. Criar propriedade
curl -X POST http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "name": "Casa Jardins",
      "property_type": "house",
      "bedrooms": 3,
      "price": 850000
    }
  }'
```

---

## 📦 Schemas de Dados

### User Schema

```json
{
  "id": 1,
  "name": "João Silva",
  "email": "joao@example.com",
  "login": "joao.silva",
  "groups": ["Real Estate Manager"],
  "company_id": 1,
  "company_name": "TheDevKitchen Imóveis",
  "active": true,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-03-20T14:22:00Z"
}
```

### Property Schema

```json
{
  "id": 42,
  "name": "Apartamento Vila Mariana",
  "property_type": "apartment",
  "bedrooms": 2,
  "bathrooms": 1,
  "area": 65.5,
  "price": 450000,
  "address": "Rua Domingos de Morais, 1234",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "04010-100",
  "status": "available",
  "agent_id": 5,
  "agent_name": "Maria Santos",
  "created_at": "2026-02-10T09:15:00Z",
  "updated_at": "2026-03-15T16:45:00Z"
}
```

Ver schemas completos no Swagger UI.

---

## ⚡ Rate Limiting

Para proteger a API contra abuso:

```
Limite: 100 requisições por minuto por IP
Limite Autenticado: 1000 requisições por minuto por usuário
```

**Headers de resposta:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1679933400
```

Quando o limite é excedido:
```
HTTP 429 Too Many Requests
{
  "error": "Rate limit exceeded. Try again in 42 seconds."
}
```

---

## 🔍 Paginação

Endpoints de listagem suportam paginação:

```bash
GET /api/v1/users?page=1&limit=50
```

**Parâmetros:**
- `page` - Número da página (default: 1)
- `limit` - Itens por página (default: 50, max: 100)

**Resposta:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "items": [...],
    "total": 234,
    "page": 1,
    "pages": 5,
    "limit": 50
  }
}
```

---

## 🔎 Filtros e Busca

Use query parameters para filtrar:

```bash
# Buscar usuários ativos
GET /api/v1/users?active=true

# Buscar propriedades por tipo
GET /api/v1/properties?property_type=apartment

# Buscar propriedades por cidade e preço
GET /api/v1/properties?city=São Paulo&price_min=400000&price_max=600000

# Buscar por texto (full-text search)
GET /api/v1/properties?search=vila mariana
```

---

## 🚨 Tratamento de Erros

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 201 | Criado |
| 400 | Bad Request (dados inválidos) |
| 401 | Não autenticado |
| 403 | Não autorizado (sem permissão) |
| 404 | Não encontrado |
| 409 | Conflito (ex: email duplicado) |
| 422 | Validação falhou |
| 429 | Rate limit excedido |
| 500 | Erro interno do servidor |

### Formato de Erro

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": 400,
    "message": "Validation error",
    "data": {
      "email": ["Email já está em uso"],
      "cpf": ["CPF inválido"]
    }
  }
}
```

---

## 📚 Recursos Adicionais

### Postman Collection
Importe a collection oficial:
- [Postman Collection](../postman/) - Collection completa com exemplos

### Insomnia Workspace
- Importe o `openapi.json` diretamente no Insomnia

### Geradores de Client
Use `openapi-generator` para gerar clients automáticos:

```bash
# Python client
openapi-generator generate -i openapi.json -g python -o ./client-python

# TypeScript client
openapi-generator generate -i openapi.json -g typescript-axios -o ./client-ts

# Java client
openapi-generator generate -i openapi.json -g java -o ./client-java
```

---

## 📚 Próximos Passos

- [Capítulo 2: Componentes Docker](02-docker-components.md) - Entenda a stack
- [Capítulo 5: Deployment](05-deployment.md) - Deploy em produção
- [Voltar ao Índice](00-index.md)

---

*Última atualização: 27 de março de 2026*
