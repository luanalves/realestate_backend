# Tasks: User Onboarding & Password Management

**Input**: Design documents from `/specs/009-user-onboarding-password-management/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅, quickstart.md ✅

**Tests**: Explicitly required per spec.md (ADR-003 "Golden Rule"). Unit tests (unittest + mock), E2E API (shell/curl), E2E UI (Cypress).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Module**: `18.0/extra-addons/thedevkitchen_user_onboarding/`
- **E2E API tests**: `integration_tests/`
- **E2E UI tests**: `cypress/e2e/`
- **Postman**: `docs/postman/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module directory structure and initialization files

- [X] T001 Create module directory structure per plan.md: `18.0/extra-addons/thedevkitchen_user_onboarding/` with subdirectories `controllers/`, `models/`, `services/`, `data/`, `security/`, `views/`, `tests/`, `tests/unit/`, `i18n/`
- [X] T002 [P] Create `18.0/extra-addons/thedevkitchen_user_onboarding/__manifest__.py` with module metadata, version `18.0.1.0.0`, depends `['mail', 'thedevkitchen_apigateway', 'quicksol_estate']`, and data file references for security, data, and views XML/CSV files
- [X] T003 [P] Create all `__init__.py` files: module root (imports controllers, models, services), `controllers/__init__.py` (imports invite_controller, password_controller), `models/__init__.py` (imports password_token, email_link_settings, res_users), `services/__init__.py` (imports token_service, invite_service, password_service), `tests/__init__.py`, `tests/unit/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, services, security, and data that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create `thedevkitchen.password.token` model in `18.0/extra-addons/thedevkitchen_user_onboarding/models/password_token.py` — fields: `user_id` (Many2one res.users, ondelete=cascade), `token` (Char(64), unique, index), `token_type` (Selection: invite/reset), `status` (Selection: pending/used/expired/invalidated, default=pending), `expires_at` (Datetime), `used_at` (Datetime), `ip_address` (Char(45)), `user_agent` (Char(255)), `company_id` (Many2one thedevkitchen.estate.company), `created_by` (Many2one res.users), `active` (Boolean, default=True). Include SQL constraint `token_unique`, Python constraint `_check_expires_at`, composite index on `(user_id, token_type, status)`, index on `expires_at`. Include `_cron_cleanup_expired_tokens()` method per research.md R12
- [X] T005 [P] Create `thedevkitchen.email.link.settings` Singleton model in `18.0/extra-addons/thedevkitchen_user_onboarding/models/email_link_settings.py` — fields: `name` (Char(100), default='Email Link Configuration'), `invite_link_ttl_hours` (Integer, default=24), `reset_link_ttl_hours` (Integer, default=24), `frontend_base_url` (Char(255), default='http://localhost:3000'), `max_resend_attempts` (Integer, default=5), `rate_limit_forgot_per_hour` (Integer, default=3). Include `_check_link_ttl_positive` constraint (1-720h) and `get_settings()` singleton method
- [X] T006 [P] Create `res.users` extension in `18.0/extra-addons/thedevkitchen_user_onboarding/models/res_users.py` — `_inherit = 'res.users'`, add `signup_pending` Boolean field (default=False, help='Indicates user is waiting to create their password via invite link'). Coexists with `quicksol_estate` extension per research.md R9
- [X] T007 Create `PasswordTokenService` in `18.0/extra-addons/thedevkitchen_user_onboarding/services/token_service.py` — methods: `generate_token(user, token_type, company)` (UUID v4 → SHA-256, create password.token record with TTL from settings), `validate_token(raw_token)` (hash → lookup → check status/expiry, auto-expire if past TTL), `invalidate_previous_tokens(user_id, token_type)` (set status=invalidated for all pending tokens of same user+type), `check_rate_limit(email, token_type)` (Redis counter per research.md R5 for forgot-password: `forgot_password:{email}` with 1h TTL)
- [X] T008 [P] Create ACL file `18.0/extra-addons/thedevkitchen_user_onboarding/security/ir.model.access.csv` — CRUD permissions for `thedevkitchen.password.token` (read/write for estate users, full for admin) and `thedevkitchen.email.link.settings` (read for estate users, full for admin/system)
- [X] T009 [P] Create record rules in `18.0/extra-addons/thedevkitchen_user_onboarding/security/record_rules.xml` — company isolation rule for `thedevkitchen.password.token` with domain `[('company_id', 'in', user.estate_company_ids.ids)]` applied to `group_real_estate_user`
- [X] T010 [P] Create `18.0/extra-addons/thedevkitchen_user_onboarding/data/default_settings.xml` — default singleton record for `thedevkitchen.email.link.settings` (24h TTL for both link types, localhost:3000 frontend URL, max 5 resends, rate limit 3/hour) and `ir.cron` record for daily token cleanup calling `_cron_cleanup_expired_tokens`
- [X] T011 [P] Create `18.0/extra-addons/thedevkitchen_user_onboarding/data/email_templates.xml` — two `mail.template` records: (1) `email_template_user_invite` on `res.users` with subject including company name, body with user name, invite link (`{frontend_base_url}/set-password?token={raw_token}`), expiry hours; (2) `email_template_password_reset` on `res.users` with subject including company name, body with user name, reset link (`{frontend_base_url}/reset-password?token={raw_token}`), expiry hours. Both in pt_BR

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Invite User (Priority: P1) 🎯 MVP

**Goal**: Owner/Manager/Agent can invite new users via API. System creates `res.users` without password, sends email with secure invite link. Portal profile creates dual record (`res.users` + `real.estate.tenant`).

**Independent Test**: `POST /api/v1/users/invite` with valid auth → user created with `signup_pending=True`, email sent, response includes HATEOAS links. Portal invite → tenant record exists and linked via `partner_id`.

### Implementation for User Story 1

- [ ] T012 [US1] Create `InviteService` in `18.0/extra-addons/thedevkitchen_user_onboarding/services/invite_service.py` — implement: `INVITE_AUTHORIZATION` dict (per research.md R11), `PROFILE_TO_GROUP` mapping dict, `check_authorization(requester_user, target_profile)` method, `create_invited_user(name, email, document, profile, company, created_by, **extra_fields)` method (creates `res.users` with group, `password=False`, `signup_pending=True`, validates document via `validate_docbr` for CPF or `validators.validate_document()` for portal CPF/CNPJ), `send_invite_email(user, raw_token, expires_hours)` method (uses `mail.template` with context variables)
- [ ] T013 [US1] Add portal dual record creation to `18.0/extra-addons/thedevkitchen_user_onboarding/services/invite_service.py` — implement `_create_portal_user(name, email, document, phone, birthdate, company_id, occupation, created_by)` that atomically creates `res.users` (portal group) + `real.estate.tenant` (linked via `user.partner_id`). Validate conditional required fields (`phone`, `birthdate`, `company_id`). Check for document conflict (existing tenant without `res.users` → 409). All within single Odoo transaction per research.md R6
- [ ] T014 [US1] Create `InviteController` in `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py` — `POST /api/v1/users/invite` with `@require_jwt`, `@require_session`, `@require_company` decorators. Parse and validate request body (base fields + conditional portal fields per ADR-018). Check authorization matrix. Delegate to `InviteService`. Return 201 with HATEOAS links (self, resend_invite, collection). Include portal tenant data in response when `profile=portal`. Handle errors: 400 (validation), 403 (forbidden), 409 (email/document conflict), 500 (email failure). Follow controller patterns from `.github/instructions/controllers.instructions.md`
- [X] T015 [P] [US1] Create unit test `18.0/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_invite_authorization.py` — test authorization matrix: Owner can invite all 9 profiles, Manager can invite 5 operational profiles, Agent can invite owner+portal only, Director inherits Manager permissions, other profiles (Prospector, Receptionist, Financial, Legal, Portal) cannot invite anyone (403). Also test `test_email_template_rendering()`: invite email template renders with correct variables (user name, invite link, expiry hours). Mock `env['res.users']`, `env['thedevkitchen.password.token']`, and `env['mail.template']`
- [ ] T016 [P] [US1] Create E2E test `integration_tests/test_us9_s1_invite_flow.sh` — scenarios: Owner invites Manager (201 + email), Manager invites Agent (201), Agent invites Owner (201), set-password with valid token (200 + login works), set-password with expired token (410), set-password with already-used token (410), invite with duplicate email (409), invite with duplicate document (409), login before set-password (401), login after set-password (success with session_id + JWT). Use curl with JSON payloads, assert HTTP status codes and response body fields
- [ ] T017 [P] [US1] Create E2E test `integration_tests/test_us9_s3_portal_dual_record.sh` — scenarios: Agent invites portal tenant with all required fields (201 + tenant_id in response), verify `real.estate.tenant` record exists with correct `partner_id` linkage, portal invite missing `phone` (400), portal invite missing `birthdate` (400), portal invite with existing document for unlinked tenant (409), portal user login after set-password (success)
- [ ] T018 [P] [US1] Create E2E test `integration_tests/test_us9_s4_authorization_matrix.sh` — scenarios: Owner invites each of 9 profiles (all 201), Manager invites agent/prospector/receptionist/financial/legal (all 201), Manager tries to invite owner (403), Agent invites owner+portal (201), Agent tries to invite manager (403), Prospector/Receptionist/Financial/Legal try to invite anyone (403)

**Checkpoint**: User Story 1 fully functional — users can be invited, passwords set, and login works

---

## Phase 4: User Story 2 — Set Password via Invite Link (Priority: P1) 🎯 MVP

**Goal**: Invited user clicks email link and sets their password via public endpoint. Token is consumed and user can login.

**Independent Test**: `POST /api/v1/auth/set-password` with valid token + password → password set, `signup_pending=False`, token status=used, login succeeds.

### Implementation for User Story 2

- [X] T019 [US2] Create `PasswordService` in `18.0/extra-addons/thedevkitchen_user_onboarding/services/password_service.py` — methods: `set_password(raw_token, password, confirm_password, ip_address, user_agent)` (validate token via TokenService, check password min 8 chars, check password == confirm_password, set user password via Odoo, update `signup_pending=False`, mark token as used with `used_at`/`ip_address`/`user_agent`)
- [X] T020 [US2] Create `PasswordController` in `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/password_controller.py` — `POST /api/v1/auth/set-password` as `# public endpoint` (auth='none', csrf=False, cors='*'). Parse request body (`token`, `password`, `confirm_password`). Delegate to `PasswordService.set_password()`. Return 200 with success message + HATEOAS link to login. Handle errors: 400 (validation), 404 (token not found), 410 (expired/used). Follow controller patterns from `.github/instructions/controllers.instructions.md`
- [X] T021 [P] [US2] Create unit test `18.0/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_password_validation.py` — test: password < 8 chars rejected, password == confirm_password passes, password != confirm_password rejected, empty password rejected, empty confirm_password rejected. Mock `env['res.users']` for password setting
- [X] T022 [P] [US2] Create unit test `18.0/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_token_service.py` — test: `generate_token()` returns UUID-format raw token and stores SHA-256 hash, `validate_token()` with valid token returns user, `validate_token()` with expired token raises/returns error, `validate_token()` with used token raises/returns error, `validate_token()` with nonexistent hash returns None/404, `invalidate_previous_tokens()` sets all pending tokens to invalidated, token uniqueness constraint. Mock `env['thedevkitchen.password.token']` and `env['thedevkitchen.email.link.settings']`

**Checkpoint**: User Story 2 functional — invited users can set password and login

---

## Phase 5: User Story 3 — Forgot Password (Priority: P1) 🎯 MVP

**Goal**: Any user can request password reset. System sends email with reset link. User resets password. All active sessions invalidated after reset.

**Independent Test**: `POST /api/v1/auth/forgot-password` with registered email → 200 (always), email sent. `POST /api/v1/auth/reset-password` with valid token → password changed, sessions invalidated, login with new password works.

### Implementation for User Story 3

- [X] T023 [US3] Extend `PasswordService` in `18.0/extra-addons/thedevkitchen_user_onboarding/services/password_service.py` — add methods: `forgot_password(email)` (always return success, if email exists+active: invalidate previous reset tokens, generate new reset token via TokenService, send reset email via `mail.template`; check rate limit via TokenService.check_rate_limit), `reset_password(raw_token, password, confirm_password, ip_address, user_agent)` (validate token, set password, mark token used, invalidate all active sessions via `api_session.active=False` per research.md R7)
- [X] T024 [US3] Extend `PasswordController` in `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/password_controller.py` — add two `# public endpoint` routes: (1) `POST /api/v1/auth/forgot-password` (accepts `email`, validates format, delegates to `PasswordService.forgot_password()`, ALWAYS returns 200 with generic message per anti-enumeration ADR-008, returns 429 if rate limited, returns 400 if email missing/invalid); (2) `POST /api/v1/auth/reset-password` (accepts `token`, `password`, `confirm_password`, delegates to `PasswordService.reset_password()`, returns 200 with success + HATEOAS login link, handles 400/404/410 errors)
- [X] T025 [P] [US3] Create unit test — add to `18.0/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_token_service.py` (or extend T022): test `test_forgot_password_always_200()` (service returns success regardless of email existence), `test_reset_token_invalidates_previous()` (new reset token marks previous pending tokens as invalidated), `test_rate_limit_check()` (Redis counter increments, blocks at threshold, respects TTL), `test_session_invalidation_after_reset()` (`api_session.active=False` called for all user sessions). Mock Redis client and `env['thedevkitchen.api.session']`
- [ ] T026 [US3] Create E2E test `integration_tests/test_us9_s2_forgot_password.sh` — scenarios: forgot-password with registered email (200 + email sent), forgot-password with unregistered email (200, no email), forgot-password with inactive user (200, no email), reset-password with valid token (200 + password changed), reset-password with expired token (410), reset-password with used token (410), full forgot→reset→login flow (success with new password), previous reset tokens invalidated when new one generated, session invalidation after reset (old session_id invalid), rate limiting (4th request within 1 hour → 429)

**Checkpoint**: User Story 3 functional — users can reset forgotten passwords

---

## Phase 6: User Story 6 — Universal Login for All Profiles (Priority: P1) 🎯 MVP

**Goal**: Verify that the existing login endpoint (`POST /api/v1/users/login`) works for all 9 RBAC profiles without any code modification.

**Independent Test**: For each of the 9 profiles, after invite + set-password → login returns `session_id`, user data, and company info. Pending user (no password) → 401.

**⚠️ NO CODE CHANGES**: This user story is verification-only via E2E tests.

### Implementation for User Story 6

- [ ] T027 [US6] Add login verification scenarios to `integration_tests/test_us9_s1_invite_flow.sh` — extend the invite flow test to verify login for all 9 profiles: create one user per profile (owner, director, manager, agent, prospector, receptionist, financial, legal, portal) via invite → set-password → verify `POST /api/v1/users/login` succeeds with `session_id` and user data. Also verify: pending user (invited but no password set) → login returns 401, inactive user → login returns 403

**Checkpoint**: Universal login verified for all 9 profiles

---

## Phase 7: User Story 4 — Resend Invite (Priority: P2)

**Goal**: Owner/Manager/Agent can resend invite email to users who haven't set their password yet. Previous tokens invalidated, new token generated.

**Independent Test**: `POST /api/v1/users/{id}/resend-invite` for pending user → 200, new token generated, old tokens invalidated, email sent. For active user → 400. For other company's user → 404.

### Implementation for User Story 4

- [X] T028 [US4] Add resend-invite endpoint to `18.0/extra-addons/thedevkitchen_user_onboarding/controllers/invite_controller.py` — `POST /api/v1/users/{id}/resend-invite` with `@require_jwt`, `@require_session`, `@require_company` decorators. Validate: user exists in requester's company (404 if not), user has `signup_pending=True` (400 if already active, suggest forgot-password), check authorization matrix. Invalidate previous invite tokens, generate new token, send invite email. Return 200 with success message and `invite_expires_at`.  Handle 400/401/403/404 errors
- [X] T029 [US4] Create E2E test `integration_tests/test_us9_s6_resend_invite.sh` — scenarios: resend to pending user (200 + new token + old token invalidated), resend to active user (400 + message suggesting forgot-password), resend to user in different company (404), verify resend email contains updated expiry, verify old invite link no longer works after resend (410)

**Checkpoint**: User Story 4 functional — invites can be resent to pending users

---

## Phase 8: User Story 5 — Dynamic Link Settings Configuration (Priority: P2)

**Goal**: System administrator can configure email link validity, frontend URL, and rate limits via Odoo's Technical menu.

**Independent Test**: Navigate to Technical > Configuration > Email Link Settings → form loads, can edit TTL values, save persists, validation prevents invalid values (0, negative, >720).

### Implementation for User Story 5

- [X] T030 [P] [US5] Create form view in `18.0/extra-addons/thedevkitchen_user_onboarding/views/email_link_settings_views.xml` — form view for `thedevkitchen.email.link.settings` with groups: Link Validity (`invite_link_ttl_hours`, `reset_link_ttl_hours`), Frontend Configuration (`frontend_base_url`), Rate Limiting (`max_resend_attempts`, `rate_limit_forgot_per_hour`). Follow Odoo 18.0 standards: no `attrs`, use `invisible` attribute directly. Use `<list>` not `<tree>` if list view needed (KB-10)
- [X] T031 [P] [US5] Create menu entry in `18.0/extra-addons/thedevkitchen_user_onboarding/views/menu.xml` — menu item under Technical > Configuration > Email Link Settings. Action opens form view in singleton mode (auto-open single record). Restrict menu visibility to admin/system group
- [X] T032 [P] [US5] Create unit test — add to `18.0/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_token_service.py` (or new file `test_email_link_settings.py`): test `test_link_ttl_default_24h()` (singleton model returns 24h default for both link types), `test_link_ttl_positive_validation()` (constraint rejects 0, negative, >720 values), `test_get_settings_creates_default()` (singleton pattern creates record if none exists). Mock `env['thedevkitchen.email.link.settings']`
- [ ] T033 [US5] Create Cypress E2E test `cypress/e2e/email-link-settings.cy.js` — scenarios: settings menu is accessible from Technical > Configuration, form loads without errors, can edit `invite_link_ttl_hours` and save, can edit `reset_link_ttl_hours` and save, validation prevents values outside 1-720 range, `frontend_base_url` field is editable, zero JS console errors throughout

**Checkpoint**: User Story 5 functional — settings are configurable via UI

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting tests, documentation, translations, and quality validation

- [ ] T034 Create E2E test `integration_tests/test_us9_s5_multitenancy.sh` — cross-cutting multi-tenancy scenarios: invite user in Company A → not visible from Company B context, resend-invite for Company B user from Company A context → 404, token lookup respects company isolation (token created in Company A cannot be used with Company B session), forgot-password works cross-company (public endpoint, no isolation needed), verify `record_rules.xml` enforcement on `thedevkitchen.password.token`
- [ ] T035 [P] Create Postman collection `docs/postman/feature009_user_onboarding_v1.0_postman_collection.json` — all 5 endpoints per ADR-016 with required variables (`base_url`, `jwt_token`, `session_id`), request examples for standard + portal invite, set-password, forgot-password, reset-password, resend-invite. Include test scripts for token extraction from invite response. Follow Postman collection naming from ADR-016
- [ ] T036 [P] Create translation file `18.0/extra-addons/thedevkitchen_user_onboarding/i18n/pt_BR.po` — translate all user-facing strings: error messages, email template content, settings view labels, menu items, constraint messages to Portuguese (pt_BR)
- [ ] T037 Run `quickstart.md` validation — execute all 3 test flows from `specs/009-user-onboarding-password-management/quickstart.md`: (1) invite→set-password→login flow, (2) forgot→reset→login flow, (3) portal dual record flow. Verify installation steps, troubleshooting SQL queries, and all commands work as documented
- [ ] T038 Code quality validation — run `ruff check` + `black --check` on all Python files in `18.0/extra-addons/thedevkitchen_user_onboarding/` (per constitution: `ruff` + `black`). Run `pylint` and verify score ≥ 8.0/10 per ADR-022. Run `lint_xml.py` on all XML files. Fix any issues found
- [ ] T039 [P] Update constitution `.specify/memory/constitution.md` — add new patterns introduced by this feature: token-based onboarding (SHA-256), anti-enumeration response, `# public endpoint` pattern, email template integration (`mail.template`), singleton configuration model, rate limiting pattern, dual record creation for portal entities. Version bump 1.2.0 → 1.3.0. Add Feature 009 as reference implementation alongside Feature 007
- [ ] T040 [P] Deploy OpenAPI spec to `docs/openapi/009-user-onboarding.yaml` — copy/adapt from `specs/009-user-onboarding-password-management/contracts/openapi.yaml` to the project-wide API docs location per ADR-005
- [ ] T041 [P] Update `.github/copilot-instructions.md` — add `# public endpoint` pattern documentation for unauthenticated endpoints, add reference to `thedevkitchen_user_onboarding` module

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — No dependencies on other stories
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — Can be implemented in parallel with US1, but benefits from US1 being done first (invite creates users for set-password to test)
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) + US2 (Phase 4) for `PasswordService` base file
- **US6 (Phase 6)**: Depends on US1 (Phase 3) + US2 (Phase 4) — needs invited users with set passwords to test login
- **US4 (Phase 7)**: Depends on US1 (Phase 3) — extends invite_controller.py
- **US5 (Phase 8)**: Depends on Foundational (Phase 2) only — model/views/menu can be built independently
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational ──────────────────────┐
    │                                        │
    ├──► Phase 3: US1 (Invite) ─────┐        │
    │         │                     │        │
    │         ▼                     │        │
    │    Phase 7: US4 (Resend)      │        │
    │                               │        │
    ├──► Phase 4: US2 (Set Pass) ◄──┘        │
    │         │                              │
    │         ▼                              │
    │    Phase 5: US3 (Forgot Pass)          │
    │         │                              │
    │         ▼                              │
    │    Phase 6: US6 (Login Verify)         │
    │                                        │
    ├──► Phase 8: US5 (Settings UI) ◄────────┘
    │
    ▼
Phase 9: Polish
```

### Within Each User Story

- Models before services
- Services before controllers
- Controllers before E2E tests
- Unit tests can be written in parallel with implementation (marked [P])
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003)
- All Foundational tasks marked [P] can run in parallel (T004, T005, T006, T008, T009, T010, T011)
- Unit tests within any story marked [P] can run in parallel with E2E tests
- **US1 and US5 can be developed in parallel** (different files, no dependencies)
- **US4 can start as soon as US1 is complete** (extends same controller file)

---

## Parallel Example: Foundational Phase

```bash
# Launch all model files together (different files, no dependencies):
T004: "Create password_token model in models/password_token.py"
T005: "Create email_link_settings model in models/email_link_settings.py"
T006: "Create res_users extension in models/res_users.py"

# Launch all security + data files together (different files):
T008: "Create ACLs in security/ir.model.access.csv"
T009: "Create record rules in security/record_rules.xml"
T010: "Create default settings in data/default_settings.xml"
T011: "Create email templates in data/email_templates.xml"
```

## Parallel Example: User Story 1

```bash
# After T014 (invite_controller) is complete, launch all tests together:
T015: "Unit test test_invite_authorization.py"
T016: "E2E test_us9_s1_invite_flow.sh"
T017: "E2E test_us9_s3_portal_dual_record.sh"
T018: "E2E test_us9_s4_authorization_matrix.sh"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3 + 6 = P1 only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T011)
3. Complete Phase 3: US1 — Invite (T012–T018)
4. Complete Phase 4: US2 — Set Password (T019–T022)
5. Complete Phase 5: US3 — Forgot Password (T023–T026)
6. Complete Phase 6: US6 — Login Verification (T027)
7. **STOP and VALIDATE**: All P1 stories functional, independently testable
8. Deploy/demo MVP

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 + US2 → Test invite + set-password flow → Deploy (MVP core!)
3. Add US3 → Test forgot + reset flow → Deploy (full auth lifecycle)
4. Add US6 → Verify login all profiles → Deploy (MVP complete)
5. Add US4 → Test resend flow → Deploy (P2 increment)
6. Add US5 → Test settings UI → Deploy (P2 complete)
7. Polish → Cross-cutting validation → Final release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (Invite) → US4 (Resend) → US6 (Login tests)
   - Developer B: US2 (Set Password) → US3 (Forgot Password)
   - Developer C: US5 (Settings UI) → Polish
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `# public endpoint` comment required above `@http.route` for unauthenticated endpoints
- Authenticated endpoints require triple decorators: `@require_jwt` + `@require_session` + `@require_company`
- Portal dual record (US1) is the highest complexity task — ensure atomic transaction
- US6 requires NO code changes — verification only via E2E tests
- All test file names follow existing convention: `test_us9_sN_*.sh` for E2E API
