#!/bin/bash
# Test: RBAC Owner Login e Acesso Total
# Spec: 005-rbac-user-profiles - User Story 1 - Scenario 1
#
# Cenário:
# - SaaS admin cria uma company
# - Cria um owner user linkado à company
# - Owner faz login
# - Owner vê todos os dados da sua company
# - Owner NÃO vê dados de outras companies

set -e

# Carregar variáveis de ambiente
if [ -f "18.0/.env" ]; then
  source 18.0/.env
else
  echo "❌ Arquivo 18.0/.env não encontrado"
  exit 1
fi

BASE_URL="http://localhost:8069"
DB="${TEST_DATABASE:-realestate}"

echo "🧪 Teste: RBAC Owner Login e Acesso Total"
echo "============================================"

# 1. Fazer login como admin para criar dados
echo ""
echo "1️⃣ Fazendo login como admin..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEST_USER_ADMIN}\",\"password\":\"${TEST_PASSWORD_ADMIN}\",\"database\":\"$DB\"}" \
  | jq -r '.access_token')

if [ "$ADMIN_TOKEN" = "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo "❌ Falha no login do admin"
  exit 1
fi

echo "✅ Admin autenticado"

# 2. Criar Company A
echo ""
echo "2️⃣ Criando Company A..."
COMPANY_A_ID=$(curl -s -X POST "$BASE_URL/api/v1/companies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Company A","vat":"12345678000190"}' \
  | jq -r '.id')

if [ "$COMPANY_A_ID" = "null" ] || [ -z "$COMPANY_A_ID" ]; then
  echo "❌ Falha ao criar Company A"
  exit 1
fi

echo "✅ Company A criada (ID: $COMPANY_A_ID)"

# 3. Criar Company B (para testar isolamento)
echo ""
echo "3️⃣ Criando Company B (para testar isolamento)..."
COMPANY_B_ID=$(curl -s -X POST "$BASE_URL/api/v1/companies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Company B","vat":"98765432000110"}' \
  | jq -r '.id')

if [ "$COMPANY_B_ID" = "null" ] || [ -z "$COMPANY_B_ID" ]; then
  echo "❌ Falha ao criar Company B"
  exit 1
fi

echo "✅ Company B criada (ID: $COMPANY_B_ID)"

# 4. Criar owner user para Company A
echo ""
echo "4️⃣ Criando owner user para Company A..."
OWNER_EMAIL="owner_test_$(date +%s)@example.com"
OWNER_PASSWORD="owner123"

OWNER_ID=$(curl -s -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test Owner\",\"login\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\",\"estate_company_ids\":[$COMPANY_A_ID],\"groups_id\":[[6,0,[\"base.group_user\",\"quicksol_estate.group_real_estate_owner\"]]]}" \
  | jq -r '.id')

if [ "$OWNER_ID" = "null" ] || [ -z "$OWNER_ID" ]; then
  echo "❌ Falha ao criar owner user"
  exit 1
fi

echo "✅ Owner user criado (ID: $OWNER_ID, Login: $OWNER_EMAIL)"

# 5. Criar propriedade na Company A
echo ""
echo "5️⃣ Criando propriedade na Company A..."
PROPERTY_A_ID=$(curl -s -X POST "$BASE_URL/api/v1/properties" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Property Company A\",\"estate_company_id\":$COMPANY_A_ID,\"expected_price\":100000}" \
  | jq -r '.id')

echo "✅ Propriedade criada na Company A (ID: $PROPERTY_A_ID)"

# 6. Criar propriedade na Company B
echo ""
echo "6️⃣ Criando propriedade na Company B..."
PROPERTY_B_ID=$(curl -s -X POST "$BASE_URL/api/v1/properties" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Property Company B\",\"estate_company_id\":$COMPANY_B_ID,\"expected_price\":200000}" \
  | jq -r '.id')

echo "✅ Propriedade criada na Company B (ID: $PROPERTY_B_ID)"

# 7. Fazer login como owner
echo ""
echo "7️⃣ Fazendo login como owner da Company A..."
OWNER_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\",\"database\":\"$DB\"}" \
  | jq -r '.access_token')

if [ "$OWNER_TOKEN" = "null" ] || [ -z "$OWNER_TOKEN" ]; then
  echo "❌ Falha no login do owner"
  exit 1
fi

echo "✅ Owner autenticado"

# 8. Owner busca propriedades (deve ver apenas da Company A)
echo ""
echo "8️⃣ Owner buscando propriedades..."
PROPERTIES=$(curl -s -X GET "$BASE_URL/api/v1/properties" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  | jq -r '.data')

PROPERTY_COUNT=$(echo $PROPERTIES | jq '. | length')
PROPERTY_A_VISIBLE=$(echo $PROPERTIES | jq "map(select(.id == $PROPERTY_A_ID)) | length")
PROPERTY_B_VISIBLE=$(echo $PROPERTIES | jq "map(select(.id == $PROPERTY_B_ID)) | length")

echo "   Total de propriedades visíveis: $PROPERTY_COUNT"
echo "   Property A (Company A) visível: $PROPERTY_A_VISIBLE"
echo "   Property B (Company B) visível: $PROPERTY_B_VISIBLE"

# 9. Validar multi-tenancy
echo ""
echo "9️⃣ Validando isolamento multi-tenancy..."

if [ "$PROPERTY_A_VISIBLE" -eq 1 ]; then
  echo "✅ Owner VÊ propriedade da sua company (Company A)"
else
  echo "❌ Owner NÃO VÊ propriedade da sua company (Company A)"
  exit 1
fi

if [ "$PROPERTY_B_VISIBLE" -eq 0 ]; then
  echo "✅ Owner NÃO VÊ propriedade de outra company (Company B)"
else
  echo "❌ Owner VÊ propriedade de outra company (Company B) - FALHA DE SEGURANÇA!"
  exit 1
fi

# 10. Cleanup (opcional - comentado para debug)
# echo ""
# echo "🧹 Limpando dados de teste..."
# curl -s -X DELETE "$BASE_URL/api/v1/properties/$PROPERTY_A_ID" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null
# curl -s -X DELETE "$BASE_URL/api/v1/properties/$PROPERTY_B_ID" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null
# curl -s -X DELETE "$BASE_URL/api/v1/users/$OWNER_ID" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null
# curl -s -X DELETE "$BASE_URL/api/v1/companies/$COMPANY_A_ID" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null
# curl -s -X DELETE "$BASE_URL/api/v1/companies/$COMPANY_B_ID" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

echo ""
echo "============================================"
echo "✨ Teste concluído com sucesso!"
echo ""
echo "📊 Resumo:"
echo "   - Company A criada e isolada"
echo "   - Owner criado e vinculado à Company A"
echo "   - Owner vê apenas dados da sua company"
echo "   - Multi-tenancy funcionando corretamente"
