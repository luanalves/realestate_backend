# Implementation Plan: Redis Cache para Sessão e JWT

**Branch**: `023-redis-session-cache` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/023-redis-session-cache/spec.md`

## Summary

Toda requisição autenticada paga hoje 2 SELECTs + 1 UPDATE no PostgreSQL antes de qualquer lógica de negócio. Esta feature implementa cache Redis nos três lookup críticos: JWT (`require_jwt`), sessão (`require_session`) e métricas de corretor (`PerformanceService`). A abordagem é **zero-breaking-change**: contratos ORM (`request.jwt_token`, `request.api_session`) são preservados via `env.cache.set()` do Odoo 18. Invalidação é imediata via overrides de `write()`/`action_revoke()`. TTLs configuráveis via backoffice. Fallback total para PostgreSQL se Redis estiver indisponível.

## Technical Context

**Language/Version**: Python 3.11 / Odoo 18.0  
**Primary Dependencies**: `redis-py` (já disponível), `thedevkitchen_apigateway`, `quicksol_estate`  
**Storage**: PostgreSQL (source of truth), Redis DB index 1 (cache — AOF persistência, 256MB LRU)  
**Testing**: `odoo.tests.common.TransactionCase` (Odoo unit/integration), bash scripts HTTP (integration), `unittest.mock.patch` (unit com Redis mockado)  
**Target Platform**: Linux container (Docker Compose 18.0)  
**Performance Goals**: Eliminar 2 SELECTs + 1 UPDATE por requisição autenticada em cache hit  
**Constraints**: Zero 500s por falha de cache; contratos ORM inalterados; sem novo modelo de banco; TTL = 0 desabilita cada cache individualmente  
**Scale/Scope**: Afeta todos os endpoints com `@require_jwt` + `@require_session` (100% dos endpoints autenticados)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| **ADR-004**: Prefix `thedevkitchen_` em novos modelos/tabelas | ✅ PASS | Nenhum modelo novo. Campos adicionados em `thedevkitchen.security.settings` existente |
| **ADR-011**: Triple decorators `@require_jwt` + `@require_session` + `@require_company` | ✅ PASS | Decorators preservados; cache é implementado internamente, não remove decorators |
| **ADR-017**: PostgreSQL como source of truth, Redis como cache | ✅ PASS | Exatamente o padrão especificado. Redis = cache, PostgreSQL = verdade |
| **Constitution v1.9.1 — Cache-Before-Invalidation**: Hooks de invalidação devem ser deploiadas antes das de população | ✅ PASS | Ordem de deploy explicitada na seção de Deployment Order |
| **Constitution v1.9.1 — RedisClient**: Todo método swallows exceptions | ✅ PASS | Padrão implementado em `RedisClient`; nenhuma exceção propaga para a requisição |
| **Constitution v1.9.1 — JWT TTL**: `expires_at - now()` sem cap arbitrário | ✅ PASS | Implementado conforme R1 |
| **Security**: Nunca usar raw token como Redis key | ✅ PASS | SHA-256 hash do token como key (`jwt:{hash[:32]}`) |
| **Security**: Dados sensíveis (`security_token`) no payload de cache são strings opacas | ✅ PASS | `security_token` é JWT assinado, não dados PII raw |

**Post-design re-check**: ✅ Nenhuma violação identificada. Nenhuma abstração desnecessária. Padrões do projeto seguidos.

## Project Structure

### Documentation (this feature)

```text
specs/023-redis-session-cache/
├── plan.md              ← Este arquivo
├── research.md          ← Análise de integração, write points, gaps (concluído)
├── data-model.md        ← Campos novos em SecuritySettings (Phase 1)
├── quickstart.md        ← Como testar localmente (Phase 1)
├── contracts/           ← N/A (feature backend-only, sem novos endpoints de API)
└── tasks.md             ← /speckit.tasks (NOT criado aqui)
```

### Source Code — Arquivos modificados

```text
18.0/extra-addons/thedevkitchen_apigateway/
├── services/
│   └── redis_client.py                     ← NOVO: RedisClient singleton
├── middleware.py                            ← MODIFY: require_jwt + require_session com cache
├── models/
│   ├── oauth_token.py                       ← MODIFY: action_revoke() override (invalidação JWT)
│   ├── api_session.py                       ← MODIFY: write() override (invalidação session)
│   └── security_settings.py                 ← MODIFY: +3 campos TTL
├── views/
│   └── security_settings_views.xml          ← MODIFY: +grupo Cache & Session Configuration
└── tests/
    ├── unit/
    │   └── test_redis_cache_unit.py          ← NOVO: unit tests com Redis mockado
    └── integration/
        └── test_redis_cache_integration.py   ← NOVO: integration tests Odoo TransactionCase

18.0/extra-addons/quicksol_estate/
├── services/
│   └── performance_service.py               ← MODIFY: stubs → implementação real
├── models/
│   └── commission_transaction.py            ← MODIFY: create() override (invalidação performance)
└── tests/
    └── unit/
        └── test_performance_cache_unit.py    ← NOVO: unit tests cache de métricas

18.0/extra-addons/quicksol_estate/
└── controllers/
    └── profile_api.py                        ← MODIFY: delete endpoint + invalidação proativa de sessões

integration_tests/
└── test_us023_redis_cache.sh                 ← NOVO: bash E2E com Redis flush por cenário
```

## Complexity Tracking

Sem violações de gates da constituição. Nenhuma justificativa necessária.

---

## Phase 0: Research (Concluído)

Ver [research.md](research.md) para análise completa de:
- R1: Ponto de integração `require_jwt`
- R2: Ponto de integração `require_session` + Odoo 18 field cache injection
- R3: Mecanismo `env.cache.set()` para ORM lazy records
- R4: Todos os write points de invalidação mapeados (tabela completa)
- R5: Invalidação de sessão ao mudar perfil via Odoo UI
- R6: PerformanceService stubs → real Redis
- R7: Campos novos em SecuritySettings
- R8: Estratégia de QA com toggle de cache por tipo (TTL = 0)
- R9: Ordem de deploy obrigatória

---

## Phase 1: Design & Implementation Architecture

### 1.1 — RedisClient Singleton

**Arquivo**: `thedevkitchen_apigateway/services/redis_client.py`

```python
import json, hashlib, time, logging
import redis
from odoo.tools import config

_logger = logging.getLogger(__name__)

class RedisClient:
    _pool = None

    @classmethod
    def _get_connection(cls):
        """Lazy init. Returns None if Redis disabled or unavailable."""
        if not config.get('enable_redis'):
            return None
        try:
            if cls._pool is None:
                cls._pool = redis.ConnectionPool(
                    host=config.get('redis_host', 'localhost'),
                    port=int(config.get('redis_port', 6379)),
                    db=int(config.get('redis_dbindex', 1)),
                    password=config.get('redis_pass') or None,
                    decode_responses=True,
                    max_connections=10,
                )
            return redis.Redis(connection_pool=cls._pool)
        except Exception as e:
            _logger.warning(f"[CACHE] Redis connection failed: {e}")
            return None

    @classmethod
    def get_json(cls, key: str) -> dict | None:
        try:
            conn = cls._get_connection()
            if not conn:
                return None
            raw = conn.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            _logger.warning(f"[CACHE] get_json error key={key}: {e}")
            return None

    @classmethod
    def set_json(cls, key: str, data: dict, ttl: int) -> bool:
        if ttl <= 0:
            return False  # TTL=0 = cache desabilitado para este tipo
        try:
            conn = cls._get_connection()
            if not conn:
                return False
            conn.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            _logger.warning(f"[CACHE] set_json error key={key}: {e}")
            return False

    @classmethod
    def delete(cls, *keys: str) -> bool:
        try:
            conn = cls._get_connection()
            if not conn:
                return False
            conn.delete(*keys)
            return True
        except Exception as e:
            _logger.warning(f"[CACHE] delete error keys={keys}: {e}")
            return False

    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        try:
            conn = cls._get_connection()
            if not conn:
                return 0
            cursor, keys = conn.scan(0, match=pattern, count=100)
            while cursor:
                cursor, batch = conn.scan(cursor, match=pattern, count=100)
                keys.extend(batch)
            if keys:
                conn.delete(*keys)
            return len(keys)
        except Exception as e:
            _logger.warning(f"[CACHE] delete_pattern error pattern={pattern}: {e}")
            return 0

    @staticmethod
    def jwt_key(raw_token: str) -> str:
        return f"jwt:{hashlib.sha256(raw_token.encode()).hexdigest()[:32]}"

    @staticmethod
    def session_key(session_id: str) -> str:
        return f"session:{session_id}"

    @staticmethod
    def performance_key(agent_id: int, date_from, date_to) -> str:
        return f"performance:agent:{agent_id}:{date_from}:{date_to}"
```

**Regra absoluta**: Nenhum método propaga exceção. A aplicação funciona a 100% sem Redis.

---

### 1.2 — JWT Cache em `require_jwt`

**Arquivo**: `thedevkitchen_apigateway/middleware.py` — função `require_jwt`

**Fluxo com cache**:
```
raw_token extraído do header
  ↓
key = RedisClient.jwt_key(raw_token)
cached = RedisClient.get_json(key)
  ↓ HIT
validate expires_at_ts e revoked em memória → rejeita 401 sem banco
request.jwt_token = Token.browse(cached['id'])  ← lazy ORM, zero SELECT
env.cache.set(token_record, Token._fields['scope'], cached['scope'])
env.cache.set(token_record, Token._fields['expires_at'], ...)
env.cache.set(token_record, Token._fields['revoked'], False)
env.cache.set(token_record, Token._fields['application_id'], cached['application_id'])
log INFO cache hit
  ↓ MISS
Token.search([('access_token', '=', token)], limit=1)  ← banco como hoje
validações existentes (token_type, expires_at, revoked)
ttl = max(0, int(token_record.expires_at.timestamp() - time.time()))
if ttl > 0:
    RedisClient.set_json(key, payload, ttl)
log WARNING cache miss
```

**Payload JWT**:
```python
{
    "id": int,
    "application_id": int,
    "token_type": str,
    "expires_at_ts": float,   # Unix timestamp para validação in-memory
    "scope": str,
    "revoked": bool
}
```

---

### 1.3 — Session Cache em `SessionValidator.validate()`

**Arquivo**: `thedevkitchen_apigateway/services/session_validator.py`

**Fluxo com cache**:
```
session_id recebido
  ↓
settings = SecuritySettings.get_settings()
ttl = settings.session_cache_ttl_seconds  ← lido do backoffice
key = RedisClient.session_key(session_id)
cached = RedisClient.get_json(key)
  ↓ HIT
if not cached['is_active'] → return False, None, None, 'Invalid or expired session'
if not cached['user_active'] → return False, None, None, 'User inactive'
api_session = APISession.browse(cached['id'])
# Odoo 18 field cache injection (zero SELECT)
env.cache.set(api_session, APISession._fields['security_token'], cached['security_token'])
env.cache.set(api_session, APISession._fields['is_active'], True)
env.cache.set(api_session, APISession._fields['company_id'], cached['company_id'])
user = Users.browse(cached['user_id'])
env.cache.set(user, Users._fields['active'], True)
# SKIP last_activity UPDATE (trade-off aceito)
log INFO cache hit session:{session_id[:10]}
return True, user, api_session, None
  ↓ MISS
# fluxo existente: search, write last_activity, check user.active
# após validação bem-sucedida:
if ttl > 0:
    RedisClient.set_json(key, payload, ttl)
log WARNING cache miss
```

**Payload Session**:
```python
{
    "id": int,
    "user_id": int,
    "is_active": bool,
    "security_token": str,    # JWT de fingerprint — obrigatório para require_session
    "company_id": int,
    "user_active": bool
}
```

---

### 1.4 — Invalidação via `APISession.write()` Override

**Arquivo**: `thedevkitchen_apigateway/models/api_session.py`

```python
def write(self, vals):
    result = super().write(vals)
    if 'is_active' in vals or 'company_id' in vals:
        try:
            from ..services.redis_client import RedisClient
            for record in self:
                key = RedisClient.session_key(record.session_id)
                RedisClient.delete(key)
                _logger.info(f"[CACHE] session invalidated: {record.session_id[:10]}...")
        except Exception:
            pass  # Nunca bloquear o write
    return result
```

**Cobertura**: logout, login (sessões antigas), switch-company, cleanup cron, user deactivation, password reset — todos sem modificar os call sites.

---

### 1.5 — Invalidação via `OAuthToken.action_revoke()` Override

**Arquivo**: `thedevkitchen_apigateway/models/oauth_token.py`

```python
def action_revoke(self):
    result = super().action_revoke()
    try:
        import hashlib
        from ..services.redis_client import RedisClient
        for record in self:
            key = RedisClient.jwt_key(record.access_token)
            RedisClient.delete(key)
            _logger.info(f"[CACHE] JWT invalidated for token id={record.id}")
    except Exception:
        pass
    return result
```

---

### 1.6 — Invalidação Proativa em `profile_api.py` (Gap Corrigido)

**Arquivo**: `quicksol_estate/controllers/profile_api.py` — endpoint `DELETE /api/v1/profiles/:id`

Após `user_record.write({'active': False})`, adicionar:
```python
# Invalidar sessões ativas do usuário (proativo — evita janela TTL com cache)
from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
active_sessions = request.env['thedevkitchen.api.session'].sudo().search([
    ('user_id', '=', user_record.id),
    ('is_active', '=', True),
])
for sess in active_sessions:
    sess.write({'is_active': False})  # dispara o write() override automaticamente
```

**Nota**: O `write()` override do `APISession` já cuida do Redis delete — não há chamada direta ao RedisClient aqui, mantendo responsabilidade única.

---

### 1.7 — Invalidação ao Mudar Profile Type (Odoo UI)

**Arquivo**: `quicksol_estate/models/profile.py` — override `write()`

```python
def write(self, vals):
    # Detectar mudança de profile_type ANTES do super() para capturar valor antigo
    profile_type_changed = 'profile_type_id' in vals
    result = super().write(vals)
    if profile_type_changed and self.partner_id:
        try:
            User = self.env['res.users'].sudo()
            users = User.search([('partner_id', '=', self.partner_id.id)])
            for user in users:
                sessions = self.env['thedevkitchen.api.session'].sudo().search([
                    ('user_id', '=', user.id),
                    ('is_active', '=', True),
                ])
                for sess in sessions:
                    sess.write({'is_active': False})  # write() override invalida Redis
        except Exception:
            pass
    return result
```

---

### 1.8 — PerformanceService: Stubs → Real Redis

**Arquivo**: `quicksol_estate/services/performance_service.py`

```python
def __init__(self, env):
    self.env = env
    # TTL lido das settings configuráveis
    settings = env['thedevkitchen.security.settings'].sudo().search([], limit=1)
    self.cache_ttl = settings.performance_cache_ttl_seconds if settings else 300

def _get_cached_performance(self, cache_key):
    from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
    cached = RedisClient.get_json(cache_key)
    if cached:
        _logger.info(f"[CACHE] performance HIT key={cache_key}")
    else:
        _logger.warning(f"[CACHE] performance MISS key={cache_key}")
    return cached

def _cache_performance(self, cache_key, performance_data):
    from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
    RedisClient.set_json(cache_key, performance_data, self.cache_ttl)
    _logger.info(f"[CACHE] performance SET key={cache_key} ttl={self.cache_ttl}")

def invalidate_cache(self, agent_id):
    from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
    pattern = f"performance:agent:{agent_id}:*"
    count = RedisClient.delete_pattern(pattern)
    _logger.info(f"[CACHE] performance INVALIDATED agent={agent_id} keys_deleted={count}")
```

---

### 1.9 — `CommissionTransaction.create()` Override (Trigger de Invalidação)

**Arquivo**: `quicksol_estate/models/commission_transaction.py`

```python
@api.model
def create(self, vals):
    record = super().create(vals)
    # Invalidar cache de métricas do agente ao criar transação
    if record.agent_id:
        try:
            from ...thedevkitchen_apigateway.services.redis_client import RedisClient
            pattern = RedisClient.performance_key(record.agent_id.id, '*', '*')
            RedisClient.delete_pattern(f"performance:agent:{record.agent_id.id}:*")
            _logger.info(f"[CACHE] performance invalidated on transaction create agent={record.agent_id.id}")
        except Exception:
            pass
    return record
```

---

### 1.10 — SecuritySettings: Novos Campos

**Arquivo**: `thedevkitchen_apigateway/models/security_settings.py`

```python
session_cache_ttl_seconds = fields.Integer(
    string='Session Cache TTL (segundos)',
    default=300,
    help='Tempo de validade do cache Redis para sessões. 0 = desabilitado.'
)
session_inactivity_days = fields.Integer(
    string='Inatividade de Sessão (dias)',
    default=7,
    help='Após quantos dias sem atividade o cron marca a sessão como inativa.'
)
performance_cache_ttl_seconds = fields.Integer(
    string='Performance Cache TTL (segundos)',
    default=300,
    help='Tempo de validade do cache Redis para métricas de corretores. 0 = desabilitado.'
)
```

**Arquivo**: `thedevkitchen_apigateway/views/security_settings_views.xml` — adicionar grupo:
```xml
<group string="Cache &amp; Session Configuration">
    <field name="session_cache_ttl_seconds"
           help="0 = cache de sessão desabilitado (sempre usa banco)"/>
    <field name="session_inactivity_days"/>
    <field name="performance_cache_ttl_seconds"
           help="0 = cache de métricas desabilitado"/>
</group>
```

**`SessionValidator.cleanup_expired()`** — usar `session_inactivity_days` de settings:
```python
settings = env['thedevkitchen.security.settings'].sudo().search([], limit=1)
days = settings.session_inactivity_days if settings else 7
cutoff = datetime.now() - timedelta(days=days)
```

---

## Phase 1: Test Strategy

### Arquitetura de QA — Toggle de Cache por Tipo

A estratégia de teste é baseada na premissa de um QA experiente que precisa:
1. **Testar o comportamento SEM cache** (banco puro) → TTL = 0 nas settings
2. **Testar o comportamento COM cache** → TTL > 0, Redis populado
3. **Testar fallback** → Redis mockado para retornar erro
4. **Testar invalidação** → verificar que chave foi deletada do Redis após operação

**Mecanismo de toggle**: `SecuritySettings.session_cache_ttl_seconds = 0` desabilita o cache de sessão. O `RedisClient.set_json()` recusa TTL ≤ 0, então nenhuma entrada é criada e cada requisição vai ao banco. Sem alteração de código — só configuração.

---

### Matriz de Testes

#### T01 — Unit: RedisClient métodos isolados (sem Odoo)
**Arquivo**: `tests/unit/test_redis_cache_unit.py`  
**Framework**: `unittest` + `unittest.mock`

| Cenário | Mock | Assertiva |
|---|---|---|
| `get_json` com Redis UP e chave existe | `redis.Redis.get` → JSON bytes | Retorna dict desserializado |
| `get_json` com Redis DOWN | `_get_connection` → `None` | Retorna `None`, sem exceção |
| `get_json` com JSON corrompido | `redis.Redis.get` → `b"invalid"` | Retorna `None`, loga WARNING |
| `set_json` com TTL = 0 | sem mock necessário | Retorna `False`, nenhum `setex` chamado |
| `set_json` com Redis DOWN | `_get_connection` → `None` | Retorna `False`, sem exceção |
| `delete` com múltiplas keys | `redis.Redis.delete` | Chamado uma vez com todas as keys |
| `delete_pattern` sem matches | `redis.Redis.scan` → `(0, [])` | Retorna 0, sem `delete` |
| `jwt_key` — hash correto | sem mock | SHA-256[:32] do token |

#### T02 — Unit: `require_jwt` com cache HIT
**Arquivo**: `tests/unit/test_redis_cache_unit.py`

| Cenário | Setup | Assertiva |
|---|---|---|
| Token válido — HIT | `get_json` retorna payload JWT válido | `Token.search` NOT called; `request.jwt_token.id` correto |
| Token revogado — HIT | `get_json` retorna `{"revoked": true, ...}` | 401 sem chamar banco |
| Token expirado — HIT | `get_json` retorna `expires_at_ts` < `time.time()` | 401 sem chamar banco |
| Cache corrompido — fallback | `get_json` retorna `None` (JSON inválido) | `Token.search` chamado (MISS path) |
| Cache DOWN — fallback | `get_json` → `None` | `Token.search` chamado; requisição processada normalmente |

#### T03 — Unit: `SessionValidator.validate()` com cache HIT/MISS
**Arquivo**: `tests/unit/test_redis_cache_unit.py`

| Cenário | Setup | Assertiva |
|---|---|---|
| Sessão válida — HIT | `get_json` retorna payload session válido | `APISession.search` NOT called; `last_activity` NOT updated |
| Sessão inativa — HIT | `get_json` retorna `{"is_active": false, ...}` | 401 sem banco |
| Usuário inativo — HIT | `get_json` retorna `{"user_active": false, ...}` | 401 `User inactive` sem banco |
| **Cache MISS — modo banco puro** | `session_cache_ttl_seconds = 0` nas settings mockadas | `APISession.search` chamado; `last_activity` atualizado; cache NÃO populado |
| Cache DOWN — fallback | `get_json` → exception mockada | `APISession.search` chamado; requisição OK |

**Como desabilitar o cache de sessão nos testes**:
```python
def setUp(self):
    super().setUp()
    # Configurar settings com TTL=0 para testar sem cache
    self.settings = self.env['thedevkitchen.security.settings'].get_settings()
    self.settings.write({'session_cache_ttl_seconds': 0})
```

#### T04 — Unit: Invalidação JWT via `action_revoke()`
**Arquivo**: `tests/unit/test_redis_cache_unit.py`

| Cenário | Assertiva |
|---|---|
| Revogar token → cache deletado | `RedisClient.delete(jwt_key)` chamado uma vez |
| Redis DOWN durante revoke | `action_revoke()` conclui normalmente; sem exceção |

#### T05 — Unit: Invalidação Session via `APISession.write()`
**Arquivo**: `tests/unit/test_redis_cache_unit.py`

| Cenário | Assertiva |
|---|---|
| `write({'is_active': False})` → cache deletado | `RedisClient.delete(session_key)` chamado |
| `write({'company_id': X})` → cache deletado | `RedisClient.delete(session_key)` chamado |
| `write({'last_activity': ...})` → cache preservado | `RedisClient.delete` NOT called |
| Redis DOWN durante write | `write()` conclui normalmente; sem exceção |

#### T06 — Unit: Invalidação Profile → Sessions
**Arquivo**: `tests/unit/test_redis_cache_unit.py`

| Cenário | Assertiva |
|---|---|
| `profile.write({'profile_type_id': X})` com sessões ativas | `APISession.write({'is_active': False})` chamado; Redis keys deletadas |
| Profile sem partner_id | Nenhuma busca de sessão; sem erro |

#### T07 — Unit: PerformanceService cache real (sem stubs)
**Arquivo**: `quicksol_estate/tests/unit/test_performance_cache_unit.py`

| Cenário | Setup | Assertiva |
|---|---|---|
| Primeira chamada — MISS | `get_json` → `None` | Métricas calculadas; `set_json` chamado |
| Segunda chamada — HIT | `get_json` → payload válido | `_calculate_performance_metrics` NOT called |
| **Performance cache desabilitado** | `performance_cache_ttl_seconds = 0` | `set_json` NOT called; cálculo sempre executado |
| Nova transação → invalidação | `CommissionTransaction.create()` | `delete_pattern(f"performance:agent:{id}:*")` chamado |

#### T08 — Integration (Odoo TransactionCase): Fluxo completo com Redis real
**Arquivo**: `tests/integration/test_redis_cache_integration.py`

**Prerequisite**: Redis disponível no ambiente de teste (`enable_redis=True` no odoo.conf de test).

| Cenário | Setup | Assertiva |
|---|---|---|
| Login → 1ª req → cache populado | TTL > 0 | Chave `session:*` existe no Redis após 1ª req |
| 2ª req mesma sessão — HIT | Chave no Redis | `log INFO cache hit` presente; sem SELECT em `thedevkitchen_api_session` |
| Logout → cache invalidado | Logout via API | Chave `session:*` NÃO existe no Redis após logout |
| Revoke token → cache invalidado | `action_revoke()` | Chave `jwt:*` NÃO existe no Redis |
| **Teste modo banco puro (session TTL = 0)** | `session_cache_ttl_seconds = 0` via settings | Chave session NUNCA criada; requisições funcionam normalmente via banco |
| **Teste modo banco puro (performance TTL = 0)** | `performance_cache_ttl_seconds = 0` via settings | Cache de métricas nunca criado; cálculo sempre feito |
| Redis indisponível | `enable_redis=False` no conf | Todas as requisições autenticadas processadas via banco; zero 500s |

**Padrão de setup para testar com/sem cache**:
```python
class TestWithCache(TransactionCase):
    def setUp(self):
        super().setUp()
        self.settings = self.env['thedevkitchen.security.settings'].get_settings()
        self.settings.write({'session_cache_ttl_seconds': 300})  # CACHE ON

class TestWithoutCache(TransactionCase):
    def setUp(self):
        super().setUp()
        self.settings = self.env['thedevkitchen.security.settings'].get_settings()
        self.settings.write({'session_cache_ttl_seconds': 0})   # CACHE OFF — banco puro
```

#### T09 — Integration E2E (bash): Cenários API com Redis flush
**Arquivo**: `integration_tests/test_us023_redis_cache.sh`

```bash
# Helper: flush somente keys desta feature
flush_cache() {
    docker compose exec redis redis-cli -n 1 KEYS "session:*" | xargs -r docker compose exec redis redis-cli -n 1 DEL
    docker compose exec redis redis-cli -n 1 KEYS "jwt:*" | xargs -r docker compose exec redis redis-cli -n 1 DEL
}

# Verificar se chave existe no Redis
key_exists() {
    local key=$1
    docker compose exec redis redis-cli -n 1 EXISTS "$key"
}
```

| Cenário | Passos | Assertiva |
|---|---|---|
| S01: Cache populado após login + 1ª req | flush → login → GET /api/v1/me | Chave `session:*` existe no Redis |
| S02: Logout invalida cache | Login → GET /me → POST /logout | Chave `session:*` removida; nova req com mesma sessão → 401 |
| S03: Revoke invalida JWT cache | flush → req (popula JWT) → POST /revoke | Chave `jwt:*` removida; req com mesmo token → 401 |
| S04: switch-company invalida session cache | Login → troca empresa → GET /me | Chave antiga removida; nova GET popula nova chave |
| S05: Profile delete invalida sessions proativamente | Login → DELETE /profiles/:id | Sessões ativas → 401 sem aguardar TTL |
| S06: Cache fallback — Redis indisponível | Parar container Redis → req autenticada | HTTP 200 (fallback banco); sem 500 |
| S07: Performance cache — HIT na 2ª chamada | GET /performance (1ª) → GET /performance (2ª) | Logs mostram "performance HIT"; resposta idêntica |
| S08: Performance cache — invalidado ao criar transação | GET /performance → POST /transactions → GET /performance | Log "performance INVALIDATED" após POST; 3ª GET recalcula |

#### T10 — Odoo UI: Validação dos settings no backoffice
**Manual / Odoo TransactionCase**

| Cenário | Assertiva |
|---|---|
| Acessar Technical → API Gateway → Security Settings | Campos `session_cache_ttl_seconds`, `session_inactivity_days`, `performance_cache_ttl_seconds` visíveis |
| Alterar `session_cache_ttl_seconds` para 60 | Próximas sessões cacheadas com TTL = 60s |
| Alterar para 0 | Cache de sessão desabilitado — verificável via logs e ausência de chaves no Redis |

---

## Deployment Order (MANDATORY)

```
Step 1: Deploy invalidation hooks (sem ativar population)
   → APISession.write() override
   → OAuthToken.action_revoke() override
   → Profile.write() override (profile_type_id change)
   → profile_api.py proactive session invalidation
   → CommissionTransaction.create() override

Step 2: Smoke test — operações de escrita não geram erros, logs mostram "[CACHE] ... invalidated"

Step 3: Deploy population hooks (ativa cache de fato)
   → require_jwt: HIT path + set_json no MISS
   → SessionValidator.validate(): HIT path + set_json no MISS
   → PerformanceService: stubs → real Redis

Step 4: Deploy SecuritySettings fields + view
   → Permite configurar TTL via backoffice sem redeploy

Step 5: Smoke test — verificar Redis keys criadas após requisições autenticadas
```

**Rationale**: Se Step 3 for deployado antes de Step 1, um logout logo após o deploy não limpa o cache recém-criado, criando janela de sessão stale. A ordem inversa é safe porque invalidar uma chave inexistente é no-op.

---

## Trade-offs Documentados

| Trade-off | Decisão | Rationale |
|---|---|---|
| `last_activity` desatualizado em cache hits | Aceito | Campo de métrica de uso, não controle de segurança |
| TTL de sessão configurável (não derivado de evento) | Aceito | Sessões não têm `expires_at` intrínseco; TTL = 0 desabilita limpo |
| JWT TTL = `expires_at` sem cap | Aceito | JWT já define seu ciclo de vida; cap artificial causaria re-reads desnecessários |
| Invalidação de sessão ao desativar perfil é proativa (não via `res.users.write` override) | Aceito | `res.users` é do core Odoo; override teria escopo muito amplo e risco de regressão |
| `profile_type_id` imutável via API, mutável via Odoo UI | Aceito | Feature cobre o caso UI com override em `Profile.write()` |
| `change-password` não invalida sessões (gap pré-existente) | Out of scope | Gap existe hoje sem cache; não é introduzido por esta feature |

