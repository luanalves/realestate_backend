-- Create owner@example.com user and profile for E2E tests
-- Step 1: Create partner
INSERT INTO res_partner (name, email, active, create_date, write_date, company_id)
VALUES ('Owner Example', 'owner@example.com', true, NOW(), NOW(), 1)
ON CONFLICT DO NOTHING;

-- Step 2: Create user (Odoo will hash password on first use)
WITH new_partner AS (
  SELECT id FROM res_partner WHERE email = 'owner@example.com' LIMIT 1
)
INSERT INTO res_users (login, password, partner_id, active, notification_type, create_date, write_date, company_id)
SELECT 'owner@example.com', 'SecurePass123!', id, true, 'inbox', NOW(), NOW(), 1
FROM new_partner
ON CONFLICT (login) DO UPDATE SET password = 'SecurePass123!';

-- Step 2.5: Configure user company access
WITH user_info AS (
  SELECT id FROM res_users WHERE login = 'owner@example.com'
)
INSERT INTO thedevkitchen_user_company_rel (user_id, company_id)
SELECT id, 1 FROM user_info
ON CONFLICT DO NOTHING;

UPDATE res_users 
SET main_estate_company_id = 1
WHERE login = 'owner@example.com';

-- Step 2.6: Add user to owner security group (required for RBAC)
WITH user_info AS (
  SELECT id FROM res_users WHERE login = 'owner@example.com'
),
owner_group AS (
  SELECT res_id FROM ir_model_data 
  WHERE model = 'res.groups' 
  AND module = 'quicksol_estate' 
  AND name = 'group_real_estate_owner'
)
INSERT INTO res_groups_users_rel (gid, uid)
SELECT owner_group.res_id, user_info.id
FROM owner_group, user_info
ON CONFLICT DO NOTHING;

-- Step 3: Create owner profile
WITH new_user AS (
  SELECT u.id as user_id, u.partner_id 
  FROM res_users u 
  WHERE u.login = 'owner@example.com'
  LIMIT 1
),
owner_type AS (
  SELECT id FROM thedevkitchen_profile_type WHERE code = 'owner' LIMIT 1
)
INSERT INTO thedevkitchen_estate_profile (
  profile_type_id, company_id, partner_id, name, document, document_normalized,
  email, birthdate, active, created_at, write_date, create_date
)
SELECT 
  owner_type.id, 1, new_user.partner_id, 'Owner Example', '987.654.321-00', '98765432100',
  'owner@example.com', '1975-05-20', true, NOW(), NOW(), NOW()
FROM new_user, owner_type
ON CONFLICT (document, company_id, profile_type_id) DO NOTHING;

-- Verify
SELECT 
  u.id as user_id, u.login, p.name as partner_name,
  ep.id as profile_id, pt.code as profile_type
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
LEFT JOIN thedevkitchen_estate_profile ep ON ep.partner_id = u.partner_id
LEFT JOIN thedevkitchen_profile_type pt ON ep.profile_type_id = pt.id
WHERE u.login = 'owner@example.com';
