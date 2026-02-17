#!/bin/bash

#
# Helper script to list available companies in the database
# This helps identify which company ID to use in X-Company-ID header for API tests
#

set -e

echo "================================"
echo "Listando empresas disponíveis..."
echo "================================"
echo ""

# Check if PostgreSQL container is running
if ! docker ps | grep -q postgres16; then
    echo "ERROR: PostgreSQL container is not running"
    echo "Start it with: docker compose up -d"
    exit 1
fi

# Execute SQL query
docker compose exec -T db psql -U odoo -d realestate <<'EOF'
\x
SELECT 
    id,
    name,
    legal_name,
    cnpj,
    active,
    create_date
FROM thedevkitchen_estate_company
ORDER BY id;
EOF

echo ""
echo "================================"
echo "Total de empresas ativas:"
echo "================================"

docker compose exec -T db psql -U odoo -d realestate -t -c \
    "SELECT COUNT(*) as total FROM thedevkitchen_estate_company WHERE active = true;"

echo ""
echo "Use o ID da empresa listada acima no header X-Company-ID dos testes"
