from celery import Celery
from celery.signals import worker_init
import xmlrpc.client
import os
import sys

app = Celery(
    'odoo_events',
    broker=os.getenv('CELERY_BROKER_URL', 'amqp://odoo:password@rabbitmq:5672//'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
)

# Configuração de filas
app.conf.task_routes = {
    'process_event_task': {'queue': 'audit_events'},
}

# ---------------------------------------------------------------------------
# OpenTelemetry Initialization
# ---------------------------------------------------------------------------
_otel_initialized = False


def _initialize_otel():
    """
    Initialize OpenTelemetry tracer for the Celery worker process.
    
    Uses the same Tempo backend as the Odoo application.
    CeleryInstrumentor automatically creates spans for task execution
    and propagates trace context from task headers.
    """
    global _otel_initialized
    if _otel_initialized:
        return

    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    if not otel_enabled:
        print("🔇 OpenTelemetry disabled for Celery worker", file=sys.stderr, flush=True)
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        service_name = os.getenv('OTEL_SERVICE_NAME', 'celery-worker')
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'tempo:4317')
        otlp_insecure = os.getenv('OTEL_EXPORTER_OTLP_INSECURE', 'true').lower() == 'true'
        environment = os.getenv('OTEL_DEPLOYMENT_ENVIRONMENT', 'development')

        resource = Resource.create({
            'service.name': service_name,
            'service.version': os.getenv('OTEL_SERVICE_VERSION', '18.0'),
            'deployment.environment': environment,
        })

        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=otlp_insecure,
        )

        provider.add_span_processor(BatchSpanProcessor(
            exporter,
            schedule_delay_millis=5000,
            max_queue_size=2048,
            max_export_batch_size=512,
        ))

        trace.set_tracer_provider(provider)

        # Auto-instrument Celery: creates spans for task run/apply_async
        CeleryInstrumentor().instrument()

        _otel_initialized = True
        # Use print because worker_init fires before Celery configures logging
        print(
            f"✅ OpenTelemetry initialized for Celery worker: "
            f"service={service_name}, endpoint={otlp_endpoint}, env={environment}",
            file=sys.stderr, flush=True,
        )

    except ImportError as e:
        print(f"⚠️  OpenTelemetry not available in Celery worker: {e}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"❌ Failed to initialize OpenTelemetry in Celery worker: {e}", file=sys.stderr, flush=True)


@worker_init.connect
def on_worker_init(**kwargs):
    """Initialize OpenTelemetry when the Celery worker process starts."""
    _initialize_otel()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.task(bind=True, max_retries=3)
def process_event_task(self, event_name, data):
    """
    Task Celery que processa eventos assíncronos.
    Conecta ao Odoo via XML-RPC e chama observer.handle_async().
    
    When OpenTelemetry is enabled, CeleryInstrumentor automatically:
    - Creates a span for this task execution
    - Links it to the parent span from the dispatcher (if trace context was propagated)
    - Records task metadata (task name, task id, queue, retries)
    """
    try:
        # Conectar ao Odoo
        url = os.environ['ODOO_URL']
        db = os.environ['ODOO_DB']
        username = os.environ['ODOO_USER']
        password = os.environ['ODOO_PASSWORD']
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        uid = common.authenticate(db, username, password, {})
        
        # Buscar observers para o evento
        observer_ids = models.execute_kw(
            db, uid, password,
            'quicksol.abstract.observer',
            'search',
            [[('_observe_events', 'in', [event_name])]]
        )
        
        # Executar handle_async de cada observer
        for observer_id in observer_ids:
            models.execute_kw(
                db, uid, password,
                observer_id,
                'handle_async',
                [event_name, data]
            )
        
        return f"Processed {event_name} with {len(observer_ids)} observers"
    
    except Exception as exc:
        # Retry com exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


if __name__ == '__main__':
    app.start()
