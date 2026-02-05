# Feature 007 Shell Tests - Authentication Setup Required

## Status: BLOCKED

The Feature 007 shell integration tests are currently **BLOCKED** due to missing authentication API endpoints.

## Issue

All 5 shell test scripts (`test_us7_s*.sh`) attempt to authenticate using:

```bash
curl -X POST "${BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin@admin.com",
    "password": "admin",
    "db": "realestate"
  }'
```

**Problem**: This endpoint returns **404 Not Found** (HTML error page).

Also tried:
```bash
curl -X POST "${BASE_URL}/api/v1/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "username": "admin@admin.com",
    "password": "admin",
    "db": "realestate"
  }'
```

**Problem**: Also returns **404 Not Found**.

## Affected Tests

1. ❌ `test_us7_s1_owner_crud.sh` - Owner CRUD operations (9 scenarios)
2. ❌ `test_us7_s2_owner_company_link.sh` - Owner-Company linking (10 scenarios)
3. ❌ `test_us7_s3_company_crud.sh` - Company CRUD operations (12 scenarios)
4. ❌ `test_us7_s4_rbac.sh` - RBAC validation (9 scenarios)
5. ❌ `test_us7_s5_multitenancy.sh` - Multi-tenancy isolation (6 scenarios)

**Total: 46 shell test scenarios blocked**

## Alternative: Python Integration Tests

The Python integration tests in `18.0/extra-addons/quicksol_estate/tests/api/` use Odoo's built-in authentication and **do work**:

✅ **test_owner_api.py** - 14 test methods (including RBAC and no-company scenarios)  
✅ **test_company_api.py** - 16 test methods (including RBAC tests)

**Total: 30 Python test methods working**

## Solutions

### Option 1: Use Existing Odoo Web Authentication

Modify shell tests to use `/web/session/authenticate` pattern like existing US1 tests:

```bash
# Example from test_us1_s1_owner_login.sh
ADMIN_SESSION=$(curl -s -X POST "$BASE_URL/web/session/authenticate" \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"call\",
    \"params\": {
      \"db\": \"${DB_NAME}\",
      \"login\": \"${ADMIN_LOGIN}\",
      \"password\": \"${ADMIN_PASSWORD}\"
    }
  }")

SESSION_ID=$(echo "$ADMIN_SESSION" | jq -r '.result.session_id // empty')
```

Then use session cookies instead of Bearer tokens.

### Option 2: Implement Missing Auth API

Create the authentication endpoints expected by Feature 007 tests:

1. **POST /api/auth/login** - Login with username/password
   - Input: `{login, password, db}`
   - Output: `{access_token, token_type: "Bearer", expires_in}`

2. **POST /api/v1/oauth/token** - OAuth2 token endpoint
   - Grant types: `password`, `client_credentials`
   - Output: `{access_token, refresh_token, token_type, expires_in}`

### Option 3: Run Python Tests Only

Accept that shell tests are blocked and rely on Python integration tests:

```bash
cd 18.0
docker compose exec odoo python -m pytest \
  extra-addons/quicksol_estate/tests/api/test_owner_api.py \
  extra-addons/quicksol_estate/tests/api/test_company_api.py \
  -v
```

## Current Workaround

For testing the Feature 007 endpoints, use:

1. **Odoo Web UI** - Login at http://localhost:8069 and use Odoo's interface
2. **Python Tests** - Run pytest tests (authentication handled by Odoo TestCase)
3. **Postman/Insomnia** - Use session cookies from web login

## Recommendation

**Short-term**: Run Python integration tests to validate feature functionality.

**Medium-term**: Implement Option 2 (auth API endpoints) to enable shell tests. This would also benefit:
- Mobile app development
- Third-party integrations
- Automated testing in CI/CD
- API documentation examples

## Test Coverage Summary

| Test Type | Status | Count | Coverage |
|-----------|--------|-------|----------|
| Python Unit Tests | ✅ Working | 24 methods | Validation logic |
| Python Integration Tests | ✅ Working | 30 methods | API endpoints + RBAC |
| Shell Integration Tests | ❌ Blocked | 46 scenarios | End-to-end flows |
| **Total** | **Partial** | **100 scenarios** | **54% executable** |

---

**Updated**: February 5, 2026  
**Status**: Awaiting auth API implementation or shell test refactor
