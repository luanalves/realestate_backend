# Quickstart: Rental Credit Check (spec 014)

**Module**: `thedevkitchen_estate_credit_check`
**Branch**: `014-rental-credit-check`
**Odoo version**: 18.0

---

## Prerequisites

Ensure the following are running and healthy:

```bash
cd /opt/homebrew/var/www/realestate/realestate_backend/18.0
docker compose ps
# Expected: odoo, db, redis all UP
```

Required modules already installed:
- `thedevkitchen_apigateway` (JWT auth, sessions)
- `quicksol_estate` (proposals, properties, agents)
- `thedevkitchen_user_onboarding` (RBAC profiles)

---

## Step 1 — Create the module scaffold

```bash
# From repo root
mkdir -p 18.0/extra-addons/thedevkitchen_estate_credit_check/{models,controllers,services,views,security,data,tests}
touch 18.0/extra-addons/thedevkitchen_estate_credit_check/{__init__.py,__manifest__.py}
touch 18.0/extra-addons/thedevkitchen_estate_credit_check/models/__init__.py
touch 18.0/extra-addons/thedevkitchen_estate_credit_check/controllers/__init__.py
touch 18.0/extra-addons/thedevkitchen_estate_credit_check/services/__init__.py
touch 18.0/extra-addons/thedevkitchen_estate_credit_check/tests/__init__.py
```

Reference the existing module structure in `thedevkitchen_user_onboarding` for manifest and `__init__.py` patterns.

---

## Step 2 — Install the module

```bash
# Restart Odoo with module update flag
docker compose exec odoo bash -c \
  "odoo -c /etc/odoo/odoo.conf -u thedevkitchen_estate_credit_check --stop-after-init"

# Or via Odoo UI: Settings → Activate developer mode → Apps → Update Apps List
# Then install "TheDevKitchen Estate Credit Check"
```

---

## Step 3 — Verify DB schema

```bash
docker compose exec db psql -U odoo -d realestate -c \
  "\d thedevkitchen_estate_credit_check"
```

Expected columns: `id`, `proposal_id`, `company_id`, `partner_id`, `result`, `requested_by`, `requested_at`, `result_registered_by`, `result_registered_at`, `rejection_reason`, `check_date`, `active`, `create_date`, `write_date`, `create_uid`, `write_uid`.

Verify partial unique index:

```bash
docker compose exec db psql -U odoo -d realestate -c \
  "\di thedevkitchen_estate_credit_check_one_pending_per_proposal"
```

---

## Step 4 — Authenticate (get JWT + session)

```bash
# 1. Get OAuth token
curl -s -X POST http://localhost:8069/oauth2/token \
  -d "grant_type=password&username=admin&password=admin&client_id=<client_id>&client_secret=<client_secret>" \
  | python3 -m json.tool
# Save: access_token

# 2. Get session cookie
curl -s -c cookies.txt -X POST http://localhost:8069/api/v1/auth/login \
  -H "Authorization: Bearer <access_token>" \
  | python3 -m json.tool
# cookies.txt now contains session_id
```

---

## Step 5 — Create a test proposal in `sent` state

Use the proposals API (spec 013) or Odoo UI to create a property + proposal.
Ensure the proposal is in `sent` state (agent submitted, owner/manager reviewed).

```bash
# Check proposal state
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, state, partner_id FROM thedevkitchen_estate_proposal WHERE state = 'sent' LIMIT 5;"
```

Note the `proposal_id` for the next steps.

---

## Step 6 — Initiate a credit check

```bash
PROPOSAL_ID=<your_proposal_id>

curl -s -b cookies.txt -X POST \
  http://localhost:8069/api/v1/proposals/${PROPOSAL_ID}/credit-checks \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool
```

Expected response:
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "proposal_id": <proposal_id>,
    "result": "pending",
    ...
  }
}
```

Verify proposal state changed:
```bash
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, state FROM thedevkitchen_estate_proposal WHERE id = ${PROPOSAL_ID};"
# Expected: state = 'credit_check_pending'
```

---

## Step 7 — Register a result (approve or reject)

```bash
CHECK_ID=<check_id_from_step_6>

# Approve
curl -s -b cookies.txt -X PATCH \
  http://localhost:8069/api/v1/proposals/${PROPOSAL_ID}/credit-checks/${CHECK_ID} \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"result": "approved", "check_date": "2026-04-29"}' \
  | python3 -m json.tool

# Or reject
curl -s -b cookies.txt -X PATCH \
  http://localhost:8069/api/v1/proposals/${PROPOSAL_ID}/credit-checks/${CHECK_ID} \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"result": "rejected", "rejection_reason": "Renda insuficiente.", "check_date": "2026-04-29"}' \
  | python3 -m json.tool
```

---

## Step 8 — Query client credit history

```bash
PARTNER_ID=<partner_id_from_proposal>

curl -s -b cookies.txt \
  http://localhost:8069/api/v1/clients/${PARTNER_ID}/credit-history \
  -H "Authorization: Bearer <access_token>" \
  | python3 -m json.tool
```

---

## Step 9 — Run unit tests

```bash
docker compose exec odoo bash -c \
  "python -m pytest 18.0/extra-addons/thedevkitchen_estate_credit_check/tests/ -v"

# Or via Odoo test runner
docker compose exec odoo bash -c \
  "odoo -c /etc/odoo/odoo.conf --test-enable --stop-after-init -m thedevkitchen_estate_credit_check"
```

---

## Step 10 — Run integration tests

```bash
cd /opt/homebrew/var/www/realestate/realestate_backend
bash integration_tests/run_feature014_tests.sh
```

(Script to be created as part of implementation.)

---

## Email testing (MailHog — ADR-023)

```bash
# MailHog UI
open http://localhost:8025

# Or API
curl http://localhost:8025/api/v2/messages | python3 -m json.tool
```

After approving or rejecting a credit check, the notification email should appear in MailHog within ~5 seconds (Celery dispatch).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `400: A credit check is already pending` | Duplicate initiation | Reject/cancel the existing pending check first |
| `400: Proposal is not in sent state` | Wrong proposal state | Ensure proposal is `sent` before initiating |
| `403: Not authorized` | Agent doesn't own proposal | Use correct agent credentials |
| `404: Proposal not found` | Wrong company context | Check `company_id` in session |
| Partial unique index missing | `_auto_init` not run | Reinstall the module or run migration |
| Email not appearing in MailHog | Celery not running | `docker compose up celery_worker -d` |
