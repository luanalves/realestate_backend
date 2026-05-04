# Quickstart — Service Pipeline (Atendimentos)

**Feature**: 015-service-pipeline-atendimentos
**Audience**: Backend developer implementing the feature, QA running E2E, frontend integrator.

This quickstart shows end-to-end how to bring up the feature in a local Docker stack and exercise the main flows.

## Prerequisites

- Docker Compose stack running (per `18.0/docker-compose.yml`): Odoo + PostgreSQL + Redis + RabbitMQ + Celery
- Module `quicksol_estate` installed and upgraded with this feature's code
- A valid OAuth2 client + JWT for the calling user (see `thedevkitchen_apigateway` docs)
- `jq` and `curl` (for shell snippets)

```bash
cd 18.0
docker compose up -d
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
```

## 1. Authenticate (obtain JWT + session)

```bash
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"grant_type":"client_credentials","client_id":"test-client-id","client_secret":"test-client-secret-12345"}' \
  | jq -r .access_token)

SESSION_ID=$(curl -s -X POST http://localhost:8069/api/v1/users/login \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"seed_owner_a@test.com","password":"Owner@123"}' \
  | jq -r .session_id)

H_AUTH="Authorization: Bearer $TOKEN"
H_SESS="X-Openerp-Session-Id: $SESSION_ID"
```

## 2. Happy path — Agent creates a service and walks the pipeline

### 2.1. Create a service (cliente novo)

```bash
curl -s -X POST http://localhost:8069/api/v1/services \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{
    "client": {
      "name": "Danilo Silva",
      "email": "danilo@example.com",
      "phones": [
        { "type": "mobile", "number": "(98) 98882-5176", "is_primary": true }
      ]
    },
    "operation_type": "rent",
    "source_id": 3,
    "property_ids": [45],
    "tag_ids": [],
    "notes": "Cliente interessada em apto 2 quartos no Centro"
  }' | jq
```

Expected: HTTP 201, body returns `id`, `name=ATD/2026/00xxx`, `stage="no_service"`, `is_pending=false`, `links[]` with HATEOAS.

### 2.2. Move to `in_service`

```bash
SID=101  # use id returned above
curl -s -X PATCH http://localhost:8069/api/v1/services/$SID/stage \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "stage": "in_service", "comment": "Primeiro contato realizado" }' | jq
```

### 2.3. Try moving to `proposal` — should pass (property already linked)

```bash
curl -s -X PATCH http://localhost:8069/api/v1/services/$SID/stage \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "stage": "proposal" }' | jq
```

If property_ids were empty, expect HTTP 422 with `reason: "proposal stage requires at least one property linked"`.

### 2.4. Try moving to `formalization` without approved proposal — should fail 422

```bash
curl -s -X PATCH http://localhost:8069/api/v1/services/$SID/stage \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "stage": "formalization" }'
# Expect: 422 unprocessable
```

Create + accept a proposal via `/api/v1/proposals/...` (013), then retry — should pass.

### 2.5. Mark as lost from any non-terminal stage

```bash
curl -s -X PATCH http://localhost:8069/api/v1/services/$SID/stage \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "stage": "lost", "lost_reason": "Cliente desistiu por motivo financeiro" }' | jq
```

Without `lost_reason`, expect HTTP 422.

## 3. Manager view — kanban summary + filters + reassign

### 3.1. Authenticate as manager and fetch summary

```bash
# (Repeat step 1 with seed_manager_a@test.com)
curl -s -G http://localhost:8069/api/v1/services/summary \
  -H "$H_AUTH" -H "$H_SESS" \
  --data-urlencode "operation_type=rent" | jq
```

Expected response (under 100 ms):
```json
{
  "no_service": 12, "in_service": 30, "visit": 5,
  "proposal": 3, "formalization": 1, "won": 4, "lost": 8,
  "orphan_agent": 0,
  "links": [{"href":"/api/v1/services?stage=in_service","rel":"by-stage","type":"GET"}, ...]
}
```

### 3.2. Filter pendências

```bash
curl -s -G http://localhost:8069/api/v1/services \
  -H "$H_AUTH" -H "$H_SESS" \
  --data-urlencode "is_pending=true" \
  --data-urlencode "ordering=pendency" \
  --data-urlencode "per_page=50" | jq '.items[] | {id,name,last_activity_date,agent_id}'
```

### 3.3. Reassign agent

```bash
curl -s -X PATCH http://localhost:8069/api/v1/services/$SID/reassign \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "new_agent_id": 7, "reason": "Corretor de férias" }' | jq
```

Expect: 200 with updated `agent_id`, audit message in `mail.thread`.

## 4. Tags & Sources CRUD (Owner/Manager)

```bash
# Create custom tag
curl -s -X POST http://localhost:8069/api/v1/service-tags \
  -H "$H_AUTH" -H "$H_SESS" -H 'Content-Type: application/json' \
  -d '{ "name": "VIP", "color": "#FF0000" }'

# Try to delete the system tag "closed" → expect 403
CLOSED_ID=$(curl -s -G http://localhost:8069/api/v1/service-tags -H "$H_AUTH" -H "$H_SESS" \
  | jq -r '.[] | select(.name=="closed") | .id')
curl -s -X DELETE "http://localhost:8069/api/v1/service-tags/$CLOSED_ID" -H "$H_AUTH" -H "$H_SESS" -i
```

## 5. Multi-tenancy isolation check

```bash
# Authenticate as owner_b in company 2; try to GET service from company 1 → expect 404
SID_A=101
curl -s -X GET http://localhost:8069/api/v1/services/$SID_A -H "$H_AUTH_B" -H "$H_SESS_B" -i
# HTTP/1.1 404 Not Found
```

## 6. Run unit + integration tests

```bash
# Unit (TransactionCase)
docker compose exec odoo odoo --test-tags /quicksol_estate:TestServicePipeline -d realestate --stop-after-init

# Integration (HTTP)
./integration_tests/test_us15_s1_agent_creates_service_lifecycle.sh
./integration_tests/test_us15_s2_manager_reassigns_service.sh
./integration_tests/test_us15_s3_filters_and_summary.sh
./integration_tests/test_us15_s5_multitenancy_isolation.sh
./integration_tests/test_us15_s6_rbac_matrix.sh
```

## 7. Cypress (admin UI)

```bash
cd /opt/homebrew/var/www/realestate/realestate_backend
npx cypress run --spec cypress/e2e/015_services_admin.cy.js
```

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `409 Conflict` on POST | Active service already exists for (client, type, agent) | Use existing service or move existing one to terminal |
| `422` on stage=`proposal` | No `property_ids` linked | PUT service with `property_ids` first |
| `422` on stage=`formalization` | No accepted proposal | Create + accept proposal via `/api/v1/proposals` |
| `423 Locked` | Service has system tag `closed` | Remove `closed` tag (Owner/Manager) before transitioning |
| `404` from another company | Multi-tenancy isolation | Verify `company_id` of authenticated user |
| `is_pending` always false | Cron not running or threshold too high | Check `thedevkitchen.service.settings.pendency_threshold_days` |

## 9. Where things live

- Models: [18.0/extra-addons/quicksol_estate/models/service.py](../../18.0/extra-addons/quicksol_estate/models/) (and siblings)
- Controllers: [18.0/extra-addons/quicksol_estate/controllers/service_controller.py](../../18.0/extra-addons/quicksol_estate/controllers/)
- Migration (EXCLUDE): [18.0/extra-addons/quicksol_estate/migrations/](../../18.0/extra-addons/quicksol_estate/migrations/)
- Tests: [18.0/extra-addons/quicksol_estate/tests/](../../18.0/extra-addons/quicksol_estate/tests/) and [integration_tests/](../../integration_tests/)
- Spec: [spec.md](./spec.md) · [spec-idea.md](./spec-idea.md) · [data-model.md](./data-model.md) · [contracts/openapi.yaml](./contracts/openapi.yaml) · [research.md](./research.md)
