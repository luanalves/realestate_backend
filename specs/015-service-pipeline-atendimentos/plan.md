# Implementation Plan: Service Pipeline Management (Atendimentos)

**Branch**: `015-service-pipeline-atendimentos` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/015-service-pipeline-atendimentos/spec.md`
**Source-of-truth (technical detail)**: [spec-idea.md](./spec-idea.md)

## Summary

Introduce a new domain entity `real.estate.service` (Atendimento) — a kanban-style pipeline tracking each engagement between an agent and a client over a specific operation (Sale or Rent), distinct from existing Lead/Proposal entities. The pipeline has 7 stages with stage gates, audit via `mail.thread`, system-tag locking, conditional uniqueness via PostgreSQL `EXCLUDE` constraint, and 9 REST endpoints (including a `/summary` aggregation endpoint for kanban counters). Auxiliary entities: `service.tag`, `service.source`, `partner.phone`, singleton `service.settings`. Multi-tenant by `company_id`, RBAC matrix across 5 profiles, soft delete (ADR-015), HATEOAS responses (ADR-007), triple decorator security (ADR-011). Implementation lives in existing addon `quicksol_estate`.

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0)
**Primary Dependencies**: Odoo 18.0 (`mail.thread`, `mail.activity.mixin`, `res.partner`, `res.users`, `res.company`), `quicksol_estate` (existing — provides `real.estate.lead`, `real.estate.property`, `real.estate.proposal`, `real.estate.agent`), `thedevkitchen_apigateway` (OAuth2/JWT/session), `thedevkitchen_user_onboarding` (RBAC profile groups)
**Storage**: PostgreSQL ≥14 (required for partial `EXCLUDE` constraint with `WHERE`); Redis 7 DB index 1 (optional cache for `/summary`, deferred per research R4)
**Testing**: Odoo `TransactionCase` (unit), shell scripts (`integration_tests/test_us15_*.sh`) for E2E HTTP, Cypress for Odoo admin UI
**Target Platform**: Docker Compose (existing 18.0 stack — Odoo + PostgreSQL + Redis + RabbitMQ + Celery)
**Project Type**: single (Odoo monolith) — addon module under `18.0/extra-addons/quicksol_estate/`
**Performance Goals**: GET list < 300ms (p95) at 10k records; GET `/summary` < 100ms (p95); POST/PATCH < 500ms (p95); pipeline movement confirmed < 1s end-to-end
**Constraints**: Multi-tenant strict isolation (zero cross-company leakage); audit retention indefinite (soft delete only); 80%+ test coverage (ADR-003)
**Scale/Scope**: Up to 10k active services per company; up to ~50 concurrent users per agency

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.6.0 (ratified 2026-01-03, last amended 2026-05-03 with patterns ratified for this feature) reviewed against this plan:

| Principle / Pattern | Status | Notes |
|---|---|---|
| **I. Security First (NON-NEGOTIABLE)** | ✅ Pass | All 9 authenticated endpoints use triple decorator (`@require_jwt + @require_session + @require_company`); no public endpoints required |
| **II. Test Coverage Mandatory (≥80%)** | ✅ Pass | Plan includes unit (TransactionCase) + integration (shell) + Cypress; all FRs and stage gates testable |
| **III. API-First Design** | ✅ Pass | OpenAPI 3.0 contracts in `contracts/openapi.yaml`; Postman collection deferred to post-impl per ADR-016 standard practice; HATEOAS in all responses (ADR-007) |
| **IV. Multi-Tenancy by Design** | ✅ Pass | `company_id` on every entity; record rules per profile; isolation tests required |
| **V. ADR Governance** | ✅ Pass | References ADR-001/003/004/005/007/008/009/011/015/016/017/018/019/022 |
| **VI. Headless Architecture** | ✅ Pass | API serves all 5 operational profiles; Odoo UI restricted to admin |
| **Pipeline State Machine Pattern** (v1.6.0) | ✅ Pass | Stages as Selection; @api.constrains stage gates; mail.thread audit; terminal states |
| **Aggregation Endpoint Pattern** (v1.6.0) | ✅ Pass | `GET /api/v1/services/summary` with single GROUP BY via Odoo `read_group()` |
| **Conditional Uniqueness via EXCLUDE** (v1.6.0) | ✅ Pass | PostgreSQL EXCLUDE constraint via migration script (research R1) |
| **System Tag Pattern** (v1.6.0) | ✅ Pass | `is_system` flag on `real.estate.service.tag`; `closed` tag immutable, locks pipeline |
| **Singleton Configuration Model** | ✅ Pass | `thedevkitchen.service.settings` per company with `get_settings()` class method, validation constraints |
| **Async Processing (ADR-021)** | N/A | No async use case in this feature; reassign notifications via mail.thread (sync) |

**Result**: ✅ All gates pass. No violations to justify in Complexity Tracking.

**Post-Phase-1 re-check**: After designing data-model.md and contracts/openapi.yaml, no new violations or unjustified complexity surfaced. Confirmed pass.

## Project Structure

### Documentation (this feature)

```text
specs/015-service-pipeline-atendimentos/
├── spec-idea.md         # Original technical-rich draft (source-of-truth for tech detail)
├── spec.md              # Business specification (Phase 0 input — done)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output — 7 research decisions resolved
├── data-model.md        # Phase 1 output — 5 entities + 1 additive field on proposal
├── quickstart.md        # Phase 1 output — end-to-end usage walkthrough
├── contracts/
│   └── openapi.yaml     # Phase 1 output — OpenAPI 3.0 contract for the 9 endpoints
├── checklists/
│   └── requirements.md  # Spec quality checklist (done)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── models/
│   ├── service.py                         # NEW — real.estate.service
│   ├── service_tag.py                     # NEW — real.estate.service.tag
│   ├── service_source.py                  # NEW — real.estate.service.source
│   ├── partner_phone.py                   # NEW — real.estate.partner.phone
│   ├── service_settings.py                # NEW — thedevkitchen.service.settings (singleton per company)
│   ├── proposal.py                        # MODIFIED — add additive field service_id (Many2one)
│   └── __init__.py                        # MODIFIED — register new models
├── controllers/
│   ├── service_controller.py              # NEW — 9 endpoints under /api/v1/services + summary + reassign + stage
│   ├── service_tag_controller.py          # NEW — CRUD /api/v1/service-tags
│   ├── service_source_controller.py       # NEW — CRUD /api/v1/service-sources
│   └── __init__.py                        # MODIFIED
├── services/
│   ├── service_pipeline_service.py        # NEW — business logic for stage transitions, gates, reassign
│   └── partner_dedup_service.py           # NEW — partner deduplication by phone OR email
├── security/
│   ├── ir.model.access.csv                # MODIFIED — add new models access rights per profile
│   └── service_record_rules.xml           # NEW — record rules per profile
├── data/
│   ├── service_sources_data.xml           # NEW — default sources via post-init hook
│   ├── service_tags_data.xml              # NEW — system tag (closed) via post-init hook
│   ├── service_settings_data.xml          # NEW — default settings per company via post-init hook
│   ├── service_sequence_data.xml          # NEW — sequence ATD/YYYY/NNNNN
│   ├── service_cron_data.xml              # NEW — daily pendency recompute cron
│   └── seed_services_data.xml             # NEW — seed data (5 profiles × 2 companies × all stages)
├── migrations/
│   └── 18.0.x.x.x/
│       └── pre-migrate.py                 # NEW — create EXCLUDE constraint
├── views/
│   ├── service_views.xml                  # NEW — list/form/kanban (Odoo 18.0 — KB-10)
│   ├── service_tag_views.xml              # NEW
│   ├── service_source_views.xml           # NEW
│   ├── service_settings_views.xml         # NEW — singleton form
│   └── service_menu.xml                   # NEW — menus without `groups` (admin-only per KB-10)
├── wizards/
│   └── service_reassign_wizard.py         # NEW — Manager reassignment wizard (admin UI)
├── hooks/
│   └── post_init.py                       # NEW — per-company defaults (research R6)
└── tests/
    ├── unit/
    │   ├── test_service_pipeline.py       # NEW — stage gates, transitions, audit
    │   ├── test_service_uniqueness.py     # NEW — EXCLUDE constraint
    │   ├── test_service_tag_system.py     # NEW — is_system flag immutability + lock behavior
    │   ├── test_service_settings.py       # NEW — singleton + validators
    │   ├── test_service_pendency.py       # NEW — last_activity_date + is_pending
    │   ├── test_orphan_agent.py           # NEW — FR-024a behavior
    │   └── test_partner_dedup.py          # NEW
    └── api/
        ├── test_service_endpoints.py      # NEW — HTTP layer + HATEOAS
        ├── test_service_summary.py        # NEW — aggregation endpoint
        ├── test_service_rbac.py           # NEW — 5 profiles authorization matrix
        └── test_service_isolation.py      # NEW — multi-tenancy

integration_tests/
├── test_us15_s1_agent_creates_service_lifecycle.sh    # NEW
├── test_us15_s2_manager_reassigns_service.sh           # NEW
├── test_us15_s3_filters_and_summary.sh                 # NEW
├── test_us15_s4_tags_and_sources_crud.sh               # NEW
├── test_us15_s5_multitenancy_isolation.sh              # NEW
├── test_us15_s6_rbac_matrix.sh                         # NEW
└── test_us15_s7_partner_dedup_multiphone.sh            # NEW

cypress/e2e/
└── 015_services_admin.cy.js               # NEW — admin opens services list/form, no console errors

docs/
├── adr/
│   └── ADR-028-service-pipeline-domain-boundaries.md   # NEW (recommended)
├── api/                                                # OpenAPI Swagger sync via DB upgrade post-impl
└── postman/
    └── feature015_services_v1.0_postman_collection.json  # NEW (post-impl per ADR-016)
```

**Structure Decision**: **Single project — Odoo monolith**. Feature added to existing addon `quicksol_estate` (where `real.estate.lead`, `real.estate.property`, `real.estate.proposal`, `real.estate.agent` already live). This preserves cohesion of the real-estate domain, avoids new module overhead, and maximizes reuse of existing security groups/record rules. The configuration singleton lives under the `thedevkitchen.*` namespace (consistent with `thedevkitchen.email.link.settings` from Feature 009).

## Complexity Tracking

> No constitutional violations. This section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | — | — |

---

## Phase Output References

- **Phase 0** → [research.md](./research.md) — 7 technical decisions resolved (R1–R7): EXCLUDE constraint approach, last_activity_date compute strategy, formalization stage gate cross-model coupling, /summary cache deferral, Cypress scope, per-company defaults via post-init hook, lead_id linkage semantics
- **Phase 1** → [data-model.md](./data-model.md) (5 new entities + 1 additive field on proposal + record rules + indexes), [contracts/openapi.yaml](./contracts/openapi.yaml) (9 endpoints, OpenAPI 3.0), [quickstart.md](./quickstart.md) (e2e walkthrough)
- **Phase 2** → `tasks.md` (generated by `/speckit.tasks`, NOT here)
