# Implementation Plan: Company & Owner Management System

**Branch**: `007-company-owner-management` | **Date**: 2026-02-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-company-owner-management/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement complete CRUD management system for Real Estate Companies (Imobiliárias) and Owners via REST API and Odoo Web interface. Owners can create companies and manage other Owners within their companies. SaaS Admin has full control via Odoo Web. Enforces multi-tenancy isolation (ADR-008) and RBAC rules (ADR-019) using triple decorator pattern (`@require_jwt`, `@require_session`, `@require_company`).

## Technical Context

**Language/Version**: Python 3.10+ (Odoo 18.0)  
**Primary Dependencies**: Odoo 18.0 ORM, thedevkitchen_apigateway (OAuth2/JWT), quicksol_estate (existing module)  
**Storage**: PostgreSQL 14+ with existing tables (thedevkitchen_estate_company, res_users)  
**Testing**: pytest + Odoo test framework (Unit), curl/shell (Integration), Cypress (E2E)  
**Target Platform**: Docker Linux server (Odoo 18.0 container)
**Project Type**: Web (Odoo backend + headless SSR frontend)  
**Performance Goals**: Standard Odoo response times (<500ms for CRUD operations)  
**Constraints**: Must use existing Company model, Owner is a role (not separate model), soft delete pattern (ADR-015)  
**Scale/Scope**: Multi-tenant SaaS, ~100 companies initially, ~10 Owners per company

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Security First | ✅ PASS | All endpoints use `@require_jwt` + `@require_session` + `@require_company` decorators |
| II. Test Coverage | ✅ PLANNED | Unit tests (validations), Integration tests (API endpoints), E2E tests (Cypress for Odoo Web) |
| III. API-First Design | ✅ PASS | REST endpoints with HATEOAS links, JSON responses, OpenAPI documentation |
| IV. Multi-Tenancy | ✅ PASS | `estate_company_ids` filtering, record rules, 404 for inaccessible resources |
| V. ADR Governance | ✅ PASS | Follows ADR-004, ADR-007, ADR-008, ADR-011, ADR-015, ADR-018, ADR-019 |
| VI. Headless Architecture | ✅ PASS | REST APIs for SSR frontend, Odoo Web for SaaS Admin |

**Gate Result**: ✅ ALL PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/007-company-owner-management/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - Technical details (COMPLETE)
├── data-model.md        # Phase 1 output - Entity definitions
├── quickstart.md        # Phase 1 output - Developer onboarding
├── contracts/           # Phase 1 output - OpenAPI specs
│   └── company-owner-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── controllers/
│   ├── __init__.py           # MODIFY - import new controllers
│   ├── company_api.py        # CREATE - Company CRUD endpoints
│   └── owner_api.py          # CREATE - Owner CRUD endpoints (nested)
├── models/
│   ├── company.py            # EXISTS - extend if needed
│   └── res_users.py          # MODIFY - add owner_company_ids computed field
├── views/
│   ├── company_views.xml     # CREATE - Form, List, Search views
│   └── real_estate_menus.xml # MODIFY - fix action_company reference
├── security/
│   └── record_rules.xml      # MODIFY - add Owner management rule
├── tests/
│   ├── api/
│   │   ├── test_company_api.py  # CREATE - Company integration tests
│   │   └── test_owner_api.py    # CREATE - Owner integration tests
│   └── unit/
│       ├── test_company_validations.py  # CREATE - CNPJ, email validation
│       └── test_owner_validations.py    # CREATE - last-owner protection
└── __manifest__.py           # MODIFY - add new views to data list

integration_tests/
├── test_us7_s1_owner_creates_company.sh   # CREATE
├── test_us7_s2_owner_creates_owner.sh     # CREATE
├── test_us7_s3_company_rbac.sh            # CREATE
└── test_us7_s4_company_multitenancy.sh    # CREATE

cypress/e2e/
├── admin-company-management.cy.js  # CREATE
└── admin-owner-management.cy.js    # CREATE
```

**Structure Decision**: Extends existing `quicksol_estate` module following Odoo conventions (ADR-001, ADR-004). New controllers follow existing pattern in `controllers/` directory. Tests follow existing structure in `tests/api/` and `tests/unit/`.

## Complexity Tracking

> No Constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

---

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Security First | ✅ PASS | OpenAPI spec defines bearerAuth for all endpoints; decorators in plan |
| II. Test Coverage | ✅ PLANNED | Test files defined in Project Structure; pyramid coverage (unit → E2E) |
| III. API-First Design | ✅ PASS | OpenAPI 3.0 spec created at `contracts/company-owner-api.yaml` |
| IV. Multi-Tenancy | ✅ PASS | Data model includes record rules; 404 for inaccessible resources |
| V. ADR Governance | ✅ PASS | All ADRs referenced in research.md; constraints documented |
| VI. Headless Architecture | ✅ PASS | REST API for SSR frontend; Odoo Web views for SaaS Admin |

**Post-Design Gate Result**: ✅ ALL PASS - Ready for `/speckit.tasks`

---

## Phase 0 & 1 Artifacts Summary

| Phase | Artifact | Status | Location |
|-------|----------|--------|----------|
| 0 | research.md | ✅ Complete | [research.md](research.md) |
| 1 | data-model.md | ✅ Complete | [data-model.md](data-model.md) |
| 1 | contracts/ | ✅ Complete | [contracts/company-owner-api.yaml](contracts/company-owner-api.yaml) |
| 1 | quickstart.md | ✅ Complete | [quickstart.md](quickstart.md) |
| 1 | Agent context | ✅ Updated | `.github/agents/copilot-instructions.md` |

---

## Next Step

Run `/speckit.tasks` to generate task breakdown for implementation.
