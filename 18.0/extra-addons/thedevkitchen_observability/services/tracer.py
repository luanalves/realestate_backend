# -*- coding: utf-8 -*-
"""
OpenTelemetry Tracer Configuration and Utilities

This module provides:
- TracerProvider initialization with OTLP exporter
- Decorator @trace_http_request for controller methods
- Context propagation utilities (W3C Trace Context)
- Helper functions to access current span
"""

import os
import logging
import functools
from typing import Optional, Callable, Any

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
_logger.info("🔍 thedevkitchen_observability.services.tracer module imported")

# Global tracer instance
_tracer = None
_tracer_provider = None


def initialize_tracer():
    """
    Initialize OpenTelemetry TracerProvider with OTLP gRPC exporter.
    
    This function should be called once during module initialization.
    Configuration is read from environment variables:
    
    - OTEL_ENABLED: Enable/disable tracing (default: true)
    - OTEL_SERVICE_NAME: Service identifier (default: odoo)
    - OTEL_SERVICE_VERSION: Service version (default: 18.0)
    - OTEL_DEPLOYMENT_ENVIRONMENT: Environment (default: development)
    - OTEL_EXPORTER_OTLP_ENDPOINT: Tempo endpoint (default: tempo:4317)
    - OTEL_EXPORTER_OTLP_INSECURE: Use insecure connection (default: true)
    - OTEL_TRACES_SAMPLER: Sampling strategy (default: always_on)
    - OTEL_LOG_LEVEL: Tracer log level (default: info)
    
    Returns:
        Tracer instance or None if tracing is disabled
    """
    global _tracer, _tracer_provider
    
    # Check if tracing is enabled
    if not _is_tracing_enabled():
        _logger.info("🔕 OpenTelemetry tracing is DISABLED (OTEL_ENABLED=false)")
        return None
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ALWAYS_OFF, TraceIdRatioBased, ParentBased
        
        # Get configuration from environment
        service_name = os.getenv('OTEL_SERVICE_NAME', 'odoo')
        service_version = os.getenv('OTEL_SERVICE_VERSION', '18.0')
        deployment_env = os.getenv('OTEL_DEPLOYMENT_ENVIRONMENT', 'development')
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'tempo:4317')
        otlp_insecure = os.getenv('OTEL_EXPORTER_OTLP_INSECURE', 'true').lower() == 'true'
        sampler_type = os.getenv('OTEL_TRACES_SAMPLER', 'always_on')
        
        # Create resource with service identification
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": deployment_env,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })
        
        # Configure sampler
        if sampler_type == 'always_on':
            sampler = ALWAYS_ON
        elif sampler_type == 'always_off':
            sampler = ALWAYS_OFF
        elif sampler_type.startswith('traceidratio'):
            # Format: traceidratio:0.1 (10% sampling)
            ratio = float(sampler_type.split(':')[1]) if ':' in sampler_type else 1.0
            sampler = ParentBased(root=TraceIdRatioBased(ratio))
        else:
            sampler = ALWAYS_ON
        
        # Create TracerProvider
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=otlp_insecure,
        )
        
        # Add BatchSpanProcessor for performance
        # Exports spans in batches to reduce overhead
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            schedule_delay_millis=5000,  # Export every 5 seconds
            max_export_batch_size=512,
            export_timeout_millis=30000,
        )
        _tracer_provider.add_span_processor(span_processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(_tracer_provider)
        
        # Get tracer instance
        _tracer = trace.get_tracer(
            instrumenting_module_name="odoo.addons.thedevkitchen_observability",
            instrumenting_library_version="1.0.0",
        )
        
        _logger.info(
            f"✅ OpenTelemetry initialized: service={service_name}, "
            f"endpoint={otlp_endpoint}, sampler={sampler_type}, env={deployment_env}"
        )
        
        return _tracer
        
    except ImportError as e:
        _logger.error(
            f"❌ OpenTelemetry dependencies not installed: {e}. "
            "Install with: pip install -r extra-addons/thedevkitchen_observability/requirements.txt"
        )
        return None
    except Exception as e:
        _logger.error(f"❌ Failed to initialize OpenTelemetry tracer: {e}", exc_info=True)
        return None


def get_tracer():
    """
    Get the global tracer instance.
    
    Returns:
        Tracer instance or None if tracing is disabled/failed
    """
    global _tracer
    if _tracer is None:
        initialize_tracer()
    return _tracer


def get_current_span():
    """
    Get the current active span from context.
    
    Returns:
        Span instance or None if no active span
    """
    try:
        from opentelemetry import trace
        return trace.get_current_span()
    except ImportError:
        return None


def get_trace_context():
    """
    Get current trace context (trace_id, span_id) as dict.
    
    Useful for injecting into logs, error reports, etc.
    
    Returns:
        dict: {'trace_id': str, 'span_id': str} or empty dict if no context
    """
    span = get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        return {
            'trace_id': format(ctx.trace_id, '032x'),
            'span_id': format(ctx.span_id, '016x'),
        }
    return {}


def trace_http_request(func: Callable) -> Callable:
    """
    Decorator to automatically trace HTTP controller methods.
    
    Creates a span for the HTTP request with semantic conventions:
    - http.method: GET, POST, etc.
    - http.route: /api/v1/users
    - http.url: Full URL
    - http.status_code: 200, 404, etc.
    - http.user_agent: User agent header
    - http.client_ip: Client IP address
    - error: true (if exception occurs)
    - exception.type, exception.message (if exception)
    
    Also propagates W3C Trace Context from incoming headers (traceparent, tracestate).
    
    Usage:
        @http.route('/api/v1/users', type='http', auth='none', methods=['GET'])
        @require_jwt
        @require_session
        @trace_http_request
        def list_users(self, **kwargs):
            return request.make_json_response({'users': [...]})
    
    Args:
        func: Controller method to decorate
        
    Returns:
        Wrapped function with tracing
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        
        # If tracing is disabled, just call the original function
        if not tracer or not _is_tracing_enabled():
            return func(*args, **kwargs)
        
        try:
            from opentelemetry import trace
            from opentelemetry.trace import Status, StatusCode
            from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
            
            # Extract trace context from incoming headers (W3C Trace Context)
            carrier = {}
            if hasattr(request, 'httprequest') and request.httprequest:
                carrier = dict(request.httprequest.headers)
            
            propagator = TraceContextTextMapPropagator()
            context = propagator.extract(carrier=carrier)
            
            # Get HTTP method and route
            http_method = request.httprequest.method if hasattr(request, 'httprequest') else 'UNKNOWN'
            http_route = request.httprequest.path if hasattr(request, 'httprequest') else func.__name__
            
            # Create span with semantic naming: HTTP GET /api/v1/users
            span_name = f"{http_method} {http_route}"
            
            # Start span with extracted context
            with tracer.start_as_current_span(span_name, context=context) as span:
                # Set HTTP semantic attributes
                span.set_attribute("http.method", http_method)
                span.set_attribute("http.route", http_route)
                
                if hasattr(request, 'httprequest'):
                    span.set_attribute("http.url", request.httprequest.url)
                    span.set_attribute("http.scheme", request.httprequest.scheme)
                    span.set_attribute("http.target", request.httprequest.full_path)
                    
                    # User agent
                    user_agent = request.httprequest.headers.get('User-Agent', '')
                    if user_agent:
                        span.set_attribute("http.user_agent", user_agent)
                    
                    # Client IP
                    client_ip = request.httprequest.remote_addr
                    if client_ip:
                        span.set_attribute("http.client_ip", client_ip)
                
                # Add user context if available
                if hasattr(request, 'session') and request.session.uid:
                    span.set_attribute("enduser.id", str(request.session.uid))
                    if hasattr(request.env, 'user'):
                        span.set_attribute("enduser.name", request.env.user.name or '')
                
                try:
                    # Call original function
                    result = func(*args, **kwargs)
                    
                    # Set status code (if result is a Response object)
                    if hasattr(result, 'status_code'):
                        status_code = int(result.status_code.split()[0]) if isinstance(result.status_code, str) else result.status_code
                        span.set_attribute("http.status_code", status_code)
                        
                        # Set span status based on HTTP status
                        if status_code >= 500:
                            span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))
                        elif status_code >= 400:
                            span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))
                        else:
                            span.set_status(Status(StatusCode.OK))
                    else:
                        span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error", True)
                    span.set_attribute("exception.type", type(e).__name__)
                    span.set_attribute("exception.message", str(e))
                    
                    # Re-raise exception
                    raise
                    
        except ImportError:
            # OpenTelemetry not available, just call original function
            _logger.warning("OpenTelemetry not available, tracing disabled for this request")
            return func(*args, **kwargs)
    
    return wrapper


def _is_tracing_enabled() -> bool:
    """
    Check if tracing is enabled via environment variable.
    
    Returns:
        bool: True if OTEL_ENABLED is not explicitly set to 'false'
    """
    return os.getenv('OTEL_ENABLED', 'true').lower() != 'false'


# Utility functions for manual instrumentation

def add_span_attribute(key: str, value: Any):
    """
    Add custom attribute to current span.
    
    Usage:
        add_span_attribute('user.role', 'admin')
        add_span_attribute('query.count', 42)
    
    Args:
        key: Attribute key (use dot notation for namespacing)
        value: Attribute value (str, int, float, bool)
    """
    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None):
    """
    Add event to current span.
    
    Events are timestamped annotations that can be added to spans
    to mark significant moments during request processing.
    
    Usage:
        add_span_event('cache.hit', {'cache.key': 'user:123'})
        add_span_event('database.query.start', {'query': 'SELECT * FROM users'})
    
    Args:
        name: Event name
        attributes: Optional dictionary of attributes
    """
    span = get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def create_child_span(name: str, attributes: Optional[dict] = None):
    """
    Create a child span for detailed operation tracking.
    
    Usage:
        tracer = get_tracer()
        with create_child_span('database.query') as span:
            span.set_attribute('db.statement', 'SELECT * FROM users')
            result = cr.execute(query)
    
    Args:
        name: Span name
        attributes: Optional initial attributes
        
    Returns:
        Context manager for the span
    """
    tracer = get_tracer()
    if not tracer:
        # Return no-op context manager
        from contextlib import nullcontext
        return nullcontext()
    
    span = tracer.start_span(name)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    return trace.use_span(span, end_on_exit=True)


# =============================================================================
# AUTO-INITIALIZATION
# =============================================================================
# Initialize tracer automatically when module is imported
# This ensures tracing works even if post_init_hook is not called
try:
    if _is_tracing_enabled():
        initialize_tracer()
except Exception as e:
    _logger.warning(f"Failed to auto-initialize OpenTelemetry tracer: {e}")
