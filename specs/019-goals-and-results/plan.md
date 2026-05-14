# Implementation Plan: Goals and Results (Metas e Resultados)

**Branch**: `019-goals-and-results` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-goals-and-results/spec.md`

---

## Summary

Create a new Odoo module `thedevkitchen_estate_goals` that enables Owners, Directors, and Managers to define monthly performance goals per user across 5 real estate funnel metrics (captações, novos clientes, visitas, propostas, fechamento). Achievement data is computed automatically at query time by joining existing domain entities (`real.estate.property`, `real.estate.service`, `real.estate.proposal`) and using `mail.tracking.value` to detect stage transitions. Five REST endpoints (`POST`, `PUT`, `DELETE`, `GET` list, `GET` report) expose goal management and reporting to the headless frontend, all guarded by triple auth decorators (`@require_jwt + @require_session + @require_company`). An Odoo admin UI (list + form views) serves the system `admin` user.

**New module only** — no changes to existing modules in this feature.

## Technical Context

**Language/Version**: Python 3.11 / Odoo 18.0  
**Primary Dependencies**: Odoo ORM (`mail.tracking.value` for stage history, `mail.thread` mixin), `thedevkitchen_apigateway` (triple auth), `quicksol_estate` (domain models)  
**Storage**: PostgreSQL 14+ — new table `thedevkitchen_estate_goal`; no new files, no Redis required in v1  
**Testing**: Odoo `TransactionCase` (unit/integration); E2E bash scripts (`integration_tests/`); Cypress (`18.0/cypress/e2e/`)  
**Target Platform**: Linux Docker container — `odoo/odoo:18.0`  
**Project Type**: Single Odoo module (`thedevkitchen_estate_goals`)  
**Performance Goals**: Single-month report (≤50 users) < 500ms; 12-month accumulated < 2s; report hard cap = 200 users (422 if exceeded)  
**Constraints**: No new Python packages; `mail.tracking.value` queries must be date-range scoped; composite DB indexes mandatory; no pagination on report endpoint (v1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | **Module naming** — `thedevkitchen_` prefix (ADR-004) | ✅ PASS | Module: `thedevkitchen_estate_goals`; model: `thedevkitchen.estate.goal`; table: `thedevkitchen_estate_goal` |
| 2 | **API security** — triple auth decorators on all private endpoints (ADR-011) | ✅ PASS | All 5 endpoints use `@require_jwt` + `@require_session` + `@require_company`; no public endpoints in this feature |
| 3 | **Soft delete** — `active = Boolean(default=True)` with `_sql_constraints` (ADR-015) | ✅ PASS | `active` field present on `thedevkitchen.estate.goal`; deletion endpoint sets `active=False` |
| 4 | **API documentation** — Swagger via `thedevkitchen_api_endpoint` DB records (ADR-005) | ✅ PASS | `data/api_endpoints_data.xml` seeds all 5 endpoints; never edit static files |
| 5 | **RBAC / multitenancy** — `company_id` on model + record rules (ADR-011) | ✅ PASS | `company_id` on every goal; record rule restricts reads to `env.company` |
| 6 | **Performance** — no N+1 queries; SQL for report aggregation; indexes on FK columns | ✅ PASS | Report uses raw SQL via `env.cr.execute`; composite index `(user_id, company_id, year, month)` |

**Gate result**: ✅ All principles satisfied — no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/019-goals-and-results/
├── spec.md              # speckit.specify output (polished, with clarifications)
├── spec-idea.md         # Original idea file — IMMUTABLE
├── plan.md              # This file — speckit.plan output
├── research.md          # Phase 0 — model field findings + query patterns
├── data-model.md        # Phase 1 — ERD + field table + constraints
├── quickstart.md        # Phase 1 — dev onboarding + curl examples
├── contracts/           # Phase 1 — OpenAPI 3.0 YAML per endpoint
│   ├── create-goal.yaml
│   ├── update-goal.yaml
│   ├── delete-goal.yaml
│   ├── list-goals.yaml
│   └── goals-report.yaml
└── tasks.md             # Phase 2 — speckit.tasks output (not yet created)
```

### Source Code (new module)

```text
18.0/extra-addons/thedevkitchen_estate_goals/
├── __init__.py
├── __manifest__.py                          # depends: quicksol_estate, thedevkitchen_apigateway
├── controllers/
│   ├── __init__.py
│   └── goals_controller.py                  # All 5 endpoints
├── models/
│   ├── __init__.py
│   └── estate_goal.py                       # thedevkitchen.estate.goal model
├── services/
│   ├── __init__.py
│   └── goals_report_service.py              # Achievement computation (SQL)
├── security/
│   ├── ir.model.access.csv                  # ACL for thedevkitchen.estate.goal
│   └── record_rules.xml                     # Multitenancy: restrict by company_id
├── data/
│   └── api_endpoints_data.xml               # Swagger endpoint records
├── views/
│   └── estate_goal_views.xml                # Admin list + form views
└── tests/
    ├── __init__.py
    └── unit/
        ├── __init__.py
        └── test_estate_goal.py              # Constraint, CRUD, report logic tests
```

### Integration & E2E Tests

```text
integration_tests/
├── test_us019_s1_create_goals.sh
├── test_us019_s2_goal_lifecycle.sh
├── test_us019_s3_report_single_month.sh
├── test_us019_s4_report_date_range.sh
├── test_us019_s5_rbac_matrix.sh
└── test_us019_s6_multitenancy.sh
```

**Structure Decision**: Standard single-module Odoo layout — mirrors `thedevkitchen_user_onboarding` and `thedevkitchen_estate_profiles` structures. `services/` layer isolates SQL logic from controller. No additional projects needed.

## Complexity Tracking

> No constitution violations — this section records justified deviations only.

*None required for this feature.*
