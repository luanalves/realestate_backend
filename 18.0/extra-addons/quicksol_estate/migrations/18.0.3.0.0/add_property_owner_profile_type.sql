-- Migration: Add Property Owner as 10th Profile Type
-- Version: 18.0.3.0.0
-- Date: 2026-02-20
-- Context: Resolve semantic ambiguity between Company Owner (profile_type owner) 
--          and Property Owner (client who owns real estate properties)
-- Reference: .investigate-property-owner.md

-- ========================================
-- STEP 1: Add profile_type record for property_owner
-- ========================================
-- Note: This will be created by profile_type_data.xml with noupdate="1"
-- This SQL is for manual execution in existing databases

DO $$
BEGIN
    -- Check if property_owner already exists
    IF NOT EXISTS (
        SELECT 1 FROM thedevkitchen_profile_type WHERE code = 'property_owner'
    ) THEN
        -- Insert new profile type
        INSERT INTO thedevkitchen_profile_type (
            code, 
            name, 
            level,
            group_xml_id,
            create_date,
            write_date
        ) VALUES (
            'property_owner',
            '{"en_US": "Proprietário de Imóvel"}',
            'external',
            'quicksol_estate.group_real_estate_property_owner',
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Property Owner profile type created successfully';
    ELSE
        RAISE NOTICE 'Property Owner profile type already exists - skipping';
    END IF;
END $$;

-- ========================================
-- STEP 2: Verify profile types
-- ========================================
-- Should return 10 rows: owner, director, manager, agent, prospector, 
--                        receptionist, financial, legal, portal, property_owner

SELECT 
    id,
    code,
    name,
    level,
    group_xml_id
FROM thedevkitchen_profile_type
ORDER BY 
    CASE level
        WHEN 'admin' THEN 1
        WHEN 'operational' THEN 2
        WHEN 'external' THEN 3
        ELSE 4
    END,
    id;

-- ========================================
-- STEP 3: (Future) Migration Plan for Property Owners
-- ========================================
-- TODO in next phase:
-- 1. Migrate existing real_estate_property_owner records to thedevkitchen_estate_profile
-- 2. Update FKs in real_estate_property.owner_id to point to profile_id
-- 3. Deprecate real_estate_property_owner model
-- 
-- NOT executing now because this requires:
-- - API endpoints update
-- - Data integrity validation
-- - Rollback strategy
-- - Full integration testing
--
-- This migration only adds the profile_type definition.

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Check if group exists
SELECT id, name FROM res_groups 
WHERE name = 'Real Estate Property Owner';

-- Count current property owners (legacy model)
SELECT COUNT(*) as legacy_property_owners 
FROM real_estate_property_owner
WHERE active = true;
