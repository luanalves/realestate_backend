# Tenant to Profile Migration Cleanup

**Feature**: 010-profile-unification  
**Date**: 2025-01-13  
**Status**: Phase 3 Complete

## Overview

This document describes the SQL cleanup required after migrating from the `real.estate.tenant` model to the unified `thedevkitchen.estate.profile` model.

## Migration Summary

**Phase 1-2 Completed**:
- Created unified profile model with 9 profile types
- Added profile FK to agent, lease, property, company models
- Removed tenant model, controller, views, and security rules

**Phase 3 — Database Cleanup** (this document):
- Drop tenant-related tables
- Remove orphan ORM metadata entries

## Prerequisites

Before running these commands:

1. ✅ All code references to `real.estate.tenant` removed from codebase
2. ✅ Module updated via Odoo UI or `odoo-bin -u quicksol_estate`
3. ✅ All lease records migrated to use `profile_id` instead of `tenant_id`
4. ⚠️ **Database backup created** (mandatory before running DROP commands)

## SQL Cleanup Commands

### Step 1: Backup Database

```bash
# Connect to Docker container
docker compose exec db bash

# Create backup
pg_dump -U odoo -d realestate > /tmp/backup_before_tenant_cleanup_$(date +%Y%m%d_%H%M%S).sql

# Exit container
exit
```

### Step 2: Verify No Active References

```sql
-- Check if any tables still reference real_estate_tenant
SELECT 
    tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND ccu.table_name = 'real_estate_tenant';
```

**Expected Result**: 0 rows (all FKs should be migrated to profile)

### Step 3: Drop Tenant Tables

```sql
-- Connect to database
-- docker compose exec db psql -U odoo -d realestate

-- Drop tenant table (CASCADE removes dependent objects)
DROP TABLE IF EXISTS real_estate_tenant CASCADE;

-- Drop M2M join table for company-tenant relationship
DROP TABLE IF EXISTS thedevkitchen_company_tenant_rel CASCADE;
```

### Step 4: Clean ORM Metadata

```sql
-- Remove model registry entry
DELETE FROM ir_model WHERE model = 'real.estate.tenant';

-- Remove field definitions (orphans after table drop)
DELETE FROM ir_model_fields WHERE model = 'real.estate.tenant';

-- Remove model constraints
DELETE FROM ir_model_constraint WHERE model IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);

-- Remove access control entries
DELETE FROM ir_model_access WHERE model_id IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);

-- Remove record rules
DELETE FROM ir_rule WHERE model_id IN (
    SELECT id FROM ir_model WHERE model = 'real.estate.tenant'
);
```

### Step 5: Verify Cleanup

```sql
-- Check ir_model (should return 0 rows)
SELECT * FROM ir_model WHERE model = 'real.estate.tenant';

-- Check ir_model_fields (should return 0 rows)
SELECT * FROM ir_model_fields WHERE model = 'real.estate.tenant';

-- Check if tables still exist (should return no rows)
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
    AND (tablename = 'real_estate_tenant' 
         OR tablename = 'thedevkitchen_company_tenant_rel');
```

**Expected Results**: All queries return 0 rows.

### Step 6: Restart Odoo

After database cleanup, restart Odoo to clear cached model registry:

```bash
docker compose restart odoo
```

## Verification Checklist

After cleanup:

- [ ] `real_estate_tenant` table dropped
- [ ] `thedevkitchen_company_tenant_rel` table dropped
- [ ] `ir_model` has no `real.estate.tenant` entry
- [ ] `ir_model_fields` has no fields for `real.estate.tenant`
- [ ] `ir_model_access` has no tenant ACL entries
- [ ] `ir_rule` has no tenant record rules
- [ ] Odoo server restarts without errors
- [ ] Module list shows no "Uninstallable" errors for `quicksol_estate`
- [ ] Lease endpoints work with `profile_id` parameter
- [ ] No 500 errors in Odoo logs referencing `real.estate.tenant`

## Rollback Plan

If issues occur after cleanup:

1. **Restore database backup**:
   ```bash
   docker compose exec db psql -U odoo -d realestate < /tmp/backup_before_tenant_cleanup_YYYYMMDD_HHMMSS.sql
   ```

2. **Revert code changes** (git):
   ```bash
   git revert <commit-hash>  # Revert Phase 3 commits
   ```

3. **Update module**:
   ```bash
   docker compose exec odoo odoo-bin -u quicksol_estate -d realestate --stop-after-init
   ```

## Migration Status

**Commits**:
- `dac8520`: Phase 1 — Profile schema creation (T01-T10)
- `ffe161b`: Phase 2 Part 1 — Profile controller + unit tests (T11, T14-T16)
- `ee349d5`: Phase 2 Part 2 — Invite flow integration (T12-T13)
- TBD: Phase 3 — Cleanup (T17-T20, this document)

**Files Modified**:
- Deleted: `models/tenant.py`, `controllers/tenant_api.py`, `views/tenant_views.xml`
- Updated: `models/lease.py`, `models/property.py`, `models/company.py`
- Updated: `controllers/lease_api.py`, `controllers/utils/schema.py`
- Updated: `security/ir.model.access.csv`, `security/record_rules.xml`
- Updated: `models/__init__.py`, `controllers/__init__.py`, `__manifest__.py`

## References

- **ADR-024**: Profile Unification Architecture
- **Feature 010 Spec**: `specs/010-profile-unification/spec.md`
- **Data Model**: `specs/010-profile-unification/data-model.md`
- **Tasks**: `specs/010-profile-unification/tasks.md` (T20)
