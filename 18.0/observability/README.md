# 📊 Observabilidade - Grafana Stack

Stack completa de observabilidade para monitorar Odoo em produção usando **Grafana**, **Prometheus**, **Loki** e **Tempo**.

## 🎯 O que está incluído

### Componentes Principais

1. **Grafana** (port 3000) - Dashboards e visualização
2. **Prometheus** (port 9090) - Métricas de sistema e aplicação
3. **Loki** (port 3100) - Agregação e consulta de logs
4. **Tempo** (port 3200) - Distributed tracing (APM)

### Exporters

- **node-exporter** - Métricas do sistema operacional (CPU, RAM, disco)
- **cadvisor** - Métricas dos containers Docker
- **postgres-exporter** - Métricas do PostgreSQL
- **redis-exporter** - Métricas do Redis
- **promtail** - Coleta logs dos containers

## 🚀 Início Rápido

### 1. Configurar Variáveis de Ambiente

```bash
# Copiar .env.example
cp .env.example .env

# Gerar senhas fortes
openssl rand -base64 32  # Para GRAFANA_ADMIN_PASSWORD
openssl rand -base64 32  # Para outras senhas

# Editar .env e substituir TROCAR_* por valores reais
nano .env
```

### 2. Iniciar Stack Completa

```bash
# Método 1: Usando script (recomendado)
./start-observability.sh start

# Método 2: Docker Compose manualmente
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

### 3. Acessar Dashboards

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / (ver .env) |
| **Prometheus** | http://localhost:9090 | Sem autenticação |
| **Loki** | http://localhost:3100 | Sem autenticação |
| **Tempo** | http://localhost:3200 | Sem autenticação |
| **cAdvisor** | http://localhost:8080 | Sem autenticação |

## 📈 Dashboards Recomendados

Importar no Grafana (Dashboards → Import → Digite o ID):

| Dashboard | ID | Descrição |
|-----------|----|-----------| 
| Node Exporter Full | 1860 | Métricas completas do sistema operacional |
| PostgreSQL Database | 9628 | Performance do PostgreSQL |
| Redis | 11835 | Cache hit rate, memória, conexões |
| Docker Container & Host | 193 | Recursos dos containers |
| Traefik | 11462 | Se usar Traefik como reverse proxy |

## 🔧 Comandos Úteis

### Script de Gerenciamento

```bash
# Ver todos os comandos disponíveis
./start-observability.sh help

# Iniciar stack completa
./start-observability.sh start

# Parar tudo
./start-observability.sh stop

# Reiniciar
./start-observability.sh restart

# Ver logs de todos os serviços
./start-observability.sh logs

# Ver logs de um serviço específico
./start-observability.sh logs grafana
./start-observability.sh logs prometheus
./start-observability.sh logs odoo

# Verificar status e saúde
./start-observability.sh status

# Listar URLs de acesso
./start-observability.sh dashboards

# Limpar TODOS os dados (CUIDADO!)
./start-observability.sh clean
```

### Docker Compose Direto

```bash
# Subir só observabilidade
docker compose -f docker-compose.observability.yml up -d

# Parar observabilidade
docker compose -f docker-compose.observability.yml down

# Ver logs
docker compose -f docker-compose.observability.yml logs -f [serviço]

# Ver status
docker compose -f docker-compose.observability.yml ps
```

## 📊 O que Monitorar

### 1. Sistema (Node Exporter)
- CPU usage (%)
- Memory usage (%)
- Disk usage e I/O
- Network I/O
- Load average

### 2. Containers (cAdvisor)
- CPU por container
- Memória por container
- Restarts
- Uptime

### 3. PostgreSQL
- **Crítico:** Conexões ativas (alerta se > 80%)
- **Crítico:** Cache hit rate (ideal > 99%)
- Slow queries (> 1 segundo)
- Deadlocks
- Tamanho de tabelas
- Queries por segundo

### 4. Redis
- **Crítico:** Cache hit rate (ideal > 80%)
- Memória usada vs maxmemory
- Evicted keys
- Conexões ativas
- Commands/s

### 5. Odoo (quando instrumentado)
- Requests/s
- Response time (p50, p95, p99)
- Error rate
- Active sessions

### 6. RabbitMQ
- Queue depth
- Message rate
- Consumer lag

### 7. Celery
- Tasks/s
- Success/failure rate
- Task duration

## 🚨 Alertas Configurados

Ver arquivo `observability/alerts.yml` para lista completa.

### Alertas Críticos

- ❌ **DiskSpaceCritical**: Disco < 20% livre
- ❌ **HighMemoryUsage**: Memória > 90%
- ❌ **ContainerDown**: Serviço crítico down
- ❌ **PostgreSQLDown**: Database offline
- ❌ **PostgreSQLConnectionsCritical**: > 95% conexões usadas
- ❌ **RedisDown**: Cache offline

### Alertas de Warning

- ⚠️ **DiskSpaceWarning**: Disco < 40% livre
- ⚠️ **HighCPUUsage**: CPU > 80% por 10min
- ⚠️ **PostgreSQLTooManyConnections**: > 80% conexões
- ⚠️ **PostgreSQLLowCacheHitRate**: < 80%
- ⚠️ **PostgreSQLSlowQueries**: Média > 1s
- ⚠️ **RedisLowHitRate**: < 70%
- ⚠️ **RedisHighMemory**: > 90% maxmemory

## 🔍 Queries Úteis

### Prometheus (PromQL)

```promql
# CPU usage por container
rate(container_cpu_usage_seconds_total[5m]) * 100

# Memória usada por container
container_memory_usage_bytes / container_spec_memory_limit_bytes * 100

# PostgreSQL cache hit rate
sum(pg_stat_database_blks_hit) / (sum(pg_stat_database_blks_hit) + sum(pg_stat_database_blks_read))

# Redis cache hit rate
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Disk usage
(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100
```

### Loki (LogQL)

```logql
# Todos os logs de erro
{job="docker"} |= "ERROR"

# Logs do Odoo com filtro
{container="odoo"} |= "INFO" | json

# Slow queries do PostgreSQL
{container="db"} |= "duration:" | json | duration > 1000

# Top 10 erros
sum by (level) (count_over_time({job="docker"} |= "ERROR" [1h]))
```

### Tempo (TraceQL)

```traceql
# Traces com duração > 1s
{ duration > 1s }

# Traces com erro
{ status = error }

# Traces de um serviço específico
{ service.name = "odoo" }

# Traces com span específico
{ name = "database_query" }
```

## 🎨 Criar Dashboards Customizados

### No Grafana

1. **Dashboards → New → New Dashboard**
2. **Add panel**
3. **Escolher data source:**
   - Prometheus (métricas)
   - Loki (logs)
   - Tempo (traces)
4. **Escrever query**
5. **Configurar visualização**
6. **Save** dashboard

### Exemplo: Dashboard de Odoo

```json
{
  "title": "Odoo Performance",
  "panels": [
    {
      "title": "Requests per Second",
      "targets": [
        {
          "expr": "rate(http_requests_total{service=\"odoo\"}[5m])",
          "datasource": "Prometheus"
        }
      ]
    },
    {
      "title": "Error Rate",
      "targets": [
        {
          "expr": "{container=\"odoo\"} |= \"ERROR\"",
          "datasource": "Loki"
        }
      ]
    },
    {
      "title": "Slow Traces",
      "targets": [
        {
          "query": "{ service.name = \"odoo\" && duration > 1s }",
          "datasource": "Tempo"
        }
      ]
    }
  ]
}
```

## 🔧 Troubleshooting

### Grafana não conecta nos data sources

```bash
# Verificar se serviços estão rodando
docker compose -f docker-compose.observability.yml ps

# Verificar logs do Grafana
docker compose -f docker-compose.observability.yml logs grafana

# Verificar network
docker network inspect odoo-net

# Testar conectividade
docker compose -f docker-compose.observability.yml exec grafana ping prometheus
```

### Prometheus não coleta métricas

```bash
# Verificar targets no Prometheus
# Acessar: http://localhost:9090/targets

# Ver logs do Prometheus
docker compose -f docker-compose.observability.yml logs prometheus

# Verificar configuração
docker compose -f docker-compose.observability.yml exec prometheus cat /etc/prometheus/prometheus.yml
```

### Loki não recebe logs

```bash
# Verificar Promtail está rodando
docker compose -f docker-compose.observability.yml ps promtail

# Ver logs do Promtail
docker compose -f docker-compose.observability.yml logs promtail

# Testar conectividade Promtail → Loki
docker compose -f docker-compose.observability.yml exec promtail wget -O- http://loki:3100/ready
```

### Tempo não recebe traces

```bash
# Verificar portas abertas
docker compose -f docker-compose.observability.yml ps tempo

# Ver logs do Tempo
docker compose -f docker-compose.observability.yml logs tempo

# Testar endpoint OTLP
curl -v http://localhost:4318/v1/traces
```

## 📁 Estrutura de Arquivos

```
observability/
├── prometheus.yml              # Config Prometheus
├── alerts.yml                  # Regras de alertas
├── loki-config.yml             # Config Loki
├── promtail-config.yml         # Config Promtail
├── tempo-config.yml            # Config Tempo
├── postgres-queries.yaml       # Queries customizadas PostgreSQL
└── grafana/
    ├── provisioning/
    │   └── datasources/
    │       └── datasources.yml # Data sources do Grafana
    └── dashboards/             # Dashboards customizados (JSON)
```

## 🔐 Segurança

### Checklist

- [ ] Grafana admin password alterado (não usar `admin`)
- [ ] Prometheus NÃO exposto publicamente (só rede interna)
- [ ] Loki SEM autenticação (ok - só rede interna)
- [ ] Grafana atrás de HTTPS (Traefik + Let's Encrypt)
- [ ] Dashboards com controle de acesso (Grafana teams/orgs)
- [ ] Alertas configurados e testados
- [ ] Retenção de dados configurada (30 dias padrão)

### Produção - Boas Práticas

1. **Grafana atrás de Traefik:**
   ```yaml
   grafana:
     labels:
       - "traefik.enable=true"
       - "traefik.http.routers.grafana.rule=Host(`grafana.seudominio.com`)"
       - "traefik.http.routers.grafana.tls=true"
   ```

2. **Prometheus com autenticação:**
   - Adicionar basic auth via Traefik
   - Ou usar Grafana como proxy

3. **Backups regulares:**
   ```bash
   # Backup Grafana dashboards
   docker cp grafana:/var/lib/grafana grafana-backup-$(date +%Y%m%d)
   ```

## 📚 Referências

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)
- [OpenTelemetry](https://opentelemetry.io/)

## 🆘 Suporte

Problemas comuns e soluções no [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) seção "Observabilidade & Monitoramento".
