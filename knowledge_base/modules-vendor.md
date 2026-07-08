# Third-Party Dependencies (Vendor)

> Sources: `Dockerfile` (root, image build for the `odoo` service), `18.0/celery_worker/requirements.txt`, `18.0/extra-addons/*/__manifest__.py` (`external_dependencies`), `18.0/package.json`, `18.0/.flake8`.
> Odoo core itself (the framework/runtime) and its official first-party addons (`base`, `web`, `mail`, `bus`, `portal`) are excluded here — see [architecture.md](architecture.md) for the core stack.

## Odoo Community Association (OCA) module

### auditlog
- **Version:** 18.0.2.0.2
- **Category:** Compliance / Audit
- **Purpose:** Generic audit-log module (OCA `server-tools`) — records CRUD operations, HTTP sessions and HTTP requests for models flagged for auditing. Installed under `18.0/extra-addons/auditlog` alongside the custom modules; author is ABF OSIELL / OCA, license AGPL-3 (note: stricter copyleft than the project's own LGPL-3 modules). Ships its own `ir.cron` job (`Auto-vacuum audit logs`, disabled by default).

## Python packages (installed via `pip3` in the Odoo image `Dockerfile`)

### authlib
- **Version:** 1.6.5
- **Category:** Auth
- **Purpose:** OAuth 2.0 server implementation backing `thedevkitchen_apigateway` (client_credentials grant, token introspection/revocation).

### PyJWT
- **Version:** 2.10.1
- **Category:** Auth
- **Purpose:** JWT encode/decode for the API Gateway's `require_jwt` authentication decorator and session fingerprinting.

### bcrypt
- **Version:** 5.0.0
- **Category:** Auth
- **Purpose:** Password/token hashing.

### cryptography
- **Version:** 46.0.3
- **Category:** Auth / Security
- **Purpose:** Underlying crypto primitives for JWT/OAuth signing and TLS-related operations.

### jsonschema
- **Version:** 4.25.1
- **Category:** Dev/QA
- **Purpose:** Request/response schema validation for REST APIs (ADR-018 input validation layer).

### email-validator
- **Version:** 2.1.0 (Docker image) / listed again as `email_validator` in `thedevkitchen_user_onboarding` manifest
- **Category:** Dev/QA (validation)
- **Purpose:** RFC-compliant email address validation used in onboarding/invite flows.

### validate_docbr
- **Category:** Integration (Brazilian market validation)
- **Purpose:** CPF/CNPJ validation for Brazilian real estate documents (agents, owners, companies).

### python-magic (`magic`)
- **Category:** Security
- **Purpose:** Magic-byte (not extension-based) MIME type detection for CMS media upload validation (`thedevkitchen_cms`).

### celery[redis]
- **Version:** 5.3.4
- **Category:** Messaging/Queue
- **Purpose:** Distributed task queue for asynchronous processing (commission calculation, notifications, audit events). Installed both in the Odoo image and in the dedicated `celery_worker` image.

### opentelemetry-api / opentelemetry-sdk / opentelemetry-exporter-otlp-proto-grpc / opentelemetry-instrumentation / opentelemetry-instrumentation-celery
- **Version:** >=1.22.0 (core), >=0.43b0 (instrumentation)
- **Category:** Dev/QA (Observability)
- **Purpose:** Distributed tracing SDK and auto-instrumentation for Odoo controllers, DB calls, and Celery tasks, exporting to Grafana Tempo (ADR-025, ADR-026).

### Code-quality toolchain (installed in the Odoo image, per ADR-022)
| Package | Version | Purpose |
|---|---|---|
| black | 24.10.0 | Python code formatter |
| isort | 5.13.2 | Import sorting (Black-compatible) |
| flake8 | 7.1.1 | Linting (PEP 8 + `E501/E203/W503/E402` ignored per `18.0/.flake8`, max line length 88) |
| pylint | 3.3.1 | Deep static analysis |
| mypy | 1.13.0 | Gradual static type checking |

## Celery worker image dependencies (`18.0/celery_worker/requirements.txt`)

### pika
- **Version:** 1.3.2
- **Category:** Messaging/Queue
- **Purpose:** Low-level AMQP client (RabbitMQ), used alongside/underneath Celery's broker transport.

### pandas
- **Version:** 2.1.4
- **Category:** Data processing
- **Purpose:** Used within Celery tasks for batch/report data processing (e.g., commission calculation task).

### requests
- **Version:** 2.31.0
- **Category:** Integration
- **Purpose:** HTTP client used by Celery tasks to call back into the Odoo XML-RPC/REST API.

### python-dotenv
- **Version:** 1.0.0
- **Category:** Dev/QA
- **Purpose:** Loads `.env` file variables into the Celery worker process.

## Frontend / test tooling (`18.0/package.json`)

### cypress
- **Version:** ^15.10.0
- **Category:** Dev/QA
- **Purpose:** End-to-end browser testing framework (ADR-002) driving the ~60+ specs under `cypress/e2e/`.

## Infrastructure images (not language packages, but vendor components pinned in `docker-compose.yml`)

| Image | Version pin | Category | Purpose |
|---|---|---|---|
| `postgres` | 16-alpine | Database | Primary relational datastore |
| `redis` | 7-alpine | Cache | HTTP session cache, JWT cache, Celery result backend |
| `rabbitmq` | 3-management-alpine | Messaging/Queue | AMQP broker + management UI |
| `mher/flower` | 2.0 | Dev/QA (monitoring) | Celery task monitoring UI |
| `mongo` | 4.4-focal | Data store | Backing store for MailHog message persistence |
| `mailhog/mailhog` | latest | Email (dev only) | SMTP capture server for development/testing |

## Discrepancies / Findings

- `auditlog` (AGPL-3) is bundled inside `extra-addons/` alongside project modules licensed LGPL-3. No license-conflict issue was found in code (it is a separate installable module, not linked/imported by the LGPL modules), but it is worth flagging for legal review if the project is ever distributed as a combined work.
- No `requirements.txt` exists for the main Odoo image; all Python dependencies are pinned ad hoc inside `Dockerfile` `RUN pip3 install` layers rather than a single manifest. This makes dependency auditing/upgrades harder to track in one place.
