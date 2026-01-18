# Implementation Plan: Dual Authentication for Remaining API Endpoints

**Branch**: `002-dual-auth-remaining-endpoints` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)  
**Status**: Ready for Implementation  
**Effort**: 14-16 hours (2 working days at 7-8 hours/day, reduced from 3-4 days)

## Summary

**Primary Requirement**: Ensure consistent dual authentication (Bearer Token + Session validation) across all 23 business API endpoints.

**Key Discovery**: All 23 business endpoints already have `@require_jwt` + `@require_session` decorators applied. This fundamentally changes the approach from "add decorators" to "validate + document + test".

**Technical Approach**: 
1. Validate existing decorators work correctly
2. Create comprehensive Postman collection from scratch (file is currently empty)
3. Remove 4 debug log statements from middleware
4. Add session_id length validation (60-100 characters)
5. Document User-Agent consistency requirement
6. Create 5 E2E tests for validation (not coverage)

## Technical Context

**Language/Version**: Python 3.11+  
**Framework**: Odoo 18.0  
**Primary Dependencies**: 
- Odoo ORM and HTTP routing
- Authlib 1.3+ (OAuth 2.0 + JWT)
- Redis 7 (session storage)
- PostgreSQL 16 (persistent data)

**Storage**: 
- PostgreSQL: `thedevkitchen_api_session` table (10 fields, 3 indexes)
- Redis DB 1: Session cache (7200s TTL)

**Testing**: 
- Odoo Test Suite (integration tests)
- Cypress 13+ (E2E tests)
- Manual testing with Postman

**Target Platform**: Docker containers (Linux)  
**Project Type**: Web backend API  
**Performance Goals**: 
- Session validation: < 50ms overhead per request
- Fingerprint check: < 20ms
- No measurable performance degradation

**Constraints**: 
- JSON-RPC compatibility (must return dict, not HTTP Response)
- User-Agent must remain constant during session lifetime
- Session expires after 2 hours of inactivity
- Must maintain backward compatibility with Master Data endpoints (bearer only)

**Scale/Scope**: 
- 23 business endpoints to validate
- Complete Postman collection creation (~50+ endpoints total)
- 5 E2E tests (one per domain)
- ~80 lines session_id format documentation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ADR-011: Controller Security ✅ PASS
- [x] All endpoints have `@require_jwt` decorator (23/23 verified)
- [x] All endpoints have `@require_session` decorator (23/23 verified, except Master Data)
- [x] Session fingerprint validation active (IP + User-Agent + Language)
- [x] Multi-tenancy isolation with `@require_company` where appropriate

**Status**: PASS - All security requirements met. This spec validates/documents existing implementation.

### ADR-003: Mandatory Test Coverage ⚠️ IN PROGRESS
- [ ] E2E tests for each domain (5 total) - **TO BE CREATED**
- [x] Integration tests for decorators (covered in spec 001)
- [ ] Test coverage > 80% - **TO BE VERIFIED**

**Status**: PARTIAL - E2E tests are the main deliverable of this spec.

### ADR-005: OpenAPI 3.0 Documentation ⚠️ PARTIAL  
- [ ] Postman collection complete - **TO BE CREATED (currently empty)**
- [ ] OpenAPI/Swagger documentation - **OUT OF SCOPE** (separate task)
- [ ] Endpoint descriptions with auth requirements - **TO BE ADDED**

**Status**: PARTIAL - Postman collection is the main documentation deliverable.

### ADR-006: Git Flow Workflow ✅ PASS
- [x] Feature branch created: `002-dual-auth-remaining-endpoints`
- [x] Spec documentation in place (spec.md, research.md, data-model.md, quickstart.md)
- [ ] Implementation commits - **PENDING**
- [ ] Pull request - **PENDING**

**Status**: PASS - Branch and specs complete, implementation pending.

### Violations Requiring Justification

**None** - All constitution requirements are either met or explicitly scoped into this implementation.

## Project Structure

### Documentation (this feature)

```text
specs/002-dual-auth-remaining-endpoints/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file (IN PROGRESS)
├── research.md          # Endpoint inventory & analysis (COMPLETE)
├── data-model.md        # Session entity documentation (COMPLETE)
├── quickstart.md        # Testing guide (COMPLETE)
├── tasks.md             # Granular task breakdown (EXISTS - needs update)
├── README.md            # Quick reference (COMPLETE)
└── SUMMARY.md           # Executive summary (COMPLETE)
```

### Source Code (Odoo backend)

```text
18.0/extra-addons/
├── thedevkitchen_apigateway/
│   ├── middleware.py                    # ⚠️ MODIFY: Remove 4 debug logs, add validation
│   ├── models/
│   │   └── api_session.py               # ✅ NO CHANGE: Session entity (reference only)
│   ├── controllers/
│   │   ├── user_auth_controller.py      # ✅ NO CHANGE: Completed in spec 001
│   │   └── me_controller.py             # ✅ NO CHANGE: Completed in spec 001
│   └── tests/
│       └── test_dual_auth_validation.py # 🆕 CREATE: Validation tests
│
└── quicksol_estate/
    ├── controllers/
    │   ├── agent_api.py                 # ✅ VALIDATE ONLY: 11 endpoints already protected
    │   ├── property_api.py              # ✅ VALIDATE ONLY: 4 endpoints already protected
    │   └── master_data_api.py           # ✅ NO CHANGE: Bearer only (correct)
    └── tests/
        └── test_endpoints_dual_auth.py  # 🆕 CREATE: Endpoint validation tests

postman/
└── QuicksolAPI_Complete.postman_collection.json  # 🆕 CREATE: Complete from scratch (0 bytes)

cypress/e2e/
├── agents-dual-auth.cy.js               # 🆕 CREATE: Agents E2E test
├── properties-dual-auth.cy.js           # 🆕 CREATE: Properties E2E test
├── assignments-dual-auth.cy.js          # 🆕 CREATE: Assignments E2E test
├── commissions-dual-auth.cy.js          # 🆕 CREATE: Commissions E2E test
└── performance-dual-auth.cy.js          # 🆕 CREATE: Performance E2E test

docs/
├── api-authentication.md                # 🆕 CREATE: Authentication guide
└── troubleshooting-sessions.md          # 🆕 CREATE: Session troubleshooting
```

**Structure Decision**: This is a validation/documentation feature, not a code implementation feature. Most work is creating Postman collection and E2E tests. Only 2 files need code modification (middleware.py for cleanup and validation).

## Complexity Tracking

> **No constitution violations to justify**

All ADR requirements are either met or explicitly scoped into this implementation. The only "violations" are work items (E2E tests, Postman collection) which are the deliverables of this spec.

---

## Implementation Phases

### Phase 0: Quick Wins (Day 1 Morning - 1 hour)

**Goal**: Clean up code quality issues

**Tasks**:
1. Remove 4 debug log lines from middleware.py
   - Lines 159, 168, 170, 179: Delete `[SESSION DEBUG]` statements
   - Keep security warnings (HIJACKING DETECTED, Invalid session)
   
2. Add session_id length validation
   - In `@require_session` decorator
   - Check: 60 ≤ len(session_id) ≤ 100
   - Return clear error: `{'error': {'status': 401, 'message': 'Invalid session_id format'}}`
   
3. Test validation works
   - Unit test with short session_id (10 chars) → expect 401
   - Unit test with long session_id (150 chars) → expect 401
   - Unit test with valid session_id (80 chars) → expect success

**Deliverables**:
- ✅ Clean middleware.py (no debug logs)
- ✅ Session validation working
- ✅ Tests passing

---

### Phase 1: Postman Collection (Day 1-2 - 6-8 hours)

**Goal**: Create comprehensive API documentation via Postman

**Approach**: Create complete collection from scratch documenting ALL system endpoints (not just the 23 in-scope).

**Structure**:
```
QuicksolAPI_Complete/
├── Environment Variables
│   ├── odoo_base_url
│   ├── oauth_client_id
│   ├── oauth_client_secret
│   ├── test_user_email
│   ├── test_user_password
│   ├── access_token (auto-set)
│   └── session_id (auto-set)
│
├── 1. Authentication
│   ├── Get OAuth Token (sets access_token)
│   ├── Refresh Token
│   └── Revoke Token
│
├── 2. User Authentication
│   ├── User Login (sets session_id from BODY, not cookie) ⚠️ CRITICAL
│   ├── User Logout
│   ├── User Profile
│   ├── Change Password
│   └── Get Current User (/api/v1/me)
│
├── 3. Agents
│   ├── List Agents (GET /api/v1/agents + session_id)
│   ├── Create Agent (POST /api/v1/agents + session_id)
│   ├── Get Agent (GET /api/v1/agents/{id} + session_id)
│   ├── Update Agent (PUT /api/v1/agents/{id} + session_id)
│   ├── Deactivate Agent (POST /api/v1/agents/{id}/deactivate + session_id)
│   ├── Reactivate Agent (POST /api/v1/agents/{id}/reactivate + session_id)
│   ├── Agent Properties (GET /api/v1/agents/{id}/properties + session_id)
│   ├── Agent Performance (GET /api/v1/agents/{id}/performance + session_id)
│   ├── Agent Ranking (GET /api/v1/agents/ranking + session_id)
│   ├── Commission Rules - Create (POST + session_id)
│   └── Commission Rules - Get (GET + session_id)
│
├── 4. Properties
│   ├── Create Property (POST /api/v1/properties + session_id)
│   ├── Get Property (GET /api/v1/properties/{id} + session_id)
│   ├── Update Property (PUT /api/v1/properties/{id} + session_id)
│   └── Delete Property (DELETE /api/v1/properties/{id} + session_id)
│
├── 5. Assignments
│   ├── Create Assignment (POST /api/v1/assignments + session_id)
│   └── Get Assignment (GET /api/v1/assignments/{id} + session_id)
│
├── 6. Commissions
│   ├── Update Commission Rule (PUT /api/v1/commission-rules/{id} + session_id)
│   └── Create Transaction (POST /api/v1/commission-transactions + session_id)
│
├── 7. Performance
│   └── (covered in Agents section)
│
└── 8. Master Data (bearer only, NO session_id)
    └── List Agents (Master) (GET /api/v1/agents - different endpoint)
```

**Critical Implementation Details**:

1. **Login Script** (Fix from spec 001):
   ```javascript
   // Test script for "User Login"
   if (pm.response.code === 200) {
       const jsonData = pm.response.json();
       if (jsonData.result && jsonData.result.session_id) {
           pm.environment.set('session_id', jsonData.result.session_id);
           console.log('✅ Session ID saved: ' + jsonData.result.session_id);
       } else {
           console.error('❌ No session_id in response');
       }
       // DO NOT capture from cookies - this is the bug from spec 001
   }
   ```

2. **Request Body Template** (for all protected endpoints):
   ```json
   {
     "jsonrpc": "2.0",
     "method": "call",
     "params": {
       "session_id": "{{session_id}}",
       // ... endpoint-specific params
     }
   }
   ```

3. **Endpoint Descriptions** (for each endpoint):
   ```markdown
   **Authentication**: 
   - Bearer Token: Required (in Authorization header)
   - Session ID: Required (in request body params)

   **Security Notes**:
   - Session validation includes fingerprint check (IP, User-Agent, Accept-Language)
   - User-Agent must remain consistent for session duration
   - Session expires after 2 hours of inactivity

   **Example Request**:
   [Include full JSON-RPC request with session_id]
   ```

**Deliverables**:
- ✅ Postman collection with ~50+ endpoints
- ✅ Environment variables configured
- ✅ Test scripts working (login captures session_id correctly)
- ✅ All endpoint descriptions include auth requirements

---

### Phase 2: Documentation (Day 2 - 3 hours)

**Goal**: Document User-Agent requirement and create troubleshooting guide

**Tasks**:

1. **API Authentication Guide** (`docs/api-authentication.md`):
   - Dual authentication model explanation
   - How to get bearer token (OAuth flow)
   - How to get session_id (user login)
   - How to use both in requests
   - Session lifecycle (login → request → logout)
   - Security features (fingerprint validation)

2. **Troubleshooting Guide** (`docs/troubleshooting-sessions.md`):
   ```markdown
   # Common Session Issues
   
   ## "Session validation failed"
   - Cause: User-Agent changed between login and request
   - Solution: Keep User-Agent constant during session
   - Example: Don't switch browsers mid-session
   
   ## "Session required"
   - Cause: session_id not in request body
   - Solution: Add "session_id": "{{session_id}}" to params
   
   ## "Session expired"
   - Cause: Last activity > 2 hours ago
   - Solution: Re-login to get new session
   
   ## "Invalid session_id format"
   - Cause: session_id too short or too long
   - Solution: Use session_id from login response (80 chars)
   ```

3. **Update Controller Docstrings**:
   - Add User-Agent requirement note to all endpoint docstrings
   - Document session fingerprint validation
   - Include security warnings

**Deliverables**:
- ✅ API authentication guide
- ✅ Troubleshooting guide
- ✅ Updated docstrings (23 endpoints)

---

### Phase 3: E2E Tests (Day 2 - 2.5 hours)

**Goal**: Create validation tests for each domain

**Template** (for each domain):
```javascript
describe('Domain Dual Auth Validation', () => {
  let accessToken;
  let sessionId;
  
  before(() => {
    // Get OAuth token
    cy.request({
      method: 'POST',
      url: '/api/v1/auth/token',
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {
          grant_type: 'client_credentials',
          client_id: Cypress.env('oauth_client_id'),
          client_secret: Cypress.env('oauth_client_secret')
        }
      }
    }).then((response) => {
      accessToken = response.body.result.access_token;
    });
    
    // User login
    cy.request({
      method: 'POST',
      url: '/api/v1/users/login',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {
          email: Cypress.env('test_user_email'),
          password: Cypress.env('test_user_password')
        }
      }
    }).then((response) => {
      sessionId = response.body.result.session_id;
    });
  });
  
  it('should reject request without bearer token', () => {
    cy.request({
      method: 'GET',
      url: '/api/v1/endpoint',
      failOnStatusCode: false,
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: { session_id: sessionId }
      }
    }).then((response) => {
      expect(response.status).to.eq(401);
      expect(response.body.error.message).to.include('Bearer token');
    });
  });
  
  it('should reject request without session_id', () => {
    cy.request({
      method: 'GET',
      url: '/api/v1/endpoint',
      failOnStatusCode: false,
      headers: { Authorization: `Bearer ${accessToken}` },
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {}
      }
    }).then((response) => {
      expect(response.status).to.eq(401);
      expect(response.body.error.message).to.include('Session');
    });
  });
  
  it('should succeed with valid bearer + session', () => {
    cy.request({
      method: 'GET',
      url: '/api/v1/endpoint',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: { session_id: sessionId }
      }
    }).then((response) => {
      expect(response.status).to.eq(200);
    });
  });
  
  it('should reject request with different User-Agent (fingerprint)', () => {
    cy.request({
      method: 'GET',
      url: '/api/v1/endpoint',
      failOnStatusCode: false,
      headers: { 
        Authorization: `Bearer ${accessToken}`,
        'User-Agent': 'DifferentBrowser/1.0'
      },
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: { session_id: sessionId }
      }
    }).then((response) => {
      expect(response.status).to.eq(401);
      expect(response.body.error.message).to.include('validation failed');
    });
  });
});
```

**Create 5 Tests**:
1. `cypress/e2e/agents-dual-auth.cy.js` - Agents domain
2. `cypress/e2e/properties-dual-auth.cy.js` - Properties domain
3. `cypress/e2e/assignments-dual-auth.cy.js` - Assignments domain
4. `cypress/e2e/commissions-dual-auth.cy.js` - Commissions domain
5. `cypress/e2e/performance-dual-auth.cy.js` - Performance domain

**Deliverables**:
- ✅ 5 E2E tests (one per domain)
- ✅ All tests passing
- ✅ Fingerprint validation tested

---

### Phase 4: Validation & Cleanup (Day 2 Afternoon - 1.5 hours)

**Goal**: Verify everything works and clean up

**Tasks**:

1. **Run All Tests** (30 min):
   - Cypress E2E tests: `npx cypress run`
   - Integration tests: `odoo --test-enable`
   - Manual Postman testing: All collections

2. **Code Review** (30 min):
   - Verify no debug logs: `grep -r "SESSION DEBUG"`
   - Verify session validation: Check middleware.py changes
   - Review E2E tests for consistency
   - Review Postman collection completeness

3. **Git Operations** (15 min):
   - Commit middleware changes: `feat: remove debug logs and add session_id validation`
   - Commit Postman collection: `docs: create complete Postman API collection`
   - Commit E2E tests: `test: add E2E validation tests for dual auth`
   - Commit documentation: `docs: add authentication and troubleshooting guides`
   - Push to GitHub: `git push origin 002-dual-auth-remaining-endpoints`

4. **Update Status** (15 min):
   - Update IMPLEMENTATION_STATUS.md
   - Update README.md (if needed)
   - Mark spec as complete

**Deliverables**:
- ✅ All tests passing
- ✅ Code reviewed
- ✅ Commits pushed
- ✅ Documentation updated

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Postman collection takes longer than 6-8 hours | Medium | Start with minimal working collection (auth + 1 domain), iterate |
| Existing decorators have subtle bugs discovered | High | Thorough E2E testing before marking complete, fix bugs as separate commits |
| User-Agent docs insufficient | Low | Include troubleshooting examples and clear error messages |
| Debug log removal breaks something | Very Low | Test middleware immediately after removal, rollback if needed |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 0: Quick Wins | 1 hour | None |
| 1: Postman Collection | 6-8 hours | Phase 0 complete |
| 2: Documentation | 3 hours | Phase 1 complete |
| 3: E2E Tests | 2.5 hours | Phase 1 complete (need working collection for reference) |
| 4: Validation | 1.5 hours | All phases complete |
| **Total** | **14-16 hours** | **~2 days** |

---

## Success Criteria

**Code Quality**:
- ✅ Zero debug logs in middleware.py
- ✅ Session_id length validation working (60-100 chars)
- ✅ All existing decorators validated

**Documentation**:
- ✅ Postman collection complete with ~50+ endpoints
- ✅ All endpoint descriptions include auth requirements
- ✅ API authentication guide created
- ✅ Troubleshooting guide created

**Testing**:
- ✅ 5 E2E tests passing (one per domain)
- ✅ All tests use .env credentials
- ✅ Fingerprint validation tested

**Usability**:
- ✅ Postman collection works end-to-end (login → request → success)
- ✅ Session_id captured from body (NOT cookie)
- ✅ Clear error messages for all failure modes

---

## Next Steps After This Spec

1. **Swagger/OpenAPI Documentation** - Generate from code annotations (separate spec)
2. **HATEOAS Implementation** - Add hypermedia links to responses (see TECHNICAL_DEBIT.md)
3. **Rate Limiting** - If needed based on production usage (separate spec)
4. **Performance Optimization** - If session validation overhead becomes issue

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
