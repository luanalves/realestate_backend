#!/bin/bash
# Recreate Owner B for multi-tenancy testing

cd "$(dirname "$0")/../18.0"

echo "=== Recreating Owner B (Urban Properties) ==="

# Generate password hash
echo "1. Generating password hash..."
PASSWORD_HASH=$(docker compose exec odoo python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['pbkdf2_sha512'], deprecated='auto')
print(pwd_context.hash('OwnerB123!'))
")
echo "✓ Password hash generated"

# Execute SQL to create Owner B
echo ""
echo "2. Creating Owner B user and profile..."
docker compose exec -T db psql -U odoo -d realestate << EOSQL
-- Get profile type and group IDs
DO \$\$
DECLARE
    v_partner_id INTEGER;
    v_user_id INTEGER;
    v_owner_type_id INTEGER;
    v_owner_group_id INTEGER;
BEGIN
    -- Get owner profile type
    SELECT id INTO v_owner_type_id FROM thedevkitchen_profile_type WHERE code = 'owner' LIMIT 1;
    
    -- Get owner Odoo group
    SELECT res_id INTO v_owner_group_id FROM ir_model_data 
    WHERE module = 'quicksol_estate' AND name = 'group_real_estate_owner' AND model = 'res.groups' LIMIT 1;
    
    -- Create partner
    INSERT INTO res_partner (name, company_id, email, active, create_date, write_date, create_uid, write_uid)
    VALUES ('Owner Company B', 1, 'owner2@example.com', true, NOW(), NOW(), 2, 2)
    RETURNING id INTO v_partner_id;
    
    -- Create user
    INSERT INTO res_users (
        login, password, partner_id, company_id, active, notification_type,
        main_estate_company_id, create_date, write_date, create_uid, write_uid
    ) VALUES (
        'owner2@example.com',
        '$PASSWORD_HASH',
        v_partner_id,
        1,  -- Odoo res_company (must be 1)
        true,
        'email',
        2,  -- Urban Properties
        NOW(), NOW(), 2, 2
    ) RETURNING id INTO v_user_id;
    
    -- Associate with estate company via Many2many
    INSERT INTO thedevkitchen_user_company_rel (user_id, company_id)
    VALUES (v_user_id, 2)
    ON CONFLICT DO NOTHING;
    
    -- Create estate profile
    INSERT INTO thedevkitchen_estate_profile (
        name, partner_id, company_id, profile_type_id,
        document, email, birthdate, created_at, updated_at
    ) VALUES (
        'Owner Company B',
        v_partner_id,
        2,  -- Urban Properties
        v_owner_type_id,
        '98765432109',
        'owner2@example.com',
        '1980-01-01',
        NOW(), NOW()
    );
    
    -- Add to Odoo group
    IF v_owner_group_id IS NOT NULL THEN
        INSERT INTO res_groups_users_rel (gid, uid)
        VALUES (v_owner_group_id, v_user_id)
        ON CONFLICT DO NOTHING;
    END IF;
    
    RAISE NOTICE 'Owner B created: user_id=%, partner_id=%', v_user_id, v_partner_id;
END \$\$;

-- Verify
SELECT 
    u.id as user_id,
    u.login,
    u.main_estate_company_id,
    ec.name as estate_company,
    p.id as profile_id,
    pt.code as profile_type,
    CASE WHEN gur.uid IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_owner_group
FROM res_users u
LEFT JOIN thedevkitchen_estate_company ec ON u.main_estate_company_id = ec.id
LEFT JOIN thedevkitchen_estate_profile p ON p.partner_id = u.partner_id
LEFT JOIN thedevkitchen_profile_type pt ON p.profile_type_id = pt.id
LEFT JOIN (
    SELECT gur2.uid
    FROM res_groups_users_rel gur2
    INNER JOIN ir_model_data imd ON imd.res_id = gur2.gid AND imd.model = 'res.groups'
    WHERE imd.module = 'quicksol_estate' AND imd.name = 'group_real_estate_owner'
) gur ON gur.uid = u.id
WHERE u.login = 'owner2@example.com';
EOSQL

echo ""
echo "=== ✓ Owner B setup complete ==="
