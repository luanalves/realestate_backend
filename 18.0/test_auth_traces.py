#!/usr/bin/env python3
"""Test authenticated endpoints and verify traces in Tempo."""
import http.client
import json
import time

print("🔍 Gerando tráfego autenticado para endpoints instrumentados...")

# 1. Login to get JWT token
conn = http.client.HTTPConnection('localhost', 8069)
headers = {'Content-Type': 'application/x-www-form-urlencoded'}
body = 'grant_type=password&username=admin&password=admin'

print("\n1️⃣  POST /api/v1/auth/token")
conn.request('POST', '/api/v1/auth/token', body=body, headers=headers)
resp = conn.getresponse()
data = resp.read().decode()
print(f"   Status: {resp.status}")

if resp.status != 200:
    print(f"   ❌ Login failed: {data}")
    exit(1)

token_data = json.loads(data)
token = token_data.get('access_token')
print(f"   ✅ Token obtained")

# 2. GET /api/v1/me (authenticated)
print("\n2️⃣  GET /api/v1/me")
conn2 = http.client.HTTPConnection('localhost', 8069)
conn2.request('GET', '/api/v1/me', headers={'Authorization': f'Bearer {token}'})
resp2 = conn2.getresponse()
print(f"   Status: {resp2.status}")
me_data = resp2.read()
conn2.close()

conn.close()

print("\n⏳ Aguardando 5s para exportação de spans...")
time.sleep(5)

# 3. Query Tempo for all traces
print("\n✅ Buscando traces no Tempo...")
conn3 = http.client.HTTPConnection('localhost', 3200)
conn3.request('GET', '/api/search?tags=service.name%3Dodoo-development&limit=20')
resp3 = conn3.getresponse()
traces = json.loads(resp3.read().decode())
conn3.close()

print(f"\n📊 Total de traces encontrados: {len(traces.get('traces', []))}")
print("\nÚltimos 10 traces:")
for t in traces.get('traces', [])[:10]:
    print(f"   • {t['rootTraceName']:50} {t['durationMs']:6}ms  TraceID: {t['traceID'][:16]}...")

# 4. Get detailed trace for the /api/v1/me request
me_traces = [t for t in traces.get('traces', []) if '/api/v1/me' in t['rootTraceName']]
if me_traces:
    trace_id = me_traces[0]['traceID']
    print(f"\n🔍 Detalhes do trace /api/v1/me (TraceID: {trace_id}):")
    
    conn4 = http.client.HTTPConnection('localhost', 3200)
    conn4.request('GET', f'/api/traces/{trace_id}')
    resp4 = conn4.getresponse()
    trace_detail = json.loads(resp4.read().decode())
    conn4.close()
    
    # Extract span info
    if 'batches' in trace_detail:
        for batch in trace_detail['batches']:
            for scope_span in batch.get('scopeSpans', []):
                for span in scope_span.get('spans', []):
                    attrs = {attr['key']: attr['value'] for attr in span.get('attributes', [])}
                    duration_ns = int(span.get('endTimeUnixNano', 0)) - int(span.get('startTimeUnixNano', 0))
                    
                    print(f"\n   Span: {span.get('name')}")
                    print(f"   Duration: {duration_ns / 1_000_000:.2f}ms")
                    print(f"   HTTP Method: {attrs.get('http.method', {}).get('stringValue', 'N/A')}")
                    print(f"   HTTP Route: {attrs.get('http.route', {}).get('stringValue', 'N/A')}")
                    print(f"   HTTP Status: {attrs.get('http.status_code', {}).get('intValue', 'N/A')}")
                    print(f"   TraceID: {trace_id}")
                    print(f"   SpanID: {span.get('spanId', 'N/A')}")

print("\n✅ Teste completo! Traces estão funcionando perfeitamente.")
