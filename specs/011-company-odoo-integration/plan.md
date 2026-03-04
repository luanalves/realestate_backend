# Implementation Plan: Integração do Módulo de Imobiliária com Company do Odoo

**Branch**: `011-company-odoo-integration` | **Date**: 2026-03-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-company-odoo-integration/spec.md`

## Summary

Migrate the custom `thedevkitchen.estate.company` model (standalone, 224-line model with 8 M2M tables and custom user association) to Odoo's native `res.company` via `_inherit`. This eliminates the parallel company architecture, enables native multi-company record rules, replaces all M2M `company_ids` on business models with M2O `company_id`, removes the custom `real.estate.state` model (use native `res.country.state`), and updates 82 files across models, controllers, security, tests, and documentation (6 ADRs + 1 KB).

## Technical Context

**Language/Version**: Python 3.10+ (Odoo 18.0), XML (views/data), Bash (integration tests)
**Primary Dependencies**: Odoo 18.0 ORM, PostgreSQL 15, Redis 7-alpine (sessions/cache), RabbitMQ + Celery (async)
**Storage**: PostgreSQL — `realestate` database; Redis DB1 (sessions/cache), DB2 (Celery)
**Testing**: Python `unittest` + `unittest.mock` (unit), curl/shell (E2E API), Cypress (E2E UI) — per ADR-003
**Target Platform**: Docker (odoo:18.0 image), macOS dev, Linux prod
**Project Type**: Web (Odoo backend modules + headless SSR frontend consuming REST APIs)
**Performance Goals**: N/A for this refactoring — no new endpoints, no new load patterns
**Constraints**: Zero breaking changes to API contracts (FR-014). Dev environment — data destruction acceptable via `reset_db.sh`. Must maintain 80%+ test coverage (ADR-003).
**Scale/Scope**: 82 files modified, 8 tables dropped, 2 models eliminated, 19 FRs, 14 SCs, 7 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Security First (NON-NEGOTIABLE)

| Gate | Status | Evidence |
|------|--------|----------|
| All authenticated endpoints keep `@require_jwt` + `@require_session` + `@require_company` | ✅ PASS | FR-009 specifies `@require_company` rewrite; no decorators removed, only middleware internals change |
| Public endpoints marked with `# public endpoint` | ✅ PASS | No new public endpoints added; existing public endpoints (Feature 009) unchanged |
| Session hijacking protection preserved | ✅ PASS | Redis session storage unchanged; `@require_session` decorator preserved |
| Multi-tenant isolation maintained | ✅ PASS | Migrating FROM custom isolation TO native Odoo isolation (`company_ids` nativo). Stronger, not weaker. All 15+ record rules rewritten to native `[('company_id', 'in', company_ids)]` |

### Principle II — Test Coverage Mandatory (NON-NEGOTIABLE)

| Gate | Status | Evidence |
|------|--------|----------|
| Unit tests updated for changed logic | ✅ PASS | 29 test files updated per inventory. 2 test files removed and rewritten for `res.company` |
| Integration tests cover new isolation | ✅ PASS | 14 shell scripts updated. US3 defines isolation test scenarios |
| Coverage stays ≥80% | ✅ PASS | Same or more test methods — migration is 1:1 replacement, not reduction |

### Principle III — API-First Design (NON-NEGOTIABLE)

| Gate | Status | Evidence |
|------|--------|----------|
| Existing API contracts preserved | ✅ PASS | FR-014: "Zero breaking changes para consumidores da API" |
| Response JSON format unchanged | ✅ PASS | FR-010: "Manter o mesmo formato de resposta JSON" |
| OpenAPI/Postman docs remain valid | ✅ PASS | No new endpoints; existing contracts unchanged |

### Principle IV — Multi-Tenancy by Design (NON-NEGOTIABLE)

| Gate | Status | Evidence |
|------|--------|----------|
| Company isolation enforced | ✅ PASS | Native `[('company_id', 'in', company_ids)]` — Odoo's built-in, optimized mechanism |
| Record rules use native pattern | ✅ PASS | FR-008: All 15+ rules migrated to native domain |
| Middleware validates company access | ✅ PASS | FR-009: `request.update_env(company=...)` replaces custom domain injection |
| No cross-company data leakage | ✅ PASS | US3 acceptance scenarios test isolation explicitly |

### Principle V — ADR Governance

| Gate | Status | Evidence |
|------|--------|----------|
| ADR-004 compliance (naming) | ✅ PASS | Fields on inherited models use plain names (idiom per `l10n_br`). ADR-004 updated to clarify scope: prefix for tables and module names only |
| ADR-008 compliance (multi-tenancy) | ✅ PASS | ADR-008 updated: `estate_company_ids` → `company_ids` nativo |
| ADR-011 compliance (controller security) | ✅ PASS | Triple decorators maintained on all authenticated endpoints |
| ADR-019 compliance (RBAC) | ✅ PASS | All 9 RBAC profiles migrated to native record rules |
| New patterns documented | ✅ PASS | KB-07 gains inheritance patterns section. ADR-004 gains `_inherit` clarification |

### Principle VI — Headless Architecture (NON-NEGOTIABLE)

| Gate | Status | Evidence |
|------|--------|----------|
| SSR frontend API contracts preserved | ✅ PASS | FR-014: Zero breaking changes |
| Odoo Web admin still works | ✅ PASS | `res.company` views extend native forms — Odoo Web natively supports inherited views |

**Gate Result: ALL PASS** — Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/011-company-odoo-integration/
├── plan.md              # This file
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── company-api.md   # API contract documentation for affected endpoints
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
18.0/extra-addons/
├── quicksol_estate/                          # Main estate module
│   ├── models/
│   │   ├── company.py                        # REWRITE: _inherit='res.company' + real estate fields
│   │   ├── state.py                          # DELETE: real.estate.state eliminated
│   │   ├── res_users.py                      # MODIFY: remove estate_company_ids
│   │   ├── property.py                       # MODIFY: M2M→M2O, state_id→res.country.state
│   │   ├── agent.py                          # MODIFY: M2M→M2O, adapt sync methods
│   │   ├── lead.py                           # MODIFY: M2M→M2O
│   │   ├── lease.py                          # MODIFY: M2M→M2O
│   │   ├── sale.py                           # MODIFY: remove M2M, keep M2O→res.company
│   │   ├── commission_rule.py                # MODIFY: M2O→res.company
│   │   ├── commission_transaction.py         # MODIFY: M2O→res.company
│   │   ├── profile.py                        # MODIFY: M2O→res.company
│   │   ├── assignment.py                     # MODIFY: M2O→res.company, simplify validation
│   │   ├── property_owner.py                 # MODIFY: state_id→res.country.state
│   │   ├── property_building.py              # MODIFY: state_id→res.country.state
│   │   └── observers/
│   │       └── user_company_validator_observer.py  # MODIFY: company_ids nativo
│   ├── controllers/  (6 files)               # MODIFY: env refs + company_ids
│   ├── services/     (2 files)               # MODIFY: env refs
│   ├── security/     (2 files)               # MODIFY: ACLs + record rules
│   ├── data/         (3 files)               # REWRITE/DELETE: seeds
│   ├── views/        (2 files)               # REWRITE: inherited views
│   ├── tests/        (29 files)              # MODIFY: env refs + company_ids
│   └── __manifest__.py                       # MODIFY: data files + dependencies
├── thedevkitchen_apigateway/
│   ├── middleware.py                          # REWRITE: require_company internals
│   └── controllers/ (2 files)                # MODIFY: login/me payloads
└── thedevkitchen_user_onboarding/ (3 files)  # MODIFY: company_id→res.company

docs/adr/    (6 files)                        # ADR-004,008,009,019,020,024
docs/architecture/ (1 file)                   # DATABASE_ARCHITECTURE_USERS.md
knowledge_base/ (1 file)                      # 07-programming-in-odoo.md
integration_tests/ (14 files)                 # Shell scripts: SQL/model refs
```

**Structure Decision**: Existing Odoo module structure preserved. No new modules created. Changes are in-place refactoring across 3 existing modules + documentation + tests.

## Constitution Re-Check (Post Phase 1 Design)

*Re-evaluated after data-model.md, contracts/, and quickstart.md were generated.*

| Principle | Status | Post-Design Evidence |
|-----------|--------|---------------------|
| I — Security First | ✅ PASS | `is_real_estate` discriminator prevents non-RE company leakage. `request.update_env()` uses native security. Triple decorators unchanged. |
| II — Test Coverage | ✅ PASS | quickstart.md Phase E mandates 29 test files + 14 integration scripts + 3 new test scenarios. Coverage ≥80%. |
| III — API-First | ✅ PASS | contracts/company-api.md documents zero breaking changes across all 6 endpoint groups. Field mapping table for `zip_code`↔`zip`. |
| IV — Multi-Tenancy | ✅ PASS | data-model.md: all record rules migrate to native `[('company_id', 'in', company_ids)]`. |
| V — ADR Governance | ✅ PASS | 6 ADRs + 1 KB doc identified for update in quickstart.md Phase F. |
| VI — Headless Architecture | ✅ PASS | No new Odoo Web views. Only `_inherit` form extensions for admin. |

**Post-Design Gate Result: ALL PASS** — No violations, no new risks introduced by design artifacts.

## Complexity Tracking

> No constitution violations found — all gates pass. No complexity justification needed.
