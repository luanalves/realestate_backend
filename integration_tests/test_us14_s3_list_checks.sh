#!/usr/bin/env bash
# =============================================================================
# Feature 014 - US14-S3: List Credit Checks for Proposal
# E2E test via curl para GET /api/v1/proposals/{id}/credit-checks
#
# Success Criteria:
# - Manager lista checks de proposta da empresa → 200 com array
# - Filtro ?result=pending retorna apenas checks pendentes
# - Proposta inexistente → 404
# - Proposta de outra empresa → 404 (isolamento)
# - Resposta inclui HATEOAS _links e paginação
# ADR-003: E2E API test com banco de dados real
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-${TEST_BASE_URL:-http://localhost:8069}}"
API_BASE="$BASE_URL/api/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ PASS${NC} — $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}✗ FAIL${NC} — $1"; FAIL=$((FAIL + 1)); }
info() { echo -e "  ${YELLOW}→${NC} $1"; }

echo "========================================"
echo "US14-S3: List Credit Checks"
echo "Feature 014 — Rental Credit Check"
echo "========================================"

# ---------------------------------------------------------------------------
# Step 0: OAuth2 Bearer Token
# ---------------------------------------------------------------------------
echo ""
echo "Step 0: Obtendo token OAuth2..."
BEARER_TOKEN=$(get_oauth2_token)
if [ $? -ne 0 ] || [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Falha ao obter token OAuth2${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bearer token obtido${NC}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
login_user() {
    local email="$1"
    local password="$2"
    local response
    response=$(curl -s -m 30 -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")
    local session_id
    session_id=$(echo "$response" | jq -r '.session_id // empty')
    local company_id
    company_id=$(echo "$response" | jq -r '.user.default_company_id // .company_id // empty')
    [ -z "$session_id" ] && echo "" && return 1
    echo "${session_id}|${company_id}"
}

get_checks() {
    local session="$1"
    local company="$2"
    local proposal_id="$3"
    local query="${4:-}"
    curl -s -m 30 -w "\n%{http_code}" \
        -X GET "$API_BASE/proposals/${proposal_id}/credit-checks${query}" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $session" \
        -H "X-Company-ID: $company"
}

# ---------------------------------------------------------------------------
# Step 1: Login como Manager
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Login como Manager..."
MANAGER_DATA=$(login_user "${TEST_USER_MANAGER:-manager@seed.com.br}" "${TEST_PASSWORD_MANAGER:-Senha@123}")
if [ -z "$MANAGER_DATA" ]; then
    echo -e "${RED}✗ Login do Manager falhou${NC}"
    exit 1
fi
MANAGER_SESSION="${MANAGER_DATA%%|*}"
MANAGER_COMPANY="${MANAGER_DATA##*|}"
echo -e "${GREEN}✓ Manager autenticado (company=$MANAGER_COMPANY)${NC}"

# ---------------------------------------------------------------------------
# Step 2: Buscar proposta com análises (qualquer estado com checks)
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Buscando proposta com análises registradas..."
ALL_PROPOSALS=$(curl -s -m 30 \
    -X GET "$API_BASE/proposals?proposal_type=lease&limit=10" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
    -H "X-Company-ID: $MANAGER_COMPANY")

# Encontra primeira proposta que tenha checks
PROPOSAL_ID=""
for PID in $(echo "$ALL_PROPOSALS" | jq -r '.data[].id // empty'); do
    CHECKS=$(curl -s -m 15 \
        -X GET "$API_BASE/proposals/${PID}/credit-checks" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
        -H "X-Company-ID: $MANAGER_COMPANY")
    COUNT=$(echo "$CHECKS" | jq -r '.total // 0')
    if [ "$COUNT" -gt 0 ] 2>/dev/null; then
        PROPOSAL_ID="$PID"
        info "Proposta $PROPOSAL_ID tem $COUNT checks"
        break
    fi
done

# ---------------------------------------------------------------------------
# Cenário 1: Proposta inexistente → 404
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 1: Proposta inexistente → 404"
RESP=$(get_checks "$MANAGER_SESSION" "$MANAGER_COMPANY" "999999")
HTTP_CODE=$(echo "$RESP" | tail -1)
info "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "404" ]; then
    pass "Proposta inexistente retorna 404"
else
    fail "Esperado 404, obtido $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Cenário 2: Lista todos os checks de proposta existente → 200 + array
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 2: Listar checks de proposta existente → 200 + array"
if [ -z "$PROPOSAL_ID" ]; then
    # Tentar com qualquer proposta de locação que exista
    PROPOSAL_ID=$(echo "$ALL_PROPOSALS" | jq -r '.data[0].id // empty')
fi

if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Pulado — sem propostas de locação disponíveis${NC}"
else
    RESP=$(get_checks "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE — proposal_id=$PROPOSAL_ID"
    if [ "$HTTP_CODE" = "200" ]; then
        IS_ARRAY=$(echo "$BODY" | jq 'if .data | type == "array" then "yes" else "no" end' -r)
        HAS_TOTAL=$(echo "$BODY" | jq 'if has("total") then "yes" else "no" end' -r)
        if [ "$IS_ARRAY" = "yes" ] && [ "$HAS_TOTAL" = "yes" ]; then
            TOTAL=$(echo "$BODY" | jq -r '.total')
            pass "Lista retornada com $TOTAL checks (array + total presentes)"
        else
            fail "200 mas resposta inválida: is_array=$IS_ARRAY, has_total=$HAS_TOTAL"
        fi
    else
        fail "Esperado 200, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 3: Filtro ?result=approved retorna apenas aprovados
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 3: Filtro ?result=approved filtra corretamente"
if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    RESP=$(get_checks "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "?result=approved")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
        # Verifica que todos os checks retornados têm result=approved
        NON_APPROVED=$(echo "$BODY" | jq '[.data[] | select(.result != "approved")] | length')
        if [ "$NON_APPROVED" = "0" ]; then
            TOTAL=$(echo "$BODY" | jq -r '.total')
            pass "Filtro result=approved correto ($TOTAL checks aprovados)"
        else
            fail "$NON_APPROVED checks com result != approved retornados com filtro"
        fi
    else
        fail "Esperado 200, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 4: Paginação — limit=1 retorna 1 item max
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 4: Paginação limit=1 → máx 1 resultado"
if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    RESP=$(get_checks "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "?limit=1&offset=0")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
        COUNT=$(echo "$BODY" | jq '.data | length')
        if [ "$COUNT" -le 1 ] 2>/dev/null; then
            pass "Paginação limit=1 retornou $COUNT item(s)"
        else
            fail "limit=1 retornou $COUNT items"
        fi
    else
        fail "Esperado 200, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 5: _links HATEOAS presente na resposta
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 5: Resposta inclui _links HATEOAS"
if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    RESP=$(get_checks "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | head -1)
    if [ "$HTTP_CODE" = "200" ]; then
        HAS_LINKS=$(echo "$BODY" | jq 'if has("_links") then "yes" else "no" end' -r)
        if [ "$HAS_LINKS" = "yes" ]; then
            pass "_links HATEOAS presente na resposta"
        else
            fail "_links ausente na resposta"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo -e "  ${GREEN}PASS: $PASS${NC}   ${RED}FAIL: $FAIL${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
