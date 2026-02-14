# Implementation Plan: Tenant, Lease & Sale API Endpoints

**Branch**: `008-tenant-lease-sale-api` | **Date**: 2026-02-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-tenant-lease-sale-api/spec.md`

## Summary

Implement 18 REST API endpoints for Tenants (6), Leases (7), and Sales (5) management in the `quicksol_estate` Odoo module. Extends 3 existing models with lifecycle/soft-delete fields, creates 1 new audit model (`lease.renewal.history`), and adds 3 new controller files following the established triple-auth, multi-tenant, HATEOAS pattern from Feature 007.

## Technical Context

**Language/Version**: Python 3.12 (Ubuntu Noble Docker image)
**Primary Dependencies**: Odoo 18.0 (ORM, HTTP framework), Redis 7 (sessions)
**Storage**: PostgreSQL 14+ via Odoo ORM, Redis 7 for HTTP sessions
**Testing**: Python unittest + mock (unit), curl/bash scripts (API integration), Cypress (E2E)
**Target Platform**: Linux Docker container (Odoo 18.0 + PostgreSQL 14 + Redis 7)
**Project Type**: Web application (Odoo backend module, headless REST API)
**Performance Goals**: < 2s response time for single-resource operations (SC-006)
**Constraints**: 100% company data isolation (SC-007), >= 80% test coverage (Constitution II)
**Scale/Scope**: 18 endpoints, 4 models (3 modified + 1 new), 3 controllers, 6 schemas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Security First | PASS | All 18 endpoints use triple decorator pattern. No public endpoints. |
| II. Test Coverage | PASS | Plan includes unit tests (models, validators), integration tests (all endpoints), E2E tests (Cypress). Target >= 80%. |
| III. API-First | PASS | OpenAPI 3.0.3 contracts for all 3 entities. HATEOAS links. Postman collection planned. |
| IV. Multi-Tenancy | PASS | All queries filtered by company_ids via @require_company. Record Rules enforce Odoo Web isolation. |
| V. ADR Governance | PASS | Compliant with ADR-003 (tests), ADR-007 (HATEOAS), ADR-008 (multi-tenancy), ADR-011 (auth), ADR-015 (soft-delete), ADR-016 (Postman). |
| VI. Headless Architecture | PASS | Pure REST API. No Odoo Web UI views. Designed for SSR frontend consumption. |

**Post-Phase 1 Re-Check**: All 6 principles remain PASS. Design decisions (in-place lease renewal, transitive RBAC, property sold status) align with constitutional principles and confirmed clarifications.

## Project Structure

### Documentation (this feature)

    specs/008-tenant-lease-sale-api/
    |- plan.md                          # This file
    |- research.md                      # Phase 0 output (10 research items)
    |- data-model.md                    # Phase 1 output (4 entities, ER diagram)
    |- quickstart.md                    # Phase 1 output (developer guide)
    |- contracts/
    |  |- tenant-api.yaml              # OpenAPI 3.0.3 - 6 endpoints
    |  |- lease-api.yaml               # OpenAPI 3.0.3 - 7 endpoints
    |  |- sale-api.yaml                # OpenAPI 3.0.3 - 5 endpoints
    |- checklists/
    |  |- requirements.md              # Spec quality checklist (16/16)
    |- tasks.md                         # Phase 2 output (NOT created by /speckit.plan)

### Source Code (repository root)

    18.0/extra-addons/quicksol_estate/
    |- models/
    |  |- __init__.py                  # MODIFY: add lease_renewal_history import
    |  |- tenant.py                    # MODIFY: add active, deactivation fields
    |  |- lease.py                     # MODIFY: add status, termination, renewal fields
    |  |- sale.py                      # MODIFY: add status, cancellation fields
    |  |- lease_renewal_history.py     # NEW: audit model for lease renewals
    |- controllers/
    |  |- __init__.py                  # MODIFY: add tenant_api, lease_api, sale_api
    |  |- tenant_api.py                # NEW: 6 endpoints (CRUD + leases sub-resource)
    |  |- lease_api.py                 # NEW: 7 endpoints (CRUD + renew + terminate)
    |  |- sale_api.py                  # NEW: 5 endpoints (CRUD + cancel)
    |  |- utils/
    |     |- schema.py                # MODIFY: add 6 validation schemas
    |- security/
    |  |- ir.model.access.csv         # MODIFY: add access rules for new model
    |  |- record_rules.xml            # MODIFY: add company isolation rules
    |- tests/
    |  |- api/
    |  |  |- test_tenant_api.py       # NEW: tenant endpoint tests
    |  |  |- test_lease_api.py        # NEW: lease endpoint tests
    |  |  |- test_sale_api.py         # NEW: sale endpoint tests
    |  |- utils/
    |     |- test_validators.py       # MODIFY: add new validation tests
    |- data/
    |  |- master_data.xml              # MODIFY: add lease status master data (if needed)
    |- __manifest__.py                  # MODIFY: bump version

    docs/postman/
    |- feature008_tenant_lease_sale_v1.0_postman_collection.json  # NEW: ADR-016

    integration_tests/
    |- test_us8_s1_tenant_crud.sh       # NEW
    |- test_us8_s2_lease_lifecycle.sh   # NEW
    |- test_us8_s3_sale_management.sh   # NEW
    |- test_us8_s4_tenant_lease_history.sh  # NEW
    |- test_us8_s5_soft_delete.sh       # NEW

    cypress/e2e/
    |- tenant-management.cy.js          # NEW
    |- lease-management.cy.js           # NEW
    |- sale-management.cy.js            # NEW

**Structure Decision**: Follows existing Odoo module layout per ADR-001/ADR-004. All new code goes into the existing quicksol_estate module. No new modules needed. Feature 007 (owner_api.py) serves as the reference implementation for controller patterns.

## Complexity Tracking

> No constitution violations detected. All 6 principles pass without exceptions.t 
