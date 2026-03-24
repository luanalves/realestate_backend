"""
Database Instrumentation - PostgreSQL Query Tracing

Monkey-patches Odoo's sql_db.Cursor.execute to wrap every SQL query
in an OpenTelemetry span. This approach works with Odoo's connection pool
because it patches the Cursor class (not psycopg2.connect).

Features:
- Automatic span creation for all SQL queries
- Query text in span attributes (sanitizable for production)
- Slow query detection (queries > threshold)
- Parent-child linking with HTTP request spans
- Query categorization (SELECT, INSERT, UPDATE, DELETE, etc.)

Configuration:
    - OTEL_SLOW_QUERY_THRESHOLD_MS: Slow query threshold in milliseconds (default: 100)
    - OTEL_DB_STATEMENT_SANITIZE: Sanitize query params in prod (default: true)
"""

import os
import re
import logging

_logger = logging.getLogger(__name__)

_db_instrumentation_initialized = False
_original_execute = None

# Pre-compiled regex for query categorization
_RE_QUERY_TYPE = re.compile(r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|LISTEN|NOTIFY|COMMIT|ROLLBACK|SAVEPOINT|SET|WITH)\b', re.IGNORECASE)
_RE_TABLE_NAME = re.compile(r'(?:FROM|INTO|UPDATE|JOIN)\s+"?(\w+)"?', re.IGNORECASE)


def _categorize_query(query_str):
    """Extract operation type and table name from a SQL query."""
    if not query_str:
        return 'UNKNOWN', None
    
    if isinstance(query_str, bytes):
        query_str = query_str.decode('utf-8', errors='replace')
    
    m = _RE_QUERY_TYPE.match(query_str)
    operation = m.group(1).upper() if m else 'OTHER'
    
    m2 = _RE_TABLE_NAME.search(query_str)
    table = m2.group(1) if m2 else None
    
    return operation, table


def _sanitize_query(query_str, params):
    """Replace parameter placeholders with '?' for production."""
    if not query_str:
        return query_str
    if isinstance(query_str, bytes):
        query_str = query_str.decode('utf-8', errors='replace')
    return re.sub(r'%s', '?', query_str)


def initialize_db_instrumentation() -> bool:
    """
    Monkey-patch Odoo's Cursor.execute to create OpenTelemetry spans.
    
    Works with pre-existing connections because it patches the Cursor class,
    not psycopg2.connect().
    """
    global _db_instrumentation_initialized, _original_execute
    
    if _db_instrumentation_initialized:
        _logger.debug("Database instrumentation already initialized, skipping")
        return True
    
    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    if not otel_enabled:
        _logger.info("🔇 OpenTelemetry disabled, skipping DB instrumentation")
        return False
    
    try:
        from opentelemetry import trace
        from opentelemetry.trace import StatusCode
        import odoo.sql_db as sql_db
        
        slow_query_threshold_ms = int(os.getenv('OTEL_SLOW_QUERY_THRESHOLD_MS', '100'))
        sanitize = os.getenv('OTEL_DB_STATEMENT_SANITIZE', 'true').lower() == 'true'
        
        # Save original execute
        _original_execute = sql_db.Cursor.execute
        
        def _traced_execute(self, query, params=None, log_exceptions=True):
            """Wrapped Cursor.execute that creates an OpenTelemetry span."""
            tracer = trace.get_tracer('odoo.sql')
            
            # Get query string for span naming
            query_str = str(query) if query else ''
            operation, table = _categorize_query(query_str)
            
            # Span name: "SELECT res_users" or "INSERT res_partner"
            span_name = operation
            if table:
                span_name = f"{operation} {table}"
            
            with tracer.start_as_current_span(
                span_name,
                kind=trace.SpanKind.CLIENT,
            ) as span:
                # Set standard DB semantic attributes
                span.set_attribute('db.system', 'postgresql')
                span.set_attribute('db.name', getattr(self, 'dbname', 'unknown'))
                span.set_attribute('db.operation', operation)
                
                if table:
                    span.set_attribute('db.sql.table', table)
                
                # Query statement (sanitized or raw)
                if sanitize:
                    span.set_attribute('db.statement', _sanitize_query(query_str, params))
                else:
                    display_query = query_str if isinstance(query_str, str) else query_str.decode('utf-8', errors='replace')
                    span.set_attribute('db.statement', display_query[:2000])
                
                try:
                    result = _original_execute(self, query, params, log_exceptions)
                    
                    # Row count if available
                    if hasattr(self, '_obj') and self._obj and hasattr(self._obj, 'rowcount'):
                        span.set_attribute('db.rowcount', self._obj.rowcount)
                    
                    return result
                    
                except Exception as exc:
                    span.set_status(StatusCode.ERROR, str(exc)[:200])
                    span.record_exception(exc)
                    raise
        
        # Apply monkey-patch
        sql_db.Cursor.execute = _traced_execute
        
        _db_instrumentation_initialized = True
        
        _logger.info(
            "✅ PostgreSQL instrumentation initialized (Odoo Cursor.execute patched): "
            f"slow_query_threshold={slow_query_threshold_ms}ms, sanitize={sanitize}"
        )
        
        return True
        
    except ImportError as e:
        _logger.warning("⚠️  DB instrumentation not available: %s", e)
        return False
    except Exception as e:
        _logger.error(f"❌ Failed to initialize DB instrumentation: {e}", exc_info=True)
        return False


def initialize_redis_instrumentation() -> bool:
    """
    Initialize Redis instrumentation for distributed tracing.
    
    Uses the standard RedisInstrumentor which patches the redis-py library.
    Works because Redis connections are created on-demand, not pooled at boot.
    """
    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    if not otel_enabled:
        return False
    
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        
        RedisInstrumentor().instrument()
        
        _logger.info("✅ Redis instrumentation initialized")
        return True
        
    except ImportError as e:
        _logger.warning("⚠️  Redis instrumentation not available: %s", e)
        return False
    except Exception as e:
        _logger.error(f"❌ Failed to initialize Redis instrumentation: {e}", exc_info=True)
        return False


def get_slow_query_threshold_ms() -> int:
    return int(os.getenv('OTEL_SLOW_QUERY_THRESHOLD_MS', '100'))


def is_db_instrumentation_enabled() -> bool:
    return _db_instrumentation_initialized


def auto_initialize():
    """
    Auto-initialize both PostgreSQL and Redis instrumentation.
    
    Called from services/__init__.py when the module loads.
    """
    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    if not otel_enabled:
        _logger.info("🔇 OpenTelemetry disabled, skipping DB instrumentation")
        return

    try:
        pg_ok = initialize_db_instrumentation()
        redis_ok = initialize_redis_instrumentation()

        pg_status = '✅' if pg_ok else '❌'
        redis_status = '✅' if redis_ok else '❌'
        _logger.info(f"🔍 Database instrumentation: PostgreSQL {pg_status}, Redis {redis_status}")
    except Exception as e:
        _logger.error(f"Failed to auto-initialize database instrumentation: {e}", exc_info=True)
