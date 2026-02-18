# Tasks: Unificação de Perfis (Profile Unification)

**Feature**: 010-profile-unification | **Date**: 2026-02-18
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)
**Research**: [research.md](research.md) | **Quickstart**: [quickstart.md](quickstart.md)

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ⏱️ | Effort estimate (story points: 1=trivial, 2=small, 3=medium, 5=large, 8=complex) |
| 🔗 | Dependency (must complete before starting this task) |
| 🧪 | Has associated tests |
| 📝 | Documentation / configuration only |
| ⚠️ | Risk flag |

---

## Dependency Graph

```
T01 ────────────────┐
                    │
T02 ──── T03        │
  │                 ▼
  └──────────────► T04 ──► T05 ──► T06
                    │               │
                    │               ▼
                    │         ┌──► T07 ──► T08 ──► T09
                    │         │
                    ▼         │
                   T10 ◄──── T06
                    │
                    ▼
              ┌──► T11
              │
              ├──► T12
              │
              ├──► T13
              │
              └──► T14 ──► T15 ──► T16
                                    │
                                    ▼
                              ┌──► T17
                              │
                              ├──► T18
                              │
                              └──► T19 ──► T20
```

---

## Phase 1: Schema Creation

### T01 — Implement validator functions in `validators.py` ⏱️ 3

**File**: `18.0/extra-addons/quicksol_estate/utils/validators.py`
**Dependencies**: 🔗 None (first task)
**Spec References**: D11, FR1.7
**Risk**: ⚠️ Low — additive changes, no existing code modified

**Description**: Add 4 missing functions to the centralized validators module. These are prerequisites for both the profile model and schema validation.

**Subtasks**:
1. Implement `normalize_document(document: str) -> str` — strip non-digit characters
2. Implement `is_cpf(document: str) -> bool` — validate CPF checksum (11 digits, two verification digits)
3. Implement `is_cnpj(document: str) -> bool` — delegate to existing `validate_cnpj()` after length check
4. Implement `validate_document(document: str) -> bool` — dispatch: 11→`is_cpf`, 14→`is_cnpj`, else `False`

**Acceptance Criteria**:
- [ ] `normalize_document('123.456.789-01')` returns `'12345678901'`
- [ ] `normalize_document('12.345.678/0001-95')` returns `'12345678000195'`
- [ ] `is_cpf('12345678901')` validates checksum correctly
- [ ] `is_cpf('11111111111')` returns `False` (all same digits)
- [ ] `is_cnpj('12345678000195')` delegates to `validate_cnpj` correctly
- [ ] `validate_document('12345678901')` dispatches to `is_cpf`
- [ ] `validate_document('12345678000195')` dispatches to `is_cnpj`
- [ ] `validate_document('123')` returns `False` (invalid length)
- [ ] Existing functions (`validate_cnpj`, `format_cnpj`, `validate_email_format`, etc.) unchanged

**Done When**: All 4 functions implemented, no regressions on existing validators.

---

### T02 — Create `thedevkitchen.profile.type` model ⏱️ 2

**File**: `18.0/extra-addons/quicksol_estate/models/profile_type.py` (NEW)
**Dependencies**: 🔗 None (independent)
**Spec References**: D6, data-model.md §2.1
**Risk**: ⚠️ Low — new file, no existing code changed

**Description**: Create the lookup table model for the 9 RBAC profile types per KB-09 §2.1.

**Subtasks**:
1. Create `profile_type.py` with model class `ProfileType`
2. Define 8 fields: `code` (Char, unique, indexed), `name` (Char, translatable), `group_xml_id` (Char), `level` (Selection: admin/operational/external), `is_active` (Boolean), `created_at` (Datetime), `updated_at` (Datetime)
3. Add `_sql_constraints` for `UNIQUE(code)`
4. Set `_order = 'name asc'`, `_rec_name = 'name'`

**Acceptance Criteria**:
- [ ] Model class defined with `_name = 'thedevkitchen.profile.type'`
- [ ] `UNIQUE(code)` SQL constraint declared
- [ ] `level` Selection has 3 options: `admin`, `operational`, `external`
- [ ] Audit fields `created_at`/`updated_at` with defaults (spec D10)
- [ ] Field `is_active` defaults to `True`

**Done When**: File created, passes Python syntax check.

---

### T03 — Create profile type seed data XML ⏱️ 1

**File**: `18.0/extra-addons/quicksol_estate/data/profile_type_data.xml` (NEW)
**Dependencies**: 🔗 T02 (model must exist)
**Spec References**: data-model.md §5
**Risk**: ⚠️ Low — new file, `noupdate="1"`

**Description**: Create XML seed data with the 9 profile type records. Must load after `groups.xml` because it references group XML IDs.

**Subtasks**:
1. Create XML file with `noupdate="1"` wrapper
2. Add 9 `<record>` elements (owner, director, manager, agent, prospector, receptionist, financial, legal, portal)
3. Each record: `code`, `name` (pt_BR), `group_xml_id` (full XML ID), `level`

**Acceptance Criteria**:
- [ ] All 9 records present with correct `code` values
- [ ] `group_xml_id` uses full path (e.g., `quicksol_estate.group_real_estate_owner`)
- [ ] Levels: admin (owner, director, manager), operational (agent, prospector, receptionist, financial, legal), external (portal)
- [ ] `noupdate="1"` set on data wrapper

**Done When**: XML file created with all 9 records.

---

### T04 — Create `thedevkitchen.estate.profile` model ⏱️ 5

**File**: `18.0/extra-addons/quicksol_estate/models/profile.py` (NEW)
**Dependencies**: 🔗 T01 (validators), T02 (profile type model)
**Spec References**: D2, D3, D5, D9, D10, data-model.md §2.2, FR1.1–FR1.14
**Risk**: ⚠️ Medium — core new model, compound constraint, computed fields

**Description**: Create the unified profile model with 19 fields, compound unique constraint, python constraints for document/email/birthdate validation, computed `document_normalized`, and `write()` override for `updated_at`.

**Subtasks**:
1. Create `profile.py` with model class `Profile`
2. Define relationship fields: `profile_type_id` (M2O, required, restrict), `company_id` (M2O, required, restrict), `partner_id` (M2O, optional, restrict)
3. Define cadastral fields: `name`, `document`, `document_normalized` (computed, stored), `email`, `phone`, `mobile`, `occupation`, `birthdate` (required), `hire_date`, `profile_picture`
4. Define soft delete fields: `active`, `deactivation_date`, `deactivation_reason` (ADR-015)
5. Define audit fields: `created_at`, `updated_at` (spec D10)
6. Add compound unique SQL constraint: `UNIQUE(document, company_id, profile_type_id)`
7. Implement `_compute_document_normalized()` using `validators.normalize_document()`
8. Implement `@api.constrains('document')` using `validators.validate_document()`
9. Implement `@api.constrains('email')` using `validators.validate_email_format()`
10. Implement `@api.constrains('birthdate')` — must be in the past
11. Override `write()` to update `updated_at` timestamp
12. Add `_inherit = ['mail.thread', 'mail.activity.mixin']` for tracking

**Acceptance Criteria**:
- [ ] `_name = 'thedevkitchen.estate.profile'`
- [ ] Compound UNIQUE constraint: `(document, company_id, profile_type_id)`
- [ ] `document_normalized` is a stored computed field with `index=True`
- [ ] Python constraints validate document (CPF/CNPJ), email format, and birthdate
- [ ] `write()` override sets `updated_at = fields.Datetime.now()`
- [ ] `mail.thread` inheritance for field tracking
- [ ] All FK fields have explicit `ondelete` parameter
- [ ] `birthdate` is `required=True` (spec D9)

**Done When**: Model file created with all fields, constraints, and overrides.

---

### T05 — Add ACLs for profile and profile_type ⏱️ 2

**File**: `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv`
**Dependencies**: 🔗 T02 (profile_type model), T04 (profile model)
**Spec References**: data-model.md §4
**Risk**: ⚠️ Low — additive rows, mechanical work

**Description**: Add 12 new ACL rows: 8 for `thedevkitchen.estate.profile` and 4 for `thedevkitchen.profile.type`.

**Subtasks**:
1. Add 8 profile ACL rows (owner=CRUD, manager=RWC, receptionist=RWC, agent=R, system=CRUD, director=CRUD, user=RWC, portal=R)
2. Add 4 profile_type ACL rows (user=R, owner=R, system=CRUD, portal=R)

**Acceptance Criteria**:
- [ ] 8 ACL rows for `model_thedevkitchen_estate_profile`
- [ ] 4 ACL rows for `model_thedevkitchen_profile_type`
- [ ] Agent has read-only on profiles
- [ ] Portal has read-only on profiles and profile types
- [ ] System admin has full CRUD on both models
- [ ] CSV format matches existing entries (comma-separated, correct column order)

**Done When**: 12 ACL rows added to CSV file.

---

### T06 — Add record rules for profile ⏱️ 3

**File**: `18.0/extra-addons/quicksol_estate/security/record_rules.xml`
**Dependencies**: 🔗 T04 (profile model), T05 (ACLs)
**Spec References**: data-model.md §3, research.md §5.2
**Risk**: ⚠️ Medium — security-critical, must match permission model

**Description**: Add 7 record rules for profile (6 group-specific + 1 profile-type global read) following patterns from property/lease/agent rules. All use `company_id in user.estate_company_ids.ids` domain for company isolation except portal (own record only).

**Subtasks**:
1. Add `rule_owner_profiles` — Owner: full CRUD, company isolation
2. Add `rule_manager_all_company_profiles` — Manager: Read/Write/Create, company isolation
3. Add `rule_agent_company_profiles` — Agent: Read only, company isolation
4. Add `rule_receptionist_company_profiles` — Receptionist: Read/Write/Create, company isolation
5. Add `rule_portal_own_profile` — Portal: Read only, `partner_id = user.partner_id`
6. Add `rule_profile_multi_company` — User+Manager base: company isolation
7. Add `rule_profile_type_global_read` — All authenticated: read profile types

**Acceptance Criteria**:
- [ ] 6 profile record rules with correct group references
- [ ] 1 profile type global read rule
- [ ] Portal rule uses `('partner_id', '=', user.partner_id.id)` domain
- [ ] All other rules use `('company_id', 'in', user.estate_company_ids.ids)` domain
- [ ] Permission flags (perm_read, perm_write, perm_create, perm_unlink) match data-model.md §3.1

**Done When**: 7 record rules added to XML file.

---

### T07 — Add profile schemas to `schema.py` ⏱️ 2

**File**: `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py`
**Dependencies**: 🔗 T01 (validators for constraints)
**Spec References**: quickstart.md §4.4, FR1.1
**Risk**: ⚠️ Low — additive, follows existing pattern

**Description**: Add `PROFILE_CREATE_SCHEMA` and `PROFILE_UPDATE_SCHEMA` following the existing `TENANT_CREATE_SCHEMA`/`AGENT_CREATE_SCHEMA` pattern.

**Subtasks**:
1. Add `PROFILE_CREATE_SCHEMA` with required fields: `name`, `company_id`, `document`, `email`, `birthdate`, `profile_type`; optional: `phone`, `mobile`, `occupation`, `hire_date`
2. Add `PROFILE_UPDATE_SCHEMA` with all fields optional except immutable ones (`profile_type`, `company_id`)
3. Add document constraint using `validators.normalize_document()` + `validators.validate_document()`
4. Add email constraint using existing inline pattern

**Acceptance Criteria**:
- [ ] `PROFILE_CREATE_SCHEMA` has correct required/optional field lists
- [ ] `PROFILE_UPDATE_SCHEMA` excludes `profile_type` and `company_id` (immutable)
- [ ] Document constraint calls centralized `validators.validate_document()` (not `validate_docbr`)
- [ ] Email constraint follows existing pattern
- [ ] `types` dict maps all fields to Python types

**Done When**: Both schemas added, consistent with existing schema patterns.

---

### T08 — Register models in `__init__.py` ⏱️ 1 📝

**Files**:
- `18.0/extra-addons/quicksol_estate/models/__init__.py`
- `18.0/extra-addons/quicksol_estate/__manifest__.py`
**Dependencies**: 🔗 T02 (profile_type), T03 (seed XML), T04 (profile)
**Spec References**: quickstart.md §6
**Risk**: ⚠️ Low — mechanical registration

**Description**: Register new models and data files so Odoo loads them.

**Subtasks**:
1. Add `from . import profile_type` to `models/__init__.py`
2. Add `from . import profile` to `models/__init__.py`
3. Add `'data/profile_type_data.xml'` to `__manifest__.py` data list (after `groups.xml`)

**Acceptance Criteria**:
- [ ] Both imports present in `models/__init__.py`
- [ ] `profile_type_data.xml` in `__manifest__.py` data list, positioned after `security/groups.xml`
- [ ] Module installs successfully with `docker compose exec odoo odoo -d realestate -i quicksol_estate --stop-after-init`

**Done When**: Models load and seed data installs without errors.

---

### T09 — Unit tests for validators ⏱️ 2 🧪

**File**: `18.0/extra-addons/quicksol_estate/tests/unit/test_validators_unit.py` (NEW)
**Dependencies**: 🔗 T01 (validator functions)
**Spec References**: ADR-003, T1.5
**Risk**: ⚠️ Low — isolated, no DB needed

**Description**: Unit tests for the 4 new validator functions using `unittest` + `unittest.mock`. No database access.

**Subtasks**:
1. Test `normalize_document()` — formatted CPF, formatted CNPJ, empty string, already clean
2. Test `is_cpf()` — valid CPF, invalid checksum, all-same digits, wrong length
3. Test `is_cnpj()` — valid CNPJ, invalid, wrong length
4. Test `validate_document()` — dispatch logic: 11→CPF, 14→CNPJ, other→False

**Acceptance Criteria**:
- [ ] Minimum 12 test methods covering all branches
- [ ] Uses `unittest.TestCase`, no Odoo imports
- [ ] Run command documented in module docstring
- [ ] All tests pass: `docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_validators_unit.py`

**Done When**: Test file created, all tests pass.

---

### T10 — Unit tests for profile model constraints ⏱️ 3 🧪

**File**: `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_validations_unit.py` (NEW)
**Dependencies**: 🔗 T04 (profile model)
**Spec References**: ADR-003, T1.1–T1.7, FR1.3, FR1.7
**Risk**: ⚠️ Low — isolated unit tests with mocks

**Description**: Unit tests for profile model python constraints and computed fields. Mock Odoo model, no DB access.

**Subtasks**:
1. Test `_check_document()` — valid CPF, valid CNPJ, invalid doc raises `ValidationError`
2. Test `_compute_document_normalized()` — formatted input → digits-only output
3. Test `_check_email()` — valid email, invalid email raises `ValidationError`
4. Test `_check_birthdate()` — past date OK, future date raises `ValidationError`
5. Test compound unique constraint logic (mock SQL constraint behavior)
6. Test `write()` override updates `updated_at`

**Acceptance Criteria**:
- [ ] Tests cover all 4 python constraints + computed field + write override
- [ ] Uses `unittest.TestCase` + `unittest.mock.MagicMock`
- [ ] No database access (mocked models)
- [ ] Minimum 10 test methods
- [ ] Run command in docstring

**Done When**: Test file created, all tests pass.

---

## Phase 2: Controller Creation

### T11 — Create `profile_api.py` controller ⏱️ 8

**File**: `18.0/extra-addons/quicksol_estate/controllers/profile_api.py` (NEW)
**Dependencies**: 🔗 T04 (profile model), T06 (record rules), T07 (schemas)
**Spec References**: US1–US4, FR1.1–FR4.4, quickstart.md §4.1–4.7
**Risk**: ⚠️ Medium — largest single task, 6 endpoints, RBAC matrix, HATEOAS

**Description**: Create the profile REST controller with 6 endpoints. Follows triple decorator pattern (ADR-011), HATEOAS responses, company_ids query param on GET, company_id in body on POST, RBAC authorization matrix, and soft delete on DELETE.

**Subtasks**:
1. Create `ProfileApiController(http.Controller)` class with imports
2. **POST `/api/v1/profiles`** — Create profile (US1)
   - Triple decorators: `@require_jwt` + `@require_session` + `@require_company`
   - Parse JSON body, validate with `PROFILE_CREATE_SCHEMA`
   - Validate `company_id` from body against `user.estate_company_ids`
   - Lookup `profile_type` code → `thedevkitchen.profile.type` record
   - Check RBAC authorization matrix (owner→all, manager→5, agent→2)
   - Normalize document via `validators.normalize_document()`
   - Create profile record
   - If `profile_type='agent'`, create `real.estate.agent` atomically with `profile_id`
   - Return 201 with HATEOAS links (self, invite, company, agent if applicable)
3. **GET `/api/v1/profiles`** — List profiles (US2)
   - Triple decorators
   - Required `company_ids` query param (comma-separated)
   - Optional filters: `profile_type`, `document`, `name`, `active`
   - Pagination: `offset`/`limit` (default 0/20, max 100)
   - Ordering: `order_by` (default `name asc`)
   - RBAC visibility filtering
   - HATEOAS pagination links
4. **GET `/api/v1/profiles/<int:profile_id>`** — Get detail (US2)
   - Triple decorators
   - Company isolation check
   - HATEOAS links including agent extension if applicable
5. **PUT `/api/v1/profiles/<int:profile_id>`** — Update profile (US3)
   - Triple decorators
   - Validate `PROFILE_UPDATE_SCHEMA`
   - Reject immutable fields (`profile_type`, `company_id`)
   - Sync changes to agent extension if `profile_type='agent'`
   - Return updated profile with HATEOAS links
6. **DELETE `/api/v1/profiles/<int:profile_id>`** — Soft delete (US4)
   - Triple decorators
   - Set `active=False`, `deactivation_date`, `deactivation_reason` (optional body)
   - Cascade: deactivate agent extension + linked `res.users`
   - Already inactive → 400
7. **GET `/api/v1/profile-types`** — List types
   - `@require_jwt` + `@require_session` (no `@require_company` needed)
   - Return all active profile types (seed data)
8. Implement RBAC authorization matrix as constant dict
9. Implement profile serializer (dict for JSON response)
10. Register in `controllers/__init__.py`

**Acceptance Criteria**:
- [ ] All 6 endpoints use correct auth decorators (ADR-011)
- [ ] `POST` validates `company_id` from body (D5.1)
- [ ] `GET` requires `company_ids` query param (D5.2)
- [ ] RBAC matrix enforced: owner→9, manager→5, agent→2 types
- [ ] Agent profile creates `real.estate.agent` atomically (FR1.4)
- [ ] `DELETE` cascades to agent extension + `res.users` (FR4.2)
- [ ] HATEOAS `_links` in all responses (FR1.9)
- [ ] Pagination on list endpoint (FR2.4)
- [ ] `profile_type` and `company_id` immutable on `PUT` (FR3.2)
- [ ] Duplicate document+company+type returns 409 (FR1.3)
- [ ] Cross-company access returns 404 (FR1.12, anti-enumeration)
- [ ] Invalid `profile_type` returns 400 (AC1.7)
- [ ] Document validation via centralized validators (D11)

**Done When**: All 6 endpoints functional, registered in `controllers/__init__.py`.

---

### T12 — Modify agent creation to auto-create profile ⏱️ 3

**File**: `18.0/extra-addons/quicksol_estate/controllers/agent_api.py`
**Dependencies**: 🔗 T04 (profile model), T11 (profile_api for pattern reference)
**Spec References**: D8, FR1.4, data-model.md §2.3
**Risk**: ⚠️ Medium — modifying 1,462 LOC controller, complex `create_agent()` method

**Description**: Modify the agent creation endpoint to auto-create a `thedevkitchen.estate.profile` (profile_type='agent') alongside the agent record, linking them via `profile_id`. Existing agent API consumers see no breaking changes.

**Subtasks**:
1. In `create_agent()`: lookup `profile_type='agent'` from profile_type model
2. Create profile record with agent's cadastral data (name, cpf→document, email, phone, company_id, birthdate if available)
3. Pass `profile_id` to agent creation `vals`
4. Wrap both creates in atomic transaction (Odoo's default `cr.savepoint()`)
5. Add `profile_id` reference in agent serializer response (if applicable)

**Acceptance Criteria**:
- [ ] Agent creation via `POST /api/v1/agents` auto-creates a profile record
- [ ] Profile has `profile_type_id` pointing to agent profile type
- [ ] Agent's `profile_id` FK links to the new profile
- [ ] Existing 18 agent endpoints continue working (no breaking changes)
- [ ] If profile creation fails, agent is not created (atomicity)

**Done When**: Agent API creates profile+agent atomically, no regressions.

---

### T13 — Modify Feature 009 invite flow to accept `profile_id` ⏱️ 5

**Files**:
- `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py`
- `18.0/extra-addons/thedevkitchen_user_onboarding/services/invite_service.py`
**Dependencies**: 🔗 T04 (profile model)
**Spec References**: US5, FR5.1–FR5.5, research.md §2.7
**Risk**: ⚠️ High — modifying invite flow (297 LOC service), dual record creation logic

**Description**: Modify Feature 009's invite controller and service to accept optional `profile_id`. When provided, name/email/document/company_id are read from the profile instead of the request body. The service must stop creating `real.estate.tenant` records for portal invites and instead link to the existing profile.

**Subtasks**:
1. **`invite_controller.py`**: Accept optional `profile_id` in invite payload
2. **`invite_controller.py`**: If `profile_id` provided, load profile and use its data (name, email, document, company_id)
3. **`invite_controller.py`**: If `profile_id` provided, derive security group from `profile.profile_type_id.group_xml_id` instead of body `profile` field
4. **`invite_service.py`**: Modify `create_invited_user()` to accept `profile_id` and link user via `partner_id`
5. **`invite_service.py`**: Modify `create_portal_user()` to stop creating `real.estate.tenant` — instead, link to existing profile
6. **`invite_service.py`**: Remove `self.env['real.estate.tenant'].sudo().search(...)` tenant existence check
7. Handle backward compatibility: invite still works without `profile_id` (legacy flow)
8. After set-password, ensure `profile.user_id` is populated via `partner_id` linkage

**Acceptance Criteria**:
- [ ] `POST /api/v1/users/invite` accepts optional `profile_id` (FR5.1)
- [ ] Profile already has `res.users` → 409 Conflict (FR5.2)
- [ ] Security group from `profile_type.group_xml_id` (FR5.3)
- [ ] Invite without `profile_id` still works (backward compatibility)
- [ ] No `real.estate.tenant` creation on portal invite (when `profile_id` provided)
- [ ] `company_id` inherited from profile to invite context (FR5.5)

**Done When**: Invite flow works with `profile_id`, backward compatible without it.

---

### T14 — Add `profile_id` FK to agent model ⏱️ 2

**File**: `18.0/extra-addons/quicksol_estate/models/agent.py`
**Dependencies**: 🔗 T04 (profile model)
**Spec References**: data-model.md §2.3
**Risk**: ⚠️ Medium — modifying 611 LOC model, but additive change only

**Description**: Add `profile_id` Many2one FK to agent model. Extend `create()` override to sync cadastral data from profile when `profile_id` is provided. Phase 1 only — no field conversions to `related`.

**Subtasks**:
1. Add `profile_id = fields.Many2one('thedevkitchen.estate.profile', ondelete='restrict', index=True)` field
2. Extend `create()` override: if `profile_id` in vals, copy `name`, `cpf` (from document), `email`, `phone`, `company_id` from profile using `setdefault()`
3. Keep existing fields as-is (Phase 1 strategy: sync, not `related`)

**Acceptance Criteria**:
- [ ] `profile_id` FK added with `ondelete='restrict'`, `index=True`
- [ ] Agent `create()` syncs data from profile when `profile_id` provided
- [ ] Agent `create()` works normally when `profile_id` not provided (backward compat)
- [ ] Existing SQL constraints unchanged (`cpf_company_unique`, `user_company_unique`)

**Done When**: FK added, create override extended, existing tests pass.

---

### T15 — Unit tests for RBAC authorization matrix ⏱️ 2 🧪

**File**: `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_authorization_unit.py` (NEW)
**Dependencies**: 🔗 T11 (RBAC matrix constant in profile_api.py)
**Spec References**: ADR-003, ADR-019, T1.14, FR1.10
**Risk**: ⚠️ Low — isolated unit tests

**Description**: Unit tests for the RBAC authorization matrix logic. Verify that each creator role can only create authorized profile types.

**Subtasks**:
1. Test Owner can create all 9 profile types
2. Test Manager can create 5 operational types (agent, prospector, receptionist, financial, legal)
3. Test Director inherits Manager permissions
4. Test Agent can create only owner + portal
5. Test unauthorized creation attempt raises/returns 403
6. Test profile types not in matrix are rejected

**Acceptance Criteria**:
- [ ] All 4 creator roles tested (owner, manager/director, agent)
- [ ] All 9 profile types covered
- [ ] Negative cases: unauthorized types return 403
- [ ] Uses `unittest.TestCase` + mocks (no DB)
- [ ] Minimum 8 test methods

**Done When**: Test file created, all tests pass.

---

### T16 — Unit tests for agent ↔ profile sync ⏱️ 2 🧪

**File**: `18.0/extra-addons/quicksol_estate/tests/unit/test_profile_sync_unit.py` (NEW)
**Dependencies**: 🔗 T14 (agent `profile_id` FK + create override)
**Spec References**: ADR-003, T1.4, FR1.4
**Risk**: ⚠️ Low — isolated unit tests

**Description**: Unit tests for the sync logic between agent and profile on creation. Uses mocks.

**Subtasks**:
1. Test agent create with `profile_id` syncs name, cpf, email, phone, company_id
2. Test agent create without `profile_id` works normally (backward compat)
3. Test `setdefault()` doesn't override explicit values
4. Test profile update syncs to agent (if implemented in Phase 1)

**Acceptance Criteria**:
- [ ] Sync from profile to agent verified
- [ ] Backward compatibility verified
- [ ] `setdefault` behavior verified
- [ ] Uses `unittest.TestCase` + mocks
- [ ] Minimum 5 test methods

**Done When**: Test file created, all tests pass.

---

## Phase 3: Cleanup

### T17 — Migrate lease `tenant_id` → `profile_id` ⏱️ 3

**Files**:
- `18.0/extra-addons/quicksol_estate/models/lease.py`
- `18.0/extra-addons/quicksol_estate/controllers/lease_api.py`
- `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py`
**Dependencies**: 🔗 T11 (profile_api for pattern reference), T04 (profile model)
**Spec References**: data-model.md §2.4, research.md §2.2
**Risk**: ⚠️ Medium — affects `_compute_name`, 5+ locations in `lease_api.py`, schema

**Description**: Change lease FK from `tenant_id` (pointing to `real.estate.tenant`) to `profile_id` (pointing to `thedevkitchen.estate.profile`). Update model, computed name, controller references, schema, and HATEOAS links. MUST be atomic (model + controller + schema in same commit).

**Subtasks**:
1. In `lease.py`: rename field `tenant_id` → `profile_id`, change FK target, set `ondelete='restrict'`
2. Update `_compute_name()`: replace `tenant_id` with `profile_id`
3. In `lease_api.py`: replace all `tenant_id` references with `profile_id` (~5 locations: create, serialize, filter, browse)
4. In `schema.py`: update `LEASE_CREATE_SCHEMA` — `tenant_id` → `profile_id`
5. Update HATEOAS links in lease responses
6. Update record rule `rule_portal_own_leases`: domain `('tenant_id.partner_id', '=', ...)` → `('profile_id.partner_id', '=', ...)`

**Acceptance Criteria**:
- [ ] Lease model uses `profile_id` FK to `thedevkitchen.estate.profile`
- [ ] `_compute_name` uses `profile_id.name`
- [ ] `LEASE_CREATE_SCHEMA` requires `profile_id` (not `tenant_id`)
- [ ] Portal lease record rule updated with `profile_id` path
- [ ] HATEOAS links reference profile endpoint
- [ ] All changes in same commit (atomic)

**Done When**: Lease fully references profile instead of tenant, no `tenant_id` references remain.

---

### T18 — Migrate property and company FK references ⏱️ 2

**Files**:
- `18.0/extra-addons/quicksol_estate/models/property.py`
- `18.0/extra-addons/quicksol_estate/models/company.py`
**Dependencies**: 🔗 T04 (profile model)
**Spec References**: data-model.md §2.5, §2.6
**Risk**: ⚠️ Low — property FK optional, company M2M→O2M straightforward

**Description**: Update property and company models to reference profile instead of tenant.

**Subtasks**:
1. In `property.py` (line ~217): rename `tenant_id` → `profile_id`, change FK target to `thedevkitchen.estate.profile`, keep `ondelete='set null'`
2. In `company.py` (line ~59): remove `tenant_ids` M2M + `tenant_count` computed
3. In `company.py`: add `profile_ids = fields.One2many('thedevkitchen.estate.profile', 'company_id')` and `profile_count` computed field
4. Update `_compute_counts` in company.py if it references `tenant_count`

**Acceptance Criteria**:
- [ ] `property.py` uses `profile_id` FK (optional, `ondelete='set null'`)
- [ ] `company.py` has `profile_ids` O2M reverse field
- [ ] `company.py` `tenant_ids` M2M removed (and `tenant_count`)
- [ ] `_compute_counts` updated if needed
- [ ] Join table `thedevkitchen_company_tenant_rel` no longer referenced

**Done When**: Property and company reference profile, no tenant references.

---

### T19 — Remove tenant artifacts ⏱️ 2

**Files**:
- `18.0/extra-addons/quicksol_estate/models/tenant.py` (DELETE)
- `18.0/extra-addons/quicksol_estate/controllers/tenant_api.py` (DELETE)
- `18.0/extra-addons/quicksol_estate/views/tenant_views.xml` (DELETE)
- `18.0/extra-addons/quicksol_estate/models/__init__.py`
- `18.0/extra-addons/quicksol_estate/controllers/__init__.py`
- `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv`
- `18.0/extra-addons/quicksol_estate/security/record_rules.xml`
- `18.0/extra-addons/quicksol_estate/controllers/utils/schema.py`
- `18.0/extra-addons/quicksol_estate/__manifest__.py`
**Dependencies**: 🔗 T17 (lease migrated), T18 (property/company migrated)
**Spec References**: data-model.md §7, research.md §8.3
**Risk**: ⚠️ Medium — broad cleanup, must ensure no dangling references

**Description**: Remove all tenant-related artifacts from the codebase. This is safe only after all FKs have been migrated to profile.

**Subtasks**:
1. Delete `models/tenant.py`
2. Delete `controllers/tenant_api.py`
3. Delete `views/tenant_views.xml`
4. Remove `from . import tenant` from `models/__init__.py`
5. Remove `from . import tenant_api` from `controllers/__init__.py`
6. Remove 7 ACL rows for `model_real_estate_tenant` from `ir.model.access.csv`
7. Remove `rule_tenant_multi_company` from `record_rules.xml`
8. Remove `TENANT_CREATE_SCHEMA` and `TENANT_UPDATE_SCHEMA` from `schema.py`
9. Remove `'views/tenant_views.xml'` from `__manifest__.py` data list
10. Add `from . import profile_api` to `controllers/__init__.py` (if not done in T11)

**Acceptance Criteria**:
- [ ] No files referencing `real.estate.tenant` remain in codebase
- [ ] Grep for `tenant` in models/, controllers/, security/ returns 0 relevant hits
- [ ] `__init__.py` files updated (tenant removed, profile added)
- [ ] `__manifest__.py` updated (tenant views removed, profile data added)
- [ ] Module installs cleanly after cleanup

**Done When**: Zero `real.estate.tenant` references in codebase, clean module install.

---

### T20 — ORM metadata cleanup SQL ⏱️ 1 📝

**File**: Documentation / manual SQL execution
**Dependencies**: 🔗 T19 (all tenant artifacts removed)
**Spec References**: data-model.md §7.2
**Risk**: ⚠️ Low — dev environment only, optional

**Description**: Clean up Odoo's internal model registry entries for the removed tenant model. Execute after module update to prevent orphan references.

**Subtasks**:
1. Document SQL cleanup commands (delete from `ir_model`, `ir_model_fields`, `ir_model_access`, `ir_rule`)
2. Drop tables: `real_estate_tenant`, `thedevkitchen_company_tenant_rel`
3. Run via `docker compose exec db psql -U odoo -d realestate`

**Acceptance Criteria**:
- [ ] SQL commands documented
- [ ] `DROP TABLE IF EXISTS real_estate_tenant CASCADE;` executed
- [ ] `DROP TABLE IF EXISTS thedevkitchen_company_tenant_rel CASCADE;` executed
- [ ] No orphan `ir_model` entries for `real.estate.tenant`

**Done When**: Tables dropped, ORM registry clean.

---

## Phase 4: E2E Tests

### T21 — E2E: Create profile (all types) ⏱️ 3 🧪

**File**: `integration_tests/test_us10_s1_create_profile.sh` (NEW)
**Dependencies**: 🔗 T11 (profile controller running)
**Spec References**: US1, T1.8–T1.15

**Description**: E2E shell test for `POST /api/v1/profiles` covering all 9 profile types, RBAC, document validation, compound unique constraint, and HATEOAS links.

**Subtasks**:
1. Test Owner creates Manager profile → 201
2. Test Owner creates Agent profile → 201 + agent extension created
3. Test Owner creates Portal profile with occupation → 201
4. Test duplicate document+company+type → 409
5. Test same document, different company → 201
6. Test Agent creates Director → 403 (RBAC violation)
7. Test invalid document (CPF) → 400
8. Test invalid profile_type → 400
9. Test response has HATEOAS `_links`
10. Test cross-company access → 404

**Acceptance Criteria**:
- [ ] Source `.env` for credentials (no hardcoded values)
- [ ] Login per profile (owner, manager, agent) — no admin login
- [ ] Valid CNPJ/CPF in test data
- [ ] Minimum 10 test cases covering all ACs from US1
- [ ] Exit 1 on first failure

**Done When**: Script runs green against live instance.

---

### T22 — E2E: List and get profiles ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s2_list_profiles.sh` (NEW)
**Dependencies**: 🔗 T21 (profiles exist for querying)
**Spec References**: US2, T2.1–T2.8

**Subtasks**:
1. Test list with `company_ids` → returns profiles
2. Test filter by `profile_type=agent` → filtered results
3. Test get detail with HATEOAS links
4. Test cross-company profile → 404
5. Test agent-type detail includes agent extension link
6. Test pagination (offset+limit)
7. Test missing `company_ids` → 400
8. Test unauthorized `company_ids` → 403

**Done When**: Script runs green, all 8 cases pass.

---

### T23 — E2E: Update profile ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s3_update_profile.sh` (NEW)
**Dependencies**: 🔗 T21 (profiles exist)
**Spec References**: US3, T3.1–T3.5

**Subtasks**:
1. Test update name → 200
2. Test update document causing duplicate → 409
3. Test update agent-type syncs to agent model
4. Test change profile_type → 400 (immutable)
5. Test Manager cannot update Director → 403

**Done When**: Script runs green, all 5 cases pass.

---

### T24 — E2E: Soft delete profile ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s4_deactivate_profile.sh` (NEW)
**Dependencies**: 🔗 T21 (profiles exist)
**Spec References**: US4, T4.1–T4.4

**Subtasks**:
1. Test soft delete with reason → 200, `active=False`
2. Test agent extension deactivated in cascade
3. Test linked `res.users` deactivated
4. Test already inactive → 400

**Done When**: Script runs green, all 4 cases pass.

---

### T25 — E2E: Feature 009 integration (two-step flow) ⏱️ 3 🧪

**File**: `integration_tests/test_us10_s5_feature009_integration.sh` (NEW)
**Dependencies**: 🔗 T13 (invite flow modified), T21 (profiles exist)
**Spec References**: US5, T5.1–T5.4

**Subtasks**:
1. Test create profile → invite via `profile_id` → user created, email sent
2. Test profile already has user → 409
3. Test correct security group assigned from `profile_type.group_xml_id`
4. Test after set-password, `profile.user_id` populated

**Done When**: Script runs green, full two-step flow works.

---

### T26 — E2E: RBAC matrix ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s6_rbac_matrix.sh` (NEW)
**Dependencies**: 🔗 T11 (profile controller)
**Spec References**: ADR-019, Authorization Matrix

**Subtasks**:
1. Test Owner creates all 9 types → 201 each
2. Test Manager creates 5 operational → 201; tries admin types → 403
3. Test Agent creates owner+portal → 201; tries others → 403
4. Test unauthenticated → 401

**Done When**: Script runs green, full RBAC matrix verified.

---

### T27 — E2E: Multi-tenancy isolation ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s7_multitenancy.sh` (NEW)
**Dependencies**: 🔗 T11 (profile controller)
**Spec References**: ADR-008, FR1.5, FR1.12

**Subtasks**:
1. Test same document in different companies → both succeed
2. Test cross-company read → 404
3. Test company_ids with unauthorized company → 403
4. Test user sees only own company profiles

**Done When**: Script runs green, company isolation verified.

---

### T28 — E2E: Compound unique + pagination ⏱️ 2 🧪

**Files**:
- `integration_tests/test_us10_s8_compound_unique.sh` (NEW)
- `integration_tests/test_us10_s10_pagination_hateoas.sh` (NEW)
**Dependencies**: 🔗 T11 (profile controller)
**Spec References**: FR1.3, FR2.4

**Subtasks**:
1. Test same doc+company+type → 409
2. Test same doc+company+different type → 201
3. Test same doc+different company+same type → 201
4. Test pagination: offset=0/limit=5, verify count/next links
5. Test HATEOAS links structure

**Done When**: Both scripts run green.

---

### T29 — E2E: Agent ↔ profile sync on creation ⏱️ 2 🧪

**File**: `integration_tests/test_us10_s9_agent_profile_sync.sh` (NEW)
**Dependencies**: 🔗 T12 (agent auto-creates profile)
**Spec References**: FR1.4, data-model.md §2.3

**Subtasks**:
1. Test `POST /api/v1/agents` auto-creates profile with `profile_type='agent'`
2. Test agent `profile_id` FK populated
3. Test profile data matches agent data (name, document, email)
4. Test `POST /api/v1/profiles` with `profile_type='agent'` creates agent extension

**Done When**: Script runs green, bidirectional sync verified.

---

## Phase 5: Documentation & Finalization

### T30 — Update Postman collection ⏱️ 2 📝

**File**: `docs/postman/feature010_profile_unification_v1.0_postman_collection.json` (NEW)
**Dependencies**: 🔗 T11 (all endpoints finalized)
**Spec References**: ADR-016

**Description**: Create Postman collection following ADR-016 standards with all 6 profile endpoints + profile-types endpoint.

**Subtasks**:
1. Create collection with proper naming convention
2. Add variables: `base_url`, `jwt_token`, `session_id`
3. Add all 7 requests with headers, body examples, test scripts
4. Add OAuth token endpoint with auto-save script

**Done When**: Collection importable, all requests work against live instance.

---

### T31 — Mark `test_us8_*` as superseded ⏱️ 1 📝

**Files**: `integration_tests/test_us8_s1_tenant_crud.sh` and related
**Dependencies**: 🔗 T19 (tenant removed)
**Spec References**: research.md §9.1

**Description**: Add header comments to existing `test_us8_*` shell tests marking them as superseded by `test_us10_*` (profile-based tests). Do not delete — keep for reference.

**Done When**: Superseded tests marked, not breaking CI.

---

## Summary

| Phase | Tasks | Total ⏱️ | Description |
|-------|-------|----------|-------------|
| **Phase 1** (Schema) | T01–T10 | 24 pts | Models, validators, security, schemas, unit tests |
| **Phase 2** (Controllers) | T11–T16 | 22 pts | Profile API, agent modification, invite integration, unit tests |
| **Phase 3** (Cleanup) | T17–T20 | 8 pts | FK migrations, tenant removal, ORM cleanup |
| **Phase 4** (E2E Tests) | T21–T29 | 20 pts | All E2E shell test scripts |
| **Phase 5** (Docs) | T30–T31 | 3 pts | Postman collection, supersede old tests |
| **TOTAL** | **31 tasks** | **77 pts** | — |

### Critical Path

```
T01 → T04 → T06 → T11 → T17 → T19 → T20
          ↗                ↗
T02 → T03                T18
```

**Longest path**: T01 → T04 → T06 → T11 → T17 → T19 → T20 = **24 pts**

### Priority Order (Recommended Execution)

| Order | Tasks | Milestone |
|-------|-------|-----------|
| 1 | T01, T02 (parallel) | Validators + ProfileType model ready |
| 2 | T03, T09 (parallel) | Seed data + validator tests |
| 3 | T04 | Profile model ready |
| 4 | T05, T06, T07, T08 (parallel group) | Security + schemas + registration |
| 5 | T10 | Profile validation unit tests |
| 6 | T11 | Profile API controller (largest task) |
| 7 | T12, T13, T14 (parallel group) | Agent mod + Invite mod + Agent FK |
| 8 | T15, T16 | RBAC + sync unit tests |
| 9 | T17, T18 (parallel) | FK migrations |
| 10 | T19, T20 | Tenant removal + cleanup |
| 11 | T21–T29 | E2E tests (sequential, each builds on previous) |
| 12 | T30, T31 | Documentation finalization |
