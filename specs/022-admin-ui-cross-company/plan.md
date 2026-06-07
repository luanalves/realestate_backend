# Implementation Plan: Admin UI — Cross-Company Access for System Admin

**Branch**: `022-admin-ui-cross-company` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/022-admin-ui-cross-company/spec.md`

## Summary

`base.group_system` (System Admin) is blocked from viewing cross-company data in the Odoo UI because multi-tenancy record rules designed for business users also apply to the admin. Simultaneously, the REST API login endpoint has no guard preventing System Admins from authenticating through a channel they should never use.

The solution is two-pronged:
1. **Record rule overrides**: Add `[(1,'=',1)]` rules assigned to `base.group_system` for every model that has a company-filtering rule. Odoo's native OR-union evaluation means these rules grant the admin full visibility without touching business-user isolation.
2. **API login block**: Inject a `has_group('base.group_system')` check in `user_auth_controller.py` after credential validation but before session creation; return HTTP 401 (anti-enumeration) and audit-log the attempt. Rate limiting is delegated to Kong API Gateway (no application-level throttle).

Additionally: the `menu_real_estate_lead` menu gains `base.group_system` visibility; FR-007 (admin not invitable via API) is verified by test (satisfied by Feature 009's authorization matrix — no new guard code); the convention is formalised as ADR-029 + a knowledge-base checklist (FR-008).

No new models, no database migrations, no new API endpoints.

---

## Technical Context

**Language/Version**: Python 3.11 (controller guard); XML data files (Odoo 18.0 record rules + menus)  
**Primary Dependencies**: Odoo 18.0 ORM (ir.rule), `base.group_system` (Odoo core), `thedevkitchen_apigateway.services.audit_logger.AuditLogger`, Kong API Gateway (rate limiting — existing, no changes)  
**Storage**: PostgreSQL — record rules stored in `ir.rule` table, applied at query-filter level. No schema changes.  
**Testing**: Cypress (E2E / Odoo UI), bash integration tests (API block + FR-007 verification)  
**Target Platform**: Odoo 18.0 on Docker (Linux x86-64)  
**Project Type**: Single Odoo backend monorepo (no frontend changes)  
**Performance Goals**: Zero runtime overhead — record rule additions are evaluated at query build time (same cost as existing rules). The API login block adds one `has_group()` call (~1 SQL query) per login attempt.  
**Constraints**:
- Files with `noupdate="1"` require a separate `<data noupdate="0">` block (R-002)
- No `ir.model.access.csv` changes needed — `access_system_admin_*` entries already cover all models (R-008)
- Write access for System Admin is unrestricted across all entities including `thedevkitchen.password.token` (clarified 2026-06-03 — admin already has native Odoo access via another platform area)
- Rate limiting for blocked admin login attempts is delegated to Kong — no application-level throttle added (clarified 2026-06-03)
- FR-007 (admin not invitable via API) is already enforced by Feature 009's authorization matrix — this feature adds only a verification test + ADR-029 documentation, no new guard code

**Scale/Scope**: 7 XML security files + 1 menu file + 1 controller file + 1 ADR + 1 knowledge base entry + 3 test files across 6 Odoo modules.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status | Notes |
|-----------|-------|--------|-------|
| I — Security First | API block returns 401 (anti-enumeration) + audit log. Admin channel explicitly enforced. Rate limiting delegated to Kong. | ✅ PASS | |
| II — Test Coverage ≥80% | Cypress E2E for cross-company UI visibility; bash integration test for API 401; bash test verifying FR-007 (admin invite blocked). No new Python services — no unit test burden. | ✅ PASS | |
| III — API-First | No new endpoints. Existing login endpoint behavior change documented in `contracts/login-block.md`. | ✅ PASS | Behavior contract replaces new endpoint contract |
| IV — Multi-Tenancy | Business-user isolation unchanged (existing rules unmodified). Admin override is additive (OR-union). SaaS Admin exception documented in constitution v1.8.0. Write access unrestricted — no carve-outs. | ✅ PASS | |
| V — ADR Governance | New ADR-029 documents the `base.group_system` channel separation and new-module convention. FR-007 cross-referencing ADR-029. | ✅ PASS | |
| VI — Headless Architecture | Admin remains Odoo UI only. API block enforces this boundary at the controller level. | ✅ PASS | |

**Post-design re-check**: ✅ All principles still pass after Phase 1 design and post-clarify updates. No new violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/022-admin-ui-cross-company/
├── plan.md              ← this file
├── research.md          ← Phase 0 (complete)
├── data-model.md        ← Phase 1 (complete)
├── quickstart.md        ← Phase 1 (complete)
├── contracts/
│   └── login-block.md   ← Phase 1 (complete)
└── tasks.md             ← Phase 2 (/speckit.tasks — not yet created)
```

### Source Code (files to be modified/created)

```text
# Security XML files — record rule overrides (base.group_system)
18.0/extra-addons/quicksol_estate/security/
├── record_rules.xml                            # MODIFY — append noupdate="0" block (10 models)
├── proposal_record_rules.xml                   # MODIFY — append inside existing block
└── service_record_rules.xml                    # MODIFY — append inside existing block

18.0/extra-addons/thedevkitchen_cms/security/
└── cms_record_rules.xml                        # MODIFY — append noupdate="0" block (3 models)

18.0/extra-addons/thedevkitchen_estate_goals/security/
└── record_rules.xml                            # MODIFY — append inside existing block

18.0/extra-addons/thedevkitchen_estate_credit_check/security/
└── record_rules.xml                            # MODIFY — append noupdate="0" block

18.0/extra-addons/thedevkitchen_user_onboarding/security/
└── record_rules.xml                            # MODIFY — append noupdate="0" block

# Menu file — admin visibility for Leads
18.0/extra-addons/quicksol_estate/views/
└── real_estate_menus.xml                       # MODIFY — add base.group_system to menu_real_estate_lead

# Controller — API login block
18.0/extra-addons/thedevkitchen_apigateway/controllers/
└── user_auth_controller.py                     # MODIFY — inject has_group check after user.active

# Documentation artefacts (new files)
docs/adr/
└── ADR-029-saas-admin-channel-separation.md    # CREATE — formalises the convention + FR-007 reference

knowledge_base/
└── 13-saas-admin-module-checklist.md           # CREATE — developer checklist for new modules

# Tests (new files)
cypress/e2e/views/
└── admin_cross_company.cy.js                   # CREATE — E2E: cross-company visibility in Odoo UI

integration_tests/
├── test_admin_api_block.sh                     # CREATE — API 401 + audit log verification (FR-004/SC-004)
└── test_admin_invite_block.sh                  # CREATE — FR-007 verification (admin invite rejected by Feature 009)
```

**Structure Decision**: Single-project (Odoo monorepo). No new modules created. All changes are additive modifications to existing modules, one new ADR, one knowledge base entry, and three test files (one added post-clarify for FR-007 verification).

---

## Complexity Tracking

> No constitution violations. No complexity justification required.
