# Feature Specification: Company Isolation for Lead List/Export/Statistics/Activity Endpoints

**Feature Branch**: `024-leads-company-isolation`
**Created**: 2026-07-09
**Status**: Draft
**ADR References**: ADR-004 (naming), ADR-007 (HATEOAS), ADR-008 (API security multi-tenancy — 5 mandatory principles), ADR-009 (headless auth user context), ADR-011 (dual/triple auth decorator chain), ADR-015 (soft delete), ADR-017 (session hijacking prevention), ADR-018 (input validation), ADR-019 (RBAC/multi-tenancy profiles), ADR-022 (linting/static analysis)

---

## Executive Summary

`GET /api/v1/leads`, `GET /api/v1/leads/export`, and `GET /api/v1/leads/statistics` are fully authenticated (`@require_jwt` + `@require_session` + `@require_company`), but the controller body queries `real.estate.lead` via `.sudo()` with an ORM domain that never restricts by `company_id`, which silently bypasses the `ir.rule` record rules (`rule_agent_own_leads`, `rule_manager_all_company_leads`, `rule_owner_all_company_leads`) intended to enforce that isolation. This directly violates ADR-008 Principle #1 ("NUNCA usar `.sudo()` em queries de dados transacionais" / "SEMPRE aplicar filtro de empresa no domínio da query"). Three sibling activity endpoints (`log_activity`, `list_activities`, `schedule_activity`) additionally lack the `@require_company` decorator entirely, despite a code comment claiming it is present. This feature makes company/agent scoping explicit and verifiable in all six endpoints, closes the isolation gap, and adds the missing database index needed to keep the now-mandatory `company_id` filter performant at scale.

---

## Verified Current State (code-grounded, not assumption)

| File | Endpoint | Auth chain present? | Company filter in domain? | `.sudo()` used? |
|------|----------|---------------------|---------------------------|------------------|
| `controllers/lead_api.py::list_leads` | `GET /api/v1/leads` | Yes (`@require_jwt`, `@require_session`, `@require_company`) | **No** | Yes |
| `controllers/lead_api.py::export_leads_csv` | `GET /api/v1/leads/export` | Yes | **No** | Yes |
| `controllers/lead_api.py::lead_statistics` | `GET /api/v1/leads/statistics` | Yes | **No** | Yes |
| `controllers/lead_api.py::log_activity` | `POST /api/v1/leads/<id>/activities` | `@require_jwt` + `@require_session` only — **`@require_company` missing** | N/A (single-record) | Yes |
| `controllers/lead_api.py::list_activities` | `GET /api/v1/leads/<id>/activities` | Same gap | N/A (single-record) | Yes |
| `controllers/lead_api.py::schedule_activity` | `POST /api/v1/leads/<id>/schedule-activity` | Same gap | N/A (single-record) | Yes |

This corrects the stale claim in `CLAUDE.md` §12 discrepancy #6 that `GET /api/v1/leads` is `auth='none'` with no decorators — that premise is outdated for this endpoint. `knowledge_base/security.md` and `knowledge_base/api-surface.md` should be corrected as a documentation follow-up (see Constitution Feedback below), not treated as a code change in this spec.

`security/record_rules.xml` already defines the intended isolation rules for `real.estate.lead`:
- `rule_agent_own_leads`: `[('agent_id.user_id', '=', user.id)]` (group `group_real_estate_agent`)
- `rule_manager_all_company_leads`: `[('company_id', 'in', company_ids)]` (group `group_real_estate_manager`)
- `rule_owner_all_company_leads`: `[('company_id', 'in', company_ids)]` (group `group_real_estate_owner`)

These rules are correct but **inert** on the affected endpoints because `.sudo()` skips `ir.rule` evaluation entirely (confirmed: `env.user.has_group()`-gated rules only apply to a non-superuser environment).

`thedevkitchen_apigateway/middleware.py::require_company` (lines 362-417) already computes, before the controller body runs:
- `request.company_domain` — `[]` for `base.group_system` (admin, unrestricted), else `[('company_id', 'in', re_companies.ids)]`.
- `request.user_company_ids` — `[]` for admin, else the list of the user's real-estate company ids.
- Returns `403 no_company` before the controller runs if a non-admin user has zero real-estate companies (`re_companies` empty).

This feature's design principle is to **consume** `request.company_domain` / `request.user_company_ids` as the single source of truth in the controller, rather than re-deriving company scoping locally (avoiding the divergent pattern already present in `sale_api.py`'s own `_get_company_ids()` helper).

`models/lead.py`: `company_id` (line 144) is a required `Many2one` to `res.company` with **no `index=True`** (contrast with `agent_id`, line 133-142, which does have `index=True`). The model's own `init()` hook (lines 17-62) hand-creates indexes for `state`, `create_date`, `(state, agent_id)` composite, `(budget_min, budget_max)`, and `location_preference` — but not `company_id`.

---

## User Scenarios & Testing

### User Story 1: Manager/Owner sees only their own company's leads (Priority: P1) 🎯 MVP

**As a** Manager or Owner (per ADR-019 RBAC profiles)
**I want to** call `GET /api/v1/leads` and only receive leads belonging to a company I'm a member of
**So that** lead data from a different real-estate agency (tenant) sharing the same Odoo instance is never exposed to me

**Acceptance Criteria**:
- [ ] Given a Manager in Company A and leads existing in both Company A and Company B, when they call `GET /api/v1/leads`, then only Company A's leads are returned (Company B's leads never appear, not even with a matching filter/search term).
- [ ] Given the same scenario for `GET /api/v1/leads/export` (CSV) and `GET /api/v1/leads/statistics`, then the same isolation holds for the exported rows and the aggregated counts/`by_agent`/`by_status`/`conversion_rate` figures.
- [ ] Given an Owner instead of a Manager, then the same isolation and acceptance criteria apply identically (both roles use `company_ids`-scoped rules).
- [ ] Given a `base.group_system` (admin) caller, when they call any of the three endpoints, then no company restriction is applied (matches existing `@require_company` admin-bypass semantics — no regression for admin cross-company back-office use).
- [ ] Given invalid/absent company resolution (user has zero real-estate companies), when calling any of these endpoints, then the existing `require_company` `403 no_company` behavior is unchanged (this feature does not touch that path).

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_lead_domain_includes_company_filter()` | Verifies the domain passed to `search()`/`search_count()` includes `request.company_domain` | ⚠️ Required |
| Integration (curl, per `integration_tests/*.sh` convention) | `test_manager_cannot_see_other_company_leads()` | Manager in Company A calling `GET /api/v1/leads` never sees Company B leads created via seed data | ⚠️ Required |
| Integration | `test_owner_cannot_see_other_company_leads()` | Same as above for Owner role | ⚠️ Required |
| Integration | `test_export_csv_company_isolation()` | CSV export rows scoped to caller's company only | ⚠️ Required |
| Integration | `test_statistics_company_isolation()` | `total`/`by_status`/`by_agent`/`conversion_rate` reflect only caller's company's leads | ⚠️ Required |
| Integration | `test_admin_sees_all_companies_leads()` | `base.group_system` user still sees cross-company data (no regression) | ⚠️ Required |
| Integration | `test_multitenancy_isolation()` | General cross-company isolation regression test per ADR-008 | ⚠️ Required |

### User Story 2: Agent only sees their own assigned leads, scoped within their company (Priority: P1) 🎯 MVP

**As an** Agent (per ADR-019, `group_real_estate_agent` without `group_real_estate_manager`/`group_real_estate_owner`)
**I want to** call `GET /api/v1/leads` (and export/statistics) and only receive leads where `agent_id.user_id` is me
**So that** I cannot browse, export, or infer aggregate statistics about leads assigned to other agents, in my own company or any other

**Acceptance Criteria**:
- [ ] Given an Agent with leads assigned to them and other leads (same company) assigned to a different agent, when they call `GET /api/v1/leads`, then only their own leads are returned.
- [ ] Given the same scenario for `GET /api/v1/leads/export` and `GET /api/v1/leads/statistics`, then the same agent-level restriction applies (statistics reflect only the agent's own leads, not the whole company's).
- [ ] Given a Manager or Owner (not purely an Agent), the agent-only restriction does **not** apply — they retain full company-wide visibility per Story 1.
- [ ] Given the existing `agent_id` query parameter (managers filtering by a specific agent), this parameter's existing manager-only guard (`user.has_group('quicksol_estate.group_real_estate_manager')`) is preserved unchanged; it must still be combined with (not replace) the company/agent domain restriction.

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_is_agent_role_helper()` | Validates the new `_is_agent_role()` helper correctly classifies Agent vs. Manager/Owner/Admin combinations | ⚠️ Required |
| Integration | `test_agent_sees_only_own_leads_in_list()` | Agent A does not see Agent B's leads within the same company via `GET /api/v1/leads` | ⚠️ Required |
| Integration | `test_agent_sees_only_own_leads_in_export()` | Same, for CSV export | ⚠️ Required |
| Integration | `test_agent_sees_only_own_leads_in_statistics()` | Same, for statistics endpoint | ⚠️ Required |
| Integration | `test_manager_agent_id_filter_still_works()` | Regression: manager filtering list by `agent_id` query param still functions correctly alongside the new domain logic | ⚠️ Required |

### User Story 3: Company-scoped access on single-lead activity endpoints (Priority: P2)

**As an** Agent, Manager, or Owner
**I want to** be blocked from logging activities, listing activities, or scheduling activities on a lead that does not belong to any of my companies
**So that** cross-tenant data leakage/write access is not possible through the activity sub-resources, closing the same class of bug found in the list endpoints

**Acceptance Criteria**:
- [ ] Given a lead belonging to Company B, when a user whose `company_ids` only include Company A calls `POST /api/v1/leads/<id>/activities` (log_activity), then a `403 ACCESS_DENIED` is returned and no chatter message is posted.
- [ ] Given the same cross-company scenario for `GET /api/v1/leads/<id>/activities` (list_activities), then `403 ACCESS_DENIED` is returned and no activity data leaks in the response body.
- [ ] Given the same cross-company scenario for `POST /api/v1/leads/<id>/schedule-activity` (schedule_activity), then `403 ACCESS_DENIED` is returned and no `mail.activity` record is created.
- [ ] Given a `base.group_system` (admin) caller (`request.user_company_ids == []`), the check is bypassed entirely (consistent with `require_company`'s own admin semantics) — no regression for back-office admin use.
- [ ] Given a lead within the caller's own company, all three endpoints behave exactly as before this change (no regression to the pre-existing, unrelated agent-ownership check that compares `lead.agent_id.id` to `current_user.id` — see Out-of-Scope Follow-ups).

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_activity_endpoints_have_require_company_decorator()` | Static/introspection check that all three routes carry `@require_company` in their decorator chain | ⚠️ Required |
| Integration | `test_log_activity_blocks_other_company_lead()` | Cross-company 403 on log_activity | ⚠️ Required |
| Integration | `test_list_activities_blocks_other_company_lead()` | Cross-company 403 on list_activities | ⚠️ Required |
| Integration | `test_schedule_activity_blocks_other_company_lead()` | Cross-company 403 on schedule_activity | ⚠️ Required |
| Integration | `test_admin_bypasses_company_check_on_activity_endpoints()` | Admin unaffected | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Company-scoped list/export/statistics domain**
- FR1.1: `list_leads`, `export_leads_csv`, and `lead_statistics` MUST append `request.company_domain` (as computed by `@require_company`) to the ORM domain passed to `.search()` / `.search_count()` / `.read_group()`, before any other filter parameter is applied, and as part of the same query (not a post-fetch filter in Python).
- FR1.2: The misleading comment `# Query leads (record rules auto-filter by agent/company)` in `list_leads` MUST be removed/corrected, since the domain now performs this restriction explicitly rather than relying on record rules under `.sudo()`.
- FR1.3: `.sudo()` usage is retained in these three endpoints (removing it is a larger change — see Out-of-Scope); the explicit domain filter is the enforcement mechanism, not `ir.rule`.

**FR2: Agent-role restriction on list/export/statistics**
- FR2.1: A new private helper `_is_agent_role(self, user)` on `LeadApiController` MUST return `True` only when the user has `group_real_estate_agent` and does **not** have `group_real_estate_manager`, `group_real_estate_owner`, or `base.group_system`.
- FR2.2: When `_is_agent_role(user)` is `True`, the domain for `list_leads`, `export_leads_csv`, and `lead_statistics` MUST additionally restrict to `('agent_id.user_id', '=', user.id)`.
- FR2.3: The existing manager-only `agent_id` query-parameter filter (managers filtering by a specific agent) MUST continue to function unchanged, combined with (not instead of) FR1.1/FR2.2.

**FR3: Company enforcement on single-lead activity endpoints**
- FR3.1: `log_activity`, `list_activities`, and `schedule_activity` MUST add `@require_company` to their existing decorator chain (after `@require_session`, matching the convention used by every other route in this controller).
- FR3.2: Immediately after the lead is loaded and its existence confirmed (`lead.exists()` check), each of these three endpoints MUST perform an explicit check: if `request.user_company_ids` is non-empty and `lead.company_id.id` is not in `request.user_company_ids`, return `403 ACCESS_DENIED` before any further processing (message posting, activity creation, or activity listing).
- FR3.3: The false comment `# Note: Company isolation is handled by @require_company decorator` MUST be replaced with the real check described in FR3.2 (or removed if redundant with the code now present).
- FR3.4: An empty `request.user_company_ids` (i.e., `base.group_system` admin) MUST bypass this check entirely, consistent with `require_company`'s own admin semantics.

**FR4: Database indexing for company-scoped queries**
- FR4.1: `real.estate.lead.company_id` MUST be declared with `index=True` on the field definition (mirroring `agent_id`).
- FR4.2: A composite index on `(company_id, state)` MUST be added via the model's existing `init()` hook (alongside the pre-existing `state`, `create_date`, `(state, agent_id)`, `(budget_min, budget_max)`, and `location_preference` indexes), since `company_id` is now present in virtually every list/export/statistics query domain, frequently combined with a `state` filter.

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

No new entity is introduced. This feature modifies the existing entity below.

**Entity: Lead (existing, modified)**
- **Model Name**: `real.estate.lead` (pre-existing; this model predates ADR-004's `thedevkitchen_` prefix and is part of the documented legacy exception for `quicksol_estate`, per `CLAUDE.md` §12 discrepancy #5 — not changed by this feature)
- **Table Name**: `real_estate_lead`

| Field | Type | Constraints (current → change) | Description |
|-------|------|-----|-------------|
| `company_id` | Many2one → `res.company` | required, `index=False` → **`index=True`** (this feature) | Multi-tenancy company (ADR-008) |
| `agent_id` | Many2one → `real.estate.agent` | required, `index=True` (unchanged) | Assigned agent (owner of lead) |
| `state` | Selection | required (unchanged) | Pipeline stage |

**Index changes** (via model `init()`, ADR-004/knowledge_base/09-database-best-practices.md pattern already used in this file):
```python
# Field definition change
company_id = fields.Many2one(
    "res.company",
    string="Company",
    required=True,
    tracking=True,
    index=True,  # NEW — added by this feature
    ondelete="restrict",
    default=lambda self: self._default_company_id(),
    help="Company this lead belongs to (multi-tenancy)",
)
```
```sql
-- Added to init(), alongside existing indexes
CREATE INDEX IF NOT EXISTS real_estate_lead_company_state_idx
ON real_estate_lead (company_id, state);
```

**Record Rules** (no change — already correct, per ADR-019; this feature makes them *effective* by removing the `.sudo()`-without-domain gap that was rendering them inert on these six endpoints):
- `rule_agent_own_leads`, `rule_manager_all_company_leads`, `rule_owner_all_company_leads` in `security/record_rules.xml` are unchanged.

### API Endpoints (per ADR-007, ADR-009, ADR-011)

No new endpoints, no new request/response schema fields. All six endpoints below keep their existing route signatures, methods, and response shapes; the change is confined to server-side domain/authorization logic.

**Endpoint: GET /api/v1/leads** (modified — internal logic only)

| Attribute | Value |
|-----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/leads` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` (unchanged, ADR-011) |
| **Authorization** | Manager/Owner: all leads in `company_ids`. Agent: only `agent_id.user_id == self`, within `company_ids`. Admin (`base.group_system`): unrestricted (ADR-019) |
| **Change** | Domain now includes `request.company_domain` and, for agents, `('agent_id.user_id', '=', user.id)` |

**Endpoint: GET /api/v1/leads/export** — same authorization semantics as above, CSV response format unchanged.

**Endpoint: GET /api/v1/leads/statistics** — same authorization semantics as above; pre-existing manager/owner-only gate (`403` for non-manager/owner roles) is unchanged and unaffected by the new company/agent domain restriction (agents already cannot reach this endpoint at all due to that pre-existing gate — the FR2 agent-domain logic is documented for completeness/defense-in-depth but has no observable effect on this specific endpoint today).

**Endpoint: POST /api/v1/leads/<id>/activities** (log_activity) — response unchanged; new failure mode:

| Code | Condition | Response |
|------|-----------|----------|
| 403 | Lead's `company_id` not in caller's `user_company_ids` (new, FR3.2) | `{"error": "ACCESS_DENIED", "message": "Access denied"}` |

**Endpoint: GET /api/v1/leads/<id>/activities** (list_activities) — same new 403 failure mode as above.

**Endpoint: POST /api/v1/leads/<id>/schedule-activity** (schedule_activity) — same new 403 failure mode as above.

### Seed Data (MANDATORY — all solution types)

**Seed: Companies**
```python
seed_company_a = env['res.company'].create({'name': 'Imobiliária A (Seed)', 'is_real_estate': True})
seed_company_b = env['res.company'].create({'name': 'Imobiliária B (Seed)', 'is_real_estate': True})
```

**Seed: Users per role, split across both companies**
```python
seed_users = {
    'seed_manager_a':  {'login': 'seed_manager_a@test.com',  'company': seed_company_a, 'group': 'group_real_estate_manager'},
    'seed_owner_a':    {'login': 'seed_owner_a@test.com',    'company': seed_company_a, 'group': 'group_real_estate_owner'},
    'seed_agent_a1':   {'login': 'seed_agent_a1@test.com',   'company': seed_company_a, 'group': 'group_real_estate_agent'},
    'seed_agent_a2':   {'login': 'seed_agent_a2@test.com',   'company': seed_company_a, 'group': 'group_real_estate_agent'},
    'seed_manager_b':  {'login': 'seed_manager_b@test.com',  'company': seed_company_b, 'group': 'group_real_estate_manager'},
    'seed_agent_b1':   {'login': 'seed_agent_b1@test.com',   'company': seed_company_b, 'group': 'group_real_estate_agent'},
}
```

**Seed: Agents (real.estate.agent) linked to the seed users above**
```python
seed_agent_a1 = env['real.estate.agent'].create({
    'name': 'Seed Agent A1', 'user_id': seed_users['seed_agent_a1'].id, 'company_id': seed_company_a.id,
})
seed_agent_a2 = env['real.estate.agent'].create({
    'name': 'Seed Agent A2', 'user_id': seed_users['seed_agent_a2'].id, 'company_id': seed_company_a.id,
})
seed_agent_b1 = env['real.estate.agent'].create({
    'name': 'Seed Agent B1', 'user_id': seed_users['seed_agent_b1'].id, 'company_id': seed_company_b.id,
})
```

**Seed: Leads — minimum dataset to exercise every user journey above**
```python
# Company A, agent A1's own leads (2) — for agent-isolation assertions
seed_lead_a1_1 = env['real.estate.lead'].create({'name': 'Seed Lead A1-1', 'agent_id': seed_agent_a1.id, 'company_id': seed_company_a.id, 'state': 'new'})
seed_lead_a1_2 = env['real.estate.lead'].create({'name': 'Seed Lead A1-2', 'agent_id': seed_agent_a1.id, 'company_id': seed_company_a.id, 'state': 'qualified'})
# Company A, agent A2's own lead (1) — must NOT be visible to agent A1
seed_lead_a2_1 = env['real.estate.lead'].create({'name': 'Seed Lead A2-1', 'agent_id': seed_agent_a2.id, 'company_id': seed_company_a.id, 'state': 'new'})
# Company B, agent B1's lead (1) — must NOT be visible to any Company A user, including managers/owners
seed_lead_b1_1 = env['real.estate.lead'].create({'name': 'Seed Lead B1-1', 'agent_id': seed_agent_b1.id, 'company_id': seed_company_b.id, 'state': 'new'})
```

> **Rules**: `seed_` prefix on all IDs/logins/names; idempotent (guard creation with `search()` on unique fields before `create()` in the actual seed script); every integration test in this spec starts from this dataset without additional setup.

---

### Non-Functional Requirements

**NFR1: Security** (per ADR-008, ADR-011, ADR-017, ADR-019)
- All six endpoints require the full triple-decorator chain (`@require_jwt` + `@require_session` + `@require_company`) — this feature adds the missing `@require_company` to `log_activity`/`list_activities`/`schedule_activity` (FR3.1).
- ADR-008 Principle #1 ("never `.sudo()` without an explicit company filter in the domain") is satisfied by pairing the retained `.sudo()` calls with an explicit `request.company_domain` restriction (FR1.1) rather than by removing `.sudo()` (which is a larger, separately-tracked change — see Out-of-Scope Follow-ups).
- ADR-008 Principle #5 ("generic responses, no enumeration") is preserved for the activity endpoints: the new check returns `403 ACCESS_DENIED` (an existing error shape already used elsewhere in this controller), not a distinguishing message that reveals whether the lead exists in another company.
- RBAC enforcement (Manager/Owner: company-wide; Agent: own-leads-only) is now enforced at the query layer, matching ADR-019 intent, rather than relying on inert `ir.rule` record rules under `.sudo()`.

**NFR2: Performance** (per `knowledge_base/performance.md`, feature-specific analysis)
- **Indexing**: `company_id` on `real.estate.lead` currently has **no index** (verified: `models/lead.py:144`, contrast with `agent_id` at line 138 which has `index=True`). Since this feature makes `('company_id', 'in', re_companies.ids)` (or `('company_id', '=', ...)` for single-company tenants) a **mandatory** clause in the domain of every list/export/statistics query, this is a real, not hypothetical, hot-path change. FR4.1 adds `index=True` to the field; FR4.2 adds a composite `(company_id, state)` index via the existing `init()` hook, since the most common query pattern in this controller combines a company restriction with a `state` filter (`state_filter` query param) or a `state` group-by (`lead_statistics`'s per-status counts). The existing `(state, agent_id)` composite index remains useful for the agent-role restriction (FR2.2) combined with state filtering.
- **N+1 query risk**: `list_leads`'s per-row serialization (`_serialize_lead`-equivalent inline block, lines 208-247) accesses `lead.agent_id.name`, `lead.property_type_interest.name` per lead in a Python loop. Odoo's ORM prefetch mechanism batches these Many2one reads across the recordset returned by a single `search()` call (not per-record queries), so this is **not a new N+1 risk introduced by this feature** — it is pre-existing, acceptable behavior unchanged by adding a domain clause. No mitigation is required as part of this feature; flagged here only for completeness of the performance analysis, not as an action item.
- `lead_statistics`'s `last_activity_before` code path (not modified by this feature, but sharing the same domain) issues one `mail.message` search **per lead** in a Python loop (lines 160-193) — this is a genuine, pre-existing N+1 pattern, but it is out of scope for this feature (no query parameters or logic in that branch are touched here); flagged as a follow-up (see Out-of-Scope Follow-ups) since adding the company filter narrows, but does not eliminate, the row count driving that loop.
- **Caching**: These are per-request, per-user, filter-parameterized list/aggregate reads (arbitrary combinations of `state`, `search`, `budget_min/max`, `bedrooms`, `location`, `created_from/to`, `sort_by/order`, `limit/offset`). This does not fit the existing Redis cache-aside pattern used for JWT/session validation (`thedevkitchen_apigateway/services/redis_client.py`), which caches a single deterministic key (token → payload). Caching arbitrary filtered list results would require a cache key encoding the full query-parameter set plus `company_id`/`agent_id` scope and an invalidation strategy tied to lead writes — assessed as **not a cache candidate** for this feature; the correct performance lever here is the index added in FR4, not caching.
- **Async/Celery offload**: None of the six endpoints in this feature perform slow, offloadable work — `list_leads`/`export_leads_csv`/`lead_statistics` are synchronous read queries (bounded by `limit`, max 100 per FR-established convention), and `log_activity`/`schedule_activity` are single-row writes (`message_post`, `mail.activity.create`). None warrant moving to `commission_events`/`audit_events`/`notification_events` or a new queue; assessed as **not applicable**.
- List pagination: unchanged, existing `limit` (max 100) / `offset` behavior preserved as-is.
- API response time target: < 200ms for `GET /api/v1/leads` under the new indexed domain, for a single-company dataset up to ~50k leads (typical B2B SaaS tenant scale per `knowledge_base/multi-tenancy.md`).

**NFR3: Quality** (per ADR-022)
- Code must pass `black`, `isort`, `flake8` (`cd 18.0 && ./lint.sh quicksol_estate`).
- Pylint score ≥ 8.0/10.
- 100% test coverage on the new domain-construction logic and the new `_is_agent_role()` helper (ADR-003).

**NFR4: Data Integrity** (per knowledge_base/09-database-best-practices.md)
- No schema/constraint change beyond the two index additions (FR4); these are additive, non-destructive migrations (`CREATE INDEX IF NOT EXISTS`, matching the existing pattern already used in this same `init()` method) and require no data backfill.
- Soft delete (`active` field, ADR-015) behavior on `real.estate.lead` is unchanged by this feature.

**NFR5: Frontend Compatibility**
- Not applicable. This feature is entirely server-side/API-only logic on existing headless endpoints; no Odoo views, menus, or forms are touched (confirms the "Access Model" constraint: none of the six affected endpoints are part of the admin-only Odoo UI surface).

---

## Technical Constraints

### Must Follow (from ADRs & Knowledge Base)

| Source | Requirement | Applied To |
|--------|-------------|------------|
| ADR-008 §1 | Never `.sudo()` without an explicit company filter in the domain | `list_leads`, `export_leads_csv`, `lead_statistics` domains |
| ADR-008 §5 | Generic 403/404, no enumeration of cross-tenant existence | Activity endpoints' new 403 check |
| ADR-011 | Full `@require_jwt` + `@require_session` + `@require_company` chain | `log_activity`, `list_activities`, `schedule_activity` |
| ADR-019 | RBAC: Manager/Owner company-wide, Agent own-record-only | `_is_agent_role()` helper and domain construction |
| ADR-004 | `real.estate.lead` naming is a documented pre-existing exception, not extended or altered here | Data Model section |
| ADR-003 | 100% test coverage on new validations/authorization logic | All new test cases listed above |
| ADR-022 | Linting standards | All modified Python code |
| Arch | Odoo UI accessible only by `admin`; these are all headless API endpoints, no Odoo UI/menu/view changes | Entire feature |

### Architecture Patterns

- **Controller Pattern**: Reuse `request.company_domain` / `request.user_company_ids` (already computed by `@require_company`) as the single source of truth, per this design's stated principle — do not reimplement company-id derivation locally (avoids the divergence already present between this controller and `sale_api.py`'s separate `_get_company_ids()` helper).
- **Testing Pattern**: Curl-based `integration_tests/*.sh` convention (this project deliberately avoids Odoo `HttpCase` due to its read-only-transaction limitation, per `knowledge_base/testing.md`).

---

## Out-of-Scope Follow-ups (explicitly called out, not silently deferred)

These are real, verified gaps discovered during investigation of this same controller. They are **not fixed by this spec** because they are larger and/or riskier changes than the scope above, but they must not be lost — each is a candidate for its own future spec:

1. **`get_lead` / `update_lead` / `delete_lead` / `convert_lead` / `reopen_lead` have a no-op company/record-rule check.** These five single-record endpoints call `lead.check_access_rights(...)` / `lead.check_access_rule(...)` after `Lead.sudo().browse(lead_id)` — but `check_access_rule()` is a **no-op under the superuser environment produced by `.sudo()`**, so despite looking like an authorization check, it currently grants access unconditionally regardless of company or agent ownership. This is the single-record counterpart of the exact bug this spec fixes for list/export/statistics, and is arguably higher severity (it affects write/delete operations, not just reads) — but fixing it safely requires a broader design (e.g., deciding whether to drop `.sudo()` entirely for these five endpoints and rely on real record rules, vs. adding the same explicit `company_id` check pattern used in FR3.2). Tracked as a required follow-up spec, not addressed here.
2. **Agent-ownership check bug in `log_activity`/`list_activities`/`schedule_activity`.** The existing code compares `lead.agent_id.id != current_user.id` — but `lead.agent_id` is a `real.estate.agent` record and `current_user` is a `res.users` record; these ids belong to different models and will essentially never match by coincidence for correctly-configured data, meaning the "agent can only act on their own leads" check on these three endpoints is likely already broken independent of company isolation. This spec adds the company-level 403 (FR3.2) without touching or fixing this pre-existing, unrelated correctness bug — flagged for a separate fix.
3. **`lead_statistics`'s `last_activity_before` N+1 loop** (see NFR2) — narrowed by the new company filter but not eliminated; a proper fix (e.g., a single `mail.message` aggregate query instead of a per-lead search) is out of scope here.
4. **Documentation corrections** — `knowledge_base/security.md`, `knowledge_base/api-surface.md`, and `CLAUDE.md` §12 discrepancy #6 should be updated to remove the stale claim that `GET /api/v1/leads` is `auth='none'`/undecorated. This is a documentation-only follow-up, not a code change, and is recommended to run through the `thedevkitchen-speckit-project-knowledge-base` subagent rather than being hand-edited as part of this feature's implementation.

---

## Success Criteria

### Backend
- [ ] All three user stories implemented and tested per the tables above
- [ ] 100% unit test coverage on `_is_agent_role()` and the new domain-construction logic (ADR-003)
- [ ] Integration tests (curl-based) prove cross-company isolation on all six endpoints using the seed dataset above
- [ ] Multi-company isolation verified for Manager, Owner, Agent, and Admin roles
- [ ] Code quality: Pylint ≥ 8.0, all linters passing (ADR-022)
- [ ] Security requirements validated against ADR-008's 5 principles (explicit domain filter present; no client-supplied `company_ids` accepted by these read-only endpoints; generic 403 on activity endpoints; no `.sudo()`-only reliance without a domain filter)
- [ ] `company_id` index and `(company_id, state)` composite index present after module upgrade (verify via `\d real_estate_lead` in psql or `pg_indexes`)

### Seeds
- [ ] Seed data file created with `seed_` prefix on all IDs/logins/names, matching the dataset defined above
- [ ] Seed covers Manager, Owner, and two distinct Agents, split across two companies
- [ ] Seed is idempotent (safe to run multiple times)
- [ ] Integration tests use seed records as their starting state (no per-test bespoke fixture creation for the isolation assertions)

### Documentation
- [ ] Constitution feedback analyzed and documented (below)
- [ ] Swagger/OpenAPI: no schema change needed for `list_leads`/`export_leads_csv`/`lead_statistics`/activity endpoints (no new request/response fields introduced) — confirm via `swagger-updater` skill that the existing entries remain accurate after implementation
- [ ] Journey flowcharts created at `specs/024-leads-company-isolation/flowcharts.md` (one per user story, post-implementation)
- [ ] `knowledge_base/security.md`/`api-surface.md`/`CLAUDE.md` stale-endpoint-auth correction tracked as a follow-up (see Out-of-Scope Follow-ups #4)

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| Consume `request.company_domain`/`request.user_company_ids` directly in controllers instead of re-deriving company scoping | Establishes `require_company`'s output as the single source of truth for company-scoped domains, reducing divergence across controllers (e.g., vs. `sale_api.py`'s local `_get_company_ids()`) | `.specify/memory/constitution.md` — API/controller pattern section | High |
| Explicit domain-based company filter as the enforcement mechanism when `.sudo()` is retained for legacy reasons | A named, reusable pattern for cases where full `.sudo()` removal is out of scope but ADR-008 compliance is still required | `.specify/memory/constitution.md` — Security Requirements | Medium |

### New Entities/Relationships

None — no new entities or relationships are introduced by this feature.

### Architectural Decisions

| Decision | Rationale | ADR Required? |
|----------|-----------|---------------|
| Retain `.sudo()` in `list_leads`/`export_leads_csv`/`lead_statistics`, pairing it with an explicit domain filter, rather than removing `.sudo()` and relying on `ir.rule` | Removing `.sudo()` here is a larger change (affects downstream behavior of these three endpoints in ways not yet fully scoped) than adding a domain filter; tracked as a deliberate, scoped decision | No — consistent with existing ADR-008 guidance, no new ADR needed |
| Add `@require_company` + explicit single-record company check (rather than adding record-rule-based enforcement) to `log_activity`/`list_activities`/`schedule_activity` | Matches the pattern already used successfully elsewhere in this same file for single-record endpoints reached via `.sudo().browse()` | No |

### Constitution Update Recommendation

- **Update Required**: Yes (pattern-level, not principle-level)
- **Suggested Version Bump**: PATCH
- **Sections to Update**:
  - [x] Security Requirements — document the "explicit domain filter alongside retained `.sudo()`" pattern as an accepted interim compliance mechanism for ADR-008 Principle #1
  - [ ] Core Principles
  - [ ] Quality & Testing Standards
  - [ ] Development Workflow
  - [ ] New Section: [name]

---

## Assumptions & Dependencies

**Assumptions**:
- `request.company_domain` and `request.user_company_ids`, as computed by the existing `require_company` middleware, are correct and require no modification themselves — this feature only changes how controllers *consume* them.
- The pre-existing manager-only `agent_id` query-parameter filter in `list_leads`/`export_leads_csv` is intentional, correct behavior and is preserved as-is.
- `lead_statistics`'s existing manager/owner-only gate means Agents cannot reach that endpoint today regardless of this feature; the FR2 agent-domain-restriction language is included for completeness/defense-in-depth, not because it is currently reachable by an agent.

**Dependencies**:
- Existing modules: `quicksol_estate` (controller/model changes), `thedevkitchen_apigateway` (unchanged; only consumed via `request.company_domain`/`request.user_company_ids`)
- Database: PostgreSQL 16 (index additions)
- No new external service or infrastructure dependency

---

## Implementation Phases

### Phase 1: Foundation
- Add `index=True` to `company_id` field on `real.estate.lead` (FR4.1)
- Add `(company_id, state)` composite index to model `init()` (FR4.2)
- Add `_is_agent_role()` helper to `LeadApiController` (FR2.1)
- Unit tests for the helper and index presence

### Phase 2: Controller Logic
- Update `list_leads`, `export_leads_csv`, `lead_statistics` domains (FR1, FR2)
- Add `@require_company` + explicit company check to `log_activity`, `list_activities`, `schedule_activity` (FR3)
- Remove/correct misleading comments (FR1.2, FR3.3)

### Phase 3: Testing & Quality
- Seed data script (per Seed Data section)
- Integration test suite (curl-based) per the User Stories test tables
- Lint/pylint pass (ADR-022)

### Phase 4: Documentation & Artifacts
- Constitution update (PATCH, per Constitution Feedback above)
- Journey flowcharts (`specs/024-leads-company-isolation/flowcharts.md`)
- Follow-up spec stubs for Out-of-Scope items #1-#3 (recommend, do not require, as part of this feature's completion)
- `knowledge_base`/`CLAUDE.md` documentation correction (Out-of-Scope item #4)

---

## Artifacts to Generate

Per this project's mandatory skill usage:
- **`development-best-practices`** skill — consult before implementing the domain/helper changes above.
- **`swagger-updater`** skill — confirm no schema drift after implementation (no new fields expected).
- **`postman-collection-manager`** skill — not required (no new endpoints/request shapes); confirm existing collection entries for these six endpoints remain accurate.

---

## Validation Checklist

### Backend Validation
- [ ] ADR-008 Principle #1 satisfied: explicit domain company filter present alongside retained `.sudo()` on all three list-type endpoints
- [ ] ADR-011 full decorator chain present on all six endpoints (three already had it; three gain `@require_company`)
- [ ] ADR-019 RBAC semantics correctly reflected: Manager/Owner company-wide, Agent own-leads-only, Admin unrestricted
- [ ] Multi-tenancy correctly specified and tested (ADR-008) using the two-company seed dataset
- [ ] Test strategy complete — unit (`_is_agent_role`) + integration (curl, cross-company assertions) per ADR-003
- [ ] Database indexing verified post-migration (`company_id` index, `(company_id, state)` composite index)
- [ ] Error handling unchanged/consistent (existing `403 ACCESS_DENIED` shape reused, no new error codes introduced)
- [ ] Code quality requirements defined (ADR-022)
- [ ] Out-of-scope items explicitly documented, not silently dropped (see Out-of-Scope Follow-ups)

### Frontend Validation
- Not applicable — no Odoo UI/views/menus are touched by this feature (API-only, headless endpoints per the project's Access Model).
