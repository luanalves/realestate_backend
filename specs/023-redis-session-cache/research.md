# Research: Redis Cache para Sessão e JWT

**Feature**: 023-redis-session-cache  
**Date**: 2026-06-08  
**Status**: Complete

---

## R1: Ponto exato de integração no `require_jwt`

**Decision**: Integrar antes do `Token.search()` existente, na linha ~28 do `middleware.py`.

**Findings**:
- `require_jwt` extrai o token bruto do header `Authorization: Bearer <token>`
- Faz `Token.search([('access_token', '=', token)], limit=1)` — 1 SELECT a cada requisição
- Após validação: seta `request.jwt_token = token_record` e `request.jwt_application = token_record.application_id`
- **Contrato imutável**: `request.jwt_token` deve ser um ORM record com campos `.id`, `.scope`, `.expires_at`, `.revoked`, `.application_id`

**Cache strategy**:
- Key: `jwt:{sha256(raw_token).hexdigest()[:32]}` (nunca raw token como key)
- Payload: `{"id": int, "application_id": int, "token_type": str, "expires_at_ts": float, "scope": str, "revoked": bool}`
- On HIT: `Token.browse(id)` (lazy, zero SELECT) + `env.cache.set()` para campos críticos
- TTL: `max(0, int(expires_at.timestamp() - time.time()))` — usa `expires_at` do próprio token

---

## R2: Ponto exato de integração no `require_session`

**Decision**: Integrar no `SessionValidator.validate()` (services/session_validator.py), não no decorator diretamente.

**Findings**:
- `require_session` chama `SessionValidator.validate(session_id)` na linha ~185 do `middleware.py`
- `SessionValidator.validate()` faz: (1) `APISession.search(...)` SELECT, (2) `api_session.write({'last_activity': now()})` UPDATE, (3) `user.active` acesso ORM
- Após validação, o decorator lê `api_session.security_token` para o `jwt.decode()` de fingerprint — **este campo deve estar no payload de cache**
- `request.api_session` deve ser ORM record com: `.security_token`, `.is_active`, `.company_id`, `.session_id`, `.user_id`, `.write()`

**Cache strategy**:
- Key: `session:{session_id}`
- Payload: `{"id": int, "user_id": int, "is_active": bool, "security_token": str, "company_id": int, "user_active": bool}`
- On HIT: `APISession.browse(id)` + `env.cache.set()` para todos os campos do payload (Odoo 18 field cache injection)
- `last_activity` update: **skipped** on HIT (trade-off aceito)
- TTL: lido de `thedevkitchen.security.settings.session_cache_ttl_seconds` (padrão 300s)

---

## R3: Odoo 18 Field Cache Injection

**Decision**: Usar `env.cache.set(record, field_obj, value)` para pre-popular o ORM field cache em registros `browse()`.

**Findings**:
- `env.cache` é o cache ORM do Odoo 18 — dicionário in-process por requisição
- `APISession._fields['security_token']` retorna o objeto de campo para usar com `env.cache.set()`
- Campos injetados: `security_token`, `is_active`, `company_id` no record de sessão; `active` no record de usuário
- **Sem este mecanismo**: `api_session.security_token` dispararia SELECT mesmo após `browse(id)`

**Implementation**:
```python
env.cache.set(api_session, APISession._fields['security_token'], cached['security_token'])
env.cache.set(api_session, APISession._fields['is_active'], True)
env.cache.set(api_session, APISession._fields['company_id'], cached['company_id'])
env.cache.set(user_record, Users._fields['active'], True)
```

---

## R4: Estratégia de Invalidação — Análise de Todos os Write Points

**Decision**: Invalidação via override de `write()` em `APISession` e `action_revoke()` em `OAuthToken`, mais invalidação proativa em `profile_api.py`.

**Write points mapeados na base de código**:

| Localização | Código | Cache afetado | Cobertura |
|---|---|---|---|
| `user_auth_controller.py:199` | `api_session.write({'is_active': False})` | session | ✅ via write() override |
| `user_auth_controller.py:105` | loop `old_session.write({'is_active': False})` | session | ✅ via write() override |
| `user_auth_controller.py:427` | `api_session.write({'company_id': X})` | session | ✅ via write() override |
| `session_validator.py:35` | `api_session.write({'is_active': False})` | session | ✅ via write() override |
| `session_validator.py:58` | `expired.write({'is_active': False})` lote | session | ✅ via write() override |
| `auth_controller.py:~143` | `token_record.action_revoke()` | jwt | ✅ via action_revoke() override |
| `password_service.py:201` | `sessions.write({'is_active': False})` lote | session | ✅ via write() override |
| `profile_api.py:600-611` | `user_record.write({'active': False})` | session | ⚠️ NÃO cobre sessões — requer invalidação proativa explícita |

**Gap confirmado em `profile_api.py`**: O endpoint `DELETE /api/v1/profiles/:id` desativa `res.users` mas não toca `thedevkitchen.api.session`. Com cache, a janela de inconsistência seria o TTL completo. **Solução**: Adicionar chamada explícita a `_invalidate_user_sessions(user_id)` + `RedisClient.delete_pattern(f"session:{session_id}")` para cada sessão ativa do usuário no endpoint de deleção de perfil.

**Gap de segurança pré-existente (fora do escopo)**: `change-password` no `user_auth_controller.py` faz `user.write({'password': new_password})` sem invalidar sessões. Não é introduzido por esta feature, não será corrigido aqui.

---

## R5: Perfil — Invalidação de Sessão ao Mudar Profile Type

**Decision**: Override do método `write()` em `Profile` model (`quicksol_estate/models/profile.py`) quando `profile_type_id` muda.

**Findings**:
- `profile.write()` já tem override para timestamp `updated_at` — pode ser estendido
- `profile_type_id` é campo imutável via API mas editável via Odoo UI
- A ligação perfil → usuário é via `profile.partner_id` → `res.users.partner_id`
- **Flow de invalidação**: Quando `profile_type_id` muda → buscar `res.users` com `partner_id == profile.partner_id.id` → buscar `thedevkitchen.api.session` com `user_id` ativo → `RedisClient.delete(f"session:{s.session_id}")` para cada sessão

---

## R6: PerformanceService — Stubs vs Real Redis

**Decision**: Substituir os 3 stubs (`_get_cached_performance`, `_cache_performance`, `invalidate_cache`) por implementação real usando o `RedisClient` singleton.

**Findings**:
- `cache_ttl = 300` já definido em `__init__` — substituir por leitura de `security_settings.performance_cache_ttl_seconds`
- Cache key já definido: `f"performance:agent:{agent_id}:{date_from}:{date_to}"`
- `invalidate_cache(agent_id)` deve usar `RedisClient.delete_pattern(f"performance:agent:{agent_id}:*")`
- **Trigger de invalidação**: `real.estate.commission_transaction.create()` via observer ou override de `create()` no model `CommissionTransaction`

---

## R7: `SecuritySettings` — Campos Novos

**Decision**: Adicionar 3 campos ao modelo existente `thedevkitchen.security.settings` (não criar novo modelo).

**Fields**:
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

**TTL = 0 como mecanismo de desabilitar**: Se TTL = 0, `set_json` recusa a escrita (contrato do RedisClient) e a feature funciona em modo 100% banco. Isso é o mecanismo de toggle por tipo de cache para testes.

---

## R8: Estratégia de Testes — QA com Toggle de Cache por Tipo

**Decision**: Usar TTL = 0 via `SecuritySettings` como toggle limpo para desabilitar cada tipo de cache em testes. Complementado por mocks no nível de `RedisClient` para testes unitários.

**Findings**:
- `set_json(key, data, ttl)` com `ttl <= 0` já é rejeitado pelo contrato do `RedisClient`
- Configurar `session_cache_ttl_seconds = 0` → cache de sessão desabilitado, banco usado para tudo
- Configurar `performance_cache_ttl_seconds = 0` → cache de métricas desabilitado
- JWT TTL = 0 quando `expires_at <= now()` → token expirado, não é cacheado (comportamento natural)

**Camadas de teste**:
1. **Unit (mock Redis)**: `patch('...RedisClient.get_json', return_value=None)` para forçar MISS; `patch(..., return_value={...})` para forçar HIT
2. **Odoo integration (TransactionCase)**: Criar settings com TTL = 0 em `setUp()` para testar fluxo sem cache; TTL > 0 para testar com cache
3. **API integration (bash/HTTP)**: Flush Redis antes de cada cenário (`redis-cli FLUSHDB`); testar cenários com e sem dados em cache

---

## R9: Ordem de Deploy (MANDATORY)

**Decision**: Invalidation hooks devem ser ativadas **antes** das population hooks.

**Rationale**: Se as hooks de população rodarem sem as de invalidação, um logout imediatamente após o deploy não limparia o cache recém-criado, criando janela de dados stale. Deployar hooks de invalidação primeiro é sem-op (nada para deletar ainda).

**Order**:
1. Deploy `APISession.write()` override (invalidation)
2. Deploy `OAuthToken.action_revoke()` override (invalidation)
3. Deploy `Profile.write()` override (invalidation)
4. Deploy `profile_api.py` proactive invalidation (invalidation)
5. ONLY THEN: Deploy `require_jwt` + `require_session` cache HIT paths (population)
6. Deploy `PerformanceService` real cache (population + invalidation simultâneos — ok pois invalidação é separada)
