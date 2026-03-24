# TheDevKitchen Observability Module

OpenTelemetry instrumentation for Odoo 18.0 with distributed tracing support.

## 📋 Overview

This module provides **automatic distributed tracing** for Odoo using OpenTelemetry, enabling:

- 🔍 **Request tracing**: Automatic HTTP request spans with semantic conventions
- 🔗 **Context propagation**: W3C Trace Context support for distributed systems
- 📊 **OTLP export**: Sends traces to Grafana Tempo via gRPC
- 🔗 **Log correlation**: Automatic trace_id/span_id injection in logs
- 🎯 **Custom instrumentation**: Decorators and utilities for manual tracing
- ⚡ **Performance**: Batch span processor with configurable sampling

## 🚀 Installation

### 1. Install Python Dependencies

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
pip install -r extra-addons/thedevkitchen_observability/requirements.txt
```

Dependencies:
- `opentelemetry-api>=1.22.0`
- `opentelemetry-sdk>=1.22.0`
- `opentelemetry-exporter-otlp-proto-grpc>=1.22.0`
- `opentelemetry-instrumentation>=0.43b0`

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# OpenTelemetry Configuration
OTEL_ENABLED=true
OTEL_SERVICE_NAME=odoo-production
OTEL_SERVICE_VERSION=18.0
OTEL_DEPLOYMENT_ENVIRONMENT=production
OTEL_EXPORTER_OTLP_ENDPOINT=tempo:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_TRACES_SAMPLER=always_on
OTEL_LOG_LEVEL=info
```

### 3. Enable Module in Odoo

```bash
# Install module via Odoo UI or CLI
docker compose exec odoo odoo -u thedevkitchen_observability -d realestate --stop-after-init

# Or add to odoo.conf
server_wide_modules = base,web,thedevkitchen_observability
```

### 4. Start Observability Stack

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
./start-observability.sh start
```

## 📖 Usage

### Automatic Tracing (Recommended)

All HTTP controllers are automatically traced when you use the `@trace_http_request` decorator:

```python
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.decorators import require_jwt, require_session
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

class UserController(http.Controller):
    
    @http.route('/api/v1/users', type='http', auth='none', methods=['GET'])
    @require_jwt
    @require_session
    @trace_http_request  # 👈 Add this decorator
    def list_users(self, **kwargs):
        """List all users - automatically traced"""
        users = request.env['res.users'].search([])
        return request.make_json_response({
            'users': [{'id': u.id, 'name': u.name} for u in users]
        })
```

The `@trace_http_request` decorator automatically captures:
- ✅ HTTP method, URL, route, status code
- ✅ User agent, client IP
- ✅ User ID and name (if authenticated)
- ✅ Request duration
- ✅ Exceptions and error details
- ✅ W3C Trace Context propagation

### Manual Instrumentation

For complex operations, use manual spans:

```python
from odoo.addons.thedevkitchen_observability.services.tracer import (
    get_tracer,
    add_span_attribute,
    add_span_event,
    create_child_span,
)

class PropertyService:
    
    def calculate_price(self, property_id):
        """Complex operation with detailed tracing"""
        tracer = get_tracer()
        
        with tracer.start_as_current_span("calculate_price") as span:
            # Add custom attributes
            span.set_attribute("property.id", property_id)
            span.set_attribute("operation.type", "price_calculation")
            
            # Load property
            add_span_event("fetch.property.start")
            prop = self.env['real.estate.property'].browse(property_id)
            add_span_event("fetch.property.complete", {
                'property.type': prop.property_type,
                'property.status': prop.status_id.name,
            })
            
            # Calculate with child span
            with create_child_span("fetch.market.data") as child_span:
                child_span.set_attribute("market.region", prop.city)
                market_data = self._fetch_market_data(prop.city)
            
            # Calculate price
            price = self._calculate(prop, market_data)
            span.set_attribute("price.result", price)
            
            return price
```

### Helper Functions

```python
from odoo.addons.thedevkitchen_observability.services.tracer import (
    get_current_span,
    get_trace_context,
    add_span_attribute,
    add_span_event,
)

# Get current span
span = get_current_span()
if span.is_recording():
    span.set_attribute("custom.field", "value")

# Get trace context for logging
context = get_trace_context()
# Returns: {'trace_id': 'abc123...', 'span_id': 'def456...'}

# Add attributes to current span
add_span_attribute("user.role", "manager")
add_span_attribute("query.count", 42)

# Add events (timestamped annotations)
add_span_event("cache.hit", {"cache.key": "user:123"})
add_span_event("database.query.slow", {"duration_ms": 1500})
```

## 🔗 Log Correlation

Logs automatically include `trace_id` and `span_id` fields, enabling correlation in Grafana:

**Python log:**
```python
_logger.info("Processing payment for property %s", property_id)
# Output: 2024-03-24 10:15:30 INFO [trace_id=abc123...] [span_id=def456...] Processing payment for property 42
```

**Grafana Loki:**
1. Click on log line in Loki
2. See "View Trace" button (automatically linked via trace_id)
3. Click to jump directly to the trace in Tempo
4. See all related logs in Loki panel below trace

**Grafana Tempo:**
1. View trace timeline
2. Click on span to see details
3. See "View Logs" button in span details
4. Click to see all logs for that trace_id in Loki

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `true` | Enable/disable tracing globally |
| `OTEL_SERVICE_NAME` | `odoo` | Service identifier in traces |
| `OTEL_SERVICE_VERSION` | `18.0` | Service version tag |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | `development` | Environment tag (production/staging/dev) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `tempo:4317` | Tempo gRPC endpoint |
| `OTEL_EXPORTER_OTLP_INSECURE` | `true` | Use insecure connection (no TLS) |
| `OTEL_TRACES_SAMPLER` | `always_on` | Sampling strategy (see below) |
| `OTEL_LOG_LEVEL` | `info` | Tracer log level |

### Sampling Strategies

Control what percentage of requests are traced:

- **`always_on`**: Trace 100% of requests (recommended for staging/dev)
- **`always_off`**: Disable tracing (same as OTEL_ENABLED=false)
- **`traceidratio:0.1`**: Trace 10% of requests (recommended for high-traffic production)
- **`traceidratio:0.01`**: Trace 1% of requests (ultra high-traffic)

Example for production with 10% sampling:
```bash
OTEL_TRACES_SAMPLER=traceidratio:0.1
```

### Performance Tuning

The BatchSpanProcessor exports spans in batches to minimize overhead:

```python
# Default configuration (in tracer.py)
BatchSpanProcessor(
    max_queue_size=2048,           # Max spans in queue
    schedule_delay_millis=5000,    # Export every 5 seconds
    max_export_batch_size=512,     # Max spans per batch
    export_timeout_millis=30000,   # 30s timeout
)
```

For high-throughput systems, increase `max_queue_size` and `max_export_batch_size`.

## 📊 Grafana Integration

### View Traces in Tempo

1. Open Grafana: http://localhost:3000
2. Go to **Explore** → Select **Tempo** data source
3. Query options:
   - **Search**: Filter by service, operation, tags
   - **TraceQL**: Advanced queries (e.g., `{span.http.status_code>=500}`)
   - **Trace ID**: Direct lookup if you have trace_id from logs

Example TraceQL queries:
```traceql
# Find slow requests (>1 second)
{duration>1s}

# Find errors in specific service
{service.name="odoo-production" && status=error}

# Find requests to specific endpoint
{http.route="/api/v1/users"}

# Combine conditions
{service.name="odoo-production" && http.method="POST" && duration>500ms}
```

### View Correlated Logs in Loki

1. In Tempo trace view, click on any span
2. Click **"Logs for this span"** button
3. Loki opens with logs filtered by trace_id
4. See all logs related to this request

### Create Dashboards

Use these metrics in Prometheus dashboards:

```promql
# Request rate by endpoint
rate(http_requests_total[5m])

# Request duration (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m])
```

Link metrics to traces using **exemplars** (automatically enabled in Grafana).

## 🐛 Troubleshooting

### Traces not appearing in Tempo

1. **Check if tracing is enabled:**
   ```bash
   # In container
   echo $OTEL_ENABLED  # Should be 'true'
   echo $OTEL_EXPORTER_OTLP_ENDPOINT  # Should be 'tempo:4317'
   ```

2. **Check Odoo logs:**
   ```bash
   docker compose logs odoo | grep -i opentelemetry
   # Should see: ✅ OpenTelemetry initialized: service=odoo-production...
   ```

3. **Check Tempo is receiving spans:**
   ```bash
   docker compose -f docker-compose.observability.yml logs tempo
   # Should see span batches being received
   ```

4. **Test connectivity:**
   ```bash
   docker compose exec odoo nc -zv tempo 4317
   # Should output: tempo (172.x.x.x:4317) open
   ```

### trace_id not in logs

1. **Check filter is installed:**
   ```bash
   docker compose logs odoo | grep TraceContextFilter
   # Should see: ✅ TraceContextFilter installed on root logger
   ```

2. **Test with a request:**
   ```bash
   curl -X GET http://localhost:8069/api/v1/health
   docker compose logs odoo --tail 50
   # Should see [trace_id=...] in log lines
   ```

### High overhead / performance impact

1. **Enable sampling:**
   ```bash
   OTEL_TRACES_SAMPLER=traceidratio:0.1  # Only trace 10%
   ```

2. **Increase batch size:**
   Edit `tracer.py` and increase `max_export_batch_size` to 1024.

3. **Disable tracing temporarily:**
   ```bash
   OTEL_ENABLED=false
   docker compose restart odoo
   ```

## 📚 References

- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [TraceQL Query Language](https://grafana.com/docs/tempo/latest/traceql/)

## 🧪 Testing

### Test Trace Generation

```bash
# Generate some traffic
for i in {1..10}; do
  curl -X GET http://localhost:8069/api/v1/health
  sleep 1
done

# Check traces in Tempo
# Open Grafana → Explore → Tempo → Search
# Set time range to Last 5 minutes
# Click "Run Query"
# Should see 10 traces for GET /api/v1/health
```

### Test Log Correlation

```python
# In Odoo shell
import logging
from odoo.addons.thedevkitchen_observability.services.tracer import get_trace_context

_logger = logging.getLogger(__name__)

# Log with trace context
context = get_trace_context()
_logger.info(f"Test log with context: {context}")

# Check logs
docker compose logs odoo --tail 10
# Should see [trace_id=...] [span_id=...] in output
```

## 🤝 Contributing

When adding custom instrumentation:

1. **Use semantic conventions**: Follow [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
2. **Add context**: Include relevant attributes (user.id, property.id, etc.)
3. **Create child spans**: For database queries, external API calls, heavy computations
4. **Add events**: For important milestones (cache hit/miss, validation passed, etc.)
5. **Handle errors**: Use `span.record_exception()` and `span.set_status(Status.ERROR)`

## 📄 License

LGPL-3 (same as Odoo)

---

**Need help?** Check the [Observability Stack README](../../observability/README.md) for Grafana, Prometheus, Loki, and Tempo configuration.
