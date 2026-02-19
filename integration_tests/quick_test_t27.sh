#!/bin/bash
# Quick test for T27 multi-tenancy

cd "$(dirname "$0")/../18.0"
source .env

BASE_URL="http://localhost:8069"

# Function to generate valid CPF with timestamp
generate_cpf() {
    local ts=$(date +%s)
    local base=$(printf "%09d" $((ts % 1000000000)))
    
    # Calculate first check digit
    local sum=0
    for i in {0..8}; do
        local digit=${base:$i:1}
        local mult=$((10 - i))
        sum=$((sum + digit * mult))
    done
    local d1=$((11 - (sum % 11)))
    [ $d1 -ge 10 ] && d1=0
    
    # Calculate second check digit
    sum=0
    for i in {0..8}; do
        local digit=${base:$i:1}
        local mult=$((11 - i))
        sum=$((sum + digit * mult))
    done
    sum=$((sum + d1 * 2))
    local d2=$((11 - (sum % 11)))
    [ $d2 -ge 10 ] && d2=0
    
    echo "${base}${d1}${d2}"
}

echo "=== Testing Multi-Tenancy (T27) ==="
echo ""

# Step 1: Get OAuth token
echo "1. Getting OAuth token..."
TOKEN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${OAUTH_CLIENT_ID}&client_secret=${OAUTH_CLIENT_SECRET}")

BEARER=$(echo "$TOKEN_RESP" | jq -r '.access_token // empty')
if [ -z "$BEARER" ]; then
  echo "ERROR: Failed to get OAuth token"
  echo "$TOKEN_RESP"
  exit 1
fi
echo "✓ OAuth token obtained"

# Step 2: Login Owner A
echo ""
echo "2. Login Owner A ($TEST_USER_OWNER)..."
LOGIN_A=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer $BEARER" \
  -H "Content-Type: application/json" \
  -d "{\"login\": \"$TEST_USER_OWNER\", \"password\": \"$TEST_PASSWORD_OWNER\"}")

SESSION_A=$(echo "$LOGIN_A" | jq -r '.session_id // empty')
COMPANY_A=$(echo "$LOGIN_A" | jq -r '.user.main_estate_company_id // empty')

if [ -z "$SESSION_A" ] || [ "$COMPANY_A" == "null" ]; then
  echo "ERROR: Owner A login failed"
  echo "$LOGIN_A"
  exit 1
fi
echo "✓ Owner A logged in (Company $COMPANY_A)"

# Step 3: Login Owner B
echo ""
echo "3. Login Owner B ($TEST_USER_OWNER_B)..."
LOGIN_B=$(curl -s -X POST "$BASE_URL/api/v1/users/login" \
  -H "Authorization: Bearer $BEARER" \
  -H "Content-Type: application/json" \
  -d "{\"login\": \"$TEST_USER_OWNER_B\", \"password\": \"$TEST_PASSWORD_OWNER_B\"}")

SESSION_B=$(echo "$LOGIN_B" | jq -r '.session_id // empty')
COMPANY_B=$(echo "$LOGIN_B" | jq -r '.user.main_estate_company_id // empty')

if [ -z "$SESSION_B" ] || [ "$COMPANY_B" == "null" ]; then
  echo "ERROR: Owner B login failed"
  echo "$LOGIN_B"
  exit 1
fi
echo "✓ Owner B logged in (Company $COMPANY_B)"

# Step 4: Verify different companies
echo ""
echo "4. Verifying companies are different..."
if [ "$COMPANY_A" == "$COMPANY_B" ]; then
  echo "ERROR: Both owners have the same company ($COMPANY_A)"
  exit 1
fi
echo "✓ Company A=$COMPANY_A, Company B=$COMPANY_B (different)"

# Step 5: Create profile in Company A
echo ""
echo "5. Creating profile in Company A..."
TS=$(date +%s)
CPF=$(generate_cpf)

CREATE_A=$(curl -s -w "\nHTTP:%{http_code}" -X POST "$BASE_URL/api/v1/profiles" \
  -H "Authorization: Bearer $BEARER" \
  -H "X-Openerp-Session-Id: $SESSION_A" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Profile CompanyA\",
    \"company_id\": $COMPANY_A,
    \"document\": \"$CPF\",
    \"email\": \"testa_$TS@test.com\",
    \"phone\": \"11999998888\",
    \"birthdate\": \"1985-06-10\",
    \"profile_type\": \"manager\"
  }")

HTTP_CODE=$(echo "$CREATE_A" | tail -n1 | sed 's/HTTP://')
BODY=$(echo "$CREATE_A" | sed '$d')
PROFILE_A=$(echo "$BODY" | jq -r '.id // empty')

if [ -z "$PROFILE_A" ] || [ "$HTTP_CODE" != "201" ]; then
  echo "ERROR: Failed to create profile in Company A (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi
echo "✓ Profile created in Company A (ID=$PROFILE_A, CPF=$CPF)"

# Step 6: Create profile with same document in Company B
echo ""
echo "6. Creating profile with same document in Company B..."
CREATE_B=$(curl -s -w "\nHTTP:%{http_code}" -X POST "$BASE_URL/api/v1/profiles" \
  -H "Authorization: Bearer $BEARER" \
  -H "X-Openerp-Session-Id: $SESSION_B" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Profile CompanyB\",
    \"company_id\": $COMPANY_B,
    \"document\": \"$CPF\",
    \"email\": \"testb_$TS@test.com\",
    \"phone\": \"11988887777\",
    \"birthdate\": \"1987-09-15\",
    \"profile_type\": \"manager\"
  }")

HTTP_CODE=$(echo "$CREATE_B" | tail -n1 | sed 's/HTTP://')
BODY=$(echo "$CREATE_B" | sed '$d')
PROFILE_B=$(echo "$BODY" | jq -r '.id // empty')

if [ -z "$PROFILE_B" ] || [ "$HTTP_CODE" != "201" ]; then
  echo "ERROR: Should allow same document in different company (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi
echo "✓ Same document allowed in Company B (ID=$PROFILE_B)"

# Step 7: Cross-company read (should fail)
echo ""
echo "7. Testing cross-company read (Company A tries to read Company B profile)..."
READ_CROSS=$(curl -s -w "\nHTTP:%{http_code}" -X GET "$BASE_URL/api/v1/profiles/$PROFILE_B?company_ids=$COMPANY_A" \
  -H "Authorization: Bearer $BEARER" \
  -H "X-Openerp-Session-Id: $SESSION_A")

HTTP_CODE=$(echo "$READ_CROSS" | tail -n1 | sed 's/HTTP://')
if [ "$HTTP_CODE" != "404" ]; then
  echo "ERROR: Cross-company read should return 404, got $HTTP_CODE"
  exit 1
fi
echo "✓ Cross-company read blocked (404)"

echo ""
echo "=== ✓ All multi-tenancy tests PASSED ==="
exit 0
