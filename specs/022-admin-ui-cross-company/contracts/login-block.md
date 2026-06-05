# Behavior Contract: POST /api/v1/users/login — System Admin Block

**Feature**: 022-admin-ui-cross-company  
**Date**: 2026-06-03  
**Endpoint**: `POST /api/v1/users/login`  
**Change type**: Behavior change (new early-exit guard, not a new endpoint)

---

## Overview

This contract documents the **new rejection behavior** added to the existing login endpoint for System Admin users (`base.group_system`). No other behavior changes are made to this endpoint.

---

## Endpoint

```
POST /api/v1/users/login
```

### Request (unchanged)

```json
{
  "email": "admin@example.com",
  "password": "s3cr3t"
}
```

### Response — New: System Admin Rejected (HTTP 401)

Triggered when credentials are valid but the authenticated user belongs to `base.group_system`.

```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": {
    "status": 401,
    "message": "Invalid credentials"
  }
}
```

> **Anti-enumeration**: The response body is **identical** to a failed-credential response. The HTTP status is also identical (401). No information is leaked about whether the account exists, is active, or is blocked due to channel policy.

### Response — Existing: Invalid Credentials (HTTP 401, unchanged)

```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": {
    "status": 401,
    "message": "Invalid credentials"
  }
}
```

### Response — Existing: Successful Login (HTTP 200, unchanged)

Not affected. Business users (`Owner`, `Manager`, `Agent`, etc.) continue to authenticate normally.

---

## Evaluation Order (guard placement in controller)

```
1. Parse request body (email, password)
2. Call request.session.authenticate()             ← validates credentials
3. Check uid (if invalid → 401 Invalid credentials)
4. Load user = res.users.browse(uid)
5. Check user.active (if false → 403 User inactive)
6. ★ NEW: Check user.has_group('base.group_system')
      → if true: AuditLogger.log_failed_login(..., 'Admin API login blocked')
                 return 401 {"error": {"status": 401, "message": "Invalid credentials"}}
7. Invalidate old sessions
8. Create new session token
9. Return 200 with session data
```

---

## Side Effects

| Side Effect | Condition | Notes |
|---|---|---|
| Audit log entry | Always when System Admin blocked | `AuditLogger.log_failed_login(ip, email, 'Admin API login blocked')` |
| No session created | Always when System Admin blocked | Guard fires before session creation |
| No token issued | Always when System Admin blocked | Guard fires before token creation |
| No session invalidation | Always when System Admin blocked | Guard fires before old-session cleanup |

---

## Security Properties

| Property | Value |
|---|---|
| HTTP status | 401 (identical to bad-credential response) |
| Response body | Identical to bad-credential response (`"Invalid credentials"`) |
| Audit log | Yes — internal reason `'Admin API login blocked'` (not exposed in response) |
| Enumeration resistance | ✅ Attacker cannot distinguish "bad password" from "admin blocked" |
| ADR compliance | ADR-008 (anti-enumeration), ADR-009 (headless API for business users only) |

---

## Test Assertions

```bash
# Must return 401
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer <app_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "correct_password"}')
[ "$HTTP_STATUS" = "401" ]

# Must NOT return a session_id or access_token
BODY=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer <app_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "correct_password"}')
echo "$BODY" | jq -e '.session_id // .access_token // .data' | grep -q null

# Business user must still authenticate normally
HTTP_STATUS_BIZ=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer <app_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@tenant.com", "password": "correct_password"}')
[ "$HTTP_STATUS_BIZ" = "200" ]
```
