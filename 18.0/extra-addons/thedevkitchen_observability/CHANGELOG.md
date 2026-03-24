# Changelog

All notable changes to the thedevkitchen_observability module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.0.0] - 2024-03-24

### Added
- Initial release of thedevkitchen_observability module
- OpenTelemetry SDK integration (v1.22+)
- OTLP gRPC exporter for Grafana Tempo
- `@trace_http_request` decorator for automatic HTTP controller tracing
- Automatic trace_id and span_id injection in logs (TraceContextFilter)
- W3C Trace Context propagation for distributed tracing
- BatchSpanProcessor for optimal performance
- Configurable sampling strategies (always_on, always_off, traceidratio)
- Helper functions: `get_tracer()`, `get_current_span()`, `get_trace_context()`
- Manual instrumentation utilities: `add_span_attribute()`, `add_span_event()`, `create_child_span()`
- Comprehensive README with usage examples and troubleshooting
- INSTRUMENTATION_EXAMPLE.md with before/after code samples
- HTML description page for Odoo Apps interface
- Environment variable configuration (.env integration)
- docker-compose.yml integration with OTEL_* variables

### Features
- **Automatic HTTP Tracing**: Controllers decorated with `@trace_http_request` capture full HTTP semantics
- **Log Correlation**: trace_id/span_id in logs enable one-click navigation to traces in Grafana
- **Grafana Integration**: Seamless Tempo (traces), Loki (logs), and Prometheus (metrics) integration
- **Production Ready**: Configurable sampling, batch processing, and performance optimization
- **Developer Experience**: Simple decorator pattern, minimal code changes required

### Configuration
- `OTEL_ENABLED`: Enable/disable tracing (default: true)
- `OTEL_SERVICE_NAME`: Service identifier (default: odoo)
- `OTEL_SERVICE_VERSION`: Service version (default: 18.0)
- `OTEL_DEPLOYMENT_ENVIRONMENT`: Environment tag (default: development)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: Tempo gRPC endpoint (default: tempo:4317)
- `OTEL_EXPORTER_OTLP_INSECURE`: Use insecure connection (default: true)
- `OTEL_TRACES_SAMPLER`: Sampling strategy (default: always_on)
- `OTEL_LOG_LEVEL`: Tracer log level (default: info)

### Technical Details
- Language: Python 3.10+
- OpenTelemetry API/SDK: 1.22+
- Protocol: OTLP (gRPC)
- Propagation: W3C Trace Context
- Processor: BatchSpanProcessor (async, optimized)
- Sampling: Configurable (always_on, traceidratio, parent-based)

### Dependencies
- `opentelemetry-api>=1.22.0`
- `opentelemetry-sdk>=1.22.0`
- `opentelemetry-exporter-otlp-proto-grpc>=1.22.0`
- `opentelemetry-instrumentation>=0.43b0`

### Documentation
- [README.md](README.md): Complete module documentation
- [INSTRUMENTATION_EXAMPLE.md](INSTRUMENTATION_EXAMPLE.md): Practical examples
- [static/description/index.html](static/description/index.html): Odoo Apps page

### Integration
- Works with Grafana observability stack (docker-compose.observability.yml)
- Compatible with existing authentication decorators (@require_jwt, @require_session)
- No changes required to existing code (opt-in via decorator)

### Performance
- Batch span processing (512 spans per batch, 5s interval)
- Configurable sampling for production (10% recommended)
- Async export (non-blocking)
- Queue size: 2048 spans
- Export timeout: 30s

### Security
- No sensitive data in spans by default
- Configurable via environment variables
- Can be disabled globally (OTEL_ENABLED=false)
- Supports sampling for production use

---

## Future Enhancements (Planned)

### [18.0.2.0.0] - TBD
- [ ] Automatic database query instrumentation (psycopg2)
- [ ] Automatic Redis operation instrumentation
- [ ] Automatic HTTP client instrumentation (requests library)
- [ ] RabbitMQ/Celery task tracing
- [ ] Custom Grafana dashboards (JSON export)
- [ ] Alert rules for slow/failed requests
- [ ] Span processor for span filtering (exclude health checks)
- [ ] Support for multiple exporters (Jaeger, Zipkin)
- [ ] Metrics integration (request rate, duration histograms)
- [ ] Exemplar support (link metrics to traces)

### [18.0.3.0.0] - TBD
- [ ] Automatic model CRUD instrumentation (ORM events)
- [ ] SQL query attribution (which controller triggered which query)
- [ ] Profiling integration (cProfile + traces)
- [ ] Memory profiling (tracemalloc integration)
- [ ] Custom span processors (business logic hooks)
- [ ] TraceQL query builder UI
- [ ] Integration with Sentry (traces + errors)

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 18.0.1.0.0 | 2024-03-24 | Initial release with core tracing features |

---

## Contributing

To contribute to this module:

1. Follow [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
2. Add tests for new features
3. Update README.md with new configuration options
4. Update this CHANGELOG.md
5. Increment version in __manifest__.py

## License

LGPL-3 (same as Odoo)
