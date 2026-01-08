# Implementation Plan: Company Isolation Phase 1

**Branch**: `001-company-isolation` | **Date**: January 8, 2026 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-company-isolation/spec.md`

## Summary

Complete the multi-tenant company isolation system by ensuring all API endpoints enforce company filtering, implementing comprehensive isolation tests, activating Record Rules for Odoo Web UI, and validating all create/update operations against user's authorized companies. This builds upon the existing `@require_company` decorator and `CompanyValidator` service (30% complete) to achieve 100% data isolation across competing real estate agencies.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Odoo 18.0, Authlib 1.3+, PyJWT, PostgreSQL 16, Redis 7  
**Storage**: PostgreSQL 16-alpine with Many2many junction tables (`company_property_rel`, `company_agent_rel`, etc.)  
**Testing**: Odoo Test Suite (unittest) + Cypress 13.x for E2E  
**Target Platform**: Linux server (Docker containers on macOS development)  
**Project Type**: Web application (backend API + Odoo Web UI)  
**Performance Goals**: <10% degradation vs. Phase 0 baseline (API response time <200ms p95), maintain 1000 req/s throughput  
**Constraints**: Zero data leakage between companies (100% isolation), backward compatibility with existing 12 API endpoints, maintain 80%+ test coverage  
**Scale/Scope**: 3 competing real estate companies (test env), ~500 properties per company, 10-20 users per company

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Security First ✅ PASS
- [x] All API endpoints use `@require_jwt` + `@require_session` + `@require_company` (triple-layer defense)
- [x] Company isolation at ORM level prevents SQL injection bypasses
- [x] Error messages return 404 (not 403) for unauthorized records to prevent information disclosure
- [x] Audit logging captures all unauthorized access attempts
- **Status**: Fully aligned - this feature IS the multi-tenant security implementation

### Principle II: Test Coverage Mandatory ✅ PASS
- [x] User Story 5 requires comprehensive isolation test suite (30+ scenarios)
- [x] Integration tests for all endpoints (12 existing + new ones)
- [x] E2E tests for Odoo Web UI Record Rules
- [x] Edge case testing (0/1/multiple company assignments, session expiry, etc.)
- [x] Target: 80%+ coverage maintained
- **Status**: Test-first approach aligned with ADR-003

### Principle III: API-First Design ✅ PASS
- [x] No changes to existing API contracts (backward compatible)
- [x] Decorator approach is transparent to API consumers
- [x] OpenAPI docs updated to reflect company filtering behavior
- [x] Error responses use standard `error_response()` helper
- **Status**: Maintains RESTful design, no breaking changes

### Principle IV: Multi-Tenancy by Design ✅ PASS (THIS IS THE FEATURE)
- [x] Implements company isolation (core requirement of ADR-008 Phase 1)
- [x] Filters by `estate_company_ids` Many2many relationship
- [x] Validates create/update operations against authorized companies
- [x] Record Rules enforce isolation in Odoo Web UI
- **Status**: This feature completes Phase 1 of multi-tenancy architecture

### Principle V: ADR Governance ✅ PASS
- [x] Implements ADR-008 (API Security & Multi-Tenancy)
- [x] Follows ADR-011 (Controller Security patterns)
- [x] Follows ADR-001 (OOP architecture, service layers)
- [x] Follows ADR-004 (naming conventions for models/tests)
- **Status**: Directly implements documented ADRs

### Overall Constitution Compliance: ✅ ALL GATES PASS

**No violations** - Feature is fully aligned with all 5 constitution principles. Proceed to Phase 0 research.

**Post-Phase 1 Re-evaluation**: ✅ ALL GATES STILL PASS

After completing design artifacts (data-model.md, record-rules.xml, quickstart.md):
- ✅ Security approach confirmed: Triple-layer decorators + Record Rules + ORM filtering
- ✅ Test strategy confirmed: 30+ isolation tests + integration tests + E2E tests
- ✅ API contracts unchanged: Backward compatible, transparent filtering
- ✅ Multi-tenancy complete: Junction tables + Many2many relationships documented
- ✅ ADR compliance verified: Follows ADR-001 (OOP), ADR-008 (isolation), ADR-011 (decorators)

**Final Verdict**: Approved for implementation (Phase 2: Tasks)

## Project Structure

### Documentation (this feature)

```text
specs/001-company-isolation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── record-rules.xml # Odoo Record Rule definitions
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (Odoo module structure)

```text
18.0/extra-addons/
├── thedevkitchen_apigateway/
│   ├── middleware.py                    # ✅ @require_company decorator exists (line 280)
│   ├── services/
│   │   └── audit_logger.py              # TO ENHANCE: Add company isolation violation logging
│   └── tests/
│       ├── test_require_company.py      # TO CREATE: Decorator unit tests
│       └── test_middleware_integration.py # TO ENHANCE: Add company scenarios
│
└── quicksol_estate/
    ├── models/
    │   ├── property.py                  # ✅ Has estate_company_ids field
    │   ├── agent.py                     # ✅ Has estate_company_ids field  
    │   ├── tenant.py                    # ✅ Has estate_company_ids field
    │   ├── owner.py                     # ✅ Has estate_company_ids field
    │   ├── building.py                  # ✅ Has estate_company_ids field
    │   ├── lease.py                     # TO VERIFY: Needs estate_company_ids?
    │   └── sale.py                      # TO VERIFY: Needs estate_company_ids?
    │
    ├── controllers/
    │   ├── property_api.py              # ✅ Uses @require_company (4 endpoints)
    │   └── master_data_api.py           # ✅ Uses @require_company (8 endpoints)
    │
    ├── services/
    │   ├── company_validator.py         # ✅ EXISTS: validate_company_ids(), ensure_company_ids()
    │   └── security_service.py          # TO CREATE: Centralized company filtering logic
    │
    ├── security/
    │   ├── ir.model.access.csv          # ✅ EXISTS: Access control
    │   └── security.xml                 # TO ENHANCE: Add Record Rules for company isolation
    │
    └── tests/
        ├── api/
        │   ├── test_property_api.py     # TO ENHANCE: Add company isolation scenarios (53 tests exist)
        │   ├── test_master_data_api.py  # TO ENHANCE: Add company isolation scenarios (22 tests exist)
        │   └── test_company_isolation.py # TO CREATE: Dedicated isolation test suite (30+ tests)
        │
        └── models/
            └── test_company_filtering.py # TO CREATE: ORM-level filtering tests

tests/ (E2E - Cypress)
└── e2e/
    └── company-isolation.cy.js          # TO CREATE: Odoo Web UI isolation tests
```

**Structure Decision**: Using existing Odoo 18.0 module structure. Code changes are incremental enhancements to existing `thedevkitchen_apigateway` and `quicksol_estate` modules. No new modules required. Follows ADR-001 (OOP architecture) and ADR-004 (naming conventions).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

✅ **No violations** - Constitution Check passed all gates. No complexity justification required.
