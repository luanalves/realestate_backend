# Quickstart: User Onboarding & Password Management

**Feature**: 009-user-onboarding-password-management
**Date**: 2026-02-16

---

## Prerequisites

1. **Docker environment running** (from `18.0/` directory):
   ```bash
   cd 18.0 && docker compose up -d
   ```

2. **SMTP configured** in Odoo:
   - Go to Settings > Technical > Outgoing Mail Servers
   - Configure SMTP (e.g., Mailtrap for development, production SMTP for prod)
   - **Development alternative**: Use `docker compose logs -f odoo` to view email content in logs (Odoo logs emails when no SMTP is configured)

3. **Existing modules installed**:
   - `thedevkitchen_apigateway` (OAuth2 + JWT + session management)
   - `quicksol_estate` (RBAC groups, tenant model)

4. **Test users available** (from `18.0/.env`):
   - Owner, Manager, Agent credentials configured

---

## Installation

### 1. Install the module

```bash
# Copy module to extra-addons (if not already there)
# Module should be at: 18.0/extra-addons/thedevkitchen_user_onboarding/

# Restart Odoo with module update
docker compose exec odoo odoo --update=thedevkitchen_user_onboarding --stop-after-init

# Or via Odoo UI: Settings > Apps > Update Apps List > Search "User Onboarding" > Install
```

### 2. Verify installation

```bash
# Check module is loaded
docker compose exec odoo odoo shell -c "
env['ir.module.module'].search([('name', '=', 'thedevkitchen_user_onboarding')]).state
"
# Expected: 'installed'

# Verify default settings created
docker compose exec db psql -U odoo -d realestate -c "
SELECT id, name, invite_link_ttl_hours, reset_link_ttl_hours, frontend_base_url
FROM thedevkitchen_email_link_settings;
"
# Expected: 1 row with defaults (24h, 24h, http://localhost:3000)
```

---

## Quick Test Flow

### Flow 1: Owner Invites Agent → Agent Sets Password → Agent Logs In

```bash
BASE_URL="http://localhost:8069"

# Step 1: Authenticate as Owner (get JWT + session)
JWT_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"owner@test.com","password":"owner_password"}' \
  | jq -r '.access_token')

SESSION_ID=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@test.com","password":"owner_password"}' \
  | jq -r '.session_id')

# Step 2: Invite a new Agent
INVITE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/invite" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "X-Company-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Novo Agente",
    "email": "novo.agente@test.com",
    "document": "12345678909",
    "profile": "agent"
  }')

echo "$INVITE_RESPONSE" | jq .
# Expected: 201 with user data + signup_pending=true

# Step 3: Get token from email (in dev, check Odoo logs or DB)
# In production, user clicks link in email
RAW_TOKEN=$(docker compose exec db psql -U odoo -d realestate -t -c "
SELECT encode(decode(token, 'hex'), 'hex') FROM thedevkitchen_password_token 
WHERE user_id = (SELECT id FROM res_users WHERE login='novo.agente@test.com') 
ORDER BY create_date DESC LIMIT 1;
" | tr -d ' \n')
# NOTE: The DB stores the HASH. For testing, you need the raw token from the email/logs.

# Step 4: Set password using token from email
curl -s -X POST "$BASE_URL/api/v1/auth/set-password" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$RAW_TOKEN\",
    \"password\": \"AgentPass123!\",
    \"confirm_password\": \"AgentPass123!\"
  }" | jq .
# Expected: 200 with "Password set successfully"

# Step 5: Agent logs in
curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"novo.agente@test.com","password":"AgentPass123!"}' | jq .
# Expected: 200 with session_id + user data
```

### Flow 2: Forgot Password → Reset → Login

```bash
# Step 1: Request password reset
curl -s -X POST "$BASE_URL/api/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "novo.agente@test.com"}' | jq .
# Expected: 200 (always, even if email doesn't exist)

# Step 2: Get reset token from email/logs
# (In dev: check Odoo logs or query DB for the raw token)

# Step 3: Reset password
curl -s -X POST "$BASE_URL/api/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"<reset_token_from_email>\",
    \"password\": \"NewAgentPass456!\",
    \"confirm_password\": \"NewAgentPass456!\"
  }" | jq .
# Expected: 200 with "Password reset successfully"

# Step 4: Login with new password
curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"novo.agente@test.com","password":"NewAgentPass456!"}' | jq .
```

### Flow 3: Agent Invites Portal User (Tenant — Dual Record)

```bash
# Step 1: Authenticate as Agent
# (same auth flow as Step 1 in Flow 1, using agent credentials)

# Step 2: Invite a portal user (tenant)
curl -s -X POST "$BASE_URL/api/v1/users/invite" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "X-Company-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Maria Inquilina",
    "email": "maria.inquilina@test.com",
    "document": "98765432100",
    "profile": "portal",
    "phone": "11999998888",
    "birthdate": "1990-05-15",
    "company_id": 1
  }' | jq .
# Expected: 201 with user data + tenant data + signup_pending=true

# Verify dual record created
docker compose exec db psql -U odoo -d realestate -c "
SELECT u.id as user_id, u.login, t.id as tenant_id, t.document, t.partner_id
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
JOIN real_estate_tenant t ON t.partner_id = p.id
WHERE u.login = 'maria.inquilina@test.com';
"
```

---

## Configuration

### Email Link Settings (Odoo UI)

1. Go to **Settings > Technical > Configuration > Email Link Settings**
2. Adjust:
   - **Invite link validity**: Default 24 hours (1-720 hours)
   - **Reset link validity**: Default 24 hours (1-720 hours)
   - **Frontend base URL**: Default `http://localhost:3000` (change for production)
   - **Max resend attempts**: Default 5
   - **Rate limit (forgot/hour)**: Default 3

### Email Link Settings (CLI)

```bash
docker compose exec db psql -U odoo -d realestate -c "
UPDATE thedevkitchen_email_link_settings 
SET invite_link_ttl_hours = 48, 
    reset_link_ttl_hours = 12,
    frontend_base_url = 'https://app.meusite.com.br'
WHERE id = 1;
"
```

---

## Running Tests

### Unit Tests

```bash
docker compose exec odoo python3 \
  /mnt/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_token_service.py

docker compose exec odoo python3 \
  /mnt/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_password_validation.py

docker compose exec odoo python3 \
  /mnt/extra-addons/thedevkitchen_user_onboarding/tests/unit/test_invite_authorization.py
```

### E2E API Tests (shell/curl)

```bash
cd integration_tests/

# All Feature 009 tests
bash test_us9_s1_invite_flow.sh
bash test_us9_s2_forgot_password.sh
bash test_us9_s3_portal_dual_record.sh
bash test_us9_s4_authorization_matrix.sh
bash test_us9_s5_multitenancy.sh
bash test_us9_s6_resend_invite.sh
```

### Cypress E2E (UI)

```bash
npx cypress run --spec cypress/e2e/email-link-settings.cy.js
```

---

## Troubleshooting

### Email not sending
```bash
# Check Odoo mail queue
docker compose exec db psql -U odoo -d realestate -c "
SELECT id, email_to, subject, state, failure_reason 
FROM mail_mail ORDER BY create_date DESC LIMIT 10;
"

# Check SMTP configuration
docker compose exec db psql -U odoo -d realestate -c "
SELECT name, smtp_host, smtp_port, smtp_encryption FROM ir_mail_server;
"
```

### Token issues
```bash
# List recent tokens
docker compose exec db psql -U odoo -d realestate -c "
SELECT pt.id, ru.login, pt.token_type, pt.status, pt.expires_at, pt.used_at
FROM thedevkitchen_password_token pt
JOIN res_users ru ON pt.user_id = ru.id
ORDER BY pt.create_date DESC LIMIT 20;
"

# Check expired tokens
docker compose exec db psql -U odoo -d realestate -c "
SELECT COUNT(*) as expired_tokens 
FROM thedevkitchen_password_token 
WHERE status = 'pending' AND expires_at < NOW();
"
```

### Redis rate limiting
```bash
# Check rate limit keys
docker compose exec redis redis-cli KEYS "rate_limit:forgot_password:*"

# Clear rate limit for specific email
docker compose exec redis redis-cli DEL "rate_limit:forgot_password:user@example.com"
```

---

## API Quick Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/users/invite` | JWT + Session + Company | Invite new user |
| POST | `/api/v1/auth/set-password` | Public | Set password via invite token |
| POST | `/api/v1/auth/forgot-password` | Public (rate limited) | Request password reset |
| POST | `/api/v1/auth/reset-password` | Public | Reset password via token |
| POST | `/api/v1/users/{id}/resend-invite` | JWT + Session + Company | Resend invite email |
