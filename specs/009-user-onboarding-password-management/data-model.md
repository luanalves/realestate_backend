# Data Model: User Onboarding & Password Management

**Feature**: 009-user-onboarding-password-management
**Date**: 2026-02-16
**ADR References**: ADR-004 (naming), ADR-008 (multi-tenancy), ADR-015 (soft delete)

---

## Entity Relationship Diagram

```
┌─────────────────────────────┐
│       res.users             │
│ (Extended — Odoo core)      │
├─────────────────────────────┤
│ + signup_pending: Boolean   │
│   (default=False)           │
│ + cpf: Char (existing)      │
│ + estate_company_ids (exist)│
└───────────┬─────────────────┘
            │ 1
            │
            │ N
┌───────────┴─────────────────┐        ┌──────────────────────────────────┐
│ thedevkitchen.password.token│        │ thedevkitchen.email.link.settings│
├─────────────────────────────┤        │ (Singleton)                      │
│ user_id: FK → res.users     │        ├──────────────────────────────────┤
│ token: Char(64) SHA-256     │        │ invite_link_ttl_hours: Integer   │
│ token_type: Selection       │        │ reset_link_ttl_hours: Integer    │
│ status: Selection           │        │ frontend_base_url: Char          │
│ expires_at: Datetime        │        │ max_resend_attempts: Integer     │
│ used_at: Datetime           │        │ rate_limit_forgot_per_hour: Int  │
│ ip_address: Char(45)        │        └──────────────────────────────────┘
│ user_agent: Char(255)       │
│ company_id: FK → company    │
│ created_by: FK → res.users  │
│ active: Boolean             │
└─────────────────────────────┘

            ┌─────────────────┐
            │ res.users       │
            │ (portal group)  │
            └────────┬────────┘
                     │ partner_id
                     │ (auto-created)
            ┌────────┴────────┐
            │   res.partner   │
            └────────┬────────┘
                     │
            ┌────────┴────────┐
            │ real.estate.    │
            │ tenant          │
            │ (partner_id FK) │
            └─────────────────┘
```

---

## Entity 1: `thedevkitchen.password.token`

**Table**: `thedevkitchen_password_token` (auto-generated)
**Module**: `thedevkitchen_user_onboarding`
**Purpose**: Stores hashed tokens for invite and password reset flows

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | Integer | auto | auto | PK | Primary key |
| `user_id` | Many2one(`res.users`) | ✅ | — | FK, `ondelete='cascade'`, index | User associated with this token |
| `token` | Char(64) | ✅ | — | unique, index | SHA-256 hash of the raw token (never stores raw token) |
| `token_type` | Selection | ✅ | — | `[('invite', 'Invite'), ('reset', 'Reset')]` | Type of token |
| `status` | Selection | ✅ | `'pending'` | `[('pending', 'Pending'), ('used', 'Used'), ('expired', 'Expired'), ('invalidated', 'Invalidated')]` | Token lifecycle status |
| `expires_at` | Datetime | ✅ | — | Must be future | Expiration timestamp |
| `used_at` | Datetime | ❌ | — | — | When token was consumed |
| `ip_address` | Char(45) | ❌ | — | — | IP address used for token consumption (audit) |
| `user_agent` | Char(255) | ❌ | — | — | Browser User-Agent at consumption (audit) |
| `company_id` | Many2one(`thedevkitchen.estate.company`) | ❌ | — | FK, index | Company context for multi-tenancy |
| `created_by` | Many2one(`res.users`) | ❌ | — | FK | Who created this invite (audit trail) |
| `active` | Boolean | ✅ | `True` | — | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | auto | — | Record creation timestamp |
| `write_date` | Datetime | auto | auto | — | Last modification timestamp |

### SQL Constraints

```python
_sql_constraints = [
    ('token_unique', 'unique(token)', 'Token must be unique'),
]
```

### Python Constraints

```python
@api.constrains('expires_at')
def _check_expires_at(self):
    for record in self:
        if record.expires_at and record.expires_at <= fields.Datetime.now():
            raise ValidationError('Expiration date must be in the future')
```

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `token_unique` | `token` | Fast lookup by token hash |
| `user_id` | `user_id` | FK index (auto) |
| Composite | `(user_id, token_type, status)` | Fast invalidation of previous tokens |
| Single | `expires_at` | Cron cleanup of expired tokens |

### State Machine

```
                  ┌──────────┐
     create  ───▶ │ pending  │
                  └────┬─────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │   used   │ │ expired  │ │ invalidated  │
    └──────────┘ └──────────┘ └──────────────┘
    (set/reset   (cron or     (new token for
     password)    on check)    same user)
```

**Transitions**:
- `pending → used`: User successfully sets/resets password with this token
- `pending → expired`: Token TTL exceeded (checked at validation time or by cron)
- `pending → invalidated`: New token generated for same user+type (previous tokens invalidated)

### Record Rules

```xml
<record id="rule_password_token_company" model="ir.rule">
    <field name="name">Password Token: Company Isolation</field>
    <field name="model_id" ref="model_thedevkitchen_password_token"/>
    <field name="domain_force">[('company_id', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_real_estate_user'))]"/>
</record>
```

---

## Entity 2: `thedevkitchen.email.link.settings` (Singleton)

**Table**: `thedevkitchen_email_link_settings` (auto-generated)
**Module**: `thedevkitchen_user_onboarding`
**Purpose**: Configurable settings for email link validity and rate limiting

### Fields

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | Integer | auto | auto | PK | Primary key |
| `name` | Char(100) | ✅ | `'Email Link Configuration'` | — | Configuration name |
| `invite_link_ttl_hours` | Integer | ✅ | `24` | `> 0, <= 720` | Invite link validity in hours |
| `reset_link_ttl_hours` | Integer | ✅ | `24` | `> 0, <= 720` | Reset link validity in hours |
| `frontend_base_url` | Char(255) | ✅ | `'http://localhost:3000'` | — | Frontend base URL for email links |
| `max_resend_attempts` | Integer | ✅ | `5` | — | Max invite resend attempts per user |
| `rate_limit_forgot_per_hour` | Integer | ✅ | `3` | — | Forgot-password rate limit per email/hour |

### Python Constraints

```python
@api.constrains('invite_link_ttl_hours', 'reset_link_ttl_hours')
def _check_link_ttl_positive(self):
    for record in self:
        if record.invite_link_ttl_hours <= 0 or record.invite_link_ttl_hours > 720:
            raise ValidationError('Invite link validity must be between 1 and 720 hours')
        if record.reset_link_ttl_hours <= 0 or record.reset_link_ttl_hours > 720:
            raise ValidationError('Reset link validity must be between 1 and 720 hours')
```

### Singleton Pattern

```python
@api.model
def get_settings(self):
    """Returns the single settings record, creating default if needed."""
    settings = self.search([], limit=1)
    if not settings:
        settings = self.create({'name': 'Email Link Configuration'})
    return settings
```

### Odoo View

- **Form view**: Accessible from Technical > Configuration > Email Link Settings
- **Follows**: Odoo 18.0 standards (no `attrs`, `<list>` not `<tree>`)

---

## Entity 3: `res.users` (Extension)

**Table**: `res_users` (existing Odoo core table)
**Module**: `thedevkitchen_user_onboarding` (via `_inherit`)
**Purpose**: Add `signup_pending` flag to track invite status

### New Fields (added by this module)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `signup_pending` | Boolean | ❌ | `False` | `True` when user was invited but hasn't set password yet |

### Coexistence with `quicksol_estate`

`quicksol_estate/models/res_users.py` already extends `res.users` with:
- `cpf` (Char) — Brazilian CPF
- `estate_company_ids` (Many2many) — Company association
- `company_role_ids` (Many2many) — Role assignments

Both `_inherit` declarations coexist. Odoo merges fields from all inheriting models into `res.users`.

---

## Entity 4: `real.estate.tenant` (Existing — Referenced, NOT modified)

**Table**: `real_estate_tenant` (existing in `quicksol_estate`)
**Purpose**: Business entity for tenants. Linked to `res.users` via `partner_id` for portal access.

### Relevant Fields for Portal Dual Record

| Field | Type | Description |
|-------|------|-------------|
| `partner_id` | Many2one(`res.partner`) | Links tenant to the user's partner (auto-created by `res.users`) |
| `name` | Char | Tenant name |
| `document` | Char | CPF or CNPJ (unique constraint) |
| `email` | Char | Email address |
| `phone` | Char | Phone number |
| `birthdate` | Date | Date of birth |
| `company_ids` | Many2many | Associated companies |

### Dual Record Flow

When `profile=portal`:
1. Create `res.users` → auto-creates `res.partner` record
2. Create `real.estate.tenant` with `partner_id = user.partner_id.id`
3. Both records are created in a single DB transaction (atomic)

---

## Email Templates (mail.template)

### Template 1: User Invite

| Attribute | Value |
|-----------|-------|
| **XML ID** | `thedevkitchen_user_onboarding.email_template_user_invite` |
| **Model** | `res.users` |
| **Subject** | `Convite para criar sua senha - ${object.company_id.name}` |
| **Recipient** | `${object.email}` |
| **Body variables** | `object.name`, `invite_link` (context), `expires_hours` (context) |

### Template 2: Password Reset

| Attribute | Value |
|-----------|-------|
| **XML ID** | `thedevkitchen_user_onboarding.email_template_password_reset` |
| **Model** | `res.users` |
| **Subject** | `Redefinição de senha - ${object.company_id.name}` |
| **Recipient** | `${object.email}` |
| **Body variables** | `object.name`, `reset_link` (context), `expires_hours` (context) |

---

## Cron Job

### Token Cleanup

| Attribute | Value |
|-----------|-------|
| **XML ID** | `thedevkitchen_user_onboarding.cron_cleanup_expired_tokens` |
| **Model** | `thedevkitchen.password.token` |
| **Method** | `_cron_cleanup_expired_tokens` |
| **Interval** | Every 24 hours |
| **Action** | Mark tokens with `status='pending'` and `expires_at < now()` as `status='expired'` |

---

## Profile-to-Group Mapping

| Profile Value | Odoo Group XML ID | Dual Record |
|---------------|-------------------|-------------|
| `owner` | `quicksol_estate.group_real_estate_owner` | ❌ |
| `director` | `quicksol_estate.group_real_estate_director` | ❌ |
| `manager` | `quicksol_estate.group_real_estate_manager` | ❌ |
| `agent` | `quicksol_estate.group_real_estate_agent` | ❌ |
| `prospector` | `quicksol_estate.group_real_estate_prospector` | ❌ |
| `receptionist` | `quicksol_estate.group_real_estate_receptionist` | ❌ |
| `financial` | `quicksol_estate.group_real_estate_financial` | ❌ |
| `legal` | `quicksol_estate.group_real_estate_legal` | ❌ |
| `portal` | `quicksol_estate.group_real_estate_portal_user` | ✅ `res.users` + `real.estate.tenant` |

---

## Authorization Matrix

| Requester Group | Allowed Target Profiles |
|----------------|-------------------------|
| `group_real_estate_owner` | ALL 9 profiles |
| `group_real_estate_director` | agent, prospector, receptionist, financial, legal |
| `group_real_estate_manager` | agent, prospector, receptionist, financial, legal |
| `group_real_estate_agent` | owner, portal |
| All others | NONE (403 Forbidden) |
