# Company Isolation Code Review Checklist

**Feature**: 001-company-isolation  
**Reviewer**: _____________  
**Date**: _____________  
**Status**: ⏳ Pending Review

---

## Security & Authentication

### Decorator Usage

- [ ] **All protected endpoints** use the triple decorator chain in correct order:
  ```python
  @require_jwt        # 1️⃣ First
  @require_session    # 2️⃣ Second  
  @require_company    # 3️⃣ Third
  ```

- [ ] **Public endpoints** are explicitly marked with `# public endpoint` comment

- [ ] **No endpoints** bypass company filtering (except intentionally public ones)

### Decorator Order Verification

Check these files for correct decorator order:

- [ ] `18.0/extra-addons/quicksol_estate/controllers/property_api.py`
  - [ ] POST /api/v1/properties
  - [ ] GET /api/v1/properties/{id}
  - [ ] PUT /api/v1/properties/{id}
  - [ ] DELETE /api/v1/properties/{id}

- [ ] `18.0/extra-addons/quicksol_estate/controllers/master_data_api.py`
  - [ ] GET /api/v1/master-data/property-types
  - [ ] GET /api/v1/master-data/location-types
  - [ ] GET /api/v1/master-data/states
  - [ ] GET /api/v1/master-data/agents
  - [ ] GET /api/v1/master-data/owners
  - [ ] GET /api/v1/master-data/companies
  - [ ] GET /api/v1/master-data/tags
  - [ ] GET /api/v1/master-data/amenities

---

## Company Filtering Implementation

### ORM Queries

- [ ] **All search() calls** in protected endpoints use `request.company_domain`
  ```python
  domain = [...custom filters...] + request.company_domain
  Model.search(domain)
  ```

- [ ] **GET by ID endpoints** combine ID filter with company_domain:
  ```python
  domain = [('id', '=', entity_id)] + request.company_domain
  entity = Model.search(domain, limit=1)
  ```

- [ ] **404 responses** used for unauthorized access (NOT 403):
  ```python
  if not entity:
      return error_response(404, 'Entity not found')  # Correct
  # NOT: return error_response(403, 'Access denied')  # Wrong
  ```

### Create/Update Operations

- [ ] **POST endpoints** validate company_ids with CompanyValidator:
  ```python
  from ..services.company_validator import CompanyValidator
  
  data = CompanyValidator.ensure_company_ids(data)
  valid, error = CompanyValidator.validate_company_ids(company_ids)
  if not valid:
      return error_response(403, error)
  ```

- [ ] **PUT endpoints** block company_ids changes:
  ```python
  if 'company_ids' in data:
      return error_response(403, 'Cannot change company_ids via API')
  ```

- [ ] **DELETE endpoints** verify entity belongs to user's companies before deletion

---

## Data Models

### Many2many Fields

- [ ] **All isolation-enabled models** have `company_ids` Many2many field:
  - [X] real.estate.property
  - [X] real.estate.agent
  - [X] real.estate.tenant
  - [X] real.estate.lease
  - [X] real.estate.sale
  - [ ] res.users (uses `estate_company_ids`)

- [ ] **Field definitions** follow correct pattern:
  ```python
  company_ids = fields.Many2many(
      'thedevkitchen.estate.company',
      'junction_table_name',
      'entity_id_column',
      'company_id_column',
      string='Real Estate Companies'
  )
  ```

### Model Registration

- [ ] **All models** with company_ids registered in ir.model.access.csv

- [ ] **Junction tables** created by Odoo (automatic for Many2many)

---

## Record Rules

### Security Files

- [ ] **record_rules.xml** exists at `18.0/extra-addons/quicksol_estate/security/record_rules.xml`

- [ ] **__manifest__.py** loads record_rules.xml:
  ```python
  'data': [
      'security/groups.xml',
      'security/record_rules.xml',  # Must be after groups.xml
  ]
  ```

### Rule Definitions

- [ ] **All multi-tenant models** have corresponding Record Rules:
  - [X] property_multi_company_rule
  - [X] agent_multi_company_rule
  - [X] tenant_multi_company_rule
  - [X] lease_multi_company_rule
  - [X] sale_multi_company_rule

- [ ] **Rule domain_force** uses correct pattern:
  ```xml
  <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
  ```

- [ ] **Rule groups** target correct user groups (typically `group_real_estate_user`, `group_real_estate_manager`)

- [ ] **Rule permissions** set correctly (perm_read, perm_write, perm_create, perm_unlink)

---

## Services & Utilities

### CompanyValidator Service

- [ ] **validate_company_ids()** method exists and returns `(bool, error_msg)`:
  ```python
  valid, error = CompanyValidator.validate_company_ids([1, 2, 3])
  ```

- [ ] **get_default_company_id()** method returns user's default or first company

- [ ] **ensure_company_ids()** method auto-assigns default if missing:
  ```python
  data = CompanyValidator.ensure_company_ids(data)
  ```

- [ ] **Admin bypass** implemented (base.group_system users see all companies)

### AuditLogger Service

- [ ] **log_company_isolation_violation()** method exists:
  ```python
  AuditLogger.log_company_isolation_violation(
      user_id, user_login, unauthorized_companies, endpoint
  )
  ```

- [ ] **log_unauthorized_record_access()** method logs 404 responses:
  ```python
  AuditLogger.log_unauthorized_record_access(
      user_id, user_login, record_model, record_id, endpoint
  )
  ```

---

## Documentation

### API Documentation

- [ ] **README.md** includes decorator section at `18.0/extra-addons/thedevkitchen_apigateway/README.md`

- [ ] **decorators.md** exists with comprehensive examples at `18.0/extra-addons/thedevkitchen_apigateway/docs/decorators.md`

- [ ] **Documentation covers**:
  - [ ] Decorator order (@require_jwt → @require_session → @require_company)
  - [ ] Usage patterns (list, get by ID, create, update)
  - [ ] request.company_domain injection
  - [ ] request.user_company_ids availability
  - [ ] Admin bypass behavior
  - [ ] Error responses (403 vs 404)

### Code Comments

- [ ] **Public endpoints** marked with `# public endpoint` comment

- [ ] **Complex filtering** has inline comments explaining logic

- [ ] **CompanyValidator** methods have docstrings

---

## Testing

### Test Coverage

- [ ] **test_company_isolation.py** exists at `18.0/extra-addons/quicksol_estate/tests/test_company_isolation.py`

- [ ] **Test suite** covers all user stories:
  - [ ] US1: Property/entity filtering (4 tests)
  - [ ] US2: Create/update validation (4 tests)
  - [ ] US3: Decorator integration (2 tests)
  - [ ] US4: Record Rules (implicitly tested)
  - [ ] US5: Edge cases (5+ tests)

- [ ] **Tests** for Agent, Tenant filtering (6 tests)

- [ ] **Admin bypass** test exists

- [ ] **Zero companies** test exists

### Test Execution

- [ ] **All tests pass** when run with:
  ```bash
  docker compose exec odoo odoo-bin -c /etc/odoo/odoo.conf --test-enable --stop-after-init -u quicksol_estate --test-tags=company_isolation
  ```

- [ ] **No SQL errors** in logs during test execution

- [ ] **Test execution time** < 5 seconds (performance acceptable)

---

## Security Verification

### Information Disclosure

- [ ] **Unauthorized access** returns 404 (not 403) to prevent information disclosure

- [ ] **Error messages** don't reveal sensitive data (company names, record details)

- [ ] **Audit logs** created for security events (401, 403, 404 responses)

### Session Hijacking Protection

- [ ] **@require_session** decorator enforces session fingerprinting

- [ ] **Fingerprint mismatch** returns 403 with security warning

- [ ] **Session expiry** handled gracefully (401 response)

### Company Reassignment

- [ ] **PUT endpoints** block company_ids changes via API

- [ ] **Company reassignment** only possible via Odoo Web UI (with proper permissions)

---

## Performance

### Database Queries

- [ ] **Junction tables** have indexes on company_id column (if not auto-indexed):
  ```sql
  CREATE INDEX idx_company_property_rel_company_id ON thedevkitchen_company_property_rel(company_id);
  CREATE INDEX idx_company_agent_rel_company_id ON company_agent_rel(company_id);
  -- etc.
  ```

- [ ] **company_domain filtering** doesn't cause N+1 queries

- [ ] **ORM queries** use efficient search() patterns (not browse loops)

### API Response Times

- [ ] **Baseline response time** measured before isolation

- [ ] **Post-isolation response time** < 10% degradation

- [ ] **No significant slowdown** on endpoints with company filtering

---

## Migration & Compatibility

### Data Migration

- [ ] **Orphaned records** (company_ids empty) handled:
  - [ ] Migration script assigns default company, OR
  - [ ] Documented as intentional (e.g., system-level master data)

- [ ] **Existing users** assigned to at least one company

### Backward Compatibility

- [ ] **API endpoints** maintain same request/response format

- [ ] **No breaking changes** to existing API contracts

- [ ] **Odoo Web UI** continues to work (Record Rules don't break existing views)

---

## Final Checklist

### Pre-Merge Requirements

- [ ] **All automated tests pass** (test_company_isolation.py)

- [ ] **Manual testing complete** (quickstart.md scenarios)

- [ ] **Documentation updated** (README.md, decorators.md, test-coverage.md)

- [ ] **Code review approved** by at least 1 team member

- [ ] **No merge conflicts** with main branch

- [ ] **Backup created** of security files (already done in T005)

### Post-Merge Actions

- [ ] **Upgrade module** on staging: `docker compose exec odoo odoo-bin -u quicksol_estate`

- [ ] **Smoke tests** on staging environment

- [ ] **Monitor logs** for security events (audit_logger entries)

- [ ] **Performance monitoring** for first 24 hours

---

## Common Issues Checklist

### ❌ Missing @require_company Decorator

**Symptom**: Endpoint returns all data regardless of user's companies  
**Fix**: Add @require_company decorator after @require_session

### ❌ Wrong Decorator Order

**Symptom**: 500 error, AttributeError: 'NoneType' object has no attribute 'estate_company_ids'  
**Fix**: Ensure order is @require_jwt → @require_session → @require_company

### ❌ Forgot request.company_domain in Search

**Symptom**: User sees data from other companies  
**Fix**: Add `+ request.company_domain` to search domain

### ❌ Returns 403 Instead of 404

**Symptom**: Information disclosure (attacker knows record exists)  
**Fix**: Change error_response(403, ...) to error_response(404, ...)

### ❌ PUT Allows company_ids Changes

**Symptom**: Users can reassign records to unauthorized companies  
**Fix**: Add check `if 'company_ids' in data: return error_response(403, ...)`

### ❌ Missing CompanyValidator.validate_company_ids()

**Symptom**: POST endpoints allow creating records for unauthorized companies  
**Fix**: Add validation in create endpoints before create()

---

## Sign-Off

**Developer**: _____________  
**Date**: _____________  

**Code Reviewer**: _____________  
**Date**: _____________  

**QA Tester**: _____________  
**Date**: _____________  

---

## Notes

Use this space for review comments, discovered issues, or recommendations:

```
[Reviewer notes here]
```
