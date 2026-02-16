#!/bin/bash
set -e

echo "Reiniciando Odoo..."
docker compose -f /opt/homebrew/var/www/realestate/realestate_backend/18.0/docker-compose.yml restart odoo

echo "Aguardando Odoo inicializar..."
sleep 12

echo "Limpando dados de teste..."
docker compose -f /opt/homebrew/var/www/realestate/realestate_backend/18.0/docker-compose.yml exec -T db psql -U odoo -d realestate -c "DELETE FROM thedevkitchen_estate_company WHERE id > 3;" -c "DELETE FROM real_estate_agent;" -c "DELETE FROM real_estate_property_owner;" -c "DELETE FROM res_users WHERE id > 10;" > /dev/null 2>&1

echo "Executando S3..."
cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests
bash test_us7_s3_company_crud.sh
