# Database Cleanup: Tenant Tables

**Status**: ⚠️ **PENDING MANUAL EXECUTION**
**Date**: 2026-02-20
**Feature**: 010 - Profile Unification (ADR-024)

## Context

The `real.estate.tenant` model has been fully replaced by `thedevkitchen.estate.profile` with `profile_type_id = 9` (code='portal'). However, **database tables still exist** and must be dropped manually.

## Files Removed (✅ Complete)

- ✅ `models/tenant.py` (model definition)
- ✅ `views/tenant_views.xml` (Odoo UI views)
- ✅ `controllers/tenant_api.py` (REST API endpoints)
- ✅ `specs/008-tenant-lease-sale-api/contracts/tenant-api.yaml` (OpenAPI spec)
- ✅ Postman collection section "18. Tenants"
- ✅ `__manifest__.py` description updated

## Database Tables (❌ Still Exist)

The following PostgreSQL tables **still exist in the database**:

1. **`real_estate_tenant`** - Main tenant table
   - Columns: id, name, document, partner_id, phone, email, etc.
   - Constraint: `document_unique`

2. **`thedevkitchen_company_tenant_rel`** - Many2many relationship table
   - Links tenants to companies

3. **Odoo Metadata Tables**:
   - `ir_model` - Model registry entry for `real.estate.tenant`
   - `ir_model_fields` - Field definitions
   - `ir_model_data` - XML ID references
   - `ir_ui_view` - View definitions
   - `ir_ui_menu` - Menu items (if any)
   - `ir_act_window` - Window actions

## ⚠️ Pre-Migration Checklist

**Before dropping tables, verify:**

1. **All lease records use `profile_id` (not `tenant_id`)**:
   ```sql
   SELECT column_name 
   FROM information_schema.columns 
   WHERE table_name = 'real_estate_lease' 
     AND column_name = 'tenant_id';
   ```
   Expected: **0 rows** (if tenant_id exists, DO NOT proceed!)

2. **No external references to tenant tables**:
   ```sql
   SELECT 
     tc.table_name, 
     kcu.column_name,
     ccu.table_name AS foreign_table_name
   FROM information_schema.table_constraints AS tc
   JOIN information_schema.key_column_usage AS kcu
     ON tc.constraint_name = kcu.constraint_name
   JOIN information_schema.constraint_column_usage AS ccu
     ON ccu.constraint_name = tc.constraint_name
   WHERE ccu.table_name = 'real_estate_tenant';
   ```
   Expected: **0 rows** (no foreign keys pointing to tenant table)

3. **Backup your database**:
   ```bash
   docker compose exec db pg_dump -U odoo realestate > backup_before_tenant_drop_$(date +%Y%m%d).sql
   ```

## Migration Steps

### Step 1: Verify Current State

```bash
# Enter PostgreSQL container
docker compose exec db psql -U odoo -d realestate

# Check if tenant table exists
\dt *tenant*

# Check lease.profile_id (should exist)
\d real_estate_lease

# Exit
\q
```

### Step 2: Execute Migration Script

```bash
# From repository root
docker compose exec db psql -U odoo -d realestate -f /mnt/extra-addons/quicksol_estate/migrations/drop_tenant_tables.sql
```

**Or execute manually:**

```bash
docker compose exec db psql -U odoo -d realestate < 18.0/extra-addons/quicksol_estate/migrations/drop_tenant_tables.sql
```

### Step 3: Verify Cleanup

```sql
-- Check tables dropped
SELECT tablename FROM pg_tables WHERE tablename LIKE '%tenant%';
-- Expected: 0 rows

-- Check Odoo metadata cleaned
SELECT * FROM ir_model WHERE model LIKE '%tenant%';
-- Expected: 0 rows

-- Check lease uses profile_id
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'real_estate_lease' 
  AND column_name IN ('tenant_id', 'profile_id');
-- Expected: 1 row (profile_id only)
```

### Step 4: Optimize Database

```sql
-- Reclaim disk space
VACUUM FULL;

-- Update statistics
ANALYZE;
```

## Post-Migration

After successful cleanup:

1. **Restart Odoo container** to clear model registry cache:
   ```bash
   docker compose restart odoo
   ```

2. **Test Profile API** endpoints to ensure everything works:
   ```bash
   curl -X GET "http://localhost:8069/api/v1/profiles?page=1&page_size=10" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Openerp-Session-Id: $SESSION_ID"
   ```

3. **Update this README** to mark as complete (✅)

## Rollback

**There is NO automatic rollback for DROP TABLE operations.**

If you need to rollback:
1. Restore from backup taken in Step 1
2. Revert git commit that removed tenant.py
3. Restart Odoo

## Migration Path for Data (If Needed)

If you have existing tenant records that need migration to profiles:

```sql
-- Example: Migrate tenant → profile (adjust as needed)
INSERT INTO thedevkitchen_estate_profile 
  (name, email, document, phone, birthdate, occupation, profile_type_id, company_id, partner_id, active)
SELECT 
  t.name,
  t.email,
  t.document,
  t.phone,
  t.birthdate,
  t.occupation,
  9 as profile_type_id,  -- portal type
  c.id as company_id,  -- Get from tenant_company relation
  t.partner_id,
  t.active
FROM real_estate_tenant t
CROSS JOIN LATERAL (
  SELECT company_id FROM thedevkitchen_company_tenant_rel 
  WHERE tenant_id = t.id LIMIT 1
) c;

-- Then update lease references (if tenant_id still exists):
-- UPDATE real_estate_lease 
-- SET profile_id = (SELECT id FROM thedevkitchen_estate_profile WHERE document = ...)
-- WHERE tenant_id = ...;
```

## References

- **ADR-024**: Profile Unification
- **Feature 010**: Profile Unification Implementation
- **Commit**: d20d7c3 - "Remove deprecated Tenant API"
- **Spec**: `specs/010-profile-unification/spec.md`
- **Tasks**: `specs/010-profile-unification/tasks.md` (T17)

## Status Tracking

- [ ] Pre-migration checks completed
- [ ] Database backup created
- [ ] Migration script executed
- [ ] Verification queries passed
- [ ] Odoo container restarted
- [ ] Profile API tested
- [ ] This README updated to mark complete
