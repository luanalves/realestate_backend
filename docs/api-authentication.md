# API Authentication Guide

**Feature**: Dual Authentication Model  
**Version**: 1.0  
**Last Updated**: 2026-01-17

---

## Overview

The Quicksol Real Estate API uses a **dual authentication model** that combines:

1. **OAuth 2.0 Bearer Tokens** - For API access authorization
2. **Session IDs** - For user context and fingerprint validation

This architecture provides both stateless token-based authentication (OAuth) and stateful session management with security fingerprinting.

---

## Authentication Levels

### Level 1: Bearer Token Only

**Endpoints**: OAuth token management, Master data (read-only)

**Requirements**:
- Valid OAuth 2.0 Bearer token in `Authorization` header
- No session required

**Use Case**: Service-to-service API access, public data retrieval

**Example Endpoints**:
- `POST /api/v1/auth/token` - Get OAuth token
- `POST /api/v1/auth/revoke` - Revoke token
- `GET /api/v1/master/agents` - Read-only master data

### Level 2: Dual Authentication (Bearer + Session)

**Endpoints**: All business operations (Agents, Properties, Assignments, Commissions, etc.)

**Requirements**:
- Valid OAuth 2.0 Bearer token in `Authorization` header
- Valid Session ID in request body (`session_id` parameter)
- Consistent User-Agent during session lifetime
- Session must be active (< 2 hours since last activity)

**Use Case**: User-initiated business operations requiring full security

**Example Endpoints**:
- `GET /api/v1/agents` - List agents
- `POST /api/v1/properties` - Create property
- `PUT /api/v1/agents/{id}` - Update agent

---

## OAuth 2.0 Flow

### Step 1: Obtain Bearer Token

**Endpoint**: `POST /api/v1/auth/token`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "grant_type": "client_credentials",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "refresh_token_value"
  }
}
```

**Store**: Save `access_token` for subsequent API calls

### Step 2: Use Bearer Token

Include the token in all API requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

When token expires (after `expires_in` seconds):

**Endpoint**: `POST /api/v1/auth/token`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "grant_type": "refresh_token",
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }
}
```

---

## User Login Flow (Session Creation)

### Step 1: User Login

**Endpoint**: `POST /api/v1/users/login`

**Requirements**: Valid Bearer token required

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "email": "user@company.com",
    "password": "user_password"
  }
}
```

**Headers**:
```http
Authorization: Bearer {your_access_token}
User-Agent: YourApp/1.0 (Platform)
Accept-Language: pt-BR
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "user_id": 7,
    "session_id": "NKKHAU6wwcZiHKNt4sFnbZDMiYVWGiYpWEU0UW2ksT4p5Hgx8Sqc5XYGv4Xlkn3-newpG236ZQG84NGnOOo0",
    "user_name": "João Silva",
    "email": "user@company.com",
    "companies": [
      {"id": 1, "name": "Imobiliária ABC"}
    ]
  }
}
```

**CRITICAL**: 
- Session ID is in `result.session_id` (NOT in cookies)
- Store `session_id` for subsequent business operations
- Session valid for 2 hours of inactivity

### Step 2: Use Session in Business Requests

**Example**: List Agents

**Endpoint**: `GET /api/v1/agents`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "NKKHAU6wwc...ZQG84NGnOOo0",
    "limit": 10,
    "offset": 0
  }
}
```

**Headers**:
```http
Authorization: Bearer {your_access_token}
User-Agent: YourApp/1.0 (Platform)  ← MUST match login User-Agent
Accept-Language: pt-BR              ← MUST match login language
```

### Step 3: User Logout (Session Invalidation)

**Endpoint**: `POST /api/v1/users/logout`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "NKKHAU6wwc...ZQG84NGnOOo0"
  }
}
```

**Effect**:
- Session marked as inactive in database
- Session removed from Redis cache
- Subsequent requests with this session_id will fail

---

## Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Lifecycle                        │
└─────────────────────────────────────────────────────────────┘

1. LOGIN
   POST /api/v1/users/login
   ├─ Create session record (PostgreSQL)
   ├─ Generate session_id (~80 chars)
   ├─ Create JWT with fingerprint (IP + UA + Lang)
   ├─ Store in Redis (TTL: 7200s)
   └─ Return session_id to client

2. BUSINESS REQUESTS
   GET /api/v1/agents + session_id
   ├─ Validate session_id length (60-100 chars)
   ├─ Lookup session in Redis (fast)
   ├─ Validate JWT fingerprint:
   │  ├─ IP address match
   │  ├─ User-Agent match  ← CRITICAL
   │  └─ Accept-Language match
   ├─ Update last_activity timestamp
   └─ Proceed with request

3. SESSION TIMEOUT (2 hours inactivity)
   ├─ Redis key expires (automatic)
   ├─ Database session stays (for audit)
   └─ Next request: "Session expired" error

4. LOGOUT
   POST /api/v1/users/logout
   ├─ Set is_active = False (database)
   ├─ Delete from Redis
   └─ Return success
```

---

## Fingerprint Validation

### What is Fingerprinting?

Session fingerprinting validates that requests come from the same client that created the session. This prevents **session hijacking** attacks.

### Fingerprint Components

1. **IP Address** - Client's remote IP
2. **User-Agent** - Browser/application identifier
3. **Accept-Language** - Client's preferred language

### How It Works

**Login** (Session Creation):
```python
fingerprint = {
    'ip': '192.168.1.100',
    'ua': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
    'lang': 'pt-BR'
}

# Stored in JWT token
jwt_payload = {
    'uid': 7,
    'session_id': 'NKKHAU6...',
    'fingerprint': fingerprint,
    'exp': 1705498522
}
```

**Subsequent Requests**:
```python
# Extract fingerprint from JWT
token_fingerprint = jwt.decode(session.security_token)['fingerprint']

# Compare with current request
current_ip = request.remote_addr
current_ua = request.headers['User-Agent']
current_lang = request.headers['Accept-Language']

if current_ua != token_fingerprint['ua']:
    return {"error": {"status": 401, "message": "Session validation failed"}}
```

### User-Agent Consistency Requirement

**CRITICAL**: Your application MUST use the same `User-Agent` header for all requests during a session.

**Example - Correct**:
```bash
# Login
curl -H "User-Agent: MyApp/1.0" POST /api/v1/users/login

# Business request (same User-Agent)
curl -H "User-Agent: MyApp/1.0" GET /api/v1/agents  ✅ SUCCESS
```

**Example - Incorrect**:
```bash
# Login
curl -H "User-Agent: MyApp/1.0" POST /api/v1/users/login

# Business request (different User-Agent)
curl -H "User-Agent: MyApp/2.0" GET /api/v1/agents  ❌ FAIL (401)
```

**Why This Matters**:
- Prevents attackers from stealing session IDs
- Detects if session is being used from different device/browser
- Part of ADR-011 security requirements

---

## Session Expiration

### Timeout Rules

- **Inactivity Timeout**: 2 hours (7200 seconds)
- **Trigger**: No requests with this session_id for 2 hours
- **Effect**: Redis key expires, session invalid

### Checking Session Status

Session validation occurs on every request:

```python
# Redis TTL check
if redis.ttl(f'session:{session_id}') <= 0:
    return {"error": {"status": 401, "message": "Session expired"}}
```

### Extending Session

Every successful request **extends** the session:

```python
# Update last_activity and reset Redis TTL
redis.setex(f'session:{session_id}', 7200, session_data)
```

**Effect**: As long as you make at least one request every 2 hours, session stays alive.

---

## Request Format Examples

### Authentication Only (Bearer Token)

```http
POST /api/v1/auth/token HTTP/1.1
Host: localhost:8069
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "grant_type": "client_credentials",
    "client_id": "client_xxx",
    "client_secret": "secret_yyy"
  }
}
```

### Dual Authentication (Bearer + Session)

```http
GET /api/v1/agents HTTP/1.1
Host: localhost:8069
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
User-Agent: MyApp/1.0 (macOS 12.0)
Accept-Language: pt-BR
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "NKKHAU6wwc...ZQG84NGnOOo0",
    "limit": 10,
    "offset": 0
  }
}
```

---

## Multi-Tenancy (Company Isolation)

### Company Domain Filtering

Most business endpoints use `@require_company` decorator to enforce multi-tenant isolation.

**Behavior**:
- User's accessible companies determined at login
- Each request filtered by `company_ids IN user.estate_company_ids`
- Users only see/modify data from their companies

**Example**:
```python
# User João belongs to companies [1, 2]
# Query: Get all agents

# SQL generated:
SELECT * FROM estate_agent 
WHERE company_ids IN (1, 2)
```

**Superuser Exception**:
- Users with `base.group_system` see ALL companies
- Useful for administrators and reporting

---

## Error Responses

### 401 Unauthorized - Missing Bearer Token

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authorization header is required"
  }
}
```

### 401 Unauthorized - Invalid Token

```json
{
  "error": {
    "code": "invalid_token",
    "message": "Token not found or invalid"
  }
}
```

### 401 Unauthorized - Missing Session

```json
{
  "error": {
    "status": 401,
    "message": "Session required"
  }
}
```

### 401 Unauthorized - Session Expired

```json
{
  "error": {
    "status": 401,
    "message": "Session expired"
  }
}
```

### 401 Unauthorized - Fingerprint Mismatch

```json
{
  "error": {
    "status": 401,
    "message": "Session validation failed"
  }
}
```

**Note**: Fingerprint mismatch logged server-side with details:
```
[SESSION HIJACKING DETECTED - USER-AGENT MISMATCH]
user_id=7 session_id=NKKHAU6...
```

### 401 Unauthorized - Invalid Session Format

```json
{
  "error": {
    "status": 401,
    "message": "Invalid session_id format (must be 60-100 characters)"
  }
}
```

### 403 Forbidden - Insufficient Scope

```json
{
  "error": "insufficient_scope",
  "error_description": "Missing required scopes: write:agents"
  }
}
```

### 403 Forbidden - No Company Access

```json
{
  "error": {
    "status": 403,
    "message": "User has no company access"
  }
}
```

---

## Best Practices

### 1. Store Credentials Securely

```bash
# Use environment variables
export OAUTH_CLIENT_ID="client_xxx"
export OAUTH_CLIENT_SECRET="secret_yyy"

# Never commit credentials to git
echo ".env" >> .gitignore
```

### 2. Refresh Tokens Before Expiry

```javascript
// Check token expiration
const expiresAt = Date.now() + (response.expires_in * 1000);

// Refresh 5 minutes before expiry
if (Date.now() > expiresAt - 300000) {
    await refreshToken();
}
```

### 3. Maintain Consistent User-Agent

```javascript
// Set once at app initialization
const USER_AGENT = 'MyApp/1.0 (macOS 12.0)';

// Use in all requests
axios.defaults.headers.common['User-Agent'] = USER_AGENT;
```

### 4. Handle Session Expiration

```javascript
// Detect session expiry
if (response.error && response.error.message.includes('Session expired')) {
    // Re-login
    await login(email, password);
    // Retry request
    return retryRequest(originalRequest);
}
```

### 5. Logout on App Close

```javascript
// Cleanup on exit
window.addEventListener('beforeunload', async () => {
    if (sessionId) {
        await logout(sessionId);
    }
});
```

---

## Security Considerations

### Session ID Format

- **Length**: 60-100 characters (typically ~80)
- **Entropy**: High randomness using `secrets.token_urlsafe(64)`
- **Validation**: Length checked before database lookup

### JWT Token Security

- **Algorithm**: HS256 (HMAC with SHA-256)
- **Secret**: From `database_secret` or `admin_passwd` config
- **Expiry**: 24 hours from creation
- **Claims**: uid, session_id, fingerprint, exp, iat, iss

### Storage Recommendations

**Browser Applications**:
- Store session_id in `sessionStorage` (cleared on tab close)
- DO NOT store in `localStorage` (XSS risk)
- Use HttpOnly cookies if possible (set server-side)

**Mobile Applications**:
- Use platform's secure storage (Keychain on iOS, Keystore on Android)
- Clear on logout
- Encrypt if storing on disk

**Server-to-Server**:
- Store in memory or encrypted configuration
- Rotate regularly
- Use service accounts with minimal scopes

---

## Testing Authentication

### Using Postman

1. **Get OAuth Token**:
   - Run "Get OAuth Token" request
   - Auto-saves `access_token` to environment

2. **User Login**:
   - Run "User Login" request
   - Auto-saves `session_id` to environment

3. **Business Request**:
   - Run any business endpoint
   - Uses `{{access_token}}` and `{{session_id}}` automatically

### Using cURL

```bash
# Step 1: Get OAuth token
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "grant_type": "client_credentials",
      "client_id": "client_xxx",
      "client_secret": "secret_yyy"
    }
  }' | jq -r '.result.access_token')

# Step 2: User login
SESSION=$(curl -s -X POST http://localhost:8069/api/v1/users/login \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: TestClient/1.0" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "email": "user@company.com",
      "password": "password"
    }
  }' | jq -r '.result.session_id')

# Step 3: Business request
curl -X GET http://localhost:8069/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: TestClient/1.0" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"call\",
    \"params\": {
      \"session_id\": \"$SESSION\",
      \"limit\": 5
    }
  }"
```

---

## Related Documentation

- **Troubleshooting**: See [troubleshooting-sessions.md](troubleshooting-sessions.md) for common issues
- **API Reference**: See Postman collection `QuicksolAPI_Complete.postman_collection.json`
- **ADR-011**: Controller Security and Authentication Storage requirements
- **ADR-008**: API Security and Multi-Tenancy architecture

---

## Support

For authentication issues:
1. Check [troubleshooting-sessions.md](troubleshooting-sessions.md)
2. Review server logs for `[SESSION HIJACKING DETECTED]` messages
3. Verify User-Agent consistency
4. Check session hasn't expired (< 2 hours)
