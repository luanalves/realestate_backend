# Spec: Dual Authentication for Remaining API Endpoints

**Feature ID**: 002-dual-auth-remaining-endpoints  
**Created**: 2026-01-17  
**Status**: Complete  
**Completed**: 2026-01-17  
**Priority**: High (Security)

## Overview

Apply dual authentication (Bearer Token + Session validation) to all remaining API endpoints following the security model established in spec 001 and ADR-011. This ensures consistent security across the entire API surface.

## Background

### Current State
- **User Authentication endpoints**: Already protected with dual auth (spec 001) ✅
- **OAuth/Authentication endpoints**: Token generation - no session required ✅
- **Master Data endpoints**: Bearer token only (read-only, no user context) ✅
- **Business endpoints**: Currently inconsistent protection ❌

### Problem
The following domains lack consistent dual authentication:
- **Agents** (~7 endpoints) - Agent CRUD and management
- **Properties** (~4 endpoints) - Property CRUD
- **Assignments** (~3 endpoints) - Agent-Property assignments  
- **Commissions** (~4 endpoints) - Commission calculations
- **Performance** (~2 endpoints) - Agent performance metrics

**Security Risks**:
1. Endpoints accessible without proper session validation
2. No session hijacking prevention (missing fingerprint check)
3. Inconsistent security model across API
4. Violates ADR-011 controller security requirements

## User Needs

### Primary Users
- **API Consumers**: Mobile/web applications integrating with the real estate API
- **Real Estate Agents**: Accessing their data through the API
- **System Administrators**: Managing security and access control

### User Stories

**As an API consumer**, I need all endpoints to require valid authentication so that unauthorized access is prevented.

**As a real estate agent**, I need my session to be validated on every request so that my data cannot be accessed if my session is stolen.

**As a system administrator**, I need consistent security across all endpoints so that the API surface is uniformly protected.

## What We're Building

### In Scope

**Note**: Research revealed all 23 business endpoints already have `@require_jwt` + `@require_session` decorators applied. This spec now focuses on validation, quality improvements, and comprehensive documentation.

**1. Validate Existing Dual Authentication**

Verify decorators are correctly applied to:

**Agents Domain** (11 endpoints - all already protected ✅):
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents/{id}` - Get agent details
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent
- `GET /api/v1/agents` - List agents
- `GET /api/v1/agents/{id}/properties` - Agent's properties
- `GET /api/v1/agents/{id}/performance` - Agent performance

**Properties Domain** (4 endpoints):
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get property
- `PUT /api/v1/properties/{id}` - Update property
- `DELETE /api/v1/properties/{id}` - Delete property

**Assignments Domain** (3 endpoints):
- `POST /api/v1/assignments` - Assign agent to property
- `GET /api/v1/assignments/{id}` - Get assignment
- `DELETE /api/v1/assignments/{id}` - Remove assignment

**Commissions Domain** (4 endpoints):
- `POST /api/v1/commissions/calculate` - Calculate commission
- `GET /api/v1/commissions/{id}` - Get commission
- `GET /api/v1/commissions` - List commissions
- `PUT /api/v1/commissions/{id}` - Update commission

**Performance Domain** (2 endpoints):
- `GET /api/v1/performance/agents/{id}` - Agent metrics
- `GET /api/v1/performance/overview` - Overview metrics

**Total**: 23 business endpoints (11 Agents + 4 Properties + 2 Assignments + 4 Commissions + 2 Performance)

**2. Update Postman Collection**

**Scope**: Create complete Postman collection from scratch documenting all system endpoints (not just the 23 in-scope endpoints). This provides comprehensive API documentation and testing capability.

**Critical fixes** based on lessons learned from spec 001:
- Add `session_id` to request body params for all endpoints
- Fix test scripts to capture session_id from `jsonData.result.session_id` (NOT cookies)
- Document dual auth requirement in endpoint descriptions
- Update all endpoint examples with proper session_id usage

**3. Code Quality Improvements**

From chat history:
- Remove `[SESSION DEBUG]` log statements from middleware
- Validate session_id length (~80 characters)
- Document User-Agent consistency requirement
- Ensure all error responses return plain dict (not HTTP Response objects)

**4. Testing**

- Use credentials from `.env` file for test users
- Minimum 3 tests per endpoint:
  - Request without bearer token → 401
  - Request without session_id → 401  
  - Request with invalid/expired session → 401
  - Request with valid auth → 200/201
- E2E tests per domain covering complete flow

### Out of Scope

**Explicitly excluded** (already handled or not needed):
- ❌ User Authentication endpoints (completed in spec 001)
- ❌ OAuth/Authentication endpoints (token generation - no session needed)
- ❌ Master Data endpoints (read-only, bearer token only sufficient)
- ❌ Swagger documentation (separate task)
- ❌ HATEOAS implementation (separate task in TECHNICAL_DEBIT.md)
- ❌ Rate limiting per session_id (defer to future spec if needed)

## User Scenarios & Testing

### Scenario 1: Agent Management with Valid Session
**Given**: User has valid bearer token and active session  
**When**: User calls `POST /api/v1/agents` with session_id in body  
**Then**: Agent is created and response includes HATEOAS links  
**Success Criteria**: Response is 201 with agent data

### Scenario 2: Session Hijacking Prevention
**Given**: Attacker steals session_id from legitimate user  
**When**: Attacker makes request from different User-Agent/IP  
**Then**: Request is blocked due to fingerprint mismatch  
**Success Criteria**: Response is 401 "Session validation failed"

### Scenario 3: Postman Collection Usage
**Given**: Developer imports updated Postman collection  
**When**: Developer runs "User Login" then any protected endpoint  
**Then**: Session_id is automatically populated from login response (NOT cookie)  
**Success Criteria**: All subsequent requests succeed with correct session_id

### Scenario 4: Missing Authentication
**Given**: User has no bearer token or session  
**When**: User calls any protected endpoint  
**Then**: Clear error message indicates missing authentication  
**Success Criteria**: Response is 401 with specific error (bearer or session)

## Functional Requirements

### FR1: Decorator Application
**Must** apply decorators in this exact order to all in-scope endpoints:
```python
@http.route('/api/v1/endpoint', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def endpoint_function(self, **kwargs):
    # Implementation
```

### FR2: Session ID Extraction
**Must** accept session_id from multiple sources with priority:
1. Function kwargs: `kwargs.get('session_id')` (highest priority)
2. Request body: `request.get_json_data().get('session_id')`
3. Headers/Cookies: fallback only (lowest priority)

### FR3: Fingerprint Validation
**Must** validate JWT fingerprint includes:
- IP address (must match)
- User-Agent (must match)
- Accept-Language (must match)

**Must** reject requests with fingerprint mismatch and log attempt.

### FR4: Error Response Format
**Must** return plain dict for JSON-RPC compatibility:
```json
{
  "error": {
    "status": 401,
    "message": "Session required"
  }
}
```

**Must not** return HTTP Response objects (causes double-wrapping).

### FR5: Postman Collection Updates
**Must** update all in-scope endpoints in `QuicksolAPI_Complete.postman_collection.json`:

**Request body format**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "{{session_id}}",
    // ... other parameters
  }
}
```

**Test script** (correct way):
```javascript
if (pm.response.code === 200) {
    const jsonData = pm.response.json();
    if (jsonData.result && jsonData.result.session_id) {
        pm.environment.set('session_id', jsonData.result.session_id);
        console.log('✅ Session ID saved: ' + jsonData.result.session_id);
    }
}
```

**Must NOT** capture from cookies (lesson learned from spec 001).

### FR6: Code Quality
**Must** remove all debug logging:
- Remove `[SESSION DEBUG]` statements from middleware.py
- Keep security warnings (HIJACKING DETECTED, Invalid session)

**Must** validate session_id format:
- Expected length: ~80 characters (typical from Odoo session generation)
- Acceptable range: 60-100 characters (allows for implementation variations)
- Validation: Reject session_id outside 60-100 char range with 401 error
- Format: Alphanumeric string (no specific regex - Odoo generates the format)
- Note: No additional format validation beyond length (Odoo session IDs are opaque tokens)

### FR7: Documentation
**Must** document in endpoint descriptions:
- Requires bearer token: Yes
- Requires session: Yes (except Master Data)
- Requires company context: Yes
- Session validation includes fingerprint check
- User-Agent must remain consistent for session duration

**Documentation Locations**:
1. **Middleware**: Add User-Agent requirement note in `@require_session` decorator docstring (18.0/extra-addons/thedevkitchen_apigateway/middleware.py)
2. **Controllers**: Update all endpoint docstrings in agent_api.py, property_api.py with fingerprint validation notes
3. **Postman**: Add User-Agent consistency warning to all dual auth endpoint descriptions
4. **API Guide**: Document in docs/api-authentication.md (created in Phase 2)

### FR8: Testing Requirements
**Must** create tests using credentials from `.env`:
- Integration tests: 3 per endpoint minimum
- E2E tests: 1 per domain (5 total)
- All tests must use environment variables for credentials

## Success Criteria

**Security**:
- ✅ All 20 endpoints protected with dual authentication
- ✅ Fingerprint validation active on all endpoints
- ✅ No endpoints accessible without valid bearer token + session
- ✅ Session hijacking attempts blocked and logged

**Postman Collection**:
- ✅ All endpoints include session_id in request body
- ✅ Test scripts capture session_id from body (not cookies)
- ✅ Collection documentation updated with security requirements
- ✅ All example requests work with {{session_id}} variable

**Code Quality**:
- ✅ No debug logs in production code
- ✅ Session_id validation prevents malformed IDs
- ✅ Error responses follow consistent format
- ✅ User-Agent consistency documented

**Testing**:
- ✅ 5 E2E tests (1 per domain) covering dual auth validation
- ✅ All tests pass using .env credentials
- ✅ Test coverage ≥ 80% for modified/validated files (middleware.py, controllers)
- ✅ Session_id extraction priority tested (kwargs → body → headers)

**Performance**:
- ✅ No measurable performance degradation
- ✅ Session validation completes in < 50ms
- ✅ Fingerprint check completes in < 20ms

## Assumptions

1. **Session storage**: Redis is already configured and working
2. **JWT secret**: Available in config (database_secret or admin_passwd)
3. **User-Agent stability**: Clients maintain consistent User-Agent per session
4. **.env file**: Contains valid test user credentials
5. **Middleware**: `@require_jwt` and `@require_session` decorators are working (from spec 001)
6. **Database**: `thedevkitchen_api_session` table exists and is indexed

## Dependencies

### Internal
- Spec 001 (bearer token validation for User Authentication) - **Completed**
- ADR-011 (Controller Security) - **Approved**
- `middleware.py` decorators - **Available**
- Redis session storage - **Configured**

### External
- None

## Constraints

### Technical
- Must maintain JSON-RPC compatibility
- Must not break existing Master Data endpoints (bearer only)
- Session validation adds ~50ms latency (acceptable)
- User-Agent must match for session duration

### Business
- Must complete before external API launch
- High priority (security requirement)
- No budget for new infrastructure

### Regulatory
- Must comply with ADR-011 security requirements
- Session data must be encrypted in transit (HTTPS)
- Audit logging required for security events

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Postman collection breaks existing workflows | High | Medium | Test collection thoroughly, provide migration guide |
| User-Agent mismatch blocks legitimate users | Medium | Low | Document requirement, provide clear error messages |
| Performance degradation | Medium | Low | Monitor response times, optimize fingerprint validation |
| Debug logs accidentally left in code | Low | Medium | Code review checklist, automated grep check |
| Test credentials in .env missing/invalid | High | Low | Validate .env file in CI, document required format |

## Clarifications

### Session 2026-01-17

- Q: O arquivo Postman collection está vazio (0 bytes). Qual abordagem seguir? → A: Criar collection completa do zero documentando todos os endpoints do sistema
- Q: Todos os 23 endpoints já têm @require_jwt + @require_session. Como proceder? → A: Validar que decorators existentes estão corretos e focar em qualidade/documentação
- Q: Devemos adicionar rate limiting por session_id? → A: No rate limiting (estado atual) - implementar em spec futura dedicada se necessário

## Open Questions

None - all critical ambiguities have been clarified.

## Related Documents

- [Spec 001: Bearer Token Validation](../001-bearer-token-validation/spec.md) - Completed implementation
- [ADR-011: Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md)
- [PLANO-SECURITY-SESSION-HIJACKING.md](../../PLANO-SECURITY-SESSION-HIJACKING.md)
- [TECHNICAL_DEBIT.md](../../TECHNICAL_DEBIT.md)

## Appendix

### Lessons Learned from Spec 001

**Problems Encountered**:
1. ❌ Postman script overwrote session_id variable with cookie value
2. ❌ User-Agent mismatch blocked valid requests (fingerprint check)
3. ❌ Middleware returned HTTP Response objects causing double-wrapping
4. ❌ Session_id not read from kwargs (only headers/cookies)
5. ❌ Debug logs cluttered production output

**Solutions Applied**:
1. ✅ Capture session_id only from `jsonData.result.session_id`
2. ✅ Document User-Agent consistency requirement
3. ✅ Return plain dict for `type='json'` routes
4. ✅ Check `kwargs.get('session_id')` first
5. ✅ Remove debug logs before merge

### Example Endpoint Implementation

```python
@http.route('/api/v1/agents', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def create_agent(self, name, email, phone, creci, **kwargs):
    """
    Create new agent
    
    Security: Requires bearer token + session (ADR-011)
    Session validation includes fingerprint check
    """
    try:
        company = request.env.company
        agent = request.env['real.estate.agent'].create({
            'name': name,
            'email': email,
            'phone': phone,
            'creci': creci,
            'company_id': company.id
        })
        
        return {
            'id': agent.id,
            'name': agent.name,
            'email': agent.email,
            '_links': {
                'self': {'href': f'/api/v1/agents/{agent.id}'},
                'properties': {'href': f'/api/v1/agents/{agent.id}/properties'}
            }
        }
    except Exception as e:
        _logger.error(f'Error creating agent: {e}')
        return {'error': {'status': 500, 'message': 'Internal server error'}}
```

### Postman Request Example

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "{{session_id}}",
    "name": "João Silva",
    "email": "joao@realestate.com",
    "phone": "(11) 99999-9999",
    "creci": "12345-SP"
  }
}
```

### Test Credentials from .env

```bash
# .env file structure expected
TEST_USER_EMAIL=joao@imobiliaria.com
TEST_USER_PASSWORD=test123
TEST_ADMIN_EMAIL=admin
TEST_ADMIN_PASSWORD=admin
OAUTH_CLIENT_ID=client_XXX
OAUTH_CLIENT_SECRET=secret_XXX
```
