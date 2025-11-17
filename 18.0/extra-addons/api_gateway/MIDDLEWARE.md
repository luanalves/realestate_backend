# JWT Middleware - API Gateway

Middleware para autenticação JWT em endpoints REST do Odoo.

## 🎯 Funcionalidades

### 1. Decorator `@require_jwt`
Protege endpoints com autenticação JWT.

**Uso:**
```python
from odoo import http
from odoo.http import request
from ..middleware import require_jwt

@http.route('/api/v1/protected', auth='none', methods=['GET'], csrf=False)
@require_jwt
def protected_endpoint(self, **kwargs):
    # Acesso autenticado!
    # Aplicação disponível em: request.jwt_application
    # Token disponível em: request.jwt_token
    return request.make_json_response({
        'message': 'Success',
        'app': request.jwt_application.name
    })
```

**Validações:**
- ✅ Header Authorization presente
- ✅ Formato "Bearer <token>"
- ✅ Token existe no banco
- ✅ Token não expirado
- ✅ Token não revogado

**Respostas de Erro:**
- `401 unauthorized` - Header ausente
- `401 invalid_token` - Token inválido ou formato incorreto
- `401 token_expired` - Token expirado
- `401 token_revoked` - Token revogado

---

### 2. Decorator `@require_jwt_with_scope`
Protege endpoints com JWT + validação de scopes.

**Uso:**
```python
from ..middleware import require_jwt_with_scope

@http.route('/api/v1/admin', auth='none', methods=['GET'], csrf=False)
@require_jwt_with_scope('admin', 'write')
def admin_endpoint(self, **kwargs):
    # Requer scopes 'admin' E 'write'
    return request.make_json_response({'message': 'Admin access'})
```

**Validações:**
- ✅ Todas as validações do `@require_jwt`
- ✅ Token possui TODOS os scopes requeridos

**Respostas de Erro:**
- Todas as respostas do `@require_jwt`, mais:
- `403 insufficient_scope` - Token não possui scopes necessários

---

### 3. Função `log_api_access()`
Registra estatísticas de acesso aos endpoints.

**Uso:**
```python
from ..middleware import log_api_access

@http.route('/api/v1/properties', auth='none', methods=['GET'], csrf=False)
@require_jwt
def list_properties(self, **kwargs):
    log_api_access('/api/v1/properties', 'GET', 200)
    # ... lógica do endpoint
```

**Funcionalidade:**
- Incrementa contador de chamadas no `api.endpoint`
- Atualiza timestamp da última chamada
- (Futuro) Cria registro em `api.access.log`

---

### 4. Decorator `@validate_json_schema`
Valida JSON do request contra um schema.

**Uso:**
```python
from ..middleware import validate_json_schema

@http.route('/api/v1/properties', auth='none', methods=['POST'], csrf=False)
@require_jwt
@validate_json_schema({
    'type': 'object',
    'required': ['name', 'price'],
    'properties': {
        'name': {'type': 'string'},
        'price': {'type': 'number', 'minimum': 0}
    }
})
def create_property(self, **kwargs):
    data = request.jsonrequest  # Já validado!
    # ... criar propriedade
```

**Validações:**
- ✅ Request body é JSON válido
- ✅ JSON conforme schema (futuro - implementar com cerberus/jsonschema)

**Respostas de Erro:**
- `400 invalid_request` - Body não é JSON
- `400 validation_error` - JSON não conforme schema

---

## 📝 Endpoints de Teste

O módulo inclui endpoints de teste para validar o middleware:

### 1. **Endpoint Público**
```bash
curl http://localhost:8069/api/v1/test/public
```

**Resposta:**
```json
{
  "message": "This is a public endpoint",
  "protected": false
}
```

---

### 2. **Endpoint Protegido**
```bash
# Obter token primeiro
TOKEN=$(curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=XXX&client_secret=YYY" \
  | jq -r '.access_token')

# Acessar endpoint protegido
curl http://localhost:8069/api/v1/test/protected \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta:**
```json
{
  "message": "You are authenticated!",
  "protected": true,
  "application": "My Application",
  "client_id": "abc123",
  "token_expires_at": "2025-11-15T16:00:00"
}
```

---

### 3. **Endpoint com Scopes**
```bash
curl http://localhost:8069/api/v1/test/scoped \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta (sucesso):**
```json
{
  "message": "You have admin and write scopes!",
  "protected": true,
  "scopes": ["admin", "write", "read"]
}
```

**Resposta (erro):**
```json
{
  "error": "insufficient_scope",
  "error_description": "Missing required scopes: admin, write"
}
```

---

### 4. **Endpoint Echo**
```bash
curl -X POST http://localhost:8069/api/v1/test/echo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "value": 123}'
```

**Resposta:**
```json
{
  "message": "Echo endpoint",
  "received": {
    "name": "Test",
    "value": 123
  },
  "application": "My Application"
}
```

---

## 🔒 Variáveis de Request

Após autenticação bem-sucedida, o middleware adiciona ao `request`:

- **`request.jwt_token`** - Registro do model `oauth.token`
- **`request.jwt_application`** - Registro do model `oauth.application`

**Exemplo de uso:**
```python
@require_jwt
def my_endpoint(self, **kwargs):
    # Acessar informações do token
    token = request.jwt_token
    app = request.jwt_application
    
    print(f"App: {app.name}")
    print(f"Client ID: {app.client_id}")
    print(f"Token expira em: {token.expires_at}")
    print(f"Scopes: {token.scope}")
```

---

## 📊 Registro de Endpoints

Outros módulos devem registrar seus endpoints no `api.endpoint`:

```python
# Em um método _post_init_hook() ou no create do módulo
self.env['api.endpoint'].register_endpoint({
    'name': 'List Properties',
    'path': '/api/v1/properties',
    'method': 'GET',
    'module_name': 'quicksol_estate',
    'description': 'Get list of all properties with filters',
    'summary': 'List all properties',
    'tags': 'Properties,Real Estate',
    'protected': True,
})
```

**Benefícios:**
- Documentação centralizada
- Estatísticas de uso (call_count, last_called)
- Base para Swagger/OpenAPI
- Controle de acesso centralizado

---

## 🎓 Boas Práticas

1. **Sempre use `auth='none'`** nos routes protegidos por JWT
2. **Use `csrf=False`** para APIs REST
3. **Chame `log_api_access()`** para estatísticas
4. **Registre endpoints** no `api.endpoint` para documentação
5. **Use scopes** para controle de acesso granular
6. **Retorne JSON padronizado** com `request.make_json_response()`

---

## 🚀 Próximos Passos

- [ ] Implementar validação de JSON Schema (cerberus/jsonschema)
- [ ] Criar model `api.access.log` para auditoria completa
- [ ] Implementar rate limiting por aplicação
- [ ] Gerar Swagger/OpenAPI automaticamente do registry
- [ ] Suporte a OAuth 2.0 Authorization Code Grant
- [ ] Webhook para notificar revogação de tokens

---

**Versão:** 1.0.0  
**Última Atualização:** 15/11/2025
