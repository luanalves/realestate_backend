# Fase 1: Isolamento por Empresa (Company Isolation) - Baby Steps

**Objetivo:** Implementar isolamento completo de dados por empresa (imobiliária), garantindo que usuários apenas vejam e manipulem dados das empresas às quais estão vinculados.

**Pré-requisitos:** 
- ✅ Fase 0 completa (Login/Logout com sessões + decorator @require_session)
- ✅ Modelo `thedevkitchen.estate.company` existente
- ✅ Relacionamentos many2many entre Company e entidades já criados
- ✅ Campos `estate_company_ids` e `estate_default_company_id` em `res.users`

**Tempo estimado:** 12-16 horas (desenvolvedor junior)

---

## 🔄 Progresso Recente (09/01/2026)

### ⚠️ STATUS REAL DA FASE 1: PARCIALMENTE IMPLEMENTADA

**Importante:** A infraestrutura de isolamento está implementada, mas as funcionalidades de negócio ainda precisam ser desenvolvidas.

#### ✅ O QUE ESTÁ IMPLEMENTADO (Infraestrutura)

**1. Decorator @require_company** ✅
- **Arquivo:** `thedevkitchen_apigateway/middleware.py`
- **Funcionalidade:** Filtra automaticamente queries por `user.estate_company_ids`
- **Status:** Implementado e funcional

**2. Serviço de Validação de Empresas** ✅
- **Arquivo:** `quicksol_estate/services/company_validator.py`
- **Métodos:** `validate_company_ids()`, `get_default_company_id()`, `ensure_company_ids()`
- **Status:** Implementado e funcional

**3. Endpoints Protegidos LIMITADOS** ⚠️
- **Master Data (8 endpoints):** ✅ COMPLETO
  - `/api/v1/property-types` ✅
  - `/api/v1/location-types` ✅
  - `/api/v1/states` ✅
  - `/api/v1/agents` ✅ (apenas listagem)
  - `/api/v1/owners` ✅ (apenas listagem)
  - `/api/v1/companies` ✅
  - `/api/v1/tags` ✅
  - `/api/v1/amenities` ✅

- **Properties (4 endpoints básicos):** ✅ COMPLETO
  - `POST /api/v1/properties` ✅ (criação básica)
  - `GET /api/v1/properties/<id>` ✅
  - `PUT /api/v1/properties/<id>` ✅
  - `DELETE /api/v1/properties/<id>` ✅

**4. Record Rules** ✅
- **Arquivo:** `quicksol_estate/security/record_rules.xml`
- **Regras ativas:** 5 (Property, Agent, Tenant, Lease, Sale)
- **Status:** Implementado para Web UI

#### ❌ O QUE AINDA FALTA IMPLEMENTAR (Funcionalidades de Negócio)

**1. Gestão Completa de Funcionários/Agentes** ❌
- [ ] CRUD completo de agentes vinculados à imobiliária
- [ ] Atribuição de agentes a imóveis
- [ ] Gestão de permissões por agente
- [ ] Relatórios de performance de agentes
- [ ] Comissionamento de agentes
- **Arquivo a criar:** `quicksol_estate/controllers/agent_api.py`

**2. Gestão de Contratos de Locação (Leases)** ❌
- [ ] CRUD de contratos de aluguel
- [ ] Vinculação contrato-imóvel-inquilino-imobiliária
- [ ] Controle de vencimentos e pagamentos
- [ ] Renovação de contratos
- [ ] Rescisão de contratos
- [ ] Histórico de locações
- **Arquivo a criar:** `quicksol_estate/controllers/lease_api.py`

**3. Gestão de Contratos de Venda (Sales)** ❌
- [ ] CRUD de contratos de venda
- [ ] Vinculação venda-imóvel-comprador-imobiliária
- [ ] Controle de propostas
- [ ] Etapas de venda (proposta, aceite, contrato, escritura)
- [ ] Histórico de vendas
- **Arquivo a criar:** `quicksol_estate/controllers/sale_api.py`

**4. Gestão Completa de Imóveis** ⚠️ PARCIAL
- [x] CRUD básico ✅
- [ ] Upload de fotos/documentos
- [ ] Publicação em portais
- [ ] Controle de chaves
- [ ] Histórico de visitas
- [ ] Relatórios de imóveis
- [ ] Integração com portais (Zap, VivaReal, etc)
- **Arquivo existente:** `quicksol_estate/controllers/property_api.py` (precisa expansão)

**5. Gestão de Inquilinos (Tenants)** ❌
- [ ] CRUD de inquilinos vinculados à imobiliária
- [ ] Histórico de locações por inquilino
- [ ] Análise de crédito
- [ ] Documentação de inquilinos
- **Arquivo a criar:** `quicksol_estate/controllers/tenant_api.py`

**6. Gestão de Proprietários (Owners)** ⚠️ PARCIAL
- [x] Listagem básica ✅
- [ ] CRUD completo de proprietários
- [ ] Vinculação proprietário-imóveis-imobiliária
- [ ] Histórico de transações
- [ ] Relatórios de repasse
- **Arquivo a expandir:** `quicksol_estate/controllers/master_data_api.py`

**7. Gestão Financeira** ❌
- [ ] Controle de recebimentos (aluguéis)
- [ ] Controle de repasses a proprietários
- [ ] Comissões de agentes
- [ ] Taxas de administração
- [ ] Relatórios financeiros
- **Arquivo a criar:** `quicksol_estate/controllers/financial_api.py`

**8. Relatórios e Dashboard** ❌
- [ ] Dashboard da imobiliária
- [ ] Relatórios de imóveis disponíveis
- [ ] Relatórios de contratos ativos
- [ ] Performance de agentes
- [ ] Indicadores financeiros
- **Arquivo a criar:** `quicksol_estate/controllers/reports_api.py`

**9. Notificações e Alertas** ❌
- [ ] Vencimento de contratos
- [ ] Pagamentos atrasados
- [ ] Renovações pendentes
- [ ] Alertas de manutenção
- **Arquivo a criar:** `quicksol_estate/controllers/notifications_api.py`

**10. Testes de Isolamento Completos** ⚠️ PARCIAL
- [x] Testes básicos de autenticação ✅
- [ ] Testes de isolamento para contratos
- [ ] Testes de isolamento para agentes
- [ ] Testes de isolamento para inquilinos
- [ ] Testes de isolamento financeiro
- **Arquivo existente:** `quicksol_estate/tests/api/test_company_isolation_api.py` (expandir)

### 📊 Resumo do Estado Atual

| Componente | Status | Progresso |
|------------|--------|-----------|
| **Infraestrutura de Isolamento** | ✅ Completo | 100% |
| **Autenticação e Sessões** | ✅ Completo | 100% |
| **Master Data APIs** | ✅ Completo | 100% |
| **Properties CRUD Básico** | ✅ Completo | 100% |
| **Record Rules** | ✅ Completo | 100% |
| **Gestão de Agentes** | ❌ Não iniciado | 0% |
| **Gestão de Contratos (Lease)** | ❌ Não iniciado | 0% |
| **Gestão de Vendas (Sales)** | ❌ Não iniciado | 0% |
| **Gestão de Inquilinos** | ❌ Não iniciado | 0% |
| **Gestão Financeira** | ❌ Não iniciado | 0% |
| **Relatórios/Dashboard** | ❌ Não iniciado | 0% |
| **Notificações** | ❌ Não iniciado | 0% |
| **Imóveis Completo** | ⚠️ Parcial | 30% |
| **Testes Completos** | ⚠️ Parcial | 25% |

**Progresso Geral da Fase 1:** ~35% (infraestrutura pronta, funcionalidades de negócio pendentes)

---

## 🔄 Progresso Histórico (12/12/2025)

### ✅ Implementado: Proteção de Sessão via JWT

**Contexto:** Implementação de token JWT assinado para proteger sessões contra sequestro (session hijacking).

**Arquivos modificados:**
- `models/ir_http.py` - Override de `session_info()` com geração/validação de token JWT
- `models/security_settings.py` - Configurações admin para fingerprint (IP/UA/Lang)
- `views/security_settings_views.xml` - Interface admin para configurações
- `security/ir.model.access.csv` - Permissões para modelo de configurações
- `tests/test_session_fingerprint.py` - Testes unitários JWT (7 cenários)
- `quicksol_estate/tests/api/test_user_login.py` - Test 7 atualizado (integração)
- `__manifest__.py` - Dependências atualizadas (partner_autocomplete)

**Comportamento:**
- Token JWT gerado no primeiro login (payload: uid, fingerprint{ip, ua, lang}, iat, exp=24h, iss)
- Token armazenado em `request.session['_security_token']`
- Validação a cada requisição: assinatura, exp, uid match, fingerprint components match
- Logout automático + log detalhado se validação falhar
- Configurável via Settings > Security (toggles IP/UA/Lang)

**Testes:**
- ✅ 7/7 testes de integração passando (`test_user_login.py`)
- ✅ Test 7 confirma bloqueio de sessão hijacking (headers diferentes = fingerprint mismatch)
- ✅ Testes unitários criados (geração, validação, expiração, componentes)

**Commits:**
- `4fbeaca` - security(session): implementar JWT para proteger sessões
- `7859ad4` - tests(session): adicionar testes unitários e ajustar integração
- `1f3b2fe` - chore(manifest): atualizar dependências e views
- `e664609` - docs(security): atualizar plano de segurança v3.0

**Próximos Passos:**
- Implementar decorator `@require_company` (Fase 1)
- Aplicar filtros de empresa em endpoints de API
- Criar testes de isolamento multi-tenant

---

## 📋 Checklist Geral

### Pré-requisitos (Fase 0)
- [x] **Autenticação de usuários** - Login/Logout via `/api/v1/users/login` ✅ COMPLETO
- [x] **Proteção de sessão JWT** - Token assinado com fingerprint (IP/UA/Lang) ✅ COMPLETO
- [x] **Testes de segurança** - Session hijacking bloqueado (7/7 testes passando) ✅ COMPLETO
- [x] **Middleware @require_session** - Validação de sessão em endpoints ✅ COMPLETO

### Implementação Fase 1 (Company Isolation)

#### Infraestrutura Básica
- [x] **Passo 1:** Criar decorator @require_company ✅ COMPLETO
- [x] **Passo 2:** Criar serviço de Validação de Empresas ✅ COMPLETO
- [x] **Passo 3:** Aplicar decorator em endpoints de Master Data ✅ COMPLETO
- [x] **Passo 4:** Aplicar decorator em endpoints de Properties (CRUD básico) ✅ COMPLETO
- [x] **Passo 5:** Validar criação de registros ✅ COMPLETO
- [x] **Passo 6:** Validar atualização de registros ✅ COMPLETO
- [x] **Passo 7:** Escrever testes de isolamento básicos ✅ COMPLETO
- [x] **Passo 8:** Ativar Record Rules (Odoo Web) ✅ COMPLETO

#### Funcionalidades de Negócio (PENDENTES)
- [ ] **Passo 9:** Implementar CRUD completo de Agentes/Funcionários ❌ NÃO INICIADO
- [ ] **Passo 10:** Implementar CRUD completo de Contratos de Locação ❌ NÃO INICIADO
- [ ] **Passo 11:** Implementar CRUD completo de Contratos de Venda ❌ NÃO INICIADO
- [ ] **Passo 12:** Implementar gestão completa de Imóveis (fotos, docs, chaves) ❌ NÃO INICIADO
- [ ] **Passo 13:** Implementar CRUD completo de Inquilinos ❌ NÃO INICIADO
- [ ] **Passo 14:** Implementar CRUD completo de Proprietários ❌ NÃO INICIADO
- [ ] **Passo 15:** Implementar gestão financeira (pagamentos, repasses) ❌ NÃO INICIADO
- [ ] **Passo 16:** Implementar relatórios e dashboard ❌ NÃO INICIADO
- [ ] **Passo 17:** Implementar sistema de notificações ❌ NÃO INICIADO
- [ ] **Passo 18:** Completar testes de isolamento para todas as entidades ❌ NÃO INICIADO
- [ ] **Passo 19:** Validar e documentar sistema completo ❌ NÃO INICIADO

---

## 🔑 Conceitos Importantes

### Multi-Tenancy vs Single-Tenant

**Single-Tenant (tradicional):**
- Cada cliente tem sua própria instância do sistema
- Banco de dados separado para cada cliente
- Mais custoso, mais complexo de manter

**Multi-Tenancy (nosso caso):**
- Todos os clientes no mesmo sistema
- Mesmo banco de dados, dados isolados por empresa (`company_id`)
- Mais eficiente, mais escalável
- Requer isolamento rigoroso de dados

### Arquitetura de Segurança em Camadas

**Defense in Depth:**
1. **Autenticação:** Verifica quem é o usuário (Fase 0 - @require_session)
2. **Autorização:** Verifica quais empresas o usuário pode acessar (Fase 1 - @require_company)
3. **Record Rules:** Filtra dados automaticamente no Odoo Web (Fase 1)
4. **Validação:** Garante que registros criados/editados pertencem às empresas corretas (Fase 1)

### Fluxo de Autenticação + Autorização

```
1. Login:
   POST /api/v1/users/login {email, password}
   → Valida credenciais
   → Cria sessão Odoo
   → Retorna session_id + empresas do usuário
   
2. Requisição à API:
   GET /api/v1/properties
   Headers: X-Openerp-Session-Id: <hash>
   
   → @require_session valida session_id e injeta user
   → @require_company filtra por user.estate_company_ids
   → Retorna apenas propriedades das empresas do usuário
```

### Validação de Acesso

**Regra de Ouro:** Usuário só pode acessar dados das empresas em `user.estate_company_ids`

**Casos de Uso:**
- User A tem acesso a [Company 1, Company 2]
- User B tem acesso a [Company 3]
- Property X pertence a Company 1
- Property Y pertence a Company 3

**Resultados:**
- User A pode ler/editar Property X ✅
- User A NÃO pode ler/editar Property Y ❌
- User B pode ler/editar Property Y ✅
- User B NÃO pode ler/editar Property X ❌

---

## Passo 1: Criar decorator @require_company

### 📝 O que fazer

Criar decorator que filtra automaticamente queries por `user.estate_company_ids`.

### 📂 Arquivo

`18.0/extra-addons/thedevkitchen_apigateway/middleware.py`

Adicionar após o decorator `@require_session`:

### 🔨 Implementação

```python
def require_company(func):
    """
    Decorator para injetar filtro de empresa automaticamente.
    
    IMPORTANTE: Deve ser usado APÓS @require_session
    
    Uso:
        @http.route('/api/v1/properties', auth='none', csrf=False, cors='*')
        @require_jwt
        @require_session
        @require_company
        def list_properties(self):
            # company_domain já injetado no request
            properties = request.env['real.estate.property'].search(request.company_domain)
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = request.env.user
        
        # System admin vê tudo
        if user.has_group('base.group_system'):
            request.company_domain = []
            return func(*args, **kwargs)
        
        # Valida que usuário tem empresas
        if not user.estate_company_ids:
            _logger.warning(f'User {user.login} has no companies')
            return {
                'error': {
                    'status': 403,
                    'message': 'User has no company access'
                }
            }
        
        # Injeta domain de filtro por empresas
        request.company_domain = [('company_ids', 'in', user.estate_company_ids.ids)]
        request.user_company_ids = user.estate_company_ids.ids
        
        return func(*args, **kwargs)
    
    return wrapper
```

### 📖 Conceitos

- **Decorator:** Adiciona lógica de filtro automaticamente antes da função
- **request.company_domain:** Lista de tuplas que o Odoo usa para filtrar (`[('company_ids', 'in', [1, 2, 3])]`)
- **request.user_company_ids:** IDs das empresas do usuário (para validações adicionais)
- **Decorator Stacking:** Múltiplos decorators são executados de baixo para cima

### 🎯 Critério de aceite

- [x] Decorator criado em middleware.py
- [x] Injeta `request.company_domain` corretamente
- [x] Injeta `request.user_company_ids` corretamente
- [x] System admin (base.group_system) não tem restrições
- [x] Usuários sem empresas recebem erro 403

---

## Passo 2: Criar serviço de Validação de Empresas

### 📝 O que fazer

Criar serviço para validar que registros criados/editados pertencem às empresas autorizadas.

### 📂 Arquivo (CRIAR NOVO)

`18.0/extra-addons/quicksol_estate/services/company_validator.py`

### 🔨 Implementação

```python
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CompanyValidator:
    """
    Serviço para validar acesso a empresas em operações de API.
    Segue princípios de ADR-001 (orientação a objetos) e ADR-008 (segurança).
    """
    
    @staticmethod
    def validate_company_ids(company_ids):
        """
        Valida que as empresas informadas estão nas empresas do usuário.
        
        Args:
            company_ids (list): Lista de IDs de empresas a validar
            
        Returns:
            tuple: (valid: bool, error_message: str or None)
            
        Exemplo:
            valid, error = CompanyValidator.validate_company_ids([1, 2])
            if not valid:
                return {'error': {'status': 403, 'message': error}}
        """
        user = request.env.user
        
        # System admin pode tudo
        if user.has_group('base.group_system'):
            return True, None
        
        if not company_ids:
            return False, 'At least one company must be specified'
        
        # Converte para set para facilitar comparação
        user_company_ids = set(user.estate_company_ids.ids)
        requested_ids = set(company_ids)
        
        # Verifica se todas as empresas solicitadas estão autorizadas
        unauthorized = requested_ids - user_company_ids
        
        if unauthorized:
            _logger.warning(
                f'User {user.login} (id={user.id}) attempted to access '
                f'unauthorized companies: {list(unauthorized)}. '
                f'Allowed: {list(user_company_ids)}'
            )
            return False, f'Access denied to companies: {list(unauthorized)}'
        
        return True, None
    
    @staticmethod
    def get_default_company_id():
        """
        Retorna ID da empresa padrão do usuário.
        
        Returns:
            int: ID da empresa padrão, ou ID da primeira empresa, ou None
        """
        user = request.env.user
        
        if user.estate_default_company_id:
            return user.estate_default_company_id.id
        
        if user.estate_company_ids:
            return user.estate_company_ids[0].id
        
        return None
    
    @staticmethod
    def ensure_company_ids(data):
        """
        Garante que 'company_ids' está presente nos dados.
        Se não estiver, adiciona a empresa padrão.
        
        Args:
            data (dict): Dados do request (modificado in-place)
            
        Returns:
            dict: Dados com company_ids garantido
            
        Exemplo:
            data = {'name': 'Property 1', 'price': 100000}
            data = CompanyValidator.ensure_company_ids(data)
            # data agora tem: {'name': 'Property 1', 'price': 100000, 'company_ids': [1]}
        """
        if 'company_ids' not in data:
            default_id = CompanyValidator.get_default_company_id()
            if default_id:
                data['company_ids'] = [(6, 0, [default_id])]
        
        return data
```

### 📂 Atualizar `__init__.py`

`18.0/extra-addons/quicksol_estate/services/__init__.py`

```python
from . import company_validator
```

### 📖 Conceitos

- **Validation Service:** Centraliza lógica de validação (reusável)
- **Separation of Concerns:** Controller chama serviço, não contém lógica complexa
- **Odoo Many2many syntax:** `[(6, 0, [id1, id2])]` = "replace with these IDs"

### 🎯 Critério de aceite

- [x] Serviço criado em `services/company_validator.py`
- [x] Método `validate_company_ids()` funciona
- [x] Método `get_default_company_id()` funciona
- [x] Método `ensure_company_ids()` funciona
- [x] System admin não tem restrições
- [x] Logs de warning para acessos não autorizados

---

## Passo 3: Aplicar decorator em endpoints de Master Data

### 📝 O que fazer

Aplicar `@require_company` em todos os 8 endpoints de master data.

### 📂 Arquivo

`18.0/extra-addons/quicksol_estate/controllers/master_data_api.py`

### 🔨 Implementação

Atualizar imports no topo do arquivo:

```python
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt, require_session, require_company
import json
import logging

_logger = logging.getLogger(__name__)
```

**Aplicar decorator em todos os 8 endpoints:**

1. `/api/v1/property-types`
2. `/api/v1/location-types`
3. `/api/v1/states`
4. `/api/v1/agents`
5. `/api/v1/owners`
6. `/api/v1/companies`
7. `/api/v1/tags`
8. `/api/v1/amenities`

**Exemplo para property-types:**

```python
@http.route('/api/v1/property-types', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company  # <-- NOVO DECORATOR
def list_property_types(self, **kwargs):
    try:
        # ANTES: property_types = request.env['real.estate.property.type'].search([])
        # AGORA: Usa company_domain injetado pelo decorator
        domain = request.company_domain
        property_types = request.env['real.estate.property.type'].search(domain)
        
        result = [{
            'id': pt.id,
            'name': pt.name,
            'description': pt.description,
            'company_ids': pt.company_ids.ids,
        } for pt in property_types]
        
        return request.make_response(
            json.dumps({'data': result}),
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        _logger.exception('Error listing property types')
        return request.make_response(
            json.dumps({'error': 'Internal server error'}),
            status=500,
            headers={'Content-Type': 'application/json'}
        )
```

**IMPORTANTE:** Repetir padrão acima para TODOS os 8 endpoints!

### 📖 Conceitos

- **Decorator Order:** `@require_company` sempre APÓS `@require_jwt` e `@require_session`
- **request.company_domain:** Injetado automaticamente pelo decorator
- **Filtro transparente:** Controller não precisa saber sobre empresas, decorator cuida

### 🎯 Critério de aceite

- [x] 8 endpoints com `@require_company`
- [x] Imports atualizados corretamente
- [x] Todos usam `request.company_domain` no search
- [x] Response inclui `company_ids` em cada registro
- [x] Código compila sem erros

---

## Passo 4: Aplicar decorator em endpoints de Properties

### 📝 O que fazer

Aplicar `@require_company` nos 4 endpoints CRUD de Properties.

### 📂 Arquivo

`18.0/extra-addons/quicksol_estate/controllers/property_api.py`

### 🔨 Implementação

Atualizar imports:

```python
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt, require_session, require_company
from ..services.company_validator import CompanyValidator
import json
import logging

_logger = logging.getLogger(__name__)
```

**Aplicar nos 4 endpoints:**

**1. CREATE (POST /api/v1/properties):**

```python
@http.route('/api/v1/properties', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company  # <-- NOVO
def create_property(self, **kwargs):
    try:
        data = json.loads(request.httprequest.data)
        
        # Garantir que company_ids está presente (usa default se não tiver)
        data = CompanyValidator.ensure_company_ids(data)
        
        # Validar que as empresas estão autorizadas
        company_ids = [cmd[2] for cmd in data.get('company_ids', []) if cmd[0] == 6][0]
        valid, error = CompanyValidator.validate_company_ids(company_ids)
        if not valid:
            return request.make_response(
                json.dumps({'error': error}),
                status=403,
                headers={'Content-Type': 'application/json'}
            )
        
        # Criar registro
        property_record = request.env['real.estate.property'].create(data)
        
        return request.make_response(
            json.dumps({'id': property_record.id, 'message': 'Property created successfully'}),
            status=201,
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        _logger.exception('Error creating property')
        return request.make_response(
            json.dumps({'error': 'Internal server error'}),
            status=500,
            headers={'Content-Type': 'application/json'}
        )
```

**2. READ (GET /api/v1/properties/<id>):**

```python
@http.route('/api/v1/properties/<int:property_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company  # <-- NOVO
def get_property(self, property_id, **kwargs):
    try:
        # Buscar COM filtro de empresa
        domain = [('id', '=', property_id)] + request.company_domain
        property_record = request.env['real.estate.property'].search(domain, limit=1)
        
        if not property_record:
            # Retornar 404 genérico (não expor se existe mas não tem acesso)
            return request.make_response(
                json.dumps({'error': 'Property not found'}),
                status=404,
                headers={'Content-Type': 'application/json'}
            )
        
        result = {
            'id': property_record.id,
            'name': property_record.name,
            'price': property_record.price,
            'company_ids': property_record.company_ids.ids,
            # ... outros campos
        }
        
        return request.make_response(
            json.dumps({'data': result}),
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        _logger.exception(f'Error getting property {property_id}')
        return request.make_response(
            json.dumps({'error': 'Internal server error'}),
            status=500,
            headers={'Content-Type': 'application/json'}
        )
```

**3. UPDATE (PUT /api/v1/properties/<id>):**

```python
@http.route('/api/v1/properties/<int:property_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company  # <-- NOVO
def update_property(self, property_id, **kwargs):
    try:
        data = json.loads(request.httprequest.data)
        
        # IMPORTANTE: Bloquear alteração de company_ids via API
        if 'company_ids' in data:
            return request.make_response(
                json.dumps({'error': 'Cannot change company_ids via API'}),
                status=403,
                headers={'Content-Type': 'application/json'}
            )
        
        # Buscar COM filtro de empresa
        domain = [('id', '=', property_id)] + request.company_domain
        property_record = request.env['real.estate.property'].search(domain, limit=1)
        
        if not property_record:
            return request.make_response(
                json.dumps({'error': 'Property not found'}),
                status=404,
                headers={'Content-Type': 'application/json'}
            )
        
        # Atualizar
        property_record.write(data)
        
        return request.make_response(
            json.dumps({'message': 'Property updated successfully'}),
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        _logger.exception(f'Error updating property {property_id}')
        return request.make_response(
            json.dumps({'error': 'Internal server error'}),
            status=500,
            headers={'Content-Type': 'application/json'}
        )
```

**4. DELETE (DELETE /api/v1/properties/<id>):**

```python
@http.route('/api/v1/properties/<int:property_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company  # <-- NOVO
def delete_property(self, property_id, **kwargs):
    try:
        # Buscar COM filtro de empresa
        domain = [('id', '=', property_id)] + request.company_domain
        property_record = request.env['real.estate.property'].search(domain, limit=1)
        
        if not property_record:
            return request.make_response(
                json.dumps({'error': 'Property not found'}),
                status=404,
                headers={'Content-Type': 'application/json'}
            )
        
        # Deletar
        property_record.unlink()
        
        return request.make_response(
            json.dumps({'message': 'Property deleted successfully'}),
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        _logger.exception(f'Error deleting property {property_id}')
        return request.make_response(
            json.dumps({'error': 'Internal server error'}),
            status=500,
            headers={'Content-Type': 'application/json'}
        )
```

### 📖 Conceitos

- **Defense in Depth:** Validação em camadas (decorator + serviço + filtro)
- **404 genérico:** Não expor se registro existe mas usuário não tem acesso
- **Bloqueio de company_ids:** Prevenir mass assignment de empresas
- **Search antes de Write/Unlink:** Garantir que registro pertence às empresas do usuário

### 🎯 Critério de aceite

- [x] 4 endpoints com `@require_company`
- [x] CREATE valida company_ids
- [x] CREATE adiciona company padrão se não informado
- [x] READ filtra por empresa
- [x] UPDATE bloqueia alteração de company_ids
- [x] UPDATE filtra por empresa
- [x] DELETE filtra por empresa
- [x] Todos retornam 404 genérico para acessos negados

---

## Passo 5: Validar criação de registros

### 📝 O que fazer

Garantir que TODOS os registros criados via API recebem empresa corretamente.

### 📂 Arquivo

Todos os controllers que criam registros (`master_data_api.py`, `property_api.py`)

### 🔨 Checklist de Validação

Para CADA endpoint POST:

1. **Importar CompanyValidator:**
   ```python
   from ..services.company_validator import CompanyValidator
   ```

2. **Garantir company_ids:**
   ```python
   data = CompanyValidator.ensure_company_ids(data)
   ```

3. **Validar company_ids:**
   ```python
   company_ids = [cmd[2] for cmd in data.get('company_ids', []) if cmd[0] == 6][0]
   valid, error = CompanyValidator.validate_company_ids(company_ids)
   if not valid:
       return error_response(403, error)
   ```

4. **Criar registro:**
   ```python
   record = request.env['model.name'].create(data)
   ```

5. **Retornar com company_ids:**
   ```python
   return {'id': record.id, 'company_ids': record.company_ids.ids}
   ```

### 📖 Conceitos

- **Ensure company_ids:** Evita registros sem empresa
- **Validate company_ids:** Previne mass assignment malicioso
- **Return company_ids:** Cliente pode verificar empresa atribuída

### 🎯 Critério de aceite

- [x] Todos os endpoints POST validam company_ids
- [x] Registros sem company_ids recebem default
- [x] Registros com company_ids não autorizadas são rejeitados (403)
- [x] Response inclui company_ids atribuídas

---

## Passo 6: Validar atualização de registros

### 📝 O que fazer

Bloquear alteração de `company_ids` via API e validar acesso.

### 📂 Arquivo

Todos os controllers que atualizam registros (`master_data_api.py`, `property_api.py`)

### 🔨 Checklist de Validação

Para CADA endpoint PUT/PATCH:

1. **Bloquear company_ids:**
   ```python
   if 'company_ids' in data:
       return error_response(403, 'Cannot change company_ids via API')
   ```

2. **Buscar com filtro:**
   ```python
   domain = [('id', '=', record_id)] + request.company_domain
   record = request.env['model.name'].search(domain, limit=1)
   ```

3. **Validar acesso:**
   ```python
   if not record:
       return error_response(404, 'Record not found')
   ```

4. **Atualizar:**
   ```python
   record.write(data)
   ```

### 📖 Conceitos

- **Immutable company_ids:** Previne movimentação de registros entre empresas
- **Search com filtro:** Garante acesso antes de atualizar
- **404 genérico:** Segurança por obscuridade (não expor existência)

### 🎯 Critério de aceite

- [x] Todos os endpoints PUT/PATCH bloqueiam company_ids
- [x] Busca sempre filtra por empresa
- [x] Retorna 404 para registros inacessíveis
- [x] Atualização só funciona para registros das empresas do usuário

---

## Passo 7: Escrever testes de isolamento

### 📝 O que fazer

Criar testes E2E validando isolamento completo de dados.

### 📂 Arquivo (CRIAR NOVO)

`18.0/extra-addons/quicksol_estate/tests/test_company_isolation_api.py`

### 🔨 Implementação

```python
from odoo.tests.common import HttpCase
import json


class TestCompanyIsolationAPI(HttpCase):
    """
    Testes E2E de isolamento de dados por empresa via API.
    Valida que usuários só acessam dados das suas empresas.
    """
    
    def setUp(self):
        super().setUp()
        
        # Criar 2 empresas
        self.company_a = self.env['thedevkitchen.estate.company'].create({
            'name': 'Company A',
            'cnpj': '11222333000181',
        })
        
        self.company_b = self.env['thedevkitchen.estate.company'].create({
            'name': 'Company B',
            'cnpj': '22333444000182',
        })
        
        # Criar 2 usuários (1 por empresa)
        self.user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'usera@test.com',
            'email': 'usera@test.com',
            'password': 'test123',
            'estate_company_ids': [(6, 0, [self.company_a.id])],
            'estate_default_company_id': self.company_a.id,
        })
        
        self.user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'userb@test.com',
            'email': 'userb@test.com',
            'password': 'test123',
            'estate_company_ids': [(6, 0, [self.company_b.id])],
            'estate_default_company_id': self.company_b.id,
        })
        
        # Fazer login como User A
        self.session_a = self._login('usera@test.com', 'test123')
        
        # Fazer login como User B
        self.session_b = self._login('userb@test.com', 'test123')
    
    def _login(self, email, password):
        """Helper para fazer login e retornar session_id"""
        response = self.url_open(
            '/api/v1/users/login',
            data=json.dumps({'email': email, 'password': password}),
            headers={'Content-Type': 'application/json'}
        )
        data = response.json()
        return data.get('result', {}).get('session_id')
    
    def test_user_a_creates_property_for_company_a(self):
        """User A cria propriedade para Company A → sucesso"""
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        payload = {
            'name': 'Property A',
            'price': 100000,
            'company_ids': [(6, 0, [self.company_a.id])]
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers=headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
    
    def test_user_a_cannot_create_property_for_company_b(self):
        """User A tenta criar propriedade para Company B → 403"""
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        payload = {
            'name': 'Property B',
            'price': 200000,
            'company_ids': [(6, 0, [self.company_b.id])]  # Company B não autorizada!
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers=headers
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
    
    def test_user_a_cannot_read_property_from_company_b(self):
        """User A tenta ler propriedade de Company B → 404"""
        # Criar propriedade como User B
        property_b = self.env['real.estate.property'].sudo().create({
            'name': 'Property B',
            'price': 200000,
            'company_ids': [(6, 0, [self.company_b.id])]
        })
        
        # User A tenta ler
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        response = self.url_open(
            f'/api/v1/properties/{property_b.id}',
            headers=headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_user_a_cannot_update_property_from_company_b(self):
        """User A tenta atualizar propriedade de Company B → 404"""
        # Criar propriedade como User B
        property_b = self.env['real.estate.property'].sudo().create({
            'name': 'Property B',
            'price': 200000,
            'company_ids': [(6, 0, [self.company_b.id])]
        })
        
        # User A tenta atualizar
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        payload = {'price': 999999}
        
        response = self.url_open(
            f'/api/v1/properties/{property_b.id}',
            data=json.dumps(payload),
            headers=headers
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_user_a_cannot_delete_property_from_company_b(self):
        """User A tenta deletar propriedade de Company B → 404"""
        # Criar propriedade como User B
        property_b = self.env['real.estate.property'].sudo().create({
            'name': 'Property B',
            'price': 200000,
            'company_ids': [(6, 0, [self.company_b.id])]
        })
        
        # User A tenta deletar
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        response = self.url_open(
            f'/api/v1/properties/{property_b.id}',
            headers=headers,
            timeout=10,
            allow_redirects=False,
            method='DELETE'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_list_properties_returns_only_company_a(self):
        """User A lista propriedades → retorna apenas de Company A"""
        # Criar propriedades para ambas empresas
        prop_a = self.env['real.estate.property'].sudo().create({
            'name': 'Property A',
            'price': 100000,
            'company_ids': [(6, 0, [self.company_a.id])]
        })
        
        prop_b = self.env['real.estate.property'].sudo().create({
            'name': 'Property B',
            'price': 200000,
            'company_ids': [(6, 0, [self.company_b.id])]
        })
        
        # User A lista
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_a
        }
        
        response = self.url_open(
            '/api/v1/properties',
            headers=headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', [])
        
        # Deve retornar apenas Property A
        ids = [p['id'] for p in data]
        self.assertIn(prop_a.id, ids)
        self.assertNotIn(prop_b.id, ids)
```

### ✅ Rodar testes

```bash
cd 18.0
docker compose exec odoo odoo -d realestate --test-enable --stop-after-init \
  --test-tags /quicksol_estate.test_company_isolation_api
```

### 🎯 Critério de aceite

- [x] 9 testes criados (OAuth + isolamento)
- [x] Todos os testes implementados
- [x] CREATE: sucesso para empresa autorizada
- [x] CREATE: 403 para empresa não autorizada
- [x] READ: 404 para empresa não autorizada
- [x] UPDATE: 404 para empresa não autorizada
- [x] DELETE: 404 para empresa não autorizada
- [x] LIST: retorna apenas dados das empresas autorizadas

---

## Passo 8: Ativar Record Rules (Odoo Web)

### 📝 O que fazer

Descomentar e ativar record rules para filtrar dados na interface web do Odoo.

### 📂 Arquivo

`18.0/extra-addons/quicksol_estate/security/record_rules.xml`

### 🔨 Implementação

**Descomentar as regras existentes e ajustar domínio:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Property: User vê apenas das suas empresas -->
    <record id="real_estate_property_company_rule" model="ir.rule">
        <field name="name">Property: Multi-Company</field>
        <field name="model_id" ref="model_real_estate_property"/>
        <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
    </record>

    <!-- Agent: User vê apenas das suas empresas -->
    <record id="real_estate_agent_company_rule" model="ir.rule">
        <field name="name">Agent: Multi-Company</field>
        <field name="model_id" ref="model_real_estate_agent"/>
        <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
    </record>

    <!-- Tenant: User vê apenas das suas empresas -->
    <record id="real_estate_tenant_company_rule" model="ir.rule">
        <field name="name">Tenant: Multi-Company</field>
        <field name="model_id" ref="model_real_estate_tenant"/>
        <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
    </record>

    <!-- Lease: User vê apenas das suas empresas -->
    <record id="real_estate_lease_company_rule" model="ir.rule">
        <field name="name">Lease: Multi-Company</field>
        <field name="model_id" ref="model_real_estate_lease"/>
        <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
    </record>

    <!-- Sale: User vê apenas das suas empresas -->
    <record id="real_estate_sale_company_rule" model="ir.rule">
        <field name="name">Sale: Multi-Company</field>
        <field name="model_id" ref="model_real_estate_sale"/>
        <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
        <field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
    </record>
</odoo>
```

### ✅ Atualizar módulo

```bash
cd 18.0
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
docker compose restart odoo
```

### 🎯 Critério de aceite

- [x] Record rules implementadas e ativas
- [x] Domínio usa `user.estate_company_ids.ids`
- [x] Aplicadas a todos os modelos principais (5 regras)
- [x] Carregadas no manifest sem erros
- [x] Web UI filtra dados por empresa

---

## Passo 9: Validar e documentar

### 📝 O que fazer

Validar que tudo está funcionando e documentar o que foi implementado.

### ✅ Checklist de Validação

**1. Testes automatizados:**
```bash
# Rodar todos os testes de isolamento
docker compose exec odoo odoo -d realestate --test-enable --stop-after-init \
  --test-tags /quicksol_estate.test_company_isolation_api
```

**2. Testes manuais via cURL:**

```bash
# Login User A
SESSION_A=$(curl -X POST http://localhost:8069/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"usera@test.com","password":"test123"}' \
  | jq -r '.result.session_id')

# Criar propriedade
curl -X POST http://localhost:8069/api/v1/properties \
  -H "Content-Type: application/json" \
  -H "X-Openerp-Session-Id: $SESSION_A" \
  -d '{"name":"Test Property","price":100000}'

# Listar propriedades (deve retornar apenas de Company A)
curl -X GET http://localhost:8069/api/v1/properties \
  -H "X-Openerp-Session-Id: $SESSION_A"
```

**3. Validar Web UI:**
- Logar como User A no Odoo Web (`http://localhost:8069`)
- Criar propriedade via interface
- Verificar que só vê propriedades da Company A
- Logar como User B
- Verificar que só vê propriedades da Company B

### 📖 Documentar

Atualizar `MULTI-TENANCY-IMPLMENTATION-PLAN.md`:

```markdown
### Fase 1: Isolamento por Empresa ✅ COMPLETO

**Status:** Implementado e testado
**Data:** 2025-12-05

**Implementações:**
- ✅ Decorator @require_company
- ✅ Serviço CompanyValidator
- ✅ 8 endpoints master data protegidos
- ✅ 4 endpoints properties protegidos (CRUD)
- ✅ Validação de criação de registros
- ✅ Validação de atualização de registros
- ✅ 7 testes E2E de isolamento
- ✅ Record rules ativadas (Odoo Web)

**Cobertura:**
- Master Data: 8/8 endpoints ✅
- Properties: 4/4 endpoints ✅
- Testes: 7/7 passando ✅
- Record Rules: 5/5 ativas ✅
```

### 🎯 Critério de aceite

- [x] Todos os testes automatizados implementados
- [x] Testes de integração HTTP validam isolamento
- [x] Web UI filtra por empresa corretamente (via record rules)
- [x] Documentação atualizada (09/01/2026)
- [x] Fase 1 100% completa e documentada

---

## 📊 Resumo Final

### ✅ O que foi implementado (~35% da Fase 1)

**Status:** Infraestrutura de multi-tenancy completa, funcionalidades de negócio pendentes

✅ **Decorator @require_company**
- Filtra automaticamente por `user.estate_company_ids`
- Injeta `request.company_domain` e `request.user_company_ids`
- Bloqueia usuários sem empresas (403)
- **Arquivo:** `thedevkitchen_apigateway/middleware.py`

✅ **Serviço CompanyValidator**
- Valida company_ids em criação/atualização
- Garante empresa padrão se não informada
- Loga tentativas de acesso não autorizado
- **Arquivo:** `quicksol_estate/services/company_validator.py`

✅ **12 Endpoints Básicos Protegidos**
- 8 master data endpoints (listagem) ✅
- 4 property CRUD básico ✅
- Todos validam company_ids em operações
- **Arquivos:**
  - `quicksol_estate/controllers/master_data_api.py`
  - `quicksol_estate/controllers/property_api.py`

✅ **Validações de Segurança Básicas**
- CREATE: valida e adiciona empresas ✅
- READ: filtra por empresa (404 genérico) ✅
- UPDATE: bloqueia alteração de company_ids ✅
- DELETE: filtra por empresa (404 genérico) ✅

✅ **Testes de Integração HTTP Básicos**
- 9 testes de isolamento básico ✅
- Validam autenticação e isolamento simples ✅
- **Arquivo:** `quicksol_estate/tests/api/test_company_isolation_api.py`

✅ **Record Rules**
- 5 regras ativadas (Property, Agent, Tenant, Lease, Sale) ✅
- Filtra automaticamente na Web UI ✅
- **Arquivo:** `quicksol_estate/security/record_rules.xml`

### ❌ O que ainda falta (~65% da Fase 1)

❌ **Gestão Completa de Agentes/Funcionários**
- Sem CRUD completo, apenas listagem básica
- Falta atribuição, permissões, comissionamento
- **Arquivo a criar:** `controllers/agent_api.py`

❌ **Gestão de Contratos de Locação**
- Modelo existe mas sem API
- Falta CRUD, controle de pagamentos, renovações
- **Arquivo a criar:** `controllers/lease_api.py`

❌ **Gestão de Contratos de Venda**
- Modelo existe mas sem API
- Falta CRUD, propostas, etapas de venda
- **Arquivo a criar:** `controllers/sale_api.py`

❌ **Gestão Completa de Imóveis**
- CRUD básico existe, mas falta:
  - Upload de fotos e documentos
  - Controle de chaves
  - Histórico de visitas
  - Publicação em portais
- **Arquivo a expandir:** `controllers/property_api.py`

❌ **Gestão de Inquilinos e Proprietários**
- Listagem básica existe, falta CRUD completo
- Falta histórico, documentação, análises
- **Arquivos a criar/expandir:** `controllers/tenant_api.py`, `master_data_api.py`

❌ **Gestão Financeira**
- Não existe
- Falta controle de pagamentos, repasses, comissões
- **Arquivo a criar:** `controllers/financial_api.py`

❌ **Relatórios e Dashboard**
- Não existe
- **Arquivo a criar:** `controllers/reports_api.py`

❌ **Sistema de Notificações**
- Não existe
- **Arquivo a criar:** `controllers/notifications_api.py`

### Próximos passos (Prioridades)

**Fase 2:** HATEOAS e Links de Hipermídia (ADR-007)
**Fase 3:** Auditoria de Operações
**Fase 4:** Testes de Carga e Performance

---

## 🔧 Troubleshooting

### Erro: "User has no company access"
**Causa:** Usuário sem empresas vinculadas  
**Solução:** Adicionar usuário a uma empresa via Web UI

### Erro: "Access denied to companies: [X]"
**Causa:** Tentativa de criar/editar registro para empresa não autorizada  
**Solução:** Usar apenas empresas em `user.estate_company_ids`

### Erro: Record rules não funcionam
**Causa:** Módulo não atualizado ou regras comentadas  
**Solução:** 
```bash
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
docker compose restart odoo
```

### Erro: Testes falhando
**Causa:** Dados de teste conflitantes  
**Solução:** Limpar banco de teste:
```bash
docker compose exec odoo odoo -d realestate --test-enable --stop-after-init --test-tags /quicksol_estate -i quicksol_estate
```

---

**Status Geral da Fase 1**: ⚠️ **~35% COMPLETO** (Infraestrutura pronta, funcionalidades de negócio pendentes)
**Data de Atualização**: 09/01/2026  
**Tempo Investido**: ~14 horas (infraestrutura)  
**Tempo Estimado Restante**: ~40-60 horas (funcionalidades de negócio)

**Próximos Passos Prioritários:**
1. Implementar CRUD completo de Agentes/Funcionários
2. Implementar CRUD completo de Contratos de Locação
3. Implementar CRUD completo de Contratos de Venda
4. Expandir funcionalidades de Imóveis (fotos, documentos, chaves)
5. Implementar gestão de Inquilinos e Proprietários

⚠️ **A infraestrutura de multi-tenancy está funcional, mas o sistema de gestão imobiliária ainda precisa ser desenvolvido.**
