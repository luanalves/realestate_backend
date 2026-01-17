# Tasks: Dual Authentication for Remaining API Endpoints

**Feature ID**: 002-dual-auth-remaining-endpoints  
**Branch**: `002-dual-auth-remaining-endpoints`  
**Status**: Ready for Implementation  
**Effort**: 14-16 hours (2 working days at 7-8 hours/day)

**Input Documents**: 
- [spec.md](spec.md) - Complete specification with clarifications
- [plan.md](plan.md) - 4-phase implementation approach
- [research.md](research.md) - Endpoint inventory showing all 23 endpoints already protected
- [data-model.md](data-model.md) - Session entity reference

**Organization**: Tasks organized by implementation phases from plan.md. This is primarily a validation, documentation, and testing feature - all decorators are already applied.

---

## Format: `- [ ] [ID] [P?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- All paths relative to repository root

---

## Phase 0: Quick Wins (Day 1 Morning - 1 hour)

**Goal**: Clean up code quality issues in middleware

### Code Cleanup

- [X] T001 [P] Remove debug log at line 159 in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py (`[SESSION DEBUG] Checking session`)
- [X] T002 [P] Remove debug log at line 168 in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py (`[SESSION DEBUG] Session found in Redis`)
- [X] T003 [P] Remove debug log at line 170 in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py (`[SESSION DEBUG] Validating fingerprint`)
- [X] T004 [P] Remove debug log at line 179 in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py (`[SESSION DEBUG] Fingerprint validated`)

### Session Validation

- [X] T005 Add session_id length validation (60-100 chars acceptable range; ~80 expected) in @require_session decorator in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
- [X] T006 Add error response for invalid session_id format: `{'error': {'status': 401, 'message': 'Invalid session_id format (must be 60-100 characters)'}}` in 18.0/extra-addons/thedevkitchen_apigateway/middleware.py

### Validation Tests

- [X] T007 Test session_id too short (10 chars) → expect 401 response
- [X] T008 Test session_id too long (150 chars) → expect 401 response
- [X] T009 Test session_id valid length (80 chars) → expect success
- [X] T009a Test session_id extraction priority: kwargs overrides body overrides headers (FR2 compliance)

**Checkpoint**: Clean middleware, validation working, extraction priority tested, quick wins complete

---

## Phase 1: Postman Collection (Day 1-2 - 6-8 hours)

**Goal**: Create comprehensive API documentation via Postman collection from scratch

### Environment Setup

- [X] T010 Create Postman environment variables in postman/QuicksolAPI_Complete.postman_collection.json:
  - odoo_base_url (http://localhost:8069)
  - oauth_client_id (from .env)
  - oauth_client_secret (from .env)
  - test_user_email (from .env)
  - test_user_password (from .env)
  - access_token (auto-set by scripts)
  - session_id (auto-set by scripts)

### Folder Structure

- [X] T011 Create folder "1. Authentication" in Postman collection
- [X] T012 Create folder "2. User Authentication" in Postman collection
- [X] T013 Create folder "3. Agents" in Postman collection
- [X] T014 Create folder "4. Properties" in Postman collection
- [X] T015 Create folder "5. Assignments" in Postman collection
- [X] T016 Create folder "6. Commissions" in Postman collection
- [X] T017 Create folder "7. Performance" in Postman collection
- [X] T018 Create folder "8. Master Data" in Postman collection

### Authentication Endpoints (Bearer Only)

- [X] T019 [P] Create "Get OAuth Token" request in folder "1. Authentication" (POST /api/v1/auth/token) with test script to set access_token
- [X] T020 [P] Create "Refresh Token" request in folder "1. Authentication" (POST /api/v1/auth/token with grant_type=refresh_token)
- [X] T021 [P] Create "Revoke Token" request in folder "1. Authentication" (POST /api/v1/auth/revoke)

### User Authentication Endpoints (Dual Auth)

- [X] T022 Create "User Login" request in folder "2. User Authentication" (POST /api/v1/users/login) with CRITICAL test script to capture session_id from jsonData.result.session_id (NOT cookies) - See plan.md lines 227-237 for exact JavaScript template
- [X] T023 [P] Create "User Logout" request in folder "2. User Authentication" (POST /api/v1/users/logout + session_id)
- [X] T024 [P] Create "User Profile" request in folder "2. User Authentication" (GET /api/v1/users/profile + session_id)
- [X] T025 [P] Create "Change Password" request in folder "2. User Authentication" (POST /api/v1/users/change-password + session_id)
- [X] T026 [P] Create "Get Current User" request in folder "2. User Authentication" (GET /api/v1/me + session_id)

### Agents Endpoints (11 total - Dual Auth)

- [X] T027 [P] Create "List Agents" request (GET /api/v1/agents + session_id) with auth requirements in description
- [X] T028 [P] Create "Create Agent" request (POST /api/v1/agents + session_id) with JSON-RPC body template
- [X] T029 [P] Create "Get Agent" request (GET /api/v1/agents/{id} + session_id)
- [X] T030 [P] Create "Update Agent" request (PUT /api/v1/agents/{id} + session_id)
- [X] T031 [P] Create "Deactivate Agent" request (POST /api/v1/agents/{id}/deactivate + session_id)
- [X] T032 [P] Create "Reactivate Agent" request (POST /api/v1/agents/{id}/reactivate + session_id)
- [X] T033 [P] Create "Agent Properties" request (GET /api/v1/agents/{id}/properties + session_id)
- [X] T034 [P] Create "Agent Performance" request (GET /api/v1/agents/{id}/performance + session_id)
- [X] T035 [P] Create "Agent Ranking" request (GET /api/v1/agents/ranking + session_id)
- [X] T036 [P] Create "Create Commission Rule" request (POST /api/v1/agents/{id}/commission-rules + session_id)
- [X] T037 [P] Create "Get Commission Rules" request (GET /api/v1/agents/{id}/commission-rules + session_id)

### Properties Endpoints (4 total - Dual Auth)

- [X] T038 [P] Create "Create Property" request (POST /api/v1/properties + session_id)
- [X] T039 [P] Create "Get Property" request (GET /api/v1/properties/{id} + session_id)
- [X] T040 [P] Create "Update Property" request (PUT /api/v1/properties/{id} + session_id)
- [X] T041 [P] Create "Delete Property" request (DELETE /api/v1/properties/{id} + session_id)

### Assignments Endpoints (2 total - Dual Auth)

- [X] T042 [P] Create "Create Assignment" request (POST /api/v1/assignments + session_id)
- [X] T043 [P] Create "Get Assignment" request (GET /api/v1/assignments/{id} + session_id)

### Commissions Endpoints (4 total - Dual Auth)

- [X] T044 [P] Create "Update Commission Rule" request (PUT /api/v1/commission-rules/{id} + session_id)
- [X] T045 [P] Create "Create Transaction" request (POST /api/v1/commission-transactions + session_id)
- [X] T046 [P] Create "Calculate Commission" request (POST /api/v1/commissions/calculate + session_id)
- [X] T047 [P] Create "List Commissions" request (GET /api/v1/commissions + session_id)

### Master Data Endpoints (Bearer Only - No Session)

- [X] T048 [P] Create "List Agents (Master)" request (GET /api/v1/agents - master data version) with note: Bearer only, NO session_id required

### Documentation for All Endpoints

- [X] T049 Add authentication requirements to all dual auth endpoint descriptions (lines: "Bearer Token: Required", "Session ID: Required", "Fingerprint validation active")
- [X] T050 Add User-Agent consistency warning to all dual auth endpoint descriptions
- [X] T051 Add session expiration note (2 hours inactivity) to all dual auth endpoint descriptions
- [X] T052 Add JSON-RPC example request body to all endpoint descriptions

**Checkpoint**: Postman collection complete with ~50 endpoints, all scripts working

---

## Phase 2: Documentation (Day 2 - 3 hours)

**Goal**: Document User-Agent requirement and create troubleshooting guide

### API Authentication Guide

- [X] T053 Create docs/api-authentication.md with dual authentication model explanation
- [X] T054 Add OAuth flow documentation (how to get bearer token) to docs/api-authentication.md
- [X] T055 Add user login flow documentation (how to get session_id) to docs/api-authentication.md
- [X] T056 Add request format examples (bearer + session_id in body) to docs/api-authentication.md
- [X] T057 Add session lifecycle diagram (login → requests → logout) to docs/api-authentication.md
- [X] T058 Add fingerprint validation explanation (IP + User-Agent + Accept-Language) to docs/api-authentication.md

### Troubleshooting Guide

- [X] T059 Create docs/troubleshooting-sessions.md with common session issues section
- [X] T060 Add "Session validation failed" troubleshooting entry (User-Agent mismatch) to docs/troubleshooting-sessions.md
- [X] T061 Add "Session required" troubleshooting entry (missing session_id) to docs/troubleshooting-sessions.md
- [X] T062 Add "Session expired" troubleshooting entry (> 2 hours inactivity) to docs/troubleshooting-sessions.md
- [X] T063 Add "Invalid session_id format" troubleshooting entry (length validation) to docs/troubleshooting-sessions.md
- [X] T064 Add examples and error messages for each issue to docs/troubleshooting-sessions.md

### Controller Docstrings

- [X] T065 Update docstring for all 11 Agents endpoints in 18.0/extra-addons/quicksol_estate/controllers/agent_api.py (add User-Agent requirement note - see spec.md Appendix for template starting line 366)
- [X] T066 Update docstring for all 4 Properties endpoints in 18.0/extra-addons/quicksol_estate/controllers/property_api.py (add fingerprint validation note)
- [X] T067 Update docstring for Assignments endpoints (add session security notes)
- [X] T068 Update docstring for Commissions endpoints (add session security notes)

**Checkpoint**: Complete authentication and troubleshooting documentation

---

## Phase 3: E2E Tests (Day 2 - 2.5 hours)

**Goal**: Create validation tests for each domain (5 total)

### Agents Domain E2E Test

- [X] T069 Create cypress/e2e/agents-dual-auth.cy.js with OAuth token acquisition in before() hook
- [X] T070 Add user login flow to get session_id in cypress/e2e/agents-dual-auth.cy.js
- [X] T071 Add test: "should reject request without bearer token" for GET /api/v1/agents
- [X] T072 Add test: "should reject request without session_id" for GET /api/v1/agents
- [X] T073 Add test: "should succeed with valid bearer + session" for GET /api/v1/agents
- [X] T074 Add test: "should reject request with different User-Agent (fingerprint)" for GET /api/v1/agents

### Properties Domain E2E Test

- [X] T075 Create cypress/e2e/properties-dual-auth.cy.js with complete auth flow
- [X] T076 Add test: "should reject request without bearer token" for GET /api/v1/properties/{id}
- [X] T077 Add test: "should reject request without session_id" for GET /api/v1/properties/{id}
- [X] T078 Add test: "should succeed with valid bearer + session" for GET /api/v1/properties/{id}
- [X] T079 Add test: "should reject request with different User-Agent" for GET /api/v1/properties/{id}

### Assignments Domain E2E Test

- [X] T080 Create cypress/e2e/assignments-dual-auth.cy.js with complete auth flow
- [X] T081 Add test: "should reject request without bearer token" for POST /api/v1/assignments
- [X] T082 Add test: "should reject request without session_id" for POST /api/v1/assignments
- [X] T083 Add test: "should succeed with valid bearer + session" for POST /api/v1/assignments
- [X] T084 Add test: "should reject request with different User-Agent" for POST /api/v1/assignments

### Commissions Domain E2E Test

- [X] T085 Create cypress/e2e/commissions-dual-auth.cy.js with complete auth flow
- [X] T086 Add test: "should reject request without bearer token" for POST /api/v1/commissions/calculate
- [X] T087 Add test: "should reject request without session_id" for POST /api/v1/commissions/calculate
- [X] T088 Add test: "should succeed with valid bearer + session" for POST /api/v1/commissions/calculate
- [X] T089 Add test: "should reject request with different User-Agent" for POST /api/v1/commissions/calculate

### Performance Domain E2E Test

- [X] T090 Create cypress/e2e/performance-dual-auth.cy.js with complete auth flow
- [X] T091 Add test: "should reject request without bearer token" for GET /api/v1/agents/{id}/performance
- [X] T092 Add test: "should reject request without session_id" for GET /api/v1/agents/{id}/performance
- [X] T093 Add test: "should succeed with valid bearer + session" for GET /api/v1/agents/{id}/performance
- [X] T094 Add test: "should reject request with different User-Agent" for GET /api/v1/agents/{id}/performance

**Checkpoint**: 5 E2E tests complete, all passing

---

## Phase 4: Validation & Cleanup (Day 2 Afternoon - 1.5 hours)

**Goal**: Verify everything works and clean up

### Test Execution

- [ ] T095 Run all Cypress E2E tests: `cd 18.0 && npx cypress run`
- [ ] T096 Verify all 5 domain tests pass (agents, properties, assignments, commissions, performance)
- [ ] T097 Run manual Postman collection test (login → agents → properties → success)

### Code Review

- [ ] T098 Verify no debug logs remain: `grep -r "SESSION DEBUG" 18.0/extra-addons/thedevkitchen_apigateway/middleware.py` (expect 0 results)
- [ ] T098a [P] Validate @require_company decorator present on all 23 endpoints requiring multi-tenant isolation (constitution compliance)
- [ ] T098b [P] Document which endpoints intentionally omit @require_company (if any) with justification
- [ ] T099 Verify session_id validation works: Test with curl/Postman using 10-char session_id → expect 401
- [ ] T100 Review Postman collection completeness: Verify all ~50 endpoints present
- [ ] T101 Review E2E tests for consistency: Check all 5 tests follow same pattern

### Git Operations

- [X] T103 Commit middleware changes: `git add 18.0/extra-addons/thedevkitchen_apigateway/middleware.py && git commit -m "feat: remove debug logs and add session_id validation"`
- [X] T104 Commit Postman collection: `git add postman/QuicksolAPI_Complete.postman_collection.json && git commit -m "docs: create complete Postman API collection"`
- [X] T105 Commit E2E tests: `git add cypress/e2e/*-dual-auth.cy.js && git commit -m "test: add E2E validation tests for dual auth"`
- [X] T106 Commit documentation: `git add docs/api-authentication.md docs/troubleshooting-sessions.md && git commit -m "docs: add authentication and troubleshooting guides"`
- [X] T106a Push to GitHub: `git push origin 002-dual-auth-remaining-endpoints`

### Coverage Verification (Constitution Requirement)

- [ ] T107 Run test coverage report: `cd 18.0 && pytest --cov=extra-addons/thedevkitchen_apigateway --cov=extra-addons/quicksol_estate/controllers --cov-report=term-missing`
- [ ] T107a Verify coverage ≥ 80% for middleware.py (constitution ADR-003 compliance)
- [ ] T107b Verify coverage ≥ 80% for all validated controller files (agent_api.py, property_api.py)

### Status Updates

- [X] T108 Update specs/002-dual-auth-remaining-endpoints/SUMMARY.md with completion status
- [X] T109 Update docs/IMPLEMENTATION_STATUS.md with spec 002 completion
- [X] T110 Mark spec as complete in spec.md header: Status: Complete

**Checkpoint**: All work complete, tested, coverage verified ≥80%, committed, and pushed

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Phase 0 (Quick Wins)**: No dependencies - can start immediately
2. **Phase 1 (Postman Collection)**: Depends on Phase 0 (clean middleware needed for accurate testing)
3. **Phase 2 (Documentation)**: Depends on Phase 1 (need collection complete for reference)
4. **Phase 3 (E2E Tests)**: Depends on Phase 1 (need working collection for test guidance)
5. **Phase 4 (Validation)**: Depends on ALL previous phases

### Parallel Opportunities

**Phase 0**:
- T001-T004 (debug log removal) can run in parallel
- T005-T006 (validation logic) sequential (same function)
- T007-T009 (tests) can run in parallel after T006

**Phase 1**:
- T011-T018 (folder creation) can run in parallel
- T019-T021 (auth endpoints) can run in parallel
- T023-T026 (user auth) can run in parallel AFTER T022 (login must be first)
- T027-T037 (agents) can run in parallel
- T038-T041 (properties) can run in parallel
- T042-T043 (assignments) can run in parallel
- T044-T047 (commissions) can run in parallel
- T049-T052 (documentation) sequential (affects all endpoints)

**Phase 2**:
- T053-T058 (API guide) sequential (same file)
- T059-T064 (troubleshooting) sequential (same file)
- T065-T068 (docstrings) can run in parallel (different files)
- Phase 2 subtasks can overlap: API guide || Troubleshooting || Docstrings

**Phase 3**:
- All T069-T094 (5 E2E tests) can run in PARALLEL (different files)

**Phase 4**:
- T095-T097 (tests) sequential
- T098-T101 (review) can run in parallel
- T102-T106 (git) sequential (commit order matters)
- T107-T109 (status) can run in parallel

---

## Implementation Strategy

### MVP Scope (Day 1 - 8 hours)

**Goal**: Basic validation and most critical documentation

- Phase 0: Quick Wins (1 hour)
- Phase 1: Minimal Postman Collection (5 hours)
  - Authentication folder + User Authentication folder + Agents folder only
  - Total ~20 endpoints instead of 50
- Phase 2: API Authentication Guide only (2 hours)
  - Skip troubleshooting guide (can add later)
  - Skip docstring updates (can add later)

**MVP Deliverable**: Clean middleware + working Postman collection for core flows + basic auth guide

### Full Scope (Day 2 - 8 hours)

**Goal**: Complete all remaining work

- Phase 1: Complete Postman Collection (3 hours)
  - Add remaining folders (Properties, Assignments, Commissions, Performance, Master Data)
  - Add endpoint documentation
- Phase 2: Complete Documentation (1 hour)
  - Troubleshooting guide
  - Docstring updates
- Phase 3: E2E Tests (2.5 hours)
  - All 5 domain tests
- Phase 4: Validation & Cleanup (1.5 hours)

**Full Deliverable**: Complete spec implementation ready for production

---

## Validation Criteria

### Code Quality ✅
- [ ] Zero debug logs in middleware.py (grep verification)
- [ ] Session_id length validation working (60-100 chars acceptable range)
- [ ] Session_id extraction priority correct (kwargs → body → headers)
- [ ] All 23 endpoints have correct decorators (@require_jwt + @require_session + @require_company where needed)

### Documentation ✅
- [ ] Postman collection complete with ~50 endpoints
- [ ] All endpoint descriptions include auth requirements
- [ ] API authentication guide created and accurate
- [ ] Troubleshooting guide created with examples

### Testing ✅
- [ ] 5 E2E tests passing (one per domain)
- [ ] All tests use .env credentials
- [ ] Fingerprint validation tested in each domain
- [ ] Manual Postman flow tested (login → request → success)
- [ ] Test coverage ≥ 80% verified for middleware.py and controllers (constitution ADR-003)

### Usability ✅
- [ ] Postman "User Login" captures session_id from body (NOT cookie)
- [ ] All requests use {{session_id}} variable correctly
- [ ] Clear error messages for missing bearer/session
- [ ] User-Agent consistency requirement documented

---

## Total Task Count

- **Phase 0**: 10 tasks (1 hour) - includes extraction priority test
- **Phase 1**: 43 tasks (6-8 hours) - LARGEST PHASE
- **Phase 2**: 16 tasks (3 hours)
- **Phase 3**: 26 tasks (2.5 hours)
- **Phase 4**: 20 tasks (1.5 hours) - includes coverage verification + company decorator validation

**TOTAL**: 115 tasks across 14-16 hours

---

## Notes

**Key Insight**: This is NOT a decorator implementation feature - it's a validation, documentation, and testing feature. All code is already protected.

**Primary Deliverable**: Complete Postman collection (Phase 1 = 40% of total effort)

**Critical Task**: T022 (User Login script) - must capture session_id from response body, NOT cookies (lesson from spec 001)

**Parallel Efficiency**: ~60% of tasks marked [P] can run in parallel, enabling 1-2 day completion with focused effort

**Testing Strategy**: E2E tests are validation-focused (not coverage) - 4 tests per domain is sufficient to confirm dual auth works
