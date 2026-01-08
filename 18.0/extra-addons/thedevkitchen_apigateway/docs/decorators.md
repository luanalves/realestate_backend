# API Security Decorators

## Overview

The API Gateway provides three essential security decorators for protecting REST API endpoints with multi-layered authentication and company isolation.

## Decorator Chain

**IMPORTANT**: Decorators must be applied in this specific order:

```python
@http.route('/api/v1/endpoint', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt        # 1️⃣ First: Validate JWT token
@require_session    # 2️⃣ Second: Validate user session
@require_company    # 3️⃣ Third: Inject company filtering context
def your_endpoint(self, **kwargs):
    # Your code here
    pass
```

**Rationale**: Each decorator depends on the previous one:
- `@require_jwt` validates the OAuth 2.0 token and sets up request context
- `@require_session` ensures the user has a valid session with fingerprinting
- `@require_company` injects company isolation filters based on the authenticated user

---

## 1. @require_jwt

**Purpose**: Validates OAuth 2.0 JWT tokens from the Authorization header.

**Location**: `thedevkitchen_apigateway/controllers/utils/auth.py`

### Usage

```python
from .utils.auth import require_jwt

@http.route('/api/v1/data', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
def get_data(self, **kwargs):
    user = request.env.user  # Authenticated user
    # Your code
```

### What it does

1. Extracts token from `Authorization: Bearer <token>` header
2. Validates token signature using application's `client_secret`
3. Checks token expiration (`exp` claim)
4. Verifies token is not revoked (blacklist check)
5. Sets up `request.env.user` with the authenticated user
6. Logs successful/failed authentication attempts

### Error Responses

| HTTP Status | Error | Description |
|-------------|-------|-------------|
| 401 | `missing_auth_header` | Authorization header not present |
| 401 | `invalid_token_format` | Header doesn't match "Bearer <token>" format |
| 401 | `invalid_token` | Token signature invalid or malformed |
| 401 | `token_expired` | Token has passed its `exp` timestamp |
| 401 | `token_revoked` | Token was explicitly revoked via `/oauth/revoke` |
| 403 | `insufficient_scope` | Token doesn't have required scopes for this endpoint |

### Example Response (401)

```json
{
  "error": "invalid_token",
  "error_description": "Token signature verification failed",
  "status": 401
}
```

---

## 2. @require_session

**Purpose**: Validates user session and protects against session hijacking via fingerprinting.

**Location**: `thedevkitchen_apigateway/middleware.py`

### Usage

```python
from odoo.addons.thedevkitchen_apigateway.middleware import require_session

@http.route('/api/v1/data', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
def get_data(self, **kwargs):
    # Session is validated
    # User context is guaranteed
```

### What it does

1. Checks if user has an active Odoo session (via session cookie or session_id)
2. Validates session fingerprint (IP + User-Agent + Accept-Language hash)
3. Detects session hijacking attempts (fingerprint mismatch)
4. Ensures `request.env.user` is properly set
5. Logs suspicious session activity

### Fingerprinting

**Security Feature**: Sessions are bound to the client's fingerprint to prevent token theft.

```python
# Fingerprint components
fingerprint = {
    'ip': request.httprequest.remote_addr,
    'user_agent': request.httprequest.headers.get('User-Agent'),
    'language': request.httprequest.headers.get('Accept-Language')
}
# Hashed with SHA-256 and stored in session
```

**Why this matters**: Even if an attacker steals a JWT token, they cannot hijack the session from a different IP/browser without triggering fingerprint mismatch detection.

### Error Responses

| HTTP Status | Error | Description |
|-------------|-------|-------------|
| 401 | `session_required` | No active session found |
| 403 | `session_hijacking_detected` | Session fingerprint doesn't match (suspicious activity) |
| 403 | `session_expired` | Session has timed out |

### Example Response (403)

```json
{
  "error": "session_hijacking_detected",
  "message": "Session fingerprint mismatch - possible security threat",
  "status": 403
}
```

---

## 3. @require_company

**Purpose**: Enforces multi-tenant company isolation by injecting company filtering context into the request.

**Location**: `thedevkitchen_apigateway/middleware.py`

### Usage

```python
from odoo.addons.thedevkitchen_apigateway.middleware import require_company

@http.route('/api/v1/properties', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def list_properties(self, **kwargs):
    # Company context is available
    domain = request.company_domain  # [('company_ids', 'in', [1, 2, 3])]
    
    Property = request.env['real.estate.property'].sudo()
    properties = Property.search(domain, order='name')
    
    return success_response([serialize_property(p) for p in properties])
```

### What it does

1. Checks if user has company assignments (`user.estate_company_ids`)
2. Injects `request.company_domain` for ORM filtering
3. Provides `request.user_company_ids` for validation
4. Bypasses filtering for system administrators (`base.group_system`)
5. Returns 403 if user has no company assignments

### Injected Request Attributes

```python
# Available after @require_company
request.company_domain = [('company_ids', 'in', [1, 2, 3])]
request.user_company_ids = [1, 2, 3]  # User's authorized company IDs
```

### Usage Patterns

#### Pattern 1: List/Search with Filtering

```python
@require_company
def list_entities(self, **kwargs):
    domain = request.company_domain  # Use this for filtering
    entities = request.env['model.name'].sudo().search(domain)
    return success_response([serialize(e) for e in entities])
```

#### Pattern 2: Get by ID with Access Control

```python
@require_company
def get_entity(self, entity_id, **kwargs):
    domain = [('id', '=', entity_id)] + request.company_domain
    entity = request.env['model.name'].sudo().search(domain, limit=1)
    
    if not entity:
        # Returns 404 (not 403) to avoid information disclosure
        return error_response(404, 'Entity not found')
    
    return success_response(serialize(entity))
```

#### Pattern 3: Create with Validation

```python
from ..services.company_validator import CompanyValidator

@require_company
def create_entity(self, **kwargs):
    data = json.loads(request.httprequest.data.decode('utf-8'))
    
    # Ensure company_ids is present (auto-assigns default if missing)
    data = CompanyValidator.ensure_company_ids(data)
    
    # Validate user has access to specified companies
    if 'company_ids' in data:
        company_ids = data['company_ids'][0][2]  # Extract from Many2many tuple
        valid, error = CompanyValidator.validate_company_ids(company_ids)
        if not valid:
            return error_response(403, error)
    
    entity = request.env['model.name'].sudo().create(data)
    return success_response(serialize(entity), status_code=201)
```

#### Pattern 4: Update with Company Lock

```python
@require_company
def update_entity(self, entity_id, **kwargs):
    data = json.loads(request.httprequest.data.decode('utf-8'))
    
    # Block company reassignment via API
    if 'company_ids' in data:
        return error_response(403, 'Cannot change company_ids via API')
    
    # Find entity with company filtering
    domain = [('id', '=', entity_id)] + request.company_domain
    entity = request.env['model.name'].sudo().search(domain, limit=1)
    
    if not entity:
        return error_response(404, 'Entity not found')
    
    entity.write(data)
    return success_response(serialize(entity))
```

### Error Responses

| HTTP Status | Error | Description |
|-------------|-------|-------------|
| 403 | `no_company_access` | User has no company assignments (empty `estate_company_ids`) |
| 403 | `unauthorized_company` | User attempted to access data from unauthorized company |

### Example Response (403)

```json
{
  "error": "no_company_access",
  "message": "User has no company access",
  "status": 403
}
```

### Admin Bypass

System administrators (`base.group_system`) bypass company filtering:

```python
if user.has_group('base.group_system'):
    request.company_domain = []  # No filtering for admins
    return func(*args, **kwargs)
```

**Use case**: Admins need to see all data across all companies for system maintenance.

---

## Integration with CompanyValidator Service

The `CompanyValidator` service complements the `@require_company` decorator for create/update validation.

**Location**: `quicksol_estate/services/company_validator.py`

### Methods

```python
class CompanyValidator:
    @staticmethod
    def validate_company_ids(company_ids):
        """
        Validate user has access to requested companies.
        
        Args:
            company_ids (list): List of company IDs to validate
            
        Returns:
            tuple: (bool, error_message or None)
            
        Example:
            valid, error = CompanyValidator.validate_company_ids([1, 2])
            if not valid:
                return error_response(403, error)
        """
        pass
    
    @staticmethod
    def get_default_company_id():
        """
        Get user's default company ID.
        
        Returns:
            int or None: Default company ID or None if no companies
            
        Example:
            default_id = CompanyValidator.get_default_company_id()
        """
        pass
    
    @staticmethod
    def ensure_company_ids(data):
        """
        Auto-assign default company if company_ids not in data.
        
        Args:
            data (dict): Request data
            
        Returns:
            dict: Modified data with company_ids
            
        Example:
            data = CompanyValidator.ensure_company_ids(data)
        """
        pass
```

---

## Complete Endpoint Example

```python
# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from ..services.company_validator import CompanyValidator

class MyApiController(http.Controller):
    
    @http.route('/api/v1/entities', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_entities(self, **kwargs):
        """List entities filtered by user's companies."""
        try:
            domain = request.company_domain
            entities = request.env['my.model'].sudo().search(domain, order='name')
            
            entities_list = []
            for entity in entities:
                entities_list.append({
                    'id': entity.id,
                    'name': entity.name,
                    'company_ids': entity.company_ids.ids,
                })
            
            return success_response(entities_list)
            
        except Exception as e:
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/entities/<int:entity_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_entity(self, entity_id, **kwargs):
        """Get entity by ID with company filtering."""
        try:
            domain = [('id', '=', entity_id)] + request.company_domain
            entity = request.env['my.model'].sudo().search(domain, limit=1)
            
            if not entity:
                return error_response(404, 'Entity not found')
            
            return success_response({
                'id': entity.id,
                'name': entity.name,
                'company_ids': entity.company_ids.ids,
            })
            
        except Exception as e:
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/entities', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_entity(self, **kwargs):
        """Create entity with company validation."""
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Ensure company_ids
            data = CompanyValidator.ensure_company_ids(data)
            
            # Validate company access
            if 'company_ids' in data:
                company_ids = data['company_ids'][0][2]
                valid, error = CompanyValidator.validate_company_ids(company_ids)
                if not valid:
                    return error_response(403, error)
            
            # Validate required fields
            if 'name' not in data:
                return error_response(400, 'Missing required field: name')
            
            # Create entity
            entity = request.env['my.model'].sudo().create(data)
            
            return success_response({
                'id': entity.id,
                'name': entity.name,
                'company_ids': entity.company_ids.ids,
            }, status_code=201)
            
        except Exception as e:
            return error_response(500, 'Internal server error')
```

---

## Testing Decorators

### Test @require_jwt

```bash
# Valid token
curl -X GET "http://localhost:8069/api/v1/entities" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Missing token (401)
curl -X GET "http://localhost:8069/api/v1/entities"

# Invalid token (401)
curl -X GET "http://localhost:8069/api/v1/entities" \
  -H "Authorization: Bearer invalid_token"
```

### Test @require_session

```bash
# Valid session + token
curl -X GET "http://localhost:8069/api/v1/entities" \
  -H "Authorization: Bearer <valid_token>" \
  -H "Cookie: session_id=<session_id>"

# No session (401)
curl -X GET "http://localhost:8069/api/v1/entities" \
  -H "Authorization: Bearer <valid_token>"
```

### Test @require_company

```bash
# User with companies
curl -X GET "http://localhost:8069/api/v1/entities" \
  -H "Authorization: Bearer <valid_token>" \
  -H "Cookie: session_id=<session_id>"

# User with no companies (403)
# Create a user with empty estate_company_ids and test
```

---

## Security Best Practices

### 1. Always use all three decorators

```python
# ✅ CORRECT
@require_jwt
@require_session
@require_company
def my_endpoint(self, **kwargs):
    pass

# ❌ WRONG - Missing session validation
@require_jwt
@require_company
def my_endpoint(self, **kwargs):
    pass
```

### 2. Never use .sudo() without company filtering

```python
# ✅ CORRECT
domain = request.company_domain
entities = request.env['model'].sudo().search(domain)

# ❌ WRONG - No filtering, data leakage!
entities = request.env['model'].sudo().search([])
```

### 3. Return 404 (not 403) for unauthorized records

```python
# ✅ CORRECT - Doesn't reveal record exists
if not entity:
    return error_response(404, 'Entity not found')

# ❌ WRONG - Information disclosure
if not entity:
    return error_response(403, 'Access denied to this entity')
```

### 4. Block company reassignment

```python
# ✅ CORRECT
if 'company_ids' in data:
    return error_response(403, 'Cannot change company_ids via API')

# ❌ WRONG - Allows company reassignment vulnerability
entity.write(data)  # data may contain malicious company_ids
```

### 5. Document public endpoints

```python
# ✅ CORRECT
@http.route('/api/v1/public/data', auth='none', methods=['GET'])
# public endpoint
def public_data(self, **kwargs):
    pass

# ❌ WRONG - No comment, unclear intent
@http.route('/api/v1/data', auth='none', methods=['GET'])
def data(self, **kwargs):
    pass
```

---

## Troubleshooting

### "Authorization header missing"

**Problem**: Endpoint returns 401 even though token is sent.

**Solution**: Check header format is exactly `Authorization: Bearer <token>` (space after "Bearer").

### "Session fingerprint mismatch"

**Problem**: Endpoint returns 403 session hijacking error.

**Solution**: User's IP or User-Agent changed. This is a security feature. Re-authenticate to create new session.

### "User has no company access"

**Problem**: Endpoint returns 403 with this message.

**Solution**: Assign user to at least one company via `estate_company_ids` field in Odoo.

### "Company filtering not working"

**Problem**: User sees data from other companies.

**Solution**: Check you're using `request.company_domain` in search queries. Verify decorator order is correct.

---

## Related Documentation

- [API Gateway README](../README.md) - Main module documentation
- [OAuth 2.0 Flow](../README.md#autenticação-oauth-20) - Token acquisition
- [CompanyValidator Service](../../quicksol_estate/services/company_validator.py) - Validation helpers
- [ADR-011: Controller Security](../../../../docs/adr/ADR-011-controller-security-authentication-storage.md) - Architecture decision record
