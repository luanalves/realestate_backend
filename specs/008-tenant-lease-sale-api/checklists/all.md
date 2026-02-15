# Comprehensive Requirements Quality Checklist: Tenant, Lease & Sale API

**Purpose**: Validate specification completeness, clarity, and consistency across all domains (API, Security, Integration Tests, Non-Functional) for PR review
**Created**: 2026-02-14
**Triaged**: 2026-02-14
**Feature**: [spec.md](../spec.md)
**Depth**: Standard | **Audience**: PR Reviewer | **Focus**: All domains

**Triage Summary**: 23 ✅ RESOLVED | 14 ⚠️ SPEC GAP | 8 ℹ️ ACCEPTABLE

## Requirement Completeness

- [ ] CHK001 - ⚠️ **SPEC GAP** — Are error response formats (shape, status codes, error codes) standardized across all 18 endpoints? Two competing shapes coexist: `error_response()` → `{error, message, code}` vs `util_error()` → `{success, message, errors}`. Controllers mix both within the same endpoint. **Action: unify error envelope or document both as valid.**
- [x] CHK002 - ✅ RESOLVED — Lease `expired` transition implemented via `_cron_expire_leases()` daily cron (data/lease_cron.xml). Searches active leases with `end_date < today`, sets expired via context flag `cron_expire`.
- [x] CHK003 - ✅ RESOLVED — Event payload is `{sale_id: int, sale: recordset}`, emitted synchronously via `_emit_sync`. Documented in code; spec can reference as-is.
- [x] CHK004 - ✅ RESOLVED — All 3 controllers use consistent defaults: `page_size=20`, `max=100` via `min(int(page_size), 100)`.
- [ ] CHK005 - ⚠️ **SPEC GAP** — Event emission runs inside the same transaction. Observer failures are silently swallowed (fire-and-forget for non-`before_` events). If `event_bus.emit()` itself raises, the entire sale creation rolls back. **Action: document "fire-and-forget" behavior in spec.**
- [x] CHK006 - ℹ️ ACCEPTABLE — No bulk endpoints exist. Consistent with CRUD-first approach; can be added later.
- [ ] CHK007 - ⚠️ **SPEC GAP** — Only lease renewals have dedicated audit trail (`renewal_history`). Tenant archive stores `deactivation_date`/`reason` on the record. Sale cancellation stores `cancellation_date`/`reason` on the record. No general-purpose audit log model. **Action: document that audit is limited to in-record fields + renewal history.**
- [x] CHK008 - ✅ RESOLVED — Computed name: `"{Property} - {Tenant} ({start_date})"`, fallback `"New Lease"`. Stored computed field.
- [x] CHK009 - ✅ RESOLVED — `action_cancel()` now guards property revert: only sets `state='new'` if `property_id.state == 'sold'`. Skips revert if property state was changed after sale creation.
- [ ] CHK010 - ⚠️ **SPEC GAP** — Tenant archive (`DELETE`) performs soft-delete **without checking for active leases**. No warning, no guard. Spec edge case mentions warning but no endpoint implements it. **Action: add active-lease check or remove warning from spec.**

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
- [ ] CHK019 - ⚠️ **SPEC GAP** — Sale has **no DELETE endpoint** (only `POST /cancel`). Tenant and Lease have `DELETE` (soft-archive). Sale uses cancel semantics instead of archive. `active` field exists but no archive endpoint. **Action: add `DELETE /sales/<id>` for archive, or document cancel-only as intentional.**
- [x] CHK020 - ✅ RESOLVED — All controllers include status-aware action links: lease has `renew`/`terminate` (when active), sale has `cancel` (when not cancelled), tenant has `leases` sub-resource link.
- [ ] CHK021 - ⚠️ **SPEC GAP** — Integration test `test_us8_s5_soft_delete.sh` tests **only tenants**. No lease or sale soft-delete/reactivation integration tests. **Action: extend S5 test to cover all 3 entities.**

## Acceptance Criteria Quality

- [x] CHK022 - ✅ RESOLVED — Added `test_us8_s6_isolation_rbac.sh` with cross-company negative tests: Manager creates tenant → User B login → GET/LIST/UPDATE tenant → expects 404/403 (data isolation). Gracefully skips when User B not provisioned.
- [x] CHK023 - ✅ RESOLVED — Unit tests cover all schema constraints, model `@api.constrains`, and validator lambdas across 4 test files (130 tests total).
- [x] CHK024 - ✅ RESOLVED — Added `VALID_TRANSITIONS` state machine in `lease.py` `write()` override: `draft→[active], active→[terminated], terminated→[], expired→[]`. Context flags `cron_expire` and `lease_terminate` allow controlled bypass. 10 unit tests validate all transitions.
- [x] CHK025 - ✅ RESOLVED (implicitly) — Archived properties (`active=False`) are excluded by Odoo's default `active_test`, so `prop.exists()` returns False → sale creation fails with "Property not found".

## Scenario Coverage

- [ ] CHK026 - ⚠️ **SPEC GAP** — Concurrent lease check is ORM-level `@api.constrains` (read-then-check). No `SELECT FOR UPDATE`, no advisory lock. Two simultaneous requests could pass the check before either commits. **Action: document as known limitation or add DB-level locking.**
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

- [ ] CHK035 - ⚠️ **SPEC GAP** — No rate limiting on CRUD endpoints. A `rate_limit_exceeded` helper exists in `error_handler.py` (returns 429) but is **never called** from feature 008 controllers. **Action: define rate limit thresholds or note as deferred.**
- [x] CHK036 - ℹ️ ACCEPTABLE — Odoo WSGI `limit_request` (default 8192) covers payload limits. No custom validation needed for JSON payloads.
- [ ] CHK037 - ⚠️ **SPEC GAP** — Only global SC-006 (<2s). No per-endpoint thresholds. List endpoints with large datasets may need different targets. **Action: add per-endpoint SLAs or note global threshold as sufficient.**
- [x] CHK038 - ✅ RESOLVED — All 3 controllers use `_logger.error(exc_info=True)` on catch blocks and `_logger.warning` for validation errors. EventBus uses `_logger.debug`. Structured logging in place.
- [ ] CHK039 - ⚠️ **SPEC GAP** — All error messages are hardcoded English. `_()` i18n function only in `schema.py`, not in controllers. Headless API typically uses English errors, but spec should clarify given Portuguese user base. **Action: decide on i18n policy for API errors.**

## Security Requirements

- [x] CHK040 - ✅ RESOLVED — Company isolation violations consistently return **404** (not 403) across all 3 controllers. Prevents information leakage (can't distinguish "not found" vs "not yours").
- [ ] CHK041 - ⚠️ **SPEC GAP** — `_serialize_sale` **always** returns `buyer_phone`/`buyer_email` regardless of role. Agents, managers, and owners see identical fields. **Action: define field visibility policy by role or document full exposure as acceptable.**
- [x] CHK042 - ℹ️ ACCEPTABLE — No HTML rendering in REST API → no XSS risk. Odoo ORM uses parameterized queries → no SQLi risk. `.strip()` applied to key string fields. Adequate for headless API.

## Dependencies & Assumptions

- [x] CHK043 - ✅ RESOLVED — `quicksol.event.bus` exists, is fully implemented, imported, tested (in `tests/observers/`), and used by sale, property, and auth modules.
- [x] CHK044 - ✅ RESOLVED — Spec explicitly justifies in two places: "shared email (e.g., a household) is acceptable". Code matches — no `_sql_constraints` on email, only format validation.
- [ ] CHK045 - ⚠️ **SPEC GAP** — Redis and PostgreSQL are documented only in `plan.md`, not in `spec.md` Dependencies section. **Action: add infrastructure requirements reference to spec or cross-link to plan.**

---

## Triage Summary

| Verdict | Count | Items |
|---------|-------|-------|
| ✅ RESOLVED | 23 | CHK002-004, 006, 008-009, 011-018, 020, 022-025, 027, 029-032, 034, 036, 038, 040, 042-044 |
| ⚠️ SPEC GAP | 14 | CHK001, 005, 007, 010, 019, 021, 026, 035, 037, 039, 041, 045 |
| ℹ️ ACCEPTABLE | 8 | CHK006, 011, 012, 016, 017, 028, 033, 034, 036 |

### Critical Gaps — ALL RESOLVED ✅

| # | Gap | Resolution |
|---|-----|-----------|
| CHK002 | No `expired` status transition | ✅ Added `_cron_expire_leases()` daily cron + `data/lease_cron.xml` |
| CHK009/031 | Sale cancel reverts property blindly | ✅ Added guard: only revert if `property_id.state == 'sold'` |
| CHK022 | No cross-company isolation tests | ✅ Added `test_us8_s6_isolation_rbac.sh` Part 1 (cross-company negative tests) |
| CHK024 | No state machine validation | ✅ Added `VALID_TRANSITIONS` in `write()` override + 10 unit tests |
| CHK027 | No agent-scoped integration tests | ✅ Added `test_us8_s6_isolation_rbac.sh` Part 2 (agent RBAC tests) |

### Low Priority (document in spec, address later)

| # | Gap | Notes |
|---|-----|-------|
| CHK001 | Dual error response format | Cosmetic; both work. Unify in future refactor |
| CHK005 | Event failure behavior | Already fire-and-forget; just document it |
| CHK007 | Limited audit beyond renewals | In-record fields adequate for MVP |
| CHK035 | No rate limiting | Deferred; not in MVP scope |
| CHK039 | English-only error messages | Standard for headless API |
