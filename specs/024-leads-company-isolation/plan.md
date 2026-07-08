# Lead Endpoint Company Isolation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `GET /api/v1/leads`, `GET /api/v1/leads/export`, and `GET /api/v1/leads/statistics` actually enforce company (and agent) isolation via the query domain, and close a decorator gap on the three lead-activity endpoints that silently skip `@require_company`.

**Architecture:** No new files, models, or migrations. All changes are additive edits to `18.0/extra-addons/quicksol_estate/controllers/lead_api.py`: the domain-building code for three list-style endpoints gains `request.company_domain` (already computed by the existing `@require_company` middleware) plus an agent-only-sees-own-leads clause; three activity endpoints gain the `@require_company` decorator plus a real post-fetch company check (they load a single record by id, so a domain-level filter isn't applicable there). New curl-based integration tests under `integration_tests/` follow the project's existing bash-script convention (ADR-003).

**Tech Stack:** Odoo 18.0 Python controllers, Odoo ORM domains, bash + curl integration tests (existing `integration_tests/lib`/`tests/lib/auth_helper.sh` helpers).

## Global Constraints

- Company scoping must come from `request.company_domain` / `request.user_company_ids` (set by `@require_company` in `18.0/extra-addons/thedevkitchen_apigateway/middleware.py:362-417`) — do not reimplement company-id lookup logic. This is the same pattern already used in `property_api.py:689` (`domain = [...] + request.company_domain`) and `property_api.py:65` (`if request.user_company_ids: ...`).
- `base.group_system` (System Admin) keeps unrestricted access: `request.user_company_ids == []` and `request.company_domain == []` for admins, so appending/checking against them is always a no-op for admins. Do not add a separate admin special-case.
- Do not touch `get_lead`, `update_lead`, `delete_lead`, `convert_lead`, `reopen_lead`, `create_filter`, `list_filters`, `delete_filter` — out of scope per `specs/024-leads-company-isolation/spec.md`.
- Do not fix the pre-existing `lead.agent_id.id != current_user.id` comparison bug in the activity endpoints (comparing a `real.estate.agent` id to a `res.users` id) — out of scope, already documented as a known follow-up in the spec.
- Company filters must be pushed into the ORM domain passed to `.search()`/`.search_count()`/`.read_group()` (parameterized SQL), never applied by fetching unfiltered rows and filtering in Python.
- After every edit to `lead_api.py`, restart the Odoo container before testing — this project runs Odoo with `workers = 0` (threaded dev mode) and no `--dev=reload`, so Python source changes are not picked up until restart: `cd 18.0 && docker compose restart odoo && cd -`.
- All new integration test scripts must load credentials from `18.0/.env` and follow the existing structure in `integration_tests/test_us6_s5_manager_all_leads.sh` (colored output, `test_logs/` output, `set -e` or explicit pass/fail counters).

---

### Task 1: Add `_is_agent_role` helper and apply company/agent domain isolation to `list_leads`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:64-65` (domain init in `list_leads`), `:195` (misleading comment), `:934+` (private helpers section, add new method)

**Interfaces:**
- Produces: `LeadApiController._is_agent_role(self, user) -> bool` — returns `True` only for a user in `quicksol_estate.group_real_estate_agent` and none of `group_real_estate_manager`, `group_real_estate_owner`, `base.group_system`. Reused by Tasks 2 (not Task 3, see below).

- [ ] **Step 1: Reproduce the bug manually (failing check)**

Requires Owner B to exist. Run this once; if it errors because Owner B already exists, continue anyway:

```bash
./integration_tests/setup_owner_b.sh
```

Then, from repo root, run:

```bash
source 18.0/.env
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"

# Owner B (company "Urban Properties") creates a lead
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB Isolation Probe",
  "phone": "+5511900000001",
  "email": "companyb.probe@example.com",
  "state": "new"
}')
echo "$CREATE_RESP"
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
echo "LEAD_B_ID=$LEAD_B_ID"

# Owner A (company A) lists leads — should NOT include LEAD_B_ID, but does today
unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
make_api_request "GET" "/api/v1/leads?limit=100" | grep -o "\"id\":$LEAD_B_ID"
```

Expected (current buggy behavior): the last command **prints** `"id":<LEAD_B_ID>`, proving Owner A can see Owner B's company lead.

- [ ] **Step 2: Add the `_is_agent_role` helper**

In `18.0/extra-addons/quicksol_estate/controllers/lead_api.py`, find the `PRIVATE HELPERS` section:

```python
    # ==================== PRIVATE HELPERS ====================

    def _serialize_lead(self, lead, include_activities=False):
```

Add the new method directly above `_serialize_lead`:

```python
    # ==================== PRIVATE HELPERS ====================

    def _is_agent_role(self, user):
        """Check if user has only agent role (not manager/owner/admin)."""
        return (
            user.has_group("quicksol_estate.group_real_estate_agent")
            and not user.has_group("quicksol_estate.group_real_estate_manager")
            and not user.has_group("quicksol_estate.group_real_estate_owner")
            and not user.has_group("base.group_system")
        )

    def _serialize_lead(self, lead, include_activities=False):
```

- [ ] **Step 3: Apply the domain filter in `list_leads`**

Find:

```python
            # Build domain for filtering
            domain = []

            # Active filter (ADR-015: soft-delete)
```

Replace with:

```python
            # Build domain for filtering
            domain = []

            # Company isolation (request.company_domain is set by @require_company;
            # it is [] for base.group_system, meaning unrestricted access)
            domain += request.company_domain

            # Agent isolation: agents only see their own leads
            if self._is_agent_role(user):
                domain.append(("agent_id.user_id", "=", user.id))

            # Active filter (ADR-015: soft-delete)
```

- [ ] **Step 4: Fix the misleading comment**

Find:

```python
            # Query leads (record rules auto-filter by agent/company)
            Lead = request.env["real.estate.lead"]
```

Replace with:

```python
            # Query leads (company/agent isolation enforced explicitly above)
            Lead = request.env["real.estate.lead"]
```

- [ ] **Step 5: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5
```

Re-run the exact same commands from Step 1 (reuse `$LEAD_B_ID`, re-authenticate both users since sessions may have reset):

```bash
source 18.0/.env
BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
make_api_request "GET" "/api/v1/leads?limit=100" | grep -o "\"id\":$LEAD_B_ID"
echo "exit code: $?"
```

Expected: the `grep` finds nothing and exits non-zero (no match) — Owner A no longer sees Owner B's lead.

- [ ] **Step 6: Cleanup and commit**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "owner2@example.com" "OwnerB123!"
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): enforce company/agent isolation on GET /api/v1/leads"
```

---

### Task 2: Apply the same domain filter to `export_leads_csv`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:299-341` (domain init and query in `export_leads_csv`)

**Interfaces:**
- Consumes: `LeadApiController._is_agent_role` (Task 1).

- [ ] **Step 1: Reproduce the bug manually**

Reuse the pattern from Task 1 Step 1 but hit `/api/v1/leads/export` instead (CSV response, so grep the raw body):

```bash
source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB Export Probe",
  "phone": "+5511900000002",
  "email": "companyb.export.probe@example.com",
  "state": "new"
}')
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
echo "LEAD_B_ID=$LEAD_B_ID"

unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
make_api_request "GET" "/api/v1/leads/export" | grep "CompanyB Export Probe"
```

Expected (current buggy behavior): the CSV row for "CompanyB Export Probe" is present in Owner A's export.

- [ ] **Step 2: Apply the domain filter**

Find:

```python
            # Build domain (same logic as list_leads, without pagination)
            domain = []

            if active_filter == "true":
```

Replace with:

```python
            # Build domain (same logic as list_leads, without pagination)
            domain = []

            # Company isolation (request.company_domain is set by @require_company;
            # it is [] for base.group_system, meaning unrestricted access)
            domain += request.company_domain

            # Agent isolation: agents only see their own leads
            if self._is_agent_role(user):
                domain.append(("agent_id.user_id", "=", user.id))

            if active_filter == "true":
```

- [ ] **Step 3: Fix the misleading comment**

Find:

```python
            # Query leads (record rules enforce security)
            Lead = request.env["real.estate.lead"]
            leads = Lead.sudo().search(domain, order="create_date desc")
```

Replace with:

```python
            # Query leads (company/agent isolation enforced explicitly above)
            Lead = request.env["real.estate.lead"]
            leads = Lead.sudo().search(domain, order="create_date desc")
```

- [ ] **Step 4: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5

source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
make_api_request "GET" "/api/v1/leads/export" | grep "CompanyB Export Probe"
echo "exit code: $?"
```

Expected: `grep` finds nothing (exit code 1) — Owner A's export no longer contains Owner B's lead.

- [ ] **Step 5: Cleanup and commit**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "owner2@example.com" "OwnerB123!"
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): enforce company/agent isolation on GET /api/v1/leads/export"
```

---

### Task 3: Apply company domain filter to `lead_statistics`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:879-892` (domain init and total count in `lead_statistics`)

**Interfaces:**
- None new. `lead_statistics` is already gated to Manager/Owner only (lines 864-872), so `_is_agent_role` would never be `True` here — only the company filter is added, not the agent clause.

- [ ] **Step 1: Reproduce the bug manually**

```bash
source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB Stats Probe",
  "phone": "+5511900000003",
  "email": "companyb.stats.probe@example.com",
  "state": "new"
}')
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")

unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
BEFORE_TOTAL=$(make_api_request "GET" "/api/v1/leads/statistics" | grep -o '"total":[0-9]*')
echo "Owner A total before: $BEFORE_TOTAL"
```

Note the number — it currently includes Company B's leads (cannot assert an exact expected count without knowing pre-existing data, so this step is a baseline capture, not a strict pass/fail).

- [ ] **Step 2: Apply the domain filter**

Find:

```python
            # Build domain
            domain = [("active", "=", True)]

            if date_from:
```

Replace with:

```python
            # Build domain
            domain = [("active", "=", True)]

            # Company isolation (request.company_domain is set by @require_company;
            # it is [] for base.group_system, meaning unrestricted access)
            domain += request.company_domain

            if date_from:
```

- [ ] **Step 3: Fix the misleading comment**

Find:

```python
            # Total leads (record rules auto-filter by company)
            total = Lead.sudo().search_count(domain)
```

Replace with:

```python
            # Total leads (company isolation enforced explicitly above)
            total = Lead.sudo().search_count(domain)
```

- [ ] **Step 4: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5

source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
AFTER_TOTAL=$(make_api_request "GET" "/api/v1/leads/statistics" | grep -o '"total":[0-9]*')
echo "Owner A total after: $AFTER_TOTAL"
```

Expected: `AFTER_TOTAL` is strictly less than `BEFORE_TOTAL` captured in Step 1 (Company B's probe lead, and any other Company B leads, are no longer counted).

- [ ] **Step 5: Cleanup and commit**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "owner2@example.com" "OwnerB123!"
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): enforce company isolation on GET /api/v1/leads/statistics"
```

---

### Task 4: Add `@require_company` and a real company check to `log_activity`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:1067-1069` (decorator chain), `:1092-1094` (body)

**Interfaces:**
- Consumes: `request.user_company_ids` (set by `@require_company`).

- [ ] **Step 1: Reproduce the gap manually**

```bash
source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB Activity Probe",
  "phone": "+5511900000004",
  "email": "companyb.activity.probe@example.com",
  "state": "new"
}')
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
echo "LEAD_B_ID=$LEAD_B_ID"

unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
HTTP_STATUS=$(curl -s -o /tmp/log_activity_probe.json -w "%{http_code}" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"body":"cross-company probe note","activity_type":"note"}}')
echo "status=$HTTP_STATUS"
cat /tmp/log_activity_probe.json
```

Expected (current buggy behavior): `status=200` (or 201) — Owner A, who has no membership in Company B, can log an activity on Company B's lead.

- [ ] **Step 2: Add `@require_company` to the decorator chain**

Find:

```python
    @require_jwt
    @require_session
    def log_activity(self, lead_id, **kwargs):
```

Replace with:

```python
    @require_jwt
    @require_session
    @require_company
    def log_activity(self, lead_id, **kwargs):
```

- [ ] **Step 3: Replace the false comment with a real check**

Find:

```python
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only log on their own leads)
```

Replace with:

```python
            # Verify user has access to this lead
            current_user = request.env.user

            if (
                request.user_company_ids
                and lead.company_id.id not in request.user_company_ids
            ):
                return error_response("Access denied", 403, "ACCESS_DENIED")

            # Check agent isolation (agents can only log on their own leads)
```

- [ ] **Step 4: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5

source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
curl -s -o /tmp/log_activity_probe.json -w "status=%{http_code}\n" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"body":"cross-company probe note","activity_type":"note"}}'
cat /tmp/log_activity_probe.json
```

Expected: `status=403` with `"error":"ACCESS_DENIED"` in the body.

- [ ] **Step 5: Verify same-company access still works**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "owner2@example.com" "OwnerB123!"
curl -s -o /tmp/log_activity_ok.json -w "status=%{http_code}\n" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"body":"same-company note","activity_type":"note"}}'
cat /tmp/log_activity_ok.json
```

Expected: `status=200` (Owner B logging on Owner B's own lead still works).

- [ ] **Step 6: Cleanup and commit**

```bash
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): add missing @require_company and company check to log_activity"
```

---

### Task 5: Add `@require_company` and a real company check to `list_activities`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:1165-1167` (decorator chain), `:1182-1184` (body)

**Interfaces:**
- Consumes: `request.user_company_ids` (set by `@require_company`).

- [ ] **Step 1: Reproduce the gap manually**

```bash
source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB ListActivities Probe",
  "phone": "+5511900000005",
  "email": "companyb.listact.probe@example.com",
  "state": "new"
}')
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")

unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
curl -s -o /tmp/list_activities_probe.json -w "status=%{http_code}\n" \
  -X GET "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}"
cat /tmp/list_activities_probe.json
```

Expected (current buggy behavior): `status=200` — Owner A can list activities on Company B's lead.

- [ ] **Step 2: Add `@require_company` to the decorator chain**

Find:

```python
    @require_jwt
    @require_session
    def list_activities(self, lead_id, **kwargs):
```

Replace with:

```python
    @require_jwt
    @require_session
    @require_company
    def list_activities(self, lead_id, **kwargs):
```

- [ ] **Step 3: Replace the false comment with a real check**

Find:

```python
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only view their own leads)
```

Replace with:

```python
            # Verify user has access to this lead
            current_user = request.env.user

            if (
                request.user_company_ids
                and lead.company_id.id not in request.user_company_ids
            ):
                return error_response(
                    403, "Access denied: lead belongs to a different company", "ACCESS_DENIED"
                )

            # Check agent isolation (agents can only view their own leads)
```

- [ ] **Step 4: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5

source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
curl -s -o /tmp/list_activities_probe.json -w "status=%{http_code}\n" \
  -X GET "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}"
cat /tmp/list_activities_probe.json
```

Expected: `status=403` with `"error":"ACCESS_DENIED"` in the body.

- [ ] **Step 5: Verify same-company access still works**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "owner2@example.com" "OwnerB123!"
curl -s -o /tmp/list_activities_ok.json -w "status=%{http_code}\n" \
  -X GET "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/activities" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}"
cat /tmp/list_activities_ok.json
```

Expected: `status=200`.

- [ ] **Step 6: Cleanup and commit**

```bash
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): add missing @require_company and company check to list_activities"
```

---

### Task 6: Add `@require_company` and a real company check to `schedule_activity`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/lead_api.py:1298-1300` (decorator chain), `:1331-1333` (body)

**Interfaces:**
- Consumes: `request.user_company_ids` (set by `@require_company`).

- [ ] **Step 1: Reproduce the gap manually**

```bash
source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh

authenticate_user "owner2@example.com" "OwnerB123!"
CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" '{
  "name": "CompanyB Schedule Probe",
  "phone": "+5511900000006",
  "email": "companyb.schedule.probe@example.com",
  "state": "new"
}')
LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")

unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
curl -s -o /tmp/schedule_activity_probe.json -w "status=%{http_code}\n" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"cross-company probe","date_deadline":"2099-01-01"}}'
cat /tmp/schedule_activity_probe.json
```

Expected (current buggy behavior): `status=200` (or 201) — Owner A can schedule an activity on Company B's lead.

- [ ] **Step 2: Add `@require_company` to the decorator chain**

Find:

```python
    @require_jwt
    @require_session
    def schedule_activity(self, lead_id, **kwargs):
```

Replace with:

```python
    @require_jwt
    @require_session
    @require_company
    def schedule_activity(self, lead_id, **kwargs):
```

- [ ] **Step 3: Replace the false comment with a real check**

Find:

```python
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator

            # Check agent isolation (agents can only schedule on their own leads)
```

Replace with:

```python
            # Verify user has access to this lead
            current_user = request.env.user

            if (
                request.user_company_ids
                and lead.company_id.id not in request.user_company_ids
            ):
                return error_response(
                    "Forbidden", "Access denied: lead belongs to a different company", 403
                )

            # Check agent isolation (agents can only schedule on their own leads)
```

- [ ] **Step 4: Restart Odoo and re-run the manual check**

```bash
cd 18.0 && docker compose restart odoo && cd -
sleep 5

source 18.0/.env
source 18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh
authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"
curl -s -o /tmp/schedule_activity_probe.json -w "status=%{http_code}\n" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"cross-company probe","date_deadline":"2099-01-01"}}'
cat /tmp/schedule_activity_probe.json
```

Expected: `status=403`.

- [ ] **Step 5: Verify same-company access still works**

```bash
unset OAUTH_TOKEN USER_SESSION_ID
authenticate_user "owner2@example.com" "OwnerB123!"
curl -s -o /tmp/schedule_activity_ok.json -w "status=%{http_code}\n" \
  -X POST "${ODOO_BASE_URL:-http://localhost:8069}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
  -H "Authorization: Bearer ${OAUTH_TOKEN}" \
  -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"same-company activity","date_deadline":"2099-01-01"}}'
cat /tmp/schedule_activity_ok.json
```

Expected: `status=200` (or 201).

- [ ] **Step 6: Cleanup and commit**

```bash
make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null

git add 18.0/extra-addons/quicksol_estate/controllers/lead_api.py
git commit -m "fix(024): add missing @require_company and company check to schedule_activity"
```

---

### Task 7: Integration test — cross-company isolation for list/export/statistics

**Files:**
- Create: `integration_tests/test_us024_leads_cross_company_isolation.sh`

**Interfaces:**
- None (standalone bash script). Depends only on the already-fixed behavior from Tasks 1-3 and on `18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh` (`authenticate_user`, `make_api_request`, `extract_json_field`).

- [ ] **Step 1: Write the test script**

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Cross-Company Lead Isolation
# ==============================================================================
# Verifies GET /api/v1/leads, /api/v1/leads/export, and /api/v1/leads/statistics
# never return data from a company the requesting user does not belong to.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_cross_company_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

assert_true() {
    local label="$1" condition="$2"
    if [ "$condition" = "true" ]; then
        echo -e "${GREEN}✓${NC} $label"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label"
        FAIL=$((FAIL+1))
    fi
}

{
    echo "=== Test Started: $(date) ==="
    TIMESTAMP=$(date +%s)

    echo -e "${BLUE}GIVEN${NC}: Owner B creates a lead in Company B"
    authenticate_user "owner2@example.com" "OwnerB123!"
    CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" "{
        \"name\": \"US024 CrossCompany Lead ${TIMESTAMP}\",
        \"phone\": \"+551190${TIMESTAMP: -7}\",
        \"email\": \"us024.crosscompany.${TIMESTAMP}@example.com\",
        \"state\": \"new\"
    }")
    LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
    echo "Lead B ID: $LEAD_B_ID"

    if [ -z "$LEAD_B_ID" ] || [ "$LEAD_B_ID" = "null" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create Company B lead — is Owner B seeded? Run integration_tests/setup_owner_b.sh"
        exit 1
    fi

    unset OAUTH_TOKEN USER_SESSION_ID
    echo ""
    echo -e "${BLUE}WHEN${NC}: Owner A queries list/export/statistics"
    authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"

    LIST_RESP=$(make_api_request "GET" "/api/v1/leads?limit=200")
    EXPORT_RESP=$(make_api_request "GET" "/api/v1/leads/export")
    STATS_RESP=$(make_api_request "GET" "/api/v1/leads/statistics")

    echo ""
    echo -e "${BLUE}THEN${NC}: Company B's lead must not appear for Owner A"

    if echo "$LIST_RESP" | grep -q "\"id\":$LEAD_B_ID"; then
        assert_true "list_leads excludes Company B lead" "false"
    else
        assert_true "list_leads excludes Company B lead" "true"
    fi

    if echo "$EXPORT_RESP" | grep -q "US024 CrossCompany Lead ${TIMESTAMP}"; then
        assert_true "export_leads_csv excludes Company B lead" "false"
    else
        assert_true "export_leads_csv excludes Company B lead" "true"
    fi

    if echo "$STATS_RESP" | grep -q '"total":[0-9]*'; then
        assert_true "lead_statistics returns a total (endpoint reachable)" "true"
    else
        assert_true "lead_statistics returns a total (endpoint reachable)" "false"
    fi

    echo ""
    echo -e "${BLUE}AND${NC}: Owner B still sees their own lead via all three endpoints"
    unset OAUTH_TOKEN USER_SESSION_ID
    authenticate_user "owner2@example.com" "OwnerB123!"

    LIST_RESP_B=$(make_api_request "GET" "/api/v1/leads?limit=200")
    EXPORT_RESP_B=$(make_api_request "GET" "/api/v1/leads/export")

    if echo "$LIST_RESP_B" | grep -q "\"id\":$LEAD_B_ID"; then
        assert_true "Owner B still sees own lead in list_leads" "true"
    else
        assert_true "Owner B still sees own lead in list_leads" "false"
    fi

    if echo "$EXPORT_RESP_B" | grep -q "US024 CrossCompany Lead ${TIMESTAMP}"; then
        assert_true "Owner B still sees own lead in export" "true"
    else
        assert_true "Owner B still sees own lead in export" "false"
    fi

    echo ""
    echo "Cleanup: archiving Company B test lead..."
    make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null 2>&1

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x integration_tests/test_us024_leads_cross_company_isolation.sh
./integration_tests/test_us024_leads_cross_company_isolation.sh
```

Expected: `PASS: 5  FAIL: 0` and exit code `0`. If Owner B isn't seeded yet, the script exits early with a clear message pointing at `setup_owner_b.sh` — run that once, then re-run this test.

- [ ] **Step 3: Commit**

```bash
git add integration_tests/test_us024_leads_cross_company_isolation.sh
git commit -m "test(024): add cross-company isolation test for lead list/export/statistics"
```

---

### Task 8: Integration test — agent only sees own leads

**Files:**
- Create: `integration_tests/test_us024_leads_agent_isolation.sh`

**Interfaces:**
- None (standalone bash script). `18.0/extra-addons/quicksol_estate/data/demo_users.xml` seeds `pedro@imobiliaria.com` as the only demo Agent in `company_quicksol_real_estate` (`joao@imobiliaria.com` is a plain "User" role, not an Agent, and `carmen@luxurygroup.com` is an Agent in a *different* company — neither pairs with Pedro for a same-company agent-vs-agent test). This test therefore creates its own second, same-company agent fixture via native Odoo admin JSON-RPC (`/web/session/authenticate` + `/web/dataset/call_kw`), following the same admin-fixture technique as `integration_tests/test_us3_s3_agent_own_leads.sh`, but targeting the real `real.estate.agent`/`real.estate.lead` models (that older script targets Odoo's stock `crm.lead`, which is a different, unrelated model) and resolving group ids dynamically via `ir.model.data` instead of hardcoding a group id.

- [ ] **Step 1: Write the test script**

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Agent-Only-Own-Leads on list_leads
# ==============================================================================
# Verifies GET /api/v1/leads only returns an agent's own leads
# (agent_id.user_id = self), even within the same company. Creates a second,
# same-company agent fixture on the fly since demo_users.xml only seeds one
# Agent per company.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
DB_NAME="${ODOO_DB:-${POSTGRES_DB:-realestate}}"
ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin}"
ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"
ADMIN_COOKIE_FILE="/tmp/odoo_us024_agent_admin_$$.txt"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_agent_isolation_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

assert_true() {
    local label="$1" condition="$2"
    if [ "$condition" = "true" ]; then
        echo -e "${GREEN}✓${NC} $label"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label"
        FAIL=$((FAIL+1))
    fi
}

cleanup() { rm -f "$ADMIN_COOKIE_FILE"; }
trap cleanup EXIT

admin_rpc() {
    local model="$1" method="$2" args="$3" kwargs="${4:-{}}"
    curl -s -X POST "$BASE_URL/web/dataset/call_kw" \
        -H "Content-Type: application/json" \
        -b "$ADMIN_COOKIE_FILE" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"model\":\"$model\",\"method\":\"$method\",\"args\":$args,\"kwargs\":$kwargs}}"
}

{
    echo "=== Test Started: $(date) ==="
    TIMESTAMP=$(date +%s)

    echo -e "${BLUE}SETUP${NC}: Admin login (native Odoo session, fixture creation only)"
    LOGIN_RESP=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
        -H "Content-Type: application/json" \
        -c "$ADMIN_COOKIE_FILE" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"$DB_NAME\",\"login\":\"$ADMIN_LOGIN\",\"password\":\"$ADMIN_PASSWORD\"},\"id\":1}")
    ADMIN_UID=$(echo "$LOGIN_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result',{}).get('uid') or '')")
    if [ -z "$ADMIN_UID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Admin login failed"
        exit 1
    fi
    echo "Admin UID: $ADMIN_UID"

    echo ""
    echo -e "${BLUE}GIVEN${NC}: Pedro's existing agent record, plus a fresh second agent in the same company"
    PEDRO_AGENT_RESP=$(admin_rpc "real.estate.agent" "search_read" "[[[\"email\",\"=\",\"pedro@imobiliaria.com\"]]]" "{\"fields\":[\"id\",\"company_id\"]}")
    PEDRO_AGENT_ID=$(echo "$PEDRO_AGENT_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['id'] if d else '')")
    PEDRO_COMPANY_ID=$(echo "$PEDRO_AGENT_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['company_id'][0] if d else '')")
    echo "Pedro agent_id=$PEDRO_AGENT_ID company_id=$PEDRO_COMPANY_ID"

    if [ -z "$PEDRO_AGENT_ID" ] || [ -z "$PEDRO_COMPANY_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not resolve pedro@imobiliaria.com's agent record — check demo_users.xml seed data"
        exit 1
    fi

    AGENT_GROUP_RESP=$(admin_rpc "ir.model.data" "search_read" "[[[\"module\",\"=\",\"quicksol_estate\"],[\"name\",\"=\",\"group_real_estate_agent\"],[\"model\",\"=\",\"res.groups\"]]]" "{\"fields\":[\"res_id\"]}")
    AGENT_GROUP_ID=$(echo "$AGENT_GROUP_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['res_id'] if d else '')")

    USER_GROUP_RESP=$(admin_rpc "ir.model.data" "search_read" "[[[\"module\",\"=\",\"base\"],[\"name\",\"=\",\"group_user\"],[\"model\",\"=\",\"res.groups\"]]]" "{\"fields\":[\"res_id\"]}")
    USER_GROUP_ID=$(echo "$USER_GROUP_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];print(d[0]['res_id'] if d else '')")

    if [ -z "$AGENT_GROUP_ID" ] || [ -z "$USER_GROUP_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not resolve required res.groups ids via ir.model.data"
        exit 1
    fi

    NEW_AGENT_LOGIN="us024.otheragent.${TIMESTAMP}@imobiliaria.com"
    NEW_USER_RESP=$(admin_rpc "res.users" "create" "[{\"name\":\"US024 Other Agent\",\"login\":\"$NEW_AGENT_LOGIN\",\"password\":\"agent123\",\"company_id\":$PEDRO_COMPANY_ID,\"company_ids\":[[6,0,[$PEDRO_COMPANY_ID]]],\"groups_id\":[[6,0,[$AGENT_GROUP_ID,$USER_GROUP_ID]]]}]")
    NEW_USER_ID=$(echo "$NEW_USER_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")
    echo "New agent user_id=$NEW_USER_ID"

    CPF=$(python3 -c "
def d(cpf, w):
    s = sum(int(c) * x for c, x in zip(cpf, w)); r = s % 11
    return '0' if r < 2 else str(11 - r)
base = str(${TIMESTAMP})[-9:].zfill(9)
d1 = d(base, range(10, 1, -1)); d2 = d(base + d1, range(11, 1, -1))
print(f'{base[0:3]}.{base[3:6]}.{base[6:9]}-{d1}{d2}')
")
    NEW_AGENT_REC_RESP=$(admin_rpc "real.estate.agent" "create" "[{\"name\":\"US024 Other Agent\",\"user_id\":$NEW_USER_ID,\"company_id\":$PEDRO_COMPANY_ID,\"email\":\"$NEW_AGENT_LOGIN\",\"cpf\":\"$CPF\"}]")
    NEW_AGENT_ID=$(echo "$NEW_AGENT_REC_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")
    echo "New agent real.estate.agent id=$NEW_AGENT_ID"

    if [ -z "$NEW_USER_ID" ] || [ -z "$NEW_AGENT_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create fixture agent (see raw responses above)"
        exit 1
    fi

    PEDRO_LEAD_RESP=$(admin_rpc "real.estate.lead" "create" "[{\"name\":\"US024 Pedro Own Lead ${TIMESTAMP}\",\"agent_id\":$PEDRO_AGENT_ID,\"company_id\":$PEDRO_COMPANY_ID}]")
    PEDRO_LEAD_ID=$(echo "$PEDRO_LEAD_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")

    OTHER_LEAD_RESP=$(admin_rpc "real.estate.lead" "create" "[{\"name\":\"US024 OtherAgent Lead ${TIMESTAMP}\",\"agent_id\":$NEW_AGENT_ID,\"company_id\":$PEDRO_COMPANY_ID}]")
    OTHER_LEAD_ID=$(echo "$OTHER_LEAD_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('result') or '')")

    echo "Pedro's lead=$PEDRO_LEAD_ID  Other agent's lead=$OTHER_LEAD_ID"

    if [ -z "$PEDRO_LEAD_ID" ] || [ -z "$OTHER_LEAD_ID" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create fixture leads"
        exit 1
    fi

    echo ""
    echo -e "${BLUE}WHEN${NC}: Pedro (agent) lists leads via GET /api/v1/leads"
    authenticate_user "pedro@imobiliaria.com" "agent123"
    LIST_RESP=$(make_api_request "GET" "/api/v1/leads?limit=200")

    echo ""
    echo -e "${BLUE}THEN${NC}: Pedro sees his own lead but not the other agent's lead"
    if echo "$LIST_RESP" | grep -q "\"id\":$PEDRO_LEAD_ID"; then
        assert_true "Pedro sees his own lead" "true"
    else
        assert_true "Pedro sees his own lead" "false"
    fi

    if echo "$LIST_RESP" | grep -q "\"id\":$OTHER_LEAD_ID"; then
        assert_true "Pedro does not see the other agent's lead" "false"
    else
        assert_true "Pedro does not see the other agent's lead" "true"
    fi

    echo ""
    echo "Cleanup: deactivating fixture leads and agent..."
    admin_rpc "real.estate.lead" "write" "[[$PEDRO_LEAD_ID,$OTHER_LEAD_ID],{\"active\":false}]" > /dev/null
    admin_rpc "real.estate.agent" "unlink" "[[$NEW_AGENT_ID]]" > /dev/null
    admin_rpc "res.users" "write" "[[$NEW_USER_ID],{\"active\":false}]" > /dev/null

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x integration_tests/test_us024_leads_agent_isolation.sh
./integration_tests/test_us024_leads_agent_isolation.sh
```

Expected: `PASS: 2  FAIL: 0`. Requires `python3` (already a project dependency, used by other integration tests) and a working `admin`/`ADMIN_PASSWORD` login from `18.0/.env`.

- [ ] **Step 3: Commit**

```bash
git add integration_tests/test_us024_leads_agent_isolation.sh
git commit -m "test(024): add agent-only-sees-own-leads test for list_leads"
```

---

### Task 9: Integration test — cross-company 403 on activity endpoints

**Files:**
- Create: `integration_tests/test_us024_leads_activity_cross_company.sh`

**Interfaces:**
- None (standalone bash script). Exercises the three `type="json"` endpoints fixed in Tasks 4-6 using the JSON-RPC envelope convention already used elsewhere in this project (see `integration_tests/test_us1_s2_owner_crud.sh`).

- [ ] **Step 1: Write the test script**

```bash
#!/bin/bash
# ==============================================================================
# Integration Test: Feature 024 - Cross-Company 403 on Lead Activity Endpoints
# ==============================================================================
# Verifies log_activity, list_activities, and schedule_activity reject a user
# whose company does not match the lead's company with 403 ACCESS_DENIED.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../18.0/.env"

AUTH_LIB="$SCRIPT_DIR/../18.0/extra-addons/quicksol_estate/tests/lib/auth_helper.sh"
source "$AUTH_LIB"

BASE_URL="${ODOO_BASE_URL:-http://localhost:8069}"
TEST_LOG="$SCRIPT_DIR/test_logs/us024_activity_cross_company_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

mkdir -p "$SCRIPT_DIR/test_logs"

assert_status() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $label (status=$actual)"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} $label (expected=$expected actual=$actual)"
        FAIL=$((FAIL+1))
    fi
}

{
    echo "=== Test Started: $(date) ==="
    TIMESTAMP=$(date +%s)

    echo -e "${BLUE}GIVEN${NC}: Owner B creates a lead in Company B"
    authenticate_user "owner2@example.com" "OwnerB123!"
    CREATE_RESP=$(make_api_request "POST" "/api/v1/leads" "{
        \"name\": \"US024 Activity CrossCompany ${TIMESTAMP}\",
        \"phone\": \"+551192${TIMESTAMP: -7}\",
        \"email\": \"us024.activity.${TIMESTAMP}@example.com\",
        \"state\": \"new\"
    }")
    LEAD_B_ID=$(extract_json_field "$CREATE_RESP" "id")
    echo "Lead B ID: $LEAD_B_ID"

    if [ -z "$LEAD_B_ID" ] || [ "$LEAD_B_ID" = "null" ]; then
        echo -e "${RED}✗ FAIL${NC}: Could not create Company B lead — is Owner B seeded? Run integration_tests/setup_owner_b.sh"
        exit 1
    fi

    unset OAUTH_TOKEN USER_SESSION_ID
    echo ""
    echo -e "${BLUE}WHEN${NC}: Owner A (different company) calls the three activity endpoints"
    authenticate_user "$TEST_USER_OWNER" "$TEST_PASSWORD_OWNER"

    STATUS_LOG=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"body":"cross-company note","activity_type":"note"}}')
    assert_status "log_activity rejects cross-company access" "403" "$STATUS_LOG"

    STATUS_LIST=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}")
    assert_status "list_activities rejects cross-company access" "403" "$STATUS_LIST"

    STATUS_SCHEDULE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"cross-company activity","date_deadline":"2099-01-01"}}')
    assert_status "schedule_activity rejects cross-company access" "403" "$STATUS_SCHEDULE"

    echo ""
    echo -e "${BLUE}AND${NC}: Owner B (same company) can still use all three endpoints"
    unset OAUTH_TOKEN USER_SESSION_ID
    authenticate_user "owner2@example.com" "OwnerB123!"

    STATUS_LOG_OK=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"body":"same-company note","activity_type":"note"}}')
    assert_status "log_activity still works for same company" "200" "$STATUS_LOG_OK"

    STATUS_LIST_OK=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/activities" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}")
    assert_status "list_activities still works for same company" "200" "$STATUS_LIST_OK"

    STATUS_SCHEDULE_OK=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/leads/${LEAD_B_ID}/schedule-activity" \
        -H "Authorization: Bearer ${OAUTH_TOKEN}" \
        -H "X-Openerp-Session-Id: ${USER_SESSION_ID}" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"call","params":{"summary":"same-company activity","date_deadline":"2099-01-01"}}')
    if [ "$STATUS_SCHEDULE_OK" = "200" ] || [ "$STATUS_SCHEDULE_OK" = "201" ]; then
        echo -e "${GREEN}✓${NC} schedule_activity still works for same company (status=$STATUS_SCHEDULE_OK)"
        PASS=$((PASS+1))
    else
        echo -e "${RED}✗${NC} schedule_activity still works for same company (actual=$STATUS_SCHEDULE_OK)"
        FAIL=$((FAIL+1))
    fi

    echo ""
    echo "Cleanup: archiving Company B test lead..."
    make_api_request "DELETE" "/api/v1/leads/$LEAD_B_ID" > /dev/null 2>&1

    echo ""
    echo "=========================================="
    echo "PASS: $PASS  FAIL: $FAIL"
    echo "=========================================="
    echo "=== Test Ended: $(date) ==="

    [ "$FAIL" -eq 0 ]

} 2>&1 | tee "$TEST_LOG"

exit "${PIPESTATUS[0]}"
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x integration_tests/test_us024_leads_activity_cross_company.sh
./integration_tests/test_us024_leads_activity_cross_company.sh
```

Expected: `PASS: 6  FAIL: 0`.

- [ ] **Step 3: Commit**

```bash
git add integration_tests/test_us024_leads_activity_cross_company.sh
git commit -m "test(024): add cross-company 403 test for lead activity endpoints"
```

---

### Task 10: Correct stale documentation

**Files:**
- Modify: `knowledge_base/security.md` (the line asserting `GET /api/v1/leads` is public)
- Modify: `knowledge_base/api-surface.md:124` and `:243` (the rows/notes describing `list_leads` auth as `none`)
- Modify: `CLAUDE.md` discrepancy #6 (item 12 in the "Attention Points" table)

**Interfaces:** None — documentation only.

- [ ] **Step 1: Inspect the exact current wording**

```bash
grep -n "leads" knowledge_base/security.md | head -20
grep -n "list_leads\|/api/v1/leads" knowledge_base/api-surface.md | head -20
```

- [ ] **Step 2: Correct `knowledge_base/security.md`**

Find the line(s) listing `GET /api/v1/leads` alongside `/sales` and `/tags` as fully public/no-decorator endpoints. Replace the `/api/v1/leads` portion of that note with:

```markdown
`GET /api/v1/leads` is fully authenticated (`@require_jwt` + `@require_session` + `@require_company`) and, as of Feature 024, enforces explicit company- and agent-based domain filtering. It was previously misdocumented here as public — the auth decorators were always present; the bug was a missing `company_id` domain filter inside the handler. `/api/v1/sales` and `/api/v1/tags` are unaffected by this correction and remain open questions.
```

- [ ] **Step 3: Correct `knowledge_base/api-surface.md`**

At line 124 (endpoint table row for `list_leads`), change the `auth` column value from `none` to `JWT+Session+Company`, matching the other `/api/v1/leads/*` rows.

At line 243 (the narrative note about public GET endpoints), remove `/api/v1/leads` from the list of endpoints with `auth='none'`, leaving `/api/v1/sales` and `/api/v1/tags` (not touched by this task).

- [ ] **Step 4: Correct `CLAUDE.md` discrepancy #6**

Find item 6 in the "Attention Points" section (`## 12. Attention Points`). Replace it with:

```markdown
6. **`GET /api/v1/leads` documentation corrected (RESOLVED as of Feature 024).** This item previously claimed `/api/v1/leads`, `/api/v1/sales`, and `/api/v1/tags` were all fully public (`auth='none'`, no decorators). Code inspection during Feature 024 (`specs/024-leads-company-isolation/`) confirmed `GET /api/v1/leads` always had the full `@require_jwt`/`@require_session`/`@require_company` chain — the real bug was a missing `company_id` domain filter inside the handler (now fixed, plus a matching fix for `/api/v1/leads/export`, `/api/v1/leads/statistics`, and three lead-activity endpoints that were missing `@require_company` entirely). `/api/v1/sales` (GET) and `/api/v1/tags` (GET) were **not** re-verified as part of this fix and remain an open question — confirm their `auth='none'` status independently before treating them the same way.
```

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/security.md knowledge_base/api-surface.md CLAUDE.md
git commit -m "docs(024): correct stale public-endpoint claims for GET /api/v1/leads"
```

---

### Task 11: Update the Postman collection (ADR-016 / `postman-collection-manager`)

**Files:**
- Create: `docs/postman/quicksol_api_v1.35_postman_collection.json`
- Modify: `docs/postman/README.md`

Note: per explicit user instruction, the previous version (`quicksol_api_v1.34_postman_collection.json`) is kept, not deleted — this deviates from the "keep only the latest version" rule in `.github/skills/postman-collection-manager/SKILL.md`, matching this project's existing practice of keeping many historical versioned files in `docs/postman/`.

**Interfaces:** None — documentation/tooling artifact only.

All six affected endpoints (`List Leads`, `Export Leads to CSV`, `Get Lead Statistics`, `List Lead Activities`, `Log Activity on Lead`, `Schedule Activity on Lead`) already exist in `quicksol_api_v1.34_postman_collection.json` under folders `10. Leads - CRUD`, `12. Lead Analytics`, and `13. Lead Activities`. `List Leads`, `Export Leads to CSV`, and `Get Lead Statistics` already document `**Multi-tenancy:** Company isolation active (@require_company)` in their `request.description` (that claim was previously false due to the bug fixed in Tasks 1-3; no text change needed there, it is now accurate). `List Lead Activities`, `Log Activity on Lead`, and `Schedule Activity on Lead` are **missing** that line entirely — confirmed by inspecting the raw JSON — because they were missing `@require_company` before Tasks 4-6. This task adds it.

- [ ] **Step 1: Write and run the version-bump script**

Save as `/private/tmp/claude-501/-opt-homebrew-var-www-realestate-odoo-docker/scratchpad/bump_postman_v1_35.py` (or any scratch path) and run with `python3`:

```python
import json

SRC = "docs/postman/quicksol_api_v1.34_postman_collection.json"
DST = "docs/postman/quicksol_api_v1.35_postman_collection.json"

with open(SRC, encoding="utf-8") as f:
    collection = json.loads(f.read(), strict=False)

UPDATES = {
    "List Lead Activities": (
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Fingerprint validation:** Active\n\n"
        "**IMPORTANT:** For GET requests, session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in body.\n\n"
        "List all activities logged on a specific lead.",
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Multi-tenancy:** Company isolation active (@require_company) — returns 403 ACCESS_DENIED if the lead belongs to a different company\n"
        "**Fingerprint validation:** Active\n\n"
        "**IMPORTANT:** For GET requests, session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in body.\n\n"
        "List all activities logged on a specific lead.",
    ),
    "Log Activity on Lead": (
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Fingerprint validation:** Active\n\n"
        "Log a new activity (call, email, visit, etc.) on a lead.",
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Multi-tenancy:** Company isolation active (@require_company) — returns 403 ACCESS_DENIED if the lead belongs to a different company\n"
        "**Fingerprint validation:** Active\n\n"
        "Log a new activity (call, email, visit, etc.) on a lead.",
    ),
    "Schedule Activity on Lead": (
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Fingerprint validation:** Active\n\n"
        "Schedule a future activity on a lead with deadline.",
        "**Authentication:** Bearer Token + Session ID required\n"
        "**Multi-tenancy:** Company isolation active (@require_company) — returns 403 ACCESS_DENIED if the lead belongs to a different company\n"
        "**Fingerprint validation:** Active\n\n"
        "Schedule a future activity on a lead with deadline.",
    ),
}


def walk(items):
    for it in items:
        if "item" in it:
            yield from walk(it["item"])
        else:
            yield it


applied = set()
for it in walk(collection["item"]):
    name = it.get("name")
    if name in UPDATES:
        old_desc, new_desc = UPDATES[name]
        req = it.get("request", {})
        current = req.get("description", "")
        if current != old_desc:
            raise SystemExit(
                f"Description for '{name}' did not match the expected text — "
                f"the collection may have changed since this script was written. "
                f"Found:\n{current!r}"
            )
        req["description"] = new_desc
        applied.add(name)

missing = set(UPDATES) - applied
if missing:
    raise SystemExit(f"Could not find these requests in the collection: {missing}")

collection["info"]["version"] = "1.35"
collection["info"]["description"] += (
    "\n\n## Changelog v1.35 (Feature 024)\n\n"
    "**Lead company isolation enforced**\n\n"
    "✅ `List Leads`, `Export Leads to CSV`, and `Get Lead Statistics` now actually "
    "enforce the company/agent isolation their descriptions always claimed "
    "(previously a domain-filter bug let cross-company leads leak through).\n"
    "✅ `List Lead Activities`, `Log Activity on Lead`, and `Schedule Activity on Lead` "
    "now require `@require_company` and return **403 ACCESS_DENIED** when the "
    "target lead belongs to a different company than the requester's."
)

with open(DST, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print(f"Wrote {DST} (version {collection['info']['version']}, updated: {sorted(applied)})")
```

Run it from the repo root:

```bash
python3 /private/tmp/claude-501/-opt-homebrew-var-www-realestate-odoo-docker/scratchpad/bump_postman_v1_35.py
```

Expected output:

```
Wrote docs/postman/quicksol_api_v1.35_postman_collection.json (version 1.35, updated: ['List Lead Activities', 'Log Activity on Lead', 'Schedule Activity on Lead'])
```

If it exits with `SystemExit` instead, the collection has drifted from what Task 11 assumed — open `quicksol_api_v1.34_postman_collection.json`, find the current description text for the named request, and adjust `old_desc` in the script to match before re-running.

- [ ] **Step 2: Validate the new file**

```bash
python3 -c "
import json
d = json.load(open('docs/postman/quicksol_api_v1.35_postman_collection.json'))
assert d['info']['version'] == '1.35'
assert 'v1.35' in d['info']['description']
def walk(items):
    for it in items:
        if 'item' in it: yield from walk(it['item'])
        else: yield it
names = {it['name']: it['request'].get('description','') for it in walk(d['item'])}
for n in ('List Lead Activities', 'Log Activity on Lead', 'Schedule Activity on Lead'):
    assert 'Multi-tenancy' in names[n], f'{n} missing multi-tenancy note'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Update `docs/postman/README.md`**

Update the header block near the top:

```markdown
**Version:** 1.35.0
**Last Updated:** <today's date, YYYY-MM-DD>
**Spec Coverage:** Complete API (55+ endpoints)
```

Add a new first entry under "## Available Collections" (renumber the existing "### 1. Complete API Collection (v1.31)" entry to "### 2." and so on is not required — this project's README already has non-sequential/duplicate numbering across versions, e.g. two "### 1." style entries from different eras; just prepend, don't renumber existing entries):

```markdown
### 1. Complete API Collection (v1.35) ⭐ RECOMMENDED
**File:** `quicksol_api_v1.35_postman_collection.json`
**Coverage:** All 55+ endpoints - Complete API coverage
**ADR Compliance:** ADR-016 (complete)
**Note:** Lead company/agent isolation now correctly enforced on List Leads, Export Leads to CSV, Get Lead Statistics, and all three Lead Activities endpoints (Feature 024)
```

Add a new changelog section directly above `## Changelog v1.31 (Latest - 2026-05-12)`:

```markdown
## Changelog v1.35 (Latest - <today's date, YYYY-MM-DD>)

**Lead company isolation enforced (Feature 024)**

✅ `List Leads`, `Export Leads to CSV`, and `Get Lead Statistics` now actually enforce the company/agent isolation their descriptions always claimed.
✅ `List Lead Activities`, `Log Activity on Lead`, and `Schedule Activity on Lead` now require `@require_company` and document the new **403 ACCESS_DENIED** response for cross-company access attempts.

```

- [ ] **Step 4: Commit**

The previous version (`quicksol_api_v1.34_postman_collection.json`) is kept, not deleted, per explicit user instruction:

```bash
git add docs/postman/quicksol_api_v1.35_postman_collection.json docs/postman/README.md
git commit -m "docs(024): add Postman collection v1.35 for lead company isolation"
```
