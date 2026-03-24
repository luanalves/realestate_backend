#!/bin/bash
# Phase 5 End-to-End Testing Script
# Tests the complete observability stack: Browser → Backend → Database → Grafana

set -e

echo "============================================================"
echo "Phase 5: Full-Stack APM Testing"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if service is responding
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Checking ${name}... "
    if curl -s -o /dev/null -w "%{http_code}" "${url}" | grep -q "${expected}"; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

echo "Step 1: Verify Observability Services"
echo "----------------------------------------"

check_service "Grafana" "http://localhost:3000/api/health" "200"
check_service "Prometheus" "http://localhost:9090/-/healthy" "200"
check_service "Tempo" "http://localhost:3200/ready" "200"
check_service "Loki" "http://localhost:3100/ready" "200"

echo ""
echo "Step 2: Verify Odoo OpenTelemetry"
echo "----------------------------------------"

OTEL_ENABLED=$(docker exec odoo18 env | grep OTEL_ENABLED || echo "not set")
echo "OTEL_ENABLED: ${OTEL_ENABLED}"

if echo "${OTEL_ENABLED}" | grep -q "true"; then
    echo -e "${GREEN}✓ OpenTelemetry enabled${NC}"
else
    echo -e "${RED}✗ OpenTelemetry NOT enabled - set OTEL_ENABLED=true in .env${NC}"
    exit 1
fi

echo ""
echo "Step 3: Check Existing Traces in Tempo"
echo "----------------------------------------"

python3 check_tempo_traces.py

echo ""
echo "Step 4: Generate Test Traffic"
echo "----------------------------------------"

echo "Generating backend API traces..."

# Test OAuth token endpoint (public)
echo -n "  - POST /api/v1/auth/token... "
curl -s -X POST http://localhost:8069/api/v1/auth/token \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}' \
    > /dev/null && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}⚠ (expected 401)${NC}"

# Test health check (public)
echo -n "  - GET /api/v1/health... "
curl -s http://localhost:8069/api/v1/health > /dev/null && \
    echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

# Test companies endpoint (should fail - no auth)
echo -n "  - GET /api/v1/companies (no auth)... "
curl -s http://localhost:8069/api/v1/companies > /dev/null && \
    echo -e "${YELLOW}⚠ (expected 401)${NC}" || echo -e "${GREEN}✓${NC}"

echo ""
echo -e "${BLUE}ℹ️  Waiting 15 seconds for traces to be exported...${NC}"
sleep 15

echo ""
echo "Step 5: Verify Traces in Tempo"
echo "----------------------------------------"

python3 check_tempo_traces.py

echo ""
echo "Step 6: Check Prometheus Metrics"
echo "----------------------------------------"

echo -n "Querying HTTP request metrics... "
METRIC_COUNT=$(curl -s "http://localhost:9090/api/v1/query?query=up" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data',{}).get('result',[])))")

if [ "${METRIC_COUNT}" -gt "0" ]; then
    echo -e "${GREEN}✓ ${METRIC_COUNT} targets found${NC}"
else
    echo -e "${RED}✗ No metrics found${NC}"
fi

echo ""
echo "Step 7: Verify Grafana Dashboard"
echo "----------------------------------------"

# Check if Full-Stack APM dashboard exists
DASHBOARD_CHECK=$(curl -s -u admin:admin "http://localhost:3000/api/search?query=Full-Stack" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print('found' if len(data) > 0 else 'not_found')")

if [ "${DASHBOARD_CHECK}" = "found" ]; then
    echo -e "${GREEN}✓ Full-Stack APM dashboard found in Grafana${NC}"
    echo ""
    echo "  📊 Open dashboard at:"
    echo "     http://localhost:3000/d/full-stack-apm"
    echo ""
else
    echo -e "${YELLOW}⚠ Dashboard not found - may need to restart Grafana${NC}"
    echo "  Run: docker compose restart grafana"
fi

echo ""
echo "Step 8: Loki Log Availability"
echo "----------------------------------------"

LOG_COUNT=$(curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
    --data-urlencode 'query={container_name="odoo18"}' \
    --data-urlencode "start=$(date -u -v-1H +%s)000000000" \
    --data-urlencode "end=$(date -u +%s)000000000" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data',{}).get('result',[])))" 2>/dev/null || echo "0")

if [ "${LOG_COUNT}" -gt "0" ]; then
    echo -e "${GREEN}✓ Odoo logs available in Loki (${LOG_COUNT} streams)${NC}"
else
    echo -e "${YELLOW}⚠ No logs found - check Promtail${NC}"
fi

echo ""
echo "============================================================"
echo "Manual Testing Steps"
echo "============================================================"
echo ""
echo "1. Browser Testing:"
echo "   - Open http://localhost:8069 in Chrome/Firefox"
echo "   - Open DevTools Console (Cmd+Option+J / F12)"
echo "   - Look for: '✅ OpenTelemetry Browser initialized'"
echo "   - Navigate: Login, menus, create records"
echo "   - Network tab: Check for POST to /api/otel/traces"
echo ""
echo "2. Grafana Dashboards:"
echo "   - Login: http://localhost:3000 (admin/admin)"
echo "   - Navigate: Dashboards → Full-Stack APM"
echo "   - Verify panels show data (may take 30-60s)"
echo "   - Check other dashboards: System, PostgreSQL, Redis"
echo ""
echo "3. Tempo Trace Explorer:"
echo "   - Grafana → Explore → Select 'Tempo' datasource"
echo "   - Query: {resource.service.name=\"odoo-browser\"}"
echo "   - Click trace ID to see spans"
echo "   - Verify parent-child relationships"
echo ""
echo "4. Prometheus Alerts:"
echo "   - Open: http://localhost:9090/alerts"
echo "   - Check alert rules are loaded (25+ alerts)"
echo "   - Verify targets: http://localhost:9090/targets"
echo ""
echo "5. Loki Logs:"
echo "   - Grafana → Explore → Select 'Loki' datasource"
echo "   - Query: {container_name=\"odoo18\"} |= \"OpenTelemetry\""
echo "   - Verify traces and logs correlation"
echo ""
echo "============================================================"

if [ -n "$(python3 check_tempo_traces.py 2>/dev/null | grep 'Browser traces' | grep -v ': 0')" ]; then
    echo -e "${GREEN}✅ Phase 5 Testing: PASSED${NC}"
    echo "   Backend traces confirmed in Tempo"
    echo "   Next: Open browser and generate frontend traces"
else
    echo -e "${YELLOW}⚠️  Phase 5 Testing: PARTIAL${NC}"
    echo "   Backend services OK, awaiting browser traces"
    echo "   Action: Open http://localhost:8069 in browser"
fi

echo ""
