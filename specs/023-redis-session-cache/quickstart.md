# Quickstart: Redis Cache para Sessão e JWT

**Feature**: 023-redis-session-cache

---

## Pré-requisitos

```bash
cd 18.0
docker compose up -d  # Redis e PostgreSQL já sobem juntos
```

Verificar Redis ativo:
```bash
docker compose exec redis redis-cli ping
# → PONG
```

---

## Verificar Cache Funcionando

### 1. Fazer login e obter token + session_id
```bash
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin","client_id":"...","client_secret":"..."}' \
  | jq -r '.access_token')

SESSION=$(curl -s ... | jq -r '.session_id')
```

### 2. Primeira requisição — MISS (popula cache)
```bash
curl -s http://localhost:8069/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Session-Id: $SESSION"
# Logs: [CACHE] session MISS, [CACHE] jwt MISS
```

### 3. Ver chaves no Redis
```bash
docker compose exec redis redis-cli -n 1 KEYS "*"
# → session:abc123...
# → jwt:def456...
```

### 4. Segunda requisição — HIT (sem banco para auth)
```bash
curl -s http://localhost:8069/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Session-Id: $SESSION"
# Logs: [CACHE] session HIT, [CACHE] jwt HIT
```

---

## Desabilitar Cache por Tipo (Para Testes)

Acessar **Technical → API Gateway → Security Settings** no Odoo e configurar:

| Campo | Valor | Efeito |
|---|---|---|
| `session_cache_ttl_seconds` | 0 | Cache de sessão desabilitado — todas as reqs vão ao banco |
| `performance_cache_ttl_seconds` | 0 | Cache de métricas desabilitado |
| `session_inactivity_days` | 1 | Sessões marcadas inativas após 1 dia sem atividade |

JWT não tem campo — TTL é sempre `expires_at - now()`.

---

## Flush Manual de Cache (Ambiente de Teste)

```bash
# Flush somente keys desta feature (não afeta outros dados Redis)
docker compose exec redis redis-cli -n 1 KEYS "session:*" | xargs -r \
  docker compose exec redis redis-cli -n 1 DEL
docker compose exec redis redis-cli -n 1 KEYS "jwt:*" | xargs -r \
  docker compose exec redis redis-cli -n 1 DEL
docker compose exec redis redis-cli -n 1 KEYS "performance:*" | xargs -r \
  docker compose exec redis redis-cli -n 1 DEL
```

---

## Executar Testes Automatizados

### Unit tests (com Redis mockado — não requer container Redis)
```bash
docker compose exec odoo bash -c \
  "python -m pytest /mnt/extra-addons/thedevkitchen_apigateway/tests/unit/test_redis_cache_unit.py -v"
```

### Integration tests (requer Redis)
```bash
docker compose exec odoo bash -c \
  "python -m pytest /mnt/extra-addons/thedevkitchen_apigateway/tests/integration/test_redis_cache_integration.py -v"
```

### E2E bash (requer serviços rodando)
```bash
cd 18.0 && bash ../integration_tests/test_us023_redis_cache.sh
```

---

## Testar Fallback (Redis Indisponível)

```bash
# Parar Redis
docker compose stop redis

# Fazer requisição autenticada — deve retornar 200 (fallback banco)
curl -s http://localhost:8069/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Session-Id: $SESSION"
# → HTTP 200 (sem 500)
# Logs: [CACHE] Redis connection failed: ...

# Restaurar Redis
docker compose start redis
```
