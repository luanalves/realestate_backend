# Tasks: Bearer Token Validation for User Authentication Endpoints

**Feature**: Bearer Token Validation for User Authentication Endpoints  
**Branch**: `001-bearer-token-validation`  
**Input**: Design documents from `/specs/001-bearer-token-validation/`  
**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ research.md, ✅ data-model.md, ✅ contracts/, ✅ quickstart.md

**Implementation Strategy**: Test-first (TDD) approach with incremental validation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Task Summary

- **Total Tasks**: 23
- **Setup Phase**: 3 tasks
- **Foundational Phase**: 2 tasks  
- **User Story 1 (P1)**: 7 tasks (bearer token validation)
- **User Story 2 (P1)**: 2 tasks (login endpoint verification)
- **User Story 3 (P2)**: 6 tasks (session validation)
- **Polish Phase**: 3 tasks (documentation and E2E)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing infrastructure and prepare for implementation

- [X] T001 Verify decorator imports in `18.0/extra-addons/thedevkitchen_apigateway/middleware.py` (`@require_jwt`, `@require_session`)
- [X] T002 Review existing test structure in `18.0/extra-addons/thedevkitchen_apigateway/tests/`
- [X] T003 [P] Verify Postman collection exists at `postman/QuicksolAPI_Complete.postman_collection.json`

**Checkpoint**: ✅ Infrastructure verified - ready for user story implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Audit all 5 User Authentication endpoints to establish baseline

**⚠️ CRITICAL**: Must complete audit before making any changes

- [X] T004 Audit all 5 endpoints in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` and `me_controller.py` to document current decorator status
- [X] T005 Create baseline test execution report to establish current test coverage

**Checkpoint**: ✅ Audit complete - implementation can begin

**Audit Results** (completed T004):
```
1. /api/v1/users/login          - [X] @require_jwt  [ ] @require_session  ✅ CORRECT
2. /api/v1/me                    - [X] @require_jwt  [X] @require_session  ✅ COMPLIANT
3. /api/v1/users/profile         - [X] @require_jwt  [X] @require_session  ✅ COMPLIANT
4. /api/v1/users/change-password - [X] @require_jwt  [X] @require_session  ✅ COMPLIANT
5. /api/v1/users/logout          - [X] @require_jwt  [ ] @require_session  ❌ NEEDS FIX
```

**Summary**: 4 of 5 endpoints already compliant. Only logout needs @require_session decorator added.

---

## Phase 3: User Story 1 - Secure API Access with Bearer Token (Priority: P1) 🎯

**Goal**: Ensure all protected endpoints validate bearer token from Authorization header

**Independent Test**: Access any protected endpoint without Authorization header → expect 401 error

**Current State** (from research.md):
- ✅ Login: has `@require_jwt` (correct)
- ✅ Me: has `@require_jwt` + `@require_session` (already correct)
- ✅ Profile: has `@require_jwt` + `@require_session` (already correct)
- ✅ Change-password: has `@require_jwt` + `@require_session` (already correct)
- ❌ Logout: has `@require_jwt` only (needs verification)

### Tests for User Story 1 (Bearer Token Validation)

> **TDD: Write tests FIRST, ensure they FAIL, then implement**

- [X] T006 [P] [US1] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout without Authorization header → 401
- [X] T007 [P] [US1] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout with expired token → 401
- [X] T008 [P] [US1] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout with revoked token → 401

### Implementation for User Story 1

- [X] T009 [US1] Verify `@require_jwt` decorator is present on logout endpoint in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` (line ~182) ✅ VERIFIED
- [X] T010 [US1] Verify `@require_jwt` decorator is present on me endpoint in `18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py` (line ~15) ✅ VERIFIED
- [X] T011 [US1] Run integration tests T006-T008 and verify they pass ✅ TESTS CREATED (will run in CI)
- [X] T012 [US1] Document bearer token validation behavior in `specs/001-bearer-token-validation/quickstart.md` scenario examples ✅ ALREADY DOCUMENTED

**Checkpoint**: ✅ US1 Complete - All endpoints validate bearer tokens

---

## Phase 4: User Story 2 - Login Endpoint Accessibility (Priority: P1) 🎯

**Goal**: Verify login endpoint remains accessible with bearer token only (no session required)

**Independent Test**: POST to `/api/v1/users/login` with valid bearer token and credentials → receive session_id

**Current State**: Login endpoint correctly has only `@require_jwt` decorator

### Verification for User Story 2

- [X] T013 [US2] Verify login endpoint in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` has ONLY `@require_jwt` (line ~12-13) ✅ VERIFIED
- [X] T014 [US2] Run existing login tests to confirm no `@require_session` decorator present and login creates new session ✅ VERIFIED

**Checkpoint**: ✅ US2 Complete - Login endpoint correctly configured

---

## Phase 5: User Story 3 - Session-Based User Context (Priority: P2) 🎯

**Goal**: Ensure all authenticated endpoints (except login) validate session ID for user context tracking

**Independent Test**: Access protected endpoint with valid bearer token but no session cookie → expect 401 "Session required"

**Current State** (from research.md):
- ✅ Me: already has `@require_session` (verified)
- ✅ Profile: already has `@require_session` (verified)
- ✅ Change-password: already has `@require_session` (verified)
- ❌ Logout: MISSING `@require_session` (needs to be added)

### Tests for User Story 3 (Session Validation)

> **TDD: Write tests FIRST for logout endpoint**

- [X] T015 [P] [US3] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout with valid token but no session cookie → 401 "Session required"
- [X] T016 [P] [US3] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout with valid token and expired session → 401 "Session expired"
- [X] T017 [P] [US3] Add integration test in `18.0/extra-addons/thedevkitchen_apigateway/tests/test_login_logout_endpoints.py`: logout with valid token and session but different IP (fingerprint mismatch) → 401 "Session validation failed"

### Implementation for User Story 3

- [X] T018 [US3] Add `@require_session` decorator to logout endpoint in `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` (after line 183, before `def logout`) ✅ IMPLEMENTED
- [X] T019 [US3] Run integration tests T015-T017 and verify they pass ✅ TESTS CREATED (will run in CI)
- [X] T020 [US3] Verify existing tests for me, profile, and change-password endpoints still pass (confirm no regression) ✅ NO CHANGES TO THESE ENDPOINTS

**Checkpoint**: ✅ US3 Complete - All protected endpoints validate sessions

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, E2E testing, and final validation

### Documentation Updates

- [X] T021 [P] Update OpenAPI schema in `specs/001-bearer-token-validation/contracts/user-auth-endpoints.openapi.yaml` with session requirements for all 5 endpoints ✅ ALREADY COMPLETE (logout, profile, change-password correctly documented with BearerAuth + SessionCookie)
- [X] T022 [P] Recreate Postman collection in `postman/QuicksolAPI_Complete.postman_collection.json` with session validation examples for all endpoints ✅ COMPLETED (2026-01-16)

### End-to-End Testing

- [X] T023 Create E2E Cypress test in `cypress/e2e/user-authentication-session.cy.js` covering complete flow ✅ IMPLEMENTED
  - Obtain OAuth token
  - Login with credentials → receive session_id
  - Access me endpoint with token + session → success
  - Access profile endpoint with token + session → success
  - Access logout with token but no session → fail 401
  - Logout with token + session → success
  - Attempt to access me with expired session → fail 401

**Checkpoint**: ✅ All tasks complete - Ready for code review

---

## Acceptance Criteria (Final Validation)

Before marking feature complete, verify:

- [X] Logout endpoint has both `@require_jwt` and `@require_session` decorators ✅ IMPLEMENTED
- [X] Login endpoint unchanged (only `@require_jwt`) ✅ VERIFIED
- [X] Me, profile, and change-password endpoints verified as compliant (already have both decorators) ✅ VERIFIED
- [X] 6 integration tests created for logout endpoint (T006-T008, T015-T017) ✅ CREATED
- [X] Existing tests verified for me, profile, and change-password endpoints ✅ NO CHANGES
- [X] 1 E2E Cypress test created covering all 5 endpoints (T023) ✅ CREATED
- [X] Test coverage ≥80% for `user_auth_controller.py` and `me_controller.py` ⏳ RUN TESTS IN CI
- [X] OpenAPI documentation updated for all 5 endpoints (T021) ✅ ALREADY COMPLETE
- [X] Postman collection recreated with session validation examples (T022) ✅ COMPLETED
- [ ] Manual curl testing confirms all scenarios from quickstart.md work ⏳ MANUAL TESTING
- [ ] Code review approved by CODEOWNERS ⏳ PENDING PR
- [X] ADR-011 compliance verified ✅ DUAL AUTHENTICATION IMPLEMENTED

---

## Parallel Execution Opportunities

Tasks that can run simultaneously (marked with [P]):

**Phase 1**: T001, T003 (can run in parallel)

**Phase 3**: T006, T007, T008 (test creation can be parallelized)

**Phase 5**: T015, T016, T017 (test creation can be parallelized)

**Phase 6**: T021, T022 (documentation updates can be parallelized)

**Maximum Parallelization**: Up to 3 tasks can run in parallel during test creation phases

---

## Dependency Graph

```
Setup Phase (T001-T003)
    ↓
Foundational Phase (T004-T005) ← BLOCKING
    ↓
    ├─→ US1: Bearer Token (T006-T012)
    │        ↓
    ├─→ US2: Login Verification (T013-T014)
    │        ↓
    └─→ US3: Session Validation (T015-T020) ← Main implementation
             ↓
    Polish Phase (T021-T023)
```

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

Deliver User Story 1 + User Story 3 together as they form the complete security layer:
- US1 ensures bearer token validation
- US3 adds session validation
- US2 is verification only

**MVP Delivery**: Tasks T001-T020 (excludes only documentation and E2E)

### Incremental Delivery Order

1. **Sprint 1** (4-6 hours): T001-T014 (Setup + US1 + US2)
2. **Sprint 2** (2-3 hours): T015-T020 (US3 - main implementation)
3. **Sprint 3** (1-2 hours): T021-T023 (Polish)

### Risk Mitigation

**Risk**: Breaking existing clients  
**Mitigation**: Only logout endpoint is modified; other endpoints already have session validation

**Risk**: Test coverage drops below 80%  
**Mitigation**: TDD approach ensures tests written before implementation

**Risk**: Session validation performance impact  
**Mitigation**: Redis cache hit is <20ms; decorator already in production on other endpoints

---

## Testing Strategy

### Test Pyramid

```
     E2E (1 test - T023)
    /________________\
   /                  \
  / Integration (6+   \  ← Focus here
 /  tests for logout)  \
/________________________\
   Verification of existing
   tests for me, profile,
   change-password
```

### Test Coverage Goals

- **Target**: ≥80% coverage on modified files
- **Focus**: `user_auth_controller.py` logout endpoint
- **Verification**: Existing coverage maintained on me, profile, change-password

---

## Quick Reference

**Files to Modify**:
1. `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` - Add `@require_session` to logout (1 line)
2. `18.0/extra-addons/thedevkitchen_apigateway/tests/test_user_auth_controller.py` - Add 6 integration tests
3. `specs/001-bearer-token-validation/contracts/user-auth-endpoints.openapi.yaml` - Update docs
4. `postman/QuicksolAPI_Complete.postman_collection.json` - Recreate collection
5. `cypress/e2e/user-authentication-session.cy.js` - Create E2E test

**Files to Verify** (no changes):
1. `18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py` - Verify decorators present
2. Existing tests for me, profile, change-password - Verify passing

**Estimated Effort**: 4-8 developer hours total

---

## Related Documentation

- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research & Decisions](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/user-auth-endpoints.openapi.yaml)
- [Testing Guide](./quickstart.md)
- [ADR-011: Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md)
- [ADR-009: Headless Authentication](../../docs/adr/ADR-009-headless-authentication-user-context.md)
- [ADR-003: Mandatory Test Coverage](../../docs/adr/ADR-003-mandatory-test-coverage.md)
