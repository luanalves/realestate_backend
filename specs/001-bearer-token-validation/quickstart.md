# Quickstart Guide: Bearer Token Validation Testing

**Feature**: Bearer Token Validation for User Authentication Endpoints  
**Audience**: Developers and QA Engineers  
**Date**: January 15, 2026

## Overview

This guide provides step-by-step instructions for testing bearer token and session validation on User Authentication endpoints after implementation.

## Prerequisites

- Odoo 18.0 development environment running (Docker container)
- PostgreSQL with `realestate` database
- Redis cache running on port 6379
- OAuth application registered in system
- Test user credentials
- HTTP client (curl, Postman, or HTTPie)

## Quick Test Scenarios

### Scenario 1: Obtain OAuth Bearer Token

**Purpose**: Get a valid bearer token for API authentication

```bash
curl -X POST http://localhost:8069/oauth2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'username=admin' \
  -d 'password=admin' \
  -d 'client_id=<your_client_id>' \
  -d 'client_secret=<your_client_secret>'
```

**Expected Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "refresh_token": "def502..."
}
```

**Store** the `access_token` value for subsequent requests.

---

### Scenario 2: Login with Bearer Token (Creates Session)

**Purpose**: Authenticate user and obtain session cookie

```bash
curl -X POST http://localhost:8069/api/v1/users/login \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{
    "email": "admin",
    "password": "admin"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "session_id": "abc123def456...",
  "user": {
    "id": 2,
    "name": "Admin",
    "email": "admin@example.com",
    "login": "admin"
  }
}
```

**Note**: Session cookie automatically saved to `cookies.txt` for subsequent requests.

---

### Scenario 3: Access Protected Endpoint with Token + Session ✅

**Purpose**: Verify successful access with both bearer token and session

```bash
curl -X PATCH http://localhost:8069/api/v1/users/profile \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{
    "name": "Updated Name"
  }'
```

**Expected Response**: `200 OK`
```json
{
  "success": true,
  "user": {
    "id": 2,
    "name": "Updated Name",
    ...
  }
}
```

---

### Scenario 4: Missing Bearer Token ❌

**Purpose**: Verify rejection when bearer token is missing

```bash
curl -X PATCH http://localhost:8069/api/v1/users/profile \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"name": "Test"}'
```

**Expected Response**: `401 Unauthorized`
```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authorization header is required"
  }
}
```

---

### Scenario 5: Missing Session Cookie ❌

**Purpose**: Verify rejection when session is missing

```bash
curl -X PATCH http://localhost:8069/api/v1/users/profile \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test"}'
```

**Expected Response**: `401 Unauthorized`
```json
{
  "error": "unauthorized",
  "message": "Session required",
  "code": 401
}
```

OR

```json
{
  "error": {
    "status": 401,
    "message": "Session validation failed"
  }
}
```

---

### Scenario 6: Expired Bearer Token ❌

**Purpose**: Verify rejection when token is expired

1. Wait for token expiration (or manually revoke token in database)
2. Attempt to access endpoint:

```bash
curl -X POST http://localhost:8069/api/v1/users/logout \
  -H 'Authorization: Bearer <expired_token>' \
  -H 'Content-Type: application/json' \
  -b cookies.txt
```

**Expected Response**: `401 Unauthorized`
```json
{
  "error": {
    "code": "token_expired",
    "message": "Token has expired"
  }
}
```

---

### Scenario 7: Session Hijacking Detection (Fingerprint Mismatch) ❌

**Purpose**: Verify session validation prevents hijacking

**Setup**: Obtain session from one IP/User-Agent, then replay from different context.

```bash
# Original request creates session
curl -X POST http://localhost:8069/api/v1/users/login \
  -H 'Authorization: Bearer <access_token>' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh)' \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{"email": "admin", "password": "admin"}'

# Replay with different User-Agent
curl -X PATCH http://localhost:8069/api/v1/users/profile \
  -H 'Authorization: Bearer <access_token>' \
  -H 'User-Agent: curl/7.64.1' \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"name": "Test"}'
```

**Expected Response**: `401 Unauthorized`
```json
{
  "error": {
    "status": 401,
    "message": "Session validation failed"
  }
}
```

**Note**: Check logs for `[SESSION HIJACKING DETECTED - USER-AGENT MISMATCH]` message.

---

## Running Automated Tests

### Integration Tests (pytest)

```bash
# Navigate to module directory
cd 18.0/extra-addons/thedevkitchen_apigateway

# Run all user auth controller tests
docker compose exec odoo python -m pytest tests/test_user_auth_controller.py -v

# Run specific test
docker compose exec odoo python -m pytest tests/test_user_auth_controller.py::TestUserAuthController::test_logout_requires_session -v

# Run with coverage
docker compose exec odoo python -m pytest tests/test_user_auth_controller.py --cov=controllers/user_auth_controller --cov-report=term-missing
```

**Expected**: All tests pass with >80% coverage

---

### E2E Tests (Cypress)

```bash
# From repository root
cd 18.0

# Open Cypress UI
npm run cypress:open

# Run specific spec
npx cypress run --spec cypress/e2e/user-authentication-session.cy.js

# Run all E2E tests
npm run cypress:run
```

**Expected**: Complete authentication flow passes including session validation failures

---

## Debugging Tips

### Check Bearer Token in Database

```sql
-- Connect to PostgreSQL
docker compose exec db psql -U odoo -d realestate

-- View tokens
SELECT 
  access_token,
  token_type,
  expires_at,
  revoked,
  user_id,
  application_id
FROM thedevkitchen_oauth_token
WHERE access_token = '<your_token>'
LIMIT 1;
```

### Check Session in Redis

```bash
# Connect to Redis
docker compose exec redis redis-cli

# Switch to DB 1 (Odoo sessions)
SELECT 1

# List all sessions
KEYS session:*

# View specific session
GET session:<session_id>

# Check session TTL
TTL session:<session_id>
```

### View Security Logs

```bash
# Real-time log monitoring
docker compose logs -f odoo | grep -E 'SESSION|JWT|AUTH'

# Filter session hijacking attempts
docker compose logs odoo | grep 'SESSION HIJACKING DETECTED'

# View audit logs in database
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT * FROM auditlog_log WHERE model_model = 'res.users' ORDER BY create_date DESC LIMIT 10;"
```

---

## Common Issues and Solutions

### Issue: "Authorization header is required"
**Cause**: Bearer token not included in request  
**Solution**: Add `Authorization: Bearer <token>` header to all requests

### Issue: "Session required"
**Cause**: Session cookie not sent with request  
**Solution**: Ensure cookies are enabled and session cookie is included (`-b cookies.txt` in curl)

### Issue: "Session validation failed"
**Cause**: Fingerprint mismatch (IP/User-Agent/Language changed)  
**Solution**: Use consistent IP and User-Agent for all requests in a session

### Issue: "Token has expired"
**Cause**: Bearer token exceeded `expires_at` timestamp  
**Solution**: Request new token via `/oauth2/token` endpoint or use refresh token

### Issue: Tests fail with "No module named 'pytest'"
**Cause**: pytest not installed in container  
**Solution**: `docker compose exec odoo pip install pytest pytest-cov`

---

## Security Checklist

Before deploying to production:

- [ ] All User Authentication endpoints except login have both `@require_jwt` and `@require_session`
- [ ] Login endpoint has only `@require_jwt` (no session required)
- [ ] All endpoints return appropriate 401 errors for missing/invalid credentials
- [ ] Session hijacking detection logs security events
- [ ] Integration tests cover all success and failure scenarios
- [ ] E2E test validates complete authentication flow
- [ ] OpenAPI documentation updated with security requirements
- [ ] Code review confirms ADR-011 compliance
- [ ] Test coverage ≥80% for modified controllers

---

## Next Steps

1. Review [data-model.md](./data-model.md) for entity relationships
2. Review [contracts/user-auth-endpoints.openapi.yaml](./contracts/user-auth-endpoints.openapi.yaml) for API specifications
3. Implement changes following [tasks.md](./tasks.md) (generated via `/speckit.tasks`)
4. Run full test suite before submitting PR
5. Update Swagger UI documentation at http://localhost:8069/api/docs

## References

- [ADR-011: Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md)
- [ADR-003: Mandatory Test Coverage](../../docs/adr/ADR-003-mandatory-test-coverage.md)
- [ADR-002: Cypress E2E Testing](../../docs/adr/ADR-002-cypress-end-to-end-testing.md)
