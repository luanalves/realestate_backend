# Migration 18.0.3.0.0: Add Property Owner Profile Type

**Date**: 2026-02-20  
**Priority**: High  
**Breaking Changes**: No  
**Rollback**: Safe (only adds new profile type)

## Context

### Problem Identified

**Semantic Ambiguity**: The profile type `code='owner'` (id=1) was being used for **Company Owner** (owner of the real estate company), but Feature 009 specifications expect to invite **Property Owner** (client who owns properties) using `profile='owner'`.

This creates a conflict:
- **Company Owner** (`res.users` + `group_real_estate_owner`): Administrator of the company in the system
- **Property Owner** (`real.estate.property.owner`): Client who owns real estate properties

### Solution

Add **10th profile type**: `property_owner` to distinguish between:
1. `owner` → Company Owner (admin)
2. `property_owner` → Property Owner (external client)

## Changes

### 1. New Profile Type
- **Code**: `property_owner`
- **Name**: "Proprietário de Imóvel"
- **Level**: `external`
- **Group**: `group_real_estate_property_owner`

### 2. Files Modified
- `data/profile_type_data.xml` - Add property_owner record
- `security/groups.xml` - Add group_real_estate_property_owner
- `migrations/18.0.3.0.0/add_property_owner_profile_type.sql` - Migration script

## Execution

### Automatic (New Installations)
- Profile type will be created automatically via XML data file

### Manual (Existing Databases)

```bash
# Execute SQL script
cd 18.0
docker compose exec db psql -U odoo -d realestate \
  -f /opt/homebrew/var/www/realestate/realestate_backend/18.0/extra-addons/quicksol_estate/migrations/18.0.3.0.0/add_property_owner_profile_type.sql
```

### Verification

```sql
-- Should return 10 profile types
SELECT code, name, level FROM thedevkitchen_profile_type ORDER BY id;

-- Verify group exists
SELECT name FROM res_groups WHERE name = 'Real Estate Property Owner';
```

## Impact Analysis

### ✅ No Breaking Changes
- Existing profile types unchanged
- No data migration required in this phase
- APIs remain compatible

### 📋 Future Work (Next Phase)
1. Migrate `real_estate_property_owner` → `thedevkitchen_estate_profile`
2. Update Feature 009 to use `property_owner` instead of `owner`
3. Create API endpoints for property owner management
4. Update authorization matrix (Agent can invite property_owner)

## Authorization Matrix Update

| Profile | Can Create | Updated |
|---------|-----------|---------|
| Owner | All 10 types | ✅ |
| Manager | 5 operational (agent, prospector, receptionist, financial, legal) | No change |
| Agent | **property_owner** + tenant | ✅ Changed from "owner" to "property_owner" |

## References

- Investigation: `.investigate-property-owner.md`
- ADR-024: Profile Unification (update to 10 types)
- Feature 009: User Onboarding (Agent invites property_owner)
- DEC-011 (Feature 007): Company Owner vs Property Owner terminology

## Rollback

If needed:
```sql
-- Remove profile type
DELETE FROM thedevkitchen_profile_type WHERE code = 'property_owner';

-- Remove group (if safe - check dependencies first)
-- DELETE FROM res_groups WHERE name = 'Real Estate Property Owner';
```

## Status

- [x] Profile type definition created
- [x] Security group added
- [x] Migration script created
- [ ] ADR-024 updated (9 → 10 types)
- [ ] Feature 009 specs updated
- [ ] Data migration from real_estate_property_owner (Phase 2)
- [ ] API endpoints created (Phase 2)
