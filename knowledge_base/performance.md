# Performance

> Sources: `18.0/odoo.conf`, `18.0/docker-compose.yml`, `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`, `docs/architecture/DATABASE_ARCHITECTURE_USERS.md` (§11.3), `docs/architecture/event-driven-rbac.md`, `TECHNICAL_DEBIT.md`, `docs/guide/02-docker-components.md`.

## Cache Strategy

- **Redis** is the single cache layer for the whole platform (`redis:7-alpine`, `maxmemory 256mb`, `allkeys-lru` eviction, AOF persistence). Three distinct usages, all pointing at the same Redis instance but different logical DB indexes:
  - **DB index 1** — Odoo native HTTP session storage and ORM cache (`enable_redis=True`, `redis_dbindex=1` in `odoo.conf`; this is Odoo 18's built-in Redis session backend, not a custom implementation).
  - **DB index 2** — Celery result backend (`CELERY_RESULT_BACKEND=redis://:<pwd>@redis:6379/2`), with password URL-encoding handled explicitly in `celery_worker/tasks.py` to avoid kombu parser failures on special characters.
  - **Custom cache-aside layer** (`thedevkitchen_apigateway/services/redis_client.py`, used by `middleware.py`) — caches validated JWT payloads (`RedisClient.jwt_key(token)`) to avoid a DB lookup (`thedevkitchen.oauth.token` browse) on every authenticated request; falls back gracefully to a DB lookup on cache MISS or if `RedisClient` import fails.
- No full-page/HTTP edge cache (e.g. Varnish, CDN cache-control) was found in this repo; caching is application/session-level only.
- No CDN configuration was found for static assets; Odoo serves its own web assets bundle (`web.assets_backend`/`web.assets_frontend`) directly.

## Search / Indexing

- No dedicated search engine (Elasticsearch/OpenSearch/Algolia) is used. Search/filtering is performed via standard PostgreSQL queries (Odoo ORM `search()` domains) with targeted B-tree indexes added on hot columns, e.g.:
  - `real_estate_agent(cpf)`, `real_estate_agent(creci_normalized)` — indexed lookup fields.
  - `res_users(login)` — Odoo core index.
  - Composite index `(company_id, year, month, operation_type) WHERE active=true` on the goals-achievement query path (`thedevkitchen_estate_goals`).
- Computed fields that are expensive to recalculate are `store=True` + `index=True` where used for lookups (e.g., `creci_normalized`), avoiding recomputation on every read.

## Async Processing / Background Jobs

Fully covered in [crons-queues.md](crons-queues.md); in summary: RabbitMQ + 3 dedicated Celery worker processes (commission, audit, notification queues) offload non-critical/bulk work from the synchronous request path, per ADR-021. Retry policy on Celery tasks: `max_retries=3`, exponential backoff with jitter (per `docs/guide/02-docker-components.md`; retry decorator confirmed in `tasks.py` via `@app.task(bind=True, max_retries=3)`).

## Runtime Performance Settings

- Odoo worker/thread tuning (`workers`, `max_cron_threads`, `limit_time_cpu`, `limit_time_real`, `limit_memory_hard/soft`, `limit_request`) is **environment-variable driven** (`ODOO_WORKERS`, `ODOO_MAX_CRON_THREADS`, `ODOO_LIMIT_*` in `.env`), not hardcoded in the checked-in `odoo.conf` (which leaves these directives commented out). Documented target values per environment (dev/homol/prod) are in [infrastructure.md](infrastructure.md).
- No Python-level GC tuning or opcode-cache/JIT configuration (e.g. no `PYTHONOPTIMIZE`, no gunicorn/uwsgi worker recycling) was found — Odoo runs under its own multi-worker prefork model (`odoo-bin`), standard for the framework.
- Celery worker concurrency is tuned per queue (see [crons-queues.md](crons-queues.md)): `commission_events` concurrency 2, `audit_events` concurrency 1, `notification_events` concurrency 1.
- PostgreSQL tuning values documented in `docs/guide/02-docker-components.md` (`max_connections=100`, `shared_buffers=256MB`, `effective_cache_size=1GB`, `maintenance_work_mem=64MB`) — these are **descriptive of intent**, not found as an actual `postgresql.conf` override file in this repo (the `db` service uses the stock `postgres:16-alpine` image with no custom config mount), so actual production tuning could not be verified from code.

## CDN / Static Asset Strategy

Not found — no CDN, `web.assets` bundling customization beyond standard Odoo asset bundles (`web.assets_backend`, `web.assets_frontend`), and no static-asset offload (e.g., S3 + CloudFront) configuration for attachments/media (property photos, CMS media library) was identified; Odoo's filestore (`/var/lib/odoo`, Docker volume `odoo18-data`) is the only storage backend found for binary attachments.

## Discrepancies / Findings

- `TECHNICAL_DEBIT.md` lists as **pending**: "substituir consultas ao banco de dados por cache no redis para o processo de login" and "incluir a consulta do session_id e do JWT no redis, para ganho de performance." However, the current code in `thedevkitchen_apigateway/middleware.py` **already implements** a Redis cache-aside pattern for JWT validation (`RedisClient.jwt_key`, populated ORM field cache on HIT). This suggests the technical debt note is **partially stale** — likely written before, or independently of, the recent "023-redis-session-cache" change (see `git log`: PR #25, merged). Recommend the team re-validate and update `TECHNICAL_DEBIT.md` to reflect current state (e.g., clarify what specifically remains unimplemented — session_id lookup vs. JWT token lookup may be two distinct, only-partially-addressed items).
- No load-testing/benchmark artifacts (e.g. k6, Locust, JMeter scripts) were found in the repository to validate the performance characteristics described in the environment tables.
