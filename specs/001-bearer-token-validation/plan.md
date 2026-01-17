# Implementation Plan: Bearer Token Validation for User Authentication Endpoints

**Branch**: `001-bearer-token-validation` | **Date**: January 15, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-bearer-token-validation/spec.md`

## Summary

This feature implements comprehensive bearer token and session validation for all User Authentication endpoints in the `thedevkitchen_apigateway` module. The primary requirement is to enforce dual authentication (OAuth 2.0 JWT bearer token + HTTP session) on endpoints that manage user operations. The system has 5 endpoints total: login (token only), me, profile, change-password, and logout (all requiring token + session).

**Technical Approach**: Verify and ensure all User Authentication endpoints except login have both `@require_jwt` and `@require_session` decorators, ensuring compliance with ADR-011 (Controller Security - Dual Authentication). Analysis shows only logout endpoint needs the session decorator added; the other endpoints (me, profile, change-password) are already compliant.

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0)  
**Primary Dependencies**: Odoo 18.0, PyJWT, Redis 7-alpine, PostgreSQL 16  
**Storage**: PostgreSQL (oauth.access_token table), Redis DB index 1 (HTTP sessions)  
**Testing**: pytest + Odoo test framework, Cypress for E2E  
**Target Platform**: Docker containerized environment (Linux)  
**Project Type**: Odoo web module (backend API)  
**Performance Goals**: <50ms bearer token validation, <20ms session validation (95th percentile)  
**Constraints**: Zero authentication bypass vulnerabilities, 80% minimum test coverage  
**Scale/Scope**: 5 endpoints total - 1 requires modification (logout), 3 already compliant (me, profile, change-password), 1 unchanged (login)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Security First ✅ PASS
- **Requirement**: All endpoints MUST use `@require_jwt` + `@require_session` + `@require_company`
- **Current State**: Login endpoint has `@require_jwt` only (correct); me, profile, and change-password already have both decorators; logout has only `@require_jwt`
- **This Feature**: Adds `@require_session` to logout endpoint only (other endpoints already compliant)
- **Compliance**: Full compliance after implementation. Login endpoint correctly exempted per constitution (no pre-existing session needed for authentication entry point)

### Principle II: Test Coverage Mandatory ✅ PASS
- **Requirement**: Minimum 80% test coverage with unit + integration + E2E tests
- **Plan**: 
  - Integration tests for logout endpoint (401 without session, 401 with expired session, 200 with valid credentials+session, 401 with fingerprint mismatch)
  - Verify existing tests cover me, profile, and change-password endpoints
  - E2E Cypress test for complete authentication flow with session validation across all endpoints
- **Coverage Target**: 100% of modified endpoint (logout: 6 test scenarios minimum) + verification of existing endpoint coverage

### Principle III: API-First Design ✅ PASS
- **Requirement**: OpenAPI 3.0 documentation, HATEOAS, consistent error responses
- **Plan**: Update OpenAPI schema to document session requirement and error responses (401 "Session required", 401 "Session expired")
- **Error Format**: Already standardized as `{"error": {"status": int, "message": string}}`

### Principle IV: Multi-Tenancy by Design ✅ PASS
- **Requirement**: Company isolation via `@require_company`
- **Current State**: Existing endpoints already implement company isolation
- **This Feature**: No changes to multi-tenancy logic; session validation reinforces user context isolation

### Principle V: ADR Governance ✅ PASS
- **Relevant ADRs**:
  - ADR-011: Controller Security - Dual Authentication (JWT + Session) - **PRIMARY COMPLIANCE TARGET**
  - ADR-009: Headless Authentication and User Context
  - ADR-003: Mandatory Test Coverage
  - ADR-002: Cypress E2E Testing
- **Compliance**: Feature directly implements ADR-011 requirements for dual authentication

### Principle VI: Headless Architecture ✅ PASS
- **Requirement**: SSR frontend consumes REST APIs with OAuth 2.0
- **Alignment**: Session validation enables secure SSR-to-backend API calls with proper user context tracking
- **No Changes**: Existing API contracts maintained; only security enforcement enhanced

**GATE STATUS**: ✅ **PASSED** - No constitution violations. Feature aligns with all principles and implements ADR-011 requirements.

**POST-DESIGN RE-CHECK**: ✅ **CONFIRMED PASS**
- Phase 0 research confirms all required infrastructure exists (no new dependencies)
- Phase 1 design shows zero data model changes (pure configuration)
- Contract definitions align with existing error response patterns
- Test strategy meets 80% coverage requirement with integration + E2E tests
- Implementation requires only decorator additions to existing endpoints
- No architectural complexity added - leverages existing authentication infrastructure

## Project Structure

### Documentation (this feature)

```text
specs/001-bearer-token-validation/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (already exists)
├── research.md          # Phase 0 output (decorator behavior analysis)
├── data-model.md        # Phase 1 output (N/A - no new data models)
├── quickstart.md        # Phase 1 output (testing guide)
├── contracts/           # Phase 1 output (OpenAPI updates)
│   └── user-auth-endpoints.openapi.yaml
├── checklists/          # Quality validation (already exists)
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
18.0/extra-addons/thedevkitchen_apigateway/
├── controllers/
│   ├── user_auth_controller.py          # MODIFIED: Add @require_session to logout endpoint
│   │                                     # VERIFIED: login (jwt only), profile, change-password (jwt+session)
│   └── me_controller.py                 # VERIFIED: Already has @require_jwt + @require_session
├── middleware.py                          # EXISTING: Contains @require_jwt and @require_session decorators
├── services/
│   ├── audit_logger.py                   # EXISTING: Security event logging
│   └── session_validator.py             # EXISTING: Session validation logic
├── tests/
│   ├── test_user_auth_controller.py     # MODIFIED: Add session validation tests for logout
│   └── test_me_controller.py            # VERIFIED: Verify existing session validation tests
└── static/
    └── description/
        └── openapi/
            └── user_auth.yaml            # MODIFIED: Update OpenAPI schema for all 5 endpoints

cypress/
└── e2e/
    └── user-authentication-session.cy.js # NEW: E2E test covering all 5 endpoints

postman/
└── QuicksolAPI_Complete.postman_collection.json # MODIFIED: Recreate with session examples
```

**Structure Decision**: This is a security enhancement to an existing Odoo module (`thedevkitchen_apigateway`). No new modules or files required - only modifications to existing controller decorators, test additions, and OpenAPI documentation updates. The Odoo monolithic structure is used as per project standards (ADR-001, ADR-004).

## Complexity Tracking

> **No violations - this section intentionally left empty**

This feature has zero constitution violations. All requirements align with existing architectural principles and ADRs. No complexity justification needed.

---

## Phase 2: Implementation Approach (Preview)

**Note**: Detailed task breakdown will be generated via `/speckit.tasks` command. This section provides high-level implementation guidance.

### Implementation Strategy

**Approach**: Incremental decorator addition with test-first methodology

**Order of Operations**:
1. Verify existing decorators on all 5 endpoints (login, me, profile, change-password, logout)
2. Add integration tests for logout endpoint (TDD approach)
3. Apply `@require_session` decorator to `/api/v1/users/logout`
4. Validate tests pass for logout
5. Verify existing tests pass for me, profile, and change-password endpoints
6. Add E2E Cypress test for complete flow covering all 5 endpoints
7. Update OpenAPI documentation for all endpoints
8. Update Postman collection with session validation examples
9. Code review and PR submission

### Files to Modify

**Primary Changes**:
- `18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py` (1 decorator addition to logout endpoint)
- `18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py` (verification only - already compliant)

**Test Changes**:
- `18.0/extra-addons/thedevkitchen_apigateway/tests/test_user_auth_controller.py` (add 6 test cases for logout endpoint)
- Verify existing tests for me, profile, and change-password endpoints
- `cypress/e2e/user-authentication-session.cy.js` (new file, E2E test covering all 5 endpoints)

**Documentation Changes**:
- `18.0/extra-addons/thedevkitchen_apigateway/static/description/openapi/user_auth.yaml` (update security requirements for all 5 endpoints)
- `postman/QuicksolAPI_Complete.postman_collection.json` (recreate with session validation examples for all endpoints)

### Risk Mitigation

**Risk**: Breaking existing clients that don't send session cookies  
**Mitigation**: Login endpoint remains unchanged (session creation point); other endpoints already require authentication, so adding session is an additional layer, not a breaking change

**Risk**: Session validation performance impact  
**Mitigation**: Redis cache hit is <20ms; decorator already in production on other endpoints

**Risk**: Test coverage drops below 80%  
**Mitigation**: Add tests BEFORE applying decorators (TDD); run coverage report before PR

### Acceptance Criteria Checklist

Implementation complete when:
- [ ] Logout endpoint has both `@require_jwt` and `@require_session` decorators
- [ ] Login endpoint unchanged (only `@require_jwt`)
- [ ] Me, profile, and change-password endpoints verified as compliant (already have both decorators)
- [ ] 6 integration tests pass for logout endpoint
- [ ] Existing tests verified for me, profile, and change-password endpoints
- [ ] 1 E2E Cypress test passes covering all 5 endpoints
- [ ] Test coverage ≥80% for `user_auth_controller.py` and `me_controller.py`
- [ ] OpenAPI documentation updated for all 5 endpoints
- [ ] Postman collection recreated with session validation examples
- [ ] Manual curl testing confirms all scenarios work
- [ ] Code review approved by CODEOWNERS
- [ ] ADR-011 compliance verified

---

## Artifacts Generated

### Phase 0: Research ✅
- [research.md](./research.md) - Decorator behavior analysis, technology recommendations, decisions

### Phase 1: Design ✅
- [data-model.md](./data-model.md) - Entity relationships (none required - existing models only)
- [contracts/user-auth-endpoints.openapi.yaml](./contracts/user-auth-endpoints.openapi.yaml) - API specifications
- [quickstart.md](./quickstart.md) - Testing guide for developers

### Phase 2: Tasks (Next Step)
- `tasks.md` - **To be generated via `/speckit.tasks` command**
- Detailed task breakdown with acceptance criteria
- Implementation checklist
- Testing procedures

---

## Next Steps

1. **Review this plan** with team for approval
2. **Run `/speckit.tasks`** to generate detailed implementation tasks
3. **Begin implementation** following TDD approach from tasks.md
4. **Submit PR** with all tests passing and documentation updated

## Summary

This is a **low-complexity, high-impact security enhancement** that:
- ✅ Requires zero new infrastructure
- ✅ Leverages existing decorators and authentication system
- ✅ Implements ADR-011 dual authentication requirements
- ✅ Adds comprehensive security without breaking changes
- ✅ Maintains 80%+ test coverage mandate
- ✅ Completes in 1 day of focused development
- ✅ **Most endpoints already compliant** (3 of 4 protected endpoints already correct)

**Estimated Effort**: 4-8 developer hours (including testing and documentation)

**Note**: Reduced effort due to discovery that 3 of 4 protected endpoints (me, profile, change-password) are already correctly implemented with both decorators. Only logout endpoint requires modification.

**Impact**: Significantly improves API security by preventing unauthorized access to user management operations and enabling robust session tracking for audit and multi-tenancy compliance.

**Endpoints Summary** (5 total):
1. `/api/v1/users/login` - ✅ Correct (JWT only - creates session)
2. `/api/v1/me` - ✅ Already compliant (JWT + Session)
3. `/api/v1/users/profile` - ✅ Already compliant (JWT + Session)
4. `/api/v1/users/change-password` - ✅ Already compliant (JWT + Session)
5. `/api/v1/users/logout` - ❌ **Needs fix** (has JWT, missing Session)
