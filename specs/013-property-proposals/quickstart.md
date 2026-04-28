# Quickstart: Property Proposals (Feature 013)

**Audience**: Developers picking up implementation tasks for feature 013-property-proposals.
**Branch**: `013-property-proposals`
**Module**: `quicksol_estate` (Odoo 18.0)

---

## 1. Prerequisites

Working environment:

- Docker + Docker Compose (project uses `18.0/docker-compose.yml`)
- Repository cloned to `/opt/homebrew/var/www/realestate/realestate_backend`
- On branch `013-property-proposals`
- ADR-027 (Pessimistic Locking for Resource Queues) authored at `docs/adr/ADR-027-pessimistic-locking-resource-queues.md` *(blocker — must exist before code is merged)*

---

## 2. Spin up the stack

```bash
cd 18.0
docker compose up -d
docker compose logs -f odoo  # in another shell — wait for "HTTP service running"
```

Visit:

- Odoo Web: http://localhost:8069
- Odoo API docs (post-development): http://localhost:8069/api/docs
- MailHog (test inbox for transactional emails): http://localhost:8025
- Flower (Celery monitor): http://localhost:5555

DB: `realestate` / user `admin` / password `admin` (per `.github/copilot-instructions.md`).

---

## 3. Install / upgrade the module

After making model or view changes:

```bash
docker compose exec odoo odoo -d realestate -u quicksol_estate --stop-after-init
```

For a fresh install (data + sequence + cron + templates):

```bash
docker compose exec odoo odoo -d realestate -i quicksol_estate --stop-after-init
```

---

## 4. Run tests

```bash
# Unit tests for the proposal model + controller + lead integration
docker compose exec odoo odoo -d realestate \
  --test-tags /quicksol_estate:test_proposal_model,test_proposal_controller,test_proposal_lead_integration \
  --stop-after-init

# Integration tests (E2E API) - run from the repo root
./integration_tests/test_us1_proposal_create_send.sh
./integration_tests/test_us2_proposal_fifo_queue.sh
./integration_tests/test_us3_proposal_counter.sh
./integration_tests/test_us4_proposal_accept_reject.sh
./integration_tests/test_us5_proposal_lead_capture.sh
./integration_tests/test_us6_proposal_list_filters_metrics.sh
./integration_tests/test_us7_proposal_attachments.sh
./integration_tests/test_us8_proposal_expiration.sh
./integration_tests/test_us_proposal_concurrent_creation.sh   # SC-003 race-condition load test

# Cypress E2E for Odoo views
npx cypress run --spec 'cypress/e2e/views/proposals.cy.js'
```

---

## 5. Manual smoke test (REST)

Get an OAuth token (existing flow per Feature 007):

```bash
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/oauth/token \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"...", "client_secret":"...", "grant_type":"client_credentials"}' \
  | jq -r .access_token)
SESSION=...    # set via auth/login (returns X-Openerp-Session-Id)
```

Create a proposal:

```bash
curl -X POST http://localhost:8069/api/v1/proposals \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION" \
  -H 'Content-Type: application/json' \
  -d '{
    "property_id": 12,
    "client_name": "Ana Silva",
    "client_document": "12345678901",
    "client_email": "ana@example.com",
    "client_phone": "+5511999998888",
    "agent_id": 3,
    "proposal_type": "sale",
    "proposal_value": 550000.00
  }'
```

Send it:

```bash
curl -X POST http://localhost:8069/api/v1/proposals/1/send \
  -H "Authorization: Bearer $TOKEN" -H "X-Openerp-Session-Id: $SESSION"
```

Check MailHog at http://localhost:8025 — the `proposal_sent` template email should appear.

Inspect the queue for that property:

```bash
curl http://localhost:8069/api/v1/proposals/1/queue \
  -H "Authorization: Bearer $TOKEN" -H "X-Openerp-Session-Id: $SESSION"
```

---

## 6. Verifying the FIFO invariant

The most important business rule. Two ways to verify:

### Option A — Manual (dev shell)

```bash
docker compose exec odoo odoo shell -d realestate
```

```python
P = env['real.estate.proposal']
# Create 5 proposals concurrently for the same empty property would normally race;
# the model handles it via SELECT FOR UPDATE.
# Quick check: there must be at most one with state in ('draft','sent','negotiation','accepted')
# AND active=True AND parent_proposal_id IS NULL per property at any time.
prop = env['real.estate.property'].browse(12)
active = P.search([('property_id','=',prop.id),
                   ('state','in',['draft','sent','negotiation','accepted']),
                   ('active','=',True),
                   ('parent_proposal_id','=',False)])
print(f"Active count: {len(active)} (must be 0 or 1)")
```

### Option B — Automated load test

```bash
./integration_tests/test_us_proposal_concurrent_creation.sh
# 100 trials × 10 parallel writes; asserts exactly 1 active per trial.
```

---

## 7. Common pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `IntegrityError: real_estate_proposal_one_active_per_property` | Logic skipped the `SELECT FOR UPDATE` path. | Audit `create()` override; never write `state='draft'` from outside `create()` without acquiring the property lock. |
| Email not sent after `/accept` | Celery worker not running OR RabbitMQ down. | `docker compose ps`; check `celery_notification_worker` logs. State transition still succeeds (per FR-041a) and failure is logged in proposal chatter. |
| Listing returns proposals from another company | Missing `@require_company` on controller OR record rule disabled. | Verify all 4 record rules are loaded (`security/proposal_record_rules.xml`); confirm decorator stack on the controller. |
| Counter-proposal collides with parent on unique index | Partial unique index missing `parent_proposal_id IS NULL` clause. | Re-run `migrations/18.0.1.x.0/post-migrate.py`. |
| Queue position not updating after sibling promoted | Stored compute trigger missing dependency. | Inspect `@api.depends` on `_compute_queue_position` — must include sibling state changes via `property_id.proposal_ids.state`. |

---

## 8. Where things live

| Concern | File |
|---|---|
| Model + FSM | `18.0/extra-addons/quicksol_estate/models/proposal.py` |
| Lead extension | `18.0/extra-addons/quicksol_estate/models/lead.py` |
| Property cascade | `18.0/extra-addons/quicksol_estate/models/property.py` |
| REST controllers | `18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py` |
| Views | `18.0/extra-addons/quicksol_estate/views/proposal_views.xml` |
| Record rules | `18.0/extra-addons/quicksol_estate/security/proposal_record_rules.xml` |
| Sequence | `18.0/extra-addons/quicksol_estate/data/proposal_sequence.xml` |
| Cron | `18.0/extra-addons/quicksol_estate/data/proposal_cron.xml` |
| Mail templates | `18.0/extra-addons/quicksol_estate/data/mail_templates_proposal.xml` |
| Migration | `18.0/extra-addons/quicksol_estate/migrations/18.0.1.x.0/` |
| Unit tests | `18.0/extra-addons/quicksol_estate/tests/test_proposal_*.py` |
| Integration tests | `integration_tests/test_us[1-8]_proposal_*.sh` |
| Cypress E2E | `cypress/e2e/views/proposals.cy.js` |
| OpenAPI contract | `specs/013-property-proposals/contracts/openapi.yaml` |
| Spec | `specs/013-property-proposals/spec.md` |
| Plan | `specs/013-property-proposals/plan.md` |
| Data model | `specs/013-property-proposals/data-model.md` |
| ADR-027 | `docs/adr/ADR-027-pessimistic-locking-resource-queues.md` (must exist) |

---

## 9. Post-development deliverables

After the feature is merged, generate:

- `docs/openapi/proposals.yaml` (publish version of `contracts/openapi.yaml` — ADR-005)
- `docs/postman/feature013_property_proposals_v1.0_postman_collection.json` (ADR-016)
- Constitution bump to v1.4.0 (Concurrency Patterns section + ADR-027 reference)

---

## 10. Useful one-liners

```bash
# List all proposals (dev shell)
docker compose exec odoo odoo shell -d realestate -c "env['real.estate.proposal'].search([]).read(['proposal_code','state','property_id','agent_id','queue_position'])"

# Trigger expiration cron manually (for testing)
docker compose exec odoo odoo shell -d realestate -c "env.ref('quicksol_estate.cron_expire_proposals').method_direct_trigger()"

# Check Redis cache (DB index 1)
docker compose exec redis redis-cli -n 1 KEYS '*proposal*'
```
