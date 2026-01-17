# Troubleshooting: Session Issues

**Feature**: Session Validation and Fingerprinting  
**Version**: 1.0  
**Last Updated**: 2026-01-17

---

## Quick Diagnosis

Use this flowchart to identify your issue:

```
┌─────────────────────────────────────┐
│   Error Message                     │
└─────────────────────────────────────┘
           │
           ├─ "Session required"
           │   └─► Issue #1: Missing session_id
           │
           ├─ "Session validation failed"
           │   └─► Issue #2: User-Agent mismatch (most common)
           │
           ├─ "Session expired"
           │   └─► Issue #3: Session timeout (> 2 hours)
           │
           ├─ "Invalid session_id format"
           │   └─► Issue #4: Session ID length validation
           │
           └─ "Session token required"
               └─► Issue #5: Missing JWT in session record
```

---

## Issue #1: "Session required"

### Error Response

```json
{
  "error": {
    "status": 401,
    "message": "Session required"
  }
}
```

### Root Cause

Session ID is missing from the request or cannot be found in the database/Redis.

### Common Scenarios

#### Scenario A: session_id Not Sent

**Problem**: Request doesn't include `session_id` parameter

**Example**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "limit": 10  // ❌ Missing session_id
  }
}
```

**Solution**: Add `session_id` to request body
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "session_id": "NKKHAU6wwc...ZQG84NGnOOo0",  // ✅ Added
    "limit": 10
  }
}
```

#### Scenario B: session_id Extraction Failed

**Problem**: session_id sent in wrong location

**Extraction Priority**:
1. **Function kwargs** (highest priority)
2. **Request body** (JSON-RPC params)
3. **Headers** (X-Openerp-Session-Id)
4. **Cookies** (session_id)

**Solution**: Put session_id in request body (params) for JSON-RPC calls

#### Scenario C: Session Not Found in Database

**Problem**: Invalid or deleted session_id

**Check**:
```sql
SELECT * FROM thedevkitchen_api_session 
WHERE session_id = 'your_session_id';
```

**Solution**: 
- If no record found: User needs to login again
- If record exists but `is_active = False`: Session was logged out
- If record exists but Redis missing: Redis cache cleared (expected after restart)

---

## Issue #2: "Session validation failed" (User-Agent Mismatch)

### Error Response

```json
{
  "error": {
    "status": 401,
    "message": "Session validation failed"
  }
}
```

### Server Log

```
[SESSION HIJACKING DETECTED - USER-AGENT MISMATCH]
user_id=7 session_id=NKKHAU6...
```

### Root Cause

**User-Agent header changed** between login and current request.

This is the **most common session validation failure**.

### Understanding the Problem

**What is User-Agent?**
```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) 
            AppleWebKit/537.36 (KHTML, like Gecko) 
            Chrome/91.0.4472.124 Safari/537.36
```

**Why It Matters:**
- Stored in JWT token during login as fingerprint
- Validated on every subsequent request
- Prevents session hijacking attacks

### Common Scenarios

#### Scenario A: Inconsistent User-Agent in API Client

**Problem**: API client uses different User-Agent per request

**Example - Postman**:
```
Login request:  User-Agent: PostmanRuntime/7.28.4
Next request:   User-Agent: PostmanRuntime/7.29.0  ❌ MISMATCH
```

**Solution**: Set consistent User-Agent in Postman
1. Go to Settings → General
2. Set "User-Agent" to fixed value
3. Or remove to use default consistently

**Example - JavaScript/Axios**:
```javascript
// ❌ Bad: Different User-Agent per request
axios.post('/api/v1/users/login', {...});
axios.get('/api/v1/agents', {...});  // Default UA may differ

// ✅ Good: Set once globally
axios.defaults.headers.common['User-Agent'] = 'MyApp/1.0';
axios.post('/api/v1/users/login', {...});
axios.get('/api/v1/agents', {...});  // Same UA
```

**Example - cURL**:
```bash
# ❌ Bad: Missing User-Agent on login, present on business request
curl -X POST /api/v1/users/login ...
curl -H "User-Agent: TestClient/1.0" -X GET /api/v1/agents ...

# ✅ Good: Consistent User-Agent
UA="TestClient/1.0"
curl -H "User-Agent: $UA" -X POST /api/v1/users/login ...
curl -H "User-Agent: $UA" -X GET /api/v1/agents ...
```

#### Scenario B: Browser Updates Mid-Session

**Problem**: Browser auto-updates during active session

**Example**:
```
Login:        User-Agent: Chrome/120.0.0.0
After update: User-Agent: Chrome/121.0.0.0  ❌ MISMATCH
```

**Solution**: 
- User must logout and login again after browser update
- Implement session refresh mechanism
- Consider relaxing fingerprint to major version only (requires code change)

#### Scenario C: Load Balancer Modifying Headers

**Problem**: Proxy/load balancer strips or modifies User-Agent

**Detection**:
```python
# Login User-Agent (before proxy)
User-Agent: MyApp/1.0

# Request User-Agent (after proxy modification)
User-Agent: nginx/1.18.0  ❌ REPLACED
```

**Solution**:
- Configure proxy to preserve original User-Agent
- Use `X-Forwarded-User-Agent` custom header
- Modify middleware to check both headers

### Debugging Steps

#### Step 1: Capture User-Agent from Login

```bash
# Login and save User-Agent used
curl -v -X POST http://localhost:8069/api/v1/users/login \
  -H "User-Agent: TestClient/1.0" \
  ... \
  2>&1 | grep "User-Agent"
```

#### Step 2: Check Server Logs

```bash
# Look for fingerprint validation logs
docker compose -f 18.0/docker-compose.yml logs odoo | grep "USER-AGENT MISMATCH"
```

**Example Log**:
```
[SESSION HIJACKING DETECTED - USER-AGENT MISMATCH]
Token UA: Mozilla/5.0 (Macintosh; ...)
Current UA: PostmanRuntime/7.28.4
user_id=7 session_id=NKKHAU6...
```

#### Step 3: Compare User-Agents

```python
# Extract from JWT token
import jwt
token = session.security_token
payload = jwt.decode(token, secret, algorithms=['HS256'])
login_ua = payload['fingerprint']['ua']

# Compare with current request
current_ua = request.headers.get('User-Agent')

if login_ua != current_ua:
    print(f"MISMATCH!")
    print(f"Login:   {login_ua}")
    print(f"Current: {current_ua}")
```

### Preventive Measures

1. **Set User-Agent Once**:
```javascript
// Application initialization
const APP_USER_AGENT = 'MyApp/1.0 (Platform)';
axios.defaults.headers.common['User-Agent'] = APP_USER_AGENT;
```

2. **Test Before Deployment**:
```bash
# Verify User-Agent consistency
./scripts/test-session-fingerprint.sh
```

3. **Monitor Logs**:
```bash
# Alert on fingerprint mismatches
tail -f odoo.log | grep "USER-AGENT MISMATCH" | mail -s "Alert" admin@company.com
```

---

## Issue #3: "Session expired"

### Error Response

```json
{
  "error": {
    "status": 401,
    "message": "Session expired"
  }
}
```

### Server Log

```
JWT token expired for session NKKHAU6...
```

### Root Cause

Session has not been used for **2 hours** (7200 seconds).

### How Session Timeout Works

**Creation**:
```python
# Login creates session
redis.setex(f'session:{session_id}', 7200, session_data)
# TTL = 7200 seconds (2 hours)
```

**Activity Extension**:
```python
# Every request resets TTL
redis.setex(f'session:{session_id}', 7200, updated_data)
# Clock resets to 2 hours from now
```

**Expiration**:
```python
# After 2 hours of no requests
redis.ttl(f'session:{session_id}')  # Returns -2 (expired)
# Session key deleted automatically
```

### Common Scenarios

#### Scenario A: Long Idle Period

**Problem**: User left application open, no requests for > 2 hours

**Timeline**:
```
10:00 AM - Login (session created, TTL = 2h)
10:30 AM - Request (TTL reset to 2h from now = 12:30 PM)
11:00 AM - Request (TTL reset to 2h from now = 1:00 PM)
... no activity ...
1:01 PM - Request ❌ EXPIRED (> 2h since 11:00 AM)
```

**Solution**: Implement keep-alive mechanism
```javascript
// Ping every 90 minutes to keep session alive
setInterval(async () => {
    await axios.get('/api/v1/me', {
        params: { session_id: sessionId }
    });
}, 90 * 60 * 1000);  // 90 minutes
```

#### Scenario B: JWT Token Expiry (24 hours)

**Problem**: JWT token in session record expired

**Check**:
```python
import jwt
payload = jwt.decode(session.security_token, secret, algorithms=['HS256'])
# Raises jwt.ExpiredSignatureError if exp < now
```

**Solution**: User must login again (cannot refresh JWT)

#### Scenario C: Server Restart Cleared Redis

**Problem**: Redis restarted, all sessions lost

**Detection**:
```bash
# Check Redis uptime
docker compose exec redis redis-cli INFO server | grep uptime_in_seconds
```

**Solution**:
- Configure Redis persistence (AOF/RDB)
- Users login again after server restart
- Implement session restoration from PostgreSQL (requires code change)

### Debugging Steps

#### Step 1: Check Redis TTL

```bash
# Check if session exists in Redis
docker compose exec redis redis-cli GET "session:NKKHAU6..."

# Check remaining TTL
docker compose exec redis redis-cli TTL "session:NKKHAU6..."
# Returns: remaining seconds (-2 = expired, -1 = no expiry)
```

#### Step 2: Check Database Session

```sql
SELECT 
    session_id,
    is_active,
    last_activity,
    EXTRACT(EPOCH FROM (NOW() - last_activity)) as seconds_since_activity,
    login_at,
    logout_at
FROM thedevkitchen_api_session
WHERE session_id = 'NKKHAU6...';
```

**Interpretation**:
```
seconds_since_activity > 7200  → Session timed out
logout_at IS NOT NULL         → User logged out
is_active = False              → Session invalidated
```

### Solutions

#### Solution A: Auto-Refresh Session

```javascript
// Check session age on each request
const sessionAge = Date.now() - lastActivityTime;
const twoHours = 2 * 60 * 60 * 1000;

if (sessionAge > twoHours) {
    // Session likely expired, re-login
    await login(email, password);
}
```

#### Solution B: Extend TTL to 8 Hours

**Code Change** (requires developer):
```python
# middleware.py
redis.setex(f'session:{session_id}', 28800, session_data)  # 8 hours
```

**Trade-off**: Longer sessions = higher security risk

#### Solution C: Session Refresh Endpoint

**Create** new endpoint:
```python
@http.route('/api/v1/sessions/refresh', type='http', auth='none', methods=['POST'])
@require_jwt
@require_session
def refresh_session(self, session_id, **kwargs):
    # Extend session TTL without re-login
    return {'success': True, 'expires_at': new_expiry}
```

---

## Issue #4: "Invalid session_id format"

### Error Response

```json
{
  "error": {
    "status": 401,
    "message": "Invalid session_id format (must be 60-100 characters)"
  }
}
```

### Root Cause

Session ID length is outside acceptable range (60-100 characters).

**Expected Length**: ~80 characters

### Common Scenarios

#### Scenario A: Truncated Session ID

**Problem**: session_id copied/pasted incorrectly

**Example**:
```
Full:      NKKHAU6wwcZiHKNt4sFnbZDMiYVWGiYpWEU0UW2ksT4p5Hgx8Sqc5XYGv4Xlkn3...
Truncated: NKKHAU6wwcZiHKNt4sFnbZD  ❌ Only 23 chars
```

**Solution**: 
- Copy full session_id from login response
- Use variable/environment storage instead of manual copy

#### Scenario B: Empty/Null session_id

**Problem**: session_id is empty string or null

**Example**:
```json
{
  "params": {
    "session_id": "",  // ❌ Length = 0
    "limit": 10
  }
}
```

**Solution**: Ensure session_id is populated before request

#### Scenario C: Wrong Value Used

**Problem**: Using access_token instead of session_id

**Example**:
```json
{
  "params": {
    "session_id": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  // ❌ This is JWT token, not session_id
    "limit": 10
  }
}
```

**Solution**: Use `result.session_id` from login response, not `access_token`

### Debugging Steps

#### Step 1: Measure session_id Length

```javascript
console.log('session_id length:', sessionId.length);
// Expected: 60-100 (typically ~80)
```

```bash
echo -n "$SESSION_ID" | wc -c
# Expected: 60-100
```

#### Step 2: Validate Format

```python
import re

# Valid session_id pattern
pattern = r'^[A-Za-z0-9_-]{60,100}$'

if not re.match(pattern, session_id):
    print("Invalid session_id format")
else:
    print("Valid session_id")
```

### Solutions

#### Solution A: Extract session_id Correctly

```javascript
// ✅ Correct extraction from login response
const response = await login(email, password);
const sessionId = response.result.session_id;  // NOT response.result.access_token

// Verify length
if (sessionId.length < 60 || sessionId.length > 100) {
    throw new Error('Invalid session_id received from server');
}
```

#### Solution B: Use Environment Variables (Postman)

```javascript
// Login test script
const jsonData = pm.response.json();
if (jsonData.result && jsonData.result.session_id) {
    pm.environment.set('session_id', jsonData.result.session_id);
}

// Subsequent requests
{
  "params": {
    "session_id": "{{session_id}}"  // ✅ Auto-populated
  }
}
```

---

## Issue #5: "Session token required"

### Error Response

```json
{
  "error": {
    "status": 401,
    "message": "Session token required"
  }
}
```

### Server Log

```
[SESSION SECURITY] No JWT token found for session NKKHAU6... user_id=7
```

### Root Cause

Session record exists but `security_token` field is NULL or empty.

### Common Scenarios

#### Scenario A: Database Corruption

**Problem**: security_token deleted or not created during login

**Check**:
```sql
SELECT session_id, security_token IS NULL as missing_token
FROM thedevkitchen_api_session
WHERE session_id = 'NKKHAU6...';

-- missing_token = true → Problem confirmed
```

**Solution**: User must logout and login again to regenerate token

#### Scenario B: Migration Issue

**Problem**: Old sessions created before security_token field added

**Detection**:
```sql
SELECT COUNT(*) 
FROM thedevkitchen_api_session
WHERE security_token IS NULL;
-- > 0 → Old sessions exist
```

**Solution**: Invalidate old sessions
```sql
UPDATE thedevkitchen_api_session
SET is_active = false
WHERE security_token IS NULL;
```

---

## Additional Common Issues

### Issue #6: IP Address Mismatch

**Error**: "Session validation failed"

**Log**:
```
[SESSION HIJACKING DETECTED - IP MISMATCH]
Token IP=192.168.1.100 != Current IP=192.168.1.200
```

**Cause**: Client IP changed (VPN, network switch, mobile data ↔ WiFi)

**Solution**: 
- User logout and login again
- Or configure middleware to skip IP validation (security risk)

### Issue #7: Accept-Language Mismatch

**Error**: "Session validation failed"

**Log**:
```
[SESSION HIJACKING DETECTED - LANGUAGE MISMATCH]
```

**Cause**: Browser/client language settings changed

**Solution**: Keep Accept-Language header consistent

### Issue #8: Session Already Logged Out

**Error**: "Session required"

**Cause**: Session was explicitly logged out via `/api/v1/users/logout`

**Check**:
```sql
SELECT logout_at, is_active 
FROM thedevkitchen_api_session
WHERE session_id = 'NKKHAU6...';

-- logout_at NOT NULL → Session was logged out
-- is_active = false → Session inactive
```

**Solution**: User must login again (cannot reactivate logged-out session)

---

## Prevention Checklist

Before going to production, verify:

- [ ] User-Agent set consistently across all requests
- [ ] session_id extracted from `result.session_id` (not cookies)
- [ ] Session keep-alive implemented (if long idle periods expected)
- [ ] Error handling for "Session expired" → auto-login
- [ ] Error handling for "Session validation failed" → user notification
- [ ] Monitoring for `[SESSION HIJACKING DETECTED]` logs
- [ ] Session length validated (60-100 chars) before sending
- [ ] Accept-Language header set consistently
- [ ] Logout called on app close/logout button

---

## Monitoring and Alerts

### Log Patterns to Monitor

```bash
# Session hijacking attempts
grep "SESSION HIJACKING DETECTED" odoo.log | wc -l

# Expired sessions
grep "Session expired" odoo.log | wc -l

# Invalid session formats
grep "Invalid session_id format" odoo.log | wc -l
```

### Metrics to Track

```sql
-- Active sessions count
SELECT COUNT(*) 
FROM thedevkitchen_api_session
WHERE is_active = true;

-- Average session duration
SELECT AVG(EXTRACT(EPOCH FROM (logout_at - login_at))) as avg_duration_seconds
FROM thedevkitchen_api_session
WHERE logout_at IS NOT NULL;

-- Session validation failures (from audit log)
SELECT COUNT(*) 
FROM api_access_log
WHERE status_code = 401
  AND created_at > NOW() - INTERVAL '1 day';
```

---

## Getting Help

If issues persist after following this guide:

1. **Check Server Logs**:
   ```bash
   docker compose -f 18.0/docker-compose.yml logs -f odoo | grep -i session
   ```

2. **Enable Debug Logging** (temporarily):
   ```python
   # middleware.py
   _logger.setLevel(logging.DEBUG)
   ```

3. **Collect Diagnostic Info**:
   - Session ID (first 20 chars only)
   - Error message
   - Server log excerpt
   - User-Agent headers from requests
   - Timeline of events

4. **Contact Support**:
   - Include diagnostic info
   - Describe expected vs actual behavior
   - Provide reproduction steps

---

## Related Documentation

- **Authentication Flow**: See [api-authentication.md](api-authentication.md)
- **API Reference**: See Postman collection
- **ADR-011**: Controller Security requirements
- **Spec 002**: Dual Authentication implementation details
