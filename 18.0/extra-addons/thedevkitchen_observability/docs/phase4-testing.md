# Phase 4: Frontend Instrumentation - Testing Guide

## Overview
Phase 4 implements browser-side OpenTelemetry instrumentation to capture client-side latency and enable full-stack distributed tracing (Browser → Odoo → Database).

## Architecture

### Components
1. **browser_tracer.js**: OpenTelemetry Web SDK initialization with auto-instrumentation
2. **opentelemetry-bundle.js**: Webpack bundled OTel dependencies (139KB)
3. **otel_loader.js**: Odoo module that initializes OTel when web client loads
4. **otel_browser_config.xml**: Template that injects config into HTML `<head>`
5. **otlp_proxy_controller.py**: CORS-safe proxy endpoint (`/api/otel/traces`)
6. **otel_config.py**: Helper model to access environment variables in templates

### Data Flow
```
Browser (fetch/XHR)
  ├─> Auto-instrumentation captures request
  ├─> Injects traceparent header
  ├─> Creates browser span
  └─> Exports to /api/otel/traces (OTLP/HTTP)
         └─> Odoo proxy forwards to Tempo:4318
                └─> Stored in Tempo
                      └─> Visible in Grafana
```

## Automated Tests

### 1. Connectivity Tests
```bash
cd 18.0
python3 test_browser_otel.py
```

**Expected Output:**
```
✅ All tests passed!
- OTEL configuration found in HTML
- CORS preflight returns 204
- POST endpoint returns 200
```

**What it tests:**
- HTML injection of window.OTEL_* configuration
- CORS headers (Access-Control-Allow-Origin: *)
- Proxy endpoint connectivity

## Manual Browser Tests

### 2. Browser Initialization
**Purpose:** Verify OpenTelemetry initializes in the browser

**Steps:**
1. Open http://localhost:8069 in Chrome/Firefox
2. Open DevTools Console (Cmd+Option+J or F12)
3. Look for initialization message

**Expected Output:**
```
✅ OpenTelemetry Browser initialized
   Service: odoo-browser
   Environment: development
   Endpoint: http://localhost:8069/api/otel/traces
```

**Troubleshooting:**
- If no message: Check Console for errors
- Check if bundle loaded: Look for `opentelemetry-bundle.js` in Network tab
- Verify config injection: Type `window.OTEL_ENABLED` in console (should be `true`)

### 3. Trace Export
**Purpose:** Verify browser sends traces to Odoo proxy

**Steps:**
1. Open DevTools Network tab
2. Enable "Preserve log"
3. Filter by `/api/otel/traces`
4. Perform actions: login, navigate menus, make API calls
5. Observe POST requests

**Expected Behavior:**
- POST requests to `/api/otel/traces` every 5 seconds (batch export)
- Request headers include: `Content-Type: application/x-protobuf`
- Response status: 200 OK
- Request payload: Binary protobuf data

**Troubleshooting:**
- No requests: Check console for OTel initialization errors
- 404 errors: Verify Odoo module is updated (`docker compose exec odoo odoo -d realestate -u thedevkitchen_observability`)
- 500 errors: Check Odoo logs for proxy forwarding issues

### 4. TraceParent Header Injection
**Purpose:** Verify auto-instrumentation injects W3C Trace Context headers

**Steps:**
1. Open DevTools Network tab
2. Make an authenticated API call (e.g., GET /api/v1/me)
3. Click the request in Network tab
4. View Request Headers

**Expected Header:**
```
traceparent: 00-<trace-id>-<span-id>-01
```

**Example:**
```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

**Format:**
- `00`: Version
- `4bf92f...`: Trace ID (32 hex chars)
- `00f067...`: Span ID (16 hex chars)
- `01`: Sampled flag

**Troubleshooting:**
- No traceparent: Check FetchInstrumentation is enabled in browser_tracer.js
- Different format: OpenTelemetry uses W3C Trace Context standard

### 5. Full-Stack Trace Propagation
**Purpose:** Verify browser spans link to backend spans (distributed tracing)

**Steps:**
1. Make an API request from browser (e.g., login)
2. Note the `traceparent` header from Network tab (copy trace ID)
3. Query Tempo API with the trace ID:
   ```bash
   # Replace TRACE_ID with the 32-character hex string from traceparent
   curl "http://localhost:3200/api/traces/TRACE_ID" | jq
   ```
4. Verify the trace contains spans from multiple services:
   - `odoo-browser` (root span)
   - `odoo-development` (HTTP handler span)
   - `postgres` (SQL query spans)

**Expected Trace Structure:**
```
odoo-browser: GET /api/v1/me
  └─> odoo-development: GET /api/v1/me
        ├─> postgres: SELECT FROM res_users
        └─> postgres: SELECT FROM res_partner
```

**Troubleshooting:**
- Only browser span: Backend not propagating context (check require_jwt decorator)
- Missing SQL spans: database instrumentation disabled (check Phase 2)
- Disconnected traces: Trace context not propagating (check traceparent injection)

## Tempo Query Tests

### 6. Search Browser Traces
**Purpose:** Verify browser traces are stored in Tempo

**Query:**
```bash
cd 18.0
python3 check_tempo_traces.py
```

**Manual Query (if script fails):**
```python
import urllib.request, json, time
start = int(time.time()) - 600
end = int(time.time())
url = f'http://localhost:3200/api/search?q=%7Bresource.service.name%3D%22odoo-browser%22%7D&start={start}&end={end}'
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())
    print(f"Browser traces: {len(data['traces'])}")
```

**Expected:**
- After browser activity: `Browser traces: >0`
- Before any activity: `Browser traces: 0` (expected)

## Grafana Verification

### 7. Visualize in Grafana
**Purpose:** See traces in Grafana UI

**Steps:**
1. Open http://localhost:3000 (Grafana)
2. Login: admin/admin
3. Go to Explore → Data source: Tempo
4. Query:
   ```
   {resource.service.name="odoo-browser"}
   ```
5. Select a trace to view waterfall diagram

**Expected:**
- Traces appear with `odoo-browser` service name
- Clicking trace shows span details (URL, method, status)
- Connected traces show browser→backend→database spans

## Performance Validation

### 8. Bundle Size
**Metric:** opentelemetry-bundle.js size

**Command:**
```bash
ls -lh static/lib/opentelemetry-bundle.js
```

**Expected:** ~139KB (minified)

**Acceptable Range:** 100-200KB

**Impact:**
- Loaded async, non-blocking
- Cached by browser
- Negligible impact on page load

### 9. Span Export Rate
**Metric:** Number of POST requests to /api/otel/traces

**Observation:**
- Look at Network tab over 30 seconds
- Count POST requests to `/api/otel/traces`

**Expected:**
- 1 request per 5 seconds (BatchSpanProcessor default delay)
- Only when spans are generated (no activity = no exports)

**Configuration** (browser_tracer.js):
```javascript
scheduledDelayMillis: 5000,  // Export every 5s
maxQueueSize: 2048,          // Buffer up to 2048 spans
maxExportBatchSize: 512,     // Send 512 spans per batch
```

## Common Issues

### Browser Console Errors

**Error:** `Failed to load resource: net::ERR_BLOCKED_BY_CLIENT`
**Cause:** Ad blocker blocking OTLP requests
**Fix:** Whitelist localhost or disable ad blocker for localhost

**Error:** `CORS policy: No 'Access-Control-Allow-Origin' header`
**Cause:** CORS not configured on proxy endpoint
**Fix:** Verify otlp_proxy_controller.py has `cors='*'` in `@http.route`

**Error:** `Cannot read property 'initialize' of undefined`
**Cause:** opentelemetry-bundle.js failed to load
**Fix:** Check Network tab, verify bundle exists in `static/lib/`, rebuild with `npm run build`

### Odoo Errors

**Error:** `QWebException: Can not compile expression: request.env.get`
**Cause:** Template trying to access OS environment incorrectly
**Fix:** Use otel.config.helper model (already fixed in otel_browser_config.xml)

**Error:** `ModuleNotFoundError: No module named 'requests'`
**Cause:** Python `requests` library not installed in Odoo container
**Fix:** Should be pre-installed in Odoo 18 image

### Network Issues

**Error:** `Connection refused` when proxy forwards to Tempo
**Cause:** Tempo not running or not accessible from Odoo container
**Fix:** Check `docker compose -f docker-compose.observability.yml ps tempo`

## Success Criteria

✅ **Phase 4 is complete when:**

1. Browser console shows "✅ OpenTelemetry Browser initialized"
2. Network tab shows POST requests to `/api/otel/traces` (status 200)
3. API requests include `traceparent` header
4. Tempo contains traces with service.name="odoo-browser"
5. Grafana shows full-stack traces (browser→backend→database)
6. No console errors or CORS issues
7. Page load performance is acceptable (<200ms overhead)

## Next Steps

After confirming Phase 4 works:

1. **Phase 5:** Advanced Instrumentation (Database query details, Redis operations)
2. **Phase 6:** Alerting & Dashboards (SLO tracking, performance alerts)
3. **Phase 7:** Production Readiness (Sampling, data retention, security)

## References

- ADR-025: OpenTelemetry Distributed Tracing
- OpenTelemetry JS: https://opentelemetry.io/docs/instrumentation/js/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- OTLP Protocol: https://opentelemetry.io/docs/specs/otlp/
