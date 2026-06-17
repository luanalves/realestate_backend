# Tasks: Redis Cache para Sessão e JWT

**Feature Branch**: `023-redis-session-cache`
**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md)
**Módulos afetados**: `thedevkitchen_apigateway`, `quicksol_estate`
**Date**: 2026-06-08

---

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Task pode rodar em paralelo (arquivos diferentes, sem dependências com tasks incompletas)
- **[Story]**: US1, US2, US3 — mapeia para user stories do spec.md (fases US1+ obrigatório)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Criar o `RedisClient` singleton e torná-lo importável no módulo `thedevkitchen_apigateway`. Nenhuma fase pode iniciar antes desta.

- [X] T001 Create `RedisClient` singleton class with methods `get_json`, `set_json`, `delete`, `delete_pattern`, `is_available` (all swallow exceptions), and key helpers `jwt_key`, `session_key`, `performance_key` in `18.0/extra-addons/thedevkitchen_apigateway/services/redis_client.py`
- [X] T002 Update `18.0/extra-addons/thedevkitchen_apigateway/services/__init__.py` to import `redis_client` module

**Checkpoint**: `from ..services.redis_client import RedisClient` importável sem erros no Odoo; `RedisClient.is_available()` retorna `True` com Redis rodando no Docker.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Campos de configuração de TTL no backoffice e testes unitários do `RedisClient` puro. Necessários para **todas** as user stories (TTL lido nas operações de população de cache).

**⚠️ CRITICAL**: Nenhuma user story pode ser implementada antes desta fase estar completa.

- [X] T003 [P] Add fields `session_cache_ttl_seconds` (Integer, default 300), `performance_cache_ttl_seconds` (Integer, default 300), `session_inactivity_days` (Integer, default 7) to `18.0/extra-addons/thedevkitchen_apigateway/models/security_settings.py`
- [X] T004 [P] Add `<group string="Cache &amp; Session Configuration">` with the 3 new fields to `18.0/extra-addons/thedevkitchen_apigateway/views/security_settings_views.xml`
- [X] T005 [P] Write unit tests T01 (`RedisClient` isolated: `get_json` HIT, MISS, JSON-corrupt→None, `set_json` TTL=0→False no-op, Redis DOWN→False, `delete` multi-key, `delete_pattern` no-match→0, `jwt_key` SHA-256 correctness) in `18.0/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py`
- [X] T010 [P] Update `cleanup_expired()` to read `session_inactivity_days` from `SecuritySettings.get_settings()` replacing hardcoded `days=7` in `18.0/extra-addons/thedevkitchen_apigateway/services/session_validator.py`

**Checkpoint**: SecuritySettings com 3 novos campos visíveis no backoffice após `odoo -u thedevkitchen_apigateway`; `cleanup_expired()` lê `session_inactivity_days` de settings; testes T01 passam.

---

## Phase 3: User Story 1 — Cache elimina consultas ao banco em requisições autenticadas (Priority: P1)

**Goal**: Toda requisição com token + sessão já vistos anteriormente é processada sem consultar `thedevkitchen_oauth_token` ou `thedevkitchen_api_session` no banco.

**Independent Test**: Login → 1ª requisição autenticada (logs mostram MISS + Redis populado) → 2ª requisição com mesmo token/sessão (logs mostram HIT, nenhum SELECT em tabelas de auth).

### Tests for User Story 1 ⚠️ Write FIRST — must FAIL before implementation

- [X] T006 [P] [US1] Write unit tests T02 (`require_jwt` with cache: HIT payload válido → `Token.search` NOT called; HIT `revoked=True` → 401 sem banco; HIT `expires_at_ts` expirado → 401 sem banco; HIT JSON corrompido → fallback `Token.search`; Redis DOWN → fallback `Token.search` + req OK) in `18.0/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py`
- [X] T007 [P] [US1] Write unit tests T03 (`SessionValidator.validate` with cache: HIT sessão válida → `APISession.search` NOT called + `last_activity` NOT updated; HIT `is_active=False` → 401; HIT `user_active=False` → 401 `User inactive`; `session_cache_ttl_seconds=0` → `set_json` NOT called; Redis DOWN → `APISession.search` chamado + req OK; `get_json` retorna `None` por JSON corrompido → `APISession.search` chamado (MISS path)) in `18.0/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement JWT cache HIT path in `require_jwt` before `Token.search()`: `get_json(jwt_key(token))` → validate `expires_at_ts`+`revoked` in-memory → `Token.browse(id)` + `env.cache.set()` for `scope`, `expires_at`, `revoked`, `application_id`; MISS path: after existing validations, `set_json(key, payload, ttl=max(0,expires_at-now()))` in `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`
- [X] T009 [US1] Implement Session cache HIT path in `SessionValidator.validate()` before `APISession.search()`: `get_json(session_key(session_id))` → validate `is_active`+`user_active` in-memory → `APISession.browse(id)` + `env.cache.set()` for `security_token`, `is_active`, `company_id`; MISS path: after existing validations, `set_json(key, payload, ttl=session_cache_ttl_seconds)` from settings; skip `last_activity` UPDATE on HIT in `18.0/extra-addons/thedevkitchen_apigateway/services/session_validator.py`
- [X] T011 [US1] Write integration tests T08-partial (full auth flow: login → req1 MISS key populated in Redis → req2 HIT key exists; `session_cache_ttl_seconds=0` → keys never created in Redis) in `18.0/extra-addons/thedevkitchen_apigateway/tests/integration/test_redis_cache_integration.py`

**Checkpoint**: Segunda requisição autenticada com mesmo token/sessão não gera `SELECT` em `thedevkitchen_oauth_token` ou `thedevkitchen_api_session`; logs mostram `[CACHE] jwt HIT` e `[CACHE] session HIT`.

---

## Phase 4: User Story 2 — Invalidação imediata ao mutar estado de segurança (Priority: P1)

**Goal**: Logout, revogação de token, troca de empresa, desativação de perfil e mudança de tipo de perfil removem imediatamente a entrada de cache correspondente — sem janela de sessão stale.

**Independent Test**: Login → 1ª requisição (popula cache) → logout → verificar com `redis-cli` que chave `session:*` foi removida → nova requisição com mesma sessão retorna 401 sem tocar banco de sessões.

**⚠️ Deployment note**: As tasks desta fase (hooks de invalidação) DEVEM ser merged e deployadas em produção ANTES das tasks da Phase 3 (hooks de população). Invalidar chave inexistente é no-op seguro; inverso cria janela stale.

### Tests for User Story 2 ⚠️ Write FIRST — must FAIL before implementation

- [X] T012 [P] [US2] Write unit tests T04 (`OAuthToken.action_revoke` → `RedisClient.delete(jwt_key(access_token))` called once; Redis DOWN → `action_revoke()` completes without exception) in `18.0/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py`
- [X] T013 [P] [US2] Write unit tests T05 (`APISession.write({'is_active': False})` → `delete(session_key)` called; `write({'company_id': X})` → `delete` called; `write({'last_activity': ...})` only → `delete` NOT called; Redis DOWN → write completes without exception) in `18.0/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py`
- [X] T014 [P] [US2] Write unit tests T06 (`Profile.write({'profile_type_id': X})` with active sessions → `APISession.write({'is_active': False})` called → `delete(session_key)` called; Profile with no `partner_id` → no error) in `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_cache_unit.py`

### Implementation for User Story 2

- [X] T015 [US2] Override `APISession.write(vals)` to call `RedisClient.delete(f"session:{record.session_id}")` for each record when `'is_active' in vals or 'company_id' in vals`; wrap in `try/except`; log INFO per invalidation in `18.0/extra-addons/thedevkitchen_apigateway/models/api_session.py`
- [X] T016 [US2] Override `OAuthToken.action_revoke()` to call `RedisClient.delete(jwt_key(record.access_token))` for each record in `self`; wrap in `try/except`; log INFO in `18.0/extra-addons/thedevkitchen_apigateway/models/oauth_token.py`
- [X] T017 [US2] Add proactive session invalidation to `DELETE /api/v1/profiles/:id` after `user_record.write({'active': False})`: search active sessions for user → `sess.write({'is_active': False})` (write() override handles Redis automatically) in `18.0/extra-addons/quicksol_estate/controllers/profile_api.py`
- [X] T018 [US2] Override `Profile.write(vals)` to detect `'profile_type_id' in vals` and call `sess.write({'is_active': False})` on all active sessions for the associated `res.users` via `self.partner_id`; wrap in `try/except` in `18.0/extra-addons/quicksol_estate/models/profile.py`
- [X] T019 [US2] Write integration tests T08-complete (logout → session key absent in Redis; revoke → JWT key absent; switch-company → session key absent; new login with prior active sessions → all old `session:*` keys absent after new login; all operations complete without 500) in `18.0/extra-addons/thedevkitchen_apigateway/tests/integration/test_redis_cache_integration.py`
- [X] T020 [US2] Create E2E bash test file with helper functions `flush_cache` and `key_exists` and scenarios S01–S06 (S01: cache populated after req, S02: logout removes key + 401, S03: revoke removes JWT key + 401, S04: switch-company removes key, S05: profile DELETE → active sessions 401 without waiting TTL, S06: Redis stopped → HTTP 200 fallback) in `integration_tests/test_us023_redis_cache.sh`

**Checkpoint**: Após logout, chave `session:*` ausente no Redis; nova requisição com sessão encerrada retorna 401 sem consultar `thedevkitchen_api_session` no banco (SC-002 satisfeito).

---

## Phase 5: User Story 3 — Cache de métricas de desempenho de corretores (Priority: P2)

**Goal**: Segunda consulta de métricas do corretor com os mesmos parâmetros é servida do cache; nova transação invalida o cache automaticamente.

**Independent Test**: Chamar endpoint de performance duas vezes com mesmos parâmetros → logs mostram `[CACHE] performance HIT` na 2ª chamada sem queries de agregação ao banco.

### Tests for User Story 3 ⚠️ Write FIRST — must FAIL before implementation

- [X] T021 [P] [US3] Write unit tests T07 (1ª chamada MISS → `set_json` called; 2ª chamada HIT → `_calculate_performance_metrics` NOT called; `performance_cache_ttl_seconds=0` → `set_json` NOT called; `CommissionTransaction.create()` → `delete_pattern(f"performance:agent:{id}:*")` called) in `18.0/extra-addons/quicksol_estate/tests/unit/test_performance_cache_unit.py`

### Implementation for User Story 3

- [X] T022 [US3] Replace `_get_cached_performance`, `_cache_performance`, `invalidate_cache` stubs with real `RedisClient` calls; read `performance_cache_ttl_seconds` from `SecuritySettings` in `__init__`; add `[CACHE] performance HIT/MISS/INVALIDATED` INFO/WARNING logs per operation in `18.0/extra-addons/quicksol_estate/services/performance_service.py`
- [X] T023 [US3] Override `CommissionTransaction.create(vals)` to call `RedisClient.delete_pattern(f"performance:agent:{record.agent_id.id}:*")` when `record.agent_id` is set; wrap in `try/except`; log INFO with agent_id and keys_deleted count in `18.0/extra-addons/quicksol_estate/models/commission_transaction.py`
- [X] T024 [US3] Add E2E bash scenarios S07–S08 to `integration_tests/test_us023_redis_cache.sh` (S07: GET performance twice → 2nd call log shows `performance HIT`; S08: GET performance → POST transaction → GET performance → log shows `performance INVALIDATED` + recalculation)

**Checkpoint**: Segunda consulta de métricas com mesmos parâmetros retorna sem queries de agregação ao banco (SC-003 satisfeito).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Aplicar migration de schema, validar settings backoffice e confirmar quickstart.

- [X] T025 [P] Upgrade Odoo module to apply SecuritySettings schema migration for the 3 new fields: `docker compose exec odoo odoo -d realestate -u thedevkitchen_apigateway --stop-after-init` in `18.0/` directory
- [X] T026 [P] Write integration test T10 (verify `session_cache_ttl_seconds`, `performance_cache_ttl_seconds`, `session_inactivity_days` readable and writable via `SecuritySettings.get_settings()`; verify `ttl=0` → `set_json` returns `False` → no Redis key created for each cache type) in `18.0/extra-addons/thedevkitchen_apigateway/tests/integration/test_redis_cache_integration.py`
- [X] T027 Validate all steps in `specs/023-redis-session-cache/quickstart.md` in running Docker environment (flush cache, toggle TTL, Redis fallback scenario S06)
- [X] T028 Run full existing test suite (`test_middleware.py`, `test_session_validation.py`, `test_login_logout_endpoints.py`, `test_user_auth.py`) and confirm zero failures — verifies SC-004 (no regressions in existing auth tests after implementation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (T001+T002) — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 — independent of Phase 4 and Phase 5
- **Phase 4 (US2)**: Depends on Phase 2 — independent of Phase 3 and Phase 5
- **Phase 5 (US3)**: Depends on Phase 2 — independent of Phase 3 and Phase 4
- **Phase 6 (Polish)**: Depends on Phase 3 + Phase 4 + Phase 5

### User Story Production Deployment Order

| Story | Code Dependency | Production Deploy Order |
|---|---|---|
| US2 (invalidation) | Phase 2 | **Deploy FIRST** — safe (invalidate no-op if key absent) |
| US1 (population) | Phase 2 | **Deploy AFTER US2** — stale window risk if deployed before |
| US3 (performance) | Phase 2 + US2 invalidation | After US2 for CommissionTransaction invalidation |

### Within Each User Story

- Tests **MUST** be written and **FAIL** before implementation begins (TDD)
- Models before services; services before controllers
- `[P]` tasks within a phase can start simultaneously

### Parallel Opportunities Per Phase

| Phase | Parallel batch |
|---|---|
| Phase 2 | T003, T004, T005, T010 all in parallel |
| Phase 3 | T006+T007 → then T008+T009 → T011 |
| Phase 4 | T012+T013+T014 → then T015+T016+T017+T018 → T019 → T020 |
| Phase 5 | T021 → T022+T023 → T024 |
| Phase 6 | T025+T026 → T027 |

---

## Parallel Execution Example: User Story 2 (Invalidation)

```bash
# After Phase 2 completes:

# Batch 1 — tests first (parallel, same file different test methods)
implement T012 &   # JWT revoke unit test
implement T013 &   # APISession write unit test
implement T014     # Profile type-change unit test
wait

# Verify all FAIL before writing production code
run_tests T012 T013 T014   # Expected: all FAIL

# Batch 2 — implementation (parallel, different files)
implement T015 &   # models/api_session.py write() override
implement T016 &   # models/oauth_token.py action_revoke() override
implement T017 &   # controllers/profile_api.py proactive invalidation
implement T018     # quicksol_estate/models/profile.py write() override
wait

run_tests T012 T013 T014   # Expected: all PASS

# Batch 3 — integration + E2E (sequential, depend on T015-T018)
implement T019     # integration test
implement T020     # bash E2E script
```

---

## Implementation Strategy

Implementação completa em ordem de segurança de deploy:

1. **Phase 1 + 2**: Setup e configuração (bloqueante)
2. **Phase 4 (US2)**: Hooks de invalidação — deploy em produção **primeiro** (safe: invalida chave inexistente é no-op)
3. **Phase 3 (US1)**: População de cache — deploy **após US2** em produção (evita janela stale)
4. **Phase 5 (US3)**: Cache de métricas (independente)
5. **Phase 6**: Polish e validação final

---

## Summary

| Metric | Count |
|---|---|
| **Total tasks** | **28** |
| Phase 1 (Setup) | 2 |
| Phase 2 (Foundational) | 4 |
| Phase 3 (US1 — P1) | 5 |
| Phase 4 (US2 — P1) | 9 |
| Phase 5 (US3 — P2) | 4 |
| Phase 6 (Polish) | 4 |
| Tasks marked [P] | 14 |
| New files | 5 |
| Modified files | 11 |
