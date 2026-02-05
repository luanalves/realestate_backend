# Quickstart: Company & Owner Management

**Feature**: 007-company-owner-management  
**Branch**: `007-company-owner-management`  
**Time to first test**: ~15 minutes

---

## Prerequisites

```bash
# 1. Ensure Docker services are running
cd 18.0
docker compose up -d

# 2. Verify Odoo is accessible
curl http://localhost:8069/web/health

# 3. Check you're on the correct branch
git checkout 007-company-owner-management
```

---

## Quick Environment Setup

### 1. Get Authentication Token

```bash
# Get OAuth token for Owner user
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "owner@test.com",
    "client_secret": "admin"
  }' | jq -r '.access_token')

echo $TOKEN
```

### 2. Test Company API

```bash
# List companies (should return user's companies)
curl -X GET http://localhost:8069/api/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Create a new company
curl -X POST http://localhost:8069/api/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Imobiliária",
    "cnpj": "12.345.678/0001-90",
    "email": "test@imobiliaria.com"
  }'
```

### 3. Test Owner API

```bash
# List owners of company 1
curl -X GET http://localhost:8069/api/v1/companies/1/owners \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Create new owner for company 1
curl -X POST http://localhost:8069/api/v1/companies/1/owners \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Owner",
    "email": "newowner@test.com",
    "password": "secure123"
  }'
```

---

## Running Tests

### Unit Tests

```bash
cd 18.0

# Run all unit tests for this feature
docker compose exec odoo python -m pytest \
  extra-addons/quicksol_estate/tests/unit/test_company_validations.py \
  extra-addons/quicksol_estate/tests/unit/test_owner_validations.py \
  -v

# Run specific test
docker compose exec odoo python -m pytest \
  extra-addons/quicksol_estate/tests/unit/test_company_validations.py::TestCNPJValidation \
  -v
```

### Integration Tests (API)

```bash
cd 18.0

# Run Company API tests
docker compose exec odoo python -m pytest \
  extra-addons/quicksol_estate/tests/api/test_company_api.py \
  -v

# Run Owner API tests
docker compose exec odoo python -m pytest \
  extra-addons/quicksol_estate/tests/api/test_owner_api.py \
  -v
```

### E2E Tests (Shell)

```bash
cd integration_tests

# Run all company/owner tests
./test_us7_s1_owner_creates_company.sh
./test_us7_s2_owner_creates_owner.sh
./test_us7_s3_company_rbac.sh
./test_us7_s4_company_multitenancy.sh
```

### E2E Tests (Cypress)

```bash
cd 18.0

# Install dependencies if not done
npm install

# Run Cypress tests headlessly
npx cypress run --spec "cypress/e2e/admin-company-management.cy.js"
npx cypress run --spec "cypress/e2e/admin-owner-management.cy.js"

# Or open Cypress UI
npx cypress open
```

---

## File Locations

### Controllers (API)

```
18.0/extra-addons/quicksol_estate/controllers/
├── company_api.py      # Company CRUD endpoints
└── owner_api.py        # Owner CRUD endpoints (nested)
```

### Models

```
18.0/extra-addons/quicksol_estate/models/
├── company.py          # Company model (existing)
└── res_users.py        # User extension (add owner_company_ids)
```

### Views (Odoo Web)

```
18.0/extra-addons/quicksol_estate/views/
├── company_views.xml   # Form, List, Search views
└── real_estate_menus.xml  # Menu with action_company
```

### Tests

```
18.0/extra-addons/quicksol_estate/tests/
├── api/
│   ├── test_company_api.py
│   └── test_owner_api.py
└── unit/
    ├── test_company_validations.py
    └── test_owner_validations.py

integration_tests/
├── test_us7_s1_owner_creates_company.sh
├── test_us7_s2_owner_creates_owner.sh
├── test_us7_s3_company_rbac.sh
└── test_us7_s4_company_multitenancy.sh

cypress/e2e/
├── admin-company-management.cy.js
└── admin-owner-management.cy.js
```

---

## Common Issues & Troubleshooting

### Issue: 401 Unauthorized

**Cause**: Token expired or invalid
**Solution**: Re-authenticate to get new token

```bash
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/oauth/token ...)
```

### Issue: 403 Forbidden

**Cause**: User doesn't have Owner role or not linked to company
**Solution**: Check user's groups and `estate_company_ids`

```python
# In Odoo shell
user = env['res.users'].browse(USER_ID)
print(user.groups_id.mapped('name'))
print(user.estate_company_ids.mapped('name'))
```

### Issue: 404 Not Found

**Cause**: Company/Owner doesn't exist or user doesn't have access (multi-tenancy)
**Solution**: Verify the resource ID and user's `estate_company_ids`

### Issue: CNPJ Validation Failed

**Cause**: Invalid CNPJ format or check digits
**Solution**: Use valid test CNPJs:

```
Valid test CNPJs:
- 11.222.333/0001-81
- 12.345.678/0001-95
- 00.000.000/0001-91 (all zeros - invalid)
```

---

## API Reference

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/companies` | List companies | Owner+ |
| POST | `/api/v1/companies` | Create company | Owner |
| GET | `/api/v1/companies/{id}` | Get company | Any |
| PUT | `/api/v1/companies/{id}` | Update company | Owner |
| DELETE | `/api/v1/companies/{id}` | Archive company | Owner |
| GET | `/api/v1/companies/{id}/owners` | List owners | Owner |
| POST | `/api/v1/companies/{id}/owners` | Create owner | Owner |
| GET | `/api/v1/companies/{id}/owners/{oid}` | Get owner | Owner |
| PUT | `/api/v1/companies/{id}/owners/{oid}` | Update owner | Owner |
| DELETE | `/api/v1/companies/{id}/owners/{oid}` | Deactivate owner | Owner |

---

## Next Steps

1. **Implement controllers**: Start with `company_api.py`
2. **Add views**: Create `company_views.xml` with form/list views
3. **Write tests**: Unit tests first, then integration
4. **Run linting**: `./lint.sh` before committing
5. **Submit PR**: Include test results and coverage report
