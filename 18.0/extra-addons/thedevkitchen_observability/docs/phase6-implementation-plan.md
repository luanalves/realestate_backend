# Phase 6: Advanced Features - Implementation Plan

## Overview

Phase 6 enhances the observability infrastructure with advanced production features: richer span attributes for business context, custom metrics for domain-specific KPIs, query performance analysis, optimized sampling strategies, and resource utilization tracking.

## Status: In Progress (Started March 24, 2026)

### Prerequisites (Completed)
- ✅ Phase 1: HTTP tracing via OpenTelemetryInstrumentor
- ✅ Phase 2: Database instrumentation (SQLAlchemy)
- ✅ Phase 3: Celery task tracing
- ✅ Phase 4: Browser instrumentation (OpenTelemetry JS SDK)
- ✅ Phase 5: Grafana dashboards and alerting

---

## Task 1: Enhanced Span Attributes (Priority: HIGH)

### Objective
Add business-context attributes to existing spans for better filtering, debugging, and analytics.

### Implementation

#### 1.1 User Context Attributes
**File:** `instrumentation/http_instrumentation.py`

Add to HTTP spans:
```python
# User identification
span.set_attribute("user.id", request.env.uid)
span.set_attribute("user.email", request.env.user.email)
span.set_attribute("user.name", request.env.user.name)

# User profile (for RBAC analysis)
span.set_attribute("user.profile", request.env.user.profile_id.name)
# Values: owner, manager, agent, receptionist, prospector, tenant, etc.
```

#### 1.2 Multi-Tenancy Attributes
**File:** `instrumentation/http_instrumentation.py`

Add to HTTP spans:
```python
# Company isolation (critical for multi-tenancy)
span.set_attribute("company.id", request.env.company.id)
span.set_attribute("company.name", request.env.company.name)

# For debugging cross-company data leaks
span.set_attribute("company.allowed_ids", ",".join(map(str, request.env.companies.ids)))
```

#### 1.3 Request Context Attributes
**File:** `instrumentation/http_instrumentation.py`

Add to HTTP spans:
```python
# API versioning
span.set_attribute("api.version", "v1")  # Extract from route

# Request metadata
span.set_attribute("request.content_length", len(request.httprequest.data or ""))
span.set_attribute("request.user_agent", request.httprequest.headers.get("User-Agent", ""))
span.set_attribute("request.referer", request.httprequest.headers.get("Referer", ""))

# Session information
if hasattr(request, 'session') and request.session.sid:
    span.set_attribute("session.id", request.session.sid)
    span.set_attribute("session.age_seconds", time.time() - request.session.creation_time)
```

#### 1.4 Database Query Attributes
**File:** `instrumentation/database_instrumentation.py`

Enhance SQL spans:
```python
# Query classification
span.set_attribute("db.query.type", classify_query(statement))
# Values: SELECT, INSERT, UPDATE, DELETE, DDL, etc.

# Performance hints
span.set_attribute("db.query.returns_rows", returns_rows)
span.set_attribute("db.query.parameter_count", len(parameters or []))

# Query fingerprint (for grouping similar queries)
span.set_attribute("db.query.fingerprint", generate_fingerprint(statement))
```

#### 1.5 Business Domain Attributes
**File:** `instrumentation/http_instrumentation.py`

Add to relevant endpoints:
```python
# Property management (when endpoint deals with properties)
if "property" in route:
    span.set_attribute("business.entity", "property")
    span.set_attribute("property.id", property_id)
    span.set_attribute("property.type", property_type)  # sale/rent

# Lead management
if "lead" in route:
    span.set_attribute("business.entity", "lead")
    span.set_attribute("lead.id", lead_id)
    span.set_attribute("lead.stage", lead_stage)

# User onboarding (Feature 009)
if "invite" in route or "password" in route:
    span.set_attribute("business.flow", "user_onboarding")
```

### Testing
**File:** `tests/test_enhanced_attributes.py`

```python
def test_user_context_attributes():
    """Verify user context is added to HTTP spans"""
    # Make authenticated request
    # Check span has user.id, user.email, user.profile

def test_company_isolation_attributes():
    """Verify multi-tenancy attributes"""
    # Make request as Company A user
    # Check span has company.id, company.name

def test_query_classification():
    """Verify SQL queries are classified correctly"""
    # Execute SELECT, INSERT, UPDATE queries
    # Check db.query.type attribute
```

### Success Criteria
- ✅ All HTTP spans include user.id, user.profile, company.id
- ✅ SQL spans include query.type and query.fingerprint
- ✅ Spans filterable in Tempo by user profile, company
- ✅ <1ms overhead per attribute addition

### Grafana Queries (Tempo)
```traceql
# All requests by specific user
{user.id="42"}

# All agent profile requests
{user.profile="agent"}

# All requests for Company A
{company.id="1"}

# Slow SELECT queries
{db.query.type="SELECT" && duration>100ms}

# User onboarding flow traces
{business.flow="user_onboarding"}
```

---

## Task 2: Custom Business Metrics (Priority: HIGH)

### Objective
Export custom Prometheus metrics for business KPIs not captured by standard OTEL instrumentation.

### Implementation

#### 2.1 Create Metrics Exporter
**File:** `metrics/business_metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import metrics as otel_metrics

# Property metrics
property_views_total = Counter(
    'realestate_property_views_total',
    'Total property detail page views',
    ['property_type', 'company_id']
)

property_inquiries_total = Counter(
    'realestate_property_inquiries_total',
    'Total property inquiry submissions',
    ['property_type', 'company_id', 'user_profile']
)

# Lead metrics
lead_conversions_total = Counter(
    'realestate_lead_conversions_total',
    'Total lead conversions (visit → contract)',
    ['property_type', 'agent_id', 'company_id']
)

lead_stage_duration_seconds = Histogram(
    'realestate_lead_stage_duration_seconds',
    'Time spent in each lead stage',
    ['from_stage', 'to_stage', 'company_id'],
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800, 86400, 172800]
)

# User onboarding metrics (Feature 009)
user_invites_sent_total = Counter(
    'realestate_user_invites_sent_total',
    'Total user invitations sent',
    ['profile', 'inviter_profile', 'company_id']
)

user_invite_acceptance_duration_seconds = Histogram(
    'realestate_user_invite_acceptance_duration_seconds',
    'Time from invite sent to password set',
    ['profile', 'company_id'],
    buckets=[3600, 7200, 21600, 43200, 86400, 172800, 604800]
)

password_reset_requests_total = Counter(
    'realestate_password_reset_requests_total',
    'Total password reset requests',
    ['company_id']
)

# API performance by endpoint
api_endpoint_requests_total = Counter(
    'realestate_api_endpoint_requests_total',
    'Total API requests by endpoint',
    ['method', 'endpoint', 'status_code', 'company_id']
)

# Active resources
active_properties_gauge = Gauge(
    'realestate_active_properties',
    'Number of active properties (available for sale/rent)',
    ['property_type', 'company_id']
)

active_leads_gauge = Gauge(
    'realestate_active_leads',
    'Number of leads in active status',
    ['stage', 'agent_id', 'company_id']
)
```

#### 2.2 Instrument Business Logic
**File:** `models/real_estate_property_offer.py`

```python
# In lead conversion method
def accept_offer(self):
    # ... existing logic ...
    
    # Emit metric
    from ..metrics.business_metrics import lead_conversions_total
    lead_conversions_total.labels(
        property_type=self.property_id.property_type,
        agent_id=self.property_id.agent_id.id,
        company_id=self.company_id.id
    ).inc()
```

**File:** `controllers/property_controller.py`

```python
# In property detail endpoint
@http.route('/api/v1/properties/<int:property_id>', ...)
@require_jwt
@require_session
@require_company
def get_property_detail(self, property_id, **kwargs):
    # ... existing logic ...
    
    # Emit metric
    from ..metrics.business_metrics import property_views_total
    property_views_total.labels(
        property_type=property.property_type,
        company_id=request.env.company.id
    ).inc()
    
    return response
```

**File:** `controllers/user_invite_controller.py`

```python
# In invite endpoint
@http.route('/api/v1/users/invite', ...)
@require_jwt
@require_session
@require_company
def invite_user(self, **kwargs):
    # ... existing logic ...
    
    # Emit metric
    from ..metrics.business_metrics import user_invites_sent_total
    user_invites_sent_total.labels(
        profile=validated_data['profile'],
        inviter_profile=request.env.user.profile_id.name,
        company_id=request.env.company.id
    ).inc()
    
    return response
```

#### 2.3 Periodic Metric Collection
**File:** `models/metrics_collector.py`

```python
from odoo import models, api
from odoo.addons.thedevkitchen_observability.metrics.business_metrics import (
    active_properties_gauge,
    active_leads_gauge
)

class MetricsCollector(models.AbstractModel):
    _name = 'metrics.collector'
    
    @api.model
    def _collect_active_properties(self):
        """Run every 60 seconds via ir.cron"""
        Property = self.env['real.estate.property']
        
        # Group by type and company
        for company in self.env['res.company'].search([]):
            for prop_type in ['sale', 'rent']:
                count = Property.search_count([
                    ('state', '=', 'available'),
                    ('property_type', '=', prop_type),
                    ('company_id', '=', company.id)
                ])
                
                active_properties_gauge.labels(
                    property_type=prop_type,
                    company_id=company.id
                ).set(count)
    
    @api.model
    def _collect_active_leads(self):
        """Run every 60 seconds via ir.cron"""
        Lead = self.env['real.estate.property.offer']
        
        for company in self.env['res.company'].search([]):
            # Group by stage and agent
            for stage in ['new', 'qualified', 'visit_scheduled', 'negotiation']:
                leads = Lead.search([
                    ('state', '=', stage),
                    ('company_id', '=', company.id)
                ])
                
                # Group by agent
                agent_counts = {}
                for lead in leads:
                    agent_id = lead.property_id.agent_id.id
                    agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
                
                for agent_id, count in agent_counts.items():
                    active_leads_gauge.labels(
                        stage=stage,
                        agent_id=agent_id,
                        company_id=company.id
                    ).set(count)
```

#### 2.4 Expose Metrics Endpoint
**File:** `controllers/metrics_controller.py`

```python
from odoo import http
from odoo.http import request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

class MetricsController(http.Controller):
    
    @http.route('/metrics', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def prometheus_metrics(self, **kwargs):
        """
        Prometheus scrape endpoint
        Returns metrics in Prometheus text format
        
        Security: Should be protected with IP whitelist or token in production
        """
        # TODO: Add IP whitelist check or Bearer token auth
        # For now, allow from localhost only
        if request.httprequest.remote_addr not in ['127.0.0.1', '::1', 'localhost']:
            return request.make_json_response(
                {'error': 'Forbidden'}, 
                status=403
            )
        
        # Generate Prometheus exposition format
        return request.make_response(
            generate_latest(),
            headers={'Content-Type': CONTENT_TYPE_LATEST}
        )
```

#### 2.5 Configure Prometheus Scraping
**File:** `observability/prometheus.yml`

Add scrape job:
```yaml
scrape_configs:
  # ... existing jobs ...
  
  - job_name: 'odoo-business-metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
    static_configs:
      - targets: ['odoo18:8069']
    metrics_path: '/metrics'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'odoo-app'
```

### Testing
**File:** `tests/test_business_metrics.py`

```python
def test_property_view_metric():
    """Verify property views are counted"""
    # Before: Check metric baseline
    # Action: GET /api/v1/properties/123
    # After: Verify metric incremented

def test_lead_conversion_metric():
    """Verify lead conversions are tracked"""
    # Action: Accept an offer
    # Check: lead_conversions_total incremented

def test_metrics_endpoint():
    """Verify /metrics endpoint returns Prometheus format"""
    response = requests.get('http://localhost:8069/metrics')
    assert response.status_code == 200
    assert 'realestate_property_views_total' in response.text
```

### Success Criteria
- ✅ Prometheus scrapes `/metrics` endpoint every 30s
- ✅ Business metrics appear in Prometheus UI
- ✅ Grafana dashboards can query custom metrics
- ✅ <5ms overhead per metric emission

### Grafana Queries (PromQL)
```promql
# Property views per minute
rate(realestate_property_views_total[5m])

# Lead conversion rate (%)
(
  rate(realestate_lead_conversions_total[1h])
  / 
  rate(realestate_property_inquiries_total[1h])
) * 100

# Avg invite acceptance time (hours)
(
  rate(realestate_user_invite_acceptance_duration_seconds_sum[24h])
  / 
  rate(realestate_user_invite_acceptance_duration_seconds_count[24h])
) / 3600

# Active properties by type
realestate_active_properties

# Top 10 agents by lead volume
topk(10, sum by (agent_id) (realestate_active_leads))
```

---

## Task 3: Query Performance Analysis Dashboard (Priority: MEDIUM)

### Objective
Create Grafana dashboard showing slow queries, N+1 patterns, and query optimization opportunities.

### Implementation

#### 3.1 Query Fingerprinting
**File:** `instrumentation/database_instrumentation.py`

Add fingerprint generation:
```python
import re

def generate_query_fingerprint(sql):
    """
    Normalize SQL query for grouping similar queries
    Example: "SELECT * FROM users WHERE id = 123" 
          → "SELECT * FROM users WHERE id = ?"
    """
    # Remove values from IN clauses
    sql = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', sql, flags=re.IGNORECASE)
    
    # Replace numeric literals
    sql = re.sub(r'\b\d+\b', '?', sql)
    
    # Replace string literals
    sql = re.sub(r"'[^']*'", '?', sql)
    
    # Normalize whitespace
    sql = re.sub(r'\s+', ' ', sql).strip()
    
    return sql
```

#### 3.2 N+1 Query Detection
**File:** `instrumentation/database_instrumentation.py`

```python
from collections import defaultdict
import threading

# Thread-local storage for tracking queries per request
_request_queries = threading.local()

def track_query_in_request(fingerprint, duration_ms):
    """
    Track queries executed within a single HTTP request
    Detect N+1 patterns (same query executed many times)
    """
    if not hasattr(_request_queries, 'queries'):
        _request_queries.queries = defaultdict(list)
    
    _request_queries.queries[fingerprint].append(duration_ms)

def analyze_request_queries():
    """
    Analyze queries at end of request
    Return N+1 patterns and recommendations
    """
    if not hasattr(_request_queries, 'queries'):
       return []
    
    issues = []
    
    for fingerprint, durations in _request_queries.queries.items():
        if len(durations) > 5:  # Same query executed >5 times
            issues.append({
                'type': 'n_plus_one',
                'fingerprint': fingerprint,
                'count': len(durations),
                'total_duration_ms': sum(durations),
                'recommendation': 'Consider using prefetch_related() or select_related()'
            })
    
    # Clear for next request
    _request_queries.queries = defaultdict(list)
    
    return issues
```

#### 3.3 Create Dashboard
**File:** `observability/grafana/dashboards/query-performance-analysis.json`

Panels:
1. **Slowest Queries (P95)** - Table showing top 20 slow queries by fingerprint
2. **Query Count by Type** - Pie chart (SELECT vs INSERT vs UPDATE vs DELETE)
3. **N+1 Query Patterns** - Table showing queries executed >10 times per request
4. **Query Duration Distribution** - Heatmap showing latency buckets
5. **Queries Over Time** - Time series of query rate
6. **Cache Hit Rate** - PostgreSQL buffer cache efficiency

### Testing
**File:** `tests/test_query_analysis.py`

```python
def test_query_fingerprinting():
    """Verify SQL normalization works correctly"""
    sql1 = "SELECT * FROM users WHERE id = 123"
    sql2 = "SELECT * FROM users WHERE id = 456"
    assert generate_query_fingerprint(sql1) == generate_query_fingerprint(sql2)

def test_n_plus_one_detection():
    """Verify N+1 patterns are detected"""
    # Execute same query 10 times
    # Check analyze_request_queries() returns issue
```

### Success Criteria
- ✅ Slow queries (>100ms) visible in dashboard
- ✅ N+1 patterns detected and logged
- ✅ Query fingerprints group similar queries
- ✅ Dashboard updates in real-time

---

## Task 4: Tail-Based Sampling (Priority: LOW)

### Objective
Implement dynamic sampling to reduce trace volume in production while keeping interesting traces (errors, slow requests).

### Implementation

#### 4.1 Configure Tempo Tail Sampling
**File:** `observability/tempo-config.yml`

```yaml
# Add tail sampling processor
overrides:
  defaults:
    metrics_generator:
      # ... existing config ...
    
    # Tail-based sampling
    ingestion_rate_limit_bytes: 15000000  # 15MB/s
    ingestion_burst_size_bytes: 20000000  # 20MB burst
    
    # Keep interesting traces
    tail_sampling:
      policies:
        # Always keep errors
        - name: error-traces
          type: status_code
          status_code:
            status_codes: [ERROR]
        
        # Keep slow requests (>500ms)
        - name: slow-traces
          type: latency
          latency:
            threshold_ms: 500
        
        # Keep 10% of normal requests
        - name: probabilistic-sample
          type: probabilistic
          probabilistic:
            sampling_percentage: 10
        
        # Always keep user onboarding flows
        - name: business-critical
          type: string_attribute
          string_attribute:
            key: business.flow
            values: [user_onboarding, payment, contract_signing]
```

#### 4.2 Update Odoo OTEL Configuration
**File:** `.env`

```bash
# Send all traces to Tempo (let Tempo decide what to keep)
OTEL_TRACES_SAMPLER=always_on
```

### Testing
**File:** `tests/test_tail_sampling.py`

```python
def test_error_traces_kept():
    """Verify error traces are always sampled"""
    # Generate 100 traces with 10 errors
    # Query Tempo after 1 minute
    # Verify all 10 error traces exist

def test_normal_traces_sampled():
    """Verify normal traces are sampled at 10%"""
    # Generate 1000 normal traces
    # Query Tempo after 1 minute
    # Verify ~100 traces kept (±20%)
```

### Success Criteria
- ✅ All error traces (status=ERROR) kept
- ✅ All slow traces (>500ms) kept
- ✅ Normal traces sampled at ~10%
- ✅ Trace storage reduced by 85-90%

---

## Task 5: Resource Utilization Tracking (Priority: LOW)

### Objective
Track CPU and memory usage per HTTP request for capacity planning and anomaly detection.

### Implementation

#### 5.1 Add Resource Tracking to HTTP Spans
**File:** `instrumentation/http_instrumentation.py`

```python
import psutil
import os

def add_resource_attributes(span, start_time):
    """
    Add CPU and memory metrics to span
    Called at end of request
    """
    process = psutil.Process(os.getpid())
    
    # CPU usage during request (%)
    cpu_percent = process.cpu_percent()
    span.set_attribute("resource.cpu.percent", cpu_percent)
    
    # Memory growth during request (MB)
    mem_info = process.memory_info()
    span.set_attribute("resource.memory.rss_mb", mem_info.rss / (1024 * 1024))
    span.set_attribute("resource.memory.vms_mb", mem_info.vms / (1024 * 1024))
    
    # Thread count
    span.set_attribute("resource.threads", len(process.threads()))
    
    # File descriptors (Linux only)
    try:
        span.set_attribute("resource.file_descriptors", process.num_fds())
    except AttributeError:
        pass  # Not supported on Windows
```

#### 5.2 Create Resource Dashboard
**File:** `observability/grafana/dashboards/resource-utilization.json`

Panels:
1. **CPU % by Endpoint** - Heatmap showing which endpoints use most CPU
2. **Memory Growth by Endpoint** - Identify memory-hungry requests
3. **Requests by Resource Usage** - Scatter plot (CPU vs Memory)
4. **High-Resource Requests** - Table of requests using >80% CPU or >500MB memory

### Testing
**File:** `tests/test_resource_tracking.py`

```python
def test_cpu_tracking():
    """Verify CPU usage is recorded"""
    # Make API request
    # Check span has resource.cpu.percent attribute

def test_memory_tracking():
    """Verify memory usage is recorded"""
    # Make API request
    # Check span has resource.memory.rss_mb attribute
```

### Success Criteria
- ✅ CPU and memory attributes on all HTTP spans
- ✅ Grafana dashboard shows resource usage by endpoint
- ✅ Alerts for high-resource requests (>80% CPU)
- ✅ <2ms overhead for resource collection

---

## Dependencies

```
pip install psutil>=5.9.0
```

Add to `requirements.txt`:
```
prometheus-client>=0.19.0
psutil>=5.9.0
```

---

## Migration Path

### Phase 5 → Phase 6

1. **No breaking changes** - All Phase 6 features are additive
2. **Optional features** - Can be enabled incrementally:
   - Enhanced attributes: Backward compatible, just more data
   - Custom metrics: Opt-in via feature flags
   - Tail sampling: Configure in Tempo, doesn't affect Odoo
   - Resource tracking: Can be disabled if overhead is concern

### Rollback Strategy

If Phase 6 causes issues:
```bash
# Disable enhanced attributes
export OTEL_ENABLE_ENHANCED_ATTRIBUTES=false

# Disable custom metrics
export ENABLE_BUSINESS_METRICS=false

# Disable resource tracking
export OTEL_TRACK_RESOURCES=false

# Revert to 100% sampling in Tempo
# Edit observability/tempo-config.yml, set sampling_percentage=100
```

---

## Testing Strategy

### Unit Tests
- `tests/test_enhanced_attributes.py` (20 tests)
- `tests/test_business_metrics.py` (15 tests)
- `tests/test_query_analysis.py` (10 tests)
- `tests/test_tail_sampling.py` (8 tests)
- `tests/test_resource_tracking.py` (6 tests)

### Integration Tests
- End-to-end trace with all enhanced attributes
- Property view → Lead creation → Metrics emission flow
- Query fingerprinting across multiple requests
- Tail sampling verification (sample 1000 traces, check Tempo)

### Performance Tests
- Benchmark overhead of enhanced attributes (<1ms)
- Benchmark metrics emission (<5ms)
- Benchmark resource tracking (<2ms)
- Total overhead target: <10ms per request (Phase 6 only)

---

## Timeline

**Total Duration:** 2-3 weeks

| Task | Duration | Priority |
|------|----------|----------|
| 1. Enhanced Span Attributes | 3 days | HIGH |
| 2. Custom Business Metrics | 4 days | HIGH |
| 3. Query Performance Dashboard | 2 days | MEDIUM |
| 4. Tail-Based Sampling | 2 days | LOW |
| 5. Resource Utilization Tracking | 2 days | LOW |
| Testing & Documentation | 3 days | HIGH |
| **Total** | **16 days** | |

---

## Success Metrics

### Functional
- ✅ All spans include user context (user.id, user.profile, company.id)
- ✅ 10+ custom business metrics exported to Prometheus
- ✅ Query fingerprinting working (groups similar queries)
- ✅ N+1 query detection operational
- ✅ Tail sampling reduces trace volume by 85-90%
- ✅ Resource tracking on all HTTP requests

### Performance
- ✅ Enhanced attributes overhead: <1ms per request
- ✅ Metrics emission overhead: <5ms per event
- ✅ Resource tracking overhead: <2ms per request
- ✅ Total Phase 6 overhead: <10ms per request
- ✅ Combined Phases 1-6 overhead: <3% total

### Observability
- ✅ Traces filterable by user, company, profile in Tempo
- ✅ Business KPIs visible in Prometheus/Grafana
- ✅ Slow queries visible in Query Performance dashboard
- ✅ High-resource endpoints identifiable
- ✅ Storage costs reduced by 85-90% via tail sampling

---

## Next Phase: Phase 7 (Production Hardening)

After Phase 6 completion:
- Security hardening (authentication, TLS)
- High availability (distributed Tempo, Prometheus federation)
- Data retention policies (automated aggregation)
- Disaster recovery procedures
- Complete runbooks and troubleshooting guides

---

**Document Version:** 1.0  
**Status:** Implementation In Progress  
**Start Date:** March 24, 2026  
**Target Completion:** Mid-April 2026
