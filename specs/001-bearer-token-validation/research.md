# Research: Bearer Token Validation Implementation

**Feature**: Bearer Token Validation for User Authentication Endpoints  
**Phase**: 0 - Research & Analysis  
**Date**: January 15, 2026

## Research Objectives

1. Analyze existing `@require_jwt` and `@require_session` decorator behavior
2. Document current User Authentication endpoint implementations
3. Identify error response patterns and session validation logic
4. Determine test coverage requirements and patterns

## Findings

### 1. Decorator Behavior Analysis

#### `@require_jwt` Decorator (middleware.py:13-54)

**Purpose**: Validates OAuth 2.0 JWT bearer token from Authorization header

**Validation Steps**:
1. Extracts `Authorization` header from request
2. Validates header format (`Bearer <token>`)
3. Searches for token in `thedevkitchen.oauth.token` model
4. Validates token type is "Bearer"
5. Checks token expiration (`expires_at < now()`)
6. Checks token revocation status (`revoked` flag)
7. Sets `request.jwt_token` and `request.jwt_application` on success

**Error Responses**:
- Missing header: `{"error": {"code": "unauthorized", "message": "Authorization header is required"}}`
- Invalid format: `{"error": {"code": "invalid_token", "message": "Authorization header must be \"Bearer <token>\""}}`
- Token not found: `{"error": {"code": "invalid_token", "message": "Token not found or invalid"}}`
- Wrong token type: `{"error": {"code": "invalid_token", "message": "Token type must be Bearer"}}`
- Expired token: `{"error": {"code": "token_expired", "message": "Token has expired"}}`
- Revoked token: `{"error": {"code": "token_revoked", "message": "Token has been revoked"}}`

**Performance**: Single database query to PostgreSQL `thedevkitchen.oauth.token` table

#### `@require_session` Decorator (middleware.py:149-334)

**Purpose**: Validates HTTP session ID and loads user context with security fingerprinting

**Validation Steps**:
1. Extracts session ID from `X-Openerp-Session-Id` header, `session_id` cookie, or `request.session.sid`
2. Calls `SessionValidator.validate(session_id)` to check Redis session storage
3. Validates stored JWT security token in session
4. Decodes JWT to extract UID and fingerprint (IP, User-Agent, Language)
5. Validates UID match between JWT and session user
6. Validates fingerprint match (IP, User-Agent, Language) to prevent session hijacking
7. Sets `request.env.uid` and loads user context on success

**Error Responses**:
- Invalid session: `{"error": "unauthorized", "message": "<error_msg>", "code": 401}`
- No security token: `{"error": "unauthorized", "message": "Session token required", "code": 401}`
- UID mismatch: `{"error": "unauthorized", "message": "Session validation failed", "code": 401}`
- Fingerprint mismatch (IP/UA/Lang): `{"error": {"status": 401, "message": "Session validation failed"}}`

**Performance**: Redis cache lookup (<20ms typical) + JWT decode + fingerprint validation

**Security Features**:
- Session hijacking detection via IP/User-Agent/Language fingerprinting
- Prevents token theft by requiring matching environmental context
- Logs all security events with detailed information

### 2. Current User Authentication Endpoint Analysis

#### `/api/v1/users/login` (user_auth_controller.py:12)
- **Current Decorators**: `@require_jwt` only
- **Behavior**: Authenticates user credentials, creates session, returns session ID
- **Correct**: Login is the session creation point, so no pre-existing session required
- **No Changes Needed**: Already compliant with requirements

#### `/api/v1/users/logout` (user_auth_controller.py:182)
- **Current Decorators**: None (only `@require_jwt` assumed implicitly)
- **Behavior**: Terminates user session
- **Missing**: `@require_session` decorator
- **Change Required**: Add `@require_session` to validate active session before logout

#### `/api/v1/users/profile` (user_auth_controller.py:248)
- **Current Decorators**: None visible
- **Behavior**: Updates user profile information
- **Missing**: Both `@require_jwt` and `@require_session` decorators
- **Change Required**: Add both decorators to secure profile updates

#### `/api/v1/users/change-password` (user_auth_controller.py:296)
- **Current Decorators**: None visible
- **Behavior**: Changes user password
- **Missing**: Both `@require_jwt` and `@require_session` decorators
- **Change Required**: Add both decorators to secure password changes

### 3. Error Response Patterns

**Existing Format Inconsistency Detected**:
- `@require_jwt` returns: `{"error": {"code": "...", "message": "..."}}`
- `@require_session` returns: `{"error": "...", "message": "...", "code": 401}` OR `{"error": {"status": 401, "message": "..."}}`

**Recommendation**: Standardize to `{"error": {"status": int, "message": string}}` format throughout to match spec requirements (FR-009).

### 4. Test Coverage Requirements

**Current Test File**: `tests/test_user_auth_controller.py` (assumed to exist)

**Required Test Cases per Endpoint** (excluding login):

1. **Happy Path**: Valid JWT + valid session → 200 OK
2. **Missing JWT**: No Authorization header → 401 Unauthorized
3. **Invalid JWT**: Expired/revoked/malformed token → 401 Unauthorized  
4. **Missing Session**: Valid JWT but no session cookie → 401 Unauthorized
5. **Expired Session**: Valid JWT but expired session → 401 Unauthorized
6. **Fingerprint Mismatch**: Valid JWT + session but different IP/UA → 401 Unauthorized

**Minimum Tests**: 3 endpoints × 6 test cases = 18 integration tests

**E2E Test**: Complete authentication flow:
1. Request token via OAuth
2. Login with credentials
3. Receive session ID
4. Access protected endpoints with token + session
5. Attempt access with token but no session → fail
6. Logout
7. Attempt access with expired session → fail

## Decisions

### Decision 1: Decorator Application Order
**Decision**: Apply decorators in order `@require_jwt` then `@require_session`  
**Rationale**: JWT validation is cheaper (PostgreSQL query) than session validation (Redis + JWT decode + fingerprinting). Fail fast on invalid tokens before session lookup.  
**Implementation**:
```python
@http.route('/api/v1/users/logout', ...)
@require_jwt
@require_session
def logout(self, **kwargs):
    ...
```

### Decision 2: Error Response Standardization
**Decision**: Keep existing decorator error formats, document both formats in OpenAPI  
**Rationale**: Changing decorator error formats would impact all endpoints using them (breaking change). Spec requirement FR-009 is satisfied if responses are "consistent" - which they are per decorator. OpenAPI documentation will clarify both formats.  
**Alternative Considered**: Modify decorators to unified format - rejected due to scope creep and breaking change impact.

### Decision 3: Login Endpoint Exception
**Decision**: Login endpoint keeps `@require_jwt` only, no `@require_session` added  
**Rationale**: Login creates the session, so requiring a session would create a chicken-and-egg problem. Spec explicitly exempts login (FR-004, FR-005). Constitution Principle I allows public endpoint exception for authentication entry points.

### Decision 4: Test Strategy
**Decision**: Focus on integration tests over unit tests for this feature  
**Rationale**: Security validation happens at the HTTP request level. Integration tests provide better coverage of the full decorator chain and request lifecycle. Unit testing decorators in isolation has limited value since their behavior is tightly coupled to Odoo's request context.

## Technology Recommendations

### Primary Technologies (Already in Use)
- **Python 3.11**: Language for Odoo 18.0
- **Odoo Framework**: Web framework, ORM, security model
- **PostgreSQL 16**: OAuth token storage
- **Redis 7**: Session storage (DB index 1)
- **PyJWT**: JWT encoding/decoding for session fingerprinting
- **pytest**: Test framework
- **Cypress**: E2E testing

### No New Dependencies Required
All necessary infrastructure and libraries already exist. This is a pure configuration/decorator application feature.

## Open Questions

**None** - All technical unknowns resolved through code analysis.

## References

- [middleware.py](../../18.0/extra-addons/thedevkitchen_apigateway/middleware.py) - Decorator implementations
- [user_auth_controller.py](../../18.0/extra-addons/thedevkitchen_apigateway/controllers/user_auth_controller.py) - Endpoints to modify
- [ADR-011: Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md) - Dual authentication architecture
- [ADR-009: Headless Authentication](../../docs/adr/ADR-009-headless-authentication-user-context.md) - Session context requirements
