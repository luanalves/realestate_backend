# Design: Company Isolation for Lead Endpoints

**Date:** 2026-07-08
**Status:** Approved (pending implementation plan)
**Area:** `quicksol_estate` module, `controllers/lead_api.py`

## Problem

`GET /api/v1/leads` (`list_leads`) already carries the full auth chain
(`@require_jwt` → `@require_session` → `@require_company`), contrary to what
`knowledge_base/security.md` and `knowledge_base/api-surface.md` currently
document (they incorrectly list it as public/`auth='none'` with no
decorators — item #6 of the project constitution).

The real bug is inside the controller body: the ORM domain never includes a
`company_id` restriction, and the query runs under `.sudo()`, which bypasses
the `ir.rule` record rules (`rule_agent_own_leads`,
`rule_manager_all_company_leads`, `rule_owner_all_company_leads` in
`security/record_rules.xml`) that would otherwise enforce this. A misleading
comment (`# Query leads (record rules auto-filter by agent/company)`)
asserts protection that does not exist. The same `.sudo()`-without-domain
pattern repeats in `export_leads_csv` and `lead_statistics`.

Separately, three activity endpoints (`log_activity`, `list_activities`,
`schedule_activity`) carry a comment claiming "Company isolation is handled
by `@require_company` decorator" — but the decorator is **not actually
applied** to these routes (only `@require_jwt` + `@require_session` are).
This is a second, distinct isolation gap discovered during investigation.

## Goals

- Cross-company data isolation on `list_leads`, `export_leads_csv`,
  `lead_statistics`, `log_activity`, `list_activities`, `schedule_activity`.
- Agent-role isolation (an Agent — not Manager/Owner/Admin — only sees their
  own leads) on the three list/export/statistics endpoints, matching the
  intent of `rule_agent_own_leads`.
- Company filtering must be pushed into the SQL query itself (ORM domain
  passed to `.search()`/`.search_count()`), not applied by fetching rows and
  filtering in Python.
- No change to authentication endpoints' existing behavior for `base.group_system`
  (admin keeps unrestricted cross-company access, matching current
  `@require_company` middleware semantics).

## Non-goals

- `get_lead` / `update_lead` / `delete_lead` / `convert_lead` / `reopen_lead`:
  these call `lead.sudo().check_access_rule("read")`, which is a no-op
  because `check_access_rule` is skipped entirely for the superuser
  environment produced by `.sudo()`. This is a real gap but larger and
  riskier to fix than the current task's scope — tracked as a follow-up
  technical debt item, not fixed here.
- The pre-existing, unrelated bug where the agent-isolation check in
  `log_activity`/`list_activities`/`schedule_activity` compares
  `lead.agent_id.id != current_user.id` (comparing a `real.estate.agent` id
  against a `res.users` id — different models). Documented, not fixed, to
  keep this change focused on company isolation.
- `create_filter` / `list_filters` / `delete_filter`: saved search filters
  are user-scoped, not lead-scoped; out of scope.
- Swagger/OpenAPI sync: `export_leads_csv` and `lead_statistics` are not
  currently documented in swagger, so no swagger update is needed for them.
  `list_leads`'s existing swagger entry does not need a schema change (no
  new query params are introduced).

## Design

### Principle: reuse `@require_company`'s output as the single source of truth

`thedevkitchen_apigateway/middleware.py:362-417`'s `require_company` decorator
already computes, before the controller body runs:

- `request.company_domain` — `[]` for `base.group_system` (unrestricted), or
  `[('company_id', 'in', re_companies.ids)]` for everyone else.
- `request.user_company_ids` — `[]` for admin, or the list of the user's
  real-estate company ids otherwise.
- For any non-admin user with zero real-estate companies, the middleware
  itself already returns `403 no_company` **before** the controller runs —
  this already satisfies "the endpoint must not return data without a
  resolved company."

Controllers should consume `request.company_domain` /
`request.user_company_ids` directly instead of re-deriving company scoping
(avoids the inconsistency where `sale_api.py` reimplements similar logic via
its own `_get_company_ids()` helper).

### 1. List/export/statistics endpoints

Applies to `list_leads`, `export_leads_csv`, `lead_statistics` (all three
already have the full `@require_jwt`/`@require_session`/`@require_company`
chain).

Add, immediately after the domain list is initialized (before other filter
params are appended, so it's part of the same `.search()`/`.search_count()`
call and therefore the same parameterized SQL query):

```python
domain += request.company_domain
if self._is_agent_role(user):
    domain.append(("agent_id.user_id", "=", user.id))
```

New private helper on `LeadApiController` (mirrors the equivalent helper
already in `sale_api.py`):

```python
def _is_agent_role(self, user):
    return (
        user.has_group("quicksol_estate.group_real_estate_agent")
        and not user.has_group("quicksol_estate.group_real_estate_manager")
        and not user.has_group("quicksol_estate.group_real_estate_owner")
        and not user.has_group("base.group_system")
    )
```

Remove the misleading comment `# Query leads (record rules auto-filter by
agent/company)` in `list_leads` since the domain now performs this
explicitly; `.sudo()` remains in place (removing it is a larger change, out
of scope) but is now paired with an explicit, correct domain.

`export_leads_csv` and `lead_statistics` receive the identical two-line
change at the equivalent point in their own domain-building code.

### 2. Activity endpoints missing `@require_company`

Applies to `log_activity`, `list_activities`, `schedule_activity`.

- Add `@require_company` to the decorator chain (after `@require_session`,
  matching the convention used everywhere else in this file).
- Replace the false comment (`# Note: Company isolation is handled by
  @require_company decorator`) with a real, explicit check performed right
  after the lead is loaded and confirmed to exist:

```python
if request.user_company_ids and lead.company_id.id not in request.user_company_ids:
    return error_response("Access denied", 403, "ACCESS_DENIED")
```

An empty `request.user_company_ids` means the user is `base.group_system`
(unrestricted), matching the middleware's own semantics — this mirrors the
admin-bypass behavior kept in section 1.

This is a single-record check (the endpoint already must `browse(lead_id)`
to return 404 vs. 403 correctly), not a list scan, so pushing it into a
`search()` domain instead of a post-fetch check would not change performance
characteristics here — the record is already loaded by id.

### 3. Documentation corrections

- `knowledge_base/security.md` and `knowledge_base/api-surface.md`: remove
  the incorrect claim that `GET /api/v1/leads` is public/undecorated (item
  #6 of `CLAUDE.md`). Replace with an accurate description: the endpoint is
  fully authenticated, and (after this change) company- and agent-scoped.
- `CLAUDE.md` discrepancy #6 should be updated or removed once the knowledge
  base is corrected, since its premise (three public GET endpoints) is
  partially stale for `/leads` specifically. (`/sales` and `/tags` are
  outside this task's scope and not re-verified here.)

### 4. Tests

New integration test(s) (curl-based, following the existing
`integration_tests/*.sh` convention) creating leads across at least two
different companies, asserting:

- A Manager/Owner in company A cannot see company B's leads via
  `GET /api/v1/leads`, `GET /api/v1/leads/export`, or
  `GET /api/v1/leads/statistics`.
- An Agent only sees their own leads (`agent_id.user_id = self`) via the same
  three endpoints, even within their own company.
- A user from company A receives `403 ACCESS_DENIED` when calling
  `POST /api/v1/leads/<id>/activities` (log_activity),
  `GET /api/v1/leads/<id>/activities` (list_activities), or the
  schedule-activity endpoint for a lead belonging to company B.

No existing test currently exercises cross-company isolation on these
endpoints (confirmed during investigation), so this is net-new coverage,
not a modification of existing assertions.

## Known follow-up items (not part of this change)

- `get_lead`/`update_lead`/`delete_lead`/`convert_lead`/`reopen_lead`'s
  `check_access_rule()` call is a no-op under `.sudo()` and does not provide
  real isolation. Needs its own design.
- `log_activity`/`list_activities`/`schedule_activity`'s existing agent
  isolation check compares `lead.agent_id.id` (a `real.estate.agent` id)
  against `current_user.id` (a `res.users` id) — a pre-existing, unrelated
  correctness bug independent of company isolation.
- **`log_activity` and `schedule_activity` (both `type="json"` routes) never
  return a usable HTTP status to real JSON-RPC clients — pre-existing,
  discovered during Task 6.** Both call `error_response()`/`success_response()`,
  which build a `werkzeug`/Odoo `Response` via `request.make_json_response(...)`.
  For a `type="http"` route that value is returned to the client as-is (status
  code included); for a `type="json"` route, Odoo's JSON-RPC dispatcher instead
  always answers with `HTTP 200` and serializes the *returned value* into the
  `"result"` field — since a `Response` object isn't JSON-serializable, it falls
  back to `str(response)`, so the client receives
  `{"jsonrpc": "2.0", "id": null, "result": "<_Response NN bytes [403 FORBIDDEN]>"}`
  with HTTP 200, for both error *and success* paths (confirmed on the
  pre-existing 400/404 validation paths too, not just the new company check).
  **The authorization itself is not broken** — verified directly against the
  database that a blocked cross-company `log_activity`/`schedule_activity`
  call creates no `mail.message`/`mail.activity` row — but no real API
  consumer can distinguish success from failure from the HTTP status alone on
  these two endpoints. `list_activities` (`type="http"`) is unaffected.
  `create_filter`/`list_filters`/`delete_filter` are also `type="json"` and
  likely share this bug, though not independently re-verified here. Fixing
  this properly means changing these routes to return plain dicts (letting
  Odoo's own JSON-RPC envelope carry them) instead of `Response` objects,
  which touches every success and error branch in three functions — a larger,
  separate change than Feature 024's scope. Tracked as technical debt.
