# Phase 5: Dashboards & Observability Stack - Implementation Guide

## Overview

Phase 5 enhances the observability infrastructure with production-ready dashboards, alerting rules, and comprehensive monitoring capabilities across the full stack.

## Status: ✅ Implemented (March 24, 2026)

### What's Included

1. **Full-Stack APM Dashboard** - Browser → Backend → Database visualization
2. **Existing Dashboards** - System, PostgreSQL, Redis, Logs, Distributed Tracing
3. **Alert Rules** - 25+ production-ready alerts for SLO monitoring
4. **Complete Observability Stack** - Grafana, Prometheus, Loki, Tempo, Exporters
5. **Documentation** - Setup, usage, troubleshooting guides

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Grafana    │  │  Prometheus  │  │     Loki     │           │
│  │ (Dashboard)  │  │  (Metrics)   │  │    (Logs)    │           │
│  │  Port: 3000  │  │  Port: 9090  │  │  Port: 3100  │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│  ┌──────────────┐  ┌──────▼───────┐  ┌──────────────┐           │
│  │    Tempo     │  │  Exporters   │  │   Promtail   │           │
│  │  (Traces)    │  │  - Node      │  │(Log Scraper) │           │
│  │  Port: 3200  │  │  - cAdvisor  │  │              │           │
│  │  OTLP: 4317  │  │  - Postgres  │  │              │           │
│  │  HTTP: 4318  │  │  - Redis     │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────┐
              │     Application Stack      │
              │  - Odoo (OpenTelemetry)   │
              │  - PostgreSQL              │
              │  - Redis                   │
              │  - Celery Workers          │
              │  - RabbitMQ                │
              └───────────────────────────┘
```

## Starting the Observability Stack

### Full Stack (Recommended)

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0

# Start application + observability
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Verify all services are healthy
docker compose -f docker-compose.yml -f docker-compose.observability.yml ps
```

### Observability Only

```bash
# If Odoo is already running
docker compose -f docker-compose.observability.yml up -d
```

### Stopping

```bash
# Stop all services
docker compose -f docker-compose.yml -f docker-compose.observability.yml down

# Stop and remove volumes (CAUTION: loses data)
docker compose -f docker-compose.yml -f docker-compose.observability.yml down -v
```

## Accessing Services

### Grafana (Dashboards)

**URL:** http://localhost:3000  
**Credentials:** admin / admin (change on first login)

**Available Dashboards:**
1. **Full-Stack APM** - Browser→Backend→DB performance
2. **Distributed Tracing** - Request tracing and latency
3. **System Overview** - CPU, memory, disk, network
4. **PostgreSQL Metrics** - Connections, queries, cache hit rate
5. **Redis Metrics** - Memory, hit rate, operations
6. **Application Logs** - Loki log aggregation

### Prometheus (Metrics)

**URL:** http://localhost:9090  
**No auth required** (development only)

**Query Examples:**
```promql
# Request rate
rate(http_requests_total[5m])

# CPU usage by container
rate(container_cpu_usage_seconds_total[5m])

# PostgreSQL connections
pg_stat_activity_count

# Redis memory usage
redis_memory_used_bytes
```

### Loki (Logs)

**URL:** http://localhost:3100  
**Query via Grafana Explore**

**LogQL Examples:**
```logql
# All Odoo logs
{container_name="odoo18"}

# Errors only
{container_name="odoo18"} |= "ERROR"

# Traces with specific ID
{container_name="odoo18"} | json | trace_id="abc123..."

# PostgreSQL slow queries
{container_name="db"} |= "duration" | duration > 1000
```

### Tempo (Traces)

**URL:** http://localhost:3200  
**Query via Grafana Explore**

**TraceQL Examples:**
```traceql
# All browser traces
{resource.service.name="odoo-browser"}

# Slow requests (>500ms)
{duration>500ms}

# Errors only
{status=error}

# Specific endpoint
{http.route="/api/v1/users"}

# Full-stack traces (browser + backend)
{resource.service.name="odoo-browser" && duration>200ms}
```

## Dashboards Guide

### 1. Full-Stack APM Dashboard

**Path:** Dashboards → Full-Stack APM (Browser → Backend → DB)

**Panels:**
- **Request Latency by Service (P95)** - Shows 95th percentile latency for browser vs backend
- **Error Rate (SLO: <0.1%)** - Gauge showing current error rate vs SLO target
- **Request Distribution by Service** - Pie chart of requests by service
- **Recent Traces (All Services)** - Table of recent traces with filtering
- **Request Rate by Service** - Time series of request volume
- **Browser Request Latency by Method** - GET vs POST latency breakdown

**Use Cases:**
- Identify slow endpoints
- Track SLO compliance
- Debug performance issues
- Monitor browser vs server latency split

### 2. Distributed Tracing Dashboard

**Path:** Dashboards → Distributed Tracing (APM)

**Panels:**
- **Recent Traces** - Last 20 traces with trace ID, duration, status
- **Request Duration by Endpoint** - Heatmap of latency distribution
- **Request Rate by Status Code** - 2xx vs 4xx vs 5xx breakdown

**Use Cases:**
- Find slow traces
- Investigate errors
- Analyze endpoint performance
- Correlate with logs/metrics

### 3. System Overview Dashboard

**Path:** Dashboards → System Overview

**Panels:**
- CPU usage (per core + total)
- Memory usage (used/free/buffers)
- Disk I/O (read/write rates)
- Network I/O (RX/TX rates)
- Load average (1m, 5m, 15m)

**Use Cases:**
- Capacity planning
- Identify resource bottlenecks
- Monitor system health

### 4. PostgreSQL Metrics Dashboard

**Path:** Dashboards → PostgreSQL Metrics

**Panels:**
- **Connections** - Active, idle, total
- **Cache Hit Rate** - Buffer cache efficiency (target >99%)
- **Query Performance** - Avg query time, slow queries
- **Transactions** - Commits, rollbacks per second
- **Database Size** - Growth over time
- **Lock Contention** - Deadlocks, lock waits

**Use Cases:**
- Optimize query performance
- Monitor connection pool health
- Detect deadlocks
- Track database growth

### 5. Redis Metrics Dashboard

**Path:** Dashboards → Redis Metrics

**Panels:**
- **Memory Usage** - Used vs max memory
- **Cache Hit Rate** - Hits vs misses ratio
- **Operations/s** - GET, SET, DEL rates
- **Evicted Keys** - Keys removed due to memory pressure
- **Connected Clients** - Current connections
- **Keyspace** - Keys by database

**Use Cases:**
- Optimize cache sizing
- Monitor eviction rate
- Track cache effectiveness

### 6. Application Logs Dashboard

**Path:** Dashboards → Application Logs

**Panels:**
- **Log Volume** - Logs per second by level (INFO, WARN, ERROR)
- **Recent Logs** - Last 100 log lines with filtering
- **Error Rate** - Errors per minute
- **Log Patterns** - Top log messages

**Use Cases:**
- Debug application issues
- Track error trends
- Find unusual patterns

## Alerting Rules

### Alert Categories

1. **System** (7 alerts)
   - DiskSpaceCritical (<20% free)
   - DiskSpaceWarning (<40% free)
   - HighMemoryUsage (>90%)
   - HighCPUUsage (>80% for 10min)
   - HighLoadAverage (>2x CPU count)

2. **Containers** (3 alerts)
   - ContainerDown (critical services)
   - ContainerHighRestartRate (>3/hour)
   - ContainerHighMemory (>90% limit)

3. **PostgreSQL** (7 alerts)
   - PostgreSQLDown
   - PostgreSQLTooManyConnections (>80%)
   - PostgreSQLConnectionsCritical (>95%)
   - PostgreSQLLowCacheHitRate (<80%)
   - PostgreSQLSlowQueries (avg >1s)
   - PostgreSQLDeadlocks

4. **Redis** (5 alerts)
   - RedisDown
   - RedisLowHitRate (<70%)
   - RedisHighMemory (>90% maxmemory)
   - RedisRejectedConnections
   - RedisHighEvictionRate (>100/s)

5. **Observability** (3 alerts)
   - PrometheusScrapeFailures
   - TempoDown
   - LokiDown

### Alert Severities

- **critical** - Immediate action required (service down, data loss risk)
- **warning** - Action needed soon (degraded performance, approaching limits)
- **info** - Informational (capacity planning, trends)

### Configuring Alertmanager (Optional)

**For production, configure alerting destinations:**

1. Create `observability/alertmanager.yml`:
```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'team-email'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'ops@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'PASSWORD'
  
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

2. Add Alertmanager to `docker-compose.observability.yml`:
```yaml
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    restart: unless-stopped
    volumes:
      - ./observability/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    ports:
      - "9093:9093"
    networks:
      - odoo-net
```

3. Update Prometheus config to use Alertmanager:
```yaml
# In observability/prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

## SLO Monitoring

### Defined SLOs

**API Endpoints (Authenticated):**
- **Availability:** 99.9% (downtime <8.76 hours/year)
- **Latency (P95):** <200ms
- **Latency (P99):** <500ms
- **Error Rate:** <0.1% (excluding 4xx client errors)

**Browser Experience:**
- **Page Load Time (P95):** <2s
- **API Call Latency (P95):** <300ms (includes network)
- **Error Rate:** <0.5%

### Checking SLO Compliance

**In Grafana:**
1. Open "Full-Stack APM" dashboard
2. Check "Error Rate (SLO: <0.1%)" gauge
3. Check "Request Latency by Service (P95)" graph
4. Verify values are within thresholds

**Via Prometheus:**
```promql
# Error rate (should be <0.001)
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m]))

# P95 latency (should be <200ms)
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)
```

## Troubleshooting

### Grafana Issues

**Problem:** Can't login to Grafana  
**Solution:**
```bash
# Reset admin password
docker exec -it grafana grafana-cli admin reset-admin-password admin
```

**Problem:** Dashboards not showing data  
**Solution:**
1. Check data source connection: Configuration → Data Sources
2. Verify Tempo/Prometheus/Loki are running: `docker ps | grep -E "tempo|prometheus|loki"`
3. Check time range (top-right) - try "Last 1 hour"

**Problem:** "No data" on specific dashboard  
**Solution:**
1. Check if application is generating data (make API requests)
2. Verify OTEL_ENABLED=true in .env
3. Check Odoo logs: `docker logs odoo18 | grep -i opentelemetry`

### Prometheus Issues

**Problem:** Targets showing as "DOWN"  
**Solution:**
```bash
# Check target status
open http://localhost:9090/targets

# Verify services are running
docker compose -f docker-compose.observability.yml ps

# Check exporter logs
docker logs postgres-exporter
docker logs redis-exporter
```

**Problem:** High memory usage  
**Solution:**
1. Reduce retention: Edit `observability/prometheus.yml`, change `--storage.tsdb.retention.time=30d` to `7d`
2. Restart Prometheus: `docker compose -f docker-compose.observability.yml restart prometheus`

### Tempo Issues

**Problem:** No traces appearing  
**Solution:**
1. Verify Tempo is receiving traces:
   ```bash
   docker logs tempo | tail -50
   ```
2. Check if Odoo is sending traces:
   ```bash
   docker logs odoo18 | grep "✅ OpenTelemetry"
   ```
3. Test connectivity:
   ```bash
   docker compose exec odoo nc -zv tempo 4317
   ```

**Problem:** Traces incomplete (missing spans)  
**Solution:**
1. Check if all instrumentation phases are enabled:
   - Phase 1: HTTP tracing
   - Phase 2: Database tracing
   - Phase 3: Celery tracing
   - Phase 4: Browser tracing
2. Verify span processors are working (check Odoo logs for export errors)

### Loki Issues

**Problem:** Logs not appearing  
**Solution:**
1. Check Promtail status:
   ```bash
   docker logs promtail | tail -50
   ```
2. Verify Promtail can access Docker socket:
   ```bash
   docker exec promtail ls -l /var/run/docker.sock
   ```

**Problem:** High disk usage  
**Solution:**
1. Reduce retention in `observability/loki-config.yml`:
   ```yaml
   limits_config:
     retention_period: 168h  # 7 days (default: 720h = 30 days)
   ```
2. Restart Loki: `docker compose -f docker-compose.observability.yml restart loki`

## Performance Tuning

### For High-Traffic Systems

**Adjust Prometheus scrape intervals:**
```yaml
# In observability/prometheus.yml
global:
  scrape_interval: 30s  # Increase from 15s to reduce load
  evaluation_interval: 30s
```

**Increase Tempo retention for traces:**
```yaml
# In observability/tempo-config.yml
storage:
  trace:
    backend: local
    local:
      path: /var/tempo
    block:
      max_retention_duration: 168h  # 7 days
```

**Reduce log volume:**
```yaml
# In observability/promtail-config.yml
# Add filters to exclude noisy logs
- match:
    selector: '{job="containerd"}'
    stages:
    - drop:
        expression: ".*healthcheck.*"
```

## Backup & Disaster Recovery

### Backup Grafana Dashboards

```bash
# Export all dashboards
cd observability/grafana/dashboards
for dashboard in *.json; do
  echo "Backed up: $dashboard"
done

# Commit to git
git add observability/grafana/dashboards/
git commit -m "backup: Grafana dashboards - $(date)"
```

###Backup Prometheus Data (Optional)

```bash
# Snapshot Prometheus data
docker compose exec prometheus curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Copy snapshot
docker cp prometheus:/prometheus/snapshots/. ./backups/prometheus-$(date +%Y%m%d)
```

### Restore Procedure

1. **Grafana:** Dashboards are auto-loaded from `observability/grafana/dashboards/`
2. **Prometheus:** Data rebuilds automatically from scraping targets
3. **Tempo:** Historical traces lost (7-day retention is acceptable for APM)
4. **Loki:** Historical logs lost (7-day retention is acceptable)

## Next Steps (Phase 6+)

### Phase 6: Advanced Features (Planned Q3 2026)

- **Tail-based sampling** - Dynamic sampling based on trace attributes
- **Custom business metrics** - Property views, lead conversions, revenue tracking
- **Enhanced span attributes** - User segments, feature flags, A/B test variants
- **Query performance analysis** - Automatic slow query detection
- **Resource attribution** - Cost tracking per API endpoint

### Phase 7: Production Hardening (Planned Q4 2026)

- **Authentication** - Secure Grafana/Prometheus with OAuth/SAML
- **High availability** - Distributed Tempo backends, Prometheus federation
- **Data retention policies** - Automatic aggregation and downsampling
- **Disaster recovery**Ready runbooks and backup automation
- **Security hardening** - TLS everywhere, secrets management

## References

- ADR-025: OpenTelemetry Distributed Tracing
- Grafana Documentation: https://grafana.com/docs/
- Prometheus Documentation: https://prometheus.io/docs/
- Tempo Documentation: https://grafana.com/docs/tempo/
- Loki Documentation: https://grafana.com/docs/loki/
