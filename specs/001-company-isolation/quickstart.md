# Quickstart: Company Isolation Phase 1

**Feature**: Company Isolation Phase 1  
**Audience**: Developers implementing/testing multi-tenant isolation  
**Estimated Time**: 30 minutes

## Prerequisites

- Docker and Docker Compose installed
- Odoo 18.0 environment running (Phase 0 complete)
- Database: `realestate` with existing properties
- Basic understanding of Odoo ORM and decorators

## Setup Guide

### Step 1: Create Test Companies (via Odoo Web UI)

1. **Start Odoo containers**:
   ```bash
   cd 18.0
   docker compose up -d
   docker compose logs -f odoo  # Wait for "odoo.modules.loading: Modules loaded."
   ```

2. **Access Odoo Web**: http://localhost:8069
   - Email: `admin`
   - Password: `admin`

3. **Navigate to Real Estate Companies**:
   - Apps > Real Estate > Configuration > Companies
   - Click "Create"

4. **Create Company A**:
   - Name: `ABC Imóveis`
   - Registration: `12.345.678/0001-90` (CNPJ)
   - Email: `contato@abcimoveis.com.br`
   - Save

5. **Create Company B**:
   - Name: `XYZ Imóveis`
   - Registration: `98.765.432/0001-12` (CNPJ)
   - Email: `contato@xyzimoveis.com.br`
   - Save

### Step 2: Create Test Users

1. **Navigate to Users**: Settings > Users & Companies > Users

2. **Create User A** (assigned to ABC Imóveis):
   - Name: `Alice Silva`
   - Login: `alice@abcimoveis.com`
   - Password: `alice123`
   - Real Estate Companies: Select `ABC Imóveis`
   - Default Company: `ABC Imóveis`
   - Access Rights: `Real Estate / User` (or Manager for testing)
   - Save

3. **Create User B** (assigned to XYZ Imóveis):
   - Name: `Bob Santos`
   - Login: `bob@xyzimoveis.com`
   - Password: `bob123`
   - Real Estate Companies: Select `XYZ Imóveis`
   - Default Company: `XYZ Imóveis`
   - Access Rights: `Real Estate / User`
   - Save

4. **Create User C** (assigned to both companies):
   - Name: `Carol Oliveira`
   - Login: `carol@consultant.com`
   - Password: `carol123`
   - Real Estate Companies: Select BOTH `ABC Imóveis` and `XYZ Imóveis`
   - Default Company: `ABC Imóveis` (choose either)
   - Access Rights: `Real Estate / Manager`
   - Save

### Step 3: Create Test Properties

1. **Log in as Alice** (User A):
   - Logout from admin account
   - Login with `alice@abcimoveis.com` / `alice123`

2. **Create Property A1**:
   - Real Estate > Properties > Create
   - Name: `Apartamento Jardins 101`
   - Property Type: `Apartment`
   - Companies: `ABC Imóveis` (should auto-select)
   - Fill required fields (area, address, etc.)
   - Save

3. **Create Property A2**:
   - Name: `Casa Vila Madalena 202`
   - Companies: `ABC Imóveis`
   - Save

4. **Log in as Bob** (User B):
   - Logout from Alice
   - Login with `bob@xyzimoveis.com` / `bob123`

5. **Create Property B1**:
   - Name: `Cobertura Pinheiros 303`
   - Companies: `XYZ Imóveis` (should auto-select)
   - Save

6. **Create Property B2**:
   - Name: `Loft Itaim 404`
   - Companies: `XYZ Imóveis`
   - Save

### Step 4: Verify Isolation in Odoo Web UI

1. **As Alice** (ABC Imóveis user):
   - Navigate to Real Estate > Properties
   - **Expected**: See only Property A1 and A2 (NOT B1 or B2)
   - Try to access Property B1 via direct URL: `http://localhost:8069/web#id=<b1_id>&model=thedevkitchen.estate.property`
   - **Expected**: "Access Denied" error

2. **As Bob** (XYZ Imóveis user):
   - Navigate to Real Estate > Properties
   - **Expected**: See only Property B1 and B2 (NOT A1 or A2)

3. **As Carol** (both companies):
   - Navigate to Real Estate > Properties
   - **Expected**: See ALL 4 properties (A1, A2, B1, B2)

### Step 5: Test API Isolation

1. **Get Session Token for Alice**:
   ```bash
   curl -X POST http://localhost:8069/api/v1/users/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "alice@abcimoveis.com",
       "password": "alice123"
     }'
   ```
   
   Response:
   ```json
   {
     "success": true,
     "data": {
       "session_id": "abc123xyz...",
       "user": {...}
     }
   }
   ```

2. **List Properties as Alice**:
   ```bash
   curl -X GET http://localhost:8069/api/v1/properties \
     -H "X-Openerp-Session-Id: abc123xyz..."
   ```
   
   **Expected**: JSON with 2 properties (A1, A2 only)

3. **Attempt to Access Property B1 as Alice**:
   ```bash
   curl -X GET http://localhost:8069/api/v1/properties/<b1_id> \
     -H "X-Openerp-Session-Id: abc123xyz..."
   ```
   
   **Expected**: 404 Not Found (not 403, to avoid information disclosure)

4. **Create Property as Alice with Unauthorized Company**:
   ```bash
   curl -X POST http://localhost:8069/api/v1/properties \
     -H "X-Openerp-Session-Id: abc123xyz..." \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Property",
       "property_type_id": 1,
       "area": 100,
       "company_ids": [[6, 0, [<xyz_company_id>]]]
     }'
   ```
   
   **Expected**: 403 Forbidden with error "Access denied to companies: [<xyz_company_id>]"

### Step 6: Run Isolation Tests

1. **Access Odoo Container**:
   ```bash
   docker compose exec odoo bash
   ```

2. **Run Company Isolation Tests** (when implemented):
   ```bash
   odoo -c /etc/odoo/odoo.conf \
     -d realestate \
     -u quicksol_estate \
     --test-enable \
     --test-tags /company_isolation \
     --stop-after-init
   ```

3. **Check Test Results**:
   - Look for `INFO test.thedevkitchen.estate.test_company_isolation: TestCompanyIsolation...`
   - All tests should PASS (0 failures, 0 errors)

4. **Run All API Tests**:
   ```bash
   odoo -c /etc/odoo/odoo.conf \
     -d realestate \
     -u quicksol_estate \
     --test-enable \
     --test-tags /api \
     --stop-after-init
   ```

## Common Issues & Troubleshooting

### Issue 1: "User has no company access" Error

**Symptom**: API returns `{"error": {"status": 403, "message": "User has no company access"}}`

**Solution**:
1. Verify user has `estate_company_ids` set in Odoo Web UI
2. Check user's session is valid (not expired)
3. Ensure `@require_company` decorator is applied to endpoint

### Issue 2: User Sees Properties from All Companies

**Symptom**: Alice sees Bob's properties in Odoo Web UI

**Possible Causes**:
- Record Rules not activated in `security.xml`
- User is a system admin (`base.group_system`) - admins bypass all rules
- `estate_company_ids` field not set on properties

**Solution**:
1. Check if Record Rules are active: Settings > Technical > Security > Record Rules
2. Search for "Property: Multi-company Isolation"
3. Verify domain: `[('estate_company_ids', 'in', user.estate_company_ids.ids)]`
4. If missing, add to `quicksol_estate/security/security.xml` and upgrade module

### Issue 3: API Returns All Properties Despite @require_company

**Symptom**: API ignores company filtering

**Solution**:
1. Check controller code: Is `request.company_domain` applied to search?
   ```python
   # WRONG:
   properties = request.env['thedevkitchen.estate.property'].search([])
   
   # CORRECT:
   domain = [('estate_company_ids', 'in', request.user_company_ids)]
   properties = request.env['thedevkitchen.estate.property'].search(domain)
   ```

2. Verify decorator is BEFORE function definition:
   ```python
   @http.route('/api/v1/properties', ...)
   @require_jwt
   @require_session
   @require_company  # Must be here!
   def list_properties(self, **kwargs):
   ```

### Issue 4: Tests Fail with "company_id not found"

**Symptom**: `KeyError: 'company_id'` in test logs

**Solution**:
- Tests must create companies and users with company assignments in `setUp()`
- Use Many2many syntax: `'estate_company_ids': [(6, 0, [company.id])]`

## Validation Checklist

Before proceeding to implementation, verify:

- [ ] Created 2 test companies (ABC Imóveis, XYZ Imóveis)
- [ ] Created 3 test users (Alice, Bob, Carol) with correct company assignments
- [ ] Created 4 test properties (2 per company)
- [ ] Verified Odoo Web UI shows correct properties per user
- [ ] Tested API isolation (Alice cannot access Bob's properties)
- [ ] Tested unauthorized create attempt returns 403
- [ ] Read `data-model.md` to understand entity relationships
- [ ] Read `contracts/record-rules.xml` to understand Record Rule syntax

## Next Steps

1. **Implement Record Rules**: Add `security.xml` rules to `quicksol_estate` module
2. **Create Test Suite**: Implement `test_company_isolation.py` with 30+ scenarios
3. **Update Controllers**: Ensure all endpoints apply `request.company_domain`
4. **Run Full Test Suite**: Verify 80%+ coverage maintained
5. **Performance Benchmark**: Measure <10% degradation vs. Phase 0

## Additional Resources

- [Odoo Record Rules Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html#record-rules)
- [Many2many Field Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#relational-fields)
- [ADR-008: API Security & Multi-Tenancy](../../docs/adr/ADR-008-api-security-multi-tenancy.md)
- [Constitution: Principle IV - Multi-Tenancy by Design](../../.specify/memory/constitution.md)

---

**Quickstart Status**: ✅ Ready for implementation team  
**Estimated Completion**: 30 minutes  
**Difficulty**: Intermediate
