# External Integrations

> Sources: `docs/adr/ADR-026`, `docs/architecture/event-driven-rbac.md`, `18.0/docker-compose.yml`, `18.0/celery_worker/tasks.py`, `18.0/extra-addons/quicksol_estate/data/system_parameters.xml`, `18.0/observability/*`, code search for outbound HTTP calls.

## Kong API Gateway

| Field | Value |
|-------|-------|
| **Type** | Other (API Gateway / reverse proxy — infrastructure integration) |
| **Direction** | Inbound (all external client traffic passes through it in production) |
| **Protocol** | REST (HTTP/HTTPS), plugin-based (Prometheus metrics scrape, OpenTelemetry) |
| **Frequency** | Real-time (every request) |
| **Modules/Services** | All REST controllers under `/api/v1/*` and `/api/docs` (front door in production only; bypassed locally) |
| **Data exchanged** | All API request/response payloads; Prometheus metrics (`/metrics`) scraped by the observability stack; OTLP traces forwarded to the shared Grafana Tempo backend |
| **Notes** | Maintained in a **separate repository** (`apigateway`), referenced only from this repo's ADRs (ADR-026) and `docker-compose-production.yml` network wiring (`dokploy-network`). Not directly inspectable from this codebase. |

## Grafana Observability Stack (Prometheus / Loki / Tempo / Grafana)

| Field | Value |
|-------|-------|
| **Type** | Analytics/Monitoring |
| **Direction** | Outbound (Odoo + Celery workers push metrics/logs/traces) |
| **Protocol** | OTLP/gRPC (traces), Prometheus scrape (metrics, pull-based from Kong and presumably Odoo), Promtail/Docker socket (logs) |
| **Frequency** | Real-time (always-on sampler, `OTEL_TRACES_SAMPLER=always_on` by default) |
| **Modules/Services** | `thedevkitchen_observability` (Odoo + Celery instrumentation), `18.0/observability/` compose stack |
| **Data exchanged** | Spans (HTTP request tracing, DB/Redis operation tracking), `trace_id`-correlated logs, request/error-rate/latency metrics, Kong gateway metrics (ADR-026) |

## RabbitMQ + Celery (internal async messaging)

| Field | Value |
|-------|-------|
| **Type** | Other (internal messaging backbone) |
| **Direction** | Bidirectional (Odoo publishes events; Celery workers call back into Odoo via XML-RPC/REST) |
| **Protocol** | AMQP (broker), XML-RPC/HTTP (worker → Odoo callback, see `celery_worker/tasks.py` `xmlrpc.client` import) |
| **Frequency** | Real-time (event-driven) |
| **Modules/Services** | `quicksol_estate` (event_bus.py), `thedevkitchen_estate_credit_check`, `celery_worker/tasks.py` |
| **Data exchanged** | Domain events (`user.created`, `property.created`, `commission.split.calculated`, `property.assignment.changed`), proposal notification emails |
| **Notes** | Fully documented in [crons-queues.md](crons-queues.md); listed here because it is a service-to-service integration, not just an in-process mechanism. |

## MailHog (development/testing only)

| Field | Value |
|-------|-------|
| **Type** | Other (email testing double) |
| **Direction** | Outbound (Odoo/Celery send emails to it instead of a real SMTP relay) |
| **Protocol** | SMTP (port 1025), REST/Web UI (port 8025) |
| **Frequency** | Real-time, on-demand (invites, password reset, proposal notifications, lease/renewal emails) |
| **Modules/Services** | `thedevkitchen_user_onboarding`, `quicksol_estate` (proposal mail templates), any module using `mail.template`/`mail.mail` |
| **Data exchanged** | Outgoing transactional emails (captured, not delivered) |
| **Notes** | ADR-023 documents this as dev/staging-only; **no production SMTP relay (SendGrid, AWS SES, etc.) configuration was found in this repository** — `docs/guide/02-docker-components.md` recommends one for production but the actual outgoing mail server configuration for prod is **Not identified** (likely configured directly in the production Odoo database via `ir.mail_server`, which is not version-controlled). |

## OAuth 2.0 Client (external Frontend application)

| Field | Value |
|-------|-------|
| **Type** | SSO / API consumer authentication |
| **Direction** | Inbound |
| **Protocol** | REST, OAuth 2.0 `client_credentials` grant (RFC 6749), JWT Bearer tokens (RFC 9068 profile) |
| **Frequency** | Real-time |
| **Modules/Services** | `thedevkitchen_apigateway` (`auth_controller.py`: `/api/v1/auth/token`, `/refresh`, `/revoke`) |
| **Data exchanged** | Access/refresh tokens; the external frontend (Next.js/React, referenced in `docs/guide/02-docker-components.md` and the `thedevkitchen_cms` public SSR route) is the primary consumer |

## Odoo native IAP `partner_autocomplete` service — explicitly disabled

| Field | Value |
|-------|-------|
| **Type** | Other (Odoo built-in SaaS service) |
| **Direction** | N/A (disabled) |
| **Protocol** | N/A |
| **Frequency** | N/A |
| **Modules/Services** | `quicksol_estate/data/system_parameters.xml` |
| **Data exchanged** | None — a system parameter explicitly disables the IAP `partner_autocomplete` endpoint to avoid request timeouts during company seeding. Documented here because it is a deliberate integration decision (opt-out), not an oversight. |

## Not Found / Not Identified

- **No payment gateway integration** (Stripe, PagSeguro, Mercado Pago, etc.) was found in code — commissions/sales appear to be tracked internally (accounting entities) without an external payment processor.
- **No CEP (Brazilian postal code) lookup webservice call** (e.g. ViaCEP) was found via code search (`requests.get`/`urlopen` grep in `quicksol_estate`); despite the module description mentioning "CEP integration," this could not be confirmed as an outbound HTTP integration in the current codebase — recorded as **Not identified**, reason: no matching outbound HTTP call found; may be a manual/local-only field, a frontend-side integration (outside this repo), or dead/planned functionality.
- **No logistics/ERP/marketing/analytics-platform integrations** (e.g., Google Analytics, HubSpot, ERP connectors) were found in code.
