# Data Model: Redis Cache para Sessão e JWT

**Feature**: 023-redis-session-cache  
**Date**: 2026-06-08

---

## Entidades Existentes Modificadas

### `thedevkitchen.security.settings` — Novos Campos

**Arquivo**: `thedevkitchen_apigateway/models/security_settings.py`

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `session_cache_ttl_seconds` | Integer | 300 | TTL do cache Redis para sessões (segundos). 0 = desabilitado |
| `session_inactivity_days` | Integer | 7 | Dias sem atividade após os quais o cron marca a sessão como inativa |
| `performance_cache_ttl_seconds` | Integer | 300 | TTL do cache Redis para métricas de corretores. 0 = desabilitado |

**Validações**:
- `session_cache_ttl_seconds` ≥ 0 (0 = cache desabilitado para tipo sessão)
- `session_inactivity_days` ≥ 1
- `performance_cache_ttl_seconds` ≥ 0 (0 = cache desabilitado para tipo performance)

---

### `thedevkitchen.api.session` — Novo Override de `write()`

Sem novos campos. Override de `write()` adicionado para disparar invalidação do cache Redis quando `is_active` ou `company_id` mudam.

---

### `thedevkitchen.oauth.token` — Novo Override de `action_revoke()`

Sem novos campos. Override de `action_revoke()` adicionado para deletar a entrada de cache JWT correspondente.

---

### `real.estate.commission_transaction` — Novo Override de `create()`

Sem novos campos. Override de `create()` adicionado para invalidar o cache de métricas do agente vinculado à transação.

---

## Novo Serviço: RedisClient

**Arquivo**: `thedevkitchen_apigateway/services/redis_client.py`  
**Tipo**: Classe Python (não modelo ORM — sem tabela de banco)

### Responsabilidades
- Singleton de conexão Redis via `ConnectionPool`
- Métodos de I/O sem propagação de exceção (`get_json`, `set_json`, `delete`, `delete_pattern`)
- Helpers de geração de chaves (`jwt_key`, `session_key`, `performance_key`)

### Contratos de Chaves Redis (Redis DB index 1)

| Tipo | Padrão de Chave | TTL | Conteúdo |
|---|---|---|---|
| JWT | `jwt:{sha256(raw_token)[:32]}` | `expires_at - now()` | `{id, application_id, token_type, expires_at_ts, scope, revoked}` |
| Session | `session:{session_id}` | `session_cache_ttl_seconds` (backoffice) | `{id, user_id, is_active, security_token, company_id, user_active}` |
| Performance | `performance:agent:{id}:{date_from}:{date_to}` | `performance_cache_ttl_seconds` (backoffice) | payload completo de métricas |

---

## Diagrama de Fluxo de Dados

```
HTTP Request (autenticada)
        │
        ▼
require_jwt
  ├─ Redis GET jwt:{hash}
  │    ├─ HIT → validate in-memory → Token.browse(id) + env.cache.set()
  │    └─ MISS → Token.search() → Redis SET jwt:{hash} ttl=expires_at-now()
        │
        ▼
require_session (via SessionValidator.validate)
  ├─ Redis GET session:{session_id}
  │    ├─ HIT → validate in-memory → APISession.browse(id) + env.cache.set()
  │    │         skip last_activity UPDATE
  │    └─ MISS → APISession.search() → UPDATE last_activity → Redis SET session:{id} ttl=TTL_settings
        │
        ▼
[lógica de negócio]
```

```
Evento de Mutação
        │
        ├─ logout / switch-company / login (old sessions)
        │    → APISession.write({'is_active': False / 'company_id': X})
        │         → write() override → RedisClient.delete(session:{id})
        │
        ├─ token revoke
        │    → OAuthToken.action_revoke()
        │         → action_revoke() override → RedisClient.delete(jwt:{hash})
        │
        ├─ profile delete (API)
        │    → profile_api.py → sessions.write({'is_active': False})
        │         → write() override → RedisClient.delete(session:{id})
        │
        ├─ profile type change (Odoo UI)
        │    → Profile.write({'profile_type_id': X})
        │         → Profile.write() override → sessions.write({'is_active': False})
        │              → APISession.write() override → RedisClient.delete(session:{id})
        │
        └─ nova transação de comissão
             → CommissionTransaction.create()
                  → create() override → RedisClient.delete_pattern(performance:agent:{id}:*)
```
