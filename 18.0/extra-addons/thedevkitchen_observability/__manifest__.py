{
    'name': 'TheDevKitchen Observability',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'OpenTelemetry instrumentation for distributed tracing',
    'description': """
Observability Module - OpenTelemetry Integration
=================================================

Provides distributed tracing instrumentation for Odoo using OpenTelemetry.

Features:
---------
* Automatic HTTP request tracing
* Distributed context propagation (W3C Trace Context)
* OTLP exporter (gRPC) for Grafana Tempo
* trace_id injection in logs for correlation
* Controller decorator @trace_http_request
* Service method decorators
* Database query tracking (optional)
* Redis operation tracking (optional)

Technical Details:
------------------
* OpenTelemetry SDK 1.22+
* OTLP Protocol Exporter (gRPC)
* W3C Trace Context propagation
* Semantic conventions for HTTP
* Resource detection (service.name, service.version)
* Batch span processor for performance
* Configurable sampling (always_on by default)

Integration:
------------
* Grafana Tempo: Distributed tracing backend
* Loki: Log correlation via trace_id
* Prometheus: Exemplar linking (metrics → traces)

Configuration:
--------------
Environment variables (.env):
- OTEL_ENABLED=true                          # Enable/disable tracing
- OTEL_SERVICE_NAME=odoo-production          # Service identifier
- OTEL_EXPORTER_OTLP_ENDPOINT=tempo:4317    # Tempo gRPC endpoint
- OTEL_EXPORTER_OTLP_INSECURE=true          # Use insecure connection (dev)
- OTEL_TRACES_SAMPLER=always_on             # Sampling strategy
- OTEL_LOG_LEVEL=info                       # Tracer log level

Usage:
------
1. Controllers are automatically traced via HTTP middleware
2. Use @trace_http_request decorator for explicit tracing
3. Logs automatically include trace_id and span_id
4. Access current span: get_current_span()
5. Add custom attributes: span.set_attribute('key', 'value')

Example:
--------
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

@http.route('/api/v1/users', type='http', auth='none', methods=['GET'])
@require_jwt
@require_session
@trace_http_request  # Automatic tracing with HTTP semantics
def list_users(self, **kwargs):
    # Span automatically includes: http.method, http.route, http.status_code
    # trace_id is in logs, Loki can link to Tempo
    return request.make_json_response({'users': [...]})
    """,
    'author': 'TheDevKitchen',
    'website': 'https://thedevkitchen.com.br',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
    ],
    'external_dependencies': {
        'python': [
            'opentelemetry-api>=1.22.0',
            'opentelemetry-sdk>=1.22.0',
            'opentelemetry-exporter-otlp-proto-grpc>=1.22.0',
            'opentelemetry-instrumentation>=0.43b0',
        ],
    },
    'data': [
        'views/otel_browser_config.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # OpenTelemetry bundle (loaded first)
            'thedevkitchen_observability/static/lib/opentelemetry-bundle.js',
            # Odoo module that initializes OTel (loaded second)
            'thedevkitchen_observability/static/src/js/otel_loader.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
