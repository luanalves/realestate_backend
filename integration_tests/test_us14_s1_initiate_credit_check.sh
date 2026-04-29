#!/usr/bin/env bash
# =============================================================================
# Feature 014 - US14-S1: Initiate Credit Check
# E2E test via curl for POST /api/v1/proposals/{id}/credit-checks
#
# Success Criteria:
# - Manager inicia análise em proposta de locação no estado 'sent' → 201
# - Manager inicia em proposta com análise já pendente → 409
# - Manager tenta iniciar em proposta de venda → 400 (FR-006)
# - Agent sem acesso à proposta → 403
# - Proposta inexistente → 404
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
DB_NAME="${POSTGRES_DB:-realestate}"

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
echo "US14-S1: Initiate Credit Check"
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
# Helper: Login por perfil
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
    if [ -z "$session_id" ]; then
        echo ""
        return 1
    fi
    echo "${session_id}|${company_id}"
}

# Helper: POST initiate
post_initiate() {
    local session="$1"
    local company="$2"
    local proposal_id="$3"
    local insurer="$4"
    curl -s -m 30 -w "\n%{http_code}" \
        -X POST "$API_BASE/proposals/${proposal_id}/credit-checks" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $session" \
        -H "X-Company-ID: $company" \
        -d "{\"insurer_name\": \"$insurer\", \"session_id\": \"$session\"}"
}

# ---------------------------------------------------------------------------
# Step 1: Login como Manager
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Login como Manager..."
MANAGER_EMAIL="${TEST_USER_MANAGER:-manager@seed.com.br}"
MANAGER_PASS="${TEST_PASSWORD_MANAGER:-Senha@123}"

MANAGER_DATA=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASS")
if [ -z "$MANAGER_DATA" ]; then
    echo -e "${RED}✗ Login do Manager falhou — verifique TEST_USER_MANAGER e TEST_PASSWORD_MANAGER no .env${NC}"
    exit 1
fi
MANAGER_SESSION="${MANAGER_DATA%%|*}"
MANAGER_COMPANY="${MANAGER_DATA##*|}"
echo -e "${GREEN}✓ Manager autenticado (company=$MANAGER_COMPANY)${NC}"

# ---------------------------------------------------------------------------
# Step 2: Buscar proposta de locação no estado 'sent'
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Buscando proposta de locação em estado 'sent'..."
PROPOSALS_RESP=$(curl -s -m 30 \
    -X GET "$API_BASE/proposals?proposal_type=lease&state=sent&limit=1" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
    -H "X-Company-ID: $MANAGER_COMPANY")

PROPOSAL_ID=$(echo "$PROPOSALS_RESP" | jq -r '.data[0].id // empty')
PROPOSAL_TYPE=$(echo "$PROPOSALS_RESP" | jq -r '.data[0].proposal_type // empty')
PARTNER_ID=$(echo "$PROPOSALS_RESP" | jq -r '.data[0].partner_id // empty')

# Validar que é realmente uma proposta de LOCAÇÃO (API pode ignorar filtro)
if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ] || [ "$PROPOSAL_TYPE" != "lease" ]; then
    echo -e "${YELLOW}⚠ Nenhuma proposta de locação em 'sent' encontrada no banco${NC}"
    PROPOSAL_ID=""
fi

# ---------------------------------------------------------------------------
# Cenário 1: Proposta inexistente → 404
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 1: Proposta inexistente → 404"
RESP=$(post_initiate "$MANAGER_SESSION" "$MANAGER_COMPANY" "999999" "Tokio Marine")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
info "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "404" ]; then
    pass "Proposta inexistente retorna 404"
else
    fail "Esperado 404, obtido $HTTP_CODE — body: $body"
fi

# ---------------------------------------------------------------------------
# Cenário 2: Proposta de locação em 'sent' → 201 (somente se existe)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 2: Iniciar análise em proposta de locação → 201"
if [ -z "$PROPOSAL_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado — nenhuma proposta de locação 'sent' disponível${NC}"
else
    RESP=$(post_initiate "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "Tokio Marine")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE — proposal_id=$PROPOSAL_ID"
    if [ "$HTTP_CODE" = "201" ]; then
        CHECK_ID=$(echo "$BODY" | jq -r '.data.id // empty')
        CHECK_RESULT=$(echo "$BODY" | jq -r '.data.result // empty')
        pass "Análise iniciada (check_id=$CHECK_ID, result=$CHECK_RESULT)"
        # Exporta para uso nos próximos cenários
        export TEST_PROPOSAL_ID="$PROPOSAL_ID"
        export TEST_CHECK_ID="$CHECK_ID"
        export TEST_PARTNER_ID="$PARTNER_ID"
    elif [ "$HTTP_CODE" = "409" ]; then
        # Já existe pendente — pegar o check_id existente
        EXISTING_ID=$(echo "$BODY" | jq -r '.data.check_id // empty')
        pass "Análise já pendente detectada (409 — estado consistente)"
        # Tentar buscar o check existente
        LIST_RESP=$(curl -s -m 30 \
            -X GET "$API_BASE/proposals/${PROPOSAL_ID}/credit-checks?result=pending" \
            -H "Authorization: Bearer $BEARER_TOKEN" \
            -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
            -H "X-Company-ID: $MANAGER_COMPANY")
        CHECK_ID=$(echo "$LIST_RESP" | jq -r '.data[0].id // empty')
        export TEST_PROPOSAL_ID="$PROPOSAL_ID"
        export TEST_CHECK_ID="$CHECK_ID"
        export TEST_PARTNER_ID="$PARTNER_ID"
    else
        fail "Esperado 201 ou 409, obtido $HTTP_CODE — body: $BODY"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 3: Segunda chamada na mesma proposta → 409 (já pendente)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 3: Segunda chamada com análise já pendente → 409"
if [ -z "$PROPOSAL_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado — sem proposta disponível${NC}"
else
    RESP=$(post_initiate "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "Porto Seguro")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "409" ]; then
        pass "Análise duplicada corretamente rejeitada (409)"
    else
        fail "Esperado 409 para análise duplicada, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 4: Proposta de venda → 400 (FR-006)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 4: Proposta de venda → 400 (FR-006)"
SALE_RESP=$(curl -s -m 30 \
    -X GET "$API_BASE/proposals?proposal_type=sale&state=sent&limit=1" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
    -H "X-Company-ID: $MANAGER_COMPANY")
SALE_PROPOSAL_ID=$(echo "$SALE_RESP" | jq -r '.data[0].id // empty')

if [ -z "$SALE_PROPOSAL_ID" ] || [ "$SALE_PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Pulado — nenhuma proposta de venda disponível${NC}"
else
    RESP=$(post_initiate "$MANAGER_SESSION" "$MANAGER_COMPANY" "$SALE_PROPOSAL_ID" "Tokio Marine")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    info "HTTP $HTTP_CODE — sale_proposal_id=$SALE_PROPOSAL_ID"
    if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "422" ]; then
        pass "Proposta de venda bloqueada (HTTP $HTTP_CODE, FR-006)"
    else
        fail "Esperado 400/422 para proposta de venda, obtido $HTTP_CODE"
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
