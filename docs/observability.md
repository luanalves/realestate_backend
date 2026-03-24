# Observability Configuration Guide

## Overview

The Odoo Docker environment includes a complete observability stack with distributed tracing, centralized logging, and metrics visualization using the LGTM (Loki, Grafana, Tempo, Mimir) stack.

## Architecture Components

### Infrastructure Stack (23 containers)

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| **Grafana** | Latest | 3000 | Visualization and dashboarding |
| **Loki** | 2.9.3 | 3100 | Log aggregation |
| **Promtail** | 2.9.3 | - | Log collection agent |
| **Tempo** | 2.3.1 | 3200 (HTTP), 4317 (OTLP/gRPC) | Distributed tracing backend |
| **Prometheus** | Latest | 9090 | Metrics collection |
| **cAdvisor** | Latest | 8080 | Container metrics |
| **Node Exporter** | Latest | 9100 | Host metrics |
| **Postgres Exporter** | Latest | 9187 | PostgreSQL metrics |
| **Redis Exporter** | Latest | 9121 | Redis metrics |

### Application Components

| Module | Purpose | Status |
|--------|---------|--------|
| **thedevkitchen_observability** | Core tracing infrastructure | ✅ Installed |
| **OpenTelemetry SDK** | v1.40.0 | ✅ Configured |
| **TraceContextFilter** | Log-trace correlation | ✅ Active |
| **DB Instrumentor** | PostgreSQL query tracing (Cursor.execute patch) | ✅ Active |
| **Redis Instrumentor** | Redis command tracing | ✅ Active |

## Configuration

### Environment Variables (.env)

```bash
# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
OTEL_SERVICE_NAME=odoo-development
OTEL_TRACES_SAMPLER=always_on
OTEL_RESOURCE_ATTRIBUTES=service.environment=development

# Database Instrumentation (Phase 2)
OTEL_SLOW_QUERY_THRESHOLD_MS=100          # Slow query threshold in ms (default: 100)
OTEL_DB_STATEMENT_SANITIZE=false          # Sanitize SQL params in spans (default: true)
```

### Sampling Configuration

**Development:**
- `OTEL_TRACES_SAMPLER=always_on` (100% sampling)
- All requests are traced for debugging

**Production (recommended):**
```bash
OTEL_TRACES_SAMPLER=traceidratio:0.1  # 10% sampling
```

### Span Export Configuration

**BatchSpanProcessor settings** (tracer.py):
- `schedule_delay_millis`: 5000 (5 seconds)
- `max_queue_size`: 2048
- `max_export_batch_size`: 512
- `export_timeout_millis`: 30000

## Instrumented Endpoints

### thedevkitchen_apigateway (6 controllers, 15 endpoints)

All endpoints use the `@trace_http_request` decorator:

**auth_controller.py:**
- `POST /api/v1/auth/token` - OAuth2 token generation
- `POST /api/v1/auth/refresh` - Token refresh

**me_controller.py:**
- `GET /api/v1/me` - Current user info

**user_auth_controller.py:**
- `POST /api/v1/users/login` - Login with session management
- `POST /api/v1/users/logout` - Session invalidation
- `GET /api/v1/users/profile` - User profile

**swagger_controller.py:**
- `GET /api/docs` - Swagger UI
- `GET /api/v1/openapi.json` - OpenAPI spec

### thedevkitchen_user_onboarding (2 controllers, 7 endpoints)

**invite_controller.py:**
- `POST /api/v1/users/invite`
- `POST /api/v1/users/{id}/resend-invite`

**password_controller.py:**
- `POST /api/v1/auth/set-password`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

## Phase 2: Database Instrumentation

### How It Works

Every SQL query executed by Odoo is automatically wrapped in an OpenTelemetry span via a monkey-patch on `odoo.sql_db.Cursor.execute`. SQL spans are created as **children** of the active HTTP span, enabling full request-to-database tracing.

```
GET /api/v1/me (HTTP span - 12ms)
  ├─ SELECT res_users (SQL span - 0.5ms)
  ├─ SELECT res_company (SQL span - 0.3ms)
  └─ SELECT res_partner (SQL span - 0.8ms)
```

### Why Not Psycopg2Instrumentor?

The standard `opentelemetry-instrumentation-psycopg2` patches `psycopg2.connect()`, but Odoo creates database connections at boot time (before modules load). Pre-existing connections in Odoo's `ConnectionPool` are **not instrumented**. Our approach patches `Cursor.execute` which intercepts ALL queries regardless of connection age.

### SQL Span Attributes

| Attribute | Example | Description |
|-----------|---------|-------------|
| `db.system` | `postgresql` | Database system |
| `db.name` | `realestate` | Database name |
| `db.operation` | `SELECT`, `INSERT`, `UPDATE`, `DELETE` | SQL operation type |
| `db.sql.table` | `res_users` | Target table |
| `db.statement` | `SELECT id, name FROM res_users WHERE...` | Query text (sanitizable) |
| `db.rowcount` | `5` | Number of affected rows |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SLOW_QUERY_THRESHOLD_MS` | `100` | Queries slower than this are flagged |
| `OTEL_DB_STATEMENT_SANITIZE` | `true` | Replace `%s` params with `?` in production |

### Querying SQL Traces in Grafana

```traceql
# Find slow SQL queries
{span.db.system="postgresql" && duration > 100ms}

# Find queries on a specific table
{span.db.sql.table="res_users"}

# Find HTTP requests with SQL children
{service.name="odoo-development" && span.http.method="GET"} >> {span.db.system="postgresql"}
```

## Grafana Dashboards

### 1. System Overview
**File:** `observability/grafana/dashboards/system-overview.json`

Metrics:
- CPU usage (per service)
- Memory usage (per container)
- Service uptime
- Container restarts

### 2. Application Logs
**File:** `observability/grafana/dashboards/application-logs.json`

Log streams:
- Odoo application logs
- Celery worker logs
- Error rate trends
- Log volume by severity

### 3. Distributed Tracing (APM)
**File:** `observability/grafana/dashboards/distributed-tracing.json`

Metrics:
- Request latency (p50, p95, p99)
- Request rate by endpoint
- Error rate by status code
- Trace duration heatmap

**Note:** Some panels may show 400 errors for rate() queries. This is expected - Tempo stores traces (not metrics). Use Grafana Explore → Tempo for trace search.

### 4. PostgreSQL Metrics
**File:** `observability/grafana/dashboards/postgresql-metrics.json`

Metrics:
- Active connections
- Transaction rate
- Cache hit ratio
- Database size
- Slow query detection

### 5. Redis Metrics
**File:** `observability/grafana/dashboards/redis-metrics.json`

Metrics:
- Connected clients
- Memory usage
- Commands per second
- Cache hit rate
- Eviction rate

## Usage

### Accessing Web UIs

```bash
# Grafana (admin/admin123)
open http://localhost:3000

# Prometheus
open http://localhost:9090

# Tempo API
open http://localhost:3200
```

### Querying Traces

**Via Grafana Explore:**
1. Navigate to http://localhost:3000/explore
2. Select "Tempo" datasource
3. Use TraceQL syntax:
   ```traceql
   {service.name="odoo-development"}
   {service.name="odoo-development" && http.status_code=500}
   {http.route="/api/v1/me" && duration > 100ms}
   ```

**Via Tempo API:**
```bash
# Search traces by service name
curl "http://localhost:3200/api/search?tags=service.name%3Dodoo-development&limit=10"

# Get specific trace
curl "http://localhost:3200/api/traces/{traceID}"
```

### Verifying Trace Export

```bash
# 1. Generate traffic to instrumented endpoint
curl http://localhost:8069/api/docs

# 2. Wait 5 seconds for BatchSpanProcessor export
sleep 5

# 3. Query Tempo for recent traces
curl "http://localhost:3200/api/search?tags=service.name%3Dodoo-development"
```

### Log Correlation (Loki ↔ Tempo)

**How it works:**
- `TraceContextFilter` injects `trace_id` into every log record
- Grafana links traces → logs automatically
- Use "Logs for this span" button in Tempo trace view

**Manual correlation:**
1. Copy `trace_id` from a span in Grafana → Tempo
2. Switch to Grafana → Explore → Loki
3. Query: `{job="odoo"} |= "trace_id_here"`

**Example log format:**
```
2026-03-24 10:41:04,421 1 INFO [trace_id=c44d3542660320afd2beee48acf5cbf7] realestate odoo.service: User logged in
```

## Troubleshooting

### No traces in Tempo

**Check tracer initialization:**
```bash
docker logs odoo18 --tail 100 | grep "OpenTelemetry"
```

Expected output:
```
✅ OpenTelemetry initialized: service=odoo-development, endpoint=tempo:4317, sampler=always_on, env=development
✅ TraceContextFilter installed on root logger
```

**Verify connectivity:**
```bash
docker compose exec odoo python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('tempo', 4317))
print('✅ Connected' if result == 0 else '❌ Failed')
sock.close()
"
```

**Check for export errors:**
```bash
docker logs odoo18 2>&1 | grep -i "otlp\|exporter\|grpc" | grep -i "error\|failed"
```

### Dashboards not loading

**Verify provisioning path:**
```bash
# Should show JSON files
docker compose exec grafana ls -la /var/lib/grafana/dashboards/

# Check Grafana logs
docker logs grafana | grep "provisioning"
```

**Validate JSON syntax:**
```bash
python3 -m json.tool observability/grafana/dashboards/system-overview.json > /dev/null
echo $?  # Should be 0
```

### TraceContextFilter not working

**Check if installed:**
```bash
docker logs odoo18 | grep "TraceContextFilter"
```

### SQL spans not appearing

**Check DB instrumentation initialization:**
```bash
docker logs odoo18 2>&1 | grep -E "PostgreSQL|Cursor|db_instru"
```

Expected:
```
✅ PostgreSQL instrumentation initialized (Odoo Cursor.execute patched): slow_query_threshold=100ms, sanitize=True
✅ Redis instrumentation initialized
🔍 Database instrumentation: PostgreSQL ✅, Redis ✅
```

**SQL spans are root spans (not linked to HTTP)?**
- This should not happen with the Cursor.execute approach
- If it does, verify `@trace_http_request` decorator is on the endpoint
- The decorator creates the parent HTTP span; SQL spans inherit via OpenTelemetry context propagation

**No SQL spans at all?**
- Check that `OTEL_ENABLED=true` in `.env`
- Restart Odoo after changing `.env`: `docker compose restart odoo`
- Verify the module is loaded: `docker logs odoo18 | grep "observability"`

**Check if installed:**
```bash
docker logs odoo18 | grep "TraceContextFilter"
```

Expected:
```
✅ TraceContextFilter installed on root logger
```

**Why no trace_id in logs?**
- Endpoints like `/api/docs` and `/api/v1/openapi.json` don't generate application logs (only HTTP access logs)
- trace_id appears only in logs from instrumented endpoints that execute `_logger.info/warning/error()`
- Test with endpoints that perform business logic (e.g., `/api/v1/users/login`)

## Performance Considerations

### Resource Usage

**Expected overhead:**
- CPU: < 2% additional overhead per traced request
- Memory: ~50MB for OTEL SDK + BatchSpanProcessor buffer
- Network: ~5KB per traced request (span export)

### Production Optimization

1. **Use sampling:**
   ```bash
   OTEL_TRACES_SAMPLER=traceidratio:0.1  # 10% sampling
   ```

2. **Increase batch size:**
   ```python
   batch_processor = BatchSpanProcessor(
       exporter,
       max_queue_size=4096,       # Increased from 2048
       max_export_batch_size=1024 # Increased from 512
   )
   ```

3. **Filter high-volume static endpoints:**
   ```python
   EXCLUDED_PATHS = ['/web/static/', '/web/assets/', '/web_editor/']
   
   if any(path in http_route for path in EXCLUDED_PATHS):
       return func(*args, **kwargs)  # Skip tracing
   ```

## Known Issues

### OpenTelemetry SDK v1.40.0 Breaking Change

**Issue:** `AlwaysOn` sampler class removed, replaced with `ALWAYS_ON` constant.

**Fixed in:** [18.0/extra-addons/thedevkitchen_observability/services/tracer.py](../18.0/extra-addons/thedevkitchen_observability/services/tracer.py)

**Before:**
```python
from opentelemetry.sdk.trace.sampling import AlwaysOn
sampler = AlwaysOn()
```

**After:**
```python
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
sampler = ALWAYS_ON
```

### Tempo TraceQL Rate Queries

**Issue:** Dashboard panels using `rate()` show 400 errors.

**Reason:** Tempo stores traces (spans), not time-series metrics. Rate queries need Prometheus, not Tempo.

**Workaround:** Use Grafana Explore → Tempo for trace search instead of dashboard rate panels.

## Testing

### Automated Test Script

Location: `18.0/test_auth_traces.py`

```bash
cd 18.0
python3 test_auth_traces.py
```

**What it tests:**
- OAuth token generation (`/api/v1/auth/token`)
- Authenticated endpoint (`/api/v1/me`)
- Trace export to Tempo
- Span attributes (HTTP method, route, status)

### Manual Testing

```bash
# Start observability stack
cd 18.0
docker compose up -d

# Generate test traffic
curl http://localhost:8069/api/docs
curl http://localhost:8069/api/v1/openapi.json

# Wait for export (5 seconds)
sleep 5

# Verify traces in Tempo
python3 -c "
import http.client, json
conn = http.client.HTTPConnection('localhost', 3200)
conn.request('GET', '/api/search?tags=service.name%3Dodoo-development')
traces = json.loads(conn.getresponse().read().decode())
print(f'Found {len(traces.get(\"traces\", []))} traces')
for t in traces['traces'][:5]:
    print(f'  • {t[\"rootTraceName\"]} ({t[\"durationMs\"]}ms)')
"
```

## References

- **OpenTelemetry Python Docs:** https://opentelemetry.io/docs/instrumentation/python/
- **Tempo Documentation:** https://grafana.com/docs/tempo/latest/
- **TraceQL Query Language:** https://grafana.com/docs/tempo/latest/traceql/
- **W3C Trace Context:** https://www.w3.org/TR/trace-context/

## Support

For issues or questions:
1. Check [TECHNICAL_DEBIT.md](../TECHNICAL_DEBIT.md) for known issues
2. Review ADR-010: OpenTelemetry Integration (if created)
3. Consult `.specify/memory/constitution.md` for patterns
