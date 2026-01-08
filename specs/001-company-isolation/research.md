# Research: Company Isolation Phase 1

**Feature**: Company Isolation Phase 1  
**Phase**: 0 (Research & Discovery)  
**Date**: January 8, 2026

## Research Objectives

Validate technical approaches for completing multi-tenant company isolation, including:
1. Existing `@require_company` decorator capabilities and limitations
2. Odoo Record Rules syntax and best practices
3. Test patterns for isolation verification
4. Performance implications of Many2many filtering

## Findings

### 1. @require_company Decorator (EXISTING)

**Decision**: Use existing decorator in `thedevkitchen_apigateway/middleware.py` (line 280)

**Current Implementation**:
```python
def require_company(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = request.env.user
        
        if user.has_group('base.group_system'):
            request.company_domain = []
            return func(*args, **kwargs)
        
        if not user.estate_company_ids:
            return {'error': {'status': 403, 'message': 'User has no company access'}}
        
        request.company_domain = [('company_ids', 'in', user.estate_company_ids.ids)]
        request.user_company_ids = user.estate_company_ids.ids
        
        return func(*args, **kwargs)
    return wrapper
```

**Capabilities**:
- ✅ Injects `request.company_domain` for use in search queries
- ✅ Provides `request.user_company_ids` for validation
- ✅ Bypasses filtering for system admins (`base.group_system`)
- ✅ Returns 403 for users with no company assignments

**Limitations Identified**:
- ❌ Does NOT automatically filter ORM queries (controllers must manually apply domain)
- ❌ No automatic enforcement on `.search()`, `.browse()`, or `.create()`
- ❌ Relies on developer discipline to use `request.company_domain` correctly

**Rationale**: Odoo's ORM architecture doesn't support transparent query interception like Django ORM. The decorator provides a domain filter, but controllers must explicitly apply it. This is intentional to maintain visibility of filtering logic.

**Alternatives Considered**:
- **ORM monkey-patching**: Rejected due to complexity, maintainability, and compatibility risks with Odoo core
- **Database views**: Rejected due to performance overhead and limited flexibility
- **Record Rules alone**: Insufficient for REST APIs (only applies to Odoo Web UI)

### 2. CompanyValidator Service (EXISTING)

**Decision**: Enhance existing `quicksol_estate/services/company_validator.py`

**Current Methods**:
- `validate_company_ids(company_ids)` - Validates user has access to requested companies
- `get_default_company_id()` - Returns user's default company
- `ensure_company_ids(data)` - Auto-assigns default company if missing in request body

**Enhancement Needed**:
- Add `filter_by_company(recordset)` method for consistent filtering across controllers
- Add `get_company_domain()` method to centralize domain construction

**Rationale**: Centralized validation logic prevents inconsistent security checks across controllers. Existing methods are well-tested and follow ADR-001 (service layer pattern).

### 3. Odoo Record Rules

**Decision**: Implement Record Rules in `quicksol_estate/security/security.xml`

**Syntax** (Odoo 18.0):
```xml
<record id="property_company_rule" model="ir.rule">
    <field name="name">Property: Multi-company</field>
    <field name="model_id" ref="model_thedevkitchen_estate_property"/>
    <field name="domain_force">[('estate_company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

**Key Properties**:
- `domain_force`: Python expression evaluated in user context
- `groups`: Apply to all authenticated users (not just specific roles)
- Automatically enforced on all CRUD operations in Odoo Web UI
- Does NOT affect REST API controllers (they bypass Record Rules with `auth='none'`)

**Best Practices** (from Odoo documentation):
- Use `user.estate_company_ids.ids` for Many2many field access
- Apply to `base.group_user` (all internal users) unless role-specific
- Use separate rules for global read vs. write permissions
- Test with users having 0, 1, and multiple company assignments

**Rationale**: Record Rules ensure consistency between API and Web UI, preventing developer confusion and security gaps during debugging/administration.

### 4. Test Patterns for Isolation

**Decision**: Create dedicated test class `TestCompanyIsolation` in `tests/api/test_company_isolation.py`

**Pattern** (from existing `test_property_api.py`):
```python
class TestCompanyIsolation(TransactionCase):
    def setUp(self):
        super().setUp()
        # Create 2 companies
        self.company_a = self.env['thedevkitchen.estate.company'].create({'name': 'ABC Imóveis'})
        self.company_b = self.env['thedevkitchen.estate.company'].create({'name': 'XYZ Imóveis'})
        
        # Create users assigned to different companies
        self.user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a',
            'estate_company_ids': [(6, 0, [self.company_a.id])],
            'estate_default_company_id': self.company_a.id
        })
        
        # Create properties in each company
        self.property_a = self.env['thedevkitchen.estate.property'].create({
            'name': 'Property A',
            'estate_company_ids': [(6, 0, [self.company_a.id])]
        })
        
    def test_user_sees_only_own_company_properties(self):
        # Authenticate as user_a
        # GET /api/v1/properties
        # Assert response contains only property_a (not property_b)
```

**Test Scenarios** (30+ total):
1. User with 1 company sees only their properties (CRUD operations)
2. User with 2 companies sees aggregated data from both
3. User with 0 companies gets empty results or 403 error
4. User cannot create property assigned to unauthorized company
5. User cannot update property to unauthorized company
6. Direct access to unauthorized property ID returns 404 (not 403)
7. Master data endpoints respect company filtering
8. System admin bypasses filtering (sees all companies)
9. Session expiry during request doesn't leak data
10. Bulk operations respect company boundaries

**Rationale**: Dedicated isolation tests catch regressions during refactoring. Separate from functional tests to enable targeted execution during code reviews.

### 5. Performance Considerations

**Decision**: Accept <10% performance degradation; optimize if p95 exceeds 200ms

**Benchmarking Plan**:
```python
# Baseline (Phase 0): GET /api/v1/properties (100 properties, no filtering)
# Target (Phase 1): Same endpoint with company filtering
# Measure: Average response time, p50, p95, p99
# Tool: Odoo built-in profiling + manual `time.time()` measurement
```

**Expected Impact**:
- Many2many join adds ~2-5ms per query (PostgreSQL benchmarks)
- Index on `company_property_rel.property_id` and `company_id` reduces overhead
- Caching user's company IDs in session reduces repeated lookups

**Mitigation**:
- Create database indexes via migration script (if not exists)
- Cache `request.user_company_ids` in request context (already done by decorator)
- Consider Redis caching for frequently accessed company data (Phase 3 optimization)

**Rationale**: Security takes precedence over performance. <10% degradation is acceptable trade-off for 100% data isolation. Real-world usage unlikely to hit limits with ~500 properties per company.

## Decisions Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **Decorator Approach** | Use existing `@require_company` | Proven pattern, already integrated, no ORM monkey-patching |
| **Query Filtering** | Manual application of `request.company_domain` | Odoo ORM doesn't support transparent interception; explicit filtering is safer |
| **Validation Service** | Enhance `CompanyValidator` with helper methods | Centralized logic prevents inconsistency |
| **Record Rules** | Implement for all estate models | Ensures Web UI consistency with API |
| **Test Strategy** | Dedicated `TestCompanyIsolation` class (30+ tests) | Enables targeted regression testing |
| **Performance** | Accept <10% degradation, optimize if needed | Security prioritized; likely won't hit limits |

## Alternatives Considered (and Rejected)

| Alternative | Why Rejected |
|-------------|--------------|
| ORM monkey-patching for transparent filtering | High complexity, maintenance burden, Odoo version compatibility risks |
| PostgreSQL row-level security (RLS) | Requires superuser privileges, breaks Odoo's security model |
| Separate databases per company | Massive complexity, loses shared master data benefits |
| Record Rules only (no decorator) | Doesn't protect REST APIs (auth='none' bypasses rules) |
| SQLAlchemy query interceptors | Odoo uses custom ORM, not SQLAlchemy |

## Open Questions (None)

✅ All technical uncertainties resolved. No NEEDS CLARIFICATION items remain.

## Next Steps

Proceed to **Phase 1: Design** to create:
1. `data-model.md` - Entity relationships and field definitions
2. `contracts/record-rules.xml` - Odoo Record Rule specifications
3. `quickstart.md` - Developer setup guide for testing isolation

---

**Research Status**: ✅ COMPLETE  
**Blockers**: None  
**Ready for Phase 1**: Yes
