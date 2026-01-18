# Data Model: Bearer Token Validation

**Feature**: Bearer Token Validation for User Authentication Endpoints  
**Phase**: 1 - Design  
**Date**: January 15, 2026

## Overview

This feature does **not introduce new data models**. It leverages existing authentication and session infrastructure.

## Existing Data Models (No Changes)

### OAuth Access Token (`thedevkitchen.oauth.token`)

**Location**: `thedevkitchen_apigateway` module  
**Purpose**: Stores OAuth 2.0 JWT access tokens for API authentication

**Key Fields**:
- `access_token` (Char): The JWT token string (indexed)
- `token_type` (Char): Token type (always "Bearer")
- `expires_at` (Datetime): Token expiration timestamp
- `revoked` (Boolean): Revocation flag
- `application_id` (Many2one): Reference to OAuth application
- `user_id` (Many2one): Reference to authenticated user
- `scope` (Char): Granted permissions (e.g., "read write")

**Used By**: `@require_jwt` decorator for bearer token validation

**No Changes**: Feature uses existing validation logic without model modifications

### HTTP Session (Redis Storage)

**Location**: Redis DB index 1  
**Purpose**: Stores active user sessions with context and security fingerprints

**Key Pattern**: `session:<session_id>`

**Stored Data** (Python dict serialized to Redis):
```python
{
    "uid": 2,                           # User ID
    "login": "user@example.com",        # Username
    "security_token": "<jwt_string>",   # Session JWT with fingerprint
    "context": {
        "lang": "pt_BR",
        "tz": "America/Sao_Paulo",
        "allowed_company_ids": [1, 2]
    },
    "company_id": 1,
    "last_activity": <timestamp>
}
```

**TTL**: 7200 seconds (2 hours) with auto-renewal on activity

**Used By**: `@require_session` decorator for session validation

**No Changes**: Feature uses existing session storage without structure modifications

### API Session Model (`thedevkitchen.api.session`)

**Location**: `thedevkitchen_apigateway` module  
**Purpose**: Tracks API sessions for audit and management

**Key Fields**:
- `session_id` (Char): Session identifier
- `user_id` (Many2one): Reference to user
- `security_token` (Text): JWT with fingerprint for session hijacking prevention
- `ip_address` (Char): Client IP address
- `user_agent` (Char): Client user agent
- `created_at` (Datetime): Session creation timestamp
- `last_activity` (Datetime): Last request timestamp

**Used By**: `SessionValidator.validate()` called by `@require_session`

**No Changes**: Feature uses existing session tracking without model modifications

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Flow                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      validates      ┌────────────────────────┐
│  HTTP Request    │─────────────────────>│  OAuth Access Token    │
│  (Authorization  │                      │  (PostgreSQL)          │
│   Header)        │                      │  - access_token        │
└──────────────────┘                      │  - expires_at          │
                                          │  - revoked             │
                                          │  - application_id      │
                                          └────────────────────────┘
                                                    │
                                                    │ references
                                                    ▼
┌──────────────────┐      validates      ┌────────────────────────┐
│  HTTP Request    │─────────────────────>│  HTTP Session          │
│  (session_id     │                      │  (Redis)               │
│   Cookie)        │                      │  - uid                 │
└──────────────────┘                      │  - security_token      │
                                          │  - context             │
                                          │  - fingerprint (IP/UA) │
                                          └────────────────────────┘
                                                    │
                                                    │ tracked in
                                                    ▼
                                          ┌────────────────────────┐
                                          │  API Session Model     │
                                          │  (PostgreSQL)          │
                                          │  - session_id          │
                                          │  - user_id             │
                                          │  - security_token      │
                                          │  - ip_address          │
                                          │  - user_agent          │
                                          └────────────────────────┘
```

## Data Flow

### Successful Authentication Flow

```
1. Client sends request:
   Authorization: Bearer <jwt_token>
   Cookie: session_id=<session_id>

2. @require_jwt validates token:
   - Query PostgreSQL oauth.token table
   - Check expiration, revocation
   - Set request.jwt_token

3. @require_session validates session:
   - Query Redis for session:<session_id>
   - Extract security_token from session
   - Decode JWT and verify fingerprint
   - Check IP/User-Agent/Language match
   - Set request.env.uid

4. Request proceeds to controller method
```

### Failed Authentication Flows

```
No Bearer Token:
  @require_jwt → 401 {"error": {"code": "unauthorized", "message": "..."}}
  (stops here, @require_session never called)

Valid Token, No Session:
  @require_jwt → PASS
  @require_session → 401 {"error": "unauthorized", "message": "Session required", "code": 401}

Valid Token, Expired Session:
  @require_jwt → PASS
  @require_session → 401 {"error": "unauthorized", "message": "Session expired", "code": 401}

Valid Token + Session, Fingerprint Mismatch (Different IP):
  @require_jwt → PASS
  @require_session → 401 {"error": {"status": 401, "message": "Session validation failed"}}
  (Security event logged: SESSION HIJACKING DETECTED)
```

## Database Impact Analysis

**PostgreSQL Queries per Request**:
- `@require_jwt`: 1 SELECT on `thedevkitchen.oauth.token` (indexed by access_token)
- `@require_session`: 0 direct queries (uses Redis cache)

**Redis Operations per Request**:
- `@require_session`: 1 GET on key `session:<session_id>`

**Write Operations**:
- None (read-only validation)

**Performance Impact**: Negligible (<5ms additional latency for both decorators combined)

## Migration Requirements

**None** - No database schema changes, no data migrations required.

## Summary

This feature is a **pure configuration change** that applies existing decorators to endpoints. No data model modifications, no migrations, no new tables or fields. All required infrastructure (OAuth tokens, Redis sessions, session fingerprinting) already exists and is operational.
