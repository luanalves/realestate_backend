# Quickstart Guide: Feature 011 — Company–Odoo Integration

**Phase 1 output** | **Date**: 2026-03-02

## Purpose

Step-by-step developer guide for implementing the migration of `thedevkitchen.estate.company` → `res.company` (via `_inherit`). Follow phases in order — each phase builds on the previous.

---

## Prerequisites

```bash
cd 18.0
docker compose up -d          # PostgreSQL + Redis + Odoo running
docker compose exec db psql -U odoo -d realestate  # Verify DB access
```

**Branch**: `011-company-odoo-integration` (already created)

---

## Implementation Phases

### Phase A: Foundation (res.company extension + field migration)

**Goal**: Create the `_inherit = 'res.company'` model with real estate fields, leaving all other code untouched.

1. **Rewrite `company.py`**
   - Replace the standalone `thedevkitchen.estate.company` model with `_inherit = 'res.company'`
   - Add discriminator `is_real_estate = fields.Boolean(default=False)`
   - Move custom fields: `cnpj`, `creci`, `legal_name`, `foundation_date`, `description`
   - Move computed fields: `property_count`, `agent_count`, `tenant_count`, `lease_count`
   - Preserve CNPJ validation (`_check_cnpj`) and `_sql_constraints`
   - **Do NOT change** the `_name` — it stays as `res.company` via inheritance

2. **Delete `state.py`**
   - Remove the `real.estate.state` model entirely
   - All references to `real.estate.state` will be migrated to `res.country.state`

3. **Update `__manifest__.py`**
   - Remove `real.estate.state` seed data file from `data` list
   - Add any new data files if needed
   - Verify `depends` includes `'base'` (provides `res.company`, `res.country.state`)

4. **Write migration script** (optional — dev environment uses `reset_db.sh`)
   - Data migration for `is_real_estate=True` flagging on existing companies
   - Transfer custom field data from `thedevkitchen_estate_company` → `res_company`

**Validation**: `docker compose restart odoo && docker compose logs -f odoo` — module loads without errors.

---

### Phase B: Model Relations (M2M → M2O + comodel changes)

**Goal**: Update all business models to use `company_id = Many2one('res.company')` and `state_id → res.country.state`.

1. **Update fields on each model** (see `data-model.md` for full table):

   | Model | Change |
   |-------|--------|
   | `real.estate.property` | Drop `company_ids` M2M, keep/add `company_id` M2O → `res.company` |
   | `real.estate.lease` | Drop `company_ids` M2M, add `company_id` M2O → `res.company` |
   | `real.estate.lead` | Drop `company_ids` M2M, add `company_id` M2O → `res.company` |
   | `real.estate.sale` | Drop `company_ids` M2M, change existing `company_id` M2O comodel |
   | `real.estate.agent` | Drop `company_ids` M2M, change `company_id` M2O comodel |
   | `real.estate.commission.rule` | Change `company_id` M2O comodel |
   | `real.estate.commission.transaction` | Change `company_id` M2O comodel |
   | `thedevkitchen.estate.profile` | Change `company_id` M2O comodel |
   | `real.estate.property.assignment` | Change `company_id` M2O comodel |

2. **Update `state_id` comodel** on:
   - `real.estate.property` → `state_id = Many2one('res.country.state')`
   - `real.estate.property.owner` → `state_id = Many2one('res.country.state')`
   - `real.estate.building` → `state_id = Many2one('res.country.state')`

3. **Update `agent.py`** specifically:
   - Remove deprecated `company_ids` M2M field
   - Change `company_id` comodel to `res.company`
   - Update `_onchange_user_id()`: read from `user.company_ids` (native) instead of `user.estate_company_ids`
   - Update `create()` / `write()` overrides
   - Adjust SQL constraint if needed

4. **Update `res_users.py`**:
   - Remove `estate_company_ids` M2M field
   - Remove `main_estate_company_id` M2O field
   - Remove `owner_company_ids` computed field
   - Update `write()` agent sync to use native `company_ids`

**Validation**: `python -m pytest` — model-level unit tests pass. DB schema correct (no M2M tables remain).

---

### Phase C: Security Layer (record rules + middleware)

**Goal**: Migrate all record rules to native pattern and update middleware.

1. **Rewrite `record_rules.xml`**:
   - Replace all `[('company_ids', 'in', user.estate_company_ids.ids)]` with `[('company_id', 'in', company_ids)]`
   - Replace all `[('id', 'in', user.estate_company_ids.ids)]` with `[('is_real_estate', '=', True), ('id', 'in', company_ids)]`
   - Note: `company_ids` (unqualified) in record rule domains refers to Odoo's magic variable resolving `user.company_ids.ids`

2. **Rewrite `middleware.py` (`require_company`)**:
   - Read from `user.company_ids` instead of `user.estate_company_ids`
   - Validate `company.is_real_estate == True`
   - Call `request.update_env(company=company_id)` (native context propagation)
   - Keep `request.user_company_ids` for backward compatibility

3. **Update `ir.model.access.csv`**:
   - Remove ACL rows for `thedevkitchen.estate.company` and `real.estate.state`
   - Verify `res.company` ACLs are adequate (usually native)

4. **Update observer** (`user_company_validator_observer.py`):
   - Validate writes to `company_ids` (native) instead of `estate_company_ids`
   - Keep same validation logic (prevent unauthorized company association)

**Validation**: `docker compose restart odoo` — no access rule errors in logs. Manual test: login, verify company isolation.

---

### Phase D: Controllers (API backward compatibility)

**Goal**: Update all controllers to read from `res.company` while preserving exact JSON response format.

1. **Update `company_api.py`** (6 endpoints):
   - `env['thedevkitchen.estate.company']` → `env['res.company']`
   - Add `is_real_estate=True` to create defaults
   - Domain filter: `[('is_real_estate', '=', True), ('id', 'in', user.company_ids.ids)]`
   - Auto-linkage: `user.company_ids += (4, company.id)` instead of `estate_company_ids`
   - **Field mapping**: `zip_code` (API) → `zip` (res.company) in both read and write

2. **Update `user_auth_controller.py`** (login payload):
   - Companies: `user.company_ids.filtered(lambda c: c.is_real_estate)`
   - Fix latent bug: `getattr(c, 'vat', None)` → `c.cnpj`
   - Default company: `user.company_id.id` instead of `main_estate_company_id.id`

3. **Update `me_controller.py`** (profile payload):
   - Same pattern as login: filter `company_ids` by `is_real_estate`
   - Default company: `user.company_id.id`

4. **Update `property_api.py`**, `sale_api.py`**, `profile_api.py`**:
   - `request.company_domain` → use native ORM filtering (already applied via `request.update_env()`)
   - Or keep explicit domain `[('company_id', '=', request.env.company.id)]`

5. **Update `master_data_api.py`**:
   - `env['real.estate.state']` → `env['res.country.state']`
   - Response shape preserved

6. **Update `invite_controller.py`** + `invite_service.py`**:
   - `env['thedevkitchen.estate.company'].browse(id)` → `env['res.company'].browse(id)`
   - Company association: `company_ids += (4, id)`

**Validation**: Run full integration test suite (`./integration_tests/run_all_tests.sh`). All responses match expected JSON shapes.

---

### Phase E: Tests

**Goal**: Update all 29 test files and 14 integration scripts.

1. **Unit tests**: Replace `env['thedevkitchen.estate.company']` references, update M2M→M2O field access, fix factory/fixture methods.

2. **Integration tests**: Update SQL queries in shell scripts: `thedevkitchen_estate_company` → `res_company WHERE is_real_estate`, `thedevkitchen_user_company_rel` → `res_company_users_rel`, `estate_company_ids` → `company_ids`.

3. **New tests**: Add specific test for `is_real_estate` discriminator filtering, `zip`↔`zip_code` mapping, `request.update_env()` propagation.

**Validation**: `./integration_tests/run_all_tests.sh` — all green. Coverage report ≥80%.

---

### Phase F: Documentation & Seed Data

**Goal**: Update all ADRs, KB docs, architecture docs, and seed data files.

1. **ADR updates** (6 files): ADR-004, 008, 009, 019, 020, 024 — replace all `estate_company_ids` → `company_ids`, `thedevkitchen.estate.company` → `res.company`, M2M→M2O references.

2. **KB-07 update**: Add `_inherit` best practices section, `is_real_estate` discriminator pattern.

3. **DATABASE_ARCHITECTURE_USERS.md**: Rewrite ER diagrams, field tables, relationship descriptions.

4. **Seed data** (`demo_data.xml`, `seed_companies.xml`): Rewrite to create `res.company` records with `is_real_estate=True`. Delete `seed_states.xml` (use native country states).

5. **Postman collection**: Update environment variables and description text (no endpoint changes).

---

## Recommended Task Order

```
Phase A: Foundation               ← Can be tested independently
Phase B: Model Relations          ← Depends on A (company.py rewritten)
Phase C: Security Layer           ← Depends on B (M2O fields exist)
Phase D: Controllers              ← Depends on B+C (models + security ready)
Phase E: Tests                    ← Depends on D (controllers work end-to-end)
Phase F: Documentation            ← Independent, can parallel with E
```

## Key Risk: `zip_code` → `zip` Mapping

The API contract uses `zip_code` but `res.company` uses `zip` natively. The controller must:
- **Read**: serialize `c.zip` as `"zip_code"` in JSON responses
- **Write**: map `data.get('zip_code')` → `vals['zip']` in create/update
- **Never expose** the internal field name `zip` to API consumers

## Key Risk: `is_real_estate` Filter Completeness

Every query/domain that previously targeted `thedevkitchen.estate.company` (which by definition was always a real estate company) must now include `is_real_estate=True` when targeting `res.company` to avoid returning non-real-estate Odoo companies.

## Commands Cheat Sheet

```bash
# Reset DB (dev only)
cd 18.0 && bash reset_db.sh

# Restart with module update
docker compose restart odoo

# Run unit tests for quicksol_estate
docker compose exec odoo python -m pytest /mnt/extra-addons/quicksol_estate/tests/ -v

# Run integration tests
cd ../integration_tests && bash run_all_tests.sh

# Check record rules in DB
docker compose exec db psql -U odoo -d realestate -c "SELECT name, domain_force FROM ir_rule WHERE name LIKE '%estate%';"

# Verify M2M tables dropped
docker compose exec db psql -U odoo -d realestate -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'thedevkitchen_company_%';"

# Check is_real_estate flag
docker compose exec db psql -U odoo -d realestate -c "SELECT id, name, is_real_estate FROM res_company;"
```
