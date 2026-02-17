# Implementation Plan: User Onboarding & Password Management

**Branch**: `009-user-onboarding-password-management` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-user-onboarding-password-management/spec.md`

## Summary

Implementar fluxo completo de onboarding (convite por email + criação de senha) e recuperação de senha para todos os 9 perfis RBAC (ADR-019) do sistema imobiliário. Abordagem técnica: novo módulo `thedevkitchen_user_onboarding` com modelo de tokens (SHA-256), serviço de geração/validação, 5 endpoints REST (invite, set-password, forgot-password, reset-password, resend-invite), templates de email via `mail.template`, e configuração dinâmica de TTL via Singleton (menu Technical). Suporte a dual record creation para perfil portal (`res.users` + `real.estate.tenant`).

## Technical Context

**Language/Version**: Python 3.10+ (Odoo 18.0 framework)
**Primary Dependencies**: Odoo 18.0, `thedevkitchen_apigateway` v18.0.1.1.0 (auth middleware), `quicksol_estate` v18.0.2.1.0 (RBAC groups, models), `validate_docbr` (CPF validation), `email_validator`
**Storage**: PostgreSQL 14+ (tokens, settings, users) + Redis 7+ (sessions, cache)
**Testing**: Python `unittest` + `unittest.mock` (unit), shell/curl (E2E API), Cypress (E2E UI) — per ADR-003 "Golden Rule"
**Target Platform**: Linux server (Docker: Odoo 18.0 + PostgreSQL 14 + Redis 7-alpine)
**Project Type**: Web (Odoo backend module — headless API architecture)
**Performance Goals**: < 200ms response time for token operations, async email sending via `mail.template.send_mail()`
**Constraints**: < 200ms p95 API responses, multi-tenant isolation (company-level), LGPD compliance, SHA-256 token hashing (no plain-text)
**Scale/Scope**: 9 RBAC profiles, 5 API endpoints, 2 new models, 1 model extension, 2 email templates, ~15 unit tests, ~20 E2E tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate (Constitution Principle) | Status | Evidence |
|---|-------------------------------|--------|----------|
| I | **Security First** — Dual auth on private endpoints, `# public endpoint` on public ones | ✅ PASS | Spec: `@require_jwt` + `@require_session` + `@require_company` on invite/resend-invite. Public endpoints (set-password, forgot-password, reset-password) marked `# public endpoint`. SHA-256 token hashing. Anti-enumeration on forgot-password. Rate limiting. |
| II | **Test Coverage ≥ 80%** — Unit + Integration + E2E per feature | ✅ PASS | Spec: ~15 unit tests (validations, token lifecycle, authorization matrix) + ~20 E2E API shell tests (all flows) + Cypress for settings view. |
| III | **API-First** — RESTful with HATEOAS, OpenAPI, Postman | ✅ PASS | 5 REST endpoints with HATEOAS links in responses. OpenAPI schema → `contracts/openapi.yaml`. Postman collection → `docs/postman/feature009_*`. |
| IV | **Multi-Tenancy** — Company isolation via `@require_company` | ✅ PASS | Record rules on `thedevkitchen.password.token` with `company_id`. Invite/resend endpoints use `@require_company`. Isolation E2E tests specified. |
| V | **ADR Governance** — Documented decisions | ✅ PASS | References ADR-003, 004, 007, 008, 009, 011, 015, 017, 018, 019, 022. Potential new ADR-023 (Rate Limiting). |
| VI | **Headless Architecture** — REST APIs for SSR frontend | ✅ PASS | All endpoints REST API. Frontend URL configurable via `frontend_base_url` setting. Settings form is only Odoo web view. |

**Gate Result**: ✅ ALL GATES PASS — Proceed to Phase 0.

### Post-Design Re-evaluation (after Phase 1)

| # | Gate | Post-Design Status | Notes |
|---|------|--------------------|-------|
| I | Security First | ✅ PASS | `data-model.md`: tokens use SHA-256 hash, record rules enforce company isolation. `openapi.yaml`: public endpoints documented. Controllers split by auth pattern. |
| II | Test Coverage ≥ 80% | ✅ PASS | `quickstart.md`: 3 unit test files + 6 E2E shell scripts + 1 Cypress spec. Covers token lifecycle, password validation, authorization matrix, all API flows, multi-tenancy. |
| III | API-First | ✅ PASS | `contracts/openapi.yaml`: Full OpenAPI 3.0 spec with all 5 endpoints, schemas, examples, HATEOAS links. Postman collection path defined. |
| IV | Multi-Tenancy | ✅ PASS | `data-model.md`: `company_id` FK on `thedevkitchen.password.token`. Record rule with `estate_company_ids` filter. E2E test `test_us9_s5_multitenancy.sh` planned. |
| V | ADR Governance | ✅ PASS | `research.md`: All decisions documented with rationale + alternatives. ADR-004 naming followed (`thedevkitchen_` prefix). Potential ADR-023 noted. |
| VI | Headless Architecture | ✅ PASS | All endpoints REST. `frontend_base_url` configurable. Only Odoo view is settings form (Technical menu). |

**Post-Design Gate Result**: ✅ ALL GATES PASS

## Project Structure

### Documentation (this feature)

```text
specs/009-user-onboarding-password-management/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # OpenAPI 3.0 spec for all 5 endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
18.0/extra-addons/thedevkitchen_user_onboarding/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── invite_controller.py       # POST /api/v1/users/invite + POST /api/v1/users/{id}/resend-invite
│   └── password_controller.py     # POST /api/v1/auth/set-password, forgot-password, reset-password
├── models/
│   ├── __init__.py
│   ├── password_token.py          # thedevkitchen.password.token
│   ├── email_link_settings.py     # thedevkitchen.email.link.settings (Singleton)
│   └── res_users.py               # Extension: signup_pending field
├── services/
│   ├── __init__.py
│   ├── token_service.py           # Token generation (UUID v4), SHA-256 hashing, validation, invalidation
│   ├── invite_service.py          # User creation, profile-group mapping, dual record (portal), email dispatch
│   └── password_service.py        # Password set/reset logic, session invalidation after reset
├── data/
│   ├── email_templates.xml        # mail.template: invite + reset password
│   └── default_settings.xml       # Default singleton record (24h TTL)
├── security/
│   ├── ir.model.access.csv        # ACLs for password_token and email_link_settings
│   └── record_rules.xml           # Company isolation for password_token
├── views/
│   ├── email_link_settings_views.xml  # Form view for settings
│   └── menu.xml                       # Technical > Configuration > Email Link Settings
├── tests/
│   ├── __init__.py
│   └── unit/
│       ├── __init__.py
│       ├── test_token_service.py        # Token generation, hashing, expiration, invalidation
│       ├── test_password_validation.py  # Password strength, confirmation match
│       └── test_invite_authorization.py # Authorization matrix per profile
└── i18n/
    └── pt_BR.po

# E2E API tests (existing convention: integration_tests/)
integration_tests/
├── test_us9_s1_invite_flow.sh
├── test_us9_s2_forgot_password.sh
├── test_us9_s3_portal_dual_record.sh
├── test_us9_s4_authorization_matrix.sh
├── test_us9_s5_multitenancy.sh
└── test_us9_s6_resend_invite.sh

# E2E UI tests (existing convention: cypress/e2e/)
cypress/e2e/
└── email-link-settings.cy.js

# API documentation
docs/postman/
└── feature009_user_onboarding_v1.0_postman_collection.json
```

**Structure Decision**: New Odoo module `thedevkitchen_user_onboarding` following ADR-004 naming (`thedevkitchen_` prefix). Separate module to maintain single-responsibility — depends on `thedevkitchen_apigateway` (auth middleware) and `quicksol_estate` (RBAC groups, tenant model). Services layer follows existing pattern in both modules. Tests follow ADR-003 "Golden Rule" — unit for pure logic (mocks), E2E shell for API (real DB), Cypress for UI.

## Complexity Tracking

> No constitution violations detected — this section is empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
