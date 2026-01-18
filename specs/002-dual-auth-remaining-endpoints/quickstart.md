# Quickstart: Testing Dual Authentication

**Feature**: 002-dual-auth-remaining-endpoints  
**Estimated Time**: 15 minutes  
**Prerequisites**: Docker running, Odoo container started

---

## Quick Validation (5 minutes)

### 1. Verify Decorators Applied

```bash
# Check Agents endpoints
grep -A 2 "@http.route.*agents" 18.0/extra-addons/quicksol_estate/controllers/agent_api.py | grep "@require_session"

# Check Properties endpoints  
grep -A 2 "@http.route.*properties" 18.0/extra-addons/quicksol_estate/controllers/property_api.py | grep "@require_session"

# Expected: Multiple matches showing @require_session decorator
```

### 2. Check Debug Logs Removed

```bash
grep -n "SESSION DEBUG" 18.0/extra-addons/thedevkitchen_apigateway/middleware.py

# Expected: No matches (all 4 debug logs removed)
```

### 3. Verify Session Validation Working

```bash
# Access Odoo logs
docker compose -f 18.0/docker-compose.yml logs -f odoo | grep -i "session"

# Make a test request and watch for validation messages
```

---

## Full E2E Test (10 minutes)

### 1. Get OAuth Token

```bash
# Using credentials from .env
curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "grant_type": "client_credentials",
      "client_id": "client_EEQix5KVT6JsSUARsdUGnw",
      "client_secret": "Xu5l7zL9Je6HKcx6EbJJiLwy9JAA0QHozcDE37TGjjC5skPEWfkigZPouqTWzDBG"
    }
  }'

# Save the access_token from response
export TOKEN="<your_access_token>"
```

### 2. User Login (Get Session)

```bash
curl -X POST http://localhost:8069/api/v1/users/login \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "email": "joao@imobiliaria.com",
      "password": "test123"
    }
  }'

# Save the session_id from response
export SESSION_ID="<your_session_id>"
```

### 3. Test Protected Endpoint (Agents)

```bash
# Should succeed with valid bearer + session
curl -X GET http://localhost:8069/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "session_id": "'$SESSION_ID'",
      "limit": 5
    }
  }'

# Expected: 200 OK with agent list
```

### 4. Test Without Bearer Token

```bash
# Should fail with 401
curl -X GET http://localhost:8069/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "session_id": "'$SESSION_ID'",
      "limit": 5
    }
  }'

# Expected: 401 "Bearer token required"
```

### 5. Test Without Session ID

```bash
# Should fail with 401
curl -X GET http://localhost:8069/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "limit": 5
    }
  }'

# Expected: 401 "Session required"
```

### 6. Test Session Hijacking Prevention

```bash
# Change User-Agent (simulate hijacking attempt)
curl -X GET http://localhost:8069/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "User-Agent: DifferentBrowser/1.0" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "session_id": "'$SESSION_ID'",
      "limit": 5
    }
  }'

# Expected: 401 "Session validation failed" (fingerprint mismatch)
```

---

## Using Postman Collection

### 1. Import Collection

```bash
# Collection location
open postman/QuicksolAPI_Complete.postman_collection.json

# Import in Postman: File → Import → Choose file
```

### 2. Setup Environment

Create Postman environment with variables:
```json
{
  "odoo_base_url": "http://localhost:8069",
  "oauth_client_id": "client_EEQix5KVT6JsSUARsdUGnw",
  "oauth_client_secret": "Xu5l7zL9Je6HKcx6EbJJiLwy9JAA0QHozcDE37TGjjC5skPEWfkigZPouqTWzDBG",
  "test_user_email": "joao@imobiliaria.com",
  "test_user_password": "test123",
  "access_token": "",
  "session_id": ""
}
```

### 3. Run Collection

1. **Get OAuth Token**: Run "Get Access Token" request
   - `access_token` automatically saved to environment

2. **User Login**: Run "User Login" request  
   - `session_id` automatically saved to environment (from body, NOT cookie)

3. **Test Agents**: Run any Agents endpoint request
   - Uses `{{access_token}}` and `{{session_id}}` variables
   - Should return 200 OK

4. **Test Security**: Remove `session_id` from request
   - Should return 401 "Session required"

---

## Running E2E Tests

### Cypress Tests

```bash
# From repository root
cd 18.0
npx cypress open

# Select test file:
# - cypress/e2e/agents-dual-auth.cy.js
# - cypress/e2e/properties-dual-auth.cy.js
# - cypress/e2e/assignments-dual-auth.cy.js
# - cypress/e2e/commissions-dual-auth.cy.js
# - cypress/e2e/performance-dual-auth.cy.js

# Or run all tests headless
npx cypress run
```

### Integration Tests

```bash
# From Odoo container
docker compose exec odoo bash

# Run specific test module
odoo -c /etc/odoo/odoo.conf \
  -d realestate \
  --test-enable \
  --stop-after-init \
  -u thedevkitchen_apigateway

# Run specific test file
odoo -c /etc/odoo/odoo.conf \
  -d realestate \
  --test-enable \
  --test-file=addons/thedevkitchen_apigateway/tests/test_dual_auth_validation.py
```

---

## Troubleshooting

### Session ID Not Working

```bash
# Check session in database
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT session_id, user_id, is_active, last_activity 
   FROM thedevkitchen_api_session 
   WHERE session_id = '<your_session_id>';"

# Check session in Redis
docker compose exec redis redis-cli
> SELECT 1
> GET "session:<your_session_id>"
```

### User-Agent Mismatch

```bash
# Check Odoo logs for fingerprint validation
docker compose logs odoo | grep -i "user-agent\|fingerprint\|hijacking"

# Expected: "SESSION HIJACKING DETECTED - USER-AGENT MISMATCH"
```

### Invalid Session ID Format

```bash
# Session IDs should be 60-100 characters
echo -n "<your_session_id>" | wc -c

# If not in range, check middleware validation is working:
grep -A 10 "if len(session_id)" 18.0/extra-addons/thedevkitchen_apigateway/middleware.py
```

### Debug Logs Still Appearing

```bash
# Verify all debug logs removed
grep -n "SESSION DEBUG" 18.0/extra-addons/thedevkitchen_apigateway/middleware.py

# Should return no matches
# If matches found, debug logs not properly removed
```

---

## Expected Outcomes

After completing this spec, you should see:

✅ **All 23 endpoints** protected with dual authentication  
✅ **No debug logs** in Odoo console output  
✅ **Session validation** working (fingerprint check)  
✅ **Postman collection** complete and functional  
✅ **E2E tests** passing for all 5 domains  
✅ **Clear error messages** for missing bearer/session  

---

## Next Steps

1. **Documentation**: Read API authentication guide
2. **Testing**: Run full E2E test suite
3. **Integration**: Use Postman collection for development
4. **Monitoring**: Watch Odoo logs for security events

---

## Quick Reference

| Endpoint | Method | Requires Bearer | Requires Session | Requires Company |
|----------|--------|----------------|------------------|------------------|
| `/api/v1/agents` | GET | ✅ | ✅ | ✅ |
| `/api/v1/agents` | POST | ✅ | ✅ | ✅ |
| `/api/v1/properties` | GET/POST | ✅ | ✅ | ✅ |
| `/api/v1/assignments` | POST | ✅ | ✅ | ✅ |
| `/api/v1/agents/{id}/commission-rules` | GET/POST | ✅ | ✅ | ❌ |
| `/api/v1/agents/{id}/performance` | GET | ✅ | ✅ | ❌ |

**Master Data** endpoints: Bearer only (no session required)

---

## Support

- **Documentation**: See `/specs/002-dual-auth-remaining-endpoints/`
- **Issues**: Check `research.md` for known issues
- **Constitution**: Review `/docs/constitution.md` for architecture
- **ADRs**: See `/docs/adr/ADR-011-controller-security-authentication-storage.md`
