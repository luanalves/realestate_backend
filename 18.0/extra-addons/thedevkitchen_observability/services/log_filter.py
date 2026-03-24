# -*- coding: utf-8 -*-
"""
Logging Filter for OpenTelemetry Trace Context Injection

This module provides a logging filter that automatically adds trace_id and span_id
to all log records, enabling correlation between logs (Loki) and traces (Tempo).

The filter is automatically installed when the module is loaded.
"""

import logging
from odoo.addons.thedevkitchen_observability.services.tracer import get_trace_context

_logger = logging.getLogger(__name__)


class TraceContextFilter(logging.Filter):
    """
    Logging filter that injects trace_id and span_id into log records.
    
    This allows Loki to extract trace_id from logs and create links to Tempo traces.
    Promtail is configured to parse these fields via regex.
    
    Log format example:
        2024-03-24 10:15:30,123 INFO [trace_id=abc123...] [span_id=def456...] odoo.http: GET /api/v1/users
    
    The filter adds these fields to LogRecord:
        - trace_id: 32-char hex string (128-bit trace ID)
        - span_id: 16-char hex string (64-bit span ID)
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add trace context to log record.
        
        Args:
            record: Log record to modify
            
        Returns:
            bool: Always True (don't filter any records)
        """
        trace_context = get_trace_context()
        
        # Add trace_id and span_id to record
        record.trace_id = trace_context.get('trace_id', '')
        record.span_id = trace_context.get('span_id', '')
        
        return True


def install_trace_context_filter():
    """
    Install the trace context filter on the root logger.
    
    This function should be called once during module initialization.
    It modifies the root logger to add trace context to ALL logs.
    """
    try:
        root_logger = logging.getLogger()
        
        # Check if filter is already installed
        for f in root_logger.filters:
            if isinstance(f, TraceContextFilter):
                _logger.debug("TraceContextFilter already installed, skipping")
                return
        
        # Install filter
        trace_filter = TraceContextFilter()
        root_logger.addFilter(trace_filter)
        
        _logger.info("✅ TraceContextFilter installed on root logger")
        
    except Exception as e:
        _logger.error(f"❌ Failed to install TraceContextFilter: {e}", exc_info=True)


def configure_log_format():
    """
    Configure Odoo's log format to include trace_id and span_id.
    
    This function modifies existing log handlers to use a format that includes
    trace context. It should be called during module initialization.
    
    Note: This is optional. If Promtail uses regex parsing, the default Odoo
    format is sufficient (trace_id is added as a field in the LogRecord).
    """
    try:
        # Custom format with trace context
        # Format: timestamp level [trace_id] [span_id] logger: message
        log_format = (
            '%(asctime)s %(levelname)s '
            '[trace_id=%(trace_id)s] [span_id=%(span_id)s] '
            '%(name)s: %(message)s'
        )
        
        formatter = logging.Formatter(log_format)
        
        # Apply to all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
        
        _logger.info("✅ Log format configured with trace context")
        
    except Exception as e:
        _logger.error(f"❌ Failed to configure log format: {e}", exc_info=True)


# Auto-install filter when module is loaded
try:
    install_trace_context_filter()
    
    # Optionally configure log format (comment out if using Promtail regex parsing)
    # configure_log_format()
    
except Exception as e:
    _logger.error(f"Failed to auto-install trace context filter: {e}")
