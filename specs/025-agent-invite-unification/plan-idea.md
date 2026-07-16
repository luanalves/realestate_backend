# Unify Agent Creation into the Invite Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a profile of type `agent` is invited via `POST /api/v1/users/invite`, atomically create its `real.estate.agent` record (with the same CRECI/bank-field validation `POST /api/v1/agents` uses today), then deprecate and eventually remove the now-redundant `POST /api/v1/agents` endpoint.

**Architecture:** A new `AgentService.create_agent_from_profile()` method (added to the existing `quicksol_estate/services/agent_service.py`) becomes the single place that creates a `real.estate.agent` from a profile plus optional CRECI/bank fields, reusing the model's existing `setdefault()` profile-sync and `_check_creci_format` constraint. `invite_controller.py::invite_user` calls it in the same DB transaction as `res.users` creation whenever the target profile's type is `agent`. `POST /api/v1/agents` is left functionally untouched (no shared-service refactor — it's scheduled for deletion) but gains `Deprecation`/`Sunset` headers and a `deprecated` flag surfaced through Swagger. A final, explicitly gated phase removes it entirely.

**Tech Stack:** Odoo 18.0 (Python 3.12), PostgreSQL 16, Odoo ORM (`TransactionCase` unit tests), curl-based integration tests (`integration_tests/*.sh` — this project deliberately avoids Odoo `HttpCase` due to its read-only-transaction limitation, per `knowledge_base/testing.md`).

## Global Constraints

- Odoo 18.0 / Python 3.12 — follow existing code style (black/isort/flake8 per `18.0/.flake8`; pylint ≥ 8.0, per ADR-022).
- ADR-004: do not rename `quicksol_estate` or `real.estate.agent` — legacy naming exception, out of scope for this feature.
- ADR-008: the `agent` object on `POST /api/v1/users/invite` never accepts `company_id` — it is always derived from the already-validated `profile_record.company_id`.
- ADR-011: both endpoints keep their existing `@require_jwt` → `@require_session` → `@require_company` decorator chain, unchanged.
- ADR-005/ADR-016: OpenAPI is generated dynamically from the `thedevkitchen.api.endpoint` table — never hand-edit static OpenAPI/Postman files; Postman changes go through the `postman-collection-manager` skill, OpenAPI changes go through editing the DB-backed XML records (this project's swagger generator reads that table directly, so no separate "regenerate" build step exists — the JSON is generated per-request from `GET /api/v1/openapi.json`).
- Seed data/test fixtures use a `seed_` prefix on IDs/logins (project convention, e.g. `seed_agent_025@test.com`).
- No schema/model changes beyond the one new `deprecated` boolean field on `thedevkitchen.api.endpoint` (Task 6) — everything else reuses existing fields.
- Full requirements, error-code mapping, and test-coverage tables already live in [spec-idea.md](spec-idea.md); architecture-level decisions live in [design.md](design.md). This plan does not repeat those — it only turns them into exact file diffs and executable steps.

---

### Task 1: Add `AGENT_INVITE_EXTRA_SCHEMA` to `SchemaValidator`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py:87` (insert new schema block after `AGENT_UPDATE_SCHEMA`, before the `# Assignment schema` comment)
- Modify: `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py` (insert new wrapper method after `validate_agent_update`)
- Test: `18.0/extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py`

**Interfaces:**
- Produces: `SchemaValidator.AGENT_INVITE_EXTRA_SCHEMA` (dict), `SchemaValidator.validate_agent_invite_extra(data: dict) -> tuple[bool, list[str]]` — consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `18.0/extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py`:

```python
# -*- coding: utf-8 -*-
import unittest
from odoo.addons.quicksol_estate.controllers.utils.schema import SchemaValidator


class TestAgentInviteExtraSchema(unittest.TestCase):
    """Feature 025: optional `agent` object validation on POST /api/v1/users/invite."""

    def test_empty_payload_is_valid(self):
        is_valid, errors = SchemaValidator.validate_agent_invite_extra({})
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_creci_too_short_is_invalid(self):
        is_valid, errors = SchemaValidator.validate_agent_invite_extra({"creci": "ab"})
        self.assertFalse(is_valid)
        self.assertTrue(any("creci" in e for e in errors))

    def test_valid_full_payload(self):
        is_valid, errors = SchemaValidator.validate_agent_invite_extra(
            {
                "creci": "CRECI/SP 123456",
                "hire_date": "2026-01-01",
                "bank_name": "Banco Seed",
                "bank_account": "12345-6",
                "pix_key": "seed@pix.com",
            }
        )
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_wrong_type_is_invalid(self):
        is_valid, errors = SchemaValidator.validate_agent_invite_extra({"creci": 123456})
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec odoo python3 -m pytest /opt/odoo/extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py -v` (adjust the container path prefix if your compose mounts addons elsewhere — confirm with `docker compose exec odoo python3 -c "import quicksol_estate; print(quicksol_estate.__file__)"` if unsure)
Expected: FAIL with `AttributeError: type object 'SchemaValidator' has no attribute 'validate_agent_invite_extra'`

- [ ] **Step 3: Add the schema and wrapper method**

In `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py`, insert after line 87 (right after the closing `}` of `AGENT_UPDATE_SCHEMA`, before the `# Assignment schema` comment on line 89):

```python
    # Agent invite extra schema (Feature 025) — optional agent-specific
    # fields on POST /api/v1/users/invite when the target profile is 'agent'.
    AGENT_INVITE_EXTRA_SCHEMA = {
        "required": [],
        "optional": ["creci", "hire_date", "bank_name", "bank_account", "pix_key"],
        "types": {
            "creci": str,
            "hire_date": str,
            "bank_name": str,
            "bank_account": str,
            "pix_key": str,
        },
        "constraints": {
            "creci": lambda v: len(v) >= 4 if v else True,
        },
    }
```

Then, in the same file, immediately after the existing `validate_agent_update` static method (the one that calls `SchemaValidator.validate_request(data, SchemaValidator.AGENT_UPDATE_SCHEMA)`), add:

```python
    @staticmethod
    def validate_agent_invite_extra(data):
        """Validate the optional `agent` object on POST /api/v1/users/invite (Feature 025)."""
        return SchemaValidator.validate_request(
            data, SchemaValidator.AGENT_INVITE_EXTRA_SCHEMA
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec odoo python3 -m pytest /opt/odoo/extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py -v`
Expected: 4 passed

- [ ] **Step 5: Lint**

Run: `cd 18.0 && ./lint.sh extra-addons/quicksol_estate/controllers/utils/schema.py extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/utils/schema.py 18.0/extra-addons/quicksol_estate/tests/unit/test_schema_agent_invite_extra.py
git commit -m "feat(quicksol_estate): add AGENT_INVITE_EXTRA_SCHEMA for unified invite flow"
```

---

### Task 2: Add `create_agent_from_profile` to the existing `AgentService`

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/services/agent_service.py` (append new method to the existing `AgentService` class — do NOT create a new file; `agent_service.py` already exists and is already imported at `services/__init__.py:6`)
- Test: `18.0/extra-addons/quicksol_estate/tests/unit/test_agent_service_create_from_profile.py`

**Interfaces:**
- Consumes: `real.estate.agent.create()`'s existing `profile_id`-based `setdefault()` sync (already implemented, `models/agent.py:436-470` — no changes needed there), and the existing `_check_creci_format` constraint (`models/agent.py:286-309`).
- Produces: `AgentService.create_agent_from_profile(self, profile_record, agent_payload=None) -> real.estate.agent recordset`, raising `odoo.exceptions.ValidationError` on CRECI format/uniqueness failure. Consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `18.0/extra-addons/quicksol_estate/tests/unit/test_agent_service_create_from_profile.py`:

```python
# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from odoo.addons.quicksol_estate.services.agent_service import AgentService


class TestAgentServiceCreateFromProfile(TransactionCase):
    """Feature 025: AgentService.create_agent_from_profile()."""

    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"].create({"name": "Seed Company 025"})
        self.profile_type_agent = self.env["thedevkitchen.profile.type"].search(
            [("code", "=", "agent"), ("is_active", "=", True)], limit=1
        )
        self.profile = self.env["thedevkitchen.estate.profile"].create(
            {
                "name": "Seed Agent Profile",
                "company_id": self.company.id,
                "profile_type_id": self.profile_type_agent.id,
                "document": "11144477735",
                "email": "seed_agent_025@test.com",
                "birthdate": "1990-01-01",
            }
        )
        self.service = AgentService(self.env)

    def test_creates_bare_agent_from_profile_without_payload(self):
        agent = self.service.create_agent_from_profile(self.profile, agent_payload=None)
        self.assertEqual(agent.name, "Seed Agent Profile")
        self.assertEqual(agent.cpf, "11144477735")
        self.assertEqual(agent.email, "seed_agent_025@test.com")
        self.assertEqual(agent.company_id.id, self.company.id)
        self.assertFalse(agent.creci)

    def test_creates_agent_with_creci_and_bank_fields(self):
        agent = self.service.create_agent_from_profile(
            self.profile,
            agent_payload={
                "creci": "CRECI/SP 123456",
                "bank_name": "Banco Seed",
                "bank_account": "12345-6",
                "pix_key": "seed@pix.com",
            },
        )
        self.assertEqual(agent.creci_normalized, "CRECI/SP 123456")
        self.assertEqual(agent.bank_name, "Banco Seed")
        self.assertEqual(agent.bank_account, "12345-6")
        self.assertEqual(agent.pix_key, "seed@pix.com")

    def test_duplicate_creci_same_company_raises_validation_error(self):
        self.service.create_agent_from_profile(
            self.profile, agent_payload={"creci": "CRECI/SP 999999"}
        )
        other_profile = self.env["thedevkitchen.estate.profile"].create(
            {
                "name": "Seed Agent Profile 2",
                "company_id": self.company.id,
                "profile_type_id": self.profile_type_agent.id,
                "document": "52998224725",
                "email": "seed_agent_025_2@test.com",
                "birthdate": "1990-01-01",
            }
        )
        with self.assertRaises(ValidationError):
            self.service.create_agent_from_profile(
                other_profile, agent_payload={"creci": "CRECI/SP 999999"}
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec odoo /opt/odoo/odoo-bin --test-enable -i quicksol_estate --test-tags /quicksol_estate:TestAgentServiceCreateFromProfile --stop-after-init -d <your_dev_db>` (or the project's equivalent `-u quicksol_estate --test-enable` flow per `knowledge_base/testing.md`)
Expected: FAIL with `AttributeError: 'AgentService' object has no attribute 'create_agent_from_profile'`

- [ ] **Step 3: Add the method**

In `18.0/extra-addons/quicksol_estate/services/agent_service.py`, add this method to the existing `AgentService` class (place it right after `create_agent`, i.e. after line 60, before `update_agent`):

```python
    def create_agent_from_profile(self, profile_record, agent_payload=None):
        """Feature 025: create a real.estate.agent linked to an existing profile.

        Cadastral fields (name, cpf, email, phone, mobile, company_id, hire_date)
        are sourced from the profile via real.estate.agent.create()'s existing
        setdefault() sync (models/agent.py:436-470). Only agent-specific fields
        (creci, bank data) come from agent_payload. CRECI format/uniqueness is
        enforced by the model's own _check_creci_format constraint — not
        duplicated here, unlike create_agent()'s legacy pre-check.
        """
        agent_payload = agent_payload or {}
        vals = {"profile_id": profile_record.id}

        for field in ("creci", "hire_date", "bank_name", "bank_account", "pix_key"):
            if agent_payload.get(field) is not None:
                vals[field] = agent_payload[field]

        agent = self.Agent.create(vals)
        _logger.info(
            "Created agent %s (ID: %s) from profile %s",
            agent.name,
            agent.id,
            profile_record.id,
        )
        return agent
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: 3 tests pass (bare creation, creci+bank fields, duplicate-CRECI ValidationError).

- [ ] **Step 5: Lint**

Run: `cd 18.0 && ./lint.sh extra-addons/quicksol_estate/services/agent_service.py extra-addons/quicksol_estate/tests/unit/test_agent_service_create_from_profile.py`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/services/agent_service.py 18.0/extra-addons/quicksol_estate/tests/unit/test_agent_service_create_from_profile.py
git commit -m "feat(quicksol_estate): add AgentService.create_agent_from_profile for unified invite flow"
```

---

### Task 3: Wire the unified agent creation into `invite_user`

**Files:**
- Modify: `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py:12` (add two imports), `:97-146` (insert agent-creation branch + response fields)

**Interfaces:**
- Consumes: `SchemaValidator.validate_agent_invite_extra` (Task 1), `AgentService.create_agent_from_profile` (Task 2).
- Produces: `POST /api/v1/users/invite` response now includes `data.agent_id` and `links.agent` when the invited profile is `agent`-typed. Consumed by Task 4 (integration tests).

- [ ] **Step 1: Add imports**

In `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py`, after line 12 (`from odoo.addons.quicksol_estate.services.role_resolver import resolve_role`), add:

```python
from odoo.addons.quicksol_estate.controllers.utils.schema import SchemaValidator
from odoo.addons.quicksol_estate.services.agent_service import AgentService
```

- [ ] **Step 2: Insert the agent-creation branch**

Replace lines 97-114 (from `# Feature 010: Create user from profile (unified flow - no dual records)` through the `raw_token, token_record = token_service.generate_token(...)` call) with:

```python
            # Feature 010: Create user from profile (unified flow - no dual records)
            try:
                user = invite_service.create_user_from_profile(
                    profile_record=profile_record,
                    created_by=current_user
                )
            except ValidationError as e:
                if "already exists" in str(e):
                    field = "cpf" if "CPF" in str(e) else "email"
                    return self._error_response(
                        409, "conflict", str(e), {"field": field}
                    )
                return self._error_response(400, "validation_error", str(e))

            # Feature 025: when the invited profile is 'agent'-typed, create the
            # real.estate.agent record in the same transaction as the res.users
            # above. This closes a gap where invite-created agents previously
            # got login access but no domain record (no CRECI/commission data).
            agent_id = None
            if profile_type == "agent":
                agent_payload = data.get("agent") or {}
                is_valid, errors = SchemaValidator.validate_agent_invite_extra(
                    agent_payload
                )
                if not is_valid:
                    return self._error_response(
                        400, "validation_error", ", ".join(errors)
                    )

                agent_service = AgentService(request.env.sudo())
                try:
                    agent = agent_service.create_agent_from_profile(
                        profile_record, agent_payload
                    )
                    agent_id = agent.id
                except ValidationError as e:
                    # The res.users above and the partial agent insert are both
                    # still uncommitted at this point — roll back explicitly so
                    # a CRECI conflict doesn't leave an orphaned user account
                    # (matches the request.env.cr.rollback() pattern already
                    # used in thedevkitchen_estate_goals/controllers/goals_controller.py:143).
                    request.env.cr.rollback()
                    if "já cadastrado" in str(e):
                        return self._error_response(
                            409, "conflict", str(e), {"field": "creci"}
                        )
                    return self._error_response(400, "validation_error", str(e))

            # Generate invite token
            raw_token, token_record = token_service.generate_token(
                user=user, token_type="invite", company=company, created_by=current_user
            )
```

- [ ] **Step 3: Add `agent_id` to the response body and `agent` link**

Replace the `response_data` dict (lines 128-146 in the original) with:

```python
            # Build response data (Feature 010: no dual records, just user + profile link)
            response_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "document": profile_record.document,
                "profile": profile_type,
                "profile_id": profile_id,
                "signup_pending": user.signup_pending,
                "invite_sent_at": (
                    token_record.create_date.isoformat()
                    if token_record.create_date
                    else None
                ),
                "invite_expires_at": (
                    token_record.expires_at.isoformat()
                    if token_record.expires_at
                    else None
                ),
            }
            if agent_id:
                response_data["agent_id"] = agent_id

            # Add email status if failed
            if not email_sent:
                response_data["email_status"] = "failed"

            # Build HATEOAS links (as dict for easier access in tests)
            links = {
                "self": f"/api/v1/users/{user.id}",
                "resend_invite": f"/api/v1/users/{user.id}/resend-invite",
                "collection": "/api/v1/users",
                "profile": f"/api/v1/profiles/{profile_id}",
            }
            if agent_id:
                links["agent"] = f"/api/v1/agents/{agent_id}"
```

- [ ] **Step 4: Lint**

Run: `cd 18.0 && ./lint.sh extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add 18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py
git commit -m "feat(user_onboarding): create real.estate.agent atomically during agent-profile invite"
```

(This task has no standalone unit test — `invite_user` reads `request.httprequest.data` directly, so it can only be exercised through a real HTTP request. Task 4 provides the executable coverage via curl-based integration tests, consistent with this project's documented HttpCase read-only-transaction limitation.)

---

### Task 4: Integration tests for the unified invite flow

**Files:**
- Create: `integration_tests/test_feature_025_agent_invite_unification.sh`

**Interfaces:**
- Consumes: `POST /api/v1/profiles`, `POST /api/v1/users/invite` (as modified by Task 3), `lib/get_oauth2_token.sh` (existing OAuth2 helper), `18.0/.env` (existing env vars: `BASE_URL`, seed admin credentials).

- [ ] **Step 1: Write the test script**

Create `integration_tests/test_feature_025_agent_invite_unification.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
source "${SCRIPT_DIR}/../18.0/.env"

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="${BASE_URL}/api/v1"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

TOTAL=0
PASSED=0
FAILED=0

pass() { PASSED=$((PASSED+1)); TOTAL=$((TOTAL+1)); echo -e "${GREEN}PASS${NC}: $1"; }
fail() { FAILED=$((FAILED+1)); TOTAL=$((TOTAL+1)); echo -e "${RED}FAIL${NC}: $1 - $2"; }

echo "=== Feature 025: Agent Invite Unification ==="

bearer=$(get_oauth2_token)
session_id="${SEED_ADMIN_SESSION_ID:-}"

# --- Setup: create a company and a manager user to act as the requester ---
company_resp=$(curl -s -X POST "${API_BASE}/companies" \
  -H "Authorization: Bearer ${bearer}" -H "Content-Type: application/json" \
  -d '{"name": "Seed Company 025 A"}')
company_a_id=$(echo "$company_resp" | jq -r '.data.id // empty')

company_b_resp=$(curl -s -X POST "${API_BASE}/companies" \
  -H "Authorization: Bearer ${bearer}" -H "Content-Type: application/json" \
  -d '{"name": "Seed Company 025 B"}')
company_b_id=$(echo "$company_b_resp" | jq -r '.data.id // empty')

AGENT_PROFILE_TYPE_ID=$(curl -s "${API_BASE}/profile-types?code=agent" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" | jq -r '.data[0].id // empty')

create_profile() {
  local company_id=$1 name=$2 doc=$3 email=$4
  curl -s -X POST "${API_BASE}/profiles" \
    -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_id}" -H "Content-Type: application/json" \
    -d "{\"name\": \"${name}\", \"company_id\": ${company_id}, \"document\": \"${doc}\", \"email\": \"${email}\", \"birthdate\": \"1990-01-01\", \"profile_type_id\": ${AGENT_PROFILE_TYPE_ID}}" \
    | jq -r '.data.id // empty'
}

# --- Test 1: happy path — agent object with CRECI + bank fields ---
profile_id=$(create_profile "$company_a_id" "Seed Agent 025 Happy" "11144477735" "seed_agent_025_happy@test.com")
response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/users/invite" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"profile_id\": ${profile_id}, \"agent\": {\"creci\": \"CRECI/SP 100001\", \"bank_name\": \"Banco Seed\"}}")
status=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
agent_id=$(echo "$body" | jq -r '.data.agent_id // empty')
if [[ "$status" == "201" && -n "$agent_id" ]]; then
  pass "happy path: 201 with agent_id present"
else
  fail "happy path" "status=$status body=$body"
fi

# --- Test 2: invalid CRECI format → 400, no records created ---
profile_id=$(create_profile "$company_a_id" "Seed Agent 025 BadCreci" "52998224725" "seed_agent_025_badcreci@test.com")
response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/users/invite" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"profile_id\": ${profile_id}, \"agent\": {\"creci\": \"ab\"}}")
status=$(echo "$response" | tail -n1)
if [[ "$status" == "400" ]]; then
  pass "invalid CRECI: 400"
else
  fail "invalid CRECI" "expected 400, got $status"
fi

# --- Test 3: duplicate CRECI in same company → 409, no orphaned user ---
profile_id=$(create_profile "$company_a_id" "Seed Agent 025 DupCreci" "39053344705" "seed_agent_025_dupcreci@test.com")
response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/users/invite" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"profile_id\": ${profile_id}, \"agent\": {\"creci\": \"CRECI/SP 100001\"}}")
status=$(echo "$response" | tail -n1)
if [[ "$status" == "409" ]]; then
  pass "duplicate CRECI: 409"
else
  fail "duplicate CRECI" "expected 409, got $status"
fi
user_check=$(curl -s "${API_BASE}/users?email=seed_agent_025_dupcreci@test.com" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" | jq -r '.data | length')
if [[ "$user_check" == "0" ]]; then
  pass "duplicate CRECI: no orphaned res.users (atomic rollback verified)"
else
  fail "duplicate CRECI atomicity" "expected 0 users, found $user_check"
fi

# --- Test 4: agent profile, no agent object → bare agent still created (bug fix) ---
profile_id=$(create_profile "$company_a_id" "Seed Agent 025 Bare" "16559916640" "seed_agent_025_bare@test.com")
response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/users/invite" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"profile_id\": ${profile_id}}")
status=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
agent_id=$(echo "$body" | jq -r '.data.agent_id // empty')
if [[ "$status" == "201" && -n "$agent_id" ]]; then
  pass "no agent object: bare agent still created"
else
  fail "no agent object" "status=$status body=$body"
fi

# --- Test 5: cross-company profile → 404 ---
profile_id_b=$(create_profile "$company_b_id" "Seed Agent 025 CrossCo" "72741791625" "seed_agent_025_crossco@test.com")
response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/users/invite" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"profile_id\": ${profile_id_b}}")
status=$(echo "$response" | tail -n1)
if [[ "$status" == "404" ]]; then
  pass "cross-company profile: 404"
else
  fail "cross-company profile" "expected 404, got $status"
fi

echo ""
echo "=== Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed ==="
[[ "$FAILED" -eq 0 ]] && exit 0 || exit 1
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x integration_tests/test_feature_025_agent_invite_unification.sh`

- [ ] **Step 3: Run it against a local dev stack**

Run: `cd 18.0 && docker compose up -d && cd .. && ./integration_tests/test_feature_025_agent_invite_unification.sh`
Expected: `=== Results: 6/6 passed, 0 failed ===` (once Tasks 1-3 are in place; before them, expect failures on the `agent_id` assertions)

- [ ] **Step 4: Commit**

```bash
git add integration_tests/test_feature_025_agent_invite_unification.sh
git commit -m "test(integration): add E2E coverage for unified agent invite flow"
```

*(Note: this script assumes `POST /api/v1/companies` and `GET /api/v1/profile-types` endpoints exist per the project's existing API surface — confirm exact paths/params against `knowledge_base/api-surface.md` when executing this task; adjust the two setup calls if the real paths differ, everything after profile/invite creation is unaffected.)*

---

### Task 5: Deprecate `POST /api/v1/agents` (headers only, no behavior change)

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/agent_api.py:178-322`

**Interfaces:**
- Produces: `POST /api/v1/agents` responses (success and error) now include `Deprecation: true` and `Sunset: <date>` headers. Behavior/body otherwise byte-for-byte unchanged (FR5.3).

- [ ] **Step 1: Write the failing test (curl-based, appended to an existing agent test script)**

Add to `integration_tests/test_feature_025_agent_invite_unification.sh` (append before the final `echo "=== Results"` block):

```bash
# --- Test 6: create_agent (legacy) carries deprecation headers, behavior unchanged ---
legacy_headers=$(curl -s -D - -o /dev/null -X POST "${API_BASE}/agents" \
  -H "Authorization: Bearer ${bearer}" -H "X-Company-ID: ${company_a_id}" -H "Content-Type: application/json" \
  -d "{\"name\": \"Seed Legacy Agent 025\", \"cpf\": \"36745238864\", \"email\": \"seed_legacy_025@test.com\", \"company_id\": ${company_a_id}}")
if echo "$legacy_headers" | grep -qi "^Deprecation: true" && echo "$legacy_headers" | grep -qi "^Sunset:"; then
  pass "create_agent: Deprecation + Sunset headers present"
else
  fail "create_agent deprecation headers" "headers were: $legacy_headers"
fi
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./integration_tests/test_feature_025_agent_invite_unification.sh`
Expected: Test 6 fails (`FAIL: create_agent: Deprecation + Sunset headers present`) — headers not yet present.

- [ ] **Step 3: Wrap `create_agent` with a thin header-adding shim**

In `18.0/extra-addons/quicksol_estate/controllers/agent_api.py`, rename the existing decorated method to a private helper and add a thin public wrapper carrying the route/decorators, so the original 178-322 body is preserved verbatim inside the new private method:

Replace lines 178-191 (the `@http.route(...)` block through `def create_agent(self, **kwargs):  # noqa: C901 ...`) with:

```python
    @http.route(
        "/api/v1/agents",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def create_agent(self, **kwargs):
        """Feature 025: deprecated in favor of POST /api/v1/profiles +
        POST /api/v1/users/invite (see specs/025-agent-invite-unification).
        Behavior below is intentionally left untouched; only deprecation
        headers are added. Scheduled for removal — see spec-idea.md FR6."""
        response = self._create_agent_legacy(**kwargs)
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Wed, 16 Jan 2027 00:00:00 GMT"
        return response

    def _create_agent_legacy(
        self, **kwargs
    ):  # noqa: C901 - legacy endpoint, keep behavior stable
```

Everything from the original `try:` block (previously line 192) through the original method's final `except Exception as e:` block (previously ending at line 322, right before the next `@http.route` at line 323) stays exactly as-is, now indented under `_create_agent_legacy` instead of `create_agent`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./integration_tests/test_feature_025_agent_invite_unification.sh`
Expected: `=== Results: 7/7 passed, 0 failed ===`, and re-run the project's existing `create_agent` test suite (e.g. `18.0/extra-addons/quicksol_estate/tests/integration/test_agent_crud.py` and `test_rbac_agent.py`) to confirm zero regressions:

Run: `docker compose exec odoo /opt/odoo/odoo-bin --test-enable -i quicksol_estate --stop-after-init -d <your_dev_db>`
Expected: all pre-existing `agent_api` tests still pass unmodified.

- [ ] **Step 5: Lint**

Run: `cd 18.0 && ./lint.sh extra-addons/quicksol_estate/controllers/agent_api.py`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add 18.0/extra-addons/quicksol_estate/controllers/agent_api.py integration_tests/test_feature_025_agent_invite_unification.sh
git commit -m "feat(quicksol_estate): add Deprecation/Sunset headers to legacy create_agent endpoint"
```

---

### Task 6: `deprecated` field on `thedevkitchen.api.endpoint` + Swagger generator support

**Files:**
- Modify: `18.0/extra-addons/thedevkitchen_apigateway/models/api_endpoint.py` (add field)
- Modify: `18.0/extra-addons/thedevkitchen_apigateway/controllers/swagger_controller.py:140` (surface the flag in generated OpenAPI)
- Modify: `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml:4344-4374` (mark the `create_agent` record deprecated + update its description)
- Modify: `18.0/extra-addons/thedevkitchen_user_onboarding/data/api_endpoints_data.xml:11-78` (document the new optional `agent` object on the invite endpoint)

**Interfaces:**
- Produces: `GET /api/v1/openapi.json`'s operation for `POST /api/v1/agents` includes `"deprecated": true`; the invite endpoint's documented request schema includes the optional `agent` object.

- [ ] **Step 1: Add the `deprecated` field to the registry model**

In `18.0/extra-addons/thedevkitchen_apigateway/models/api_endpoint.py`, add after the existing `active` field (line 19):

```python
    deprecated = fields.Boolean(
        string="Deprecated",
        default=False,
        help="If True, this endpoint is marked deprecated in the generated OpenAPI spec.",
    )
```

- [ ] **Step 2: Surface it in the Swagger generator**

In `18.0/extra-addons/thedevkitchen_apigateway/controllers/swagger_controller.py`, immediately after line 171 (`operation["security"] = []`, still inside the `if not endpoint.protected:` block's enclosing scope), add:

```python
            # Add security if protected
            if not endpoint.protected:
                operation["security"] = []

            # Feature 025: surface deprecation flag for endpoints scheduled for removal
            if endpoint.deprecated:
                operation["deprecated"] = True

            spec["paths"][path][method] = operation
```

(This replaces the block at lines 169-173, inserting the two new lines between the existing `security` check and the final `spec["paths"][path][method] = operation` assignment.)

- [ ] **Step 3: Mark the `create_agent` registry record deprecated**

In `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml`, replace the `<record id="api_endpoint_create_agent" ...>` block (lines 4344-4374) with:

```xml
        <record id="api_endpoint_create_agent" model="thedevkitchen.api.endpoint">
            <field name="name">Create Agent</field>
            <field name="path">/api/v1/agents</field>
            <field name="method">POST</field>
            <field name="module_name">quicksol_estate</field>
            <field name="protected" eval="True"/>
            <field name="tags">Agents</field>
            <field name="summary">Create a new agent</field>
            <field name="description">**DEPRECATED (Feature 025):** use POST /api/v1/profiles followed by POST /api/v1/users/invite instead, which now applies the same CRECI/bank-field validation when the invited profile is of type "agent". This endpoint is scheduled for removal — see specs/025-agent-invite-unification/spec-idea.md.

Creates a new real estate agent with CRECI registration and commission configuration.

Required fields:
- name (string): Agent's full name (3-255 characters)
- cpf (string): Brazilian CPF document (11 digits, format: 123.456.789-01 or 12345678901)
- company_id (integer): ID of the real estate company the agent will belong to. Required for multi-tenancy.
- email (string): Email address (must contain @ and .). Required for account activation email.

Optional fields:
- phone (string): Phone number
- mobile (string): Mobile number
- creci (string): CRECI registration number (minimum 4 characters, format: CRECI-SP 12345)
- hire_date (string): Hire date in ISO format (YYYY-MM-DD)
- bank_name (string): Bank name for commission payments
- bank_account (string): Bank account number
- pix_key (string): PIX key for payments

RBAC: Only managers and admins can create agents.
Multi-tenancy: Agent is linked to the specified company_id.

Returns: Agent object with id, name, cpf, email, creci, company_id, company_name, and HATEOAS links.</field>
            <field name="active" eval="True"/>
            <field name="deprecated" eval="True"/>
        </record>
```

- [ ] **Step 4: Document the optional `agent` object on the invite endpoint**

In `18.0/extra-addons/thedevkitchen_user_onboarding/data/api_endpoints_data.xml`, replace the `request_schema` field content (lines 44-57) with:

```xml
            <field name="request_schema"><![CDATA[
{
  "type": "object",
  "title": "InviteUserRequest",
  "required": ["profile_id"],
  "properties": {
    "profile_id": {"type": "integer", "example": 17},
    "agent": {
      "type": "object",
      "description": "Feature 025: optional, only used when the target profile's type is 'agent'. Ignored for all other profile types.",
      "properties": {
        "creci":        {"type": "string", "example": "CRECI/SP 123456"},
        "hire_date":    {"type": "string", "format": "date", "example": "2026-01-01"},
        "bank_name":    {"type": "string", "example": "Banco Seed"},
        "bank_account": {"type": "string", "example": "12345-6"},
        "pix_key":      {"type": "string", "example": "seed@pix.com"}
      }
    }
  }
}
]]></field>
```

Note this replaces the previous, stale `name`/`email`/`profile`/`cpf`/`phone` shape (lines 46-56 in the original) with the actual current contract (`profile_id` + optional `agent`) — the old schema no longer matched the Feature 010 unified-profile flow even before this change, so this also fixes a pre-existing documentation drift while making the required edit.

Also update the `description` field (lines 19-43) to append, right after the existing `**Error Responses:**` section:

```xml
            <field name="description">Sends an invitation email to a new user. Creates a pending user account with a secure invite token (UUID v4 → SHA-256).

**Authorization Matrix:**
- Owner → all 9 profiles
- Manager → 5 operational profiles (agent, prospector, receptionist, financial, inspector)
- Agent → owner + portal only

**Required Headers:**
- `Authorization: Bearer {jwt_token}`
- `X-Openerp-Session-Id: {session_id}`
- `X-Company-Id: {company_id}`

**Required Fields:**
- `profile_id`: ID of an existing thedevkitchen.estate.profile record (integer)

**Optional Fields:**
- `agent`: object with `creci`, `hire_date`, `bank_name`, `bank_account`, `pix_key` — only applied when the profile's type is "agent" (Feature 025). When omitted for an agent-typed profile, a bare real.estate.agent record is still created from the profile's existing cadastral data.

**Error Responses:**
- **400 Bad Request**: invalid JSON, missing `profile_id`, or invalid `agent` object (e.g. malformed CRECI)
- **403 Forbidden**: caller not authorized to invite target profile type
- **404 Not Found**: profile not found or belongs to a different company
- **409 Conflict**: profile already has a linked user, or `agent.creci` already registered in this company</field>
```

- [ ] **Step 5: Run test to verify the OpenAPI spec reflects both changes**

Run: `docker compose up -d && docker compose exec odoo /opt/odoo/odoo-bin -u thedevkitchen_apigateway,quicksol_estate,thedevkitchen_user_onboarding --stop-after-init -d <your_dev_db>` (to reload the data files), then:

```bash
curl -s http://localhost:8069/api/v1/openapi.json | jq '.paths["/api/v1/agents"].post.deprecated'
```
Expected: `true`

```bash
curl -s http://localhost:8069/api/v1/openapi.json | jq '.paths["/api/v1/users/invite"].post.requestBody.content["application/json"].schema.properties.agent'
```
Expected: the `agent` object schema, non-null

- [ ] **Step 6: Lint**

Run: `cd 18.0 && ./lint_xml.sh extra-addons/quicksol_estate/data/api_endpoints.xml extra-addons/thedevkitchen_user_onboarding/data/api_endpoints_data.xml && ./lint.sh extra-addons/thedevkitchen_apigateway/models/api_endpoint.py extra-addons/thedevkitchen_apigateway/controllers/swagger_controller.py`
Expected: no errors

- [ ] **Step 7: Commit**

```bash
git add 18.0/extra-addons/thedevkitchen_apigateway/models/api_endpoint.py 18.0/extra-addons/thedevkitchen_apigateway/controllers/swagger_controller.py 18.0/extra-addons/quicksol_estate/data/api_endpoints.xml 18.0/extra-addons/thedevkitchen_user_onboarding/data/api_endpoints_data.xml
git commit -m "docs(api): mark create_agent deprecated in OpenAPI, document unified invite agent object"
```

---

### Task 7: Update the Postman collection (deprecation window)

**Files:**
- Modify: Postman collection JSON (path per this project's convention, see `.claude/skills/postman-collection-manager/SKILL.md` — typically `docs/postman/*.postman_collection.json`)

- [ ] **Step 1: Invoke the `postman-collection-manager` skill**

Run the `postman-collection-manager` skill with this instruction: "In the 'Agents' folder, rename the existing 'Create Agent' request to '[DEPRECATED] Create Agent (legacy)' and prepend a note in its description pointing to the unified invite flow. In the 'User Onboarding' folder, add a new request 'Invite Agent (recommended)' demonstrating `POST /api/v1/users/invite` with `profile_id` + the optional nested `agent` object (`creci`, `hire_date`, `bank_name`, `bank_account`, `pix_key`), following ADR-016 conventions (`X-Openerp-Session-Id` header, no JSON-RPC envelope, OAuth token auto-save script already present at the collection root)." Bump the collection version per ADR-016.

- [ ] **Step 2: Verify**

Confirm the regenerated collection file has the renamed legacy request and the new recommended request, and that `newman run` (or the project's existing Postman validation step, if any) still passes against the collection's own internal consistency checks.

- [ ] **Step 3: Commit**

```bash
git add <postman collection file path>
git commit -m "docs(postman): relabel legacy create-agent request, add unified invite-agent example"
```

---

### Task 8 (GATED — do not execute until preconditions below are met): Remove `POST /api/v1/agents`

**Do not run this task's steps as part of the same implementation pass as Tasks 1-7.** Per `spec-idea.md`'s User Story 4, execute this task only once:
1. Tasks 1-7 have been deployed and validated in production for at least one full release cycle, and
2. A check of the `thedevkitchen_apigateway` API access log shows negligible/zero production traffic on `POST /api/v1/agents`, or the team has explicitly accepted the migration risk for remaining callers.

**Files:**
- Modify: `18.0/extra-addons/quicksol_estate/controllers/agent_api.py` (delete `create_agent` + `_create_agent_legacy`, and their `@http.route`)
- Modify: `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml` (delete the `api_endpoint_create_agent` record)
- Delete: `18.0/extra-addons/quicksol_estate/tests/integration/test_agent_crud.py`, `18.0/extra-addons/quicksol_estate/tests/integration/test_rbac_agent.py` (or whichever test files exclusively cover `create_agent` — confirm no shared coverage with other agent endpoints like `PATCH`/`GET`/`DELETE /api/v1/agents/{id}` before deleting; only delete tests scoped to the POST-creation route)
- Modify: Postman collection (delete the legacy request)

- [ ] **Step 1: Delete the route and controller methods**

In `18.0/extra-addons/quicksol_estate/controllers/agent_api.py`, delete the entire `create_agent` wrapper (added in Task 5) and the `_create_agent_legacy` method (the original body) in full — both the `@http.route(...)` decorator block and the method bodies.

- [ ] **Step 2: Delete the registry record**

In `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml`, delete the `<record id="api_endpoint_create_agent" ...>` block entirely.

- [ ] **Step 3: Delete superseded tests**

Delete any test file/test case exclusively exercising `POST /api/v1/agents` creation (not shared with `GET`/`PATCH`/`DELETE /api/v1/agents/*`, which remain).

- [ ] **Step 4: Run test to verify removal**

Run: `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8069/api/v1/agents -H "Content-Type: application/json" -d '{}'`
Expected: `404`

Run: `curl -s http://localhost:8069/api/v1/openapi.json | jq '.paths["/api/v1/agents"].post // "absent"'`
Expected: `"absent"`

- [ ] **Step 5: Update Postman via the skill**

Run the `postman-collection-manager` skill with instruction: "Delete the '[DEPRECATED] Create Agent (legacy)' request from the 'Agents' folder entirely; the 'Invite Agent (recommended)' request is now the only agent-creation path documented."

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore(quicksol_estate): remove deprecated POST /api/v1/agents endpoint (Feature 025 Phase 5)"
```

---

## Self-Review Notes

- **Spec coverage**: FR1 (Task 1), FR2 (Task 2+3), FR3 (Task 3), FR4 (no code change needed — `INVITE_AUTHORIZATION`/`PROFILE_TO_GROUP` already support `agent`, confirmed via direct code read), FR5 (Task 5+6), FR6 (Task 8, gated). User Stories 1/2/4 covered by Tasks 3-4, 5-6, 8 respectively. User Story 3 (resend-invite idempotency) required no code change — confirmed `resend_invite`'s existing logic doesn't touch agent creation, so it's already correct; no task needed.
- **Type consistency**: `AgentService.create_agent_from_profile(self, profile_record, agent_payload=None)` signature is used identically in Task 2's test and Task 3's controller call.
- **No placeholders**: every step shows exact code/XML/commands; the one open runtime uncertainty (exact `POST /api/v1/companies`/`GET /api/v1/profile-types` paths in Task 4's setup helpers) is flagged explicitly as something to confirm against `knowledge_base/api-surface.md` at execution time, since it's outside this feature's own changed files.
