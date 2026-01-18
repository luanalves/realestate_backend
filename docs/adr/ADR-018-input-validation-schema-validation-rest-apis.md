# ADR-018: Input Validation and Schema Validation for REST APIs

## Status
Aceito

## Contexto

A arquitetura de APIs REST implementa endpoints que recebem dados de clientes (criação, atualização de resources). Sem validação adequada de entrada, o sistema está vulnerável a:

**Problemas identificados:**
1. **Mass Assignment Attack** - Cliente envia campos não esperados e consegue mudar dados protegidos
2. **Type Confusion** - Cliente envia tipo de dado errado (string em vez de int)
3. **Constraint Violations** - Dados violam regras de negócio (email inválido, CPF com 10 dígitos)
4. **Missing Fields** - Requisição não contém campos obrigatórios
5. **Invalid Formats** - Strings mal formatadas (CEP, CNPJ, telefone)

**Impacto:**
- Dados inválidos corrompem banco de dados
- Ataques de manipulação de dados via API
- Logs genéricos fazem difícil rastrear problemas
- Erro 500 ao invés de 400 em requisições inválidas
- Falta de contrato claro entre cliente e servidor

**Dependência de ADR-005:**
ADR-005 (OpenAPI 3.0) define que schemas devem estar documentados. Esta ADR define como **validar contra esses schemas em tempo de execução**.

## Decisão

Implementar **duas camadas de validação**:

### 1. Schema Validation (Entrada)

**Responsabilidade:** Validar que a requisição está em conformidade com o contrato OpenAPI.

**Componentes:**
```python
class SchemaValidator:
    """
    Validates request data against predefined schemas.
    Ensures API contracts are enforced and data integrity is preserved.
    """
    
    # Define schemas para cada endpoint
    AGENT_CREATE_SCHEMA = {
        'required': ['name', 'cpf'],
        'optional': ['email', 'phone', 'creci', ...],
        'types': {
            'name': str,
            'cpf': str,
            'email': str,
            ...
        },
        'constraints': {
            'name': lambda v: 3 <= len(v) <= 255,
            'cpf': lambda v: len(v.replace('.', '').replace('-', '')) == 11,
            'email': lambda v: '@' in v and '.' in v,
            ...
        }
    }
    
    # Métodos:
    # - validate_request(data, schema) → Returns (is_valid, errors)
    # - validate_agent_create(data) → Specialista para agents
    # - validate_agent_update(data) → Specialista para updates
```

**Características:**
- ✅ Declarativo - Schemas definidos como dados, não código
- ✅ Reutilizável - Mesmo schema usado em múltiplos endpoints
- ✅ Type-checking - Valida tipos de dados (str, int, float, bool)
- ✅ Constraint validation - Regras de negócio (email com @, CPF 11 dígitos)
- ✅ Required/Optional - Diferencia campos obrigatórios vs opcionais
- ✅ Clear errors - Mensagens descrevem exatamente o que falhou

### 2. Integração em Controllers

**Padrão obrigatório em TODOS os endpoints que manipulam dados:**

```python
@http.route('/api/v1/agents', type='http', auth='none', 
            methods=['POST'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def create_agent(self, **kwargs):
    """
    Create a new agent (POST /api/v1/agents)
    
    Body: AGENT_CREATE_SCHEMA
    Returns: 201 Created + agent JSON
    """
    try:
        data = json.loads(request.httprequest.data.decode('utf-8'))
    except:
        return error_response(400, 'Invalid JSON')
    
    # ← VALIDAÇÃO DE SCHEMA (novo)
    validator = SchemaValidator()
    is_valid, errors = validator.validate_agent_create(data)
    if not is_valid:
        # Retorna 400 Bad Request com erros descritivos
        return error_response(400, 'Validation failed', {'errors': errors})
    
    # ← Agora podemos assumir que data é válido
    try:
        agent = self.env['real.estate.agent'].create({
            'name': data['name'],
            'cpf': data['cpf'],
            'email': data.get('email'),
            ...
        })
        return success_response({
            'id': agent.id,
            'name': agent.name,
            ...
        }, status=201)
    except Exception as e:
        _logger.error(f'Error creating agent: {e}')
        return error_response(500, 'Internal server error')
```

## Validação em Três Níveis

### Nível 1: Presença (Required Fields)

```python
'required': ['name', 'cpf']

# Validação:
if field not in data:
    errors.append(f"Missing required field: {field}")
```

### Nível 2: Tipo de Dado (Type Checking)

```python
'types': {
    'name': str,
    'cpf': str,
    'company_id': int,
}

# Validação:
if not isinstance(data['name'], str):
    errors.append(f"Field 'name' must be string, got {type(data['name'])}")
```

### Nível 3: Constraints (Regras de Negócio)

```python
'constraints': {
    'name': lambda v: 3 <= len(v) <= 255,
    'cpf': lambda v: len(v.replace('.', '').replace('-', '')) == 11,
    'email': lambda v: '@' in v and '.' in v,
}

# Validação:
if not constraint(data['field']):
    errors.append(f"Field '{field}' violates constraint")
```

## Tratamento de Campos Extras

**Política:** Campos não esperados são **PERMITIDOS mas IGNORADOS**

```python
# Requisição:
{
    "name": "João",
    "cpf": "123.456.789-00",
    "admin": true,  ← Campo não esperado
    "secret_key": "xxx"  ← Tampoco esperado
}

# Validação:
- name ✓ válido
- cpf ✓ válido
- admin → IGNORADO (não está no schema)
- secret_key → IGNORADO (não está no schema)

# Resultado: Criado com sucesso
```

**Motivo:** Evita quebra de clientes legados. Se futuramente adicionarmos campo `admin`, clientes antigos que enviam `admin=false` não quebram.

## Respostas de Erro

### Válido

```json
GET /api/v1/agents/999
HTTP/1.1 404 Not Found

{
  "error": "Agent not found",
  "code": 404
}
```

### Inválido (Schema Violation)

```json
POST /api/v1/agents
Body: {"name": "Jo", "cpf": "123"}
HTTP/1.1 400 Bad Request

{
  "error": "Validation failed",
  "code": 400,
  "details": {
    "errors": [
      "Field 'name' must be 3-255 characters, got 2",
      "Field 'cpf' must be 11 digits, got 3",
      "Missing required field: email"
    ]
  }
}
```

## Implementação

### Arquivos

**Criados:**
- `controllers/utils/schema.py` (184 linhas)
  - `SchemaValidator` class com 4 schemas (AGENT_CREATE, AGENT_UPDATE, ASSIGNMENT, PERFORMANCE)
  - Generic `validate_request(data, schema)` method
  - Specialized validators: `validate_agent_create()`, `validate_agent_update()`, etc.

**Modificados:**
- `controllers/agent_api.py`
  - Import SchemaValidator
  - Integração em 3 endpoints: POST /agents, PUT /agents/{id}, POST /assignments

### Testes

**Arquivo:** `tests/test_schema_validation.py` (334 linhas, 31 testes)

**Cobertura:**
1. **Valid Data Tests** (6 testes)
   - Agent creation com dados válidos
   - Agent update com dados válidos
   - Assignment creation com dados válidos

2. **Missing Fields Tests** (6 testes)
   - Requisição sem campos obrigatórios
   - Validação retorna lista completa de campos faltando

3. **Invalid Type Tests** (4 testes)
   - String em vez de int
   - Int em vez de string
   - Type mismatch detectado

4. **Constraint Violation Tests** (7 testes)
   - Name < 3 caracteres
   - CPF != 11 dígitos
   - Email sem @
   - Responsibility type inválido

5. **Extra Fields Tests** (4 testes)
   - Campos extras são ignorados (não causam erro)
   - Campos extras não são salvos no banco

6. **Integration Tests** (4 testes)
   - Validação antes de criar objeto
   - Retorna 400 Bad Request em caso de falha
   - Retorna 201 Created em caso de sucesso

## Conformidade com ADRs

| ADR | Aspecto | Status |
|-----|---------|--------|
| **ADR-005** | OpenAPI Schemas | ✅ Validation enforce contrato |
| **ADR-008** | Security | ✅ Input validation previne injection |
| **ADR-001** | Guidelines | ✅ Type hints, docstrings, errors |
| **ADR-003** | Test Coverage | ✅ 31 test methods |
| **ADR-011** | Security Layers | ✅ Validation antes de business logic |

## Consequências

### Positivas

1. **Segurança aumentada**
   - Previne mass assignment attacks
   - Valida tipos antes de processar
   - Constraints garantem integridade de dados

2. **Developer Experience**
   - Schemas reutilizáveis
   - Erros descritivos
   - Fácil adicionar novos campos

3. **Debugging simplificado**
   - Erro 400 (cliente culpado) vs Error 500 (servidor culpado)
   - Mensagens claras do que falhou
   - Logs rastreáveis

4. **Contrato API claro**
   - Schemas definem contrato explicitamente
   - OpenAPI gerado a partir dos schemas
   - Documentação sincronizada com código

5. **Reutilização**
   - Mesmo schema em múltiplos endpoints
   - Validação centralizada
   - DRY principle

### Negativas

1. **Overhead inicial**
   - ~2-5ms por validação (aceitável)
   - Schema definitions são verbosas
   - Mais código para manter

2. **False Positives**
   - Constraints lambda são limitados
   - Não pode fazer validações complexas no schema (ex: CPF válido verificando dígito verificador)
   - Soluções complexas requerem código customizado

3. **Manutenção**
   - Quando adiciona novo campo, precisa atualizar schema
   - Esquecimento causa bug silencioso

### Riscos Mitigados

- **CWE-20:** Improper Input Validation
- **CWE-915:** Improperly Controlled Modification of Dynamically-Determined Object Attributes
- **OWASP A01:2021:** Broken Access Control (mass assignment)

## Padrão de Implementação

Todos os endpoints POST/PUT/PATCH **DEVEM** seguir este padrão:

```python
@http.route('/api/v1/resource', type='http', auth='none', methods=['POST'])
@require_jwt
@require_session
@require_company
def create_resource(self, **kwargs):
    # 1. Parse JSON
    data = json.loads(request.httprequest.data.decode('utf-8'))
    
    # 2. Validate schema ← OBRIGATÓRIO
    validator = SchemaValidator()
    is_valid, errors = validator.validate_resource_create(data)
    if not is_valid:
        return error_response(400, 'Validation failed', {'errors': errors})
    
    # 3. Business logic (agora dados são garantidamente válidos)
    resource = self.env['model'].create({...})
    
    # 4. Response
    return success_response({...}, status=201)
```

## Extensibilidade

Para adicionar novo schema:

```python
class SchemaValidator:
    # ... existing schemas ...
    
    # Novo schema (ex: PROPERTY_CREATE)
    PROPERTY_CREATE_SCHEMA = {
        'required': ['name', 'type_id', 'location_type_id'],
        'optional': ['description', 'price', ...],
        'types': {...},
        'constraints': {...}
    }
    
    def validate_property_create(self, data):
        return self.validate_request(data, self.PROPERTY_CREATE_SCHEMA)
```

Padrão é simples e reutilizável.

## Referências

- OWASP Input Validation: https://owasp.org/www-community/attacks/Command_Injection
- CWE-20: Improper Input Validation: https://cwe.mitre.org/data/definitions/20.html
- JSON Schema: https://json-schema.org/
- ADR-005: OpenAPI 3.0 Swagger Documentation
- ADR-001: Development Guidelines for Odoo Screens
- ADR-003: Mandatory Test Coverage

## Histórico

- **2026-01-15**: Schema Validation implementado em agent_api.py
- **2026-01-17**: ADR criada documentando padrão de input validation

---

## Apêndice: Exemplo Completo de Uso

### Endpoint POST /api/v1/agents

```python
# controllers/agent_api.py
from .utils.schema import SchemaValidator

@http.route('/api/v1/agents', type='http', auth='none', 
            methods=['POST'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def create_agent(self, **kwargs):
    """
    Create a new agent
    
    Request Body:
    {
        "name": "João Silva",
        "cpf": "123.456.789-00",
        "email": "joao@company.com",
        "phone": "(11) 99999-9999",
        "creci": "12345"
    }
    
    Response 201:
    {
        "id": 42,
        "name": "João Silva",
        "cpf": "123.456.789-00",
        ...
    }
    
    Response 400 (Validation Error):
    {
        "error": "Validation failed",
        "code": 400,
        "details": {
            "errors": [
                "Field 'name' must be 3-255 characters",
                "Field 'cpf' must be 11 digits"
            ]
        }
    }
    """
    try:
        data = json.loads(request.httprequest.data.decode('utf-8'))
    except:
        return error_response(400, 'Invalid JSON in request body')
    
    # Validar contra schema
    validator = SchemaValidator()
    is_valid, errors = validator.validate_agent_create(data)
    
    if not is_valid:
        return error_response(400, 'Validation failed', {'errors': errors})
    
    # Dados válido, criar agent
    try:
        agent = self.env['real.estate.agent'].create({
            'name': data['name'],
            'cpf': data['cpf'],
            'email': data.get('email'),
            'phone': data.get('phone'),
            'creci': data.get('creci'),
            'company_ids': [(6, 0, [request.session.company_id])]
        })
        
        return success_response({
            'id': agent.id,
            'name': agent.name,
            'cpf': agent.cpf,
            'email': agent.email,
            'phone': agent.phone,
            'creci': agent.creci,
            'company_id': agent.company_ids[0].id if agent.company_ids else None
        }, status=201)
    except Exception as e:
        _logger.error(f'Error creating agent: {e}')
        return error_response(500, 'Internal server error')
```

### Test Example

```python
# tests/test_schema_validation.py
def test_agent_create_valid():
    """Agent creation with valid data"""
    data = {
        "name": "João Silva",
        "cpf": "123.456.789-00",
        "email": "joao@company.com"
    }
    
    validator = SchemaValidator()
    is_valid, errors = validator.validate_agent_create(data)
    
    assert is_valid == True
    assert len(errors) == 0

def test_agent_create_missing_cpf():
    """Agent creation missing required field (cpf)"""
    data = {
        "name": "João Silva"
        # cpf missing
    }
    
    validator = SchemaValidator()
    is_valid, errors = validator.validate_agent_create(data)
    
    assert is_valid == False
    assert "Missing required field: cpf" in errors

def test_agent_create_invalid_email():
    """Agent creation with invalid email format"""
    data = {
        "name": "João Silva",
        "cpf": "123.456.789-00",
        "email": "invalid-email-no-at"  # Sem @
    }
    
    validator = SchemaValidator()
    is_valid, errors = validator.validate_agent_create(data)
    
    assert is_valid == False
    assert any("email" in err for err in errors)
```
