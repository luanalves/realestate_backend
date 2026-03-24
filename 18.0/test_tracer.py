import os
print("=== OpenTelemetry Environment Check ===")
print(f"OTEL_ENABLED: {os.getenv('OTEL_ENABLED')}")
print(f"OTEL_SERVICE_NAME: {os.getenv('OTEL_SERVICE_NAME')}")
print(f"OTEL_EXPORTER_OTLP_ENDPOINT: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')}")

try:
    from odoo.addons.thedevkitchen_observability.services import tracer
    print("\n=== Tracer Module Import ===")
    print(f"Tracer module: {tracer}")
    print(f"TracerProvider initialized: {hasattr(tracer, 'TRACER_PROVIDER')}")
    if hasattr(tracer, 'TRACER_PROVIDER'):
        print(f"TracerProvider: {tracer.TRACER_PROVIDER}")
    
    # Test get_tracer function
    test_tracer = tracer.get_tracer()
    print(f"\nget_tracer() result: {test_tracer}")
    
except Exception as e:
    print(f"Error importing or testing tracer: {e}")
    import traceback
    traceback.print_exc()
