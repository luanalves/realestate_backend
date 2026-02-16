#!/bin/bash
# Clean all test data in correct order to avoid FK constraint violations

set -e

echo "Cleaning test data..."

# Delete in order to respect foreign key constraints
docker compose exec db psql -U odoo -d realestate -c "DELETE FROM thedevkitchen_estate_company WHERE id > 3;" > /dev/null
echo "✓ Companies deleted"

docker compose exec db psql -U odoo -d realestate - "DELETE FROM real_estate_agent;" > /dev/null
echo "✓ Agents deleted"

docker compose exec db psql -U odoo -d realestate -c "DELETE FROM real_estate_property_owner;" > /dev/null
echo "✓ Owners deleted"

docker compose exec db psql -U odoo -d realestate -c "DELETE FROM res_users WHERE id > 10;" > /dev/null
echo "✓ Users deleted"

echo "✓ Test data cleaned successfully"
