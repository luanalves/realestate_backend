# Implementation Plan: Unificação de Perfis (Profile Unification)

**Branch**: `010-profile-unification` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-profile-unification/spec.md`

## Summary

Unificar os 9 perfis RBAC (ADR-019) em um modelo normalizado `thedevkitchen.estate.profile` com tabela lookup `thedevkitchen.profile.type` (3NF, KB-09). Abordagem técnica: 2 novos modelos no módulo `quicksol_estate`, endpoint unificado `POST /api/v1/profiles` com `company_id` no body, constraint composta `UNIQUE(document, company_id, profile_type_id)`, validação centralizada via `utils/validators.py`, extensão do `real.estate.agent` com FK `profile_id`, remoção direta do `real.estate.tenant` (ambiente dev), e integração com Feature 009 (invite flow two-step). Campos `birthdate` e `document` obrigatórios para todos os 9 tipos.

## Technical Context

**Language/Version**: Python 3.10+ (Odoo 18.0 framework)
**Primary Dependencies**: Odoo 18.0, `thedevkitchen_apigateway` v18.0.1.1.0 (auth middleware: `@require_jwt`, `@require_session`, `@require_company`), `quicksol_estate` v18.0.2.1.0 (RBAC groups, agent model, validators)
**Storage**: PostgreSQL 14+ (profile, profile_type, agent FK) + Redis 7+ (sessions, cache)
**Testing**: Python `unittest` + `unittest.mock` (unit), shell/curl (E2E API), Cypress (E2E UI) — per ADR-003 "Golden Rule"
**Target Platform**: Linux server (Docker: Odoo 18.0 + PostgreSQL 14 + Redis 7-alpine)
**Project Type**: Web (Odoo backend module — headless API architecture)
**Performance Goals**: < 200ms p95 for CRUD operations, compound unique constraint enforced at DB level
**Constraints**: Multi-tenant isolation (company-level), `company_id` from POST body (not header), `birthdate`+`document` required for ALL 9 profiles, audit fields `created_at`/`updated_at` (not `create_date`/`write_date`), validators from `utils/validators.py`
**Scale/Scope**: 9 profile types, 6 API endpoints (5 CRUD + 1 types listing), 2 new models, 1 model extension (agent), ~15 unit tests, ~25 E2E tests, ~3 Cypress specs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate (Constitution Principle) | Status | Evidence |
|---|-------------------------------|--------|----------|
| I | **Security First** — Dual auth on private endpoints, `# public endpoint` on public ones | ✅ PASS | Spec: all 6 endpoints use `@require_jwt` + `@require_session` + `@require_company`. No public endpoints in this feature. Authorization matrix from ADR-019 enforced per profile type. |
| II | **Test Coverage ≥ 80%** — Unit + Integration + E2E per feature | ✅ PASS | Spec: ~15 unit tests (constraints, validations, authorization matrix, sync logic) + ~25 E2E API shell tests (all CRUD flows, RBAC, multi-tenancy, pagination, HATEOAS). |
| III | **API-First** — RESTful with HATEOAS, OpenAPI, Postman | ✅ PASS | 6 REST endpoints with HATEOAS links. OpenAPI schema → `contracts/openapi.yaml`. Postman collection → `docs/postman/`. |
| IV | **Multi-Tenancy** — Company isolation via `@require_company` | ✅ PASS | Record rules on `thedevkitchen.estate.profile` with `company_id in user.estate_company_ids`. `company_id` from POST body validated against `user.estate_company_ids`. `GET` uses `company_ids` query param with same validation. |
| V | **ADR Governance** — Documented decisions | ✅ PASS | References ADR-004, 008, 009, 011, 015, 018, 019. New ADR-024 (Profile Unification). KB-09 (Database Best Practices). |
| VI | **Headless Architecture** — REST APIs for SSR frontend | ✅ PASS | All endpoints REST API. No Odoo web views except admin profile type management (Technical menu). |

**Gate Result**: ✅ ALL GATES PASS — Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-profile-unification/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # OpenAPI 3.0 spec for all 6 endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── models/
│   ├── __init__.py                    # ADD: import profile_type, profile
│   ├── profile_type.py                # NEW: thedevkitchen.profile.type (lookup)
│   ├── profile.py                     # NEW: thedevkitchen.estate.profile (unified)
│   ├── agent.py                       # MODIFY: add profile_id FK + sync logic
│   └── tenant.py                      # REMOVE: replaced by profile (portal type)
├── controllers/
│   ├── __init__.py                    # ADD: import profile_api
│   ├── profile_api.py                 # NEW: 6 endpoints (/api/v1/profiles, /api/v1/profile-types)
│   ├── tenant_api.py                  # REMOVE: replaced by profile_api.py
│   ├── agent_api.py                   # MODIFY: auto-create profile on agent creation
│   └── utils/
│       └── schema.py                  # ADD: PROFILE_CREATE_SCHEMA, PROFILE_UPDATE_SCHEMA
├── utils/
│   └── validators.py                  # MODIFY: add validate_document(), normalize_document(), is_cpf(), is_cnpj()
├── data/
│   └── profile_type_data.xml          # NEW: seed 9 profile types (noupdate="1")
├── security/
│   ├── ir.model.access.csv            # ADD: ACLs for profile_type, profile
│   └── record_rules.xml              # ADD: company isolation for profile
├── views/
│   └── profile_type_views.xml         # NEW: admin view for profile types (Technical menu)
├── tests/
│   └── unit/
│       ├── test_profile_validations_unit.py    # NEW: document, email, constraints
│       ├── test_profile_authorization_unit.py  # NEW: RBAC matrix per creator role
│       └── test_profile_sync_unit.py           # NEW: agent ↔ profile sync logic
└── i18n/
    └── pt_BR.po                       # UPDATE: profile-related translations

# E2E API tests (existing convention: integration_tests/)
integration_tests/
├── test_us10_s1_create_profile.sh         # US1: Create profile (all 9 types)
├── test_us10_s2_list_profiles.sh          # US2: List/filter profiles with company_ids
├── test_us10_s3_update_profile.sh         # US3: Update profile
├── test_us10_s4_deactivate_profile.sh     # US4: Soft delete
├── test_us10_s5_feature009_integration.sh # US5: Two-step flow (profile + invite)
├── test_us10_s6_rbac_matrix.sh            # RBAC: owner/manager/agent create permissions
├── test_us10_s7_multitenancy.sh           # Multi-tenancy: company isolation
├── test_us10_s8_compound_unique.sh        # Compound unique constraint validation
├── test_us10_s9_agent_profile_sync.sh     # Agent ↔ Profile sync on creation
└── test_us10_s10_pagination_hateoas.sh    # Pagination + HATEOAS links

# E2E UI tests (optional)
cypress/e2e/
└── profile-type-admin.cy.js              # Profile type admin view

# API documentation
docs/postman/
└── feature010_profile_unification_v1.0_postman_collection.json
```

### Modified Feature 009 Files

```text
18.0/extra-addons/thedevkitchen_user_onboarding/
├── controllers/
│   └── invite_controller.py           # MODIFY: accept profile_id in invite payload
└── services/
    └── invite_service.py              # MODIFY: link invite to existing profile
```

**Structure Decision**: Models and controllers added to existing `quicksol_estate` module following ADR-004. Profile models are estate domain, same as agent. `thedevkitchen.profile.type` prefixed per ADR-004 (`thedevkitchen_` prefix for custom models). Tests follow ADR-003 "Golden Rule" — unit for pure logic (mocks), E2E shell for API (real DB), Cypress for admin UI.

## Implementation Phases (from Spec Cleanup Plan)

### Phase 1: Schema Creation
1. Create `thedevkitchen.profile.type` model + seed data XML (9 records)
2. Create `thedevkitchen.estate.profile` model with compound unique constraint
3. Add `profile_id` FK to `real.estate.agent` (nullable initially)
4. Add `validate_document()`, `normalize_document()`, `is_cpf()`, `is_cnpj()` to `utils/validators.py`
5. Create security: ACLs (`ir.model.access.csv`) + record rules (company isolation)
6. Create `PROFILE_CREATE_SCHEMA` and `PROFILE_UPDATE_SCHEMA` in `controllers/utils/schema.py`

### Phase 2: Controller Creation
1. Create `profile_api.py` with 6 endpoints (CRUD + types listing)
2. Modify `agent_api.py` to auto-create profile on agent creation
3. Modify Feature 009 `invite_controller.py` to accept `profile_id`

### Phase 3: Cleanup (Direct Removal — Dev Environment)
1. Remove `real.estate.tenant` model and `tenant.py`
2. Remove `tenant_api.py` controller
3. Remove deprecated `company_ids` M2M from agent
4. Convert agent common fields to `related` fields pointing to profile
5. Update `real.estate.lease` FK: `tenant_id` → `profile_id`
6. Drop `real_estate_tenant` and `thedevkitchen_company_tenant_rel` tables

## Key Design Decisions (from Spec)

| # | Decision | Rationale |
|---|----------|-----------|
| D2 | Agent as business extension (not absorbed) | 611 LOC domain-specific code (CRECI, commissions, assignments) |
| D3 | Tenant fully absorbed | 35 LOC, all fields fit unified profile |
| D4 | Single endpoint `POST /api/v1/profiles` | Eliminates endpoint sprawl; `profile_type` determines behavior |
| D5.1 | `company_id` in POST body | Multi-company users need explicit company selection |
| D5.2 | `company_ids` query param on GET | Same pattern as `property_api.py` — validates against `user.estate_company_ids` |
| D6 | Lookup table for profile types | KB-09 §2.1: enums > 5 values → lookup table |
| D9 | `birthdate` + `document` required all 9 types | No profile-type differentiation for required fields |
| D10 | `created_at`/`updated_at` (not `write_date`) | Project convention for explicit audit fields |
| D11 | Reuse `utils/validators.py` | Constitution mandates centralized validation |
| D12 | No migration (dev environment) | Direct removal of legacy tables, data recreated |

## Complexity Tracking

> No constitution violations detected — this section is empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
