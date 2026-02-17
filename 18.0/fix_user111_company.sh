#!/bin/bash

#
# Fix user 111 (luan.pro2@gmail.com) to have a linked company
# This is required for Feature 009 tests to work
#

set -e

echo "================================"
echo "Fixing user 111 company linkage..."
echo "================================"
echo ""

# Check if PostgreSQL container is running
if ! docker ps | grep -q "db"; then
    echo "ERROR: PostgreSQL container is not running"
    echo "Start it with: cd 18.0 && docker compose up -d"
    exit 1
fi

echo "Step 1: Getting first available company ID..."

COMPANY_ID=$(docker compose exec -T db psql -U odoo -d realestate -t -c \
    "SELECT id FROM thedevkitchen_estate_company WHERE active = true ORDER BY id LIMIT 1;")

COMPANY_ID=$(echo $COMPANY_ID | tr -d ' ')

if [ -z "$COMPANY_ID" ]; then
    echo "ERROR: No active company found in database"
    echo "Please ensure company seed data is loaded"
    exit 1
fi

echo "Found company ID: $COMPANY_ID"
echo ""

echo "Step 2: Linking user 111 to company $COMPANY_ID..."

docker compose exec -T db psql -U odoo -d realestate <<EOF
-- Link user 111 to the first company
INSERT INTO thedevkitchen_user_company_rel (user_id, company_id)
VALUES (111, $COMPANY_ID)
ON CONFLICT DO NOTHING;

-- Set as main company
UPDATE res_users 
SET company_id = (SELECT id FROM res_company LIMIT 1)
WHERE id = 111;

-- Verify the linkage
SELECT 
    u.id,
    u.login,
    u.name,
    array_agg(rec.company_id) as linked_companies
FROM res_users u
LEFT JOIN thedevkitchen_user_company_rel rec ON rec.user_id = u.id
WHERE u.id = 111
GROUP BY u.id, u.login, u.name;
EOF

echo ""
echo "================================"
echo "User 111 updated successfully!"
echo "Company ID $COMPANY_ID is now linked"
echo "================================"
