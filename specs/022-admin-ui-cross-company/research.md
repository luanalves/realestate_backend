# Research: Admin UI — Cross-Company Access for System Admin

**Feature**: 022-admin-ui-cross-company  
**Date**: 2026-06-03  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## R-001 Odoo Record Rule OR-Union Evaluation

**Question**: Does Odoo genuinely combine multiple record rules for the same model with OR when the user belongs to multiple groups?

**Decision**: Yes — confirmed in Odoo source (`ir.rule._compute_domain`). When a user belongs to two groups each with a separate rule on the same model, Odoo evaluates them as `rule_A OR rule_B`. A `[(1,'=',1)]` rule for `base.group_system` therefore supersedes any company-filtered rule from `base.group_user` or role groups that the admin also inherits.

**Rationale**: This is the native mechanism Odoo itself uses in core modules (e.g., `sale`, `purchase`, `stock`) to grant managers unrestricted access alongside restricted group rules.

**Alternatives considered**: `.sudo()` in controllers — rejected because it would bypass record rules globally and violate ADR-008. Creating a separate admin-only model — rejected as unnecessary complexity.

---

## R-002 `noupdate="1"` Compatibility Strategy

**Question**: How can new admin override rules be applied to existing production databases when the target file uses `noupdate="1"`, which prevents record update on `--update`?

**Decision**: Place new admin override rules in a **separate `<data noupdate="0">` block** appended at the bottom of the same XML file. Odoo processes all `<data>` blocks in a file sequentially; the new block will be created/updated on every module upgrade while the existing `noupdate="1"` rules remain untouched.

**Rationale**: Cleanest approach — no new files, no migration scripts. The two blocks coexist in one file without conflict.

**noupdate audit by file**:

| File | Current noupdate | Admin block strategy |
|------|-----------------|----------------------|
| `quicksol_estate/security/record_rules.xml` | `"1"` | Append new `<data noupdate="0">` block |
| `quicksol_estate/security/proposal_record_rules.xml` | `"0"` | Append directly inside existing block |
| `quicksol_estate/security/service_record_rules.xml` | `"0"` | Append directly inside existing block |
| `thedevkitchen_cms/security/cms_record_rules.xml` | `"1"` | Append new `<data noupdate="0">` block |
| `thedevkitchen_estate_goals/security/record_rules.xml` | `"0"` | Append directly inside existing block |
| `thedevkitchen_estate_credit_check/security/record_rules.xml` | `"1"` | Append new `<data noupdate="0">` block |
| `thedevkitchen_user_onboarding/security/record_rules.xml` | `"1"` | Append new `<data noupdate="0">` block |

**Alternatives considered**: Migration script in `migrations/` — more complex, not necessary when a `noupdate="0"` block suffices. New standalone XML files per module — adds file count without benefit.

---

## R-003 `AuditLogger.log_failed_login` Signature

**Question**: What is the exact call signature of `AuditLogger.log_failed_login` in the existing controller?

**Decision**: Signature is `log_failed_login(ip_address: str, email: str, reason: str = None)`.

**Evidence**: Confirmed from `user_auth_controller.py` lines 50, 61, 73:
- Line 50: `AuditLogger.log_failed_login(ip_address, email)` — no reason
- Line 61: `AuditLogger.log_failed_login(ip_address, email, str(auth_error))` — with reason
- Line 73: `AuditLogger.log_failed_login(ip_address, email, 'User inactive')` — with reason

**Admin block call**: `AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')` — uses explicit reason for forensic auditability while keeping the HTTP response generic (anti-enumeration).

---

## R-004 Login Controller Insertion Point

**Question**: Where exactly in `user_auth_controller.py` should the System Admin block be inserted?

**Decision**: After the `if not user.active` check (line ~73) and **before** the "Invalidar sessões antigas" block (line ~80+). This is the earliest safe point where:
- `uid` has been obtained (credentials verified valid)
- `user` object is loaded (so `has_group` can be called)
- No session has been created yet (no logout/invalidation side-effects)

**Why not before `authenticate()`**: `has_group` requires a loaded user object; we cannot call it before verifying credentials. Also, calling `has_group` on an unauthenticated email string is not possible.

**Why not after session creation**: Session invalidation and new session creation would already have occurred, causing spurious audit entries and partial side-effects.

---

## R-005 HTTP Status for Admin API Block

**Question**: Should the admin API login block return HTTP 403 or HTTP 401?

**Decision**: HTTP 401 — resolved in clarification session 2026-06-03.

**Rationale**: Anti-enumeration principle (ADR-008). A 403 would reveal that the credentials are valid and the user exists but is blocked. A 401 response is identical to a failed-credential response, giving an attacker no signal that a System Admin account was successfully identified. The internal audit log captures the real reason; the external response hides it.

---

## R-006 Menu Visibility Scope

**Question**: Which menus in `real_estate_menus.xml` are currently hidden from System Admin?

**Decision**: Only `menu_real_estate_lead` (line 9) is explicitly restricted via `groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager"`. All other menus have no `groups` attribute and are visible to all authenticated users including System Admin.

**Evidence**: Full scan of `real_estate_menus.xml` shows 9 `<menuitem>` declarations; only `menu_real_estate_lead` carries a `groups` restriction.

**Fix**: Add `base.group_system` to the existing `groups` attribute of `menu_real_estate_lead`.

---

## R-007 FR-008 Convention Artifacts

**Question**: Where should the developer checklist for "always include System Admin override" live?

**Decision**: Two locations (resolved in clarification session 2026-06-03):
1. `docs/adr/ADR-029-saas-admin-channel-separation.md` — formal architectural decision
2. `knowledge_base/13-saas-admin-module-checklist.md` — day-to-day developer reference

**ADR number**: ADR-028 is `service-pipeline-domain-boundaries.md`. Next available is **ADR-029**.

**Knowledge base**: Existing files are numbered 01–12 plus EXAMPLES, QUICK_REFERENCE, README. New file will be `13-saas-admin-module-checklist.md`.

---

## R-008 No New Models or Migrations Required

**Question**: Does this feature require any new Odoo model definitions, database migrations, or `ir.model.access.csv` entries?

**Decision**: No. This feature is purely:
- XML data (record rules + menu) — handled by module upgrade
- One Python controller guard — no model changes
- Documentation (ADR + knowledge base)

No `ir.model.access.csv` changes needed — `base.group_system` users already have full model access via existing `access_system_admin_*` entries in each module's CSV.

---

## R-010 FR-007 Enforcement — Feature 009 Already Covers It

**Question**: Does FR-007 ("System Admin cannot be invited via REST API") require new guard code in the invite controller?

**Decision**: No new code needed. Feature 009's invitation authorization matrix defines which profiles each role can invite (`Owner → 9 profiles`, `Manager → 5 profiles`, `Agent → 3 profiles`). `base.group_system` is not an invitable profile in any of these matrices — there is no code path that could result in a System Admin being invited via the API.

**Rationale**: Clarified 2026-06-03. The authorization matrix is the correct enforcement layer. Adding a redundant guard would create maintenance overhead without security value. The convention is documented in ADR-029 so future changes to the matrix cannot inadvertently re-enable admin invite.

**Deliverable for this feature**: One integration test (`integration_tests/test_admin_invite_block.sh`) verifying that attempting to set a `base.group_system` user as invite target returns a rejection from the existing matrix logic.

---

## R-011 Write Access Scope for Sensitive Models

**Question**: Should System Admin write access (FR-002) be unrestricted across all entities including `thedevkitchen.password.token`?

**Decision**: Unrestricted — the `[(1,'=',1)]` record rule override applies uniformly to all models for read, write, create, and delete.

**Rationale**: Clarified 2026-06-03. The System Admin already has native Odoo-level access to password tokens via another area of the platform (outside the custom security module). Adding read-only carve-outs would create inconsistency and add complexity without security benefit. System Admin is a trusted platform-level role; the threat model of a rogue admin is a break-glass scenario outside this feature's scope.

**Impact on implementation**: No special handling needed for `thedevkitchen.password.token` or any other model. All record rule overrides follow the same canonical pattern.

---

## R-012 Rate Limiting for Admin API Login Block

**Question**: Should the application add a rate limit for repeated blocked System Admin login attempts?

**Decision**: Delegate to Kong API Gateway — no application-level throttle added.

**Rationale**: Clarified 2026-06-03. Kong already enforces rate limiting at the gateway level for all login endpoint traffic. Adding a duplicate application-level throttle would create inconsistency in rate-limit policy management. The audit log (SC-005) provides the forensic record; Kong handles volumetric defense.

**Impact on implementation**: No rate-limit logic added to `user_auth_controller.py`. The controller guard is: check group → audit log → return 401. No counter, no backoff, no block list.

---

## R-009 Cypress Test Location

**Question**: Where should the new Cypress E2E test file be placed?

**Decision**: `cypress/e2e/views/admin_cross_company.cy.js` — consistent with the existing `cypress/e2e/views/` directory which contains UI navigation tests (e.g., `cms.cy.js`, `cms_status_transitions.cy.js`).

**Integration tests**:
- `integration_tests/test_admin_api_block.sh` — API 401 + audit log verification (FR-004/SC-004)
- `integration_tests/test_admin_invite_block.sh` — FR-007 verification (admin invite rejected by Feature 009 authorization matrix; added post-clarify 2026-06-03)
