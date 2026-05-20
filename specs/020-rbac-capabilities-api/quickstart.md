# Quickstart: RBAC Capabilities API

**Feature**: `020-rbac-capabilities-api`  
**Branch**: `020-rbac-capabilities-api`  
**Target module**: `quicksol_estate` (Odoo 18.0)  
**Date**: 2026-05-18

This guide walks implementers through the complete development workflow for the
`GET /api/v1/me/capabilities` endpoint from an empty branch to a passing test suite.

---

## Prerequisites

Before implementing, read:
- [`spec.md`](./spec.md) — authoritative requirements and acceptance criteria
- [`research.md`](./research.md) — all design decisions resolved
- [`data-model.md`](./data-model.md) — canonical ROLE_RULES matrix and virtual entity contract
- [`contracts/capabilities.yaml`](./contracts/capabilities.yaml) — OpenAPI 3.0 reference contract

Verify your working branch:
```bash
cd /opt/homebrew/var/www/realestate/odoo-docker
git checkout 020-rbac-capabilities-api
```

---

## Architecture at a Glance

```
GET /api/v1/me/capabilities
  ↓
quicksol_estate/controllers/capabilities_controller.py
  │  decorators: @require_jwt  @require_session  @require_company
  ↓
quicksol_estate/services/capability_service.py
  │  ROLE_RULES dict  +  ALLOWED_ACTIONS / ALLOWED_SUBJECTS whitelists
  ↓
{ "user": {...}, "rules": [...] }
```

No DB writes. No new models. No Swagger file edits.

---

## Step 1 — Create the Capability Service

**File**: `18.0/extra-addons/quicksol_estate/services/capability_service.py`

### Key implementation details

```python
# capability_service.py skeleton

ALLOWED_ACTIONS = {"view", "create", "update", "delete", "reassign", "approve", "cancel", "export"}

ALLOWED_SUBJECTS = {
    "MenuCRM", "MenuAdmin", "MenuCMS",
    "Dashboard", "Property", "Lead", "Service", "Proposal",
    "Agent", "Company", "Settings", "Appointment",
    "Report", "Goal", "CMSPage", "CMSMedia",
}

# Tuples in canonical declaration order (subject order × action order)
# See data-model.md for the full matrix.
ROLE_RULES: dict[str, list[tuple[str, str]]] = {
    "owner": [
        ("view", "MenuCRM"), ("view", "MenuAdmin"),
        ("view", "Dashboard"),
        ("view", "Property"), ("create", "Property"), ("update", "Property"), ("delete", "Property"),
        ("view", "Lead"), ("create", "Lead"), ("update", "Lead"), ("delete", "Lead"), ("reassign", "Lead"),
        ("view", "Service"), ("create", "Service"), ("update", "Service"), ("delete", "Service"), ("reassign", "Service"), ("cancel", "Service"),
        ("view", "Proposal"), ("create", "Proposal"), ("update", "Proposal"), ("delete", "Proposal"), ("approve", "Proposal"), ("cancel", "Proposal"),
        ("view", "Agent"), ("create", "Agent"), ("update", "Agent"), ("delete", "Agent"),
        ("view", "Company"), ("update", "Company"),
        ("view", "Settings"), ("update", "Settings"),
        ("view", "Report"), ("export", "Report"),
        ("view", "Goal"),
    ],
    # ... director, manager, agent, prospector, receptionist, financial, legal,
    #     property_owner, tenant  (see data-model.md for complete matrix)
}


class CapabilityService:
    def __init__(self, env):
        self.env = env

    def get_rules(self, role: str | None) -> list[dict]:
        """
        Return ordered, deduplicated list of CASL-safe rule dicts for the given role.
        Returns [] if role is None or unrecognised.
        Fails closed (omits rule) on whitelist violations.
        """
        if not role:
            return []

        declared = ROLE_RULES.get(role, [])
        seen: set[tuple[str, str]] = set()
        result = []

        for action, subject in declared:
            if action not in ALLOWED_ACTIONS or subject not in ALLOWED_SUBJECTS:
                continue  # fail closed (FR6.4)
            pair = (action, subject)
            if pair in seen:
                continue  # deduplicate (FR-015)
            seen.add(pair)
            result.append({"action": action, "subject": subject})

        return result
```

> **Ordering note**: `ROLE_RULES` lists are the sole source of order — do **not** apply
> `sorted()` at any point. Canonical order lives in the declaration, not in a sort key.

---

## Step 2 — Create the Controller

**File**: `18.0/extra-addons/quicksol_estate/controllers/capabilities_controller.py`

### Key implementation details

```python
# capabilities_controller.py skeleton

import logging
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt, require_session, require_company
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
from ..services.capability_service import CapabilityService

_logger = logging.getLogger(__name__)

ROLE_MAP = {
    'quicksol_estate.group_real_estate_owner':        'owner',
    'quicksol_estate.group_real_estate_director':     'director',
    'quicksol_estate.group_real_estate_manager':      'manager',
    'quicksol_estate.group_real_estate_agent':        'agent',
    'quicksol_estate.group_real_estate_prospector':   'prospector',
    'quicksol_estate.group_real_estate_receptionist': 'receptionist',
    'quicksol_estate.group_real_estate_financial':    'financial',
    'quicksol_estate.group_real_estate_legal':        'legal',
    'quicksol_estate.group_real_estate_property_owner': 'property_owner',
    'quicksol_estate.group_real_estate_tenant':       'tenant',
}


class CapabilitiesController(http.Controller):

    @http.route('/api/v1/me/capabilities', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    @trace_http_request
    def get_capabilities(self, **kwargs):
        try:
            user = request.env.user

            if not user or user.id == 4:
                return request.make_json_response({"error": "unauthorized"}, status=401)

            # Resolve effective role (same precedence as /api/v1/me)
            role = next(
                (role_name for xml_id, role_name in ROLE_MAP.items() if user.has_group(xml_id)),
                None
            )

            company_id = user.company_id.id if user.company_id else None

            service = CapabilityService(request.env)
            rules = service.get_rules(role)

            return request.make_json_response({
                "user": {
                    "id": user.id,
                    "role": role,
                    "company_id": company_id,
                },
                "rules": rules,
            })

        except Exception as e:
            _logger.error(f'Error in /api/v1/me/capabilities: {e}', exc_info=True)
            return request.make_json_response({"error": "internal_server_error"}, status=500)
```

> **Important**: The decorator stack order is `@require_jwt → @require_session → @require_company → @trace_http_request`.  
> **Do not** put `@require_company` after `@trace_http_request` — company context must be
> set before the controller body executes.

---

## Step 3 — Register the Controller

Update `18.0/extra-addons/quicksol_estate/controllers/__init__.py` to import the new controller:

```python
# Add to __init__.py:
from . import capabilities_controller
```

---

## Step 4 — Write Unit Tests

**File**: `18.0/extra-addons/quicksol_estate/tests/utils/test_capability_service.py`

Minimum required tests (spec-idea.md §User Story 1 & 2 test coverage):

```python
class TestCapabilityService(TestCase):
    def test_role_resolver_matches_me_endpoint_order(self): ...
    def test_capability_service_deduplicates_rules(self): ...
    def test_capability_service_omits_denied_rules(self): ...
    def test_capability_service_stable_sort_order(self): ...
    def test_only_whitelisted_subjects_are_serialized(self): ...
    def test_only_whitelisted_actions_are_serialized(self): ...
```

These tests run without an HTTP server — mock `env` and call `CapabilityService` directly.

---

## Step 5 — Write E2E API Tests

**File**: `18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py`

Minimum required tests:

```python
class TestCapabilitiesAPI(HttpCase):
    # Auth guards
    def test_get_capabilities_requires_jwt(self): ...           # → 401
    def test_get_capabilities_requires_session(self): ...       # → 401
    def test_get_capabilities_requires_company(self): ...       # → 403

    # Contract shape
    def test_get_capabilities_returns_user_and_rules_only(self): ...
    def test_user_object_has_exactly_id_role_company_id(self): ...

    # Role matrix
    def test_owner_receives_menu_admin_rule(self): ...
    def test_agent_does_not_receive_menu_admin_rule(self): ...
    def test_manager_receives_reassign_rules(self): ...
    def test_external_roles_receive_limited_rules(self): ...
    def test_all_ten_roles_matrix_smoke(self): ...

    # Isolation
    def test_capabilities_respects_active_company(self): ...
    def test_capabilities_cross_company_forbidden(self): ...
    def test_capabilities_no_cross_company_payload_leakage(self): ...

    # Non-leakage
    def test_no_internal_security_details_leak(self): ...

    # Regression guard
    def test_me_endpoint_contract_unchanged(self): ...
```

---

## Step 6 — Seed Data

Use the seed pattern from `spec-idea.md §Seed Data` to create the minimum required dataset:
- 2 companies (`seed_company_a`, `seed_company_b`)
- 10 users per company A (one per role), 3 minimum in company B for isolation checks
- 1 multi-role user (manager + agent) for resolver parity check

Seed code should live in a `@classmethod setUpClass` in the `HttpCase` or in a dedicated
`demo/` XML file if shared across test files.

---

## Step 7 — Run Tests

```bash
# From Docker host
cd /opt/homebrew/var/www/realestate/odoo-docker

# Capabilities unit tests
docker compose exec odoo python3 \
  /mnt/extra-addons/quicksol_estate/tests/unit/test_capability_service_unit.py

# Capabilities API tests
docker compose exec odoo python -m pytest \
  18.0/extra-addons/quicksol_estate/tests/api/test_capabilities_api.py -v

# Repository quality gate
cd 18.0 && ./lint.sh quicksol_estate
```

---

## Step 8 — Performance Gate (SC-005)

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
bash integration_tests/test_us020_s4_performance.sh
```

The script performs 100 sequential authenticated `GET /api/v1/me/capabilities`
requests and fails if p95 is `>= 1000 ms`.

---

## Step 9 — Swagger Registration (Post-Implementation)

After the implementation passes all tests, register the endpoint in Swagger via the
DB-backed workflow (do **not** edit static YAML files):

1. Keep the endpoint definition in `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml`.
2. Upgrade the `quicksol_estate` module so XML syncs into `thedevkitchen_api_endpoint`.
3. Verify the endpoint appears in `/api/docs`.

---

## Step 10 — Postman Collection

Use the collection version below for this feature:

```text
docs/postman/quicksol_api_v1.33_postman_collection.json
```

Keep `session_id` in `X-Openerp-Session-Id` for this GET request and include
`X-Company-ID` per ADR-016.

---

## Step 11 — Module Version Bump

In `18.0/extra-addons/quicksol_estate/__manifest__.py`:
```python
'version': '18.0.5.0.0',  # Feature 020: RBAC Capabilities API
```

---

## Checklist Before PR

- [ ] `capability_service.py` created with full `ROLE_RULES` matrix (all 10 roles)
- [ ] `capabilities_controller.py` created with triple decorator stack
- [ ] Controller registered in `controllers/__init__.py`
- [ ] Unit tests pass: deduplication, ordering, omission, whitelist
- [ ] E2E API tests pass: 10-role matrix, 401/403 guards, multi-company isolation
- [ ] Performance script passes: `integration_tests/test_us020_s4_performance.sh`
- [ ] `/api/v1/me` regression test passes (contract unchanged)
- [ ] No XML IDs / Odoo internals appear in any response payload
- [ ] `quicksol_estate` version bumped to `18.0.5.0.0`
- [ ] Swagger updated via XML → module upgrade → DB → `/api/docs`
- [ ] Postman collection updated to `quicksol_api_v1.33_postman_collection.json`
- [ ] Linting: `ruff` + `black` passing (`./lint.sh`)
- [ ] No Cypress tests added (API-only feature)
