#!/usr/bin/env bash
# Cleanup script for US7 integration tests
# Removes all test data created by test_us7_s*.sh scripts

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load auth helper
source "${SCRIPT_DIR}/lib/get_auth_headers.sh"

echo "============================================"
echo "US7 Data Cleanup"
echo "============================================"

# Get authentication
echo "Step 1: Authenticating..."
if ! get_full_auth; then
    echo -e "${RED}✗ Authentication failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated (JWT: ${#ACCESS_TOKEN} chars, UID: ${ADMIN_UID})${NC}"

BASE_URL="${BASE_URL:-http://localhost:8069}"

# Step 2: List all companies
echo ""
echo "Step 2: Listing companies..."
COMPANIES_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/companies?page=1&page_size=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -b ${SESSION_COOKIE_FILE})

COMPANY_COUNT=$(echo "$COMPANIES_RESPONSE" | jq -r '.data | length // 0')
echo -e "${GREEN}✓ Found ${COMPANY_COUNT} companies${NC}"

# Step 3: Delete companies (exclude ID 1 - default company)
if [ "$COMPANY_COUNT" -gt 0 ]; then
    echo ""
    echo "Step 3: Deleting test companies..."
    DELETED=0
    
    echo "$COMPANIES_RESPONSE" | jq -r '.data[] | select(.id != 1) | .id' | while read -r ID; do
        if [ -n "$ID" ]; then
            DELETE_RESP=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/companies/${ID}" \
              -H "Authorization: Bearer ${ACCESS_TOKEN}" \
              -b ${SESSION_COOKIE_FILE})
            
            HTTP_CODE=$(echo "$DELETE_RESP" | tail -n 1)
            
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
                echo -e "  ${GREEN}✓${NC} Deleted company ID=${ID}"
                DELETED=$((DELETED + 1))
            else
                echo -e "  ${YELLOW}⚠${NC} Could not delete company ID=${ID} (HTTP ${HTTP_CODE})"
            fi
        fi
    done
    
    echo -e "${GREEN}✓ Deleted ${DELETED} companies${NC}"
else
    echo -e "${YELLOW}⚠ No companies to delete${NC}"
fi

# Step 4: List all owners
echo ""
echo "Step 4: Listing owners..."
OWNERS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/owners?page=1&page_size=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -b ${SESSION_COOKIE_FILE})

# Owners API returns array directly, not {data: [...]}
OWNER_COUNT=$(echo "$OWNERS_RESPONSE" | jq -r 'if type == "array" then length else 0 end')
echo -e "${GREEN}✓ Found ${OWNER_COUNT} owners${NC}"

# Step 5: Delete owners
if [ "$OWNER_COUNT" -gt 0 ]; then
    echo ""
    echo "Step 5: Deleting test owners..."
    DELETED=0
    
    echo "$OWNERS_RESPONSE" | jq -r '.[] | .id' | while read -r ID; do
        if [ -n "$ID" ]; then
            DELETE_RESP=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/owners/${ID}" \
              -H "Authorization: Bearer ${ACCESS_TOKEN}" \
              -b ${SESSION_COOKIE_FILE})
            
            HTTP_CODE=$(echo "$DELETE_RESP" | tail -n 1)
            
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
                echo -e "  ${GREEN}✓${NC} Deleted owner ID=${ID}"
                DELETED=$((DELETED + 1))
            else
                echo -e "  ${YELLOW}⚠${NC} Could not delete owner ID=${ID} (HTTP ${HTTP_CODE})"
            fi
        fi
    done
    
    echo -e "${GREEN}✓ Deleted ${DELETED} owners${NC}"
else
    echo -e "${YELLOW}⚠ No owners to delete${NC}"
fi

echo ""
echo "============================================"
echo "✓ CLEANUP COMPLETE"
echo "============================================"
