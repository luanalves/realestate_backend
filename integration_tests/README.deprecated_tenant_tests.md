# Deprecated Tenant Tests

**Date**: February 20, 2026
**Reason**: Feature 010 - Profile Unification (ADR-024)

## Migration Path

The following tests were deprecated after the complete removal of the Tenant API:

- `test_us8_s1_tenant_crud.sh.deprecated`
- `test_us8_s2_lease_lifecycle.sh.deprecated`
- `test_us8_s4_tenant_lease_history.sh.deprecated`
- `test_us8_s5_soft_delete.sh.deprecated`
- `test_us8_s6_isolation_rbac.sh.deprecated`

## Replacement

All tenant operations should now use the **Unified Profile API** (`/api/v1/profiles`):

### Old Endpoint (Removed)
```bash
POST /api/v1/tenants
{
  "name": "Maria Santos",
  "email": "maria@example.com",
  "phone": "(11) 98765-4321",
  "occupation": "Lawyer",
  "birthdate": "1985-03-20"
}
```

### New Endpoint (Use This)
```bash
POST /api/v1/profiles
{
  "name": "Maria Santos",
  "email": "maria@example.com",
  "document": "12345678909",
  "profile_type_id": 9,  # portal (tenant/buyer)
  "company_id": 1,
  "phone": "(11) 98765-4321",
  "occupation": "Lawyer",
  "birthdate": "1985-03-20"
}
```

## Key Changes

1. **Model Change**: `real.estate.tenant` → `thedevkitchen.estate.profile`
2. **Endpoint Change**: `/api/v1/tenants` → `/api/v1/profiles`
3. **Profile Type**: All tenants are now profile type `portal` (code='portal', id=9)
4. **Document Required**: CPF/CNPJ validation is mandatory
5. **Compound Unique**: Same person can be tenant in multiple companies or have multiple profile types

## Reference

- **ADR-024**: Profile Unification
- **Feature 010**: Profile Unification Implementation
- **Spec**: `specs/010-profile-unification/spec.md`
- **Data Model**: `specs/010-profile-unification/data-model.md`
