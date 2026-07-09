---
name: postman-collection-manager
description: "Use when creating a new Postman collection from scratch, adding endpoints to the existing collection, bumping its version, or validating ADR-016 compliance (naming/versioning, required variables, headers by endpoint type, OAuth token auto-save scripts, JSON-RPC-free body format). Triggers: postman, collection, postman_collection.json, ADR-016, OAuth token endpoint, session_id header vs body, X-Openerp-Session-Id, criar coleção, adicionar endpoint postman, atualizar versão da coleção."
---

# Postman Collection Manager

Creates, updates, and validates Postman collections following strict ADR-016 rules (Postman Collection Standards, `docs/adr/ADR-016-postman-collection-standards.md`).

## When to Use

- Creating a new Postman collection from scratch
- Adding new endpoints to an existing collection
- Bumping a collection's version
- Validating whether a collection is ADR-016 compliant
- Syncing endpoints from the OpenAPI spec into Postman
- Onboarding developers who need to test the API

## Prerequisites

1. Read `docs/adr/ADR-016-postman-collection-standards.md` in full
2. Know the API structure and available endpoints
3. Have access to the OpenAPI spec if syncing from it

## Mandatory ADR-016 Rules

Before creating or modifying any collection, **always** follow these rules.

### 1. Naming & Versioning (ADR-016 §1)

**File:**
- Format: `{api_name}_v{version}_postman_collection.json`
- Example: `quicksol_api_v1.2_postman_collection.json`
- Location: `docs/postman/`

**Inside the JSON:**
```json
{
  "info": {
    "name": "Quicksol Real Estate API",  // NO version here
    "version": "1.2",                     // version goes here
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  }
}
```

**❌ Never do:**
- `"name": "Quicksol Real Estate API v1.2"` (version in the name)
- File name without version: `quicksol_api_postman_collection.json`
- Patch version: `v1.2.3` (major.minor only)

### 2. Required Variables (ADR-016 §2)

Every collection **MUST** include:

```json
"variable": [
  {"key": "base_url", "value": "http://localhost:8069"},
  {"key": "client_id", "value": "client_xxx"},
  {"key": "client_secret", "value": "secret_yyy"},
  {"key": "access_token", "value": ""},
  {"key": "refresh_token", "value": ""},
  {"key": "session_id", "value": ""},
  {"key": "user_agent", "value": "PostmanRuntime/7.26.8"},
  {"key": "user_email", "value": "admin@example.com"},
  {"key": "user_password", "value": "admin"}
]
```

**🚫 Forbidden:** hardcoding sensitive values (tokens, passwords, secrets).

### 3. Headers by Endpoint Type (ADR-016 §3)

**Common headers (all endpoints except OAuth):**
```json
[
  {"key": "Content-Type", "value": "application/json"},
  {"key": "User-Agent", "value": "{{user_agent}}", "description": "Required for session fingerprint validation"},
  {"key": "Authorization", "value": "Bearer {{access_token}}", "description": "OAuth 2.0 Bearer token"}
]
```

**GET endpoints (`type='http'`)** — also add:
```json
{
  "key": "X-Openerp-Session-Id",
  "value": "{{session_id}}",
  "description": "Session ID for fingerprint validation (REQUIRED for GET)"
}
```

**POST/PUT/PATCH endpoints (`type='json'`)** — session ID goes in the **JSON body**, not the header:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "session_id": "{{session_id}}"
}
```

### 4. OAuth Token Endpoint (ADR-016 §4)

```json
{
  "name": "Get OAuth Token",
  "request": {
    "method": "POST",
    "header": [{"key": "Content-Type", "value": "application/json"}],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"client_id\": \"{{client_id}}\",\n  \"client_secret\": \"{{client_secret}}\",\n  \"grant_type\": \"client_credentials\"\n}"
    },
    "url": "{{base_url}}/api/v1/auth/token"
  },
  "event": [{
    "listen": "test",
    "script": {
      "exec": [
        "const jsonData = pm.response.json();",
        "if (jsonData && jsonData.access_token) {",
        "    pm.environment.set('access_token', jsonData.access_token);",
        "    console.log('✅ Access token saved to environment');",
        "    if (jsonData.refresh_token) {",
        "        pm.environment.set('refresh_token', jsonData.refresh_token);",
        "        console.log('✅ Refresh token saved to environment');",
        "    }",
        "}"
      ]
    }
  }]
}
```

**⚠️ IMPORTANT:** OAuth endpoints do **NOT** use JSON-RPC. Send plain JSON.

### 5. User Login Endpoint (ADR-016 §5)

```json
{
  "name": "User Login",
  "request": {
    "method": "POST",
    "header": [/* common headers */],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"email\": \"{{user_email}}\",\n  \"password\": \"{{user_password}}\"\n}"
    },
    "url": "{{base_url}}/api/v1/users/login"
  },
  "event": [{
    "listen": "test",
    "script": {
      "exec": [
        "const jsonData = pm.response.json();",
        "if (jsonData && jsonData.result && jsonData.result.session_id) {",
        "    pm.environment.set('session_id', jsonData.result.session_id);",
        "    console.log('✅ Session ID saved to environment');",
        "}"
      ]
    }
  }]
}
```

### 6. Folder Structure (ADR-016 §6)

```
Collection Root
├── 1. Authentication (OAuth Token, Refresh Token)
├── 2. User Management (Login, Logout, Get Me)
├── 3. Agents (CRUD endpoints)
├── 4. Properties (CRUD endpoints)
├── 5. Assignments (Assignment endpoints)
├── 6. Leads (Lead management)
└── [other domain folders]
```

### 7. Endpoint Descriptions (ADR-016 §7)

Every endpoint description **MUST** include:

```markdown
**Authentication:** Bearer Token + Session ID required
**Multi-tenancy:** Company isolation active (@require_company)
**Fingerprint validation:** Active (IP + User-Agent + Accept-Language)

**IMPORTANT:** For GET requests (type='http'), session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in request body.

[Endpoint-specific functional description]
```

### 8. Golden Rules (ADR-016 §8)

1. **🚫 NEVER** use a JSON-RPC wrapper — send plain JSON in the body
2. **🚫 NEVER** send `session_id` in the body of a GET — it will be ignored
3. **✅ ALWAYS** use `{{...}}` variables instead of hardcoded values
4. **✅ ALWAYS** include a consistent User-Agent (fingerprint validation)
5. **✅ ALWAYS** version collections on structural changes
6. **✅ ALWAYS** add test scripts to auto-populate tokens
7. **✅ ALWAYS** save `refresh_token` to a variable (used by refresh endpoints)
8. **✅ ALWAYS** document the auth type in the description

---

## Critical Rule: New Feature → Update the Main Collection

**NEVER create a separate collection file per feature** (e.g. `feature013_proposals_v1.0_postman_collection.json`).

When implementing endpoints for a new feature:
1. **Find the latest version** of the main collection in `docs/postman/` (e.g. `quicksol_api_v1.23_postman_collection.json`)
2. **Add the new endpoints** as a new numbered folder (e.g. `21. Property Proposals`)
3. **Bump the minor version** (`1.23` → `1.24`)
4. **Add a Changelog entry** in `info.description`
5. **Add any new variables** needed (e.g. `proposal_id`)
6. **Save as a new file** with the updated version
7. **Delete the old file** (only keep the latest version)

**Finding the latest version:**
```bash
ls docs/postman/quicksol_api_v*.json | sort -V | tail -1
```

**Python script to merge:**
```python
import json

# 1. Load the latest version
with open('quicksol_api_v1.23_postman_collection.json', encoding='utf-8') as f:
    collection = json.loads(f.read(), strict=False)  # strict=False for control chars

# 2. Build the new feature folder
new_folder = {
    "name": "21. Property Proposals",
    "description": "...",
    "item": [/* endpoints */]
}

# 3. Add folder, bump version, add changelog
collection['item'].append(new_folder)
collection['info']['version'] = '1.24'
collection['info']['description'] += '\n\n## Changelog v1.24\n- **NEW**: ...'

# 4. Add new variables
collection['variable'].append({'key': 'proposal_id', 'value': '', 'type': 'string'})

# 5. Save with the new version
with open('quicksol_api_v1.24_postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)
```

> **Note:** `json.loads(..., strict=False)` is required because some files may contain control characters in description fields. Always use this option when reading existing collections.

---

## Process: Create a New Collection

1. **Read ADR-016 in full**: `docs/adr/ADR-016-postman-collection-standards.md`
2. **Determine the version**: Major (v2.0) = breaking API changes; Minor (v1.1) = new endpoints/fixes; first collection = v1.0
3. **Create the base structure:**

```json
{
  "info": {
    "_postman_id": "[generate a unique UUID]",
    "name": "Quicksol Real Estate API",
    "description": "REST API for a multi-tenant real estate system with OAuth 2.0 and dual authentication",
    "version": "1.0",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [],
  "variable": []
}
```

4. Add the required variables (§2)
5. Create the standard folders (§6): 1. Authentication, 2. User Management, 3-6. domain folders
6. Add essential endpoints: OAuth Token (with test script), Refresh Token, User Login (with test script), User Logout, Get Current User (`/api/v1/me`)
7. Save as `docs/postman/quicksol_api_v1.0_postman_collection.json`
8. Validate: `info.version` present? Name without version? All required variables? Standardized headers? Test scripts on the right endpoints?
9. Commit:
   ```bash
   git add docs/postman/quicksol_api_v1.0_postman_collection.json
   git commit -m "feat: create Postman collection v1.0 (ADR-016 compliant)"
   ```

## Process: Add a GET Endpoint

1. Identify the correct folder (e.g. "3. Agents")
2. Create the request:

```json
{
  "name": "List Agents",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "{{user_agent}}"},
      {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}
    ],
    "url": {
      "raw": "{{base_url}}/api/v1/agents?limit=10&offset=0",
      "host": ["{{base_url}}"],
      "path": ["api", "v1", "agents"],
      "query": [
        {"key": "limit", "value": "10"},
        {"key": "offset", "value": "0"}
      ]
    },
    "description": "**Authentication:** Bearer Token + Session ID required\n**Multi-tenancy:** Company isolation active\n\n**IMPORTANT:** For GET requests, session_id MUST be sent via header 'X-Openerp-Session-Id', NOT in body.\n\nReturns paginated list of agents in the current company."
  }
}
```

3. Add it to the correct folder in the `item` array
4. **Critical checks for GET:**
   - [ ] `X-Openerp-Session-Id` header present?
   - [ ] `session_id` NOT in the body?
   - [ ] Description warns about sending via header?

## Process: Add a POST Endpoint

1. Identify the correct folder
2. Create the request:

```json
{
  "name": "Create Agent",
  "request": {
    "method": "POST",
    "header": [
      {"key": "Content-Type", "value": "application/json"},
      {"key": "Authorization", "value": "Bearer {{access_token}}"},
      {"key": "User-Agent", "value": "{{user_agent}}"}
    ],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"name\": \"João Silva\",\n  \"email\": \"joao@example.com\",\n  \"creci\": \"F123456\",\n  \"session_id\": \"{{session_id}}\"\n}"
    },
    "url": {
      "raw": "{{base_url}}/api/v1/agents",
      "host": ["{{base_url}}"],
      "path": ["api", "v1", "agents"]
    },
    "description": "**Authentication:** Bearer Token + Session ID required\n**Multi-tenancy:** Company isolation active\n\n**IMPORTANT:** Business endpoints do NOT use JSON-RPC format. Send JSON directly in body.\n\nCreates a new agent in the current company."
  }
}
```

3. **Critical checks for POST:**
   - [ ] `session_id` is in the **JSON body**?
   - [ ] `X-Openerp-Session-Id` header NOT present?
   - [ ] Body is plain JSON (no JSON-RPC wrapper)?
   - [ ] Description warns about NOT using JSON-RPC?

## Process: Bump the Version

1. Determine the change type: breaking change → major (1.0 → 2.0); new endpoints → minor (1.0 → 1.1)
2. Load the current collection
3. Update `info.version` (e.g. `"1.1"`)
4. Generate the new file name (e.g. `quicksol_api_v1.1_postman_collection.json`)
5. Save with the new name
6. Commit and remove the old file:
   ```bash
   git rm docs/postman/quicksol_api_v1.0_postman_collection.json
   git add docs/postman/quicksol_api_v1.1_postman_collection.json
   git commit -m "chore: update Postman collection to v1.1"
   ```

## Process: Validate a Collection

**Validation checklist:**

1. **File & Metadata**
   - [ ] File name: `{name}_v{version}_postman_collection.json`
   - [ ] `info.version` present
   - [ ] `info.name` without version
   - [ ] Schema: `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`

2. **Variables (ADR-016 §2)**
   - [ ] base_url, client_id, client_secret, access_token, refresh_token, session_id, user_agent, user_email, user_password

3. **OAuth Endpoints**
   - [ ] Get OAuth Token with test script (saves access_token + refresh_token)
   - [ ] Refresh Token endpoint present

4. **User Endpoints**
   - [ ] User Login with test script (saves session_id)
   - [ ] Correct headers (Authorization + User-Agent)

5. **GET Endpoints**
   - [ ] `X-Openerp-Session-Id` header present
   - [ ] `session_id` NOT in body
   - [ ] Description warns about header usage

6. **POST/PUT/PATCH Endpoints**
   - [ ] `session_id` in JSON body
   - [ ] `X-Openerp-Session-Id` header NOT present
   - [ ] Plain JSON (no JSON-RPC wrapper)

7. **Descriptions**
   - [ ] Auth type documented
   - [ ] Multi-tenancy documented
   - [ ] Important warnings present

Fix any failing item before committing.

## Common Pitfalls

### ❌ Version in the collection name
```json
// WRONG
"name": "Quicksol Real Estate API v1.1"

// CORRECT
"name": "Quicksol Real Estate API",
"version": "1.1"
```

### ❌ Session ID in a GET body
```json
// WRONG — GET does not process a body
{
  "method": "GET",
  "body": {"raw": "{\"session_id\": \"...\"}"}
}

// CORRECT — Session ID via header
{
  "method": "GET",
  "header": [
    {"key": "X-Openerp-Session-Id", "value": "{{session_id}}"}
  ]
}
```

### ❌ Using JSON-RPC
```json
// WRONG — JSON-RPC wrapper
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {"name": "John"}
}

// CORRECT — plain JSON
{
  "name": "John",
  "session_id": "{{session_id}}"
}
```

### ❌ Not saving the refresh token
```javascript
// WRONG — only saves access_token
pm.environment.set('access_token', jsonData.access_token);

// CORRECT — saves both
pm.environment.set('access_token', jsonData.access_token);
if (jsonData.refresh_token) {
    pm.environment.set('refresh_token', jsonData.refresh_token);
}
```

### ❌ Creating a separate file per feature
```
// WRONG — isolated feature file
docs/postman/feature013_property_proposals_v1.0_postman_collection.json

// CORRECT — add to the main collection, bump minor version
docs/postman/quicksol_api_v1.24_postman_collection.json  // was v1.23
```

One new feature = one new folder in the main collection + a minor version bump.

### ❌ Hardcoded headers
```json
// WRONG
{"key": "User-Agent", "value": "PostmanRuntime/7.26.8"}

// CORRECT
{"key": "User-Agent", "value": "{{user_agent}}"}
```

## Related Documentation

- `docs/adr/ADR-016-postman-collection-standards.md` — full rules and rationale
- `docs/adr/ADR-005-openapi-30-swagger-documentation.md` — complementary docs — see the `swagger-updater` skill
- `docs/adr/ADR-009-headless-authentication-user-context.md` — dual-auth context
- `docs/adr/ADR-011-controller-security-authentication-storage.md` — `@require_jwt`/`@require_session` decorators
- [Postman Collection Format v2.1.0](https://schema.getpostman.com/json/collection/v2.1.0/collection.json) — official schema

## Related Skills

- `swagger-updater` — keep the OpenAPI spec and this collection in sync
- `development-best-practices` — naming/security conventions for the endpoints being documented

## Maintenance

- Update whenever new endpoints are created, auth changes, or the API has breaking changes
- Validate in PRs: confirm the collection was updated alongside endpoint changes
- Versioning follows Git Flow (ADR-006)
- Keep OpenAPI and Postman in sync — collections should reflect the OpenAPI spec
