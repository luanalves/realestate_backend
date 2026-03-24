/** @odoo-module **/

/*
 * OpenTelemetry Browser Instrumentation for Odoo
 * 
 * Initializes OpenTelemetry Web SDK to capture browser-side telemetry:
 * - HTTP requests (fetch, XMLHttpRequest)
 * - User interactions
 * - Page load performance
 * 
 * Automatically propagates W3C trace context (traceparent header) to backend,
 * enabling full-stack distributed tracing: Browser → Odoo → DB.
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { 
    ATTR_SERVICE_NAME, 
    ATTR_SERVICE_VERSION,
    ATTR_DEPLOYMENT_ENVIRONMENT 
} from '@opentelemetry/semantic-conventions';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { ZoneContextManager } from '@opentelemetry/context-zone';

let initialized = false;

/**
 * Initialize OpenTelemetry browser tracing.
 * Should be called once when the Odoo web client loads.
 */
function initializeBrowserTracing() {
    if (initialized) {
        console.log('[OTel Browser] Already initialized, skipping');
        return;
    }

    // Check if tracing is enabled
    const otelEnabled = window.OTEL_ENABLED !== undefined 
        ? window.OTEL_ENABLED 
        : true;

    if (!otelEnabled) {
        console.log('[OTel Browser] 🔇 Disabled via config');
        return;
    }

    try {
        // Get configuration from window object (set by backend template)
        const serviceName = window.OTEL_SERVICE_NAME || 'odoo-browser';
        const serviceVersion = window.OTEL_SERVICE_VERSION || '18.0';
        const environment = window.OTEL_DEPLOYMENT_ENVIRONMENT || 'development';
        const otlpEndpoint = window.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces';

        // Create resource with service identification
        const resource = new Resource({
            [ATTR_SERVICE_NAME]: serviceName,
            [ATTR_SERVICE_VERSION]: serviceVersion,
            [ATTR_DEPLOYMENT_ENVIRONMENT]: environment,
        });

        // Create tracer provider
        const provider = new WebTracerProvider({
            resource: resource,
        });

        // Configure OTLP HTTP exporter (gRPC not supported in browser)
        const exporter = new OTLPTraceExporter({
            url: otlpEndpoint,
            headers: {}, // Add auth headers if needed
        });

        // Add batch span processor (same tuning as backend)
        provider.addSpanProcessor(new BatchSpanProcessor(exporter, {
            scheduledDelayMillis: 5000,
            maxQueueSize: 2048,
            maxExportBatchSize: 512,
        }));

        // Register the provider
        provider.register({
            contextManager: new ZoneContextManager(),
        });

        // Register auto-instrumentations
        registerInstrumentations({
            instrumentations: [
                // Instrument fetch API
                new FetchInstrumentation({
                    propagateTraceHeaderCorsUrls: /.*/,  // Propagate to all origins
                    clearTimingResources: true,
                    applyCustomAttributesOnSpan: (span, request, result) => {
                        // Add Odoo-specific attributes
                        if (request.url && request.url.includes('/api/')) {
                            span.setAttribute('odoo.api', true);
                        }
                    },
                }),
                // Instrument XMLHttpRequest (Odoo's RPC uses this)
                new XMLHttpRequestInstrumentation({
                    propagateTraceHeaderCorsUrls: /.*/,
                    clearTimingResources: true,
                    applyCustomAttributesOnSpan: (span, xhr) => {
                        // Add Odoo-specific attributes
                        if (xhr.responseURL && xhr.responseURL.includes('/web/dataset/call_kw')) {
                            span.setAttribute('odoo.rpc', true);
                            span.setAttribute('odoo.rpc.type', 'call_kw');
                        }
                        if (xhr.responseURL && xhr.responseURL.includes('/jsonrpc')) {
                            span.setAttribute('odoo.rpc', true);
                            span.setAttribute('odoo.rpc.type', 'jsonrpc');
                        }
                    },
                }),
            ],
        });

        initialized = true;
        console.log(
            `✅ OpenTelemetry Browser initialized: service=${serviceName}, ` +
            `endpoint=${otlpEndpoint}, env=${environment}`
        );

    } catch (error) {
        console.error('❌ Failed to initialize OpenTelemetry Browser:', error);
    }
}

// Auto-initialize when module is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeBrowserTracing);
} else {
    // DOMContentLoaded already fired
    initializeBrowserTracing();
}

// Export for manual initialization if needed
export default {
    initialize: initializeBrowserTracing,
    isInitialized: () => initialized,
};
