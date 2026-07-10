# Leads Company Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the multi-tenancy isolation gap on `GET /api/v1/leads`, `GET /api/v1/leads/export`, `GET /api/v1/leads/statistics`, and the three lead-activity endpoints, where `.sudo()` queries currently run with no `company_id` domain filter (silently bypassing the correct `ir.rule` record rules already defined for `real.estate.lead`).

**Architecture:** Consume `request.company_domain` / `request.user_company_ids` (already computed by the existing `@require_company` middleware in `thedevkitchen_apigateway/middleware.py`) as the single source of truth inside `LeadApiController`, prepending it to every ORM domain instead of relying on `ir.rule` under `.sudo()`. Add a new `_is_agent_role()` helper for agent-vs-manager/owner/admin classification, and a new `_check_lead_company_access()` helper for the single-record activity endpoints. Pair this with a missing database index (`company_id`) since the field becomes a mandatory domain clause on every affected query.

**Tech Stack:** Odoo 18.0 (Python 3.12), PostgreSQL 16, `unittest`/`unittest.mock` for pure unit tests (ADR-003, no DB), curl-based bash scripts for integration tests (`integration_tests/*.sh`, this project's convention — Odoo `HttpCase` is deliberately avoided due to its read-only-transaction limitation).

## Global Constraints

- ADR-008 §1: Never `.sudo()` without an explicit company filter in the domain.
- ADR-008 §5: Generic `403`/`404` responses — no enumeration of cross-tenant record existence.
- ADR-011: Full `@require_jwt` + `@require_session` + `@require_company` decorator chain on every affected route.
- ADR-019: RBAC semantics — Manager/Owner see all leads in their company_ids; Agent sees only leads where `agent_id.user_id == self`; `base.group_system` (admin) is unrestricted.
- ADR-004: `real.estate.lead` naming is a documented legacy exception — do not rename or restructure it as part of this feature.
- ADR-003: 100% test coverage on new authorization/domain-construction logic; unit tests must NOT touch the database (`unittest.mock` only); integration tests are curl-based (`integration_tests/*.sh`), never Odoo `HttpCase`.
- ADR-022: Code must pass `black`, `isort`, `flake8` (`cd 18.0 && ./lint.sh quicksol_estate`); Pylint ≥ 8.0/10.
- No new endpoints, no new request/response schema fields — every change in this plan is internal server-side logic only.
- Seed data must use a `seed_` (or `seed_024_`) prefix on all new IDs/logins/names and be idempotent (`noupdate="0"` XML data, safe to re-run on module upgrade).

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `18.0/extra-addons/quicksol_estate/models/lead.py` | Add `index=True` to `company_id` (FR4.1) + composite `(company_id, state)` index in `init()` (FR4.2) |
| `18.0/extra-addons/quicksol_estate/controllers/lead_api.py` | Add `_is_agent_role()` + `_check_lead_company_access()` helpers; update `list_leads`/`export_leads_csv`/`lead_statistics` domains (FR1, FR2); add `@require_company` + explicit check to `log_activity`/`list_activities`/`schedule_activity` (FR3) |
| `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py` (new) | Pure `unittest.mock` tests for `_is_agent_role()` and `_check_lead_company_access()` (ADR-003, no DB) |
| `18.0/extra-addons/quicksol_estate/data/seed_leads_company_isolation.xml` (new) | Seed data: 1 new Manager, 1 new Owner, 1 new second Agent (all scoped to the existing `company_quicksol_real_estate`), and 4 leads split across the existing two demo companies, to exercise cross-company/cross-agent isolation |
| `18.0/extra-addons/quicksol_estate/__manifest__.py` | Register the new seed data file in the `data` list |
| `integration_tests/test_us024_s1_manager_owner_company_isolation.sh` (new) | US1: Manager/Owner see only their own company's leads (list/export/statistics) |
| `integration_tests/test_us024_s2_agent_company_isolation.sh` (new) | US2: Agent sees only their own assigned leads, scoped within their company |
| `integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh` (new) | US3: Activity endpoints (`log_activity`/`list_activities`/`schedule_activity`) reject cross-company access |

---

### Task 1: Add `company_id` index + composite index (FR4)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/models/lead.py:144-152` (field definition), `18.0/extra-addons/quicksol_estate/models/lead.py:17-62` (`init()`)

**Interfaces:**
- Produces: `real_estate_lead_company_state_idx` PostgreSQL index on `(company_id, state)`, and a native B-tree index on `company_id` (from `index=True`), consumed implicitly by every query built in Tasks 3-5.

- [ ] **Step 1: Edit the `company_id` field definition to add `index=True`**

In `18.0/extra-addons/quicksol_estate/models/lead.py`, replace:

```python
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        tracking=True,
        ondelete="restrict",
        default=lambda self: self._default_company_id(),
        help="Company this lead belongs to (multi-tenancy)",
    )
```

with:

```python
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        tracking=True,
        index=True,
        ondelete="restrict",
        default=lambda self: self._default_company_id(),
        help="Company this lead belongs to (multi-tenancy)",
    )
```

- [ ] **Step 2: Add the composite `(company_id, state)` index to `init()`**

In the same file, inside `init()`, after the existing `real_estate_lead_state_agent_idx` block (ends around line 46) and before the budget index block, add:

```python
        # Composite index for company-scoped queries (Feature 024: company isolation)
        # Every list/export/statistics query now has company_id as a mandatory
        # domain clause, frequently combined with a state filter/group-by.
        self._cr.execute(
            """
            CREATE INDEX IF NOT EXISTS real_estate_lead_company_state_idx
            ON real_estate_lead (company_id, state)
        """
        )
```

- [ ] **Step 3: Upgrade the module to apply the index migration**

Run:
```bash
cd 18.0 && docker compose run --rm odoo odoo -u quicksol_estate --stop-after-init
```
Expected: exits 0, log shows `Modules loaded` with no errors.

- [ ] **Step 4: Verify both indexes exist in PostgreSQL**

Run:
```bash
cd 18.0 && docker compose exec -T db psql -U odoo -d realestate -c "\d real_estate_lead" | grep -i company
```
Expected output includes two lines, one for the field-level index (e.g. `real_estate_lead_company_id_index`) and one for `real_estate_lead_company_state_idx`.

- [ ] **Step 5: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/models/lead.py
git commit -m "feat(quicksol_estate): index company_id on real.estate.lead for mandatory company-scoped queries"
```

---

### Task 2: Add `_is_agent_role()` helper + unit tests (FR2.1)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py` (add helper in the `# ==================== PRIVATE HELPERS ====================` section, after `_serialize_lead`, around line 1055)
- Create: `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py`

**Interfaces:**
- Produces: `LeadApiController._is_agent_role(self, user) -> bool` — consumed by Task 3, 4, 5 to decide whether to append the agent-ownership domain clause.

- [ ] **Step 1: Write the failing unit test**

Create `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py`:

```python
# -*- coding: utf-8 -*-
"""
Unit Test: Lead Company/Agent Isolation Helpers (Feature 024)

Tests _is_agent_role() and _check_lead_company_access(), the two new
helpers on LeadApiController that make company/agent scoping explicit
in list_leads/export_leads_csv/lead_statistics and the activity
endpoints (log_activity/list_activities/schedule_activity).

Follows ADR-003: Unitario (SEM banco, mock only).
"""

import unittest
from unittest.mock import MagicMock

from odoo.addons.quicksol_estate.controllers.lead_api import LeadApiController


class TestIsAgentRole(unittest.TestCase):
    """Validates _is_agent_role() classification (FR2.1)"""

    def setUp(self):
        self.controller = LeadApiController()

    def _user_with_groups(self, groups):
        user = MagicMock()
        user.has_group.side_effect = lambda group: group in groups
        return user

    def test_pure_agent_returns_true(self):
        user = self._user_with_groups({"quicksol_estate.group_real_estate_agent"})
        self.assertTrue(self.controller._is_agent_role(user))

    def test_agent_and_manager_returns_false(self):
        user = self._user_with_groups(
            {
                "quicksol_estate.group_real_estate_agent",
                "quicksol_estate.group_real_estate_manager",
            }
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_agent_and_owner_returns_false(self):
        user = self._user_with_groups(
            {
                "quicksol_estate.group_real_estate_agent",
                "quicksol_estate.group_real_estate_owner",
            }
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_admin_with_agent_group_returns_false(self):
        user = self._user_with_groups(
            {"quicksol_estate.group_real_estate_agent", "base.group_system"}
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_no_agent_group_returns_false(self):
        user = self._user_with_groups(set())
        self.assertFalse(self.controller._is_agent_role(user))


class TestCheckLeadCompanyAccess(unittest.TestCase):
    """Validates _check_lead_company_access() (FR3.2/FR3.4)"""

    def setUp(self):
        self.controller = LeadApiController()

    def _lead_with_company(self, company_id):
        lead = MagicMock()
        lead.company_id.id = company_id
        return lead

    def test_lead_in_caller_company_allowed(self):
        lead = self._lead_with_company(1)
        self.assertTrue(
            self.controller._check_lead_company_access(lead, user_company_ids=[1, 2])
        )

    def test_lead_outside_caller_companies_denied(self):
        lead = self._lead_with_company(99)
        self.assertFalse(
            self.controller._check_lead_company_access(lead, user_company_ids=[1, 2])
        )

    def test_empty_company_ids_bypasses_check_admin(self):
        lead = self._lead_with_company(99)
        self.assertTrue(
            self.controller._check_lead_company_access(lead, user_company_ids=[])
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit && python3 -m unittest test_lead_company_isolation_unit -v
```
Expected: `ImportError` or `AttributeError` — `_is_agent_role`/`_check_lead_company_access` do not exist yet on `LeadApiController`.

- [ ] **Step 3: Implement the two helpers**

In `18.0/extra-addons/quicksol_estate/controllers/lead_api.py`, inside the `# ==================== PRIVATE HELPERS ====================` section (directly after the `_serialize_lead` method, i.e. after the `return data` at the end of that method, currently around line 1055), add:

```python
    def _is_agent_role(self, user):
        """FR2.1: True only for a pure Agent (no Manager/Owner/Admin override).

        Managers and Owners already see all company leads (FR1); Admins
        (base.group_system) are unrestricted. Only a user who has the
        Agent group and none of those broader roles is scoped down to
        their own leads.
        """
        if user.has_group("base.group_system"):
            return False
        if user.has_group("quicksol_estate.group_real_estate_manager"):
            return False
        if user.has_group("quicksol_estate.group_real_estate_owner"):
            return False
        return user.has_group("quicksol_estate.group_real_estate_agent")

    def _check_lead_company_access(self, lead, user_company_ids):
        """FR3.2/FR3.4: explicit company check for single-lead activity endpoints.

        An empty user_company_ids means the caller is base.group_system
        (admin), which bypasses this check entirely, consistent with
        require_company's own admin semantics.
        """
        if not user_company_ids:
            return True
        return lead.company_id.id in user_company_ids
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit && python3 -m unittest test_lead_company_isolation_unit -v
```
Expected: all 8 tests `OK`.

- [ ] **Step 5: Run the full unit test suite to check for regressions**

Run:
```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit && python3 run_unit_tests.py
```
Expected: no failures introduced (pre-existing failures, if any, are unrelated to this change).

- [ ] **Step 6: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py 18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py
git commit -m "feat(quicksol_estate): add _is_agent_role/_check_lead_company_access helpers for lead isolation"
```

---

### Task 3: Company/agent-scoped domain in `list_leads` (FR1.1, FR1.2, FR2.2, FR2.3)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:64-65` (domain init), `:195` (misleading comment)

**Interfaces:**
- Consumes: `LeadApiController._is_agent_role(self, user) -> bool` (Task 2); `request.company_domain` / `request.user_company_ids` (already set by `@require_company`, `thedevkitchen_apigateway/middleware.py:408-409`).

- [ ] **Step 1: Prepend the company/agent domain immediately after domain initialization**

In `list_leads`, replace:

```python
            # Build domain for filtering
            domain = []
```

with:

```python
            # Build domain for filtering
            # FR1.1: company scoping is the base of every subsequent filter,
            # including the last_activity_before subquery below.
            domain = list(request.company_domain)

            # FR2.2: pure Agents are additionally restricted to their own leads.
            if self._is_agent_role(user):
                domain.append(("agent_id.user_id", "=", user.id))
```

- [ ] **Step 2: Correct the misleading comment**

Replace:

```python
            # Query leads (record rules auto-filter by agent/company)
```

with:

```python
            # Query leads (company/agent domain applied explicitly above,
            # per ADR-008 Sec.1 — .sudo() is retained but no longer relied
            # upon alone for isolation; see FR1.3)
```

- [ ] **Step 3: Manually verify domain construction order**

Read the full method again and confirm: `domain = list(request.company_domain)` + agent clause is the very first thing appended, before `active`, `state`, `agent_id` (query-param), `search`, budget, bedrooms, property_type, location, created_from/to, and — critically — before the `last_activity_before` block that calls `Lead.sudo().search(domain)` to build `inactive_lead_ids` (so that subquery is also company/agent-scoped).

Run:
```bash
grep -n "domain = list(request.company_domain)\|domain.append((\"agent_id.user_id\"\|all_leads = Lead.sudo().search(domain)" 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
```
Expected: the `domain = list(request.company_domain)` line number is smaller than the `all_leads = Lead.sudo().search(domain)` line number.

- [ ] **Step 4: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(quicksol_estate): scope list_leads domain by company/agent (ADR-008 Sec.1)"
```

---

### Task 4: Company/agent-scoped domain in `export_leads_csv` (FR1.1, FR1.2, FR2.2, FR2.3)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:299-300` (domain init), `:339` (misleading comment)

**Interfaces:**
- Consumes: `LeadApiController._is_agent_role(self, user) -> bool` (Task 2), same as Task 3.

- [ ] **Step 1: Prepend the company/agent domain**

In `export_leads_csv`, replace:

```python
            # Build domain (same logic as list_leads, without pagination)
            domain = []
```

with:

```python
            # Build domain (same logic as list_leads, without pagination)
            # FR1.1: company scoping is the base of every subsequent filter.
            domain = list(request.company_domain)

            # FR2.2: pure Agents are additionally restricted to their own leads.
            if self._is_agent_role(user):
                domain.append(("agent_id.user_id", "=", user.id))
```

- [ ] **Step 2: Correct the misleading comment**

Replace:

```python
            # Query leads (record rules enforce security)
```

with:

```python
            # Query leads (company/agent domain applied explicitly above,
            # per ADR-008 Sec.1 — .sudo() is retained but no longer relied
            # upon alone for isolation; see FR1.3)
```

- [ ] **Step 3: Run flake8 on the file to catch syntax errors early**

Run:
```bash
cd 18.0 && flake8 extra-addons/quicksol_estate/controllers/lead_api.py --max-line-length=88 --extend-ignore=E203,E501,W503,E402
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(quicksol_estate): scope export_leads_csv domain by company/agent (ADR-008 Sec.1)"
```

---

### Task 5: Company/agent-scoped domain in `lead_statistics` (FR1.1, FR1.2, FR2.2)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:879-880` (domain init), `:891` (misleading comment)

**Interfaces:**
- Consumes: `LeadApiController._is_agent_role(self, user) -> bool` (Task 2), same as Tasks 3-4.

- [ ] **Step 1: Prepend the company/agent domain**

In `lead_statistics`, replace:

```python
            # Build domain
            domain = [("active", "=", True)]
```

with:

```python
            # Build domain
            # FR1.1: company scoping is the base of every subsequent filter.
            # FR2.2 is included here for defense-in-depth/consistency with
            # list_leads and export_leads_csv, even though the manager/owner
            # gate above already means a pure Agent can never reach this line.
            domain = [("active", "=", True)] + list(request.company_domain)

            if self._is_agent_role(user):
                domain.append(("agent_id.user_id", "=", user.id))
```

- [ ] **Step 2: Correct the misleading comment**

Replace:

```python
            # Total leads (record rules auto-filter by company)
```

with:

```python
            # Total leads (company/agent domain applied explicitly above)
```

- [ ] **Step 3: Run flake8 on the file**

Run:
```bash
cd 18.0 && flake8 extra-addons/quicksol_estate/controllers/lead_api.py --max-line-length=88 --extend-ignore=E203,E501,W503,E402
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(quicksol_estate): scope lead_statistics domain by company/agent (ADR-008 Sec.1)"
```

---

### Task 6: Company enforcement on activity endpoints (FR3)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:1059-1156` (`log_activity`), `:1157-1288` (`list_activities`), `:1290-1427` (`schedule_activity`)

**Interfaces:**
- Consumes: `LeadApiController._check_lead_company_access(self, lead, user_company_ids) -> bool` (Task 2); `request.user_company_ids` (set by `@require_company`).
- Consumes: `require_company` already imported at the top of the file (`from odoo.addons.thedevkitchen_apigateway.middleware import (require_session, require_company)`).

- [ ] **Step 1: Add `@require_company` and the explicit check to `log_activity`**

Replace:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/activities",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    def log_activity(self, lead_id, **kwargs):
```

with:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/activities",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def log_activity(self, lead_id, **kwargs):
```

Then, still inside `log_activity`, replace:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response("Not Found", f"Lead {lead_id} not found", 404)

            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only log on their own leads)
```

with:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response("Not Found", f"Lead {lead_id} not found", 404)

            # Verify user has access to this lead
            current_user = request.env.user

            # FR3.2/FR3.4: explicit cross-company check (request.user_company_ids
            # is empty only for base.group_system, which bypasses this check).
            if not self._check_lead_company_access(
                lead, request.user_company_ids
            ):
                return error_response("Access denied", 403, "ACCESS_DENIED")

            # Check agent isolation (agents can only log on their own leads)
```

- [ ] **Step 2: Add `@require_company` and the explicit check to `list_activities`**

Replace:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/activities",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    def list_activities(self, lead_id, **kwargs):
```

with:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/activities",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def list_activities(self, lead_id, **kwargs):
```

Then, still inside `list_activities`, replace:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response(404, f"Lead {lead_id} not found", "NOT_FOUND")

            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only view their own leads)
```

with:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response(404, f"Lead {lead_id} not found", "NOT_FOUND")

            # Verify user has access to this lead
            current_user = request.env.user

            # FR3.2/FR3.4: explicit cross-company check (request.user_company_ids
            # is empty only for base.group_system, which bypasses this check).
            if not self._check_lead_company_access(
                lead, request.user_company_ids
            ):
                return error_response("Access denied", 403, "ACCESS_DENIED")

            # Check agent isolation (agents can only view their own leads)
```

- [ ] **Step 3: Add `@require_company` and the explicit check to `schedule_activity`**

Replace:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/schedule-activity",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    def schedule_activity(self, lead_id, **kwargs):
```

with:

```python
    @http.route(
        "/api/v1/leads/<int:lead_id>/schedule-activity",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def schedule_activity(self, lead_id, **kwargs):
```

Then, still inside `schedule_activity`, replace:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response("Not Found", f"Lead {lead_id} not found", 404)

            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only schedule on their own leads)
```

with:

```python
            Lead = request.env["real.estate.lead"].sudo()
            lead = Lead.browse(lead_id)

            if not lead.exists():
                return error_response("Not Found", f"Lead {lead_id} not found", 404)

            # Verify user has access to this lead
            current_user = request.env.user

            # FR3.2/FR3.4: explicit cross-company check (request.user_company_ids
            # is empty only for base.group_system, which bypasses this check).
            if not self._check_lead_company_access(
                lead, request.user_company_ids
            ):
                return error_response("Access denied", 403, "ACCESS_DENIED")

            # Check agent isolation (agents can only schedule on their own leads)
```

- [ ] **Step 4: Run flake8 on the file**

Run:
```bash
cd 18.0 && flake8 extra-addons/quicksol_estate/controllers/lead_api.py --max-line-length=88 --extend-ignore=E203,E501,W503,E402
```
Expected: no errors.

- [ ] **Step 5: Upgrade the module to load the decorator/route changes**

Run:
```bash
cd 18.0 && docker compose run --rm odoo odoo -u quicksol_estate --stop-after-init
```
Expected: exits 0, `Modules loaded`.

- [ ] **Step 6: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(quicksol_estate): enforce @require_company + explicit company check on lead activity endpoints"
```

---

### Task 7: Seed data for company/agent isolation testing

**Files:**
- Create: `18.0/extra-addons/quicksol_estate/data/seed_leads_company_isolation.xml`
- Modify: `18.0/extra-addons/quicksol_estate/__manifest__.py` (register the new data file)

**Interfaces:**
- Produces (for Tasks 8-10, via fixed seed logins/passwords):
  - `manager024@imobiliaria.com` / `manager123seed024` — Manager, `company_ids=[company_quicksol_real_estate]` only
  - `owner024@imobiliaria.com` / `owner123seed024` — Owner, `company_ids=[company_quicksol_real_estate]` only
  - `agent2.024@imobiliaria.com` / `agent123seed024` — second Agent in `company_quicksol_real_estate` (alongside the existing `pedro@imobiliaria.com`)
  - Reuses existing `pedro@imobiliaria.com` / `agent123` (Agent, `company_quicksol_real_estate`) and `carmen@luxurygroup.com` / `agent123` (Agent, `company_urban_properties`) from `data/demo_users.xml`.
  - 4 leads: `lead_seed_024_a1_1`, `lead_seed_024_a1_2` (agent = pedro, company = quicksol), `lead_seed_024_a2_1` (agent = agent2.024, company = quicksol), `lead_seed_024_b1_1` (agent = carmen, company = urban_properties).

- [ ] **Step 1: Create the seed data XML**

Create `18.0/extra-addons/quicksol_estate/data/seed_leads_company_isolation.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!--
    SEED: Lead Company/Agent Isolation (Feature 024)
    ─────────────────────────────────────────────────────────────────────────
    Reuses the two existing demo companies (company_quicksol_real_estate,
    company_urban_properties, both from data/demo_users.xml) and their
    existing agents (agent_pedro_demo, agent_carmen_demo) as "Company A"
    and "Company B". Adds only what's missing to exercise every acceptance
    criterion in specs/024-leads-company-isolation/spec-idea.md:

      - A Manager and an Owner restricted to ONLY company_quicksol_real_estate
        (the existing user_estate_manager_demo has access to BOTH demo
        companies, which would make it useless for proving isolation).
      - A second Agent inside company_quicksol_real_estate, so pedro's
        "own leads only" restriction can be tested against a same-company,
        different-agent lead (not just a different-company lead).
      - 4 leads split across agents/companies as described above.

    Dependencies: data/demo_users.xml must load first (company + agent refs).
-->
<odoo>
    <data noupdate="0" context="{'tracking_disable': True, 'no_recompute': True}">

        <!-- Manager restricted to Company A only (quicksol) -->
        <record id="user_seed_024_manager" model="res.users">
            <field name="name">Seed024 Manager (Company A only)</field>
            <field name="login">manager024@imobiliaria.com</field>
            <field name="password">manager123seed024</field>
            <field name="email">manager024@imobiliaria.com</field>
            <field name="groups_id" eval="[(6, 0, [
                ref('base.group_user'),
                ref('quicksol_estate.group_real_estate_manager')
            ])]"/>
            <field name="company_ids" eval="[(6, 0, [
                ref('quicksol_estate.company_quicksol_real_estate')
            ])]"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <!-- Owner restricted to Company A only (quicksol) -->
        <record id="user_seed_024_owner" model="res.users">
            <field name="name">Seed024 Owner (Company A only)</field>
            <field name="login">owner024@imobiliaria.com</field>
            <field name="password">owner123seed024</field>
            <field name="email">owner024@imobiliaria.com</field>
            <field name="groups_id" eval="[(6, 0, [
                ref('base.group_user'),
                ref('quicksol_estate.group_real_estate_owner')
            ])]"/>
            <field name="company_ids" eval="[(6, 0, [
                ref('quicksol_estate.company_quicksol_real_estate')
            ])]"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <!-- Second Agent in Company A (quicksol), alongside pedro -->
        <record id="user_seed_024_agent2" model="res.users">
            <field name="name">Seed024 Agent 2 (Company A)</field>
            <field name="login">agent2.024@imobiliaria.com</field>
            <field name="password">agent123seed024</field>
            <field name="email">agent2.024@imobiliaria.com</field>
            <field name="groups_id" eval="[(6, 0, [
                ref('base.group_user'),
                ref('quicksol_estate.group_real_estate_agent')
            ])]"/>
            <field name="company_ids" eval="[(6, 0, [
                ref('quicksol_estate.company_quicksol_real_estate')
            ])]"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <record id="agent_seed_024_agent2" model="real.estate.agent">
            <field name="name">Seed024 Agent 2</field>
            <field name="cpf">222.333.444-05</field>
            <field name="user_id" ref="user_seed_024_agent2"/>
            <field name="email">agent2.024@imobiliaria.com</field>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <!-- Leads: Company A / Agent pedro (2 leads) -->
        <record id="lead_seed_024_a1_1" model="real.estate.lead">
            <field name="name">Seed024 Lead A1-1 (pedro, Company A)</field>
            <field name="state">new</field>
            <field name="active" eval="True"/>
            <field name="email">seed024.a1.1@test-seed.com.br</field>
            <field name="agent_id" ref="quicksol_estate.agent_pedro_demo"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <record id="lead_seed_024_a1_2" model="real.estate.lead">
            <field name="name">Seed024 Lead A1-2 (pedro, Company A)</field>
            <field name="state">qualified</field>
            <field name="active" eval="True"/>
            <field name="email">seed024.a1.2@test-seed.com.br</field>
            <field name="agent_id" ref="quicksol_estate.agent_pedro_demo"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <!-- Lead: Company A / Agent 2 (must NOT be visible to pedro) -->
        <record id="lead_seed_024_a2_1" model="real.estate.lead">
            <field name="name">Seed024 Lead A2-1 (agent2, Company A)</field>
            <field name="state">new</field>
            <field name="active" eval="True"/>
            <field name="email">seed024.a2.1@test-seed.com.br</field>
            <field name="agent_id" ref="agent_seed_024_agent2"/>
            <field name="company_id" ref="quicksol_estate.company_quicksol_real_estate"/>
        </record>

        <!-- Lead: Company B / Agent carmen (must NOT be visible to any Company A user) -->
        <record id="lead_seed_024_b1_1" model="real.estate.lead">
            <field name="name">Seed024 Lead B1-1 (carmen, Company B)</field>
            <field name="state">new</field>
            <field name="active" eval="True"/>
            <field name="email">seed024.b1.1@test-seed.com.br</field>
            <field name="agent_id" ref="quicksol_estate.agent_carmen_demo"/>
            <field name="company_id" ref="quicksol_estate.company_urban_properties"/>
        </record>

    </data>
</odoo>
```

- [ ] **Step 2: Register the new data file in the manifest**

In `18.0/extra-addons/quicksol_estate/__manifest__.py`, find the line:

```python
        "data/seed_leads.xml",  # Seed: Leads da Imobiliária Seed cobrindo todas as jornadas de filtro
```

and add immediately after it:

```python
        "data/seed_leads_company_isolation.xml",  # Feature 024: company/agent isolation seed data
```

- [ ] **Step 3: Upgrade the module to load the new seed data**

Run:
```bash
cd 18.0 && docker compose run --rm odoo odoo -u quicksol_estate --stop-after-init
```
Expected: exits 0, `Modules loaded`, no XML parse errors.

- [ ] **Step 4: Verify the seed data loaded correctly**

Run:
```bash
cd 18.0 && docker compose exec -T db psql -U odoo -d realestate -c "SELECT login FROM res_users WHERE login IN ('manager024@imobiliaria.com','owner024@imobiliaria.com','agent2.024@imobiliaria.com') ORDER BY login;"
```
Expected: 3 rows returned.

Run:
```bash
cd 18.0 && docker compose exec -T db psql -U odoo -d realestate -c "SELECT name, company_id FROM real_estate_lead WHERE name ILIKE 'Seed024%' ORDER BY name;"
```
Expected: 4 rows returned (a1_1, a1_2, a2_1, b1_1).

- [ ] **Step 5: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/data/seed_leads_company_isolation.xml 18.0/extra-addons/quicksol_estate/__manifest__.py
git commit -m "test(quicksol_estate): add company/agent isolation seed data for Feature 024"
```

---

### Task 8: Integration test — US1 Manager/Owner company isolation

**Files:**
- Create: `integration_tests/test_us024_s1_manager_owner_company_isolation.sh`

**Interfaces:**
- Consumes: `integration_tests`/`18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh` (`get_oauth_token`, `user_login`), the seed users from Task 7 (`manager024@imobiliaria.com`/`manager123seed024`, `owner024@imobiliaria.com`/`owner123seed024`), and the 4 seed leads from Task 7.

- [ ] **Step 1: Write the test script**

Create `integration_tests/test_us024_s1_manager_owner_company_isolation.sh`:

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: US024-S1 - Manager/Owner Company Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 1: Manager/Owner sees only their own company's leads
# Verifies GET /api/v1/leads, /leads/export, /leads/statistics are all
# scoped by request.company_domain (FR1.1) and never leak Company B's
# (urban_properties) leads to a Company A (quicksol)-only Manager/Owner.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s1_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

FAILED=0

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${GREEN}✓${NC} $label"
    else
        echo -e "${RED}✗ FAIL${NC}: $label"
        FAILED=1
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${RED}✗ FAIL${NC}: $label (unexpectedly found: $needle)"
        FAILED=1
    else
        echo -e "${GREEN}✓${NC} $label"
    fi
}

echo "=========================================="
echo "US024-S1: Manager/Owner Company Isolation"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="

    # --------------------------------------------------------------------
    # Company A (quicksol) Manager
    # --------------------------------------------------------------------
    echo -e "${BLUE}STEP 1${NC}: Authenticating as Company A Manager..."
    authenticate_user "manager024@imobiliaria.com" "manager123seed024"
    MANAGER_TOKEN="$OAUTH_TOKEN"
    MANAGER_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Manager authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads..."
    MANAGER_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    assert_contains "$MANAGER_LEADS" "Seed024 Lead A1-1" "Manager sees Company A lead A1-1"
    assert_contains "$MANAGER_LEADS" "Seed024 Lead A1-2" "Manager sees Company A lead A1-2"
    assert_contains "$MANAGER_LEADS" "Seed024 Lead A2-1" "Manager sees Company A lead A2-1 (own-company, different agent)"
    assert_not_contains "$MANAGER_LEADS" "Seed024 Lead B1-1" "Manager does NOT see Company B lead B1-1"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads/export..."
    MANAGER_CSV=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/export" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    assert_contains "$MANAGER_CSV" "Seed024 Lead A1-1" "Manager CSV export includes Company A lead A1-1"
    assert_not_contains "$MANAGER_CSV" "Seed024 Lead B1-1" "Manager CSV export excludes Company B lead B1-1"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Manager calls GET /api/v1/leads/statistics..."
    MANAGER_STATS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/statistics" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    MANAGER_STATS_TOTAL=$(extract_json_field "$MANAGER_STATS" "total")
    echo "Manager statistics total: $MANAGER_STATS_TOTAL"
    if [ "$MANAGER_STATS_TOTAL" -ge 3 ]; then
        echo -e "${GREEN}✓${NC} Manager statistics total includes at least the 3 Company A seed leads"
    else
        echo -e "${RED}✗ FAIL${NC}: Manager statistics total ($MANAGER_STATS_TOTAL) is lower than expected"
        FAILED=1
    fi

    # --------------------------------------------------------------------
    # Company A (quicksol) Owner — same isolation semantics as Manager
    # --------------------------------------------------------------------
    echo ""
    echo -e "${BLUE}STEP 2${NC}: Authenticating as Company A Owner..."
    authenticate_user "owner024@imobiliaria.com" "owner123seed024"
    OWNER_TOKEN="$OAUTH_TOKEN"
    OWNER_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Owner authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: Owner calls GET /api/v1/leads..."
    OWNER_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -H "X-Openerp-Session-Id: $OWNER_SESSION")

    assert_contains "$OWNER_LEADS" "Seed024 Lead A1-1" "Owner sees Company A lead A1-1"
    assert_not_contains "$OWNER_LEADS" "Seed024 Lead B1-1" "Owner does NOT see Company B lead B1-1"

    echo ""
    if [ "$FAILED" -eq 0 ]; then
        echo "=========================================="
        echo -e "${GREEN}TEST PASSED${NC}"
        echo "=========================================="
    else
        echo "=========================================="
        echo -e "${RED}TEST FAILED${NC}"
        echo "=========================================="
    fi
    echo "=== Test Ended: $(date) ==="

} 2>&1 | tee "$TEST_LOG"

exit $FAILED
```

- [ ] **Step 2: Make the script executable**

Run:
```bash
chmod +x integration_tests/test_us024_s1_manager_owner_company_isolation.sh
```

- [ ] **Step 3: Run the test against a live local Odoo instance**

Run:
```bash
cd 18.0 && docker compose up -d
cd .. && bash integration_tests/test_us024_s1_manager_owner_company_isolation.sh
```
Expected: `TEST PASSED`, exit code `0`.

- [ ] **Step 4: Commit**

```bash
git add integration_tests/test_us024_s1_manager_owner_company_isolation.sh
git commit -m "test(integration): add US024-S1 manager/owner company isolation test"
```

---

### Task 9: Integration test — US2 Agent company/agent isolation

**Files:**
- Create: `integration_tests/test_us024_s2_agent_company_isolation.sh`

**Interfaces:**
- Consumes: same `auth_helper.sh` as Task 8, plus the existing `pedro@imobiliaria.com`/`agent123` seed login (`18.0/extra-addons/quicksol_estate/data/demo_users.xml`) and the Task 7 seed leads.

- [ ] **Step 1: Write the test script**

Create `integration_tests/test_us024_s2_agent_company_isolation.sh`:

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: US024-S2 - Agent Company/Agent Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 2: Agent only sees their own assigned leads, scoped within
# their company. Verifies pedro@imobiliaria.com (Agent, Company A) sees
# lead A1-1/A1-2 (his own) but NOT A2-1 (same company, different agent)
# and NOT B1-1 (different company entirely).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s2_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

FAILED=0

assert_contains() {
    local haystack="$1"; local needle="$2"; local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${GREEN}✓${NC} $label"
    else
        echo -e "${RED}✗ FAIL${NC}: $label"; FAILED=1
    fi
}

assert_not_contains() {
    local haystack="$1"; local needle="$2"; local label="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo -e "${RED}✗ FAIL${NC}: $label (unexpectedly found: $needle)"; FAILED=1
    else
        echo -e "${GREEN}✓${NC} $label"
    fi
}

echo "=========================================="
echo "US024-S2: Agent Company/Agent Isolation"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="

    echo -e "${BLUE}STEP 1${NC}: Authenticating as Agent pedro (Company A)..."
    authenticate_user "pedro@imobiliaria.com" "agent123"
    AGENT_TOKEN="$OAUTH_TOKEN"
    AGENT_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Agent authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: Agent pedro calls GET /api/v1/leads..."
    AGENT_LEADS=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&limit=100" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "X-Openerp-Session-Id: $AGENT_SESSION")

    assert_contains "$AGENT_LEADS" "Seed024 Lead A1-1" "Agent pedro sees his own lead A1-1"
    assert_contains "$AGENT_LEADS" "Seed024 Lead A1-2" "Agent pedro sees his own lead A1-2"
    assert_not_contains "$AGENT_LEADS" "Seed024 Lead A2-1" "Agent pedro does NOT see agent2's lead A2-1 (same company)"
    assert_not_contains "$AGENT_LEADS" "Seed024 Lead B1-1" "Agent pedro does NOT see carmen's lead B1-1 (different company)"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Agent pedro calls GET /api/v1/leads/export..."
    AGENT_CSV=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/export" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "X-Openerp-Session-Id: $AGENT_SESSION")

    assert_contains "$AGENT_CSV" "Seed024 Lead A1-1" "Agent pedro CSV export includes his own lead A1-1"
    assert_not_contains "$AGENT_CSV" "Seed024 Lead A2-1" "Agent pedro CSV export excludes agent2's lead A2-1"
    assert_not_contains "$AGENT_CSV" "Seed024 Lead B1-1" "Agent pedro CSV export excludes carmen's lead B1-1"

    echo ""
    echo -e "${BLUE}WHEN${NC}: Manager filters list_leads by agent_id=pedro (regression check for FR2.3)..."
    authenticate_user "manager024@imobiliaria.com" "manager123seed024"
    MANAGER_TOKEN="$OAUTH_TOKEN"
    MANAGER_SESSION="$USER_SESSION_ID"

    AGENT_ID_RESPONSE=$(curl -s --max-time 30 -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.agent\",
                \"method\": \"search_read\",
                \"args\": [[[\"email\", \"=\", \"pedro@imobiliaria.com\"]]],
                \"kwargs\": {\"fields\": [\"id\"], \"limit\": 1}
            },
            \"id\": 1
        }")
    PEDRO_AGENT_ID=$(echo "$AGENT_ID_RESPONSE" | jq -r '.result[0].id // empty')

    MANAGER_FILTERED=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads?search=Seed024&agent_id=$PEDRO_AGENT_ID&limit=100" \
        -H "Authorization: Bearer $MANAGER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION")

    assert_contains "$MANAGER_FILTERED" "Seed024 Lead A1-1" "Manager agent_id filter still returns pedro's lead A1-1"
    assert_not_contains "$MANAGER_FILTERED" "Seed024 Lead A2-1" "Manager agent_id filter correctly excludes agent2's lead A2-1"

    echo ""
    if [ "$FAILED" -eq 0 ]; then
        echo "=========================================="
        echo -e "${GREEN}TEST PASSED${NC}"
        echo "=========================================="
    else
        echo "=========================================="
        echo -e "${RED}TEST FAILED${NC}"
        echo "=========================================="
    fi
    echo "=== Test Ended: $(date) ==="

} 2>&1 | tee "$TEST_LOG"

exit $FAILED
```

- [ ] **Step 2: Make the script executable**

Run:
```bash
chmod +x integration_tests/test_us024_s2_agent_company_isolation.sh
```

- [ ] **Step 3: Run the test**

Run:
```bash
bash integration_tests/test_us024_s2_agent_company_isolation.sh
```
Expected: `TEST PASSED`, exit code `0`.

- [ ] **Step 4: Commit**

```bash
git add integration_tests/test_us024_s2_agent_company_isolation.sh
git commit -m "test(integration): add US024-S2 agent company/agent isolation test"
```

---

### Task 10: Integration test — US3 activity endpoints company isolation

**Files:**
- Create: `integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh`

**Interfaces:**
- Consumes: same `auth_helper.sh`, `pedro@imobiliaria.com`/`agent123` (Company A) attempting cross-company access against `lead_seed_024_b1_1` (Company B).

- [ ] **Step 1: Write the test script**

Create `integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh`:

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: US024-S3 - Activity Endpoints Company Isolation
# ==============================================================================
# Spec: specs/024-leads-company-isolation/spec-idea.md
# User Story 3: log_activity/list_activities/schedule_activity reject
# cross-company access (FR3). pedro@imobiliaria.com (Company A) must be
# blocked with 403 ACCESS_DENIED when targeting lead_seed_024_b1_1
# (Company B, carmen's lead).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_s3_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$SCRIPT_DIR/test_logs"

FAILED=0

echo "=========================================="
echo "US024-S3: Activity Endpoints Company Isolation"
echo "=========================================="
echo ""

{
    echo "=== Test Started: $(date) ==="

    echo -e "${BLUE}GIVEN${NC}: Resolving lead_seed_024_b1_1's ID via admin session..."
    ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
    ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"
    ADMIN_COOKIE_FILE="/tmp/odoo_us024s3_admin_$$.txt"
    trap 'rm -f "$ADMIN_COOKIE_FILE"' EXIT

    curl -s -X POST "$BASE_URL/web/session/authenticate" \
        -H "Content-Type: application/json" \
        -c "$ADMIN_COOKIE_FILE" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"${ODOO_DB:-realestate}\",\"login\":\"$ADMIN_LOGIN\",\"password\":\"$ADMIN_PASSWORD\"}}" > /dev/null

    LEAD_B1_RESPONSE=$(curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.lead\",
                \"method\": \"search_read\",
                \"args\": [[[\"name\", \"=\", \"Seed024 Lead B1-1 (carmen, Company B)\"]]],
                \"kwargs\": {\"fields\": [\"id\"], \"limit\": 1}
            },
            \"id\": 1
        }")
    LEAD_B1_ID=$(echo "$LEAD_B1_RESPONSE" | jq -r '.result[0].id // empty')

    if [ -z "$LEAD_B1_ID" ] || [ "$LEAD_B1_ID" == "null" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not resolve lead_seed_024_b1_1's ID (seed data missing? run Task 7 first)"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} lead_seed_024_b1_1 ID = $LEAD_B1_ID"
    echo ""

    echo -e "${BLUE}STEP 1${NC}: Authenticating as Agent pedro (Company A)..."
    authenticate_user "pedro@imobiliaria.com" "agent123"
    AGENT_TOKEN="$OAUTH_TOKEN"
    AGENT_SESSION="$USER_SESSION_ID"
    echo -e "${GREEN}✓${NC} Agent authenticated"
    echo ""

    echo -e "${BLUE}WHEN${NC}: pedro calls POST /api/v1/leads/$LEAD_B1_ID/activities (log_activity)..."
    LOG_ACTIVITY_RESPONSE=$(curl -s --max-time 30 -X POST "$BASE_URL/api/v1/leads/$LEAD_B1_ID/activities" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "X-Openerp-Session-Id: $AGENT_SESSION" \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"body\":\"cross-company attempt\",\"activity_type\":\"note\"}}")

    if echo "$LOG_ACTIVITY_RESPONSE" | grep -q "ACCESS_DENIED"; then
        echo -e "${GREEN}✓${NC} log_activity returns ACCESS_DENIED for cross-company lead"
    else
        echo -e "${RED}✗ FAIL${NC}: log_activity did not return ACCESS_DENIED. Response: $LOG_ACTIVITY_RESPONSE"
        FAILED=1
    fi

    echo ""
    echo -e "${BLUE}WHEN${NC}: pedro calls GET /api/v1/leads/$LEAD_B1_ID/activities (list_activities)..."
    LIST_ACTIVITIES_RESPONSE=$(curl -s --max-time 30 -X GET "$BASE_URL/api/v1/leads/$LEAD_B1_ID/activities" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "X-Openerp-Session-Id: $AGENT_SESSION")

    if echo "$LIST_ACTIVITIES_RESPONSE" | grep -q "ACCESS_DENIED"; then
        echo -e "${GREEN}✓${NC} list_activities returns ACCESS_DENIED for cross-company lead"
    else
        echo -e "${RED}✗ FAIL${NC}: list_activities did not return ACCESS_DENIED. Response: $LIST_ACTIVITIES_RESPONSE"
        FAILED=1
    fi

    echo ""
    echo -e "${BLUE}WHEN${NC}: pedro calls POST /api/v1/leads/$LEAD_B1_ID/schedule-activity (schedule_activity)..."
    SCHEDULE_RESPONSE=$(curl -s --max-time 30 -X POST "$BASE_URL/api/v1/leads/$LEAD_B1_ID/schedule-activity" \
        -H "Authorization: Bearer $AGENT_TOKEN" \
        -H "X-Openerp-Session-Id: $AGENT_SESSION" \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"summary\":\"cross-company attempt\",\"date_deadline\":\"2027-01-01\"}}")

    if echo "$SCHEDULE_RESPONSE" | grep -q "ACCESS_DENIED"; then
        echo -e "${GREEN}✓${NC} schedule_activity returns ACCESS_DENIED for cross-company lead"
    else
        echo -e "${RED}✗ FAIL${NC}: schedule_activity did not return ACCESS_DENIED. Response: $SCHEDULE_RESPONSE"
        FAILED=1
    fi

    echo ""
    echo -e "${BLUE}WHEN${NC}: Admin (base.group_system) calls GET /api/v1/leads/$LEAD_B1_ID/activities (bypass check)..."
    ADMIN_ACTIVITIES=$(curl -s --max-time 30 -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"method\": \"call\",
            \"params\": {
                \"model\": \"real.estate.lead\",
                \"method\": \"read\",
                \"args\": [[$LEAD_B1_ID], [\"id\", \"name\"]],
                \"kwargs\": {}
            },
            \"id\": 2
        }")
    if echo "$ADMIN_ACTIVITIES" | grep -q "Seed024 Lead B1-1"; then
        echo -e "${GREEN}✓${NC} Admin (via Odoo web session) can still read the cross-company lead (no regression)"
    else
        echo -e "${RED}✗ FAIL${NC}: Admin unexpectedly cannot read the lead. Response: $ADMIN_ACTIVITIES"
        FAILED=1
    fi

    echo ""
    if [ "$FAILED" -eq 0 ]; then
        echo "=========================================="
        echo -e "${GREEN}TEST PASSED${NC}"
        echo "=========================================="
    else
        echo "=========================================="
        echo -e "${RED}TEST FAILED${NC}"
        echo "=========================================="
    fi
    echo "=== Test Ended: $(date) ==="

} 2>&1 | tee "$TEST_LOG"

exit $FAILED
```

- [ ] **Step 2: Make the script executable**

Run:
```bash
chmod +x integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh
```

- [ ] **Step 3: Run the test**

Run:
```bash
bash integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh
```
Expected: `TEST PASSED`, exit code `0`.

- [ ] **Step 4: Commit**

```bash
git add integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh
git commit -m "test(integration): add US024-S3 activity endpoints company isolation test"
```

---

### Task 11: Final lint/quality pass and full regression run

**Files:**
- No new files; validates all files touched in Tasks 1-10.

**Interfaces:**
- Consumes: everything produced by Tasks 1-10.

- [ ] **Step 1: Run the project's full lint script on `quicksol_estate`**

Run:
```bash
cd 18.0 && ./lint.sh quicksol_estate
```
Expected: no `flake8` errors reported for `models/lead.py` or `controllers/lead_api.py`.

- [ ] **Step 2: Run black/isort in check mode**

Run:
```bash
cd 18.0 && black --check extra-addons/quicksol_estate/models/lead.py extra-addons/quicksol_estate/controllers/lead_api.py extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py
isort --check-only extra-addons/quicksol_estate/models/lead.py extra-addons/quicksol_estate/controllers/lead_api.py extra-addons/quicksol_estate/tests/unit/test_lead_company_isolation_unit.py
```
Expected: no changes needed. If either reports diffs, run `black` / `isort` (without `--check`) on the same files, review the diff, and commit as a separate `style:` commit.

- [ ] **Step 3: Run the full pure unit test suite**

Run:
```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit && python3 run_unit_tests.py
```
Expected: all tests pass, including the new `test_lead_company_isolation_unit.py`.

- [ ] **Step 4: Run the full curl-based integration suite for this feature**

Run:
```bash
bash integration_tests/test_us024_s1_manager_owner_company_isolation.sh
bash integration_tests/test_us024_s2_agent_company_isolation.sh
bash integration_tests/test_us024_s3_activity_endpoints_company_isolation.sh
```
Expected: all three print `TEST PASSED` and exit `0`.

- [ ] **Step 5: Spot-check the pre-existing `test_us6_s4_agent_isolation.sh` for regressions**

Run:
```bash
bash integration_tests/test_us6_s4_agent_isolation.sh
```
Expected: `TEST PASSED` (unchanged behavior — this script exercises `pedro`/`carmen`-style ad hoc leads created within the script itself, not the Task 7 seed leads, so it validates that Task 3/6's changes don't break the pre-existing agent-isolation flow).

- [ ] **Step 6: Final commit (only if Step 2 produced formatting changes; otherwise skip — nothing to commit)**

```bash
git add -A
git commit -m "style(quicksol_estate): apply black/isort formatting for Feature 024 changes"
```

---

## Self-Review Notes (completed during plan authoring)

**Spec coverage:**
- FR1.1/FR1.2/FR1.3 → Tasks 3, 4 (list_leads, export_leads_csv)
- FR2.1 → Task 2; FR2.2/FR2.3 → Tasks 3, 4, 5
- FR3.1/FR3.2/FR3.3/FR3.4 → Task 6
- FR4.1/FR4.2 → Task 1
- Seed Data section → Task 7 (adapted to reuse existing `company_quicksol_real_estate`/`company_urban_properties`/`agent_pedro_demo`/`agent_carmen_demo` fixtures already loaded by `data/demo_users.xml`, rather than creating brand-new companies — this is a deliberate simplification: the existing demo data already provides two isolated real-estate companies with one agent each, so only the missing pieces — a single-company Manager/Owner and a second same-company Agent — needed to be added)
- User Story 1 test table → Task 8
- User Story 2 test table → Task 9
- User Story 3 test table → Task 10
- NFR2 (indexing) → Task 1; NFR2 (N+1, caching, async) — no action required, already assessed as not-applicable in the spec, no task needed
- NFR3 (quality) → Task 11
- Out-of-Scope Follow-ups #1-#4 — intentionally NOT implemented by any task in this plan (matches spec's explicit scope boundary)

**Placeholder scan:** No `TODO`/`TBD`/"add appropriate handling" phrases used; every step has literal, complete code or an exact command with expected output.

**Type/name consistency:** `_is_agent_role(self, user)` and `_check_lead_company_access(self, lead, user_company_ids)` are defined once in Task 2 and referenced with the exact same signature in Tasks 3, 4, 5 (`_is_agent_role`) and Task 6 (`_check_lead_company_access`).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-09-leads-company-isolation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
