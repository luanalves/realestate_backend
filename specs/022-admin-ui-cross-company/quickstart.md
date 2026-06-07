# Quickstart: Admin UI — Cross-Company Access for System Admin

**Feature**: 022-admin-ui-cross-company  
**Date**: 2026-06-03

---

## Prerequisites

- Docker services running: `cd 18.0 && docker compose up -d`
- Admin credentials: `admin` / `admin` (default)
- At least two tenant companies exist in the database with real estate data
- `jq` installed locally for integration test assertions

---

## 1. Apply the changes

### 1a. Security XML files (record rule overrides)

Modify the 7 security XML files listed in `plan.md → Source Code`. Each file gets `[(1,'=',1)]` rules for `base.group_system`. Files with `noupdate="1"` get a new `<data noupdate="0">` block appended; files with `noupdate="0"` get rules appended inside the existing block.

### 1b. Menu file

In `18.0/extra-addons/quicksol_estate/views/real_estate_menus.xml`, line 9, add `base.group_system` to the `menu_real_estate_lead` groups attribute:

```xml
<!-- Before -->
groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager"

<!-- After -->
groups="quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_manager,base.group_system"
```

### 1c. Controller guard

In `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py`, after the `if not user.active` block (line ~73), insert:

```python
# Block System Admin from REST API (ADR-009, FR-004)
# Anti-enumeration: return 401 identical to bad-credential response (clarification 2026-06-03)
if user.has_group('base.group_system'):
    _logger.warning(f"Admin login attempt via API blocked: {email}")
    AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')
    return request.make_json_response(
        {'error': {'status': 401, 'message': 'Invalid credentials'}},
        status=401
    )
```

### 1d. Documentation

- Create `docs/adr/ADR-029-saas-admin-channel-separation.md`
- Create `knowledge_base/13-saas-admin-module-checklist.md`

---

## 2. Upgrade affected modules

```bash
cd 18.0
docker compose exec odoo bash -c "
  odoo --update quicksol_estate,thedevkitchen_cms,thedevkitchen_estate_goals,\
thedevkitchen_estate_credit_check,thedevkitchen_user_onboarding \
  --stop-after-init -d realestate
"
```

Or via the Odoo UI: **Settings → Apps → Upgrade** for each module.

---

## 3. Verify cross-company visibility (Odoo UI)

1. Log in to `http://localhost:8069` as `admin` / `admin`
2. Navigate to **Real Estate → Properties**
3. Confirm properties from **all companies** appear (not filtered to one company)
4. Repeat for: Leads, Agents, Leases, Sales, Commission Rules
5. Confirm the **Leads** menu is now visible (was previously hidden)

---

## 4. Verify API login block

```bash
# Should return 401
curl -s -w "\nHTTP:%{http_code}" -X POST "http://localhost:8069/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@localhost", "password": "admin"}'
# Expected: HTTP:401 with {"error":{"status":401,"message":"Invalid credentials"}}

# Business user should still work
curl -s -w "\nHTTP:%{http_code}" -X POST "http://localhost:8069/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@yourcompany.com", "password": "ownerpassword"}'
# Expected: HTTP:200 with session data
```

---

## 5. Run automated tests

```bash
# E2E (Cypress) — requires Odoo running
cd /opt/homebrew/var/www/realestate/realestate_backend
npx cypress run --spec "cypress/e2e/views/admin_cross_company.cy.js"

# Integration test (API block — FR-004/SC-004)
BASE_URL=http://localhost:8069 bash integration_tests/test_admin_api_block.sh

# Integration test (FR-007 verification — admin invite blocked by Feature 009)
BASE_URL=http://localhost:8069 bash integration_tests/test_admin_invite_block.sh
```

---

## Rollback

To revert, remove the appended `<data noupdate="0">` blocks and the menu attribute change, then upgrade the modules again. The controller guard can be reverted with a Git checkout. No database migration rollback is needed — `ir.rule` records are data, not schema.
