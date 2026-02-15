# Comprehensive Requirements Quality Checklist: Tenant, Lease & Sale API

**Purpose**: Validate specification completeness, clarity, and consistency across all domains (API, Security, Integration Tests, Non-Functional) for PR review
**Created**: 2026-02-14
**Triaged**: 2026-02-14
**Feature**: [spec.md](../spec.md)
**Depth**: Standard | **Audience**: PR Reviewer | **Focus**: All domains

**Triage Summary**: 37 ✅ RESOLVED | 0 ⚠️ SPEC GAP | 8 ℹ️ ACCEPTABLE — ALL GAPS CLOSED

## Requirement Completeness

- [x] CHK001 - ✅ RESOLVED — Dual error envelope documented in spec § TD-001. Both shapes are intentional: `error_response()` for gateway-layer errors, `util_error()` for structured validation errors. Consumers MUST handle both. Unification deferred.
- [x] CHK002 - ✅ RESOLVED — Lease `expired` transition implemented via `_cron_expire_leases()` daily cron (data/lease_cron.xml). Searches active leases with `end_date < today`, sets expired via context flag `cron_expire`.
- [x] CHK003 - ✅ RESOLVED — Event payload is `{sale_id: int, sale: recordset}`, emitted synchronously via `_emit_sync`. Documented in code; spec can reference as-is.
- [x] CHK004 - ✅ RESOLVED — All 3 controllers use consistent defaults: `page_size=20`, `max=100` via `min(int(page_size), 100)`.
- [x] CHK005 - ✅ RESOLVED — Fire-and-forget event semantics documented in spec § TD-002. Observer failures for `after_` events are caught/logged; `before_` events propagate and abort. Bus infrastructure failure causes rollback.
- [x] CHK006 - ℹ️ ACCEPTABLE — No bulk endpoints exist. Consistent with CRUD-first approach; can be added later.
- [x] CHK007 - ✅ RESOLVED — Audit trail scope documented in spec § TD-005. In-record fields for tenant/sale, `lease.renewal.history` model for lease renewals. General audit log deferred.
- [x] CHK008 - ✅ RESOLVED — Computed name: `"{Property} - {Tenant} ({start_date})"`, fallback `"New Lease"`. Stored computed field.
- [x] CHK009 - ✅ RESOLVED — `action_cancel()` now guards property revert: only sets `state='new'` if `property_id.state == 'sold'`. Skips revert if property state was changed after sale creation.
- [x] CHK010 - ✅ RESOLVED — Added active-lease check to `delete_tenant()`. Archive proceeds but response includes `warning` field with count of active leases. Matches spec edge case. Documented in § TD-004.

## Requirement Clarity

- [x] CHK011 - ℹ️ ACCEPTABLE — "3 interactions" is a test design metric. Code meets intent (each operation = 1 API call).
- [x] CHK012 - ℹ️ ACCEPTABLE — Latency SLA is an operational concern for load testing, not enforced in code.
- [x] CHK013 - ✅ RESOLVED — Uses `<=` (boundary-inclusive): lease ending 2026-01-31 **conflicts** with one starting 2026-01-31. Stricter interpretation — no same-day overlap. Well-defined in code.
- [x] CHK014 - ✅ RESOLVED — All 3 controllers implement agent → `property.assignment` → property IDs → transitive resource filtering via `_get_agent_property_ids()` + `_is_agent_role()`.
- [x] CHK015 - ✅ RESOLVED — `lease_api.create_lease()` explicitly blocks **all** lease creation (draft+active) on sold properties: `if prop.state == 'sold': return 400`.
- [x] CHK016 - ℹ️ ACCEPTABLE — `sale.created` event fires automatically on `create()`. SC-005 is met by design.
- [x] CHK017 - ℹ️ ACCEPTABLE — Subjective metric for test design. Integration tests validate happy path runs to completion.

## Requirement Consistency

- [x] CHK018 - ✅ RESOLVED (by design) — Sale's dual `company_id` (M2O) + `company_ids` (M2M) is intentional: `company_id` = primary transaction company, `company_ids` = visibility scope. Controller validates and sets both.
- [x] CHK019 - ✅ RESOLVED — Cancel-only semantics for sales documented in spec § TD-003. Sales use `POST /cancel` (business action with property revert), not soft-archive. The `active` field is not toggled by any endpoint. Intentional by design.
- [x] CHK020 - ✅ RESOLVED — All controllers include status-aware action links: lease has `renew`/`terminate` (when active), sale has `cancel` (when not cancelled), tenant has `leases` sub-resource link.
- [x] CHK021 - ✅ RESOLVED — Extended `test_us8_s5_soft_delete.sh` with lease archive→query inactive→verify hidden cycle (4 new tests). Sale section documents cancel-only semantics per TD-003. S5 now passes 11/11.

## Acceptance Criteria Quality

- [x] CHK022 - ✅ RESOLVED — Added `test_us8_s6_isolation_rbac.sh` with cross-company negative tests: Manager creates tenant → User B login → GET/LIST/UPDATE tenant → expects 404/403 (data isolation). Gracefully skips when User B not provisioned.
- [x] CHK023 - ✅ RESOLVED — Unit tests cover all schema constraints, model `@api.constrains`, and validator lambdas across 4 test files (130 tests total).
- [x] CHK024 - ✅ RESOLVED — Added `VALID_TRANSITIONS` state machine in `lease.py` `write()` override: `draft→[active], active→[terminated], terminated→[], expired→[]`. Context flags `cron_expire` and `lease_terminate` allow controlled bypass. 10 unit tests validate all transitions.
- [x] CHK025 - ✅ RESOLVED (implicitly) — Archived properties (`active=False`) are excluded by Odoo's default `active_test`, so `prop.exists()` returns False → sale creation fails with "Property not found".

## Scenario Coverage

- [x] CHK026 - ✅ RESOLVED — Concurrent lease race condition documented as known limitation in spec § TD-006. ORM-level check is sufficient for MVP low-concurrency usage. PostgreSQL `EXCLUDE` constraint or `FOR UPDATE` lock documented as future mitigation.
- [x] CHK027 - ✅ RESOLVED — Added agent RBAC tests in `test_us8_s6_isolation_rbac.sh` (Part 2): Agent login → list tenants/leases/sales → verifies filtered results. Gracefully skips when agent user not provisioned.
- [x] CHK028 - ℹ️ ACCEPTABLE — Unbounded `One2many` for renewal history is standard Odoo pattern. `lease_id` has `index=True`. Pagination on detail endpoint mitigates performance concerns.
- [x] CHK029 - ✅ RESOLVED — Sale model has **no FK to Tenant** (`buyer_name`/`buyer_partner_id` are separate fields). Tenant archive has no sale integrity concern.

## Edge Case Coverage

- [x] CHK030 - ✅ RESOLVED — Concurrent lease constraint filters by `status in ['draft', 'active']`. Expired/terminated leases are **excluded** from overlap check. Unit test `test_terminated_lease_allows_overlap` confirms.
- [x] CHK031 - ✅ RESOLVED — Same fix as CHK009: `action_cancel()` now checks `property_id.state == 'sold'` before reverting. 4 unit tests in `TestSaleCancelGuard` validate all edge cases.
- [x] CHK032 - ✅ RESOLVED — `start_date == end_date` is **rejected** at both model (`end_date <= start_date → ValidationError`) and controller level.
- [x] CHK033 - ℹ️ ACCEPTABLE — Tenant reactivation is record-level only (sets `active=True`). Lease linking is a separate operation via `POST /leases` with its own validation.
- [x] CHK034 - ℹ️ ACCEPTABLE — Large offsets produce empty results. Standard Odoo/PostgreSQL behavior. No max offset check needed.

## Non-Functional Requirements

- [x] CHK035 - ✅ RESOLVED — Rate limiting deferred, documented in spec § TD-007. Internal API behind SSR frontend; Odoo WSGI `limit_request` provides natural back-pressure. Per-endpoint thresholds to be defined if public exposure is planned.
- [x] CHK036 - ℹ️ ACCEPTABLE — Odoo WSGI `limit_request` (default 8192) covers payload limits. No custom validation needed for JSON payloads.
- [x] CHK037 - ✅ RESOLVED — Global `< 2s` threshold documented as sufficient in spec § TD-008. All endpoints use indexed CRUD with pagination capped at 100 items. Per-endpoint SLAs to be introduced if degradation is observed.
- [x] CHK038 - ✅ RESOLVED — All 3 controllers use `_logger.error(exc_info=True)` on catch blocks and `_logger.warning` for validation errors. EventBus uses `_logger.debug`. Structured logging in place.
- [x] CHK039 - ✅ RESOLVED — English-only API error policy documented in spec § TD-009. Headless API uses stable English strings; SSR frontend translates to user's locale. Standard practice for machine-consumable APIs.

## Security Requirements

- [x] CHK040 - ✅ RESOLVED — Company isolation violations consistently return **404** (not 403) across all 3 controllers. Prevents information leakage (can't distinguish "not found" vs "not yours").
- [x] CHK041 - ✅ RESOLVED — Full buyer field exposure documented as acceptable in spec § TD-010. All authenticated roles have legitimate business need for buyer contact. LGPD field-level masking documented as future enhancement.
- [x] CHK042 - ℹ️ ACCEPTABLE — No HTML rendering in REST API → no XSS risk. Odoo ORM uses parameterized queries → no SQLi risk. `.strip()` applied to key string fields. Adequate for headless API.

## Dependencies & Assumptions

- [x] CHK043 - ✅ RESOLVED — `quicksol.event.bus` exists, is fully implemented, imported, tested (in `tests/observers/`), and used by sale, property, and auth modules.
- [x] CHK044 - ✅ RESOLVED — Spec explicitly justifies in two places: "shared email (e.g., a household) is acceptable". Code matches — no `_sql_constraints` on email, only format validation.
- [x] CHK045 - ✅ RESOLVED — Infrastructure dependencies (PostgreSQL 14+, Redis 7) added to spec § Dependencies with cross-reference to plan.md § Technical Context.

---

## Triage Summary

| Verdict | Count | Items |
|---------|-------|-------|
| ✅ RESOLVED | 37 | CHK001-005, 007-009, 010-015, 016-027, 029-032, 034-037, 038-041, 042-045 |
| ⚠️ SPEC GAP | 0 | — |
| ℹ️ ACCEPTABLE | 8 | CHK006, 011, 012, 016, 017, 028, 033, 034, 036 |

### All Gaps Closed ✅

**Critical gaps** (5 items — code fixes, committed `3059278`):

| # | Resolution |
|---|-----------|
| CHK002 | `_cron_expire_leases()` daily cron + `data/lease_cron.xml` |
| CHK009/031 | Sale cancel guard: only revert if `property_id.state == 'sold'` |
| CHK024 | `VALID_TRANSITIONS` state machine in `write()` + 10 unit tests |
| CHK022 | `test_us8_s6_isolation_rbac.sh` Part 1 (cross-company negative tests) |
| CHK027 | `test_us8_s6_isolation_rbac.sh` Part 2 (agent RBAC tests) |

**Spec documentation gaps** (10 items — documented in spec.md § Technical Decisions):

| # | Decision | Spec § |
|---|----------|--------|
| CHK001 | Dual error envelope: both valid, unification deferred | TD-001 |
| CHK005 | Event bus fire-and-forget semantics | TD-002 |
| CHK019 | Sale cancel-only, no DELETE endpoint | TD-003 |
| CHK010 | Tenant archive with active-lease warning | TD-004 |
| CHK007 | Audit trail scope: in-record fields + renewal history | TD-005 |
| CHK026 | Concurrent lease overlap: ORM-level, known limitation | TD-006 |
| CHK035 | Rate limiting deferred (internal API) | TD-007 |
| CHK037 | Global < 2s SLA sufficient | TD-008 |
| CHK039 | English-only error messages (SSR translates) | TD-009 |
| CHK041 | Full buyer field exposure acceptable for MVP | TD-010 |
| CHK045 | Infrastructure deps added to spec Dependencies | — |

**Code fixes** (2 items — implemented):

| # | Fix |
|---|-----|
| CHK010 | Active-lease warning in `delete_tenant()` response |
| CHK021 | S5 extended with lease soft-delete tests (11/11 passing) |
