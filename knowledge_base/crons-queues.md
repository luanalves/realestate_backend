# Scheduled Jobs and Message Queues

> Sources: `18.0/extra-addons/*/data/*.xml` (`ir.cron` records), `18.0/extra-addons/quicksol_estate/models/event_bus.py`, `18.0/celery_worker/tasks.py`, `18.0/docker-compose.yml`, `docs/adr/ADR-020`, `ADR-021`, `docs/architecture/event-driven-rbac.md`.

## Scheduled Jobs (`ir.cron`, Odoo's native scheduler)

| Job Name | Schedule | Handler | Module | Purpose |
|---|---|---|---|---|
| Lease: Auto-expire past end date | Every 1 day | `real.estate.lease._cron_expire_leases()` | `quicksol_estate` | Automatically transitions active leases whose `end_date` has passed to an expired state (`data/lease_cron.xml`, feature CHK002). |
| Proposal: Auto-expire past valid_until | Every 1 hour | `real.estate.proposal._cron_expire_proposals()` | `quicksol_estate`, extended (`_inherit` + `super()`) by `thedevkitchen_estate_credit_check/models/proposal_extension.py` | Expires property proposals past their `valid_until` date; queue-promotion logic (FIFO) then activates the next queued proposal (`data/proposal_cron.xml`, FR-026/US8). The credit-check module piggybacks on this **same** cron job (overriding `_cron_expire_proposals` and calling `super()`) rather than registering its own `ir.cron` record — this is how "cron-driven expiry of pending checks," mentioned in that module's manifest description, is actually implemented. |
| Service: Recompute pendency status (is_pending) | Every 1 day (~03:00 UTC) | `real.estate.service._cron_recompute_pendency()` | `quicksol_estate` | Recomputes the `is_pending` flag on active service-pipeline records (`data/service_cron_data.xml`, FR-015). |
| Auto-vacuum audit logs | Every 1 day (**disabled by default**, `active=False`) | `auditlog.autovacuum(180)` | `auditlog` (OCA) | Purges audit-log entries older than 180 days when enabled. |

No independent `ir.cron` jobs were found in `thedevkitchen_apigateway`, `thedevkitchen_cms`, `thedevkitchen_estate_goals`, `thedevkitchen_observability`, or `thedevkitchen_user_onboarding`.

## Message Queues (RabbitMQ + Celery)

### Architecture

Event-driven, hybrid sync/async processing built on the **Observer Pattern** (`quicksol.event.bus`, ADR-020) extended with **async messaging** (ADR-021) to avoid blocking the HTTP request thread on bulk/non-critical operations (e.g., importing 1000 properties, auditing every field change).

### Queue topology (verified in code)

| Queue | Producer(s) | Consumer worker (`docker-compose.yml` service) | Concurrency | Purpose |
|---|---|---|---|---|
| `audit_events` | `event_bus.py` `EVENT_QUEUE_MAP`: `user.created`, `property.created`; `tasks.py` `process_event_task` (statically routed here) | `celery_audit_worker` (`--queues=audit_events`) | 1 | Auditing/compliance logging (LGPD), decoupled from the write transaction. |
| `commission_events` | `event_bus.py` `EVENT_QUEUE_MAP`: `commission.split.calculated` | `celery_commission_worker` (`--queues=commission_events`) | 2 | Commission split calculation between prospector + agent after a sale/lease closes. |
| `notification_events` | `event_bus.py` `EVENT_QUEUE_MAP`: `property.assignment.changed`; `proposal.py` (`send_proposal_notification.apply_async(queue="notification_events")`); `thedevkitchen_estate_credit_check/services/credit_check_service.py` (same task/queue) | `celery_notification_worker` (`--queues=notification_events`) | 1 | Async email notifications (proposal sent/accepted/rejected, credit-check results, assignment changes). |

### Task definitions (`18.0/celery_worker/tasks.py`)

- `process_event_task` — generic event-processing task, statically routed to `audit_events` via `app.conf.task_routes`.
- `proposal.send_email` (registered task name) — sends proposal-related notification emails; retried up to 3 times (`@app.task(bind=True, max_retries=3)`).
- The worker process calls back into Odoo via `xmlrpc.client` (imported at the top of `tasks.py`) to read/write Odoo records from outside the Odoo process.
- Celery result backend: Redis DB index 2, with password URL-encoding handled explicitly to avoid kombu parsing failures on special characters in `REDIS_PASSWORD`.
- OpenTelemetry instrumentation (`CeleryInstrumentor`) auto-creates spans for task execution and propagates W3C trace context from task headers, correlating Celery task traces with the originating Odoo HTTP request trace.

### Monitoring

- **Flower** (`mher/flower:2.0`, port `5555`, basic-auth protected) provides a live UI for worker status, task success/failure rates, and queue depth.
- **RabbitMQ Management UI** (port `15672`) for queue/binding inspection and manual queue purging (documented in `docs/guide/02-docker-components.md`).

## Discrepancies / Findings

- **Queue naming mismatch between documentation and code**: `docs/guide/02-docker-components.md` describes queues named `commission_queue`, `notification_queue`, `audit_queue` with concurrency 2/4/2 respectively. The actual, verified queue names in `docker-compose.yml` and in the Python source (`event_bus.py`, `proposal.py`, `tasks.py`) are `commission_events`, `notification_events`, `audit_events`, with concurrency 2/1/1. **The code is the source of truth used in the table above**; the guide document appears stale and should be corrected.
- `thedevkitchen_estate_credit_check`'s manifest description mentions "cron-driven expiry of pending checks" as if it were a standalone feature; in reality it extends the existing `quicksol_estate` proposal-expiry cron via inheritance rather than defining a new `ir.cron` record — documented above for clarity, not a functional gap.
