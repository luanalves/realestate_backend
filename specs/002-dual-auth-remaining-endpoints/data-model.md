# Data Model: Session & Authentication

**Feature**: 002-dual-auth-remaining-endpoints  
**Date**: 2026-01-17  
**Status**: Reference (No new entities - documenting existing session model)

---

## Overview

This spec does not introduce new data entities. It validates and documents the existing session management data model used by the dual authentication system.

---

## Existing Entities

### thedevkitchen.api.session

**Purpose**: Store API session data for dual authentication (Bearer Token + Session validation)

**Table**: `thedevkitchen_api_session`

**Model File**: `18.0/extra-addons/thedevkitchen_apigateway/models/api_session.py`

#### Fields

| Field Name | Type | Required | Indexed | Description |
|------------|------|----------|---------|-------------|
| `id` | Integer | Yes | PK | Auto-increment primary key |
| `session_id` | Char(80) | Yes | Yes | Unique session identifier (~80 chars) |
| `user_id` | Many2one(res.users) | Yes | Yes | Reference to authenticated user |
| `ip_address` | Char | No | No | Client IP address for fingerprint |
| `user_agent` | Text | No | No | Client User-Agent for fingerprint |
| `is_active` | Boolean | Yes | Yes | Session active status |
| `last_activity` | Datetime | Yes | No | Last request timestamp |
| `login_at` | Datetime | Yes | No | Session creation timestamp |
| `logout_at` | Datetime | No | No | Session termination timestamp |
| `security_token` | Text | Yes | No | JWT token with fingerprint |

#### Indexes

```sql
CREATE INDEX idx_session_id ON thedevkitchen_api_session(session_id);
CREATE INDEX idx_user_id ON thedevkitchen_api_session(user_id);
CREATE INDEX idx_is_active ON thedevkitchen_api_session(is_active);
```

#### Sample Data

```python
{
    'id': 42,
    'session_id': 'NKKHAU6wwcZiHKNt4sFnbZDMiYVWGiYpWEU0UW2ksT4p5Hgx8Sqc5XYGv4Xlkn3-newpG236ZQG84NGnOOo0',
    'user_id': 7,  # res.users id
    'ip_address': '192.168.1.100',
    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
    'is_active': True,
    'last_activity': '2026-01-17 10:30:45',
    'login_at': '2026-01-17 08:15:22',
    'logout_at': None,
    'security_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
}
```

#### Validation Rules

1. **session_id**: 
   - Length: 60-100 characters (to be validated in this spec)
   - Unique across all records
   - Generated using secure random generator

2. **security_token**:
   - JWT format
   - Contains fingerprint: `{'ip': ..., 'user_agent': ..., 'language': ...}`
   - Signed with secret key
   - Expires after 24 hours

3. **is_active**:
   - Set to `True` on login
   - Set to `False` on logout or session expiration
   - Used to filter valid sessions

4. **last_activity**:
   - Updated on every authenticated request
   - Used for session timeout (2 hours of inactivity)

#### State Transitions

```
[Login] → session_id generated
        → is_active = True
        → login_at = now()
        → security_token = JWT(fingerprint)

[Request] → last_activity = now()
          → Validate fingerprint from JWT
          → Check is_active = True

[Logout] → is_active = False
         → logout_at = now()

[Timeout] → is_active = False (if last_activity > 2 hours ago)
```

---

## Redis Session Storage

**Purpose**: Fast session lookup and validation

**Redis DB**: Index 1  
**Key Pattern**: `session:{session_id}`  
**TTL**: 7200 seconds (2 hours)

### Stored Data

```json
{
  "user_id": 7,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "login_at": "2026-01-17T08:15:22Z",
  "last_activity": "2026-01-17T10:30:45Z",
  "is_active": true
}
```

### Operations

1. **Create Session** (Login):
   ```python
   redis.setex(f'session:{session_id}', 7200, json.dumps(session_data))
   ```

2. **Validate Session** (Every Request):
   ```python
   session_data = redis.get(f'session:{session_id}')
   if session_data:
       # Validate fingerprint
       # Update last_activity
       redis.setex(f'session:{session_id}', 7200, updated_data)
   ```

3. **Invalidate Session** (Logout):
   ```python
   redis.delete(f'session:{session_id}')
   ```

---

## JWT Token Structure

### Header
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload
```json
{
  "user_id": 7,
  "session_id": "NKKHAU6wwcZiHKNt...",
  "fingerprint": {
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "language": "pt-BR"
  },
  "exp": 1705498522,
  "iat": 1705412122,
  "iss": "thedevkitchen-api-gateway"
}
```

### Signature
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

---

## No New Entities Required

This spec does not create or modify any data entities. It only:

1. **Validates** existing session_id format (length check)
2. **Documents** User-Agent consistency requirement
3. **Tests** existing dual authentication system
4. **Creates** Postman collection for API documentation

All database schemas remain unchanged.

---

## Session Lifecycle (Sequence Diagram)

```
Client          API Gateway       Redis        PostgreSQL
  |                  |               |               |
  |--- POST /login --|               |               |
  |                  |-- Generate ---|               |
  |                  |   session_id  |               |
  |                  |               |               |
  |                  |-- Store ----->|               |
  |                  |   session     |               |
  |                  |               |               |
  |                  |-- INSERT ------------------>  |
  |                  |   api_session                 |
  |<-- session_id ---|                               |
  |    + JWT token   |                               |
  |                  |                               |
  |--- POST /agents --|                              |
  |    (with session) |                              |
  |                  |-- Validate -->|               |
  |                  |<-- OK --------|               |
  |                  |                               |
  |                  |-- Check fingerprint           |
  |                  |   (IP + UA match?)            |
  |                  |                               |
  |                  |-- Update ----->|              |
  |                  |   last_activity               |
  |<-- Agent data ---|                               |
  |                  |                               |
  |--- POST /logout --|                              |
  |                  |-- Delete ----->|              |
  |                  |                               |
  |                  |-- UPDATE ------------------->  |
  |                  |   (is_active=False)           |
  |<-- Success ------|                               |
```

---

## Fingerprint Validation Logic

```python
def validate_fingerprint(request, jwt_payload):
    """
    Validate request fingerprint against JWT payload
    
    Returns: (valid: bool, reason: str)
    """
    # Extract fingerprint from JWT
    jwt_fingerprint = jwt_payload.get('fingerprint', {})
    
    # Extract current request fingerprint
    current_ip = request.httprequest.remote_addr
    current_ua = request.httprequest.headers.get('User-Agent', '')
    current_lang = request.httprequest.headers.get('Accept-Language', '')
    
    # Validate IP (if configured)
    if jwt_fingerprint.get('ip') != current_ip:
        return False, f"IP mismatch: {jwt_fingerprint.get('ip')} != {current_ip}"
    
    # Validate User-Agent (if configured)
    if jwt_fingerprint.get('user_agent') != current_ua:
        return False, f"User-Agent mismatch"
    
    # Validate Language (optional)
    if jwt_fingerprint.get('language') != current_lang:
        _logger.warning(f"Language changed: {jwt_fingerprint.get('language')} -> {current_lang}")
    
    return True, "Fingerprint valid"
```

---

## Configuration

**Environment Variables** (from `.env` or `odoo.conf`):

```ini
[api_gateway]
session_timeout = 7200  # 2 hours in seconds
jwt_issuer = thedevkitchen-api-gateway
jwt_secret = ${SECRET_KEY}  # from database_secret or admin_passwd

[session_fingerprint]
validate_ip = true
validate_user_agent = true
validate_language = false  # Optional
```

---

## Validation Requirements (This Spec)

### New Validation to Add

1. **Session ID Length Validation**:
   ```python
   if len(session_id) < 60 or len(session_id) > 100:
       raise ValueError("Invalid session_id format: must be 60-100 characters")
   ```

2. **User-Agent Documentation**:
   - Must remain constant during session lifetime
   - Changing User-Agent invalidates session
   - Document in endpoint descriptions
   - Include in troubleshooting guide

3. **Error Messages**:
   - `"Invalid session_id format"` - length validation failed
   - `"Session validation failed"` - fingerprint mismatch
   - `"Session expired"` - last_activity > 2 hours ago
   - `"Session required"` - session_id not provided

---

## Summary

**Entities Modified**: None  
**Entities Created**: None  
**Validations Added**: session_id length check  
**Documentation Updated**: User-Agent requirement  

This spec focuses on **validation, testing, and documentation** of the existing session management system, not data model changes.
