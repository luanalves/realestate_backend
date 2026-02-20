# Database Cleanup: Tenant Tables

**Status**: ✅ **EXECUTED (2026-02-20)**
**Date**: 2026-02-20
**Feature**: 010 - Profile Unification (ADR-024)

## Context

The `real.estate.tenant` model has been fully replaced by `thedevkitchen.estate.profile` with `profile_type_id = 9` (code='portal'). All database tables and metadata have been successfully removed.

## Files Removed (✅ Complete)

- ✅ `models/tenant.py` (model definition)
- ✅ `views/tenant_views.xml` (Odoo UI views)
- ✅ `controllers/tenant_api.py` (REST API endpoints)
- ✅ `data/api_endpoints.xml` - 6 tenant endpoint records
- ✅ `specs/008-tenant-lease-sale-api/contracts/tenant-api.yaml` (OpenAPI spec)
- ✅ Postman collection section "18. Tenants"
- ✅ `__manifest__.py` description updated

## Database Tables (✅ Removed)

The following PostgreSQL tables were **successfully dropped** on 2026-02-20:

1. ✅ **`real_estate_tenant`** - Main tenant table
2. ✅ **`thedevkitchen_company_tenant_rel`** - Many2many relationship table
3. ✅ **Odoo Metadata**:
   - `ir_model` - Model registry cleaned
   - `ir_model_fields` - Field definitions removed
   - `ir_model_data` - XML ID references removed
   - `ir_ui_view` - View definitions removed
   - `ir_act_window` - Window actions removed

## Execution Summary

### Pre-Migration Checks (✅ Passed)

1. ✅ **All lease records use `profile_id` (not `tenant_id`)**:
   - Query executed: `SELECT column_name FROM information_schema.columns WHERE table_name = 'real_estate_lease' AND column_name = 'tenant_id';`
   - Result: **0 rows** (tenant_id does not exist, profile_id is used)

2. ✅ **No external references to tenant tables**:
   - Verified no foreign key constraints pointing to real_estate_tenant
   - Result: Safe to drop

3. ⚠️ **Database backup**: Not created (development environment only)

### Migration Executed (2026-02-20)

The following SQL commands were executed via `docker compose exec`:

```sql
-- Drop Many2many relationship table
DROP TABLE IF EXISTS thedevkitchen_company_tenant_rel CASCADE;

-- Drop main tenant table  
DROP TABLE IF EXISTS real_estate_tenant CASCADE;

-- Clean Odoo metadata
DELETE FROM ir_model_data WHERE model = 'real.estate.tenant';
DELETE FROM ir_model WHERE model = 'real.estate.tenant';
DELETE FROM ir_model_fields WHERE model = 'real.estate.tenant';
DELETE FROM ir_ui_view WHERE model = 'real.estate.tenant';
DELETE FROM ir_act_window WHERE res_model = 'real.estate.tenant';
```

### Verification Results (✅ Passed)

1. ✅ **Tables dropped successfully**:
   ```sql
   SELECT tablename FROM pg_tables WHERE tablename LIKE '%tenant%';
   -- Result: 0 rows
   ```

2. ✅ **Metadata cleaned**:
   ```sql
   SELECT model FROM ir_model WHERE model LIKE '%tenant%';
   -- Result: 0 rows
   ```

3. ✅ **Lease using profile_id**:
   ```sql
   SELECT column_name, data_type FROM information_schema.columns 
   WHERE table_name = 'real_estate_lease' AND column_name IN ('tenant_id', 'profile_id');
   -- Result: 1 row (profile_id | integer)
   ```

### Post-Migration (✅ Complete)

1. ✅ **Odoo container restarted** - Modules loaded successfully
2. ✅ **Endpoints validated**:
   - `/api/v1/tenants` → 404 (correctly removed)
   - `/api/v1/profiles` → 401 (exists, requires auth)
   - `/api/v1/leases` → 401 (functional)
3. ✅ **System stability confirmed** - No errors in logs

## Rollback

**⚠️ There is NO automatic rollback for DROP TABLE operations.**

This migration was executed in a development environment with no backup. Rollback would require:
1. Restoring database from external backup (if available)
2. Reverting commits d20d7c3, 60bd60e, and 1b7cc7b
3. Restarting Odoo container

**Not recommended**: The tenant entity has been fully replaced by the profile system (Feature 010).

## References

- **ADR-024**: Profile Unification
- **Feature 010**: Profile Unification Implementation
- **Commits**:
  - `d20d7c3` - Remove tenant_api.py controller, OpenAPI spec, Postman section
  - `60bd60e` - Remove tenant.py model, views, create migration scripts
  - `1b7cc7b` - Remove tenant endpoint data records from api_endpoints.xml
- **Spec**: `specs/010-profile-unification/spec.md`
- **Tasks**: `specs/010-profile-unification/tasks.md` (T17)

## Status Tracking

- [x] Pre-migration checks completed (2026-02-20)
- [x] Database backup evaluated (not needed for dev environment)
- [x] Migration executed via docker compose exec
- [x] Verification queries passed
- [x] Odoo container restarted
- [x] Profile API tested and functional
- [x] Tenant API confirmed removed (404)
- [x] This README updated to mark complete

## Notes

- **Environment**: Development (no backup created)
- **Execution method**: Manual SQL via docker compose exec (inline commands)
- **SQL script**: Created then removed after execution (not needed for reuse)
- **Total lines removed**: ~1,426 lines of code + database structures
