---
applyTo: "18.0/extra-addons/**/controllers/**/*.py"
---

# Controllers - Regras de Segurança

⚠️ **Documentação completa**: [ADR-011: Controller Security & Authentication](../../docs/adr/ADR-011-controller-security-authentication-storage.md)

## Regras Obrigatórias

### 1. Endpoints Protegidos (APIs REST)

SEMPRE use os três decoradores em todos os endpoints de API:

```python
from odoo.addons.thedevkitchen_apigateway.decorators import require_jwt, require_session, require_company

@http.route('/api/v1/endpoint', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt       # Valida token OAuth (aplicação autorizada)
@require_session   # Valida session_id (usuário autenticado + contexto)
@require_company   # Valida company_id (isolamento multi-tenancy)
def endpoint(self, **kwargs):
    # Contexto disponível via request.session.uid e request.session.context
    pass
```

**Por que os três?**
- `@require_jwt` → Autentica a **aplicação** (token OAuth no header `Authorization`)
- `@require_session` → Autentica o **usuário** (cookie `session_id` + contexto do Redis)
- `@require_company` → Garante **isolamento** entre empresas (header `X-Company-ID`)

NÃO são redundantes. JWT ≠ Session ≠ Company validation.

### 2. Endpoints Públicos (Exceção)

Se o endpoint não requer autenticação, marque explicitamente:

```python
@http.route('/api/v1/health', type='http', auth='none', methods=['GET'])
# public endpoint - health check sem autenticação
def health_check(self, **kwargs):
    return Response(json.dumps({'status': 'ok'}))
```

## ✅ Aceitável

```python
# Endpoint protegido completo
@http.route('/api/v1/properties', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def list_properties(self, **kwargs):
    return Response(json.dumps({'data': []}))
```

```python
# Endpoint público marcado
@http.route('/api/v1/status', type='http', auth='none', methods=['GET'])
# public endpoint
def status(self, **kwargs):
    return Response(json.dumps({'status': 'ok'}))
```

## ❌ NÃO Aceitável

```python
# ERRO: Falta @require_session
@http.route('/api/v1/properties', type='http', auth='none')
@require_jwt  # ❌ Incompleto
def list_properties(self, **kwargs):
    pass
```

```python
# ERRO: Falta @require_jwt
@http.route('/api/v1/properties', type='http', auth='none')
@require_session  # ❌ Incompleto
def list_properties(self, **kwargs):
    pass
```

```python
# ERRO: Falta @require_company
@http.route('/api/v1/properties', type='http', auth='none')
@require_jwt
@require_session  # ❌ Sem isolamento multi-tenancy
def list_properties(self, **kwargs):
    pass
```

```python
# ERRO: Endpoint sem decorators e sem marcação "public endpoint"
@http.route('/api/v1/data', type='http', auth='none')
def get_data(self, **kwargs):  # ❌ Ambíguo
    pass
```

## Arquitetura de Armazenamento

- **PostgreSQL** (`realestate`): Tokens OAuth, usuários, empresas, dados de negócio
- **Redis** (DB 1): Sessões HTTP (`session:<id>`), cache ORM, message bus

Consulte a [ADR-011](../../docs/adr/ADR-011-controller-security-authentication-storage.md) para:
- Fluxo completo de autenticação OAuth 2.0 (JWT)
- Fluxo de criação e validação de sessão HTTP
- Estrutura de dados no PostgreSQL e Redis
- Comandos de monitoramento e debugging
- Checklist completo de revisão de código
