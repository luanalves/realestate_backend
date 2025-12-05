# Plano de Implementação: Multi-Tenancy com Isolamento de Imobiliárias

**Branch:** `feature/multi-tenancy-company-isolation`  
**Data de Criação:** 30/11/2025  
**Última Atualização:** 01/12/2025  
**Status:** Planejamento

## Melhorias Aplicadas (01/12/2025)

### Arquitetura e Código
1. **Orientação a Objetos:** Código refatorado em classes de serviço independentes
   - `RateLimiter` - Controle de tentativas de login
   - `SessionValidator` - Validação de sessões de usuários (headless)
   - `AuditLogger` - Registro de eventos de segurança
   - `SecurityService` - Validação de acesso e filtros de empresa
   - `AuditService` - Auditoria de operações de API

2. **Remoção de `.sudo()`:** Eliminado uso desnecessário de privilégios elevados
   - Controllers usam `request.env` (contexto do usuário autenticado)
   - Filtros aplicados no domínio das queries
   - Segurança por camadas (defense in depth)

3. **Código Auto-Explicativo:** Removidos comentários excessivos
   - Métodos pequenos e focados
   - Nomes descritivos
   - Estrutura clara seguindo ADR-001

### Autenticação
4. **Endpoint de Login de Usuários (Novo):**
   - Parâmetros: `email` e `password`
   - Endpoint: `/api/v1/users/login` (diferente do OAuth)
   - Usa sessões nativas do Odoo (`request.session.authenticate`)
   - Retorna `session_id` (hash) para requisições headless
   - Sem OAuth/JWT para usuários (isso é só para aplicações)

5. **Clarificação de Autenticação:**
   - **OAuth/JWT** = Autenticação de APLICAÇÕES via `/api/v1/auth/token` (já existe, manter)
   - **Sessões** = Autenticação de USUÁRIOS via `/api/v1/users/login` (novo, Fase 0)
   - session_id contém contexto do usuário (`user_id`, `estate_company_ids`)
   - Mesmo session_id funciona na web E na API (sessão compartilhada)

## Objetivo

Implementar isolamento completo de dados por imobiliária, garantindo que usuários só manipulem dados das empresas (imobiliárias) às quais estão vinculados. A arquitetura de banco de dados (tabelas de relacionamento many2many) já existe; este plano foca em ativar regras de acesso, filtros de API e testes de isolamento.

## Contexto Atual

### ✅ Já Implementado

- **Modelo Company** (`thedevkitchen.estate.company`) completamente desenvolvido com validação de CNPJ
- **Relacionamentos Many2many** entre Company e todas as entidades principais:
  - `thedevkitchen_company_property_rel`
  - `thedevkitchen_company_agent_rel`
  - `thedevkitchen_company_tenant_rel`
  - `thedevkitchen_company_lease_rel`
  - `thedevkitchen_company_sale_rel`
  - `thedevkitchen_user_company_rel`
- **Campos no `res.users`**:
  - `estate_company_ids` (Many2many) - Todas as empresas às quais o usuário tem acesso
  - `estate_default_company_id` (Many2one) - Empresa padrão do usuário
- **Grupos de segurança** definidos:
  - `group_real_estate_manager` - Gerente da imobiliária
  - `group_real_estate_user` - Usuário da imobiliária
  - `group_real_estate_agent` - Corretor
  - `group_real_estate_portal_user` - Cliente/Portal
- **Regras de acesso (record rules)** rascunhadas mas **desabilitadas** em `security/record_rules.xml`
- **API Gateway** (`thedevkitchen_apigateway`) com OAuth 2.0 e JWT
- **Testes base** para modelos e API

### 🔑 Conceitos Importantes: OAuth vs Sessão de Usuário

**OAuth 2.0 (Autenticação de APLICAÇÕES):**
- Representa uma **aplicação/serviço cliente** (ex: frontend headless, APIs externas)
- Obtido via `client_id` + `client_secret` no endpoint `/api/v1/auth/token`
- **NÃO tem relação com usuários** das imobiliárias
- Usado para identificar qual aplicação está consumindo a API
- Exemplo: Frontend React precisa se autenticar para consumir APIs

**Sessão de Usuário (Autenticação de PESSOAS):**
- Representa um **usuário específico** da imobiliária (pessoa física)
- Obtido via endpoint `/api/v1/users/login` com email + senha
- Usa o sistema de **sessões nativo do Odoo** (`request.session`)
- Retorna um **hash de sessão** (session_id) persistido no banco
- Este hash é usado para validar todas as requisições headless
- **Mesmo usuário pode logar na web OU via API** (sessão compartilhada)
- **Este é o mecanismo necessário para multi-tenancy**

**Diferença Fundamental:**
- OAuth: "Qual aplicação/serviço está fazendo a requisição?"
- Sessão: "Qual pessoa (usuário da imobiliária) está usando o sistema?"

**Fluxo Completo (Headless):**
```
1. Frontend obtém token OAuth (client_id + client_secret) → Identifica a aplicação
2. Usuário faz login (email + password) → Cria sessão Odoo + retorna session_id
3. Frontend envia session_id em todas as requisições → Valida usuário e empresa
4. Logout revoga a sessão → session_id invalidado
```

### ⚠️ Gaps a Resolver

1. **Record rules desabilitadas** - Regras comentadas em XML, precisam ser ativadas
2. **API não filtra por empresa** - Endpoints retornam todos os dados, sem filtro de `estate_company_ids`
3. **Criação não atribui empresa** - Registros criados via API não recebem empresa automaticamente
4. **Falta testes de isolamento** - Nenhum teste valida que User A não vê dados de Company B
5. **HATEOAS não implementado** - Links de hipermídia ausentes (requerido por ADR-007)

### 🔴 Vulnerabilidades de Segurança Identificadas

**Contexto:** Sistema opera em modo headless com autenticação via OAuth 2.0 Password Grant (ADR-009).

#### 1. Uso Inadequado de `.sudo()`
Buscar registros com `.sudo()` antes de aplicar filtros de empresa permite bypass das record rules e potencial vazamento de dados.

**Solução:** Usar `request.env` (com contexto do usuário autenticado) e aplicar filtro de empresa no domínio da query.

#### 2. Mass Assignment de `company_ids`
Aceitar `company_ids` do cliente sem validação permite usuário vincular registros a empresas não autorizadas.

**Solução:** Validar que todas as empresas informadas estão em `user.estate_company_ids` antes de criar/atualizar.

#### 3. Ausência de Validação em UPDATE
Permitir alteração de `company_ids` via API UPDATE pode mover registros entre empresas sem autorização.

**Solução:** Proibir explicitamente alteração de `company_ids` via API.

## Fases de Implementação

### Fase 0: Autenticação de Usuários com Sessões Odoo (OBRIGATÓRIA)

**⚠️ ESTA FASE DEVE SER IMPLEMENTADA ANTES DE TODAS AS OUTRAS**

**Objetivo:** Implementar login/logout de usuários das imobiliárias usando sessões nativas do Odoo, permitindo uso tanto headless quanto web.

**Conceito:**
- Usar `request.session` do Odoo (já gerencia sessões automaticamente)
- Retornar `session_id` (hash) no login para clientes headless
- Validar `session_id` em todos os endpoints de API
- Mesma sessão funciona na web E na API
- Session_id persistido no banco (tabela `ir_sessions`)

**Referência:** ADR-009 - Autenticação Headless com Contexto de Usuário

#### 0.1. Criar Modelo de Sessão de API

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/models/api_session.py`

**Objetivo:** Estender informações da sessão para APIs headless.

```python
from odoo import models, fields, api

class APISession(models.Model):
    _name = 'thedevkitchen.api.session'
    _description = 'API Session Management'
    _order = 'create_date desc'
    
    session_id = fields.Char(
        string='Session ID',
        required=True,
        index=True,
        help='Hash da sessão (mesmo da ir.sessions)'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        ondelete='cascade'
    )
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    is_active = fields.Boolean(string='Active', default=True, index=True)
    last_activity = fields.Datetime(string='Last Activity', default=fields.Datetime.now)
    login_at = fields.Datetime(string='Login At', default=fields.Datetime.now)
    logout_at = fields.Datetime(string='Logout At')
```

**Atualizar módulo:**
```bash
docker compose exec odoo odoo -u thedevkitchen_apigateway -d realestate --stop-after-init
```

#### 0.2. Criar Endpoint de Login de Usuários

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py`

**IMPORTANTE:** Este endpoint é para **USUÁRIOS** das imobiliárias (não para aplicações/serviços).

**Estrutura modular seguindo ADR-001 (classes pequenas e auto-explicativas):**

```python
from datetime import datetime
from odoo import http
from odoo.http import request
from ..services.rate_limiter import RateLimiter
from ..services.audit_logger import AuditLogger

class UserAuthController(http.Controller):
    
    @http.route('/api/v1/auth/login', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def login(self, email, password):
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
        
        try:
            # Rate limiting (previne brute force)
            if not RateLimiter.check(ip_address, email):
                return {'error': {'status': 429, 'message': 'Too many login attempts'}}
            
            # Autentica usando sessões nativas do Odoo (MESMO sistema da web)
            db_name = request.env.cr.dbname
            uid = request.session.authenticate(db_name, email, password)
            
            if not uid:
                AuditLogger.log_failed_login(ip_address, email)
                return {'error': {'status': 401, 'message': 'Invalid credentials'}}
            
            user = request.env['res.users'].browse(uid)
            
            # Valida se está ativo e tem empresas
            if not user.active or not user.estate_company_ids:
                AuditLogger.log_failed_login(ip_address, email, 'inactive or no companies')
                return {'error': {'status': 403, 'message': 'Access denied'}}
            
            # Pega session_id da sessão Odoo (já criada pelo authenticate)
            session_id = request.session.sid
            
            # Registra sessão para controle de API headless
            request.env['thedevkitchen.api.session'].sudo().create({
                'session_id': session_id,
                'user_id': user.id,
                'ip_address': ip_address,
                'user_agent': user_agent,
            })
            
            AuditLogger.log_successful_login(ip_address, email, user.id)
            RateLimiter.clear(ip_address, email)
            
            return {
                'session_id': session_id,  # Hash para usar em requisições headless
                'user': self._build_user_response(user)
            }
            
        except Exception as e:
            AuditLogger.log_error('user.login', email, str(e))
            return {'error': {'status': 500, 'message': 'Internal server error'}}
    
    def _build_user_response(self, user):
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email or user.login,
            'companies': [
                {'id': c.id, 'name': c.name, 'cnpj': getattr(c, 'cnpj', None)}
                for c in user.estate_company_ids
            ],
            'default_company_id': (
                user.estate_default_company_id.id 
                if user.estate_default_company_id 
                else (user.estate_company_ids[0].id if user.estate_company_ids else None)
            )
        }
```

**Criar classes de serviço (seguindo ADR-001 - Orientação a Objetos):**

**Nota sobre Arquitetura:**
O código foi dividido em serviços independentes para seguir os princípios de:
- **Single Responsibility Principle:** Cada classe tem uma responsabilidade específica
- **Reusabilidade:** Serviços podem ser usados em diferentes controllers
- **Testabilidade:** Classes pequenas são mais fáceis de testar
- **Manutenibilidade:** Código auto-explicativo sem necessidade de comentários extensos

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/services/__init__.py`
```python
from . import rate_limiter
from . import audit_logger
from . import session_validator
```

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/services/rate_limiter.py`
```python
from datetime import datetime, timedelta

class RateLimiter:
    _attempts = {}
    
    @classmethod
    def check(cls, ip, email):
        now = datetime.now()
        cutoff = now - timedelta(minutes=15)
        
        key = f"{ip}:{email}"
        attempts = cls._attempts.get(key, [])
        attempts = [ts for ts in attempts if ts > cutoff]
        
        if len(attempts) >= 5:
            return False
        
        attempts.append(now)
        cls._attempts[key] = attempts
        return True
    
    @classmethod
    def clear(cls, ip, email):
        key = f"{ip}:{email}"
        if key in cls._attempts:
            del cls._attempts[key]
```
            return False
        
        attempts.append(now)
        self._attempts[key] = attempts
        return True
    
    def clear(self, ip, email):
        key = f"{ip}:{email}"
        if key in self._attempts:
            del self._attempts[key]
```

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/services/session_validator.py`
```python
from datetime import datetime, timedelta
from odoo import fields
from odoo.http import request

class SessionValidator:
    """
    Valida sessões de usuários em requisições headless.
    Usa tabela ir.sessions do Odoo + tabela customizada de API sessions.
    """
    
    @staticmethod
    def validate(session_id):
        """
        Valida se session_id é válido e ativo.
        
        Args:
            session_id (str): Hash da sessão
            
        Returns:
            tuple: (valid: bool, user: res.users or None, error_msg: str or None)
        """
        if not session_id:
            return False, None, 'No session ID provided'
        
        # Busca sessão da API
        api_session = request.env['thedevkitchen.api.session'].sudo().search([
            ('session_id', '=', session_id),
            ('is_active', '=', True)
        ], limit=1)
        
        if not api_session:
            return False, None, 'Invalid or expired session'
        
        # Atualiza última atividade
        api_session.sudo().write({'last_activity': fields.Datetime.now()})
        
        # Verifica se usuário ainda está ativo
        user = api_session.user_id
        if not user.active:
            api_session.sudo().write({'is_active': False})
            return False, None, 'User inactive'
        
        return True, user, None
    
    @staticmethod
    def cleanup_expired():
        """
        Remove sessões expiradas (mais de 7 dias sem atividade).
        Pode ser chamado via cron.
        """
        cutoff = datetime.now() - timedelta(days=7)
        expired = request.env['thedevkitchen.api.session'].sudo().search([
            ('last_activity', '<', cutoff),
            ('is_active', '=', True)
        ])
        expired.write({'is_active': False})
        return len(expired)
```

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/services/audit_logger.py`
```python
from odoo.http import request

class AuditLogger:
    @staticmethod
    def log_failed_login(ip, email, reason='Invalid credentials'):
        request.env['ir.logging'].sudo().create({
            'name': 'auth.login.failed',
            'type': 'server',
            'level': 'WARNING',
            'message': f'Failed login: {email} from {ip} - {reason}',
        })
    
    @staticmethod
    def log_successful_login(ip, email, user_id):
        request.env['ir.logging'].sudo().create({
            'name': 'auth.login.success',
            'type': 'server',
            'level': 'INFO',
            'message': f'Successful login: {email} (ID: {user_id}) from {ip}',
        })
    
    @staticmethod
    def log_logout(email, user_id):
        request.env['ir.logging'].sudo().create({
            'name': 'auth.logout',
            'type': 'server',
            'level': 'INFO',
            'message': f'Logout: {email} (ID: {user_id})',
        })
    
    @staticmethod
    def log_error(context, email, error):
        request.env['ir.logging'].sudo().create({
            'name': f'{context}.error',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error for {email}: {error}',
        })
```
    @http.route('/api/v1/users/logout', type='json', auth='user', methods=['POST'], csrf=False, cors='*')
    def logout(self):
        """
        Logout de usuário (invalida sessão).
        
        POST /api/v1/users/logout
        Cookie: session_id=abc123...
        OU
        Header: X-Openerp-Session-Id: abc123...
        
        Returns:
        {
            "message": "Logged out successfully"
        }
        """
        try:
            session_id = request.session.sid
            user = request.env.user
            
            # Marca sessão API como inativa
            api_session = request.env['thedevkitchen.api.session'].sudo().search([
                ('session_id', '=', session_id),
                ('is_active', '=', True)
            ], limit=1)
            
            if api_session:
                api_session.write({
                    'is_active': False,
                    'logout_at': fields.Datetime.now()
                })
            
            AuditLogger.log_logout(user.email or user.login, user.id)
            
            # Destroi sessão Odoo
            request.session.logout(keep_db=True)
            
            return {'message': 'Logged out successfully'}
            
        except Exception as e:
            return {'error': {'status': 500, 'message': 'Internal server error'}}
```

**Testes de segurança:**

```bash
# Login
curl -X POST http://localhost:8069/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"email":"admin","password":"admin"},"id":1}'

# Retorna:
# {"result": {"session_id": "abc123...", "user": {...}}}

# Logout (usar session_id retornado)
curl -X POST http://localhost:8069/api/v1/users/logout \
  -H "Content-Type: application/json" \
  -H "X-Openerp-Session-Id: abc123..." \
  -d '{"jsonrpc":"2.0","method":"call","params":{},"id":1}'
```

#### 0.3. Criar Decorator de Validação de Sessão

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`

**Adicionar `require_session`:**
```python
import functools
from odoo.http import request
from .services.session_validator import SessionValidator


def require_session(func):
    """
    Decorator para validar sessão de usuário em endpoints headless.
    
    Uso:
        @http.route('/api/v1/properties', auth='none', csrf=False, cors='*')
        @require_session
        def list_properties(self):
            user = request.env.user  # Já autenticado pelo decorator
            properties = request.env['real.estate.property'].search([])
            # Record rules aplicam isolamento automaticamente
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Busca session_id do header, cookie ou sessão
        session_id = (
            request.httprequest.headers.get('X-Openerp-Session-Id') or
            request.httprequest.cookies.get('session_id') or
            request.session.sid
        )
        
        # Valida sessão
        valid, user, error_msg = SessionValidator.validate(session_id)
        
        if not valid:
            return {
                'error': {
                    'status': 401,
                    'message': error_msg or 'Unauthorized'
                }
            }
        
        # CRÍTICO: Trocar contexto para usuário da sessão
        request.env = request.env(user=user)
        
        # Executa função (record rules já aplicadas automaticamente)
        return func(*args, **kwargs)
    
    return wrapper
```

**IMPORTANTE:** 
- Este decorator é para endpoints **headless** (Flutter/React/etc)
- OAuth/JWT (`require_jwt`) continua existindo para autenticação de **aplicações**
- Usuários logam via `/api/v1/users/login` (sessões), aplicações usam `/api/v1/auth/token` (JWT)

#### 0.4. Testes de Autenticação de Usuários

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/tests/test_user_auth.py`

**Cenários:**
- Login com credenciais válidas → retorna session_id + user data
- Login com senha incorreta → 401
- Login de usuário sem empresas → 403
- Logout invalida sessão
- Session_id inválido retorna 401
- Decorator `@require_session` injeta usuário correto em request.env.user
- Sessão expirada (7+ dias sem atividade) é rejeitada

**Comando:**
```bash
docker compose exec odoo odoo -u thedevkitchen_apigateway --test-enable --stop-after-init \
  --test-tags /thedevkitchen_apigateway.test_user_auth
```

---

### Fase 1: Ativação das Record Rules (Odoo Web)

**Objetivo:** Garantir que usuários só vejam/editem dados das suas empresas através da interface web do Odoo.

#### 1.1. Ativar Record Rules em `security/record_rules.xml`

**Arquivo:** `18.0/extra-addons/quicksol_estate/security/record_rules.xml`

**Ações:**
- Descomentar regras existentes (atualmente com `<!-- -->`)
- Ajustar domínios para usar `estate_company_ids`:
  ```xml
  <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
  ```
- Aplicar para todos os modelos:
  - `real.estate.property`
  - `real.estate.agent`
  - `real.estate.tenant`
  - `real.estate.lease`
  - `real.estate.sale`

**Regras específicas por grupo:**
- **Manager/User:** Acesso a todos os registros das suas empresas
- **Agent:** Apenas registros onde ele é o corretor OU registros das suas empresas
- **Portal:** Apenas seus próprios dados (inquilino vê seus aluguéis)

#### 1.2. Atualizar Módulo

```bash
cd 18.0
docker compose restart odoo
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
docker compose restart odoo
```

#### 1.3. Testes Unitários de Record Rules

**Arquivo:** `18.0/extra-addons/quicksol_estate/tests/test_company_isolation.py`

**Cenários de teste:**
- Setup: Criar 2 empresas, 2 usuários (1 por empresa)
- Test 1: User A cria propriedade → só User A e Admin veem
- Test 2: User B não consegue ler propriedade de User A
- Test 3: User B não consegue editar propriedade de User A
- Test 4: User B não consegue deletar propriedade de User A
- Test 5: Gerente vê todas as propriedades das suas empresas
- Test 6: Corretor vê apenas propriedades onde é responsável
- Repetir para: Agent, Tenant, Lease, Sale

**Cobertura esperada:** 100% das record rules (conforme ADR-003)

**Comando:**
```bash
docker compose exec odoo odoo -u quicksol_estate --test-enable --stop-after-init \
  --test-tags /quicksol_estate.test_company_isolation
```

---

### Fase 2: Filtros de API REST (thedevkitchen_apigateway)

**Objetivo:** Garantir isolamento de dados via API REST usando contexto de usuário autenticado.

**Pré-requisitos:**
1. ✅ Endpoints `/api/v1/users/login` e `/api/v1/users/logout` implementados (Fase 0)
2. ✅ Modelo `thedevkitchen.api.session` criado
3. ✅ Decorator `@require_session` injetando user: `request.env = request.env(user=user)`
4. ✅ Sessão contém: usuário autenticado com `estate_company_ids`

**Fluxo:**
1. Frontend: `POST /api/v1/users/login {email, password}`
2. Backend valida → Cria sessão Odoo + retorna `session_id` (hash)
3. Frontend armazena session_id → Envia em requests: `X-Openerp-Session-Id: <hash>`
4. Decorator `@require_session` valida hash → Injeta user em `request.env`
5. Controllers usam `request.env.user.estate_company_ids` para filtrar dados

**Princípios de Segurança:**
- ❌ Nunca usar `.sudo()` em queries transacionais
- ❌ Nunca buscar registro antes de aplicar filtro de empresa
- ❌ Nunca aceitar `company_ids` do cliente sem validação
- ✅ Sempre aplicar filtro no domínio da query
- ✅ Sempre usar `request.env` (com contexto do usuário)
- ✅ Sempre retornar 404 genérico para registros inacessíveis

#### 2.1. Implementar Serviço de Segurança Multi-Tenancy

**Arquivo:** `18.0/extra-addons/quicksol_estate/services/security_service.py`

```python
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class SecurityService:
    @staticmethod
    def get_company_domain(user=None):
        if user is None:
            user = request.env.user
        
        if user.has_group('base.group_system'):
            return []
        
        if not user.estate_company_ids:
            _logger.warning(f"User {user.login} has no companies")
            return [('id', '=', -1)]
        
        return [('company_ids', 'in', user.estate_company_ids.ids)]
    
    @staticmethod
    def validate_company_access(company_ids, user=None):
        if user is None:
            user = request.env.user
        
        if user.has_group('base.group_system'):
            return True, None
        
        user_company_ids = set(user.estate_company_ids.ids)
        requested = set(company_ids)
        unauthorized = requested - user_company_ids
        
        if unauthorized:
            _logger.warning(f"User {user.login} unauthorized for companies: {unauthorized}")
            return False, f'Access denied to companies: {list(unauthorized)}'
        
        return True, None
```

**Arquivo:** `18.0/extra-addons/quicksol_estate/services/audit_service.py`

```python
from odoo.http import request
from odoo import fields

class AuditService:
    @staticmethod
    def log_access(resource_type, resource_id, operation, success=True, error=None):
        request.env['thedevkitchen.api.access.log'].create({
            'user_id': request.env.user.id,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'operation': operation,
            'success': success,
            'error_message': error or '',
            'ip_address': request.httprequest.remote_addr,
            'timestamp': fields.Datetime.now(),
        })
```

#### 2.2. Aplicar Filtros em Controllers

**Arquivo:** `18.0/extra-addons/quicksol_estate/controllers/api_property_controller.py`

```python
from odoo import http
from odoo.http import request
from ..services.security_service import SecurityService
from ..services.audit_service import AuditService

class PropertyAPIController(http.Controller):
    
    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_session
    def get_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            domain = [('id', '=', property_id)] + SecurityService.get_company_domain(user)
            
            property_record = request.env['real.estate.property'].search(domain, limit=1)
            
            if not property_record:
                AuditService.log_access('property', property_id, 'read', 
                                       success=False, error='Not found or access denied')
                return error_response(404, 'Property not found')
            
            AuditService.log_access('property', property_id, 'read', success=True)
            return success_response(serialize_property(property_record))
            
        except Exception as e:
            return error_response(500, 'Internal server error')
```

    @http.route('/api/v1/properties', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_session
    def create_property(self, **kwargs):
        try:
            user = request.env.user
            
            if not user.has_group('quicksol_estate.group_real_estate_manager'):
                return error_response(403, 'Only managers can create properties')
            
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            if 'company_ids' in data:
                valid, error_msg = SecurityService.validate_company_access(data['company_ids'], user)
                if not valid:
                    AuditService.log_access('property', None, 'create', success=False, error=error_msg)
                    return error_response(403, error_msg)
            else:
                data['company_ids'] = [user.estate_default_company_id.id]
            
            property_vals = {
                'name': data.get('name'),
                'property_type_id': data.get('property_type_id'),
                'company_ids': [(6, 0, data['company_ids'])],
            }
            
            property_record = request.env['real.estate.property'].create(property_vals)
            AuditService.log_access('property', property_record.id, 'create', success=True)
            
            return success_response(serialize_property(property_record), status_code=201)
            
        except Exception as e:
            return error_response(500, 'Internal server error')
```

    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_session
    def update_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            if 'company_ids' in data:
                AuditService.log_access('property', property_id, 'update', 
                                       success=False, error='Cannot change company_ids')
                return error_response(403, 'Cannot change property companies')
            
            domain = [('id', '=', property_id)] + SecurityService.get_company_domain(user)
            property_record = request.env['real.estate.property'].search(domain, limit=1)
            
            if not property_record:
                AuditService.log_access('property', property_id, 'update', 
                                       success=False, error='Not found or access denied')
                return error_response(404, 'Property not found')
            
            allowed_fields = {'name', 'description', 'price', 'rent_price', 'property_status'}
            update_vals = {k: v for k, v in data.items() if k in allowed_fields}
            
            if not update_vals:
                return error_response(400, 'No valid fields to update')
            
            property_record.write(update_vals)
            AuditService.log_access('property', property_id, 'update', success=True)
            
            return success_response(serialize_property(property_record))
            
        except Exception as e:
            return error_response(500, 'Internal server error')
```

    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_session
    def delete_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            domain = [('id', '=', property_id)] + SecurityService.get_company_domain(user)
            property_record = request.env['real.estate.property'].search(domain, limit=1)
            
            if not property_record:
                AuditService.log_access('property', property_id, 'delete', 
                                       success=False, error='Not found or access denied')
                return error_response(404, 'Property not found')
            
            property_record.unlink()
            AuditService.log_access('property', property_id, 'delete', success=True)
            
            return success_response({'message': 'Property deleted successfully'})
            
        except Exception as e:
            return error_response(500, 'Internal server error')
```

**Aplicar o mesmo padrão para:**
- `api_agent_controller.py`
- `api_tenant_controller.py`
- `api_lease_controller.py`
- `api_sale_controller.py`

#### 2.3. Endpoint de Empresas do Usuário

**Novo endpoint:** `GET /api/v1/me/companies`

```python
@http.route('/api/v1/me/companies', type='json', auth='none', methods=['GET'], csrf=False, cors='*')
@authenticate_request
def get_user_companies(self):
    """Retorna empresas do usuário autenticado."""
    user = request.env.user
    companies = user.estate_company_ids
    
    return {
        'data': [{
            'id': c.id,
            'name': c.name,
            'cnpj': c.cnpj,
            'is_default': c.id == user.estate_default_company_id.id,
        } for c in companies],
        'links': [
            {'rel': 'self', 'href': '/api/v1/me/companies', 'type': 'GET'}
        ]
    }
```

#### 2.4. Atualizar Documentação OpenAPI

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/docs/openapi.yaml`

**Adicionar:**
- Parâmetro `X-Company-ID` (opcional) para sobrescrever empresa padrão
- Respostas 403 para acesso negado por empresa
- Schema `CompanyResponse` com exemplo
- Documentar filtro automático de empresa em todos os endpoints

---

### Fase 3: Testes de API Multi-Tenancy

**Objetivo:** Validar isolamento de dados via API REST com usuários de empresas diferentes.

#### 3.1. Testes de Isolamento de API

**Arquivo:** `18.0/extra-addons/quicksol_estate/tests/api/test_company_api_isolation.py`

**Setup:**
```python
class TestCompanyAPIIsolation(TransactionCase):
    def setUp(self):
        super().setUp()
        
        # Criar 2 empresas
        self.company_a = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária A',
            'cnpj': '11222333000181',
        })
        self.company_b = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária B',
            'cnpj': '44555666000172',
        })
        
        # Criar 2 usuários
        self.user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'usera',
            'estate_company_ids': [(6, 0, [self.company_a.id])],
            'estate_default_company_id': self.company_a.id,
        })
        self.user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'userb',
            'estate_company_ids': [(6, 0, [self.company_b.id])],
            'estate_default_company_id': self.company_b.id,
        })
        
        # Criar OAuth apps e tokens
        self.oauth_app = self.env['thedevkitchen.oauth.application'].create({
            'name': 'Test App',
            'client_id': 'test_client',
        })
        
        self.token_a = self._create_token(self.user_a)
        self.token_b = self._create_token(self.user_b)
```

**Cenários de teste (mínimo 15 testes):**

1. **test_list_properties_filtered_by_company**
   - User A cria 2 propriedades (Company A)
   - User B cria 1 propriedade (Company B)
   - GET /api/v1/properties com token de User A → retorna apenas 2 propriedades
   - GET /api/v1/properties com token de User B → retorna apenas 1 propriedade

2. **test_get_property_access_denied**
   - User A cria propriedade (Company A)
   - GET /api/v1/properties/{id} com token de User B → 404 ou 403

3. **test_create_property_auto_assigns_company**
   - POST /api/v1/properties com token de User A (sem company_ids no body)
   - Propriedade criada deve ter Company A automaticamente

4. **test_update_property_access_denied**
   - User A cria propriedade (Company A)
   - PUT /api/v1/properties/{id} com token de User B → 403

5. **test_delete_property_access_denied**
   - User A cria propriedade (Company A)
   - DELETE /api/v1/properties/{id} com token de User B → 403

6. **test_create_property_with_wrong_company_denied**
   - User A tenta criar propriedade com company_ids=[Company B]
   - Deve falhar com 403 ou auto-corrigir para Company A

7. **test_user_with_multiple_companies_sees_all**
   - Criar User C com acesso a Company A e Company B
   - User A cria propriedade (Company A)
   - User B cria propriedade (Company B)
   - GET /api/v1/properties com token de User C → retorna 2 propriedades

8. **test_get_user_companies_endpoint**
   - GET /api/v1/me/companies com token de User A
   - Retorna apenas Company A com is_default=true

**Repetir para:**
- Agents API
- Tenants API
- Leases API
- Sales API

**Comando:**
```bash
docker compose exec odoo odoo -u quicksol_estate --test-enable --stop-after-init \
  --test-tags /quicksol_estate.test_company_api_isolation
```

#### 3.2. Testes de Autenticação com Empresas

**Arquivo:** `18.0/extra-addons/thedevkitchen_apigateway/tests/test_auth_company.py`

**Cenários:**
- Sessão criada por User A contém contexto das company_ids no `estate_company_ids`
- Sessão expirada não permite acesso a dados de qualquer empresa
- Logout invalida sessão e contexto de empresa

---

### Fase 4: Testes E2E Cypress

**Objetivo:** Validar isolamento de empresas na jornada completa do usuário (UI + API).

#### 4.1. Testes E2E de Isolamento

**Arquivo:** `18.0/cypress/e2e/company-isolation.cy.js`

**Cenários (mínimo 8 testes):**

```javascript
describe('Company Isolation - Multi-Tenancy', () => {
  
  before(() => {
    // Setup: Criar 2 empresas e 2 usuários via API
  });
  
  it('User A should only see properties from Company A', () => {
    // Login como User A
    cy.login('usera', 'password');
    
    // Navegar para listagem de propriedades
    cy.visit('/web#action=real_estate.action_property');
    
    // Verificar que apenas propriedades de Company A aparecem
    cy.get('.o_list_view tbody tr').should('have.length', 2);
    cy.contains('Propriedade Company B').should('not.exist');
  });
  
  it('User A cannot access property URL from Company B', () => {
    // User B cria propriedade e pega ID
    const propertyBId = createPropertyAsUserB();
    
    // Login como User A
    cy.login('usera', 'password');
    
    // Tentar acessar URL direta da propriedade de Company B
    cy.visit(`/web#id=${propertyBId}&model=real.estate.property&view_type=form`);
    
    // Deve mostrar erro ou redirecionar
    cy.contains('Access Denied').should('be.visible');
  });
  
  it('Creating property via UI auto-assigns user company', () => {
    cy.login('usera', 'password');
    
    // Criar nova propriedade sem selecionar empresa
    cy.visit('/web#action=real_estate.action_property&view_type=form');
    cy.get('input[name="name"]').type('Nova Propriedade');
    cy.get('button.o_form_button_save').click();
    
    // Verificar que Company A foi auto-atribuída
    cy.get('.o_field_many2many[name="company_ids"] .o_tag_badge_text')
      .should('contain', 'Imobiliária A');
  });
  
  it('API calls from UI respect company filter', () => {
    // Interceptar chamadas de API
    cy.intercept('POST', '/api/v1/properties*').as('createProperty');
    
    cy.login('usera', 'password');
    
    // Criar propriedade via UI
    cy.createProperty({name: 'Test Property'});
    
    // Verificar que request inclui company_ids
    cy.wait('@createProperty').its('request.body')
      .should('have.property', 'company_ids');
  });
  
  it('User with multiple companies can switch context', () => {
    // Login como User C (multi-company)
    cy.login('userc', 'password');
    
    // Abrir seletor de empresa
    cy.get('.o_company_switcher').click();
    
    // Selecionar Company B
    cy.contains('Imobiliária B').click();
    
    // Listar propriedades - deve ver apenas de Company B
    cy.visit('/web#action=real_estate.action_property');
    cy.get('.o_list_view tbody tr').each($row => {
      cy.wrap($row).should('not.contain', 'Company A');
    });
  });
  
});
```

**Cenários adicionais:**
- Testar filtros em listagem de corretores
- Testar criação de aluguel com inquilino de outra empresa (deve falhar)
- Testar venda de propriedade entre empresas (se permitido)
- Testar portal de cliente (inquilino vê apenas seus dados)

#### 4.2. Testes E2E de API Multi-Tenancy

**Arquivo:** `18.0/cypress/e2e/api-company-isolation.cy.js`

**Cenários:**
- Gerar token OAuth para User A e User B
- Fazer requests paralelos com ambos os tokens
- Validar que respostas são diferentes (filtradas por empresa)
- Testar tentativa de acesso cruzado (403/404)
- Validar HATEOAS links incluem apenas recursos acessíveis

**Comando:**
```bash
cd 18.0
npm run cypress:run -- --spec "cypress/e2e/company-isolation.cy.js,cypress/e2e/api-company-isolation.cy.js"
```

---

### Fase 5: HATEOAS e Melhorias de API (Opcional)

**Objetivo:** Implementar hypermedia links conforme ADR-007.

#### 5.1. Adicionar Links em Respostas da API

**Padrão para todas as respostas:**

```json
{
  "data": {
    "id": 1,
    "name": "Apartamento 101",
    ...
  },
  "links": [
    {"rel": "self", "href": "/api/v1/properties/1", "type": "GET"},
    {"rel": "update", "href": "/api/v1/properties/1", "type": "PUT"},
    {"rel": "delete", "href": "/api/v1/properties/1", "type": "DELETE"},
    {"rel": "collection", "href": "/api/v1/properties", "type": "GET"},
    {"rel": "company", "href": "/api/v1/companies/5", "type": "GET"}
  ]
}
```

**Links condicionais baseados em permissões:**
- `update` e `delete` só aparecem se usuário tem permissão
- `company` só aparece se usuário tem acesso à empresa do recurso

#### 5.2. Paginação com HATEOAS

```json
{
  "data": [...],
  "meta": {
    "total": 150,
    "page": 2,
    "per_page": 20
  },
  "links": [
    {"rel": "self", "href": "/api/v1/properties?page=2"},
    {"rel": "first", "href": "/api/v1/properties?page=1"},
    {"rel": "prev", "href": "/api/v1/properties?page=1"},
    {"rel": "next", "href": "/api/v1/properties?page=3"},
    {"rel": "last", "href": "/api/v1/properties?page=8"}
  ]
}
```

---

### Fase 6: OAuth Apps por Empresa (Futuro)

**Status:** A definir (não crítico para MVP)

**Questão:** Vincular OAuth applications a empresas específicas?

**Opções:**
1. **Manter global** - Um app pode gerar tokens para usuários de qualquer empresa
2. **App por empresa** - Criar campo `company_id` em `thedevkitchen.oauth.application`
   - Token herda empresa do app
   - User só pode usar apps da sua empresa

**Impacto:**
- Se global: Mais simples, mas menos isolamento
- Se por empresa: Mais seguro, mas requer migração de apps existentes

**Decisão:** Postergar para depois do MVP de isolamento

---

## Critérios de Aceitação

### Autenticação de Usuários (Fase 0)
- [ ] Endpoints `/api/v1/users/login` e `/api/v1/users/logout` implementados e funcionando
- [ ] Modelo `thedevkitchen.api.session` criado e funcional
- [ ] Sessão contém `session_id` (hash), `user_id` e metadados (IP, user_agent)
- [ ] Decorator `@require_session` injeta usuário da sessão em `request.env.user`
- [ ] Frontend consegue fazer login e receber session_id
- [ ] Logout revoga sessão corretamente
- [ ] Sessão funciona tanto na web quanto na API headless

### Funcional
- [ ] Usuário só vê propriedades das suas empresas na UI
- [ ] Usuário só vê corretores, inquilinos, aluguéis e vendas das suas empresas
- [ ] API retorna apenas dados das empresas do usuário autenticado
- [ ] Criação via API auto-atribui empresa padrão do usuário (de `estate_default_company_id`)
- [ ] Tentativa de acesso a dados de outra empresa retorna 404 genérico
- [ ] Gerente vê todos os dados das suas empresas
- [ ] Corretor vê apenas seus próprios registros + dados das suas empresas
- [ ] Portal user vê apenas seus próprios dados

### Testes (conforme ADR-003)
- [ ] 100% cobertura de testes unitários para autenticação de usuários
- [ ] 100% cobertura de testes unitários para record rules
- [ ] 100% cobertura para filtros de API
- [ ] Mínimo 15 testes de API de isolamento passando
- [ ] Mínimo 8 testes E2E Cypress passando (com login headless)
- [ ] Todos os testes executam em < 5 minutos

### Documentação (conforme ADR-005)
- [ ] OpenAPI atualizado com endpoint de login
- [ ] OpenAPI atualizado com filtros de empresa
- [ ] Exemplos de autenticação headless (login → token → request)
- [ ] Exemplos de request/response com company_ids
- [ ] Respostas 401/403/404 documentadas
- [ ] README com instruções de setup multi-empresa headless

### Performance
- [ ] Queries com índices em company_ids (verificar EXPLAIN)
- [ ] Índice em `oauth_token.user_id` para lookup rápido
- [ ] Cache de user.estate_company_ids para evitar queries repetidas
- [ ] Testes de carga com 1000+ propriedades por empresa

---

## Checklist de Execução

### Preparação
- [x] Criar branch `feature/multi-tenancy-company-isolation`
- [ ] Ler ADR-003 (testes), ADR-004 (nomenclatura), ADR-005 (OpenAPI), ADR-007 (HATEOAS), ADR-008 (segurança)
- [ ] Revisar modelos existentes em `quicksol_estate/models/`

### Fase 0: Autenticação de Usuários ⚠️ OBRIGATÓRIA PRIMEIRO
- [ ] Criar modelo `thedevkitchen.api.session`
- [ ] Criar endpoints `POST /api/v1/users/login` e `/api/v1/users/logout`
- [ ] Criar serviços `SessionValidator`, `RateLimiter`, `AuditLogger`
- [ ] Criar decorator `@require_session` para injetar user da sessão
- [ ] Criar testes de login, logout e validação de sessão
- [ ] Atualizar módulo `thedevkitchen_apigateway`
- [ ] Validar que `request.env.user` representa usuário autenticado
- [ ] Todos os testes de autenticação passando

### Fase 1: Record Rules
- [ ] Descomentar record rules em `security/record_rules.xml`
- [ ] Atualizar domínios para `estate_company_ids`
- [ ] Atualizar módulo Odoo
- [ ] Criar `test_company_isolation.py`
- [ ] Escrever 20+ testes unitários
- [ ] Atingir 100% cobertura
- [ ] Todos os testes passando

### Fase 2: API Filters
- [ ] Criar método `_apply_company_filter()` em base controller
- [ ] Aplicar filtro em GET properties
- [ ] Aplicar filtro em GET property by ID
- [ ] Auto-atribuir empresa em POST properties
- [ ] Validar acesso em PUT properties
- [ ] Validar acesso em DELETE properties
- [ ] Repetir para agents, tenants, leases, sales
- [ ] Criar endpoint `GET /api/v1/me/companies`
- [ ] Atualizar OpenAPI documentation

### Fase 3: API Tests
- [ ] Criar `test_company_api_isolation.py`
- [ ] Setup com 2 empresas + 2 usuários + OAuth tokens
- [ ] Escrever 15+ testes de isolamento
- [ ] Testar CRUD de properties com multi-tenancy
- [ ] Repetir para agents, tenants, leases, sales
- [ ] Criar `test_auth_company.py` no apigateway
- [ ] Todos os testes passando

### Fase 4: E2E Tests
- [ ] Criar `company-isolation.cy.js`
- [ ] Setup de empresas e usuários para Cypress
- [ ] Escrever 8+ testes E2E de UI
- [ ] Criar `api-company-isolation.cy.js`
- [ ] Escrever testes E2E de API REST
- [ ] Todos os testes E2E passando

### Fase 5: HATEOAS (Opcional)
- [ ] Adicionar links em respostas da API
- [ ] Implementar links condicionais por permissão
- [ ] Adicionar paginação com HATEOAS
- [ ] Atualizar testes para validar links

### Finalização
- [ ] Code review interno
- [ ] Executar todos os testes (unit + API + E2E)
- [ ] Validar performance de queries
- [ ] Atualizar CHANGELOG.md
- [ ] Criar Pull Request
- [ ] Documentar casos de uso em README

---

## Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Record rules quebram UI existente | Alto | Média | Testar todas as telas antes de ativar rules |
| Performance degrada com filtros de empresa | Médio | Baixa | Criar índices em company_ids, cache de user companies |
| Dados existentes sem empresa atribuída | Alto | Alta | Script de migração para atribuir company_id a registros órfãos |
| OAuth tokens não carregam contexto de empresa | Médio | Média | Armazenar company_id no JWT payload |
| Testes E2E flaky com multi-tenancy | Baixo | Média | Usar fixtures isolados, limpar dados entre testes |
| Conflito com regras de acesso existentes | Alto | Baixa | Revisar ir.model.access.csv antes de ativar record rules |

---

## Dependências Externas

- Odoo 18.0 running in Docker
- PostgreSQL 16+ (para suporte a índices GIN em arrays)
- Cypress 13+ para testes E2E
- Python 3.11+ para testes unitários

---

## Próximos Passos Após Conclusão

1. **Company Switcher UI** - Componente para trocar empresa ativa
2. **Audit Log por Empresa** - Rastrear mudanças com contexto de empresa
3. **Relatórios Multi-Empresa** - Dashboard consolidado para usuários com múltiplas empresas
4. **OAuth Apps por Empresa** - Isolar aplicações OAuth por imobiliária
5. **API de Transferência** - Endpoint para transferir propriedades entre empresas
6. **Webhooks por Empresa** - Notificações filtradas por empresa

---

## Referências

- **ADR-003:** Mandatory Test Coverage - 100% cobertura obrigatória
- **ADR-004:** Nomenclatura de Módulos e Tabelas - Padrão `thedevkitchen.*`
- **ADR-005:** OpenAPI 3.0 Documentation - Schemas e exemplos obrigatórios
- **ADR-007:** HATEOAS for REST API - Links de hipermídia em respostas
- **ADR-008:** **API Security Multi-Tenancy - Segurança obrigatória em 5 camadas** ⚠️ **CRÍTICO**
- **ADR-009:** **Autenticação Headless com Contexto de Usuário - OAuth Password Grant + JWT** ⚠️ **CRÍTICO**
- **OWASP Top 10 2021:** https://owasp.org/Top10/
- **OWASP API Security Top 10:** https://owasp.org/API-Security/
- **RFC 6749 - OAuth 2.0:** https://tools.ietf.org/html/rfc6749
- **RFC 7519 - JWT:** https://tools.ietf.org/html/rfc7519
- **Odoo Security:** https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html

---

**Data de Última Atualização:** 30/11/2025  
**Autor:** GitHub Copilot + Luan Alves  
**Revisores:** A definir
