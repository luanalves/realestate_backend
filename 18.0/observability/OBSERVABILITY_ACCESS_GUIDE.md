# Guia de Observabilidade - Acesso aos Serviços

## 📊 Dashboards Disponíveis no Grafana

Acesse o Grafana em: **http://localhost:3000**
- **Usuário**: admin
- **Senha**: admin

### Dashboards Criados

1. **System Overview** (`system-overview`)
   - CPU Usage (%)
   - Memory Usage (%)
   - Services Up (gauge)
   - Odoo CPU Usage (gauge)

2. **Application Logs** (`application-logs`)
   - Odoo Logs (tempo real)
   - Celery Logs (tempo real)
   - Error Logs (todas as fontes - filtra por ERROR/Exception/Traceback)

3. **Distributed Tracing (APM)** (`distributed-tracing`)
   - Recent Traces (últimas 20 traces)
   - Request Duration by Endpoint (ms)
   - Request Rate by Status Code (req/s)

4. **PostgreSQL Metrics** (`postgresql-metrics`)
   - Active Connections
   - Database Up (status)
   - Transactions per Second (commits/rollbacks)
   - Cache Hit Ratio (%)
   - Temporary Files Usage
   - Tuple Operations (inserts/updates/deletes)

5. **Redis Metrics** (`redis-metrics`)
   - Connected Clients
   - Redis Up (status)
   - Memory Usage (used vs max)
   - Commands per Second
   - Keyspace - Total Keys
   - Cache Hit Rate (%)

## 🔍 Como Acessar Traces do Tempo

⚠️ **IMPORTANTE**: Tempo **NÃO tem UI standalone** em localhost:3200

O endpoint localhost:3200 é a **API REST do Tempo**, não uma interface web.

### Acesso via Grafana Explore

1. Acesse o Grafana: http://localhost:3000
2. No menu lateral, clique em **Explore** (ícone de bússola)
3. No seletor de datasource (topo), escolha **Tempo**
4. Use TraceQL ou busque por tags:

#### Buscar traces do Odoo:
```traceql
{service.name="odoo-development"}
```

#### Buscar traces por endpoint específico:
```traceql
{service.name="odoo-development" && http.route="/api/v1/users/invite"}
```

#### Buscar traces por status code:
```traceql
{service.name="odoo-development" && http.status_code=200}
```

#### Buscar traces com erro:
```traceql
{service.name="odoo-development" && status=error}
```

#### Buscar por trace_id específico:
Digite o trace_id na barra de busca e clique em "Run Query"

### Correlação Logs ↔ Traces

Quando um trace contém `trace_id`, você pode:
1. Copiar o `trace_id` do span no Grafana Explore (Tempo)
2. Ir para Grafana → Explore → Loki
3. Buscar: `{job="odoo"} |= "trace_id_aqui"`

Isso mostrará todos os logs correlacionados com aquele trace específico.

## 📈 Acesso ao Prometheus

**URL**: http://localhost:9090

### Targets Ativos (verificado)
- ✅ cadvisor:8080 (métricas de containers)
- ✅ grafana:3000 (métricas do Grafana)
- ✅ loki:3100 (métricas do Loki)
- ✅ node-exporter:9100 (métricas do sistema)
- ✅ postgres-exporter (métricas do PostgreSQL)
- ✅ redis-exporter (métricas do Redis)
- ✅ prometheus (self-monitoring)
- ✅ tempo (métricas do Tempo)

### Queries Úteis no Prometheus

#### Verificar targets up/down:
```promql
up
```

#### CPU usage:
```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

#### Memory usage:
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

#### PostgreSQL connections:
```promql
pg_stat_database_numbackends{datname="realestate"}
```

#### Redis memory:
```promql
redis_memory_used_bytes
```

## 📝 Acesso ao Loki

**URL**: http://localhost:3100

⚠️ **Loki não tem UI web** - acesse via Grafana Explore:

1. Grafana → Explore → Loki (datasource)
2. Use LogQL para buscar logs:

```logql
# Todos os logs do Odoo
{job="odoo"}

# Logs com erro
{job="odoo"} |= "ERROR"

# Logs do Celery
{job="celery"}

# Logs nos últimos 5 minutos com "invite"
{job="odoo"} |= "invite"
```

## 🚀 Gerando Traces de Teste

Para verificar se o tracing está funcionando:

### 1. Acesse um endpoint instrumentado:
```bash
# Swagger UI (público)
curl http://localhost:8069/api/docs

# OpenAPI spec (público)
curl http://localhost:8069/api/v1/openapi.json
```

### 2. Com autenticação (requer token):
```bash
# Login para obter token
curl -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=admin&password=admin"

# Use o token nos endpoints instrumentados
curl http://localhost:8069/api/v1/me \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 3. Visualizar traces:
1. Aguarde 10-15 segundos (buffer do exporter)
2. Grafana → Explore → Tempo
3. Query: `{service.name="odoo-development"}`
4. Clique em "Run Query"
5. Você verá as traces geradas com:
   - Duração
   - Status code
   - Endpoint (http.route)
   - Método (http.method)

## 🔧 Troubleshooting

### Dashboards não aparecem no Grafana
```bash
# Verificar arquivos existem
ls -la /opt/homebrew/var/www/realestate/odoo-docker/18.0/observability/grafana/dashboards/

# Reiniciar Grafana
docker compose -f docker-compose.yml -f docker-compose.observability.yml restart grafana

# Aguardar 30 segundos
sleep 30

# Acessar: http://localhost:3000 → Dashboards → Browse
```

### Traces não aparecem no Tempo
```bash
# 1. Verificar módulo instalado
docker compose exec -u odoo odoo psql -U odoo -d realestate -c \
  "SELECT name, state FROM ir_module_module WHERE name='thedevkitchen_observability';"

# 2. Verificar variáveis de ambiente
docker compose exec odoo env | grep OTEL

# 3. Verificar logs do Odoo (procurar inicialização do tracer)
docker compose logs odoo --tail 100 | grep -E "🔍|✅|❌|OpenTelemetry|tracer"

# 4. Verificar Tempo está recebendo dados
docker logs tempo --tail 50 | grep -i "received"
```

### Prometheus sem dados
⚠️ **FALSO PROBLEMA**: Prometheus **TEM dados** (8 targets ativos verificados)

Para visualizar no Grafana:
1. Grafana → Explore → Prometheus (datasource)
2. Escrever query PromQL (ex: `up`)
3. Clicar em "Run Query"

## 📌 Resumo de URLs

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Tempo API | http://localhost:3200 (API, não UI) | - |
| Loki | http://localhost:3100 (API, não UI) | - |
| Odoo (para traces) | http://localhost:8069 | admin / admin |

---

**Última atualização**: 2024-03-24
**Dashboards criados**: 5 (system-overview, application-logs, distributed-tracing, postgresql-metrics, redis-metrics)
**Endpoints instrumentados**: 15 (6 controllers)
