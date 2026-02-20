# Research: User Onboarding & Password Management

**Feature**: 009-user-onboarding-password-management
**Date**: 2026-02-16
**Status**: Complete

---

## R1: Missing Validator Functions (`validate_document`, `normalize_document`)

**Context**: The spec references `validators.validate_document()` and `validators.normalize_document()` for CPF/CNPJ validation on the portal profile. The constitution lists these functions in `utils/validators.py`. However, codebase analysis reveals they do NOT exist in `quicksol_estate/utils/validators.py`.

**Finding**: `tenant_api.py` (line 222-223) imports and calls `validators.normalize_document()` and `validators.validate_document()` at runtime via `from ..utils import validators`. These functions are referenced but NOT defined — this appears to be a **pre-existing bug** or the functions exist in a different location not found by search.

**Decision**: The new module `thedevkitchen_user_onboarding` will implement its own document validation in `services/invite_service.py`:
- For non-portal profiles: use `validate_docbr.CPF` directly (same pattern as `owner_api.py` line 45, `agent.py` line 296, `res_users.py` line 87)
- For portal profile: use `validate_docbr.CPF` + custom CNPJ validation (same algorithm as `quicksol_estate/utils/validators.py:validate_cnpj()`)
- If `validate_document`/`normalize_document` are found at implementation time, reuse them

**Rationale**: Avoid depending on potentially broken references. The `validate_docbr` library is already a dependency and provides reliable CPF validation. CNPJ validation logic already exists in `validators.py:validate_cnpj()`.

**Alternatives considered**:
- Add missing functions to `quicksol_estate/utils/validators.py` → rejected (out of scope, modifying another module)
- Import `validate_cnpj` from `quicksol_estate` → acceptable fallback, but creates tight coupling

---

## R2: New Module vs. Extending Existing Module

**Context**: Should onboarding logic live in `thedevkitchen_apigateway`, `quicksol_estate`, or a new module?

**Decision**: New module `thedevkitchen_user_onboarding`

**Rationale**:
- `thedevkitchen_apigateway` is a generic OAuth/auth gateway — onboarding is domain-specific (RBAC profiles, tenant dual record)
- `quicksol_estate` is already large (30+ model files, 10+ controllers) — adding onboarding increases complexity
- New module follows single-responsibility principle and ADR-004 naming (`thedevkitchen_` prefix)
- Module depends on both: `thedevkitchen_apigateway` (auth decorators) and `quicksol_estate` (groups, tenant model)

**Alternatives considered**:
- Extend `thedevkitchen_apigateway` → rejected (domain-specific logic doesn't belong in generic gateway)
- Extend `quicksol_estate` → rejected (module already large, violates SRP)
- Add to `quicksol_estate/controllers/` only → rejected (need models + services + views + security)

---

## R3: `mail.template` Best Practices in Odoo 18.0

**Context**: No `mail.template` usage exists in the codebase. This is a new pattern for Feature 009.

**Decision**: Use `mail.template` with XML data records and `send_mail()` API.

**Best Practices Found**:
1. Define templates in `data/email_templates.xml` with `noupdate="1"` (don't overwrite on module update)
2. Template body uses `${object.field}` Jinja-like syntax for dynamic variables
3. Render via `template.send_mail(record_id, force_send=False)` — async by default (queued in Odoo mail queue)
4. Link `mail.template` to model via `model_id` (e.g., `model_thedevkitchen_password_token`)
5. For transactional emails (invite/reset), use `force_send=True` for immediate delivery (or `force_send=False` + cron)
6. `ir.mail_server` must be configured (SMTP outbound) — prerequisite
7. `email_from` defaults to company email or can be set explicitly
8. Template supports `lang` field for i18n (future multilingual support)

**Implementation pattern**:
```xml
<record id="email_template_invite" model="mail.template">
    <field name="name">User Invite - Password Creation</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="email_from">${(object.company_id.email or 'noreply@example.com')}</field>
    <field name="email_to">${object.email}</field>
    <field name="subject">Convite para criar sua senha - ${object.company_id.name}</field>
    <field name="body_html" type="html">...</field>
</record>
```

**Note**: Template linked to `res.users` model (not to `password_token`) since the email recipient is the user. Token data passed via `render_template()` context or computed in controller before `send_mail()`.

**Alternatives considered**:
- Custom SMTP sending (smtplib) → rejected (Odoo already has robust mail infrastructure)
- `mail.mail` direct creation → rejected (no template reusability, no i18n support)

---

## R4: Token Hashing — SHA-256 Implementation

**Context**: Spec requires SHA-256 hash of UUID v4 tokens stored in database, raw token only in email URLs.

**Decision**: Use Python stdlib `hashlib.sha256` + `uuid.uuid4`.

**Implementation pattern**:
```python
import uuid
import hashlib

def generate_token():
    raw_token = uuid.uuid4().hex  # 32 hex chars
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # 64 hex chars
    return raw_token, token_hash

def verify_token(raw_token, stored_hash):
    computed_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return computed_hash == stored_hash
```

**Rationale**: SHA-256 is pre-image resistant — even if DB is compromised, attacker cannot recover raw tokens from hashes. This follows the same principle used for OAuth tokens in `thedevkitchen_apigateway` (see `oauth_token.py` which stores SHA-256 hashes).

**Alternatives considered**:
- bcrypt → rejected (too slow for token verification, designed for passwords not tokens)
- HMAC-SHA256 with secret key → rejected (unnecessary complexity for tokens, SHA-256 sufficient for pre-image resistance)
- Plain UUID storage → rejected (security risk if DB compromised)

---

## R5: Rate Limiting Strategy for Public Endpoints

**Context**: Spec requires rate limiting on `forgot-password` (3 requests/email/hour). No rate limiting exists in the codebase today.

**Decision**: Implement simple in-memory rate limiting using Redis (already available for sessions).

**Implementation pattern**:
```python
# In password_controller.py or a rate_limit service
def check_rate_limit(email, limit=3, window_seconds=3600):
    redis_client = get_redis_client()  # From Odoo Redis config
    key = f"rate_limit:forgot_password:{email}"
    current = redis_client.get(key)
    if current and int(current) >= limit:
        return False  # Rate limited
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    pipe.execute()
    return True
```

**Rationale**: Redis is already available (DB index 1, configured in `odoo.conf`). Simple counter with TTL provides adequate protection. No need for complex middleware.

**Alternatives considered**:
- Odoo `ir.config_parameter` counter → rejected (DB write for every request, performance impact)
- Nginx rate limiting → rejected (requires infrastructure changes outside application scope)
- Token bucket algorithm → rejected (over-engineering for 3 req/hour limit)
- Decorator-based middleware → considered for future ADR-023, but simple inline check sufficient for MVP

---

## R6: Dual Record Creation — Portal Profile Atomicity

**Context**: When inviting a `portal` profile, must create `res.users` + `real.estate.tenant` atomically.

**Decision**: Use Odoo ORM within a single HTTP request (implicit transaction). On any failure, Odoo's transaction management rolls back automatically.

**Implementation pattern**:
```python
# In invite_service.py
def create_portal_user(self, data, company_id):
    # Step 1: Create res.users with portal group
    user_vals = {
        'name': data['name'],
        'login': data['email'],
        'email': data['email'],
        'password': False,
        'signup_pending': True,
        'groups_id': [(6, 0, [portal_group_id])],
    }
    user = request.env['res.users'].sudo().create(user_vals)
    
    # Step 2: Create real.estate.tenant linked via partner_id
    tenant_vals = {
        'name': data['name'],
        'email': data['email'],
        'document': data['document'],
        'phone': data['phone'],
        'birthdate': data['birthdate'],
        'partner_id': user.partner_id.id,  # Link to res.partner created by res.users
        'company_ids': [(4, company_id)],
    }
    tenant = request.env['real.estate.tenant'].sudo().create(tenant_vals)
    
    return user, tenant
```

**Rationale**: Odoo HTTP controllers run within a DB transaction that commits only on successful response. If `tenant.create()` fails, the `user.create()` is also rolled back. No explicit transaction management needed.

**Key detail**: `res.users.create()` automatically creates a `res.partner` record. The `real.estate.tenant.partner_id` field links to this auto-created partner, establishing the user↔tenant relationship.

**Alternatives considered**:
- Explicit `cr.savepoint()` → rejected (unnecessary, Odoo already handles transaction boundaries)
- Two-step creation with compensation → rejected (complex, error-prone, Odoo transactions suffice)

---

## R7: Session Invalidation After Password Reset

**Context**: Spec requires all active sessions to be invalidated after password reset (FR4.7).

**Decision**: Use Redis to delete all session keys for the user.

**Implementation pattern**:
```python
# In password_service.py
def invalidate_user_sessions(self, user_id):
    # Option A: Query api_session model and delete
    sessions = request.env['thedevkitchen.api.session'].sudo().search([
        ('user_id', '=', user_id),
        ('active', '=', True),
    ])
    sessions.write({'active': False})
    
    # Option B: Also clear Redis session keys (belt and suspenders)
    # Redis keys follow pattern: session:<session_id>
    # Use thedevkitchen_apigateway's session management
```

**Finding**: `thedevkitchen_apigateway` has `api_session.py` model and `session_validator.py` service. Sessions are stored in both PostgreSQL (`thedevkitchen.api.session`) and Redis. Deactivating in PostgreSQL and letting Redis TTL expire is sufficient for security (session validation checks `active` flag).

**Rationale**: Mark sessions as inactive in PostgreSQL immediately. The `session_validator.py` will reject these sessions on next validation attempt. Redis entries expire naturally via TTL.

**Alternatives considered**:
- Redis SCAN + DEL for user sessions → rejected (Redis session keys may not include user_id in key name, would require pattern matching)
- Force password change on next login → rejected (not in spec, different UX pattern)

---

## R8: Module Placement Decision — Controllers Split

**Context**: 5 endpoints need to be organized into controllers.

**Decision**: Two controller files:
- `invite_controller.py` — handles `POST /api/v1/users/invite` and `POST /api/v1/users/{id}/resend-invite` (both authenticated, user-management focused)
- `password_controller.py` — handles `POST /api/v1/auth/set-password`, `POST /api/v1/auth/forgot-password`, `POST /api/v1/auth/reset-password` (all public, auth-focused)

**Rationale**: Split by authentication pattern and domain concern. Invite operations are authenticated user management. Password operations are public auth flows. This matches Odoo controller file naming convention used in other modules (e.g., `auth_controller.py` vs `me_controller.py` in apigateway).

**Alternatives considered**:
- Single `onboarding_controller.py` → rejected (violates SRP, mixes auth patterns)
- Three files (invite, password_set, password_reset) → rejected (over-splitting, password operations share validation logic)

---

## R9: Existing `res_users.py` Extension Pattern

**Context**: Need to add `signup_pending` field to `res.users`. `quicksol_estate` already extends `res.users` in `models/res_users.py`.

**Decision**: Create a separate `res_users.py` in the new module that also inherits `res.users`. Odoo supports multiple `_inherit` declarations across modules — fields are merged.

**Implementation pattern**:
```python
# thedevkitchen_user_onboarding/models/res_users.py
from odoo import fields, models

class ResUsersOnboarding(models.Model):
    _inherit = 'res.users'
    
    signup_pending = fields.Boolean(
        string='Signup Pending',
        default=False,
        help='Indicates user is waiting to create their password via invite link'
    )
```

**Finding**: `quicksol_estate/models/res_users.py` already extends `res.users` with fields like `cpf`, `estate_company_ids`, `company_role_ids`. Both extensions coexist via Odoo's `_inherit` mechanism.

**Rationale**: Standard Odoo pattern. No conflicts expected since `signup_pending` is a new field name.

---

## R10: Frontend URL Configuration

**Context**: Email templates need `frontend_base_url` for constructing links like `{base_url}/set-password?token={raw_token}`.

**Decision**: Store in `thedevkitchen.email.link.settings` Singleton model. Default value `http://localhost:3000` (Next.js dev server).

**Implementation**: The `invite_service.py` reads `frontend_base_url` from settings at invite time and passes it to the email template context.

**Rationale**: Configurable without redeploy. Accessible from Technical menu. Single source of truth for all email link generation.

---

## R11: Authorization Matrix Implementation

**Context**: Spec defines which profiles can invite which other profiles. Need to enforce at controller level.

**Decision**: Implement as a Python dict in `invite_service.py`:

```python
INVITE_AUTHORIZATION = {
    'group_real_estate_owner': ['owner', 'director', 'manager', 'agent', 'prospector', 'receptionist', 'financial', 'legal', 'tenant', 'property_owner'],
    'group_real_estate_director': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],  # Inherits manager
    'group_real_estate_manager': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
    'group_real_estate_agent': ['property_owner', 'tenant'],
}

PROFILE_TO_GROUP = {
    'owner': 'quicksol_estate.group_real_estate_owner',
    'director': 'quicksol_estate.group_real_estate_director',
    'manager': 'quicksol_estate.group_real_estate_manager',
    'agent': 'quicksol_estate.group_real_estate_agent',
    'prospector': 'quicksol_estate.group_real_estate_prospector',
    'receptionist': 'quicksol_estate.group_real_estate_receptionist',
    'financial': 'quicksol_estate.group_real_estate_financial',
    'legal': 'quicksol_estate.group_real_estate_legal',
    'portal': 'quicksol_estate.group_real_estate_portal_user',
}
```

**Rationale**: Static dict is simple, testable (unit tests on authorization matrix), and matches spec exactly. No need for a dynamic configuration model for this.

**Finding**: Director inherits Manager (confirmed in `groups.xml`: `<field name="implied_ids" eval="[(4, ref('group_real_estate_manager'))]"/>`). So Director can do everything Manager can, plus more if needed. Currently, Director has the same invite permissions as Manager per spec.

---

## R12: Cleanup Cron for Expired Tokens

**Context**: NFR2 mentions "Cron job para limpeza de tokens expirados (diário)".

**Decision**: Create an `ir.cron` record in XML data that calls a method on `thedevkitchen.password.token` to mark/delete expired tokens daily.

```python
# In password_token.py
@api.model
def _cron_cleanup_expired_tokens(self):
    expired = self.search([
        ('status', '=', 'pending'),
        ('expires_at', '<', fields.Datetime.now()),
    ])
    expired.write({'status': 'expired'})
```

**Rationale**: Prevents unbounded growth of pending tokens. Standard Odoo cron pattern. Daily frequency sufficient since token expiration is also checked at validation time.
