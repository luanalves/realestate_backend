# Quickstart: Goals and Results (019)

**Module**: `thedevkitchen_estate_goals`  
**Branch**: `019-goals-and-results`  
**Date**: 2026-05-11

---

## Prerequisites

- Docker running: `cd 18.0 && docker compose ps` shows `odoo`, `db`, `redis` all running
- `quicksol_estate` module installed (domain models)
- `thedevkitchen_apigateway` module installed (auth decorators)
- A valid admin session for `curl` examples below

---

## 1. Install the Module

```bash
# From repo root:
cd /opt/homebrew/var/www/realestate/odoo-docker

# Trigger module install via Odoo CLI
docker compose exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d realestate \
  --update thedevkitchen_estate_goals \
  --stop-after-init \
  --no-http
```

Verify table was created:

```bash
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT column_name, data_type FROM information_schema.columns \
   WHERE table_name = 'thedevkitchen_estate_goal' ORDER BY ordinal_position;"
```

---

## 2. Seed Data

### 2a. Create goals for all 9 profiles (manual)

After obtaining a JWT via `/api/v1/auth/login`:

```bash
BASE="http://localhost:8069"
JWT="<your-jwt-token>"
SESSION="<your-session-id>"

# Create a captação/sale goal for user 5 in March 2025
curl -s -X POST "$BASE/api/v1/goals" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "year": 2025,
    "month": 3,
    "metric_type": "captacao",
    "operation_type": "sale",
    "target": 10,
    "target_vgv": 500000.00,
    "notes": "Meta de captação Q1 para Ana"
  }' | python3 -m json.tool
```

### 2b. Bulk seed via integration test

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker
bash integration_tests/test_us019_s1_create_goals.sh
```

---

## 3. Run Unit Tests

```bash
docker compose exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d realestate_test \
  --test-enable \
  --test-tags thedevkitchen_estate_goals \
  --stop-after-init \
  --no-http
```

---

## 4. Run Integration Tests

Each test script is self-contained (obtains JWT, runs assertions, cleans up):

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker

# US-019 S1: Create goals
bash integration_tests/test_us019_s1_create_goals.sh

# US-019 S2: Update and delete goal lifecycle
bash integration_tests/test_us019_s2_goal_lifecycle.sh

# US-019 S3: Single-month report
bash integration_tests/test_us019_s3_report_single_month.sh

# US-019 S4: Accumulated (date range) report
bash integration_tests/test_us019_s4_report_date_range.sh

# US-019 S5: RBAC matrix (Owner/Manager/Agent permissions)
bash integration_tests/test_us019_s5_rbac_matrix.sh

# US-019 S6: Multitenancy isolation
bash integration_tests/test_us019_s6_multitenancy.sh

# Run all US-019 tests
bash integration_tests/run_feature019_tests.sh
```

---

## 5. API Endpoint Reference

### Authentication

All endpoints require:
- `Authorization: Bearer <JWT>` header
- `Cookie: session_id=<session_id>` header

Obtain credentials:

```bash
curl -s -X POST "http://localhost:8069/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login": "manager@example.com", "password": "yourpassword"}' | python3 -m json.tool
```

### POST /api/v1/goals — Create Goal

```bash
curl -s -X POST "$BASE/api/v1/goals" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "year": 2025,
    "month": 3,
    "metric_type": "visitas",
    "operation_type": "all",
    "target": 8
  }' | python3 -m json.tool
```

Expected: `201 Created` with goal object.

### PUT /api/v1/goals/{id} — Update Goal

```bash
curl -s -X PUT "$BASE/api/v1/goals/42" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"target": 12, "notes": "Revisado em abril"}' | python3 -m json.tool
```

Expected: `200 OK` with updated goal object.

### DELETE /api/v1/goals/{id} — Soft-Delete Goal

```bash
curl -s -X DELETE "$BASE/api/v1/goals/42" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool
```

Expected: `200 OK` with `{"active": false}`.

### GET /api/v1/goals — List Goals

```bash
# All goals for company
curl -s "$BASE/api/v1/goals" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool

# Filter by user and month
curl -s "$BASE/api/v1/goals?user_id=5&year=2025&month=3" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool
```

Expected: `200 OK` with `{"goals": [...], "total": N}`.

### GET /api/v1/goals/report — Goals vs. Achievement Report

**Single-month mode**:

```bash
curl -s "$BASE/api/v1/goals/report?year=2025&month=3&operation_type=sale" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool
```

**Accumulated mode (Q1 2025)**:

```bash
curl -s "$BASE/api/v1/goals/report?date_from=2025-01-01&date_to=2025-03-31" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool
```

**Agent self-service (single user)**:

```bash
curl -s "$BASE/api/v1/goals/report?year=2025&month=3&user_id=5" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" | python3 -m json.tool
```

Expected: `200 OK` with `{"users": [...], "totals": {...}, "period": {...}}`.

### Error cases to test manually

```bash
# Missing year in single-month mode → 422
curl -s "$BASE/api/v1/goals/report?month=3" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION"

# Duplicate goal → 409
curl -s -X POST "$BASE/api/v1/goals" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 5, "year": 2025, "month": 3, "metric_type": "captacao", "operation_type": "sale", "target": 10}'
# (run twice — second call should return 409)
```

---

## 6. Odoo Admin UI

Open `http://localhost:8069/web` as `admin`.

Navigate to: **Real Estate → Goals (Metas)** (new menu added by this module).

The list view shows all active goals for the company. The form view allows creating/editing goals with all fields visible.

---

## 7. Swagger / OpenAPI Docs

After module install, the 5 endpoints are registered in `thedevkitchen_api_endpoint`.

View at: `http://localhost:8069/api/docs`

To verify:

```bash
curl -s "http://localhost:8069/api/docs/openapi.json" | python3 -m json.tool | grep '/api/v1/goals'
```

---

## 8. Troubleshooting

| Problem | Check |
|---------|-------|
| `thedevkitchen_estate_goals` not in module list | Verify `extra-addons/thedevkitchen_estate_goals/__manifest__.py` exists and is valid Python |
| `mail.tracking.value` queries return 0 | Confirm `real.estate.service.stage` has `tracking=True` and test data has stage changes in the date range |
| 422 on report (user cap) | Reduce scope with `user_id` filter or verify company has ≤200 active users |
| Duplicate key error on goal creation | Check unique constraint `(user_id, company_id, year, month, metric_type, operation_type)` — goal already exists |
| `proposal_type='lease'` not mapping | Verify `OP_TYPE_TO_PROPOSAL_TYPE` mapping in `goals_report_service.py` |
