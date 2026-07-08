# Infrastructure

> Sources: `18.0/docker-compose.yml`, `18.0/docker-compose-production.yml`, `18.0/Dockerfile` (root), `18.0/entrypoint.sh`, `18.0/odoo-init.sh`, `18.0/.env.example`, `DOKPLOY_DEPLOY.md`, `PRODUCTION_SETUP.md`, `docs/guide/02-docker-components.md`, `docs/guide/03-environments.md`, `18.0/observability/*`, `docs/adr/ADR-025`, `ADR-026`.

## Platform

- **Containerized**, orchestrated with **Docker Compose** (not Kubernetes). Two compose files exist:
  - `18.0/docker-compose.yml` — local development stack (default `odoo-net` bridge network, ports exposed on `localhost`).
  - `18.0/docker-compose-production.yml` — production stack, additionally attached to a `dokploy-network` (external network), indicating deployment via **Dokploy** (a self-hosted PaaS), documented in `DOKPLOY_DEPLOY.md` and `PRODUCTION_SETUP.md`.
- No Terraform/CloudFormation/Pulumi IaC was found; infrastructure is defined entirely through Compose files and Dokploy's own configuration (outside this repo).

## Environments

Per `docs/guide/03-environments.md` (existing documentation, used as base — not independently verifiable from this repo alone since the target servers are external):

| Environment | URL | Workers | Max Cron Threads | Notes |
|---|---|---|---|---|
| **Local** | http://localhost:8069 | 0 (default, threaded dev mode) | — | `docker compose up -d` from `18.0/`; default creds `admin/admin` |
| **Dev** | https://dev.torque-backoffice.thedevkitchen.com.br | 2 | 1 | Auto-deploy on push to `develop`; dev mode/reload enabled; no access restrictions |
| **Homologação (staging)** | https://homol.torque-backoffice.thedevkitchen.com.br | 4 | 2 | Manual deploy after review; weekly DB refresh from prod (sanitized) |
| **Produção** | https://torque-backoffice.thedevkitchen.com.br | 8 | 4 | Manual deploy after final approval; MFA required for admin access; VPN required for DB access |

Environment-specific tuning is driven by `.env` values (`ODOO_WORKERS`, `ODOO_MAX_CRON_THREADS`, `ODOO_LIMIT_*`, `ODOO_LOG_LEVEL`, `ODOO_DB_FILTER`, `ODOO_LIST_DB`) — see `18.0/.env.example` for the full variable catalogue (redis, celery, JWT, OAuth, seed users, OTel, Grafana/domain routing).

## CI/CD

- **No CI/CD pipeline configuration was found in this repository** — no `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, or `.circleci/` directory exists (verified: `.github/` only contains agent/prompt/skill instructions for AI coding assistants, e.g. `.github/copilot-instructions.md`, `.github/agents/*`, no `workflows/`).
- `docs/guide/02-docker-components.md` and `03-environments.md` **describe** a GitHub → CI/CD → Dev(auto)/Homol(manual)/Prod(manual) pipeline, but the pipeline definition itself is **not present in this repo** — it is either managed entirely through Dokploy's git-push-to-deploy webhooks (per `DOKPLOY_DEPLOY.md`) or lives in infrastructure tooling outside this codebase. **Discrepancy:** documentation describes an automated CI/CD pipeline with quality gates, but no executable pipeline definition (lint/test/build workflow file) exists in-repo to verify this claim; local scripts (`lint.sh`, `lint_xml.sh`, `scripts/validate_coverage.sh`, `scripts/validate_openapi_sync.sh`) exist but there is no evidence they are wired to run automatically on push/PR.
- `.coderabbit.yaml` at the repo root configures **CodeRabbit** (AI PR review bot) — the closest thing to an automated code-quality gate found in-repo, but this is a review aid, not a build/test pipeline.

## Support Services (from `docker-compose*.yml` / `.env.example`)

| Service | Image | Role |
|---|---|---|
| `db` | postgres:16-alpine | Primary relational database (`realestate`) |
| `redis` | redis:7-alpine | HTTP session cache, JWT validation cache (native Odoo 18 Redis support), Celery result backend (`db=2`) |
| `rabbitmq` | rabbitmq:3-management-alpine | AMQP broker for Celery; management UI on `:15672` |
| `celery_commission_worker` / `celery_audit_worker` / `celery_notification_worker` | custom-celery-worker:18.0 (built from `18.0/celery_worker/Dockerfile`) | Async task processing, one process per queue (see [crons-queues.md](crons-queues.md)) |
| `flower` | mher/flower:2.0 | Celery monitoring UI on `:5555` (basic-auth protected) |
| `mailhog_realestate` + `mailhog_mongo` | mailhog/mailhog:latest + mongo:4.4-focal | Dev-only fake SMTP server + message persistence backing store |
| `odoo-init` | custom-odoo:18.0 (same image as `odoo`) | One-shot init/upgrade container (`odoo-init.sh`) that installs/upgrades modules and seeds admin password before `odoo` starts (`service_completed_successfully` dependency gate) |
| Observability stack (`18.0/observability/`) | Prometheus, Loki, Tempo, Grafana (+ Promtail) | Metrics, logs, and distributed traces; provisioned dashboards under `observability/grafana/dashboards/` including a dedicated Kong API Gateway dashboard (ADR-026) |
| Kong API Gateway | External repository (not in this codebase) | Production-only reverse proxy / rate-limiting layer in front of Odoo, integrated into the same observability stack (ADR-026) |

**Reverse proxy / CDN:** no reverse proxy (nginx/Traefik/Caddy) configuration was found inside this repository; SSL/TLS termination and domain routing for `*.torque-backoffice.thedevkitchen.com.br` subdomains (Grafana, Flower, MailHog, RabbitMQ, Swagger) are referenced via `.env` variables (`GRAFANA_DOMAIN`, `ODOO_DOMAIN`, `FLOWER_DOMAIN`, `MAILHOG_DOMAIN`, `RABBITMQ_DOMAIN`) but the actual proxy/router configuration lives in Dokploy, external to this repo.

## Web Server / Runtime Configuration

- Odoo runs on its bundled **Werkzeug** HTTP server (`odoo-bin`), not behind Gunicorn/uWSGI.
- Ports exposed: `8069` (HTTP), `8071` (XML-RPCS), `8072` (longpolling/websocket bus).
- `odoo.conf` base config: `db_host=db`, `db_name=realestate`, Redis session/cache enabled (`enable_redis=True`, `redis_dbindex=1`), most performance-tuning directives (`workers`, `limit_memory_hard/soft`, `limit_time_cpu/real`, `max_cron_threads`) left commented out in the checked-in `odoo.conf` and instead expected to be supplied via environment variables per environment (see Environments table above) — this indirection is a mild discrepancy worth flagging since the checked-in `odoo.conf` alone does not reflect production tuning.
- Container base image: Ubuntu Noble with Odoo 18.0 nightly `.deb` package, `wkhtmltopdf` for PDF report generation, `python3-magic`/`python3-phonenumbers`/etc. system packages, and Node.js `rtlcss`/`node-less` for asset building.

## Discrepancies / Gaps

- No automated CI pipeline definition found despite documentation describing one (see CI/CD section above) — recommend confirming with the team whether this lives in Dokploy or a separate infra repo.
- `odoo.conf` checked into the repo has most performance directives commented out; actual per-environment values (workers, cron threads, memory limits) are asserted only in `docs/guide/03-environments.md`, not verifiable from any `.env` file present in this repo (production `.env` values are not committed, as expected for secrets).
