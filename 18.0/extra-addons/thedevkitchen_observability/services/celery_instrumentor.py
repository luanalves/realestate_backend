"""
Celery Client Instrumentation (Odoo side)

Instruments the Celery client calls made from Odoo (apply_async, delay)
so that trace context is automatically propagated to Celery worker tasks.

The CeleryInstrumentor hooks into Celery signals:
- before_task_publish: Injects traceparent header into task headers
- task_prerun / task_postrun: Creates spans (worker side, handled by worker's own instrumentor)

This module only handles the CLIENT side (task dispatch from Odoo).
The WORKER side instrumentation lives in celery_worker/tasks.py.
"""

import os
import logging

_logger = logging.getLogger(__name__)

_celery_instrumentation_initialized = False


def initialize_celery_instrumentation() -> bool:
    """
    Initialize Celery client-side instrumentation in the Odoo process.
    
    This instruments apply_async calls so that W3C trace context
    (traceparent header) is injected into task message headers,
    allowing the Celery worker to link its task span as a child
    of the HTTP request span that triggered the async event.
    """
    global _celery_instrumentation_initialized

    if _celery_instrumentation_initialized:
        _logger.debug("Celery client instrumentation already initialized, skipping")
        return True

    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    if not otel_enabled:
        return False

    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()

        _celery_instrumentation_initialized = True
        _logger.info("✅ Celery client instrumentation initialized (trace context propagation)")
        return True

    except ImportError as e:
        _logger.warning("⚠️  Celery instrumentation not available: %s", e)
        return False
    except Exception as e:
        _logger.error("❌ Failed to initialize Celery client instrumentation: %s", e, exc_info=True)
        return False


def is_celery_instrumentation_enabled() -> bool:
    return _celery_instrumentation_initialized
