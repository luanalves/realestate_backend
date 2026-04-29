# Implementation Plan: Rental Credit Check

**Branch**: `014-rental-credit-check` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/014-rental-credit-check/spec.md`

## Summary

Implement **Análise de Ficha** (rental credit check): a credit analysis gate that an Owner, Manager, or Agent initiates after a proposal is `sent` or in `negotiation`, transitioning the proposal through a `credit_check_pending` state before reaching `accepted` or `rejected`. The feature introduces a new Odoo module (`thedevkitchen_estate_credit_check`) that creates the `thedevkitchen.estate.credit.check` entity, extends the `thedevkitchen.estate.proposal` FSM, exposes 4 REST endpoints, and reuses the existing ADR-021 Outbox/EventBus pattern for async notifications.

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0)  
**Primary Dependencies**: Odoo ORM, `mail.thread`, `mail.activity.mixin`, `thedevkitchen_apigateway` (JWT/session auth), `quicksol_estate` (proposal/property models), `thedevkitchen_user_onboarding` (RBAC groups)  
**Storage**: PostgreSQL 15 (primary persistence) + Redis DB1 (sessions, HTTP cache — existing infrastructure)  
**Testing**: `OdooTestCase` / `TransactionCase` for unit tests; shell integration tests (`integration_tests/`); Cypress E2E for Owner/Manager UI flows  
**Target Platform**: Linux server (Docker), Odoo 18.0, multi-tenant SaaS  
**Project Type**: Single Odoo addon module  
**Performance Goals**: `GET /clients/{id}/credit-history` < 300 ms for up to 1,000 checks per company (SC-004); queue promotion after rejection < 5 s (SC-008)  
**Constraints**: Multi-tenant by `company_id`; LGPD compliance (no PII in logs); ADR-001 (no `attrs`, `<list>` not `<tree>`); ADR-011 (triple decorator on all authenticated endpoints); ADR-015 (soft delete via `active` field); ADR-027 (partial unique index guard for pending invariant)  
**Scale/Scope**: Up to 1,000 `CreditCheck` records per company; 9 RBAC profiles; 4 REST endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Status | Notes |
|-----------|-------|--------|-------|
| I — Security First | All 4 endpoints use `@require_jwt` + `@require_session` + `@require_company`. No public endpoints. | ✅ PASS | Agent scope for credit-history enforced: 404 anti-enumeration (ADR-008) |
| II — Test Coverage | Unit tests (`OdooTestCase`), integration tests (shell), Cypress E2E for UI | ✅ PASS | Tests cover all state transitions, authorization matrix, edge cases |
| III — API-First | 4 REST endpoints, OpenAPI 3.0 YAML in `contracts/`, Postman collection (ADR-016) | ✅ PASS | Swagger via `thedevkitchen_api_endpoint` table (ADR-005) |
| IV — Multi-Tenancy | `company_id` on `CreditCheck`, record rule `rule_credit_check_company`, denormalized from proposal | ✅ PASS | Invariant: no cross-company check access |
| V — ADR Governance | ADR-004 (naming), ADR-007 (HATEOAS `_links`), ADR-011 (auth), ADR-015 (soft delete), ADR-018 (input validation), ADR-019 (RBAC), ADR-022 (linting), ADR-027 (pessimistic locking) | ✅ PASS | No violations. Extends spec 013 cron per ADR-021 |
| VI — Headless | Agents: API only (REST). Owner/Manager/Admin: Odoo Web UI + API. No agent-facing Odoo views | ✅ PASS | Confirmed in clarification Q5 (2026-04-29) |

**Post-Phase-1 re-check**: All principles still PASS after data-model.md and contracts/ design.

## Project Structure

### Documentation (this feature)

```text
specs/014-rental-credit-check/
├── plan.md              # This file
├── research.md          # Phase 0 — all unknowns resolved ✅
├── data-model.md        # Phase 1 — entity design, constraints, access matrix ✅
├── quickstart.md        # Phase 1 — dev setup and first-run guide ✅
├── contracts/
│   └── openapi.yaml     # Phase 1 — OpenAPI 3.0 for all 4 endpoints ✅
└── tasks.md             # Phase 2 output (speckit.tasks — NOT yet created)
```

### Source Code (repository root)

```text
18.0/extra-addons/thedevkitchen_estate_credit_check/
├── __init__.py
├── __manifest__.py                    # depends: mail, thedevkitchen_apigateway, quicksol_estate
├── models/
│   ├── __init__.py
│   ├── credit_check.py                # thedevkitchen.estate.credit.check (new entity)
│   └── proposal_extension.py         # _inherit thedevkitchen.estate.proposal
├── controllers/
│   ├── __init__.py
│   └── credit_check_controller.py    # 4 REST endpoints (triple decorator)
├── services/
│   ├── __init__.py
│   └── credit_check_service.py       # FSM transitions, queue promotion, event emission
├── views/
│   ├── credit_check_views.xml        # <list> + <form> for Owner/Manager (ADR-001)
│   └── menu.xml                      # Sub-menu under Proposals
├── security/
│   ├── ir.model.access.csv           # CRUD grants per RBAC group
│   └── record_rules.xml              # company isolation rule
├── data/
│   ├── api_endpoints_data.xml        # Swagger DB records (ADR-005)
│   └── mail_templates.xml            # credit_check.approved + credit_check.rejected templates
└── tests/
    ├── __init__.py
    ├── test_credit_check_model.py     # Unit: constraints, FSM guards, computed fields
    ├── test_credit_check_service.py   # Unit: transitions, queue promotion, event emission
    └── test_credit_check_controller.py # Integration: all 4 endpoints, auth, edge cases
```

**Structure Decision**: Single Odoo addon following the established pattern from `thedevkitchen_user_onboarding`. Separation of concerns: models (data layer), services (business logic), controllers (HTTP layer). No frontend code — agents use the REST API; Owner/Manager use Odoo Web UI via the views.

## Complexity Tracking

> No constitution violations. No complexity justification required.
