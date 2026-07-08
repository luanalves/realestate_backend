# Knowledge Base — Realestate Backend (Odoo 18.0)

This knowledge base has two parts:

1. **Project Discovery** (this update) — the detailed, code-verified technical truth about this specific codebase: custom/vendor modules, architecture, infrastructure, multi-tenancy, integrations, performance, security, scheduled jobs/queues, API surface, and testing strategy.
2. **Odoo Development Guidelines** (pre-existing) — general Odoo 18/19 coding standards and conventions used as a reference during development (not specific to this project's business logic).

**Last updated:** 2026-07-08
**Detected stack:** Odoo 18.0 (Python 3.12, self-built Docker image) + PostgreSQL 16 + Redis 7 + RabbitMQ 3 + Celery 5.3.4. Source root analyzed: `18.0/` (contains `odoo.conf`, `docker-compose.yml`, `extra-addons/`, `celery_worker/`).
**Prior documentation used as base (Step 0.5):** `README.md` (root and `18.0/`), `docs/guide/*` (chapters 1–5), `docs/adr/*` (29 ADRs), `docs/architecture/*`, `TECHNICAL_DEBIT.md`. All discrepancies found between this prior documentation and the actual code are called out explicitly in each file below.

---

## Part 1 — Project Discovery

| File | Area | Last updated |
|------|------|--------------|
| [modules-custom.md](modules-custom.md) | Custom modules/components (8 TheDevKitchen/Quicksol addons) | 2026-07-08 |
| [modules-vendor.md](modules-vendor.md) | Third-party dependencies (OCA module + Python/infra packages) | 2026-07-08 |
| [architecture.md](architecture.md) | Architecture and tech stack | 2026-07-08 |
| [infrastructure.md](infrastructure.md) | Infrastructure, environments, CI/CD, support services | 2026-07-08 |
| [multi-tenancy.md](multi-tenancy.md) | Multi-tenancy (multi-agency SaaS) model | 2026-07-08 |
| [integrations.md](integrations.md) | External integrations (Kong, observability, MailHog, OAuth2) | 2026-07-08 |
| [performance.md](performance.md) | Cache, indexing, async processing, runtime tuning | 2026-07-08 |
| [security.md](security.md) | Authentication, RBAC, CORS, compliance, known gaps | 2026-07-08 |
| [crons-queues.md](crons-queues.md) | Scheduled jobs (`ir.cron`) and RabbitMQ/Celery queues | 2026-07-08 |
| [api-surface.md](api-surface.md) | Full REST API surface (~180 endpoints across 9 modules) | 2026-07-08 |
| [testing.md](testing.md) | Testing strategy (Cypress, curl/integration_tests, coverage) | 2026-07-08 |

### Key discoveries at a glance

- **Single Odoo 18.0 instance**, modular monolith, extended with 8 custom addons + 1 vendored OCA module (`auditlog`); headless REST API (JWT/OAuth2) is the primary contract — there is no server-rendered customer frontend in this repo.
- **Multi-tenant SaaS** for real estate agencies (`res.company` = tenant), enforced via `ir.rule` record rules + an API-layer "5 principles" security model (ADR-008), with a documented **open gap**: action authorization is currently global (Odoo security groups) rather than per-company, despite per-company profile data already existing (see [multi-tenancy.md](multi-tenancy.md)).
- **Event-driven async processing** via an in-house Observer/EventBus pattern (ADR-020) feeding RabbitMQ + 3 dedicated Celery workers (`commission_events`, `audit_events`, `notification_events`).
- **No CI/CD pipeline definition found in this repository** despite documentation describing one — likely managed externally via Dokploy (see [infrastructure.md](infrastructure.md)).
- A **stale, unreferenced duplicate `addons/` directory** exists at the repository root (outside `18.0/`), not wired into `odoo.conf`/`docker-compose.yml`, and missing manifests in places — flagged as a cleanup candidate in [modules-custom.md](modules-custom.md).
- Queue names/concurrency in `docs/guide/02-docker-components.md` do not match the actual code/compose configuration — corrected in [crons-queues.md](crons-queues.md) and [architecture.md](architecture.md).

---

## Part 2 — Odoo Development Guidelines (reference)

General Odoo 18/19 coding standards, created from official Odoo documentation. Not project-specific — use these when writing new code in any module.

### Structure and Organization
| Document | Description |
|-----------|-------------|
| [Module Structure](01-module-structure.md) | Directory/file organization: `models/`, `views/`, `controllers/`, `security/`, `data/`, `static/` |
| [File Naming Conventions](02-file-naming-conventions.md) | Naming conventions for models, views, controllers, wizards, reports |

### Code and Standards
| Document | Description |
|-----------|-------------|
| [Python Coding Guidelines](03-python-coding-guidelines.md) | PEP 8, imports, idioms, builtins |
| [XML Guidelines](04-xml-guidelines.md) | Records, views, actions, menus, inheritance |
| [JavaScript Guidelines](05-javascript-guidelines.md) | OWL, widgets, templates, async/await |
| [CSS and SCSS Guidelines](06-css-scss-guidelines.md) | Syntax, naming, variables, mixins |

### Development Practices
| Document | Description |
|-----------|-------------|
| [Programming in Odoo](07-programming-in-odoo.md) | Framework-specific best practices: context, extensibility, transactions, exceptions |
| [Symbols and Conventions](08-symbols-conventions.md) | Variable/method/class naming, attribute ordering |
| [Database Best Practices](09-database-best-practices.md) | Normalization, naming, indexes, constraints, migrations |

### Frontend and Infrastructure
| Document | Description |
|-----------|-------------|
| [Frontend & Views](10-frontend-views-odoo18.md) | Views, templates, OWL, assets |
| [Email Sending Odoo 18](11-email-sending-odoo18.md) | `mail.template` vs `mail.mail`, `inline_template` engine, troubleshooting |
| [Deploy New Module](12-deploy-new-module.md) | Steps to deploy a new module into this project's environments |
| [SaaS Admin Module Checklist](13-saas-admin-module-checklist.md) | Checklist for SaaS-admin-facing modules |

### Quick Guides
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — Checklists, common patterns, shortcuts
- **[EXAMPLES.md](EXAMPLES.md)** — Full worked example module (Real Estate)

### Critical Rules

**Never:**
1. Call `cr.commit()` or `cr.rollback()` manually (the framework manages this)
2. Hardcode credentials or sensitive data
3. Catch a generic `Exception` without specifying a type
4. Add minified libraries to the codebase
5. Use `id` selectors in CSS
6. Modify stable code purely to apply style guidelines

**Always:**
1. Use `filtered`, `mapped`, `sorted` for iteration
2. Prefix community modules with `thedevkitchen_` (see ADR-004; `quicksol_estate` is a documented legacy exception)
3. Document code with docstrings
4. Organize imports (stdlib, odoo, addons)
5. Use savepoints when catching exceptions
6. Follow the project's ADRs (`docs/adr/`) when available

---

## Maintenance

- **Part 1 (Project Discovery)** should be refreshed whenever a module is added/removed, an ADR is accepted, infrastructure/compose files change, or a new integration is introduced. Re-run the knowledge-base generation process pointed at `18.0/` as `SOURCE_DIR`.
- **Part 2 (Odoo Guidelines)** should be refreshed when the team adopts new Odoo-version-specific conventions or after major framework upgrades.
- After any significant update to this knowledge base, consider running the **thedevkitchen-speckit-project-constitution** agent to keep the project constitution (`CLAUDE.md`/`.specify/`) aligned with these findings.
